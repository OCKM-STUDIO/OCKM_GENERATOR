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
    for v in ["kick", "snare", "clap", "rim", "hat", "ohat", "tom", "perc"] + [n + sfx for sfx in ("b", "c") for n in ["kick", "snare", "clap", "rim", "hat", "ohat", "tom", "perc"]]:
        h = Harness(dut=f"ockm-{v} x")
        h.record(os.path.join(work, f"v_{v}.wav"), source="dut")
        h.at(50, "test-in 1"); h.at(650, "test-in 0.5")
        _, (s, sr) = play(work, h, f"t_voice_{v}", with_main=False, ms=1250)
        A, B = s[int(0.05 * sr):int(0.6 * sr)], s[int(0.65 * sr):int(1.2 * sr)]
        assert peak(A) > 0.05, f"{v} is silent"
        a, b = math.sqrt(sum(x * x for x in A) / len(A)), math.sqrt(sum(x * x for x in B) / len(B))   # average level: metal voices beat, peaks jump about
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
def loop_save_and_reload(work):
    """Save writes the loop to loop.txt; after a change, back to last save reads it back."""
    h = Harness()
    h.at(200, "ockm-pat-d1 0 1 0 1 1 0 0 0 0 0 0 1 0 0 0 0 1 ; ockm-save bang")
    h.at(300, "ockm-pat-d1 const 0")
    h.at(400, "ockm-revert bang")
    g = h.add("#X obj 10 300 r test-get;"); a = h.add("#X obj 10 330 array get ockm-pat-d1 0 16;"); p = h.add("#X obj 10 360 print RELOADED;")
    h.con(g, a); h.con(a, p)
    h.at(500, "test-get bang")
    f = os.path.join(work, "t_save.pd"); h.finish(600, f)
    out = run(work, f)
    want = "1 0 1 1 0 0 0 0 0 0 1 0 0 0 0 1"
    assert printed(out, "RELOADED") == [want], f"reload gave {printed(out, 'RELOADED')}"
    line = [l for l in open(os.path.join(work, "projects", "default", "loop.txt")).read().split(";") if "ockm-pat-d1 " in l][0]
    assert " ".join(line.split()[2:18]) == want, "the loop wasn't written to loop.txt"

def show_values(h, names, label):
    """Print the on-screen value of each setting (via its ockm-show-... hook) as label-name: value."""
    for n in names:
        r = h.add(f"#X obj 700 300 r ockm-show-{n};"); pr = h.add(f"#X obj 700 330 print {label}-{n};"); h.con(r, pr)

def last(out, name):
    v = printed(out, name)
    return v[-1].replace("set ", "") if v else None

@test
def save_quit_and_reopen(work):
    h = Harness()
    h.at(200, "ockm-bpm 131 ; ockm-d2-decay 150 ; ockm-bass-engine 5 ; ockm-swing 60 ; ockm-length 32")
    h.at(300, "ockm-save bang")
    f = os.path.join(work, "t_save1.pd"); h.finish(400, f); run(work, f)
    h = Harness(); show_values(h, ["bpm", "d2-decay", "bass-engine", "swing", "bass-len"], "V")
    h.at(200, "ockm-resync bang")
    f = os.path.join(work, "t_save2.pd"); h.finish(400, f)
    out = run(work, f)
    got = {k: last(out, f"V-{k}") for k in ["bpm", "d2-decay", "bass-engine", "swing", "bass-len"]}
    assert got == {"bpm": "131", "d2-decay": "150", "bass-engine": "5", "swing": "60", "bass-len": "32"}, f"settings not restored after reopening: {got}"

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
def lead_motifs_follow_the_bar(work):
    """A motif melody over a four-bar rhythm: the rhythm runs four bars before it repeats, the idea in bar 1 comes back
    in bar 2, every note on the beat is in the chord, bar 4 comes home to the root, and new gives a different line."""
    h = Harness()
    h.at(100, "ockm-lead-sync 0 ; ockm-lead-len 64 ; ockm-lead-notes 15 ; ockm-lead-rhythm 10")
    g = h.add("#X obj 10 300 r test-get;"); t = h.add("#X obj 10 330 t b b;")
    a1 = h.add("#X obj 10 360 array get ockm-pat-lead-on 0 64;"); p1 = h.add("#X obj 10 390 print ON;")
    a2 = h.add("#X obj 150 360 array get ockm-pat-lead-note 0 64;"); p2 = h.add("#X obj 150 390 print NOTE;")
    h.con(g, t); h.con(t, a1, 1); h.con(a1, p1); h.con(t, a2, 0); h.con(a2, p2)
    h.at(200, "test-get bang")
    h.at(250, "ockm-lead-seed 3")
    h.at(300, "test-get bang")
    f = os.path.join(work, "t_motif.pd"); h.finish(400, f)
    out = run(work, f)
    ons = [[int(float(x)) for x in l.split()] for l in printed(out, "ON")]
    notes = [[int(float(x)) for x in l.split()] for l in printed(out, "NOTE")]
    on, note = ons[0], notes[0]
    assert on[0:16] != on[48:64] and sum(on) > 20, f"the phrase rhythm should run four bars: {on}"
    both = [i for i in range(16) if on[i] and on[16 + i]]
    assert both and all(note[i] == note[16 + i] for i in both), f"bar 2 should say bar 1's idea again: {note[:32]}"
    chord = {9, 0, 4}   # A minor: A C E
    beats = [(i, note[i]) for i in range(64) if on[i] and i % 4 == 0]
    assert all(n % 12 in chord for _, n in beats), f"notes on the beat should be in the chord: {beats}"
    last = max(i for i in range(48, 64) if on[i])
    assert note[last] % 12 == 9, f"bar 4 should come home to the root: {note[48:64]}"
    hits0 = [n for n, o in zip(note, on) if o]; hits1 = [n for n, o in zip(notes[1], ons[1]) if o]
    assert hits0 != hits1, "new should give a different line"

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
    for eng, name in enumerate(["acid", "sub", "fm", "reese", "pluck", "saw", "house"]):
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
def lead_engines_play_in_tune_and_level(work):
    """Every lead engine sounds, plays A2 at about 110 Hz, and sits at a similar level to the others."""
    levels = {}
    for eng, name in enumerate(["acid", "juno", "dx", "sync", "mini"]):
        h = Harness(dut="ockm-lead zz")
        h.record(os.path.join(work, f"l_{name}.wav"), source="dut")
        k1, k3 = (0, 0) if name == "sync" else (0.5, 0.3)   # sync: zero sync, so the pitch counter sees the fundamental
        h.at(20, f"ockm-zz-engine {eng} ; ockm-zz-k1 {k1} ; ockm-zz-k2 0.1 ; ockm-zz-k3 {k3} ; ockm-zz-k4 0.9 ; ockm-zz-drive 0")
        h.at(50, "test-in 45 0 0 1")
        _, (x, sr) = play(work, h, f"t_lead_{name}", with_main=False, ms=650)
        seg = x[int(0.1 * sr):int(0.35 * sr)]
        assert peak(seg) > 0.05, f"{name} lead is silent"
        f0 = cycles_per_second(seg, sr)
        assert 95 < f0 < 128, f"{name} lead plays {f0:.0f} Hz for A2, expected about 110"
        levels[name] = math.sqrt(sum(v * v for v in seg) / len(seg))
    lo, hi = min(levels.values()), max(levels.values())
    assert hi / lo < 4, "lead engines are too far apart in level: " + ", ".join(f"{k} {v:.2f}" for k, v in levels.items())
    print("      lead levels (rms): " + ", ".join(f"{k} {v:.2f}" for k, v in levels.items()))

@test
def chord_engines_sound_and_sit_together(work):
    """Every chord engine sounds, the sine-based ones in tune (A3 = 220 Hz), and all at a similar level to each other."""
    levels = {}
    for eng, name in enumerate(["stab", "organ", "pad", "piano", "rhodes", "strings"]):
        h = Harness(dut="ockm-chord zz")
        h.record(os.path.join(work, f"c_{name}.wav"), source="dut")
        h.at(20, f"ockm-zz-engine {eng} ; ockm-zz-k1 0.5 ; ockm-zz-k2 0.3 ; ockm-zz-k3 0.3 ; ockm-zz-k4 0.6")
        h.at(50, "test-in 57 0 0 0 1")        # just the root, to check the pitch
        h.at(700, "test-in off")
        h.at(1000, "test-in 57 60 64 0 1")    # the chord, for the level
        _, (x, sr) = play(work, h, f"t_chord_{name}", with_main=False, ms=1700)
        root = x[int(0.25 * sr):int(0.55 * sr)]
        assert peak(root) > 0.01, f"{name} is silent"
        if name in ("piano", "rhodes"):   # FM pianos: the pitch counter reads them cleanly (saws and the organ's sub drawbar fool it)
            f0 = cycles_per_second(root, sr)
            assert 195 < f0 < 245, f"{name} plays {f0:.0f} Hz for A3, expected about 220"
        ch = x[int(1.05 * sr):int(1.6 * sr)]
        levels[name] = math.sqrt(sum(v * v for v in ch) / len(ch))
    lo, hi = min(levels.values()), max(levels.values())
    print("      chord levels (rms): " + ", ".join(f"{k} {v:.3f}" for k, v in levels.items()))
    assert hi / lo < 3, "chord engines are too far apart in level: " + ", ".join(f"{k} {v:.3f}" for k, v in levels.items())

