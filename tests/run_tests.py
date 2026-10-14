#!/usr/bin/env python3
"""OCKM_GENERATOR test suite.

Runs the patch headless in Pure Data (vanilla Pd, not plugdata) and checks that the
important behaviour still works: sounds, accents, patterns, swing, the bass generator,
the bass engines, effects and MIDI clock.

Usage:
  python3 tests/run_tests.py            run everything (about 2 minutes, it plays in real time)
  python3 tests/run_tests.py swing bass  run only tests whose names contain these words

Needs the `pd` command. On the Pi: `sudo apt install puredata`. On a Mac, install Pd vanilla
from puredata.info and set PD=/Applications/Pd-0.55-2.app/Contents/Resources/bin/pd (or similar).
It works on a temporary copy, so your patterns are never touched.
"""
import os, sys, shutil, subprocess, tempfile, wave, struct, math, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PD = os.environ.get("PD") or shutil.which("pd") or shutil.which("puredata")


def find_pdlua():
    """The folder holding pdlua (the Lua loader the touchscreen needs). plugdata has it built in;
    plain Pd needs it installed (deken: pdlua, or apt: pd-lua 0.12 or newer). Set PDLUA=/path to override."""
    cands = [os.environ.get("PDLUA", ""), os.path.expanduser("~/Documents/Pd/externals/pdlua"),
             os.path.expanduser("~/.local/lib/pd/extra/pdlua"), "/usr/lib/pd/extra/pdlua", "/usr/local/lib/pd-externals/pdlua"]
    for c in cands:
        if c and os.path.isdir(c) and any(n.startswith("pdlua.") and not n.endswith(".pd") for n in os.listdir(c)):
            return c
    return None


PDLUA = find_pdlua()
LUA = shutil.which("lua5.4") or shutil.which("lua5.3") or shutil.which("lua")


class Skip(Exception):
    pass

# ---------------------------------------------------------------- helpers
class Harness:
    """Builds a small test patch: timed messages, printed receives, optional recording."""
    def __init__(self, dut=None):
        self.objs, self.cons, self.t = [], [], 0
        self.add("#X declare -path voices -path seq;", raw=True)
        self.lb = self.add("#X obj 10 10 loadbang;")
        self.dsp = self.add("#X msg 10 40 \\; pd dsp 1;"); self.con(self.lb, self.dsp)
        self.prev = self.lb
        self.dut = None
        if dut:
            r = self.add("#X obj 400 10 r test-in;")
            self.dut = self.add(f"#X obj 400 40 {dut};")
            self.con(r, self.dut)

    def add(self, line, raw=False):
        self.objs.append((line, raw))
        return sum(1 for _, r in self.objs if not r) - 1

    def con(self, a, b, outlet=0, inlet=0):
        self.cons.append((a, outlet, b, inlet))

    def at(self, ms, msg):
        """Send a message (Pd 'semicolon' message text, e.g. 'ockm-play 1') at time ms."""
        d = self.add(f"#X obj 10 80 delay {max(ms - self.t, 0)};")
        self.con(self.prev, d)
        m = self.add("#X msg 10 110 \\; " + msg.replace(";", "\\;").replace(",", "\\,") + ";")
        self.con(d, m)
        self.prev, self.t = d, ms

    def show(self, *names):
        for n in names:
            r = self.add(f"#X obj 200 10 r {n};"); p = self.add(f"#X obj 200 40 print {n};"); self.con(r, p)

    def record(self, path, source="master"):
        w = self.add("#X obj 600 40 writesf~ 1;")
        r = self.add("#X obj 600 10 r test-wav;"); self.con(r, w)
        if source == "master":
            s = self.add("#X obj 700 10 r~ ockm-master;"); self.con(s, w)
        else:
            self.con(self.dut, w)
        self.wav = path
        self.at(self.t, f"test-wav open {path} , start")

    def finish(self, ms, path):
        if hasattr(self, "wav"):
            self.at(ms, "test-wav stop")
            ms += 600
        self.at(ms, "pd quit")
        lines = ["#N canvas 0 0 800 600 12;"] + [l for l, _ in self.objs]
        lines += [f"#X connect {a} {o} {b} {i};" for a, o, b, i in self.cons]
        lines += ["#X obj 10 500 declare -path voices -path seq;"]
        open(path, "w").write("\n".join(lines) + "\n")


def run(work, harness_file, with_main=True, timeout=60):
    cmd = [PD, "-nogui", "-nosound", "-nomidi", "-stderr"]
    if PDLUA:
        cmd += ["-path", PDLUA, "-lib", "pdlua"]
    if with_main:
        cmd += ["-open", "OCKM_GENERATOR.pd"]
    cmd += ["-open", harness_file]
    p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=timeout)
    return p.stdout + p.stderr


def printed(out, name):
    vals = []
    for line in out.splitlines():
        if line.startswith(name + ":"):
            vals.append(line.split(":", 1)[1].strip())
    return vals


def read_wav(path):
    w = wave.open(path)
    n, sr = w.getnframes(), w.getframerate()
    data = struct.unpack(f"<{n}h", w.readframes(n))
    return [v / 32767 for v in data], sr


def play(work, h, name, with_main=True, ms=None):
    """Run a harness that records; retry a couple of times if the file comes back empty."""
    f = os.path.join(work, name + ".pd")
    h.finish(ms if ms is not None else h.t, f)
    for _ in range(3):
        if os.path.exists(h.wav):
            os.remove(h.wav)
        out = run(work, f, with_main)
        if os.path.exists(h.wav) and wave.open(h.wav).getnframes() > 0:
            return out, read_wav(h.wav)
    raise RuntimeError("recording came back empty")


