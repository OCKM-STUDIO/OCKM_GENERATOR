# OCKM Drum Lab: a separate patch for designing a drum kit (clap, snare, hats, kick, toms, congas, rim, shaker) and rendering it to WAV.
# Run by tools/build.py (it uses P, D and R from there). Writes OCKM_DRUM_LAB.pd and lab/.
# Nothing in the instrument depends on it: the lab only writes WAVs into the samples folders.

LAB_CLAP = [  # name, low, high, start, label
    ("bursts", 1, 6, 4, "bursts"), ("gap", 4, 25, 10, "gap between bursts (ms)"), ("jitter", 0, 1, 0.3, "looseness"),
    ("bdecay", 2, 15, 6, "burst length (ms)"), ("toneA", 600, 2500, 1150, "body tone (Hz)"), ("toneB", 1500, 6000, 2600, "air tone (Hz)"),
    ("width", 0.5, 6, 2.2, "tone focus"), ("balance", 0, 1, 0.4, "body to air"), ("tail", 30, 600, 180, "tail (ms)"),
    ("tailtone", 500, 3000, 1200, "tail tone (Hz)"), ("room", 0, 0.9, 0.35, "room"), ("drive", 0, 1, 0.35, "snap / drive"),
    ("level", 0, 1, 0.8, "level"),
]
LAB_SNARE = [
    ("pitch", 120, 320, 190, "body pitch (Hz)"), ("ratio", 1.2, 2.2, 1.6, "second tone ratio"), ("drop", 0, 12, 5, "pitch drop (semitones)"),
    ("droptime", 5, 60, 20, "drop time (ms)"), ("bodydec", 30, 300, 110, "body decay (ms)"), ("wires", 1500, 8000, 3800, "wires tone (Hz)"),
    ("wwidth", 0.3, 3, 0.9, "wires focus"), ("wdecay", 40, 400, 170, "wires decay (ms)"), ("click", 0, 1, 0.4, "click"),
    ("mix", 0, 1, 0.55, "body to wires"), ("drive", 0, 1, 0.3, "drive"), ("level", 0, 1, 0.8, "level"),
]
LAB_HAT = [   # one metallic sound, played short (closed) or long (open)
    ("pitch", 0.5, 2, 1, "metal pitch"), ("ring", 0, 1, 0.55, "noise to metal"), ("tone", 4000, 12000, 8000, "tone (Hz)"),
    ("focus", 0.4, 3, 1, "tone focus"), ("bright", 3000, 10000, 6000, "low cut (Hz)"), ("closed", 10, 120, 45, "closed length (ms)"),
    ("open", 150, 900, 420, "open length (ms)"), ("drive", 0, 1, 0.25, "drive"), ("level", 0, 1, 0.7, "level"),
]
os.makedirs(os.path.join(R, "lab"), exist_ok=True)
MK_CLAP, MK_SNARE, MK_HAT = 1.4, 1.0, 2.6      # makeup gain before the drive (set by measuring renders)

# ---- a band-pass whose frequency and focus come from two receive names (RBJ, 0 dB at the centre)
q = P()
q.add("#X text 20 10 Band-pass for the lab: args are the receive names for frequency and focus (Q).;")
inl = q.add("#X obj 30 40 inlet~;")
bq = q.add("#X obj 30 200 biquad~;"); out = q.add("#X obj 30 230 outlet~;")
rf = q.add(f"#X obj 200 40 r {D}1;"); rq = q.add(f"#X obj 300 40 r {D}2;"); tq = q.add("#X obj 300 65 t b f;")
lb = q.add("#X obj 420 40 loadbang;"); sr = q.add("#X obj 420 65 samplerate~;"); tsr = q.add("#X obj 420 90 t b f;")
S = f"(if({D}f3>1 \\, {D}f3 \\, 48000))"; Qx = f"(max({D}f2 \\, 0.1))"; W = f"(6.2831853*{D}f1/{S})"; A = f"(sin({W})/(2*{Qx}))"
ex = q.add(f"#X obj 200 120 expr 2*cos({W})/(1+{A}) \\; -(1-{A})/(1+{A}) \\; {A}/(1+{A}) \\; 0 \\; -{A}/(1+{A});")
pk = q.add("#X obj 200 160 pack f f f f f;")
for c in [(inl, 0, bq, 0), (bq, 0, out, 0), (rf, 0, ex, 0), (rq, 0, tq, 0), (tq, 1, ex, 1), (tq, 0, ex, 0), (lb, 0, sr, 0), (sr, 0, tsr, 0),
          (tsr, 1, ex, 2), (tsr, 0, ex, 0), (pk, 0, bq, 0)]: q.con(*c)
for i in range(5): q.con(ex, i, pk, i)
q.save("lab/ockm-lab-bp.pd", "#N canvas 200 200 700 260 12;")

def save_voice(q, x, fn, header):
    """every lab-<x>- receive becomes $1- (the voice's argument), so one voice file serves the lab and each drum slot"""
    q.L = [l.replace(f"lab-{x}-", f"{D}1-") for l in q.L]
    q.save(fn, header)

def env_sq(p, x, y, name):
    """[r name] -> vline~ -> squared (so the decay sounds natural)"""
    r = p.add(f"#X obj {x} {y} r {name};"); v = p.add(f"#X obj {x} {y+25} vline~;"); s = p.add(f"#X obj {x} {y+50} *~;")
    p.con(r, 0, v, 0); p.con(v, 0, s, 0); p.con(v, 0, s, 1)
    return s

def drive_out(p, x, y, src, pre, makeup):
    """src -> makeup gain -> tanh drive (lab-<pre>-drive) -> level (lab-<pre>-level) -> outlet~"""
    mk = p.add(f"#X obj {x} {y} *~ {makeup};")
    rd = p.add(f"#X obj {x+150} {y} r {D}1-drive;"); dx = p.add(f"#X obj {x+150} {y+25} expr 1+{D}f1*4;")
    th = p.add(f"#X obj {x} {y+50} expr~ tanh({D}v1*{D}f2)/tanh({D}f2);")
    lv = p.add(f"#X obj {x} {y+80} *~ 0.8;"); rl = p.add(f"#X obj {x+150} {y+55} r {D}1-level;")
    # how hard it was hit: a plain volume after everything else, so a soft hit is the same sound, quieter
    rv = p.add(f"#X obj {x+150} {y+85} r {D}1-vel;"); mv = p.add(f"#X msg {x+150} {y+110} {D}1 1;"); ln = p.add(f"#X obj {x+150} {y+135} line~;")
    vg = p.add(f"#X obj {x} {y+110} *~;")
    o = p.add(f"#X obj {x} {y+140} outlet~;")
    lb = p.add(f"#X obj {x+300} {y} loadbang;"); one = p.add(f"#X msg {x+300} {y+25} 1;")
    for c in [(src, 0, mk, 0), (mk, 0, th, 0), (rd, 0, dx, 0), (dx, 0, th, 1), (lb, 0, one, 0), (one, 0, th, 1), (th, 0, lv, 0), (rl, 0, lv, 1),
              (lv, 0, vg, 0), (rv, 0, mv, 0), (one, 0, mv, 0), (mv, 0, ln, 0), (ln, 0, vg, 1), (vg, 0, o, 0)]: p.con(*c)