@test
def track_eq_cuts_and_boosts(work):
    """White noise through a track EQ: flat by default; the low cut and low shelf change the lows, the high shelf the highs,
    and the mid bell the middle, each in the right direction."""
    def lows(x):    # energy below ~250 Hz: average over 2 ms
        k = 96; out = []; acc = 0.0
        for i, v in enumerate(x):
            acc += v
            if i >= k: acc -= x[i - k]
            out.append(acc / k)
        return math.sqrt(sum(v * v for v in out) / len(out))
    def highs(x):   # energy of fast change: mostly above a few kHz
        d = [x[i] - x[i - 1] for i in range(1, len(x))]
        return math.sqrt(sum(v * v for v in d) / len(d))
    res = {}
    for name, msg in [("flat", ""), ("lowcut", "ockm-zz-lowcut 400"), ("lowboost", "ockm-zz-eqlow 12"),
                      ("highcut", "ockm-zz-eqhigh -12"), ("highboost", "ockm-zz-eqhigh 12")]:
        h = Harness(dut="ockm-eq zz")
        nz = h.add("#X obj 500 70 noise~;"); g = h.add("#X obj 500 95 *~ 0.2;"); h.con(nz, g); h.con(g, h.dut)
        h.record(os.path.join(work, f"eq_{name}.wav"), source="dut")
        if msg: h.at(50, msg)
        _, (x, sr) = play(work, h, f"t_eq_{name}", with_main=False, ms=700)
        seg = x[int(0.2 * sr):int(0.6 * sr)]
        res[name] = (lows(seg), highs(seg))
    f = res["flat"]
    assert res["lowcut"][0] < f[0] * 0.6, f"low cut 400 Hz should take the lows down: {res['lowcut'][0]:.4f} vs {f[0]:.4f}"
    assert res["lowboost"][0] > f[0] * 2, f"+12 dB low shelf should lift the lows: {res['lowboost'][0]:.4f} vs {f[0]:.4f}"
    assert res["highcut"][1] < f[1] * 0.5 and res["highboost"][1] > f[1] * 1.8, f"high shelf -12 / +12: {res['highcut'][1]:.4f} {f[1]:.4f} {res['highboost'][1]:.4f}"
    assert abs(res["lowboost"][1] / f[1] - 1) < 0.2, "a low boost shouldn't change the highs much"

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
    h.at(100, "ockm-bass-gen bang ; ockm-chord-gen bang ; ockm-lead-gen bang ; ockm-play 1"); h.at(8000, "ockm-play 0")
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
    h.at(350, "ockm-page 0")
    h.at(500, "ockm-play 1"); h.at(500 + 3 * 15000 / 124 + 20, "ockm-play 0")
    f = os.path.join(work, "t_panel.pd"); h.finish(1200, f)
    out = run(work, f)
    pat = {nm: [int(float(x)) for x in printed(out, f"PAT-{nm}")[0].split()] for nm in ("d1", "d2", "d3")}
    assert pat["d2"][5] == 1, f"clicking slot 2 step 6 didn't set it: {pat['d2'][:16]}"
    assert pat["d3"][1] == 2, f"accent-mode click should set an accent: {pat['d3'][:16]}"
    assert "32" in printed(out, "ockm-len"), "length button didn't set 32 steps"
    assert pat["d1"][17] == 1, f"page 2 click should set step 18: {pat['d1'][16:32]}"
    ui = printed(out, "ockm-ui-d2-5")
    assert any(x.startswith("set 1") for x in ui) and any(x.startswith(("color #ededed", "color #1a1a1a")) for x in ui), f"square wasn't redrawn as a hit: {ui}"
    assert any(x.startswith(("color #ff5a24", "color #ff4f1a")) for x in printed(out, "ockm-ui-ph-2")), "playhead didn't light step 3"

@test
def touchscreen_drives_the_engine(work):
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-edit", "ockm-page", "ockm-len", "ockm-load", "ockm-d1-sound", "ockm-bass-edit", "ockm-want", "ockm-lead-k1", "ockm-filter", "ockm-chord-prog", "ockm-chord-type", "ockm-d1-mute", "ockm-d2-mute", "ockm-bass-level", "ockm-bass-mode")
    tap = lambda ms, x, y: h.at(ms, f"ockm-ui-test tap {x} {y}")
    h.at(100, "ockm-resync bang")
    tap(150, 50, 137)                    # perform: open the kick lane
    tap(170, 160, 212); tap(180, 160, 212)   # step 3: on, then accent
    tap(190, 262, 36)                    # perform tab
    tap(200, 539, 36)                    # drums tab (back to the kick slot)
    tap(210, 668, 88)                    # drum length: 2 bars (navigation strip)
    h.at(220, "ockm-ui-test drag 600 212 200 212")   # swipe left: steps 17-32
    tap(230, 45, 212)                    # step 17
    h.at(240, "ockm-ui-test drag 200 212 600 212")   # swipe right: back to 1-16
    tap(245, 194, 88)                    # forward arrow (steps 17-32)
    tap(248, 38, 88)                     # back arrow (steps 1-16)
    tap(250, 262, 36)                    # perform tab
    tap(255, 200, 438); tap(258, 129, 524)   # synth card: lead, then its first knob
    tap(260, 601, 36)                    # bass tab (bass is on auto)
    tap(265, 45, 158)                    # tap a step on auto: locked, nothing is edited
    tap(266, 477, 36); tap(267, 417, 154)   # compose: mode manual (every part yours)
    tap(268, 601, 36)                    # back to the bass tab
    tap(270, 45, 158)                    # now bass step 1 edits
    tap(280, 600, 236)                   # note picker: third note of the scale
    tap(290, 262, 36)                    # perform tab
    tap(310, 629, 500)                   # master fx: filter, middle
    tap(320, 477, 36)                    # compose tab
    tap(330, 71, 154)                    # mode: chord priority again (chords are yours)
    tap(335, 283, 349)                   # chord column: next progression
    tap(340, 200, 486)                   # spice 3 (ninth)
    tap(345, 262, 36); tap(348, 126, 137)  # perform tab, mute the kick lane
    tap(349, 192 + 47 * 1 + 20, 165)     # perform: snare lane, step 2
    tap(350, 407, 36)                    # mixer tab
    tap(355, 673, 361)                   # bass fader, halfway (below the EQ button)
    tap(360, 130, 505)                   # mute on strip 2
    f = os.path.join(work, "t_touch.pd"); h.finish(600, f)
    out = run(work, f)
    edits = printed(out, "ockm-edit")
    assert edits[:2] == ["d1 2 1", "d1 2 2"], f"tapping step 3 should go on, then accent: {edits}"
    assert "32" in printed(out, "ockm-len"), "length button didn't set 32"
    pages = printed(out, "ockm-page")
    assert pages.count("1") >= 2 and "0" in pages[pages.index("1") + 1:], f"swipes and block buttons should go to block 2 and back: {pages}"
    assert any(e.startswith("d1 16 ") for e in edits), f"tap after the swipe should edit step 17: {edits}"
    be = printed(out, "ockm-bass-edit")
    assert len(be) >= 2 and be[-1].split()[:2] == ["0", "36"], f"bass step 1 should become C (A minor, third step): {be}"
    lk = [float(x) for x in printed(out, "ockm-lead-k1")]
    assert any(0.4 < x < 0.6 for x in lk), f"perform strip: lead knob 1 should be about halfway: {lk}"
    assert any(abs(float(x)) < 0.1 for x in printed(out, "ockm-filter")), "perform strip: filter in the middle should be about 0"
    assert printed(out, "ockm-chord-prog"), "compose: the progression arrow should pick the next progression"
    assert any(e.startswith("d2 1 ") for e in edits), f"tapping the snare lane on perform should edit d2 step 2: {edits}"
    assert "1" in printed(out, "ockm-bass-mode"), "editing the bass in manual mode should mark it as hand-edited"
    assert "1" in printed(out, "ockm-d1-mute"), "perform: M on the kick lane should mute d1"
    assert "1" in printed(out, "ockm-d2-mute"), "mixer: M on strip 2 should mute d2"
    bl = [float(x) for x in printed(out, "ockm-bass-level")]
    assert any(0.4 < x < 0.6 for x in bl), f"mixer: bass fader halfway should be about 0.5: {bl}"
    assert "6" in printed(out, "ockm-chord-type"), f"compose: spice 3 should pick the ninth chord type (6): {printed(out, 'ockm-chord-type')}"
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
    assert len(os.listdir(os.path.join(work, "preview"))) == 28, "expected twenty-eight screen pictures"

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

@test
def bass_follows_chords_and_manual_stays_put(work):
    h = Harness(); h.show("ockm-bass-mode", "ockm-len")
    # bass: root notes on the offbeat rhythm, following the chords. Chords: deep house (i iv VI v, a bar each)
    h.at(100, "ockm-resync bang ; ockm-root 9 ; ockm-scale 0 ; ockm-bass-sync 1 ; ockm-bass-notes 0 ; ockm-bass-rhythm 0")
    h.at(150, "ockm-chord-rhythm 0 ; ockm-chord-prog 3")
    g = h.add("#X obj 10 300 r test-get;"); a = h.add("#X obj 10 330 array get ockm-pat-bass-note 0 64;"); pr = h.add("#X obj 10 360 print NOTES;")
    h.con(g, a); h.con(a, pr)
    h.at(200, "test-get bang")
    h.at(220, "ockm-bass-mode 1 ; ockm-root 0")        # manual: a key change must not rewrite the bass
    h.at(240, "test-get bang")
    h.at(260, "ockm-bass-rhythm 1")                    # picking a preset generates again and goes back to auto
    f = os.path.join(work, "t_sync.pd"); h.finish(320, f)
    out = run(work, f)
    notes = [[int(float(x)) for x in v.split()] for v in printed(out, "NOTES")]
    # step 3 of each bar (offbeat rhythm): A minor bass on i, iv, VI (below), v (below)
    got = [notes[0][b * 16 + 2] for b in range(4)]
    assert got == [33, 38, 29, 28], f"bass should follow the chords i iv VI v: {got}"
    assert notes[1] == notes[0], "in manual, changing the key must not rewrite the bass"
    modes = printed(out, "ockm-bass-mode")
    assert modes[-1] == "0", f"picking a rhythm should put the bass back in auto: {modes}"

@test
def bass_lock_density_and_mutate(work):
    h = Harness()
    kick = "1 0 0 0 1 0 0 0 1 0 0 0 1 0 0 0"
    h.at(100, f"ockm-resync bang ; ockm-pat-d1 0 {kick} ; ockm-bass-sync 0 ; ockm-bass-notes 3 ; ockm-bass-rhythm 6 ; ockm-length 16")
    g = h.add("#X obj 10 300 r test-get;"); t = h.add("#X obj 10 325 t b b;")
    a1 = h.add("#X obj 10 350 array get ockm-pat-bass-on 0 16;"); p1 = h.add("#X obj 10 375 print ON;")
    a2 = h.add("#X obj 200 350 array get ockm-pat-bass-note 0 16;"); p2 = h.add("#X obj 200 375 print NOTE;")
    h.con(g, t); h.con(t, a2, 0); h.con(t, a1, 1); h.con(a1, p1); h.con(a2, p2)
    h.at(150, "test-get bang")                                  # 0: own rhythm (acid 16ths: every step)
    h.at(160, "ockm-bass-lock 1"); h.at(170, "test-get bang")   # 1: lock to kick
    h.at(180, "ockm-bass-lock 2"); h.at(190, "test-get bang")   # 2: fill the gaps
    h.at(200, "ockm-bass-lock 0 ; ockm-bass-density 0.3"); h.at(210, "test-get bang")   # 3: thinner
    h.at(220, "ockm-bass-density 1 ; ockm-bass-seed 3"); h.at(230, "test-get bang")     # 4: mutated
    h.at(240, "ockm-bass-seed 0"); h.at(250, "test-get bang")                          # 5: back to the original
    f = os.path.join(work, "t_lock.pd"); h.finish(300, f)
    out = run(work, f)
    on = [[int(float(x)) for x in v.split()] for v in printed(out, "ON")]
    notes = [[int(float(x)) for x in v.split()] for v in printed(out, "NOTE")]
    kicks = [int(x) for x in kick.split()]
    assert on[0] == [1] * 16, f"acid 16ths should play every step: {on[0]}"
    assert on[1] == kicks, f"lock to kick should play only with the kick: {on[1]}"
    assert on[2] == [1 - k for k in kicks], f"fill the gaps should play only between kicks: {on[2]}"
    assert 0 < sum(on[3]) < 16, f"density 0.3 should thin the line out: {on[3]}"
    assert notes[4] != notes[0], "mutate should change the line"
    assert notes[5] == notes[0] and on[5] == on[0], "seed 0 should bring back the original"

