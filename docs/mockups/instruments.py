#!/usr/bin/env python3
"""Mock-ups for the instruments (v1.39 idea): the start screen, Bass and Analog. 960x600, Core Grey dark.
python3 docs/mockups/instruments.py  -> docs/mockups/inst-*.png"""
import os, math
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))
C = dict(bg="#2A2A28", card="#363634", off="#444442", on="#C2C2BE", acc="#C43732", accfg="#FFFFFF", mute="#B0B0AA", txt="#E8E8E4", dim="#5C5C58")
W, H = 960, 600


def font(sz, bold=False):
    f = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(f, sz)


class S:
    def __init__(s):
        s.im = Image.new("RGB", (W, H), C["bg"]); s.d = ImageDraw.Draw(s.im)

    def rr(s, x, y, w, h, col, r=6, outline=None, width=2):
        s.d.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=C.get(col, col), outline=C.get(outline, outline) if outline else None, width=width)

    def t(s, txt, x, y, sz=12, col="mute", bold=False, anchor="la"):
        s.d.text((x, y), txt, fill=C.get(col, col), font=font(sz, bold), anchor=anchor)

    def ct(s, txt, x, y, w, h, sz=13, col="txt", bold=False):
        s.d.text((x + w / 2, y + h / 2), txt, fill=C.get(col, col), font=font(sz, bold), anchor="mm")

    def btn(s, x, y, w, h, label, sel=False, live=False, sz=13):
        s.rr(x, y, w, h, "acc" if live else ("on" if sel else "off"))
        s.ct(label, x, y, w, h, sz, "accfg" if live else ("bg" if sel else "txt"))

    def knob(s, cx, cy, r, v, label, val="", big=False):
        # a ring: the track in dim, the value in the strong grey, a dot at the end
        a0, a1 = 135, 405
        s.d.arc([cx - r, cy - r, cx + r, cy + r], a0, a1, fill=C["dim"], width=6 if big else 5)
        s.d.arc([cx - r, cy - r, cx + r, cy + r], a0, a0 + (a1 - a0) * v, fill=C["on"], width=6 if big else 5)
        ang = math.radians(a0 + (a1 - a0) * v)
        px, py = cx + (r - 1) * math.cos(ang), cy + (r - 1) * math.sin(ang)
        s.d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=C["txt"])
        if val: s.t(val, cx, cy, 13 if big else 11, "txt", anchor="mm")
        s.t(label, cx, cy + r + 12, 12 if big else 11, "mute", anchor="mm")

    def card(s, x, y, w, h, title):
        s.rr(x, y, w, h, "card", 10)
        s.t(title, x + 12, y + 9, 12, "mute", True)

    def top(s, name, tabs, cur):
        # home (back to the start screen), play, tempo, the instrument's own tabs, save and menu: as the groovebox
        s.rr(16, 12, 52, 48, "off")
        # a little house
        s.d.polygon([(30, 38), (42, 26), (54, 38)], fill=C["txt"]); s.d.rectangle([34, 38, 50, 48], fill=C["txt"])
        s.rr(76, 12, 64, 48, "off"); s.d.polygon([(100, 25), (118, 36), (100, 47)], fill=C["txt"])
        s.t("124", 150, 14, 32, "txt"); s.t("bpm", 211, 40, 12, "mute"); s.t(name, 211, 18, 11, "txt", True)
        x = 270
        for lab, w in tabs:
            s.rr(x, 12, w, 48, "on" if lab == cur else "off"); s.ct(lab, x, 12, w, 48, 12, "bg" if lab == cur else "txt"); x += w + 4
        s.rr(W - 120, 12, 50, 48, "off"); s.rr(W - 66, 12, 50, 48, "off")
        cx = W - 95
        s.d.rounded_rectangle([cx - 11, 25, cx + 11, 47], radius=3, outline=C["txt"], width=2); s.d.rectangle([cx - 6, 25, cx + 6, 32], fill=C["txt"]); s.d.rectangle([cx - 7, 39, cx + 7, 45], fill=C["txt"])
        for j in (-1, 0, 1): s.d.rectangle([W - 52, 35 + j * 7, W - 30, 37 + j * 7], fill=C["txt"])

    def steps(s, y, notes, acc, slide, play=4, h=70, label_top=None):
        pitch = (W - 32) / 16
        for i in range(16):
            x = 16 + i * pitch + 3; w = pitch - 6
            n = notes[i]
            s.rr(x, y, w, h, "on" if n else "off")
            if n:
                s.ct(n, x, y, w, h - 14, 15, "bg", True)
                if acc[i]: s.rr(x + 6, y + h - 12, w - 12, 4, "acc", 2)
                if slide[i]: s.d.line([x + w - 4, y + h / 2, x + w + 10, y + h / 2], fill=C["acc"], width=3)
            if i % 4 == 0: s.d.rectangle([x, y + h + 5, x + w, y + h + 6], fill=C["mute"])
        x = 16 + play * pitch + 3
        s.d.rectangle([x, y + h + 3, x + pitch - 6, y + h + 7], fill=C["acc"])

    def save(s, name):
        s.im.save(os.path.join(OUT, name)); print("wrote", name)


