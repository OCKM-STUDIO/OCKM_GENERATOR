#include "EngineBridge.h"
#include "z_libpd.h"
#include <CoreMIDI/CoreMIDI.h>
#include <atomic>
#include <thread>
#include <mutex>
#include <deque>
#include <vector>
#include <string>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <sstream>
#include <iomanip>
extern "C" void pdlua_setup(void);

namespace {
constexpr uint64_t capacity=16384, target=1024;
float ring[capacity*2]{};
std::atomic<uint64_t> written{0},readAt{0},underruns{0};
std::atomic<bool> running{false};
std::thread worker;
std::mutex commandMutex, frameMutex, logMutex;
struct Command {std::string receiver, selector, symbol; float a=0,b=0; int count=0; std::vector<uint8_t> midi;};
std::deque<Command> commands;
std::string frame, building, logText;
bool inFrame=false;
void *patch=nullptr, *binding=nullptr;
MIDIClientRef midiClient=0;
MIDIPortRef inputPort=0,outputPort=0;
MIDIEndpointRef selectedInput=0;
std::atomic<MIDIEndpointRef> selectedOutput{0};
std::vector<uint8_t> midiOut;
int midiExpected=0;
uint8_t midiInStatus=0;
std::vector<uint8_t> midiInData;
bool inSysEx=false;

std::string quote(const char *s) {
  std::ostringstream o; o << '"';
  for (const unsigned char c:std::string(s)) {
    if(c=='"'||c=='\\') o << '\\' << c;
    else if(c<32) o << "\\u" << std::hex << std::setw(4) << std::setfill('0') << int(c) << std::dec;
    else o << c;
  }
  o << '"'; return o.str();
}
void print(const char *s) {
  std::lock_guard<std::mutex> guard(logMutex);
  logText += s;
  if(logText.size()>65536) logText.erase(0,logText.size()-65536);
}
void message(const char *source,const char *selector,int count,t_atom *atoms) {
  if(std::strcmp(source,"ockm-native-draw")) return;
  if(!std::strcmp(selector,"begin")) {building="[";inFrame=true;return;}
  if(!std::strcmp(selector,"end")) {
    if(!inFrame) return;
    building += "]";
    {std::lock_guard<std::mutex> guard(frameMutex);frame=std::move(building);}
    inFrame=false;return;
  }
  if(!inFrame) return;
  if(building.size()>1) building += ',';
  building += "["+quote(selector);
  for(int i=0;i<count;++i) {
    building += ',';
    if(libpd_is_float(atoms+i)) {
      float v=libpd_get_float(atoms+i);
      building += std::isfinite(v)?std::to_string(v):"0";
    } else building += quote(libpd_get_symbol(atoms+i));
  }
  building += ']';
}
void sendMIDI(const std::vector<uint8_t>& bytes) {
  auto destination=selectedOutput.load();
  if(!destination||!outputPort||bytes.empty()||bytes.size()>256) return;
  MIDIPacketList packets;
  auto p=MIDIPacketListInit(&packets);
  MIDIPacketListAdd(&packets,sizeof(packets),p,0,bytes.size(),bytes.data());
  MIDISend(outputPort,destination,&packets);
}
void midiByte(int,int value) {
  uint8_t v=uint8_t(value);
  if(v>=0xf8) {sendMIDI({v});return;}
  if(v&0x80) {
    midiOut={v}; midiExpected=(v<0xf0)?(((v&0xf0)==0xc0||(v&0xf0)==0xd0)?2:3):0;
  } else if(midiExpected) midiOut.push_back(v);
  if(midiExpected&&int(midiOut.size())==midiExpected) {sendMIDI(midiOut);midiOut.resize(1);}
}
void midiRead(const MIDIPacketList *packets,void *,void *) {
  const MIDIPacket *p=&packets->packet[0];
  Command c;c.midi.reserve(256);
  for(uint32_t i=0;i<packets->numPackets;++i) {c.midi.insert(c.midi.end(),p->data,p->data+p->length);p=MIDIPacketNext(p);}
  std::lock_guard<std::mutex> guard(commandMutex);
  if(commands.size()<4096) commands.push_back(std::move(c));
}
void receiveByte(uint8_t b) {
  libpd_midibyte(0,b);
  if(b>=0xf8) {libpd_sysrealtime(0,b);return;}
  if(b==0xf0) {inSysEx=true;midiInStatus=0;midiInData.clear();libpd_sysex(0,b);return;}
  if(inSysEx) {libpd_sysex(0,b);if(b==0xf7)inSysEx=false;return;}
  if(b&0x80) {midiInStatus=b<0xf0?b:0;midiInData.clear();return;}
  if(!midiInStatus)return;
  midiInData.push_back(b);
  const int type=midiInStatus&0xf0,ch=midiInStatus&15;
  const size_t expected=type==0xc0||type==0xd0?1:2;
  if(midiInData.size()!=expected)return;
  int a=midiInData[0],v=expected==2?midiInData[1]:0;
  switch(type) {
    case 0x80:libpd_noteon(ch,a,0);break;
    case 0x90:libpd_noteon(ch,a,v);break;
    case 0xa0:libpd_polyaftertouch(ch,a,v);break;
    case 0xb0:libpd_controlchange(ch,a,v);break;
    case 0xc0:libpd_programchange(ch,a);break;
    case 0xd0:libpd_aftertouch(ch,a);break;
    case 0xe0:libpd_pitchbend(ch,(v*128+a)-8192);break;
  }
  midiInData.clear();
}
void dispatch(const Command& c) {
  if(c.selector=="__midi-output") {
    for(int ch=0;ch<16;++ch)sendMIDI({uint8_t(0xb0+ch),123,0});
    selectedOutput=c.a>=0?MIDIGetDestination(int(c.a)):0;
    midiOut.clear();midiExpected=0;midiInStatus=0;midiInData.clear();inSysEx=false;
    return;
  }
  if(!c.midi.empty()) {for(auto b:c.midi) receiveByte(b);return;}
  if(c.selector=="float") {libpd_float(c.receiver.c_str(),c.a);return;}
  libpd_start_message(c.count);
  if(!c.symbol.empty()) libpd_add_symbol(c.symbol.c_str());
  else {if(c.count>0) libpd_add_float(c.a);if(c.count>1) libpd_add_float(c.b);}
  libpd_finish_message(c.receiver.c_str(),c.selector.c_str());
}
void loop(int rate) {
  float block[64*9]{};
  uint64_t nextFrame=0;
  while(running.load()) {
    std::deque<Command> pending;
    {std::lock_guard<std::mutex> guard(commandMutex);pending.swap(commands);}
    for(auto& c:pending) dispatch(c);
    auto w=written.load(std::memory_order_relaxed);
    if(w-readAt.load(std::memory_order_acquire)<target) {
      libpd_process_float(1,nullptr,block);
      for(int i=0;i<64;++i) {
        auto index=((w+i)%capacity)*2;
        ring[index]=block[i*9];ring[index+1]=block[i*9+1];
      }
      written.store(w+64,std::memory_order_release);
      if(w>=nextFrame) {dispatch({"ockm-native","frame"});nextFrame=w+rate/25;}
    } else std::this_thread::sleep_for(std::chrono::microseconds(500));
  }
  std::deque<Command> pending;
  {std::lock_guard<std::mutex> guard(commandMutex);pending.swap(commands);}
  for(auto& c:pending) dispatch(c);
  // Save only the recovery stash, preserving the distinction between saved and unsaved work.
  dispatch({"ockm-native","keep"});
  for(int ch=0;ch<16;++ch)sendMIDI({uint8_t(0xb0+ch),123,0});
}
}
extern "C" int ockm_open(const char *path,int rate) {
  if(running||patch||rate<8000) return -1;
  libpd_init();libpd_set_printhook(print);libpd_set_messagehook(message);libpd_set_midibytehook(midiByte);
  std::string base(path);
  for(auto folder:{"","/voices","/seq","/lab","/ui","/pdlua"}) libpd_add_to_search_path((base+folder).c_str());
  class_set_extern_dir(gensym((base+"/pdlua").c_str()));
  pdlua_setup();class_set_extern_dir(gensym(""));
  binding=libpd_bind("ockm-native-draw");
  if(libpd_init_audio(0,9,rate)) return -2;
  patch=libpd_openfile("OCKM_GENERATOR.pd",path);
  if(!patch) {libpd_unbind(binding);binding=nullptr;return -3;}
  libpd_start_message(1);libpd_add_float(1);libpd_finish_message("pd","dsp");
  MIDIClientCreate(CFSTR("OCKM GENERATOR"),nullptr,nullptr,&midiClient);
  if(midiClient) {MIDIInputPortCreate(midiClient,CFSTR("OCKM Input"),midiRead,nullptr,&inputPort);MIDIOutputPortCreate(midiClient,CFSTR("OCKM Output"),&outputPort);}
  written=0;readAt=0;underruns=0;running=true;worker=std::thread(loop,rate);
  return 0;
}
extern "C" void ockm_close() {
  if(running.exchange(false)&&worker.joinable()) worker.join();
  if(midiClient) {MIDIClientDispose(midiClient);midiClient=0;inputPort=0;outputPort=0;selectedInput=0;selectedOutput=0;}
  if(patch) {libpd_closefile(patch);patch=nullptr;}
  if(binding) {libpd_unbind(binding);binding=nullptr;}
}
extern "C" void ockm_command(const char *sel,const char *sym,float a,float b,int count) {
  std::lock_guard<std::mutex> guard(commandMutex);
  // Motion is expendable, but releases and transport commands must not be lost.
  if(commands.size()>4096&&!std::strcmp(sel,"move")) return;
  commands.push_back({"ockm-native",sel,sym?sym:"",a,b,count});
}
extern "C" void ockm_float(const char *receiver,float value) {
  std::lock_guard<std::mutex> guard(commandMutex);commands.push_back({receiver,"float","",value});
}
extern "C" void ockm_render(float *left,float *right,uint32_t frames) {
  auto r=readAt.load(std::memory_order_relaxed),w=written.load(std::memory_order_acquire);
  uint32_t available=uint32_t(std::min<uint64_t>(frames,w-r));
  for(uint32_t i=0;i<available;++i) {auto index=((r+i)%capacity)*2;left[i]=ring[index];right[i]=ring[index+1];}
  for(uint32_t i=available;i<frames;++i) left[i]=right[i]=0;
  readAt.store(r+available,std::memory_order_release);
  if(available<frames) underruns.fetch_add(1,std::memory_order_relaxed);
}
extern "C" char *ockm_copy_frame() {std::lock_guard<std::mutex> g(frameMutex);if(frame.empty())return nullptr;auto p=strdup(frame.c_str());frame.clear();return p;}
extern "C" char *ockm_copy_log() {std::lock_guard<std::mutex> g(logMutex);return strdup(logText.c_str());}
extern "C" void ockm_free(void *p) {free(p);}
extern "C" uint64_t ockm_underruns() {return underruns.load();}
extern "C" int ockm_midi_input_count(){return int(MIDIGetNumberOfSources());}
extern "C" int ockm_midi_output_count(){return int(MIDIGetNumberOfDestinations());}
extern "C" char *ockm_midi_name(int output,int index) {
  auto endpoint=output?MIDIGetDestination(index):MIDIGetSource(index);CFStringRef value=nullptr;
  if(!endpoint||MIDIObjectGetStringProperty(endpoint,kMIDIPropertyDisplayName,&value))return strdup("Unavailable");
  char text[1024]{};CFStringGetCString(value,text,sizeof(text),kCFStringEncodingUTF8);CFRelease(value);return strdup(text);
}
extern "C" void ockm_midi_select(int input,int output) {
  if(selectedInput&&inputPort)MIDIPortDisconnectSource(inputPort,selectedInput);
  selectedInput=input>=0?MIDIGetSource(input):0;
  {std::lock_guard<std::mutex> guard(commandMutex);commands.push_back({"","__midi-output","",float(output)});}
  if(selectedInput&&inputPort)MIDIPortConnectSource(inputPort,selectedInput,nullptr);
}