def peak(x): return max(abs(v) for v in x) if x else 0.0


def cycles_per_second(x, sr):
    """Pitch estimate: smooth away overtones, then count upward zero crossings."""
    k = max(1, int(sr / 250))
    sm, acc = [], 0.0
    for i, v in enumerate(x):
        acc += v
        if i >= k: acc -= x[i - k]
        sm.append(acc / k)
    mean = sum(sm) / len(sm)
    sm = [v - mean for v in sm]
    z = sum(1 for i in range(1, len(sm)) if sm[i - 1] < 0 <= sm[i])
    return z / (len(x) / sr)


# ---------------------------------------------------------------- tests
TESTS = []
def test(fn): TESTS.append(fn); return fn

@test
def loads_clean(work):
    h = Harness(); h.at(300, "pd quit")
    f = os.path.join(work, "t_load.pd"); h.finish(300, f)
    out = run(work, f)
    bad = [l for l in out.splitlines() if re.search(r"error|couldn't create|connection failed", l, re.I)]
    if not PDLUA:   # without pdlua the screen can't load; the engine still must
        bad = [l for l in bad if "ockm-ui" not in l]
    assert not bad, "problems while loading: " + " | ".join(bad[:5])

@test
def drum_voices_sound_and_respond(work):
    for v in ["kick", "snare", "clap", "rim", "hat", "ohat", "tom", "perc"]:
        h = Harness(dut=f"ockm-{v} x")
        h.record(os.path.join(work, f"v_{v}.wav"), source="dut")
        h.at(50, "test-in 1"); h.at(650, "test-in 0.5")
        _, (s, sr) = play(work, h, f"t_voice_{v}", with_main=False, ms=1250)
        a, b = peak(s[int(0.05 * sr):int(0.6 * sr)]), peak(s[int(0.65 * sr):int(1.2 * sr)])
        assert a > 0.05, f"{v} is silent"
        assert 0.35 < b / a < 0.65, f"{v}: half-strength hit should be about half as loud ({b / a:.2f})"
    h = Harness(dut="ockm-kick x"); h.record(os.path.join(work, "v_tune.wav"), source="dut")
    h.at(50, "test-in 1"); h.at(600, "ockm-x-tune 12"); h.at(610, "test-in 1")
    _, (s, sr) = play(work, h, "t_tune", with_main=False, ms=1100)
    f0 = cycles_per_second(s[int(0.08 * sr):int(0.2 * sr)], sr)
    f1 = cycles_per_second(s[int(0.64 * sr):int(0.76 * sr)], sr)
    assert 1.6 < f1 / f0 < 2.4, f"kick tuned +12 should be about twice the pitch ({f0:.0f} -> {f1:.0f})"

@test
def accents_and_step_edits(work):
    h = Harness(dut="ockm-row zz"); h.show("test-out")
    h.add("#X obj 400 70 print ROWOUT;"); h.con(h.dut, len([o for o in h.objs if not o[1]]) - 1)
    h.at(100, "ockm-pat-zz 0 1 2 0 ; ockm-accent 0.3")
    h.at(120, "test-in 0 , 1 , 2")
    h.at(150, "ockm-edit d1 3 2 ; ockm-bass-edit 0 40 1 1 0")
    g = h.add("#X obj 10 300 r test-get;"); t = h.add("#X obj 10 330 t b b;")
    a1 = h.add("#X obj 10 360 array get ockm-pat-d1;"); p1 = h.add("#X obj 10 390 print KICK;")
    a2 = h.add("#X obj 150 360 array get ockm-pat-bass-note 0 1;"); p2 = h.add("#X obj 150 390 print BASSNOTE;")
    for c in [(g, t), (a1, p1), (a2, p2)]: h.con(*c)
    h.con(t, a1, 1); h.con(t, a2, 0)
    h.at(200, "test-get bang")
    f = os.path.join(work, "t_accent.pd"); h.finish(300, f)
    out = run(work, f)
    assert printed(out, "ROWOUT") == ["0.7", "1"], f"accent strengths wrong: {printed(out, 'ROWOUT')}"
    assert printed(out, "KICK")[0].split()[3] == "2", "ockm-edit did not set drum slot 1 step 4 to accent"
    assert printed(out, "BASSNOTE")[0] == "40", "ockm-bass-edit did not set bass step 1"

@test
def pattern_save_and_reload(work):
    h = Harness()
    h.at(100, "ockm-want 7")
    h.at(200, "ockm-pat-d1 0 1 0 1 1 0 0 0 0 0 0 1 0 0 0 0 1 ; ockm-save bang")
    h.at(300, "ockm-want 0"); h.at(400, "ockm-want 7")
    g = h.add("#X obj 10 300 r test-get;"); a = h.add("#X obj 10 330 array get ockm-pat-d1 0 16;"); p = h.add("#X obj 10 360 print RELOADED;")
    h.con(g, a); h.con(a, p)
    h.at(500, "test-get bang")
    f = os.path.join(work, "t_save.pd"); h.finish(600, f)
    out = run(work, f)
    want = "1 0 1 1 0 0 0 0 0 0 1 0 0 0 0 1"
    assert printed(out, "RELOADED") == [want], f"reload gave {printed(out, 'RELOADED')}"
    line = [l for l in open(os.path.join(work, "projects", "default", "p8.txt")).read().split(";") if "ockm-pat-d1 " in l][0]
    assert " ".join(line.split()[2:18]) == want, "pattern 8 not written to disk"