def start():
    s = S()
    s.t("OCKM", 24, 22, 26, "txt", True); s.t("pick an instrument", 24, 56, 13, "mute")
    s.t("v1.39", W - 24, 30, 11, "mute", anchor="ra")
    tiles = [
        ("groovebox", "patterns, parts, perform, arrange", "grid"),
        ("bass", "big modern bass: swarm, sub, pitch zaps, acid", "saw"),
        ("analog", "classic mono: pulse, LFO, arp, chords", "pulse"),
        ("drmz", "drum machine: eight voices, sixteen steps", "drums"),
    ]
    tw, th, gx, gy = (W - 48 - 16) / 2, 220, 16, 96
    for i, (name, sub, icon) in enumerate(tiles):
        x = 24 + (i % 2) * (tw + 16); y = gy + (i // 2) * (th + 16)
        last = (name == "bass")
        s.rr(x, y, tw, th, "card", 14, outline="acc" if last else None, width=2)
        s.t(name, x + 24, y + th - 74, 30, "txt", True)
        s.t(sub, x + 24, y + th - 32, 13, "mute")
        ix, iy, iw, ih = x + 24, y + 24, tw - 48, 80
        if icon == "grid":
            for r in range(4):
                for c in range(16):
                    on = (c % 4 == 0) if r == 0 else ((c + r) % 3 == 0)
                    s.rr(ix + c * (iw / 16), iy + r * 20, iw / 16 - 4, 16, "on" if on else "off", 3)
        elif icon == "saw":
            pts = []
            for k in range(5):
                x0 = ix + k * iw / 5
                pts += [(x0, iy + ih), (x0 + iw / 5, iy)]
            s.d.line(pts, fill=C["on"], width=4)
            s.d.line([(p[0], p[1] + 10) for p in pts], fill=C["dim"], width=3)
        elif icon == "pulse":
            pts = []; xx = ix
            for k in range(5):
                wv = iw / 5
                pts += [(xx, iy + ih), (xx, iy), (xx + wv * (0.25 + 0.12 * k), iy), (xx + wv * (0.25 + 0.12 * k), iy + ih), (xx + wv, iy + ih)]
                xx += wv
            s.d.line(pts, fill=C["on"], width=4)
        else:
            for c in range(8):
                hh = [80, 34, 60, 24, 70, 30, 52, 40][c]
                s.rr(ix + c * (iw / 8), iy + ih - hh, iw / 8 - 10, hh, "on", 4)
        if last: s.t("last used", x + tw - 24, y + th - 74, 11, "acc", anchor="ra")
    s.t("hold the house button on any instrument to come back here", W / 2, H - 22, 12, "mute", anchor="mm")
    s.save("inst-start.png")


def bass():
    s = S()
    s.top("BASS", [("perform", 84), ("steps", 70), ("sounds", 76)], "perform")
    # 4 cards: osc, filter, envelopes, mod. Big knobs for the four that matter most
    y, h = 76, 300
    cards = [(16, 236, "OSCILLATOR"), (260, 236, "FILTER"), (504, 216, "ENVELOPES"), (728, 216, "MOD + DRIVE")]
    for x, w, title in cards: s.card(x, y, w, h, title)
    # oscillator
    s.btn(28, 104, 66, 32, "saw", True, sz=12); s.btn(98, 104, 66, 32, "square", sz=12); s.btn(168, 104, 72, 32, "both", sz=12)
    s.knob(134, 200, 42, 0.62, "swarm", "62", big=True)
    s.knob(66, 316, 26, 0.7, "sub", "70"); s.knob(134, 316, 26, 0.15, "noise", "15"); s.knob(202, 316, 26, 0.5, "tune", "0")
    # filter
    s.btn(272, 104, 104, 32, "low-pass", True, sz=12); s.btn(380, 104, 104, 32, "band-pass", sz=12)
    s.knob(332, 200, 42, 0.38, "cutoff", "38", big=True); s.knob(432, 200, 42, 0.72, "resonance", "72", big=True)
    s.knob(310, 316, 26, 0.55, "env", "55"); s.knob(378, 316, 26, 0.8, "accent", "80"); s.knob(446, 316, 26, 0.3, "key", "30")
    # envelopes: amp, filter, pitch
    for j, (lab, v) in enumerate([("amp", 0.45), ("filter", 0.3), ("pitch", 0.2)]):
        cx = 552 + j * 60
        s.knob(cx, 150, 24, v, "decay", f"{int(v*100)}"); s.t(lab, cx, 108, 11, "txt", True, anchor="mm")
    s.knob(582, 262, 26, 0.6, "pitch amt", "+12"); s.knob(658, 262, 26, 0.1, "attack", "10")
    s.btn(516, 330, 92, 32, "gate", sz=12); s.btn(612, 330, 96, 32, "decay", True, sz=12)
    # mod + drive
    s.knob(776, 150, 26, 0.5, "lfo rate", "1/8"); s.knob(888, 150, 26, 0.0, "lfo amt", "0")
    s.btn(740, 196, 62, 30, "filter", True, sz=11); s.btn(806, 196, 62, 30, "FM", sz=11); s.btn(872, 196, 60, 30, "pitch", sz=11)
    s.knob(800, 290, 34, 0.66, "drive", "66", big=False); s.knob(890, 290, 26, 0.35, "glide", "35")
    # bottom: preset strip and the sequencer, live
    s.rr(16, 388, 220, 40, "off"); s.ct("< 07 rubber acid >", 16, 388, 220, 40, 13)
    s.btn(244, 388, 90, 40, "random", sz=12); s.btn(338, 388, 92, 40, "save", sz=12)
    s.t("swarm: a chorus of detuned copies, for wide basses. pitch zaps from the pitch envelope", 444, 402, 11, "mute")
    notes = ["A1", "A1", "", "A2", "A1", "", "C2", "", "A1", "G1", "", "A1", "E2", "", "A1", "D2"]
    acc = [1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]; sl = [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0]
    s.steps(446, notes, acc, sl, play=4, h=78)
    s.t("every control for the sound is on this one page. the steps tab has the sequencer and the generator", 16, 548, 11, "mute")
    s.save("inst-bass.png")


def analog():
    s = S()
    s.top("ANALOG", [("perform", 84), ("steps", 70), ("sounds", 76)], "perform")
    y, h = 76, 300
    cards = [(16, 264, "OSCILLATOR"), (288, 220, "FILTER"), (516, 240, "ENVELOPE"), (764, 180, "LFO")]
    for x, w, title in cards: s.card(x, y, w, h, title)
    # oscillator: the mixer as four sliders, then pulse width
    for j, (lab, v) in enumerate([("pulse", 0.8), ("saw", 0.45), ("sub", 0.6), ("noise", 0.05)]):
        x = 32 + j * 40
        s.rr(x, 110, 22, 150, "off", 4); s.rr(x, 110 + 150 * (1 - v), 22, 150 * v, "on", 4); s.t(lab, x + 11, 274, 11, "mute", anchor="mm")
    s.knob(228, 148, 30, 0.3, "width", "30"); s.knob(228, 240, 30, 0.45, "PWM", "45")
    s.btn(28, 300, 74, 30, "-1 oct", True, sz=11); s.btn(106, 300, 74, 30, "-2 oct", sz=11); s.btn(184, 300, 84, 30, "-2 pulse", sz=11)
    s.t("sub", 30, 340, 10, "mute")
    # filter
    s.knob(345, 180, 44, 0.42, "cutoff", "42", big=True); s.knob(450, 180, 32, 0.55, "resonance", "55")
    s.knob(320, 300, 26, 0.5, "env", "50"); s.knob(393, 300, 26, 0.25, "LFO", "25"); s.knob(466, 300, 26, 0.6, "key", "60")
    # envelope: ADSR sliders
    for j, (lab, v) in enumerate([("A", 0.05), ("D", 0.4), ("S", 0.6), ("R", 0.3)]):
        x = 534 + j * 48
        s.rr(x, 110, 26, 170, "off", 4); s.rr(x, 110 + 170 * (1 - v), 26, 170 * v, "on", 4); s.t(lab, x + 13, 292, 12, "txt", True, anchor="mm")
    s.btn(724 - 0, 110, 0, 0, "")
    s.btn(528, 320, 106, 34, "env", True, sz=12); s.btn(638, 320, 106, 34, "gate", sz=12)
    # lfo
    s.knob(854, 150, 32, 0.5, "rate", "1/8")
    for j, lab in enumerate(["tri", "square", "random", "noise"]):
        s.btn(776 + (j % 2) * 82, 214 + (j // 2) * 38, 78, 32, lab, sel=(lab == "random"), sz=11)
    s.knob(854, 320, 22, 0.2, "to pitch", "20")
    # bottom: play modes
    s.rr(16, 388, 220, 40, "off"); s.ct("< 12 blip lead >", 16, 388, 220, 40, 13)
    for j, (lab, sel) in enumerate([("mono", True), ("unison", False), ("chord", False), ("poly", False)]):
        s.btn(244 + j * 84, 388, 80, 40, lab, sel, sz=12)
    s.knob(610, 408, 18, 0.35, "", ""); s.t("glide", 636, 402, 12, "mute")
    for j, (lab, sel) in enumerate([("arp off", False), ("up", True), ("down", False), ("up/dn", False), ("random", False)]):
        s.btn(690 + j * 51, 388, 47, 40, lab, sel, sz=10)
    # a keyboard you can play
    kx, ky, kw, kh = 16, 446, W - 32, 128
    white = 22; ww = kw / white
    for i in range(white):
        lit = i in (7, 9, 11)
        s.rr(kx + i * ww + 1, ky, ww - 2, kh, "acc" if lit else "on", 4)
    for i in range(white - 1):
        if i % 7 in (2, 6): continue
        s.rr(kx + (i + 1) * ww - ww * 0.3, ky, ww * 0.6, kh * 0.6, "bg", 3)
    s.t("C3", kx + 7 * ww + 6, ky + kh - 20, 11, "accfg")
    s.save("inst-analog.png")


def bass_steps():
    s = S()
    s.top("BASS", [("perform", 84), ("steps", 70), ("sounds", 76)], "steps")
    # nav like the groovebox: bars, length, the generator's lock
    s.rr(16, 70, 44, 36, "off"); s.rr(64, 70, 104, 36, "off"); s.ct("1-16", 64, 70, 104, 36, 13); s.rr(172, 70, 44, 36, "off")
    s.t("pattern 4 bars", 236, 82, 11, "mute")
    for j, lab in enumerate(["1 bar", "2 bars", "4 bars", "8 bars", "16 bars"]):
        s.btn(586 + j * 56, 70, 52, 36, lab, sel=(lab == "4 bars"), sz=11)
    s.btn(W - 86, 70, 70, 36, "double", sz=12)
    notes = ["A1", "A1", "", "A2", "A1", "", "C2", "", "A1", "G1", "", "A1", "E2", "", "A1", "D2"]
    acc = [1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]; sl = [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0]
    s.steps(116, notes, acc, sl, play=6, h=84)
    # the selected step: note, octave, accent, slide (step 7)
    s.card(16, 220, 440, 166, "STEP 7")
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    for j, n in enumerate(names):
        s.btn(28 + (j % 6) * 70, 246 + (j // 6) * 42, 64, 36, n, sel=(n == "C"), sz=13)
    for j, (lab, sel, live) in enumerate([("oct -", False, False), ("oct +", False, False), ("accent", False, False), ("slide", True, True), ("rest", False, False)]):
        s.btn(28 + j * 84, 338, 80, 36, lab, sel and not live, live, sz=12)
    # the generator: style and a few big moves, follows the groovebox's key when it's running
    s.card(472, 220, 472, 166, "GENERATOR")
    for j, lab in enumerate(["acid", "rolling", "offbeat", "octaves", "sparse"]):
        s.btn(484 + j * 90, 246, 84, 36, lab, sel=(lab == "acid"), sz=12)
    s.knob(520, 330, 22, 0.6, "busy", "60"); s.knob(590, 330, 22, 0.4, "range", "1 oct"); s.knob(660, 330, 22, 0.5, "accent", "50"); s.knob(730, 330, 22, 0.3, "slide", "30")
    s.btn(780, 296, 76, 40, "new", live=True, sz=13); s.btn(860, 296, 76, 40, "mutate", sz=12)
    s.btn(780, 340, 156, 36, "A minor  >", sz=12)
    # bottom: the filter move per step (the DB-01's modulation track)
    s.card(16, 398, W - 32, 150, "FILTER MOVE PER STEP")
    pitch = (W - 48) / 16
    vals = [0.2, 0.25, 0.3, 0.6, 0.35, 0.4, 0.8, 0.45, 0.3, 0.35, 0.4, 0.5, 0.9, 0.55, 0.4, 0.7]
    for i, v in enumerate(vals):
        x = 24 + i * pitch + 3; w = pitch - 6
        s.rr(x, 424, w, 110, "off", 4); s.rr(x, 424 + 110 * (1 - v), w, 110 * v, "on", 4)
    s.t("drag across to draw a sweep. the generator can draw one too", 16, 560, 11, "mute")
    s.save("inst-bass-steps.png")


if __name__ == "__main__":
    start(); bass(); bass_steps(); analog()
