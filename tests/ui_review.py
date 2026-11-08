#!/usr/bin/env python3
"""Look over every screen for layout faults, as the Pi draws them (Pd's fonts, wrapped at the width given):
  - text that spills out of its box (too wide, or wrapped onto more lines than the box has room for)
  - text that runs into another box, or has a line drawn through it
  - boxes that overlap each other, or touch with no gap between them

Usage: python3 tests/ui_review.py [out_dir]   -> out_dir/review.txt, and out_dir/<screen>.png with the faults outlined
Uses the same screens as tests/ui_preview.py (its SHOTS)."""
import os, sys
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_preview as up

W, H = 960, 600


def shots(lines):
    """{label: [items]} where an item is ("box", kind, x, y, w, h) or ("text", s, x, y, size, wrap_w)."""
    out, cur, tw, col = {}, None, 0, None
    for l in lines:
        if l.startswith("begin "):
            cur = l[6:]; out[cur] = []; continue
        if l.startswith("end "):
            cur = None; continue
        if cur is None:
            continue
        t = l.split(" ")
        k = t[0]
        if k == "color":
            col = tuple(t[1:4])
        elif k == "fill_all":
            out[cur].append(("box", "page", 0, 0, W, H, col))
        elif k in ("rect", "rrect", "srrect"):
            x, y, w, h = map(float, t[1:5])
            out[cur].append(("box", k, x, y, w, h, col))
        elif k == "textw":
            tw = float(t[1])
        elif k == "text":
            x, y, sz = map(float, t[1:4])
            out[cur].append(("text", " ".join(t[4:]), x, y, sz, tw))
    return out


def contains(a, b, tol=1.0):
    ax, ay, aw, ah = a; bx, by, bw, bh = b
    return bx >= ax - tol and by >= ay - tol and bx + bw <= ax + aw + tol and by + bh <= ay + ah + tol


def inter(a, b):
    ax, ay, aw, ah = a; bx, by, bw, bh = b
    w = min(ax + aw, bx + bw) - max(ax, bx); h = min(ay + ah, by + bh) - max(ay, by)
    return (w, h)


def text_box(s, x, y, sz, tw):
    cw, lh = up.pd_font(sz)
    lines = up.wrap(s, tw, sz)
    pt = max(f[0] for f in up.PD_FONTS if f[0] <= max(sz, 8))
    width = max(len(ln) for ln in lines) * cw
    height = (len(lines) - 1) * lh + pt * 0.95   # down to the bottom of the letters
    return (x, y + pt * 0.12, width, height - pt * 0.12), len(lines)


def occlude(items):
    """A big box drawn over others (a sheet, a pop-up) hides what's under it: drop those, so only what's seen is checked."""
    keep = list(items)
    for j, it in enumerate(items):
        if it[0] != "box" or it[1] not in ("rect", "rrect") or it[4] * it[5] < 20000 or (it[4] >= 950 and it[5] >= 590):
            continue
        b = it[2:6]
        for k in range(j):
            o = keep[k]
            if o is None:
                continue
            ob = o[2:6] if o[0] == "box" else text_box(o[1], o[2], o[3], o[4], o[5])[0]
            if o[0] == "box" and contains(ob, b):
                continue   # what it sits on
            w, h = inter(ob, b)
            if w > 0 and h > 0:
                keep[k] = None
    return [it for it in keep if it is not None]


