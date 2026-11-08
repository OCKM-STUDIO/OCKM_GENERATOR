#!/usr/bin/env python3
"""The screenshots for the README and the GitHub page (v1.49): every main screen at the 10-inch Pi screen's size
(1920x1200), drawn as the Pi draws it (tests/ui_preview.py's Pd fonts), from a scene with something in it.

  python3 tools/screenshots.py [project folder] [out folder]

The project folder holds project.txt and p1.txt (a scene: a saved loop, e.g. a copy of a project's loop.txt as p1.txt).
Without one it uses projects/default, which starts blank. Writes docs/img/<screen>.png and docs/img/social.png
(1280x640, for GitHub's social preview)."""
import os, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
PROJ = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "projects", "default")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "docs", "img")
os.environ["OCKM_PREVIEW_PROJECT"] = PROJ
import ui_preview as up

S = 2   # the Pi's screen: the 960x600 layout at twice the size

# each screen: what to tap to get there (the same as the preview's SHOTS), then it's drawn
SHOTS = [
    ("perform", ["send ockm-play float 1", "send ockm-playing float 1", "send ockm-mood float 0.62", "send ockm-step float 6"]),
    ("builder", ["test tap 477 36"]),
    ("drums", ["test tap 539 36", "test tap 818 134"]),
    ("drums-kick", ["test tap 879 428"]),
    ("bass", ["test tap 601 36", "test tap 509 350"]),
    ("lead", ["test tap 663 36"]),
    ("chords", ["test tap 725 36"]),
    ("mixer", ["test tap 373 36"]),
    ("fx", ["test tap 322 36", "test press 700 250"]),
    ("pads", ["test release 700 250", "test tap 539 36", "test tap 908 134"]),   # the drums as pads
]


def font(sz):
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", int(max(f[0] for f in up.PD_FONTS if f[0] <= max(sz, 8))))


def render(lines, label, path):
    """ui_preview.render, at S times the size: Pd's font for the doubled size, wrapped at the doubled width."""
    im = Image.new("RGB", (960 * S, 600 * S), "black"); d = ImageDraw.Draw(im)
    col, on, tw = (255, 255, 255), False, 0
    for l in lines:
        if l == f"begin {label}": on = True; continue
        if l == f"end {label}": break
        if not on: continue
        t = l.split(" "); k = t[0]
        if k == "color": col = tuple(int(v) for v in t[1:4])
        elif k == "fill_all": d.rectangle([0, 0, 960 * S, 600 * S], fill=col)
        elif k == "rect":
            x, y, w, h = (float(v) * S for v in t[1:5]); d.rectangle([x, y, x + w, y + h], fill=col)
        elif k == "rrect":
            x, y, w, h, r = (float(v) * S for v in t[1:6]); d.rounded_rectangle([x, y, x + w, y + h], radius=min(r, w / 2, h / 2), fill=col)
        elif k == "srrect":
            x, y, w, h, r = (float(v) * S for v in t[1:6]); d.rounded_rectangle([x, y, x + w, y + h], radius=r, outline=col, width=max(1, int(float(t[6]) * S)))
        elif k == "ellipse":
            x, y, w, h = (float(v) * S for v in t[1:5]); d.ellipse([x, y, x + w, y + h], fill=col)
        elif k == "textw": tw = float(t[1]) * S
        elif k == "text":
            x, y = float(t[1]) * S, float(t[2]) * S; sz = float(t[3]) * S
            for i, ln in enumerate(up.wrap(" ".join(t[4:]), tw, sz)):
                d.text((x, y + i * up.pd_font(sz)[1]), ln, fill=col, font=font(sz))
        elif k == "path":
            pts = [float(v) * S for v in t[1:]]; d.polygon(list(zip(pts[0::2], pts[1::2])), fill=col)
    im.save(path)
    return im


def social(perform, path):
    """GitHub's social preview: the perform screen on the right, the name and a line on the left."""
    W, H = 1280, 640
    bg = perform.getpixel((4, 4))
    im = Image.new("RGB", (W, H), bg); d = ImageDraw.Draw(im)
    shot = perform.resize((int(1920 * 0.4), int(1200 * 0.4)), Image.LANCZOS)
    x0, y0 = W - shot.width - 48, (H - shot.height) // 2
    d.rounded_rectangle([x0 - 10, y0 - 10, x0 + shot.width + 10, y0 + shot.height + 10], radius=22, fill=(20, 20, 19))
    im.paste(shot, (x0, y0))
    big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 64)
    big2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 40)
    mid = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 22)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 20)
    d.text((56, 150), "OCKM", font=big, fill=(232, 232, 228))
    d.text((56, 218), "GENERATOR", font=big2, fill=(232, 232, 228))
    d.rectangle([58, 272, 58 + 60, 278], fill=(196, 55, 50))
    for i, ln in enumerate(["A generative groovebox", "for house and techno"]):
        d.text((56, 300 + i * 34), ln, font=mid, fill=(232, 232, 228))
    for i, ln in enumerate(["Pure Data on a Raspberry Pi", "and a touchscreen. Open source."]):
        d.text((56, 390 + i * 30), ln, font=small, fill=(176, 176, 170))
    im.save(path)


def main():
    os.makedirs(OUT, exist_ok=True)
    name = os.environ.get("OCKM_SHOT_NAME", "2026-10-31-night-shift")   # the project name shown under the tempo
    script = up.project_lines() + ["send ockm-load float 0", "send ockm-patterns-exist float 1", f"send ockm-project-name symbol {name}", "send ockm-saved bang"]
    for name, steps in SHOTS:
        script += steps + ["send ockm-saved bang", f"paint {name}"]   # nothing unsaved: a clean save button
    lines = up.run(script, "dark")
    errs = [l for l in lines if l.startswith("error")]
    if errs: raise RuntimeError("\n".join(errs))
    ims = {}
    for name, _ in SHOTS:
        ims[name] = render(lines, name, os.path.join(OUT, f"{name}.png"))
    social(ims["perform"], os.path.join(OUT, "social.png"))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