def show_values(h, names, label):
    """Print the on-screen value of each setting (via its ockm-show-... hook) as label-name: value."""
    for n in names:
        r = h.add(f"#X obj 700 300 r ockm-show-{n};"); pr = h.add(f"#X obj 700 330 print {label}-{n};"); h.con(r, pr)

def last(out, name):
    v = printed(out, name)
    return v[-1].replace("set ", "") if v else None

@test
def kit_stays_synths_follow_pattern(work):
    h = Harness()
    keys = ["bass-engine", "d1-tune", "lead-engine"]
    show_values(h, keys, "V")
    r = h.add("#X obj 900 300 r ockm-snap;"); pr = h.add("#X obj 900 330 print SNAP;"); h.con(r, pr)
    tb = h.add("#X obj 900 360 t b;"); a = h.add("#X obj 900 390 array get ockm-pat-d1 0 16;"); pa = h.add("#X obj 900 420 print D1;")
    h.con(r, tb); h.con(tb, a); h.con(a, pa)
    h.at(200, "ockm-bass-engine 2 ; ockm-d1-tune 3")
    h.at(300, "ockm-want 1"); h.at(350, "ockm-snap a")                       # pattern 2: own synth sounds, same kit
    h.at(400, "ockm-want 0"); h.at(450, "ockm-snap b")                       # back to pattern 1: edits kept
    h.at(500, "ockm-lead-engine 1 ; ockm-want 5"); h.at(550, "ockm-snap c")  # empty pattern 6 inherits synth sounds
    f = os.path.join(work, "t_kit.pd"); h.finish(650, f)
    lines = run(work, f).splitlines()
    def at_snap(lab, key):
        i = next(i for i, l in enumerate(lines) if l.startswith(f"SNAP: {lab}"))
        vals = [l for l in lines[:i] if l.startswith(f"V-{key}:")]
        return vals[-1].split("set ")[-1].strip() if vals else None
    assert at_snap("a", "bass-engine") == "0" and at_snap("a", "d1-tune") == "3", f"pattern 2 should have its own bass sound but the same kit ({at_snap('a','bass-engine')}, {at_snap('a','d1-tune')})"
    assert at_snap("b", "bass-engine") == "2", "pattern 1's bass sound should be kept after switching away and back"
    assert at_snap("c", "lead-engine") == "1" and at_snap("c", "bass-engine") == "2", "a new empty pattern should keep the current synth sounds"
    d1 = [l for l in lines if l.startswith("D1:")]
    assert d1[-1].split(":", 1)[1].split() == ["0"] * 16, "a new empty pattern should start with blank steps"

@test
def save_quit_and_reopen(work):
    h = Harness()
    h.at(200, "ockm-bpm 131 ; ockm-d2-decay 150 ; ockm-bass-engine 5 ; ockm-swing 60 ; ockm-length 32")
    h.at(300, "ockm-save bang")
    f = os.path.join(work, "t_save1.pd"); h.finish(400, f); run(work, f)
    h = Harness(); show_values(h, ["bpm", "d2-decay", "bass-engine", "swing", "len"], "V")
    h.at(200, "ockm-resync bang")
    f = os.path.join(work, "t_save2.pd"); h.finish(400, f)
    out = run(work, f)
    got = {k: last(out, f"V-{k}") for k in ["bpm", "d2-decay", "bass-engine", "swing", "len"]}
    assert got == {"bpm": "131", "d2-decay": "150", "bass-engine": "5", "swing": "60", "len": "32"}, f"settings not restored after reopening: {got}"

@test
def revert_goes_back_to_saved(work):
    h = Harness(); show_values(h, ["d1-tune", "lead-k1"], "V")
    h.at(200, "ockm-d1-tune 7 ; ockm-lead-k1 0.9 ; ockm-pat-d1 0 1 1 1 1")
    h.at(300, "ockm-revert bang")
    g = h.add("#X obj 10 300 r test-get;"); a = h.add("#X obj 10 330 array get ockm-pat-d1 0 4;"); pa = h.add("#X obj 10 360 print D1;"); h.con(g, a); h.con(a, pa)
    h.at(400, "test-get bang")
    f = os.path.join(work, "t_revert.pd"); h.finish(500, f)
    out = run(work, f)
    assert last(out, "V-d1-tune") == "0" and last(out, "V-lead-k1") == "0.55", "revert should restore the saved settings"
    assert printed(out, "D1")[-1].split() == ["1", "0", "0", "0"], "revert should restore the saved steps"

@test
def drum_slot_switches_sound(work):
    rates = []
    for snd in [0, 4]:
        h = Harness(dut="ockm-drum zz")
        h.record(os.path.join(work, f"slot{snd}.wav"), source="dut")
        h.at(20, f"ockm-zz-sound {snd}"); h.at(60, "test-in 1")
        _, (s, sr) = play(work, h, f"t_slot{snd}", with_main=False, ms=400)
        x = s[int(0.06 * sr):int(0.1 * sr)]
        assert peak(x) > 0.05, f"slot is silent with sound {snd}"
        rates.append(sum(1 for i in range(1, len(x)) if x[i - 1] < 0 <= x[i]) / 0.04)
    assert rates[0] < 400 < 2000 < rates[1], f"sound 0 should be a low kick and 4 a bright hat, got {rates}"