def review(items):
    items = occlude(items)
    faults = []
    # what each box sits on: the smallest box drawn before it that holds it. A box the same colour as that is invisible
    def under(j, b):
        best = None
        for k in range(j - 1, -1, -1):
            o = items[k]
            if o[0] == "box" and o[1] != "srrect" and contains(o[2:6], b[2:6], 0):
                if best is None or o[4] * o[5] < best[4] * best[5]:
                    best = o
        return best
    vis = []
    for j, it in enumerate(items):
        if it[0] != "box" or it[1] == "page":
            continue
        u = under(j, it)
        if it[1] != "srrect" and u is not None and u[6] == it[6]:
            continue   # same colour as what it's on: not seen
        vis.append((j, it))
    def is_fill(b):   # a bar's fill: inside a bigger box, same top and height
        for _, o in vis:
            if o is not b and o[4] > b[4] + 4 and abs(o[3] - b[3]) <= 2 and abs(o[5] - b[5]) <= 2 and contains(o[2:6], b[2:6]):
                return True
        return False
    boxes = [(i, it) for i, it in vis if it[4] >= 6 and it[5] >= 6 and not (it[4] >= 900 and it[5] >= 500)]
    fills = [b for _, b in boxes if is_fill(b)]
    boxes = [(i, b) for i, b in boxes if not any(b is f for f in fills)]
    vis_lines = [(i, it) for i, it in vis if it[1] == "rect" and (it[4] < 6 or it[5] < 6) and max(it[4], it[5]) >= 10]   # a bar's fill at its least is not a line
    # text
    for i, it in enumerate(items):
        if it[0] != "text" or not it[1].strip():
            continue
        _, s, x, y, sz, tw = it
        tb, nl = text_box(s, x, y, sz, tw)
        ax, ay = x + 1, y + up.pd_font(sz)[1] * 0.5
        # its box: the smallest box drawn before it that holds where it starts
        cont = None
        for j, b in boxes:
            if j > i or b[1] == "srrect":
                continue
            bx, by, bw, bh = b[2:6]
            if bx <= ax <= bx + bw and by <= ay <= by + bh:
                if cont is None or bw * bh < cont[4] * cont[5]:
                    cont = b
        where = f'"{s}" ({sz:g})'
        if cont:
            cb = cont[2:6]
            over_r = tb[0] + tb[2] - (cb[0] + cb[2])
            over_b = tb[1] + tb[3] - (cb[1] + cb[3])
            over_l = cb[0] - tb[0]
            if over_r > 1.5 or over_l > 1.5:
                faults.append(("text too wide", where, tb, f"{max(over_r, over_l):.0f}px past the edge" + (f", {nl} lines" if nl > 1 else "")))
            elif over_b > 2:
                faults.append(("text spills below", where, tb, f"{nl} lines, {over_b:.0f}px below the box"))
        else:
            if tb[0] + tb[2] > W + 1:
                faults.append(("text off screen", where, tb, ""))
        # other boxes it runs into (not its own box or the ones it sits in)
        for j, b in boxes:
            if b is cont or b[1] == "srrect":
                continue
            bb = b[2:6]
            if cont and contains(bb, cont[2:6]):
                continue
            if bb[0] <= ax <= bb[0] + bb[2] and bb[1] <= ay <= bb[1] + bb[3]:
                continue   # a box it starts inside
            w, h = inter(tb, bb)
            if w > 2 and h > 2:
                faults.append(("text runs into a box", where, tb, f"box at {bb[0]:g},{bb[1]:g} {bb[2]:g}x{bb[3]:g}"))
                break
        for j, b in vis_lines:
            if j < i and any(items[k][0] == "box" and items[k][1] != "srrect" and contains(items[k][2:6], tb, 3) for k in range(j + 1, i)):
                continue   # a plate drawn over the line, under the words
            w, h = inter(tb, b[2:6])
            if w > 0.5 and h > 0.5:
                faults.append(("line through text", where, tb, ""))
                break
    # words against words: two texts drawn over each other
    tx = [(i, it, text_box(it[1], it[2], it[3], it[4], it[5])[0]) for i, it in enumerate(items) if it[0] == "text" and it[1].strip()]
    for a in range(len(tx)):
        for b in range(a + 1, len(tx)):
            w, h = inter(tx[a][2], tx[b][2])
            if w > 2 and h > 2:
                ta, tb2 = tx[a][2], tx[b][2]
                faults.append(("texts overlap", f'"{tx[a][1][1]}" / "{tx[b][1][1]}"', (min(ta[0], tb2[0]), min(ta[1], tb2[1]), max(ta[0] + ta[2], tb2[0] + tb2[2]) - min(ta[0], tb2[0]), max(ta[1] + ta[3], tb2[1] + tb2[3]) - min(ta[1], tb2[1])), ""))
    # boxes against boxes: filled controls (rrects) that overlap without one holding the other, or touch with no gap
    rr = [b for _, b in boxes if b[1] == "rrect"]
    seen = set()
    for a_i in range(len(rr)):
        for b_i in range(a_i + 1, len(rr)):
            a, b = rr[a_i][2:6], rr[b_i][2:6]
            if contains(a, b) or contains(b, a) or min(a[2], a[3], b[2], b[3]) <= 10:   # a fader's cap on its slot, a thin mark
                continue
            w, h = inter(a, b)
            key = (a, b)
            if key in seen:
                continue
            if w > 1 and h > 1:
                seen.add(key)
                faults.append(("boxes overlap", f"{a[0]:g},{a[1]:g} {a[2]:g}x{a[3]:g} / {b[0]:g},{b[1]:g} {b[2]:g}x{b[3]:g}", (min(a[0], b[0]), min(a[1], b[1]), max(a[0] + a[2], b[0] + b[2]) - min(a[0], b[0]), max(a[1] + a[3], b[1] + b[3]) - min(a[1], b[1])), f"{w:.0f}x{h:.0f} overlap"))
            elif (-1 <= w <= 1 and h > 4) or (-1 <= h <= 1 and w > 4):
                seen.add(key)
                faults.append(("boxes touch", f"{a[0]:g},{a[1]:g} {a[2]:g}x{a[3]:g} / {b[0]:g},{b[1]:g} {b[2]:g}x{b[3]:g}", (min(a[0], b[0]), min(a[1], b[1]), max(a[0] + a[2], b[0] + b[2]) - min(a[0], b[0]), max(a[1] + a[3], b[1] + b[3]) - min(a[1], b[1])), "no gap"))
    return faults


