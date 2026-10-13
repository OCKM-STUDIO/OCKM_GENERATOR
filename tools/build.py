#!/usr/bin/env python3
"""OCKM_GENERATOR build script.

Writes the Pure Data files for the whole project. Structural changes (new objects,
new wiring, new voices) are made here, then the patch files are rebuilt.
Sound tweaks are made with the controls in the patch, not here.

Usage:
  python3 tools/build.py                 rebuild every .pd file in the project
  python3 tools/build.py --out DIR       write to another folder (used by the tests)
  python3 tools/build.py --reset-patterns  also overwrite patterns/ with the starter patterns
                                          (this DELETES any patterns you have saved)

It never touches patterns/ unless you ask, and never touches sketches/, README or CHANGELOG.
"""
import os, sys, argparse
ap=argparse.ArgumentParser()
ap.add_argument("--out",default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument("--reset-patterns",action="store_true")
args=ap.parse_args()
R=args.out
for d in ("voices","seq","patterns"): os.makedirs(os.path.join(R,d),exist_ok=True)
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

# ---------------- voices ----------------
def kick_like(fn,title,f0,f1,sweep,dec,base):
    p=P(); header_text(p,title)
    inl=p.add("#X obj 30 50 inlet;")
    tbf=p.add("#X obj 30 80 t b f;")
    lev=p.add("#X obj 140 110 * 1;")
    pk,va=env(p,140,140,lev,base,dec)
    tbb=p.add("#X obj 30 140 t b b;")
    fs=p.add(f"#X obj 300 170 f {f0};"); fe=p.add(f"#X obj 360 140 f {f1};")
    pp=p.add("#X obj 300 200 pack f f;")
    pm=p.add(f"#X msg 300 230 {D}1 \\, {D}2 {sweep};")
    pv=p.add("#X obj 300 260 vline~;")
    osc=p.add("#X obj 300 290 osc~;")
    z=p.add("#X msg 30 260 0;")
    mul=p.add("#X obj 300 330 *~;")
    out=p.add("#X obj 300 370 outlet~;")
    for c in [(inl,0,tbf,0),(tbf,1,lev,0),(tbf,0,tbb,0),(tbb,1,fe,0),(fe,0,pp,1),(tbb,0,fs,0),(fs,0,pp,0),(tbb,0,z,0),
              (pp,0,pm,0),(pm,0,pv,0),(pv,0,osc,0),(z,0,osc,1),(osc,0,mul,0),(va,0,mul,1),(mul,0,out,0)]: p.con(*c)
    t,d,l=hooks(p,500,50)
    tx=p.add(f"#X obj 500 80 expr {f0}*pow(2\\,{D}f1/12) \; {f1}*pow(2\\,{D}f1/12);")
    dx=p.add(f"#X obj 670 80 * {dec/100};")
    p.con(t,0,tx,0); p.con(tx,0,fs,1); p.con(tx,1,fe,1); p.con(d,0,dx,0); p.con(dx,0,pk,1); p.con(l,0,lev,1)
    p.add("#X text 500 120 tune (semitones) / decay (% \\, 100 = normal) / level (0-1);")
    p.save(fn,"#N canvas 200 200 900 420 12;")

def noise_voice(fn,title,filt,freq,q,dec,base,msg="{D}1 \\, 0 {D}2"):
    p=P(); header_text(p,title)
    inl=p.add("#X obj 30 50 inlet;")
    lev=p.add("#X obj 30 80 * 1;")
    pk,va=env(p,30,110,lev,base,dec,msg)
    nz=p.add("#X obj 250 80 noise~;")
    fl=p.add(f"#X obj 250 120 {filt} {freq}{' '+str(q) if q else ''};")
    mul=p.add("#X obj 250 230 *~;")
    out=p.add("#X obj 250 270 outlet~;")
    for c in [(inl,0,lev,0),(nz,0,fl,0),(fl,0,mul,0),(va,0,mul,1),(mul,0,out,0)]: p.con(*c)
    t,d,l=hooks(p,450,50)
    tx=p.add(f"#X obj 450 80 expr {freq}*pow(2\\,{D}f1/12);")
    dx=p.add(f"#X obj 620 80 * {dec/100};")
    p.con(t,0,tx,0); p.con(tx,0,fl,1); p.con(d,0,dx,0); p.con(dx,0,pk,1); p.con(l,0,lev,1)
    p.add("#X text 450 120 tune (semitones) / decay (% \\, 100 = normal) / level (0-1);")
    p.save(fn,"#N canvas 200 200 900 320 12;")

def tonal_voice(fn,title,freqs,dec,base,square=False,filt=None,noise=None):
    """sum of oscillators (optionally squared-off), env; optional noise layer (filt,freq,dec,gain)"""
    p=P(); header_text(p,title)
    inl=p.add("#X obj 30 50 inlet;")
    lev=p.add("#X obj 30 80 * 1;")
    tff=p.add("#X obj 30 110 t f f;")
    pk,va=env(p,30,140,tff,base,dec)
    oscs=[]; summ=None
    for i,fq in enumerate(freqs):
        o=p.add(f"#X obj {250+i*110} 80 osc~ {fq};"); oscs.append(o); src=o
        if square:
            a=p.add(f"#X obj {250+i*110} 110 *~ 1000;"); c=p.add(f"#X obj {250+i*110} 140 clip~ -1 1;")
            p.con(o,0,a,0); p.con(a,0,c,0); src=c
        if summ is None: summ=src
        else:
            s2=p.add(f"#X obj 250 {170+i*5} +~;"); p.con(summ,0,s2,0); p.con(src,0,s2,1); summ=s2
    sc=p.add(f"#X obj 250 200 *~ {round(1/len(freqs),3)};"); p.con(summ,0,sc,0); last=sc
    if filt:
        f=p.add(f"#X obj 250 230 {filt};"); p.con(last,0,f,0); last=f
    mul=p.add("#X obj 250 270 *~;"); p.con(last,0,mul,0); p.con(va,0,mul,1)
    out=p.add("#X obj 250 380 outlet~;")
    p.con(inl,0,lev,0); p.con(lev,0,tff,0); p.con(mul,0,out,0)
    t,d,l=hooks(p,600,50)
    ex="expr "+" \; ".join(f"{fq}*pow(2\\,{D}f1/12)" for fq in freqs)
    tx=p.add(f"#X obj 600 80 {ex};")
    for i,o in enumerate(oscs): p.con(tx,i,o,0)
    dx=p.add(f"#X obj 770 110 * {dec/100};"); p.con(d,0,dx,0); p.con(dx,0,pk,1); p.con(l,0,lev,1); p.con(t,0,tx,0)
    if noise:
        nf,nfreq,ndec,ngain=noise
        pk2,va2=env(p,30,280,tff,ngain,ndec)
        nz=p.add("#X obj 500 230 noise~;"); fl=p.add(f"#X obj 500 260 {nf} {nfreq};"); m2=p.add("#X obj 500 300 *~;")
        p.con(nz,0,fl,0); p.con(fl,0,m2,0); p.con(va2,0,m2,1); p.con(m2,0,out,0)
        dx2=p.add(f"#X obj 870 110 * {ndec/100};"); p.con(d,0,dx2,0); p.con(dx2,0,pk2,1)
    p.add("#X text 600 150 tune (semitones) / decay (% \\, 100 = normal) / level (0-1);")
    p.save(fn,"#N canvas 200 200 1000 430 12;")

kick_like("voices/ockm-kick.pd","Kick: a sine wave that sweeps down fast. Input is hit strength (0-1).",150,45,80,300,1)
kick_like("voices/ockm-tom.pd","Tom: like the kick but higher and longer. Input is hit strength (0-1).",200,120,100,350,0.8)
noise_voice("voices/ockm-hat.pd","Closed hat: high-passed noise \\, very short.","hip~",7000,None,50,0.3)
noise_voice("voices/ockm-ohat.pd","Open hat: high-passed noise \\, longer tail.","hip~",6000,None,300,0.25)
noise_voice("voices/ockm-clap.pd","Clap: band-passed noise \\, three quick bursts then a tail.","bp~",1200,3,150,1,
            "{D}1 \\, 0 10 0 \\, {D}1 0 12 \\, 0 10 12 \\, {D}1 0 24 \\, 0 {D}2 24")
tonal_voice("voices/ockm-snare.pd","Snare: two tuned tones for the body plus filtered noise for the rattle.",[185,330],110,0.6,noise=("hip~",1500,180,0.5))
tonal_voice("voices/ockm-rim.pd","Rim: two high tones \\, very short.",[500,1720],30,0.6,filt="hip~ 400")
tonal_voice("voices/ockm-perc.pd","Perc: a 909-style rimshot. Two woody tones plus a sharp noise snap.",[330,820],60,0.4,filt="hip~ 200",noise=("hip~",3000,15,0.35))

# ---------------- drum row ----------------
p=P()
inl=p.add("#X obj 30 120 inlet;")
tr=p.add(f"#X obj 30 160 tabread ockm-pat-{D}1;")
sel=p.add("#X obj 30 190 sel 0;")
vel=p.add(f"#X obj 70 220 expr if({D}f1>1 \\, 1 \\, 1-{D}f2);")
out=p.add("#X obj 70 260 outlet;")
racc=p.add("#X obj 230 190 r ockm-accent;")
p.add("#X obj 30 300 table ockm-pat-\\$1 16;")
tw=p.add(f"#X obj 400 470 tabwrite ockm-pat-{D}1;")
for c in [(inl,0,tr,0),(tr,0,sel,0),(sel,1,vel,0),(racc,0,vel,1),(vel,0,out,0)]: p.con(*c)
for i in range(16):
    x=102+i*20+(i//4)*6
    t=p.add(f"#X obj {x} 22 tgl 18 0 empty ockm-sq-{D}1-{i} empty 17 7 0 10 #fcfcfc #000000 #000000 0 1;")
    k=p.add(f"#X obj {160+(i%8)*65} {380+(i//8)*40} pack 0 {i};")
    p.con(t,0,k,0); p.con(k,0,tw,0)
rs=p.add("#X obj 700 120 r ockm-store;"); ts=p.add("#X obj 700 150 t b f;"); ms=p.add("#X obj 760 180 * 16;")
ag=p.add(f"#X obj 700 210 array get ockm-pat-{D}1;"); aset=p.add(f"#X obj 700 250 array set ockm-bank-{D}1;")
for c in [(rs,0,ts,0),(ts,1,ms,0),(ms,0,aset,1),(ts,0,ag,0),(ag,0,aset,0)]: p.con(*c)
rl=p.add("#X obj 900 120 r ockm-load;"); ml=p.add("#X obj 900 150 * 16;")
agb=p.add(f"#X obj 900 210 array get ockm-bank-{D}1 0 16;"); tbl=p.add("#X obj 900 250 t b l;")
asp=p.add(f"#X obj 960 280 array set ockm-pat-{D}1;")
for c in [(rl,0,ml,0),(ml,0,agb,0),(agb,0,tbl,0),(tbl,1,asp,0)]: p.con(*c)
tr2=p.add("#X obj 900 310 t b b;"); z=p.add("#X msg 960 340 0;"); m16=p.add("#X msg 900 340 16;")
un=p.add("#X obj 900 370 until;"); cf=p.add("#X obj 900 400 f;"); cp=p.add("#X obj 950 400 + 1;")
tf=p.add("#X obj 900 430 t f f;"); mk=p.add(f"#X obj 1000 460 makefilename ockm-sq-{D}1-%d;")
rd=p.add(f"#X obj 900 460 tabread ockm-pat-{D}1;"); sm=p.add(f"#X msg 900 490 set {D}1;"); snd=p.add("#X obj 900 520 send;")
for c in [(tbl,0,tr2,0),(tr2,1,z,0),(z,0,cf,1),(tr2,0,m16,0),(m16,0,un,0),(un,0,cf,0),(cf,0,cp,0),(cp,0,cf,1),(cf,0,tf,0),
          (tf,1,mk,0),(mk,0,snd,1),(tf,0,rd,0),(rd,0,sm,0),(sm,0,snd,0)]: p.con(*c)
# edit hook: ockm-edit <track> <step> <0 off | 1 on | 2 accent>
re=p.add("#X obj 1150 120 r ockm-edit;"); ro=p.add(f"#X obj 1150 150 route {D}1;"); up=p.add("#X obj 1150 180 unpack f f;")
fv=p.add("#X obj 1210 240 f;"); ti=p.add("#X obj 1150 210 t b b f;"); ase=p.add(f"#X obj 1210 280 array set ockm-pat-{D}1;")
for c in [(re,0,ro,0),(ro,0,up,0),(up,1,fv,1),(up,0,ti,0),(ti,2,ase,1),(ti,1,fv,0),(fv,0,ase,0),(ti,0,tr2,0)]: p.con(*c)
p.add("#X text 100 120 step in -> look it up -> send hit strength out (accent = 1 \\, normal = 1 minus accent amount);")
p.add("#X text 700 90 store: copy this row into the bank;")
p.add("#X text 900 90 load: copy from the bank then update the squares;")
p.add("#X text 1150 90 edit: ockm-edit <track> <step> <0 off \\, 1 on \\, 2 accent>;")
p.save("seq/ockm-row.pd","#N canvas 200 200 1500 580 12;",["#X coords 0 -1 1 1 340 24 3 100 19;"])

# ---------------- bass sequencer (add edit hook) ----------------
p=P()
p.add("#X text 20 10 Bass pattern. Each step has a note \\, on/off \\, accent and slide.;")
inl=p.add("#X obj 30 60 inlet;"); t5=p.add("#X obj 30 100 t f f f f f;")
rn=p.add(f"#X obj 30 300 tabread ockm-pat-{D}1-note;"); ra=p.add(f"#X obj 140 260 tabread ockm-pat-{D}1-acc;"); rsl=p.add(f"#X obj 250 220 tabread ockm-pat-{D}1-slide;")
a15=p.add("#X obj 360 140 + 15;"); m16=p.add("#X obj 360 170 mod 16;"); t2=p.add("#X obj 360 200 t f f;")
ps=p.add(f"#X obj 360 260 tabread ockm-pat-{D}1-slide;"); po=p.add(f"#X obj 470 230 tabread ockm-pat-{D}1-on;"); mul=p.add("#X obj 360 300 *;")
pk=p.add("#X obj 30 360 pack f f f f;"); ro=p.add(f"#X obj 600 140 tabread ockm-pat-{D}1-on;"); sp=p.add("#X obj 30 400 spigot;")
eq=p.add("#X obj 600 180 == 0;"); s1=p.add("#X obj 600 210 sel 1;"); off=p.add("#X msg 600 240 off;"); out=p.add("#X obj 30 460 outlet;")
for j,nm in enumerate(["note","on","acc","slide"]): p.add(f"#X obj {30+j*160} 520 table ockm-pat-{D}1-{nm} 16;")
for c in [(inl,0,t5,0),(t5,4,ro,0),(t5,3,rsl,0),(t5,2,a15,0),(t5,1,ra,0),(t5,0,rn,0),(rn,0,pk,0),(ra,0,pk,1),(rsl,0,pk,3),
    (a15,0,m16,0),(m16,0,t2,0),(t2,1,po,0),(t2,0,ps,0),(po,0,mul,1),(ps,0,mul,0),(mul,0,pk,2),(pk,0,sp,0),(ro,0,sp,1),(ro,0,eq,0),(eq,0,s1,0),(s1,0,off,0),(off,0,out,0),(sp,0,out,0)]: p.con(*c)
rs=p.add("#X obj 720 120 r ockm-store;"); ts=p.add("#X obj 720 150 t b f;"); ms=p.add("#X obj 780 180 * 16;")
rl=p.add("#X obj 720 320 r ockm-load;"); ml=p.add("#X obj 780 380 * 16;")
p.con(rs,0,ts,0); p.con(ts,1,ms,0); p.con(rl,0,ml,0)
re=p.add("#X obj 720 560 r ockm-bass-edit;"); tl=p.add("#X obj 720 590 t l l;"); ls=p.add("#X obj 900 620 list split 1;")
up=p.add("#X obj 720 650 unpack f f f f f;")
p.con(re,0,tl,0); p.con(tl,1,ls,0); p.con(tl,0,up,0)
for j,nm in enumerate(["note","on","acc","slide"]):
    x=720+j*190
    ag=p.add(f"#X obj {x} 220 array get ockm-pat-{D}1-{nm};"); aset=p.add(f"#X obj {x} 260 array set ockm-bank-{D}1-{nm};")
    p.con(ts,0,ag,0); p.con(ag,0,aset,0); p.con(ms,0,aset,1)
    agb=p.add(f"#X obj {x} 420 array get ockm-bank-{D}1-{nm} 0 16;"); asp=p.add(f"#X obj {x} 460 array set ockm-pat-{D}1-{nm};")
    p.con(ml,0,agb,0); p.con(agb,0,asp,0)
    tw=p.add(f"#X obj {x} 700 tabwrite ockm-pat-{D}1-{nm};"); p.con(ls,0,tw,1); p.con(up,j+1,tw,0)
p.add("#X text 140 400 only lets the note through if the step is on;")
p.add("#X text 420 100 glide into this note if the previous step had slide on;")
p.add("#X text 720 530 edit one step: ockm-bass-edit <step> <note> <on> <accent> <slide>;")
p.save("seq/ockm-bassseq.pd","#N canvas 150 150 1500 760 12;")

# ---------------- main patch ----------------
DRUMS=[("kick","kick","ockm-kick"),("snare","snare","ockm-snare"),("clap","clap","ockm-clap"),("rim","rim","ockm-rim"),
       ("chat","closed hat","ockm-hat"),("ohat","open hat","ockm-ohat"),("tom","tom","ockm-tom"),("perc","rimshot","ockm-perc")]
p=P()
p.raw("#X declare -path voices -path seq;")
p.add("#X text 30 10 OCKM_GENERATOR v0.8. Click start \\, then click squares to build a beat. Pick a pattern slot \\, press save to keep it.;")
lb=p.add("#X obj 30 50 loadbang;"); lbt=p.add("#X obj 30 75 t b b b;")
dsp=p.add("#X msg 1100 760 \; pd dsp 1;")
bpmm=p.add("#X msg 30 105 124;"); bpm=p.add("#X floatatom 30 135 5 40 200 0 - - -;"); p.con(p.add("#X obj 120 105 r ockm-bpm;"),0,bpm,0); p.add("#X text 85 135 BPM;")
ex=p.add(f"#X obj 30 165 expr 15000/{D}f1;"); p.con(ex,0,p.add("#X obj 140 165 s ockm-stepms;"),0)
tg=p.add("#X obj 250 50 tgl 25 0 ockm-playing ockm-play empty 17 7 0 10 #fcfcfc #000000 #000000 0 1;"); p.add("#X text 282 52 start/stop;")
met=p.add("#X obj 250 100 metro 120;"); msp=p.add("#X obj 250 125 spigot 1;"); rtick=p.add("#X obj 180 125 r ockm-tick;"); rsync=p.add("#X obj 400 130 r ockm-sync;"); seq0=p.add("#X obj 400 150 == 0;"); rrst=p.add("#X obj 470 130 r ockm-reset;"); zr=p.add("#X msg 470 155 0;"); f=p.add("#X obj 250 150 f;"); p1=p.add("#X obj 300 150 + 1;"); m16=p.add("#X obj 300 175 mod 16;")
tff=p.add("#X obj 250 180 t f f;"); tsw=p.add("#X obj 250 205 t f f;"); md2=p.add("#X obj 340 205 mod 2;")
mfr=p.add("#X obj 340 230 *;"); mms=p.add("#X obj 340 255 *;"); pipe=p.add("#X obj 250 280 pipe 0;")
disp=p.add("#X floatatom 330 300 5 0 0 0 - - -;"); p.add("#X text 380 300 step;"); sst=p.add("#X obj 450 300 s ockm-step;")
swm=p.add("#X msg 120 205 56;"); sw=p.add("#X floatatom 120 230 5 50 75 0 - - -;"); p.add("#X text 120 255 swing %;")
swx=p.add(f"#X obj 120 280 expr ({D}f1-50)/50;")
accm=p.add("#X msg 30 205 0.3;"); acc=p.add("#X floatatom 30 230 4 0 1 0 - - ockm-accent;"); p.add("#X text 30 255 accent;")
for c in [(lb,0,lbt,0),(lbt,0,dsp,0),(lbt,0,bpmm,0),(bpmm,0,bpm,0),(bpm,0,ex,0),(ex,0,met,1),(ex,0,mms,1),(tg,0,met,0),
    (met,0,msp,0),(msp,0,f,0),(rtick,0,f,0),(rsync,0,seq0,0),(seq0,0,msp,1),(rrst,0,zr,0),(zr,0,f,1),(f,0,p1,0),(p1,0,m16,0),(m16,0,f,1),(f,0,tff,0),(tff,0,tsw,0),(tsw,1,md2,0),(md2,0,mfr,0),(mfr,0,mms,0),(mms,0,pipe,1),(tsw,0,pipe,0),
    (pipe,0,disp,0),(pipe,0,sst,0),(lbt,0,swm,0),(swm,0,sw,0),(sw,0,swx,0),(swx,0,mfr,1),(lbt,0,accm,0),(accm,0,acc,0)]: p.con(*c)
# pattern slots
p.add("#X text 520 50 pattern;")
hr=p.add("#X obj 520 75 hradio 25 1 0 8 empty ockm-slotset empty 0 -8 0 10 #fcfcfc #000000 #000000 0;")
p.add("#X text 520 105 1    2    3    4    5    6    7    8;")
sv=p.add("#X obj 740 50 bng 25 250 50 0 empty ockm-save empty 17 7 0 10 #fcfcfc #000000 #000000;"); p.add("#X text 772 52 save;")
p.con(hr,0,p.add("#X obj 520 140 s ockm-want;"),0)
rw=p.add("#X obj 560 170 r ockm-want;"); tbf=p.add("#X obj 560 195 t b f;"); pend=p.add("#X obj 560 330 f;")
tbb=p.add("#X obj 560 220 t b b;"); one=p.add("#X msg 640 245 1;"); spg=p.add("#X obj 560 250 spigot 1;")
tbb2=p.add("#X obj 560 275 t b b;"); zero=p.add("#X msg 640 300 0;"); flag=p.add("#X obj 700 300 f;"); eqz=p.add("#X obj 330 50 == 0;")
s0=p.add("#X obj 400 180 sel 0;"); s1=p.add("#X obj 700 330 sel 1;"); tbb3=p.add("#X obj 700 355 t b b;"); zero2=p.add("#X msg 780 380 0;")
tcur=p.add("#X obj 560 360 t f f;"); cur=p.add("#X obj 740 140 f;"); sld=p.add("#X obj 560 385 s ockm-load;")
tsv=p.add("#X obj 740 85 t b b;"); sstore=p.add("#X obj 740 170 s ockm-store;")
for c in [(rw,0,tbf,0),(tbf,1,pend,1),(tbf,0,tbb,0),(tbb,1,one,0),(one,0,flag,1),(tbb,0,spg,0),(spg,0,tbb2,0),(tbb2,1,zero,0),(zero,0,flag,1),(tbb2,0,pend,0),
    (tg,0,eqz,0),(eqz,0,spg,1),(tff,1,s0,0),(s0,0,flag,0),(flag,0,s1,0),(s1,0,tbb3,0),(tbb3,1,zero2,0),(zero2,0,flag,1),(tbb3,0,pend,0),
    (pend,0,tcur,0),(tcur,1,cur,1),(tcur,0,sld,0),(sv,0,tsv,0),(tsv,1,cur,0),(cur,0,sstore,0)]: p.con(*c)
names=[d[0] for d in DRUMS]
banks=["ockm-bank-"+n for n in names]+[f"ockm-bank-bass-{n}" for n in ["note","on","acc","slide"]]
files=names+[f"bass-{n}" for n in ["note","on","acc","slide"]]
wr=p.add("#X msg 840 85 \; "+" \; ".join(f"{b} write patterns/{fl}.txt" for b,fl in zip(banks,files))+";")
p.con(tsv,0,wr,0)
rdm=p.add("#X msg 1100 560 \; "+" \; ".join(f"{b} read patterns/{fl}.txt" for b,fl in zip(banks,files))+" \; ockm-slotset set 0 \; ockm-want 0;")
p.con(lbt,2,rdm,0)
for i,b in enumerate(banks): p.add(f"#X obj {1100+(i%2)*190} {420+(i//2)*22} array define {b} 128;")
p.add("#X text 1100 395 pattern banks (8 slots x 16 steps) \\, saved in the patterns folder;")
# drums
mix=p.add("#X obj 560 900 *~ 0.3;"); fx=p.add("#X obj 560 930 ockm-fx;"); dac=p.add("#X obj 560 965 dac~;"); smaster=p.add("#X obj 640 965 s~ ockm-master;")
p.con(mix,0,fx,0); p.con(fx,0,dac,0); p.con(fx,0,dac,1); p.con(fx,0,smaster,0)
for r,(nm,label,voice) in enumerate(DRUMS):
    y=340+r*40
    p.add(f"#X text 20 {y+2} {label};")
    row=p.add(f"#X obj 110 {y} ockm-row {nm};"); v=p.add(f"#X obj 560 {y+2} {voice} {nm};")
    p.con(pipe,0,row,0); p.con(row,0,v,0); p.con(v,0,mix,0)
    vs=p.add(f"#X obj 760 {y+2} *~ 0;"); vt=p.add(f"#X obj 830 {y+2} throw~ ockm-revbus;"); vr=p.add(f"#X obj 760 {y-18} r ockm-{nm}-verb;")
    p.con(v,0,vs,0); p.con(vs,0,vt,0); p.con(vr,0,vs,1)
    ds=p.add(f"#X obj 990 {y+2} *~ 0;"); dt_=p.add(f"#X obj 1060 {y+2} throw~ ockm-dlybus;"); dr_=p.add(f"#X obj 990 {y-18} r ockm-{nm}-delay;")
    p.con(v,0,ds,0); p.con(ds,0,dt_,0); p.con(dr_,0,ds,1)
# drum settings subpatch
sub=P()
sub.add("#X text 20 10 Per-drum settings. Tune in semitones \\, decay in % (100 = normal) \\, level 0 to 1.;")
slb=sub.add("#X obj 20 40 loadbang;")
for i,(nm,label,_) in enumerate(DRUMS):
    y=80+i*30
    sub.add(f"#X text 20 {y} {label};")
    VERB={"kick":0,"snare":0.25,"clap":0.35,"rim":0.2,"chat":0.1,"ohat":0.15,"tom":0.2,"perc":0.25}
    DLY={"kick":0,"snare":0,"clap":0,"rim":0.25,"chat":0,"ohat":0,"tom":0,"perc":0.3}
    for j,(param,dflt,lo,hi) in enumerate([("tune",0,-12,12),("decay",100,10,400),("level",1,0,1),("verb",VERB[nm],0,1),("delay",DLY[nm],0,1)]):
        m=sub.add(f"#X msg {130+j*150} {y} {dflt};")
        fa=sub.add(f"#X floatatom {175+j*150} {y} 5 {lo} {hi} 0 - - ockm-{nm}-{param};")
        sub.con(slb,0,m,0); sub.con(m,0,fa,0)
sub.add("#X text 130 60 tune             decay            level            reverb send      delay send;")
p.L.append(sub.text("#N canvas 300 200 940 360 drum-settings 0;").rstrip("\n"))
ds=p.add("#X restore 30 830 pd drum-settings;")
p.add("#X text 30 855 open for per-drum tune \\, decay and level;")
# bass
by=340+len(DRUMS)*40+10
p.add(f"#X text 20 {by+2} bass;")
bs=p.add(f"#X obj 110 {by} ockm-bassseq bass;"); ac=p.add(f"#X obj 560 {by} ockm-bass;")
p.con(pipe,0,bs,0); p.con(bs,0,ac,0); p.con(ac,0,mix,0)
bvs=p.add(f"#X obj 760 {by} *~ 0;"); bvt=p.add(f"#X obj 830 {by} throw~ ockm-revbus;"); bvr=p.add(f"#X obj 760 {by-18} r ockm-bass-verb;")
p.con(ac,0,bvs,0); p.con(bvs,0,bvt,0); p.con(bvr,0,bvs,1)
bds=p.add(f"#X obj 990 {by} *~ 0;"); bdt=p.add(f"#X obj 1060 {by} throw~ ockm-dlybus;"); bdr=p.add(f"#X obj 990 {by-18} r ockm-bass-delay;")
p.con(ac,0,bds,0); p.con(bds,0,bdt,0); p.con(bdr,0,bds,1)
for j,(lab,v,lo,hi,hook) in enumerate([("engine",0,0,5,"ockm-bass-engine"),("k1",0.37,0,1,"ockm-bass-k1"),("k2",0.9,0,1,"ockm-bass-k2"),
        ("k3",0.31,0,1,"ockm-bass-k3"),("k4",0.55,0,1,"ockm-bass-k4"),("drive",0,0,1,"ockm-bass-drive")]):
    m=p.add(f"#X msg {110+j*75} {by+40} {v};"); fa=p.add(f"#X floatatom {110+j*75} {by+70} 5 {lo} {hi} 0 - - {hook};")
    p.con(lbt,0,m,0); p.con(m,0,fa,0)
p.add(f"#X text 110 {by+95} engine  k1  k2  k3  k4  drive (engines: 0 acid 1 sub 2 fm 3 reese 4 pluck 5 saw);")
s0b=p.add("#X obj 400 80 sel 0;"); offm=p.add("#X msg 400 105 off;")
p.con(tg,0,s0b,0); p.con(s0b,0,offm,0); p.con(offm,0,ac,0)
# master fx subpatch
sub=P()
sub.add("#X text 20 10 Master effects. Filter -1 to 1 (below 0 low-pass \\, above 0 high-pass). Drive 0 to 1. Delay in steps.;")
slb=sub.add("#X obj 20 40 loadbang;")
for i,(lab,dflt,lo,hi,hook) in enumerate([("filter",0,-1,1,"ockm-filter"),("drive",0,0,1,"ockm-drive"),("delay level",0.5,0,1,"ockm-delay-mix"),
        ("delay feedback",0.4,0,0.9,"ockm-delay-fb"),("delay steps",3,1,8,"ockm-delay-steps"),("reverb level",0.5,0,1,"ockm-verb-mix"),("reverb size",0.6,0,1,"ockm-verb-size"),("reverb tone",0.5,0,1,"ockm-verb-tone"),("bass reverb send",0,0,1,"ockm-bass-verb"),("bass delay send",0,0,1,"ockm-bass-delay")]):
    y=80+i*30
    sub.add(f"#X text 20 {y} {lab};")
    m=sub.add(f"#X msg 160 {y} {dflt};"); fa=sub.add(f"#X floatatom 220 {y} 5 {lo} {hi} 0 - - {hook};")
    sub.con(slb,0,m,0); sub.con(m,0,fa,0)
p.L.append(sub.text("#N canvas 320 220 560 420 master-fx 0;").rstrip("\n"))
p.add("#X restore 250 830 pd master-fx;")
sub=P()
sub.add("#X text 20 10 MIDI clock. Sync 0 = leader (sends clock) \\, 1 = follower (plays to incoming clock). Clock out 1 = send clock when leading.;")
slb=sub.add("#X obj 20 40 loadbang;")
for i,(lab,dflt,lo,hi,hook) in enumerate([("sync",0,0,1,"ockm-sync"),("clock out",1,0,1,"ockm-clock-out")]):
    y=80+i*30
    sub.add(f"#X text 20 {y} {lab};")
    m=sub.add(f"#X msg 120 {y} {dflt};"); fa=sub.add(f"#X floatatom 170 {y} 3 {lo} {hi} 0 - - {hook};")
    sub.con(slb,0,m,0); sub.con(m,0,fa,0)
p.L.append(sub.text("#N canvas 340 240 640 180 midi-sync 0;").rstrip("\n"))
p.add("#X restore 450 830 pd midi-sync;")
p.add("#X text 450 855 MIDI clock leader or follower;")
p.add("#X obj 450 880 ockm-clock;")
p.add("#X text 250 855 filter \\, drive and delay;")
gy=by+130
p.add("#X obj 1100 800 declare -path voices -path seq;")
p.add(f"#X obj 110 {gy+30} ockm-bassgen bass;")
p.add(f"#X text 110 {gy} bass generator (temporary controls);")
for j,(lab,hi,hook) in enumerate([("rhythm",7,"ockm-bass-rhythm"),("notes",7,"ockm-bass-notes"),("key",11,"ockm-bass-root"),("scale",5,"ockm-bass-scale")]):
    p.add(f"#X floatatom {110+j*110} {gy+60} 3 0 {hi} 0 {lab} - {hook};")
p.add(f"#X text 110 {gy+85} rhythm 0 offbeat 1 rolling 2 gallop 3 acid 4 dub 5 bounce 6 acid16 7 trip-hop / notes 0 root 1 octaves 2 root-fifth 3 acid-riff 4 walk-up 5 stab 6 dub 7 pedal;")
p.add(f"#X text 110 {gy+105} key 0 C ... 9 A ... 11 B / scale 0 minor 1 major 2 dorian 3 phrygian 4 mixolydian 5 harmonic minor;")
p.save("OCKM_GENERATOR.pd","#N canvas 40 40 1420 1000 12;")


# ================= bass core: shared note logic for every engine =================
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
mG=q.add(f"#X msg 330 300 {D}1 60;"); mN=q.add(f"#X msg 420 300 {D}1;")
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
q.save("voices/ockm-bass-core.pd","#N canvas 150 150 900 520 12;")

# ================= engines =================
def engine(fn,idx,title,build):
    q=P(); q.add(f"#X text 20 10 {title};")
    inl=q.add("#X obj 30 50 inlet;")
    sp=q.add("#X obj 30 80 spigot 1;")
    core=q.add("#X obj 30 120 ockm-bass-core;")
    ks=[q.add(f"#X obj {200+i*110} 50 inlet;") for i in range(4)]
    re=q.add("#X obj 700 50 r ockm-bass-engine;"); eq=q.add(f"#X obj 700 80 == {idx};"); tf=q.add("#X obj 700 110 t f f;")
    sw=q.add("#X obj 700 170 switch~;"); s0=q.add("#X obj 760 140 sel 0;"); om=q.add("#X msg 760 170 off;")
    for c in [(inl,0,sp,0),(sp,0,core,0),(re,0,eq,0),(eq,0,tf,0),(tf,1,sw,0),(tf,0,s0,0),(s0,0,om,0),(om,0,core,0),(tf,0,sp,1)]: q.con(*c)
    dx=q.add(f"#X obj 650 50 expr 20*pow(100\\,{D}f1);"); q.con(ks[3],0,dx,0); q.con(dx,0,core,1)
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
    em=q.add("#X obj 300 200 *~ 12;"); pl=q.add("#X obj 30 230 +~;"); mt=q.add("#X obj 30 260 mtof~;"); osc=q.add("#X obj 30 290 osc~;")
    gn=q.add("#X obj 30 320 *~ 1;"); th=q.add(f"#X obj 30 350 expr~ tanh({D}v1);"); lp=q.add("#X obj 30 380 lop~ 400;")
    am=q.add("#X obj 30 410 *~;"); g=q.add("#X obj 30 440 *~ 0.9;")
    k1=q.add(f"#X obj 200 140 expr 60*pow(2\\,7*{D}f1);"); k2=q.add(f"#X obj 310 140 expr 1+6*{D}f1;"); k3=q.add("#X obj 420 140 * 24;")
    for c in [(core,1,em,0),(core,0,pl,0),(em,0,pl,1),(pl,0,mt,0),(mt,0,osc,0),(osc,0,gn,0),(gn,0,th,0),(th,0,lp,0),(lp,0,am,0),(core,2,am,1),(am,0,g,0),(g,0,out,0),
              (ks[0],0,k1,0),(k1,0,lp,1),(ks[1],0,k2,0),(k2,0,gn,1),(ks[2],0,k3,0),(k3,0,em,1)]: q.con(*c)
    q.add("#X text 200 110 k1 tone / k2 drive / k3 pitch drop on each note;")

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
    bob=q.add("#X obj 30 400 bob~;"); rs=q.add("#X msg 450 300 1.2;"); lb=q.add("#X obj 450 270 loadbang;")
    am=q.add("#X obj 30 430 *~;"); g=q.add("#X obj 30 460 *~ 1.2;")
    k1=q.add(f"#X obj 200 140 expr 40*pow(2\\,8*{D}f1);"); k2=q.add(f"#X obj 310 140 expr 0.003+0.02*{D}f1 \; 0.003+0.02*{D}f1;")
    up=q.add("#X obj 310 170 + 1;"); dn=q.add("#X obj 380 170 expr 1-$f1;".replace("$","\\$")); k3=q.add("#X obj 420 140 * 6000;")
    for c in [(core,0,mt,0),(mt,0,p1,0),(mt,0,ua,0),(mt,0,db,0),(ua,0,p2,0),(db,0,p3,0),(p1,0,s1,0),(p2,0,s1,1),(s1,0,s2,0),(p3,0,s2,1),
              (s2,0,sc,0),(sc,0,ce,0),(ce,0,bob,0),(core,1,em,0),(em,0,ad,0),(ad,0,cl,0),(cl,0,bob,1),(lb,0,rs,0),(rs,0,bob,2),
              (bob,0,am,0),(core,2,am,1),(am,0,g,0),(g,0,out,0),(ks[0],0,k1,0),(k1,0,ad,1),(ks[1],0,k2,0),(k2,0,up,0),(k2,1,dn,0),
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

engine("voices/ockm-bass-acid.pd",0,"Acid engine: saw wave into a resonant filter",acid)
engine("voices/ockm-bass-sub.pd",1,"Sub engine: a driven sine wave with a pitch drop. Deep and clean",sub)
engine("voices/ockm-bass-fm.pd",2,"FM engine: one sine wave bending another. Punchy and metallic",fm)
engine("voices/ockm-bass-reese.pd",3,"Reese engine: three detuned saws beating against each other. Dark and wide",reese)
engine("voices/ockm-bass-pluck.pd",4,"Pluck engine: short and bright. Good for rolling riffs",pluck)

def sawe(q,core,ks,out):
    # raw sawtooth: optional second detuned saw and sub saw, simple tone control, full-level notes that end hard
    mt=q.add("#X obj 30 200 mtof~;")
    p1=q.add("#X obj 30 240 phasor~;"); dt=q.add("#X obj 150 210 *~ 1;"); p2=q.add("#X obj 150 240 phasor~;")
    sb=q.add("#X obj 270 210 *~ 0.5;"); p3=q.add("#X obj 270 240 phasor~;")
    g2=q.add("#X obj 150 270 *~ 0;"); g3=q.add("#X obj 270 270 *~ 0;")
    m1=q.add("#X obj 30 300 +~;"); m2=q.add("#X obj 30 325 +~;")
    nm=q.add(f"#X obj 30 355 expr~ ({D}v1-0.5*(1+{D}f2+{D}f3))*2/(1+{D}f2+{D}f3);")
    lp1=q.add("#X obj 30 390 lop~ 20000;"); lp2=q.add("#X obj 30 415 lop~ 20000;")
    ec=q.add("#X obj 450 300 *~ 4;"); cl=q.add("#X obj 450 330 clip~ 0 1;")
    am=q.add("#X obj 30 450 *~;"); g=q.add("#X obj 30 480 *~ 0.6;")
    k1=q.add(f"#X obj 200 140 expr 60*pow(2\\,8.4*{D}f1);")
    k2=q.add(f"#X obj 310 140 expr 1+0.02*{D}f1 \; if({D}f1>0 \\, 0.7 \\, 0);")
    k3=q.add("#X obj 420 170 * 0.8;")
    for c in [(core,0,mt,0),(mt,0,p1,0),(mt,0,dt,0),(dt,0,p2,0),(mt,0,sb,0),(sb,0,p3,0),(p2,0,g2,0),(p3,0,g3,0),
              (p1,0,m1,0),(g2,0,m1,1),(m1,0,m2,0),(g3,0,m2,1),(m2,0,nm,0),(nm,0,lp1,0),(lp1,0,lp2,0),
              (core,1,ec,0),(ec,0,cl,0),(lp2,0,am,0),(cl,0,am,1),(am,0,g,0),(g,0,out,0),
              (ks[0],0,k1,0),(k1,0,lp1,1),(k1,0,lp2,1),(ks[1],0,k2,0),(k2,0,dt,1),(k2,1,g2,1),(k2,1,nm,1),
              (ks[2],0,k3,0),(k3,0,g3,1),(k3,0,nm,2)]: q.con(*c)
    q.add("#X text 200 110 k1 tone (1 = fully raw) / k2 second saw detune (0 = single saw) / k3 sub saw an octave down / k4 note length. Notes play at full level then stop hard.;")

engine("voices/ockm-bass-saw.pd",5,"Saw engine: a raw sawtooth. No squelch \\, just a hard buzzy bass",sawe)

# ================= bass wrapper =================
q=P()
q.add("#X text 20 10 Bass: six engines \\, one plays at a time (ockm-bass-engine 0 to 5). Knobs k1-k4 and drive come in on hooks.;")
inl=q.add("#X obj 30 50 inlet;")
ks=[q.add(f"#X obj {200+i*130} 50 r ockm-bass-k{i+1};") for i in range(4)]
names=["acid","sub","fm","reese","pluck","saw"]
eng=[q.add(f"#X obj {30+i*130} 130 ockm-bass-{n};") for i,n in enumerate(names)]
sm=q.add("#X obj 30 200 +~;")
for i,e in enumerate(eng):
    q.con(inl,0,e,0)
    for j,k in enumerate(ks): q.con(k,0,e,j+1)
    q.con(e,0,sm,0)
rd=q.add("#X obj 400 200 r ockm-bass-drive;"); dx=q.add(f"#X obj 400 230 expr 1+{D}f1*9;")
th=q.add(f"#X obj 30 260 expr~ tanh({D}v1*max({D}f2\\,1))/sqrt(max({D}f2\\,1));"); out=q.add("#X obj 30 300 outlet~;")
q.add("#X text 400 260 drive: 0 clean \\, 1 heavy;")
for c in [(rd,0,dx,0),(dx,0,th,1),(sm,0,th,0),(th,0,out,0)]: q.con(*c)
q.save("voices/ockm-bass.pd","#N canvas 140 140 900 340 12;")

# ================= master effects =================
q=P()
q.add("#X text 20 10 Master effects: reverb and delay returns \\, DJ filter \\, drive \\, tempo-synced delay \\, then a soft limiter.;")
inl0=q.add("#X obj 30 30 inlet~;"); ctch=q.add("#X obj 150 30 catch~ ockm-revbus;"); verb=q.add("#X obj 150 55 ockm-verb;"); vm=q.add("#X obj 150 75 *~ 0.3;")
rvm=q.add("#X obj 300 30 r ockm-verb-mix;"); pre=q.add("#X obj 30 70 +~;"); inl=q.add("#X obj 30 90 +~;")
dcat=q.add("#X obj 200 300 catch~ ockm-dlybus;")
for c in [(inl0,0,pre,0),(ctch,0,verb,0),(verb,0,vm,0),(vm,0,pre,1),(rvm,0,vm,1),(pre,0,inl,0)]: q.con(*c)
h1=q.add("#X obj 30 90 hip~ 10;"); h2=q.add("#X obj 30 115 hip~ 10;"); l1=q.add("#X obj 30 140 lop~ 20000;"); l2=q.add("#X obj 30 165 lop~ 20000;")
rf=q.add("#X obj 300 50 r ockm-filter;")
fx=q.add(f"#X obj 300 80 expr if({D}f1>0 \\, 20*pow(2\\,{D}f1*9.6) \\, 10) \; if({D}f1<0 \\, 20000*pow(2\\,{D}f1*9.6) \\, 20000);")
rdv=q.add("#X obj 300 200 r ockm-drive;"); dvx=q.add(f"#X obj 300 230 expr 1+{D}f1*9;")
th=q.add(f"#X obj 30 230 expr~ tanh({D}v1*max({D}f2\\,1))/sqrt(max({D}f2\\,1));")
dw=q.add(f"#X obj 200 330 delwrite~ {D}0-dly 4000;"); dr=q.add(f"#X obj 200 290 delread~ {D}0-dly 363;")
fb=q.add("#X obj 200 360 *~ 0.4;"); mx=q.add("#X obj 200 400 *~ 0;")
rst=q.add("#X obj 500 250 r ockm-stepms;"); rsteps=q.add("#X obj 620 250 r ockm-delay-steps;"); dtm=q.add("#X obj 500 280 * 3;")
rfb=q.add("#X obj 500 330 r ockm-delay-fb;"); rmx=q.add("#X obj 500 380 r ockm-delay-mix;")
tff=q.add("#X obj 620 280 t b f;"); fs=q.add("#X obj 500 220 f 121;")
sm=q.add("#X obj 30 440 +~;"); lim=q.add(f"#X obj 30 470 expr~ tanh({D}v1);"); out=q.add("#X obj 30 510 outlet~;")
for c in [(inl,0,h1,0),(h1,0,h2,0),(h2,0,l1,0),(l1,0,l2,0),(rf,0,fx,0),(fx,0,h1,1),(fx,0,h2,1),(fx,1,l1,1),(fx,1,l2,1),
          (rdv,0,dvx,0),(dvx,0,th,1),(l2,0,th,0),(dcat,0,dw,0),(dr,0,fb,0),(fb,0,dw,0),(dr,0,mx,0),(mx,0,inl,1),
          (rst,0,fs,0),(fs,0,dtm,0),(rsteps,0,tff,0),(tff,1,dtm,1),(tff,0,fs,0),(dtm,0,dr,0),(rfb,0,fb,1),(rmx,0,mx,1),
          (th,0,lim,0),(lim,0,out,0)]: q.con(*c)
q.add("#X text 500 410 delay time = step length x delay steps (3 = dotted 8th);")
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

def build_bassgen():
    L=[];C=[];A={}
    def add(s,after=None):
        L.append(s); i=sum(1 for x in L if not x.startswith("#A"))-1
        if after: L.append(after)
        return i
    def con(a,b,c,d): C.append((a,b,c,d))
    add("#X text 20 10 Bass generator. Builds a bassline from a rhythm preset + a note pattern + a key. Writes it into the bass pattern.;")
    add("#X text 20 40 Rhythm codes: 0 rest \\, 1 note \\, 2 accent \\, 3 note + slide into next \\, 4 accent + slide into next;")
    add("#X text 20 60 Note patterns are scale degrees \\, used in turn on each note: 0 root \\, 2 third \\, 4 fifth \\, 7 octave \\, -3 fifth below;")
    RHY=[("offbeat",      "0 0 2 0 0 0 1 0 0 0 2 0 0 0 1 0"),
       ("rolling",      "0 2 1 1 0 2 1 1 0 2 1 1 0 2 1 1"),
       ("gallop",       "0 0 2 1 0 1 2 0 0 0 2 1 0 1 2 0"),
       ("acid-classic", "2 1 0 1 3 4 1 0 2 1 3 1 0 2 1 3"),
       ("sparse-dub",   "2 0 0 0 0 0 0 1 0 0 1 0 0 0 0 0"),
       ("tech-bounce",  "0 0 2 0 0 1 0 0 0 0 2 0 0 1 0 1"),
       ("acid-16ths",   "2 1 3 1 2 1 1 3 2 1 3 1 2 3 1 1"),
       ("trip-hop",     "2 0 0 0 0 0 3 1 0 0 0 0 0 0 1 0")]
    N=[("root","0"),("octaves","0 7"),("root-fifth","0 4"),("acid-riff","0 0 7 0 2 0 6 4"),
       ("walk-up","0 1 2 4"),("minor-stab","0 2 4 2"),("dub","0 0 -3 -2"),("pedal","0 0 0 1")]
    S=[("minor","0 2 3 5 7 8 10"),("major","0 2 4 5 7 9 11"),("dorian","0 2 3 5 7 9 10"),("phrygian","0 1 3 5 7 8 10"),
       ("mixolydian","0 2 4 5 7 9 10"),("harmonic-minor","0 2 3 5 7 8 11")]
    def tdef(x,y,name,rows): return add(f"#X obj {x} {y} text define -k {name};","#A set "+" \; ".join(f"{a} {b}" for a,b in rows)+" \;;")
    tdef(20,100,"ockm-bass-rhythms",RHY); tdef(250,100,"ockm-bass-notes",N); tdef(480,100,"ockm-bass-scales",S)
    add("#X text 20 125 double-click these to see or edit the presets;")
    # work arrays
    for i,(nm,n) in enumerate([("ockmrtmp",16),("ockmntmp",16),("ockmstmp",7)]):
        add(f"#X obj {700+i*130} 100 array define {nm} {n};")
    # hooks and stored settings
    hooks=[("ockm-bass-rhythm",3),("ockm-bass-notes",3),("ockm-bass-root",9),("ockm-bass-scale",0)]
    store=[]
    regen_in=add("#X obj 20 330 t b b b b b;")
    for j,(h,d) in enumerate(hooks):
        x=20+j*170
        r=add(f"#X obj {x} 170 r {h};"); t=add(f"#X obj {x} 200 t b f;"); f=add(f"#X obj {x} 290 f {d};")
        con(r,0,t,0); con(t,1,f,1); con(t,0,regen_in,0); store.append(f)
    rg=add("#X obj 720 170 r ockm-bass-gen;"); con(rg,0,regen_in,0)
    # regen order (right to left): 4 scale, 3 notes, 2 rhythm, 1 root, 0 loop
    # scale
    ts=add("#X obj 560 380 text get ockm-bass-scales;"); ls=add("#X obj 560 410 list split 1;"); as_=add("#X obj 560 440 array set ockmstmp;")
    con(regen_in,4,store[3],0); con(store[3],0,ts,0); con(ts,0,ls,0); con(ls,1,as_,0)
    # notes
    tn=add("#X obj 360 380 text get ockm-bass-notes;"); ln=add("#X obj 360 410 list split 1;"); tl=add("#X obj 360 440 t l l;")
    ll=add("#X obj 420 470 list length;"); an=add("#X obj 360 500 array set ockmntmp;")
    con(regen_in,3,store[1],0); con(store[1],0,tn,0); con(tn,0,ln,0); con(ln,1,tl,0); con(tl,1,ll,0); con(tl,0,an,0)
    # rhythm
    tr=add("#X obj 170 380 text get ockm-bass-rhythms;"); lr=add("#X obj 170 410 list split 1;"); ar=add("#X obj 170 440 array set ockmrtmp;")
    con(regen_in,2,store[0],0); con(store[0],0,tr,0); con(tr,0,lr,0); con(lr,1,ar,0)
    # root -> bass register midi note
    rx=add("#X obj 20 410 expr if(36+$f1>40 \\, 24+$f1 \\, 36+$f1);".replace("$","\\$"))
    con(regen_in,1,store[2],0); con(store[2],0,rx,0)
    # loop over 16 steps
    lp=add("#X obj 20 560 t b b;")
    con(regen_in,0,lp,0)
    z1=add("#X msg 120 590 0;"); n16=add("#X msg 20 590 16;"); un=add("#X obj 20 620 until;")
    fi=add("#X obj 20 650 f;"); pi=add("#X obj 70 650 + 1;"); fh=add("#X obj 400 760 f;"); ph=add("#X obj 450 760 + 1;")
    con(lp,1,z1,0); con(z1,0,fi,1); con(z1,0,fh,1); con(lp,0,n16,0); con(n16,0,un,0); con(un,0,fi,0); con(fi,0,pi,0); con(pi,0,fi,1)
    ti=add("#X obj 20 680 t f f;")
    con(fi,0,ti,0)
    tws={}
    for j,nm in enumerate(["note","on","acc","slide"]):
        tws[nm]=add(f"#X obj {200+j*170} 900 tabwrite ockm-pat-\\$1-{nm};")
        con(ti,1,tws[nm],1)
    rd=add("#X obj 20 710 tabread ockmrtmp;")
    cx=add("#X obj 20 740 expr \\$f1>0 \; \\$f1==2 || \\$f1==4 \; \\$f1>=3;")
    con(ti,0,rd,0); con(rd,0,cx,0)
    con(cx,2,tws["slide"],0); con(cx,1,tws["acc"],0)
    to=add("#X obj 20 780 t f f;"); con(cx,0,to,0); con(to,1,tws["on"],0)
    s1=add("#X obj 20 810 sel 1;"); con(to,0,s1,0)
    con(s1,0,fh,0)
    th=add("#X obj 400 790 t f f;"); con(fh,0,th,0); con(th,1,ph,0); con(ph,0,fh,1)
    dx=add("#X obj 400 820 expr ockmntmp[\\$f1 % \\$f2];"); con(th,0,dx,0); con(ll,0,dx,1)
    nx=add("#X obj 400 860 expr \\$f2 + 12*floor(\\$f1/7) + ockmstmp[((int(\\$f1)%7)+7)%7];"); con(dx,0,nx,0); con(rx,0,nx,1)
    con(nx,0,tws["note"],0)
    add("#X text 560 820 degree -> MIDI note in the chosen key and scale;")
    add("#X text 20 960 hooks: ockm-bass-rhythm 0-7 \\, ockm-bass-notes 0-7 \\, ockm-bass-root 0-11 (0 = C \\, 9 = A) \\, ockm-bass-scale 0-5 \\, ockm-bass-gen (rebuild);")
    out="#N canvas 120 120 1100 1000 12;\n"+"\n".join(L)+"\n"+"".join(f"#X connect {a} {b} {c} {d};\n" for a,b,c,d in C)
    # fixes applied after the first version (kept here so the output matches)
    out=out.replace("expr ockmntmp[\\$f1 % \\$f2];","expr ockmntmp[int(\\$f1) % int(\\$f2)];")
    out=out.replace("ockm-bass-rhythms","ockm-presets-rhythm").replace("text define -k ockm-bass-notes","text define -k ockm-presets-notes")
    out=out.replace("text get ockm-bass-notes","text get ockm-presets-notes").replace("ockm-bass-scales","ockm-presets-scale")
    open(os.path.join(R,"seq/ockm-bassgen.pd"),"w").write(out)

def build_patterns():
    def steps(on): return [1 if i in on else 0 for i in range(16)]
    # ---------------- patterns ----------------
    def st(on,acc=()):
        return [2 if i in acc else (1 if i in on else 0) for i in range(16)]
    E=[0]*16
    pats={"kick":[st({0,4,8,12}),st({0,4,8,12}),st({0,6,10}),st({0,7,10})],
          "snare":[E,E,st({4,12,15}),st({4,12})],
          "clap":[st({4,12}),st({4,12}),E,E],
          "rim":[E,st({5,13}),E,st({14})],
          "chat":[st({2,6,10,14},{6,14}),st({3,7,11,15},{7,15}),st(set(range(0,16,2)),{2,6,10,14}),st(set(range(0,16,2)),{4,12})],
          "ohat":[E,st({2,6,10,14}),st({14}),E],
          "tom":[E,E,st({11,13}),E],
          "perc":[E,st({3,11}),E,E]}
    os.makedirs(R+"/patterns",exist_ok=True)
    for nm,ps in pats.items():
        open(f"{R}/patterns/{nm}.txt","w").write("\n".join(str(v) for v in sum(ps,[])+E*4)+"\n")

    b1=dict(note=[33,45,33,33,36,43,45,45,33,33,45,40,40,43,36,38],on=[1,1,0,1,1,1,1,0,1,1,1,1,0,1,1,1],
            acc=[1,0,0,0,0,1,0,0,1,0,0,0,0,1,0,0],slide=[0,0,0,0,1,1,0,0,0,0,1,0,0,0,0,1])
    b2=dict(note=[33]*14+[36,33],on=steps({2,6,10,14}),acc=steps({6,14}),slide=E)
    b3=dict(note=[33,33,45,33,36,33,45,43,33,33,45,33,40,38,36,45],on=[1,1,1,0,1,1,1,1,1,1,1,0,1,1,1,1],acc=steps({0,4,8,12}),slide=steps({6,14}))
    b4=dict(note=[33,33,33,33,33,33,33,33,31,31,31,31,36,36,36,36],on=steps({0,3,8,11}),acc=steps({0}),slide=E)
    for k in ["note","on","acc","slide"]:
        allv=b1[k]+b2[k]+b3[k]+b4[k]+b1[k]*4
        open(f"{R}/patterns/bass-{k}.txt","w").write("\n".join(str(v) for v in allv)+"\n")


build_bassgen()
if args.reset_patterns:
    build_patterns()
print("built", R)