# ---- clap: bursts of two noise bands, a tail of its own, a little room
q = P()
q.add("#X text 20 10 Lab clap: bursts (lab-clap-burst) of two band-passed noise colours \\, a separate tail (lab-clap-tailenv) \\, a small room \\, then drive.;")
nz = q.add("#X obj 30 50 noise~;")
ba = q.add("#X obj 30 90 ockm-lab-bp lab-clap-toneA lab-clap-width;"); bb = q.add("#X obj 300 90 ockm-lab-bp lab-clap-toneB lab-clap-width;")
ga = q.add("#X obj 30 130 *~ 0.6;"); gb = q.add("#X obj 300 130 *~ 0.4;")
rbal = q.add("#X obj 560 90 r lab-clap-balance;"); tbal = q.add("#X obj 560 115 t f f;"); inv = q.add(f"#X obj 560 140 expr 1-{D}f1;")
sm = q.add("#X obj 30 170 +~;")
be = env_sq(q, 700, 50, "lab-clap-burst")
mb = q.add("#X obj 30 210 *~;")
bt = q.add("#X obj 30 260 ockm-lab-bp lab-clap-tailtone lab-clap-tailq;")
lbq = q.add("#X obj 560 200 loadbang;"); mq = q.add("#X msg 560 225 1.2;"); sq_ = q.add(f"#X obj 560 250 s {D}1-tailq;"); q.con(mq, 0, sq_, 0)
te = env_sq(q, 700, 200, "lab-clap-tailenv")
mt = q.add("#X obj 30 300 *~;"); tg = q.add("#X obj 30 325 *~ 0.5;")
mix = q.add("#X obj 30 350 +~;"); hp = q.add("#X obj 30 375 hip~ 120;")
# room: a short feedback network of three taps
fb = q.add("#X obj 30 410 +~;"); dw = q.add(f"#X obj 200 440 delwrite~ {D}0-room 100;")
d1 = q.add(f"#X obj 200 470 delread~ {D}0-room 7.3;"); d2 = q.add(f"#X obj 330 470 delread~ {D}0-room 11.1;"); d3 = q.add(f"#X obj 460 470 delread~ {D}0-room 13.7;")
ds = q.add("#X obj 200 500 +~;"); ds2 = q.add("#X obj 200 525 +~;"); dm = q.add("#X obj 200 550 *~ 0.33;"); rm = q.add("#X obj 200 575 *~ 0.35;")
rr = q.add("#X obj 330 550 r lab-clap-room;")
for c in [(nz, 0, ba, 0), (nz, 0, bb, 0), (ba, 0, ga, 0), (bb, 0, gb, 0), (rbal, 0, tbal, 0), (tbal, 1, gb, 1), (tbal, 0, inv, 0), (inv, 0, ga, 1),
          (ga, 0, sm, 0), (gb, 0, sm, 1), (sm, 0, mb, 0), (be, 0, mb, 1), (nz, 0, bt, 0), (bt, 0, mt, 0), (te, 0, mt, 1), (mt, 0, tg, 0),
          (lbq, 0, mq, 0), (mb, 0, mix, 0), (tg, 0, mix, 1), (mix, 0, hp, 0), (hp, 0, fb, 0), (fb, 0, dw, 0),
          (d1, 0, ds, 0), (d2, 0, ds, 1), (ds, 0, ds2, 0), (d3, 0, ds2, 1), (ds2, 0, dm, 0), (dm, 0, rm, 0), (rr, 0, rm, 1), (rm, 0, fb, 1)]: q.con(*c)
drive_out(q, 30, 620, fb, "clap", MK_CLAP)
save_voice(q, "clap", "lab/ockm-lab-clap.pd", "#N canvas 200 200 900 760 12;")

# ---- snare: a tuned body with a pitch drop, a wires layer, a click
q = P()
q.add("#X text 20 10 Lab snare: two tones with a pitch drop (lab-snare-freq \\, lab-snare-body) \\, band-passed noise wires (lab-snare-wenv) \\, a click (lab-snare-cenv) \\, then drive.;")
rfq = q.add("#X obj 30 50 r lab-snare-freq;"); vf = q.add("#X obj 30 75 vline~;")
o1 = q.add("#X obj 30 110 osc~;"); rrt = q.add("#X obj 200 75 r lab-snare-ratio;"); mr = q.add("#X obj 200 110 *~ 1.6;"); o2 = q.add("#X obj 200 140 osc~;")
g2 = q.add("#X obj 200 170 *~ 0.6;"); bs = q.add("#X obj 30 200 +~;")
benv = env_sq(q, 700, 50, "lab-snare-body")
bm = q.add("#X obj 30 230 *~;")
nz = q.add("#X obj 30 280 noise~;"); wb = q.add("#X obj 30 310 ockm-lab-bp lab-snare-wires lab-snare-wwidth;")
wenv = env_sq(q, 700, 200, "lab-snare-wenv")
wm = q.add("#X obj 30 350 *~;")
ch = q.add("#X obj 300 310 hip~ 3000;"); cenv = env_sq(q, 700, 350, "lab-snare-cenv"); cm = q.add("#X obj 300 350 *~;")
rck = q.add("#X obj 450 330 r lab-snare-click;"); cg = q.add("#X obj 300 380 *~ 0.4;")
rmx = q.add("#X obj 500 200 r lab-snare-mix;"); tmx = q.add("#X obj 500 225 t f f;"); imx = q.add(f"#X obj 500 250 expr (1-{D}f1)*0.5;")
bg = q.add("#X obj 30 260 *~ 0.25;"); wg = q.add("#X obj 30 380 *~ 0.55;")
s1 = q.add("#X obj 30 420 +~;"); s2 = q.add("#X obj 30 450 +~;")
for c in [(rfq, 0, vf, 0), (vf, 0, o1, 0), (vf, 0, mr, 0), (rrt, 0, mr, 1), (mr, 0, o2, 0), (o2, 0, g2, 0), (o1, 0, bs, 0), (g2, 0, bs, 1),
          (bs, 0, bm, 0), (benv, 0, bm, 1), (bm, 0, bg, 0), (nz, 0, wb, 0), (wb, 0, wm, 0), (wenv, 0, wm, 1), (wm, 0, wg, 0),
          (nz, 0, ch, 0), (ch, 0, cm, 0), (cenv, 0, cm, 1), (cm, 0, cg, 0), (rck, 0, cg, 1),
          (rmx, 0, tmx, 0), (tmx, 1, wg, 1), (tmx, 0, imx, 0), (imx, 0, bg, 1),
          (bg, 0, s1, 0), (wg, 0, s1, 1), (s1, 0, s2, 0), (cg, 0, s2, 1)]: q.con(*c)
drive_out(q, 30, 490, s2, "snare", MK_SNARE)
save_voice(q, "snare", "lab/ockm-lab-snare.pd", "#N canvas 200 200 900 640 12;")

