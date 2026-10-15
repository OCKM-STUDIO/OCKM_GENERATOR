# Sample picker: fills samples/<sound>/ with numbered one-shots from a big sample library.
# 20 per sound, max 3 per source, CM Lofi kits first, and 5 varied picks from Tape909_Samples per sound.
# Set OCKM_SAMPLES_SRC to your library folder. Run without --copy to preview, with --copy to write files and samples/sources.csv.
import os, re, sys, struct, random, shutil, csv
SRC = os.path.expanduser(os.environ.get("OCKM_SAMPLES_SRC", "~/Music/SAMPLES_TO_GO"))
DST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "samples")
COPY = "--copy" in sys.argv
PER, CAP, TAPE = 20, 3, 5
TAPEPAT = re.compile(r"^909\w*?_(orig|tape|tapesat|x|tech\d+|amp\d+|misc\d+|sweet\d+)\.wav$", re.I)
MAXLEN = {"kick": 1.6, "snare": 1.6, "clap": 1.6, "hat": 0.9, "open-hat": 2.5, "tom": 2.0, "perc": 1.5}
BAD = re.compile(r"loop|bpm|\bfill|roll|no kick|with |groove|break|phrase|\d{2,3} ?bpm|top|full|beat|chop|vox|vocal|fx\b|riser|sweep|reverse", re.I)
def wav_len(p):
    try:
        with open(p, "rb") as f:
            h = f.read(12)
            if h[:4] != b"RIFF" or h[8:12] != b"WAVE": return None
            rate = None; bpsec = None
            while True:
                ch = f.read(8)
                if len(ch) < 8: return None
                cid, sz = ch[:4], struct.unpack("<I", ch[4:])[0]
                if cid == b"fmt ":
                    d = f.read(sz); bpsec = struct.unpack("<I", d[8:12])[0]; rate = struct.unpack("<I", d[4:8])[0]
                    if sz % 2: f.read(1)
                elif cid == b"data":
                    return sz / bpsec if bpsec else None
                else:
                    f.seek(sz + (sz % 2), 1)
    except Exception:
        return None
def kind(name, path):
    n = name.lower(); p = path.lower()
    m = re.match(r"909(bd|sd|snr|ohh|oh|hh|ht|mt|lt|tom|rim|clap|cym)", n)
    if m:
        return {"bd":"kick","sd":"snare","snr":"snare","ohh":"open-hat","oh":"open-hat","hh":"hat","ht":"tom","mt":"tom",
                "lt":"tom","tom":"tom","rim":"perc","clap":"clap","cym":None}[m.group(1)]
    if re.search(r"rim ?shot|side ?stick|sidestick|\brim\b|rim[_ -]|rim\d|\d+rim", n): return "perc"
    if re.search(r"shaker|shkr|conga|bongo|cowbell|clave|tamb|perc|block|guiro|cabasa|timbale|agogo", n): return "perc"
    if re.search(r"open|\boh\b|_oh|ohh", n) and re.search(r"hat|hh|oh", n): return "open-hat"
    if re.search(r"kick|\bkik\b|kik[ _\d]|\bbd\b|bassdrum", n): return "kick"
    if re.search(r"snare|\bsnr\b|snr[ _\d]|\bsd\b", n): return "snare"
    if re.search(r"clap|\bclp\b", n): return "clap"
    if re.search(r"\btom|tom[ _\d-]|lowtom|midtom|hightom|_tom", n): return "tom"
    if re.search(r"hat|\bhh\b|hihat|hi-hat|hi_hat", n): return "hat"
    return None
def source(top, name):
    if top == "Tape909_Samples" or TAPEPAT.match(name): return "Tape909_Samples"
    if top.startswith("_"):     # your sorted folders: the source is the label code in the name
        GENERIC = {"kick","kik","snare","snr","clap","hat","hats","hh","ohh","tom","toms","open","closed","house","hi","single","drum","drums",
                   "909","808","606","707","shaker","perc","low","mid","high","hightom","midtom","lowtom","snare01","kick01","the","a"}
        words = [w for w in re.split(r"[-_ .]+", os.path.splitext(name)[0]) if w and not w.isdigit()]
        words = [w for w in words if w.lower() not in GENERIC and not re.fullmatch(r"\d+[a-z]?", w.lower())]
        return (words[0].lower() if words else "misc")
    return top
prio = lambda top: -1 if top == "Tape909_Samples" else 0 if "lofi" in top.lower().replace(" ", "") and "cm" in top.lower() else (1 if top.startswith("_") else 2)
cands = {k: {} for k in MAXLEN}
for root, dirs, files in os.walk(SRC):
    rel = os.path.relpath(root, SRC)
    if BAD.search(rel) or "SAMPLER_PATCHES" in rel: continue
    top = rel.split(os.sep)[0]
    for fn in files:
        if not fn.lower().endswith((".wav",)) or fn.startswith("._"): continue
        if BAD.search(fn): continue
        k = kind(fn, rel)
        if not k: continue
        path = os.path.join(root, fn)
        ln = wav_len(path)
        if ln is None or ln < 0.03 or ln > MAXLEN[k]: continue
        src = source(top, fn)
        pr = -1 if src == "Tape909_Samples" else prio(top)
        cands[k].setdefault((pr, src), []).append(path)