@test
def touchscreen_mode_dial(work):
    """Compose's mode dial: melody priority makes the melody yours and the bass follow; manual makes every part yours; chord priority hands bass and melody back to the generators."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    names = ["ockm-leader", "ockm-lead-sync", "ockm-bass-sync", "ockm-bass-mode", "ockm-lead-mode", "ockm-chord-mode"]
    h = Harness(); h.show(*names)
    tap = lambda ms, x, y: h.at(ms, f"ockm-ui-test tap {x} {y}")
    tap(150, 477, 36)                   # compose
    tap(200, 186, 154); h.at(250, "test-mark 1")    # melody priority
    tap(300, 417, 154); h.at(350, "test-mark 2")    # manual
    tap(400, 71, 154);  h.at(450, "test-mark 3")    # chord priority
    mk = h.add("#X obj 10 300 r test-mark;"); pm = h.add("#X obj 10 325 print MARK;"); h.con(mk, pm)
    f = os.path.join(work, "t_dial.pd"); h.finish(500, f)
    out = run(work, f)
    state, snaps = {}, {}
    for line in out.splitlines():
        if line.startswith("MARK:"):
            snaps[int(float(line.split()[-1]))] = dict(state)
        for n in names:
            if line.startswith(n + ":"):
                state[n] = int(float(line.split()[-1]))
    m, man, ch = snaps[1], snaps[2], snaps[3]
    assert m["ockm-leader"] == 1 and m["ockm-lead-sync"] == 0 and m["ockm-bass-sync"] == 1 and m["ockm-bass-mode"] == 0, f"melody priority: {m}"
    assert man["ockm-leader"] == 3 and man["ockm-bass-mode"] == 1 and man["ockm-lead-mode"] == 1 and man["ockm-chord-mode"] == 1, f"manual: {man}"
    assert ch["ockm-leader"] == 0 and ch["ockm-bass-mode"] == 0 and ch["ockm-lead-mode"] == 0 and ch["ockm-bass-sync"] == 1, f"chord priority: {ch}"

@test
def dub_throw_rings_out_and_filter_springs_back(work):
    """Hold the throw, let go and mute everything: the echoes keep ringing. Without a throw it goes quiet. The filter glides back to 0."""
    def tail(throw):
        h = Harness(); h.record(os.path.join(work, f"throw{throw}.wav"))
        mutes = " ; ".join(f"ockm-{t}-mute 1" for t in ["d1","d2","d3","d4","d5","d6","d7","d8","bass","lead","chord"])
        h.at(100, "ockm-delay-mix 0 ; ockm-delay-fb 0.6 ; ockm-verb-mix 0 ; ockm-play 1")
        if throw: h.at(1000, "ockm-delay-throw 1")
        h.at(1500, f"ockm-delay-throw 0 ; {mutes}")
        h.at(2600, "ockm-play 0")
        _, (snd, sr) = play(work, h, f"t_throw{throw}", ms=2600)
        a, b = int(1.7 * sr), int(2.5 * sr)          # 0.2 to 1 s after letting go
        return peak(snd[a:b])
    rings, quiet = tail(1), tail(0)
    assert rings > 0.02 and rings > 5 * max(quiet, 1e-4), f"the throw's echoes should ring out after letting go: {rings:.4f} vs {quiet:.4f}"
    h = Harness(); h.show("ockm-filter-now")
    h.at(100, "ockm-filter -0.8"); h.at(300, "ockm-filter-glide 0 180")
    f = os.path.join(work, "t_spring.pd"); h.finish(700, f); out = run(work, f)
    vals = [float(v.split()[-1]) for v in printed(out, "ockm-filter-now")]
    assert min(vals) < -0.75 and abs(vals[-1]) < 1e-6, f"filter should reach -0.8 then glide back to 0: {vals[:3]} ... {vals[-3:]}"
    mid = [v for v in vals if -0.7 < v < -0.1]
    assert len(mid) >= 5, "the way back should be a glide, not a jump"

@test
def drop_holds_the_hits_and_lands_on_the_bar(work):
    """Perform's drop: hold it and nothing new plays; let go and the hits come back on the next bar, not straight away."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-gap", "ockm-drop", "ockm-bar")
    h.at(100, "ockm-bpm 120 ; ockm-play 1")
    h.at(300, "ockm-ui-test press 760 438")       # drop, held
    h.at(700, "ockm-ui-test release 760 438")     # let go part way through a bar (a bar is 2 s at 120)
    f = os.path.join(work, "t_drop.pd"); h.finish(3000, f)
    out = run(work, f)
    lines = [l for l in out.splitlines() if l.startswith(("ockm-gap:", "ockm-drop:", "ockm-bar:"))]
    gaps = [l for l in lines if l.startswith("ockm-gap:")]
    assert [g.split()[-1] for g in gaps] == ["1", "0"], f"drop should close the gap, then open it once: {lines}"
    rel = lines.index("ockm-drop: 0")
    back = lines.index(gaps[-1])
    assert any(l.startswith("ockm-bar:") for l in lines[rel:back + 1]), f"the hits should come back on a bar, not on release: {lines}"

@test
def live_mutes_land_on_the_bar(work):
    """Live screen, mutes on 'next bar': tapping the kick tile mutes it at the next bar, not straight away. 'drums only'
    mutes the synths the same way. Stopped, a mute lands at once."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-d1-mute", "ockm-bass-mute", "ockm-bar", "ockm-d2-mute")
    h.at(100, "ockm-bpm 120 ; ockm-play 1")
    h.at(150, "ockm-ui-test tap 338 36")       # live tab
    h.at(200, "ockm-ui-test tap 400 97")       # mutes land: next bar
    h.at(700, "test-mark 1 ; ockm-ui-test tap 60 180")      # kick tile, part way through the first bar (a bar is 2 s)
    h.at(2600, "ockm-ui-test tap 74 556")      # scene: drums only (after the kick has gone)
    h.at(4500, "ockm-play 0")
    h.at(4600, "test-mark 2 ; ockm-ui-test tap 175 180")    # stopped: snare tile mutes at once
    mk = h.add("#X obj 10 300 r test-mark;"); pm = h.add("#X obj 10 325 print MARK;"); h.con(mk, pm)
    f = os.path.join(work, "t_live.pd"); h.finish(4800, f)
    out = run(work, f)
    ev = [l for l in out.splitlines() if l.startswith(("MARK:", "ockm-d1-mute:", "ockm-bass-mute:", "ockm-bar:", "ockm-d2-mute:"))]
    i1 = ev.index("MARK: 1")
    after = ev[i1:]
    assert "ockm-d1-mute: 1" in after, f"the kick should mute: {ev[:40]}"
    km = after.index("ockm-d1-mute: 1")
    assert "ockm-bar: bang" in after[:km], f"the kick should mute on the next bar, not when tapped: {after[:12]}"
    assert "ockm-bass-mute: 1" in after, f"drums only should mute the bass: {after}"
    i2 = ev.index("MARK: 2")
    assert ev[i2 + 1] == "ockm-d2-mute: 1", f"stopped, a mute should land straight away: {ev[i2:i2 + 3]}"

@test
def live_macros_move_several_things_and_put_them_back(work):
    """Hold wash: delay and reverb go up together; let go and they go back. Hold strip: everything but kick and bass mutes, then returns."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-delay-mix", "ockm-verb-mix", "ockm-d2-mute", "ockm-d1-mute", "ockm-bass-mute", "ockm-filter-glide")
    h.at(100, "ockm-ui-test tap 338 36")       # live tab (mutes land now)
    h.at(200, "ockm-ui-test press 700 500")    # wash, held
    h.at(300, "ockm-ui-test release 700 500")
    h.at(400, "ockm-ui-test press 850 500")    # strip, held
    h.at(500, "ockm-ui-test release 850 500")
    f = os.path.join(work, "t_macro.pd"); h.finish(600, f)
    out = run(work, f)
    dm = [float(x) for x in printed(out, "ockm-delay-mix")]; vm = [float(x) for x in printed(out, "ockm-verb-mix")]
    assert len(dm) >= 2 and dm[-2] > 0.8 and dm[-1] == dm[0] if len(dm) > 2 else (dm[0] > 0.8 and dm[-1] < 0.8), f"wash: delay up, then back: {dm}"
    assert vm and max(vm) > 0.85 and vm[-1] < 0.85, f"wash: reverb up, then back: {vm}"
    assert printed(out, "ockm-filter-glide"), "wash: the filter moves too"
    assert printed(out, "ockm-d2-mute") == ["1", "0"], f"strip: the snare mutes, then comes back: {printed(out, 'ockm-d2-mute')}"
    assert not printed(out, "ockm-d1-mute") and not printed(out, "ockm-bass-mute"), "strip: kick and bass keep playing"

@test
def settings_macro_library_and_slots(work):
    """Settings, macros: put 'sink' on slot A, then hold slot A on Perform B: the filter sinks and the drive rises over
    a bar, and both come back when you let go. Your choice is kept in my-settings.lua, outside the projects."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    mine = os.path.join(work, "my-settings.lua")
    if os.path.exists(mine): os.remove(mine)
    h = Harness(); h.show("ockm-filter-glide", "ockm-drive")
    h.at(100, "ockm-bpm 120 ; ockm-ui-test tap 919 36")   # menu
    h.at(150, "ockm-ui-test tap 830 195")      # settings
    h.at(200, "ockm-ui-test tap 90 272")       # macros
    h.at(250, "ockm-ui-test tap 260 371")      # recipe 4: sink
    h.at(300, "ockm-ui-test tap 532 552")      # on slot A
    h.at(350, "ockm-ui-test tap 338 36")       # Perform B
    h.at(400, "ockm-ui-test press 550 520")    # hold slot A
    h.at(2600, "ockm-ui-test release 550 520")
    f = os.path.join(work, "t_settings.pd"); h.finish(2800, f)
    out = run(work, f)
    try:
        saved = open(mine).read() if os.path.exists(mine) else ""
    finally:
        if os.path.exists(mine): os.remove(mine)
    gl = printed(out, "ockm-filter-glide")
    assert gl and gl[0].split()[0] == "-0.85", f"sink should take the filter down: {gl}"
    dr = [float(x) for x in printed(out, "ockm-drive")]
    assert dr and max(dr) > 0.65 and len([x for x in dr if 0.05 < x < 0.65]) >= 3 and dr[-1] < 0.01, f"drive should rise over the bar, then go back: {dr[:6]} ... {dr[-3:]}"
    assert '"slots"' in saved and re.search(r'"slots"\]\s*=\s*\{\s*4', saved), f"slot A should be saved as recipe 4: {saved[:400]}"

@test
def touchscreen_filter_springs_and_throw(work):
    """On perform: sweep the filter and let go, it glides back to 0. With hold on it stays. The throw pad sends 1 then 0."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-filter-glide", "ockm-delay-throw", "ockm-filter-now")
    h.at(100, "ockm-ui-test drag 600 486 520 486")          # sweep the filter left, let go
    h.at(500, "ockm-ui-test tap 742 476")                   # hold on
    h.at(550, "ockm-ui-test drag 600 486 520 486")          # sweep again, let go: it stays
    h.at(900, "ockm-ui-test tap 870 438")                   # throw
    f = os.path.join(work, "t_spring_ui.pd"); h.finish(1000, f)
    out = run(work, f)
    gl = printed(out, "ockm-filter-glide")
    assert len(gl) == 1 and gl[0].split()[-1] == "50", f"only the first sweep should spring back, quickly (50 ms): {gl}"
    now = [float(v.split()[-1]) for v in printed(out, "ockm-filter-now")]
    assert min(now) < -0.3 and abs(now[-1]) > 0.3, f"held filter should stay where it was left: last {now[-3:]}"
    assert [int(float(v.split()[-1])) for v in printed(out, "ockm-delay-throw")] == [1, 0], printed(out, "ockm-delay-throw")

