#!/usr/bin/env python3
"""Mock-ups for v1.49 (ideas from the PERF-1 firmware): the drum lane controls, call and answer on the bass tab, the mood
dial on Perform, and a "show" page with the sigil. Drawn over the real screens (tests/ui_preview.py), 960x600, dark.
python3 tests/ui_preview.py /tmp/prev dark ; python3 docs/mockups/v149.py /tmp/prev  -> docs/mockups/v149-*.png"""
import os, sys, math
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))
BASE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/prev"
C = dict(bg="#2A2A28", card="#363634", off="#444442", on="#C2C2BE", acc="#C43732", accfg="#FFFFFF", mute="#B0B0AA",
         txt="#E8E8E4", dim="#5C5C58", track="#4A4A47",
         drums="#E6DFC8", bass="#C43732", lead="#9BC53D", chord="#4FB3A9", samples="#D97BA6")


def font(sz, bold=False):
    f = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(f, sz)


class S:
    def __init__(s, base=None):
        s.im = Image.open(os.path.join(BASE, base)).convert("RGB") if base else Image.new("RGB", (960, 600), C["bg"])
        s.d = ImageDraw.Draw(s.im)

    def col(s, c): return C.get(c, c)

    def rr(s, x, y, w, h, c, r=6, outline=None, width=2):
        s.d.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=s.col(c), outline=s.col(outline) if outline else None, width=width)

    def t(s, txt, x, y, sz=12, c="mute", bold=False, anchor="la"):
        s.d.text((x, y), txt, fill=s.col(c), font=font(sz, bold), anchor=anchor)

    def btn(s, x, y, w, h, label, sel=False, sz=12, sub=None):
        s.rr(x, y, w, h, "on" if sel else "off")
        fg = "bg" if sel else "txt"
        if sub:
            s.t(label, x + w / 2, y + h / 2 - 7, sz, fg, anchor="mm"); s.t(sub, x + w / 2, y + h / 2 + 9, 10, fg, anchor="mm")
        else:
            s.t(label, x + w / 2, y + h / 2, sz, fg, anchor="mm")

    def slider(s, y, label, v, val, x0=126, x1=402):
        # as the drum page's level/tune rows: a label, a track, a red dot, the value
        s.t(label, 16, y, 13, "txt", anchor="lm")
        s.d.rounded_rectangle([x0, y - 4, x1, y + 4], radius=4, fill=s.col("track"))
        px = x0 + (x1 - x0) * v
        s.d.ellipse([px - 11, y - 11, px + 11, y + 11], fill=s.col("acc"))
        s.t(val, 416, y, 12, "txt", anchor="lm")

    def hbar(s, x, y, w, h, v, label, val=""):
        # the app's bar control: dark box, lighter fill, a red edge at the value
        s.rr(x, y, w, h, "off")
        fw = int(w * v)
        if fw > 0: s.d.rectangle([x, y, x + fw, y + h], fill=s.col("dim"))
        s.d.rectangle([x + fw - 2, y, x + fw + 2, y + h], fill=s.col("acc"))
        s.t(label, x + w / 2, y + h / 2 - (6 if val else 0), 12, "txt", anchor="mm")
        if val: s.t(val, x + w / 2, y + h / 2 + 9, 10, "txt", anchor="mm")

    def note(s, txt, x, y, w=300):
        # a mock-up callout: a red tag with a line of explanation
        s.rr(x, y, w, 22, "#5A1F1C", 5)
        s.t(txt, x + 8, y + 11, 11, "txt", anchor="lm")

    def save(s, name):
        s.im.save(os.path.join(OUT, f"v149-{name}.png")); print("wrote", name)


# ---- 1. drums, one drum: rolls in the lane row, and a "lane" tab beside the sound ----
s = S("drums-dark.png")
s.d.rectangle([12, 266, 480, 300], fill=s.col("bg"))
s.btn(16, 270, 84, 25, "velocity"); s.btn(106, 270, 84, 25, "timing"); s.btn(196, 270, 84, 25, "rolls", sel=True)
s.hbar(286, 270, 100, 25, 0.2, "swing")
s.d.rectangle([12, 298, 948, 340], fill=s.col("bg"))
rolls = {4: 2, 11: 3, 14: 2, 15: 4}
for i in range(16):
    x = 18 + i * 58
    n = rolls.get(i, 1)
    s.rr(x, 300, 54, 38, "on" if n > 1 else "off", 4)
    if n > 1:
        # the roll's hits as little bars, then the count
        for k in range(n):
            bx = x + 8 + k * (38 / n); s.d.rectangle([bx, 306, bx + 38 / n - 4, 320], fill=s.col("bg"))
        s.t(f"x{n}", x + 27, 329, 11, "bg", True, anchor="mm")