# ---- hat: six square waves at clashing (808-style) pitches, mixed with noise, band-passed and high-passed.
# One envelope (lab-hat-env): short for closed, long for open, so the pair always match
q = P()
q.add("#X text 20 10 Lab hat: six squares at clashing pitches (the 808 recipe) plus noise \\, band-passed (tone \\, focus) and high-passed (low cut) \\, then drive. Closed and open share it: only the length changes.;")
rp = q.add("#X obj 30 40 r lab-hat-pitch;")
sq = None
for i, f in enumerate([205.3, 304.4, 369.6, 522.7, 540.0, 800.0]):
    x = 30 + i * 110
    m = q.add(f"#X obj {x} 70 * {f};"); ph = q.add(f"#X obj {x} 100 phasor~ {f};"); sw = q.add(f"#X obj {x} 130 expr~ ({D}v1>0.5)*2-1;")
    q.con(rp, 0, m, 0); q.con(m, 0, ph, 0); q.con(ph, 0, sw, 0)
    if sq is None: sq = sw
    else:
        a = q.add(f"#X obj 30 {160 + i * 4} +~;"); q.con(sq, 0, a, 0); q.con(sw, 0, a, 1); sq = a
mg = q.add("#X obj 30 200 *~ 0.17;"); nz = q.add("#X obj 400 200 noise~;")
rr = q.add("#X obj 700 170 r lab-hat-ring;"); trr = q.add("#X obj 700 195 t f f;"); inr = q.add(f"#X obj 760 220 expr 1-{D}f1;")
gm = q.add("#X obj 30 230 *~ 0.55;"); gn = q.add("#X obj 400 230 *~ 0.45;"); mx = q.add("#X obj 30 260 +~;")
bp = q.add("#X obj 30 290 ockm-lab-bp lab-hat-tone lab-hat-focus;")
rb = q.add("#X obj 300 300 r lab-hat-bright;"); h1 = q.add("#X obj 30 330 hip~ 6000;"); h2 = q.add("#X obj 30 360 hip~ 6000;")
he = env_sq(q, 700, 300, "lab-hat-env"); hm = q.add("#X obj 30 400 *~;")
for c in [(sq, 0, mg, 0), (mg, 0, gm, 0), (nz, 0, gn, 0), (rr, 0, trr, 0), (trr, 1, gm, 1), (trr, 0, inr, 0), (inr, 0, gn, 1),
          (gm, 0, mx, 0), (gn, 0, mx, 1), (mx, 0, bp, 0), (bp, 0, h1, 0), (h1, 0, h2, 0), (rb, 0, h1, 1), (rb, 0, h2, 1), (h2, 0, hm, 0), (he, 0, hm, 1)]: q.con(*c)
drive_out(q, 30, 440, hm, "hat", MK_HAT)
save_voice(q, "hat", "lab/ockm-lab-hat.pd", "#N canvas 200 200 900 600 12;")

# ---- tuned drums (kick, tom, conga, rim): a sine with a pitch drop, an overtone, and a noise layer (click, skin
# or slap), each with its own envelope. The brain sends lab-<x>-st (pitch drop, in semitones), lab-<x>-body and
# lab-<x>-nenv (envelopes) and lab-<x>-mul (for the low, mid and high of a set)
def tuned_voice(x, title, makeup):
    q = P()
    q.add(f"#X text 20 10 Lab {x}: {title};")
    rst = q.add(f"#X obj 30 40 r lab-{x}-st;"); vst = q.add("#X obj 30 65 vline~;")
    rp = q.add(f"#X obj 250 40 r lab-{x}-pitch;"); rm = q.add(f"#X obj 400 40 r lab-{x}-mul;")
    pm = q.add(f"#X obj 250 70 expr {D}f1*{D}f2;"); lbm = q.add("#X obj 400 10 loadbang;"); one = q.add("#X msg 400 25 1;")
    trm = q.add("#X obj 400 65 t b f;")
    fq = q.add(f"#X obj 30 100 expr~ pow(2 \\, {D}v1/12)*{D}f2;")
    o1 = q.add("#X obj 30 140 osc~;"); rr = q.add(f"#X obj 250 120 r lab-{x}-ratio;"); mr = q.add("#X obj 250 145 *~ 1.5;"); o2 = q.add("#X obj 250 175 osc~;")
    rs = q.add(f"#X obj 400 175 r lab-{x}-second;"); g2 = q.add("#X obj 250 205 *~ 0;")
    bs = q.add("#X obj 30 235 +~;"); be = env_sq(q, 600, 40, f"lab-{x}-body"); bm = q.add("#X obj 30 265 *~;")
    nz = q.add("#X obj 30 310 noise~;"); bp = q.add(f"#X obj 30 340 ockm-lab-bp lab-{x}-ntone lab-{x}-nfocus;")
    ne = env_sq(q, 600, 200, f"lab-{x}-nenv"); nm = q.add("#X obj 30 380 *~;")
    rn = q.add(f"#X obj 250 380 r lab-{x}-noise;"); ng = q.add("#X obj 30 410 *~ 0;")
    sm = q.add("#X obj 30 450 +~;")
    for c in [(rst, 0, vst, 0), (vst, 0, fq, 0), (rp, 0, pm, 0), (lbm, 0, one, 0), (one, 0, trm, 0), (rm, 0, trm, 0), (trm, 1, pm, 1), (trm, 0, pm, 0),
              (pm, 0, fq, 1), (fq, 0, o1, 0), (fq, 0, mr, 0), (rr, 0, mr, 1), (mr, 0, o2, 0), (o2, 0, g2, 0), (rs, 0, g2, 1),
              (o1, 0, bs, 0), (g2, 0, bs, 1), (bs, 0, bm, 0), (be, 0, bm, 1),
              (nz, 0, bp, 0), (bp, 0, nm, 0), (ne, 0, nm, 1), (nm, 0, ng, 0), (rn, 0, ng, 1), (bm, 0, sm, 0), (ng, 0, sm, 1)]: q.con(*c)
    drive_out(q, 30, 490, sm, x, makeup)
    save_voice(q, x, f"lab/ockm-lab-{x}.pd", "#N canvas 200 200 900 640 12;")

def tuned_params(pitch, sweep, sweeptime, decay, second, ratio, noise, ntone, nfocus, ndecay, drive, names):
    """the same set of controls for each tuned drum; each tuple is (low, high, start); names label the noise layer"""
    P_ = [("pitch", pitch, "pitch (Hz)"), ("sweep", sweep, "pitch drop (semitones)"), ("sweeptime", sweeptime, "drop time (ms)"),
          ("decay", decay, "decay (ms)"), ("second", second, "overtone"), ("ratio", ratio, "overtone ratio"),
          ("noise", noise, names[0]), ("ntone", ntone, names[0] + " tone (Hz)"), ("nfocus", nfocus, names[0] + " focus"),
          ("ndecay", ndecay, names[0] + " length (ms)"), ("drive", drive, "drive"), ("level", (0, 1, 0.8), "level")]
    return [(n, r[0], r[1], r[2], lab) for n, r, lab in P_]

LAB_KICK = tuned_params((35, 90, 48), (0, 48, 28), (5, 150, 35), (80, 1200, 420), (0, 1, 0), (1.2, 3, 1.5),
                        (0, 1, 0.35), (1000, 8000, 3500), (0.4, 3, 0.8), (2, 40, 6), (0, 1, 0.3), ("click",))