@test
def longer_patterns_and_pages(work):
    h = Harness(); h.show("ockm-step")
    h.at(100, "ockm-length 32")
    h.at(150, "ockm-page 1 ; ockm-sq-d1-1 1")
    g = h.add("#X obj 10 300 r test-get;"); a = h.add("#X obj 10 330 array get ockm-pat-d1 0 32;"); pr = h.add("#X obj 10 360 print PAT;")
    h.con(g, a); h.con(a, pr)
    h.at(200, "test-get bang")
    h.at(300, "ockm-play 1"); h.at(300 + 32 * 15000 / 124 + 30, "ockm-play 0")
    f = os.path.join(work, "t_len.pd"); h.finish(4600, f)
    out = run(work, f)
    pat = [int(float(x)) for x in printed(out, "PAT")[0].split()]
    assert pat[16:32] == [1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0], f"steps 17-32 should repeat 1-16, plus the edit on step 18: {pat[16:32]}"
    assert pat[0:16] == [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0], "editing page 2 changed page 1"
    steps = [int(float(x)) for x in printed(out, "ockm-step")]
    assert steps[:33] == list(range(32)) + [0], f"a 32-step pattern should count 1-32 then wrap: {steps[:34]}"

@test
def swing_and_bar_quantised_switching(work):
    h = Harness()
    t = h.add("#X obj 300 300 r ockm-step;"); tr = h.add("#X obj 300 330 t f b;")
    tm = h.add("#X obj 300 360 timer;"); pk = h.add("#X obj 300 390 pack f f;"); pr = h.add("#X obj 300 420 print STEPAT;")
    st = h.add("#X obj 400 300 r test-t0;")
    h.con(t, tr); h.con(tr, tm, 1, 1); h.con(tm, pk, 0, 1); h.con(tr, pk, 0, 0); h.con(pk, pr); h.con(st, tm)
    h.show("ockm-load")
    h.at(100, "test-t0 bang ; ockm-play 1")
    h.at(1000, "ockm-want 2")
    f = os.path.join(work, "t_swing.pd"); h.finish(2300, f)
    out = run(work, f)
    pairs = [tuple(map(float, v.split())) for v in printed(out, "STEPAT")]
    step = 15000 / 124
    for s_, t_ in pairs[:16]:
        expect = s_ * step + (step * 0.12 if int(s_) % 2 else 0)
        assert abs(t_ - expect) < 1.5, f"step {int(s_)} at {t_:.1f}ms, expected {expect:.1f}ms (56% swing)"
    loads = printed(out, "ockm-load")
    assert loads[-1] == "2", "pattern switch did not happen"
    i = next(i for i, l in enumerate(out.splitlines()) if l.startswith("ockm-load: 2"))
    after = [l for l in out.splitlines()[i:] if l.startswith("STEPAT")]
    assert after and after[0].split()[1] == "0", "pattern switched mid-bar instead of at the start of the bar"

@test
def bass_generator(work):
    h = Harness()
    def grab(ms, label):
        g = h.add(f"#X obj 10 300 r test-{label};"); t = h.add("#X obj 10 330 t b b b;")
        for i, nm in enumerate(["note", "on", "acc"]):
            a = h.add(f"#X obj 10 360 array get ockm-pat-bass-{nm} 0 16;"); l = h.add(f"#X obj 10 390 list prepend {label}-{nm};")
            p = h.add("#X obj 10 420 list trim;"); pr = h.add("#X obj 10 450 print GEN;")
            h.con(t, a, 2 - i); h.con(a, l); h.con(l, p); h.con(p, pr)
        h.con(g, t)
        h.at(ms, f"test-{label} bang")
    h.at(100, "ockm-bass-notes 0 ; ockm-bass-rhythm 0"); grab(150, "a")
    h.at(200, "ockm-bass-notes 3 ; ockm-bass-rhythm 3"); grab(250, "b")
    h.at(300, "ockm-root 0 ; ockm-scale 3 ; ockm-bass-notes 6 ; ockm-bass-rhythm 1"); grab(350, "c")
    f = os.path.join(work, "t_gen.pd"); h.finish(450, f)
    out = run(work, f)
    got = {v.split()[0]: [int(float(x)) for x in v.split()[1:]] for v in printed(out, "GEN")}
    def hits(label): return [n for n, o in zip(got[label + "-note"], got[label + "-on"]) if o]
    assert got["a-on"] == [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0], "offbeat rhythm wrong"
    assert hits("a") == [33] * 4, "root notes in A minor should all be 33"
    assert hits("b") == [33, 33, 45, 33, 36, 33, 43, 40, 33, 33, 45, 33, 36], f"acid riff wrong: {hits('b')}"
    assert hits("c") == [36, 36, 31, 32] * 3, f"dub pattern in C phrygian wrong: {hits('c')}"