@test
def melody_uses_chord_tones(work):
    """The 'melody' notes preset: every note is the root, 3rd, 5th or 7th of the chord under it, and it isn't just an arpeggio."""
    h = Harness()
    h.at(100, "ockm-root 9 ; ockm-scale 0 ; ockm-chord-mode 0 ; ockm-lead-sync 1 ; ockm-lead-mode 0 ; ockm-lead-lock 0 ; ockm-lead-density 1 ; ockm-lead-seed 0")
    h.at(150, "ockm-chord-prog 3")                                  # deep house: i iv VI v, a bar each
    h.at(250, "ockm-lead-rhythm 8 ; ockm-lead-notes 12")
    g = h.add("#X obj 10 300 r test-get;"); t = h.add("#X obj 10 325 t b b b;")
    outs = []
    for k, nm in enumerate(["lead-note", "lead-on", "chord-deg"]):
        a = h.add(f"#X obj {10+k*200} 350 array get ockm-pat-{nm} 0 64;"); pr = h.add(f"#X obj {10+k*200} 375 print {nm.upper()};")
        h.con(t, a, 2 - k); h.con(a, pr)
    h.con(g, t)
    h.at(350, "test-get bang")
    f = os.path.join(work, "t_melody.pd"); h.finish(400, f)
    out = run(work, f)
    notes = [int(float(x)) for x in printed(out, "LEAD-NOTE")[-1].split()]
    on = [int(float(x)) for x in printed(out, "LEAD-ON")[-1].split()]
    deg = [int(float(x)) for x in printed(out, "CHORD-DEG")[-1].split()]
    minor = [0, 2, 3, 5, 7, 8, 10]
    played = [(i, notes[i]) for i in range(64) if on[i] > 0]
    assert len(played) > 12, f"the melody should have notes: {on}"
    for i, n in played:
        d = deg[i]
        tones = {(9 + minor[(d + k) % 7]) % 12 for k in (0, 2, 4, 6)}
        assert n % 12 in tones, f"step {i}: note {n} is not a chord tone of degree {d} ({sorted(tones)})"
    seq = [n for _, n in played]
    assert len(set(seq)) >= 4, "it should use several different notes"
    assert any(abs(seq[k + 1] - seq[k]) <= 4 for k in range(len(seq) - 1)) and seq[:4] != sorted(seq[:4]), "it should move like a tune, not climb like an arpeggio"

@test
def synths_sit_at_similar_levels(work):
    """Bass, melody and every chord engine come out at a similar loudness (within about 4 dB), so nothing gets lost."""
    def rms(x): return math.sqrt(sum(v * v for v in x) / max(1, len(x)))
    tracks = ["d1","d2","d3","d4","d5","d6","d7","d8","bass","lead","chord"]
    levels = {}
    for part, setup, eng in [("bass", "ockm-bass-gen bang", None), ("chord", "ockm-chord-prog 3 ; ockm-chord-rhythm 4", 0),
                             ("chord", "ockm-chord-prog 3 ; ockm-chord-rhythm 4", 1), ("chord", "ockm-chord-prog 3 ; ockm-chord-rhythm 4", 2)]:
        h = Harness(); name = f"lv-{part}{eng}"; h.record(os.path.join(work, name + ".wav"))
        mutes = " ; ".join(f"ockm-{t}-mute {0 if t == part else 1}" for t in tracks)
        extra = f" ; ockm-chord-engine {eng}" if eng is not None else ""
        h.at(100, f"ockm-verb-mix 0 ; ockm-delay-mix 0 ; {mutes}{extra} ; {setup}"); h.at(200, "ockm-play 1"); h.at(3200, "ockm-play 0")
        _, (snd, sr) = play(work, h, name, ms=3200)
        levels[name] = rms(snd[int(0.3 * sr):int(3.0 * sr)])
    ref = levels["lv-bassNone"]
    for k, v in levels.items():
        assert 0.6 * ref < v < 1.6 * ref, f"{k} is out of balance with the bass: {v:.3f} vs {ref:.3f} ({levels})"

@test
def drum_fill_on_the_fourth_bar(work):
    """Fill every 4 bars, snare roll: pattern 1 has no snare, so the snare is silent for 3 bars, rolls in the second half of bar 4, then stops."""
    h = Harness(); h.record(os.path.join(work, "fill.wav"))
    mutes = " ; ".join(f"ockm-{t}-mute 1" for t in ["d1","d3","d4","d5","d6","d7","d8","bass","lead","chord"])
    h.at(100, f"ockm-bpm 200 ; ockm-verb-mix 0 ; ockm-delay-mix 0 ; ockm-swing 50 ; ockm-length 16 ; ockm-fill-style 0 ; ockm-fill-every 4 ; {mutes}")
    h.at(200, "ockm-play 1"); h.at(6400, "ockm-play 0")
    _, (snd, sr) = play(work, h, "t_fill", ms=6400)
    bar = 16 * 15000 / 200 / 1000.0                     # seconds per bar at 200 bpm
    t0 = next(i for i, v in enumerate(snd) if abs(v) > 1e-4) / sr if any(abs(v) > 1e-4 for v in snd) else None
    assert t0 is not None, "the snare never played"
    start = 0.2 + 0.0                                    # play started at 200 ms
    def seg(a, b): return peak(snd[int((start + a) * sr):int((start + b) * sr)])
    assert seg(0.05, 3 * bar - 0.05) < 0.01, f"bars 1-3 should have no snare: {seg(0.05, 3 * bar - 0.05):.3f}"
    assert seg(3.5 * bar, 4 * bar) > 0.05, f"the second half of bar 4 should have the snare roll: {seg(3.5 * bar, 4 * bar):.3f}"
    assert seg(4 * bar + 0.15, 5 * bar - 0.05) < 0.01, "bar 5 should be back to normal (no snare)"

@test
def drum_velocity_timing_and_loop(work):
    """Kick only, 120 bpm (a step is 125 ms). Hits on steps 0, 4, 8, 12: step 4 nudged a fifth of a step early, step 8 a fifth late,
    step 12 drawn at velocity 0.4. The drums loop is 1 bar under a 2-bar pattern, so bar 2 repeats bar 1, nudges and all."""
    h = Harness(); h.record(os.path.join(work, "nudge.wav"))
    mutes = " ; ".join(f"ockm-{t}-mute 1" for t in ["d2","d3","d4","d5","d6","d7","d8","bass","lead","chord"])
    h.at(100, f"ockm-bpm 120 ; ockm-verb-mix 0 ; ockm-delay-mix 0 ; ockm-swing 50 ; ockm-length 32 ; ockm-fill-every 0 ; ockm-d1-sample 0 ; ockm-d1-sound 0 ; ockm-d1-synth 0 ; ockm-d1-decay 40 ; {mutes}")
    h.at(150, "ockm-pat-d1 const 0 ; ockm-pat-d1-nudge const 0 ; ockm-drum-loop 16")
    h.at(170, "ockm-edit d1 0 2 ; ockm-edit d1 4 2 ; ockm-edit d1 8 2 ; ockm-edit d1 12 0.4 ; ockm-nudge d1 4 -0.2 ; ockm-nudge d1 8 0.2")
    h.at(300, "ockm-play 1"); h.at(4500, "ockm-play 0")
    _, (x, sr) = play(work, h, "t_nudge", ms=4500)
    on, i, last = [], 0, -1.0
    while i < len(x):                       # onsets: first loud sample at least 300 ms after the last one
        if abs(x[i]) > 0.02 and (i / sr - last) > 0.3:
            on.append(i / sr); last = i / sr
        i += 1
    assert len(on) >= 8, f"expected 8 kicks over two bars, heard {len(on)}"
    gaps = [round(b - a, 3) for a, b in zip(on, on[1:])][:7]
    want = [0.475, 0.55, 0.475, 0.5, 0.475, 0.55, 0.475]
    assert all(abs(g - w) < 0.008 for g, w in zip(gaps, want)), f"gaps between kicks {gaps}, expected about {want}"
    pk = [peak(x[int(o * sr):int((o + 0.08) * sr)]) for o in on[:4]]
    assert 0.3 < pk[3] / pk[0] < 0.5, f"velocity 0.4 should play at about 0.4 of an accent ({pk[3] / pk[0]:.2f})"

@test
def drum_double_copies_the_loop(work):
    """1-bar loop under a 4-bar pattern: double makes it 2 bars (bar 1 copied to bar 2, timing too), double again fills the pattern."""
    h = Harness(); h.show("ockm-drum-loop")
    g = h.add("#X obj 10 300 r test-get;"); t = h.add("#X obj 10 325 t b b;")
    a1 = h.add("#X obj 10 350 array get ockm-pat-d1 0 64;"); p1 = h.add("#X obj 10 375 print STEPS;")
    a2 = h.add("#X obj 300 350 array get ockm-pat-d1-nudge 0 32;"); p2 = h.add("#X obj 300 375 print NUDGE;")
    h.con(g, t); h.con(t, a2, 0); h.con(t, a1, 1); h.con(a1, p1); h.con(a2, p2)
    h.at(100, "ockm-length 64 ; ockm-pat-d1 const 0 ; ockm-pat-d1-nudge const 0 ; ockm-drum-loop 16")
    h.at(150, "ockm-edit d1 0 2 ; ockm-edit d1 6 0.5 ; ockm-nudge d1 6 -0.1")
    h.at(200, "ockm-drum-double bang"); h.at(250, "ockm-drum-double bang"); h.at(300, "test-get bang")
    f = os.path.join(work, "t_double.pd"); h.finish(400, f)
    out = run(work, f)
    loops = [int(float(v)) for v in printed(out, "ockm-drum-loop")]
    assert loops[-2:] == [32, 0], f"loop should go 16 -> 32 -> whole pattern: {loops}"
    st = [float(v) for v in printed(out, "STEPS")[0].split()]
    for b in range(4):
        assert st[b * 16] == 2 and st[b * 16 + 6] == 0.5, f"bar {b + 1} should be a copy of bar 1: {st[b * 16:b * 16 + 16]}"
    nu = [float(v) for v in printed(out, "NUDGE")[0].split()]
    assert nu[6] == -0.1 and nu[22] == -0.1, f"the timing should be copied too: {nu[:32]}"