LAB_TOM = tuned_params((60, 300, 120), (0, 12, 5), (10, 150, 60), (80, 900, 350), (0, 1, 0.3), (1.2, 2.5, 1.5),
                       (0, 1, 0.25), (500, 5000, 1800), (0.4, 3, 1), (5, 120, 40), (0, 1, 0.25), ("skin",))
LAB_CONGA = tuned_params((150, 450, 220), (0, 7, 2), (5, 60, 20), (60, 500, 220), (0, 1, 0.35), (1.3, 2.8, 1.6),
                         (0, 1, 0.4), (1500, 6000, 3000), (0.5, 3, 1.2), (3, 40, 12), (0, 1, 0.2), ("slap",))
LAB_RIM = tuned_params((300, 1200, 500), (0, 5, 0), (2, 20, 5), (5, 80, 25), (0, 1, 0.7), (2, 4, 3.4),
                       (0, 1, 0.5), (1000, 8000, 3500), (0.5, 4, 1.5), (1, 15, 4), (0, 1, 0.4), ("click",))
LAB_SHAKER = [
    ("tone", 3000, 12000, 7000, "tone (Hz)"), ("focus", 0.4, 3, 1, "tone focus"), ("lowcut", 1000, 8000, 3000, "low cut (Hz)"),
    ("attack", 1, 40, 8, "attack (ms)"), ("decay", 15, 250, 70, "decay (ms)"), ("grit", 0, 1, 0.3, "grit"),
    ("drive", 0, 1, 0.2, "drive"), ("level", 0, 1, 0.75, "level"),
]
MK = dict(kick=0.7, tom=0.7, conga=0.8, rim=0.8, shaker=1.6)   # makeup gain before the drive (set by measuring renders)
for k, v in list(MK.items()): MK[k] = float(os.environ.get("MK_" + k.upper(), v))
tuned_voice("kick", "a sine diving in pitch \\, an optional overtone and a click.", MK["kick"])
tuned_voice("tom", "a sine with a gentle pitch drop \\, an overtone and a noise skin. Plays low \\, mid and high.", MK["tom"])
tuned_voice("conga", "a short tuned body with an overtone and a slap. Plays low and high.", MK["conga"])
tuned_voice("rim", "two tones a long way apart (the 808 rimshot) and a click.", MK["rim"])

# ---- shaker: band-passed noise with a swell (attack) and a fall, plus grit (sparse crackle)
q = P()
q.add("#X text 20 10 Lab shaker: band-passed noise with an attack and a decay (lab-shaker-env) \\, low cut \\, and grit: crackle from the loudest grains.;")
nz = q.add("#X obj 30 40 noise~;"); bp = q.add("#X obj 30 70 ockm-lab-bp lab-shaker-tone lab-shaker-focus;")
rl = q.add("#X obj 300 80 r lab-shaker-lowcut;"); h1 = q.add("#X obj 30 110 hip~ 3000;"); h2 = q.add("#X obj 30 140 hip~ 3000;")
cr = q.add(f"#X obj 300 140 expr~ ({D}v1>0.93)*2-({D}v1<-0.93)*2;"); rg = q.add("#X obj 450 140 r lab-shaker-grit;"); cg = q.add("#X obj 300 170 *~ 0;")
sm = q.add("#X obj 30 200 +~;"); se = env_sq(q, 600, 40, "lab-shaker-env"); sh = q.add("#X obj 30 240 *~;")
for c in [(nz, 0, bp, 0), (bp, 0, h1, 0), (h1, 0, h2, 0), (rl, 0, h1, 1), (rl, 0, h2, 1), (nz, 0, cr, 0), (cr, 0, cg, 0), (rg, 0, cg, 1),
          (h2, 0, sm, 0), (cg, 0, sm, 1), (sm, 0, sh, 0), (se, 0, sh, 1)]: q.con(*c)
drive_out(q, 30, 280, sh, "shaker", MK["shaker"])
save_voice(q, "shaker", "lab/ockm-lab-shaker.pd", "#N canvas 200 200 900 440 12;")

# ---- the kit: what each sound is called, where its renders go, and its sets (name, pitch multiplier)
KIT = [  # name, title, params, sample folder, variants
    ("clap", "CLAP", LAB_CLAP, "clap", []),
    ("snare", "SNARE", LAB_SNARE, "snare", []),
    ("hat", "HATS (closed and open)", LAB_HAT, None, [("closed", 1), ("open", 1)]),
    ("kick", "KICK", LAB_KICK, "kick", []),
    ("tom", "TOMS (low mid high)", LAB_TOM, "tom", [("low", 0.75), ("mid", 1), ("high", 1.33)]),
    ("conga", "CONGAS (low high)", LAB_CONGA, "perc", [("low", 1), ("high", 1.5)]),
    ("rim", "RIM", LAB_RIM, "perc", []),
    ("shaker", "SHAKER", LAB_SHAKER, "perc", []),
]
TUNED = ("kick", "tom", "conga", "rim")
# character: one named slider per sound, moving several settings at once (weights are shares of each range; the
# slider runs from -1 to 1, so pulling it left does the opposite)
CHARACTER = {
    "clap": ("room", {"tail": 0.6, "room": 0.7, "jitter": 0.4, "tailtone": -0.4, "bdecay": 0.2}),
    "snare": ("crack", {"wires": 0.4, "wdecay": 0.3, "bodydec": -0.4, "click": 0.6, "drive": 0.4, "mix": 0.4}),
    "hat": ("metal", {"ring": 0.7, "focus": 0.5, "bright": -0.4, "tone": -0.2}),
    "kick": ("punch", {"sweep": 0.5, "sweeptime": -0.5, "noise": 0.6, "decay": -0.3, "drive": 0.3}),
    "tom": ("boom", {"pitch": -0.4, "decay": 0.5, "sweep": 0.4, "noise": -0.4}),
    "conga": ("slap", {"noise": 0.6, "ntone": 0.4, "decay": -0.3, "second": 0.4}),
    "rim": ("wood", {"ratio": -0.6, "decay": 0.4, "noise": -0.4, "pitch": -0.2}),
    "shaker": ("shake", {"attack": 0.5, "decay": 0.5, "grit": 0.6, "tone": -0.2}),
}
# morph: how far along its range each setting may wander (pitch and tuning a little, colour more, level never)
MORPH_SCALE = {"level": 0, "pitch": 0.2, "ratio": 0.25, "bursts": 0.3, "drive": 0.3, "sweep": 0.3}