@test
def bass_generator_fills_long_patterns(work):
    h = Harness()
    h.at(100, "ockm-length 32 ; ockm-bass-notes 4 ; ockm-bass-rhythm 0")
    g = h.add("#X obj 10 300 r test-get;"); t = h.add("#X obj 10 330 t b b;")
    a1 = h.add("#X obj 10 360 array get ockm-pat-bass-on 0 32;"); p1 = h.add("#X obj 10 390 print ON;")
    a2 = h.add("#X obj 150 360 array get ockm-pat-bass-note 0 32;"); p2 = h.add("#X obj 150 390 print NOTE;")
    h.con(g, t); h.con(t, a1, 1); h.con(a1, p1); h.con(t, a2, 0); h.con(a2, p2)
    h.at(200, "test-get bang")
    f = os.path.join(work, "t_gen32.pd"); h.finish(300, f)
    out = run(work, f)
    on = [int(float(x)) for x in printed(out, "ON")[0].split()]
    note = [int(float(x)) for x in printed(out, "NOTE")[0].split()]
    assert on[16:] == on[:16] and sum(on) == 8, f"rhythm should repeat across 32 steps: {on}"
    hits = [n for n, o in zip(note, on) if o]
    assert hits == [33, 35, 36, 40] * 2, f"walk-up notes should carry on through bar 2: {hits}"

@test
def lead_plays_two_octaves_up(work):
    h = Harness()
    h.at(100, "ockm-lead-notes 1 ; ockm-lead-rhythm 0")
    g = h.add("#X obj 10 300 r test-get;"); t = h.add("#X obj 10 330 t b b;")
    a1 = h.add("#X obj 10 360 array get ockm-pat-lead-on 0 16;"); p1 = h.add("#X obj 10 390 print ON;")
    a2 = h.add("#X obj 150 360 array get ockm-pat-lead-note 0 16;"); p2 = h.add("#X obj 150 390 print NOTE;")
    h.con(g, t); h.con(t, a1, 1); h.con(a1, p1); h.con(t, a2, 0); h.con(a2, p2)
    h.at(200, "test-get bang")
    f = os.path.join(work, "t_lead.pd"); h.finish(300, f)
    out = run(work, f)
    on = [int(float(x)) for x in printed(out, "ON")[0].split()]
    note = [int(float(x)) for x in printed(out, "NOTE")[0].split()]
    hits = [n for n, o in zip(note, on) if o]
    assert hits == [57, 69, 57, 69], f"lead octaves pattern in A minor should be A3 A4, got {hits}"

@test
def chord_notes_follow_key_scale_and_type(work):
    h = Harness(dut="ockm-chordseq zz")
    h.add("#X obj 400 120 ockm-presets;")
    pr = h.add("#X obj 400 90 print CHORD;"); h.con(h.dut, pr)
    h.at(100, "ockm-pat-zz-on 0 1 1 1 2 ; ockm-pat-zz-deg 0 0 5 0 0 ; ockm-zz-smooth 0")
    h.at(120, "test-in 0"); h.at(140, "test-in 1")
    h.at(160, "ockm-zz-type 1"); h.at(170, "test-in 2")
    h.at(190, "ockm-root 0 ; ockm-scale 1 ; ockm-zz-type 0"); h.at(200, "test-in 3")
    h.at(220, "ockm-root 9 ; ockm-scale 0 ; ockm-zz-smooth 1"); h.at(230, "test-in 1")        # smooth: VI folds down
    h.at(240, "ockm-zz-type 7"); h.at(250, "test-in 0")                                      # spice 4: eleventh
    f = os.path.join(work, "t_chord.pd"); h.finish(300, f)
    got = [[float(x) for x in v.split()] for v in printed(run(work, f, with_main=False), "CHORD")]
    want = [[45, 48, 52, 0, 0.75], [53, 57, 60, 0, 0.75], [45, 48, 52, 55, 0.75], [48, 52, 55, 0, 1],
            [53, 45, 48, 0, 0.75], [45, 55, 47, 50, 0.75]]
    assert got == want, f"chords wrong (A minor i, VI, i7, C major i accented, smooth VI, A minor 11): {got}"

@test
def chord_progressions_fill_and_lengthen(work):
    h = Harness(); h.show("ockm-len")
    h.at(100, "ockm-resync bang ; ockm-chord-rhythm 0 ; ockm-chord-prog 4")       # garage: half-bar changes, 2 bars
    g = h.add("#X obj 10 300 r test-get;"); t = h.add("#X obj 10 330 t b b;")
    a1 = h.add("#X obj 10 360 array get ockm-pat-chord-deg 0 32;"); p1 = h.add("#X obj 10 390 print DEG;")
    a2 = h.add("#X obj 200 360 array get ockm-pat-chord-on 0 32;"); p2 = h.add("#X obj 200 390 print ON;")
    h.con(g, t); h.con(t, a1, 1); h.con(t, a2, 0); h.con(a1, p1); h.con(a2, p2)
    h.at(200, "test-get bang")
    f = os.path.join(work, "t_prog.pd"); h.finish(300, f)
    out = run(work, f)
    assert "32" in printed(out, "ockm-len"), f"a 2-bar progression should make a 16-step pattern 32 long: {printed(out, 'ockm-len')}"
    deg = [int(float(x)) for x in printed(out, "DEG")[0].split()]
    assert deg == [0] * 8 + [5] * 8 + [3] * 8 + [4] * 8, f"garage should change chord every half bar (i VI iv v): {deg}"
    on = [int(float(x)) for x in printed(out, "ON")[0].split()]
    assert on[0] == 2 and on[16] == 2 and sum(on) == 4, f"bar-pads rhythm: one accented chord per bar: {on}"

