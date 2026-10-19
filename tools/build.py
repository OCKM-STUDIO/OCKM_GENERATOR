#!/usr/bin/env python3
"""OCKM_GENERATOR build script.

Writes the Pure Data files for the whole project. Structural changes (new objects,
new wiring, new voices) are made here, then the patch files are rebuilt.
Sound tweaks are made with the controls in the patch, not here.

Usage:
  python3 tools/build.py                 rebuild every .pd file in the project
  python3 tools/build.py --out DIR       write to another folder (used by the tests)
  python3 tools/build.py --theme light    build the screens in the light theme (default dark)
  python3 tools/build.py --ui-scale 2     size the screen for the 10" Pi display (1920x1200)
  python3 tools/build.py --reset-patterns  rewrite projects/default as a blank project: all 8 patterns empty
                                          (this DELETES any patterns and settings you have saved)
  python3 tools/build.py --reset-patterns --demo   the same, but with the old demo grooves in patterns 1 to 4

It only creates project files that are missing, and never touches sketches/, README or CHANGELOG.
"""
import os, math, sys, argparse
ap=argparse.ArgumentParser()
ap.add_argument("--out",default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument("--reset-patterns",action="store_true")
ap.add_argument("--demo",action="store_true",help="with --reset-patterns: fill patterns 1-4 with the demo grooves instead of starting blank")
ap.add_argument("--theme",choices=["dark","light"],default="dark",help="screen colours (default dark)")
ap.add_argument("--ui-scale",type=int,choices=[1,2],default=1,help="1 = 960x600 for the Mac, 2 = 1920x1200 for the 10-inch Pi screen")
args=ap.parse_args()
R=args.out
for d in ("voices","seq"): os.makedirs(os.path.join(R,d),exist_ok=True)
STEPS=256   # longest part: 16 bars
SLOTN=1     # one loop per project (the store still speaks in slots, so this stays a number)
LOOP_FILE="loop.txt"
D="\\$"   # Pd dollar as written in a file
class P:
    def __init__(s): s.L=[]; s.C=[]; s.n=0
    def add(s,line):
        s.L.append(line); s.n+=1; return s.n-1
    def raw(s,line): s.L.append(line)
    def con(s,a,b,c,d): s.C.append((a,b,c,d))
    def text(s,header,tail=()):
        return header+"\n"+"\n".join(s.L)+"\n"+"".join(f"#X connect {a} {b} {c} {d};\n" for a,b,c,d in s.C)+"".join(t+"\n" for t in tail)
    def save(s,fn,header,tail=()):
        open(os.path.join(R,fn),"w").write(s.text(header,tail))

def hooks(p,x,y):
    t=p.add(f"#X obj {x} {y} r ockm-{D}1-tune;")
    d=p.add(f"#X obj {x+170} {y} r ockm-{D}1-decay;")
    l=p.add(f"#X obj {x+350} {y} r ockm-{D}1-level;")
    return t,d,l

def env(p,x,y,amp_src,base,dec_ms,msg="{D}1 \\, 0 {D}2"):
    """level-scaled velocity -> [* base] -> [pack f dec] -> msg -> vline~ ; returns (pack, vline)"""
    b=p.add(f"#X obj {x} {y} * {base};")
    pk=p.add(f"#X obj {x} {y+30} pack f {dec_ms};")
    m=p.add(f"#X msg {x} {y+60} "+msg.replace("{D}",D)+";")
    v=p.add(f"#X obj {x} {y+90} vline~;")
    p.con(amp_src,0,b,0); p.con(b,0,pk,0); p.con(pk,0,m,0); p.con(m,0,v,0)
    return pk,v

def header_text(p,txt): p.add(f"#X text 20 10 {txt};")

# (the drum slots' synth sounds are the drum lab's voices: see tools/build_lab.py and the drum slot section below)

# ---------------- samples ----------------
# One folder per drum sound. Perc 1 and perc 2 share the perc folder. Files are numbered in name order (01, 02...).
SAMPLE_DIRS=["kick","snare","clap","perc","hat","open-hat","tom"]
SOUND_DIR=["kick","snare","clap","perc","hat","open-hat","tom","perc"]   # by sound number
AUDIO_EXT=["wav","WAV","aif","aiff","AIF","AIFF","Wav","Aif"]

def audio_glob(p,x,y):
    """[file glob] that only passes audio files. Returns (in, out): in takes a glob pattern, out gives each path (sorted)."""
    g=p.add(f"#X obj {x} {y} file glob;"); u=p.add(f"#X obj {x} {y+25} unpack s f;"); t=p.add(f"#X obj {x} {y+50} t s s;")
    hp=p.add(f"#X obj {x+150} {y+175} symbol;")
    se=p.add(f"#X obj {x} {y+75} file splitext;"); ls=p.add(f"#X obj {x} {y+100} list split 1;"); lt=p.add(f"#X obj {x+60} {y+125} list trim;")
    ro=p.add(f"#X obj {x+60} {y+150} route "+" ".join(AUDIO_EXT)+";"); tb=p.add(f"#X obj {x+60} {y+175} t b;")
    for c in [(g,0,u,0),(u,0,t,0),(t,1,hp,1),(t,0,se,0),(se,0,ls,0),(ls,1,lt,0),(lt,0,ro,0),(tb,0,hp,0)]: p.con(*c)
    for k in range(len(AUDIO_EXT)): p.con(ro,k,tb,0)
    return g,hp

def samples_base(p,x,y,trig,outlet):
    """trig's bang -> this abstraction's folder/../samples, as a symbol out of the returned object"""
    m=p.add(f"#X msg {x} {y} dir;"); pc=p.add(f"#X obj {x} {y+25} pdcontrol;")
    la=p.add(f"#X obj {x} {y+50} list append ../samples;"); fj=p.add(f"#X obj {x} {y+75} file join;")
    p.con(trig,outlet,m,0); p.con(m,0,pc,0); p.con(pc,0,la,0); p.con(la,0,fj,0)
    return fj

# sample player for one drum slot: ockm-<slot>-sample 0 = the synth sound, n = the nth file in that sound's folder
p=P(); header_text(p,"Sample player for one drum slot. ockm-<slot>-sample n loads the nth file from samples/<sound folder>. Tune = playback speed \\, decay cuts the tail \\, level scales.")
inl=p.add("#X obj 30 50 inlet;")
lb=p.add("#X obj 600 50 loadbang;"); tlb=p.add("#X obj 600 75 t b b;"); p.con(lb,0,tlb,0)
base=samples_base(p,700,100,tlb,1)
lp=p.add("#X obj 600 300 list prepend;"); bl=p.add("#X obj 700 200 list;"); p.con(base,0,bl,0); p.con(bl,0,lp,1)
rs=p.add(f"#X obj 600 150 r ockm-{D}1-sound;"); fs=p.add("#X obj 600 200 f;"); ts=p.add("#X obj 600 175 t b f;")
rn=p.add(f"#X obj 800 150 r ockm-{D}1-sample;"); tn=p.add("#X obj 800 175 t b f f;"); fn=p.add("#X obj 900 230 f;")
dl=p.add("#X obj 900 200 delay 2;"); tl=p.add("#X obj 900 225 t b b;"); z0=p.add("#X msg 1000 250 0;")
mo=p.add("#X obj 900 255 moses 1;"); tsf=p.add("#X obj 960 280 t b;")
sel=p.add("#X obj 600 230 sel "+" ".join(str(i) for i in range(8))+";")
for c in [(rs,0,ts,0),(ts,1,fs,1),(ts,0,dl,0),(rn,0,tn,0),(tn,2,fn,1),(tn,0,dl,0),(tlb,0,dl,0),(dl,0,tl,0),(tl,1,z0,0),(tl,0,fn,0),(fn,0,mo,0),(mo,1,tsf,0),(tsf,0,fs,0),(fs,0,sel,0)]: p.con(*c)
la=p.add("#X obj 600 330 file join;")
for i,d in enumerate(SOUND_DIR):
    m=p.add(f"#X msg {600+i*60} 265 list {d} *;"); p.con(sel,i,m,0); p.con(m,0,lp,0)
p.con(lp,0,la,0)
tp=p.add("#X obj 600 355 t s b;"); cnt=p.add("#X obj 700 500 f;"); inc=p.add("#X obj 750 500 + 1;"); tc=p.add("#X obj 700 525 t f f;")
z1=p.add("#X msg 760 380 0;"); eq=p.add("#X obj 700 550 ==;"); s1=p.add("#X obj 700 575 sel 1;")
gi,go=audio_glob(p,600,380)
tbs=p.add("#X obj 600 600 t b s;"); hp2=p.add("#X obj 600 650 symbol;")
for c in [(la,0,tp,0),(tp,1,z1,0),(z1,0,cnt,1),(tp,0,gi,0),(go,0,tbs,0),(tbs,1,hp2,1),(tbs,0,cnt,0),(cnt,0,inc,0),(inc,0,tc,0),(tc,1,cnt,1),(tc,0,eq,0),(tn,1,eq,1),(s1,0,hp2,0),(eq,0,s1,0)]: p.con(*c)
lat=p.add(f"#X obj 600 680 list append {D}0-smp;"); lpr=p.add("#X obj 600 705 list prepend read -resize;"); ltr=p.add("#X obj 600 730 list trim;")
sf=p.add("#X obj 600 755 soundfiler;"); ui_=p.add("#X obj 700 780 unpack f;"); p.add(f"#X obj 900 700 table {D}0-smp;")
for c in [(hp2,0,lat,0),(lat,0,lpr,0),(lpr,0,ltr,0),(ltr,0,sf,0)]: p.con(*c)
# hit: vel -> (length ms at this speed, amplitude, when to fade, sample count)
ex=p.add(f"#X obj 30 120 expr {D}f2*(1-0.4*{D}f7)/max({D}f3\\,1)*1000/pow(2\\,{D}f4/12) \\; {D}f1*{D}f6*1.4 \\; {D}f2*(1-0.4*{D}f7)/max({D}f3\\,1)*1000/pow(2\\,{D}f4/12)*min({D}f5\\,100)/100 \\; {D}f2 \\; 1+{D}f2*0.4*{D}f7;")
init=p.add("#X msg 200 75 44100;"); p.con(tlb,1,init,0); p.con(init,0,ex,2)
il=p.add("#X msg 260 75 1;"); p.con(tlb,1,il,0); p.con(il,0,ex,5)
idc=p.add("#X msg 300 75 100;"); p.con(tlb,1,idc,0); p.con(idc,0,ex,4)
p.con(z0,0,ex,1); p.con(sf,0,ex,1); p.con(sf,1,ui_,0); p.con(ui_,0,ex,2)
t_,d_,l_=hooks(p,200,20); p.con(t_,0,ex,3); p.con(d_,0,ex,4); p.con(l_,0,ex,5)
p.con(inl,0,ex,0)
pk=p.add("#X obj 30 160 pack f f f f f;")
for k in range(5): p.con(ex,k,pk,k)
rstt=p.add(f"#X obj 400 20 r ockm-{D}1-start;"); p.con(rstt,0,ex,6)
tll=p.add("#X obj 30 185 t l l;"); mph=p.add(f"#X msg 150 210 {D}5 \\, {D}4 {D}1;"); mam=p.add(f"#X msg 30 210 {D}2 \\, 0 4 {D}3;")
vph=p.add("#X obj 150 240 vline~;"); trd=p.add(f"#X obj 150 270 tabread4~ {D}0-smp;"); vam=p.add("#X obj 30 240 vline~;")
mul=p.add("#X obj 30 300 *~;"); out=p.add("#X obj 30 340 outlet~;")
for c in [(pk,0,tll,0),(tll,1,mph,0),(tll,0,mam,0),(mph,0,vph,0),(vph,0,trd,0),(mam,0,vam,0),(trd,0,mul,0),(vam,0,mul,1),(mul,0,out,0)]: p.con(*c)
p.save("voices/ockm-sampler.pd","#N canvas 150 150 1300 820 12;")

# the sample library: counts the files in each folder for the screen (ockm-sample-counts, in SAMPLE_DIRS order)
p=P(); header_text(p,"Sample library: counts the audio files in each samples folder. ockm-samples-scan to count again. Answers ockm-sample-counts "+" ".join(SAMPLE_DIRS)+".")
lb=p.add("#X obj 30 50 loadbang;"); tlb=p.add("#X obj 30 75 t b b;"); rsc=p.add("#X obj 130 50 r ockm-samples-scan;"); p.con(lb,0,tlb,0)
base=samples_base(p,400,50,tlb,1)
nd=len(SAMPLE_DIRS)
tall=p.add("#X obj 30 150 t "+" ".join(["b"]*nd)+";"); p.con(tlb,0,tall,0); p.con(rsc,0,tall,0)
pkc=p.add("#X obj 30 800 pack "+" ".join(["0"]*nd)+";"); p.con(pkc,0,p.add("#X obj 30 830 s ockm-sample-counts;"),0)
for i,d in enumerate(SAMPLE_DIRS):
    x=30+i*260
    hb=p.add(f"#X obj {x} 200 symbol;"); p.con(base,0,hb,1); p.con(tall,i,hb,0)   # outlet 0 fires last, so kick (the hot inlet) goes last
    la=p.add(f"#X obj {x} 225 list append {d} *;"); fj=p.add(f"#X obj {x} 250 file join;"); t3=p.add(f"#X obj {x} 275 t b s b;")
    z=p.add(f"#X msg {x+150} 300 0;"); gi,go=audio_glob(p,x,320)
    tb=p.add(f"#X obj {x} 560 t b;"); cnt=p.add(f"#X obj {x} 585 f;"); inc=p.add(f"#X obj {x+50} 585 + 1;"); rd=p.add(f"#X obj {x} 700 f;")
    for c in [(hb,0,la,0),(la,0,fj,0),(fj,0,t3,0),(t3,2,z,0),(z,0,cnt,1),(z,0,rd,1),(t3,1,gi,0),(tb,0,cnt,0),(cnt,0,inc,0),(inc,0,cnt,1),(inc,0,rd,1),(t3,0,rd,0),(rd,0,pkc,i)]: p.con(*c)
    # each file's name too (v0.77): ockm-sample-name <folder 0-6> <sample number> <file name without extension>. Kits are found by name
    tn=p.add(f"#X obj {x} 610 t b s;"); spn=p.add(f"#X obj {x+60} 635 file splitname;"); ls1=p.add(f"#X obj {x+60} 660 list split 1;")
    spe=p.add(f"#X obj {x+60} 685 file splitext;"); ls2=p.add(f"#X obj {x+60} 710 list split 1;")
    pkn=p.add(f"#X obj {x+120} 610 list append;"); lpn=p.add(f"#X obj {x+120} 760 list prepend {i};"); ltn=p.add(f"#X obj {x+120} 785 list trim;")
    snm=p.add(f"#X obj {x+120} 810 s ockm-sample-name;")
    for c in [(go,0,tn,0),(tn,1,spn,0),(spn,0,ls1,0),(ls1,1,spe,0),(spe,0,ls2,0),(ls2,0,pkn,1),(tn,0,tb,0),(inc,0,pkn,0),(pkn,0,lpn,0),(lpn,0,ltn,0),(ltn,0,snm,0)]: p.con(*c)
p.save("seq/ockm-samplelib.pd","#N canvas 150 150 1900 880 12;")

# ---------------- transition sounds: a riser and an impact ----------------
p=P(); header_text(p,"Transition sounds. ockm-riser-go <ms>: white noise sweeping up and getting louder over that time. ockm-impact-go: a crash and a sub boom. ockm-riser-stop cuts the riser (on the drop).")
out=p.add("#X obj 30 560 outlet~;")
# riser: noise through a band-pass that sweeps up, fading in, then cut dead
rr=p.add("#X obj 30 40 r ockm-riser-go;"); tr_=p.add("#X obj 30 65 t f f;")
mf=p.add(f"#X msg 30 95 300 \\, 9000 {D}1;"); mg=p.add(f"#X msg 150 95 0 \\, 0.32 {D}1 \\, 0 5 {D}1;")
fv=p.add("#X obj 30 125 vline~;"); gv=p.add("#X obj 150 125 vline~;")
nz=p.add("#X obj 300 125 noise~;"); bp=p.add("#X obj 300 160 vcf~ 4;"); rg=p.add("#X obj 300 195 *~;")
rs=p.add("#X obj 450 40 r ockm-riser-stop;"); ms_=p.add("#X msg 450 65 0 5;")
for c in [(rr,0,tr_,0),(tr_,1,mf,0),(tr_,0,mg,0),(mf,0,fv,0),(mg,0,gv,0),(nz,0,bp,0),(fv,0,bp,1),(bp,0,rg,0),(gv,0,rg,1),(rg,0,out,0),(rs,0,ms_,0),(ms_,0,gv,0)]: p.con(*c)
# impact: a crash (bright noise, long fade) plus a sub boom (a sine falling from 90 to 38 Hz)
ri=p.add("#X obj 30 260 r ockm-impact-go;"); ti=p.add("#X obj 30 285 t b b b;")
cm=p.add("#X msg 30 315 0.45 \\, 0 1800 2;"); cv=p.add("#X obj 30 345 vline~;"); cn=p.add("#X obj 150 315 noise~;"); ch=p.add("#X obj 150 345 hip~ 4000;")
ch2=p.add("#X obj 150 370 hip~ 2500;"); cg=p.add("#X obj 150 400 *~;")
pm=p.add("#X msg 300 315 90 \\, 38 350;"); pv=p.add("#X obj 300 345 vline~;"); po=p.add("#X obj 300 370 osc~;")
am=p.add("#X msg 420 315 0.7 \\, 0 900 5;"); av=p.add("#X obj 420 345 vline~;"); pg=p.add("#X obj 300 400 *~;")
for c in [(ri,0,ti,0),(ti,2,cm,0),(cm,0,cv,0),(cn,0,ch,0),(ch,0,ch2,0),(ch2,0,cg,0),(cv,0,cg,1),(cg,0,out,0),
          (ti,1,pm,0),(pm,0,pv,0),(pv,0,po,0),(ti,0,am,0),(am,0,av,0),(po,0,pg,0),(av,0,pg,1),(pg,0,out,0),(ri,0,p.add("#X msg 520 285 \; ockm-riser-stop bang;"),0)]: p.con(*c)
p.save("voices/ockm-transfx.pd","#N canvas 120 120 700 600 12;")

# ---------------- drum bus (v0.89): parallel compression and saturation on the eight drums together ----------------
# ockm-drum-punch 0 to 1. A squashed copy of the drums (threshold 0.3, ratio 4, a 2 ms attack so each hit's front edge gets
# through, 100 ms release) is blended under the dry drums, then the lot goes through a soft saturator. 0 leaves them alone.
# Tuned on the 909 kit: at 1 the drums are about 6 dB fuller with the peaks kept (crest 18 dB down to 13.5)
p=P(); header_text(p,"Drum bus: parallel compression plus saturation. ockm-drum-punch 0 (off) to 1.")
inl=p.add("#X obj 30 40 inlet~;"); out=p.add("#X obj 30 400 outlet~;")
env=p.add("#X obj 200 100 fexpr~ if(abs($x1)>$y1 \\, $y1+0.0104*(abs($x1)-$y1) \\, $y1*0.99979);".replace("$","\\$"))
cmp_=p.add("#X obj 200 150 expr~ $v1*min(1 \\, pow(0.3/max($v2 \\, 0.0001) \\, 0.75))*2.5;".replace("$","\\$"))   # threshold 0.3, ratio 4, 2.5x makeup
mixx=p.add("#X obj 30 250 expr~ (1-$f3)*$v1 + $f3*tanh(0.45*($v1 + 0.7*$f3*$v2))/0.45;".replace("$","\\$"))   # 0: untouched. The squashed copy adds body between the hits; the saturation (matched to the bus level, peaks near 2) only rounds the very top, so the transients keep their edge
rp=p.add("#X obj 400 40 r ockm-drum-punch;"); lp=p.add("#X obj 400 70 line 0 20;")
for c in [(inl,0,env,0),(inl,0,cmp_,0),(env,0,cmp_,1),(inl,0,mixx,0),(cmp_,0,mixx,1),(rp,0,lp,0),(lp,0,mixx,2),(mixx,0,out,0)]: p.con(*c)
p.save("voices/ockm-drumbus.pd","#N canvas 120 120 700 450 12;")

# ---------------- transitions: what happens where song sections meet ----------------
# Per pattern: ockm-end (how its last bar in the song plays: 0 nothing, 1 fill, 2 riser, 3 riser + gap, 4 dub out)
# and ockm-impact (1: a crash and sub boom on its first downbeat). Listens to ockm-song-pos <step> <bars left>: song mode is gone, so this waits for arrangements (step 5) to drive it.
p=P(); header_text(p,"Transitions (song mode). On a section's last bar: its ending (ockm-end: 1 fill \\, 2 riser \\, 3 riser + a one-beat gap \\, 4 dub out). On a new section's first downbeat: an impact if that pattern has ockm-impact 1.")
re_=p.add("#X obj 30 40 r ockm-end;"); ve=p.add("#X obj 30 65 v ockm_end;"); p.con(re_,0,ve,0)
ri=p.add("#X obj 150 40 r ockm-impact;"); vi=p.add("#X obj 150 65 v ockm_impact;"); p.con(ri,0,vi,0)
rp=p.add("#X obj 30 110 r ockm-song-pos;"); up=p.add("#X obj 30 135 unpack f f;"); tl=p.add("#X obj 30 160 t f f;")
# a new section: impact a quarter step later (the engine plays a quarter step behind, and the new pattern has loaded by then)
lst=p.add("#X obj 300 160 f -1;"); neq=p.add("#X obj 300 185 !=;"); tneq=p.add("#X obj 300 135 t f f;")
sl=p.add("#X obj 300 210 sel 1;"); dq=p.add("#X obj 300 235 delay;"); qx=p.add("#X obj 380 210 expr ockm_stepms*0.25;")
ig=p.add("#X obj 300 260 expr ockm_impact;"); si=p.add("#X obj 300 285 sel 1;"); sim=p.add("#X msg 300 310 \; ockm-impact-go bang;")
for c in [(rp,0,up,0),(up,0,tneq,0),(tneq,1,neq,0),(lst,0,neq,1),(tneq,0,lst,1),(neq,0,sl,0),(sl,0,qx,0),(qx,0,dq,0),(sl,0,dq,0),(dq,0,ig,0),(ig,0,si,0),(si,0,sim,0)]: p.con(*c)
# hmm: the delay takes its time first, then the bang: send the time to its right inlet
p.C=[c for c in p.C if c!=(qx,0,dq,0)]; p.con(qx,0,dq,1)
p.C=[c for c in p.C if c!=(sl,0,qx,0) and c!=(sl,0,dq,0)]; tsl=p.add("#X obj 300 222 t b b;"); p.con(sl,0,tsl,0); p.con(tsl,1,qx,0); p.con(tsl,0,dq,0)
# the last bar: left = 0
s0=p.add("#X obj 30 210 sel 0;"); fe0=p.add("#X msg 120 235 0;"); vfe=p.add("#X obj 120 260 v ockm_fill_end;")
ge=p.add("#X obj 30 235 expr ockm_end;"); se=p.add("#X obj 30 260 sel 1 2 3 4;")
fe1=p.add("#X msg 30 290 1;"); vfe1=p.add("#X obj 30 315 v ockm_fill_end;")
# riser over the bar (2 riser) or the first 3 beats (3 riser + gap)
rb=p.add("#X obj 100 290 expr ockm_stepms*16;"); rsb=p.add("#X obj 100 315 s ockm-riser-go;")
rb3=p.add("#X obj 200 290 expr ockm_stepms*12;"); tg3=p.add("#X obj 200 315 t f f;"); rsb3=p.add("#X obj 260 340 s ockm-riser-go;")
dgap=p.add("#X obj 200 365 delay;"); gon=p.add("#X msg 200 390 \; ockm-gap 1;")
gx=p.add("#X obj 300 390 expr ockm_stepms*4-6;"); dgo=p.add("#X obj 200 415 delay;"); goff=p.add("#X msg 200 440 \; ockm-gap 0;")
# dub out: throw the last beat into the delay
d12=p.add("#X obj 450 290 expr ockm_stepms*12;"); dd=p.add("#X obj 450 315 delay;"); thr=p.add("#X msg 450 340 \; ockm-delay-throw 1;")
d4=p.add("#X obj 560 340 expr ockm_stepms*4-6;"); dd2=p.add("#X obj 450 365 delay;"); thr0=p.add("#X msg 450 390 \; ockm-delay-throw 0;")
for c in [(up,1,s0,0),(s0,1,fe0,0),(fe0,0,vfe,0),(s0,0,ge,0),(ge,0,se,0),(se,0,fe1,0),(fe1,0,vfe1,0),(se,1,rb,0),(rb,0,rsb,0),
          (se,2,rb3,0),(rb3,0,tg3,0),(tg3,1,rsb3,0),(tg3,0,dgap,0),(dgap,0,gon,0),(dgap,0,gx,0),(gx,0,dgo,0),(dgo,0,goff,0),
          (se,3,d12,0),(d12,0,dd,0),(dd,0,thr,0),(dd,0,d4,0),(d4,0,dd2,0),(dd2,0,thr0,0)]: p.con(*c)
# a delay given a float starts with that time: [delay] takes 'float' as a new time and starts. Good.
# stop: everything back to normal
rpl=p.add("#X obj 600 40 r ockm-playing;"); sp0=p.add("#X obj 600 65 sel 0;")
rst=p.add("#X msg 600 90 \; ockm-gap 0 \; ockm-delay-throw 0 \; ockm-riser-stop bang;"); fz=p.add("#X msg 760 90 0;"); vfz=p.add("#X obj 760 115 v ockm_fill_end;")
stp=p.add("#X msg 600 120 stop;"); lr=p.add("#X msg 680 120 -1;")
for c in [(rpl,0,sp0,0),(sp0,0,rst,0),(sp0,0,fz,0),(fz,0,vfz,0),(sp0,0,stp,0),(stp,0,dgap,0),(stp,0,dgo,0),(stp,0,dd,0),(stp,0,dd2,0),(stp,0,dq,0),(sp0,0,lr,0),(lr,0,lst,1)]: p.con(*c)
p.save("seq/ockm-transitions.pd","#N canvas 120 120 900 500 12;")

# ---------------- per-track EQ: a low cut and three bands ----------------
# Hooks per track: ockm-<t>-lowcut (Hz, 20 = off), -eqlow (dB at 100 Hz, shelf), -eqmid (dB), -eqmidf (Hz), -eqhigh (dB at 8 kHz, shelf).
# The bands are biquads with RBJ cookbook coefficients, worked out when a knob moves (so nothing heavy runs per sample).
EQ_DEF={"lowcut":20,"eqlow":0,"eqmid":0,"eqmidf":400,"eqhigh":0}
SR="max(ockm_sr\\,22050)"
def eq_band(p,kind,x,db_hook,fdef,f_hook=None):
    """one biquad band; returns the biquad~ object"""
    rdb=p.add(f"#X obj {x} 60 r {db_hook};"); pk=p.add(f"#X obj {x} 110 pack f {fdef};"); p.con(rdb,0,pk,0)
    if f_hook:
        rf=p.add(f"#X obj {x+90} 60 r {f_hook};"); tf=p.add(f"#X obj {x+90} 85 t b f;"); p.con(rf,0,tf,0); p.con(tf,1,pk,1); p.con(tf,0,pk,0)
    ac=p.add(f"#X obj {x} 140 expr pow(10\\,{D}f1/40) \\; cos(6.283185*{D}f2/{SR}) \\; sin(6.283185*{D}f2/{SR});")
    A,c,sn="$f1","$f2","$f3"
    if kind=="low":
        r_=f"2*sqrt({A})*{sn}*0.70711"
        a0=f"(({A}+1)+({A}-1)*{c}+{r_})"
        cf=[f"2*(({A}-1)+({A}+1)*{c})/{a0}", f"-(({A}+1)+({A}-1)*{c}-{r_})/{a0}",
            f"{A}*(({A}+1)-({A}-1)*{c}+{r_})/{a0}", f"2*{A}*(({A}-1)-({A}+1)*{c})/{a0}", f"{A}*(({A}+1)-({A}-1)*{c}-{r_})/{a0}"]
    elif kind=="high":
        r_=f"2*sqrt({A})*{sn}*0.70711"
        a0=f"(({A}+1)-({A}-1)*{c}+{r_})"
        cf=[f"-2*(({A}-1)-({A}+1)*{c})/{a0}", f"-(({A}+1)-({A}-1)*{c}-{r_})/{a0}",
            f"{A}*(({A}+1)+({A}-1)*{c}+{r_})/{a0}", f"-2*{A}*(({A}-1)+({A}+1)*{c})/{a0}", f"{A}*(({A}+1)+({A}-1)*{c}-{r_})/{a0}"]
    else:   # peak, Q about 1
        al=f"({sn}/2)"
        a0=f"(1+{al}/{A})"
        cf=[f"2*{c}/{a0}", f"-(1-{al}/{A})/{a0}", f"(1+{al}*{A})/{a0}", f"-2*{c}/{a0}", f"(1-{al}*{A})/{a0}"]
    ex=" \\; ".join(cf).replace("$",D).replace(",","\\,")
    co=p.add(f"#X obj {x} 170 expr {ex};"); pk5=p.add(f"#X obj {x} 200 pack f f f f f;"); bq=p.add(f"#X obj {x} 230 biquad~;")
    p.con(pk,0,ac,0); p.con(ac,0,co,0); p.con(ac,1,co,1); p.con(ac,2,co,2)
    for k in range(5): p.con(co,k,pk5,k)
    p.con(pk5,0,bq,0)
    return bq,rdb
p=P(); header_text(p,"Track EQ: low cut \\, then low shelf (100 Hz) \\, mid bell (ockm-<t>-eqmidf) and high shelf (8 kHz) \\, each -12 to +12 dB. Flat when all are 0.")
inl=p.add("#X obj 30 300 inlet~;"); out=p.add("#X obj 30 520 outlet~;")
lb=p.add("#X obj 30 20 loadbang;"); tl=p.add("#X obj 30 40 t b b;"); srm=p.add("#X obj 120 40 samplerate~;"); vsr=p.add("#X obj 120 60 v ockm_sr;")
p.con(lb,0,tl,0); p.con(tl,1,srm,0); p.con(srm,0,vsr,0)
rlc=p.add(f"#X obj 30 330 r ockm-{D}1-lowcut;"); h1=p.add("#X obj 30 360 hip~ 20;"); h2=p.add("#X obj 30 385 hip~ 20;")
b1,r1=eq_band(p,"low",250,f"ockm-{D}1-eqlow",100)
b2,r2=eq_band(p,"peak",500,f"ockm-{D}1-eqmid",400,f_hook=f"ockm-{D}1-eqmidf")
b3,r3=eq_band(p,"high",800,f"ockm-{D}1-eqhigh",8000)
for bnd in (b1,b2,b3):
    pass
# once the sample rate is known, work every band out again from the values it already has (flat unless the project set them)
for rr_,x in ((r1,250),(r2,500),(r3,800)):
    tgt=[c for c in p.C if c[0]==rr_][0]
    p.con(tl,0,tgt[2],0)
for c in [(rlc,0,h1,1),(rlc,0,h2,1),(inl,0,h1,0),(h1,0,h2,0),(h2,0,b1,0),(b1,0,b2,0),(b2,0,b3,0),(b3,0,out,0)]: p.con(*c)
# analyser: 8 octave bands (60 Hz to 8 kHz), level in dB (100 = full scale), sent as ockm-spec <track> <band> <dB>.
# It only runs while asked: ockm-spec-<track> 1 (the EQ sheet) or ockm-spec-all 1 (de-mud listening)
sp=P()
si=sp.add("#X obj 20 20 inlet~;"); sw=sp.add("#X obj 600 20 switch~;"); z0=sp.add("#X msg 600 0 0;")
lb2=sp.add("#X obj 600 -20 loadbang;"); sp.con(lb2,0,z0,0); sp.con(z0,0,sw,0)
r1=sp.add(f"#X obj 700 -20 r ockm-spec-{D}1;"); r2=sp.add("#X obj 800 -20 r ockm-spec-all;"); onb=sp.add("#X obj 700 -50 bang;")
for rr in (r1,r2): sp.con(rr,0,sw,0); sp.con(rr,0,onb,0)
ss=sp.add("#X obj 20 300 s ockm-spec;")
for b,fq in enumerate([60,120,250,500,1000,2000,4000,8000]):
    x=20+b*90
    # a true octave-wide band (RBJ band-pass, 0 dB at the centre): Pd's bp~ and vcf~ barely filter up high
    W=f"(6.28319*{fq}/max(ockm_sr\\,22050))"; AL=f"(sin({W})/2.82)"
    cx=sp.add(f"#X obj {x} -80 expr 2*cos({W})/(1+{AL}) \\; -(1-{AL})/(1+{AL}) \\; {AL}/(1+{AL}) \\; -{AL}/(1+{AL});")
    pk=sp.add(f"#X obj {x} -50 pack f f f f;"); cm=sp.add(f"#X msg {x} -20 \\$1 \\$2 \\$3 0 \\$4;")
    for o in range(4): sp.con(cx,o,pk,o)
    sp.con(pk,0,cm,0); sp.con(lb2,0,cx,0); sp.con(onb,0,cx,0)
    bp_=sp.add(f"#X obj {x} 60 biquad~;"); sp.con(cm,0,bp_,0); ev=sp.add(f"#X obj {x} 90 env~ 4096 2048;")
    l1=sp.add(f"#X obj {x} 120 list prepend {b};"); l2=sp.add(f"#X obj {x} 150 list prepend {D}1;"); lt=sp.add(f"#X obj {x} 180 list trim;")
    for c in [(si,0,bp_,0),(bp_,0,ev,0),(ev,0,l1,0),(l1,0,l2,0),(l2,0,lt,0),(lt,0,ss,0)]: sp.con(*c)
p.L.append(sp.text("#N canvas 0 0 900 340 spectrum 0;").rstrip("\n"))
spo=p.add("#X restore 30 470 pd spectrum;"); p.con(b3,0,spo,0)
p.save("voices/ockm-eq.pd","#N canvas 120 120 1000 560 12;")

# ---------------- recorder: the mix and stems to WAV files ----------------
STEMS=["drums","bass","lead","chord","fx"]
p=P(); header_text(p,"Recorder. ockm-rec-<name>-open <path> then ockm-rec-<name>-start for mix (stereo) and the stems "+" ".join(STEMS)+" (mono). ockm-rec-stop stops them all. 24-bit WAV. Also: ockm-exports-dir on load \\, ockm-usb-scan finds USB sticks \\, ockm-mkdir <path>.")
rstop=p.add("#X obj 30 40 r ockm-rec-stop;")
mr=p.add("#X obj 30 80 r~ ockm-master;")
for i,nm in enumerate(["mix"]+STEMS):
    x=30+i*170
    ro=p.add(f"#X obj {x} 120 r ockm-rec-{nm}-open;"); lp=p.add(f"#X obj {x} 145 list prepend open -bytes 3;"); lt=p.add(f"#X obj {x} 170 list trim;")
    rs=p.add(f"#X obj {x+80} 120 r ockm-rec-{nm}-start;"); ms=p.add(f"#X msg {x+80} 145 start;"); mstp=p.add(f"#X msg {x+40} 195 stop;")
    w=p.add(f"#X obj {x} 260 writesf~ {2 if nm=='mix' else 1};")
    for c in [(ro,0,lp,0),(lp,0,lt,0),(lt,0,w,0),(rs,0,ms,0),(ms,0,w,0),(rstop,0,mstp,0),(mstp,0,w,0)]: p.con(*c)
    if nm=="mix": p.con(mr,0,w,0); p.con(mr,0,w,1)
    else: p.con(p.add(f"#X obj {x} 230 catch~ ockm-stem-{nm};"),0,w,0)
# exports folder: OCKM_GENERATOR/exports, made on load and announced
lb=p.add("#X obj 30 330 loadbang;"); md=p.add("#X msg 30 355 dir;"); pc=p.add("#X obj 30 380 pdcontrol;")
la=p.add("#X obj 30 405 list append ../exports;"); fj=p.add("#X obj 30 430 file join;"); te=p.add("#X obj 30 455 t s s;")
mk=p.add("#X obj 130 480 file mkdir;"); sd=p.add("#X obj 30 505 s ockm-exports-dir;")
rex=p.add("#X obj 200 330 r ockm-exports-ask;"); hold=p.add("#X obj 30 480 symbol;")
for c in [(lb,0,md,0),(md,0,pc,0),(pc,0,la,0),(la,0,fj,0),(fj,0,te,0),(te,1,mk,0),(te,0,hold,0),(hold,0,sd,0),(rex,0,hold,0)]: p.con(*c)
rmk=p.add("#X obj 400 330 r ockm-mkdir;"); mk2=p.add("#X obj 400 355 file mkdir;"); p.con(rmk,0,mk2,0)
# USB sticks: anything mounted under /Volumes (Mac) or /media/<user> (Pi), except the Mac's own disks
rus=p.add("#X obj 600 330 r ockm-usb-scan;"); tus=p.add("#X obj 600 355 t b b b b;")
st=p.add("#X msg 760 380 \\; ockm-usb-list-start bang;"); en=p.add("#X msg 600 600 \\; ockm-usb-list-end bang;")
g1=p.add("#X msg 680 380 symbol /Volumes/*;"); g2=p.add("#X msg 700 405 symbol /media/*/*;"); fg=p.add("#X obj 680 430 file glob;")
ug=p.add("#X obj 680 455 unpack s f;"); sp=p.add("#X obj 680 480 spigot;"); sk=p.add("#X obj 680 505 route symbol;")
skip=p.add("#X obj 680 530 select /Volumes/Macintosh\\ HD /Volumes/Recovery /Volumes/Data /Volumes/Preboot /Volumes/VM /Volumes/Update;")
si=p.add("#X obj 680 575 s ockm-usb-item;"); sy=p.add("#X obj 680 555 symbol;")
for c in [(rus,0,tus,0),(tus,3,st,0),(tus,2,g1,0),(tus,1,g2,0),(tus,0,en,0),(g1,0,fg,0),(g2,0,fg,0),(fg,0,ug,0),(ug,1,sp,1),(ug,0,sp,0),
          (sp,0,skip,0),(skip,6,sy,0),(sy,0,si,0)]: p.con(*c)
p.save("seq/ockm-recorder.pd","#N canvas 120 120 1300 640 12;")

# ---------------- drum slot: the drum lab's sounds, or a sample ----------------
# The synth sounds are the drum lab's voices (lab/ockm-lab-<type>.pd, built by tools/build_lab.py). The slot runs its
# own copy of each, switched off unless in use, and [ockm-labdrum] (voices/ockm-labdrum.pd_lua) picks the sound, works out
# its settings (randomise, character, morph, tune, decay, level) and plays each hit.
LAB_TYPES=["kick","snare","clap","hat","tom","rim","conga","shaker"]   # switch numbers 0-7; 8 = the sample player
SOUND_NAMES=["kick","snare","clap","perc 1","closed hat","open hat","tom","perc 2"]
p=P()
p.add("#X text 20 10 Drum slot: a drum lab sound (picked by ockm-<slot>-sound 0-7 and \\, for perc \\, ockm-<slot>-synth) \\, or a sample when ockm-<slot>-sample is 1 or more. Only the one in use runs. ockm-<slot>-audition plays it once.;")
inl=p.add("#X obj 30 50 inlet;")
aud=p.add(f"#X obj 130 50 r ockm-{D}1-audition;")
brain=p.add(f"#X obj 300 50 ockm-labdrum {D}1;")
ract=p.add(f"#X obj 500 20 r ockm-{D}1-labact;"); p.con(ract,0,p.add(f"#X obj 500 45 s {D}0-act;"),0)
p.con(inl,0,brain,0); p.con(aud,0,brain,0)
outs=[]
for k,t in enumerate(LAB_TYPES+["sampler"]):
    sp=P()
    so=sp.add("#X obj 20 110 outlet~;")
    if t=="sampler":
        si=sp.add("#X obj 20 20 inlet;"); sg=sp.add("#X obj 20 50 spigot;"); vo=sp.add(f"#X obj 20 80 ockm-sampler {D}1;")
        sp.con(si,0,sg,0); sp.con(sg,0,vo,0)
    else:
        vo=sp.add(f"#X obj 20 80 ockm-lab-{t} ockm-{D}1-{t};")
    rs=sp.add(f"#X obj 200 20 r {D}0-act;"); eq=sp.add(f"#X obj 200 50 == {k};"); tf=sp.add("#X obj 200 80 t f f;"); sw=sp.add("#X obj 200 110 switch~;")
    for c in [(vo,0,so,0),(rs,0,eq,0),(eq,0,tf,0),(tf,1,sw,0)]: sp.con(*c)
    if t=="sampler": sp.con(tf,0,sg,1)
    p.L.append(sp.text(f"#N canvas 0 0 420 160 {t} 0;").rstrip("\n"))
    o=p.add(f"#X restore {30+k*100} 100 pd {t};")
    if t=="sampler": p.con(inl,0,o,0); p.con(aud,0,o,0)
    outs.append(o)
prev=outs[0]
for o in outs[1:]:
    a=p.add("#X obj 30 200 +~;"); p.con(prev,0,a,0); p.con(o,0,a,1); prev=a
# tone (-1 darker \\, 0 as it is \\, 1 brighter) and drive (0 clean \\, 1 gritty), on synth and sample alike
rtn=p.add(f"#X obj 300 160 r ockm-{D}1-tone;"); tnx=p.add(f"#X obj 300 185 expr if({D}f1<0 \\, 18000*pow(2\\,{D}f1*7) \\, 20000) \\; if({D}f1>0 \\, 20*pow(2\\,{D}f1*8) \\, 5);")
lpf=p.add("#X obj 30 215 lop~ 20000;"); hpf=p.add("#X obj 30 235 hip~ 5;")
rdr=p.add(f"#X obj 500 160 r ockm-{D}1-drive;"); drx=p.add(f"#X obj 500 185 expr 1+{D}f1*6;")
drv=p.add(f"#X obj 30 255 expr~ if({D}f2>1.001 \\, tanh({D}v1*{D}f2)/tanh({D}f2) \\, {D}v1);")
out=p.add("#X obj 30 290 outlet~;")
for c in [(prev,0,lpf,0),(lpf,0,hpf,0),(hpf,0,drv,0),(drv,0,out,0),(rtn,0,tnx,0),(tnx,0,lpf,1),(tnx,1,hpf,1),(rdr,0,drx,0),(drx,0,drv,1)]: p.con(*c)
p.save("voices/ockm-drum.pd","#N canvas 180 180 1100 320 12;")

# ---------------- drum row (up to 128 steps, shown 16 at a time) ----------------
p=P()
inl=p.add("#X obj 30 120 inlet;")
tr=p.add(f"#X obj 30 160 tabread ockm-pat-{D}1;")
sel=p.add("#X obj 30 190 sel 0;")
vel=p.add(f"#X obj 70 220 expr if({D}f1>1 \\, 1 \\, if({D}f1>0.999 \\, 1-{D}f2 \\, {D}f1));")   # 2 accent, 1 normal, between 0 and 1: drawn velocity
out=p.add("#X obj 70 260 outlet;")
racc=p.add("#X obj 230 190 r ockm-accent;")
p.add(f"#X obj 30 300 table ockm-pat-\\$1 {STEPS};")
tw=p.add(f"#X obj 400 520 tabwrite ockm-pat-{D}1;")
upk=p.add("#X obj 400 460 unpack f f;"); offs=p.add("#X obj 480 490 + 0;")
tnd=p.add("#X obj 30 152 t f f;"); nrd=p.add(f"#X obj 300 160 tabread ockm-pat-{D}1-nudge;")
nex=p.add(f"#X obj 300 185 expr ({D}f1+0.25)*ockm_stepms;"); npp=p.add("#X obj 70 240 pipe 0;")
p.add(f"#X obj 300 300 table ockm-pat-{D}1-nudge {STEPS};")
kspg=p.add("#X obj 120 270 spigot;"); kis=p.add("#X obj 200 245 == 0;"); skh=p.add("#X obj 120 295 s ockm-kick-hit;")   # a kick: tell the pump
tfi=p.add("#X obj 30 135 t f f;"); dlp=p.add(f"#X obj 30 148 expr if(ockm_drumlen>0 \\, {D}f1 % ockm_drumlen \\, {D}f1);"); fix=p.add(f"#X obj 160 135 expr int({D}f1)%16 + 16*{D}f2;"); rsn=p.add(f"#X obj 260 110 r ockm-{D}1-sound;")
frd=p.add("#X obj 160 160 tabread ockm-fillx;"); fsel=p.add(f"#X obj 30 175 expr if((ockm_fill_on || ockm_fill_end) && {D}f2>=0 \\, {D}f2 \\, {D}f1);")
for c in [(inl,0,tfi,0),(tfi,1,fix,0),(rsn,0,fix,1),(fix,0,frd,0),(frd,0,fsel,1),(tfi,0,dlp,0),(dlp,0,tnd,0),(tnd,1,nrd,0),(nrd,0,nex,0),(nex,0,npp,1),(tnd,0,tr,0),(tr,0,fsel,0),(fsel,0,sel,0),
          (sel,1,vel,0),(racc,0,vel,1),(vel,0,npp,0),(npp,0,out,0),(npp,0,kspg,0),(kspg,0,skh,0),(rsn,0,kis,0),(kis,0,kspg,1),(upk,1,offs,0),(offs,0,tw,1),(upk,0,tw,0)]: p.con(*c)
for i in range(16):
    x=102+i*20+(i//4)*6
    t=p.add(f"#X obj {x} 22 tgl 18 0 empty ockm-sq-{D}1-{i} empty 17 7 0 10 #fcfcfc #000000 #000000 0 1;")
    k=p.add(f"#X obj {160+(i%8)*65} {380+(i//8)*40} pack 0 {i};")
    p.con(t,0,k,0); p.con(k,0,upk,0)
tbl=p.add("#X obj 900 250 r ockm-refresh;")
# refresh the 16 squares for the current page
tr2=p.add("#X obj 900 310 t b b;"); z=p.add("#X msg 960 340 0;"); m16=p.add("#X msg 900 340 16;")
un=p.add("#X obj 900 370 until;"); cf=p.add("#X obj 900 400 f;"); cp=p.add("#X obj 950 400 + 1;")
tf=p.add("#X obj 900 430 t f f;"); mk=p.add(f"#X obj 1000 460 makefilename ockm-sq-{D}1-%d;")
roff=p.add("#X obj 900 460 + 0;"); rd=p.add(f"#X obj 900 490 tabread ockm-pat-{D}1;"); sm=p.add(f"#X msg 900 520 set {D}1;"); snd=p.add("#X obj 900 550 send;")
for c in [(tbl,0,tr2,0),(tr2,1,z,0),(z,0,cf,1),(tr2,0,m16,0),(m16,0,un,0),(un,0,cf,0),(cf,0,cp,0),(cp,0,cf,1),(cf,0,tf,0),
          (tf,1,mk,0),(mk,0,snd,1),(tf,0,roff,0),(roff,0,rd,0),(rd,0,sm,0),(sm,0,snd,0)]: p.con(*c)
# page: which 16 steps the squares show
rp=p.add("#X obj 1150 330 r ockm-page;"); pm=p.add("#X obj 1150 360 * 16;"); ptf=p.add("#X obj 1150 390 t b f;")
for c in [(rp,0,pm,0),(pm,0,ptf,0),(ptf,1,offs,1),(ptf,1,roff,1),(ptf,0,tr2,0)]: p.con(*c)
# edit hook: ockm-edit <track> <step 0-127> <0 off | 1 on | 2 accent>
re=p.add("#X obj 1150 120 r ockm-edit;"); ro=p.add(f"#X obj 1150 150 route {D}1;"); up=p.add("#X obj 1150 180 unpack f f;")
fv=p.add("#X obj 1210 240 f;"); ti=p.add("#X obj 1150 210 t b b f;"); ase=p.add(f"#X obj 1210 280 array set ockm-pat-{D}1;")
for c in [(re,0,ro,0),(ro,0,up,0),(up,1,fv,1),(up,0,ti,0),(ti,2,ase,1),(ti,1,fv,0),(fv,0,ase,0),(ti,0,tr2,0)]: p.con(*c)
# timing hook: ockm-nudge <track> <step> <-0.25 early .. 0 on time .. 0.25 late, in steps>
rnu=p.add("#X obj 1150 440 r ockm-nudge;"); rou=p.add(f"#X obj 1150 465 route {D}1;"); unu=p.add("#X obj 1150 490 unpack f f;")
asn=p.add(f"#X obj 1150 520 array set ockm-pat-{D}1-nudge;"); fnu=p.add("#X obj 1210 495 f;"); tnu=p.add("#X obj 1150 495 t b f;")
for c in [(rnu,0,rou,0),(rou,0,unu,0),(unu,1,fnu,1),(unu,0,tnu,0),(tnu,1,asn,1),(tnu,0,fnu,0),(fnu,0,asn,0)]: p.con(*c)   # step first, then the value
# extend: when a pattern gets longer, repeat what's there to fill the new steps
rx=p.add("#X obj 1400 120 r ockm-drum-extend;"); ux=p.add("#X obj 1400 150 unpack f f;")
cnt=p.add(f"#X obj 1400 210 expr {D}f2-{D}f1;"); txo=p.add("#X obj 1400 180 t f f;")
mo=p.add("#X obj 1400 240 moses 1;"); ux2=p.add("#X obj 1460 270 until;")
ci=p.add("#X obj 1460 300 f;"); cip=p.add("#X obj 1510 300 + 1;"); tci=p.add("#X obj 1460 330 t f f;")
md=p.add(f"#X obj 1460 360 expr {D}f1 % {D}f2;"); xr=p.add(f"#X obj 1460 390 tabread ockm-pat-{D}1;"); xw=p.add(f"#X obj 1460 420 tabwrite ockm-pat-{D}1;")
xr2=p.add(f"#X obj 1600 390 tabread ockm-pat-{D}1-nudge;"); xw2=p.add(f"#X obj 1600 420 tabwrite ockm-pat-{D}1-nudge;")
p.con(md,0,xr2,0); p.con(xr2,0,xw2,0)
for c in [(rx,0,ux,0),(ux,1,cnt,1),(ux,0,txo,0),(txo,1,ci,1),(txo,1,md,1),(txo,0,cnt,0),(cnt,0,mo,0),
          (ux2,0,ci,0),(ci,0,cip,0),(cip,0,ci,1),(ci,0,tci,0),(tci,1,xw,1),(tci,0,md,0),(md,0,xr,0),(xr,0,xw,0)]: p.con(*c)
p.con(tci,1,xw2,1)
tbf2=p.add("#X obj 1400 270 t b f;"); p.con(mo,1,tbf2,0); p.con(tbf2,1,ux2,0); p.con(tbf2,0,tr2,0)
p.add("#X text 100 120 step in -> look it up -> send hit strength out (accent = 1 \\, normal = 1 minus accent amount);")
p.add("#X text 900 90 refresh: update the squares after a pattern loads;")
p.add("#X text 1150 90 edit: ockm-edit <track> <step> <0 off \\, 1 on \\, 2 accent>;")
p.add("#X text 1400 90 extend: repeat steps to fill a longer pattern;")
p.save("seq/ockm-row.pd","#N canvas 200 200 1700 600 12;",["#X coords 0 -1 1 1 340 24 3 100 19;"])

# ---------------- bass sequencer ----------------
p=P()
p.add("#X text 20 10 Mono synth pattern (bass or lead). Each step has a note \\, on/off \\, accent and slide. Up to 128 steps.;")
inl=p.add("#X obj 30 60 inlet;"); t5=p.add("#X obj 30 100 t f f f f f f;")
pmod=p.add("#X obj 30 80 mod 256;"); p.con(p.add(f"#X obj 100 55 r ockm-{D}1-len;"),0,pmod,1)   # the step inside this part's own length
rn=p.add(f"#X obj 30 300 tabread ockm-pat-{D}1-note;"); ra=p.add(f"#X obj 140 260 tabread ockm-pat-{D}1-acc;"); rsl=p.add(f"#X obj 250 220 tabread ockm-pat-{D}1-slide;")
pz=p.add("#X obj 360 130 sel 0;"); lst=p.add("#X obj 360 160 f 128;"); m1a=p.add("#X obj 360 185 - 1;"); m1b=p.add("#X obj 420 160 - 1;"); rlen=p.add(f"#X obj 470 100 r ockm-{D}1-len;")
t2=p.add("#X obj 360 210 t f f;")
ps=p.add(f"#X obj 360 260 tabread ockm-pat-{D}1-slide;"); po=p.add(f"#X obj 470 230 tabread ockm-pat-{D}1-on;"); mul=p.add("#X obj 360 300 *;")
pk=p.add("#X obj 30 360 pack f f f f;"); ro=p.add(f"#X obj 600 140 tabread ockm-pat-{D}1-on;"); sp=p.add("#X obj 30 400 spigot;")
eq=p.add("#X obj 600 180 == 0;"); s1=p.add("#X obj 600 210 sel 1;"); off=p.add("#X msg 600 240 off;"); out=p.add("#X obj 30 460 outlet;")
for j,nm in enumerate(["note","on","acc","slide"]): p.add(f"#X obj {30+j*160} 520 table ockm-pat-{D}1-{nm} {STEPS};")
# how each note sits on the harmony as it plays (v0.74): on a turnaround bar a following part moves to V (the bass by the
# root's step, both with the scale's 7th raised); with walk on, the last notes of a bar step a semitone below the next chord's root
gstep=p.add("#X obj 30 50 t f f;")
def _semi(d): return f"({D}s4[((({d})%7)+7)%7] + 12*floor(({d})/7.0))"
_IC=f"(int({D}f2) % max(ockm_chordlen\\,1))"; _IN=f"((int({D}f2) - int({D}f2)%16 + 16) % max(ockm_chordlen\\,1))"
_C=f"int({D}s3[{_IC}])"; _N=f"int({D}s3[{_IN}])"
_SH=f"({_semi('4')} - {_semi(_C)})"; _SH2=f"({_SH} - 12*({_SH}>6) + 12*({_SH}<-6))"
_T=f"({D}f1 + {D}f7*{_SH2})"
_R7=f"({_T} + ((((int({_T}) - int(ockm_root))%12)+12)%12==10))"
_TP=f"(ockm_root + {_semi(_N)} - 1)"; _TG=f"({_TP} + 12*floor(({D}f1 - {_TP})/12.0 + 0.5))"
xf=p.add(f"#X obj 30 330 expr if({D}f1<=0 \\, {D}f1 \\, if(ockm_turn_on && {D}f5>0 \\, {_R7} \\, if({D}f6>0 && {D}f5>0 && int({D}f2)%16>=14 && {_N}!={_C} \\, {_TG} \\, {D}f1)));")
xlb=p.add("#X obj 1100 40 loadbang;"); xs3=p.add("#X obj 1100 70 symbol ockm-pat-chord-deg;"); xs4=p.add(f"#X obj 1260 70 symbol {D}0-sc;")
xsc=p.add(f"#X obj 1450 40 array define {D}0-sc 7;"); rsc=p.add("#X obj 1450 70 r ockm-scale;"); z0=p.add("#X msg 1550 70 0;")
tsc=p.add("#X obj 1450 100 text get ockm-presets-scale;"); lsc=p.add("#X obj 1450 125 list split 1;"); asc=p.add(f"#X obj 1450 150 array set {D}0-sc;")
rroot=p.add("#X obj 1100 160 r ockm-root;"); vroot=p.add("#X obj 1100 185 v ockm_root;")
rsy=p.add(f"#X obj 1250 160 r ockm-{D}1-sync;"); rwk=p.add(f"#X obj 1250 200 r ockm-{D}1-walk;")
xtr=p.add(f"#X obj 1650 70 symbol {D}1;"); xbs=p.add("#X obj 1650 95 sel bass;"); xone=p.add("#X msg 1650 120 1;")
for c in [(xlb,0,xs3,0),(xlb,0,xs4,0),(xs3,0,xf,2),(xs4,0,xf,3),(rsc,0,tsc,0),(xlb,0,z0,0),(z0,0,tsc,0),(tsc,0,lsc,0),(lsc,1,asc,0),
          (rroot,0,vroot,0),(rsy,0,xf,4),(rwk,0,xf,5),(xlb,0,xtr,0),(xtr,0,xbs,0),(xbs,0,xone,0),(xone,0,xf,6),(gstep,1,xf,1)]: p.con(*c)
for c in [(inl,0,gstep,0),(gstep,0,pmod,0),(pmod,0,t5,0),(t5,4,ro,0),(t5,3,rsl,0),(t5,2,pz,0),(t5,1,ra,0),(t5,0,rn,0),(rn,0,xf,0),(xf,0,pk,0),(sp,0,p.add(f"#X obj 200 460 s ockm-{D}1-notes-out;"),0),(ra,0,pk,1),(rsl,0,pk,3),
    (pz,0,lst,0),(lst,0,m1a,0),(m1a,0,t2,0),(pz,1,m1b,0),(m1b,0,t2,0),(rlen,0,lst,1),
    (t2,1,po,0),(t2,0,ps,0),(po,0,mul,1),(ps,0,mul,0),(mul,0,pk,2),(pk,0,sp,0),(ro,0,sp,1),(ro,0,eq,0),(eq,0,s1,0),(s1,0,off,0),(off,0,out,0),(sp,0,out,0)]: p.con(*c)
re=p.add(f"#X obj 720 560 r ockm-{D}1-edit;"); tl=p.add("#X obj 720 590 t l l;"); ls=p.add("#X obj 900 620 list split 1;")
up=p.add("#X obj 720 650 unpack f f f f f;")
p.con(re,0,tl,0); p.con(tl,1,ls,0); p.con(tl,0,up,0)
# extend
rx=p.add(f"#X obj 1500 120 r ockm-{D}1-extend;"); ux=p.add("#X obj 1500 150 unpack f f;")
cnt=p.add(f"#X obj 1500 210 expr {D}f2-{D}f1;"); txo=p.add("#X obj 1500 180 t f f;")
mo=p.add("#X obj 1500 240 moses 1;"); ux2=p.add("#X obj 1560 270 until;")
ci=p.add("#X obj 1560 300 f;"); cip=p.add("#X obj 1610 300 + 1;"); tci=p.add("#X obj 1560 330 t f f;")
md=p.add(f"#X obj 1560 360 expr {D}f1 % {D}f2;"); t4=p.add("#X obj 1560 390 t f f f f;")
for c in [(rx,0,ux,0),(ux,1,cnt,1),(ux,0,txo,0),(txo,1,ci,1),(txo,1,md,1),(txo,0,cnt,0),(cnt,0,mo,0),(mo,1,ux2,0),
          (ux2,0,ci,0),(ci,0,cip,0),(cip,0,ci,1),(ci,0,tci,0),(tci,0,md,0),(md,0,t4,0)]: p.con(*c)
for j,nm in enumerate(["note","on","acc","slide"]):
    x=720+j*190
    tw=p.add(f"#X obj {x} 700 tabwrite ockm-pat-{D}1-{nm};"); p.con(ls,0,tw,1); p.con(up,j+1,tw,0)
    xr=p.add(f"#X obj {1500+j*120} 430 tabread ockm-pat-{D}1-{nm};"); xw=p.add(f"#X obj {1500+j*120} 460 tabwrite ockm-pat-{D}1-{nm};")
    p.con(t4,3-j,xr,0); p.con(xr,0,xw,0); p.con(tci,1,xw,1)
p.add("#X text 140 400 only lets the note through if the step is on;")
p.add("#X text 420 100 glide into this note if the previous step had slide on;")
p.add("#X text 720 530 edit one step: ockm-<track>-edit <step> <note> <on> <accent> <slide>;")
p.add("#X text 1500 90 extend: repeat steps to fill a longer pattern;")
p.save("seq/ockm-monoseq.pd","#N canvas 150 150 1800 760 12;")

# ---------------- main patch ----------------
# six drum slots: (slot, default sound number)
SLOTS=[("d1",0),("d2",1),("d3",2),("d4",4),("d5",5),("d6",7),("d7",3),("d8",6)]
VERB=[0]*8   # default reverb send per sound: new projects start dry, you add it
DLY=[0]*8    # default delay send per sound: likewise
MONO=["note","on","acc","slide"]; CHORD=["on","deg"]
def show(h): return "ockm-show-"+h[5:]
# Settings registry: (hook, default, hook the store listens to if different)
PROJECT_KEYS=[("ockm-drum-punch",0.5,None),("ockm-bpm",124,"ockm-tempo"),("ockm-volume",1,None),("ockm-accent",0.3,None),("ockm-filter",0,"ockm-filter-now"),("ockm-drive",0,None),
    ("ockm-delay-mix",0.5,None),("ockm-delay-fb",0.4,None),("ockm-delay-steps",3,None),("ockm-verb-mix",0.3,None),
    ("ockm-verb-size",0.6,None),("ockm-verb-tone",0.5,None),("ockm-sync",0,None),("ockm-clock-out",1,None)]
# v0.93: a starting mix like a real one (kick loudest, hats and percussion tucked in), with room above on every fader (up to 1.5)
MIX_DRUM={0:1.0,1:0.75,2:0.75,3:0.6,4:0.55,5:0.5,6:0.65,7:0.6}   # by sound: kick snare clap perc-1 hat open-hat tom perc-2
MIX_SYNTH={"bass":0.85,"lead":0.7,"chord":0.65}
for nm,snd in SLOTS:
    PROJECT_KEYS+=[(f"ockm-{nm}-sound",snd,None),(f"ockm-{nm}-sample",0,None),(f"ockm-{nm}-synth",0,None),(f"ockm-{nm}-tone",0,None),
                   (f"ockm-{nm}-drive",0,None),(f"ockm-{nm}-start",0,None),(f"ockm-{nm}-tune",0,None),(f"ockm-{nm}-decay",100,None),
                   (f"ockm-{nm}-level",MIX_DRUM[snd],None),(f"ockm-{nm}-verb",VERB[snd],None),(f"ockm-{nm}-delay",DLY[snd],None),
                   (f"ockm-{nm}-labchar",0,None),(f"ockm-{nm}-labmorph",0,None),(f"ockm-{nm}-labrseed",0,None),(f"ockm-{nm}-labramt",0,None),(f"ockm-{nm}-labpseed",1,None)]
for _t in [n for n,_ in SLOTS]+["bass","lead","chord"]:
    PROJECT_KEYS+=[(f"ockm-{_t}-{k}",v,None) for k,v in EQ_DEF.items()]
LFO_DEF={"lfo-shape":0,"lfo-rate":4,"lfo-depth":0,"lfo-target":1,"chorus":0}   # sine, one bar, off, the first knob; chorus off
SYNTH_DEFAULTS={"bass":dict(engine=5,mode=0,sync=1,walk=0,sidechain=0,scshape=1,half=0,lock=0,density=1,seed=0,level=0.85,k1=0.42,k2=0.25,k3=0.45,k4=0.45,drive=0,verb=0,delay=0,rhythm=0,notes=0,**LFO_DEF),
                "lead":dict(engine=4,mode=0,sync=1,sidechain=0,scshape=1,half=0,lock=0,density=1,seed=0,outside=0.35,level=0.7,k1=0.55,k2=0.3,k3=0.4,k4=0.45,drive=0,verb=0,delay=0,rhythm=0,notes=0,**LFO_DEF),
                "chord":dict(engine=0,mode=0,sidechain=0,scshape=1,half=0,level=0.65,k1=0.45,k2=0.5,k3=0,k4=0.32,type=0,smooth=1,verb=0,delay=0,rhythm=0,prog=0,voicing=0,strum=0,**LFO_DEF)}
PATTERN_KEYS=[("ockm-end",0,None),("ockm-impact",0,None),("ockm-pump",0,None),("ockm-bass-on",1,None),("ockm-lead-on",1,None),("ockm-chord-on",1,None),("ockm-rise",0,None),("ockm-drum-len",16,None),("ockm-bass-len",64,None),("ockm-lead-len",64,None),("ockm-chord-len",64,None),("ockm-swing",56,"ockm-swing-now"),("ockm-root",9,None),("ockm-scale",0,None),("ockm-leader",0,None),("ockm-drum-groove",-1,None),("ockm-fill-every",0,None),("ockm-fill-style",0,None),("ockm-drums-on",1,None),("ockm-turn-every",0,None),("ockm-style",-1,None)]
for t,d in SYNTH_DEFAULTS.items():
    PATTERN_KEYS+=[(f"ockm-{t}-{k}",v,None) for k,v in d.items()]
TABLES=[f"ockm-pat-{n}" for n,_ in SLOTS]+[f"ockm-pat-{n}-nudge" for n,_ in SLOTS]+[f"ockm-pat-{t}-{f}" for t in ("bass","lead") for f in MONO]+[f"ockm-pat-chord-{f}" for f in CHORD]
PROJ_DIR="projects/default"
p=P()
p.raw("#X declare -path voices -path seq -path lab;")
p.add("#X text 30 10 OCKM_GENERATOR engine: clock \\, swing \\, pattern switching \\, voices and mixer. The screens only talk to it through the named ockm- hooks.;")
p.add("#X obj 1500 50 v ockm_sr;")   # the sample rate, for the track EQs (they fill it in on load)
lb=p.add("#X obj 30 50 loadbang;"); lbt=p.add("#X obj 30 75 t b b b;")
dsp=p.add("#X msg 1100 760 \; pd dsp 1;")
bpmm=p.add("#X obj 30 160 s ockm-tempo;"); bpm=p.add("#X floatatom 30 135 5 40 200 0 - - -;"); p.con(p.add("#X obj 120 105 r ockm-bpm;"),0,bpm,0); p.add("#X text 85 135 BPM;")
ex=p.add(f"#X obj 30 165 expr 15000/{D}f1;"); p.con(ex,0,p.add("#X obj 140 165 s ockm-stepms;"),0)
tg=p.add("#X obj 250 50 tgl 25 0 ockm-playing ockm-play empty 17 7 0 10 #fcfcfc #000000 #000000 0 1;"); p.add("#X text 282 52 start/stop;")
ttg=p.add("#X obj 250 78 t f f f f;"); s1p=p.add("#X obj 470 78 sel 1;"); z0p=p.add("#X msg 470 100 0;")
met=p.add("#X obj 250 100 metro 120;"); msp=p.add("#X obj 250 125 spigot 1;"); rtick=p.add("#X obj 180 125 r ockm-tick;"); rsync=p.add("#X obj 400 130 r ockm-sync;"); seq0=p.add("#X obj 400 150 == 0;"); rrst=p.add("#X obj 470 130 r ockm-reset;"); zr=p.add("#X msg 470 155 0;")
f=p.add("#X obj 250 150 f;"); tf0=p.add("#X obj 250 165 t f f;"); p1=p.add("#X obj 300 150 + 1;"); m16=p.add("#X obj 300 175 mod 16;"); rlen=p.add("#X obj 360 160 r ockm-len;")
tff=p.add("#X obj 250 180 t f f;"); mz=p.add("#X obj 250 195 * 1;"); tfb=p.add("#X obj 250 210 t f b;"); one1=p.add("#X msg 300 210 1;")
tsw=p.add("#X obj 250 230 t f f;"); md2=p.add("#X obj 340 230 mod 2;")
mfr=p.add("#X obj 340 255 *;"); mms=p.add("#X obj 340 280 *;"); pipe=p.add("#X obj 250 300 pipe 0;")
disp=p.add("#X floatatom 330 320 5 0 0 0 - - -;"); p.add("#X text 380 320 step;"); sst=p.add("#X obj 450 320 s ockm-step;")
swm=p.add("#X obj 120 205 r ockm-swing;"); sw=p.add("#X floatatom 120 230 5 50 75 0 - - -;"); p.add("#X text 120 255 swing %;")
swx=p.add(f"#X obj 120 280 expr ({D}f1-50)/50;")
accm=p.add("#X obj 30 205 r ockm-show-accent;"); acc=p.add("#X floatatom 30 230 4 0 1 0 - - ockm-accent;"); p.add("#X text 30 255 accent;")
for c in [(lb,0,lbt,0),(lbt,0,dsp,0),(bpm,0,bpmm,0),(bpm,0,ex,0),(ex,0,met,1),(ex,0,mms,1),
    (tg,0,ttg,0),(ttg,3,s1p,0),(s1p,0,z0p,0),(z0p,0,f,1),(ttg,0,met,0),
    (met,0,msp,0),(msp,0,f,0),(rtick,0,f,0),(rsync,0,seq0,0),(seq0,0,msp,1),(rrst,0,zr,0),(zr,0,f,1),(f,0,tf0,0),(tf0,1,p1,0),(p1,0,m16,0),(m16,0,f,1),(rlen,0,m16,1),
    (tf0,0,tff,0),(tff,0,mz,0),(mz,0,tfb,0),(tfb,1,one1,0),(one1,0,mz,1),(tfb,0,tsw,0),
    (tsw,1,md2,0),(md2,0,mfr,0),(mfr,0,mms,0),(mms,0,pipe,1),(tsw,0,pipe,0),
    (pipe,0,disp,0),(pipe,0,sst,0),(swm,0,sw,0),(sw,0,p.add("#X obj 190 255 s ockm-swing-now;"),0),(sw,0,swx,0),(swx,0,mfr,1),(accm,0,acc,0)]: p.con(*c)
# pattern slots
p.add("#X text 520 50 pattern;")
hr=p.add("#X obj 520 75 hradio 25 1 0 8 empty ockm-slotset empty 0 -8 0 10 #fcfcfc #000000 #000000 0;")
p.add("#X text 520 105 1    2    3    4    5    6    7    8;")
sv=p.add("#X obj 740 50 bng 25 250 50 0 empty ockm-save empty 17 7 0 10 #fcfcfc #000000 #000000;"); p.add("#X text 772 52 save;")
p.con(hr,0,p.add("#X obj 520 140 s ockm-want;"),0)
rw=p.add("#X obj 560 170 r ockm-want;"); tbf=p.add("#X obj 560 195 t b f;"); pend=p.add("#X obj 560 330 f;")
tbb=p.add("#X obj 560 220 t b b;"); one=p.add("#X msg 640 245 1;"); spg=p.add("#X obj 560 250 spigot 1;")
tbb2=p.add("#X obj 560 275 t b b;"); zero=p.add("#X msg 640 300 0;"); flag=p.add("#X obj 700 300 f;"); eqz=p.add("#X obj 330 50 == 0;")
bm=p.add("#X obj 400 180 mod 16;"); s0=p.add("#X obj 400 200 sel 0;"); s1=p.add("#X obj 700 330 sel 1;"); tbb3=p.add("#X obj 700 355 t b b b b;"); zero2=p.add("#X msg 860 380 0;")
zmul=p.add("#X msg 810 380 0;"); onef=p.add("#X msg 760 380 1;")
tcur=p.add("#X obj 560 360 t f f;"); cur=p.add("#X obj 740 140 f;"); sld=p.add("#X obj 560 385 s ockm-load;")
tsv=p.add("#X obj 740 85 t b b;"); sstore=p.add("#X obj 740 170 s ockm-do-save;")
tbar=p.add("#X obj 400 220 t b b;"); sbar=p.add("#X obj 330 245 s ockm-bar;")   # every bar start, after any pattern switch
bm4=p.add("#X obj 470 200 mod 4;"); sb4=p.add("#X obj 470 220 sel 0;"); sbt=p.add("#X obj 470 245 s ockm-beat;")   # every beat, before its hits
p.con(bm4,0,sb4,0); p.con(sb4,0,sbt,0)
for c in [(rw,0,tbf,0),(tbf,1,pend,1),(tbf,0,tbb,0),(tbb,1,one,0),(one,0,flag,1),(tbb,0,spg,0),(spg,0,tbb2,0),(tbb2,1,zero,0),(zero,0,flag,1),(tbb2,0,pend,0),
    (ttg,2,eqz,0),(eqz,0,spg,1),(tff,1,bm,0),(bm,0,bm4,0),(bm,0,s0,0),(s0,0,tbar,0),(tbar,1,flag,0),(tbar,0,sbar,0),(flag,0,s1,0),(s1,0,tbb3,0),
    (tbb3,3,zero2,0),(zero2,0,flag,1),(tbb3,2,zmul,0),(zmul,0,mz,1),(tbb3,1,onef,0),(onef,0,f,1),(tbb3,0,pend,0),
    (pend,0,tcur,0),(tcur,1,cur,1),(tcur,0,sld,0),(sv,0,tsv,0),(tsv,1,cur,0),(cur,0,sstore,0)]: p.con(*c)
# pattern length (1-128) and editing page
p.add("#X text 880 50 length;")
lenb=p.add("#X floatatom 880 75 4 1 256 0 - - ockm-length;"); lset=p.add(f"#X msg 880 105 set {D}1;"); rl2=p.add("#X obj 940 105 r ockm-len;")
p.con(rl2,0,lset,0); p.con(lset,0,lenb,0)
p.add("#X text 960 50 page;")
pg=p.add("#X floatatom 960 75 3 0 7 0 - - ockm-page;")
p.add("#X text 1000 75 (squares show steps page x 16 + 1 to 16);")
p.add("#X obj 880 140 ockm-lengths;")   # each part's length, and the loop length (the longest part)
rvb=p.add("#X obj 810 50 bng 25 250 50 0 empty empty empty 17 7 0 10 #fcfcfc #000000 #000000;"); p.add("#X text 842 52 revert;")
p.con(rvb,0,p.add("#X obj 810 85 s ockm-revert;"),0)
p.add("#X obj 1100 420 ockm-store;")
p.add(f"#X obj 1250 450 table ockm-solos {len(SLOTS)+3};")
_sum=p.add("#X obj 1250 560 array sum ockm-solos;"); _ss=p.add("#X obj 1250 585 s ockm-soloing;")
p.con(_sum,0,_ss,0)
for _i,_t in enumerate([n for n,_ in SLOTS]+["bass","lead","chord"]):
    _r=p.add(f"#X obj {1250+(_i%6)*110} {480+(_i//6)*40} r ockm-{_t}-solo;"); _ne=p.add(f"#X obj {1250+(_i%6)*110} {500+(_i//6)*40} != 0;")
    _tw=p.add(f"#X obj {1250+(_i%6)*110} {520+(_i//6)*40} tabwrite ockm-solos {_i};"); _tb=p.add(f"#X obj {1300+(_i%6)*110} {520+(_i//6)*40} t b f;")
    p.con(_r,0,_ne,0); p.con(_ne,0,_tb,0); p.con(_tb,1,_tw,0); p.con(_tb,0,_sum,0)
p.add(f"#X text 1100 395 settings and patterns: {PROJ_DIR} (project.txt and p1 to p8);")
# drums
mix=p.add("#X obj 560 1000 *~ 0.3;"); fx=p.add("#X obj 560 1030 ockm-fx;"); dac=p.add("#X obj 560 1065 dac~;"); smaster=p.add("#X obj 640 1065 s~ ockm-master;")
vol=p.add("#X obj 560 1048 *~;"); rvol=p.add("#X obj 700 1000 r ockm-volume;"); pvol=p.add("#X obj 700 1020 pack f 20;"); lvol=p.add("#X obj 700 1040 line~;")
p.con(mix,0,fx,0); p.con(fx,0,vol,0); p.con(rvol,0,pvol,0); p.con(pvol,0,lvol,0); p.con(lvol,0,vol,1)
p.con(vol,0,dac,0); p.con(vol,0,dac,1); p.con(vol,0,smaster,0)
# the gap before a drop: no new hits for a beat, the synths let go, the effects ring on
gsp=p.add("#X obj 250 340 spigot 1;"); p.con(pipe,0,gsp,0)
rgp=p.add("#X obj 400 340 r ockm-gap;"); ngp=p.add("#X obj 400 365 == 0;"); p.con(rgp,0,ngp,0); p.con(ngp,0,gsp,1)
sg1=p.add("#X obj 470 365 sel 1;"); p.con(rgp,0,sg1,0)
gof=p.add("#X msg 470 390 off;")
p.con(sg1,0,gof,0)
# drop (perform): hold it and nothing new plays (the same gap as above, the effects ring on); let go and everything
# comes back on the next bar. Stopped, it comes back straight away
rpv=p.add("#X obj 1500 300 r ockm-playing;"); vpv=p.add("#X obj 1500 325 v ockm_playv;"); p.con(rpv,0,vpv,0)
rdr=p.add("#X obj 1650 300 r ockm-drop;"); sdr=p.add("#X obj 1650 325 sel 1;")
don=p.add("#X msg 1650 350 \\; ockm-gap 1;")
dwait=p.add("#X obj 1720 350 expr if(ockm_playv>0 \\, 1 \\, -1);"); dsel=p.add("#X obj 1720 375 sel 1 -1;")
dpend=p.add("#X msg 1720 400 1;"); vdp=p.add("#X obj 1720 425 v ockm_droppend;")
rdb=p.add("#X obj 1850 300 r ockm-bar;"); rds=p.add("#X obj 1950 300 r ockm-playing;"); rds0=p.add("#X obj 1950 325 sel 0;")
dchk=p.add("#X obj 1850 350 expr ockm_droppend;"); dsel2=p.add("#X obj 1850 375 sel 1;")
dback=p.add("#X msg 1850 400 \\; ockm-gap 0;"); dclr=p.add("#X msg 1950 400 0;"); vdp2=p.add("#X obj 1950 425 v ockm_droppend;")
dtb=p.add("#X obj 1850 375 t b b;")
# mutes that land on the beat or the bar (live screen). ockm-mute-quant: 0 now, 1 next beat, 2 next bar.
# ockm-<track>-mute-q 0/1 asks for a mute: straight away when stopped or 'now', otherwise held until the next beat or bar,
# then sent as ockm-<track>-mute before that step's hits. Stopping lets anything waiting go at once.
rmq=p.add("#X obj 2100 300 r ockm-mute-quant;"); vmq=p.add("#X obj 2100 325 v ockm_mq;"); p.con(rmq,0,vmq,0)
# v0.93: ockm-mute-bar 1 makes every mute wait for the next bar whatever the setting (a performance recipe's mutes land
# on the 1, with its effects); 0 goes back to the setting
rmb=p.add("#X obj 1950 300 r ockm-mute-bar;"); vmb=p.add("#X obj 1950 325 v ockm_mqb;"); p.con(rmb,0,vmb,0)
rbt=p.add("#X obj 2250 300 r ockm-beat;"); xbt=p.add("#X obj 2250 325 expr ockm_mq==1 && ockm_mqb==0;"); sbt1=p.add("#X obj 2250 350 sel 1;")
rbr=p.add("#X obj 2350 300 r ockm-bar;"); xbr=p.add("#X obj 2350 325 expr ockm_mq>=1 || ockm_mqb>0;"); sbr1=p.add("#X obj 2350 350 sel 1;")
rps=p.add("#X obj 2450 300 r ockm-playing;"); sps=p.add("#X obj 2450 325 sel 0;")
stk=p.add("#X obj 2250 380 s ockm-mute-tick;")
for c in [(rbt,0,xbt,0),(xbt,0,sbt1,0),(sbt1,0,stk,0),(rbr,0,xbr,0),(xbr,0,sbr1,0),(sbr1,0,stk,0),(rps,0,sps,0),(sps,0,stk,0)]: p.con(*c)
for _i,_t in enumerate([n for n,_ in SLOTS]+["bass","lead","chord"]):
    x=2100+_i*120
    rq=p.add(f"#X obj {x} 420 r ockm-{_t}-mute-q;"); tq=p.add(f"#X obj {x} 445 t f f;"); fq=p.add(f"#X obj {x+60} 520 f;")
    now=p.add(f"#X obj {x} 470 expr if(ockm_playv>0 && (ockm_mq>0 || ockm_mqb>0) \\, -1 \\, {D}f1);"); mo=p.add(f"#X obj {x} 495 moses 0;")
    one=p.add(f"#X msg {x} 520 1;"); vp=p.add(f"#X obj {x} 545 v ockm_{_t}_mqp;")
    smt=p.add(f"#X obj {x} 600 s ockm-{_t}-mute;"); z=p.add(f"#X msg {x+40} 575 0;"); vp2=p.add(f"#X obj {x+40} 600 v ockm_{_t}_mqp;")
    rt=p.add(f"#X obj {x} 625 r ockm-mute-tick;"); xp=p.add(f"#X obj {x} 650 expr ockm_{_t}_mqp;"); sp1=p.add(f"#X obj {x} 675 sel 1;"); tbb_=p.add(f"#X obj {x} 700 t b b;")
    for c in [(rq,0,tq,0),(tq,1,fq,1),(tq,0,now,0),(now,0,mo,0),(mo,0,one,0),(one,0,vp,0),(mo,1,smt,0),(mo,1,z,0),(z,0,vp2,0),
              (rt,0,xp,0),(xp,0,sp1,0),(sp1,0,tbb_,0),(tbb_,1,z,0),(tbb_,0,fq,0),(fq,0,smt,0)]: p.con(*c)
for c in [(rdr,0,sdr,0),(sdr,0,don,0),(sdr,0,dclr,0),(sdr,1,dwait,0),(dwait,0,dsel,0),(dsel,0,dpend,0),(dpend,0,vdp,0),(dsel,1,dtb,0),
          (rdb,0,dchk,0),(rds,0,rds0,0),(rds0,0,dchk,0),(dchk,0,dsel2,0),(dsel2,0,dtb,0),(dtb,1,dclr,0),(dtb,0,dback,0),(dclr,0,vdp2,0)]: p.con(*c)
# transition sounds into the mix (and a little reverb)
tfx=p.add("#X obj 400 1000 ockm-transfx;"); p.con(tfx,0,mix,0)
tfs=p.add("#X obj 480 1030 *~ 0.35;"); p.con(tfx,0,tfs,0); p.con(tfs,0,p.add("#X obj 480 1055 throw~ ockm-revbus;"),0)
# sidechain (v0.74): each kick sends out an envelope (ockm-duck: up with the kick, back to 0 over an eighth note). Each synth
# dips by it, by its own ockm-<part>-sidechain (0 off, 1 deep), or by the Perform pump (ockm-pump) when that's deeper
rkh=p.add("#X obj 900 1000 r ockm-kick-hit;"); rpm=p.add("#X obj 1000 1000 r ockm-pump;")
# v0.79: three shapes, each its own envelope. ockm-duck: pump (dips hard, holds half a step, swells back over the beat);
# ockm-duck-short: duck (a quick dip under the kick, back within a step); ockm-duck-gate: gate (cut for an eighth, then straight back)
pmx=p.add(f"#X obj 900 1030 expr min({D}f1\\,1) \\; ockm_stepms*3.5 \\; ockm_stepms*0.5 \\; ockm_stepms*2 \\; ockm_stepms*0.8;")
vpm=p.add("#X obj 1000 1025 v ockm_pumpv;"); p.con(rpm,0,vpm,0)
pkp=p.add("#X obj 900 1060 pack f f f f f;"); p.con(rkh,0,pmx,0)
for k in (4,3,2,1,0): p.con(pmx,k,pkp,k)
lbd=p.add("#X obj 1100 1060 loadbang;"); one_d=p.add("#X msg 1100 1085 0;"); p.con(lbd,0,one_d,0)
for k,(msg,post,name) in enumerate([(f"{D}1 3 \\, 0 {D}2 {D}3","sqrt(max($v1\\,0))","ockm-duck"),(f"{D}1 1.5 \\, 0 {D}5 1.5",None,"ockm-duck-short"),(f"{D}1 2 \\, 0 3 {D}4",None,"ockm-duck-gate")]):
    m_=p.add(f"#X msg {900+k*200} 1085 {msg};"); vl_=p.add(f"#X obj {900+k*200} 1110 vline~;"); sd_=p.add(f"#X obj {900+k*200} 1160 s~ {name};")
    p.con(pkp,0,m_,0); p.con(m_,0,vl_,0); p.con(one_d,0,vl_,0)
    if post:
        ex_=p.add(f"#X obj {900+k*200} 1135 expr~ {post.replace('$',D)};"); p.con(vl_,0,ex_,0); p.con(ex_,0,sd_,0)
    else: p.con(vl_,0,sd_,0)
lbv=p.add("#X obj 820 1000 loadbang;"); onev=p.add("#X msg 820 1020 1;"); p.con(lbv,0,onev,0); p.con(onev,0,pvol,0)
# the drums in or out of this pattern (ockm-drums-on): out stops every drum row
dgo=p.add("#X obj 250 360 spigot 1;"); p.con(gsp,0,dgo,0); p.con(p.add("#X obj 320 340 r ockm-drums-on;"),0,dgo,1)
for r,(nm,snd) in enumerate(SLOTS):
    y=380+r*40
    p.add(f"#X text 20 {y+2} {nm} {SOUND_NAMES[snd].replace(' ','-')};")
    row=p.add(f"#X obj 110 {y} ockm-row {nm};"); v=p.add(f"#X obj 560 {y+2} ockm-drum {nm};")
    if r==0: p.add(f"#X obj 1200 {y} ockm-samplelib;"); p.add(f"#X obj 1200 {y+25} ockm-recorder;"); p.add(f"#X obj 1200 {y+50} ockm-transitions;")
    gt=p.add(f"#X obj 660 {y+2} ockm-gate {nm} nolevel;")
    eqd=p.add(f"#X obj 710 {y+2} ockm-eq {nm};")
    p.con(dgo,0,row,0); p.con(row,0,v,0); p.con(v,0,gt,0); p.con(gt,0,eqd,0); p.con(eqd,0,p.add(f"#X obj 640 {y+22} throw~ ockm-drumbus;"),0); v=eqd   # to the drum bus
    p.con(eqd,0,p.add(f"#X obj 700 {y+22} throw~ ockm-stem-drums;"),0)
    vs=p.add(f"#X obj 760 {y+2} *~ 0;"); vt=p.add(f"#X obj 830 {y+2} throw~ ockm-revbus;"); vr=p.add(f"#X obj 760 {y-18} r ockm-{nm}-verb;")
    p.con(v,0,vs,0); p.con(vs,0,vt,0); p.con(vr,0,vs,1)
    ds=p.add(f"#X obj 990 {y+2} *~ 0;"); dt_=p.add(f"#X obj 1060 {y+2} throw~ ockm-dlybus;"); dr_=p.add(f"#X obj 990 {y-18} r ockm-{nm}-delay;")
    p.con(v,0,ds,0); p.con(ds,0,dt_,0); p.con(dr_,0,ds,1)
# the drum bus: the eight drums together, then into the mix
cdb=p.add("#X obj 400 960 catch~ ockm-drumbus;"); dbus=p.add("#X obj 400 980 ockm-drumbus;"); p.con(cdb,0,dbus,0); p.con(dbus,0,mix,0)
rsm=p.add("#X obj 1600 380 r ockm-stepms;"); vsm=p.add("#X obj 1600 405 v ockm_stepms;"); p.con(rsm,0,vsm,0)
# build and drop (v0.83). ockm-rise 1 starts a build that ends on a loop start at least 2 bars away: the high-pass climbs
# (slowly at first), a noise riser comes in over the last bar's first 3 beats, the last beat drops out (ockm-gap), and on
# the 1 everything slams back: the filter snaps open, the riser cuts, a crash and sub boom (the impact). Then rise turns
# itself off. Turned off by hand mid-build, the filter glides back and nothing drops.
rri=p.add("#X obj 1750 380 r ockm-rise;"); tri=p.add("#X obj 1750 405 t f f;"); vri=p.add("#X obj 1850 430 v ockm_rise;"); p.con(rri,0,tri,0); p.con(tri,1,vri,0)
rs0=p.add("#X obj 1750 430 sel 0;"); p.con(tri,0,rs0,0)
roff=p.add("#X msg 1750 455 \\; ockm-rise-now 0 100 \\; ockm-gap 0 \\; ockm-riser-stop bang;"); p.con(rs0,0,roff,0)
rtb=p.add("#X obj 1800 455 t b b;"); p.con(rs0,1,rtb,0)
rtot=p.add(f"#X obj 1800 480 expr ockm_plen - ockm_rstep + max(ockm_plen\\,1)*ceil(max(0\\, 32-(ockm_plen-ockm_rstep))/max(ockm_plen\\,1));")
vtot=p.add("#X obj 1800 505 v ockm_rtotal;"); rz=p.add("#X msg 1900 480 0;"); vel=p.add("#X obj 1900 505 v ockm_relap;")
for c in [(rtb,0,rtot,0),(rtot,0,vtot,0),(rtb,1,rz,0),(rz,0,vel,0)]: p.con(*c)
rstp=p.add("#X obj 2000 380 r ockm-step;"); rsf=p.add("#X obj 2000 405 t f f;"); vrs=p.add("#X obj 2100 430 v ockm_rstep;")
p.con(rstp,0,rsf,0); p.con(rsf,1,vrs,0)
# each step of a build: count it, then left = steps to the drop
ron=p.add("#X obj 2000 430 expr if(ockm_rise>0 \\, ockm_relap+1 \\, -1);"); rmo=p.add("#X obj 2000 455 moses 0;"); p.con(rsf,0,ron,0); p.con(ron,0,rmo,0)
rtf=p.add("#X obj 2000 480 t f f;"); vel2=p.add("#X obj 2100 505 v ockm_relap;"); p.con(rmo,1,rtf,0); p.con(rtf,1,vel2,0)
rlx=p.add(f"#X obj 2000 505 expr ockm_rtotal-{D}f1 \\; 0.85*pow(min({D}f1/max(ockm_rtotal\\,1)\\,1)\\,2);"); p.con(rtf,0,rlx,0)
srn=p.add("#X obj 2150 530 s ockm-rise-now;"); p.con(rlx,1,srn,0)
rsl=p.add("#X obj 2000 530 sel 16 0;"); p.con(rlx,0,rsl,0)
# 16 steps to go: the riser over 3 beats, then the gap for the last beat
rr12=p.add("#X obj 2000 555 expr ockm_stepms*12;"); rtg=p.add("#X obj 2000 580 t f f;"); srg=p.add("#X obj 2080 605 s ockm-riser-go;")
rdg=p.add("#X obj 2000 605 delay;"); rgo=p.add("#X msg 2000 630 \\; ockm-gap 1;")
for c in [(rsl,0,rr12,0),(rr12,0,rtg,0),(rtg,1,srg,0),(rtg,0,rdg,0),(rdg,0,rgo,0)]: p.con(*c)
# the drop: rise off first (its glide back is then overridden by the snap), the gap ends, the riser cuts, the filter snaps
# open, and the impact lands a quarter step later (the engine plays a quarter step behind)
rdrop=p.add("#X msg 2150 555 \\; ockm-rise 0 \\; ockm-gap 0 \\; ockm-riser-stop bang \\; ockm-rise-now 0 5;"); p.con(rsl,1,rdrop,0)
rqx=p.add("#X obj 2300 555 expr ockm_stepms*0.25;"); rdq=p.add("#X obj 2300 580 delay;"); rimp=p.add("#X msg 2300 605 \\; ockm-impact-go bang;")
rtb2=p.add("#X obj 2300 530 t b b;"); p.con(rsl,1,rtb2,0)
for c in [(rtb2,1,rqx,0),(rqx,0,rdq,1),(rtb2,0,rdq,0),(rdq,0,rimp,0)]: p.con(*c)
# stopping: no build hanging over
rpst=p.add("#X obj 2400 380 r ockm-playing;"); rps0=p.add("#X obj 2400 405 sel 0;"); rpsm=p.add("#X msg 2400 430 stop;")
for c in [(rpst,0,rps0,0),(rps0,0,rpsm,0),(rpsm,0,rdg,0),(rpsm,0,rdq,0)]: p.con(*c)
rpl=p.add("#X obj 1450 380 r ockm-len;"); vpl=p.add("#X obj 1450 405 v ockm_plen;"); p.con(rpl,0,vpl,0)
# drum settings subpatch
sub=P()
sub.add("#X text 20 10 Drum slots. Sound 0 kick 1 snare 2 clap 3 perc-1 4 closed hat 5 open hat 6 tom 7 perc-2. Tune in semitones \\, decay in % (100 = normal) \\, level 0 to 1.;")
slb=sub.add("#X obj 20 40 loadbang;")
for i,(nm,snd) in enumerate(SLOTS):
    y=80+i*30
    sub.add(f"#X text 20 {y} {nm};")
    for j,(param,dflt,lo,hi) in enumerate([("sound",snd,0,7),("tune",0,-12,12),("decay",100,10,400),("level",1,0,1.5),("verb",VERB[snd],0,1),("delay",DLY[snd],0,1)]):
        m=sub.add(f"#X obj {70+j*140} {y-18} r {show(f'ockm-{nm}-{param}')};")
        fa=sub.add(f"#X floatatom {115+j*140} {y} 5 {lo} {hi} 0 - - ockm-{nm}-{param};")
        sub.con(m,0,fa,0)
sub.add("#X text 70 60 sound          tune           decay          level          reverb send    delay send;")
p.L.append(sub.text("#N canvas 300 200 940 360 drum-settings 0;").rstrip("\n"))
ds=p.add("#X restore 30 960 pd drum-settings;")
p.add("#X text 30 985 sound \\, tune \\, decay \\, level and sends per drum slot;")
# synth tracks: bass and lead (mono synth), chord
by=380+len(SLOTS)*40+10
SYN=[("bass","ockm-monoseq bass","ockm-mono bass"),("lead","ockm-monoseq lead","ockm-lead lead"),("chord","ockm-chordseq chord","ockm-chord chord")]
synth_voice={}
rq4=p.add("#X obj 300 1500 r ockm-stepms;"); lq4=p.add("#X obj 300 1525 * 0.25;"); p.con(rq4,0,lq4,0)
# half-time loop counter: counts each wrap to step 0, from 0 again when play starts
rhl=p.add("#X obj 200 1500 r ockm-len;")
hw0=p.add("#X obj 120 1500 sel 0;"); hwf=p.add("#X obj 120 1525 f 0;"); hwi=p.add("#X obj 160 1525 + 1;"); hwv=p.add("#X obj 120 1550 v ockm_hwrap;")
p.con(gsp,0,hw0,0); p.con(hw0,0,hwf,0); p.con(hwf,0,hwi,0); p.con(hwi,0,hwf,1); p.con(hwf,0,hwv,0)
hwp=p.add("#X obj 40 1500 r ockm-playing;"); hws=p.add("#X obj 40 1525 sel 1;"); hwz=p.add("#X msg 40 1550 0;")
p.con(hwp,0,hws,0); p.con(hws,0,hwz,0); p.con(hwz,0,hwf,1)
for r,(nm,seqo,voi) in enumerate(SYN):
    y=by+r*40
    p.add(f"#X text 20 {y+2} {nm};")
    sq=p.add(f"#X obj 110 {y} {seqo};"); vo=p.add(f"#X obj 560 {y} {voi};")
    # sidechain: dips by its amount (ockm-<part>-sidechain, 1 = silent) in its shape (ockm-<part>-scshape 0 duck, 1 pump, 2 gate),
    # or by the Perform pump (always the pump shape) when that's deeper
    gt0=p.add(f"#X obj 660 {y} ockm-gate {nm} level;")
    gdk=p.add(f"#X obj 660 {y+14} expr~ {D}v1*(1 - max({D}f3*if({D}f4 < 0.5 \\, {D}v5 \\, if({D}f4 < 1.5 \\, {D}v2 \\, {D}v6)) \\, 0.75*ockm_pumpv*{D}v2));"); p.con(gt0,0,gdk,0)
    p.con(p.add(f"#X obj 740 {y+14} r~ ockm-duck;"),0,gdk,1); p.con(p.add(f"#X obj 820 {y+14} r ockm-{nm}-sidechain;"),0,gdk,2)
    p.con(p.add(f"#X obj 900 {y+14} r ockm-{nm}-scshape;"),0,gdk,3)
    p.con(p.add(f"#X obj 980 {y+14} r~ ockm-duck-short;"),0,gdk,4); p.con(p.add(f"#X obj 1060 {y+14} r~ ockm-duck-gate;"),0,gdk,5)
    gt=p.add(f"#X obj 710 {y+14} ockm-eq {nm};"); p.con(gdk,0,gt,0)
    # a quarter step late, like the drums on time, so drum steps can be nudged early
    lq=p.add(f"#X obj 300 {y} pipe 0;"); p.con(gsp,0,lq,0); p.con(lq4,0,lq,1)
    # this part on or off in this pattern (ockm-<part>-on): off stops its steps and silences it
    pon=p.add(f"#X obj 360 {y} spigot 1;"); ron=p.add(f"#X obj 420 {y-18} r ockm-{nm}-on;"); ton=p.add(f"#X obj 420 {y+6} t f f;")
    s0n=p.add(f"#X obj 480 {y+6} sel 0;"); ofn=p.add(f"#X msg 480 {y+24} off;")
    # half-time (ockm-<part>-half): the part plays its own pattern at half speed, one of its steps every two (odd steps drop out)
    # over two loops: the first plays the pattern's first half, the second its second half
    hx=p.add(f"#X obj 330 {y-18} expr if(ockm_{nm}_half > 0 \\, if(int({D}f1)%2==0 \\, int({D}f1)/2 + (ockm_hwrap%2)*int({D}f2/2) \\, -1) \\, {D}f1);"); hm=p.add(f"#X obj 330 {y-4} moses 0;")
    p.con(rhl,0,hx,1)
    rhf=p.add(f"#X obj 300 {y-40} r ockm-{nm}-half;"); p.con(rhf,0,p.add(f"#X obj 300 {y-28} v ockm_{nm}_half;"),0)
    p.con(lq,0,hx,0); p.con(hx,0,hm,0)
    for c in [(hm,1,pon,0),(pon,0,sq,0),(ron,0,ton,0),(ton,1,pon,1),(ton,0,s0n,0),(s0n,0,ofn,0),(ofn,0,vo,0)]: p.con(*c)
    cho=p.add(f"#X obj 560 {y+20} ockm-chorus {nm};")
    p.con(sq,0,vo,0); p.con(vo,0,cho,0); p.con(cho,0,gt0,0); p.con(gt,0,mix,0)
    p.con(gt,0,p.add(f"#X obj 700 {y+22} throw~ ockm-stem-{nm};"),0)
    vs=p.add(f"#X obj 760 {y} *~ 0;"); vt=p.add(f"#X obj 830 {y} throw~ ockm-revbus;"); vr=p.add(f"#X obj 760 {y-18} r ockm-{nm}-verb;")
    p.con(gt,0,vs,0); p.con(vs,0,vt,0); p.con(vr,0,vs,1)
    ds=p.add(f"#X obj 990 {y} *~ 0;"); dt_=p.add(f"#X obj 1060 {y} throw~ ockm-dlybus;"); dr_=p.add(f"#X obj 990 {y-18} r ockm-{nm}-delay;")
    p.con(gt,0,ds,0); p.con(ds,0,dt_,0); p.con(dr_,0,ds,1)
    synth_voice[nm]=vo
s0b=p.add("#X obj 400 80 sel 0;"); offm=p.add("#X msg 400 105 off;")
p.con(ttg,1,s0b,0); p.con(s0b,0,offm,0)
p.con(s0b,0,p.add("#X msg 460 105 \\; ockm-rise-now 0;"),0)
for nm in ("bass","lead","chord"): p.con(offm,0,synth_voice[nm],0); p.con(gof,0,synth_voice[nm],0)
# generators and shared presets
gy=by+3*40+20
p.add(f"#X obj 110 {gy} ockm-presets;")
p.add(f"#X obj 230 {gy} ockm-monogen bass 0 0 0 0 1 0;")
p.add(f"#X obj 400 {gy} ockm-monogen lead 24 0 0 0 1 1;")
p.add(f"#X obj 530 {gy} ockm-chordgen chord 0;")
p.add(f"#X obj 700 {gy} ockm-grooves;")
for i,nm in enumerate(("bass","lead","chord")): p.add(f"#X obj {830+i*110} {gy} ockm-lfo-{nm};")
for i,(nm,snd) in enumerate(SLOTS): p.add(f"#X obj {110+i*120} {gy+30} ockm-drumgen {nm} {snd};")
# synth settings subpatch: key, engines, knobs, generator choices
sub=P()
sub.add("#X text 20 10 Synth settings. Key and scale are shared by bass \\, lead and chord. Knobs run 0 to 1. Generator choices rebuild that track's pattern.;")
slb=sub.add("#X obj 20 40 loadbang;")
def row(y,label,items):
    sub.add(f"#X text 20 {y} {label};")
    for j,(lab,dflt,lo,hi,hook,send_at_load) in enumerate(items):
        x=120+j*95
        sub.add(f"#X text {x} {y-18} {lab};")
        fa=sub.add(f"#X floatatom {x} {y} 5 {lo} {hi} 0 - - {hook};")
        m=sub.add(f"#X obj {x+45} {y-18} r {show(hook)};"); sub.con(m,0,fa,0)
row(80,"key",[("root",9,0,11,"ockm-root",False),("scale",0,0,5,"ockm-scale",False)])
row(140,"bass",[("engine",5,0,6,"ockm-bass-engine",True),("k1",0.42,0,1,"ockm-bass-k1",True),("k2",0.25,0,1,"ockm-bass-k2",True),("k3",0.45,0,1,"ockm-bass-k3",True),
                ("k4",0.45,0,1,"ockm-bass-k4",True),("drive",0,0,1,"ockm-bass-drive",True),("rhythm",3,0,7,"ockm-bass-rhythm",False),("notes",3,0,11,"ockm-bass-notes",False)])
row(200,"lead",[("engine",4,0,6,"ockm-lead-engine",True),("k1",0.55,0,1,"ockm-lead-k1",True),("k2",0.3,0,1,"ockm-lead-k2",True),("k3",0.4,0,1,"ockm-lead-k3",True),
                ("k4",0.45,0,1,"ockm-lead-k4",True),("drive",0,0,1,"ockm-lead-drive",True),("rhythm",6,0,7,"ockm-lead-rhythm",False),("notes",8,0,11,"ockm-lead-notes",False)])
row(260,"chord",[("engine",0,0,5,"ockm-chord-engine",True),("k1",0.45,0,1,"ockm-chord-k1",True),("k2",0.5,0,1,"ockm-chord-k2",True),("k3",0.4,0,1,"ockm-chord-k3",True),
                 ("k4",0.3,0,1,"ockm-chord-k4",True),("type",0,0,12,"ockm-chord-type",True),("smooth",1,0,1,"ockm-chord-smooth",True),("rhythm",0,0,10,"ockm-chord-rhythm",False),("prog",0,0,11,"ockm-chord-prog",False)])
sub.add("#X text 20 300 key root: 0 C ... 9 A ... 11 B. Scale: 0 minor 1 major 2 dorian 3 phrygian 4 mixolydian 5 harmonic minor;")
sub.add("#X text 20 320 bass engines: 0 acid 1 sub/808 2 FM 3 reese 4 pluck 5 analogue (default) 6 donk. Chord engines: 0 stab 1 organ 2 pad 3 piano 4 rhodes 5 strings. Chord type: 0 triad 1 seventh 2 sus2 3 power 4 sus4 5 sixth 6 ninth 7 eleventh;")
sub.add("#X text 20 340 bass/lead rhythm: 0 offbeat 1 rolling 2 gallop 3 acid 4 dub 5 bounce 6 acid16 7 trip-hop. Notes: 0 root 1 octaves 2 root-fifth 3 acid-riff 4 walk-up 5 stab 6 dub 7 pedal 8 arp-up 9 arp-updown 10 call 11 descend;")
sub.add("#X text 20 360 chord rhythm 0-9 and progression 0-9: the names are on the synths screen and in tools/build.py (PRE and PROGS). Smooth 1 = chords move by small steps.;")
p.L.append(sub.text("#N canvas 260 160 1000 400 synth-settings 0;").rstrip("\n"))
p.add(f"#X restore 30 {gy+40} pd synth-settings;")
p.add(f"#X text 30 {gy+65} key \\, engines \\, knobs and generator choices for bass \\, lead and chord;")
# master fx subpatch
sub=P()
sub.add("#X text 20 10 Master effects. Filter -1 to 1 (below 0 low-pass \\, above 0 high-pass). Drive 0 to 1. Delay in steps.;")
slb=sub.add("#X obj 20 40 loadbang;")
for i,(lab,dflt,lo,hi,hook) in enumerate([("filter",0,-1,1,"ockm-filter"),("drive",0,0,1,"ockm-drive"),("delay level",0.5,0,1,"ockm-delay-mix"),
        ("delay feedback",0.4,0,0.9,"ockm-delay-fb"),("delay steps",3,1,8,"ockm-delay-steps"),("reverb level",0.5,0,1,"ockm-verb-mix"),("reverb size",0.6,0,1,"ockm-verb-size"),("reverb tone",0.5,0,1,"ockm-verb-tone"),
        ("bass reverb send",0,0,1,"ockm-bass-verb"),("bass delay send",0,0,1,"ockm-bass-delay"),("lead reverb send",0.2,0,1,"ockm-lead-verb"),("lead delay send",0.25,0,1,"ockm-lead-delay"),
        ("chord reverb send",0.3,0,1,"ockm-chord-verb"),("chord delay send",0.35,0,1,"ockm-chord-delay")]):
    y=80+i*30
    sub.add(f"#X text 20 {y} {lab};")
    m=sub.add(f"#X obj 300 {y} r {show(hook)};"); fa=sub.add(f"#X floatatom 220 {y} 5 {lo} {hi} 0 - - {hook};")
    sub.con(m,0,fa,0)
p.L.append(sub.text("#N canvas 320 220 560 540 master-fx 0;").rstrip("\n"))
p.add("#X restore 250 960 pd master-fx;")
sub=P()
sub.add("#X text 20 10 MIDI clock. Sync 0 = leader (sends clock) \\, 1 = follower (plays to incoming clock). Clock out 1 = send clock when leading.;")
slb=sub.add("#X obj 20 40 loadbang;")
for i,(lab,dflt,lo,hi,hook) in enumerate([("sync",0,0,1,"ockm-sync"),("clock out",1,0,1,"ockm-clock-out")]):
    y=80+i*30
    sub.add(f"#X text 20 {y} {lab};")
    m=sub.add(f"#X obj 220 {y} r {show(hook)};"); fa=sub.add(f"#X floatatom 170 {y} 3 {lo} {hi} 0 - - {hook};")
    sub.con(m,0,fa,0)
p.L.append(sub.text("#N canvas 340 240 640 180 midi-sync 0;").rstrip("\n"))
p.add("#X restore 450 960 pd midi-sync;")
p.add("#X text 450 985 MIDI clock leader or follower;")
p.add("#X obj 450 1010 ockm-clock;")
# v0.95 MIDI in from a controller (an MPK mini, an MPC): pads and knobs, handed to the screen, which knows what's open.
# ockm-midi-note <note> <velocity> <channel> (velocity 0 = let go), ockm-midi-cc <value> <cc> <channel>
nin=p.add("#X obj 450 1040 notein;"); npk=p.add("#X obj 450 1065 pack f f f;"); nsd=p.add("#X obj 450 1090 s ockm-midi-note;")
cin=p.add("#X obj 600 1040 ctlin;"); cpk=p.add("#X obj 600 1065 pack f f f;"); csd=p.add("#X obj 600 1090 s ockm-midi-cc;")
for c in [(nin,2,npk,2),(nin,1,npk,1),(nin,0,npk,0),(npk,0,nsd,0),(cin,2,cpk,2),(cin,1,cpk,1),(cin,0,cpk,0),(cpk,0,csd,0)]: p.con(*c)
# v0.96: pads in program change mode (the MPK mini's PROG CHANGE button): ockm-midi-pgm <program 0-127> <channel>
pin=p.add("#X obj 750 1040 pgmin;"); pm1=p.add("#X obj 750 1065 - 1;"); ppk=p.add("#X obj 750 1090 pack f f;"); psd=p.add("#X obj 750 1115 s ockm-midi-pgm;")
for c in [(pin,1,ppk,1),(pin,0,pm1,0),(pm1,0,ppk,0),(ppk,0,psd,0)]: p.con(*c)
p.add("#X text 250 985 effects and sends;")
p.add("#X obj 1100 800 declare -path voices -path seq -path lab;")
# ---- the main window: the touchscreen UI on top; the engine and the old test panel in closed subpatches ----
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from panel import build_panel
PANW,PANH=build_panel(P,D,lambda q,fn,h: q.save(fn,h),SLOTS,SLOTN,show,args.theme)
DECL="-path voices -path seq -path lab -path ui"
assert p.L[0].startswith("#X declare"); p.L.pop(0)          # the declare belongs to the top level
p.L=[l.replace("#X obj 1100 800 declare -path voices -path seq -path lab;","#X text 1100 800 (the declare is in the main window);") for l in p.L]
UIW,UIH=960*args.ui_scale,600*args.ui_scale
by=UIH+24
m=P()
m.raw(f"#X declare {DECL};")
m.add(f"#X obj 0 0 ockm-ui {args.ui_scale} {args.theme};")
m.L.append(p.text("#N canvas 60 60 1420 1100 engine 0;").rstrip("\n"))
m.add(f"#X restore 20 {by} pd engine;")
tp=P(); tp.add("#X obj 0 0 ockm-panel;")
m.L.append(tp.text(f"#N canvas 80 80 {PANW+40} {PANH+40} test-panel 0;").rstrip("\n"))
m.add(f"#X restore 130 {by} pd test-panel;")
m.add(f"#X obj 270 {by} declare {DECL};")
m.add(f"#X text 20 {by+30} OCKM_GENERATOR. The screen above is the instrument (see CHANGELOG.md for the version). pd engine is the sound and the sequencer. pd test-panel is the old v0.12 panel \\, kept for testing. The screen needs pdlua (built into plugdata).;")
m.save("OCKM_GENERATOR.pd",f"#N canvas 40 40 {UIW} {UIH+80} 12;")


# ================= track gate: mute, solo and (for synths) level, with a short fade =================
# args: track, and "level" to listen to ockm-<track>-level (drums apply their level inside the voice, so they pass "nolevel")
q=P()
q.add("#X text 20 10 Track gate: mute \\, solo and level. Gain = (not muted) x (soloed \\, or nothing is soloed) x level. Fades over 10 ms so it never clicks.;")
i_=q.add("#X obj 20 60 inlet~;"); m_=q.add("#X obj 20 300 *~;"); o_=q.add("#X obj 20 340 outlet~;")
vals=[]
for j,(hook,d) in enumerate([(f"ockm-{D}1-mute",0),(f"ockm-{D}1-solo",0),("ockm-soloing",0),(f"ockm-{D}1-{D}2",1)]):
    x=200+j*130
    r=q.add(f"#X obj {x} 60 r {hook};"); t=q.add(f"#X obj {x} 85 t b f;"); fv=q.add(f"#X obj {x} 160 f {d};")
    q.con(r,0,t,0); q.con(t,1,fv,1); vals.append((t,fv))
tb=q.add("#X obj 200 125 t b b b b;")
ex=q.add(f"#X obj 200 200 expr (1-({D}f1!=0)) * if({D}f3>0 \\, ({D}f2!=0) \\, 1) * {D}f4;")
pk=q.add("#X obj 200 230 pack f 10;"); ln=q.add("#X obj 200 260 line~;")
lb=q.add("#X obj 560 125 loadbang;"); q.con(lb,0,tb,0)
for j,(t,fv) in enumerate(vals):
    q.con(t,0,tb,0); q.con(tb,j,fv,0); q.con(fv,0,ex,j)   # the hot inlet (mute) fires last
for c in [(ex,0,pk,0),(pk,0,ln,0),(ln,0,m_,1),(i_,0,m_,0),(m_,0,o_,0)]: q.con(*c)
q.save("seq/ockm-gate.pd","#N canvas 200 200 760 380 12;")

# ================= band-limited oscillators =================
# PolyBLEP: a phasor-based saw or square with the sharp edges smoothed over one sample, so the top end stays clean.
BLEP="if({t}<{D}v3 \\, ({t}/{D}v3)*2-({t}/{D}v3)*({t}/{D}v3)-1 \\, if({t}>1-{D}v3 \\, (({t}-1)/{D}v3)*(({t}-1)/{D}v3)+2*(({t}-1)/{D}v3)+1 \\, 0))"
for kind in ("saw","square"):
    q=P()
    q.add(f"#X text 20 10 Band-limited {kind}: frequency in \\, a clean {kind} out (PolyBLEP).;")
    i_=q.add("#X obj 30 50 inlet~;"); ph=q.add("#X obj 30 90 phasor~;"); o=q.add("#X obj 30 300 outlet~;")
    lb=q.add("#X obj 300 40 loadbang;"); sr=q.add("#X obj 300 65 samplerate~;"); dv=q.add("#X obj 200 130 /~ 44100;")
    sh=q.add("#X obj 120 130 +~ 0.5;"); wr=q.add("#X obj 120 160 wrap~;")
    if kind=="saw":
        ex=q.add("#X obj 30 220 expr~ 2*"+D+"v1-1-("+BLEP.format(t=D+"v1",D=D)+")+0*"+D+"v2;")   # 0*v2: keeps the middle inlet a signal inlet
    else:
        ex=q.add("#X obj 30 220 expr~ if("+D+"v1<0.5 \\, 1 \\, -1)+("+BLEP.format(t=D+"v1",D=D)+")-("+BLEP.format(t=D+"v2",D=D)+");")
    for c in [(i_,0,ph,0),(i_,0,dv,0),(lb,0,sr,0),(sr,0,dv,1),(ph,0,sh,0),(sh,0,wr,0),(ph,0,ex,0),(wr,0,ex,1),(dv,0,ex,2),(ex,0,o,0)]: q.con(*c)
    q.save(f"voices/ockm-bl{kind}.pd","#N canvas 200 200 600 340 12;")

# ================= bass core: shared note logic for every engine =================
# lead=True: the lead's version. Slides glide a little slower, and held notes get a delayed vibrato
def mono_core(fn,lead=False):
  q=P()
  q.add("#X text 20 10 Bass core: turns notes into pitch \\, filter envelope and volume signals. Shared by every bass engine.;")
  inl=q.add("#X obj 30 50 inlet;")
  ro=q.add("#X obj 30 80 route off;")
  offm=q.add("#X msg 30 110 0 20;")
  up=q.add("#X obj 120 110 unpack f f f f;")
  eqh=q.add("#X obj 420 150 == 0;")
  eqg=q.add("#X obj 300 150 == 0;")
  ap1=q.add("#X obj 210 150 + 1;")
  lvx=q.add(f"#X obj 270 80 expr {D}f1*0.4+0.6;")
  tn=q.add("#X obj 120 220 t b b b f;")
  spG=q.add("#X obj 330 270 spigot;"); spN=q.add("#X obj 420 270 spigot;")
  mG=q.add(f"#X msg 330 300 {D}1 {90 if lead else 60};"); mN=q.add(f"#X msg 420 300 {D}1;")
  pv=q.add("#X obj 420 340 vline~;")
  fl=q.add("#X obj 210 270 f 0.6;"); ma=q.add(f"#X msg 210 300 {D}1 3;")
  spR=q.add("#X obj 160 270 spigot;"); mR=q.add("#X msg 160 300 0 20 75;")
  av=q.add("#X obj 30 400 vline~;")
  spF=q.add("#X obj 120 270 spigot;"); fd=q.add("#X obj 120 300 f 200;"); mF=q.add(f"#X msg 120 330 1 \\, 0 {D}1;")
  ev=q.add("#X obj 600 340 vline~;"); es=q.add("#X obj 600 380 *~ 1;")
  dec=q.add("#X obj 700 50 inlet;")
  o0=q.add("#X obj 100 460 outlet~;"); o1=q.add("#X obj 400 460 outlet~;"); o2=q.add("#X obj 700 460 outlet~;")
  q.add("#X text 100 490 outlets: pitch (MIDI) / filter envelope (x2 on accents) / volume;")
  for c in [(inl,0,ro,0),(ro,0,offm,0),(offm,0,av,0),(ro,1,up,0),(up,3,eqh,0),(eqh,0,spR,1),(up,2,eqg,0),(up,2,spG,1),(eqg,0,spN,1),(eqg,0,spF,1),
            (up,1,ap1,0),(ap1,0,es,1),(up,1,lvx,0),(lvx,0,fl,1),(up,0,tn,0),(tn,3,spG,0),(tn,3,spN,0),(spG,0,mG,0),(spN,0,mN,0),(mG,0,pv,0),(mN,0,pv,0),
            (tn,2,fl,0),(fl,0,ma,0),(ma,0,av,0),(tn,1,spR,0),(spR,0,mR,0),(mR,0,av,0),(tn,0,spF,0),(spF,0,fd,0),(fd,0,mF,0),(mF,0,ev,0),(ev,0,es,0),
            (dec,0,fd,1),(pv,0,o0,0),(es,0,o1,0),(av,0,o2,0)]: q.con(*c)
  if lead:
      # vibrato: fades in after 350 ms on each fresh (non-slide) note, 5.5 Hz, about a fifth of a semitone
      vm=q.add("#X msg 520 300 0 \\, 1 500 350;"); vv=q.add("#X obj 520 340 vline~;"); vo=q.add("#X obj 620 340 osc~ 5.5;")
      vx=q.add("#X obj 520 370 *~;"); vd=q.add("#X obj 520 400 *~ 0.2;"); vp=q.add("#X obj 420 420 +~;")
      tv=q.add("#X obj 420 320 t f b;")
      q.C=[c for c in q.C if c!=(spN,0,mN,0) and c!=(pv,0,o0,0)]
      for c in [(spN,0,tv,0),(tv,0,mN,0),(tv,1,vm,0),(vm,0,vv,0),(vv,0,vx,0),(vo,0,vx,1),(vx,0,vd,0),(pv,0,vp,0),(vd,0,vp,1),(vp,0,o0,0)]: q.con(*c)
  q.save(fn,"#N canvas 150 150 900 520 12;")
mono_core("voices/ockm-mono-core.pd")
mono_core("voices/ockm-lead-core.pd",lead=True)

# ================= engines =================
def engine(fn,idx,title,build,core_name="ockm-mono-core",hook="engine",decay=None):
    q=P(); q.add(f"#X text 20 10 {title};")
    inl=q.add("#X obj 30 50 inlet;")
    sp=q.add("#X obj 30 80 spigot 1;")
    core=q.add(f"#X obj 30 120 {core_name};")
    ks=[q.add(f"#X obj {200+i*110} 50 inlet;") for i in range(4)]
    re=q.add(f"#X obj 700 50 r ockm-{D}1-{hook};"); eq=q.add(f"#X obj 700 80 == {idx};"); tf=q.add("#X obj 700 110 t f f;")
    sw=q.add("#X obj 700 170 switch~;"); s0=q.add("#X obj 760 140 sel 0;"); om=q.add("#X msg 760 170 off;")
    for c in [(inl,0,sp,0),(sp,0,core,0),(re,0,eq,0),(eq,0,tf,0),(tf,1,sw,0),(tf,0,s0,0),(s0,0,om,0),(om,0,core,0),(tf,0,sp,1)]: q.con(*c)
    dexp=decay or ("20*pow(100\\,"+D+"f1)")   # k4: decay in ms (kept out of the f-string: older Pythons refuse backslashes there)
    dx=q.add(f"#X obj 650 50 expr {dexp};"); q.con(ks[3],0,dx,0); q.con(dx,0,core,1)
    out=q.add("#X obj 30 560 outlet~;")
    build(q,core,ks,out)
    q.add("#X text 200 25 k1 / k2 / k3 / k4 (0 to 1) \\, k4 is always decay;")
    q.save(fn,"#N canvas 160 160 900 620 12;")

def acid(q,core,ks,out):
    mt=q.add("#X obj 30 200 mtof~;"); ph=q.add("#X obj 30 230 phasor~;"); m2=q.add("#X obj 30 260 *~ 2;"); s1=q.add("#X obj 30 290 -~ 1;")
    em=q.add("#X obj 300 200 *~ 2500;"); ad=q.add("#X obj 300 230 +~ 300;"); cl=q.add("#X obj 300 260 clip~ 30 12000;")
    bob=q.add("#X obj 30 340 bob~;"); am=q.add("#X obj 30 400 *~;"); g=q.add("#X obj 30 430 *~ 1.5;")
    k1=q.add(f"#X obj 200 140 expr 30*pow(2\\,9*{D}f1);"); k2=q.add("#X obj 310 140 * 3.9;"); k3=q.add("#X obj 420 140 * 8000;")
    for c in [(core,0,mt,0),(mt,0,ph,0),(ph,0,m2,0),(m2,0,s1,0),(s1,0,bob,0),(core,1,em,0),(em,0,ad,0),(ad,0,cl,0),(cl,0,bob,1),
              (bob,0,am,0),(core,2,am,1),(am,0,g,0),(g,0,out,0),(ks[0],0,k1,0),(k1,0,ad,1),(ks[1],0,k2,0),(k2,0,bob,2),(ks[2],0,k3,0),(k3,0,em,1)]: q.con(*c)
    q.add("#X text 200 110 k1 cutoff / k2 resonance / k3 envelope amount;")

def sub(q,core,ks,out):
    # sub and 808: a driven sine. The pitch drop is quick whatever the decay; with a long decay (k4 up) the note rings
    # on past the step like an 808 boom, with a short one it ends with the step
    em=q.add(f"#X obj 300 200 expr~ pow(min(1\\, max(0\\, {D}v1))\\, 12)*{D}f2;"); pl=q.add("#X obj 30 230 +~;"); mt=q.add("#X obj 30 260 mtof~;"); osc=q.add("#X obj 30 290 osc~;")
    gn=q.add("#X obj 30 320 *~ 1.6;"); th=q.add(f"#X obj 30 350 expr~ tanh({D}v1);"); lp=q.add("#X obj 30 380 lop~ 400;")
    # v0.98: k2 is weight, the second harmonic mixed in (body you hear on small speakers); the drive slider does the driving
    h2=q.add("#X obj 130 260 *~ 2;"); o2=q.add("#X obj 130 290 osc~;"); w2=q.add("#X obj 130 320 *~ 0;"); wsum=q.add("#X obj 30 335 +~;")
    ae=q.add(f"#X obj 200 380 expr~ max({D}v1\\, pow(min(1\\, max(0\\, {D}v2))\\, 1.5));")
    am=q.add("#X obj 30 410 *~;"); g=q.add("#X obj 30 440 *~ 0.9;")
    k1=q.add(f"#X obj 200 140 expr 60*pow(2\\,7*{D}f1);"); k2=q.add("#X obj 310 140 * 0.6;"); k3=q.add("#X obj 420 140 * 30;")
    for c in [(core,1,em,0),(core,0,pl,0),(em,0,pl,1),(pl,0,mt,0),(mt,0,osc,0),(osc,0,gn,0),(gn,0,wsum,0),(mt,0,h2,0),(h2,0,o2,0),(o2,0,w2,0),(w2,0,wsum,1),
              (wsum,0,th,0),(th,0,lp,0),(lp,0,am,0),
              (core,2,ae,0),(core,1,ae,1),(ae,0,am,1),(am,0,g,0),(g,0,out,0),
              (ks[0],0,k1,0),(k1,0,lp,1),(ks[1],0,k2,0),(k2,0,w2,1),(ks[2],0,k3,0),(k3,0,em,1)]: q.con(*c)
    q.add("#X text 200 110 k1 tone / k2 weight (the second harmonic) / k3 pitch drop on each note (up to 30 semitones \\, quick) / k4 decay: turn it up for an 808 that rings on;")

def fm(q,core,ks,out):
    mt=q.add("#X obj 30 200 mtof~;"); rm=q.add("#X obj 160 240 *~ 1;"); mo=q.add("#X obj 160 270 osc~;")
    ie=q.add("#X obj 300 200 *~ 2;"); ib=q.add("#X obj 300 230 +~ 1;"); i1=q.add("#X obj 160 300 *~;"); i2=q.add("#X obj 160 330 *~;")
    ad=q.add("#X obj 30 360 +~;"); car=q.add("#X obj 30 390 osc~;"); am=q.add("#X obj 30 420 *~;"); g=q.add("#X obj 30 450 *~ 0.9;")
    k1=q.add("#X obj 200 140 * 3;"); k2=q.add(f"#X obj 310 140 expr pow(2\\,int({D}f1*6.99)/2-1);"); k3=q.add("#X obj 420 140 * 8;")
    for c in [(core,0,mt,0),(mt,0,rm,0),(rm,0,mo,0),(core,1,ie,0),(ie,0,ib,0),(mo,0,i1,0),(ib,0,i1,1),(i1,0,i2,0),(rm,0,i2,1),
              (mt,0,ad,0),(i2,0,ad,1),(ad,0,car,0),(car,0,am,0),(core,2,am,1),(am,0,g,0),(g,0,out,0),
              (ks[0],0,k1,0),(k1,0,ib,1),(ks[1],0,k2,0),(k2,0,rm,1),(ks[2],0,k3,0),(k3,0,ie,1)]: q.con(*c)
    q.add("#X text 200 110 k1 brightness / k2 ratio (0.5 to 4) / k3 envelope on brightness;")

def reese(q,core,ks,out):
    mt=q.add("#X obj 30 200 mtof~;"); ua=q.add("#X obj 130 230 *~ 1.01;"); db=q.add("#X obj 230 230 *~ 0.99;")
    p1=q.add("#X obj 30 260 phasor~;"); p2=q.add("#X obj 130 260 phasor~;"); p3=q.add("#X obj 230 260 phasor~;")
    s1=q.add("#X obj 30 290 +~;"); s2=q.add("#X obj 30 315 +~;"); sc=q.add("#X obj 30 340 *~ 0.667;"); ce=q.add("#X obj 30 365 -~ 1;")
    em=q.add("#X obj 350 200 *~ 3000;"); ad=q.add("#X obj 350 230 +~ 300;"); cl=q.add("#X obj 350 260 clip~ 30 12000;")
    # v0.80: gentler resonance (0.6), a smaller envelope range (k3 up to 2500 Hz, it was 6000: the start of each note "breathed"),
    # and a steady sine sub under the saws, so the low end holds while the detuned saws beat and cancel above it
    bob=q.add("#X obj 30 400 bob~;"); rs=q.add("#X msg 450 300 0.6;"); lb=q.add("#X obj 450 270 loadbang;")
    so=q.add("#X obj 130 400 osc~;"); sg=q.add("#X obj 130 425 *~ 0.35;"); mx=q.add("#X obj 30 450 +~;")
    am=q.add("#X obj 30 475 *~;"); g=q.add("#X obj 30 500 *~ 1.9;")   # level-matched with the other bass engines
    k1=q.add(f"#X obj 200 140 expr 40*pow(2\\,8*{D}f1);"); k2=q.add(f"#X obj 310 140 expr 0.003+0.02*{D}f1 \; 0.003+0.02*{D}f1;")
    up=q.add("#X obj 310 170 + 1;"); dn=q.add("#X obj 380 170 expr 1-$f1;".replace("$","\\$")); k3=q.add("#X obj 420 140 * 2500;")
    for c in [(core,0,mt,0),(mt,0,p1,0),(mt,0,ua,0),(mt,0,db,0),(ua,0,p2,0),(db,0,p3,0),(p1,0,s1,0),(p2,0,s1,1),(s1,0,s2,0),(p3,0,s2,1),
              (s2,0,sc,0),(sc,0,ce,0),(ce,0,bob,0),(core,1,em,0),(em,0,ad,0),(ad,0,cl,0),(cl,0,bob,1),(lb,0,rs,0),(rs,0,bob,2),
              (mt,0,so,0),(so,0,sg,0),(bob,0,mx,0),(sg,0,mx,1),
              (mx,0,am,0),(core,2,am,1),(am,0,g,0),(g,0,out,0),(ks[0],0,k1,0),(k1,0,ad,1),(ks[1],0,k2,0),(k2,0,up,0),(k2,1,dn,0),
              (up,0,ua,1),(dn,0,db,1),(ks[2],0,k3,0),(k3,0,em,1)]: q.con(*c)
    q.add("#X text 200 110 k1 cutoff / k2 detune (width) / k3 envelope amount;")

def pluck(q,core,ks,out):
    # rings out and fades on its own (ignores the 303-style gate), saw/square blend, gentle filter, sub octave for weight
    mt=q.add("#X obj 30 200 mtof~;"); ph=q.add("#X obj 30 230 phasor~;")
    saw=q.add("#X obj 30 260 *~ 2;"); saw1=q.add("#X obj 30 285 -~ 1;")
    sq=q.add(f"#X obj 130 260 expr~ ({D}v1>0.5)*2-1;")
    bl=q.add(f"#X obj 30 320 expr~ {D}v1*(1-{D}f3)+{D}v2*{D}f3;")
    sub_=q.add("#X obj 250 260 *~ 0.5;"); so=q.add("#X obj 250 290 osc~;"); sg=q.add("#X obj 250 320 *~ 0.35;")
    ec=q.add("#X obj 450 200 clip~ 0 1;"); e2=q.add("#X obj 450 230 *~;")
    em=q.add("#X obj 450 270 *~ 4000;"); ad=q.add("#X obj 450 300 +~ 300;"); cl=q.add("#X obj 450 330 clip~ 30 12000;")
    bob=q.add("#X obj 30 370 bob~;"); rs=q.add("#X msg 600 330 0.6;"); lb=q.add("#X obj 600 300 loadbang;")
    mix=q.add("#X obj 30 410 +~;"); am=q.add("#X obj 30 440 *~;"); g=q.add("#X obj 30 470 *~ 0.8;")
    k1=q.add(f"#X obj 200 140 expr 80*pow(2\\,7*{D}f1);"); k3=q.add("#X obj 420 140 * 8000;")
    for c in [(core,0,mt,0),(mt,0,ph,0),(ph,0,saw,0),(saw,0,saw1,0),(ph,0,sq,0),(saw1,0,bl,0),(sq,0,bl,1),(ks[1],0,bl,2),
              (mt,0,sub_,0),(sub_,0,so,0),(so,0,sg,0),
              (core,1,ec,0),(ec,0,e2,0),(ec,0,e2,1),(e2,0,em,0),(em,0,ad,0),(ad,0,cl,0),(cl,0,bob,1),(lb,0,rs,0),(rs,0,bob,2),
              (bl,0,bob,0),(bob,0,mix,0),(sg,0,mix,1),(mix,0,am,0),(ec,0,am,1),(am,0,g,0),(g,0,out,0),
              (ks[0],0,k1,0),(k1,0,ad,1),(ks[2],0,k3,0),(k3,0,em,1)]: q.con(*c)
    q.add("#X text 200 110 k1 brightness / k2 saw to square / k3 filter snap. Notes ring out and fade over the decay time (k4) \\, with a sub an octave down.;")

engine("voices/ockm-mono-acid.pd",0,"Acid engine: saw wave into a resonant filter",acid)
engine("voices/ockm-mono-sub.pd",1,"Sub engine: a driven sine wave with a pitch drop. Deep and clean",sub)
engine("voices/ockm-mono-fm.pd",2,"FM engine: one sine wave bending another. Punchy and metallic",fm)
engine("voices/ockm-mono-reese.pd",3,"Reese engine: three detuned saws beating against each other. Dark and wide",reese)
# v0.98: pluck is gone (analogue with a long decay rings out the same way); old projects move to analogue

def svf(Q):
    """A resonant low-pass you can sweep with a signal, flat (unity gain) from the bottom to the top: the topology-preserving
    state-variable filter, one sample at a time. Inlets: audio, cutoff in Hz (signal), sample rate. Outlet 3 is the low-pass."""
    k=round(1/Q,4)
    g=f"tan(3.14159265*min({D}x2[0]\\, 0.45*{D}f3)/max({D}f3\\, 1))"
    a1=f"(1/(1+{g}*({g}+{k})))"; a2=f"({g}*{a1})"; a3=f"({g}*{a2})"
    v3=f"({D}x1[0]-{D}y2[-1])"
    y1=f"2*({a1}*{D}y1[-1] + {a2}*{v3}) - {D}y1[-1]"
    v2=f"({D}y2[-1] + {a2}*{D}y1[-1] + {a3}*{v3})"
    y2=f"2*{v2} - {D}y2[-1]"
    return f"fexpr~ {y1} \\; {y2} \\; {v2}"

def analogue(q,core,ks,out):
    # the workhorse mono bass (Minimoog, SH-101, Pro-One): saw blending to square, a square sub an octave down, two
    # resonant low-pass stages (24 dB) opened by the filter envelope, a little drive. Plain Pd only, no bob~.
    # v0.72: the filter is a state-variable filter (svf below) with unity gain all the way up: vcf~ got quieter as the
    # cutoff rose and went silent above a quarter of the sample rate
    mt=q.add("#X obj 30 200 mtof~;"); sw=q.add("#X obj 30 230 ockm-blsaw;"); sq=q.add("#X obj 150 230 ockm-blsquare;")
    hz=q.add("#X obj 270 200 *~ 0.5;"); sb=q.add("#X obj 270 230 ockm-blsquare;")
    mx=q.add(f"#X obj 30 270 expr~ {D}v1*(1-{D}f4) - {D}v2*{D}f4*0.8 - {D}v3*0.3;")   # the squares flipped so their fundamental adds to the saw's, not cancels
    co=q.add(f"#X obj 450 270 expr~ min(18000\\, max(30\\, {D}f2*(1 + {D}v1*{D}f3)));")
    f1=q.add(f"#X obj 30 310 {svf(1.1)};"); f2=q.add(f"#X obj 30 340 {svf(0.8)};")
    srn=q.add("#X obj 600 230 loadbang;"); srs=q.add("#X obj 600 255 samplerate~;")
    dc=q.add("#X obj 30 290 hip~ 15;")   # the oscillators carry some DC: take it out before the filter (which passes DC)
    dr=q.add(f"#X obj 30 375 expr~ tanh(1.5*{D}v1)/tanh(1.5);"); am=q.add("#X obj 30 405 *~;"); g=q.add("#X obj 30 435 *~ 0.55;")
    k1=q.add(f"#X obj 200 140 expr 60*pow(2\\,7.5*{D}f1);"); k3=q.add("#X obj 420 140 * 10;")
    # v0.98: past decay 0.6 the note rings on after its step and fades with the filter envelope (as sub does), so a long
    # decay is a pluck; below it the step ends the note as before
    rg=q.add(f"#X obj 560 140 expr min(1\\, max(0\\, ({D}f1-0.6)*4));")
    ra=q.add(f"#X obj 200 405 expr~ max({D}v1\\, {D}f3*pow(min(1\\, max(0\\, {D}v2))\\, 1.5));")
    for c in [(core,0,mt,0),(mt,0,sw,0),(mt,0,sq,0),(mt,0,hz,0),(hz,0,sb,0),(sw,0,mx,0),(sq,0,mx,1),(sb,0,mx,2),
              (core,1,co,0),(co,0,f1,1),(co,0,f2,1),(mx,0,dc,0),(dc,0,f1,0),(f1,2,f2,0),(f2,2,dr,0),(srn,0,srs,0),(srs,0,f1,2),(srs,0,f2,2),(dr,0,am,0),(core,2,ra,0),(core,1,ra,1),(ra,0,am,1),(am,0,g,0),(g,0,out,0),
              (ks[0],0,k1,0),(k1,0,co,1),(ks[1],0,mx,3),(ks[2],0,k3,0),(k3,0,co,2),(ks[3],0,rg,0),(rg,0,ra,2)]: q.con(*c)
    q.add("#X text 200 110 k1 cutoff / k2 saw to square / k3 filter envelope (how far each note opens it) / k4 decay. With a square sub an octave down.;")

def donk(q,core,ks,out):
    # donk and organ bass (bassline house \\, UK garage \\, the Korg M1 organ bass): a hollow tone with a quick pitch
    # bounce down onto the note, rings out over its own decay. k1 brightness (more of the organ harmonics), k2 bounce,
    # k3 hollow (odd harmonics: woodier), k4 decay
    pe=q.add(f"#X obj 300 200 expr~ pow(min(1\\, max(0\\, {D}v1))\\, 12)*{D}f2;"); pl=q.add("#X obj 30 230 +~;"); mt=q.add("#X obj 30 260 mtof~;")
    o1=q.add("#X obj 30 290 osc~;"); m2=q.add("#X obj 150 260 *~ 2;"); o2=q.add("#X obj 150 290 osc~;"); m3=q.add("#X obj 270 260 *~ 3;"); o3=q.add("#X obj 270 290 osc~;")
    sq=q.add("#X obj 390 290 ockm-blsquare;"); sl=q.add("#X obj 390 320 lop~ 1200;")
    mx=q.add(f"#X obj 30 350 expr~ {D}v1 + {D}f5*(0.5*{D}v2 + 0.3*{D}v3) + {D}f6*0.7*{D}v4;")
    th=q.add(f"#X obj 30 380 expr~ tanh(1.4*{D}v1)/tanh(1.4);")
    ae=q.add(f"#X obj 200 380 expr~ pow(min(1\\, max(0\\, {D}v1))\\, 1.3);"); am=q.add("#X obj 30 410 *~;"); g=q.add("#X obj 30 440 *~ 0.8;")
    k2=q.add("#X obj 310 140 * 14;")
    for c in [(core,1,pe,0),(core,0,pl,0),(pe,0,pl,1),(pl,0,mt,0),(mt,0,o1,0),(mt,0,m2,0),(m2,0,o2,0),(mt,0,m3,0),(m3,0,o3,0),(mt,0,sq,0),(sq,0,sl,0),
              (o1,0,mx,0),(o2,0,mx,1),(o3,0,mx,2),(sl,0,mx,3),(mx,0,th,0),(th,0,am,0),(core,1,ae,0),(ae,0,am,1),(am,0,g,0),(g,0,out,0),
              (ks[0],0,mx,4),(ks[1],0,k2,0),(k2,0,pe,1),(ks[2],0,mx,5)]: q.con(*c)
    q.add("#X text 200 110 k1 brightness (organ harmonics) / k2 bounce (pitch drop onto the note) / k3 hollow (woodier) / k4 decay. Rings out on its own.;")

engine("voices/ockm-mono-analogue.pd",5,"Analogue engine: saw to square with a sub \\, through a resonant 24 dB low-pass. The workhorse house and techno bass (the default)",analogue)
engine("voices/ockm-mono-donk.pd",6,"Donk engine: a hollow tone that bounces down onto each note and rings out. Bassline house \\, garage \\, M1 organ bass",donk,
       decay=f"120*pow(12\\,{D}f1)")   # its decay never gets shorter than a short donk (120 ms) and goes up to about 1.4 s

# ================= bass wrapper =================
q=P()
q.add("#X text 20 10 Mono synth (bass or lead): six engines \\, one plays at a time (ockm-<track>-engine 0 to 5). Knobs k1-k4 and drive come in on hooks.;")
inl=q.add("#X obj 30 50 inlet;")
ks=[q.add(f"#X obj {200+i*130} 50 r ockm-{D}1-k{i+1}-m;") for i in range(4)]
names=["acid","sub","fm","reese","analogue","donk"]   # each knows its own engine number (4, pluck, retired in v0.98)
eng=[q.add(f"#X obj {30+i*130} 130 ockm-mono-{n} {D}1;") for i,n in enumerate(names)]
sm=q.add("#X obj 30 200 +~;")
for i,e in enumerate(eng):
    q.con(inl,0,e,0)
    for j,k in enumerate(ks): q.con(k,0,e,j+1)
    q.con(e,0,sm,0)
rd=q.add(f"#X obj 400 200 r ockm-{D}1-drive;"); dx=q.add(f"#X obj 400 230 expr 1+{D}f1*9;")
th=q.add(f"#X obj 30 260 expr~ if({D}f2>1.001 \\, tanh({D}v1*{D}f2)/sqrt({D}f2) \\, {D}v1);"); out=q.add("#X obj 30 300 outlet~;")   # drive 0 is clean
q.add("#X text 400 260 drive: 0 clean \\, 1 heavy;")
for c in [(rd,0,dx,0),(dx,0,th,1),(sm,0,th,0),(th,0,out,0)]: q.con(*c)
q.save("voices/ockm-mono.pd","#N canvas 140 140 900 340 12;")

# ================= lead engines =================
# The lead has its own engines (ockm-lead-engine). The order keeps old projects sensible: acid stays acid (0),
# FM becomes DX (2), and the old default pluck (4) becomes Mini.
# v0.98: acid (0) and juno (1) are retired (analogue with emphasis, and analogue with the chorus, do them); supersaw is 5.
# The numbers stay as they were, so saved projects keep their engine; the screen moves retired ones on
LEAD_ENGINES=[("dx",2),("sync",3),("mini",4),("supersaw",5)]
def lead_engine(name,idx,title,build): engine(f"voices/ockm-lead-{name}.pd",idx,title,build,core_name="ockm-lead-core",hook="voice")

def filt_env(q,core,ks,lo,span,x=450,y=200,kidx=2,cmin=30,cmax=14000,amt=3000):
    """core's filter envelope -> cutoff in Hz: k1 sets the base (lo..lo*2^span), k3 the envelope amount. Returns the cutoff signal."""
    em=q.add(f"#X obj {x} {y} *~ {amt};"); ad=q.add(f"#X obj {x} {y+30} +~ 300;"); cl=q.add(f"#X obj {x} {y+60} clip~ {cmin} {cmax};")
    k1=q.add(f"#X obj 200 140 expr {lo}*pow(2\\,{span}*{D}f1);")
    for c in [(core,1,em,0),(em,0,ad,0),(ad,0,cl,0),(ks[0],0,k1,0),(k1,0,ad,1)]: q.con(*c)
    if kidx is not None:
        k3=q.add("#X obj 420 140 * 7000;"); q.con(ks[kidx],0,k3,0); q.con(k3,0,em,1)
    return cl

def lead_acid(q,core,ks,out):
    # the 303, voiced to cut through: more resonance and a little grit after the filter
    mt=q.add("#X obj 30 200 mtof~;"); ph=q.add("#X obj 30 230 phasor~;"); m2=q.add("#X obj 30 260 *~ 2;"); s1=q.add("#X obj 30 290 -~ 1;")
    cut=filt_env(q,core,ks,60,8)
    bob=q.add("#X obj 30 340 bob~;"); k2=q.add(f"#X obj 310 140 expr 1+3*{D}f1;")
    dr=q.add(f"#X obj 30 370 expr~ tanh({D}v1*1.8)/1.3;"); am=q.add("#X obj 30 400 *~;"); g=q.add("#X obj 30 430 *~ 1.1;")
    for c in [(core,0,mt,0),(mt,0,ph,0),(ph,0,m2,0),(m2,0,s1,0),(s1,0,bob,0),(cut,0,bob,1),(ks[1],0,k2,0),(k2,0,bob,2),
              (bob,0,dr,0),(dr,0,am,0),(core,2,am,1),(am,0,g,0),(g,0,out,0)]: q.con(*c)
    q.add("#X text 200 110 k1 cutoff / k2 resonance / k3 envelope amount;")

def lead_mini(q,core,ks,out):
    # Minimoog-style: two saws a few cents apart plus a square an octave down, driven into a ladder filter
    mt=q.add("#X obj 30 200 mtof~;"); o1=q.add("#X obj 30 230 ockm-blsaw;")
    d2=q.add("#X obj 140 200 *~ 1.0035;"); o2=q.add("#X obj 140 230 ockm-blsaw;")
    d3=q.add("#X obj 250 200 *~ 0.5;"); o3=q.add("#X obj 250 230 ockm-blsquare;"); g3=q.add("#X obj 250 260 *~ 0.6;")
    m1=q.add("#X obj 30 270 +~;"); m2=q.add("#X obj 30 295 +~;")
    pre=q.add(f"#X obj 30 320 expr~ tanh({D}v1*0.7);")
    cut=filt_env(q,core,ks,50,8)
    bob=q.add("#X obj 30 360 bob~;"); k2=q.add(f"#X obj 310 140 expr 0.2+3.4*{D}f1;")
    am=q.add("#X obj 30 400 *~;"); g=q.add("#X obj 30 430 *~ 0.95;")
    for c in [(core,0,mt,0),(mt,0,o1,0),(mt,0,d2,0),(d2,0,o2,0),(mt,0,d3,0),(d3,0,o3,0),(o3,0,g3,0),
              (o1,0,m1,0),(o2,0,m1,1),(m1,0,m2,0),(g3,0,m2,1),(m2,0,pre,0),(pre,0,bob,0),(cut,0,bob,1),(ks[1],0,k2,0),(k2,0,bob,2),
              (bob,0,am,0),(core,2,am,1),(am,0,g,0),(g,0,out,0)]: q.con(*c)
    q.add("#X text 200 110 k1 cutoff / k2 emphasis / k3 contour (filter envelope);")

def lead_juno(q,core,ks,out):
    # Juno-style: saw plus a pulse whose width drifts slowly, a square sub, a soft filter, then the chorus
    mt=q.add("#X obj 30 200 mtof~;"); sw=q.add("#X obj 30 230 ockm-blsaw;")
    ph=q.add("#X obj 140 230 phasor~;"); lf=q.add("#X obj 260 170 osc~ 0.6;")
    pwk=q.add(f"#X obj 310 140 expr 0.45*{D}f1;"); lfa=q.add("#X obj 260 200 *~ 0;"); wd=q.add("#X obj 260 230 +~ 0.5;")
    pu=q.add(f"#X obj 140 260 expr~ ({D}v1<{D}v2)*2-1;")
    sbh=q.add("#X obj 380 200 *~ 0.5;"); sb=q.add("#X obj 380 230 ockm-blsquare;"); sbg=q.add("#X obj 380 260 *~ 0.35;")
    m1=q.add("#X obj 30 290 +~;"); m2=q.add("#X obj 30 315 +~;"); sc=q.add("#X obj 30 340 *~ 0.45;")
    cut=filt_env(q,core,ks,80,7,x=600,kidx=None,amt=1800)   # k3 is the chorus here, so the envelope amount is fixed
    bob=q.add("#X obj 30 370 bob~;"); rs=q.add("#X msg 500 330 0.5;"); lb=q.add("#X obj 500 300 loadbang;")
    am=q.add("#X obj 30 400 *~;")
    # chorus: two delay taps swept by slow sines, mixed with the dry sound. k3: 0 off, up to 0.5 = I, above = II (faster, deeper)
    dw=q.add(f"#X obj 30 440 delwrite~ {D}0-ch 30;")
    ck=q.add(f"#X obj 600 140 expr if({D}f1<0.05 \\, 0 \\, 1) \; if({D}f1<0.5 \\, 0.5 \\, 0.83) \; if({D}f1<0.5 \\, 1.8 \\, 2.6);")
    cr=q.add("#X obj 700 400 osc~ 0.5;"); cd=q.add("#X obj 700 430 *~ 1.8;"); c1=q.add("#X obj 700 460 +~ 6;"); c2n=q.add("#X obj 820 430 *~ -1;"); c2=q.add("#X obj 820 460 +~ 6;")
    v1=q.add(f"#X obj 700 490 vd~ {D}0-ch;"); v2=q.add(f"#X obj 820 490 vd~ {D}0-ch;"); wm=q.add("#X obj 700 520 +~;"); wg=q.add("#X obj 700 545 *~ 0;")
    mix=q.add("#X obj 30 500 +~;"); g=q.add("#X obj 30 530 *~ 1.25;")
    for c in [(core,0,mt,0),(mt,0,sw,0),(mt,0,ph,0),(lf,0,lfa,0),(ks[1],0,pwk,0),(pwk,0,lfa,1),(lfa,0,wd,0),(ph,0,pu,0),(wd,0,pu,1),
              (mt,0,sbh,0),(sbh,0,sb,0),(sb,0,sbg,0),(sw,0,m1,0),(pu,0,m1,1),(m1,0,m2,0),(sbg,0,m2,1),(m2,0,sc,0),
              (sc,0,bob,0),(cut,0,bob,1),(lb,0,rs,0),(rs,0,bob,2),(bob,0,am,0),(core,2,am,1),(am,0,dw,0),
              (ks[2],0,ck,0),(ck,1,cr,0),(ck,2,cd,1),(cr,0,cd,0),(cd,0,c2n,0),(cd,0,c1,0),(c2n,0,c2,0),(c1,0,v1,0),(c2,0,v2,0),
              (v1,0,wm,0),(v2,0,wm,1),(wm,0,wg,0),(ck,0,wg,1),(am,0,mix,0),(wg,0,mix,1),(mix,0,g,0),(g,0,out,0)]: q.con(*c)
    q.add("#X text 200 110 k1 cutoff / k2 pulse width movement / k3 chorus: off \\, I \\, II;")

def lead_dx(q,core,ks,out):
    # DX7-style two-operator FM. Notes ring and fade (an electric piano / bell \\, not a held organ).
    # k2 picks the character: tine (1:1) \\, reed (2:1) \\, bell (3.5:1) \\, glass (7:1). Accents hit brighter.
    mt=q.add("#X obj 30 200 mtof~;")
    ec=q.add("#X obj 450 200 clip~ 0 2;"); amp=q.add("#X obj 450 230 clip~ 0 1;")
    rt=q.add(f"#X obj 310 140 expr if({D}f1<0.25 \\, 1 \\, if({D}f1<0.5 \\, 2 \\, if({D}f1<0.75 \\, 3.5 \\, 7)));")
    rm=q.add("#X obj 160 230 *~ 1;"); mo=q.add("#X obj 160 260 osc~;")
    bi=q.add(f"#X obj 200 170 expr 0.3+4*{D}f1;"); ix=q.add("#X obj 300 260 *~ 1;")
    i1=q.add("#X obj 160 300 *~;"); i2=q.add("#X obj 160 330 *~;")
    ad=q.add("#X obj 30 360 +~;"); car=q.add("#X obj 30 390 osc~;")
    dt=q.add(f"#X obj 600 140 expr 1+0.006*{D}f1;"); mt2=q.add("#X obj 30 250 *~ 1;"); ad2=q.add("#X obj 130 360 +~;"); car2=q.add("#X obj 130 390 osc~;")
    sm=q.add("#X obj 30 420 +~;"); sc=q.add("#X obj 30 445 *~ 0.5;")
    am=q.add("#X obj 30 470 *~;"); am2=q.add("#X obj 30 495 *~;"); g=q.add("#X obj 30 520 *~ 0.65;")
    for c in [(core,0,mt,0),(core,1,ec,0),(ec,0,amp,0),(ks[1],0,rt,0),(rt,0,rm,1),(mt,0,rm,0),(rm,0,mo,0),
              (ks[0],0,bi,0),(bi,0,ix,1),(ec,0,ix,0),(mo,0,i1,0),(ix,0,i1,1),(i1,0,i2,0),(rm,0,i2,1),
              (mt,0,ad,0),(i2,0,ad,1),(ad,0,car,0),(ks[2],0,dt,0),(dt,0,mt2,1),(mt,0,mt2,0),(mt2,0,ad2,0),(i2,0,ad2,1),(ad2,0,car2,0),
              (car,0,sm,0),(car2,0,sm,1),(sm,0,sc,0),(sc,0,am,0),(amp,0,am,1),(am,0,am2,0),(core,2,am2,1),(am2,0,g,0),(g,0,out,0)]: q.con(*c)
    q.add("#X text 200 110 k1 brightness / k2 character: tine \\, reed \\, bell \\, glass / k3 detune (a second voice beside it);")

def lead_sync(q,core,ks,out):
    # hard sync: a second saw restarts every cycle of the first, so its pitch shows up as a sweeping tone. The envelope sweeps it
    mt=q.add("#X obj 30 200 mtof~;"); ph=q.add("#X obj 30 230 phasor~;")
    sr=q.add(f"#X obj 200 170 expr 1+3*{D}f1;"); se=q.add("#X obj 300 230 *~ 4;"); sa=q.add("#X obj 300 260 +~ 1;")
    sy=q.add(f"#X obj 30 290 expr~ fmod({D}v1*{D}v2 \\, 1)*2-1;")
    lp=q.add("#X obj 30 330 lop~ 6000;"); k2=q.add(f"#X obj 310 140 expr 800*pow(2\\,4*{D}f1);")
    k3=q.add("#X obj 420 140 * 6;"); am=q.add("#X obj 30 400 *~;"); g=q.add("#X obj 30 430 *~ 0.55;")
    for c in [(core,0,mt,0),(mt,0,ph,0),(core,1,se,0),(ks[2],0,k3,0),(k3,0,se,1),(se,0,sa,0),(ks[0],0,sr,0),(sr,0,sa,1),
              (ph,0,sy,0),(sa,0,sy,1),(sy,0,lp,0),(ks[1],0,k2,0),(k2,0,lp,1),(lp,0,am,0),(core,2,am,1),(am,0,g,0),(g,0,out,0)]: q.con(*c)
    q.add("#X text 200 110 k1 sync amount / k2 tone / k3 sweep (envelope on the sync);")

def lead_supersaw(q,core,ks,out):
    # v0.98: seven saws. k1 spread: at 0 one saw, at 1 the trance and peak-time stack (the outer pair about 25 cents out).
    # k2 cutoff (with the filter envelope on top, which sweeps it like a hoover when the decay is long), k3 drift (each saw
    # wanders a little on its own slow wobble), k4 decay
    mt=q.add("#X obj 30 200 mtof~;")
    spr=q.add(f"#X obj 600 140 expr {D}f1;"); mix=q.add("#X obj 30 330 +~;")
    det=[-1,-0.62,-0.3,0,0.3,0.62,1]
    for j,dv in enumerate(det):
        x=30+j*95
        if dv==0:
            o=q.add(f"#X obj {x} 260 ockm-blsaw;"); q.con(mt,0,o,0); q.con(o,0,mix,0); continue
        # pitch = f * (1 + spread*0.0145*dv + drift*0.004*wobble)
        wb=q.add(f"#X obj {x} 170 osc~ {round(0.07+0.05*j,3)};"); wd=q.add(f"#X obj {x} 190 *~ 0;")
        ex=q.add(f"#X obj {x} 215 expr~ {D}v1*(1 + {D}f2*{round(0.0145*dv,5)} + {D}v3*0.004);")
        o=q.add(f"#X obj {x} 260 ockm-blsaw;"); ga=q.add(f"#X obj {x} 290 *~ 0;")
        for c in [(wb,0,wd,0),(mt,0,ex,0),(wd,0,ex,2),(ex,0,o,0),(o,0,ga,0),(ga,0,mix,0),(spr,0,ex,1),(spr,0,ga,1)]: q.con(*c)
        q.con(ks[2],0,wd,1)
    q.con(ks[0],0,spr,0)
    nrm=q.add(f"#X obj 700 170 expr 1/sqrt(1+6*{D}f1*{D}f1);"); ng=q.add("#X obj 30 360 *~ 1;")
    q.con(ks[0],0,nrm,0); q.con(nrm,0,ng,1); q.con(mix,0,ng,0)
    em=q.add("#X obj 450 400 *~ 5000;"); co=q.add(f"#X obj 450 430 expr~ min(16000\\, max(60\\, {D}f2 + {D}v1));")
    k2=q.add(f"#X obj 310 140 expr 200*pow(2\\,6*{D}f1);")
    f1=q.add("#X obj 30 400 vcf~ 1.2;"); f2=q.add("#X obj 30 430 lop~ 9000;")
    am=q.add("#X obj 30 460 *~;"); g=q.add("#X obj 30 490 *~ 0.6;")
    for c in [(core,0,mt,0),(core,1,em,0),(em,0,co,0),(ks[1],0,k2,0),(k2,0,co,1),(ng,0,f1,0),(co,0,f1,1),(f1,1,f2,0),
              (f2,0,am,0),(core,2,am,1),(am,0,g,0),(g,0,out,0)]: q.con(*c)
    q.add("#X text 200 110 k1 spread (one saw to seven) / k2 cutoff / k3 drift / k4 decay;")

for nm,fnb,title in [
        ("dx",lead_dx,"DX lead: two-operator FM. Electric piano \\, reed \\, bell or glass"),
        ("sync",lead_sync,"Sync lead: a hard-synced saw that sweeps with the envelope. Tech house and electro"),
        ("mini",lead_mini,"Analogue lead (was mini): three oscillators driven into a ladder filter. Big and warm"),
        ("supersaw",lead_supersaw,"Supersaw lead: seven detuned saws. One saw to a trance stack \\, a hoover with a long decay")]:
    lead_engine(nm,dict(LEAD_ENGINES)[nm],title,fnb)

# ================= lead wrapper =================
q=P()
q.add("#X text 20 10 Lead synth: its own engines \\, one plays at a time (ockm-lead-engine: "+" ".join(f"{i} {n}" for n,i in LEAD_ENGINES)+"). Glides on slide steps and adds vibrato to held notes.;")
inl=q.add("#X obj 30 50 inlet;")
ks=[q.add(f"#X obj {200+i*130} 50 r ockm-{D}1-k{i+1}-m;") for i in range(4)]
eng=[q.add(f"#X obj {30+i*130} 130 ockm-lead-{n} {D}1;") for i,(n,_) in enumerate(LEAD_ENGINES)]
sm=q.add("#X obj 30 200 +~;")
for i,e in enumerate(eng):
    q.con(inl,0,e,0)
    for j,k in enumerate(ks): q.con(k,0,e,j+1)
    q.con(e,0,sm,0)
# engine number -> the engines (anything past the last engine plays the last one)
rv=q.add(f"#X obj 800 50 r ockm-{D}1-engine;"); mn=q.add(f"#X obj 800 80 min {max(i for _,i in LEAD_ENGINES)};"); sv=q.add(f"#X obj 800 110 s ockm-{D}1-voice;")
q.con(rv,0,mn,0); q.con(mn,0,sv,0)
rd=q.add(f"#X obj 400 200 r ockm-{D}1-drive;"); dx=q.add(f"#X obj 400 230 expr 1+{D}f1*9;")
th=q.add(f"#X obj 30 260 expr~ if({D}f2>1.001 \\, tanh({D}v1*{D}f2)/sqrt({D}f2) \\, {D}v1);"); out=q.add("#X obj 30 300 outlet~;")
for c in [(rd,0,dx,0),(dx,0,th,1),(sm,0,th,0),(th,0,out,0)]: q.con(*c)
q.save("voices/ockm-lead.pd","#N canvas 140 140 900 340 12;")

# ================= master effects =================
q=P()
q.add("#X text 20 10 Master effects: reverb and delay returns \\, DJ filter \\, drive \\, tempo-synced delay \\, then a soft limiter.;")
inl0=q.add("#X obj 30 30 inlet~;"); ctch=q.add("#X obj 150 30 catch~ ockm-revbus;"); verb=q.add("#X obj 150 55 ockm-verb;"); vm=q.add("#X obj 150 75 *~ 0.3;")
rvm=q.add("#X obj 300 30 r ockm-verb-mix;"); pre=q.add("#X obj 30 70 +~;"); inl=q.add("#X obj 30 90 +~;")
dcat=q.add("#X obj 200 300 catch~ ockm-dlybus;")
for c in [(inl0,0,pre,0),(ctch,0,verb,0),(verb,0,vm,0),(vm,0,pre,1),(rvm,0,vm,1),(pre,0,inl,0)]: q.con(*c)
inl2=q.add("#X obj 30 100 +~;")   # plus the dub throw's echoes
h1=q.add("#X obj 30 90 hip~ 10;"); h2=q.add("#X obj 30 115 hip~ 10;"); l1=q.add("#X obj 30 140 lop~ 20000;"); l2=q.add("#X obj 30 165 lop~ 20000;")
rf0=q.add("#X obj 300 20 r ockm-filter;"); pkf=q.add("#X obj 300 40 pack f 25;"); rgl=q.add("#X obj 400 20 r ockm-filter-glide;")
rf=q.add("#X obj 300 60 line 0 5;"); tfn=q.add("#X obj 300 70 t f f;"); sfn=q.add("#X obj 420 70 s ockm-filter-now;")
q.con(rf0,0,pkf,0); q.con(pkf,0,rf,0); q.con(rgl,0,rf,0); q.con(rf,0,tfn,0); q.con(tfn,1,sfn,0)
# build rise: ockm-rise-now (0 to 1) lifts the high-pass, never lower than the filter setting already has it
rrn=q.add("#X obj 520 20 r ockm-rise-now;"); prn=q.add("#X obj 520 40 list append 100;"); lrn=q.add("#X obj 520 60 line 0 10;"); trn=q.add("#X obj 520 80 t b f;")   # "value" glides over 100 ms; "value ms" sets the time
prs=q.add("#X obj 600 40 list split 2;")
rmx_=q.add(f"#X obj 300 75 expr if({D}f2>0.001 \\, max({D}f1 \\, {D}f2) \\, {D}f1);")
for c in [(rrn,0,prn,0),(prn,0,prs,0),(prs,0,lrn,0),(lrn,0,trn,0),(trn,1,rmx_,1),(trn,0,rmx_,0)]: q.con(*c)
fx=q.add(f"#X obj 300 80 expr if({D}f1>0 \\, 20*pow(2\\,{D}f1*9.6) \\, 10) \; if({D}f1<0 \\, 20000*pow(2\\,{D}f1*9.6) \\, 20000);")
rdv=q.add("#X obj 300 200 r ockm-drive;"); dvx=q.add(f"#X obj 300 230 expr 1+{D}f1*9;")
th=q.add(f"#X obj 30 230 expr~ if({D}f2>1.001 \\, tanh({D}v1*{D}f2)/sqrt({D}f2) \\, {D}v1);")   # drive 0 is clean
dw=q.add(f"#X obj 200 330 delwrite~ {D}0-dly 4000;"); dr=q.add(f"#X obj 200 290 delread~ {D}0-dly 363;")
fb=q.add("#X obj 200 360 *~ 0.4;"); mx=q.add("#X obj 200 400 *~ 0;")
rst=q.add("#X obj 500 250 r ockm-stepms;"); rsteps=q.add("#X obj 620 250 r ockm-delay-steps;"); dtm=q.add("#X obj 500 280 * 3;")
rfb=q.add("#X obj 500 330 r ockm-delay-fb;"); rmx=q.add("#X obj 500 380 r ockm-delay-mix;")
tff=q.add("#X obj 620 280 t b f;"); fs=q.add("#X obj 500 220 f 121;")
sm=q.add("#X obj 30 440 +~;"); lim=q.add(f"#X obj 30 470 expr~ if(abs({D}v1)<0.8 \\, {D}v1 \\, (0.8+0.2*tanh((abs({D}v1)-0.8)/0.2))*({D}v1/abs({D}v1)));"); out=q.add("#X obj 30 510 outlet~;")   # limiter: clean below 0.8
for c in [(inl,0,inl2,0),(inl2,0,h1,0),(h1,0,h2,0),(h2,0,l1,0),(l1,0,l2,0),(tfn,0,rmx_,0),(rmx_,0,fx,0),(fx,0,h1,1),(fx,0,h2,1),(fx,1,l1,1),(fx,1,l2,1),
          (rdv,0,dvx,0),(dvx,0,th,1),(l2,0,th,0),(dcat,0,dw,0),(dr,0,fb,0),(fb,0,dw,0),(dr,0,mx,0),(mx,0,inl,1),
          (rst,0,fs,0),(fs,0,dtm,0),(rsteps,0,tff,0),(tff,1,dtm,1),(tff,0,fs,0),(dtm,0,dr,0),(rfb,0,fb,1),(rmx,0,mx,1),
          (th,0,lim,0),(lim,0,out,0)]: q.con(*c)
q.add("#X text 500 410 delay time = step length x delay steps (3 = dotted 8th);")
# dub throw: while held, the whole mix goes into its own echo line; let go and the echoes ring out
rth=q.add("#X obj 700 450 r ockm-delay-throw;"); thm=q.add(f"#X msg 700 475 {D}1 15;"); thl=q.add("#X obj 700 500 line~;")
ths=q.add("#X obj 600 525 *~;"); tdw=q.add(f"#X obj 600 600 delwrite~ {D}0-thr 4000;"); tdr=q.add(f"#X obj 600 550 delread~ {D}0-thr 363;")
tfb=q.add("#X obj 700 575 *~ 0.4;"); tad=q.add("#X obj 600 575 +~;"); tgo=q.add("#X obj 600 640 *~ 0.8;")
st_fx=q.add("#X obj 400 120 throw~ ockm-stem-fx;"); q.con(vm,0,st_fx,0); q.con(mx,0,st_fx,0)
for c in [(rth,0,thm,0),(thm,0,thl,0),(pre,0,ths,0),(thl,0,ths,1),(ths,0,tad,0),(tdr,0,tfb,0),(tfb,0,tad,1),(tad,0,tdw,0),
          (dtm,0,tdr,0),(rfb,0,tfb,1),(tdr,0,tgo,0),(tgo,0,inl2,1),(tgo,0,st_fx,0)]: q.con(*c)
q.save("voices/ockm-fx.pd","#N canvas 140 140 900 560 12;")

# ================= reverb =================
q=P()
q.add("#X text 20 10 Reverb: four damped comb filters in parallel then two all-pass filters (a classic Schroeder/Freeverb-style room). Size sets the tail \\, tone darkens it.;")
inl=q.add("#X obj 30 50 inlet~;")
rsz=q.add("#X obj 500 50 r ockm-verb-size;"); szx=q.add(f"#X obj 500 80 expr 0.7+{D}f1*0.27;")
rtn=q.add("#X obj 680 50 r ockm-verb-tone;"); tnx=q.add(f"#X obj 680 80 expr 1500*pow(2\\,{D}f1*3.5);")
q.con(rsz,0,szx,0); q.con(rtn,0,tnx,0)
sm=q.add("#X obj 30 330 +~;"); sm2=q.add("#X obj 30 355 +~;"); sm3=q.add("#X obj 30 380 +~;"); sc=q.add("#X obj 30 405 *~ 0.25;")
combs=[29.7,37.1,41.1,43.7]
outs=[]
for i,ms in enumerate(combs):
    x=30+i*115
    ad=q.add(f"#X obj {x} 120 +~;"); dw=q.add(f"#X obj {x} 150 delwrite~ {D}0-c{i} 60;"); dr=q.add(f"#X obj {x} 180 delread~ {D}0-c{i} {ms};")
    lp=q.add(f"#X obj {x} 210 lop~ 4000;"); fb=q.add(f"#X obj {x} 240 *~ 0.84;")
    for c in [(inl,0,ad,0),(ad,0,dw,0),(dr,0,lp,0),(lp,0,fb,0),(fb,0,ad,1),(szx,0,fb,1),(tnx,0,lp,1)]: q.con(*c)
    outs.append(dr)
q.con(outs[0],0,sm,0); q.con(outs[1],0,sm,1); q.con(sm,0,sm2,0); q.con(outs[2],0,sm2,1); q.con(sm2,0,sm3,0); q.con(outs[3],0,sm3,1); q.con(sm3,0,sc,0)
prev=sc
for j,ms in enumerate([5.0,1.7]):
    x=30+j*230; y=450+j*0
    w=q.add(f"#X obj {x} 450 +~;"); dw=q.add(f"#X obj {x} 480 delwrite~ {D}0-a{j} 20;"); dr=q.add(f"#X obj {x+100} 450 delread~ {D}0-a{j} {ms};")
    g1=q.add(f"#X obj {x+100} 480 *~ 0.5;"); g2=q.add(f"#X obj {x} 510 *~ -0.5;"); y_=q.add(f"#X obj {x} 540 +~;")
    for c in [(prev,0,w,0),(dr,0,g1,0),(g1,0,w,1),(w,0,dw,0),(w,0,g2,0),(g2,0,y_,0),(dr,0,y_,1)]: q.con(*c)
    prev=y_
out=q.add("#X obj 30 600 outlet~;"); q.con(prev,0,out,0)
q.save("voices/ockm-verb.pd","#N canvas 160 160 900 640 12;")

# ================= MIDI clock =================
q=P()
q.add("#X text 20 10 MIDI clock: 24 ticks per beat \\, 6 per step. Leader sends clock + start/stop. Follower steps the sequencer from incoming clock and measures the tempo.;")
# --- leader: send clock ---
rpl=q.add("#X obj 30 60 r ockm-playing;"); rsy=q.add("#X obj 200 60 r ockm-sync;"); rco=q.add("#X obj 330 60 r ockm-clock-out;")
tco=q.add("#X obj 330 90 t b f;"); pk=q.add("#X obj 200 120 pack 0 1;")
allow=q.add(f"#X obj 200 150 expr ({D}f1==0)*{D}f2;")
fpl=q.add("#X obj 30 120 f;"); tal=q.add("#X obj 200 180 t b f;"); go=q.add("#X obj 30 180 *;"); tgo=q.add("#X obj 30 210 t f f;")
ch=q.add("#X obj 120 240 change;"); sel=q.add("#X obj 120 270 sel 0 1;"); m252=q.add("#X msg 120 300 252;"); m250=q.add("#X msg 170 300 250;")
rst=q.add("#X obj 330 200 r ockm-stepms;"); d6=q.add("#X obj 330 230 / 6;")
met=q.add("#X obj 30 270 metro 20;"); m248=q.add("#X msg 30 300 248;")
mo=q.add("#X obj 30 360 midiout;"); scs=q.add("#X obj 120 360 s ockm-clock-sent;")
tpl=q.add("#X obj 30 90 t b f;")
for c in [(rpl,0,tpl,0),(tpl,1,fpl,1),(tpl,0,fpl,0),(rsy,0,pk,0),(rco,0,tco,0),(tco,1,pk,1),(tco,0,pk,0),(pk,0,allow,0),
          (allow,0,tal,0),(tal,1,go,1),(tal,0,fpl,0),(fpl,0,go,0),(go,0,tgo,0),(tgo,1,ch,0),(ch,0,sel,0),(sel,0,m252,0),(sel,1,m250,0),(tgo,0,met,0),
          (rst,0,d6,0),(d6,0,met,1),(met,0,m248,0),(m248,0,mo,0),(m250,0,mo,0),(m252,0,mo,0),(m248,0,scs,0),(m250,0,scs,0),(m252,0,scs,0)]: q.con(*c)
# --- follower: receive clock ---
mri=q.add("#X obj 500 60 midirealtimein;"); rrt=q.add("#X obj 650 60 r ockm-midi-rt;")
rsy2=q.add("#X obj 760 90 r ockm-sync;"); spx=q.add("#X obj 500 120 spigot;")
ro=q.add("#X obj 500 150 route 248 250 251 252;")
tck=q.add("#X obj 500 180 t b b;")
cf=q.add("#X obj 500 210 f;"); tcf=q.add("#X obj 500 240 t f f;"); cp1=q.add("#X obj 560 240 + 1;"); cm6=q.add("#X obj 560 265 mod 6;")
cs0=q.add("#X obj 500 270 sel 0;"); run=q.add("#X obj 500 300 spigot;"); stk=q.add("#X obj 500 330 s ockm-tick;")
# tempo: time 24 clocks
bf=q.add("#X obj 700 210 f;"); tbf=q.add("#X obj 700 240 t f f;"); bp1=q.add("#X obj 760 240 + 1;"); bm=q.add("#X obj 760 265 mod 24;")
bs0=q.add("#X obj 700 270 sel 0;"); tbb=q.add("#X obj 700 300 t b b;"); tim=q.add("#X obj 700 330 timer;")
bpx=q.add(f"#X obj 700 360 expr 60000/{D}f1;"); mo1=q.add("#X obj 700 390 moses 30;"); mo2=q.add("#X obj 760 420 moses 300;")
rnd=q.add(f"#X obj 760 450 expr int({D}f1*10+0.5)/10;"); chb=q.add("#X obj 760 480 change;"); sbpm=q.add("#X obj 760 510 s ockm-bpm;")
# start / continue / stop
tst=q.add("#X obj 560 380 t b b b b;"); z1=q.add("#X msg 650 410 0;"); srs=q.add("#X obj 600 470 s ockm-reset;")
one=q.add("#X msg 560 410 1;"); one2=q.add("#X msg 620 380 1;"); zero=q.add("#X msg 680 380 0;")
spl=q.add("#X obj 560 500 s ockm-play;")
for c in [(mri,0,spx,0),(rrt,0,spx,0),(rsy2,0,spx,1),(spx,0,ro,0),(ro,0,tck,0),(tck,1,bf,0),(tck,0,cf,0),
          (cf,0,tcf,0),(tcf,1,cp1,0),(cp1,0,cm6,0),(cm6,0,cf,1),(tcf,0,cs0,0),(cs0,0,run,0),(run,0,stk,0),
          (bf,0,tbf,0),(tbf,1,bp1,0),(bp1,0,bm,0),(bm,0,bf,1),(tbf,0,bs0,0),(bs0,0,tbb,0),(tbb,1,tim,1),(tbb,0,tim,0),(tim,0,bpx,0),
          (bpx,0,mo1,0),(mo1,1,mo2,0),(mo2,0,rnd,0),(rnd,0,chb,0),(chb,0,sbpm,0),
          (ro,1,tst,0),(tst,3,z1,0),(z1,0,cf,1),(z1,0,bf,1),(tst,2,srs,0),(tst,0,one,0),(one,0,run,1),(one,0,spl,0),
          (ro,2,one2,0),(one2,0,run,1),(one2,0,spl,0),(ro,3,zero,0),(zero,0,run,1),(zero,0,spl,0)]: q.con(*c)
q.add("#X text 500 540 248 clock \\, 250 start \\, 251 continue \\, 252 stop. ockm-midi-rt lets other things feed clock in too.;")
q.save("seq/ockm-clock.pd","#N canvas 120 120 1000 580 12;")

# ================= shared presets =================
# melodies: a wandering line over the chord tones (root, 3rd, 5th, 7th of whatever chord is playing),
# mostly small steps, the odd leap, and a phrase that comes home to the root or fifth every 8 notes.
# 'steps' adds passing notes between them. 64 notes long, so it doesn't repeat for a while; mutate starts it elsewhere.
import random as _random
def _tune(seed, passing, lift):
    rnd=_random.Random(seed)
    ladder=[-3,-1,0,2,4,6,7,9,11] if not passing else [-3,-2,-1,0,1,2,3,4,5,6,7,8,9]
    home=[ladder.index(0), ladder.index(4)]
    i=ladder.index(0); out=[]
    for k in range(64):
        if k%8==7: i=rnd.choice(home)                       # end of a phrase: home
        else:
            mv=rnd.choices([-2,-1,0,1,2,3],[1,4,1,4,1,1])[0]
            if passing and k%2==0 and ladder[i] in (-2,1,3,5,8): mv=rnd.choice([-1,1])   # passing notes resolve
            i=max(0,min(len(ladder)-1,i+mv))
        out.append(ladder[i]+lift)
    return " ".join(str(v) for v in out)
# Melodies that follow the bar (v0.52). Unlike the lists above, which hand out the next note each time the rhythm plays,
# these give a pitch for every step of four bars, so the shape lines up with the phrase whatever the rhythm.
# Scale steps are from the chord's root: on the beat they're always a chord tone (root, third, fifth).
# Each is 8 versions of 64 steps: version 0 is the original, 'new' steps through the others.
_CT=[-3,0,2,4,7,9,11]                     # chord tones, low to high (as scale steps from the chord's root)
def _bar(beats, rnd):
    """16 steps: each beat's chord tone, with passing or neighbour notes on the steps between."""
    out=[]
    for k in range(4):
        a=beats[k]; b=beats[k+1] if k<3 else beats[k]
        out.append(a)
        for j in (1,2,3):
            v=round(a+(b-a)*j/4)
            if v==a and j==2: v=a+rnd.choice([1,-1])        # a neighbour note so held beats still move
            out.append(v)
    return out
def _ct_move(d, n): i=min(range(len(_CT)),key=lambda k:abs(_CT[k]-d)); return _CT[max(0,min(len(_CT)-1,i+n))]
def _motif_beats(rnd):
    b=[rnd.choice([0,2,4])]
    for _ in range(3): b.append(_ct_move(b[-1], rnd.choices([-2,-1,0,1,2],[1,3,2,3,1])[0]))
    return b
def _cadence(beats, target, rnd):
    """keep the start of the idea, then step home to target (0 the root: an answer; 4 the fifth: a question)"""
    mid=_ct_move(target, rnd.choice([1,-1]))
    return [beats[0], mid, target, target]   # home by beat 3 and stay there, so a phrase that ends early still lands
def _melody4(seed, kind, lift):
    rnd=_random.Random(seed)
    A=_motif_beats(rnd)
    if kind=="motif":                 # sing-along: say it, say it again, change it, come home
        B=[_ct_move(x,1) for x in A] if rnd.random()<0.5 else [_ct_move(A[0],0)]+[_ct_move(A[0], -( _CT.index(_ct_move(x,0)) - _CT.index(_ct_move(A[0],0)) )) for x in A[1:]]
        bars=[A, A, B, _cadence(A, 0, rnd)]
    else:                             # question and answer: up in the air on the fifth, then home to the root
        A2=A[:]; A2[3]=_ct_move(A2[3], rnd.choice([1,-1]))
        bars=[A, _cadence(A2, 4, rnd), A, _cadence(A, 0, rnd)]
    out, made = [], {}
    for b in bars:                    # the same idea comes back note for note
        if tuple(b) not in made: made[tuple(b)] = _bar(b, rnd)
        out += made[tuple(b)]
    return [max(-3,min(11,v))+lift for v in out]
ARP_SHAPES=[[0,2,4,7],[7,4,2,0],[0,2,4,7,4,2],[0,4,2,7],[0,4,7,4],[0,7,4,2],[-3,0,2,4],[0,2,0,4,0,7]]
def _arp4(seed):
    """an arpeggio over whichever chord is playing that changes as it goes: the same shape twice, then lifted, then a turn"""
    rnd=_random.Random(seed)
    s1=rnd.choice(ARP_SHAPES); s2=rnd.choice(ARP_SHAPES)
    lift=[_ct_move(x,1) for x in s1]
    out=[]
    for bar,shape in enumerate([s1, s1, lift if rnd.random()<0.6 else s2, s2]):
        out+=[shape[j % len(shape)] for j in range(16)]
    return out
def _bank(fn): return " ".join(str(v) for k in range(8) for v in fn(k))
def _brh(*bars):
    """Bass rhythms, one or four bars of 16 steps: X accent, x note, s/S note (accent) that slides into the next,
    - holds the note before it (no new note: it carries on). A note or hold followed by a hold slides on into it."""
    assert len(bars) in (1,4) and all(len(b)==16 for b in bars)
    c="".join(bars); out=[]
    for i,ch in enumerate(c):
        nxt=c[(i+1)%len(c)]
        if ch=="-": out.append(5 if nxt=="-" else 6)          # 5 hold (and keep holding), 6 the last step of a hold
        elif ch==".": out.append(0)
        else:
            v={"x":1,"X":2,"s":3,"S":4}[ch]
            if nxt=="-" and v<3: v+=2                            # held on: slide into the hold
            out.append(v)
    return " ".join(str(v) for v in out)
def _rhy4(*bars):
    assert len(bars)==4 and all(len(b)==16 for b in bars)
    return " ".join(str({".":0,"x":1,"X":2,"s":3,"S":4}[c]) for b in bars for c in b)
PRE={"leadrhythm":[("offbeat","0 0 2 0 0 0 1 0 0 0 2 0 0 0 1 0"),("rolling","0 2 1 1 0 2 1 1 0 2 1 1 0 2 1 1"),("gallop","0 0 2 1 0 1 2 0 0 0 2 1 0 1 2 0"),
               ("acid-classic","2 1 0 1 3 4 1 0 2 1 3 1 0 2 1 3"),("sparse-dub","2 0 0 0 0 0 0 1 0 0 1 0 0 0 0 0"),("tech-bounce","0 0 2 0 0 1 0 0 0 0 2 0 0 1 0 1"),
               ("acid-16ths","2 1 3 1 2 1 1 3 2 1 3 1 2 3 1 1"),("trip-hop","2 0 0 0 0 0 3 1 0 0 0 0 0 0 1 0"),("hook","2 0 0 1 0 0 1 0 0 0 1 0 1 0 0 0"),("sparse-melody","2 0 0 0 0 0 1 0 0 3 0 0 1 0 0 0"),
               # four bars long (v0.52): phrases that breathe
               ("phrase",_rhy4("X.x.x.x.X...x.x.","X.x.x.x.X...x...","X.x.x.x.X.x.x.x.","X...x...X.......")),
               ("question-answer",_rhy4("X.x.x..xX.x.....","x.......X.......","X.x.x..xX.x.....","x...x...X.......")),
               ("pickup",_rhy4("X.....x.....x.x.","X.......x...x.x.","X.....x.....x.x.","X...x...X.......")),
               ("arp-gate",_rhy4("XxxxXxx.XxxxXxx.","XxxxXxx.XxxxXxx.","XxxxXxxxXxxxXxxx","Xxx.Xxx.X.x.X..."))],
     # the bass has its own list: the classic dance bass rhythms first, then the older ones
     "bassrhythm":[("offbeat-donk",_brh("..X...x...X...x.")),("straight-8ths",_brh("X.x.x.x.X.x.x.x.")),
                   ("rolling-16ths",_brh("xxXxxxXxxxXxxxXx")),("dotted-8ths",_brh("X..x..x..X..x..x")),
                   ("octave-jump",_brh("x.X.x.X.x.X.x.X.")),("sustained",_brh("X---------------")),
                   ("quarters",_brh("X...x...X...x...")),("dembow",_brh("X..x..x.X..x..x.")),
                   ("two-step",_brh("X.....x...X..x..","..x..x....X...x.","X.....x...X..x..","..x..x..X...x...")),
                   ("3-2-3-cluster",_brh("Xxx.xx.Xxx..xx..")),
                   ("round-the-kick","0 2 1 1 0 2 1 1 0 2 1 1 0 2 1 1"),("gallop","0 0 2 1 0 1 2 0 0 0 2 1 0 1 2 0"),
                   ("acid-classic","2 1 0 1 3 4 1 0 2 1 3 1 0 2 1 3"),("acid-16ths","2 1 3 1 2 1 1 3 2 1 3 1 2 3 1 1"),
                   ("tech-bounce","0 0 2 0 0 1 0 0 0 0 2 0 0 1 0 1"),("sparse-dub","2 0 0 0 0 0 0 1 0 0 1 0 0 0 0 0"),
                   ("trip-hop","2 0 0 0 0 0 3 1 0 0 0 0 0 0 1 0"),
                   # v0.77: speed garage, held notes pushed off the kick, sliding at the end of the phrase
                   ("speed-garage",_brh("X-.x..X-.x..x.x.","X-.x..X-..x.S-x.","X-.x..X-.x..x.x.","X-.x..X-.x.xS-.."))],
     "notes":[("root","0"),("octaves","0 7"),("root-fifth","0 4"),("acid-riff","0 0 7 0 2 0 6 4"),("walk-up","0 1 2 4"),("minor-stab","0 2 4 2"),
              ("dub","0 0 -3 -2"),("pedal","0 0 0 1"),("arp-up","0 2 4 7"),("arp-updown","0 2 4 7 4 2"),("call","4 4 2 0 2 4 5 4"),("descend","7 6 4 2"),
              ("melody",_tune(1,False,0)),("melody-steps",_tune(2,True,0)),("melody-high",_tune(3,False,7)),
              ("motif",_bank(lambda k:_melody4(100+k,"motif",0))),("motif-call",_bank(lambda k:_melody4(200+k,"call",0))),
              ("motif-high",_bank(lambda k:_melody4(300+k,"motif",7))),("arp-evolve",_bank(lambda k:_arp4(400+k)))],
     "scale":[("minor","0 2 3 5 7 8 10"),("major","0 2 4 5 7 9 11"),("dorian","0 2 3 5 7 9 10"),("phrygian","0 1 3 5 7 8 10"),
              ("mixolydian","0 2 4 5 7 9 10"),("harmonic-minor","0 2 3 5 7 8 11")],
     "chordrhythm":[("bar-pads","2 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0"),("two-beat","2 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0"),
                    ("offbeat","0 0 1 0 0 0 1 0 0 0 1 0 0 0 1 0"),("dub-stabs","0 0 0 2 0 0 0 0 0 0 1 0 0 0 0 0"),
                    ("house-organ","1 0 0 1 0 0 1 0 0 0 1 0 0 1 0 0"),("tresillo","2 0 0 1 0 0 1 0 2 0 0 1 0 0 1 0"),
                    ("syncopated","0 0 1 0 0 1 0 0 0 1 0 0 1 0 0 0"),("garage-skip","1 0 0 1 0 0 0 0 0 1 0 0 1 0 0 0 1 0 0 1 0 0 0 0 0 1 0 0 0 0 1 0"),
                    ("call-answer","2 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 1 0 0 1 0 0 0"),("eighths","1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0"),
                    ("piano-riff","2 0 0 1 0 0 2 0 0 1 0 0 1 0 1 0 2 0 0 1 0 0 2 0 0 1 0 0 2 0 0 0")],   # v0.90: the Italo piano riff, two bars
     # chord types. Plain numbers: scale steps above the chord's root, so the chord follows the key (0 root, 2 third...).
     # "s" then numbers: a fixed shape in semitones above the chord's root, moved as one block with the progression (the
     # chord memory sound of deep house, Detroit and dub techno). v0.90: the 9th and 11th leave the root to the bass
     "chordtype":[("triad","0 2 4 -1"),("seventh","0 2 4 6"),("sus2","0 1 4 -1"),("power","0 4 7 -1"),
                  ("sus4","0 3 4 -1"),("sixth","0 2 4 5"),("ninth","2 4 6 8"),("eleventh","2 6 8 10"),
                  ("m9","s 3 7 10 14"),("m11","s 3 10 14 17"),("m7","s 0 7 10 15"),("4ths","s 0 5 10 15"),("maj9","s 4 7 11 14")]}
# Chord progressions: (name, label shown on screen, [(chord root as scale step, length in bars), ...]).
# The first 8 are the v0.10 ones (one chord per bar). Each is written out as its natural length in steps,
# then one chord root per step, so the generator only has to look things up.
PROGS=[("one-chord","i",[(0,1)]),("vamp","i iv",[(0,1),(3,1)]),("dub-techno","i . . VII",[(0,3),(6,1)]),
       ("deep-house","i iv VI v",[(0,1),(3,1),(5,1),(4,1)]),("garage","i VI iv v",[(0,.5),(5,.5),(3,.5),(4,.5)]),
       ("pop","i VI III VII",[(0,1),(5,1),(2,1),(6,1)]),("uplift","VI VII i",[(5,1),(6,1),(0,2)]),
       ("andalusian","i VII VI V",[(0,1),(6,1),(5,1),(4,1)]),("trip-hop","i VII VI v",[(0,2),(6,2),(5,2),(4,2)]),
       ("soul","ii V I",[(1,1),(4,1),(0,2)]),
       # v0.90, for Italian piano house (in a major key): the big four-chord turn, and the same starting on vi
       ("piano-house","I V vi IV",[(0,1),(4,1),(5,1),(3,1)]),("anthem","vi IV I V",[(5,1),(3,1),(0,1),(4,1)])]
# drum grooves: one 16-step line per drum sound (x hit, X accent; v0.86: g a ghost note, about a third, o soft, about two thirds). Swing 0 = leave it as it is.
# sounds: kick snare clap perc1 hat open-hat tom perc2. A groove lands on whichever slot plays that sound.
GROOVES=[
 ("four-floor",56,dict(kick="X...X...X...X...",clap="....x.......x...",hat="..x...x...x...x.")),
 ("house",56,dict(kick="X...x...X...x...",clap="....X......gX...",ohat="..x...x...x...x.",hat=".o.g.o.g.o.g.o.g")),
 ("deep-house",58,dict(kick="X...x...X...x...",clap="....x.......x..g",ohat="..x...x...x...x.",perc1=".o....x..g....x.",hat="x..gx..gx..gx.g.")),
 ("tech-house",54,dict(kick="X...x...X...x...",clap="....X.......X...",ohat="..X...X...X...X.",hat="og.xog.xog.xog.x",perc1="...o..x....g..x.",tom=".......x........")),
 ("minimal",54,dict(kick="X...X...X...X...",perc1="...g..x...o..x..",hat=".o.g.o.g.o.g.o.g",clap="............x...",tom=".........x......")),
 ("techno",50,dict(kick="X...X...X...X...",ohat="..x...x...x...x.",hat="og.xog.xog.xog.x",clap="....x.......x...",perc2="...g......x.....")),
 ("dub-techno",54,dict(kick="X...X...X...X...",perc1="...g.....x....g.",ohat="..x...x...x...x.",hat="o.g.o.g.o.g.o.g.")),
 ("garage",64,dict(kick="X.......x.x.....",snare="....X.......X...",hat="x.xxx.x.x.xxx.x.",perc1="......x......x..",ohat="..x.......x.....")),
 ("breakbeat",54,dict(kick="X.x.......xx....",snare="....X..x.x..X..x",hat="x.x.x.x.x.x.x.x.")),
 ("boom-bap",62,dict(kick="X......x..x.....",snare="....X.......X...",hat="x.x.x.x.x.x.x.x.",ohat="..............x.")),
 ("trip-hop",60,dict(kick="X.........x.....",snare="....X.......X...",hat="x...x.x.x...x.x.",perc1="..x.......x.....",tom=".............x..")),
 ("electro",50,dict(kick="X.....x...x.....",clap="....X.......X...",hat="xxxxxxxxxxxxxxxx",tom="..........x..x..")),
 ("clear",0,dict()),
 # bank 2: house and garage (after 'clear', so the numbers of bank 1 never move)
 ("chicago",56,dict(kick="X...X...X...X...",clap="....X.......X...",hat="o.x.o.x.o.x.o.x.",ohat="..x...x...x...x.",perc1="..........x.....")),
 ("jackin",58,dict(kick="X...X...X...X...",clap="....X.......X...",hat=".xg..xg..xg..xg.",ohat="..X...X...X...X.",perc2="x..g..x...o..g..")),
 ("disco",54,dict(kick="X...X...X...X...",snare="....X......gX...",ohat="..x...x...x...x.",hat="gxXxgxXxgxXxgxXx",perc1="o.g.o.g.o.g.o.g.")),
 ("soulful",58,dict(kick="X...X...X...X...",clap="....x.......x...",hat="..x...x...x...x.",perc1="x..x..x...x..x..",perc2="......x.......x.")),
 ("afro-house",56,dict(kick="X...X...X...X...",clap="....x.......x...",hat=".x.x.x.x.x.x.x.x",perc1="x..x..x...x.x...",perc2="..x...x.x...x..x")),
 ("lofi-house",62,dict(kick="X.....x.X.......",snare="....X.......X...",hat="x.x.x.x.x.x.x.x.",ohat=".......x........")),
 ("2-step",64,dict(kick="X.....x...X.....",snare="....X.......X...",hat="x.x.x.x.x.x.x.x.",perc2="..x.......x..x..")),
 ("speed-garage",60,dict(kick="X...X...X...X...",clap="....X.......X...",snare="...x..x.x..x..xx",ohat="..X...X...X...X.",hat="xx.xxx.xxx.xxx.x",perc1="..x....x..x...x.")),
 ("funky-house",56,dict(kick="X...X...X...X...",clap="....X.......X...",hat="gxXxgxXxgxXxgxXx",ohat="..x.......x.....",perc1=".x...x.x.x...x..",tom="...........x..x.")),
 ("ghetto-house",54,dict(kick="X...X..xX...X..x",clap="....X.......X...",hat="x.x.x.x.x.x.x.x.",perc2=".x...x...x...x..")),
 ("nu-disco",54,dict(kick="X...X...X...X...",snare="....X.......X...",hat="..x...x...x...x.",ohat="..........X.....",perc1="xxxxxxxxxxxxxxxx",tom="..............x.")),
 ("rolling",56,dict(kick="X...X...X...X...",clap="........x.......",ohat="..x...x...x...x.",hat="ogxgogxgogxgogxg",perc2=".x....x..x....x.",perc1="...x.......x....")),
 # bank 3: techno, breaks and downtempo
 ("detroit",54,dict(kick="X...X...X...X...",clap="....X.......X...",hat="o.xgo.xgo.xgo.xg",ohat="..x...x...x...x.",tom=".........x....x.")),
 ("berlin",50,dict(kick="X...X...X...X...",ohat="..X...X...X...X.",hat="ogxgogxgogxgogxg",perc2=".x.......x......",clap="....x.......x...")),
 ("industrial",50,dict(kick="X..xX...X..xX...",snare="....X.......X...",hat="o.x.o.x.o.x.o.x.",perc1="...x...x...x...x",tom="......x.......x.")),
 ("hypnotic",52,dict(kick="X...X...X...X...",perc1=".o.g.o.g.o.g.x.g",perc2="...x.....x...x..",ohat="..x...x...x...x.")),
 ("acid-techno",50,dict(kick="X...X...X...X...",clap="....X.......X...",hat="ogxgogxgogxgogxg",ohat="..X...X...X...X.",snare="...............x")),
 ("think-break",56,dict(kick="X.....X...X.....",snare="....X.......X..x",hat="x.x.x.x.x.x.x.x.",ohat="..............x.")),
 ("jungle",50,dict(kick="X.........X.....",snare="....X..x.x..X..x",hat="xxxxxxxxxxxxxxxx")),
 ("big-beat",54,dict(kick="X.....X.X.....X.",snare="....X.......X...",hat="x.x.x.x.x.x.x.x.",ohat="......x.......x.",perc1="..x...x...x...x.")),
 ("downtempo",60,dict(kick="X.......x.x.....",snare="....X.......X...",hat="x...x...x...x...",perc1="..x...x...x...x.")),
 ("one-drop",58,dict(kick="........X.......",snare="........X.......",hat="x.x.x.x.x.x.x.x.",perc2="..x...x...x...x.")),
 ("half-time",56,dict(kick="X.........x.....",snare="........X.......",hat="x.x.x.x.x.x.x.x.",perc1="...x.......x....")),
 ("lofi-hip-hop",64,dict(kick="X......x..X.....",snare="....X.......X...",hat="x.x.x.x.x.x.x.x.",perc2=".......x........")),
 # bank 4 (v0.76): hard and fast
 ("hard-house",50,dict(kick="X...X...X...X...",clap="....X.......X...",ohat="..X...X...X...X.",hat="o.xgo.xgo.xgo.xg",snare="............goxX")),
 ("dnb-two-step",50,dict(kick="X.........X.....",snare="....X.......X...",hat="x.x.x.x.x.x.x.x.",ohat="..............x.")),
 ("dnb-rolling",50,dict(kick="X.....X...X.....",snare="....X..x....X..x",hat="xxXxxxXxxxXxxxXx",perc2="..x.......x.....")),
]
GROOVE_BANKS=[("classics",0),("house + garage",13),("techno + breaks",25),("hard + fast",37)]   # name, first groove number
_SND=["kick","snare","clap","perc1","hat","ohat","tom","perc2"]
def _groove_line(sw,parts):
    for k,v in parts.items(): assert k in _SND and len(v)==16, (k,v)
    vals=[]
    for nm in _SND: vals+=[{".":0,"x":1,"X":2,"g":0.35,"o":0.65}[c] for c in parts.get(nm,"."*16)]   # v0.86: g ghost, o soft
    return " ".join(str(v) for v in [sw]+vals)
PRE["groove"]=[(nm,_groove_line(sw,parts)) for nm,sw,parts in GROOVES]
# drum fills: what changes on the last bar of a phrase. Per drum sound, 16 steps: '.' keep your pattern, '-' silent, 'x' hit, 'X' accent.
FILLS=[
 ("snare-roll",dict(snare="........x-x-xxXX",clap="........--------")),
 ("tom-run",dict(tom="........X-x-xxxX",kick="........x-------",snare="........--------")),
 ("cut-out",dict(kick="........--------",hat="............----",ohat="............----",clap="........--------")),
 ("snare-build",dict(snare="x-x-x-x-xxxxXXXX",clap="........x-x-xxxx",hat="xxxxxxxxxxxxxxxx")),
 # a whole bar of breakbeat in place of the groove: kick and snare in the classic broken pattern (with ghost snares),
 # straight 8th hats, everything else quiet for the bar
 ("breakbeat",dict(kick="X.x.......Xx....",snare="....X..x.x..X..x",hat="x.x.x.x.x.x.x.x.",clap="----------------",ohat="----------------",
                   tom="----------------",perc1="----------------",perc2="----------------")),
]
def _fill_line(parts):
    for k,v in parts.items(): assert k in _SND and len(v)==16, (k,v)
    vals=[]
    for nm in _SND: vals+=[{".":-1,"-":0,"x":1,"X":2}[c] for c in parts.get(nm,"."*16)]
    return " ".join(str(v) for v in vals)
PRE["fill"]=[(nm,_fill_line(parts)) for nm,parts in FILLS]
PRE["progx"]=[]
for nm,_,chords in PROGS:
    steps=[]
    for deg,bars in chords: steps+=[deg]*int(bars*16)
    assert len(steps) in (16,32,64,128), (nm,len(steps))
    PRE["progx"].append((nm," ".join(str(v) for v in [len(steps)]+steps)))
# v0.90 chord voicing, in Lua, shared by the chord sequencer (seq/ockm-chordnotes.pd_lua) and the touchscreen (its
# chord names, the notes it checks lines against, MIDI export), so the screen and the sound always agree
def _chord_types_lua():
    out=[]
    for nm,v in PRE["chordtype"]:
        t=v.split()
        if t[0]=="s": out.append(f'{{ k=1, name="{nm}", '+", ".join(t[1:])+" }")
        else: out.append(f'{{ k=0, name="{nm}", '+", ".join(x for x in t if int(x)>=0)+" }")
    return "local CHORD_TYPES = { "+", ".join(out)+" }\n"
CHORD_LUA=_chord_types_lua()+r"""local CHORD_CENTRE, CHORD_FLOOR = 62, 50   -- smooth chords sit around D4, their lowest note no lower than D3
-- a chord's notes (MIDI). deg: the chord's root as a scale step; sc: the scale (7 semitones); root: the key (0 C .. 11 B);
-- smooth: keep every chord at about the same height (inversions for chords in the key, octaves for fixed shapes), so
-- they move by small steps and stay out of the bass; voicing 0 close, 1 open, 2 wide; turn: the turnaround's major V
local function chord_voicing(deg, ctype, sc, root, smooth, voicing, turn)
  local ty = CHORD_TYPES[(ctype or 0) + 1] or CHORD_TYPES[1]
  local rox = (root <= 7) and (48 + root) or (36 + root)
  local function at(a)
    local s = sc[(a % 7) + 1]
    if turn and s == 10 then s = 11 end   -- the turnaround raises the minor 7th: E major in A minor
    return rox + 12 * math.floor(a / 7) + s
  end
  deg = math.floor(deg)
  local n = {}
  if ty.k == 1 then
    local r = at(deg)
    for _, o in ipairs(ty) do
      if turn and o % 12 == 3 then o = o + 1 end   -- a minor shape turns major on the turnaround
      n[#n + 1] = r + o
    end
  else
    for _, o in ipairs(ty) do
      local v = at(deg + o)
      if o == 8 and v - at(deg) == 13 then v = at(deg + 7) end   -- a flat 9th grinds on the bass: the root instead
      n[#n + 1] = v
    end
  end
  if smooth then
    local cands = {}
    if ty.k == 1 then cands[1] = n
    else
      table.sort(n)
      for i = 0, #n - 1 do
        local c = {}
        for j, v in ipairs(n) do c[j] = (j <= i) and v + 12 or v end
        table.sort(c); cands[#cands + 1] = c
      end
    end
    local best, bc
    for _, c in ipairs(cands) do
      local sum, lo = 0, c[1]
      for _, v in ipairs(c) do sum = sum + v; if v < lo then lo = v end end
      local mean = sum / #c
      local m = math.floor((CHORD_CENTRE - mean) / 12 + 0.5)
      for mm = m - 1, m + 1 do
        local cost = math.abs(mean + 12 * mm - CHORD_CENTRE)
        if lo + 12 * mm < CHORD_FLOOR then cost = cost + (CHORD_FLOOR - lo - 12 * mm) end
        for j = 2, #c do if c[j] - c[j - 1] == 1 then cost = cost + 4 end end   -- no semitone rubs inside a chord
        if not bc or cost < bc - 1e-9 then
          bc = cost; best = {}
          for j, v in ipairs(c) do best[j] = v + 12 * mm end
        end
      end
    end
    n = best
  end
  -- open lifts the second note an octave; wide also drops the lowest an octave and lifts the fourth
  if voicing == 1 or voicing == 2 then
    if n[2] then n[2] = n[2] + 12 end
    if voicing == 2 then n[1] = n[1] - 12; if n[4] then n[4] = n[4] + 12 end end
  end
  return n, ty
end
"""
os.makedirs(os.path.join(R,"seq"),exist_ok=True)
open(os.path.join(R,"seq","ockm-chordnotes.pd_lua"),"w").write("""-- The chord sequencer's notes: a chord type, key, scale and voicing turned into up to four MIDI notes.
-- Written by tools/build.py: change it there. In: scale <7 semitones>, type <n>, root <0-11>, smooth <0/1>,
-- voicing <0-2>, hit <strength> <scale step> <turnaround 0/1>. Out: four notes (0 for none) and the strength.
local cn = pd.Class:new():register("ockm-chordnotes")
"""+CHORD_LUA+"""
function cn:initialize(sel, atoms)
  self.inlets, self.outlets = 1, 1
  self.sc, self.ty, self.root, self.smooth, self.voicing = { 0, 2, 3, 5, 7, 8, 10 }, 0, 9, true, 0
  return true
end
function cn:in_1_scale(a) if #a >= 7 then self.sc = a end end
function cn:in_1_type(a) self.ty = math.max(0, math.floor(a[1] or 0)) end
function cn:in_1_root(a) self.root = math.floor(a[1] or 9) % 12 end
function cn:in_1_smooth(a) self.smooth = (a[1] or 1) > 0 end
function cn:in_1_voicing(a) self.voicing = math.floor(a[1] or 0) end
function cn:in_1_hit(a)
  local n = chord_voicing(a[2] or 0, self.ty, self.sc, self.root, self.smooth, self.voicing, (a[3] or 0) > 0)
  local out = {}
  for k = 1, 4 do out[k] = n[k] or 0 end
  out[5] = math.min(1, (a[1] or 0.75) * (0.92 + 0.16 * math.random()))   -- played, not programmed: no two hits quite the same
  self:outlet(1, "list", out)
end
""")
# spice 1 to 4 on screen picks one of these chord types (index into chordtype)
SPICE=[(0,"triad"),(1,"7th"),(6,"9th"),(7,"11th")]
# the touchscreen shows the same preset names: write them into the Lua file between its PRESETS markers
def _lua_list(items): return "{ " + ", ".join("{ " + ", ".join(f'"{x}"' if isinstance(x,str) else str(x) for x in it) + " }" for it in items) + " }"
_ui_src=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"ui","ockm-ui.pd_lua")
if os.path.exists(_ui_src):
    _t=open(_ui_src).read()
    _a=_t.index("-- BEGIN PRESETS"); _a=_t.index("\n",_a)+1; _b=_t.index("-- END PRESETS")
    _block=("local RHYTHMS = "+_lua_list([(n.replace("-"," "),) for n,_ in PRE["leadrhythm"]])+"\n"
            "local BASS_RHYTHMS = "+_lua_list([(n.replace("-"," "),) for n,_ in PRE["bassrhythm"]])+"\n"
            "local MONO_NOTES = { "+", ".join(f'"{n.replace("-"," ")}"' for n,_ in PRE["notes"])+" }\n"
            "local CHORD_RHY = "+_lua_list([(n.replace("-"," "),) for n,_ in PRE["chordrhythm"]])+"\n"
            "local PROGS = "+_lua_list([(n.replace("-"," "),lab) for n,lab,_ in PROGS])+"\n"
            "local SPICE = "+_lua_list([(i,lab) for i,lab in SPICE])+"\n"
            "local FILLS = { "+", ".join(f'"{n.replace("-"," ")}"' for n,_ in FILLS)+" }\n"
            "local GROOVES = { "+", ".join(f'"{n.replace("-"," ")}"' for n,_,_ in GROOVES)+" }\n"
            "local GROOVE_BANKS = { "+", ".join(f'{{ "{n}", {i} }}' for n,i in GROOVE_BANKS)+" }\n"
            +CHORD_LUA+
            "local PROG_SHAPES = { "+", ".join("{ "+", ".join(f"{{ {d}, {int(b*16)} }}" for d,b in ch)+" }" for _,_,ch in PROGS)+" }\n")
    os.makedirs(os.path.join(R,"ui"),exist_ok=True)
    open(os.path.join(R,"ui","ockm-ui.pd_lua"),"w").write(_t[:_a]+_block+_t[_b:])
p=P()
p.add("#X text 20 10 Shared presets for the generators and chords. Rhythm codes: 0 rest 1 note 2 accent 3 note+slide 4 accent+slide. Notes and progressions are scale steps (0 root \\, 2 third \\, 4 fifth \\, 7 octave).;")
for i,(k,rows) in enumerate(PRE.items()):
    p.add(f"#X obj {20+(i%3)*260} {60+(i//3)*40} text define -k ockm-presets-{k};")
    p.L.append("#A set "+" \; ".join(f"{a} {b}" for a,b in rows)+" \;;")
p.add("#X text 20 150 Change presets in tools/build.py (PRE) so they survive rebuilds.;")
p.save("seq/ockm-presets.pd","#N canvas 200 200 820 200 12;")

# ================= part lengths =================
# Each part has its own length in steps (16, 32, 64, 128 or 256): ockm-drum-len (all 8 drum rows), ockm-bass-len,
# ockm-lead-len, ockm-chord-len. The loop is as long as the longest part (sent out as ockm-len); shorter parts repeat inside it.
# Growing a part repeats its own bars to fill the new ones, unless it was that long before: then its old bars come back.
# Older loop files hold one length (ockm-len) and maybe a drums loop (ockm-drum-loop): while loading, those set the parts.
# Until the screens have a length per part: ockm-length sets every part (drums stay shorter if they were),
# ockm-drum-loop sets the drum length (0 = as long as the synths), ockm-drum-double doubles the drums.
PARTS=["drum","bass","lead","chord"]
LOOPX="max(max(ockm_drumlen\\,ockm_basslen)\\,max(ockm_leadlen\\,ockm_chordlen))"
SYNX="max(ockm_basslen\\,max(ockm_leadlen\\,ockm_chordlen))"
p=P()
p.add("#X text 20 10 Part lengths: each part repeats inside the loop \\, and the loop is as long as the longest part.;")
rld0=p.add("#X obj 20 20 r ockm-loading;"); rld=p.add("#X obj 20 40 t f f f f f f;"); p.con(rld0,0,rld,0)
vld=p.add("#X obj 20 65 v ockm_loadingv;"); p.con(rld,5,vld,0)
nld=p.add("#X obj 120 65 == 0;"); p.con(rld,4,nld,0)
# the loop length, sent whenever a part changes (held back while a loop loads, then sent once at the end)
lbang=p.add("#X obj 20 600 t b b;"); lx=p.add(f"#X obj 20 630 expr {LOOPX};"); lsp=p.add("#X obj 20 660 spigot 1;"); p.con(nld,0,lsp,1)
sln=p.add("#X obj 20 690 s ockm-len;")
dx=p.add(f"#X obj 200 630 expr if(ockm_drumlen<{SYNX} \\, ockm_drumlen \\, 0);"); dsp=p.add("#X obj 200 660 spigot 1;"); p.con(nld,0,dsp,1)
dch=p.add("#X obj 200 690 change -1;"); sdl=p.add("#X obj 200 720 s ockm-drum-loop;")   # for the screens: drums shorter than the synths
for c in [(lbang,1,lx,0),(lx,0,lsp,0),(lsp,0,sln,0),(lbang,0,dx,0),(dx,0,dsp,0),(dsp,0,dch,0),(dch,0,sdl,0)]: p.con(*c)
for i,pt in enumerate(PARTS):
    x=20+i*260
    rr=p.add(f"#X obj {x} 120 r ockm-{pt}-len;"); cl=p.add(f"#X obj {x} 145 clip 16 256;"); t3=p.add(f"#X obj {x} 170 t f f f;")
    # 1. grew past where it has been: repeat its bars into the new ones
    t2=p.add(f"#X obj {x+100} 200 t f f;"); pk=p.add(f"#X obj {x+100} 290 pack f f;")
    ex=p.add(f"#X obj {x+100} 230 expr if(ockm_loadingv==0 && {D}f1>ockm_{pt}max && ockm_{pt}max>0 \\, ockm_{pt}max \\, -1);")
    mo=p.add(f"#X obj {x+100} 260 moses 0;"); sx=p.add(f"#X obj {x+100} 320 s ockm-{pt}-extend;")
    # 2. the furthest it has reached
    mx=p.add(f"#X obj {x+50} 350 expr if(ockm_loadingv \\, {D}f1 \\, max({D}f1 \\, ockm_{pt}max));"); vmx=p.add(f"#X obj {x+50} 380 v ockm_{pt}max;")
    # 3. its length, then the loop length
    tbf=p.add(f"#X obj {x} 410 t b f;"); vl=p.add(f"#X obj {x+30} 440 v ockm_{pt}len;")
    for c in [(rr,0,cl,0),(cl,0,t3,0),(t3,2,t2,0),(t2,1,pk,1),(t2,0,ex,0),(ex,0,mo,0),(mo,1,pk,0),(pk,0,sx,0),
              (t3,1,mx,0),(mx,0,vmx,0),(t3,0,tbf,0),(tbf,1,vl,0),(tbf,0,lbang,0)]: p.con(*c)
# loaded: each part has reached its own length; send the loop length (and the drums' share) once
s0=p.add("#X obj 1100 40 sel 0;"); p.con(rld,0,s0,0); tl=p.add("#X obj 1100 65 t b b b b b;"); p.con(s0,0,tl,0)
for i,pt in enumerate(PARTS):
    e=p.add(f"#X obj {1100+i*120} 95 expr ockm_{pt}len;"); v=p.add(f"#X obj {1100+i*120} 120 v ockm_{pt}max;"); p.con(tl,4-i,e,0); p.con(e,0,v,0)
fl=p.add("#X obj 1100 160 t b b;"); p.con(tl,0,fl,0)
fx2=p.add(f"#X obj 1100 190 expr if(ockm_drumlen<{SYNX} \\, ockm_drumlen \\, 0);"); p.con(fl,1,lbang,0); p.con(fl,0,fx2,0)
st=p.add(f"#X msg 1100 220 set {D}1;"); p.con(fx2,0,st,0); p.con(st,0,dch,0); p.con(fx2,0,sdl,0)
# older files: one length for everything, maybe with the drums looping shorter
s1=p.add("#X obj 1100 280 sel 1;"); p.con(rld,1,s1,0); z=p.add("#X msg 1100 305 0;"); vdl=p.add("#X obj 1100 330 v ockm_legacy_dl;"); p.con(s1,0,z,0); p.con(z,0,vdl,0)
rol=p.add("#X obj 1300 280 r ockm-len;"); osp=p.add("#X obj 1300 305 spigot;"); p.con(rld,3,osp,1); p.con(rol,0,osp,0)
ot=p.add("#X obj 1300 330 t f f;"); od=p.add(f"#X obj 1400 360 expr if(ockm_legacy_dl>0 && ockm_legacy_dl<{D}f1 \\, ockm_legacy_dl \\, {D}f1);")
om=p.add(f"#X msg 1300 390 \\; ockm-bass-len {D}1 \\; ockm-lead-len {D}1 \\; ockm-chord-len {D}1;"); odm=p.add(f"#X msg 1400 390 \\; ockm-drum-len {D}1;")
for c in [(osp,0,ot,0),(ot,1,od,0),(od,0,odm,0),(ot,0,om,0)]: p.con(*c)
rdl=p.add("#X obj 1600 280 r ockm-drum-loop;"); dl_t=p.add("#X obj 1600 305 t f f;"); p.con(rdl,0,dl_t,0)
lsp2=p.add("#X obj 1700 330 spigot;"); p.con(rld,2,lsp2,1); p.con(dl_t,1,lsp2,0); p.con(lsp2,0,p.add("#X obj 1700 355 v ockm_legacy_dl;"),0)
# the screens, for now: one length for everything (drums stay shorter if they were), a drums loop, and double
rlg=p.add("#X obj 20 800 r ockm-length;"); cl=p.add("#X obj 20 825 clip 16 256;"); gsp=p.add("#X obj 20 850 spigot 1;"); p.con(nld,0,gsp,1)
gt=p.add("#X obj 20 875 t f f;"); gd=p.add(f"#X obj 120 905 expr if(ockm_drumlen>0 && ockm_drumlen<{LOOPX} \\, min(ockm_drumlen \\, {D}f1) \\, {D}f1);")
gm=p.add(f"#X msg 20 935 \\; ockm-bass-len {D}1 \\; ockm-lead-len {D}1 \\; ockm-chord-len {D}1;"); gdm=p.add(f"#X msg 120 935 \\; ockm-drum-len {D}1;")
for c in [(rlg,0,cl,0),(cl,0,gsp,0),(gsp,0,gt,0),(gt,1,gd,0),(gd,0,gdm,0),(gt,0,gm,0)]: p.con(*c)
dsp2=p.add("#X obj 400 830 spigot 1;"); p.con(nld,0,dsp2,1); p.con(dl_t,0,dsp2,0)
dd=p.add(f"#X obj 400 855 expr if({D}f1>0 \\, {D}f1 \\, max(ockm_drumlen \\, {SYNX}));"); p.con(dsp2,0,dd,0); p.con(dd,0,p.add("#X obj 400 880 s ockm-drum-len;"),0)
# double: a part's bars copied after themselves (up to 16 bars). ockm-<part>-double, for each part
for i,pt in enumerate(PARTS):
    x=700+i*260
    rdd=p.add(f"#X obj {x} 800 r ockm-{pt}-double;"); ddx=p.add(f"#X obj {x} 825 expr ockm_{pt}len;"); ddm=p.add(f"#X obj {x} 850 moses 129;")
    ddt=p.add(f"#X obj {x} 875 t f f;"); ddv=p.add(f"#X obj {x+100} 905 v ockm_{pt}max;"); dd2=p.add(f"#X obj {x} 905 * 2;"); dds=p.add(f"#X obj {x} 935 s ockm-{pt}-len;")
    for c in [(rdd,0,ddx,0),(ddx,0,ddm,0),(ddm,0,ddt,0),(ddt,1,ddv,0),(ddt,0,dd2,0),(dd2,0,dds,0)]: p.con(*c)
    if pt=="drum":
        p.con(dd2,0,p.add(f"#X msg {x} 965 \\; ockm-drums-changed bang \\; ockm-refresh bang;"),0)
p.save("seq/ockm-lengths.pd","#N canvas 100 100 1900 1000 12;")

# ================= mono generator (bass or lead) =================
# args: track, octave offset (semitones), default rhythm, default notes
p=P()
p.add("#X text 20 10 Mono generator: builds a bass or lead line from a rhythm preset + a note pattern + the shared key. Args: track \\, octave offset \\, default rhythm \\, default notes.;")
for nm,n in [("r",64),("n",512),("s",7)]: p.add(f"#X obj {700+['r','n','s'].index(nm)*130} 60 array define {D}0-{nm} {n};")
regen=p.add("#X obj 20 330 t b b b b b;")
# Two kinds of trigger. Picking a preset (rhythm, notes) or pressing new always generates, and puts the part in auto.
# Everything else (key, scale, chords changing) only regenerates a part that is in auto. Nothing fires while a pattern loads.
rld=p.add("#X obj 120 230 r ockm-loading;"); nl0=p.add("#X obj 120 250 == 0;")
exg=p.add("#X obj 20 270 spigot 1;"); ext=p.add("#X obj 20 295 t b b;"); m0=p.add("#X msg 60 315 0;"); sm0=p.add(f"#X obj 60 340 s ockm-{D}1-mode;")
img=p.add("#X obj 300 270 spigot 1;"); ima=p.add("#X obj 300 295 spigot 1;")
rmode=p.add(f"#X obj 460 230 r ockm-{D}1-mode;"); auto=p.add("#X obj 460 255 == 0;")
lbm=p.add("#X obj 560 205 loadbang;"); fmd=p.add(f"#X obj 560 230 f {D}5;")
for c in [(rld,0,nl0,0),(nl0,0,exg,1),(nl0,0,img,1),(exg,0,ext,0),(ext,1,m0,0),(m0,0,sm0,0),(ext,0,regen,0),
          (img,0,ima,0),(ima,0,regen,0),(rmode,0,auto,0),(lbm,0,fmd,0),(fmd,0,auto,0),(auto,0,ima,1)]: p.con(*c)
store=[]
for j,(hook,dflt,kind) in enumerate([(f"ockm-{D}1-rhythm",f"{D}3","x"),(f"ockm-{D}1-notes",f"{D}4","x"),("ockm-root","9","i"),("ockm-scale","0","i")]):
    x=20+j*170
    r=p.add(f"#X obj {x} 170 r {hook};"); t=p.add(f"#X obj {x} 200 t b f;"); fs=p.add(f"#X obj {x} 290 f {dflt};")
    p.con(r,0,t,0); p.con(t,1,fs,1); p.con(t,0,exg if kind=="x" else img,0); store.append(fs)
rg=p.add(f"#X obj 720 170 r ockm-{D}1-gen;"); p.con(rg,0,ext,0)
# rhythm lock (0 own rhythm, 1 lock to kick, 2 fill the gaps), density (1 = as the preset), mutate seed (0 = the original)
var={}
for j,nm in enumerate(["lock","density","seed","outside"]):
    x=1200+j*160
    r=p.add(f"#X obj {x} 170 r ockm-{D}1-{nm};"); t=p.add(f"#X obj {x} 195 t b f;"); p.con(r,0,t,0); p.con(t,0,exg,0); var[nm]=t
lbd=p.add("#X obj 1360 120 loadbang;"); one_d=p.add("#X msg 1360 145 1;"); p.con(lbd,0,one_d,0)
# a part locked to the kick follows your drum edits
red=p.add("#X obj 1200 230 r ockm-edit;"); teb=p.add("#X obj 1200 255 t b;"); rdc=p.add("#X obj 1120 230 r ockm-drums-changed;"); p.con(rdc,0,teb,0); lkg=p.add("#X obj 1200 280 spigot;"); lk0=p.add("#X obj 1280 230 != 0;")
for c in [(red,0,teb,0),(teb,0,lkg,0),(var["lock"],1,lk0,0),(lk0,0,lkg,1),(lkg,0,img,0)]: p.con(*c)
# a new length: an auto part rebuilds to fill it (after everything else has heard the new length)
rln=p.add(f"#X obj 1400 230 r ockm-{D}1-len;"); tlb=p.add("#X obj 1400 255 t b;"); lsp=p.add("#X obj 1400 280 spigot 1;"); ldl=p.add("#X obj 1400 305 delay 0;")
for c in [(rln,0,tlb,0),(tlb,0,lsp,0),(nl0,0,lsp,1),(lsp,0,ldl,0),(ldl,0,ima,0)]: p.con(*c)
# sync: follow the chord part. When the chords change, a synced part in auto regenerates
rsy=p.add(f"#X obj 760 230 r ockm-{D}1-sync;"); nsy=p.add("#X obj 760 255 != 0;"); fsy=p.add(f"#X obj 860 230 f {D}6;")
syg=p.add("#X obj 760 300 spigot;")
rcc=p.add("#X obj 900 270 r ockm-chord-changed;"); rce=p.add("#X obj 1060 270 r ockm-chord-edit;"); tce=p.add("#X obj 1060 290 t b;")
for c in [(rsy,0,nsy,0),(lbm,0,fsy,0),(fsy,0,nsy,0),(nsy,0,syg,1),(rcc,0,syg,0),(rce,0,tce,0),(tce,0,syg,0),(syg,0,img,0)]: p.con(*c)
# a part that follows the chords takes their length too (not while a loop loads: saved lengths stay as they were)
rcl=p.add("#X obj 760 120 r ockm-chord-len;"); csp=p.add("#X obj 760 145 spigot 1;"); csy=p.add("#X obj 760 170 spigot;")
ctf=p.add("#X obj 760 195 t f b;"); cvl=p.add(f"#X obj 860 220 v ockm_{D}1len;"); cne=p.add("#X obj 760 245 !=;"); ctf2=p.add("#X obj 760 220 t f f;")
cgo=p.add("#X obj 700 270 spigot;"); csl=p.add(f"#X obj 700 295 s ockm-{D}1-len;")
for c in [(rcl,0,csp,0),(nl0,0,csp,1),(csp,0,csy,0),(nsy,0,csy,1),(csy,0,ctf,0),(ctf,1,cvl,0),(cvl,0,cne,1),(ctf,0,ctf2,0),(ctf2,1,cne,0),(cne,0,cgo,1),(ctf2,0,cgo,0),(cgo,0,csl,0)]: p.con(*c)
ts=p.add("#X obj 560 380 text get ockm-presets-scale;"); lsp=p.add("#X obj 560 410 list split 1;"); asx=p.add(f"#X obj 560 440 array set {D}0-s;")
p.con(regen,4,store[3],0); p.con(store[3],0,ts,0); p.con(ts,0,lsp,0); p.con(lsp,1,asx,0)
tn=p.add("#X obj 360 380 text get ockm-presets-notes;"); ln=p.add("#X obj 360 410 list split 1;"); tl=p.add("#X obj 360 440 t l l;")
ll=p.add("#X obj 420 470 list length;"); an=p.add(f"#X obj 360 500 array set {D}0-n;")
p.con(regen,3,store[1],0); p.con(store[1],0,tn,0); p.con(tn,0,ln,0); p.con(ln,1,tl,0); p.con(tl,1,ll,0); p.con(tl,0,an,0)
tr=p.add(f"#X obj 170 380 text get ockm-presets-{D}1rhythm;"); lr=p.add("#X obj 170 410 list split 1;"); ar=p.add(f"#X obj 170 440 array set {D}0-r;")
trl=p.add("#X obj 230 425 t l l;"); rll=p.add("#X obj 270 455 list length;")
p.con(regen,2,store[0],0); p.con(store[0],0,tr,0); p.con(tr,0,lr,0); p.con(lr,1,trl,0); p.con(trl,1,rll,0); p.con(trl,0,ar,0)
rx=p.add(f"#X obj 20 410 expr if(36+{D}f1>40 \\, 24+{D}f1 \\, 36+{D}f1);"); ro=p.add(f"#X obj 20 440 + {D}2;")
p.con(regen,1,store[2],0); p.con(store[2],0,rx,0); p.con(rx,0,ro,0)
lp=p.add("#X obj 20 560 t b b;"); p.con(regen,0,lp,0)
z1=p.add("#X msg 120 590 0;"); nl=p.add("#X obj 20 590 f 128;"); rlg=p.add(f"#X obj 80 560 r ockm-{D}1-len;"); un=p.add("#X obj 20 620 until;")
fi=p.add("#X obj 20 650 f;"); pi=p.add("#X obj 70 650 + 1;"); fh=p.add("#X obj 400 760 f;"); ph=p.add("#X obj 450 760 + 1;")
for c in [(rlg,0,nl,1),(lp,1,z1,0),(z1,0,fi,1),(z1,0,fh,1),(lp,0,nl,0),(nl,0,un,0),(un,0,fi,0),(fi,0,pi,0),(pi,0,fi,1)]: p.con(*c)
ti=p.add("#X obj 20 680 t f f f;"); p.con(fi,0,ti,0)
rcd=p.add("#X obj 860 700 tabread ockm-pat-chord-deg;")
fold=p.add(f"#X obj 860 730 expr if(int({D}f1)>=4 \\, int({D}f1)-7 \\, int({D}f1)) * {D}f2;")   # V, VI, VII sit below the root
p.con(ti,1,rcd,0); p.con(rcd,0,fold,0); p.con(nsy,0,fold,1)
tws={}
for j,nm in enumerate(["note","on","acc","slide"]):
    tws[nm]=p.add(f"#X obj {200+j*170} 900 tabwrite ockm-pat-{D}1-{nm};"); p.con(ti,2,tws[nm],1)
m16=p.add("#X obj 20 700 mod 16;"); rd=p.add(f"#X obj 20 720 tabread {D}0-r;")
kick=p.add("#X obj 1000 700 tabread ockm-pat-d1;")
lockx=p.add(f"#X obj 160 720 expr if({D}f3==1 \\, if({D}f2>0 \\, if({D}f1==2 || {D}f1==4 || {D}f2>=2 \\, 2 \\, 1) \\, 0) \\, if({D}f3==2 \\, if({D}f2>0 \\, 0 \\, {D}f1) \\, {D}f1));")
H=f"(abs(sin({D}f4*12.9898+{D}f3*78.233+1.7)*43758.5453)-floor(abs(sin({D}f4*12.9898+{D}f3*78.233+1.7)*43758.5453)))"
dens0=p.add(f"#X obj 160 735 expr if({D}f1>0 && {D}f1<5 && {D}f2<1 && {D}f1!=2 && {D}f1!=4 && {H}>{D}f2 \\, 0 \\, if({D}f1==0 && {D}f2>1 && {H}<({D}f2-1)*0.5 \\, 1 \\, {D}f1));")
# v0.86: mutate touches the rhythm (a variation, seed above 0, adds a note on about one 8th-note rest in five and drops about
# one plain note in seven; accents and held notes stay), and the bass's last bar of a loop of 2 bars or more gets a pickup into the
# start (a note on its last 8th if it was resting). Same seed, same result, so a variation repeats steadily
H2=f"(abs(sin({D}f2*12.9898+{D}f3*78.233+7.7)*43758.5453)-floor(abs(sin({D}f2*12.9898+{D}f3*78.233+7.7)*43758.5453)))"
dens=p.add(f"#X obj 160 760 expr if({D}f3>0 && {D}f1==0 && int({D}f2)%2==0 && {H2}<0.2 \\, 1 \\, if({D}f3>0 && {D}f1==1 && {H2}>0.85 \\, 0 \\, if({D}f5==0 && {D}f4>=32 && int({D}f2)>={D}f4-16 && int({D}f2)%16==14 && {D}f1==0 \\, 1 \\, {D}f1)));")
p.con(dens0,0,dens,0)
cx=p.add(f"#X obj 20 745 expr {D}f1>0 \\; {D}f1==2 || {D}f1==4 \\; {D}f1>=3 && {D}f1!=6 \\; {D}f1>0 && {D}f1<5 \\; {D}f1>=5;")
p.con(rll,0,m16,1)   # a four-bar rhythm repeats every 64 steps
for c in [(ti,0,m16,0),(m16,0,rd,0),(rd,0,lockx,0),(lockx,0,dens0,0),(dens,0,cx,0),(cx,2,tws["slide"],0),(cx,1,tws["acc"],0),
          (ti,1,kick,0),(kick,0,lockx,1),(var["lock"],1,lockx,2),(var["density"],1,dens0,1),(one_d,0,dens0,1),(var["seed"],1,dens0,2),(ti,1,dens0,3),
          (ti,1,dens,1),(var["seed"],1,dens,2),(rlg,0,dens,3)]: p.con(*c)
to=p.add("#X obj 20 780 t f f;"); s1=p.add("#X obj 20 810 sel 1;"); th=p.add("#X obj 400 790 t f f;")
ix=p.add(f"#X obj 400 820 expr if(int({D}f2)==512 \\, (int({D}f3)%8)*64 + int({D}f4)%64 \\, int({D}f1+{D}f3) % int({D}f2));"); rn=p.add(f"#X obj 400 845 tabread {D}0-n;"); td=p.add("#X obj 400 870 t f f;")
sx=p.add(f"#X obj 560 870 expr ((int({D}f1)%7)+7)%7;"); rs=p.add(f"#X obj 560 895 tabread {D}0-s;")
addc=p.add("#X obj 400 857 + 0;")
ojump=p.add(f"#X obj 400 850 expr {D}f1 + 7*({D}f4!=512 && {D}f2>0 && (abs(sin({D}f3*7.13+{D}f2*3.7+0.3)*9137.21)-floor(abs(sin({D}f3*7.13+{D}f2*3.7+0.3)*9137.21)))<0.2);")
p.con(var["seed"],1,ix,2); p.con(var["seed"],1,ojump,1); p.con(ti,1,ojump,2); p.con(ti,1,ix,3); p.con(ll,0,ojump,3)
# the lead (arg 7): on the beat, a note that isn't in the chord moves to the nearest one that is
_R=f"((int({D}f1)%7+7)%7)"
# inside to outside (ockm-<track>-outside 0-1, the lead; v0.81). Degrees here are counted from the chord's root, so 0 2 4 are
# chord notes. Below 0.25 every note moves onto the chord. From 0.25 only the notes on the beat do, and more and more notes
# between the beats step to a neighbour (passing notes). From 0.5 some notes on the beat become the chord's 7th or 9th
# (colour). From 0.75 some leap up an octave, and (after the note is worked out, below) some off-beat notes slip a semitone
# down (chromatic). Which notes is decided by the step and the mutate seed, so each variation decorates differently but repeats.
def _h(k): return f"(abs(sin({D}f2*12.9898+{D}f5*78.233+{k})*43758.5453)-floor(abs(sin({D}f2*12.9898+{D}f5*78.233+{k})*43758.5453)))"
_SN=f"({D}f1 - ({_R}==1 || {_R}==3 || {_R}==5) + ({_R}==6))"
_ST=f"(int({D}f2)%4==0)"
_IN=f"if({_ST} \\, if({D}f4>=0.5 && {_h(1.1)}<({D}f4-0.5) \\, {D}f1-{_R}+6+2*({_h(2.3)}<0.5) \\, {_SN}) \\, if({_h(3.7)}<({D}f4-0.25)*1.2 \\, {D}f1+1-2*({_h(4.1)}<0.5) \\, {D}f1))"
_LP=f"7*({D}f4>=0.75 && {_h(5.3)}<({D}f4-0.75)*1.2)"
snap=p.add(f"#X obj 400 860 expr if({D}f3>0 \\, if({D}f4<0.25 \\, {_SN} \\, {_IN} + {_LP}) \\, {D}f1);")
fsn=p.add(f"#X obj 560 820 f {D}7;"); p.con(lbm,0,fsn,0); p.con(fsn,0,snap,2); p.con(ti,1,snap,1)
p.con(fsn,0,dens,4)   # the pickup is the bass's: the lead's phrases already land where they mean to
p.con(var["outside"],1,snap,3); fr1=p.add("#X msg 640 820 0.35;"); p.con(lbm,0,fr1,0); p.con(fr1,0,snap,3)
p.con(var["seed"],1,snap,4)
nx=p.add(f"#X obj 400 930 expr {D}f2 + 12*floor({D}f1/7) + {D}f3;")
# a hold writes the note before it again (the same pitch, sliding on), without moving on through the note list
hsel=p.add("#X obj 700 780 sel 1;"); hlast=p.add("#X obj 700 805 f;")
_HC=f"(abs(sin({D}f2*12.9898+{D}f4*78.233+6.7)*43758.5453)-floor(abs(sin({D}f2*12.9898+{D}f4*78.233+6.7)*43758.5453)))"
chrom=p.add(f"#X obj 400 945 expr {D}f1 - ({D}f5>0 && {D}f3>=0.75 && int({D}f2)%4!=0 && {_HC}<({D}f3-0.75)*1.6);")
p.con(ti,1,chrom,1); p.con(var["outside"],1,chrom,2); p.con(fr1,0,chrom,2); p.con(var["seed"],1,chrom,3); p.con(fsn,0,chrom,4)
for c in [(cx,4,hsel,0),(hsel,0,hlast,0),(hlast,0,tws["note"],0),(chrom,0,hlast,1)]: p.con(*c)
for c in [(cx,0,tws["on"],0),(cx,3,s1,0),(s1,0,fh,0),(fh,0,th,0),(th,1,ph,0),(ph,0,fh,1),(th,0,ix,0),(ll,0,ix,1),(ix,0,rn,0),(rn,0,ojump,0),(ojump,0,snap,0),(snap,0,addc,0),(fold,0,addc,1),(addc,0,td,0),
          (td,1,sx,0),(sx,0,rs,0),(rs,0,nx,2),(td,0,nx,0),(ro,0,nx,1),(nx,0,chrom,0),(chrom,0,tws["note"],0)]: p.con(*c)
p.add("#X text 20 980 hooks: ockm-<track>-rhythm 0-7 \\, ockm-<track>-notes 0-11 \\, ockm-<track>-gen (rebuild) \\, ockm-<track>-mode (0 auto \\, 1 manual) \\, ockm-<track>-sync (follow the chords) \\, ockm-<track>-lock (0 own rhythm \\, 1 lock to kick \\, 2 fill the gaps) \\, ockm-<track>-density (0-2 \\, 1 = the preset) \\, ockm-<track>-seed (mutate: 0 = the original) \\, and the shared ockm-root 0-11 and ockm-scale 0-5. Args: track \\, octave \\, rhythm \\, notes \\, default mode \\, default sync.;")
p.save("seq/ockm-monogen.pd","#N canvas 120 120 1100 1020 12;")

# ================= LFO (one per synth) =================
# Sits between a synth's four knobs and the synth: ockm-<part>-k1..k4 (your settings) in, ockm-<part>-k1-m..k4-m out.
# With depth 0, or for the knobs it isn't moving, the knob passes straight through. Its phase restarts with the loop,
# so it stays in time. Shapes: 0 sine 1 triangle 2 square 3 saw 4 sample-and-hold. Rate: 0 1/16, 1 1/8, 2 1/4, 3 1/2,
# 4 1 bar, 5 2 bars, 6 4 bars, 7 8 bars. Target 1-4: which knob. Depth 0-1 (1 swings the knob by half its range each way).
for PT in ("bass","lead","chord"):
    p=P()
    p.add(f"#X text 20 10 LFO for the {PT}: moves one of its four knobs in time with the loop.;")
    for k in range(1,5):
        x=20+(k-1)*200
        rk=p.add(f"#X obj {x} 60 r ockm-{PT}-k{k};"); tk=p.add(f"#X obj {x} 85 t f f;"); vk=p.add(f"#X obj {x+60} 110 v ockm_{PT}_b{k};")
        ok=p.add(f"#X obj {x} 140 expr if(ockm_{PT}_lt=={k} \\, min(1 \\, max(0 \\, {D}f1+ockm_{PT}_mv)) \\, {D}f1);")
        sk=p.add(f"#X obj {x} 170 s ockm-{PT}-k{k}-m;")
        for c in [(rk,0,tk,0),(tk,1,vk,0),(tk,0,ok,0),(ok,0,sk,0)]: p.con(*c)
    for nm,dflt in [("shape",0),("rate",4),("depth",0)]:
        x={"shape":20,"rate":220,"depth":420}[nm]
        rr=p.add(f"#X obj {x} 230 r ockm-{PT}-lfo-{nm};"); vv=p.add(f"#X obj {x} 255 v ockm_{PT}_l{nm[0]};")
        lb=p.add(f"#X obj {x+100} 205 loadbang;"); dm=p.add(f"#X msg {x+100} 230 {dflt};")
        for c in [(rr,0,vv,0),(lb,0,dm,0),(dm,0,vv,0)]: p.con(*c)
    # a new target: the knob it was moving goes back to its setting
    rt=p.add(f"#X obj 620 230 r ockm-{PT}-lfo-target;"); tt=p.add("#X obj 620 255 t f f;"); fo=p.add("#X obj 680 280 f 1;"); vt=p.add(f"#X obj 620 305 v ockm_{PT}_lt;")
    lbt=p.add("#X obj 760 205 loadbang;"); d1=p.add("#X msg 760 230 1;")
    sel=p.add("#X obj 680 330 sel 1 2 3 4;")
    for c in [(rt,0,tt,0),(tt,1,fo,0),(tt,0,fo,1),(tt,0,vt,0),(fo,0,sel,0),(lbt,0,d1,0),(d1,0,vt,0)]: p.con(*c)
    for k in range(1,5):
        bx=p.add(f"#X obj {600+k*90} 360 expr ockm_{PT}_b{k};"); bs=p.add(f"#X obj {600+k*90} 385 s ockm-{PT}-k{k}-m;")
        p.con(sel,k-1,bx,0); p.con(bx,0,bs,0)
    # the clock: every 20 ms, move the phase on by 20 ms worth of the rate; the loop starting puts it back to 0
    lbm=p.add("#X obj 20 420 loadbang;"); met=p.add("#X obj 20 445 metro 20;")
    ph=p.add(f"#X obj 20 470 expr fmod(ockm_{PT}_ph+20/max(1 \\, ockm_stepms*pow(2 \\, int(ockm_{PT}_lr))) \\, 1) \\; ockm_{PT}_ph;")
    tph=p.add("#X obj 20 500 t f f;"); vph=p.add(f"#X obj 100 530 v ockm_{PT}_ph;")
    # a wrap (new phase below the old) picks a new sample-and-hold value
    wr=p.add("#X obj 220 500 <;"); wsel=p.add("#X obj 220 525 sel 1;"); rnd=p.add("#X obj 220 550 random 2001;"); rsc=p.add(f"#X obj 220 575 expr {D}f1/1000-1;"); vsh=p.add(f"#X obj 220 600 v ockm_{PT}_sh;")
    shp=p.add(f"#X obj 20 560 expr if(int(ockm_{PT}_ls)==1 \\, 4*abs({D}f1-0.5)-1 \\, if(int(ockm_{PT}_ls)==2 \\, if({D}f1<0.5 \\, 1 \\, -1) \\, if(int(ockm_{PT}_ls)==3 \\, 2*{D}f1-1 \\, if(int(ockm_{PT}_ls)==4 \\, ockm_{PT}_sh \\, sin(6.2831853*{D}f1)))));")
    mv=p.add(f"#X obj 20 590 expr {D}f1*ockm_{PT}_ld*0.5;"); vmv=p.add(f"#X obj 20 620 v ockm_{PT}_mv;")
    # send the moving knob (only while there's some depth, plus once more as depth reaches 0)
    go=p.add(f"#X obj 20 650 expr ockm_{PT}_lt;"); sel2=p.add("#X obj 20 680 sel 1 2 3 4;")
    gate=p.add(f"#X obj 20 625 expr ockm_{PT}_ld>0 || ockm_{PT}_was>0;"); spg=p.add("#X obj 20 640 sel 0;")
    tgw=p.add("#X obj 120 620 t b b;"); wasx=p.add(f"#X obj 260 625 expr ockm_{PT}_ld;")   # send first, then remember the depth
    vwas=p.add(f"#X obj 160 650 v ockm_{PT}_was;")
    tb1=p.add("#X obj 120 605 t b f;"); tb2=p.add("#X obj 120 645 t b;")   # store the swing, then the expressions that read it (they want a bang)
    for k in range(1,5):
        mx=p.add(f"#X obj {20+(k-1)*120} 710 expr min(1 \\, max(0 \\, ockm_{PT}_b{k}+ockm_{PT}_mv));"); ms=p.add(f"#X obj {20+(k-1)*120} 735 s ockm-{PT}-k{k}-m;")
        p.con(sel2,k-1,mx,0); p.con(mx,0,ms,0)
    rst=p.add("#X obj 400 420 r ockm-step;"); s0=p.add("#X obj 400 445 sel 0;"); z=p.add("#X msg 400 470 0;"); vz=p.add(f"#X obj 400 495 v ockm_{PT}_ph;")
    for c in [(lbm,0,met,0),(met,0,ph,0),(ph,1,wr,1),(ph,0,tph,0),(tph,1,vph,0),(tph,1,wr,0),(wr,0,wsel,0),(wsel,0,rnd,0),(rnd,0,rsc,0),(rsc,0,vsh,0),
              (tph,0,shp,0),(shp,0,mv,0),(mv,0,tb1,0),(tb1,1,vmv,0),(tb1,0,tgw,0),(tgw,1,gate,0),(tgw,0,wasx,0),(wasx,0,vwas,0),(gate,0,spg,0),(spg,1,tb2,0),(tb2,0,go,0),(go,0,sel2,0),
              (rst,0,s0,0),(s0,0,z,0),(z,0,vz,0)]: p.con(*c)
    p.save(f"seq/ockm-lfo-{PT}.pd","#N canvas 120 120 1100 780 12;")

# ================= chorus (one per synth) =================
# Juno-style: two delay taps swept in opposite directions by one slow LFO, mixed with the dry sound.
# ockm-<part>-chorus: 0 off (dry only) \, 1 I (slow) \, 2 II (deeper) \, 3 I+II (fast and shallow)
q=P()
q.add("#X text 20 10 Chorus for a synth (ockm-<part>-chorus 0 off \\, 1 I \\, 2 II \\, 3 I+II). Off is exactly the dry sound.;")
inl=q.add("#X obj 30 40 inlet~;"); dw=q.add(f"#X obj 200 80 delwrite~ {D}0-ch 40;")
rc=q.add(f"#X obj 400 40 r ockm-{D}1-chorus;"); sel=q.add("#X obj 400 65 sel 0 1 2 3;")
modes=[(0.5,0,1,0),(0.513,1.6,0.8,0.65),(0.863,2.3,0.8,0.65),(8.5,0.25,0.85,0.55)]   # rate Hz, depth ms, dry, wet
ms=[q.add(f"#X msg {400+i*110} 95 {rt} {dp} {dr} {wt};") for i,(rt,dp,dr,wt) in enumerate(modes)]
up=q.add("#X obj 400 130 unpack f f f f;")
lfo=q.add("#X obj 200 140 osc~ 0.5;"); dep=q.add("#X obj 200 170 *~;")
c1=q.add("#X obj 200 200 +~ 5;"); inv=q.add("#X obj 320 200 *~ -1;"); c2=q.add("#X obj 320 225 +~ 5;")
v1=q.add(f"#X obj 200 260 vd~ {D}0-ch;"); v2=q.add(f"#X obj 320 260 vd~ {D}0-ch;")
ws=q.add("#X obj 200 290 +~;"); wg=q.add("#X obj 200 320 *~;"); wl=q.add("#X obj 520 290 line~;"); wpk=q.add("#X obj 520 265 pack f 30;")
dg=q.add("#X obj 30 320 *~;"); dl=q.add("#X obj 640 290 line~;"); dpk=q.add("#X obj 640 265 pack f 30;")
dpl=q.add("#X obj 760 265 pack f 30;"); dpln=q.add("#X obj 760 290 line~;")
sm=q.add("#X obj 30 360 +~;"); out=q.add("#X obj 30 390 outlet~;")
lb=q.add("#X obj 640 200 loadbang;"); one=q.add("#X msg 640 225 1;")
for c in [(inl,0,dw,0),(inl,0,dg,0),(rc,0,sel,0),(up,0,lfo,0),(up,1,dpk,0),(dpk,0,dl,0),(up,2,dpl,0),(dpl,0,dpln,0),(up,3,wpk,0),(wpk,0,wl,0),
          (lfo,0,dep,0),(dl,0,dep,1),(dep,0,c1,0),(dep,0,inv,0),(inv,0,c2,0),(c1,0,v1,0),(c2,0,v2,0),(v1,0,ws,0),(v2,0,ws,1),
          (ws,0,wg,0),(wl,0,wg,1),(dpln,0,dg,1),(dg,0,sm,0),(wg,0,sm,1),(sm,0,out,0),(lb,0,one,0),(one,0,dpl,0)]: q.con(*c)
for i,m in enumerate(ms): q.con(sel,i,m,0); q.con(m,0,up,0)
q.save("voices/ockm-chorus.pd","#N canvas 160 160 900 420 12;")

# ================= chord sequencer =================
p=P()
p.add("#X text 20 10 Chord pattern. Each step has on/accent and a chord root (scale step). Notes are worked out as it plays \\, so key \\, scale and chord type changes apply straight away.;")
inl=p.add("#X obj 30 50 inlet;"); out=p.add("#X obj 30 700 outlet;")
p.add(f"#X obj 30 760 table ockm-pat-{D}1-on {STEPS};"); p.add(f"#X obj 230 760 table ockm-pat-{D}1-deg {STEPS};")
# v0.90: the notes are worked out in Lua (seq/ockm-chordnotes.pd_lua, written above), shared with the screen
cn=p.add("#X obj 30 600 ockm-chordnotes;")
lb=p.add("#X obj 700 40 loadbang;"); lbt=p.add("#X obj 700 65 t b b b;")
d0a=p.add("#X msg 700 90 0;"); d0b=p.add("#X msg 760 90 0;"); d9=p.add("#X msg 820 90 9;")
rsc=p.add("#X obj 700 120 r ockm-scale;"); tsc=p.add("#X obj 700 150 text get ockm-presets-scale;"); lsc=p.add("#X obj 700 175 list split 1;")
rty=p.add(f"#X obj 900 120 r ockm-{D}1-type;")
rvo=p.add(f"#X obj 1400 120 r ockm-{D}1-voicing;")   # 0 close, 1 open, 2 wide
rsm=p.add(f"#X obj 1250 120 r ockm-{D}1-smooth;"); one_sm=p.add("#X msg 1250 90 1;"); p.con(lb,0,one_sm,0)   # smooth voicing on by default
rro=p.add("#X obj 1100 120 r ockm-root;")
for c in [(lb,0,lbt,0),(lbt,2,d0a,0),(lbt,1,d0b,0),(lbt,0,d9,0),(d0a,0,tsc,0),(rsc,0,tsc,0),(tsc,0,lsc,0)]: p.con(*c)
for i,(srcs,sel) in enumerate([([lsc],"scale"),([rty,d0b],"type"),([rro,d9],"root"),([rsm,one_sm],"smooth"),([rvo],"voicing")]):
    pp=p.add(f"#X obj {700+i*150} 230 list prepend {sel};"); tr=p.add(f"#X obj {700+i*150} 255 list trim;")
    for sr in srcs: p.con(sr,1 if sr is lsc else 0,pp,0)
    p.con(pp,0,tr,0); p.con(tr,0,cn,0)
cmod=p.add("#X obj 30 65 mod 256;"); p.con(p.add(f"#X obj 100 40 r ockm-{D}1-len;"),0,cmod,1)
ts=p.add("#X obj 30 80 t f f;"); rdeg0=p.add(f"#X obj 200 95 tabread ockm-pat-{D}1-deg;"); ron=p.add(f"#X obj 30 110 tabread ockm-pat-{D}1-on;")
rdeg=p.add(f"#X obj 200 115 expr if(ockm_turn_on \\, 4 \\, {D}f1);"); p.con(rdeg0,0,rdeg,0)
tdeg=p.add("#X obj 200 140 t f f;"); trn=p.add(f"#X obj 300 170 expr ockm_turn_on+0*{D}f1;")
son=p.add("#X obj 30 140 sel 0;"); vx=p.add(f"#X obj 70 170 expr if({D}f1>1 \\, 1 \\, 0.75);")
hp=p.add("#X obj 70 230 pack f f f;"); hpp=p.add("#X obj 70 260 list prepend hit;"); hpt=p.add("#X obj 70 285 list trim;")
sno=p.add(f"#X obj 200 700 s ockm-{D}1-notes-out;")
for c in [(inl,0,cmod,0),(cmod,0,ts,0),(ts,1,rdeg0,0),(rdeg,0,tdeg,0),(tdeg,1,trn,0),(trn,0,hp,2),(tdeg,0,hp,1),(ts,0,ron,0),(ron,0,son,0),
          (son,1,vx,0),(vx,0,hp,0),(hp,0,hpp,0),(hpp,0,hpt,0),(hpt,0,cn,0),(cn,0,out,0),(cn,0,sno,0)]: p.con(*c)
# store / load / edit / extend
re=p.add(f"#X obj 1300 600 r ockm-{D}1-edit;"); tl=p.add("#X obj 1300 630 t l l;"); ls=p.add("#X obj 1480 660 list split 1;"); up=p.add("#X obj 1300 690 unpack f f f;")
p.con(re,0,tl,0); p.con(tl,1,ls,0); p.con(tl,0,up,0)
rx=p.add(f"#X obj 1700 300 r ockm-{D}1-extend;"); ux=p.add("#X obj 1700 330 unpack f f;")
cnt=p.add(f"#X obj 1700 390 expr {D}f2-{D}f1;"); txo=p.add("#X obj 1700 360 t f f;"); mo=p.add("#X obj 1700 420 moses 1;"); ux2=p.add("#X obj 1760 450 until;")
ci=p.add("#X obj 1760 480 f;"); cip=p.add("#X obj 1810 480 + 1;"); tci=p.add("#X obj 1760 510 t f f;")
md=p.add(f"#X obj 1760 540 expr {D}f1 % {D}f2;"); t2=p.add("#X obj 1760 570 t f f;")
for c in [(rx,0,ux,0),(ux,1,cnt,1),(ux,0,txo,0),(txo,1,ci,1),(txo,1,md,1),(txo,0,cnt,0),(cnt,0,mo,0),(mo,1,ux2,0),
          (ux2,0,ci,0),(ci,0,cip,0),(cip,0,ci,1),(ci,0,tci,0),(tci,0,md,0),(md,0,t2,0)]: p.con(*c)
for j,nm in enumerate(["on","deg"]):
    x=1300+j*190
    tw=p.add(f"#X obj {x} 730 tabwrite ockm-pat-{D}1-{nm};"); p.con(ls,0,tw,1); p.con(up,j+1,tw,0)
    xr=p.add(f"#X obj {1700+j*120} 610 tabread ockm-pat-{D}1-{nm};"); xw=p.add(f"#X obj {1700+j*120} 640 tabwrite ockm-pat-{D}1-{nm};")
    p.con(t2,1-j,xr,0); p.con(xr,0,xw,0); p.con(tci,1,xw,1)
p.add("#X text 1300 570 edit one step: ockm-<track>-edit <step> <0 off 1 on 2 accent> <chord root as scale step>;")
p.save("seq/ockm-chordseq.pd","#N canvas 100 100 1950 800 12;")

# ================= chord generator =================
p=P()
p.add("#X text 20 10 Chord generator: a chord rhythm preset plus a progression. Progressions are stored as their natural length in steps plus one chord root per step. If the pattern is shorter than the progression \\, it is made longer first. Writes on/accent and chord roots across the whole pattern length.;")
p.add(f"#X obj 600 60 array define {D}0-r 32;"); p.add(f"#X obj 760 60 array define {D}0-p 128;")
regen=p.add("#X obj 20 250 t b b b b b;")
gate=p.add("#X obj 20 200 spigot 1;"); rld=p.add("#X obj 120 160 r ockm-loading;"); nl0=p.add("#X obj 120 180 == 0;")
gt=p.add("#X obj 20 225 t b b;"); m0=p.add("#X msg 60 225 0;"); sm0=p.add(f"#X obj 60 245 s ockm-{D}1-mode;")
p.con(gate,0,gt,0); p.con(gt,1,m0,0); p.con(m0,0,sm0,0); p.con(gt,0,regen,0); p.con(rld,0,nl0,0); p.con(nl0,0,gate,1)
# a new length: chords on auto rebuild to fill it, without stretching the pattern back out
rln=p.add(f"#X obj 700 160 r ockm-{D}1-len;"); tlb=p.add("#X obj 700 180 t b;"); lsp=p.add("#X obj 700 200 spigot 1;"); p.con(nl0,0,lsp,1)
rcm=p.add(f"#X obj 820 160 r ockm-{D}1-mode;"); cm0=p.add("#X obj 820 180 == 0;"); asp=p.add("#X obj 700 225 spigot 1;"); p.con(rcm,0,cm0,0); p.con(cm0,0,asp,1)
ldl=p.add("#X obj 700 250 delay 0;"); tnf=p.add("#X obj 700 275 t b b b;"); n1=p.add("#X msg 800 300 1;"); n0=p.add("#X msg 700 325 0;"); vn1=p.add("#X obj 800 325 v ockm_cg_nofit;"); vn0=p.add("#X obj 700 350 v ockm_cg_nofit;")
for c in [(rln,0,tlb,0),(tlb,0,lsp,0),(lsp,0,asp,0),(asp,0,ldl,0),(ldl,0,tnf,0),(tnf,2,n1,0),(n1,0,vn1,0),(tnf,1,regen,0),(tnf,0,n0,0),(n0,0,vn0,0)]: p.con(*c)
done=p.add("#X obj 20 730 s ockm-chord-changed;"); p.con(regen,0,done,0)
store=[]
for j,(hook,d) in enumerate([(f"ockm-{D}1-rhythm",0),(f"ockm-{D}1-prog",0)]):
    x=20+j*200
    r=p.add(f"#X obj {x} 100 r {hook};"); t=p.add(f"#X obj {x} 130 t b f;"); fs=p.add(f"#X obj {x} 210 f {d};")
    p.con(r,0,t,0); p.con(t,1,fs,1); p.con(t,0,gate,0); store.append(fs)
rg=p.add(f"#X obj 450 100 r ockm-{D}1-gen;"); p.con(rg,0,gt,0)
# progression: natural length, then one chord root per step
tp=p.add("#X obj 500 300 text get ockm-presets-progx;"); lpp=p.add("#X obj 500 330 list split 1;"); lp2=p.add("#X obj 500 360 list split 1;")
plen=p.add("#X obj 500 420 f 16;"); ap=p.add(f"#X obj 620 390 array set {D}0-p;")
for c in [(regen,4,store[1],0),(store[1],0,tp,0),(tp,0,lpp,0),(lpp,1,lp2,0),(lp2,0,plen,1),(lp2,1,ap,0)]: p.con(*c)
# rhythm: 16 or 32 steps
tr=p.add("#X obj 100 300 text get ockm-presets-chordrhythm;"); lr=p.add("#X obj 100 330 list split 1;"); tlr=p.add("#X obj 100 360 t l l;")
llr=p.add("#X obj 160 390 list length;"); ar=p.add(f"#X obj 100 420 array set {D}0-r;")
for c in [(regen,3,store[0],0),(store[0],0,tr,0),(tr,0,lr,0),(lr,1,tlr,0),(tlr,1,llr,0),(tlr,0,ar,0)]: p.con(*c)
# make the pattern long enough for the progression (never shorter)
curl=p.add(f"#X obj 360 470 r ockm-{D}1-len;"); fit=p.add(f"#X obj 300 500 expr if(ockm_cg_nofit \\, 0 \\, if({D}f1!={D}f2 \\, max({D}f1 \\, 16) \\, 0));"); sz=p.add("#X obj 300 530 sel 0;"); sl=p.add(f"#X obj 340 560 s ockm-{D}1-len;")
for c in [(regen,2,plen,0),(plen,0,fit,0),(curl,0,fit,1),(fit,0,sz,0),(sz,1,sl,0)]: p.con(*c)
# write every step of the pattern
z1=p.add("#X msg 120 470 0;"); nl=p.add("#X obj 20 470 f 128;"); rlg=p.add(f"#X obj 80 440 r ockm-{D}1-len;"); un=p.add("#X obj 20 500 until;")
fi=p.add("#X obj 20 530 f;"); pi=p.add("#X obj 70 530 + 1;"); ti=p.add("#X obj 20 560 t f f;"); tl2=p.add("#X obj 20 590 t f f;")
for c in [(regen,1,z1,0),(regen,1,nl,0),(rlg,0,nl,1),(z1,0,fi,1),(nl,0,un,0),(un,0,fi,0),(fi,0,pi,0),(pi,0,fi,1),(fi,0,ti,0),(ti,0,tl2,0)]: p.con(*c)
two=p.add(f"#X obj 200 700 tabwrite ockm-pat-{D}1-on;"); twd=p.add(f"#X obj 400 700 tabwrite ockm-pat-{D}1-deg;")
bx=p.add(f"#X obj 300 620 expr int({D}f1) % int(max({D}f2\\,1));"); rp=p.add(f"#X obj 300 650 tabread {D}0-p;")
mr=p.add(f"#X obj 20 620 expr int({D}f1) % int(max({D}f2\\,1));"); rr=p.add(f"#X obj 20 650 tabread {D}0-r;")
for c in [(ti,1,two,1),(ti,1,twd,1),(tl2,1,bx,0),(plen,0,bx,1),(bx,0,rp,0),(rp,0,twd,0),(tl2,0,mr,0),(llr,0,mr,1),(mr,0,rr,0),(rr,0,two,0)]: p.con(*c)
p.add("#X text 20 760 hooks: ockm-<track>-rhythm 0-9 \\, ockm-<track>-prog 0-9 \\, ockm-<track>-gen (rebuild). Presets live in tools/build.py (PRE and PROGS).;")
p.save("seq/ockm-chordgen.pd","#N canvas 120 120 900 800 12;")

# ================= drum grooves =================
p=P()
p.add("#X text 20 10 Drum grooves: ockm-drum-groove <n> writes a groove into every drum slot \\, by the sound each slot plays \\, across the whole pattern length. Sets the swing too. Ignored while a pattern loads. Then tells the screens and any part locked to the kick.;")
r=p.add("#X obj 20 60 r ockm-drum-groove;"); gate=p.add("#X obj 20 90 spigot 1;"); rld=p.add("#X obj 140 60 r ockm-loading;"); nl0=p.add("#X obj 140 85 == 0;")
mo=p.add("#X obj 20 120 moses 0;"); t=p.add("#X obj 60 150 t b b f f;")
tg=p.add("#X obj 260 190 text get ockm-presets-groove;"); l1=p.add("#X obj 260 220 list split 1;"); l2=p.add("#X obj 260 250 list split 1;")
sw=p.add("#X obj 260 280 moses 1;"); ssw=p.add("#X obj 300 310 s ockm-swing;")
go=p.add("#X obj 160 190 s ockm-groove-go;"); rf=p.add("#X obj 60 340 s ockm-refresh;"); dc=p.add("#X obj 110 310 s ockm-drums-changed;")
# a groove is one bar: the drums become 1 bar, starting afresh (go longer and the groove repeats, not whatever was there)
gl=p.add("#X msg 160 150 \\; ockm-drum-len 16;"); gm=p.add("#X msg 260 150 16;"); gv=p.add("#X obj 260 170 v ockm_drummax;")
p.con(t,3,gm,0); p.con(gm,0,gv,0); p.con(t,3,gl,0)
for c in [(r,0,gate,0),(rld,0,nl0,0),(nl0,0,gate,1),(gate,0,mo,0),(mo,1,t,0),(t,3,tg,0),(tg,0,l1,0),(l1,1,l2,0),(l2,0,sw,0),(sw,1,ssw,0),
          (t,2,go,0),(t,1,dc,0),(t,0,rf,0)]: p.con(*c)
# fills: on the last bar of every 4, 8 or 16 bars (counted from play), the drums play the chosen fill
p.add(f"#X obj 500 20 table ockm-fillx 128;")
lbf=p.add("#X obj 500 50 loadbang;"); m1=p.add("#X msg 500 75 const -1;"); p.con(lbf,0,m1,0)
q_tab=p.add("#X obj 500 100 s ockm-fillx;"); p.con(m1,0,q_tab,0)
rst=p.add("#X obj 500 140 r ockm-fill-style;"); tgs=p.add("#X obj 500 165 text get ockm-presets-fill;"); ls1=p.add("#X obj 500 190 list split 1;"); asf=p.add("#X obj 500 215 array set ockm-fillx;")
for c in [(rst,0,tgs,0),(tgs,0,ls1,0),(ls1,1,asf,0)]: p.con(*c)
p.con(lbf,0,p.add("#X msg 600 75 0;"),0)
ini=p.add("#X msg 600 100 0;"); p.con(lbf,0,ini,0); p.con(ini,0,tgs,0)
rev=p.add("#X obj 700 140 r ockm-fill-every;"); fev=p.add("#X obj 700 165 f 0;"); p.con(rev,0,fev,1)
rb=p.add("#X obj 500 260 r ockm-bar;"); tbb=p.add("#X obj 500 285 t b b;"); cnt=p.add("#X obj 500 310 f 0;"); inc=p.add("#X obj 550 310 + 1;")
on=p.add(f"#X obj 500 360 expr if({D}f2>0 \\, ({D}f1 % {D}f2) == {D}f2-1 \\, 0);"); von=p.add("#X obj 500 385 v ockm_fill_on;")
sfo=p.add("#X obj 600 385 s ockm-fill-now;")
for c in [(rb,0,tbb,0),(tbb,1,fev,0),(fev,0,on,1),(tbb,0,cnt,0),(cnt,0,inc,0),(inc,0,cnt,1),(cnt,0,on,0),(on,0,von,0),(on,0,sfo,0)]: p.con(*c)
# turnaround: on the last bar of every 4, 8 or 16 bars the harmony goes to V (major) and leads back to the start
rtv=p.add("#X obj 820 140 r ockm-turn-every;"); ftv=p.add("#X obj 820 165 f 0;"); p.con(rtv,0,ftv,1)
tbt=p.add("#X obj 820 285 t f b;"); ton=p.add(f"#X obj 820 360 expr if({D}f2>0 \\, ({D}f1 % {D}f2) == {D}f2-1 \\, 0);"); vton=p.add("#X obj 820 385 v ockm_turn_on;")
for c in [(cnt,0,tbt,0),(tbt,1,ftv,0),(ftv,0,ton,1),(tbt,0,ton,0),(ton,0,vton,0)]: p.con(*c)   # the setting first, then the bar
# play starts the count again; stop ends any fill
rpl=p.add("#X obj 700 260 r ockm-play;"); tpl=p.add("#X obj 700 285 t b f;"); z0=p.add("#X msg 700 310 0;"); z1=p.add("#X msg 760 310 0;"); von2=p.add("#X obj 760 335 v ockm_fill_on;")
for c in [(rpl,0,tpl,0),(tpl,0,z0,0),(z0,0,cnt,1),(tpl,0,z1,0),(z1,0,von2,0)]: p.con(*c)
p.con(z1,0,p.add("#X obj 860 335 v ockm_turn_on;"),0)
p.save("seq/ockm-grooves.pd","#N canvas 120 120 700 400 12;")

p=P()
p.add(f"#X text 20 10 One drum slot's share of a groove: picks the 16 steps for the sound this slot plays \\, then repeats them across the pattern. Args: slot \\, default sound.;")
p.add(f"#X obj 500 60 array define {D}0-g 16;")
lb=p.add("#X obj 300 40 loadbang;"); snd0=p.add(f"#X obj 300 65 f {D}2;"); rs=p.add(f"#X obj 380 65 r ockm-{D}1-sound;"); m16=p.add("#X obj 300 95 * 16;")
p.con(lb,0,snd0,0); p.con(snd0,0,m16,0); p.con(rs,0,m16,0)
r=p.add("#X obj 20 60 r ockm-groove-go;"); t=p.add("#X obj 20 90 t b f;")
tg=p.add("#X obj 120 120 text get ockm-presets-groove;"); l1=p.add("#X obj 120 150 list split 2;"); ls=p.add("#X obj 120 180 list split 0;"); l16=p.add("#X obj 120 210 list split 16;")
ag=p.add(f"#X obj 120 240 array set {D}0-g;")
for c in [(r,0,t,0),(t,1,tg,0),(tg,0,l1,0),(l1,1,ls,0),(m16,0,ls,1),(ls,1,l16,0),(l16,0,ag,0)]: p.con(*c)
ln=p.add("#X obj 20 270 f 128;"); rl=p.add("#X obj 80 245 r ockm-drum-len;"); z=p.add("#X msg 80 270 0;")
un=p.add("#X obj 20 300 until;"); fi=p.add("#X obj 20 330 f;"); pi=p.add("#X obj 70 330 + 1;"); ti=p.add("#X obj 20 360 t f f;")
md=p.add("#X obj 20 390 % 16;"); rd=p.add(f"#X obj 20 420 tabread {D}0-g;"); tw=p.add(f"#X obj 20 450 tabwrite ockm-pat-{D}1;")
tb=p.add("#X obj 20 240 t b b;")
for c in [(t,0,tb,0),(tb,1,z,0),(z,0,fi,1),(tb,0,ln,0),(rl,0,ln,1),(ln,0,un,0),(un,0,fi,0),(fi,0,pi,0),(pi,0,fi,1),(fi,0,ti,0),
          (ti,1,tw,1),(ti,0,md,0),(md,0,rd,0),(rd,0,tw,0)]: p.con(*c)
p.save("seq/ockm-drumgen.pd","#N canvas 140 140 700 500 12;")


# ================= chord sound: 3 engines x 4 voices =================
def chord_voice(sp,kind):
    """Fill subpatch sp with one chord voice. Inlets: note (left), velocity (right)."""
    ni=sp.add("#X obj 20 20 inlet;"); vi=sp.add("#X obj 400 20 inlet;"); out=sp.add("#X obj 20 420 outlet~;")
    fv=sp.add("#X obj 400 50 f;"); sp.con(vi,0,fv,1)
    mo=sp.add("#X obj 20 50 moses 1;"); tb=sp.add("#X obj 20 80 t b f;"); mt=sp.add("#X obj 80 110 mtof;")
    roff=sp.add(f"#X obj 600 20 r {D}0-off;"); moff=sp.add("#X msg 600 50 0 30;")
    k=[sp.add(f"#X obj {600+i*90} 100 r ockm-{D}1-k{i+1}-m;") for i in range(4)]
    am=sp.add("#X obj 20 330 *~;"); av=sp.add("#X obj 200 300 vline~;")
    for c in [(ni,0,mo,0),(mo,1,tb,0),(tb,1,mt,0),(roff,0,moff,0),(moff,0,av,0),(av,0,am,1),(am,0,out,0)]: sp.con(*c)
    if kind=="stab":
        tf=sp.add("#X obj 80 140 t f f;"); dt=sp.add("#X obj 160 170 * 1.007;"); p1=sp.add("#X obj 80 200 phasor~;"); p2=sp.add("#X obj 160 200 phasor~;")
        sm=sp.add("#X obj 80 230 +~;"); ce=sp.add("#X obj 80 255 -~ 1;")
        fe=sp.add("#X obj 400 200 vline~;"); fa=sp.add("#X obj 400 225 *~ 2200;"); fb=sp.add("#X obj 400 250 +~ 600;"); fc=sp.add("#X obj 400 275 clip~ 40 15000;")
        l1=sp.add("#X obj 80 290 lop~;"); l2=sp.add("#X obj 80 310 lop~;")
        dk=sp.add("#X obj 300 130 f 280;"); tbb=sp.add("#X obj 20 140 t b b;")
        # v0.90: how hard the hit is opens the filter, so stabs aren't all the same (accents bite, soft ones stay round)
        tdk=sp.add("#X obj 300 150 t b f;"); fv2=sp.add("#X obj 470 150 f 1;"); sp.con(vi,0,fv2,1)
        vcv=sp.add(f"#X obj 470 170 expr 0.3+0.7*{D}f1*{D}f1;"); mpk=sp.add("#X obj 400 150 pack f f 2;")
        for c in [(dk,0,tdk,0),(tdk,1,mpk,1),(tdk,0,fv2,0),(fv2,0,vcv,0),(vcv,0,mpk,0)]: sp.con(*c)
        pa=sp.add("#X obj 200 200 pack f 280 2;"); ma=sp.add(f"#X msg 200 230 {D}1 {D}3 \\, 0 {D}2 {D}3;"); mf=sp.add(f"#X msg 400 170 {D}1 {D}3 \\, 0 {D}2 {D}3;")
        # k3 attack (v0.98): the bottom third is all stab, so old projects' snap settings stay stabs; up to about 0.9 s
        x1=sp.add(f"#X obj 600 140 expr 150*pow(2\\,6*{D}f1);"); x2=sp.add(f"#X obj 690 140 expr 1+0.02*{D}f1;"); x3=sp.add(f"#X obj 780 140 expr 2+1800*pow(max(0\\, {D}f1-0.3)\\, 2);"); x4=sp.add(f"#X obj 870 140 expr 40+3000*{D}f1*{D}f1;")
        for c in [(mt,0,tf,0),(tf,1,dt,0),(dt,0,p2,0),(tf,0,p1,0),(p1,0,sm,0),(p2,0,sm,1),(sm,0,ce,0),(ce,0,l1,0),(l1,0,l2,0),(l2,0,am,0),
                  (fe,0,fa,0),(fa,0,fb,0),(fb,0,fc,0),(fc,0,l1,1),(fc,0,l2,1),
                  (tb,0,tbb,0),(tbb,1,fv,0),(fv,0,pa,0),(pa,0,ma,0),(ma,0,av,0),(tbb,0,dk,0),(mpk,0,mf,0),(mf,0,fe,0),
                  (k[0],0,x1,0),(x1,0,fb,1),(k[1],0,x2,0),(x2,0,dt,1),(k[2],0,x3,0),(x3,0,pa,2),(x3,0,mpk,2),(k[3],0,x4,0),(x4,0,dk,1),(x4,0,pa,1)]: sp.con(*c)
    elif kind=="organ":
        tf=sp.add("#X obj 80 140 t f f f f;")
        o1=sp.add("#X obj 80 200 osc~;"); h2=sp.add("#X obj 150 170 * 2;"); o2=sp.add("#X obj 150 200 osc~;"); h3=sp.add("#X obj 220 170 * 3;"); o3=sp.add("#X obj 220 200 osc~;")
        hs=sp.add("#X obj 290 170 * 0.5;"); o4=sp.add("#X obj 290 200 osc~;")
        g2=sp.add("#X obj 150 230 *~ 0.3;"); g3=sp.add("#X obj 220 230 *~ 0.2;"); g4=sp.add("#X obj 290 230 *~ 0.3;")
        pe=sp.add("#X obj 400 200 vline~;"); pg=sp.add("#X obj 400 230 *~ 0;"); p3=sp.add("#X obj 220 260 *~;")
        s1=sp.add("#X obj 80 270 +~;"); s2=sp.add("#X obj 80 290 +~;"); s3=sp.add("#X obj 80 310 +~;")
        pp=sp.add("#X msg 400 170 1 \\, 0 150;"); tbb=sp.add("#X obj 20 140 t b b;")
        pa=sp.add("#X obj 200 140 pack f 400;"); ma=sp.add(f"#X msg 200 170 {D}1 5 \\, 0 40 {D}2;")
        x1=sp.add(f"#X obj 600 140 expr 0.1+0.6*{D}f1 \; 0.05+0.4*{D}f1;"); x2=sp.add("#X obj 690 170 * 0.6;"); x3=sp.add("#X obj 780 140 * 0.7;"); x4=sp.add(f"#X obj 870 140 expr 60+{D}f1*1200;")
        for c in [(mt,0,tf,0),(tf,3,o1,0),(tf,2,h2,0),(h2,0,o2,0),(tf,1,h3,0),(h3,0,o3,0),(tf,0,hs,0),(hs,0,o4,0),(o2,0,g2,0),(o3,0,g3,0),(o4,0,g4,0),
                  (o3,0,p3,0),(pe,0,pg,0),(pg,0,p3,1),(o1,0,s1,0),(g2,0,s1,1),(s1,0,s2,0),(g3,0,s2,1),(s2,0,s3,0),(g4,0,s3,1),(s3,0,am,0),(p3,0,am,0),
                  (tb,0,tbb,0),(tbb,1,fv,0),(fv,0,pa,0),(pa,0,ma,0),(ma,0,av,0),(tbb,0,pp,0),(pp,0,pe,0),
                  (k[0],0,x1,0),(x1,0,g2,1),(x1,1,g3,1),(k[1],0,x2,0),(x2,0,pg,1),(k[2],0,x3,0),(x3,0,g4,1),(k[3],0,x4,0),(x4,0,pa,1)]: sp.con(*c)
    elif kind=="piano":
        # v0.92 house piano, rebuilt as a struck string (it was two FM sines, which sounded thin). Ten partials, each a
        # touch sharper than a whole multiple (a real string is stiff, so its overtones run sharp: B 0.0004), the first four
        # doubled by a second string 3 cents up so they beat. A harder hit, or more brightness, puts more into the upper
        # partials; the higher a partial the sooner it dies, so the note starts bright and mellows. Each partial's level falls
        # to about half over the snap time, then away over the length (squared, so it tails off like a real decay, not a
        # straight line). A felt-and-wood hammer knock on top. k1 brightness, k2 octave (the even partials), k3 snap, k4 length
        NP=10; B=0.0004
        ratios=[n*math.sqrt(1+B*n*n) for n in range(1,NP+1)]
        tm=sp.add("#X obj 80 140 t f f;")
        prm=sp.add("#X obj 400 120 pack f 0.5 0.3 150 1100;")   # velocity, brightness, octave, snap ms, length ms
        mix=sp.add("#X obj 80 380 lop~ 9000;")
        for i,r in enumerate(ratios):
            n=i+1; x=80+i*110
            fr=sp.add(f"#X obj {x} 170 * {r:.5f};"); o=sp.add(f"#X obj {x} 200 osc~;")
            # level: the hammer's spectrum, brighter with velocity and k1; k2 lifts the even partials (the octave)
            ex=sp.add(f"#X obj {x} 230 expr sqrt({D}f1*pow({n}\\, -(2.0-1.5*{D}f2*(0.5+0.5*{D}f1)))*(1+{1.6 if n%2==0 else 0}*{D}f3)) \; "
                      f"0.7*sqrt({D}f1*pow({n}\\, -(2.0-1.5*{D}f2*(0.5+0.5*{D}f1)))*(1+{1.6 if n%2==0 else 0}*{D}f3)) \; {D}f4 \; "
                      f"{D}f5/(1+0.55*{n-1}) \; {D}f4+2;")
            pk=sp.add(f"#X obj {x} 260 pack f f f f f;")
            ms=sp.add(f"#X msg {x} 285 {D}1 2 \\, {D}2 {D}3 2 \\, 0 {D}4 {D}5;")
            ev=sp.add(f"#X obj {x} 310 vline~;"); sq=sp.add(f"#X obj {x} 330 *~;"); g=sp.add(f"#X obj {x} 350 *~;")
            for c in [(tm,0,fr,0),(fr,0,o,0),(prm,0,ex,0),(ex,4,pk,4),(ex,3,pk,3),(ex,2,pk,2),(ex,1,pk,1),(ex,0,pk,0),(pk,0,ms,0),(ms,0,ev,0),
                      (ev,0,sq,0),(ev,0,sq,1),(o,0,g,0),(sq,0,g,1),(g,0,mix,0)]: sp.con(*c)
            if n<=4:   # the second string
                f2=sp.add(f"#X obj {x+50} 170 * {r*1.0017:.5f};"); o2=sp.add(f"#X obj {x+50} 200 osc~;"); g2=sp.add(f"#X obj {x+50} 350 *~;"); h=sp.add(f"#X obj {x+50} 365 *~ 0.8;")
                for c in [(tm,1,f2,0),(f2,0,o2,0),(o2,0,g2,0),(sq,0,g2,1),(g2,0,h,0),(h,0,mix,0)]: sp.con(*c)
        # the hammer: a short knock of filtered noise, harder with velocity
        nz=sp.add("#X obj 900 250 noise~;"); hb=sp.add("#X obj 900 275 bp~ 2500 1;"); hv=sp.add("#X obj 980 250 vline~;"); hg=sp.add("#X obj 900 300 *~;")
        hm=sp.add(f"#X msg 980 220 {D}1 1 \\, 0 18 1;"); hvx=sp.add("#X obj 980 200 * 0.45;")
        hl=sp.add("#X obj 80 400 *~ 0.42;")
        # the overall gate: open on the hit (the partials shape the note), closed by an off
        gt=sp.add("#X msg 300 120 1 2;")
        tbb=sp.add("#X obj 20 140 t b b;")
        x3=sp.add(f"#X obj 780 140 expr 260-200*{D}f1;"); x4=sp.add(f"#X obj 870 140 expr 400+{D}f1*3600;")
        for c in [(mt,0,tm,0),(tb,0,tbb,0),(tbb,1,fv,0),(fv,0,prm,0),(fv,0,hvx,0),(hvx,0,hm,0),(hm,0,hv,0),(tbb,0,gt,0),(gt,0,av,0),
                  (nz,0,hb,0),(hb,0,hg,0),(hv,0,hg,1),(hg,0,mix,0),(mix,0,hl,0),(hl,0,am,0),
                  (k[0],0,prm,1),(k[1],0,prm,2),(k[2],0,x3,0),(x3,0,prm,3),(k[3],0,x4,0),(x4,0,prm,4)]: sp.con(*c)
    elif kind=="rhodes":
        # v0.84 Rhodes: a warm body (gentle FM, ratio 1) plus the tine: a high partial (14x, as on the DX7 electric pianos)
        # that rings for a moment on the attack. Bark: the harder the hit, the more the body is driven (k2 sets how much),
        # with a touch of even harmonics. Tremolo (k3), a long soft decay (k4). k1 tone: how bright the body and tine are
        tf=sp.add("#X obj 80 140 t f f f;"); mo=sp.add("#X obj 80 170 osc~;"); ixv=sp.add("#X obj 300 230 vline~;")
        m1=sp.add("#X obj 80 200 *~;"); m2=sp.add("#X obj 80 225 *~ 0;"); ad=sp.add("#X obj 80 250 +~ 0;"); car=sp.add("#X obj 80 275 osc~;")
        t14=sp.add("#X obj 160 170 * 14;"); to=sp.add("#X obj 160 200 osc~;"); tvl=sp.add("#X obj 240 200 vline~;"); tg=sp.add("#X obj 160 225 *~;")
        bk=sp.add(f"#X obj 80 300 expr~ (tanh({D}v1*max({D}f2\\,1) + 0.3*(max({D}f2\\,1)-1)*{D}v1*{D}v1))/tanh(max({D}f2\\,1));"); dc=sp.add("#X obj 80 325 hip~ 15;")   # max: never divide by tanh(0) before the first note
        sm=sp.add("#X obj 80 350 +~;")
        tro=sp.add("#X obj 200 300 osc~ 4.5;"); trd=sp.add("#X obj 200 325 *~ 0;"); tr1=sp.add("#X obj 200 350 +~ 1;"); trm=sp.add("#X obj 80 375 *~;")
        tbb=sp.add("#X obj 20 140 t b b;"); tv=sp.add("#X obj 400 80 t f f f f;")
        pa=sp.add("#X obj 400 140 pack f 2500 0.6;"); ma=sp.add(f"#X msg 400 170 {D}1 3 \\, {D}3 400 3 \\, 0 {D}2 403;")
        v6=sp.add("#X obj 480 110 * 0.6;")
        ixe=sp.add(f"#X obj 300 140 expr 0.3+1.2*{D}f2 + 2.5*{D}f3*{D}f1 \\; 0.12+0.45*{D}f2;"); pk=sp.add("#X obj 300 170 pack f f;"); mi=sp.add(f"#X msg 300 200 {D}1 \\, {D}2 300;")
        tne=sp.add(f"#X obj 240 140 expr {D}f1*(0.06+0.22*{D}f2);"); tm=sp.add(f"#X msg 240 170 {D}1 1 \\, 0 70 1;")
        bkx=sp.add(f"#X obj 520 110 expr 1+3*{D}f2*{D}f1;")
        fk1=sp.add("#X obj 600 200 f 0.5;"); fk2=sp.add("#X obj 690 200 f 0.4;")
        x3=sp.add("#X obj 780 140 * 0.35;"); x4=sp.add(f"#X obj 870 140 expr 800+{D}f1*4500;")
        for c in [(mt,0,tf,0),(tf,2,mo,0),(tf,1,m2,1),(tf,1,ad,1),(tf,0,t14,0),(t14,0,to,0),
                  (mo,0,m1,0),(ixv,0,m1,1),(m1,0,m2,0),(m2,0,ad,0),(ad,0,car,0),(car,0,bk,0),(bk,0,dc,0),(dc,0,sm,0),
                  (to,0,tg,0),(tvl,0,tg,1),(tg,0,sm,1),
                  (tro,0,trd,0),(trd,0,tr1,0),(sm,0,trm,0),(tr1,0,trm,1),(trm,0,am,0),
                  (tb,0,tbb,0),(tbb,1,fv,0),(fv,0,tv,0),
                  (tv,3,bkx,0),(bkx,0,bk,1),(tv,2,tne,0),(tne,0,tm,0),(tm,0,tvl,0),
                  (tv,1,v6,0),(v6,0,pa,2),(tv,1,ixe,0),(ixe,1,pk,1),(ixe,0,pk,0),(pk,0,mi,0),(mi,0,ixv,0),
                  (tv,0,pa,0),(pa,0,ma,0),(ma,0,av,0),
                  (k[0],0,fk1,0),(fk1,0,ixe,1),(fk1,0,tne,1),(k[1],0,fk2,0),(fk2,0,ixe,2),(fk2,0,bkx,1),
                  (k[2],0,x3,0),(x3,0,trd,1),(k[3],0,x4,0),(x4,0,pa,1)]: sp.con(*c)
    elif kind=="strings":
        # string machine: three detuned saws through a soft filter, slow swell, long release. The ensemble is added after the voices
        tf=sp.add("#X obj 80 140 t f f f;"); du=sp.add("#X obj 160 170 * 1.004;"); dd=sp.add("#X obj 240 170 * 0.996;")
        p1=sp.add("#X obj 80 200 phasor~;"); p2=sp.add("#X obj 160 200 phasor~;"); p3=sp.add("#X obj 240 200 phasor~;")
        s1=sp.add("#X obj 80 230 +~;"); s2=sp.add("#X obj 80 250 +~;"); ce=sp.add("#X obj 80 270 -~ 1.5;")
        l1=sp.add("#X obj 80 290 lop~ 2000;"); l2=sp.add("#X obj 80 310 lop~ 2000;")
        pa=sp.add("#X obj 200 140 pack f 400;"); ma=sp.add(f"#X msg 200 170 {D}1 {D}2;")
        frl=sp.add("#X obj 600 200 f 800;"); mrl=sp.add(f"#X msg 600 230 0 {D}1;")
        x1=sp.add(f"#X obj 600 140 expr 300*pow(2\\,4.5*{D}f1);"); x3=sp.add(f"#X obj 780 140 expr 20+{D}f1*1500;"); x4=sp.add(f"#X obj 870 140 expr 100+{D}f1*3000;")
        sp.C=[c for c in sp.C if c!=(roff,0,moff,0)]   # strings fade out over the release time instead
        for c in [(mt,0,tf,0),(tf,2,p1,0),(tf,1,du,0),(du,0,p2,0),(tf,0,dd,0),(dd,0,p3,0),(p1,0,s1,0),(p2,0,s1,1),(s1,0,s2,0),(p3,0,s2,1),(s2,0,ce,0),
                  (ce,0,l1,0),(l1,0,l2,0),(l2,0,am,0),(tb,0,fv,0),(fv,0,pa,0),(pa,0,ma,0),(ma,0,av,0),(roff,0,frl,0),(frl,0,mrl,0),(mrl,0,av,0),
                  (k[0],0,x1,0),(x1,0,l1,1),(x1,0,l2,1),(k[2],0,x3,0),(x3,0,pa,1),(k[3],0,x4,0),(x4,0,frl,1)]: sp.con(*c)
    else:  # pad
        tf=sp.add("#X obj 80 140 t f f f;"); du=sp.add("#X obj 160 170 * 1.01;"); dd=sp.add("#X obj 240 170 * 0.99;")
        p1=sp.add("#X obj 80 200 phasor~;"); p2=sp.add("#X obj 160 200 phasor~;"); p3=sp.add("#X obj 240 200 phasor~;")
        s1=sp.add("#X obj 80 230 +~;"); s2=sp.add("#X obj 80 250 +~;"); ce=sp.add("#X obj 80 270 -~ 1.5;")
        l1=sp.add("#X obj 80 290 lop~ 1500;"); l2=sp.add("#X obj 80 310 lop~ 1500;")
        pa=sp.add("#X obj 200 140 pack f 300 1000;"); ma=sp.add(f"#X msg 200 170 {D}1 {D}2 \\, 0 400 {D}3;")
        x1=sp.add(f"#X obj 600 140 expr 200*pow(2\\,5*{D}f1);"); x2=sp.add(f"#X obj 690 140 expr 1+0.025*{D}f1 \; 1-0.025*{D}f1;")
        x3=sp.add(f"#X obj 780 140 expr 5+{D}f1*1500;"); x4=sp.add(f"#X obj 870 140 expr 100+{D}f1*2000;"); ad=sp.add(f"#X obj 870 200 expr {D}f1+{D}f2;")
        fa3=sp.add("#X obj 780 200 t f f;")
        for c in [(mt,0,tf,0),(tf,2,p1,0),(tf,1,du,0),(du,0,p2,0),(tf,0,dd,0),(dd,0,p3,0),(p1,0,s1,0),(p2,0,s1,1),(s1,0,s2,0),(p3,0,s2,1),(s2,0,ce,0),
                  (ce,0,l1,0),(l1,0,l2,0),(l2,0,am,0),(tb,0,fv,0),(fv,0,pa,0),(pa,0,ma,0),(ma,0,av,0),
                  (k[0],0,x1,0),(x1,0,l1,1),(x1,0,l2,1),(k[1],0,x2,0),(x2,0,du,1),(x2,1,dd,1),
                  (k[2],0,x3,0),(x3,0,fa3,0),(fa3,1,ad,1),(fa3,0,pa,1),(k[3],0,x4,0),(x4,0,ad,0),(ad,0,pa,2)]: sp.con(*c)

CHORD_GAIN={"stab":0.42,"organ":0.135,"piano":0.4,"rhodes":0.13}   # measured: stab was a third as loud as the bass, organ a little loud
# v0.98: four engines. Stab became poly (its k3 is attack: 0 the dub techno stab, 1 a pad, and a string machine with the
# chorus on), so pad (2) and strings (5) are retired; the numbers stay so saved projects load, and the screen moves them on
CHORD_ENGINES=[(0,"stab","Poly: two detuned saws through a filter. Attack 0 is the dub techno stab \\, up is a pad \\, with the chorus a string machine"),
               (1,"organ","Organ: sine drawbars plus a percussive click. House organ stabs"),
               (3,"piano","House piano: a struck string. Ten stretched partials \\, a second string beating \\, a hammer knock. Classic house and Italo piano"),
               (4,"rhodes","Rhodes: a warm body with the tine ringing on the attack \\, barks when hit hard \\, tremolo. Deep house")]
for idx,kind,title in CHORD_ENGINES:
    q=P(); q.add(f"#X text 20 10 Chord engine {idx}. {title}. k1-k4 0 to 1.;")
    inl=q.add("#X obj 30 50 inlet;"); sp_=q.add("#X obj 30 80 spigot 1;"); ro=q.add("#X obj 30 110 route off;")
    so=q.add(f"#X obj 30 140 s {D}0-off;"); up=q.add("#X obj 120 140 unpack f f f f f;")
    rsx=q.add(f"#X obj 500 50 r ockm-{D}1-strum;")
    strum={v: q.add(f"#X obj {500+v*60} 80 * {round(25*v,1)};") for v in (1,2,3)}
    for v in (1,2,3): q.con(rsx,0,strum[v],0)
    re=q.add(f"#X obj 700 50 r ockm-{D}1-engine;"); eq=q.add(f"#X obj 700 80 == {idx};"); tf=q.add("#X obj 700 110 t f f;")
    sw=q.add("#X obj 700 170 switch~;"); s0=q.add("#X obj 760 140 sel 0;"); bo=q.add(f"#X obj 760 170 s {D}0-off;")
    for c in [(inl,0,sp_,0),(sp_,0,ro,0),(ro,0,so,0),(ro,1,up,0),(re,0,eq,0),(eq,0,tf,0),(tf,1,sw,0),(tf,0,s0,0),(s0,0,bo,0),(tf,0,sp_,1)]: q.con(*c)
    vs=[]
    for v in range(4):
        sp=P(); chord_voice(sp,kind)
        q.L.append(sp.text(f"#N canvas 0 0 980 460 v{v} 0;").rstrip("\n"))
        o=q.add(f"#X restore {120+v*90} 200 pd v{v};"); vs.append(o)
        q.con(up,4,o,1)
        if v == 0: q.con(up,v,o,0)
        else:
            pp=q.add(f"#X obj {120+v*90} 170 pipe 0;"); q.con(up,v,pp,0); q.con(pp,0,o,0)
            q.con(strum[v],0,pp,1)
    s1=q.add("#X obj 120 260 +~;"); s2=q.add("#X obj 120 280 +~;"); s3=q.add("#X obj 120 300 +~;"); g=q.add(f"#X obj 120 330 *~ {CHORD_GAIN[kind]};"); out=q.add("#X obj 120 370 outlet~;")
    hp=q.add("#X obj 120 315 hip~ 20;")   # FM at a 1:1 ratio puts a sideband at 0 Hz (an offset): keep it out of the mix
    for c in [(vs[0],0,s1,0),(vs[1],0,s1,1),(s1,0,s2,0),(vs[2],0,s2,1),(s2,0,s3,0),(vs[3],0,s3,1),(s3,0,hp,0),(hp,0,g,0),(g,0,out,0)]: q.con(*c)
    if kind=="strings":
        # ensemble: three delay taps swept by slow sines a third of a cycle apart (k2 sets the depth)
        q.C=[c for c in q.C if c!=(g,0,out,0)]
        dw=q.add(f"#X obj 300 330 delwrite~ {D}0-ens 40;"); dry=q.add("#X obj 120 400 *~ 0.5;"); mix=q.add("#X obj 120 450 +~;")
        lb=q.add("#X obj 500 250 loadbang;"); kd=q.add(f"#X obj 700 250 r ockm-{D}1-k2-m;"); kx=q.add(f"#X obj 700 275 expr 0.5+{D}f1*3;")
        for c in [(g,0,dw,0),(g,0,dry,0),(dry,0,mix,0),(mix,0,out,0),(kd,0,kx,0)]: q.con(*c)
        for j in range(3):
            lo=q.add(f"#X obj {300+j*130} 360 osc~ 0.6;"); ph=q.add(f"#X msg {380+j*130} 335 {round(j/3,3)};"); dp=q.add(f"#X obj {300+j*130} 385 *~ 2;")
            off=q.add(f"#X obj {300+j*130} 410 +~ 8;"); vd=q.add(f"#X obj {300+j*130} 435 vd~ {D}0-ens;"); vg=q.add(f"#X obj {300+j*130} 460 *~ 0.35;")
            for c in [(lb,0,ph,0),(ph,0,lo,1),(lo,0,dp,0),(kx,0,dp,1),(dp,0,off,0),(off,0,vd,0),(vd,0,vg,0),(vg,0,mix,0)]: q.con(*c)
    q.save(f"voices/ockm-chord-{kind}.pd","#N canvas 160 160 900 420 12;")
q=P()
q.add("#X text 20 10 Chord synth: four engines \\, one plays at a time (ockm-<track>-engine 0 poly \\, 1 organ \\, 3 piano \\, 4 rhodes: 2 and 5 were pad and strings \\, retired in v0.98). Input: up to 4 MIDI notes plus a hit strength \\, or off.;")
inl=q.add("#X obj 30 50 inlet;")
eng=[q.add(f"#X obj {30+i*170} 100 ockm-chord-{k} {D}1;") for i,(_,k,_) in enumerate(CHORD_ENGINES)]
s1=q.add("#X obj 30 160 +~;"); s2=q.add("#X obj 30 185 +~;"); out=q.add("#X obj 30 220 outlet~;")
for e in eng: q.con(inl,0,e,0)
sm=q.add("#X obj 30 160 +~;"); q.C=[]
for e in eng: q.con(inl,0,e,0); q.con(e,0,sm,0)   # an outlet~ into one inlet sums
q.con(sm,0,out,0)
q.save("voices/ockm-chord.pd","#N canvas 140 140 700 260 12;")

# ================= settings store =================
# Holds every setting, the 8 patterns (in memory) and the project, and saves them as text files.
QDIR="../"+PROJ_DIR   # the store lives in seq/, so file paths are relative to that folder
q=P()
q.add(f"#X text 20 10 Settings store. Project settings and the drum kit live in {PROJ_DIR}/project.txt. Each pattern (steps \\, length \\, swing \\, key \\, generators \\, synth sounds) lives in p1.txt to p8.txt. Switching keeps edits in memory. Save writes to disk. Revert reloads from disk.;")
# --- buffers: one qlist for the project, one per pattern ---
rj=q.add(f"#X obj 1400 60 r {D}0-proj;"); qj=q.add("#X obj 1400 90 qlist;"); q.con(rj,0,qj,0)
rq=q.add(f"#X obj 1600 60 r {D}0-q;"); rt=q.add("#X obj 1600 90 route "+" ".join(str(i) for i in range(SLOTN))+";"); q.con(rq,0,rt,0)
for n in range(SLOTN):
    lt=q.add(f"#X obj {1600+n*60} 120 list trim;"); ql=q.add(f"#X obj {1600+n*60} 150 qlist;"); q.con(rt,n,lt,0); q.con(lt,0,ql,0)
rap=q.add(f"#X obj 1400 200 r {D}0-add-p;"); lpp=q.add("#X obj 1400 230 list prepend 0;"); sq=q.add(f"#X obj 1400 260 s {D}0-q;")
q.con(rap,0,lpp,0); q.con(lpp,0,sq,0)
sap=q.add(f"#X obj 1400 300 s {D}0-add-p;")   # shared sender for pattern lines
saj=q.add(f"#X obj 1400 330 s {D}0-proj;")    # shared sender for project lines
# --- every setting: remember its latest value, write it out on capture, show it on sync ---
rcp=q.add(f"#X obj 20 60 r {D}0-cap-p;"); rcj=q.add(f"#X obj 200 60 r {D}0-cap-j;"); rsy=q.add(f"#X obj 380 60 r {D}0-sync;")
q.con(q.add("#X obj 560 60 r ockm-resync;"),0,q.add(f"#X obj 560 85 s {D}0-sync;"),0)
q.add("#X obj 740 60 r ockm-saved;")
y=100
for scope,keys in (("j",PROJECT_KEYS),("p",PATTERN_KEYS)):
    for h,d,listen in keys:
        r=q.add(f"#X obj 20 {y} r {listen or h};"); fa=q.add(f"#X obj 200 {y} f {d};"); fs=q.add(f"#X obj 420 {y} f {d};")
        ma=q.add(f"#X msg 260 {y} add {h} {D}1;"); ms=q.add(f"#X msg 480 {y} set {D}1;"); ss=q.add(f"#X obj 560 {y} s {show(h)};")
        q.con(r,0,fa,1); q.con(r,0,fs,1)
        q.con(rcp if scope=="p" else rcj,0,fa,0); q.con(fa,0,ma,0); q.con(ma,0,sap if scope=="p" else saj,0)
        q.con(rsy,0,fs,0); q.con(fs,0,ms,0); q.con(ms,0,ss,0)
        y+=22
q.add("#X text 800 60 capture writes 'add <hook> <value>' lines into the buffer \\, sync sends 'set <value>' to the on-screen boxes;")
# --- step tables ---
rct=q.add(f"#X obj 1000 100 r {D}0-capt;")
for i,T in enumerate(TABLES):
    yy=130+i*22
    ag=q.add(f"#X obj 1000 {yy} array get {T};"); lp=q.add(f"#X obj 1150 {yy} list prepend add {T} 0;"); ltr=q.add(f"#X obj 1320 {yy} list trim;")
    q.con(rct,0,ag,0); q.con(ag,0,lp,0); q.con(lp,0,ltr,0); q.con(ltr,0,sap,0)
# --- an empty pattern: clear the steps, keep the synth sounds, key and swing ---
re_=q.add("#X obj 1000 600 r ockm-empty;")
me=q.add("#X msg 1000 630 \; "+" \; ".join(f"{T} const 0" for T in TABLES)+";"); q.con(re_,0,me,0)
# --- capture the current pattern into its buffer (memory only) ---
cap=q.add("#X obj 20 1200 t b b b;"); clr=q.add("#X msg 200 1230 clear;")
scp=q.add(f"#X obj 110 1260 s {D}0-cap-p;"); sct=q.add(f"#X obj 20 1290 s {D}0-capt;")
for c in [(cap,2,clr,0),(clr,0,sap,0),(cap,1,scp,0),(cap,0,sct,0)]: q.con(*c)
rcap=q.add(f"#X obj 20 1170 r {D}0-capture;"); q.con(rcap,0,cap,0)
# --- load a pattern: capture the one we're leaving, then play the new buffer ---
cur=q.add("#X obj 500 1200 f 0;"); started=q.add("#X obj 400 1230 spigot 0;")
rl=q.add("#X obj 400 1150 r ockm-load;"); tfb=q.add("#X obj 400 1175 t f b;")
scap=q.add(f"#X obj 400 1260 s {D}0-capture;")
tl=q.add("#X obj 500 1290 t b b b b b f;")
l1=q.add("#X msg 560 1330 1;"); sl1=q.add("#X obj 560 1355 s ockm-loading;")
play=q.add(f"#X msg 620 1330 {D}1 rewind \\, {D}1 bang;"); fcur=q.add("#X obj 620 1305 f;")
l0=q.add("#X msg 700 1330 0;"); sl0=q.add("#X obj 700 1355 s ockm-loading;")
rf=q.add("#X msg 760 1330 \; ockm-refresh bang;")
# settings older pattern files don't have: back to their defaults before the pattern plays in
nwd=q.add("#X msg 560 1380 \\; ockm-drum-loop 0 \\; "+" \\; ".join(f"ockm-pat-{n}-nudge const 0" for n,_ in SLOTS)+";"); q.con(tl,4,nwd,0)
syn=q.add(f"#X obj 820 1330 s {D}0-sync;"); one=q.add("#X msg 880 1330 1;")
for c in [(rl,0,tfb,0),(tfb,1,started,0),(started,0,scap,0),(tfb,0,tl,0),
          (tl,5,cur,1),(tl,5,lpp,1),(tl,5,fcur,1),(tl,4,l1,0),(l1,0,sl1,0),(tl,3,fcur,0),(fcur,0,play,0),(play,0,sq,0),
          (tl,2,l0,0),(l0,0,sl0,0),(tl,1,rf,0),(tl,0,syn,0),(tl,0,one,0),(one,0,started,1)]: q.con(*c)
def _fmtv(v): return str(int(v)) if float(v)==int(v) else str(v)
# --- projects: each project is a folder in projects/ holding project.txt and p1.txt to p8.txt ---
# Paths are built from this patch's own folder (Pd's [file] objects need full paths).
def holder(key,x,y):
    """a [symbol] that always holds the latest value sent to $0-<key>"""
    h=q.add(f"#X obj {x} {y} symbol;"); r=q.add(f"#X obj {x+80} {y-25} r {D}0-{key};"); q.con(r,0,h,1); return h
def joined(src,outlet,tail,x,y):
    """src's symbol (a folder) -> folder/tail"""
    la=q.add(f"#X obj {x} {y} list append {tail};"); fj=q.add(f"#X obj {x} {y+25} file join;")
    q.con(src,outlet,la,0); q.con(la,0,fj,0); return fj
def cmd(src,outlet,word,x,y,target):
    """src's symbol -> '<word> <symbol>' message into target"""
    a=q.add(f"#X obj {x} {y} list prepend {word};"); b=q.add(f"#X obj {x} {y+25} list trim;")
    q.con(src,outlet,a,0); q.con(a,0,b,0); q.con(b,0,target,0)
def sender(key,x,y): return q.add(f"#X obj {x} {y} s {D}0-{key};")
Y0=1450
# read every file of the open project into the buffers, then play the project settings
rra=q.add(f"#X obj 20 {Y0} r {D}0-readall;"); dr=holder("dir",20,Y0+50); q.con(rra,0,dr,0)
tr9=q.add(f"#X obj 20 {Y0+75} t "+" ".join(["s"]*(SLOTN+1))+";"); q.con(dr,0,tr9,0)
pj=joined(tr9,SLOTN,"project.txt",20,Y0+100); tpj=q.add(f"#X obj 20 {Y0+150} t b s b;")
# defaults first, so a setting missing from an older project.txt doesn't keep the last project's value
dfj=q.add(f"#X msg 400 {Y0+175} "+" \\, ".join(["clear"]+[f"add {h} {_fmtv(d)}" for h,d,_ in PROJECT_KEYS])+" \\, rewind \\, bang;"); q.con(tpj,2,dfj,0); q.con(dfj,0,saj,0)
cmd(tpj,1,"read",80,Y0+175,saj); rwb=q.add(f"#X msg 20 {Y0+225} rewind \\, bang;"); q.con(pj,0,tpj,0); q.con(tpj,0,rwb,0); q.con(rwb,0,saj,0)
for n in range(SLOTN):
    x=240+n*140; pf=joined(tr9,SLOTN-1-n,LOOP_FILE,x,Y0+100)
    a=q.add(f"#X obj {x} {Y0+150} list prepend read;"); b=q.add(f"#X obj {x} {Y0+175} list prepend {n};")
    q.con(pf,0,a,0); q.con(a,0,b,0); q.con(b,0,sq,0)
# which patterns exist (made, even if empty): pattern 1 always; others when their file is more than one line
rra3=q.add(f"#X obj 1500 {Y0+300} r {D}0-readall;"); dr3=holder("dir",1500,Y0+350); q.con(rra3,0,dr3,0)
tx=q.add(f"#X obj 1500 {Y0+375} t b "+" ".join(["s"]*SLOTN)+";"); q.con(dr3,0,tx,0)
for n in range(SLOTN):
    x=1500+n*150; yy=Y0+400
    txd=q.add(f"#X obj {x+150} {yy+250} text define {D}0-px{n};")
    pf=joined(tx,SLOTN-n,LOOP_FILE,x,yy); tf2=q.add(f"#X obj {x} {yy+50} t s s b;")
    z=q.add(f"#X msg {x+100} {yy+75} 0;"); vz=q.add(f"#X obj {x+100} {yy+100} v ockm_px{n};"); q.con(tf2,2,z,0); q.con(z,0,vz,0)
    isf=q.add(f"#X obj {x+60} {yy+75} file isfile;"); spf=q.add(f"#X obj {x} {yy+100} spigot;"); z2=q.add(f"#X msg {x+120} {yy+125} 0;")
    q.con(pf,0,tf2,0); q.con(tf2,1,isf,0); q.con(isf,0,spf,1); q.con(isf,1,z2,0); q.con(z2,0,spf,1); q.con(tf2,0,spf,0)
    rdm=q.add(f"#X obj {x} {yy+125} list prepend read;"); rdt=q.add(f"#X obj {x} {yy+150} list trim;"); td=q.add(f"#X obj {x} {yy+175} t b a;")
    sz=q.add(f"#X obj {x} {yy+200} text size {D}0-px{n};"); gt=q.add(f"#X obj {x} {yy+225} > 1;"); vv=q.add(f"#X obj {x} {yy+250} v ockm_px{n};")
    tdef=q.add(f"#X obj {x+80} {yy+200} r {D}0-px{n}-cmd;"); q.con(tdef,0,txd,0)
    q.con(spf,0,rdm,0); q.con(rdm,0,rdt,0); q.con(rdt,0,td,0); q.con(td,1,q.add(f"#X obj {x+80} {yy+175} s {D}0-px{n}-cmd;"),0); q.con(td,0,sz,0); q.con(sz,0,gt,0); q.con(gt,0,vv,0)
ex=q.add(f"#X obj 1500 {Y0+700} expr 1"+"".join(f" + {2**n}*ockm_px{n}" for n in range(1,SLOTN))+";")
q.con(tx,0,ex,0); q.con(ex,0,q.add(f"#X obj 1500 {Y0+725} s ockm-patterns-exist;"),0)
# write every buffer into the open project folder (save captures the live pattern first)
Y1=Y0+300
rwa=q.add(f"#X obj 20 {Y1} r {D}0-writeall;"); dw=holder("dir",20,Y1+50); q.con(rwa,0,dw,0)
tw9=q.add(f"#X obj 20 {Y1+75} t b "+" ".join(["s"]*(SLOTN+1))+";"); q.con(dw,0,tw9,0)
for n in range(SLOTN):
    x=240+n*140; pf=joined(tw9,SLOTN+1-1-n,LOOP_FILE,x,Y1+100)
    a=q.add(f"#X obj {x} {Y1+150} list prepend write;"); b=q.add(f"#X obj {x} {Y1+175} list prepend {n};")
    q.con(pf,0,a,0); q.con(a,0,b,0); q.con(b,0,sq,0)
pw=joined(tw9,SLOTN+1,"project.txt",20,Y1+100); tjw=q.add(f"#X obj 20 {Y1+150} t s b b;")
cj=q.add(f"#X msg 160 {Y1+175} clear;"); scj=sender("cap-j",100,Y1+200)
q.con(pw,0,tjw,0); q.con(tjw,2,cj,0); q.con(cj,0,saj,0); q.con(tjw,1,scj,0); cmd(tjw,0,"write",20,Y1+225,saj)
sgq=q.add(f"#X obj 20 {Y1+250} spigot 1;"); q.con(tw9,0,sgq,0); q.con(q.add(f"#X obj 120 {Y1+225} r {D}0-announce;"),0,sgq,1)
q.con(sgq,0,q.add(f"#X msg 20 {Y1+275} \; ockm-saved bang;"),0)
# remember the open project in projects/current.txt, and tell the screens its name
Y2=Y1+350
tcur=q.add(f"#X obj 700 {Y2+50} text define {D}0-cur;"); rcc=q.add(f"#X obj 700 {Y2+25} r {D}0-curcmd;"); q.con(rcc,0,tcur,0)
rrm=q.add(f"#X obj 20 {Y2} r {D}0-remember;"); trm=q.add(f"#X obj 20 {Y2+25} t b b b;")
clc=q.add(f"#X msg 300 {Y2+50} clear;"); q.con(trm,2,clc,0); q.con(clc,0,sender("curcmd",300,Y2+75),0)
nmh=holder("name",160,Y2+75); lst=q.add(f"#X obj 160 {Y2+100} list;"); ins=q.add(f"#X obj 160 {Y2+125} text insert {D}0-cur 1e+06;")
ann=q.add(f"#X obj 260 {Y2+125} s ockm-project-name;")
bh=holder("base",20,Y2+75); cp=joined(bh,0,"current.txt",20,Y2+100)
for c in [(rrm,0,trm,0),(trm,1,nmh,0),(nmh,0,lst,0),(lst,0,ins,0),(nmh,0,ann,0),(trm,0,bh,0)]: q.con(*c)
cmd(cp,0,"write",20,Y2+150,sender("curcmd",20,Y2+200))
# set the name: $0-name, and $0-dir = base/name
Y3=Y2+300
rsn=q.add(f"#X obj 20 {Y3} r {D}0-setname;"); tsn=q.add(f"#X obj 20 {Y3+25} t s s;")
lpb=q.add(f"#X obj 20 {Y3+75} list prepend;"); rb=q.add(f"#X obj 120 {Y3+50} r {D}0-base;"); fjn=q.add(f"#X obj 20 {Y3+100} file join;")
for c in [(rsn,0,tsn,0),(tsn,1,sender("name",120,Y3+50+30),0),(tsn,0,lpb,0),(rb,0,lpb,1),(lpb,0,fjn,0),(fjn,0,sender("dir",20,Y3+125),0)]: q.con(*c)
# load a pattern without capturing the one we're leaving (its buffer belongs to the old project)
rlf=q.add(f"#X obj 400 {Y3} r {D}0-loadpat;"); tlf=q.add(f"#X obj 400 {Y3+25} t f b;"); zz=q.add(f"#X msg 460 {Y3+50} 0;")
slo=q.add(f"#X msg 400 {Y3+75} \; ockm-slotset set {D}1 \; ockm-load {D}1;")
for c in [(rlf,0,tlf,0),(tlf,1,zz,0),(zz,0,started,1),(tlf,0,slo,0)]: q.con(*c)
# make a folder in projects/
def mkdir_of(src,outlet,x,y):
    bh2=holder("base",x+200,y); lp=q.add(f"#X obj {x} {y+25} list prepend;"); fj=q.add(f"#X obj {x} {y+50} file join;"); md=q.add(f"#X obj {x} {y+75} file mkdir;")
    t=q.add(f"#X obj {x} {y} t s b;"); q.con(src,outlet,t,0); q.con(t,1,bh2,0); q.con(bh2,0,lp,1); q.con(t,0,lp,0); q.con(lp,0,fj,0); q.con(fj,0,md,0)
Y4=Y3+200
# ockm-project-open <name>: read it all, play pattern 1
ro=q.add(f"#X obj 20 {Y4} r ockm-project-open;"); to=q.add(f"#X obj 20 {Y4+25} t b b b s;")
for c in [(ro,0,to,0),(to,3,sender("setname",200,Y4+50),0),(to,2,sender("readall",150,Y4+75),0)]: q.con(*c)
z0=q.add(f"#X msg 100 {Y4+100} 0;"); q.con(to,1,z0,0); q.con(z0,0,sender("loadpat",100,Y4+125),0); q.con(to,0,sender("remember",20,Y4+150),0)
# ockm-revert: read the open project again, stay on this pattern
rrv=q.add(f"#X obj 400 {Y4} r ockm-revert;"); trv=q.add(f"#X obj 400 {Y4+25} t b b;"); fc4=q.add(f"#X obj 400 {Y4+50} f;")
for c in [(rrv,0,trv,0),(trv,1,sender("readall",500,Y4+50),0),(trv,0,fc4,0),(tl,5,fc4,1),(fc4,0,sender("loadpat",400,Y4+75),0)]: q.con(*c)
# ockm-do-save: capture the live pattern, write everything
rsv=q.add(f"#X obj 700 {Y4} r ockm-do-save;"); tsv=q.add(f"#X obj 700 {Y4+25} t b b;")
for c in [(rsv,0,tsv,0),(tsv,1,scap,0),(tsv,0,sender("writeall",700,Y4+50),0)]: q.con(*c)
# one-step undo. ockm-snapshot: everything (the loop and the project) is written to undo/ beside projects/,
# without counting as a save. ockm-undo: read it all back and reload the pattern on screen. undo/ holds one snapshot only.
YU=Y4+120
def undo_dir(src,outlet,x,y):
    """bang -> the undo folder's path (made if missing)"""
    bu=holder("base",x,y); q.con(src,outlet,bu,0); ud=joined(bu,0,"../undo",x,y+25)
    t=q.add(f"#X obj {x} {y+75} t s s;"); q.con(ud,0,t,0); q.con(t,1,q.add(f"#X obj {x+150} {y+100} file mkdir;"),0); return t
rsn2=q.add(f"#X obj 1100 {YU} r ockm-snapshot;"); tsn2=q.add(f"#X obj 1100 {YU+25} t b b b b b b;"); q.con(rsn2,0,tsn2,0)
keep=q.add(f"#X obj 1100 {YU+250} symbol;"); dk=holder("dir",1300,YU+50); q.con(tsn2,5,dk,0); q.con(dk,0,keep,1)   # 1. remember the project folder
tu=undo_dir(tsn2,4,1450,YU+50); q.con(tu,0,sender("dir",1450,YU+150),0)                                               # 2. point at undo/
m0=q.add(f"#X msg 1250 {YU+100} 0;"); q.con(tsn2,3,m0,0); q.con(m0,0,sender("announce",1250,YU+125),0)                 # 3. quietly
q.con(tsn2,2,scap,0)                                                                                                    # 4. capture the live pattern
q.con(tsn2,1,sender("writeall",1200,YU+175),0)                                                                          # 5. write it all
tz=q.add(f"#X obj 1100 {YU+200} t b b;"); q.con(tsn2,0,tz,0); m1=q.add(f"#X msg 1250 {YU+225} 1;")                     # 6. back to normal
q.con(tz,1,m1,0); q.con(m1,0,sender("announce",1250,YU+250),0); q.con(tz,0,keep,0); q.con(keep,0,sender("dir",1100,YU+275),0)
rud=q.add(f"#X obj 1700 {YU} r ockm-undo;"); tud2=q.add(f"#X obj 1700 {YU+25} t b b b b;"); q.con(rud,0,tud2,0)
keep2=q.add(f"#X obj 1700 {YU+250} symbol;"); dk2=holder("dir",1900,YU+50); q.con(tud2,3,dk2,0); q.con(dk2,0,keep2,1)
tu2=undo_dir(tud2,2,2050,YU+50); q.con(tu2,0,sender("dir",2050,YU+150),0)
q.con(tud2,1,sender("readall",1800,YU+175),0)
tz2=q.add(f"#X obj 1700 {YU+200} t b b;"); q.con(tud2,0,tz2,0); q.con(tz2,1,keep2,0); q.con(keep2,0,sender("dir",1700,YU+275),0)
q.con(tz2,0,fc4,0)   # reload the pattern on screen from its restored buffer (as revert does)
# ockm-project-new <name>: a blank project (every pattern empty, default kit, tempo and sounds)
Y5=Y4+250
rn=q.add(f"#X obj 20 {Y5} r ockm-project-new;"); tn=q.add(f"#X obj 20 {Y5+25} t b b b b b s s;")
mkdir_of(tn,6,700,Y5)
blankp=q.add(f"#X msg 300 {Y5+75} "+" \\, ".join(["0 clear"]+[f"0 add {h} {_fmtv(d)}" for h,d,_ in PATTERN_KEYS]+["0 add ockm-empty 1"]
                                               +[x for n in range(1,SLOTN) for x in (f"{n} clear",f"{n} add ockm-empty 1")])+";")
blankj=q.add(f"#X msg 250 {Y5+100} "+" \\, ".join(["clear"]+[f"add {h} {_fmtv(d)}" for h,d,_ in PROJECT_KEYS])+" \\, rewind \\, bang;")
for c in [(rn,0,tn,0),(tn,5,sender("setname",400,Y5+50),0),(tn,4,blankp,0),(blankp,0,sq,0),(tn,3,blankj,0),(blankj,0,saj,0),
          (tn,2,sender("writeall",200,Y5+125),0)]: q.con(*c)
z1=q.add(f"#X msg 100 {Y5+150} 0;"); q.con(tn,1,z1,0); q.con(z1,0,sender("loadpat",100,Y5+175),0); q.con(tn,0,sender("remember",20,Y5+200),0)
# ockm-project-saveas <name>: this project, saved into a new folder, which becomes the open one
Y6=Y5+250
rsa=q.add(f"#X obj 20 {Y6} r ockm-project-saveas;"); tsa=q.add(f"#X obj 20 {Y6+25} t b b b s s;")
mkdir_of(tsa,4,700,Y6)
for c in [(rsa,0,tsa,0),(tsa,3,sender("setname",300,Y6+50),0),(tsa,2,scap,0),(tsa,1,sender("writeall",200,Y6+75),0),(tsa,0,sender("remember",20,Y6+100),0)]: q.con(*c)
# ockm-project-delete <name>: its files move to trash/<name> (next to projects/), then the empty folder goes
Y7=Y6+150
DEL_FILES=["project.txt",LOOP_FILE,"song.txt"]+[f"p{n+1}.txt" for n in range(8)]+[".DS_Store"]
rdl=q.add(f"#X obj 20 {Y7} r ockm-project-delete;"); tdl=q.add(f"#X obj 20 {Y7+25} t b s;"); q.con(rdl,0,tdl,0)
nmd=q.add(f"#X obj 100 {Y7+50} symbol;"); q.con(tdl,1,nmd,1)
nf=len(DEL_FILES)
steps=q.add(f"#X obj 20 {Y7+75} t "+" ".join(["b"]*(nf+3))+";"); q.con(tdl,0,steps,0)

# setup (fires first): src = base/name, dst = base/../trash/name, make the trash folders
bdl=holder("base",900,Y7+100); q.con(steps,nf+2,bdl,0)
tsu=q.add(f"#X obj 900 {Y7+125} t s s s;"); q.con(bdl,0,tsu,0)
t1=joined(tsu,2,"../trash",1100,Y7+150); md1=q.add(f"#X obj 1100 {Y7+200} file mkdir;"); q.con(t1,0,md1,0)
lps=q.add(f"#X obj 900 {Y7+225} list prepend;"); q.con(tsu,1,lps,1); fjs=q.add(f"#X obj 900 {Y7+250} file join;"); q.con(lps,0,fjs,0); 
lad=q.add(f"#X obj 1000 {Y7+150} list append ../trash;"); q.con(tsu,0,lad,0)
lpd=q.add(f"#X obj 1000 {Y7+225} list prepend;"); q.con(lad,0,lpd,1); fjd=q.add(f"#X obj 1000 {Y7+250} file join;"); q.con(lpd,0,fjd,0)
tdd=q.add(f"#X obj 1000 {Y7+275} t s s;"); q.con(fjd,0,tdd,0); q.con(tdd,1,q.add(f"#X obj 1100 {Y7+300} file mkdir;"),0); 
nm2=q.add(f"#X obj 800 {Y7+175} t s s;"); q.con(nmd,0,nm2,0); q.con(nm2,1,lpd,0); q.con(nm2,0,lps,0)
q.con(steps,nf+1,nmd,0)
# one move per file (missing files are skipped quietly)
for k,fn in enumerate(DEL_FILES):
    x=100+k*110; tb=q.add(f"#X obj {x} {Y7+350} t b b;"); q.con(steps,nf-k,tb,0)
    # dst first into the pair's right inlet, then src triggers the move
    d_a=q.add(f"#X obj {x+50} {Y7+400} list append {fn};"); d_j=q.add(f"#X obj {x+50} {Y7+425} file join;")
    s_a=q.add(f"#X obj {x} {Y7+450} list append {fn};"); s_j=q.add(f"#X obj {x} {Y7+475} file join;")
    pk=q.add(f"#X obj {x} {Y7+500} list append;"); mv=q.add(f"#X obj {x} {Y7+525} file move;")
    hd=q.add(f"#X obj {x+50} {Y7+375} symbol;"); hs=q.add(f"#X obj {x} {Y7+425} symbol;")
    q.con(tdd,0,hd,1); q.con(fjs,0,hs,1)
    for c in [(tb,1,hd,0),(hd,0,d_a,0),(d_a,0,d_j,0),(d_j,0,pk,1),(tb,0,hs,0),(hs,0,s_a,0),(s_a,0,s_j,0),(s_j,0,pk,0),(pk,0,mv,0)]: q.con(*c)
# then the empty folder, then a fresh list for the screens
hrm=q.add(f"#X obj 20 {Y7+575} symbol;"); q.con(fjs,0,hrm,1); q.con(steps,1,hrm,0); q.con(hrm,0,q.add(f"#X obj 20 {Y7+600} file delete;"),0)
q.con(steps,0,q.add(f"#X msg 20 {Y7+650} \\; ockm-project-list bang;"),0)
Y7=Y7+400
# ockm-pattern-copy <from> <to> and ockm-pattern-clear <n> (patterns 0-7)
YC=Y7+200
curf=q.add(f"#X obj 1300 {YC} f;"); q.con(tl,5,curf,1)
def reload_if_current(src,outlet,x,y):
    """src outputs a pattern number: if it's the one playing, load it again from its buffer"""
    t=q.add(f"#X obj {x} {y} t f b;"); eq=q.add(f"#X obj {x} {y+50} == ;"); t2=q.add(f"#X obj {x} {y+25} t f f;")
    sp=q.add(f"#X obj {x} {y+100} spigot;"); 
    q.con(src,outlet,t,0); q.con(t,1,curf,0); q.con(curf,0,eq,1); q.con(t,0,t2,0); q.con(t2,1,eq,0); q.con(eq,0,sp,1); q.con(t2,0,sp,0)
    q.con(sp,0,sender("loadpat",x,y+125),0)
rcp=q.add(f"#X obj 1000 {YC} r ockm-pattern-copy;"); ucp=q.add(f"#X obj 1000 {YC+25} unpack f f;")
tof=q.add(f"#X obj 1200 {YC+50} f;"); fromf=q.add(f"#X obj 1100 {YC+75} f;"); tfr=q.add(f"#X obj 1000 {YC+50} t b f;")
q.con(rcp,0,ucp,0); q.con(ucp,1,tof,1); q.con(ucp,0,tfr,0); q.con(tfr,1,fromf,1)
seq=q.add(f"#X obj 1000 {YC+100} t b b b b;"); q.con(tfr,0,seq,0)
wr1=q.add(f"#X obj 1100 {YC+225} list prepend write;"); wr2=q.add(f"#X obj 1100 {YC+250} list prepend;")
rd1=q.add(f"#X obj 1250 {YC+225} list prepend read;"); rd2=q.add(f"#X obj 1250 {YC+250} list prepend;")
for c in [(wr1,0,wr2,0),(wr2,0,sq,0),(rd1,0,rd2,0),(rd2,0,sq,0)]: q.con(*c)
# 1st: from/to into the message builders, 2nd: capture the live pattern, 3rd: write 'from' out and read it into 'to', 4th: reload if needed
q.con(seq,3,fromf,0); q.con(fromf,0,wr2,1); q.con(seq,3,tof,0); q.con(tof,0,rd2,1)
q.con(seq,2,scap,0)
bcp=holder("base",1100,YC+150); q.con(seq,1,bcp,0); clip=joined(bcp,0,"../.clipboard.txt",1100,YC+175)
tcl=q.add(f"#X obj 1100 {YC+200} t s s;"); q.con(clip,0,tcl,0); q.con(tcl,1,wr1,0); q.con(tcl,0,rd1,0)
tob=q.add(f"#X obj 1000 {YC+275} f;"); q.con(seq,0,tob,0); q.con(ucp,1,tob,1)
reload_if_current(tob,0,1000,YC+300)
rcl=q.add(f"#X obj 1400 {YC} r ockm-pattern-clear;"); tclr=q.add(f"#X obj 1400 {YC+25} t f f;")
mcl=q.add(f"#X msg 1400 {YC+50} {D}1 clear \\, {D}1 add ockm-created 1 \\, {D}1 add ockm-empty 1;")
q.add(f"#X obj 1600 {YC+50} r ockm-created;")   # marker only: a pattern made with 'start empty' still counts as made
q.con(rcl,0,tclr,0); q.con(tclr,1,mcl,0); q.con(mcl,0,sq,0); reload_if_current(tclr,0,1400,YC+100)
Y7=YC+200
# ockm-project-list: one ockm-project-item <name> per project folder, between -start and -end
Y8=Y7+350
rls=q.add(f"#X obj 20 {Y8} r ockm-project-list;"); bls=holder("base",20,Y8+50); q.con(rls,0,bls,0)
tls=q.add(f"#X obj 20 {Y8+75} t b s b;"); q.con(bls,0,tls,0)
q.con(tls,2,q.add(f"#X msg 300 {Y8+100} \; ockm-project-list-start bang;"),0)
gl=joined(tls,1,"*",100,Y8+100); fg=q.add(f"#X obj 100 {Y8+150} file glob;"); q.con(gl,0,fg,0)
ug=q.add(f"#X obj 100 {Y8+175} unpack s f;"); sp=q.add(f"#X obj 100 {Y8+225} spigot;"); sn=q.add(f"#X obj 100 {Y8+250} file splitname;")
ls2=q.add(f"#X obj 100 {Y8+275} list split 1;"); sit=q.add(f"#X obj 100 {Y8+325} s ockm-project-item;"); syi=q.add(f"#X obj 100 {Y8+300} symbol;")
for c in [(fg,0,ug,0),(ug,1,sp,1),(ug,0,sp,0),(sp,0,sn,0),(sn,0,ls2,0),(ls2,1,syi,0),(syi,0,sit,0)]: q.con(*c)
q.con(tls,0,q.add(f"#X msg 20 {Y8+350} \; ockm-project-list-end bang;"),0)
# start-up: find projects/, open the project used last time (or 'default')
Y9=Y8+400
lb=q.add(f"#X obj 20 {Y9} loadbang;"); tlb=q.add(f"#X obj 20 {Y9+25} t b b;")
dm=q.add(f"#X msg 200 {Y9+50} dir;"); pdc=q.add(f"#X obj 200 {Y9+75} pdcontrol;"); bj=joined(pdc,0,"../projects",200,Y9+100)
q.con(lb,0,tlb,0); q.con(tlb,1,dm,0); q.con(dm,0,pdc,0); q.con(bj,0,sender("base",200,Y9+150),0)
q.con(tlb,0,q.add(f"#X msg 20 {Y9+50} \; ockm-slotset set 0;"),0)
bst=holder("base",20,Y9+100); q.con(tlb,0,bst,0)
tst=q.add(f"#X obj 20 {Y9+125} t b s;"); q.con(bst,0,tst,0)
tcr=q.add(f"#X obj 100 {Y9+130} t s b;"); q.con(tst,1,tcr,0)
clr2=q.add(f"#X msg 300 {Y9+150} clear;"); q.con(tcr,1,clr2,0); q.con(clr2,0,sender("curcmd",300,Y9+175),0)
cpr=joined(tcr,0,"current.txt",100,Y9+150)
tif=q.add(f"#X obj 100 {Y9+200} t s s;"); isf=q.add(f"#X obj 250 {Y9+225} file isfile;"); spf=q.add(f"#X obj 100 {Y9+250} spigot;")
q.con(cpr,0,tif,0); q.con(tif,1,isf,0); q.con(isf,0,spf,1); q.con(tif,0,spf,0); z9=q.add(f"#X msg 330 {Y9+250} 0;"); q.con(isf,1,z9,0); q.con(z9,0,spf,1)
cmd(spf,0,"read",100,Y9+275,sender("curcmd",100,Y9+325))
sz=q.add(f"#X obj 20 {Y9+275} text size {D}0-cur;"); q.con(tst,0,sz,0)
sel0=q.add(f"#X obj 20 {Y9+300} sel 0;"); q.con(sz,0,sel0,0)
dflt=q.add(f"#X msg 20 {Y9+450} symbol default;"); q.con(sel0,0,dflt,0)
g0=q.add(f"#X msg 100 {Y9+325} 0;"); tg=q.add(f"#X obj 100 {Y9+350} text get {D}0-cur;"); q.con(sel0,1,g0,0); q.con(g0,0,tg,0)
tchk=q.add(f"#X obj 100 {Y9+375} t b s;"); nhold=q.add(f"#X obj 100 {Y9+450} symbol;"); q.con(tg,0,tchk,0); q.con(tchk,1,nhold,1)
bch=holder("base",250,Y9+400); lpc=q.add(f"#X obj 250 {Y9+425} list append;"); fjc=q.add(f"#X obj 250 {Y9+450} file join;"); isd=q.add(f"#X obj 250 {Y9+475} file isdirectory;")
q.con(tchk,1,lpc,1); q.con(tchk,0,bch,0); q.con(bch,0,lpc,0); q.con(lpc,0,fjc,0); q.con(fjc,0,isd,0)
s01=q.add(f"#X obj 250 {Y9+500} sel 0;"); tb1=q.add(f"#X obj 330 {Y9+525} t b;"); q.con(isd,0,s01,0); q.con(isd,1,dflt,0); q.con(s01,0,dflt,0); q.con(s01,1,tb1,0); q.con(tb1,0,nhold,0)
sop=q.add(f"#X obj 20 {Y9+525} s ockm-project-open;"); q.con(dflt,0,sop,0); q.con(nhold,0,sop,0)
q.save("seq/ockm-store.pd","#N canvas 60 60 2200 1960 12;")

# ================= project files =================
def build_project(reset=False, demo=False):
    """Write the starter project: project.txt (tempo, effects, MIDI, accent, drum kit) and p1-p8.
    The starter is blank: every pattern empty, every part silent. demo=True puts the old demo grooves in 1-4.
    Without reset, only missing files are written, so saved work is kept."""
    os.makedirs(os.path.join(R,PROJ_DIR),exist_ok=True)
    def write(name, lines):
        path=os.path.join(R,PROJ_DIR,name)
        if reset or not os.path.exists(path):
            open(path,"w").write("".join(l+";\n" for l in lines))
    def fmt(v): return str(int(v)) if float(v)==int(v) else str(v)
    write("project.txt",[f"{h} {fmt(d)}" for h,d,_ in PROJECT_KEYS])
    def st(on,acc=()): return [2 if i in acc else (1 if i in on else 0) for i in range(16)]
    def steps(on): return [1 if i in on else 0 for i in range(16)]
    E=[0]*16
    four={0,4,8,12}; offb={2,6,10,14}; eighths=set(range(0,16,2))
    drums={"d1":[st(four),st(four),st({0,6,10}),st({0,7,10})],
           "d2":[E,E,st({4,12,15}),st({4,12})],
           "d3":[st({4,12}),st({4,12}),E,E],
           "d4":[st(offb,{6,14}),st({3,7,11,15},{7,15}),st(eighths,offb),st(eighths,{4,12})],
           "d5":[E,st(offb),st({14}),E],
           "d6":[E,st({3,11}),E,E],
           "d7":[E,st({5,13}),E,st({14})],
           "d8":[E,E,st({11,13}),E]}
    bass=[dict(note=[33,45,33,33,36,43,45,45,33,33,45,40,40,43,36,38],on=[1,1,0,1,1,1,1,0,1,1,1,1,0,1,1,1],
               acc=[1,0,0,0,0,1,0,0,1,0,0,0,0,1,0,0],slide=[0,0,0,0,1,1,0,0,0,0,1,0,0,0,0,1]),
          dict(note=[33]*14+[36,33],on=steps(offb),acc=steps({6,14}),slide=E),
          dict(note=[33,33,45,33,36,33,45,43,33,33,45,33,40,38,36,45],on=[1,1,1,0,1,1,1,1,1,1,1,0,1,1,1,1],acc=steps({0,4,8,12}),slide=steps({6,14})),
          dict(note=[33,33,33,33,33,33,33,33,31,31,31,31,36,36,36,36],on=steps({0,3,8,11}),acc=steps({0}),slide=E)]
    lead=[dict(note=E,on=E,acc=E,slide=E),dict(note=E,on=E,acc=E,slide=E),
          dict(note=[57,60,64,69,64,60,57,55]*2,on=steps(eighths),acc=steps({0,8}),slide=E),
          dict(note=[69]*4+[67]*4+[64]*4+[62]*4,on=steps({0,3,6,10}),acc=steps({0}),slide=steps({6}))]
    chord_on=[st(offb),st({3,10},{3}),st({0},{0}),st({0,8})]
    pad=lambda v:" ".join(str(x) for x in v+[0]*(STEPS-16))
    for k in range(SLOTN):
        if k==0 and not demo:  # pattern 1 of a blank project: the default sounds and settings, no steps
            write(LOOP_FILE,[f"{h} {fmt(d)}" for h,d,_ in PATTERN_KEYS]+["ockm-empty 1"]); continue
        if k>=4 or not demo:   # empty: no steps, and it takes on the sounds you're already using
            write(LOOP_FILE,["ockm-empty 1"]); continue
        lines=[f"{h} {fmt(d)}" if not h.endswith("-len") else f"{h} 16" for h,d,_ in PATTERN_KEYS]
        lines+=[f"ockm-pat-{nm} 0 {pad(drums[nm][k])}" for nm,_ in SLOTS]
        lines+=[f"ockm-pat-bass-{f} 0 {pad(bass[k][f])}" for f in MONO]
        lines+=[f"ockm-pat-lead-{f} 0 {pad(lead[k][f])}" for f in MONO]
        lines+=[f"ockm-pat-chord-on 0 {pad(chord_on[k])}", f"ockm-pat-chord-deg 0 {pad(E)}"]
        write(LOOP_FILE,lines)


build_project(reset=args.reset_patterns, demo=args.demo)

# ================= sample folders =================
# One folder per drum sound (SAMPLE_DIRS, near the voices). Drop WAV or AIFF files in and pick them on the drums tab.
def build_samples():
    base=os.path.join(R,"samples")
    for d in SAMPLE_DIRS: os.makedirs(os.path.join(base,d),exist_ok=True)
    readme=os.path.join(base,"README.md")
    if True:  # always refresh the readme
        open(readme,"w").write("""# Samples

One folder per drum sound: """+", ".join(SAMPLE_DIRS)+""". Perc 1 and perc 2 both pick from the perc folder, so you can mix and match.

- WAV or AIFF, 16 or 24 bit, 44.1 or 48 kHz. Mono is best for drums
- Short one-shots, trimmed so the hit starts right at the beginning of the file
- The screen shows samples by number, in file-name order: `01.wav` is sample 1. Numbering your files keeps it predictable
- Mono or stereo (only the left channel plays), any sample rate
- Up to about 64 per folder keeps browsing quick on the 10-inch screen

Audio files in here aren't saved to git (they're big). Back the folder up yourself.
""")
build_samples()
# the drum lab: a separate patch for designing claps and snares (tools/build_lab.py)
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_lab.py")).read())
print("built", R)