# ---- how each sound is played (its envelopes), shared by the lab's brain and the instrument's drum slots (Lua)
PLAY_LUA = '''
local function seg(name, target, time, delay) pd.send(name, "list", { target, time, delay }) end
-- play one hit. pre: where the voice listens (lab-kick, ockm-d1-kick); v: its settings; var: which of a set
-- (hats 1 closed 2 open; toms low mid high; congas low high); vel: how hard (0 to 1)
local function play_voice(pre, which, v, var, vel, k)
  -- how hard: a plain volume after the voice's drive, so a soft hit is the same sound, just quieter.
  -- (Scaling the envelopes instead pushed less into the drive and lost the snap.) The envelopes always run full
  pd.send(pre .. "-vel", "float", { math.max(0, math.min(1, vel or 1)) })
  var, vel = var or 1, 1
  if which == "hat" then
    seg(pre .. "-env", 0, 0, 0); seg(pre .. "-env", vel, 0.2, 0); seg(pre .. "-env", 0, (var == 2) and v.open or v.closed, 0.2)
  elseif which == "clap" then
    -- the bursts: each a quick hit of the two noise colours, a gap apart (looser with jitter); then the tail
    local t, n = 0, math.max(1, math.floor(v.bursts + 0.5))
    seg(pre .. "-burst", 0, 0, 0); seg(pre .. "-tailenv", 0, 0, 0)
    for b = 1, n do
      seg(pre .. "-burst", vel, 0.3, t)
      seg(pre .. "-burst", 0, v.bdecay, t + 0.3)
      if b < n then t = t + v.gap * (1 + v.jitter * (math.random() - 0.5)) end
    end
    seg(pre .. "-tailenv", vel, 1, t)
    seg(pre .. "-tailenv", 0, v.tail, t + 1)
  elseif which == "snare" then
    seg(pre .. "-freq", v.pitch * 2 ^ (v.drop / 12), 0, 0); seg(pre .. "-freq", v.pitch, v.droptime, 0)
    seg(pre .. "-body", 0, 0, 0); seg(pre .. "-body", vel, 0.5, 0); seg(pre .. "-body", 0, v.bodydec, 0.5)
    seg(pre .. "-wenv", 0, 0, 0); seg(pre .. "-wenv", vel, 0.5, 0); seg(pre .. "-wenv", 0, v.wdecay, 0.5)
    seg(pre .. "-cenv", 0, 0, 0); seg(pre .. "-cenv", vel, 0.1, 0); seg(pre .. "-cenv", 0, 3, 0.1)
  elseif which == "shaker" then
    seg(pre .. "-env", 0, 0, 0); seg(pre .. "-env", vel, v.attack, 0); seg(pre .. "-env", 0, v.decay, v.attack)
  else
    -- the tuned drums: kick, tom, conga, rim
    local mul = (k and k.variants[var] and k.variants[var][2]) or 1
    pd.send(pre .. "-mul", "float", { mul })
    seg(pre .. "-st", v.sweep, 0, 0); seg(pre .. "-st", 0, v.sweeptime, 0)
    seg(pre .. "-body", 0, 0, 0); seg(pre .. "-body", vel, 0.3, 0); seg(pre .. "-body", 0, v.decay, 0.3)
    seg(pre .. "-nenv", 0, 0, 0); seg(pre .. "-nenv", vel, 0.1, 0); seg(pre .. "-nenv", 0, v.ndecay, 0.1)
  end
end
'''

# ---- the brain: envelopes, randomise, loop against a kick, render to WAV (Lua)
def lua_params(lst): return "{ " + ", ".join(f'{{ "{n}", {lo}, {hi}, {st} }}' for n, lo, hi, st, _ in lst) + " }"
def lua_variants(vs): return "{ " + ", ".join(f'{{ "{n}", {m} }}' for n, m in vs) + " }"
lua_kit = ",\n  ".join(f'{w} = {{ params = {lua_params(pr)}, folder = {("nil" if fo is None else chr(34) + fo + chr(34))}, variants = {lua_variants(vs)} }}'
                       for w, _, pr, fo, vs in KIT)