@test
def length_keeps_bars_and_rebuilds_followers(work):
    """Shorten a 4-bar drum part to 1 bar and back: the original bars return (not copies). Lengthen a 1-bar pattern with a 4-bar progression: the chords fill out the whole progression."""
    h = Harness()
    g = h.add("#X obj 10 300 r test-get;"); t = h.add("#X obj 10 325 t b b;")
    a1 = h.add("#X obj 10 350 array get ockm-pat-d2 0 64;"); p1 = h.add("#X obj 10 375 print D2;")
    a2 = h.add("#X obj 300 350 array get ockm-pat-chord-deg 0 64;"); p2 = h.add("#X obj 300 375 print DEG;")
    h.con(g, t); h.con(t, a2, 0); h.con(t, a1, 1); h.con(a1, p1); h.con(a2, p2)
    h.at(100, "ockm-length 64 ; ockm-edit d2 4 1 ; ockm-edit d2 36 2 ; ockm-edit d2 52 1")    # snare in bars 1, 3 and 4
    h.at(150, "ockm-length 16"); h.at(200, "ockm-length 64"); h.at(250, "test-get bang")      # 0: shrink and grow back
    h.at(300, "ockm-chord-mode 0 ; ockm-length 16 ; ockm-chord-prog 0"); h.at(320, "ockm-length 16")
    h.at(350, "ockm-chord-prog 3"); h.at(400, "ockm-length 16"); h.at(450, "ockm-length 64"); h.at(500, "test-get bang")   # 1: grow with a 4-bar progression
    f = os.path.join(work, "t_len.pd"); h.finish(600, f)
    out = run(work, f)
    d2 = [[int(float(x)) for x in v.split()] for v in printed(out, "D2")]
    deg = [[int(float(x)) for x in v.split()] for v in printed(out, "DEG")]
    assert d2[0][4] == 1 and d2[0][36] == 2 and d2[0][52] == 1 and d2[0][20] == 0, f"bars 2-4 should come back as they were, not as copies of bar 1: {d2[0][16:64]}"
    bars = [deg[1][b * 16] for b in range(4)]
    assert bars == [0, 3, 5, 4], f"growing to 4 bars should play the whole progression (i iv VI v), not repeat bar 1: {bars}"

@test
def blank_project_synths_start_and_sound(work):
    """On the blank starter, starting the bass and chords gives notes you can hear, with the default sounds."""
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build.py"), "--out", work, "--reset-patterns"], check=True, capture_output=True)
    for part, gen in (("bass", "ockm-bass-gen bang"), ("chord", "ockm-chord-gen bang")):
        h = Harness(); h.record(os.path.join(work, f"blank-{part}.wav"))
        others = " ; ".join(f"ockm-{t}-mute 1" for t in ["d1","d2","d3","d4","d5","d6","d7","d8","bass","lead","chord"] if t != part)
        h.at(100, f"{gen} ; {others} ; ockm-play 1"); h.at(2500, "ockm-play 0")
        _, (snd, sr) = play(work, h, f"t_blank_{part}", ms=2500)
        assert peak(snd) > 0.05, f"{part} on a blank project should be heard once started: peak {peak(snd):.3f}"

@test
def part_off_and_build_rise(work):
    """A part switched off in a pattern goes silent; the build rise climbs over the pattern, and drops back to 0 when switched off."""
    h = Harness(); h.record(os.path.join(work, "partoff.wav")); h.show("ockm-rise-now")
    others = " ; ".join(f"ockm-{t}-mute 1" for t in ["d1","d2","d3","d4","d5","d6","d7","d8","lead","chord"])
    h.at(100, f"ockm-bass-gen bang ; {others} ; ockm-length 16 ; ockm-bpm 120 ; ockm-rise 1 ; ockm-play 1")
    h.at(1300, "ockm-bass-on 0 ; ockm-rise 0")
    h.at(2600, "ockm-play 0")
    out, (x, sr) = play(work, h, "t_partoff", ms=2600)
    on, off = peak(x[int(0.3 * sr):int(1.2 * sr)]), peak(x[int(1.5 * sr):int(2.5 * sr)])
    assert on > 0.05 and off < 0.005, f"the bass should play, then stop when switched off ({on:.3f} then {off:.4f})"
    rise = [float(v) for v in printed(out, "ockm-rise-now")]
    first = rise[:8]
    assert len(first) >= 8 and all(b > a for a, b in zip(first, first[1:])) and first[-1] > first[0], f"the rise should climb step by step: {first}"
    assert rise[-1] == 0, f"the rise should drop to 0 when switched off: {rise[-3:]}"

@test
def sidechain_pump_ducks_the_synths(work):
    """Held organ chords, a kick on every beat (muted, so only the chords are heard). Pump 1: the chords dip just after each kick
    and swell back. Pump 0: they don't."""
    res = {}
    for pump in (0, 1):
        h = Harness(); h.record(os.path.join(work, f"pump{pump}.wav"))
        mutes = " ; ".join(f"ockm-{t}-mute 1" for t in ["d1","d2","d3","d4","d5","d6","d7","d8","bass","lead"])
        h.at(100, f"ockm-bpm 120 ; ockm-length 16 ; ockm-verb-mix 0 ; ockm-delay-mix 0 ; ockm-swing 50 ; ockm-chord-engine 1 ; ockm-chord-mode 1 ; {mutes}")
        h.at(150, "ockm-pat-chord-on const 0 ; ockm-pat-chord-deg const 0 ; ockm-chord-edit 0 1 0 ; ockm-chord-k3 0 ; ockm-chord-k4 1")
        h.at(170, "ockm-pat-d1 const 0 ; ockm-d1-sound 0 ; ockm-edit d1 0 2 ; ockm-edit d1 4 2 ; ockm-edit d1 8 2 ; ockm-edit d1 12 2 ; ockm-pump " + str(pump))
        h.at(300, "ockm-play 1"); h.at(2400, "ockm-play 0")
        _, (x, sr) = play(work, h, f"t_pump{pump}", ms=2400)
        rms = lambda a, b: math.sqrt(sum(v * v for v in x[int(a * sr):int(b * sr)]) / max(1, int((b - a) * sr)))
        # beat 2 of the bar: kick at 0.3 + 0.5 + 0.0625 (quarter-step lag) s
        k = 0.3 + 0.5 + 0.0625
        res[pump] = (rms(k + 0.01, k + 0.06), rms(k + 0.35, k + 0.45))
    d0, d1 = res[0][0] / res[0][1], res[1][0] / res[1][1]
    assert d0 > 0.85, f"no pump: the pads should hold steady ({d0:.2f})"
    assert d1 < 0.55, f"pump on: the pads should dip after the kick ({d1:.2f})"

@test
def projects_new_open_saveas_list_delete(work):
    """Projects are folders: save as copies, new starts blank, open brings one back, delete moves it to the trash."""
    h = Harness()
    g = h.add("#X obj 10 300 r test-get;"); tg = h.add("#X obj 10 325 t b b;")
    a = h.add("#X obj 10 350 array get ockm-pat-d1 0 4;"); pa = h.add("#X obj 10 375 print D1;")
    bp = h.add("#X obj 200 350 r ockm-bpm;"); pb = h.add("#X obj 200 375 print BPM;")
    it = h.add("#X obj 400 350 r ockm-project-item;"); pi = h.add("#X obj 400 375 print ITEM;")
    nm = h.add("#X obj 600 350 r ockm-project-name;"); pn = h.add("#X obj 600 375 print NAME;")
    h.con(g, tg); h.con(tg, a, 0); h.con(a, pa); h.con(bp, pb); h.con(it, pi); h.con(nm, pn)
    h.at(200, "ockm-bpm 131 ; ockm-edit d1 0 2 ; ockm-save bang")
    h.at(300, "ockm-project-saveas symbol 2026-10-14-copy-one")
    h.at(400, "ockm-project-new symbol 2026-10-14-fresh-two")
    h.at(500, "test-get bang")                                     # 0: the new project is blank
    h.at(600, "ockm-project-open symbol 2026-10-14-copy-one")
    h.at(700, "test-get bang")                                     # 1: the copy has the kick accent back
    h.at(800, "ockm-project-list bang")
    h.at(900, "ockm-project-delete symbol 2026-10-14-fresh-two")
    f = os.path.join(work, "t_proj.pd"); h.finish(1000, f)
    out = run(work, f)
    d1 = [[int(float(x)) for x in v.split()] for v in printed(out, "D1")]
    assert d1[0] == [0, 0, 0, 0], f"a new project should start blank: {d1[0]}"
    assert d1[1][0] == 2, f"opening the copy should bring back its steps: {d1[1]}"
    bpms = [v.split()[-1] for v in printed(out, "BPM")]
    assert "124" in bpms and bpms[-1] == "131", f"new should reset the tempo, open should restore it: {bpms}"
    items = [v.split()[-1] for v in printed(out, "ITEM")]
    for want in ("default", "2026-10-14-copy-one", "2026-10-14-fresh-two"):
        assert want in items, f"{want} missing from the project list: {items}"
    P = os.path.join(work, "projects")
    assert os.path.exists(os.path.join(P, "2026-10-14-copy-one", "loop.txt")), "save as should write the loop"
    assert not os.path.exists(os.path.join(P, "2026-10-14-fresh-two")), "delete should move the project out of projects/"
    assert os.path.exists(os.path.join(work, "trash", "2026-10-14-fresh-two", "project.txt")), "deleted projects go to the trash folder"
    assert open(os.path.join(P, "current.txt")).read().strip() == "2026-10-14-copy-one;", "the open project should be remembered"
    assert printed(out, "NAME")[-1].split()[-1] == "2026-10-14-copy-one"

