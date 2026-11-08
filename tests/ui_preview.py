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
    env = dict(os.environ, UI_ARGS=f"1 {theme}", OCKM_PREVIEW_THEME=theme)
    p = subprocess.run([LUA, os.path.join(ROOT, "tests", "ui_mock.lua"), os.path.join(ROOT, "ui", "ockm-ui.pd_lua"), s, o],
                       capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return open(o).read().splitlines()


# The Pi draws text with Pd's own fonts (DejaVu Sans Mono): a size is rounded down to one of Pd's sizes, each with its
# own character width and line height (Pd's sys_fontspec). Measured on the Pi's screen: 10 and 11 draw 6 wide, 12 and 14
# draw 7, 16 and 17 draw 10, 32 draws 14 wide (24)
PD_FONTS = [(8, 5, 11), (10, 6, 13), (12, 7, 16), (16, 10, 19), (24, 14, 29), (36, 22, 44)]


def pd_font(sz):
    """(character width, line height) Pd draws a text size with."""
    best = PD_FONTS[0]
    for f in PD_FONTS:
        if f[0] <= sz: best = f
    return best[1], best[2]


def wrap(s, w, sz):
    """The lines the Pi draws: word-wrapped at w pixels, as Tk does (a word longer than a line is broken)."""
    per = max(1, int(w // pd_font(sz)[0])) if w and w > 0 else 10 ** 6
    lines, cur = [], ""
    for word in s.split(" "):
        while len(word) > per:
            if cur: lines.append(cur); cur = ""
            lines.append(word[:per]); word = word[per:]
        if not cur: cur = word
        elif len(cur) + 1 + len(word) <= per: cur += " " + word
        else: lines.append(cur); cur = word
    lines.append(cur)
    return lines


def font(sz):
    sz = max(f[0] for f in PD_FONTS if f[0] <= max(sz, 8))   # Pd's size: DejaVu Sans Mono at it is as wide as Pd draws
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(f):
            return ImageFont.truetype(f, int(sz))
    return ImageFont.load_default()


def render(lines, label, path):
    im = Image.new("RGB", (960, 600), "black")
    d = ImageDraw.Draw(im)
    col = (255, 255, 255)
    on = False
    tw = 0
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
        elif k == "textw":
            tw = float(t[1])
        elif k == "text":
            x, y, sz = map(float, t[1:4])
            for i, ln in enumerate(wrap(" ".join(t[4:]), tw, sz)):
                d.text((x, y + i * pd_font(sz)[1]), ln, fill=col, font=font(sz))
        elif k == "path":
            pts = list(map(float, t[1:])); d.polygon(list(zip(pts[0::2], pts[1::2])), fill=col)
    im.save(path)


SHOTS = [
    ("perform", ["send ockm-play float 1", "send ockm-step float 4"]),
    ("perform-synths", ["array ockm-pat-d1 2 0 0 0 1 0 0 0 2 0 0 0 1 0 0 0", "array ockm-pat-d5 1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1",
                        "array ockm-pat-bass-on 1 0 1 1 0 1 1 0 1 0 1 1 0 1 1 0", "array ockm-pat-chord-on 1 0 0 0 0 0 0 0 1",
                        "send ockm-bass-seed float 2", "send ockm-play float 1", "send ockm-step float 2", "test tap 902 163"]),   # playing, filter hold on
    ("live", ["array ockm-pat-d1 2 0 0 0 1 0 0 0 2 0 0 0 1 0 0 0", "send ockm-playing float 1", "send ockm-step float 4", "test tap 616 36",
              "test tap 400 97", "test tap 60 180", "send ockm-d3-mute float 1"]),          # next bar, kick waiting to mute, clap muted
    ("live-macro", ["test tap 616 36", "test press 700 500"]),                              # holding wash
    ("menu", ["send ockm-bpm float 124", "test tap 919 36"]),                                # the menu, open (unsaved: the disc is orange)
    ("settings-device", ["test release 700 500", "test tap 830 195", "test tap 90 216"]),   # the menu is still open from the shot before
    ("settings-macros", ["test tap 90 272", "test tap 260 119"]),
    ("perform-b-pick", ["test tap 616 36", "test tap 616 458"]),                                # the v on slot A: pick a recipe
    ("drums-all", ["test tap 301 36", "test tap 301 36", "test tap 818 134"]),           # drums tab, all drums (v0.87: Perform A's grid)
    ("drums", ["test tap 879 428"]),                                  # back to one drum
    ("bass", ["test tap 363 36", "test tap 89 158"]),                 # bass tab; tapping a step on auto just explains the lock
    ("lead", ["test tap 425 36"]),
    ("chord", ["test tap 487 36"]),
    ("chord-hands", ["send ockm-chord-engine float 3", "send ockm-chord-hands float 2"]),   # v1.20: piano, two hands, pulse
    ("compose", ["test tap 239 36"]),
    ("perform-mutes", ["test tap 608 36", "test tap 74 186", "test tap 103 503"]),   # mute the kick, solo the bass
    ("mixer", ["test tap 719 36"]),
    ("midi-learn", ["test tap 616 36", "test tap 919 36", "test tap 830 345", "test tap 560 480", "send ockm-midi-cc list 64 21", "test tap 700 300"]),   # v1.30: learn on, a macro slot outlined
    ("midi-settings", ["test tap 896 579", "send ockm-midi-note list 50 90", "test tap 919 36", "test tap 830 190", "test tap 90 328"]),   # v1.31: the MIDI list in settings
    ("arrange", ["test tap 805 36", "test tap 120 566", "test tap 280 566", "test tap 120 566", "test tap 600 566", "test tap 80 190"]),   # v1.28: a version of three scenes plus one, section 1 picked
    ("arrange-trans", ["test tap 230 200", "test tap 640 357"]),         # its transition picked: rise
    ("fx", ["test tap 668 36", "test press 700 250"]),                   # v1.23: the fx page, a finger on the pad (drums: crush in)
    ("fx-settings", ["test release 700 250", "test tap 250 198"]),      # the drums bus's settings
    ("mixer-eq", ["send ockm-d4-lowcut float 300", "send ockm-d4-eqmid float -6", "send ockm-d4-eqmidf float 500", "send ockm-d4-eqhigh float 5", "test tap 719 36", "test tap 288 232"]),
    ("drums-long", ["test tap 750 546", "test tap 301 36", "test tap 861 88", "test tap 194 88"]),        # 64 steps, forward to the second block
    ("compose-melody", ["test tap 239 36", "test tap 363 250", "test tap 831 250", "test tap 586 402", "test tap 878 406"]),   # bass and lead out, phrase 8 with the turnaround
    ("drums-samples", ["test tap 301 36", "test tap 264 364", "test tap 264 364", "test tap 264 364"]),   # drums tab, step to sample 3
    ("drums-perc", ["test tap 301 36", "test tap 776 134", "test tap 264 364"]),         # drums tab, perc 1, step to the conga
    ("drums-velocity", ["array ockm-pat-d1 2 0 0 0 1 0 0.5 0 2 0 0 0 1 0 0.3 0", "test tap 301 36"]),
    ("drums-timing", ["array ockm-pat-d1 2 0 0 0 1 0 0.5 0 2 0 0 0 1 0 0.3 0", "array ockm-pat-d1-nudge 0 0 0 0 -0.2 0 0.1 0 0 0 0 0 0.25 0 -0.1 0",
                      "test tap 301 36", "test tap 145 282", "send ockm-drum-loop float 32"]),
    ("drums-groove", ["test tap 301 36", "test tap 660 445"]),                         # drums tab, tap a groove
    ("project", ["test tap 919 36", "test tap 830 95", "test tap 600 261"]),                              # project screen, pick an older project
    ("project-variations", ["test tap 919 36", "test tap 830 95", "test tap 200 180", "test tap 720 318"]),   # v1.26: neon otter picked, its v2 picked
    ("project-browser", ["test tap 876 230"]),                                                             # more: copy, tidy up, delete the project
    ("setup", ["test tap 150 36"]),
    ("arrange", ["test tap 807 36"]),                                                     # arrange tab (being rebuilt)
    ("export", ["test tap 919 36", "test tap 830 95", "test tap 902 100"]),                                    # project screen, export...
    ("bass-manual", ["test tap 363 36", "test tap 900 283", "test tap 89 158"]),      # switch to manual, then edit step 2
    ("bass-sidechain", ["test tap 836 544", "send ockm-bass-sidechain float 0.7", "test tap 363 36"]),   # the sidechain shapes, pump picked
    ("song-style", ["test tap 239 36", "test tap 584 174"]),   # peak time (last: it changes the tempo and groove)
    ("vox", ["test tap 530 36", "test tap 64 322", "test tap 740 272", "test tap 46 166", "test tap 278 166",
             "test tap 170 272", "test tap 250 322", "test tap 820 272", "test tap 510 166", "test tap 742 166",
             "send ockm-play float 1", "send ockm-step float 4"]),    # v1.38 the samples tab: arm, effect, tap steps
    ("setup-midiout", ["test tap 150 36", "test tap 93 384", "test tap 415 138", "test tap 705 138"]),   # v1.49 sequencer mode, MPC    # v1.40 MIDI out: bass on MIDI, lead channel up
    ("drums-pads", ["send ockm-play float 0", "test tap 301 36", "test tap 908 134", "test tap 70 236", "test drag 179 290 179 250"]),   # v1.45 pads: kick muted, snare up
    ("bass-synth", ["send ockm-play float 0", "test tap 363 36", "test tap 866 350"]),     # v1.45 the bass part on the Bass synth: its knobs, edit
    ("bass-synth-edit", ["test tap 859 314", "test drag 332 200 332 150", "send ockm-play float 1", "send ockm-step float 2"]),   # its page, over the playing groovebox
    ("analog-synth", ["test tap 41 36", "test tap 425 36", "test tap 900 350"]),          # back; the lead on the Analog
    ("analog-edit-keys", ["test tap 859 314", "test tap 735 36", "test tap 690 120", "test tap 100 500", "test tap 300 500", "test tap 430 500"]),   # its keys: hold, a chord
    ("drums-lane", ["test tap 41 36", "test tap 301 36", "test tap 301 36", "array ockm-pat-d1 2 0 0 0 1 0 0 0 2 0 0 0 1 0 0 0",
                    "array ockm-pat-d1-rat 0 0 0 0 3 0 0 0 0 0 0 0 6 0 0 0", "test tap 196 282", "test tap 430 364", "send ockm-d1-thin float 0.5"]),   # v1.49 rolls and the lane
    ("show", ["test tap 919 36", "test tap 830 245", "send ockm-play float 1", "send ockm-playing float 1", "send ockm-step float 6"]),   # v1.49 the show page, from the menu
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
    # the page colour, so a theme change can't slip back to the old black or the old orange
    page = (42, 42, 40) if theme == "dark" else (217, 217, 214)
    live = "\n".join(lines)
    begin = live.find("begin live\n")
    end = live.find("\nend live")
    body = live[begin:end] if begin >= 0 else ""
    if f"color {page[0]} {page[1]} {page[2]}" not in body:
        raise RuntimeError(f"live screen is not core grey ({theme})")
    leaks = [l for l in lines if l.startswith("text ") and re.search(r"\d\.0\b", " ".join(l.split()[4:]))]
    if leaks:
        raise RuntimeError("numbers drawn as decimals: " + " | ".join(leaks[:5]))
    for name, _ in SHOTS:
        render(lines, name, os.path.join(out, f"{name}-{theme}.png"))
    print("wrote", out)


if __name__ == "__main__":
    main()