open(os.path.join(R, "lab", "ockm-lab.pd_lua"), "w").write('''-- OCKM Drum Lab brain: plays each sound (its envelopes), randomises around the sound you have, loops them
-- against a kick, and renders hits to WAVs in the samples folders. Sets (hats, toms, congas) render as matching files.
-- Written by tools/build_lab.py: change it there.
local lab = pd.Class:new():register("ockm-lab")
local KIT = {
  ''' + lua_kit + '''
}
local TUNED = { kick = true, tom = true, conga = true, rim = true }
local CHARACTER = { ''' + ", ".join(f'{w} = {{ name = "{n}", w = {{ ' + ", ".join(f"{k} = {v}" for k, v in m.items()) + " } }" for w, (n, m) in CHARACTER.items()) + ''' }
local MORPH_SCALE = { ''' + ", ".join(f"{k} = {v}" for k, v in MORPH_SCALE.items()) + ''' }
local MORPH_POINTS = 4
''' + PLAY_LUA + '''
function lab:initialize(sel, atoms)
  self.inlets, self.outlets = 1, 0
  self.v, self.loop = {}, {}
  for which, k in pairs(KIT) do
    self.v[which] = {}
    for _, p in ipairs(k.params) do self.v[which][p[1]] = p[4] end
    self.loop[which] = false
  end
  self.beat = 0
  math.randomseed(os.time())
  self.home, self.char, self.morph, self.path = {}, {}, {}, {}
  for which in pairs(KIT) do
    self.home[which] = {}; for n, x in pairs(self.v[which]) do self.home[which][n] = x end
    self.char[which], self.morph[which] = 0, 0
    self:new_path(which)
  end
  return true
end

function lab:postinitialize()
  self.recv = {}
  local function listen(name, fn)
    local m = "r_" .. #self.recv
    self[m] = fn
    self.recv[#self.recv + 1] = pd.Receive:new():register(self, name, m)
  end
  for which, k in pairs(KIT) do
    for _, p in ipairs(k.params) do
      -- a setting moved by hand becomes part of the sound (as if you'd pressed keep)
      listen("lab-" .. which .. "-" .. p[1], function(o, sel, a)
        local x = tonumber(a[1]); if not x then return end
        o.v[which][p[1]] = x
        if not o.applying then o:keep(which, true) end
      end)
    end
    listen("lab-" .. which .. "-play", function(o) o:play(which, 1) end)
    for i, var in ipairs(k.variants) do listen("lab-" .. which .. "-play-" .. var[1], function(o) o:play(which, i) end) end
    listen("lab-" .. which .. "-render", function(o) o:render(which) end)
    listen("lab-" .. which .. "-loop", function(o, sel, a) o.loop[which] = (tonumber(a[1]) or 0) > 0; o:loop_check() end)
    listen("lab-" .. which .. "-reset", function(o) o:reset(which) end)
    listen("lab-" .. which .. "-char", function(o, sel, a) o.char[which] = tonumber(a[1]) or 0; o:apply(which) end)
    listen("lab-" .. which .. "-morph", function(o, sel, a) o.morph[which] = tonumber(a[1]) or 0; o:apply(which) end)
    listen("lab-" .. which .. "-newpath", function(o) o:new_path(which); o:apply(which); o:play(which, 1); o:status(which .. ": a new morph path") end)
    listen("lab-" .. which .. "-keep", function(o) o:keep(which); o:status(which .. ": kept, this is the sound now") end)
    for name, amt in pairs({ small = 0.12, medium = 0.35, wild = 1 }) do
      listen("lab-" .. which .. "-rand-" .. name, function(o) o:randomise(which, amt) end)
    end
  end
  listen("lab-test", function(o, sel, a) o:test(sel, a) end)
  self.stopclock = pd.Clock:new():register(self, "render_stop")
  self.loopclock = pd.Clock:new():register(self, "loop_tick")
  self.initclock = pd.Clock:new():register(self, "push_all")
  self.initclock:delay(0)
end

function lab:finalize()
  for _, r in ipairs(self.recv or {}) do r:destruct() end
  for _, c in ipairs({ self.stopclock, self.loopclock, self.initclock }) do if c then c:destruct() end end
end

-- every setting out to the sliders (which pass it on to the sound)
function lab:push_all()
  for which, k in pairs(KIT) do for _, p in ipairs(k.params) do self:set(which, p[1], self.v[which][p[1]]) end end
end
function lab:set(which, name, x)
  self.v[which][name] = x
  self.applying = true                               -- (the slider echoes it back: not a change by hand)
  pd.send("lab-" .. which .. "-" .. name .. "-ui", "float", { x })
  self.applying = false
end
function lab:reset(which)
  for _, p in ipairs(KIT[which].params) do self:set(which, p[1], p[4]) end
  self:keep(which)
  self:status(which .. ": back to the starting sound")
end

-- the two macro sliders. Home is the sound with both at zero; character moves its recipe of settings (either way);
-- morph walks a smooth, fixed path through nearby sounds (further along, further from home)
function lab:new_path(which)
  local pts = { {} }
  for _, p in ipairs(KIT[which].params) do pts[1][p[1]] = 0 end
  for k = 2, MORPH_POINTS + 1 do
    pts[k] = {}
    for _, p in ipairs(KIT[which].params) do
      local sc = MORPH_SCALE[p[1]] or 0.45
      pts[k][p[1]] = (math.random() * 2 - 1) * sc * (p[3] - p[2]) * math.min(1, k / 2.5)
    end
  end
  self.path[which] = pts
end
function lab:morph_offset(which, name)
  local m = self.morph[which] or 0
  if m <= 0 then return 0 end
  local pos = math.min(m, 0.9999) * MORPH_POINTS
  local i = math.floor(pos); local t = pos - i; t = t * t * (3 - 2 * t)
  local pts = self.path[which]
  return pts[i + 1][name] * (1 - t) + pts[i + 2][name] * t
end
function lab:apply(which)
  local ch = CHARACTER[which]
  for _, p in ipairs(KIT[which].params) do
    local name, lo, hi = p[1], p[2], p[3]
    local x = self.home[which][name]
    if ch and ch.w[name] then x = x + (self.char[which] or 0) * ch.w[name] * (hi - lo) end
    x = x + self:morph_offset(which, name)
    x = math.max(lo, math.min(hi, x))
    if name == "bursts" then x = math.floor(x + 0.5) end
    if math.abs(x - self.v[which][name]) > 1e-9 then self:set(which, name, x) end
  end
end
-- keep: the sound as it is becomes home, and both sliders go back to zero (the sound doesn't change)
function lab:keep(which, quiet)
  for n, x in pairs(self.v[which]) do self.home[which][n] = x end
  self.char[which], self.morph[which] = 0, 0
  self.applying = true
  pd.send("lab-" .. which .. "-char-ui", "float", { 0 }); pd.send("lab-" .. which .. "-morph-ui", "float", { 0 })
  self.applying = false
end

local function seg(name, target, time, delay) pd.send(name, "list", { target, time, delay }) end

-- play a sound; var picks one of a set (hats: 1 closed, 2 open; toms: low, mid, high; congas: low, high)
function lab:play(which, var) play_voice("lab-" .. which, which, self.v[which], var, 1, KIT[which]) end
-- the steady kick the loop plays against (the lab kick's starting sound, on its own voice)
function lab:ref_kick()
  local v = {}
  for _, p in ipairs(KIT.kick.params) do v[p[1]] = p[4] end
  for _, n in ipairs({ "pitch", "ratio", "second", "noise", "ntone", "nfocus", "drive", "level" }) do pd.send("labref-kick-" .. n, "float", { v[n] }) end
  play_voice("labref-kick", "kick", v, 1, 1, KIT.kick)
end

-- how long a hit lasts, so a render catches all of it
function lab:length(which, var)
  local v = self.v[which]
  if which == "hat" then return ((var == 2) and v.open or v.closed) * 1.6 + 40 end
  if which == "clap" then return math.min(2500, v.bursts * v.gap * 1.5 + v.tail * 1.6 + v.room * 400 + 60) end
  if which == "snare" then return math.min(2000, math.max(v.bodydec, v.wdecay) * 1.6 + 60) end
  if which == "shaker" then return v.attack + v.decay * 1.6 + 40 end
  return math.min(2500, math.max(v.decay, v.ndecay) * 1.6 + 40)
end

-- small, medium or wild: each setting moves at random within that share of its range
function lab:randomise(which, amt)
  for _, p in ipairs(KIT[which].params) do
    local name, lo, hi = p[1], p[2], p[3]
    if name ~= "level" then
      local x = self.v[which][name]
      if amt >= 1 then x = lo + math.random() * (hi - lo)
      else x = x + (math.random() * 2 - 1) * amt * (hi - lo) end
      x = math.max(lo, math.min(hi, x))
      if name == "bursts" then x = math.floor(x + 0.5) end
      self:set(which, name, x)
    end
  end
  self:keep(which)
  self:play(which, 1)
  self:status(which .. ": randomised (" .. ((amt >= 1) and "wild" or ((amt > 0.2) and "medium" or "small")) .. ")")
end

-- loop, at 120 in half beats: a kick on every beat (your lab kick if its loop is on), clap or snare on 2 and 4,
-- closed hats on the offbeats with an open one before the 1, shaker on every half beat, rim and congas off the beat,
-- a tom run at the end of the bar
function lab:loop_check()
  local on = false
  for _, x in pairs(self.loop) do on = on or x end
  if on and not self.looping then self.looping = true; self.beat = 0; self:loop_tick()
  elseif not on then self.looping = false; self.loopclock:unset() end
end
function lab:loop_tick()
  if not self.looping or self.rendering then return end
  local b, L = self.beat, self.loop                  -- half beats, 0 to 7
  if b % 2 == 0 then
    if L.kick then self:play("kick", 1) else self:ref_kick() end
  end
  if b == 2 or b == 6 then
    if L.clap then self:play("clap", 1) end
    if L.snare then self:play("snare", 1) end
  end
  if L.hat and b % 2 == 1 then self:play("hat", (b == 7) and 2 or 1) end
  if L.shaker then self:play("shaker", 1) end
  if L.rim and (b == 3 or b == 6) then self:play("rim", 1) end
  if L.conga and (b == 1 or b == 3 or b == 4) then self:play("conga", (b == 4) and 1 or 2) end
  if L.tom and b >= 5 then self:play("tom", 8 - b) end
  self.beat = (b + 1) % 8
  self.loopclock:delay(250)
end

-- render: record to samples/<folder>/lab-<sound>-<date and time>.wav (24-bit mono). A set renders each of its
-- sounds with the same name plus low/mid/high (or closed/open): the closed hat goes in samples/hat, the open in samples/open-hat
function lab:render(which)
  if self.rendering then return end
  local k = KIT[which]
  local stamp = os.date("%Y%m%d-%H%M%S")
  self.queue = {}
  if #k.variants == 0 then
    self.queue[1] = { which = which, var = 1, path = "samples/" .. k.folder .. "/lab-" .. which .. "-" .. stamp .. ".wav" }
  else
    for i, var in ipairs(k.variants) do
      local folder = k.folder or ((var[1] == "open") and "open-hat" or "hat")
      self.queue[i] = { which = which, var = i, path = "samples/" .. folder .. "/lab-" .. which .. "-" .. stamp .. "-" .. var[1] .. ".wav" }
    end
  end
  self.saved = {}
  self:render_next()
end
function lab:render_next()
  local job = table.remove(self.queue or {}, 1)
  if not job then return end
  self.rendering = job
  pd.send("lab-rec", "open", { "-bytes", 3, job.path })
  pd.send("lab-rec", "start", {})
  self:play(job.which, job.var)
  self.stopclock:delay(self:length(job.which, job.var))
end
function lab:render_stop()
  local r = self.rendering
  if not r then return end
  pd.send("lab-rec", "stop", {})
  self.rendering = nil
  pd.post("ockm-lab: saved " .. r.path)
  self.saved[#self.saved + 1] = r.path:match("[^/]+$")
  if self.queue and #self.queue > 0 then self:render_next(); return end
  self:status("saved " .. table.concat(self.saved, ", "))
  if self.looping then self.loopclock:delay(250) end
end
function lab:status(s) pd.send("lab-status", "symbol", { s }) end

-- headless tests
function lab:test(sel, a)
  if sel == "set" then self:set(tostring(a[1]), tostring(a[2]), tonumber(a[3]))
  elseif sel == "char" or sel == "morph" then
    local which, x = tostring(a[1]), tonumber(a[2]) or 0
    if sel == "char" then self.char[which] = x else self.morph[which] = x end
    self:apply(which)
  elseif sel == "keep" then self:keep(tostring(a[1]))
  elseif sel == "dump" then
    for which, k in pairs(KIT) do for _, p in ipairs(k.params) do pd.post(string.format("ockm-lab: %s %s %.3f", which, p[1], self.v[which][p[1]])) end end
  end
end
''')