@test
def chord_engines_sound(work):
    for eng, name in enumerate(["stab", "organ", "pad"]):
        h = Harness(dut="ockm-chord zz")
        h.record(os.path.join(work, f"c_{name}.wav"), source="dut")
        h.at(20, f"ockm-zz-engine {eng} ; ockm-zz-k1 0.5 ; ockm-zz-k2 0.5 ; ockm-zz-k3 0.2 ; ockm-zz-k4 0.5")
        h.at(60, "test-in 45 48 52 0 1")
        _, (s, sr) = play(work, h, f"t_chord_{name}", with_main=False, ms=900)
        x = s[int(0.08 * sr):int(0.4 * sr)]
        assert 0.02 < peak(x) < 1.0, f"{name} chord level {peak(x):.2f}"

@test
def bass_engines_play_in_tune(work):
    for eng, name in enumerate(["acid", "sub", "fm", "reese", "pluck", "saw"]):
        h = Harness(dut="ockm-mono zz")
        h.record(os.path.join(work, f"b_{name}.wav"), source="dut")
        h.at(20, f"ockm-zz-engine {eng} ; ockm-zz-k1 0.5 ; ockm-zz-k2 0.3 ; ockm-zz-k3 0 ; ockm-zz-k4 0.9 ; ockm-zz-drive 0")
        h.at(50, "test-in 33 0 0 1")
        _, (s, sr) = play(work, h, f"t_bass_{name}", with_main=False, ms=650)
        x = s[int(0.15 * sr):int(0.5 * sr)]
        assert peak(x) > 0.02, f"{name} engine is silent"
        f0 = cycles_per_second(x, sr)
        assert 45 < f0 < 68, f"{name} engine plays {f0:.0f}Hz for A1, expected about 55Hz"

@test
def delay_echoes_on_time(work):
    h = Harness(dut="ockm-fx")
    h.add("#X obj 500 10 r test-click;"); click = len([o for o in h.objs if not o[1]]) - 1
    v = h.add("#X obj 500 40 vline~;"); h.con(click, v); h.con(v, h.dut)
    h.add("#X obj 600 10 r test-click;"); c2 = len([o for o in h.objs if not o[1]]) - 1
    tw = h.add("#X obj 600 40 vline~;"); thr = h.add("#X obj 600 70 throw~ ockm-dlybus;"); h.con(c2, tw); h.con(tw, thr)
    h.record(os.path.join(work, "fx.wav"), source="dut")
    h.at(20, "ockm-stepms 100 ; ockm-delay-steps 3 ; ockm-delay-mix 0.5 ; ockm-delay-fb 0.5 ; ockm-verb-mix 0 ; ockm-drive 0 ; ockm-filter 0")
    h.at(50, "test-click 1 , 0 5")
    _, (s, sr) = play(work, h, "t_fx", with_main=False, ms=1300)
    on = next(i for i, v in enumerate(s) if abs(v) > 0.05)
    lv = [peak(s[on + int((k * 0.3 - 0.02) * sr):on + int((k * 0.3 + 0.03) * sr)]) for k in range(4)]
    gap = peak(s[on + int(0.13 * sr):on + int(0.17 * sr)])
    assert lv[1] > 0.1 and lv[2] < lv[1] and lv[3] < lv[2], f"echo levels wrong {lv}"
    assert gap < 0.01, "sound between echoes: delay time is wrong"

@test
def reverb_size_changes_tail(work):
    tails = []
    for size in [0, 1]:
        h = Harness(dut="ockm-verb")
        h.add("#X obj 500 10 r test-click;"); c = len([o for o in h.objs if not o[1]]) - 1
        v = h.add("#X obj 500 40 vline~;"); h.con(c, v); h.con(v, h.dut)
        h.record(os.path.join(work, f"verb{size}.wav"), source="dut")
        h.at(20, f"ockm-verb-size {size} ; ockm-verb-tone 0.5")
        h.at(50, "test-click 1 , 0 2")
        _, (s, sr) = play(work, h, f"t_verb{size}", with_main=False, ms=4000)
        tails.append(peak(s[int(1.5 * sr):int(2.0 * sr)]))
    assert tails[1] > tails[0] * 5, f"bigger size should ring much longer {tails}"
    assert tails[1] < 0.2, "reverb at full size is not dying away"

@test
def midi_clock_leader(work):
    h = Harness(); h.show("ockm-clock-sent")
    h.at(100, "ockm-play 1"); h.at(100 + 1935.5, "ockm-play 0")
    f = os.path.join(work, "t_lead.pd"); h.finish(2300, f)
    sent = printed(run(work, f), "ockm-clock-sent")
    assert sent[0] == "250" and sent[-1] == "252", "start/stop not sent"
    assert sent.count("248") == 97, f"expected 96 clocks per bar plus the next downbeat, got {sent.count('248')}"

@test
def midi_clock_follower(work):
    h = Harness(); h.show("ockm-step", "ockm-bpm")
    h.at(100, "ockm-sync 1 ; ockm-midi-rt 250")
    m = h.add("#X obj 600 300 metro 20;"); ms_ = h.add("#X msg 600 330 \\; ockm-midi-rt 248;"); h.con(m, ms_)
    r = h.add("#X obj 600 270 r test-clock;"); h.con(r, m)
    h.at(100, "test-clock 1"); h.at(100 + 3840, "test-clock 0 ; ockm-midi-rt 252")
    f = os.path.join(work, "t_follow.pd"); h.finish(4300, f)
    out = run(work, f)
    steps = printed(out, "ockm-step")
    assert steps == [str(i % 16) for i in range(32)], f"follower steps wrong: {steps}"
    assert printed(out, "ockm-bpm")[-1] == "125", f"tempo not measured: {printed(out, 'ockm-bpm')}"