def faults_on_every_screen():
    """[(screen, kind, what, note)] for every screen in ui_preview's SHOTS (used by the tests)."""
    script = up.project_lines() + ["send ockm-load float 0", "send ockm-patterns-exist float 15"]
    for name, steps in up.SHOTS:
        script += steps + [f"paint {name}"]
    S = shots(up.run(script, "light"))
    return [(name, k, w, n) for name, _ in up.SHOTS for k, w, _, n in review(S.get(name, []))]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(up.ROOT, "ui-review")
    os.makedirs(out, exist_ok=True)
    script = up.project_lines() + ["send ockm-load float 0", "send ockm-patterns-exist float 15"]
    for name, steps in up.SHOTS:
        script += steps + [f"paint {name}"]
    lines = up.run(script, "light")
    S = shots(lines)
    report, total = [], 0
    for name, _ in up.SHOTS:
        f = review(S.get(name, []))
        if not f:
            continue
        total += len(f)
        report.append(f"== {name} ({len(f)})")
        for kind, what, _, note in f:
            report.append(f"  {kind}: {what} {note}".rstrip())
        p = os.path.join(out, f"{name}.png")
        up.render(lines, name, p)
        im = Image.open(p).convert("RGB"); d = ImageDraw.Draw(im)
        for kind, _, b, _ in f:
            c = (230, 0, 120) if kind.startswith("text") or kind == "line through text" else (0, 140, 255)
            d.rectangle([b[0] - 2, b[1] - 2, b[0] + b[2] + 2, b[1] + b[3] + 2], outline=c, width=2)
        im.save(p)
    open(os.path.join(out, "review.txt"), "w").write("\n".join(report) + "\n")
    print("\n".join(report)); print(f"{total} faults")


if __name__ == "__main__":
    main()
