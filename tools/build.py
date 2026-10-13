#!/usr/bin/env python3
"""OCKM_GENERATOR build script.

Writes the Pure Data files for the whole project. Structural changes (new objects,
new wiring, new voices) are made here, then the patch files are rebuilt.
Sound tweaks are made with the controls in the patch, not here.

Usage:
  python3 tools/build.py                 rebuild every .pd file in the project
  python3 tools/build.py --out DIR       write to another folder (used by the tests)
  python3 tools/build.py --reset-patterns  rewrite projects/default with the starter project
                                          (this DELETES any patterns and settings you have saved)

It only creates project files that are missing, and never touches sketches/, README or CHANGELOG.
"""
import os, sys, argparse
ap=argparse.ArgumentParser()
ap.add_argument("--out",default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument("--reset-patterns",action="store_true")
args=ap.parse_args()
R=args.out
for d in ("voices","seq"): os.makedirs(os.path.join(R,d),exist_ok=True)
STEPS=128   # longest pattern
SLOTN=8     # pattern slots
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

# ---------------- drum slot: any of the 8 drum sounds ----------------
SOUNDS=["ockm-kick","ockm-snare","ockm-clap","ockm-rim","ockm-hat","ockm-ohat","ockm-tom","ockm-perc"]
SOUND_NAMES=["kick","snare","clap","rim","closed hat","open hat","tom","rimshot"]
p=P()
p.add("#X text 20 10 Drum slot: plays one of the 8 drum sounds (ockm-<slot>-sound 0-7). Only the chosen sound runs.;")
inl=p.add("#X obj 30 50 inlet;")
summ=None
outs=[]
for k,v in enumerate(SOUNDS):
    sp=P()
    si=sp.add("#X obj 20 20 inlet;"); sg=sp.add("#X obj 20 50 spigot;"); vo=sp.add(f"#X obj 20 80 {v} {D}1;"); so=sp.add("#X obj 20 110 outlet~;")
    rs=sp.add(f"#X obj 200 20 r ockm-{D}1-sound;"); eq=sp.add(f"#X obj 200 50 == {k};"); tf=sp.add("#X obj 200 80 t f f;"); sw=sp.add("#X obj 200 110 switch~;")
    for c in [(si,0,sg,0),(sg,0,vo,0),(vo,0,so,0),(rs,0,eq,0),(eq,0,tf,0),(tf,1,sw,0),(tf,0,sg,1)]: sp.con(*c)
    p.L.append(sp.text(f"#N canvas 0 0 420 160 s{k} 0;").rstrip("\n"))
    o=p.add(f"#X restore {30+k*90} 100 pd s{k};")
    p.con(inl,0,o,0); outs.append(o)
    p.add(f"#X text {30+k*90} 125 {k} {SOUND_NAMES[k].split()[0]};")
prev=outs[0]
for o in outs[1:]:
    a=p.add("#X obj 30 200 +~;"); p.con(prev,0,a,0); p.con(o,0,a,1); prev=a
out=p.add("#X obj 30 260 outlet~;"); p.con(prev,0,out,0)
p.save("voices/ockm-drum.pd","#N canvas 180 180 800 300 12;")

# ---------------- drum row (up to 128 steps, shown 16 at a time) ----------------
p=P()
inl=p.add("#X obj 30 120 inlet;")
tr=p.add(f"#X obj 30 160 tabread ockm-pat-{D}1;")
sel=p.add("#X obj 30 190 sel 0;")
vel=p.add(f"#X obj 70 220 expr if({D}f1>1 \\, 1 \\, 1-{D}f2);")
out=p.add("#X obj 70 260 outlet;")
racc=p.add("#X obj 230 190 r ockm-accent;")
p.add(f"#X obj 30 300 table ockm-pat-\\$1 {STEPS};")
tw=p.add(f"#X obj 400 520 tabwrite ockm-pat-{D}1;")
upk=p.add("#X obj 400 460 unpack f f;"); offs=p.add("#X obj 480 490 + 0;")
for c in [(inl,0,tr,0),(tr,0,sel,0),(sel,1,vel,0),(racc,0,vel,1),(vel,0,out,0),(upk,1,offs,0),(offs,0,tw,1),(upk,0,tw,0)]: p.con(*c)
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
# extend: when a pattern gets longer, repeat what's there to fill the new steps
rx=p.add("#X obj 1400 120 r ockm-extend;"); ux=p.add("#X obj 1400 150 unpack f f;")
cnt=p.add(f"#X obj 1400 210 expr {D}f2-{D}f1;"); txo=p.add("#X obj 1400 180 t f f;")
mo=p.add("#X obj 1400 240 moses 1;"); ux2=p.add("#X obj 1460 270 until;")
ci=p.add("#X obj 1460 300 f;"); cip=p.add("#X obj 1510 300 + 1;"); tci=p.add("#X obj 1460 330 t f f;")
md=p.add(f"#X obj 1460 360 expr {D}f1 % {D}f2;"); xr=p.add(f"#X obj 1460 390 tabread ockm-pat-{D}1;"); xw=p.add(f"#X obj 1460 420 tabwrite ockm-pat-{D}1;")
for c in [(rx,0,ux,0),(ux,1,cnt,1),(ux,0,txo,0),(txo,1,ci,1),(txo,1,md,1),(txo,0,cnt,0),(cnt,0,mo,0),
          (ux2,0,ci,0),(ci,0,cip,0),(cip,0,ci,1),(ci,0,tci,0),(tci,1,xw,1),(tci,0,md,0),(md,0,xr,0),(xr,0,xw,0)]: p.con(*c)
tbf2=p.add("#X obj 1400 270 t b f;"); p.con(mo,1,tbf2,0); p.con(tbf2,1,ux2,0); p.con(tbf2,0,tr2,0)
p.add("#X text 100 120 step in -> look it up -> send hit strength out (accent = 1 \\, normal = 1 minus accent amount);")
p.add("#X text 900 90 refresh: update the squares after a pattern loads;")
p.add("#X text 1150 90 edit: ockm-edit <track> <step> <0 off \\, 1 on \\, 2 accent>;")
p.add("#X text 1400 90 extend: repeat steps to fill a longer pattern;")
p.save("seq/ockm-row.pd","#N canvas 200 200 1700 600 12;",["#X coords 0 -1 1 1 340 24 3 100 19;"])

# ---------------- bass sequencer ----------------
p=P()
p.add("#X text 20 10 Mono synth pattern (bass or lead). Each step has a note \\, on/off \\, accent and slide. Up to 128 steps.;")
inl=p.add("#X obj 30 60 inlet;"); t5=p.add("#X obj 30 100 t f f f f f;")
rn=p.add(f"#X obj 30 300 tabread ockm-pat-{D}1-note;"); ra=p.add(f"#X obj 140 260 tabread ockm-pat-{D}1-acc;"); rsl=p.add(f"#X obj 250 220 tabread ockm-pat-{D}1-slide;")
pz=p.add("#X obj 360 130 sel 0;"); lst=p.add("#X obj 360 160 f 16;"); m1a=p.add("#X obj 360 185 - 1;"); m1b=p.add("#X obj 420 160 - 1;"); rlen=p.add("#X obj 470 100 r ockm-len;")
t2=p.add("#X obj 360 210 t f f;")
ps=p.add(f"#X obj 360 260 tabread ockm-pat-{D}1-slide;"); po=p.add(f"#X obj 470 230 tabread ockm-pat-{D}1-on;"); mul=p.add("#X obj 360 300 *;")
pk=p.add("#X obj 30 360 pack f f f f;"); ro=p.add(f"#X obj 600 140 tabread ockm-pat-{D}1-on;"); sp=p.add("#X obj 30 400 spigot;")
eq=p.add("#X obj 600 180 == 0;"); s1=p.add("#X obj 600 210 sel 1;"); off=p.add("#X msg 600 240 off;"); out=p.add("#X obj 30 460 outlet;")
for j,nm in enumerate(["note","on","acc","slide"]): p.add(f"#X obj {30+j*160} 520 table ockm-pat-{D}1-{nm} {STEPS};")
for c in [(inl,0,t5,0),(t5,4,ro,0),(t5,3,rsl,0),(t5,2,pz,0),(t5,1,ra,0),(t5,0,rn,0),(rn,0,pk,0),(ra,0,pk,1),(rsl,0,pk,3),
    (pz,0,lst,0),(lst,0,m1a,0),(m1a,0,t2,0),(pz,1,m1b,0),(m1b,0,t2,0),(rlen,0,lst,1),
    (t2,1,po,0),(t2,0,ps,0),(po,0,mul,1),(ps,0,mul,0),(mul,0,pk,2),(pk,0,sp,0),(ro,0,sp,1),(ro,0,eq,0),(eq,0,s1,0),(s1,0,off,0),(off,0,out,0),(sp,0,out,0)]: p.con(*c)
re=p.add(f"#X obj 720 560 r ockm-{D}1-edit;"); tl=p.add("#X obj 720 590 t l l;"); ls=p.add("#X obj 900 620 list split 1;")
up=p.add("#X obj 720 650 unpack f f f f f;")
p.con(re,0,tl,0); p.con(tl,1,ls,0); p.con(tl,0,up,0)
# extend
rx=p.add("#X obj 1500 120 r ockm-extend;"); ux=p.add("#X obj 1500 150 unpack f f;")
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
VERB=[0,0.25,0.35,0.2,0.1,0.15,0.2,0.25]   # default reverb send per sound
DLY=[0,0,0,0.25,0,0,0,0.3]                 # default delay send per sound
MONO=["note","on","acc","slide"]; CHORD=["on","deg"]
def show(h): return "ockm-show-"+h[5:]
# Settings registry: (hook, default, hook the store listens to if different)
PROJECT_KEYS=[("ockm-bpm",124,"ockm-tempo"),("ockm-accent",0.3,None),("ockm-filter",0,None),("ockm-drive",0,None),
    ("ockm-delay-mix",0.5,None),("ockm-delay-fb",0.4,None),("ockm-delay-steps",3,None),("ockm-verb-mix",0.5,None),
    ("ockm-verb-size",0.6,None),("ockm-verb-tone",0.5,None),("ockm-sync",0,None),("ockm-clock-out",1,None)]
for nm,snd in SLOTS:
    PROJECT_KEYS+=[(f"ockm-{nm}-sound",snd,None),(f"ockm-{nm}-tune",0,None),(f"ockm-{nm}-decay",100,None),
                   (f"ockm-{nm}-level",1,None),(f"ockm-{nm}-verb",VERB[snd],None),(f"ockm-{nm}-delay",DLY[snd],None)]
SYNTH_DEFAULTS={"bass":dict(engine=0,k1=0.37,k2=0.9,k3=0.31,k4=0.55,drive=0,verb=0,delay=0,rhythm=3,notes=3),
                "lead":dict(engine=4,k1=0.55,k2=0.3,k3=0.4,k4=0.45,drive=0,verb=0.2,delay=0.25,rhythm=6,notes=8),
                "chord":dict(engine=0,k1=0.45,k2=0.5,k3=0.4,k4=0.3,type=0,verb=0.3,delay=0.35,rhythm=0,prog=0)}
PATTERN_KEYS=[("ockm-len",16,None),("ockm-swing",56,"ockm-swing-now"),("ockm-root",9,None),("ockm-scale",0,None)]
for t,d in SYNTH_DEFAULTS.items():
    PATTERN_KEYS+=[(f"ockm-{t}-{k}",v,None) for k,v in d.items()]
TABLES=[f"ockm-pat-{n}" for n,_ in SLOTS]+[f"ockm-pat-{t}-{f}" for t in ("bass","lead") for f in MONO]+[f"ockm-pat-chord-{f}" for f in CHORD]
PROJ_DIR="projects/default"
p=P()
p.raw("#X declare -path voices -path seq;")
p.add("#X text 30 10 OCKM_GENERATOR v0.11. Click start \\, then click squares to build a beat. Pick a pattern slot \\, press save to keep it.;")
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
for c in [(rw,0,tbf,0),(tbf,1,pend,1),(tbf,0,tbb,0),(tbb,1,one,0),(one,0,flag,1),(tbb,0,spg,0),(spg,0,tbb2,0),(tbb2,1,zero,0),(zero,0,flag,1),(tbb2,0,pend,0),
    (ttg,2,eqz,0),(eqz,0,spg,1),(tff,1,bm,0),(bm,0,s0,0),(s0,0,flag,0),(flag,0,s1,0),(s1,0,tbb3,0),
    (tbb3,3,zero2,0),(zero2,0,flag,1),(tbb3,2,zmul,0),(zmul,0,mz,1),(tbb3,1,onef,0),(onef,0,f,1),(tbb3,0,pend,0),
    (pend,0,tcur,0),(tcur,1,cur,1),(tcur,0,sld,0),(sv,0,tsv,0),(tsv,1,cur,0),(cur,0,sstore,0)]: p.con(*c)
# pattern length (1-128) and editing page
p.add("#X text 880 50 length;")
lenb=p.add("#X floatatom 880 75 4 1 128 0 - - ockm-length;"); lset=p.add(f"#X msg 880 105 set {D}1;"); rl2=p.add("#X obj 940 105 r ockm-len;")
p.con(rl2,0,lset,0); p.con(lset,0,lenb,0)
p.add("#X text 960 50 page;")
pg=p.add("#X floatatom 960 75 3 0 7 0 - - ockm-page;")
p.add("#X text 1000 75 (squares show steps page x 16 + 1 to 16);")
rlg=p.add("#X obj 880 140 r ockm-length;"); clp=p.add("#X obj 880 165 clip 1 128;"); tl4=p.add("#X obj 880 190 t f f f;")
gt=p.add(f"#X obj 980 215 expr {D}f1>{D}f2;"); sg1=p.add("#X obj 980 240 sel 1;"); curl=p.add("#X obj 980 265 f 16;"); pkx=p.add("#X obj 980 290 pack f f;")
sx=p.add("#X obj 980 315 s ockm-extend;"); slen=p.add("#X obj 880 315 s ockm-len;"); rl3=p.add("#X obj 1060 240 r ockm-len;")
for c in [(rlg,0,clp,0),(clp,0,tl4,0),(tl4,2,pkx,1),(tl4,1,gt,0),(gt,0,sg1,0),(sg1,0,curl,0),(curl,0,pkx,0),(pkx,0,sx,0),(tl4,0,slen,0),(rl3,0,curl,1),(rl3,0,gt,1)]: p.con(*c)
rvb=p.add("#X obj 810 50 bng 25 250 50 0 empty empty empty 17 7 0 10 #fcfcfc #000000 #000000;"); p.add("#X text 842 52 revert;")
p.con(rvb,0,p.add("#X obj 810 85 s ockm-revert;"),0)
p.add("#X obj 1100 420 ockm-store;")
p.add(f"#X text 1100 395 settings and patterns: {PROJ_DIR} (project.txt and p1 to p8);")
# drums
mix=p.add("#X obj 560 1000 *~ 0.3;"); fx=p.add("#X obj 560 1030 ockm-fx;"); dac=p.add("#X obj 560 1065 dac~;"); smaster=p.add("#X obj 640 1065 s~ ockm-master;")
p.con(mix,0,fx,0); p.con(fx,0,dac,0); p.con(fx,0,dac,1); p.con(fx,0,smaster,0)
for r,(nm,snd) in enumerate(SLOTS):
    y=380+r*40
    p.add(f"#X text 20 {y+2} {nm} {SOUND_NAMES[snd].replace(' ','-')};")
    row=p.add(f"#X obj 110 {y} ockm-row {nm};"); v=p.add(f"#X obj 560 {y+2} ockm-drum {nm};")
    p.con(pipe,0,row,0); p.con(row,0,v,0); p.con(v,0,mix,0)
    vs=p.add(f"#X obj 760 {y+2} *~ 0;"); vt=p.add(f"#X obj 830 {y+2} throw~ ockm-revbus;"); vr=p.add(f"#X obj 760 {y-18} r ockm-{nm}-verb;")
    p.con(v,0,vs,0); p.con(vs,0,vt,0); p.con(vr,0,vs,1)
    ds=p.add(f"#X obj 990 {y+2} *~ 0;"); dt_=p.add(f"#X obj 1060 {y+2} throw~ ockm-dlybus;"); dr_=p.add(f"#X obj 990 {y-18} r ockm-{nm}-delay;")
    p.con(v,0,ds,0); p.con(ds,0,dt_,0); p.con(dr_,0,ds,1)
# drum settings subpatch
sub=P()
sub.add("#X text 20 10 Drum slots. Sound 0 kick 1 snare 2 clap 3 rim 4 closed hat 5 open hat 6 tom 7 rimshot. Tune in semitones \\, decay in % (100 = normal) \\, level 0 to 1.;")
slb=sub.add("#X obj 20 40 loadbang;")
for i,(nm,snd) in enumerate(SLOTS):
    y=80+i*30
    sub.add(f"#X text 20 {y} {nm};")
    for j,(param,dflt,lo,hi) in enumerate([("sound",snd,0,7),("tune",0,-12,12),("decay",100,10,400),("level",1,0,1),("verb",VERB[snd],0,1),("delay",DLY[snd],0,1)]):
        m=sub.add(f"#X obj {70+j*140} {y-18} r {show(f'ockm-{nm}-{param}')};")
        fa=sub.add(f"#X floatatom {115+j*140} {y} 5 {lo} {hi} 0 - - ockm-{nm}-{param};")
        sub.con(m,0,fa,0)
sub.add("#X text 70 60 sound          tune           decay          level          reverb send    delay send;")
p.L.append(sub.text("#N canvas 300 200 940 360 drum-settings 0;").rstrip("\n"))
ds=p.add("#X restore 30 960 pd drum-settings;")
p.add("#X text 30 985 sound \\, tune \\, decay \\, level and sends per drum slot;")
# synth tracks: bass and lead (mono synth), chord
by=380+len(SLOTS)*40+10
SYN=[("bass","ockm-monoseq bass","ockm-mono bass"),("lead","ockm-monoseq lead","ockm-mono lead"),("chord","ockm-chordseq chord","ockm-chord chord")]
synth_voice={}
for r,(nm,seqo,voi) in enumerate(SYN):
    y=by+r*40
    p.add(f"#X text 20 {y+2} {nm};")
    sq=p.add(f"#X obj 110 {y} {seqo};"); vo=p.add(f"#X obj 560 {y} {voi};")
    p.con(pipe,0,sq,0); p.con(sq,0,vo,0); p.con(vo,0,mix,0)
    vs=p.add(f"#X obj 760 {y} *~ 0;"); vt=p.add(f"#X obj 830 {y} throw~ ockm-revbus;"); vr=p.add(f"#X obj 760 {y-18} r ockm-{nm}-verb;")
    p.con(vo,0,vs,0); p.con(vs,0,vt,0); p.con(vr,0,vs,1)
    ds=p.add(f"#X obj 990 {y} *~ 0;"); dt_=p.add(f"#X obj 1060 {y} throw~ ockm-dlybus;"); dr_=p.add(f"#X obj 990 {y-18} r ockm-{nm}-delay;")
    p.con(vo,0,ds,0); p.con(ds,0,dt_,0); p.con(dr_,0,ds,1)
    synth_voice[nm]=vo
s0b=p.add("#X obj 400 80 sel 0;"); offm=p.add("#X msg 400 105 off;")
p.con(ttg,1,s0b,0); p.con(s0b,0,offm,0)
for nm in ("bass","lead","chord"): p.con(offm,0,synth_voice[nm],0)
# generators and shared presets
gy=by+3*40+20
p.add(f"#X obj 110 {gy} ockm-presets;")
p.add(f"#X obj 230 {gy} ockm-monogen bass 0 3 3;")
p.add(f"#X obj 400 {gy} ockm-monogen lead 24 6 8;")
p.add(f"#X obj 530 {gy} ockm-chordgen chord;")
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
row(140,"bass",[("engine",0,0,5,"ockm-bass-engine",True),("k1",0.37,0,1,"ockm-bass-k1",True),("k2",0.9,0,1,"ockm-bass-k2",True),("k3",0.31,0,1,"ockm-bass-k3",True),
                ("k4",0.55,0,1,"ockm-bass-k4",True),("drive",0,0,1,"ockm-bass-drive",True),("rhythm",3,0,7,"ockm-bass-rhythm",False),("notes",3,0,11,"ockm-bass-notes",False)])
row(200,"lead",[("engine",4,0,5,"ockm-lead-engine",True),("k1",0.55,0,1,"ockm-lead-k1",True),("k2",0.3,0,1,"ockm-lead-k2",True),("k3",0.4,0,1,"ockm-lead-k3",True),
                ("k4",0.45,0,1,"ockm-lead-k4",True),("drive",0,0,1,"ockm-lead-drive",True),("rhythm",6,0,7,"ockm-lead-rhythm",False),("notes",8,0,11,"ockm-lead-notes",False)])
row(260,"chord",[("engine",0,0,2,"ockm-chord-engine",True),("k1",0.45,0,1,"ockm-chord-k1",True),("k2",0.5,0,1,"ockm-chord-k2",True),("k3",0.4,0,1,"ockm-chord-k3",True),
                 ("k4",0.3,0,1,"ockm-chord-k4",True),("type",0,0,3,"ockm-chord-type",True),("rhythm",0,0,7,"ockm-chord-rhythm",False),("prog",0,0,7,"ockm-chord-prog",False)])
sub.add("#X text 20 300 key root: 0 C ... 9 A ... 11 B. Scale: 0 minor 1 major 2 dorian 3 phrygian 4 mixolydian 5 harmonic minor;")
sub.add("#X text 20 320 bass and lead engines: 0 acid 1 sub 2 FM 3 reese 4 pluck 5 saw. Chord engines: 0 stab 1 organ 2 pad. Chord type: 0 triad 1 seventh 2 sus2 3 power;")
sub.add("#X text 20 340 bass/lead rhythm: 0 offbeat 1 rolling 2 gallop 3 acid 4 dub 5 bounce 6 acid16 7 trip-hop. Notes: 0 root 1 octaves 2 root-fifth 3 acid-riff 4 walk-up 5 stab 6 dub 7 pedal 8 arp-up 9 arp-updown 10 call 11 descend;")
sub.add("#X text 20 360 chord rhythm: 0 offbeat-stabs 1 dub-stabs 2 bar-pads 3 house-organ 4 two-beat 5 syncopated 6 eighths 7 sparse. Prog: 0 i 1 i-VI-VII 2 i-iv 3 i-VII-VI-VII 4 i-v 5 i-III-VII-iv 6 i-VI-iv-v 7 ii-V-i-i;")
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
p.add("#X text 250 985 effects and sends;")
p.add("#X obj 1100 800 declare -path voices -path seq;")
p.save("OCKM_GENERATOR.pd","#N canvas 40 40 1420 1050 12;")


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
q.save("voices/ockm-mono-core.pd","#N canvas 150 150 900 520 12;")

# ================= engines =================
def engine(fn,idx,title,build):
    q=P(); q.add(f"#X text 20 10 {title};")
    inl=q.add("#X obj 30 50 inlet;")
    sp=q.add("#X obj 30 80 spigot 1;")
    core=q.add("#X obj 30 120 ockm-mono-core;")
    ks=[q.add(f"#X obj {200+i*110} 50 inlet;") for i in range(4)]
    re=q.add(f"#X obj 700 50 r ockm-{D}1-engine;"); eq=q.add(f"#X obj 700 80 == {idx};"); tf=q.add("#X obj 700 110 t f f;")
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

engine("voices/ockm-mono-acid.pd",0,"Acid engine: saw wave into a resonant filter",acid)
engine("voices/ockm-mono-sub.pd",1,"Sub engine: a driven sine wave with a pitch drop. Deep and clean",sub)
engine("voices/ockm-mono-fm.pd",2,"FM engine: one sine wave bending another. Punchy and metallic",fm)
engine("voices/ockm-mono-reese.pd",3,"Reese engine: three detuned saws beating against each other. Dark and wide",reese)
engine("voices/ockm-mono-pluck.pd",4,"Pluck engine: short and bright. Good for rolling riffs",pluck)

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

engine("voices/ockm-mono-saw.pd",5,"Saw engine: a raw sawtooth. No squelch \\, just a hard buzzy bass",sawe)

# ================= bass wrapper =================
q=P()
q.add("#X text 20 10 Mono synth (bass or lead): six engines \\, one plays at a time (ockm-<track>-engine 0 to 5). Knobs k1-k4 and drive come in on hooks.;")
inl=q.add("#X obj 30 50 inlet;")
ks=[q.add(f"#X obj {200+i*130} 50 r ockm-{D}1-k{i+1};") for i in range(4)]
names=["acid","sub","fm","reese","pluck","saw"]
eng=[q.add(f"#X obj {30+i*130} 130 ockm-mono-{n} {D}1;") for i,n in enumerate(names)]
sm=q.add("#X obj 30 200 +~;")
for i,e in enumerate(eng):
    q.con(inl,0,e,0)
    for j,k in enumerate(ks): q.con(k,0,e,j+1)
    q.con(e,0,sm,0)
rd=q.add(f"#X obj 400 200 r ockm-{D}1-drive;"); dx=q.add(f"#X obj 400 230 expr 1+{D}f1*9;")
th=q.add(f"#X obj 30 260 expr~ tanh({D}v1*max({D}f2\\,1))/sqrt(max({D}f2\\,1));"); out=q.add("#X obj 30 300 outlet~;")
q.add("#X text 400 260 drive: 0 clean \\, 1 heavy;")
for c in [(rd,0,dx,0),(dx,0,th,1),(sm,0,th,0),(th,0,out,0)]: q.con(*c)
q.save("voices/ockm-mono.pd","#N canvas 140 140 900 340 12;")

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

# ================= shared presets =================
PRE={"rhythm":[("offbeat","0 0 2 0 0 0 1 0 0 0 2 0 0 0 1 0"),("rolling","0 2 1 1 0 2 1 1 0 2 1 1 0 2 1 1"),("gallop","0 0 2 1 0 1 2 0 0 0 2 1 0 1 2 0"),
               ("acid-classic","2 1 0 1 3 4 1 0 2 1 3 1 0 2 1 3"),("sparse-dub","2 0 0 0 0 0 0 1 0 0 1 0 0 0 0 0"),("tech-bounce","0 0 2 0 0 1 0 0 0 0 2 0 0 1 0 1"),
               ("acid-16ths","2 1 3 1 2 1 1 3 2 1 3 1 2 3 1 1"),("trip-hop","2 0 0 0 0 0 3 1 0 0 0 0 0 0 1 0")],
     "notes":[("root","0"),("octaves","0 7"),("root-fifth","0 4"),("acid-riff","0 0 7 0 2 0 6 4"),("walk-up","0 1 2 4"),("minor-stab","0 2 4 2"),
              ("dub","0 0 -3 -2"),("pedal","0 0 0 1"),("arp-up","0 2 4 7"),("arp-updown","0 2 4 7 4 2"),("call","4 4 2 0 2 4 5 4"),("descend","7 6 4 2")],
     "scale":[("minor","0 2 3 5 7 8 10"),("major","0 2 4 5 7 9 11"),("dorian","0 2 3 5 7 9 10"),("phrygian","0 1 3 5 7 8 10"),
              ("mixolydian","0 2 4 5 7 9 10"),("harmonic-minor","0 2 3 5 7 8 11")],
     "chordrhythm":[("offbeat-stabs","0 0 1 0 0 0 1 0 0 0 1 0 0 0 1 0"),("dub-stabs","0 0 0 2 0 0 0 0 0 0 1 0 0 0 0 0"),("bar-pads","2 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0"),
                    ("house-organ","1 0 0 1 0 0 1 0 0 0 1 0 0 1 0 0"),("two-beat","2 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0"),("syncopated","0 0 1 0 0 1 0 0 0 1 0 0 1 0 0 0"),
                    ("eighths","1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0"),("sparse","0 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0")],
     "prog":[("i","0"),("i-VI-VII","0 0 5 6"),("i-iv","0 3"),("i-VII-VI-VII","0 6 5 6"),("i-v","0 4"),("i-III-VII-iv","0 2 6 3"),("i-VI-iv-v","0 5 3 4"),("ii-V-i-i","1 4 0 0")],
     "chordtype":[("triad","0 2 4 -1"),("seventh","0 2 4 6"),("sus2","0 1 4 -1"),("power","0 4 7 -1")]}
p=P()
p.add("#X text 20 10 Shared presets for the generators and chords. Rhythm codes: 0 rest 1 note 2 accent 3 note+slide 4 accent+slide. Notes and progressions are scale steps (0 root \\, 2 third \\, 4 fifth \\, 7 octave).;")
for i,(k,rows) in enumerate(PRE.items()):
    p.add(f"#X obj {20+(i%3)*260} {60+(i//3)*40} text define -k ockm-presets-{k};")
    p.L.append("#A set "+" \; ".join(f"{a} {b}" for a,b in rows)+" \;;")
p.add("#X text 20 150 Change presets in tools/build.py (PRE) so they survive rebuilds.;")
p.save("seq/ockm-presets.pd","#N canvas 200 200 820 200 12;")

# ================= mono generator (bass or lead) =================
# args: track, octave offset (semitones), default rhythm, default notes
p=P()
p.add("#X text 20 10 Mono generator: builds a bass or lead line from a rhythm preset + a note pattern + the shared key. Args: track \\, octave offset \\, default rhythm \\, default notes.;")
for nm,n in [("r",16),("n",16),("s",7)]: p.add(f"#X obj {700+['r','n','s'].index(nm)*130} 60 array define {D}0-{nm} {n};")
regen=p.add("#X obj 20 330 t b b b b b;")
gate=p.add("#X obj 20 305 spigot 1;"); rld=p.add("#X obj 120 280 r ockm-loading;"); nl0=p.add("#X obj 120 300 == 0;")
p.con(gate,0,regen,0); p.con(rld,0,nl0,0); p.con(nl0,0,gate,1)
store=[]
for j,(hook,dflt) in enumerate([(f"ockm-{D}1-rhythm",f"{D}3"),(f"ockm-{D}1-notes",f"{D}4"),("ockm-root","9"),("ockm-scale","0")]):
    x=20+j*170
    r=p.add(f"#X obj {x} 170 r {hook};"); t=p.add(f"#X obj {x} 200 t b f;"); fs=p.add(f"#X obj {x} 290 f {dflt};")
    p.con(r,0,t,0); p.con(t,1,fs,1); p.con(t,0,gate,0); store.append(fs)
rg=p.add(f"#X obj 720 170 r ockm-{D}1-gen;"); p.con(rg,0,regen,0)
ts=p.add("#X obj 560 380 text get ockm-presets-scale;"); lsp=p.add("#X obj 560 410 list split 1;"); asx=p.add(f"#X obj 560 440 array set {D}0-s;")
p.con(regen,4,store[3],0); p.con(store[3],0,ts,0); p.con(ts,0,lsp,0); p.con(lsp,1,asx,0)
tn=p.add("#X obj 360 380 text get ockm-presets-notes;"); ln=p.add("#X obj 360 410 list split 1;"); tl=p.add("#X obj 360 440 t l l;")
ll=p.add("#X obj 420 470 list length;"); an=p.add(f"#X obj 360 500 array set {D}0-n;")
p.con(regen,3,store[1],0); p.con(store[1],0,tn,0); p.con(tn,0,ln,0); p.con(ln,1,tl,0); p.con(tl,1,ll,0); p.con(tl,0,an,0)
tr=p.add("#X obj 170 380 text get ockm-presets-rhythm;"); lr=p.add("#X obj 170 410 list split 1;"); ar=p.add(f"#X obj 170 440 array set {D}0-r;")
p.con(regen,2,store[0],0); p.con(store[0],0,tr,0); p.con(tr,0,lr,0); p.con(lr,1,ar,0)
rx=p.add(f"#X obj 20 410 expr if(36+{D}f1>40 \\, 24+{D}f1 \\, 36+{D}f1);"); ro=p.add(f"#X obj 20 440 + {D}2;")
p.con(regen,1,store[2],0); p.con(store[2],0,rx,0); p.con(rx,0,ro,0)
lp=p.add("#X obj 20 560 t b b;"); p.con(regen,0,lp,0)
z1=p.add("#X msg 120 590 0;"); nl=p.add("#X obj 20 590 f 16;"); rlg=p.add("#X obj 80 560 r ockm-len;"); un=p.add("#X obj 20 620 until;")
fi=p.add("#X obj 20 650 f;"); pi=p.add("#X obj 70 650 + 1;"); fh=p.add("#X obj 400 760 f;"); ph=p.add("#X obj 450 760 + 1;")
for c in [(rlg,0,nl,1),(lp,1,z1,0),(z1,0,fi,1),(z1,0,fh,1),(lp,0,nl,0),(nl,0,un,0),(un,0,fi,0),(fi,0,pi,0),(pi,0,fi,1)]: p.con(*c)
ti=p.add("#X obj 20 680 t f f;"); p.con(fi,0,ti,0)
tws={}
for j,nm in enumerate(["note","on","acc","slide"]):
    tws[nm]=p.add(f"#X obj {200+j*170} 900 tabwrite ockm-pat-{D}1-{nm};"); p.con(ti,1,tws[nm],1)
m16=p.add("#X obj 20 700 mod 16;"); rd=p.add(f"#X obj 20 720 tabread {D}0-r;")
cx=p.add(f"#X obj 20 745 expr {D}f1>0 \; {D}f1==2 || {D}f1==4 \; {D}f1>=3;")
for c in [(ti,0,m16,0),(m16,0,rd,0),(rd,0,cx,0),(cx,2,tws["slide"],0),(cx,1,tws["acc"],0)]: p.con(*c)
to=p.add("#X obj 20 780 t f f;"); s1=p.add("#X obj 20 810 sel 1;"); th=p.add("#X obj 400 790 t f f;")
ix=p.add(f"#X obj 400 820 expr int({D}f1) % int({D}f2);"); rn=p.add(f"#X obj 400 845 tabread {D}0-n;"); td=p.add("#X obj 400 870 t f f;")
sx=p.add(f"#X obj 560 870 expr ((int({D}f1)%7)+7)%7;"); rs=p.add(f"#X obj 560 895 tabread {D}0-s;")
nx=p.add(f"#X obj 400 930 expr {D}f2 + 12*floor({D}f1/7) + {D}f3;")
for c in [(cx,0,to,0),(to,1,tws["on"],0),(to,0,s1,0),(s1,0,fh,0),(fh,0,th,0),(th,1,ph,0),(ph,0,fh,1),(th,0,ix,0),(ll,0,ix,1),(ix,0,rn,0),(rn,0,td,0),
          (td,1,sx,0),(sx,0,rs,0),(rs,0,nx,2),(td,0,nx,0),(ro,0,nx,1),(nx,0,tws["note"],0)]: p.con(*c)
p.add("#X text 20 980 hooks: ockm-<track>-rhythm 0-7 \\, ockm-<track>-notes 0-11 \\, ockm-<track>-gen (rebuild) \\, and the shared ockm-root 0-11 and ockm-scale 0-5;")
p.save("seq/ockm-monogen.pd","#N canvas 120 120 1100 1020 12;")

# ================= chord sequencer =================
p=P()
p.add("#X text 20 10 Chord pattern. Each step has on/accent and a chord root (scale step). Notes are worked out as it plays \\, so key \\, scale and chord type changes apply straight away.;")
inl=p.add("#X obj 30 50 inlet;"); out=p.add("#X obj 30 700 outlet;")
p.add(f"#X obj 30 760 table ockm-pat-{D}1-on {STEPS};"); p.add(f"#X obj 230 760 table ockm-pat-{D}1-deg {STEPS};")
p.add(f"#X obj 430 760 array define {D}0-sc 7;"); p.add(f"#X obj 600 760 array define {D}0-ty 4;")
lb=p.add("#X obj 700 40 loadbang;"); lbt=p.add("#X obj 700 65 t b b b;")
d0a=p.add("#X msg 700 90 0;"); d0b=p.add("#X msg 760 90 0;"); d9=p.add("#X msg 820 90 9;")
rsc=p.add("#X obj 700 120 r ockm-scale;"); tsc=p.add("#X obj 700 150 text get ockm-presets-scale;"); lsc=p.add("#X obj 700 175 list split 1;"); asc=p.add(f"#X obj 700 200 array set {D}0-sc;")
rty=p.add(f"#X obj 900 120 r ockm-{D}1-type;"); tty=p.add("#X obj 900 150 text get ockm-presets-chordtype;"); lty=p.add("#X obj 900 175 list split 1;"); aty=p.add(f"#X obj 900 200 array set {D}0-ty;")
rro=p.add("#X obj 1100 120 r ockm-root;"); rox=p.add(f"#X obj 1100 150 expr if({D}f1<=7 \\, 48+{D}f1 \\, 36+{D}f1);")
for c in [(lb,0,lbt,0),(lbt,2,d0a,0),(lbt,1,d0b,0),(lbt,0,d9,0),(d0a,0,tsc,0),(d0b,0,tty,0),(d9,0,rox,0),
          (rsc,0,tsc,0),(tsc,0,lsc,0),(lsc,1,asc,0),(rty,0,tty,0),(tty,0,lty,0),(lty,1,aty,0),(rro,0,rox,0)]: p.con(*c)
ts=p.add("#X obj 30 80 t f f;"); rdeg=p.add(f"#X obj 200 110 tabread ockm-pat-{D}1-deg;"); ron=p.add(f"#X obj 30 110 tabread ockm-pat-{D}1-on;")
son=p.add("#X obj 30 140 sel 0;"); vx=p.add(f"#X obj 70 170 expr if({D}f1>1 \\, 1 \\, 0.75);"); tv=p.add("#X obj 70 200 t b f;")
t4=p.add("#X obj 70 230 t b b b b;")
pk=p.add("#X obj 30 640 pack 0 0 0 0 0;"); sno=p.add(f"#X obj 200 700 s ockm-{D}1-notes-out;")
for c in [(inl,0,ts,0),(ts,1,rdeg,0),(ts,0,ron,0),(ron,0,son,0),(son,1,vx,0),(vx,0,tv,0),(tv,1,pk,4),(tv,0,t4,0),(pk,0,out,0),(pk,0,sno,0)]: p.con(*c)
for k in range(4):
    x=70+k*260
    mk=p.add(f"#X msg {x} 270 {k};"); rt=p.add(f"#X obj {x} 300 tabread {D}0-ty;"); tt=p.add(f"#X obj {x} 330 t f f;")
    ad=p.add(f"#X obj {x} 360 + 0;"); td=p.add(f"#X obj {x} 390 t f f;")
    sx=p.add(f"#X obj {x+90} 420 expr ((int({D}f1)%7)+7)%7;"); rs=p.add(f"#X obj {x+90} 450 tabread {D}0-sc;")
    nx=p.add(f"#X obj {x} 500 expr if({D}f4<0 \\, 0 \\, {D}f2+12*floor({D}f1/7)+{D}f3);")
    for c in [(t4,k,mk,0),(mk,0,rt,0),(rt,0,tt,0),(tt,1,nx,3),(tt,0,ad,0),(ad,0,td,0),(td,1,sx,0),(sx,0,rs,0),(rs,0,nx,2),(td,0,nx,0),(rox,0,nx,1),(rdeg,0,ad,1),(nx,0,pk,k)]: p.con(*c)
# store / load / edit / extend
re=p.add(f"#X obj 1300 600 r ockm-{D}1-edit;"); tl=p.add("#X obj 1300 630 t l l;"); ls=p.add("#X obj 1480 660 list split 1;"); up=p.add("#X obj 1300 690 unpack f f f;")
p.con(re,0,tl,0); p.con(tl,1,ls,0); p.con(tl,0,up,0)
rx=p.add("#X obj 1700 300 r ockm-extend;"); ux=p.add("#X obj 1700 330 unpack f f;")
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
p.add("#X text 20 10 Chord generator: a chord rhythm preset plus a progression (one chord per bar). Writes on/accent and chord roots across the whole pattern length.;")
p.add(f"#X obj 600 60 array define {D}0-r 16;"); p.add(f"#X obj 760 60 array define {D}0-p 8;")
regen=p.add("#X obj 20 250 t b b b;")
gate=p.add("#X obj 20 225 spigot 1;"); rld=p.add("#X obj 120 200 r ockm-loading;"); nl0=p.add("#X obj 120 220 == 0;")
p.con(gate,0,regen,0); p.con(rld,0,nl0,0); p.con(nl0,0,gate,1)
store=[]
for j,(hook,d) in enumerate([(f"ockm-{D}1-rhythm",0),(f"ockm-{D}1-prog",0)]):
    x=20+j*200
    r=p.add(f"#X obj {x} 100 r {hook};"); t=p.add(f"#X obj {x} 130 t b f;"); fs=p.add(f"#X obj {x} 210 f {d};")
    p.con(r,0,t,0); p.con(t,1,fs,1); p.con(t,0,gate,0); store.append(fs)
rg=p.add(f"#X obj 450 100 r ockm-{D}1-gen;"); p.con(rg,0,regen,0)
tp=p.add("#X obj 300 300 text get ockm-presets-prog;"); lpp=p.add("#X obj 300 330 list split 1;"); tlp=p.add("#X obj 300 360 t l l;")
llp=p.add("#X obj 360 390 list length;"); ap=p.add(f"#X obj 300 420 array set {D}0-p;")
p.con(regen,2,store[1],0); p.con(store[1],0,tp,0); p.con(tp,0,lpp,0); p.con(lpp,1,tlp,0); p.con(tlp,1,llp,0); p.con(tlp,0,ap,0)
tr=p.add("#X obj 100 300 text get ockm-presets-chordrhythm;"); lr=p.add("#X obj 100 330 list split 1;"); ar=p.add(f"#X obj 100 360 array set {D}0-r;")
p.con(regen,1,store[0],0); p.con(store[0],0,tr,0); p.con(tr,0,lr,0); p.con(lr,1,ar,0)
z1=p.add("#X msg 120 470 0;"); nl=p.add("#X obj 20 470 f 16;"); rlg=p.add("#X obj 80 440 r ockm-len;"); un=p.add("#X obj 20 500 until;")
fi=p.add("#X obj 20 530 f;"); pi=p.add("#X obj 70 530 + 1;"); ti=p.add("#X obj 20 560 t f f;"); tl2=p.add("#X obj 20 590 t f f;")
for c in [(regen,0,z1,0),(regen,0,nl,0),(rlg,0,nl,1),(z1,0,fi,1),(nl,0,un,0),(un,0,fi,0),(fi,0,pi,0),(pi,0,fi,1),(fi,0,ti,0),(ti,0,tl2,0)]: p.con(*c)
two=p.add(f"#X obj 200 700 tabwrite ockm-pat-{D}1-on;"); twd=p.add(f"#X obj 400 700 tabwrite ockm-pat-{D}1-deg;")
bx=p.add(f"#X obj 300 620 expr int({D}f1/16) % int(max({D}f2\\,1));"); rp=p.add(f"#X obj 300 650 tabread {D}0-p;")
m16=p.add("#X obj 20 620 mod 16;"); rr=p.add(f"#X obj 20 650 tabread {D}0-r;")
for c in [(ti,1,two,1),(ti,1,twd,1),(tl2,1,bx,0),(llp,0,bx,1),(bx,0,rp,0),(rp,0,twd,0),(tl2,0,m16,0),(m16,0,rr,0),(rr,0,two,0)]: p.con(*c)
p.add("#X text 20 760 hooks: ockm-<track>-rhythm 0-7 \\, ockm-<track>-prog 0-7 \\, ockm-<track>-gen (rebuild). Progressions change chord once per 16-step bar \\, so use 32 or 64 steps to hear them move.;")
p.save("seq/ockm-chordgen.pd","#N canvas 120 120 900 800 12;")

# ================= chord sound: 3 engines x 4 voices =================
def chord_voice(sp,kind):
    """Fill subpatch sp with one chord voice. Inlets: note (left), velocity (right)."""
    ni=sp.add("#X obj 20 20 inlet;"); vi=sp.add("#X obj 400 20 inlet;"); out=sp.add("#X obj 20 420 outlet~;")
    fv=sp.add("#X obj 400 50 f;"); sp.con(vi,0,fv,1)
    mo=sp.add("#X obj 20 50 moses 1;"); tb=sp.add("#X obj 20 80 t b f;"); mt=sp.add("#X obj 80 110 mtof;")
    roff=sp.add(f"#X obj 600 20 r {D}0-off;"); moff=sp.add("#X msg 600 50 0 30;")
    k=[sp.add(f"#X obj {600+i*90} 100 r ockm-{D}1-k{i+1};") for i in range(4)]
    am=sp.add("#X obj 20 330 *~;"); av=sp.add("#X obj 200 300 vline~;")
    for c in [(ni,0,mo,0),(mo,1,tb,0),(tb,1,mt,0),(roff,0,moff,0),(moff,0,av,0),(av,0,am,1),(am,0,out,0)]: sp.con(*c)
    if kind=="stab":
        tf=sp.add("#X obj 80 140 t f f;"); dt=sp.add("#X obj 160 170 * 1.007;"); p1=sp.add("#X obj 80 200 phasor~;"); p2=sp.add("#X obj 160 200 phasor~;")
        sm=sp.add("#X obj 80 230 +~;"); ce=sp.add("#X obj 80 255 -~ 1;")
        fe=sp.add("#X obj 400 200 vline~;"); fa=sp.add("#X obj 400 225 *~ 3000;"); fb=sp.add("#X obj 400 250 +~ 600;"); fc=sp.add("#X obj 400 275 clip~ 40 15000;")
        l1=sp.add("#X obj 80 290 lop~;"); l2=sp.add("#X obj 80 310 lop~;")
        dk=sp.add("#X obj 300 130 f 280;"); tbb=sp.add("#X obj 20 140 t b b;")
        pa=sp.add("#X obj 200 200 pack f 280;"); ma=sp.add(f"#X msg 200 230 {D}1 2 \\, 0 {D}2 2;"); mf=sp.add(f"#X msg 400 170 1 \\, 0 {D}1;")
        x1=sp.add(f"#X obj 600 140 expr 150*pow(2\\,6*{D}f1);"); x2=sp.add(f"#X obj 690 140 expr 1+0.02*{D}f1;"); x3=sp.add("#X obj 780 140 * 8000;"); x4=sp.add(f"#X obj 870 140 expr 40+{D}f1*800;")
        for c in [(mt,0,tf,0),(tf,1,dt,0),(dt,0,p2,0),(tf,0,p1,0),(p1,0,sm,0),(p2,0,sm,1),(sm,0,ce,0),(ce,0,l1,0),(l1,0,l2,0),(l2,0,am,0),
                  (fe,0,fa,0),(fa,0,fb,0),(fb,0,fc,0),(fc,0,l1,1),(fc,0,l2,1),
                  (tb,0,tbb,0),(tbb,1,fv,0),(fv,0,pa,0),(pa,0,ma,0),(ma,0,av,0),(tbb,0,dk,0),(dk,0,mf,0),(mf,0,fe,0),
                  (k[0],0,x1,0),(x1,0,fb,1),(k[1],0,x2,0),(x2,0,dt,1),(k[2],0,x3,0),(x3,0,fa,1),(k[3],0,x4,0),(x4,0,dk,1),(x4,0,pa,1)]: sp.con(*c)
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

CHORD_ENGINES=[("stab","Stab: two detuned saws through a filter that snaps shut. Dub techno with the delay"),
               ("organ","Organ: sine drawbars plus a percussive click. House organ stabs"),
               ("pad","Pad: three detuned saws with a slow attack. Long chords")]
for idx,(kind,title) in enumerate(CHORD_ENGINES):
    q=P(); q.add(f"#X text 20 10 Chord engine {idx}. {title}. k1-k4 0 to 1.;")
    inl=q.add("#X obj 30 50 inlet;"); sp_=q.add("#X obj 30 80 spigot 1;"); ro=q.add("#X obj 30 110 route off;")
    so=q.add(f"#X obj 30 140 s {D}0-off;"); up=q.add("#X obj 120 140 unpack f f f f f;")
    re=q.add(f"#X obj 700 50 r ockm-{D}1-engine;"); eq=q.add(f"#X obj 700 80 == {idx};"); tf=q.add("#X obj 700 110 t f f;")
    sw=q.add("#X obj 700 170 switch~;"); s0=q.add("#X obj 760 140 sel 0;"); bo=q.add(f"#X obj 760 170 s {D}0-off;")
    for c in [(inl,0,sp_,0),(sp_,0,ro,0),(ro,0,so,0),(ro,1,up,0),(re,0,eq,0),(eq,0,tf,0),(tf,1,sw,0),(tf,0,s0,0),(s0,0,bo,0),(tf,0,sp_,1)]: q.con(*c)
    vs=[]
    for v in range(4):
        sp=P(); chord_voice(sp,kind)
        q.L.append(sp.text(f"#N canvas 0 0 980 460 v{v} 0;").rstrip("\n"))
        o=q.add(f"#X restore {120+v*90} 200 pd v{v};"); vs.append(o)
        q.con(up,v,o,0); q.con(up,4,o,1)
    s1=q.add("#X obj 120 260 +~;"); s2=q.add("#X obj 120 280 +~;"); s3=q.add("#X obj 120 300 +~;"); g=q.add("#X obj 120 330 *~ 0.18;"); out=q.add("#X obj 120 370 outlet~;")
    for c in [(vs[0],0,s1,0),(vs[1],0,s1,1),(s1,0,s2,0),(vs[2],0,s2,1),(s2,0,s3,0),(vs[3],0,s3,1),(s3,0,g,0),(g,0,out,0)]: q.con(*c)
    q.save(f"voices/ockm-chord-{kind}.pd","#N canvas 160 160 900 420 12;")
q=P()
q.add("#X text 20 10 Chord synth: three engines \\, one plays at a time (ockm-<track>-engine 0 stab \\, 1 organ \\, 2 pad). Input: up to 4 MIDI notes plus a hit strength \\, or off.;")
inl=q.add("#X obj 30 50 inlet;")
eng=[q.add(f"#X obj {30+i*170} 100 ockm-chord-{k} {D}1;") for i,(k,_) in enumerate(CHORD_ENGINES)]
s1=q.add("#X obj 30 160 +~;"); s2=q.add("#X obj 30 185 +~;"); out=q.add("#X obj 30 220 outlet~;")
for e in eng: q.con(inl,0,e,0)
for c in [(eng[0],0,s1,0),(eng[1],0,s1,1),(s1,0,s2,0),(eng[2],0,s2,1),(s2,0,out,0)]: q.con(*c)
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
me=q.add("#X msg 1000 630 \; "+" \; ".join(f"{T} const 0" for T in TABLES)+" \; ockm-len 16;"); q.con(re_,0,me,0)
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
syn=q.add(f"#X obj 820 1330 s {D}0-sync;"); one=q.add("#X msg 880 1330 1;")
for c in [(rl,0,tfb,0),(tfb,1,started,0),(started,0,scap,0),(tfb,0,tl,0),
          (tl,5,cur,1),(tl,5,lpp,1),(tl,5,fcur,1),(tl,4,l1,0),(l1,0,sl1,0),(tl,3,fcur,0),(fcur,0,play,0),(play,0,sq,0),
          (tl,2,l0,0),(l0,0,sl0,0),(tl,1,rf,0),(tl,0,syn,0),(tl,0,one,0),(one,0,started,1)]: q.con(*c)
# --- save: capture, then write the pattern and the project ---
rsv=q.add("#X obj 20 1450 r ockm-do-save;"); tsv=q.add("#X obj 20 1475 t b b b b;")
fc2=q.add("#X obj 200 1505 f;"); p1=q.add("#X obj 200 1530 + 1;"); mkf=q.add(f"#X obj 200 1555 makefilename {QDIR}/p%d.txt;"); lpw=q.add("#X obj 200 1580 list prepend write;"); ltw=q.add("#X obj 200 1605 list trim;")
cj=q.add("#X msg 20 1505 clear;"); scj=q.add(f"#X obj 80 1530 s {D}0-cap-j;")
wj=q.add(f"#X msg 20 1560 write {QDIR}/project.txt;")
tj=q.add("#X obj 20 1530 t b b b;")
sdone=q.add("#X msg 400 1505 \; ockm-saved bang;")
for c in [(rsv,0,tsv,0),(tsv,3,scap,0),(tsv,2,fc2,0),(tl,5,fc2,1),(fc2,0,p1,0),(p1,0,mkf,0),(mkf,0,lpw,0),(lpw,0,ltw,0),(ltw,0,sap,0),
          (tsv,1,tj,0),(tj,2,cj,0),(cj,0,saj,0),(tj,1,scj,0),(tj,0,wj,0),(wj,0,saj,0),(tsv,0,sdone,0)]: q.con(*c)
# --- revert: reload the project and the current pattern from disk ---
rrv=q.add("#X obj 20 1650 r ockm-revert;"); trv=q.add("#X obj 20 1675 t b b b b;")
rj2=q.add(f"#X msg 300 1705 read {QDIR}/project.txt \\, rewind \\, bang;")
fc3=q.add("#X obj 200 1705 f;"); p2=q.add("#X obj 200 1730 + 1;"); mkr=q.add(f"#X obj 200 1755 makefilename {QDIR}/p%d.txt;"); lpr=q.add("#X obj 200 1780 list prepend read;"); ltr2=q.add("#X obj 200 1805 list trim;")
z=q.add("#X msg 120 1705 0;"); fc4=q.add("#X obj 20 1735 f;"); sld=q.add("#X obj 20 1760 s ockm-load;")
for c in [(rrv,0,trv,0),(trv,3,rj2,0),(rj2,0,saj,0),(trv,2,fc3,0),(tl,5,fc3,1),(fc3,0,p2,0),(p2,0,mkr,0),(mkr,0,lpr,0),(lpr,0,ltr2,0),(ltr2,0,sap,0),
          (trv,1,z,0),(z,0,started,1),(trv,0,fc4,0),(tl,5,fc4,1),(fc4,0,sld,0)]: q.con(*c)
# --- start-up: read the project and every pattern, then load pattern 1 ---
lb=q.add("#X obj 20 1850 loadbang;"); tlb=q.add("#X obj 20 1875 t b b b;")
ini_j=q.add(f"#X msg 300 1905 read {QDIR}/project.txt \\, rewind \\, bang;")
ini_p=q.add("#X msg 160 1905 "+" \\, ".join(f"{n} read {QDIR}/p{n+1}.txt" for n in range(SLOTN))+";")
go=q.add("#X msg 20 1905 \; ockm-slotset set 0 \; ockm-want 0;")
for c in [(lb,0,tlb,0),(tlb,2,ini_j,0),(ini_j,0,saj,0),(tlb,1,ini_p,0),(ini_p,0,sq,0),(tlb,0,go,0)]: q.con(*c)
q.save("seq/ockm-store.pd","#N canvas 60 60 2200 1960 12;")

# ================= project files =================
def build_project(reset=False):
    """Write the starter project: project.txt (tempo, effects, MIDI, accent, drum kit) and p1-p8.
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
        if k>=4:
            write(f"p{k+1}.txt",["ockm-empty 1"]); continue
        lines=[f"{h} {fmt(d)}" for h,d,_ in PATTERN_KEYS]
        lines+=[f"ockm-pat-{nm} 0 {pad(drums[nm][k])}" for nm,_ in SLOTS]
        lines+=[f"ockm-pat-bass-{f} 0 {pad(bass[k][f])}" for f in MONO]
        lines+=[f"ockm-pat-lead-{f} 0 {pad(lead[k][f])}" for f in MONO]
        lines+=[f"ockm-pat-chord-on 0 {pad(chord_on[k])}", f"ockm-pat-chord-deg 0 {pad(E)}"]
        write(f"p{k+1}.txt",lines)


build_project(reset=args.reset_patterns)
print("built", R)