@test
def full_mix_does_not_clip(work):
    h = Harness(); h.record(os.path.join(work, "mix.wav"))
    h.at(100, "ockm-want 1 ; ockm-play 1"); h.at(4000, "ockm-want 2"); h.at(8000, "ockm-play 0")
    _, (s, sr) = play(work, h, "t_mix", ms=8000)
    assert 0.1 < peak(s) < 0.99, f"mix peak {peak(s):.2f}"


# ---------------------------------------------------------------- runner
@test
def front_panel_drives_the_engine(work):
    h = Harness(); h.show("ockm-load", "ockm-len", "ockm-ui-d2-5", "ockm-ui-ph-2")
    h.at(100, "ockm-ui-d2-5 1")                          # click slot 2, step 6
    h.at(150, "ockm-ui-accmode 1 ; ockm-ui-d3-1 1 ; ockm-ui-accmode 0")   # accented click
    h.at(200, "ockm-ui-len 1")                            # length button 2 = 32 steps
    h.at(250, "ockm-page 1 ; ockm-ui-d1-1 1")             # page 2, step 18
    g = h.add("#X obj 10 300 r test-get;"); t = h.add("#X obj 10 330 t b b b;")
    for i, nm in enumerate(["d1", "d2", "d3"]):
        a = h.add(f"#X obj {10+i*150} 360 array get ockm-pat-{nm} 0 32;"); p = h.add(f"#X obj {10+i*150} 390 print PAT-{nm};")
        h.con(t, a, 2 - i); h.con(a, p)
    h.con(g, t)
    h.at(300, "test-get bang")
    h.at(350, "ockm-page 0 ; ockm-ui-slot 2")             # pattern button 3
    h.at(500, "ockm-play 1"); h.at(500 + 3 * 15000 / 124 + 20, "ockm-play 0")
    f = os.path.join(work, "t_panel.pd"); h.finish(1200, f)
    out = run(work, f)
    pat = {nm: [int(float(x)) for x in printed(out, f"PAT-{nm}")[0].split()] for nm in ("d1", "d2", "d3")}
    assert pat["d2"][5] == 1, f"clicking slot 2 step 6 didn't set it: {pat['d2'][:16]}"
    assert pat["d3"][1] == 2, f"accent-mode click should set an accent: {pat['d3'][:16]}"
    assert "32" in printed(out, "ockm-len"), "length button didn't set 32 steps"
    assert pat["d1"][17] == 1, f"page 2 click should set step 18: {pat['d1'][16:32]}"
    assert "2" in printed(out, "ockm-load"), "pattern button didn't load pattern 3"
    ui = printed(out, "ockm-ui-d2-5")
    assert any(x.startswith("set 1") for x in ui) and any(x.startswith(("color #ededed", "color #1a1a1a")) for x in ui), f"square wasn't redrawn as a hit: {ui}"
    assert any(x.startswith(("color #ff5a24", "color #ff4f1a")) for x in printed(out, "ockm-ui-ph-2")), "playhead didn't light step 3"

@test
def touchscreen_drives_the_engine(work):
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-edit", "ockm-page", "ockm-len", "ockm-load", "ockm-d1-sound", "ockm-bass-edit", "ockm-want", "ockm-lead-k1", "ockm-filter", "ockm-chord-prog", "ockm-chord-type", "ockm-d1-mute", "ockm-d2-mute", "ockm-bass-level")
    tap = lambda ms, x, y: h.at(ms, f"ockm-ui-test tap {x} {y}")
    h.at(100, "ockm-resync bang")
    tap(150, 50, 137)                    # perform: open the kick lane
    tap(160, 300, 312)                   # drums: sound pad 3 (clap)
    tap(170, 160, 212); tap(180, 160, 212)   # step 3: on, then accent
    tap(190, 287, 36)                    # perform tab
    tap(200, 462, 88)                    # length 32 (navigation strip)
    tap(210, 379, 36)                    # drums tab (back to the kick slot)
    h.at(220, "ockm-ui-test drag 600 212 200 212")   # swipe left: steps 17-32
    tap(230, 45, 212)                    # step 17
    h.at(240, "ockm-ui-test drag 200 212 600 212")   # swipe right: back to 1-16
    tap(245, 922, 88)                    # forward arrow (steps 17-32)
    tap(248, 644, 88)                    # back arrow (steps 1-16)
    tap(250, 287, 36)                    # perform tab
    tap(255, 244, 467); tap(258, 128, 512)   # synth half: lead, then its first knob
    tap(260, 50, 369)                    # open bass from its lane
    tap(270, 45, 158)                    # bass step 1
    tap(280, 600, 236)                   # note picker: third note of the scale
    tap(290, 287, 36)                    # perform tab
    tap(300, 149, 88)                    # pattern 3 (navigation strip)
    tap(310, 543, 486)                   # master fx: filter, middle
    tap(320, 655, 36)                    # chord tab
    tap(330, 187, 328)                   # fill view
    tap(335, 430, 399)                   # progression 5 (garage)
    tap(340, 300, 564)                   # spice 3 (ninth)
    tap(345, 287, 36); tap(348, 126, 137)  # perform tab, mute the kick lane
    tap(350, 747, 36)                    # mixer tab
    tap(355, 673, 341)                   # bass fader, halfway
    tap(360, 130, 505)                   # mute on strip 2
    f = os.path.join(work, "t_touch.pd"); h.finish(600, f)
    out = run(work, f)
    edits = printed(out, "ockm-edit")
    assert edits[:2] == ["d1 2 1", "d1 2 2"], f"tapping step 3 should go on, then accent: {edits}"
    assert "2" in printed(out, "ockm-d1-sound"), "sound pad didn't change the slot's sound"
    assert "32" in printed(out, "ockm-len"), "length button didn't set 32"
    pages = printed(out, "ockm-page")
    assert pages.count("1") >= 2 and "0" in pages[pages.index("1") + 1:], f"swipes and block buttons should go to block 2 and back: {pages}"
    assert any(e.startswith("d1 16 ") for e in edits), f"tap after the swipe should edit step 17: {edits}"
    be = printed(out, "ockm-bass-edit")
    assert len(be) >= 2 and be[-1].split()[:2] == ["0", "36"], f"bass step 1 should become C (A minor, third step): {be}"
    assert "2" in printed(out, "ockm-load"), "pattern 3 button didn't load pattern 3"
    lk = [float(x) for x in printed(out, "ockm-lead-k1")]
    assert any(0.4 < x < 0.6 for x in lk), f"perform strip: lead knob 1 should be about halfway: {lk}"
    assert any(abs(float(x)) < 0.1 for x in printed(out, "ockm-filter")), "perform strip: filter in the middle should be about 0"
    assert "4" in printed(out, "ockm-chord-prog"), f"fill: progression 5 should send 4: {printed(out, 'ockm-chord-prog')}"
    assert "1" in printed(out, "ockm-d1-mute"), "perform: M on the kick lane should mute d1"
    assert "1" in printed(out, "ockm-d2-mute"), "mixer: M on strip 2 should mute d2"
    bl = [float(x) for x in printed(out, "ockm-bass-level")]
    assert any(0.4 < x < 0.6 for x in bl), f"mixer: bass fader halfway should be about 0.5: {bl}"
    assert "6" in printed(out, "ockm-chord-type"), f"fill: spice 3 should pick the ninth chord type (6): {printed(out, 'ockm-chord-type')}"
    assert not [l for l in out.splitlines() if "error" in l.lower()], "errors: " + " | ".join(l for l in out.splitlines() if "error" in l.lower())

