"""OCKM_GENERATOR front panel (seq/ockm-panel.pd).

Minimal modern style: flat, one accent colour, lots of space. Light and dark themes.
The panel only talks to the rest of the patch through the named ockm-* hooks,
so it can be replaced by the touchscreen UI later without touching the engine.

Pd shows no comments on a front panel, so every word you see is the label of a
control or of a tiny canvas.
"""

THEMES = {
    "dark":  dict(BG="#141414", CARD="#1e1e1e", OFF="#2a2a2a", ON="#ededed", ACC="#ff5a24", MUTE="#7a7a7a", TXT="#ededed"),
    "light": dict(BG="#f4f3ef", CARD="#ffffff", OFF="#e4e2dc", ON="#1a1a1a", ACC="#ff4f1a", MUTE="#9a9890", TXT="#1a1a1a"),
}


def build_panel(P, D, save_dir_save, SLOTS, SLOTN, show, theme="dark"):
    c = THEMES[theme]
    BG, CARD, OFF, ON, ACC, MUTE, TXT = (c[k] for k in ("BG", "CARD", "OFF", "ON", "ACC", "MUTE", "TXT"))
    PW, PH = 1100, 800
    q = P()

    def esc(t): return t.replace(" ", "\\ ") if t else "empty"

    def lab(x, y, t, col=None, size=11):
        """a word or phrase on the panel: the label of a 1-pixel canvas"""
        return q.add(f"#X obj {x} {y} cnv 1 1 1 empty empty {esc(t)} 0 6 0 {size} {BG} {col or MUTE} 0;")

    def card(x, y, w, h):
        return q.add(f"#X obj {x} {y} cnv 1 {w} {h} empty empty empty 0 0 0 10 {CARD} {MUTE} 0;")

    def hsl(x, y, w, lo, hi, send, recv, label="", h=14):
        return q.add(f"#X obj {x} {y} hsl {w} {h} {lo} {hi} 0 0 {send} {recv} {esc(label)} 0 -9 0 10 {OFF} {ACC} {MUTE} 0 1;")

    def hrad(x, y, size, n, send, recv, label="", fg=None):
        return q.add(f"#X obj {x} {y} hradio {size} 1 0 {n} {send} {recv} {esc(label)} 0 -9 0 10 {OFF} {fg or ON} {MUTE} 0;")

    def tgl(x, y, size, send, recv, label=""):
        return q.add(f"#X obj {x} {y} tgl {size} 0 {send} {recv} {esc(label)} {size+6} {size//2} 0 11 {OFF} {ACC} {MUTE} 0 1;")

    def bng(x, y, size, send, label=""):
        return q.add(f"#X obj {x} {y} bng {size} 250 50 0 {send} empty {esc(label)} {size+6} {size//2} 0 11 {OFF} {ACC} {MUTE};")

    def nbx(x, y, digits, h, lo, hi, send, recv, size=11, label=""):
        return q.add(f"#X obj {x} {y} nbx {digits} {h} {lo} {hi} 0 0 {send} {recv} {esc(label)} 0 -9 0 {size} {OFF} {TXT} {MUTE} 0 256;")

    def labels_under(x, y, size, names):
        for i, n in enumerate(names):
            lab(x + i * size + 2, y, n, size=10)

    # ---------- background ----------
    q.add(f"#X obj 0 0 cnv 1 {PW} {PH} empty empty empty 0 0 0 10 {BG} {MUTE} 0;")

    # ---------- top bar ----------
    tgl(20, 18, 34, "ockm-play", "ockm-ui-playing")
    nbx(74, 18, 3, 34, 40, 200, "ockm-bpm", "ockm-show-bpm", size=24)
    lab(148, 34, "bpm")
    hsl(200, 28, 100, 50, 75, "ockm-swing", "ockm-show-swing", "swing")
    hsl(320, 28, 80, 0, 1, "ockm-accent", "ockm-show-accent", "accent amount")
    lab(430, 8, "pattern")
    hrad(430, 22, 26, SLOTN, "ockm-want", "ockm-ui-slot")
    labels_under(436, 56, 26, [str(i + 1) for i in range(SLOTN)])
    bng(660, 22, 26, "ockm-save", "save")
    bng(740, 22, 26, "ockm-revert", "revert")
    lab(830, 8, "length")
    hrad(830, 22, 26, 4, "ockm-ui-len", "ockm-ui-lenset")
    for i, n in enumerate(["16", "32", "64", "128"]):
        lab(832 + i * 26, 56, n, size=9)
    lab(960, 8, "page")
    hrad(960, 22, 16, 8, "ockm-page", "ockm-ui-pageset")
    labels_under(960, 44, 16, [str(i + 1) for i in range(8)])

    # play state, pattern and length shown back on the panel
    rp = q.add(f"#X obj 20 {PH+20} r ockm-playing;"); mp = q.add(f"#X msg 20 {PH+45} set {D}1;"); sp = q.add(f"#X obj 20 {PH+70} s ockm-ui-playing;")
    q.con(rp, 0, mp, 0); q.con(mp, 0, sp, 0)
    rld = q.add(f"#X obj 120 {PH+20} r ockm-load;"); mld = q.add(f"#X msg 120 {PH+45} set {D}1;"); sld = q.add(f"#X obj 120 {PH+70} s ockm-ui-slot;")
    q.con(rld, 0, mld, 0); q.con(mld, 0, sld, 0)
    rl = q.add(f"#X obj 220 {PH+20} r ockm-ui-len;"); lx = q.add(f"#X obj 220 {PH+45} expr 16*pow(2\\, {D}f1);"); sl = q.add(f"#X obj 220 {PH+70} s ockm-length;")
    q.con(rl, 0, lx, 0); q.con(lx, 0, sl, 0)
    rl2 = q.add(f"#X obj 400 {PH+20} r ockm-len;"); lg = q.add(f"#X obj 400 {PH+45} expr int(log({D}f1/16)/log(2)+0.5);")
    mr = q.add(f"#X msg 400 {PH+70} set {D}1;"); sr = q.add(f"#X obj 400 {PH+95} s ockm-ui-lenset;")
    for a in [(rl2, 0, lg, 0), (lg, 0, mr, 0), (mr, 0, sr, 0)]: q.con(*a)
    rpg = q.add(f"#X obj 600 {PH+20} r ockm-page;"); mpg = q.add(f"#X msg 600 {PH+45} set {D}1;"); spg = q.add(f"#X obj 600 {PH+70} s ockm-ui-pageset;")
    q.con(rpg, 0, mpg, 0); q.con(mpg, 0, spg, 0)

    # ---------- drum grid ----------
    GX, GY, SQ = 170, 110, 30
    lab(20, 84, "drums", TXT, 13)
    lab(40, 100, "sound", size=9)
    tgl(GX + 16 * SQ - 140, 84, 14, "ockm-ui-accmode", "empty", "tap adds accent")
    # playhead: 16 thin bars over the grid, the current one lit
    for i in range(16):
        q.add(f"#X obj {GX + i*SQ} {GY - 8} cnv 1 {SQ-6} 3 empty ockm-ui-ph-{i} empty 0 0 0 10 {OFF} {MUTE} 0;")
    # beat markers under the grid
    for b in range(4):
        q.add(f"#X obj {GX + b*4*SQ} {GY + 8*(SQ+4) + 2} cnv 1 {4*SQ-6} 1 empty empty empty 0 0 0 10 {OFF} {MUTE} 0;")
    page = q.add(f"#X obj 800 {PH+20} r ockm-page;"); pm = q.add(f"#X obj 800 {PH+45} * 16;")
    q.con(page, 0, pm, 0)
    rst = q.add(f"#X obj 1000 {PH+20} r ockm-step;"); phx = q.add(f"#X obj 1000 {PH+45} -;"); q.con(pm, 0, phx, 1)
    tfb = q.add(f"#X obj 1000 {PH+70} t f b;")
    prev = q.add(f"#X obj 1100 {PH+95} f 0;"); tpv = q.add(f"#X obj 1100 {PH+120} t b f;")
    mkp = q.add(f"#X obj 1150 {PH+145} makefilename ockm-ui-ph-%d;"); offc = q.add(f"#X msg 1100 {PH+170} color {OFF} {MUTE} {MUTE};")
    snp = q.add(f"#X obj 1100 {PH+195} send;")
    mo1 = q.add(f"#X obj 1000 {PH+95} moses 0;"); mo2 = q.add(f"#X obj 1040 {PH+120} moses 16;")
    tbf = q.add(f"#X obj 1040 {PH+145} t b f f;"); mkn = q.add(f"#X obj 1060 {PH+170} makefilename ockm-ui-ph-%d;")
    onc = q.add(f"#X msg 1040 {PH+195} color {ACC} {MUTE} {MUTE};"); snn = q.add(f"#X obj 1040 {PH+220} send;")
    for a in [(rst, 0, phx, 0), (phx, 0, tfb, 0), (tfb, 1, prev, 0), (prev, 0, tpv, 0), (tpv, 1, mkp, 0), (mkp, 0, snp, 1),
              (tpv, 0, offc, 0), (offc, 0, snp, 0), (tfb, 0, mo1, 0), (mo1, 1, mo2, 0), (mo2, 0, tbf, 0),
              (tbf, 2, prev, 1), (tbf, 1, mkn, 0), (mkn, 0, snn, 1), (tbf, 0, onc, 0), (onc, 0, snn, 0)]:
        q.con(*a)
    racc = q.add(f"#X obj 600 {PH+120} r ockm-ui-accmode;")
    # redraw every square on load, page change, edits and extends
    rr = [q.add(f"#X obj {1200+i*130} {PH+20} r {n};") for i, n in enumerate(["ockm-refresh", "ockm-page", "ockm-edit", "ockm-extend"])]
    dl = q.add(f"#X obj 1200 {PH+50} delay 0;")
    tb_ = q.add(f"#X obj 1200 {PH+35} t b;")   # edits arrive as 'd1 4 2': turn anything into a bang
    for r in rr: q.con(r, 0, tb_, 0)
    q.con(tb_, 0, dl, 0)
    for ri, (nm, _) in enumerate(SLOTS):
        y = GY + ri * (SQ + 4)
        lab(20, y + 9, str(ri + 1), TXT, 12)
        hrad(40, y + 7, 14, 8, f"ockm-{nm}-sound", show(f"ockm-{nm}-sound"))
        bx = 1400 + ri * 260
        ux = q.add(f"#X obj {bx} {PH+300} unpack f f;"); fv = q.add(f"#X obj {bx+60} {PH+330} expr {D}f1*(1+{D}f2);")
        ad = q.add(f"#X obj {bx} {PH+360} + 0;"); pk = q.add(f"#X obj {bx} {PH+390} pack 0 0;")
        lp = q.add(f"#X obj {bx} {PH+420} list prepend {nm};"); lt = q.add(f"#X obj {bx} {PH+450} list trim;"); se = q.add(f"#X obj {bx} {PH+480} s ockm-edit;")
        for a in [(ux, 1, fv, 0), (racc, 0, fv, 1), (fv, 0, pk, 1), (ux, 0, ad, 0), (pm, 0, ad, 1), (ad, 0, pk, 0), (pk, 0, lp, 0), (lp, 0, lt, 0), (lt, 0, se, 0)]:
            q.con(*a)
        for i in range(16):
            t = q.add(f"#X obj {GX + i*SQ} {y} tgl {SQ-6} 0 empty ockm-ui-{nm}-{i} empty 0 0 0 10 {OFF} {OFF} {MUTE} 0 1;")
            m = q.add(f"#X msg {bx + (i%4)*60} {PH+200 + (i//4)*22} {i} {D}1;")
            q.con(t, 0, m, 0); q.con(m, 0, ux, 0)
        # redraw this row: grey = empty, solid = hit, accent colour = accented hit
        yy = PH + 80 + ri * 130
        tb = q.add(f"#X obj 1200 {yy} t b b;"); z = q.add(f"#X msg 1260 {yy+20} 0;"); n16 = q.add(f"#X msg 1200 {yy+20} 16;")
        un = q.add(f"#X obj 1200 {yy+40} until;"); cf = q.add(f"#X obj 1200 {yy+60} f;"); cp = q.add(f"#X obj 1250 {yy+60} + 1;")
        tf = q.add(f"#X obj 1200 {yy+80} t f f;"); mk = q.add(f"#X obj 1300 {yy+80} makefilename ockm-ui-{nm}-%d;")
        of = q.add(f"#X obj 1200 {yy+95} + 0;"); rd = q.add(f"#X obj 1200 {yy+105} tabread ockm-pat-{nm};")
        cm = q.add(f"#X obj 1200 {yy+115} expr ({D}f1>0)+({D}f1>1) \\; {D}f1>0;")
        setm = q.add(f"#X msg 1360 {yy+115} set {D}1;"); sn = q.add(f"#X obj 1200 {yy+125} send;")
        sel = q.add(f"#X obj 1250 {yy+100} sel 0 1 2;")
        c0 = q.add(f"#X msg 1250 {yy+125} color {OFF} {OFF} {MUTE};")
        c1 = q.add(f"#X msg 1400 {yy+125} color {ON} {ON} {MUTE};")
        c2 = q.add(f"#X msg 1550 {yy+125} color {ACC} {ACC} {MUTE};")
        for a in [(dl, 0, tb, 0), (tb, 1, z, 0), (z, 0, cf, 1), (tb, 0, n16, 0), (n16, 0, un, 0), (un, 0, cf, 0), (cf, 0, cp, 0), (cp, 0, cf, 1), (cf, 0, tf, 0),
                  (tf, 1, mk, 0), (mk, 0, sn, 1), (tf, 0, of, 0), (pm, 0, of, 1), (of, 0, rd, 0), (rd, 0, cm, 0), (cm, 1, setm, 0), (setm, 0, sn, 0),
                  (cm, 0, sel, 0), (sel, 0, c0, 0), (sel, 1, c1, 0), (sel, 2, c2, 0), (c0, 0, sn, 0), (c1, 0, sn, 0), (c2, 0, sn, 0)]:
            q.con(*a)
        # slot strip: level, tune, decay, reverb and delay sends
        x0 = GX + 16 * SQ + 20
        for j, (param, lo, hi, nice) in enumerate([("level", 0, 1, "level"), ("tune", -12, 12, "tune"), ("decay", 10, 400, "decay"), ("verb", 0, 1, "reverb"), ("delay", 0, 1, "delay")]):
            hsl(x0 + j * 84, y + 9, 70, lo, hi, f"ockm-{nm}-{param}", show(f"ockm-{nm}-{param}"), nice if ri == 0 else "", h=10)
    lab(GX, GY + 8 * (SQ + 4) + 10, "sound: kick snare clap rim hat open-hat tom rimshot", size=10)

    # ---------- synths ----------
    SY = 420
    lab(20, SY, "key", TXT, 13)
    hrad(70, SY - 4, 22, 12, "ockm-root", show("ockm-root"))
    labels_under(70, SY + 22, 22, ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])
    lab(370, SY, "scale", TXT, 13)
    hrad(430, SY - 4, 22, 6, "ockm-scale", show("ockm-scale"))
    labels_under(430, SY + 22, 22, ["min", "maj", "dor", "phr", "mix", "hm"])
    SECT = [("bass", ["acid", "sub", "fm", "reese", "pluck", "saw"], 12, "rhythm", "notes"),
            ("lead", ["acid", "sub", "fm", "reese", "pluck", "saw"], 12, "rhythm", "notes"),
            ("chord", ["stab", "organ", "pad"], 10, "rhythm", "prog")]
    for si, (t, engs, nsecond, g1, g2) in enumerate(SECT):
        x = 20 + si * 360; y = SY + 50
        card(x, y, 340, 262)
        x += 14; y += 12
        lab(x, y + 4, t, TXT, 14)
        hrad(x + 60, y, 30, len(engs), f"ockm-{t}-engine", show(f"ockm-{t}-engine"))
        for i, n in enumerate(engs):
            lab(x + 61 + i * 30, y + 38, n, size=9)
        for k in range(4):
            hsl(x, y + 62 + k * 30, 150, 0, 1, f"ockm-{t}-k{k+1}", show(f"ockm-{t}-k{k+1}"), f"k{k+1}")
        if t != "chord":
            hsl(x + 180, y + 62, 130, 0, 1, f"ockm-{t}-drive", show(f"ockm-{t}-drive"), "drive")
        else:
            hrad(x + 180, y + 56, 17, 8, "ockm-chord-type", show("ockm-chord-type"), "type")
            labels_under(x + 180, y + 76, 17, ["tri", "7", "s2", "pw", "s4", "6", "9", "11"])
            tgl(x + 180, y + 96, 14, "ockm-chord-smooth", show("ockm-chord-smooth"), "smooth")
        hsl(x + 180, y + 122, 130, 0, 1, f"ockm-{t}-verb", show(f"ockm-{t}-verb"), "reverb")
        hsl(x + 180, y + 152, 130, 0, 1, f"ockm-{t}-delay", show(f"ockm-{t}-delay"), "delay")
        hrad(x, y + 192, 16 if t != "chord" else 14, 8 if t != "chord" else 10, f"ockm-{t}-{g1}", show(f"ockm-{t}-{g1}"), g1)
        hrad(x, y + 226, 14 if nsecond <= 12 else 13, nsecond, f"ockm-{t}-{g2}", show(f"ockm-{t}-{g2}"), g2)
        bng(x + 240, y + 200, 24, f"ockm-{t}-gen", "new")

    # ---------- effects and sync ----------
    FY = 760
    lab(20, FY - 4, "effects", TXT, 13)
    for j, (labt, lo, hi, hook) in enumerate([("filter", -1, 1, "ockm-filter"), ("drive", 0, 1, "ockm-drive"), ("delay", 0, 1, "ockm-delay-mix"),
                                              ("feedback", 0, 0.9, "ockm-delay-fb"), ("reverb", 0, 1, "ockm-verb-mix"), ("size", 0, 1, "ockm-verb-size"),
                                              ("tone", 0, 1, "ockm-verb-tone")]):
        hsl(100 + j * 105, FY, 90, lo, hi, hook, show(hook), labt)
    nbx(850, FY - 2, 2, 18, 1, 8, "ockm-delay-steps", show("ockm-delay-steps"), label="delay steps")
    tgl(920, FY - 2, 18, "ockm-sync", show("ockm-sync"), "follow")
    tgl(1010, FY - 2, 18, "ockm-clock-out", show("ockm-clock-out"), "clock")

    q.L.append(f"#X coords 0 -1 1 1 {PW} {PH} 1 0 0;")
    save_dir_save(q, "seq/ockm-panel.pd", f"#N canvas 20 20 {PW+40} {PH+40} 12;")
    return PW, PH