# ---- the lab patch: a section per sound (two rows of four), the sounds, a kick for the loop, the recorder
q = P()
q.raw("#X declare -path lab -path voices;")
q.add("#X text 20 10 OCKM DRUM LAB: design a kit \\, then render it into the samples folders for OCKM (or the SP-404). Click to play \\, drag the sliders \\, randomise around what you have. Sets (hats \\, toms \\, congas) render as matching files.;")
X0 = 1240   # the plumbing, to the right of the sections
brain = q.add(f"#X obj {X0} 60 ockm-lab;")
voices = [q.add(f"#X obj {X0 + (i % 4) * 130} {120 + (i // 4) * 40} ockm-lab-{w} lab-{w};") for i, (w, _, _, _, _) in enumerate(KIT)]
kick = q.add(f"#X obj {X0+560} 120 ockm-lab-kick labref-kick;"); kg = q.add(f"#X obj {X0+560} 150 *~ 0.7;")
mix = q.add(f"#X obj {X0} 220 +~;"); allm = q.add(f"#X obj {X0} 250 +~;"); vol = q.add(f"#X obj {X0} 280 *~ 0.8;"); dac = q.add(f"#X obj {X0} 310 dac~;")
rec = q.add(f"#X obj {X0+180} 280 writesf~ 1;"); rrec = q.add(f"#X obj {X0+180} 250 r lab-rec;")
lbd = q.add(f"#X obj {X0+560} 200 loadbang;"); dsp = q.add(f"#X msg {X0+560} 225 \\; pd dsp 1;")
for v in voices: q.con(v, 0, mix, 0)   # every sound into one sum (outlets into one inlet add up)
for c in [(mix, 0, allm, 0), (kick, 0, kg, 0), (kg, 0, allm, 1), (allm, 0, vol, 0), (vol, 0, dac, 0), (vol, 0, dac, 1),
          (mix, 0, rec, 0), (rrec, 0, rec, 0), (lbd, 0, dsp, 0)]: q.con(*c)
COL = "#fcfcfc #000000 #000000"
ROW_Y = (50, 780)
def section(x, y0, which, title, params, variants):
    q.add(f"#X text {x} {y0} {title};")
    btn = lambda bx, by, send, label: q.add(f"#X obj {bx} {by} bng 26 250 50 0 {send} empty {label} 30 13 0 11 {COL};")
    if variants:
        for i, (vn, _) in enumerate(variants): btn(x + i * 82, y0 + 28, f"lab-{which}-play-{vn}", vn)
    else:
        btn(x, y0 + 28, f"lab-{which}-play", "play")
    q.add(f"#X obj {x+250} {y0+28} tgl 26 0 lab-{which}-loop empty loop 30 13 0 11 {COL} 0 1;")
    q.add(f"#X text {x} {y0+68} randomise:;")
    for i, k in enumerate(("small", "medium", "wild")): btn(x + 88 + i * 70, y0 + 64, f"lab-{which}-rand-{k}", k)
    btn(x, y0 + 100, f"lab-{which}-render", "render" + (" set" if variants else ""))
    btn(x + 160, y0 + 100, f"lab-{which}-reset", "reset")
    cname = CHARACTER[which][0]
    q.add(f"#X obj {x} {y0+152} hsl 250 20 -1 1 0 1 lab-{which}-char lab-{which}-char-ui {cname}_(less_<_>_more) 0 -9 0 11 #ffe6d8 #000000 #000000 {int(round(0.5 * 249 * 100))} 1;")
    q.add(f"#X obj {x} {y0+192} hsl 250 20 0 1 0 1 lab-{which}-morph lab-{which}-morph-ui morph 0 -9 0 11 #ffe6d8 #000000 #000000 0 1;")
    btn(x, y0 + 222, f"lab-{which}-newpath", "new_path")
    btn(x + 140, y0 + 222, f"lab-{which}-keep", "keep")
    y = y0 + 288
    for name, lo, hi, st, label in params:
        w = 250
        val = int(round((st - lo) / (hi - lo) * (w - 1) * 100))
        q.add(f"#X obj {x} {y} hsl {w} 16 {lo} {hi} 0 1 lab-{which}-{name} lab-{which}-{name}-ui {label.replace(' ', '_')} 0 -8 0 10 {COL} {val} 1;")
        y += 30