s.d.rectangle([10, 343, 482, 556], fill=s.col("bg"))
s.btn(16, 346, 140, 30, "sound"); s.btn(162, 346, 140, 30, "lane", sel=True)
s.slider(398, "chance", 0.8, "80%")
s.slider(428, "thin", 0.25, "16ths out")
s.slider(458, "drift", 0.4, "40%")
s.t("plays in", 16, 482, 11, "mute", anchor="lm")
for k, (lab, sel) in enumerate([("every bar", True), ("bars 1 + 3", False), ("bars 2 + 4", False), ("last of 4", False)]):
    s.btn(16 + k * 116, 492, 110, 28, lab, sel, 11)
for k, (lab, sel) in enumerate([("first of 4", False), ("fills only", False), ("not in fills", False)]):
    s.btn(16 + k * 116, 524, 110, 28, lab, sel, 11)
s.note("new: rolls (tap a step: 1, x2 .. x6)", 500, 268, 250)
s.note("new: the lane tab", 312, 350, 150)
s.save("drums-lane")

# ---- 2. bass: call and answer ----
s = S("bass-dark.png")
s.d.rectangle([150, 264, 542, 302], fill=s.col("bg"))
s.t("answer", 236, 283, 12, "mute", anchor="rm")
for k, (lab, sel) in enumerate([("off", False), ("2 bars", False), ("4 bars", True), ("8 bars", False)]):
    s.btn(246 + k * 74, 268, 70, 30, lab, sel, 12)
# the answer bar marked on the page dots: 4 bars, the last one answers
s.d.rectangle([66, 92, 168, 104], fill=s.col("off"))
for k in range(4):
    cx = 102 + k * 10
    s.d.ellipse([cx - 4, 96, cx + 4, 104], fill=s.col("acc" if k == 0 else ("lead" if k == 3 else "dim")))
s.note("new: the last bar answers the ones before (the lead the same)", 150, 230, 380)
s.note("the answer bar shows in green", 20, 108, 200)
s.save("bass-answer")

# ---- 3. perform: the mood dial, and the countdown under the tempo ----
s = S("perform-dark.png")
s.d.rectangle([92, 50, 228, 66], fill=s.col("bg"))
s.t("default · A · drop in 3", 98, 57, 10, "acc", anchor="lm")
s.d.rectangle([490, 184, 944, 414], fill=s.col("bg"))
s.rr(494, 186, 446, 150, "card", 10)
s.t("drums bus: crush", 510, 200, 15, "txt"); s.t("touch to play it", 510, 222, 10, "mute")
s.d.line([716, 192, 716, 330], fill=s.col("on"), width=2); s.d.line([500, 262, 934, 262], fill=s.col("on"), width=2)
s.d.ellipse([700, 246, 732, 278], outline=s.col("on"), width=2)
s.rr(494, 342, 446, 70, "card", 10)
s.t("mood", 508, 356, 12, "mute", True)
s.t("chill", 508, 392, 11, "mute", anchor="lm"); s.t("peak", 926, 392, 11, "mute", anchor="rm")
x0, x1, y = 548, 886, 392
for i in range(x1 - x0):
    f = i / (x1 - x0)
    r = int(0x44 + (0xC4 - 0x44) * f); g = int(0x44 + (0x37 - 0x44) * f); b = int(0x42 + (0x32 - 0x42) * f)
    s.d.line([x0 + i, y - 5, x0 + i, y + 5], fill=(r, g, b))
v = 0.68; px = x0 + (x1 - x0) * v
s.d.ellipse([px - 13, y - 13, px + 13, y + 13], fill=s.col("txt"))
for k, lab in enumerate(["chill", "warm", "groove", "lift", "peak"]):
    tx = x0 + (x1 - x0) * k / 4
    s.d.line([tx, y + 9, tx, y + 13], fill=s.col("dim"), width=2)
s.t("lift: busier drums, more slides, the pump in, a touch of drive", 560, 356, 10, "txt")
s.note("new: one dial from chill to peak", 690, 300, 230)
s.note("new: countdown", 230, 64, 120)
s.save("perform-mood")