@test
def touchscreen_makes_and_opens_projects(work):
    """On the project screen, new blank project makes a folder named by the date and two random words, and opens it."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-project-name", "ockm-project-new", "ockm-project-open")
    tap = lambda ms, x, y: h.at(ms, f"ockm-ui-test tap {x} {y}")
    tap(150, 919, 36); tap(151, 830, 95)   # menu, project
    tap(200, 667, 178)                   # new blank project
    f = os.path.join(work, "t_touchproj.pd"); h.finish(400, f)
    out = run(work, f)
    errs = [l for l in out.splitlines() if "error" in l.lower() and "current.txt" not in l]
    made = [d for d in os.listdir(os.path.join(work, "projects")) if re.match(r"\d{4}-\d\d-\d\d-[a-z]+-[a-z]+$", d)]
    assert made, f"no new project folder: {os.listdir(os.path.join(work, 'projects'))} {errs[:3]}"
    assert os.path.exists(os.path.join(work, "projects", made[0], "loop.txt")), "the new project should be written straight away"
    assert open(os.path.join(work, "projects", "current.txt")).read().strip() == made[0] + ";"

@test
def drum_grooves_fill_every_slot(work):
    """A groove lands on each slot by the sound it plays, makes the drums 1 bar (a groove's natural length), sets the swing and moves a part locked to the kick."""
    h = Harness(); h.show("ockm-drum-len")
    h.at(100, "ockm-resync bang ; ockm-length 32 ; ockm-bass-lock 1 ; ockm-bass-mode 0")
    h.at(150, "ockm-drum-groove 3")                              # tech house
    g = h.add("#X obj 10 300 r test-get;"); t = h.add("#X obj 10 325 t b b b b;")
    outs = []
    for k, nm in enumerate(["d1", "d4", "d5", "bass-on"]):
        a = h.add(f"#X obj {10+k*190} 350 array get ockm-pat-{nm} 0 32;"); pr = h.add(f"#X obj {10+k*190} 375 print {nm.upper()};")
        h.con(t, a, 3 - k); h.con(a, pr); outs.append(nm.upper())
    h.con(g, t)
    sw = h.add("#X obj 800 300 r ockm-swing;"); psw = h.add("#X obj 800 325 print SWING;"); h.con(sw, psw)
    h.at(200, "test-get bang")
    h.at(220, "ockm-d1-sound 4 ; ockm-drum-groove 12"); h.at(260, "test-get bang")   # clear
    f = os.path.join(work, "t_groove.pd"); h.finish(300, f)
    out = run(work, f)
    rows = {n: [[int(float(x)) for x in v.split()] for v in printed(out, n)] for n in outs}
    kick = [2,0,0,0,1,0,0,0,2,0,0,0,1,0,0,0] * 2
    assert rows["D1"][0][:16] == kick[:16], f"slot 1 (kick) should get the tech house kick: {rows['D1'][0]}"
    assert printed(out, "ockm-drum-len")[-1] == "16", f"a groove makes the drums 1 bar: {printed(out, 'ockm-drum-len')}"
    assert rows["D4"][0][:16] == [1,1,0,1,1,1,0,1,1,1,0,1,1,1,0,1], f"slot 4 (hat) should get the hats: {rows['D4'][0]}"
    assert rows["D5"][0][:16] == [0,0,2,0,0,0,2,0,0,0,2,0,0,0,2,0], f"slot 5 (open hat) should get the open hats: {rows['D5'][0]}"
    assert [1 if v else 0 for v in rows["BASS-ON"][0][:16]] == [1 if v else 0 for v in kick[:16]], f"bass locked to the kick should follow the new kick: {rows['BASS-ON'][0]}"
    assert "54" in [v.split()[0].split(".")[0] for v in printed(out, "SWING")], f"tech house should set swing 54: {printed(out, 'SWING')}"
    assert all(v == 0 for n in ("D1", "D4", "D5") for v in rows[n][1][:16]), "clear should empty every slot"

@test
def suggest_chords_fit_the_melody(work):
    """Melody leads: the screen scores every progression against the lead notes and picks the best fit."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    def picks(notes):
        on = " ".join("1" if i % 4 == 0 else "0" for i in range(64))
        nt = " ".join(str(notes[(i // 4) % len(notes)]) for i in range(64))
        lines = ui_preview.run(["send ockm-length float 64", f"array ockm-pat-lead-on {on}", f"array ockm-pat-lead-note {nt}",
                                "send ockm-lead-mode float 1", "test tap 477 36", "test tap 186 154", "test tap 100 558"])
        return [int(float(l.split()[3])) for l in lines if l.startswith("sent ockm-chord-prog")]
    a_minor = picks([57, 60, 64])           # A C E: the home chord
    assert a_minor[0] == 0, f"a melody on A C E should suggest one chord first: {a_minor}"
    assert len(a_minor) == 2 and a_minor[1] != a_minor[0], f"a second tap should give the next suggestion: {a_minor}"
    # a melody that walks A minor, F, C, G one bar each: the pop progression (i VI III VII) should come first
    pop = picks([57, 60, 64, 57, 65, 69, 72, 65, 60, 64, 67, 60, 67, 71, 74, 67])
    assert ui_preview_shapes()[pop[0]] == [(0, 16), (5, 16), (2, 16), (6, 16)], f"expected the pop progression first: {pop}"
    empty = ui_preview.run(["test tap 477 36", "test tap 186 154"])
    assert not any(l.startswith("sent ockm-chord-prog") for l in empty), "no melody, no suggestion"

def ui_preview_shapes():
    """The progression shapes the screen uses, read back from its presets block."""
    import re
    line = next(l for l in open(os.path.join(ROOT, "ui", "ockm-ui.pd_lua")) if l.startswith("local PROG_SHAPES"))
    body = line.split("=", 1)[1].strip()[1:-1]
    progs, depth, cur = [], 0, ""
    for ch in body:
        if ch == "{": depth += 1
        if depth >= 1: cur += ch
        if ch == "}":
            depth -= 1
            if depth == 0: progs.append([(int(d), int(b)) for d, b in re.findall(r"\{ (\d+), (\d+) \}", cur)]); cur = ""
    return progs

@test
def touchscreen_velocity_timing_loop_and_banks(work):
    """Drums tab: drag a step's velocity up, switch to timing and pull it early, set the drums to 1 bar and double them,
    then pick a groove from the second bank."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-edit", "ockm-nudge", "ockm-drum-len", "ockm-drum-double", "ockm-drum-groove")
    h.at(100, "ockm-length 64 ; ockm-edit d1 0 1")
    h.at(200, "ockm-ui-test tap 539 36")              # drums tab
    h.at(300, "ockm-ui-test drag 45 336 45 302")      # velocity: drag step 1 to the top (accent)
    h.at(400, "ockm-ui-test tap 145 282")             # timing
    h.at(500, "ockm-ui-test drag 45 319 45 336")      # pull step 1 early
    h.at(600, "ockm-ui-test tap 612 88")              # drum length: 1 bar (navigation strip)
    h.at(700, "ockm-ui-test tap 909 88")              # double
    h.at(800, "ockm-ui-test tap 716 354")             # bank 2
    h.at(900, "ockm-ui-test tap 531 389")             # its first groove
    f = os.path.join(work, "t_lane_ui.pd"); h.finish(1000, f)
    out = run(work, f)
    edits = [e for e in printed(out, "ockm-edit") if e.startswith("d1 0")]
    assert edits and edits[-1].split()[-1] == "2", f"dragging to the top should make it an accent: {edits}"
    nud = [float(e.split()[-1]) for e in printed(out, "ockm-nudge") if e.startswith("d1 0")]
    assert nud and nud[-1] < -0.2, f"dragging down should pull it early: {nud}"
    loops = [int(float(v)) for v in printed(out, "ockm-drum-len")]
    assert 32 in loops and loops[-1] == 16, f"double should give 2 bars, then the groove makes the drums 1 bar again: {loops}"
    assert printed(out, "ockm-drum-groove")[-1:] == ["13"], f"bank 2's first groove is number 13: {printed(out, 'ockm-drum-groove')}"

@test
def touchscreen_exports_audio_stems_and_midi(work):
    """Project screen, export: the loop once, with the mix, stems and MIDI. The WAVs have sound in them,
    and the MIDI file is a proper type 1 file with drums on channel 10 and notes for each part."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness()
    h.at(100, "ockm-bass-gen bang ; ockm-chord-gen bang ; ockm-bpm 160")
    h.at(300, "ockm-ui-test tap 919 36 ; ockm-ui-test tap 830 95")      # project
    h.at(400, "ockm-ui-test tap 854 178")     # export...
    h.at(600, "ockm-ui-test tap 224 162")     # the loop plays once
    h.at(700, "ockm-ui-test tap 510 222")     # stems on
    h.at(800, "ockm-ui-test tap 736 222")     # MIDI on
    h.at(900, "ockm-ui-test tap 644 544")     # export
    f = os.path.join(work, "t_export.pd"); h.finish(6500, f)
    run(work, f, timeout=60)
    ex = os.path.join(work, "exports")
    files = sorted(os.listdir(ex)) if os.path.isdir(ex) else []
    wavs = [n for n in files if n.endswith(".wav")]
    mids = [n for n in files if n.endswith(".mid")]
    assert len(wavs) == 6, f"expected the mix and 5 stems: {files}"
    mix = [n for n in wavs if not any(n.endswith(f"-{s}.wav") for s in ["drums", "bass", "lead", "chord", "fx"])][0]
    w = wave.open(os.path.join(ex, mix)); assert w.getnchannels() == 2 and w.getsampwidth() == 3, "the mix should be 24-bit stereo"
    secs = w.getnframes() / w.getframerate()
    assert 3.0 < secs < 6.5, f"one bar at 160 bpm plus the tail should be about 4 seconds: {secs:.1f}"
    raw = w.readframes(w.getnframes()); w.close()
    loud = max(abs(int.from_bytes(raw[i:i + 3], "little", signed=True)) for i in range(0, len(raw), 6 * 50))
    assert loud > 100000, "the mix is silent"
    assert len(mids) == 1, f"expected one MIDI file: {files}"
    m = open(os.path.join(ex, mids[0]), "rb").read()
    assert m[:4] == b"MThd" and m[8:10] == b"\x00\x01" and m[10:12] == b"\x00\x05", "MIDI header: type 1, 5 tracks"
    assert m.count(b"MTrk") == 5
    assert b"\x99" in m, "drum notes on channel 10"
    assert b"\x90" in m and b"\x92" in m, "bass (channel 1) and chords (channel 3) notes"

@test
def touchscreen_exports_the_loop_and_records_live(work):
    """Export the loop once (1 bar at 160 bpm): it stops by itself at the end and lets the effects ring out.
    Then 'record what I play': recording runs until the red stop button."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness()
    h.at(100, "ockm-bass-gen bang ; ockm-bpm 160")
    h.at(300, "ockm-ui-test tap 919 36 ; ockm-ui-test tap 830 95"); h.at(400, "ockm-ui-test tap 854 178")   # project, export...
    h.at(500, "ockm-ui-test tap 224 162")     # the loop plays once
    h.at(600, "ockm-ui-test tap 644 544")     # export (stereo mix)
    h.at(8000, "ockm-ui-test tap 919 36 ; ockm-ui-test tap 830 95"); h.at(8100, "ockm-ui-test tap 854 178")
    h.at(8200, "ockm-ui-test tap 154 544")    # record what I play
    h.at(8300, "ockm-play 1")
    h.at(9800, "ockm-ui-test tap 803 36")     # stop recording
    f = os.path.join(work, "t_export_song.pd"); h.finish(10200, f)
    run(work, f, timeout=60)
    ex = os.path.join(work, "exports")
    files = sorted(os.listdir(ex)) if os.path.isdir(ex) else []
    song = [n for n in files if "-loop-" in n and n.endswith(".wav")]
    live = [n for n in files if "-live-" in n and n.endswith(".wav")]
    assert len(song) == 1 and len(live) == 1, f"expected a loop mix and a live recording: {files}"
    w = wave.open(os.path.join(ex, song[0])); secs = w.getnframes() / w.getframerate(); w.close()
    assert 3.2 < secs < 5, f"1 bar at 160 bpm (1.5 s) plus a 2.5 s tail: {secs:.1f} s"
    w = wave.open(os.path.join(ex, live[0])); secs = w.getnframes() / w.getframerate(); w.close()
    assert 1.2 < secs < 2.2, f"the live recording should be about 1.6 s: {secs:.1f} s"

