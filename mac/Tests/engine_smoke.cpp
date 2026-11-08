#include "EngineBridge.h"
#include <chrono>
#include <thread>
#include <cmath>
#include <cstdio>
#include <string>
#include <fstream>
#include <filesystem>

int main(int argc,char **argv) {
  if(argc<2) return 2;
  bool resume=argc>2;
  if(ockm_open(argv[1],48000)) return 3;
  float l[256],r[256];double energy=0;int samples=0;
  auto pump=[&](int blocks,bool measure=false) {
    for(int i=0;i<blocks;++i) {
      std::this_thread::sleep_for(std::chrono::microseconds(5400));
      ockm_render(l,r,256);
      for(int j=0;j<256;++j) {if(!std::isfinite(l[j])||!std::isfinite(r[j]))std::exit(4);if(measure){energy+=l[j]*l[j]+r[j]*r[j];samples+=2;}}
    }
  };
  pump(100);
  if(!resume) {ockm_command("style",nullptr,1,1,2);pump(30);}
  ockm_command("play",nullptr,0,0,0);pump(500,true);
  char *frame=ockm_copy_frame();
  if(!frame||std::string(frame).find("text")==std::string::npos) {std::puts("No native frame");return 5;}
  std::ofstream(std::string(argv[1])+(resume?"/frame-resume.json":"/frame.json"))<<frame;ockm_free(frame);
  ockm_command("play",nullptr,0,0,0);pump(30);
  if(!resume) {
    const char *screens[]={"compose","live","drums","bass","lead","chord","vox","fx","mixer","arrange","project","setup"};
    for(auto screen:screens) {
      ockm_command("screen",screen,0,0,1);pump(20);
      auto drawing=ockm_copy_frame();if(!drawing)return 7;
      std::ofstream(std::string(argv[1])+"/frame-"+screen+".json")<<drawing;ockm_free(drawing);
    }
    ockm_command("key-down","d",0,0,1);pump(20);
    auto down=ockm_copy_frame();if(!down||std::string(down).find("ockm-drop")==std::string::npos)return 8;ockm_free(down);
    ockm_command("key-up","d",0,0,1);pump(20);
    auto up=ockm_copy_frame();if(!up||std::string(up).find("ockm-drop")!=std::string::npos)return 9;ockm_free(up);
    ockm_command("save",nullptr,0,0,0);pump(100);
  }
  auto projects=std::filesystem::path(argv[1])/"projects";
  int scenes=0;for(auto& f:std::filesystem::directory_iterator(projects))if(f.is_directory()&&f.path().filename()!="default")++scenes;
  ockm_close();
  char *logs=ockm_copy_log();std::puts(logs);ockm_free(logs);
  printf("RMS %.6f, scenes %d, underruns %llu\n",std::sqrt(energy/samples),scenes,(unsigned long long)ockm_underruns());
  return energy>0.001&&scenes>0?0:6;
}