# ---- 4. the show page: the sigil ----
s = S("perform-dark.png")
s.d.rectangle([0, 66, 960, 600], fill=s.col("bg"))
s.d.rectangle([226, 10, 838, 64], fill=s.col("bg"))
s.btn(230, 12, 120, 48, "show", True)
s.t("tap anywhere to go back", 366, 36, 11, "mute", anchor="lm")
cx, cy, R = 300, 335, 238
NAMES = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]
# the phrase ring: bar 3 of 4 so far
s.d.arc([cx - R, cy - R, cx + R, cy + R], -90, 360, fill=s.col("card"), width=10)
s.d.arc([cx - R, cy - R, cx + R, cy + R], -90, -90 + 360 * 0.62, fill=s.col("dim"), width=10)
# the 16 steps: kick hits bone, the current step red
kick = {0, 4, 8, 12}; cur = 10
for i in range(16):
    a = math.radians(-90 + i * 22.5); r = R - 26
    x, y = cx + r * math.cos(a), cy + r * math.sin(a)
    rad = 9 if i % 4 == 0 else 6
    fill = "acc" if i == cur else ("drums" if i in kick else "off")
    s.d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=s.col(fill))
# the twelve notes, the chord's root (A) at the top; the chord (A minor 7: A C E G) as a shape
r = R - 70
pts = {}
for k in range(12):
    a = math.radians(-90 + k * 30); x, y = cx + r * math.cos(a), cy + r * math.sin(a); pts[k] = (x, y)
chord = [0, 3, 7, 10]
s.d.polygon([pts[k] for k in chord], outline=s.col("chord"), fill="#2F3C3A")
s.d.line([pts[k] for k in chord] + [pts[chord[0]]], fill=s.col("chord"), width=3)
for k in range(12):
    x, y = pts[k]
    inc = k in chord
    s.d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=s.col("chord" if inc else "card"))
    s.t(NAMES[k], x, y, 11, "bg" if inc else "mute", inc, anchor="mm")
# the lead's last note flashes as a rune, the bass's note ringed
lx, ly = pts[7]; s.d.ellipse([lx - 20, ly - 20, lx + 20, ly + 20], outline=s.col("lead"), width=3)
bx, by = pts[0]; s.d.ellipse([bx - 20, by - 20, bx + 20, by + 20], outline=s.col("bass"), width=3)
# the eye: half open in a groove
ew, eh = 62, 22
s.d.chord([cx - ew, cy - eh * 2, cx + ew, cy + eh * 2], 0, 180, fill=s.col("txt"))
s.d.chord([cx - ew, cy - eh, cx + ew, cy + eh], 180, 360, fill=s.col("bg"))
s.d.ellipse([cx - 15, cy - 4, cx + 15, cy + 26], fill=s.col("bg"))
s.d.rectangle([cx - ew, cy - 2, cx + ew, cy + 1], fill=s.col("bg"))
s.t("Am7", cx, cy + 62, 22, "txt", True, anchor="mm")
# the right side: where we are, what's next, the parts
s.rr(586, 84, 354, 112, "card", 10)
s.t("groove", 604, 104, 13, "mute", True)
s.t("drop in 3 bars", 604, 128, 30, "txt", True)
s.t("bar 3 of the 4 bar phrase · scene A", 604, 172, 11, "mute")
s.rr(586, 206, 354, 196, "card", 10)
s.t("parts", 604, 224, 12, "mute", True)
for k, (nm, c, lv) in enumerate([("drums", "drums", 0.8), ("bass", "bass", 0.65), ("lead", "lead", 0.5), ("chords", "chord", 0.4), ("samples", "samples", 0.0)]):
    y = 254 + k * 30
    s.d.ellipse([604, y - 6, 616, y + 6], fill=s.col(c))
    s.t(nm, 626, y, 13, "txt", anchor="lm")
    s.d.rounded_rectangle([720, y - 5, 920, y + 5], radius=5, fill=s.col("track"))
    if lv: s.d.rounded_rectangle([720, y - 5, 720 + 200 * lv, y + 5], radius=5, fill=s.col(c))
s.rr(586, 412, 354, 84, "card", 10)
s.t("mood", 604, 430, 12, "mute", True)
s.d.rounded_rectangle([604, 462, 920, 470], radius=4, fill=s.col("track"))
s.d.rounded_rectangle([604, 462, 604 + 316 * 0.68, 470], radius=4, fill=s.col("acc"))
s.t("lift", 920, 432, 13, "txt", True, anchor="ra")
s.rr(586, 506, 354, 80, "card", 10)
s.t("the eye: half open in a groove, shut in a breakdown,", 604, 526, 11, "mute")
s.t("wide in a build, a flash on the drop", 604, 544, 11, "mute")
s.t("one colour per part, the same on every page", 604, 562, 11, "mute")
s.save("show-sigil")
