#!/usr/bin/env python3
"""Draw the touchscreen UI to PNG files without Pure Data.

Runs ui/ockm-ui.pd_lua in plain Lua (tests/ui_mock.lua stands in for Pd), loads
pattern 1 from projects/default, and draws each screen.

Usage: python3 tests/ui_preview.py [out_dir] [dark|light]
Needs: lua (5.3 or 5.4) and Python's Pillow.
"""
import os, re, sys, shutil, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUA = shutil.which("lua5.4") or shutil.which("lua5.3") or shutil.which("lua")


def project_lines(slot=1):
    """Pattern 1 and the project, as mock-script lines."""
    out = []
    for fn in ("project.txt", f"p{slot}.txt"):
        proj = os.environ.get("OCKM_PREVIEW_PROJECT", os.path.join(ROOT, "projects", "default"))
        for raw in open(os.path.join(proj, fn)).read().split(";"):
            t = raw.split()
            if not t:
                continue
            if t[0].startswith("ockm-pat-") and len(t) > 2:
                out.append("array " + t[0] + " " + " ".join(t[2:]))
            elif len(t) == 2 and t[0].startswith("ockm-"):
                out.append(f"send {t[0]} float {t[1]}")
            elif t[0] == "add" and len(t) >= 3:  # qlist 'add' form, just in case
                pass
    return out


def run(script_lines, theme="dark"):
    d = tempfile.mkdtemp()
    s, o = os.path.join(d, "script.txt"), os.path.join(d, "out.txt")
    open(s, "w").write("\n".join(script_lines) + "\n")
    env = dict(os.environ, UI_ARGS=f"1 {theme}")
    p = subprocess.run([LUA, os.path.join(ROOT, "tests", "ui_mock.lua"), os.path.join(ROOT, "ui", "ockm-ui.pd_lua"), s, o],
                       capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return open(o).read().splitlines()


def font(sz):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(f):
            return ImageFont.truetype(f, int(sz))
    return ImageFont.load_default()


def render(lines, label, path):
    im = Image.new("RGB", (960, 600), "black")
    d = ImageDraw.Draw(im)
    col = (255, 255, 255)
    on = False
    for l in lines:
        if l == f"begin {label}":
            on = True; continue
        if l == f"end {label}":
            break
        if not on:
            continue
        t = l.split(" ")
        k = t[0]
        if k == "color":
            col = tuple(int(v) for v in t[1:4])
        elif k == "fill_all":
            d.rectangle([0, 0, 960, 600], fill=col)
        elif k == "rect":
            x, y, w, h = map(float, t[1:5]); d.rectangle([x, y, x + w, y + h], fill=col)
        elif k == "rrect":
            x, y, w, h, r = map(float, t[1:6]); d.rounded_rectangle([x, y, x + w, y + h], radius=min(r, w / 2, h / 2), fill=col)
        elif k == "srrect":
            x, y, w, h, r, th = map(float, t[1:7]); d.rounded_rectangle([x, y, x + w, y + h], radius=r, outline=col, width=int(th))
        elif k == "ellipse":
            x, y, w, h = map(float, t[1:5]); d.ellipse([x, y, x + w, y + h], fill=col)
        elif k == "text":
            x, y, sz = map(float, t[1:4]); d.text((x, y), " ".join(t[4:]), fill=col, font=font(sz))
        elif k == "path":
            pts = list(map(float, t[1:])); d.polygon(list(zip(pts[0::2], pts[1::2])), fill=col)
    im.save(path)


SHOTS = [
    ("perform", ["send ockm-play float 1", "send ockm-step float 4"]),
    ("drums", ["test tap 50 137"]),                                   # tap the kick lane name
    ("bass", ["test tap 483 36", "test tap 89 158"]),                 # bass tab; tapping a step on auto just explains the lock
    ("chord", ["test tap 621 36"]),
    ("compose", ["test tap 345 36"]),
    ("perform-mutes", ["test tap 281 36", "test tap 126 137", "test tap 166 369"]),   # mute kick, solo bass
    ("mixer", ["test tap 690 36"]),
    ("drums-long", ["test tap 414 36", "test tap 861 88", "test tap 194 88"]),        # 64 steps, forward to the second block
    ("compose-melody", ["test tap 345 36", "test tap 186 154", "test tap 400 540"]),   # melody leads, ask for chords, then mutate the bass
    ("drums-groove", ["test tap 414 36", "test tap 660 445"]),                         # drums tab, tap a groove
    ("project", ["test tap 910 36", "test tap 600 261"]),                              # project screen, pick an older project
    ("song", ["test tap 759 36", "test tap 640 282", "test tap 727 282", "test tap 727 282", "test tap 640 332", "test tap 380 199", "test tap 380 199", "test tap 380 199"]),
    ("setup", ["test tap 150 36"]),
    ("new-pattern", ["test tap 276 36", "test tap 441 88"]),             # perform, then + next to the patterns
    ("bass-manual", ["test tap 483 36", "test tap 900 283", "test tap 89 158"]),      # switch to manual, then edit step 2
]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "ui-preview")
    theme = sys.argv[2] if len(sys.argv) > 2 else "dark"
    os.makedirs(out, exist_ok=True)
    script = project_lines() + ["send ockm-load float 0", "send ockm-patterns-exist float 15"]
    for name, steps in SHOTS:
        script += steps + [f"paint {name}"]
    lines = run(script, theme)
    errs = [l for l in lines if l.startswith("error")]
    if errs:
        raise RuntimeError("\n".join(errs))
    leaks = [l for l in lines if l.startswith("text ") and re.search(r"\d\.0\b", " ".join(l.split()[4:]))]
    if leaks:
        raise RuntimeError("numbers drawn as decimals: " + " | ".join(leaks[:5]))
    for name, _ in SHOTS:
        render(lines, name, os.path.join(out, f"{name}-{theme}.png"))
    print("wrote", out)


if __name__ == "__main__":
    main()