@test
def touchscreen_screens_draw(work):
    if not LUA:
        raise Skip("lua not found")
    try:
        import PIL  # noqa: F401
    except ImportError:
        raise Skip("Pillow not installed")
    p = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "ui_preview.py"), os.path.join(work, "preview")], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-800:]
    assert len(os.listdir(os.path.join(work, "preview"))) == 9, "expected nine screen pictures"

@test
def mute_solo_and_levels(work):
    h = Harness()
    sig = h.add("#X obj 400 40 sig~ 1;")
    g = {}
    for i, (t, lv) in enumerate([("d1", "nolevel"), ("d2", "nolevel"), ("bass", "level")]):
        g[t] = h.add(f"#X obj {400 + i * 150} 70 ockm-gate {t} {lv};"); h.con(sig, g[t])
        sn = h.add(f"#X obj {400 + i * 150} 100 snapshot~;"); h.con(g[t], sn)
        pr = h.add(f"#X obj {400 + i * 150} 130 print G-{t};"); h.con(sn, pr)
        rb = h.add(f"#X obj {400 + i * 150} 10 r test-snap;"); h.con(rb, sn)
    h.at(100, "test-snap bang")                                   # all open
    h.at(120, "ockm-d1-mute 1"); h.at(160, "test-snap bang")      # d1 muted
    h.at(180, "ockm-d1-mute 0 ; ockm-d2-solo 1"); h.at(220, "test-snap bang")   # d2 soloed: others silent
    h.at(240, "ockm-d2-solo 0 ; ockm-bass-level 0.5"); h.at(280, "test-snap bang")  # no solo, bass at half
    f = os.path.join(work, "t_gate.pd"); h.finish(320, f)
    out = run(work, f)
    got = {t: [round(float(x), 2) for x in printed(out, f"G-{t}")] for t in g}
    assert got["d1"] == [1, 0, 0, 1], f"d1: open, muted, not soloed, open: {got['d1']}"
    assert got["d2"] == [1, 1, 1, 1], f"d2: always open (it's the soloed one): {got['d2']}"
    assert got["bass"] == [1, 1, 0, 0.5], f"bass: open, open, not soloed, half level: {got['bass']}"

def main():
    if not PD:
        sys.exit("Can't find Pure Data. Install it, or set PD=/path/to/pd")
    picks = sys.argv[1:]
    chosen = [t for t in TESTS if not picks or any(p in t.__name__ for p in picks)]
    passed = skipped = 0
    for t in chosen:
        work = tempfile.mkdtemp(prefix="ockm-test-")
        for item in ["OCKM_GENERATOR.pd", "voices", "seq", "ui", "projects"]:
            src = os.path.join(ROOT, item)
            (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, os.path.join(work, item))
        try:
            t(work)
            print(f"PASS  {t.__name__}"); passed += 1
        except Skip as e:
            print(f"SKIP  {t.__name__}: {e}"); skipped += 1
        except Exception as e:
            print(f"FAIL  {t.__name__}: {e}")
        finally:
            shutil.rmtree(work, ignore_errors=True)
    print(f"\n{passed}/{len(chosen)} passed" + (f", {skipped} skipped" if skipped else ""))
    sys.exit(0 if passed + skipped == len(chosen) else 1)

if __name__ == "__main__":
    main()