rnd = random.Random(14)
PRETTY = {"Tape909_Samples": "Tape909", " CM Lofi Kit 01": "CM Lofi Kit 01", "CMLOFIKIT 05 Wavs": "CM Lofi Kit 05"}
pretty = lambda s: PRETTY.get(s, s.strip())

# --add N: N more per sound, after the files already there (their numbers never move). Same rules: no file twice,
# no duplicate audio, no more than 3 per source counting the ones already picked (Tape909 keeps its 5).
if "--add" in sys.argv:
    import hashlib
    N = int(sys.argv[sys.argv.index("--add") + 1])
    old = list(csv.DictReader(open(os.path.join(DST, "sources.csv"))))
    rows = [[r["sound"], r["file"], r["source"], r["original"]] for r in old]
    for k, bysrc in cands.items():
        d = os.path.join(DST, k)
        have = [f for f in os.listdir(d) if f.lower().endswith(".wav")] if os.path.isdir(d) else []
        hashes = {hashlib.md5(open(os.path.join(d, f), "rb").read()).hexdigest() for f in have}
        used = {}
        for r in old:
            if r["sound"] == k: used[r["source"]] = used.get(r["source"], 0) + 1
        taken = {r["original"] for r in old}
        keys = sorted(bysrc, key=lambda t: (used.get(pretty(t[1]), 0), rnd.random()))   # sources not used yet come first
        for key in keys: rnd.shuffle(bysrc[key])
        new = []
        for take in range(CAP):
            for key in keys:
                src = pretty(key[1])
                if len(new) >= N: break
                if used.get(src, 0) >= (TAPE if src == "Tape909" else CAP): continue
                for path in bysrc[key]:
                    rel = os.path.relpath(path, SRC)
                    if rel in taken: continue
                    h = hashlib.md5(open(path, "rb").read()).hexdigest()
                    taken.add(rel)
                    if h in hashes: continue
                    hashes.add(h); new.append((src, path)); used[src] = used.get(src, 0) + 1
                    break
        first = []
        for s_, _ in new:
            if s_ not in first: first.append(s_)
        new.sort(key=lambda t: first.index(t[0]))
        start = max([int(f[:2]) for f in have if f[:2].isdigit()] + [len(have)]) + 1
        print(f"{k:9s} +{len(new)} as {start:02d}-{start + len(new) - 1:02d}: " + ", ".join(first))
        if COPY:
            for i, (src, path) in enumerate(new):
                name = f"{start + i:02d}.wav"
                shutil.copyfile(path, os.path.join(d, name))
                rows.append([k, name, src, os.path.relpath(path, SRC)])
    if COPY:
        with open(os.path.join(DST, "sources.csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(["sound", "file", "source", "original"]); w.writerows(rows)
        print("written")
    sys.exit(0)

picked = {}
for k, bysrc in cands.items():
    keys = sorted(bysrc, key=lambda t: (t[0], rnd.random()))
    for key in keys: rnd.shuffle(bysrc[key])
    out = []
    FL = ["orig", "tape", "tapesat", "x"]
    for key in [k2 for k2 in keys if k2[0] == -1]:
        bases = {}
        for path in bysrc[key]:
            b = re.sub(r"_(orig|tape|tapesat|x)\.wav$", "", os.path.basename(path), flags=re.I)
            bases.setdefault(b, []).append(path)
        order = sorted(bases, key=lambda b: rnd.random())
        for i, b in enumerate(order[:TAPE]):
            want = FL[i % 4]
            hit = [q for q in bases[b] if q.lower().endswith("_" + want + ".wav")]
            out.append((key[1], (hit or bases[b])[0]))
    for key in [k2 for k2 in keys if k2[0] == 0]:
        for path in bysrc[key][:CAP]:
            if len(out) < PER: out.append((key[1], path))
    keys = [k2 for k2 in keys if k2[0] > 0]
    for take in range(CAP):          # round robin: one from each source, then a second, then a third
        for key in keys:
            if len(out) >= PER: break
            if take < len(bysrc[key]): out.append((key[1], bysrc[key][take]))
    picked[k] = out
    print(f"{k:9s} {len(out):2d} picked from {len(bysrc)} sources ({sum(len(v) for v in bysrc.values())} candidates)")
if COPY:
    import hashlib
    rows = []
    for k, out in picked.items():
        d = os.path.join(DST, k); os.makedirs(d, exist_ok=True)
        seen = set(); uniq = []
        for src, path in out:      # the same hit often sits in two places in a library
            h = hashlib.md5(open(path, "rb").read()).hexdigest()
            if h not in seen: seen.add(h); uniq.append((src, path))
        first = []
        for src, _ in uniq:
            if src not in first: first.append(src)
        out = sorted(uniq, key=lambda t: first.index(t[0]))   # files from one source sit together
        for i, (src, path) in enumerate(out, 1):
            name = f"{i:02d}.wav"     # plain numbers: the source is only in sources.csv
            shutil.copyfile(path, os.path.join(d, name))
            rows.append([k, name, src, os.path.relpath(path, SRC)])
    with open(os.path.join(DST, "sources.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["sound", "file", "source", "original"]); w.writerows(rows)
    print("copied", len(rows))
else:
    for k, out in picked.items():
        print("--", k); [print("   ", s, "|", os.path.relpath(p, SRC)[:90]) for s, p in out[:8]]