for i, (w, title, params, _, variants) in enumerate(KIT):
    section(20 + (i % 4) * 300, ROW_Y[i // 4], w, title, params, variants)
q.add("#X text 20 1480 last:;")
q.add("#X symbolatom 70 1480 90 0 0 0 - lab-status -;")
q.save("OCKM_DRUM_LAB.pd", "#N canvas 20 20 1220 1000 12;")

# ---- the instrument's drum slots play the lab's sounds (voices/ockm-labdrum.pd_lua, one per slot)
# Each slot runs its own copy of every lab sound (only the one in use is switched on). This brain picks the sound
# from the slot's sound and variant (ockm-<slot>-synth: for perc, rim / conga / shaker), works out its settings:
# the lab's starting sound, a randomise (a seed and an amount, so a project recalls it exactly), the character and
# morph sliders, then the slot's tune and decay, and plays each hit. Settings go to ockm-<slot>-<sound>-<setting>.
def listens(t):
    import re
    txt = open(os.path.join(R, "lab", f"ockm-lab-{t}.pd")).read()
    return sorted(set(re.findall(r"\\\$1-([A-Za-z]+)", txt)))
DRUM_TYPES = ["kick", "snare", "clap", "hat", "tom", "rim", "conga", "shaker"]   # their switch numbers; 8 = the sample player
open(os.path.join(R, "voices", "ockm-labdrum.pd_lua"), "w").write('''-- A drum slot's synth sounds: the drum lab's voices, with randomise, character and morph.
-- Written by tools/build_lab.py: change it there.
local labdrum = pd.Class:new():register("ockm-labdrum")
local KIT = {
  ''' + lua_kit + '''
}
local CHARACTER = { ''' + ", ".join(f'{w} = {{ name = "{n}", w = {{ ' + ", ".join(f"{k} = {v}" for k, v in m.items()) + " } }" for w, (n, m) in CHARACTER.items()) + ''' }
local MORPH_SCALE = { ''' + ", ".join(f"{k} = {v}" for k, v in MORPH_SCALE.items()) + ''' }
local MORPH_POINTS = 4
local TYPES = { ''' + ", ".join(f'"{t}"' for t in DRUM_TYPES) + ''' }
-- the settings each voice listens for (the rest only shape its envelopes, played from here)
local LISTEN = { ''' + ", ".join(f'{t} = {{ ' + ", ".join(f'["{n}"] = true' for n in listens(t)) + " }" for t in DRUM_TYPES) + ''' }
local ACT = {}; for i, t in ipairs(TYPES) do ACT[t] = i - 1 end
-- which sound each drum plays (perc slots choose: ockm-<slot>-synth 0, 1, 2)
local SOUND_TYPE = { [0] = "kick", [1] = "snare", [2] = "clap", [4] = "hat", [5] = "hat", [6] = "tom" }
local PERC = { [3] = { "rim", "conga", "shaker" }, [7] = { "conga", "shaker", "rim" } }
-- what the slot's tune moves (times 2^(tune/12)) and what its decay stretches (times decay/100)
local TUNE = { kick = { "pitch" }, tom = { "pitch" }, conga = { "pitch" }, rim = { "pitch" }, snare = { "pitch", "wires" },
               hat = { "pitch", "tone" }, clap = { "toneA", "toneB", "tailtone" }, shaker = { "tone" } }
local STRETCH = { kick = { "decay" }, tom = { "decay" }, conga = { "decay" }, rim = { "decay" }, snare = { "bodydec", "wdecay" },
                  hat = { "closed", "open" }, clap = { "tail" }, shaker = { "decay" } }
''' + PLAY_LUA + '''
-- a repeatable random sequence from a seed, so a saved seed always gives the same sound
local function rng(seed)
  local s = math.floor(seed) % 2147483647; if s <= 0 then s = s + 2147483646 end
  return function() s = (s * 16807) % 2147483647; return (s - 1) / 2147483646 end
end

function labdrum:initialize(sel, atoms)
  self.inlets, self.outlets = 1, 0
  self.slot = tostring(atoms[1] or "d1")
  self.s = { sound = 0, sample = 0, synth = 0, tune = 0, decay = 100, level = 1, labchar = 0, labmorph = 0, labrseed = 0, labramt = 0, labpseed = 1 }
  self.sent = {}
  return true
end

function labdrum:postinitialize()
  self.recv = {}
  for k in pairs(self.s) do
    local m = "r_" .. k
    self[m] = function(o, sel, a) local x = tonumber(a[1]); if x then o.s[k] = x; o:update() end end
    self.recv[#self.recv + 1] = pd.Receive:new():register(self, "ockm-" .. self.slot .. "-" .. k, m)
  end
  -- once loading is done (the voices' own loadbangs have run), send everything again
  self.clock = pd.Clock:new():register(self, "resend")
  self.clock:delay(0)
end
function labdrum:resend() self.sent = {}; self.act = nil; self:update() end
function labdrum:finalize()
  for _, r in ipairs(self.recv or {}) do r:destruct() end
  if self.clock then self.clock:destruct() end
end

function labdrum:kind()
  local snd = math.floor(self.s.sound)
  if PERC[snd] then return PERC[snd][math.max(0, math.min(2, math.floor(self.s.synth))) + 1] end
  return SOUND_TYPE[snd] or "kick"
end

-- the settings this slot's sound plays with
function labdrum:settings(t)
  local k, s = KIT[t], self.s
  local v = {}
  for _, p in ipairs(k.params) do v[p[1]] = p[4] end
  if s.labrseed > 0 and s.labramt > 0 then
    local r = rng(s.labrseed)
    for _, p in ipairs(k.params) do
      local name, lo, hi = p[1], p[2], p[3]
      local u = r()
      if name ~= "level" then
        if s.labramt >= 1 then v[name] = lo + u * (hi - lo) else v[name] = v[name] + (u * 2 - 1) * s.labramt * (hi - lo) end
      end
    end
  end
  local ch = CHARACTER[t]
  local m = math.max(0, math.min(1, s.labmorph))
  local pts
  if m > 0 then
    local r = rng(s.labpseed * 7919 + ACT[t] + 1)
    pts = { {} }
    for _, p in ipairs(k.params) do pts[1][p[1]] = 0 end
    for j = 2, MORPH_POINTS + 1 do
      pts[j] = {}
      for _, p in ipairs(k.params) do pts[j][p[1]] = (r() * 2 - 1) * (MORPH_SCALE[p[1]] or 0.45) * (p[3] - p[2]) * math.min(1, j / 2.5) end
    end
  end
  for _, p in ipairs(k.params) do
    local name, lo, hi = p[1], p[2], p[3]
    local x = v[name]
    if ch and ch.w[name] then x = x + s.labchar * ch.w[name] * (hi - lo) end
    if pts then
      local pos = math.min(m, 0.9999) * MORPH_POINTS; local i = math.floor(pos); local f = pos - i; f = f * f * (3 - 2 * f)
      x = x + pts[i + 1][name] * (1 - f) + pts[i + 2][name] * f
    end
    x = math.max(lo, math.min(hi, x))
    if name == "bursts" then x = math.floor(x + 0.5) end
    v[name] = x
  end
  for _, n in ipairs(TUNE[t] or {}) do v[n] = v[n] * 2 ^ (s.tune / 12) end
  for _, n in ipairs(STRETCH[t] or {}) do v[n] = v[n] * s.decay / 100 end
  v.level = v.level * s.level
  return v
end

-- switch on the right voice (or the sample player) and send it its settings (only the ones that changed)
function labdrum:update()
  local t = self:kind()
  local act = (self.s.sample > 0) and 8 or ACT[t]
  if act ~= self.act then
    self.act = act
    pd.send("ockm-" .. self.slot .. "-labact", "float", { act })
    self.sent = {}
  end
  if act == 8 then return end
  self.t, self.v = t, self:settings(t)
  local pre = "ockm-" .. self.slot .. "-" .. t
  for name, x in pairs(self.v) do
    if LISTEN[t][name] and self.sent[name] ~= x then self.sent[name] = x; pd.send(pre .. "-" .. name, "float", { x }) end
  end
end

-- a hit (0 to 1)
function labdrum:in_1_float(vel)
  if vel <= 0 or self.act == 8 or not self.v then return end
  local var = (self.t == "hat" and math.floor(self.s.sound) == 5) and 2 or 1
  play_voice("ockm-" .. self.slot .. "-" .. self.t, self.t, self.v, var, math.min(1, vel), KIT[self.t])
end
''')