@test
def drum_slot_909_808_industrial_tone_drive(work):
    """A slot switches between its 909, 808 and industrial sounds (ockm-<slot>-synth 0, 1, 2), each different;
    tone darkens or brightens it and drive makes it louder and grittier."""
    h = Harness(); h.record(os.path.join(work, "abc.wav"))
    others = " ; ".join(f"ockm-{t}-mute 1" for t in ["d2","d3","d4","d5","d6","d7","d8","bass","lead","chord"])
    h.at(100, f"ockm-verb-mix 0 ; ockm-delay-mix 0 ; ockm-d1-sound 0 ; ockm-d1-sample 0 ; ockm-d1-verb 0 ; ockm-d1-delay 0 ; {others}")
    for i, (syn, tone, drive) in enumerate([(0, 0, 0), (1, 0, 0), (2, 0, 0), (0, -0.8, 0), (0, 0.8, 0), (0, 0, 1)]):
        t0 = 300 + i * 900
        h.at(t0, f"ockm-d1-synth {syn} ; ockm-d1-tone {tone} ; ockm-d1-drive {drive}")
        h.at(t0 + 50, "ockm-d1-audition 1")
    out, (x, sr) = play(work, h, "t_abc", ms=300 + 6 * 900 + 200)
    segs = [x[int((0.35 + i * 0.9) * sr):int((0.35 + i * 0.9 + 0.6) * sr)] for i in range(6)]
    pk = [peak(sg) for sg in segs]
    assert min(pk) > 0.05, f"every version should sound: {[round(p, 3) for p in pk]}"
    lens = [sum(1 for v in sg if abs(v) > 0.02) / sr for sg in segs[:3]]
    assert lens[1] > lens[0] * 1.3, f"the 808 kick should ring longer than the 909 ({lens[0]:.2f} vs {lens[1]:.2f} s)"
    # brightness: share of the signal that is fast change (a simple high-frequency measure)
    def bright(sg): return sum(abs(sg[i] - sg[i - 1]) for i in range(1, len(sg))) / (sum(abs(v) for v in sg) + 1e-9)
    assert bright(segs[3]) < bright(segs[0]) < bright(segs[4]), f"tone should darken then brighten: {bright(segs[3]):.3f} {bright(segs[0]):.3f} {bright(segs[4]):.3f}"
    rms = lambda sg: math.sqrt(sum(v * v for v in sg) / len(sg))
    assert rms(segs[5]) > rms(segs[0]) * 1.1, "drive should make it denser"

@test
def touchscreen_demud_listens_and_cuts(work):
    """Mixer, while the demo groove plays: de-mud listens for 4 seconds, then sets low cuts from what it heard.
    The hats get a real low cut; the kick and bass are left alone."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-d1-lowcut", "ockm-d4-lowcut", "ockm-bass-lowcut", "ockm-spec-all")
    h.at(100, "ockm-bass-gen bang ; ockm-chord-gen bang ; ockm-play 1")
    h.at(600, "ockm-ui-test tap 407 36")      # mixer
    h.at(700, "ockm-ui-test tap 905 232")     # de-mud (master strip)
    h.at(5200, "ockm-play 0")
    f = os.path.join(work, "t_demud.pd"); h.finish(5400, f)
    out = run(work, f, timeout=60)
    spec = [int(float(v)) for v in printed(out, "ockm-spec-all")]
    assert spec[:2] == [1, 0], f"the analysers should switch on to listen, then off: {spec}"
    hat = [float(v) for v in printed(out, "ockm-d4-lowcut")]
    assert hat and hat[-1] >= 120, f"the hats should get a low cut of 120 Hz or more: {hat}"
    assert not printed(out, "ockm-d1-lowcut") and not printed(out, "ockm-bass-lowcut"), "the kick and bass keep their low end"

@test
def undo_takes_back_the_last_big_change(work):
    """A snapshot goes to undo/ without counting as a save; undo brings back the drums.
    On the screen: de-mud offers an undo button, and tapping it puts the low cuts back."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-saved", "ockm-d4-lowcut")
    g = h.add("#X obj 10 300 r test-get;"); a = h.add("#X obj 10 350 array get ockm-pat-d1 0 16;"); pr = h.add("#X obj 10 375 print D1;")
    h.con(g, a); h.con(a, pr)
    h.at(100, "test-get bang")
    h.at(200, "ockm-snapshot bang")
    h.at(250, "ockm-drum-groove 12")
    h.at(300, "test-get bang")
    h.at(350, "ockm-undo bang")
    h.at(450, "test-get bang")
    h.at(500, "ockm-ui-test tap 407 36")      # mixer
    h.at(550, "ockm-ui-test tap 905 232")     # de-mud while stopped: fixed low cuts, with an undo button
    h.at(600, "ockm-ui-test tap 761 569")     # undo
    f = os.path.join(work, "t_undo.pd"); h.finish(800, f)
    out = run(work, f)
    d1 = [[int(float(x)) for x in v.split()] for v in printed(out, "D1")]
    assert len(d1) == 3 and any(d1[0]) and not any(d1[1]), f"the groove should be there, then cleared: {d1}"
    assert d1[2] == d1[0], f"undo should bring the drums back: {d1}"
    assert os.path.exists(os.path.join(work, "undo", "loop.txt")) and os.path.exists(os.path.join(work, "undo", "project.txt")), "the snapshot lives in undo/"
    assert not os.path.exists(os.path.join(work, "projects", "undo")), "undo/ sits beside projects/, never inside it"
    assert not printed(out, "ockm-saved"), "a snapshot isn't a save"
    lc = [float(v) for v in printed(out, "ockm-d4-lowcut")]
    hi = [i for i, v in enumerate(lc) if v >= 100]
    assert hi and lc[-1] == 20 and hi[-1] < len(lc) - 1, f"de-mud sets the hat's low cut, undo puts it back to 20: {lc}"

@test
def touchscreen_compose_mutes_and_solos(work):
    """Compose: each part's card has M and S, the same mute and solo as perform and the mixer."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-bass-mute", "ockm-lead-solo", "ockm-chord-mute")
    h.at(100, "ockm-ui-test tap 477 36")      # compose
    h.at(200, "ockm-ui-test tap 425 278")     # bass M
    h.at(300, "ockm-ui-test tap 778 278")     # lead S
    h.at(400, "ockm-ui-test tap 112 278")     # chord M
    h.at(500, "ockm-ui-test tap 425 278")     # bass M again: unmute
    f = os.path.join(work, "t_compose_ms.pd"); h.finish(700, f)
    out = run(work, f)
    assert [int(float(v)) for v in printed(out, "ockm-bass-mute")] == [1, 0], f"bass M should mute, then unmute: {printed(out, 'ockm-bass-mute')}"
    assert printed(out, "ockm-lead-solo")[-1:] == ["1"], "lead S should solo the lead"
    assert printed(out, "ockm-chord-mute")[-1:] == ["1"], "chord M should mute the chords"

@test
def touchscreen_steps_act_on_press(work):
    """A drum step changes the moment a finger lands (before it lifts), like a drum machine pad.
    Pressing a step and swiping sideways puts the step back and turns the page instead."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-edit", "ockm-page")
    h.at(50, "ockm-length 32")                        # 2 bars, so there's a second page to swipe to
    h.at(100, "ockm-ui-test tap 539 36")              # drums
    h.at(200, "ockm-ui-test press 105 212")           # step 2 of the kick: finger down only
    h.at(300, "ockm-ui-test release 105 212")
    h.at(400, "ockm-ui-test drag 400 212 100 212")    # press step 7, then swipe left
    f = os.path.join(work, "t_press.pd"); h.finish(600, f)
    out = run(work, f)
    edits = printed(out, "ockm-edit")
    assert edits[0] == "d1 1 1", f"the step should change as the finger lands: {edits}"
    assert len(edits) >= 3 and edits[1].split()[:2] == ["d1", "6"] and edits[2] == "d1 6 0", f"a swipe should put the pressed step back: {edits}"
    assert printed(out, "ockm-page")[-1:] == ["1"], f"the swipe should turn the page: {printed(out, 'ockm-page')}"

@test
def part_lengths_repeat_inside_the_loop(work):
    """Each part has its own length; the loop is as long as the longest. A 1-bar drum part under a 4-bar bass plays
    its kick 4 times per loop. Shortening the bass shortens the loop, a longer chord part lengthens it, and
    ockm-drum-double doubles only the drums (copying their bar)."""
    h = Harness(); h.show("ockm-len", "ockm-kick-hit", "ockm-drum-len", "ockm-drum-loop")
    g = h.add("#X obj 10 300 r test-get;"); a = h.add("#X obj 10 330 array get ockm-pat-d1 0 32;"); pr = h.add("#X obj 10 360 print D1;")
    h.con(g, a); h.con(a, pr)
    h.at(90, "ockm-bass-sync 0 ; ockm-lead-sync 0")              # independent lengths (a part following the chords takes theirs)
    h.at(100, "ockm-bpm 240 ; ockm-swing 50 ; ockm-drum-len 16 ; ockm-bass-len 64 ; ockm-lead-len 16 ; ockm-chord-len 16")
    h.at(150, "ockm-pat-d1 const 0 ; ockm-pat-d1 0 1")          # one kick, on the first step of the drum bar
    h.at(200, "ockm-play 1")
    h.at(200 + 64 * 62.5 - 20, "ockm-play 0")                     # exactly one 4-bar loop at 240 bpm
    h.at(4500, "ockm-bass-len 32")                                # loop shrinks to 2 bars
    h.at(4600, "ockm-chord-len 128")                              # and grows to 8
    h.at(4700, "ockm-pat-d1 2 1 ; ockm-drum-double bang")         # drums: 1 bar -> 2 bars, bar 1 copied
    h.at(4800, "test-get bang")
    f = os.path.join(work, "t_lens.pd"); h.finish(5000, f)
    out = run(work, f)
    kicks = printed(out, "ockm-kick-hit")
    assert len(kicks) == 4, f"a 1-bar kick part in a 4-bar loop should play 4 times: {len(kicks)}"
    lens = [int(float(v)) for v in printed(out, "ockm-len")]
    lens = [v for i, v in enumerate(lens) if i == 0 or v != lens[i - 1]]   # it may be re-sent unchanged
    assert lens[-3:] == [64, 32, 128], f"the loop should follow the longest part (64, then 32, then 128): {lens}"
    assert printed(out, "ockm-drum-len")[-1] == "32", f"double should make the drums 2 bars: {printed(out, 'ockm-drum-len')}"
    d1 = [int(float(x)) for x in printed(out, "D1")[-1].split()]
    assert d1[16] == 1 and d1[18] == 1, f"double should copy bar 1 (steps 1 and 3) into bar 2: {d1}"
    assert printed(out, "ockm-drum-loop")[-1] == "32", f"the screens hear the drums are shorter than the loop: {printed(out, 'ockm-drum-loop')}"

@test
def parts_following_the_chords_take_their_length(work):
    """A bass or melody that follows the chords takes the chord part's length; one that doesn't keeps its own."""
    h = Harness(); h.show("ockm-bass-len", "ockm-lead-len")
    h.at(100, "ockm-bass-sync 1 ; ockm-lead-sync 0 ; ockm-bass-len 16 ; ockm-lead-len 16")
    h.at(200, "ockm-chord-len 64")
    f = os.path.join(work, "t_follow_len.pd"); h.finish(400, f)
    out = run(work, f)
    assert printed(out, "ockm-bass-len")[-1] == "64", f"the bass follows the chords to 4 bars: {printed(out, 'ockm-bass-len')}"
    assert printed(out, "ockm-lead-len")[-1] == "16", f"the melody doesn't follow, so it stays 1 bar: {printed(out, 'ockm-lead-len')}"

@test
def part_lengths_save_and_older_files_load(work):
    """Part lengths are saved with the loop and come back. An older loop file with one length and a drums loop
    loads as: drums the drums-loop length, every other part the old length."""
    h = Harness(); h.show("ockm-len", "ockm-drum-len", "ockm-bass-len", "ockm-chord-len")
    h.at(90, "ockm-bass-sync 0 ; ockm-lead-sync 0")
    h.at(100, "ockm-drum-len 16 ; ockm-bass-len 64 ; ockm-lead-len 32 ; ockm-chord-len 128 ; ockm-save bang")
    h.at(200, "ockm-drum-len 64 ; ockm-chord-len 16")
    h.at(300, "ockm-revert bang")
    f = os.path.join(work, "t_lens_save.pd"); h.finish(500, f)
    out = run(work, f)
    assert printed(out, "ockm-drum-len")[-1] == "16" and printed(out, "ockm-chord-len")[-1] == "128", \
        f"back to last save should restore the part lengths: drum {printed(out, 'ockm-drum-len')} chord {printed(out, 'ockm-chord-len')}"
    assert printed(out, "ockm-len")[-1] == "128", f"the loop length after loading: {printed(out, 'ockm-len')}"
    saved = open(os.path.join(work, "projects", "default", "loop.txt")).read()
    assert "ockm-bass-len 64" in saved and "ockm-len " not in saved, "loop.txt keeps part lengths, not one length"
    # an older file: one length (32) and drums looping at 16
    lp = os.path.join(work, "projects", "default", "loop.txt")
    old = [l for l in open(lp).read().split(";\n") if l.strip() and not l.strip().startswith(("ockm-drum-len", "ockm-bass-len", "ockm-lead-len", "ockm-chord-len"))]
    open(lp, "w").write(";\n".join(old + ["ockm-drum-loop 16", "ockm-len 32"]) + ";\n")
    h2 = Harness(); h2.show("ockm-len", "ockm-drum-len", "ockm-bass-len")
    h2.at(100, "ockm-revert bang")                                # read the older file again, now we're listening
    f2 = os.path.join(work, "t_lens_old.pd"); h2.finish(400, f2)
    out2 = run(work, f2)
    assert printed(out2, "ockm-drum-len")[-1:] == ["16"] and printed(out2, "ockm-bass-len")[-1:] == ["32"], \
        f"an older file: drums 16, the rest 32: drum {printed(out2, 'ockm-drum-len')} bass {printed(out2, 'ockm-bass-len')}"
    assert printed(out2, "ockm-len")[-1:] == ["32"], f"the loop is the old length: {printed(out2, 'ockm-len')}"

@test
def touchscreen_part_lengths_and_undo(work):
    """Bass tab: the length buttons on the strip set the bass's own length; the loop follows the longest part.
    Shortening offers undo, which brings the old length back. Double doubles just this part."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-bass-len", "ockm-len", "ockm-drum-len")
    h.at(90, "ockm-bass-sync 0")                      # its own length, not the chords'
    h.at(100, "ockm-ui-test tap 601 36")              # bass tab
    h.at(200, "ockm-ui-test tap 724 88")              # 4 bars
    h.at(300, "ockm-ui-test tap 612 88")              # 1 bar: shorter, so undo is offered
    h.at(400, "ockm-ui-test tap 761 569")             # undo
    h.at(600, "ockm-ui-test tap 909 88")              # double: 4 -> 8 bars
    f = os.path.join(work, "t_partlen_ui.pd"); h.finish(800, f)
    out = run(work, f)
    bl = [int(float(v)) for v in printed(out, "ockm-bass-len")]
    assert bl[:2] == [64, 16], f"the length buttons should set the bass to 4 bars, then 1: {bl}"
    assert 64 in bl[2:-1] and bl[-1] == 128, f"undo should bring back 4 bars, then double makes 8: {bl}"
    assert printed(out, "ockm-len")[-1] == "128", f"the loop follows the longest part: {printed(out, 'ockm-len')}"
    assert set(printed(out, "ockm-drum-len")) <= {"16"}, f"the drums keep their own length (undo re-sends it unchanged): {printed(out, 'ockm-drum-len')}"

def write_tone(path, hz, secs, sr=44100, channels=1):
    w = wave.open(path, "w"); w.setnchannels(channels); w.setsampwidth(2); w.setframerate(sr)
    n = int(secs * sr)
    fr = [int(20000 * math.sin(2 * math.pi * hz * i / sr) * (1 - i / n)) for i in range(n)]
    w.writeframes(b"".join(struct.pack("<" + "h" * channels, *([v] * channels)) for v in fr)); w.close()

def raw_hz(x, sr):
    """pitch of a clean tone: upward zero crossings, no smoothing"""
    z = sum(1 for i in range(1, len(x)) if x[i - 1] < 0 <= x[i])
    return z / (len(x) / sr)

@test
def samples_load_and_play_on_drum_slots(work):
    kd = os.path.join(work, "samples", "kick"); pd_ = os.path.join(work, "samples", "perc")
    write_tone(os.path.join(kd, "01.wav"), 440, 0.4, sr=48000, channels=2)   # stereo, 48k: still plays at the right pitch
    write_tone(os.path.join(kd, "02.wav"), 880, 0.4)
    open(os.path.join(kd, "02.wav.asd"), "w").write("not audio")              # Ableton leaves these about
    write_tone(os.path.join(pd_, "01.wav"), 660, 0.3)
    h = Harness(); h.show("ockm-sample-counts")
    h.at(200, "ockm-samples-scan bang")
    h.record(os.path.join(work, "smp.wav"))
    h.at(300, "ockm-d1-sound 0 ; ockm-d1-sample 1 ; ockm-d1-verb 0 ; ockm-d1-delay 0")
    h.at(400, "ockm-d1-audition 1")            # 440
    h.at(1000, "ockm-d1-sample 2")
    h.at(1100, "ockm-d1-audition 1")           # 880
    h.at(1700, "ockm-d1-sample 1 ; ockm-d1-tune 12")
    h.at(1800, "ockm-d1-audition 1")           # 440 an octave up
    h.at(2400, "ockm-d1-tune 0 ; ockm-d1-decay 25")
    h.at(2500, "ockm-d1-audition 1")           # cut short
    h.at(3100, "ockm-d1-decay 100 ; ockm-d1-sample 0")
    h.at(3200, "ockm-d1-audition 1")           # back to the synth kick
    h.at(3800, "ockm-d1-sample 3")             # no third kick: silent, not the old sample
    h.at(3900, "ockm-d1-audition 1")
    h.at(4400, "ockm-d1-sample 1 ; ockm-d1-start 1")   # start 1: skip 40% in
    h.at(4500, "ockm-d1-audition 1")
    out, (x, sr) = play(work, h, "t_samples", ms=5100)
    counts = printed(out, "ockm-sample-counts")
    assert counts and counts[-1].split()[:4] == ["2", "0", "0", "1"], f"sample counts wrong: {counts}"
    t0 = 0.2   # recording starts at 200 ms
    def seg(a, b): return x[int((a - t0) * sr):int((b - t0) * sr)]
    f1 = raw_hz(seg(0.42, 0.6), sr); f2 = raw_hz(seg(1.12, 1.3), sr); f3 = raw_hz(seg(1.82, 1.9), sr)
    assert 400 < f1 < 480, f"sample 1 should play at 440 Hz ({f1:.0f})"
    assert 820 < f2 < 940, f"sample 2 should play at 880 Hz ({f2:.0f})"
    assert 820 < f3 < 940, f"tune +12 should double the pitch ({f3:.0f})"
    full, cut = peak(seg(0.65, 0.75)), peak(seg(2.65, 2.75))
    assert full > 0.05 and cut < full * 0.2, f"decay 25 should cut the tail ({full:.2f} vs {cut:.2f})"
    k = seg(3.22, 3.4); assert peak(k) > 0.05 and cycles_per_second(k, sr) < 200, "sample 0 should give the synth kick back"
    assert peak(seg(3.92, 4.3)) < 0.01, "a missing sample should be silent"
    def audible(a, b): return sum(1 for v in seg(a, b) if abs(v) > 0.01) / sr
    full, cut = audible(0.4, 0.95), audible(4.5, 5.05)
    assert 0.5 < cut / full < 0.7, f"start 1 should skip 40% of the sample ({full:.2f} s vs {cut:.2f} s)"

@test
def touchscreen_picks_samples_and_kits(work):
    """Drums tab: arrows step through the folder (and stop at the end), the box plays it, and 'new kit' picks for every slot that has samples."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    kd = os.path.join(work, "samples", "kick")
    write_tone(os.path.join(kd, "01.wav"), 110, 0.2); write_tone(os.path.join(kd, "02.wav"), 220, 0.2)
    write_tone(os.path.join(work, "samples", "perc", "01.wav"), 330, 0.2)
    h = Harness(); h.show("ockm-d1-sample", "ockm-d1-audition", "ockm-d6-sample", "ockm-d7-sample", "ockm-d1-sound")
    h.at(100, "ockm-ui-test tap 539 36")      # drums tab: counts the folders
    h.at(300, "ockm-ui-test tap 366 380")     # 909 -> 808
    h.at(350, "ockm-ui-test tap 366 380")     # -> industrial
    h.at(400, "ockm-ui-test tap 366 380")     # -> sample 1
    h.at(500, "ockm-ui-test tap 366 380")     # 2
    h.at(700, "ockm-ui-test tap 366 380")     # only 2 kicks: stays put
    h.at(900, "ockm-ui-test tap 200 380")     # tap the box: hear it
    h.at(1300, "ockm-ui-test tap 430 380")    # new kit: perc 1 and perc 2 get the perc sample
    f = os.path.join(work, "t_samples_ui.pd"); h.finish(1500, f)
    out = run(work, f)
    d1 = [int(float(v)) for v in printed(out, "ockm-d1-sample")]
    picked = [v for v in d1 if v > 0]
    assert picked[:2] == [1, 2] and len(picked) <= 3, f"sample steps wrong (the last one is new kit's pick): {d1}"
    assert len(printed(out, "ockm-d1-audition")) >= 3, f"should play on each change and on tapping the box: {printed(out, 'ockm-d1-audition')}"
    assert printed(out, "ockm-d6-sample") == ["1"] and printed(out, "ockm-d7-sample") == ["1"], "new kit should give both perc slots a sample"

def main():
    if not PD:
        sys.exit("Can't find Pure Data. Install it, or set PD=/path/to/pd")
    picks = sys.argv[1:]
    chosen = [t for t in TESTS if not picks or any(p in t.__name__ for p in picks)]
    passed = skipped = 0
    for t in chosen:
        work = tempfile.mkdtemp(prefix="ockm-test-")
        for item in ["OCKM_GENERATOR.pd", "voices", "seq", "ui"]:
            src = os.path.join(ROOT, item)
            (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, os.path.join(work, item))
        # only the blank starter project, opened at start-up: never your own projects (or whichever you used last)
        os.makedirs(os.path.join(work, "projects"))
        shutil.copytree(os.path.join(ROOT, "projects", "default"), os.path.join(work, "projects", "default"))
        open(os.path.join(work, "projects", "current.txt"), "w").write("default;\n")
        # the tests play the demo grooves, not your saved project or the blank starter
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build.py"), "--out", work, "--reset-patterns", "--demo"],
                       check=True, capture_output=True)
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
