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
        self.add("#X declare -path voices -path seq -path lab;", raw=True)
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
        lines += ["#X obj 10 500 declare -path voices -path seq -path lab;"]
        open(path, "w").write("\n".join(lines) + "\n")


def run(work, harness_file, with_main=True, timeout=90, main="OCKM_GENERATOR.pd"):
    cmd = [PD, "-nogui", "-nosound", "-nomidi", "-stderr"]
    if PDLUA:
        cmd += ["-path", PDLUA, "-lib", "pdlua"]
    if with_main:
        cmd += ["-open", main]
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
    """Every drum slot sound (the drum lab's voices, and the perc slots' rim, conga and shaker) plays,
    a half-strength hit is about half as loud, and tune +12 doubles the kick's pitch."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    for snd, syn, name in [(0, 0, "kick"), (1, 0, "snare"), (2, 0, "clap"), (4, 0, "hat"), (5, 0, "open hat"), (6, 0, "tom"),
                           (3, 0, "rim"), (3, 1, "conga"), (3, 2, "shaker")]:
        h = Harness(dut="ockm-drum x")
        h.record(os.path.join(work, f"v_{snd}{syn}.wav"), source="dut")
        h.at(20, f"ockm-x-sound {snd} ; ockm-x-synth {syn} ; ockm-x-sample 0")
        h.at(50, "test-in 1"); h.at(650, "test-in 0.5")
        _, (s, sr) = play(work, h, f"t_voice_{snd}{syn}", with_main=False, ms=1250)
        A, B = s[int(0.05 * sr):int(0.6 * sr)], s[int(0.65 * sr):int(1.2 * sr)]
        assert peak(A) > 0.05, f"{name} is silent"
        a, b = math.sqrt(sum(x * x for x in A) / len(A)), math.sqrt(sum(x * x for x in B) / len(B))   # average level: metal voices beat, peaks jump about
        assert 0.35 < b / a < 0.65, f"{name}: half-strength hit should be about half as loud ({b / a:.2f})"
    h = Harness(dut="ockm-drum x"); h.record(os.path.join(work, "v_tune.wav"), source="dut")
    h.at(20, "ockm-x-sound 0 ; ockm-x-sample 0")
    h.at(50, "test-in 1"); h.at(600, "ockm-x-tune 12"); h.at(610, "test-in 1")
    _, (s, sr) = play(work, h, "t_tune", with_main=False, ms=1100)
    f0 = cycles_per_second(s[int(0.08 * sr):int(0.2 * sr)], sr)
    f1 = cycles_per_second(s[int(0.64 * sr):int(0.76 * sr)], sr)
    assert 1.6 < f1 / f0 < 2.4, f"kick tuned +12 should be about twice the pitch ({f0:.0f} -> {f1:.0f})"

@test
def synth_kits_sound_like_their_machines(work):
    """v1.49 the synth kits (no samples): the 808 kick is a long, low boom; the 909 kick is shorter and has more click up
    top; the 909 long kick rings longer than the 909. Every kit's kick, snare, clap and hats sound and don't clip."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    def hit(kit, snd):
        h = Harness(dut="ockm-drum x"); name = f"kit{kit}-{snd}"
        h.record(os.path.join(work, name + ".wav"), source="dut")
        h.at(20, f"ockm-x-sound {snd} ; ockm-x-synth 0 ; ockm-x-sample 0 ; ockm-x-labkit {kit}")
        h.at(100, "test-in 1")
        _, (x, sr) = play(work, h, name, with_main=False, ms=1600)
        return x[int(0.1 * sr):], sr
    def length(x, sr):   # how long until it falls 40 dB under its peak (in 10 ms blocks)
        pk = peak(x); n = int(0.01 * sr); last = 0
        for i in range(0, len(x) - n, n):
            if peak(x[i:i + n]) > pk * 0.01: last = i
        return last / sr
    def top(x, sr):   # share of the first 20 ms in the top end (sample-to-sample differences)
        a = x[:int(0.02 * sr)]
        d = sum(abs(a[i] - a[i - 1]) for i in range(1, len(a))); e = sum(abs(v) for v in a) or 1
        return d / e
    k808, sr = hit(1, 0); k909, _ = hit(2, 0); k909l, _ = hit(3, 0)
    assert length(k808, sr) > length(k909, sr) * 1.5, f"the 808 kick rings much longer: {length(k808, sr):.2f} vs {length(k909, sr):.2f}"
    assert length(k909l, sr) > length(k909, sr) * 1.3, f"the 909 long kick rings longer than the 909: {length(k909l, sr):.2f} vs {length(k909, sr):.2f}"
    assert top(k909, sr) > top(k808, sr) * 1.3, f"the 909 kick has more click: {top(k909, sr):.3f} vs {top(k808, sr):.3f}"
    for kit in (1, 2, 3):
        for snd in (1, 2, 4, 5):
            x, sr = hit(kit, snd)
            assert 0.05 < peak(x) <= 1.0, f"kit {kit} sound {snd}: level {peak(x):.2f}"

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
def drum_lanes_thin_and_roll(work):
    """v1.49 smarter drum lanes, in Pd: thinning keeps the important steps, a roll plays its hits across the step,
    and a bar condition holds a lane back."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(dut="ockm-row zz"); h.show("test-out")
    h.add("#X obj 400 70 print ROWOUT;"); h.con(h.dut, len([o for o in h.objs if not o[1]]) - 1)
    h.at(100, "ockm-pat-zz 0 1 1 1 1 1 1 1 1 ; ockm-accent 0.3 ; ockm-stepms 100 ; ockm-zz-thin 0.5")
    h.at(120, "test-in 0 , 1 , 2 , 3")
    h.at(200, "ockm-zz-thin 0 ; ockm-rat zz 4 3")
    h.at(220, "test-in 4")
    h.at(500, "ockm-zz-when 3 ; ockm-bar bang")
    h.at(520, "test-in 5")
    h.at(600, "ockm-bar bang ; ockm-bar bang ; ockm-bar bang")
    h.at(620, "test-in 6")
    f = os.path.join(work, "t_lanes.pd"); h.finish(900, f)
    out = run(work, f)
    got = [round(float(x), 2) for x in printed(out, "ROWOUT")]
    assert len(got) == 5, f"expected 1 thinned hit, a roll of 3, then 1 hit in the 4th bar: {got}"
    assert got[0] == 0.7 and got[1] == 0.7 and got[2] < 0.7 and got[3] < got[2], f"roll hits wrong: {got}"

@test
def four_bar_build_climbs_then_drops(work):
    """v1.49 the 4 bar build: armed, it starts on the next bar line. The snare plays quarters, then 8ths, then 16ths,
    then rolls (more hits than steps) in bar 4; the kick drops out for bar 4; after four bars the drums are their own
    again, on the drop."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    def bars(sound, pat):
        h = Harness(dut="ockm-row zz"); h.show("test-out")
        h.add("#X obj 400 70 print ROWOUT;"); h.con(h.dut, len([o for o in h.objs if not o[1]]) - 1)
        h.at(100, f"ockm-pat-zz const 0 ; ockm-pat-zz 0 {pat} ; ockm-accent 0.3 ; ockm-stepms 40 ; ockm-zz-sound {sound} ; ockm-build 1")
        t = 200
        for b in range(5):
            h.at(t, f"ockm-bar bang ; test-print symbol BAR{b}"); t += 20
            for st in range(16):
                h.at(t, f"test-in {st}"); t += 45
        p_ = h.add("#X obj 600 40 r test-print;"); pr = h.add("#X obj 600 70 print ROWOUT;"); h.con(p_, pr)
        f = os.path.join(work, f"t_build{sound}.pd"); h.finish(t + 200, f)
        out = run(work, f)
        counts, cur = [], None
        for line in out.splitlines():
            if line.startswith("ROWOUT:"):
                v = line.split(":", 1)[1].strip()
                if v.startswith("symbol BAR") or v.startswith("BAR"): counts.append(0); continue
                if counts: counts[-1] += 1
        return counts
    snare = bars(1, "")
    assert snare[:3] == [4, 8, 16], f"the snare climbs: quarters, 8ths, 16ths: {snare}"
    assert snare[3] > 16, f"bar 4 rolls (more hits than steps): {snare}"
    assert snare[4] == 0, f"after four bars the snare is your own pattern again (empty here): {snare}"
    kick = bars(0, "1 0 0 0 1 0 0 0 1 0 0 0 1 0 0 0")
    assert kick == [4, 4, 4, 0, 4], f"the kick plays on, drops out for bar 4, and is back on the drop: {kick}"

@test
def restart_keeps_unsaved_work(work):
    """v1.49 an update restarts the box: unsaved work comes back. A blank project gets a style (not saved); the restart
    script's "keep;" (UDP 3091) stashes it and leaves a note; the next start opens the project and brings it back from
    the stash, so it plays. Saved work isn't touched: with nothing unsaved, no note is left."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    pdsend = shutil.which("pdsend")
    proj = os.path.join(work, "projects", "kp")
    shutil.copytree(os.path.join(work, "projects", "default"), proj)
    open(os.path.join(work, "projects", "current.txt"), "w").write("kp;\n")
    note = os.path.join(work, "stash", "kept-on-restart.txt")
    lp = os.path.join(proj, "loop.txt"); before = open(lp).read()
    h = Harness()
    h.at(1200, "ockm-ui-test tap 239 36"); h.at(1300, "ockm-ui-test tap 584 174")   # build, a style: unsaved
    f = os.path.join(work, "t_keep1.pd"); h.finish(3500 if pdsend else 2500, f)
    if pdsend:
        p = subprocess.Popen([PD, "-nogui", "-nosound", "-nomidi", "-stderr", "-path", PDLUA, "-lib", "pdlua", "-open", "OCKM_GENERATOR.pd", "-open", f],
                             cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        import time; time.sleep(2.2)
        subprocess.run([pdsend, "3091", "localhost", "udp"], input="keep;\n", text=True, timeout=5)
        p.communicate(timeout=60)
    else:
        h2 = Harness(); h2.at(1200, "ockm-ui-test tap 239 36"); h2.at(1300, "ockm-ui-test tap 584 174"); h2.at(1800, "ockm-keep bang")
        h2.finish(2500, f); run(work, f)
    assert os.path.exists(note) and open(note).read().strip() == "kp", "keep: a note naming the open project"
    assert open(lp).read() == before, "the project itself isn't saved"
    h3 = Harness(); h3.record(os.path.join(work, "kept.wav")); h3.at(1500, "ockm-play 1"); h3.at(4500, "ockm-play 0")
    _, (snd, sr) = play(work, h3, "t_keep2", ms=5000)
    assert peak(snd) > 0.05, f"after the restart the unsaved loop plays: peak {peak(snd):.3f}"
    assert not os.path.exists(note), "the note is used up"
    # nothing unsaved: no note
    h4 = Harness(); h4.at(1500, "ockm-keep bang"); f4 = os.path.join(work, "t_keep3.pd"); h4.finish(2000, f4); run(work, f4)
    assert not os.path.exists(note), "saved (just opened): keep leaves nothing"

@test
def four_bar_rush_brings_the_kick_back(work):
    """v1.49 the 4 bar rush: the kick is out for three bars and back four to the floor in the last, the open hat plays
    every 8th in the last bar, and after it the drums are your own."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    def bars(sound, pat):
        h = Harness(dut="ockm-row zz"); h.show("test-out")
        h.add("#X obj 400 70 print ROWOUT;"); h.con(h.dut, len([o for o in h.objs if not o[1]]) - 1)
        h.at(100, f"ockm-pat-zz const 0 ; ockm-pat-zz 0 {pat} ; ockm-accent 0.3 ; ockm-stepms 40 ; ockm-zz-sound {sound} ; ockm-build 2")
        t = 200
        for b in range(5):
            h.at(t, f"ockm-bar bang ; test-print symbol BAR{b}"); t += 20
            for st in range(16):
                h.at(t, f"test-in {st}"); t += 45
        p_ = h.add("#X obj 600 40 r test-print;"); pr = h.add("#X obj 600 70 print ROWOUT;"); h.con(p_, pr)
        f = os.path.join(work, f"t_rush{sound}.pd"); h.finish(t + 200, f)
        counts = []
        for line in run(work, f).splitlines():
            if line.startswith("ROWOUT:"):
                v = line.split(":", 1)[1].strip()
                if "BAR" in v: counts.append(0)
                elif counts: counts[-1] += 1
        return counts
    kick = bars(0, "1 0 0 0 1 0 0 0 1 0 0 0 1 0 0 0")
    assert kick == [0, 0, 0, 4, 4], f"the kick: out, out, out, back for the last bar, then yours: {kick}"
    ohat = bars(5, "")
    assert ohat[:4] == [0, 0, 0, 8] and ohat[4] == 0, f"the open hat on every 8th in the last bar: {ohat}"

@test
def links_open_the_filters(work):
    """v1.49 links: with the bass's kick link up, each kick pushes its first knob (the filter) up, and it closes again
    over about a beat; the chords' snare link the same on a snare. Off, nothing moves."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-bass-k1-m", "ockm-chord-k1-m")
    h.at(200, "ockm-bpm 120 ; ockm-bass-lfo-depth 0 ; ockm-bass-k1 0.3 ; ockm-chord-k1 0.4 ; ockm-bass-link 1 ; ockm-chord-link 0")
    h.at(400, "ockm-kick-hit 1 ; ockm-snare-hit 1")
    f = os.path.join(work, "t_links.pd"); h.finish(1600, f)
    out = run(work, f)
    b = [float(x) for x in printed(out, "ockm-bass-k1-m")]
    assert b and max(b) > 0.6 and abs(b[-1] - 0.3) < 0.02, f"the bass filter jumps on the kick, then back: {b[:3]} .. {b[-3:]}"
    c = [float(x) for x in printed(out, "ockm-chord-k1-m")]
    assert not c or max(c) <= 0.41, f"the chords' link is off: nothing moves: {c[:5]}"

@test
def slice_reorders_the_drum_steps(work):
    """v1.49 slice: reverse plays the bar backwards (a kick on step 1 lands on step 16); off, it's back where it was."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    def kick_steps(slice_):
        h = Harness(); h.show("ockm-step", "ockm-kick-hit")
        h.at(200, f"ockm-bpm 240 ; ockm-swing 50 ; ockm-drum-len 16 ; ockm-length 16 ; " + " ; ".join(f"ockm-pat-d{i} const 0" for i in range(1, 9)) +
             f" ; ockm-pat-d1 0 2 ; ockm-d1-sound 0 ; ockm-slice {slice_}")
        h.at(400, "ockm-play 1"); h.at(400 + 2 * 16 * 63, "ockm-play 0")
        f = os.path.join(work, f"t_slice{slice_}.pd"); h.finish(3000, f)
        steps, cur = [], None
        for line in run(work, f).splitlines():
            if line.startswith("ockm-step:"): cur = int(float(line.split(":")[1]))
            elif line.startswith("ockm-kick-hit:") and cur is not None: steps.append(cur % 16)
        return steps
    assert set(kick_steps(0)) == {0}, f"off: the kick on step 1: {kick_steps(0)}"
    rv = kick_steps(3)
    assert rv and set(rv) == {15}, f"reverse: the kick on step 16: {rv}"

@test
def build_rush_crash_and_key_on_screen(work):
    """v1.49 Perform: slot B (the 4 bar build) switches the build on, and off on the drop. The 4 bar rush (picked onto
    slot B) asks for the rush pattern and plays a crash on the drop. A recipe with a key change raises the root on its
    drop, and a breakdown brings it back."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    bars = ["send ockm-bar bang"] * 6
    go = ["send ockm-root float 9", "send ockm-play float 1", "send ockm-playing float 1", "test tap 616 36"]
    L = ui_preview.run(go + ["test tap 716 480"] + bars)
    b = [l for l in L if l.startswith("sent ockm-build ")]
    assert b[:1] == ["sent ockm-build float 1"] and b[-1:] == ["sent ockm-build float 0"], f"the build on, then off on the drop: {b}"
    L = ui_preview.run(go + ["test tap 766 458", "test tap 480 522", "test tap 716 480"] + bars)
    b = [l for l in L if l.startswith("sent ockm-build ")]
    assert b[:1] == ["sent ockm-build float 2"], f"the rush pattern: {b}"
    assert any(l.startswith("sent ockm-impact-go") for l in L), "a crash on the rush's drop"
    # the key change: the 4 bar rewind (slot A) set to +2 in the recipe editor, then played; then breakdown (slot C)
    L = ui_preview.run(["send ockm-root float 9", "test tap 919 36", "test tap 830 195", "test tap 90 272", "test tap 594 508"] + go +
                       ["test tap 560 480"] + bars + ["mark dropped", "test tap 860 480"] + bars)
    roots = [l.split()[-1] for l in L if l.startswith("sent ockm-root ")]
    assert "11" in roots, f"up 2 on the drop (A to B): {roots}"
    assert roots[-1] == "9", f"back to A at the breakdown: {roots}"

@test
def screens_have_no_collisions(work):
    """v1.49 every screen, drawn as the Pi draws it (Pd's fonts, wrapped where told): no text spilling out of its box or
    into another, no lines through words, no boxes overlapping or touching (tests/ui_review.py draws the faults)."""
    import ui_review
    f = ui_review.faults_on_every_screen()
    assert not f, f"{len(f)} layout faults (python3 tests/ui_review.py shows them): " + " | ".join(f"{a}: {b} {c} {d}" for a, b, c, d in f[:6])

@test
def mood_moves_the_hats(work):
    """v1.49 the mood: at chill a hat's off-beat 16ths and 8ths drop out; the kick's don't."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(dut="ockm-row zz"); h.show("test-out")
    h.add("#X obj 400 70 print ROWOUT;"); h.con(h.dut, len([o for o in h.objs if not o[1]]) - 1)
    h.at(100, "ockm-pat-zz 0 1 1 1 1 ; ockm-accent 0.3 ; ockm-zz-sound 4 ; ockm-mood 0")
    h.at(120, "test-in 0 , 1 , 2 , 3")
    h.at(200, "ockm-zz-sound 0")
    h.at(220, "test-in 0 , 1 , 2 , 3")
    f = os.path.join(work, "t_mood.pd"); h.finish(400, f)
    out = run(work, f)
    got = printed(out, "ROWOUT")
    assert len(got) == 1 + 4, f"a hat at chill plays just the 1; a kick plays all four: {got}"

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
    h.at(200, "ockm-bass-notes 3 ; ockm-bass-rhythm 12"); grab(250, "b")    # acid (v1.05: acid classic and acid 16ths merged)
    h.at(300, "ockm-root 0 ; ockm-scale 3 ; ockm-bass-notes 6 ; ockm-bass-rhythm 10"); grab(350, "c")   # round the kick
    f = os.path.join(work, "t_gen.pd"); h.finish(450, f)
    out = run(work, f)
    got = {v.split()[0]: [int(float(x)) for x in v.split()[1:]] for v in printed(out, "GEN")}
    def hits(label): return [n for n, o in zip(got[label + "-note"], got[label + "-on"]) if o]
    assert got["a-on"] == [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0], "offbeat rhythm wrong"
    assert hits("a") == [33] * 4, "root notes in A minor should all be 33"
    assert hits("b") == [33, 33, 45, 33, 36, 33, 43, 40, 33, 33, 45], f"acid riff wrong: {hits('b')}"   # v1.05: acid rhythm X.sxX.s.xsX.s.Sx
    assert hits("c") == [36, 36, 31, 32] * 3, f"dub pattern in C phrygian wrong: {hits('c')}"

@test
def bass_classic_rhythms(work):
    """The bass's own rhythm list: the offbeat donk lands on the "and"s, straight 8ths and quarters as named, and the
    sustained bass holds one note across the bar (the same note, sliding on, no new note until the next bar)."""
    h = Harness()
    def grab(ms, label):
        g = h.add(f"#X obj 10 300 r test-{label};"); t = h.add("#X obj 10 330 t b b b b;")
        for i, nm in enumerate(["note", "on", "acc", "slide"]):
            a = h.add(f"#X obj 10 360 array get ockm-pat-bass-{nm} 0 32;"); l = h.add(f"#X obj 10 390 list prepend {label}-{nm};")
            p = h.add("#X obj 10 420 list trim;"); pr = h.add("#X obj 10 450 print GEN;")
            h.con(t, a, 3 - i); h.con(a, l); h.con(l, p); h.con(p, pr)
        h.con(g, t)
        h.at(ms, f"test-{label} bang")
    h.at(100, "ockm-bass-sync 0 ; ockm-root 9 ; ockm-scale 0 ; ockm-bass-notes 2 ; ockm-bass-rhythm 0"); grab(150, "donk")
    h.at(200, "ockm-bass-rhythm 1"); grab(250, "eighths")
    h.at(300, "ockm-bass-rhythm 6"); grab(350, "quarters")
    h.at(400, "ockm-bass-rhythm 5"); grab(450, "held")
    f = os.path.join(work, "t_bassrhy.pd"); h.finish(550, f)
    out = run(work, f)
    got = {v.split()[0]: [int(float(x)) for x in v.split()[1:]] for v in printed(out, "GEN")}
    ons = lambda k: [i for i, o in enumerate(got[k + "-on"][:16]) if o]
    assert ons("donk") == [2, 6, 10, 14], f"offbeat donk: {ons('donk')}"
    assert ons("eighths") == list(range(0, 16, 2)), f"straight 8ths: {ons('eighths')}"
    assert ons("quarters") == [0, 4, 8, 12], f"quarters: {ons('quarters')}"
    assert ons("held") == list(range(16)), f"sustained: every step sounds: {ons('held')}"
    notes = got["held-note"]
    assert len(set(notes[:16])) == 1 and notes[16] != notes[15] or len(set(notes[:16])) == 1, f"one note held across the bar: {notes[:16]}"
    sl = got["held-slide"][:16]
    assert sl[:15] == [1] * 15 and sl[15] == 0, f"slides on through the bar, then lets the next bar start fresh: {sl}"

@test
def mutate_changes_the_rhythm_and_the_last_bar_leads_back(work):
    """Bass on quarter notes, 2 bars. The original: quarters, plus a pickup on the last 8th of bar 2 leading back to the start
    (bar 1 has no note there). Variations move a hit or two (most of them change the rhythm), and the same variation comes
    back the same."""
    h = Harness()
    def grab(ms, label):
        g = h.add(f"#X obj 10 300 r test-{label};"); a = h.add("#X obj 10 330 array get ockm-pat-bass-on 0 32;")
        l = h.add(f"#X obj 10 360 list prepend {label};"); pr = h.add("#X obj 10 390 list trim;"); pp = h.add("#X obj 10 420 print GEN;")
        h.con(g, a); h.con(a, l); h.con(l, pr); h.con(pr, pp); h.at(ms, f"test-{label} bang")
    h.at(100, "ockm-length 32 ; ockm-bass-len 32 ; ockm-bass-sync 0 ; ockm-bass-density 1 ; ockm-bass-seed 0 ; ockm-bass-notes 0 ; ockm-bass-rhythm 6")
    grab(200, "orig")
    for k, sd in enumerate((1, 2, 3, 4)):
        h.at(250 + k * 40, f"ockm-bass-seed {sd}"); grab(270 + k * 40, f"v{sd}")
    h.at(450, "ockm-bass-seed 0"); h.at(480, "ockm-bass-seed 3"); grab(520, "again")
    f = os.path.join(work, "t_mutrhy.pd"); h.finish(600, f)
    got = {v.split()[0]: [int(float(x)) for x in v.split()[1:]] for v in printed(run(work, f), "GEN")}
    o = got["orig"]
    ons = [i for i, x in enumerate(o) if x]
    assert ons == [0, 4, 8, 12, 16, 20, 24, 28, 30], f"quarters, plus the pickup on the last 8th of bar 2: {ons}"
    moved = [sd for sd in (1, 2, 3, 4) if got[f"v{sd}"] != o]
    assert len(moved) >= 3, f"most variations move a hit or two: only {moved} did"
    assert got["v3"] == got["again"], "the same variation comes back the same"

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
def chord_voicing_opens_and_widens(work):
    """Voicing: close as it is; open lifts the third an octave; wide drops the root and lifts the third and seventh."""
    h = Harness(dut="ockm-chordseq zz")
    h.add("#X obj 400 120 ockm-presets;")
    pr = h.add("#X obj 400 90 print CHORD;"); h.con(h.dut, pr)
    h.at(100, "ockm-pat-zz-on 0 1 ; ockm-pat-zz-deg 0 0 ; ockm-zz-smooth 0 ; ockm-zz-type 1")
    h.at(120, "test-in 0")
    h.at(140, "ockm-zz-voicing 1"); h.at(150, "test-in 0")
    h.at(170, "ockm-zz-voicing 2"); h.at(180, "test-in 0")
    f = os.path.join(work, "t_voicing.pd"); h.finish(250, f)
    got = [[float(x) for x in v.split()] for v in printed(run(work, f, with_main=False), "CHORD")]
    want = [[45, 48, 52, 55], [45, 60, 52, 55], [33, 60, 52, 67]]
    assert [g[:4] for g in got] == want, f"voicings wrong (A minor 7: close, open, wide): {got}"
    assert all(0.68 <= g[4] <= 0.82 for g in got), f"a plain hit plays at about 0.75, varied a little: {[g[4] for g in got]}"

@test
def lfo_moves_a_knob_in_time_and_lets_go(work):
    """An LFO on the lead's first knob swings it around your setting; at depth 0 it goes back to exactly your setting.
    Knobs it isn't moving pass straight through."""
    h = Harness(); h.show("ockm-lead-k1-m", "ockm-lead-k2-m")
    h.at(100, "ockm-lead-k1 0.5 ; ockm-lead-k2 0.3 ; ockm-lead-lfo-rate 2 ; ockm-lead-lfo-target 1 ; ockm-lead-lfo-depth 1 ; ockm-play 1")
    h.at(1600, "ockm-lead-lfo-depth 0")
    h.at(1800, "ockm-play 0")
    f = os.path.join(work, "t_lfo.pd"); h.finish(1900, f)
    out = run(work, f)
    k1 = [float(x) for x in printed(out, "ockm-lead-k1-m")]; k2 = [float(x) for x in printed(out, "ockm-lead-k2-m")]
    assert len(k1) > 30 and min(k1) < 0.15 and max(k1) > 0.85, f"the LFO should swing knob 1 widely around 0.5: {min(k1) if k1 else None}..{max(k1) if k1 else None} ({len(k1)} values)"
    assert abs(k1[-1] - 0.5) < 1e-6, f"at depth 0, knob 1 should be back on its setting: {k1[-3:]}"
    assert k2 and all(abs(x - 0.3) < 1e-6 for x in k2), f"knob 2 isn't on the LFO, so it should just pass through: {k2[:5]}"

@test
def chorus_widens_but_off_is_dry(work):
    """The chorus: off is exactly the dry sound; I adds swept delayed copies (the sound changes, at a similar level)."""
    def take(mode):
        h = Harness(dut="ockm-chorus zz")
        osc = h.add("#X obj 400 40 osc~ 220;"); h.con(osc, h.dut)
        h.record(os.path.join(work, f"ch{mode}.wav"), source="dut")
        h.at(20, f"ockm-zz-chorus {mode}")
        _, (x, sr) = play(work, h, f"t_ch{mode}", with_main=False, ms=900)
        return x[int(0.3 * sr):int(0.8 * sr)], sr
    dry, sr = take(0); wet, _ = take(1)
    n = min(len(dry), len(wet))
    ref = [math.sin(2 * math.pi * 220 * (i + int(0.3 * sr)) / sr) for i in range(n)]
    def rms(v): return math.sqrt(sum(a * a for a in v) / len(v))
    assert abs(rms(dry) - rms(ref)) < 0.02, f"chorus off should pass the sound straight through: {rms(dry):.3f}"
    diff = rms([dry[i] - wet[i] for i in range(n)])
    assert diff > 0.1 and 0.5 < rms(wet) / rms(dry) < 1.5, f"chorus I should change the sound at a similar level: diff {diff:.3f}, level {rms(wet):.3f} vs {rms(dry):.3f}"

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
    # v0.90: smooth keeps chords around D4 (VI: A C F, not F A C below it); the 11th leaves the root to the bass (C D G B)
    want = [[45, 48, 52, 0], [53, 57, 60, 0], [45, 48, 52, 55], [48, 52, 55, 0], [57, 60, 65, 0], [60, 62, 67, 71]]
    assert [g[:4] for g in got] == want, f"chords wrong (A minor i, VI, i7, C major i accented, smooth VI, A minor 11): {got}"
    vel = [g[4] for g in got]
    assert vel[3] >= 0.92 and all(0.68 <= v <= 0.82 for i, v in enumerate(vel) if i != 3), f"accents hit harder, every hit varies a little: {vel}"

@test
def chord_shapes_move_as_one_block(work):
    """v0.90 fixed shapes: an m9 shape on i then iv in A minor keeps its intervals (3 7 10 14 above the root), and with
    smooth on both sit between D3 and about D5. On the turnaround the minor shape turns major. The 9ths in the key drop a
    flat 9th (v in A minor: E, F would grind) for the root."""
    h = Harness(dut="ockm-chordseq zz")
    h.add("#X obj 400 120 ockm-presets;")
    pr = h.add("#X obj 400 90 print CHORD;"); h.con(h.dut, pr)
    h.at(100, "ockm-pat-zz-on 0 1 1 1 ; ockm-pat-zz-deg 0 0 3 4 ; ockm-zz-smooth 1 ; ockm-zz-type 8")
    h.at(120, "test-in 0"); h.at(130, "test-in 1")
    h.at(140, "ockm-zz-type 6"); h.at(150, "test-in 2")
    f = os.path.join(work, "t_shape.pd"); h.finish(220, f)
    got = [[int(float(x)) for x in v.split()[:4]] for v in printed(run(work, f, with_main=False), "CHORD")]
    assert len(got) == 3, got
    for g, root in zip(got[:2], (9, 2)):
        assert sorted((n - root) % 12 for n in g) == [2, 3, 7, 10], f"m9 shape (b3 5 b7 9 over the root): {got}"
        assert g == sorted(g) and g[1] - g[0] == 4 and g[2] - g[1] == 3 and g[3] - g[2] == 4, f"same intervals each time: {got}"
        assert 50 <= min(g) and max(g) <= 76, f"smooth keeps it out of the bass and not too high: {got}"
    assert 5 not in [n % 12 for n in got[2]], f"no flat 9th (F) on E in A minor: {got[2]}"

@test
def chord_progressions_fill_and_lengthen(work):
    h = Harness(); h.show("ockm-len", "ockm-chord-len")
    h.at(100, "ockm-resync bang ; ockm-chord-rhythm 0 ; ockm-chord-prog 4")       # garage: half-bar changes, 2 bars
    g = h.add("#X obj 10 300 r test-get;"); t = h.add("#X obj 10 330 t b b;")
    a1 = h.add("#X obj 10 360 array get ockm-pat-chord-deg 0 32;"); p1 = h.add("#X obj 10 390 print DEG;")
    a2 = h.add("#X obj 200 360 array get ockm-pat-chord-on 0 32;"); p2 = h.add("#X obj 200 390 print ON;")
    h.con(g, t); h.con(t, a1, 1); h.con(t, a2, 0); h.con(a1, p1); h.con(a2, p2)
    h.at(200, "test-get bang")
    f = os.path.join(work, "t_prog.pd"); h.finish(300, f)
    out = run(work, f)
    assert "32" in printed(out, "ockm-chord-len"), f"a 2-bar progression should make the chords 32 long: {printed(out, 'ockm-chord-len')}"   # (v1.49 the loop is 4 bars: the lead keeps 4)
    deg = [int(float(x)) for x in printed(out, "DEG")[0].split()]
    assert deg == [0] * 8 + [5] * 8 + [3] * 8 + [4] * 8, f"garage should change chord every half bar (i VI iv v): {deg}"
    on = [int(float(x)) for x in printed(out, "ON")[0].split()]
    assert on[0] == 2 and on[16] == 2 and sum(on) == 4, f"bar-pads rhythm: one accented chord per bar: {on}"

@test
def chord_rate_and_push(work):
    """v0.99. Vamp (i iv, a bar each) at rate 0 (half bar) is i for 8 steps then iv for 8; at rate 2 (two bars) the pattern
    grows to 64 steps, i for 32 then iv for 32. Push (rate 1, bar pads): every change lands two steps early (iv from step
    14, i again from step 30), and the hit that was on each 1 moves to two steps before it."""
    def take(cmds, n):
        h = Harness(); h.show("ockm-len")
        h.at(100, "ockm-resync bang ; ockm-chord-rhythm 0 ; ockm-chord-rate 1 ; ockm-chord-push 0 ; ockm-chord-prog 1")
        h.at(150, cmds)
        g = h.add("#X obj 10 300 r test-get;"); t = h.add("#X obj 10 330 t b b;")
        a1 = h.add(f"#X obj 10 360 array get ockm-pat-chord-deg 0 {n};"); p1 = h.add("#X obj 10 390 print DEG;")
        a2 = h.add(f"#X obj 200 360 array get ockm-pat-chord-on 0 {n};"); p2 = h.add("#X obj 200 390 print ON;")
        h.con(g, t); h.con(t, a1, 1); h.con(t, a2, 0); h.con(a1, p1); h.con(a2, p2)
        h.at(250, "test-get bang")
        f = os.path.join(work, f"t_rate{abs(hash(cmds)) % 1000}.pd"); h.finish(350, f)
        out = run(work, f)
        return ([int(float(x)) for x in printed(out, "DEG")[-1].split()], [int(float(x)) for x in printed(out, "ON")[-1].split()], printed(out, "ockm-len"))
    deg, on, ln = take("ockm-chord-rate 0", 16)
    assert deg == [0] * 8 + [3] * 8, f"half-bar vamp: {deg}"
    deg, on, ln = take("ockm-chord-rate 2", 64)
    assert deg == [0] * 32 + [3] * 32 and "64" in ln, f"two-bar vamp, 64 steps: {deg[:40]}... {ln}"
    deg, on, ln = take("ockm-chord-push 1", 32)
    assert deg == [0] * 14 + [3] * 16 + [0] * 2, f"push: each change two steps early: {deg}"
    assert on[14] == 2 and on[16] == 0 and on[30] == 2 and on[0] == 0, f"push: the hit on each 1 moves two steps early: {on}"

@test
def chord_sustained_follows_the_changes(work):
    """v1.01 sustained (chord rhythm 11): a hit only where the chord changes. Dub techno (i . . VII, 4 bars): hits on steps
    0 and 48 only; with push, on 46 (two steps early) and 62 (the i coming round)."""
    def take(cmds):
        h = Harness()
        h.at(100, "ockm-resync bang ; ockm-chord-rate 1 ; ockm-chord-push 0 ; ockm-chord-rhythm 11 ; ockm-chord-prog 2")
        h.at(150, cmds)
        g = h.add("#X obj 10 300 r test-get;"); a2 = h.add("#X obj 200 360 array get ockm-pat-chord-on 0 64;"); p2 = h.add("#X obj 200 390 print ON;")
        h.con(g, a2); h.con(a2, p2)
        h.at(250, "test-get bang")
        f = os.path.join(work, f"t_sus{abs(hash(cmds)) % 1000}.pd"); h.finish(350, f)
        on = [int(float(x)) for x in printed(run(work, f), "ON")[-1].split()]
        return [i for i, v in enumerate(on) if v > 0]
    assert take("ockm-chord-gen bang") == [0, 48], "sustained: hits where the chord changes"
    assert take("ockm-chord-push 1") == [46, 62], "sustained with push: two steps early"

@test
def chord_vary_breathes_and_moves(work):
    """v1.01 vary, after the chords are written. move, on bar pads over 4 bars (hits on 0, 16, 32, 48): bar 2 drops its
    last hit after the downbeat (none, so nothing), bar 4 gains one on step 62 (the latest empty 8th). breathe on offbeat
    stabs: a push on step 62. breathe on pads: the last beat rests (nothing to drop there)."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    pads = " ".join(("2" if i % 16 == 0 else "0") for i in range(64))
    offb = " ".join(("1" if i % 4 == 2 else "0") for i in range(64))
    def edits(on, vary):
        L = ui_preview.run(["send ockm-chord-len float 64", "send ockm-chord-mode float 0", f"array ockm-pat-chord-on {on}",
                            "array ockm-pat-chord-deg " + " ".join("0" for _ in range(64)), f"send ockm-chord-vary float {vary}",
                            "mark go", "send ockm-chord-changed bang"])
        return [tuple(int(float(x)) for x in l.split()[3:5]) for l in L[L.index("mark go"):] if l.startswith("sent ockm-chord-edit ")]
    assert edits(pads, 2) == [(62, 1)], f"move on pads: {edits(pads, 2)}"
    assert edits(offb, 1) == [], f"breathe on offbeat stabs: step 62 is already a hit: {edits(offb, 1)}"
    st = " ".join(("1" if i % 8 == 0 else "0") for i in range(64))   # 8ths on the beat: 2 hits a bar (a pad-like rhythm)
    assert edits(st, 0) == [], "still: nothing changes"
    three = " ".join(("1" if i % 16 in (0, 4, 8) else "0") for i in range(64))
    assert edits(three, 1) == [(62, 1)], f"breathe on a stab rhythm: a push on the last 8th: {edits(three, 1)}"
    m = edits(three, 2)
    assert (24, 0) in m and (62, 1) in m, f"move: bar 2 drops its last hit, bar 4 adds one: {m}"

@test
def bass_riffs_slide_and_octave(work):
    """v1.02 the bass's own riffs. Riff 2 (fifth: 0 4) on 8ths over one chord in A minor plays A and E in turn. Octave 1 lifts
    it an octave. Slide 1 makes notes slide into the next (8ths have no slides of their own)."""
    def take(cmds):
        h = Harness()
        h.at(100, "ockm-resync bang ; ockm-root 9 ; ockm-scale 0 ; ockm-chord-prog 0 ; ockm-bass-sync 1 ; ockm-bass-rhythm 1 ; ockm-bass-seed 0 ; ockm-bass-octave 0 ; ockm-bass-slideamt 0")
        h.at(150, cmds)
        g = h.add("#X obj 10 300 r test-get;"); t = h.add("#X obj 10 330 t b b;")
        a1 = h.add("#X obj 10 360 array get ockm-pat-bass-note 0 16;"); p1 = h.add("#X obj 10 390 print NOTE;")
        a2 = h.add("#X obj 200 360 array get ockm-pat-bass-slide 0 16;"); p2 = h.add("#X obj 200 390 print SLIDE;")
        h.con(g, t); h.con(t, a1, 1); h.con(t, a2, 0); h.con(a1, p1); h.con(a2, p2)
        h.at(300, "test-get bang")
        f = os.path.join(work, f"t_riff{abs(hash(cmds)) % 1000}.pd"); h.finish(400, f)
        out = run(work, f)
        return [int(float(x)) for x in printed(out, "NOTE")[-1].split()], [int(float(x)) for x in printed(out, "SLIDE")[-1].split()]
    n, sl = take("ockm-bass-riff 2")
    hit = [n[i] for i in range(0, 16, 2)]
    assert sorted({x % 12 for x in hit}) == [4, 9], f"fifth: A and E: {hit}"
    n2, _ = take("ockm-bass-riff 2 ; ockm-bass-octave 1")
    assert [b - a for a, b in zip(n, n2)][0] == 12, f"octave up: {n[:4]} -> {n2[:4]}"
    _, sl2 = take("ockm-bass-riff 2 ; ockm-bass-slideamt 1")
    assert sum(sl) == 0 and sum(sl2) >= 4, f"slide: none on plain 8ths, most notes slide at 1: {sl} {sl2}"

@test
def bass_rhythm_siblings_on_the_last_bar(work):
    """v1.05: a one-bar rhythm carries two siblings, other last bars of the phrase. Offbeat over 2 bars: the original plays
    the plain bar twice; variation 1 (seed 1) ends with sibling A (a pickup 16th on step 31), variation 2 with sibling B
    (no pickup)."""
    def take(seed):
        h = Harness()
        h.at(100, f"ockm-resync bang ; ockm-chord-prog 0 ; ockm-bass-len 32 ; ockm-bass-riff 0 ; ockm-bass-seed {seed} ; ockm-bass-rhythm 0")
        g = h.add("#X obj 10 300 r test-get;"); a = h.add("#X obj 10 360 array get ockm-pat-bass-on 0 32;"); pr = h.add("#X obj 10 390 print ON;")
        h.con(g, a); h.con(a, pr); h.at(250, "test-get bang")
        f = os.path.join(work, f"t_sib{seed}.pd"); h.finish(350, f)
        on = [int(float(x)) for x in printed(run(work, f), "ON")[-1].split()]
        return [i for i, v in enumerate(on) if v > 0]
    base = [2, 6, 10, 14, 18, 22, 26, 30]
    assert take(0) == base, f"original: {take(0)}"
    a = take(1)
    assert a[:4] == base[:4] and 31 in a, f"variation 1: sibling A on the last bar (a pickup on 31): {a}"
    b = take(2)   # (a variation also moves a hit or two of its own, v0.86, so only the last 16th is checked here)
    assert 31 not in b and [x for x in b if x >= 16] != [x for x in a if x >= 16], f"variation 2: sibling B, no pickup: {b}"

@test
def lead_answers_the_bass_and_rests(work):
    """v1.06. Tune 19, answer the bass: the lead plays the bass's riff (fifth: A and E) only in the gaps of the bass (8ths on
    the even steps, so the lead lands on odd steps). Rests at 1 skip some of the lead's notes, differently from bar to bar."""
    def take(cmds):
        h = Harness()
        h.at(100, "ockm-resync bang ; ockm-root 9 ; ockm-scale 0 ; ockm-chord-prog 0 ; ockm-bass-len 32 ; ockm-lead-len 32 ; ockm-bass-riff 2 ; ockm-bass-rhythm 1 ; "
                  "ockm-bass-seed 0 ; ockm-lead-seed 0 ; ockm-lead-outside 0 ; ockm-lead-rests 0 ; ockm-lead-rhythm 1 ; ockm-lead-notes 19")
        h.at(150, cmds)
        g = h.add("#X obj 10 300 r test-get;"); t = h.add("#X obj 10 330 t b b b;")
        outs = []
        for i, nm in enumerate(["bass-on", "lead-on", "lead-note"]):
            a = h.add(f"#X obj {10 + i * 190} 360 array get ockm-pat-{nm} 0 32;"); l = h.add(f"#X obj {10 + i * 190} 390 list prepend {nm};")
            tr = h.add(f"#X obj {10 + i * 190} 420 list trim;"); pr = h.add(f"#X obj {10 + i * 190} 450 print GOT;")
            h.con(t, a, 2 - i); h.con(a, l); h.con(l, tr); h.con(tr, pr)
        h.con(g, t); h.at(300, "test-get bang")
        f = os.path.join(work, f"t_ans{abs(hash(cmds)) % 1000}.pd"); h.finish(400, f)
        got = {v.split()[0]: [int(float(x)) for x in v.split()[1:]] for v in printed(run(work, f), "GOT")}
        return got
    g = take("ockm-lead-gen bang")
    lead = [i for i, v in enumerate(g["lead-on"]) if v > 0]
    assert lead and all(g["bass-on"][i] == 0 for i in lead), f"the lead only in the bass's gaps: lead {lead}, bass {[i for i, v in enumerate(g['bass-on']) if v]}"
    assert {g["lead-note"][i] % 12 for i in lead} <= {9, 4}, f"the bass's riff (A, E): {[g['lead-note'][i] for i in lead]}"
    r = take("ockm-lead-rests 1")
    lead_r = [i for i, v in enumerate(r["lead-on"]) if v > 0]
    assert len(lead_r) < len(lead), f"rests: fewer notes: {len(lead_r)} vs {len(lead)}"

@test
def chord_engines_sound(work):
    for eng, name, k3 in [(0, "poly", 0.0), (1, "organ", 0.2), (0, "poly-pad", 0.6)]:   # v0.98: poly's k3 is attack
        h = Harness(dut="ockm-chord zz")
        h.record(os.path.join(work, f"c_{name}.wav"), source="dut")
        h.at(20, f"ockm-zz-engine {eng} ; ockm-zz-k1-m 0.5 ; ockm-zz-k2-m 0.5 ; ockm-zz-k3-m {k3} ; ockm-zz-k4-m 0.5")
        h.at(60, "test-in 45 48 52 0 1")
        _, (s, sr) = play(work, h, f"t_chord_{name}", with_main=False, ms=900)
        x = s[int(0.08 * sr):int(0.4 * sr)]
        assert 0.02 < peak(x) < 1.0, f"{name} chord level {peak(x):.2f}"

@test
def bass_engines_play_in_tune(work):
    levels = {}
    for eng, name in [(0, "acid"), (1, "sub"), (2, "fm"), (3, "wide"), (5, "analogue"), (6, "donk"), (8, "swarm"), (9, "pulse")]:   # 4 (pluck) retired in v0.98
        h = Harness(dut="ockm-mono zz")
        h.record(os.path.join(work, f"b_{name}.wav"), source="dut")
        h.at(20, f"ockm-zz-engine {eng} ; ockm-zz-k1-m 0.5 ; ockm-zz-k2-m 0.3 ; ockm-zz-k3-m 0 ; ockm-zz-k4-m 0.9 ; ockm-zz-drive 0")
        h.at(50, "test-in 33 0 0 1")
        _, (s, sr) = play(work, h, f"t_bass_{name}", with_main=False, ms=650)
        x = s[int(0.15 * sr):int(0.5 * sr)]
        assert peak(x) > 0.02, f"{name} engine is silent"
        f0 = cycles_per_second(x, sr)
        assert 45 < f0 < 68, f"{name} engine plays {f0:.0f}Hz for A1, expected about 55Hz"
        levels[name] = math.sqrt(sum(v * v for v in x) / len(x))
    print("      bass levels (rms): " + ", ".join(f"{k} {v:.2f}" for k, v in levels.items()))
    for nm in ("swarm", "pulse"):   # v1.39: the new ones sit with the default (analogue)
        assert 0.4 < levels[nm] / levels["analogue"] < 2.5, f"{nm} is far from analogue's level: {levels}"

@test
def lead_engines_play_in_tune_and_level(work):
    """Every lead engine sounds, plays A2 at about 110 Hz, and sits at a similar level to the others."""
    levels = {}
    for eng, name in [(2, "dx"), (3, "sync"), (4, "analogue"), (5, "supersaw"), (7, "pulse")]:   # 0 acid and 1 juno retired in v0.98
        h = Harness(dut="ockm-lead zz")
        h.record(os.path.join(work, f"l_{name}.wav"), source="dut")
        k1, k3 = (0, 0) if name == "sync" else (0.15, 0.3) if name == "supersaw" else (0.5, 0) if name == "dx" else (0.5, 0.3)   # sync: zero sync, so the pitch counter sees the fundamental
        # dx: no detune (its second voice beats against the first, which a zero-crossing counter can't read: v1.14 widened it)
        h.at(20, f"ockm-zz-engine {eng} ; ockm-zz-k1-m {k1} ; ockm-zz-k2-m 0.1 ; ockm-zz-k3-m {k3} ; ockm-zz-k4-m 0.9 ; ockm-zz-drive 0")
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
    for eng, name, k3 in [(0, "poly", 0.0), (1, "organ", 0.3), (3, "piano", 0.3), (4, "rhodes", 0.3), (0, "poly-pad", 0.7)]:
        h = Harness(dut="ockm-chord zz")
        h.record(os.path.join(work, f"c_{name}.wav"), source="dut")
        h.at(20, f"ockm-zz-engine {eng} ; ockm-zz-k1-m 0.5 ; ockm-zz-k2-m 0.3 ; ockm-zz-k3-m {k3} ; ockm-zz-k4-m 0.6")
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
def midi_clock_goes_out_with_the_engine(work):
    """v1.49 the clock leaves a quarter step late, as the engine plays: at 124 bpm (a step 121 ms) start goes out about
    30 ms after play, so gear following it lands with the box rather than ahead of it."""
    h = Harness(); h.show("ockm-clock-sent", "ockm-mark")
    h.at(100, "ockm-bpm 124 ; ockm-play 1"); h.at(115, "ockm-mark 1"); h.at(145, "ockm-mark 2"); h.at(400, "ockm-play 0")
    f = os.path.join(work, "t_lag.pd"); h.finish(600, f)
    out = [l for l in run(work, f).splitlines() if l.startswith("ockm-clock-sent:") or l.startswith("ockm-mark:")]
    i250 = out.index("ockm-clock-sent: 250")
    assert out.index("ockm-mark: 1") < i250 < out.index("ockm-mark: 2"), f"start between 15 and 45 ms after play: {out[:5]}"

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


@test
def master_limiter_holds_a_pushed_mix(work):
    """v1.49 the master's look-ahead limiter: everything pushed to the top still peaks under 0.81 (its ceiling is 0.79,
    the soft limiter after it only a safety), and the delay's feedback can't run away (capped at 0.85)."""
    h = Harness(); h.record(os.path.join(work, "loud.wav"))
    up = " ; ".join(f"ockm-d{i}-level 1.5" for i in range(1, 9))
    h.at(100, f"{up} ; ockm-bass-level 1.5 ; ockm-lead-level 1.5 ; ockm-chord-level 1.5 ; ockm-drum-punch 1 ; ockm-delay-fb 2 ; ockm-delay-mix 1 ; "
              "ockm-bass-gen bang ; ockm-chord-gen bang ; ockm-lead-gen bang ; ockm-play 1")
    h.at(8000, "ockm-play 0")
    _, (s, sr) = play(work, h, "t_loud", ms=12000)
    assert peak(s) < 0.81, f"pushed mix peak {peak(s):.3f}"
    tail = s[int(10.5 * sr):]
    assert peak(tail) < 0.2, f"the echoes die away after it stops: {peak(tail):.3f}"

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
    tap(150, 301, 36)                    # drums tab (the kick slot)
    tap(170, 160, 212); tap(180, 160, 212)   # step 3: on, then accent
    tap(190, 608, 36)                    # perform tab
    tap(200, 301, 36)                    # drums tab (back to the kick slot)
    tap(210, 668, 88)                    # drum length: 2 bars (navigation strip)
    h.at(220, "ockm-ui-test drag 600 212 200 212")   # swipe left: steps 17-32
    tap(230, 45, 212)                    # step 17
    h.at(240, "ockm-ui-test drag 200 212 600 212")   # swipe right: back to 1-16
    tap(245, 194, 88)                    # forward arrow (steps 17-32)
    tap(248, 38, 88)                     # back arrow (steps 1-16)
    tap(260, 363, 36)                    # bass tab (bass is on auto)
    tap(270, 45, 158)                    # bass step 1: made for you, but any step can be edited (it becomes yours)
    tap(280, 600, 236)                   # note picker: third note of the scale
    tap(290, 608, 36)                    # perform tab
    tap(310, 760, 160)                   # perform: the master bus on the pad (v1.24: the pad is where the filter strip was)
    tap(320, 239, 36)                    # song tab
    tap(335, 228, 345)                   # harmony: next progression (v0.99: the stepper is narrower, rate and push beside it)
    tap(338, 487, 36)                    # chord tab
    tap(340, 298, 421)                   # colour: 9ths
    tap(345, 608, 36); tap(346, 74, 186)   # perform tab, mute the kick tile
    tap(347, 301, 36); tap(348, 818, 134)  # drums tab, all drums (v1.45: pads is right of it)
    tap(349, 192 + 47 * 1 + 20, 165)     # all drums: snare lane, step 2
    tap(350, 719, 36)                    # mixer tab (v1.38: 407 is the samples tab)
    tap(355, 623, 361)                   # bass fader, halfway (below the EQ button)
    tap(360, 123, 505)                   # mute on strip 2
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
    assert printed(out, "ockm-chord-prog"), "song: the progression arrow should pick the next progression"
    assert any(e.startswith("d2 1 ") for e in edits), f"tapping the snare lane in all drums should edit d2 step 2: {edits}"
    assert "1" in printed(out, "ockm-bass-mode"), "editing the bass should make it yours"
    assert "1" in printed(out, "ockm-d1-mute"), "perform: the kick tile should mute d1"
    assert "1" in printed(out, "ockm-d2-mute"), "mixer: M on strip 2 should mute d2"
    bl = [float(x) for x in printed(out, "ockm-bass-level")]
    assert any(0.19 < x < 0.24 for x in bl), f"mixer: bass fader halfway is -13 dB (faders are in dB, unity three quarters up): {bl}"
    assert "6" in printed(out, "ockm-chord-type"), f"chord tab: colour 9ths should pick the ninth chord type (6): {printed(out, 'ockm-chord-type')}"
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
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    want = len({name for name, _ in ui_preview.SHOTS})   # one picture per screen in the list (v1.49: was a fixed 46)
    got = len(os.listdir(os.path.join(work, "preview")))
    assert got == want, f"expected {want} screen pictures, got {got}"

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
    h.at(100, f"ockm-resync bang ; ockm-pat-d1 0 {kick} ; ockm-bass-sync 0 ; ockm-bass-notes 3 ; ockm-bass-rhythm 13 ; ockm-length 16")
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
def touchscreen_song_parts_in_and_out(work):
    """Song screen: tapping a part's tile takes it out of the pattern and back (drums, bass, chords, lead); the part tab's
    on/off switch is the same setting. The phrase (8 bars) sets the drum fill and, switched on, the turnaround to the same length.
    Perform B can't bring an out part back."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-drums-on", "ockm-bass-on", "ockm-chord-on", "ockm-lead-on", "ockm-turn-every", "ockm-fill-every", "ockm-bass-mute")
    tap = lambda ms, x, y: h.at(ms, f"ockm-ui-test tap {x} {y}")
    tap(150, 239, 36)                    # song
    tap(200, 129, 250)                   # drums out
    tap(250, 363, 250)                   # bass out
    tap(300, 597, 250)                   # chords out
    tap(350, 831, 250)                   # lead out
    tap(400, 129, 250)                   # drums back in
    tap(440, 586, 402)                   # phrase: 8 bars (the drum fill comes on with it)
    tap(450, 810, 406)                   # and the turnaround at the end of each phrase (v1.03: fill, turnaround, half-time)
    tap(500, 363, 36)                    # bass tab
    tap(550, 916, 283)                   # on/off switch: back on
    tap(600, 616, 36)                    # perform B
    tap(650, 360, 190)                   # the lead's tile: it's out, so nothing changes
    f = os.path.join(work, "t_song.pd"); h.finish(800, f)
    out = run(work, f)
    v = lambda n: [int(float(x)) for x in printed(out, n)]
    assert v("ockm-drums-on")[-2:] == [0, 1], f"drums out, then back in: {v('ockm-drums-on')}"
    assert v("ockm-bass-on")[-2:] == [0, 1], f"bass out on the song screen, back on from its tab: {v('ockm-bass-on')}"
    assert v("ockm-chord-on")[-1:] == [0] and v("ockm-lead-on")[-1:] == [0], "chords and lead out"
    assert v("ockm-turn-every")[-1:] == [8], f"turnaround every 8: {v('ockm-turn-every')}"
    assert v("ockm-fill-every")[-1:] == [8], f"the drum fill every 8, the same phrase: {v('ockm-fill-every')}"

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
    h.at(300, "ockm-ui-test press 772 106")       # drop, held (perform)
    h.at(700, "ockm-ui-test release 772 106")     # let go part way through a bar (a bar is 2 s at 120)
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
    h.at(150, "ockm-ui-test tap 616 36")       # live tab
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
    """Out of the box, slot B is the 4 bar build (v1.49; it was the lift) and slot C breakdown (stopped, so each plays while
    held). Hold the build: the build pattern is switched on, the high-pass comes in (the filter goes up) and the reverb
    rises; let go and it all comes back. Breakdown mutes the drums and brings in the low-pass (the filter goes down). The
    bass keeps playing throughout."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-verb-mix", "ockm-d2-mute", "ockm-d1-mute", "ockm-bass-mute", "ockm-filter-glide", "ockm-build")
    h.at(100, "ockm-ui-test tap 616 36")       # perform
    h.at(200, "ockm-ui-test press 700 500")    # lift, held
    h.at(300, "ockm-ui-test release 700 500")
    h.at(400, "ockm-ui-test press 850 500")    # breakdown, held
    h.at(500, "ockm-ui-test release 850 500")
    f = os.path.join(work, "t_macro.pd"); h.finish(600, f)
    out = run(work, f)
    vm = [float(x) for x in printed(out, "ockm-verb-mix")]
    assert vm and max(vm) > vm[-1] and abs(vm[-1] - 0.3) < 0.01, f"reverb eases up, then back to where it was: {vm}"
    gl = [float(x.split()[0]) for x in printed(out, "ockm-filter-glide")]
    assert gl and gl[0] > 0.2, f"lift: the high-pass first (filter up): {gl}"
    assert any(x < -0.5 for x in gl), f"breakdown: the low-pass (filter down): {gl}"
    assert printed(out, "ockm-build")[:2] == ["1", "0"], f"the build switches on, then off: {printed(out, 'ockm-build')}"
    assert printed(out, "ockm-d2-mute") == ["1", "0"], f"breakdown: the snare mutes and comes back: {printed(out, 'ockm-d2-mute')}"
    assert printed(out, "ockm-d1-mute") == ["1", "0"] and not printed(out, "ockm-bass-mute"), "the kick goes too, the bass keeps playing"

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
    h.at(250, "ockm-ui-test tap 260 328")      # recipe 5: sink (v1.49: the 4 bar rewind is first; nine recipes, shorter rows)
    h.at(300, "ockm-ui-test tap 532 552")      # on slot A
    h.at(350, "ockm-ui-test tap 616 36")       # Perform B
    h.at(400, "ockm-ui-test press 550 480")    # hold slot A
    h.at(2600, "ockm-ui-test release 550 480")
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
    assert '"slots"' in saved and re.search(r'"slots"\]\s*=\s*\{\s*5', saved), f"slot A should be saved as recipe 5: {saved[:400]}"

@test
def six_macro_slots_on_perform(work):
    """v1.49 Perform B has six macro slots, two rows of three (A-F): 8 bar lift, rush and dub out join the rewind, build
    and breakdown. Slot E plays the rush. Settings saved with three slots get D, E and F filled once."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    L = ui_preview.run(["test tap 616 36", "paint a"])
    a = L[L.index("begin a"):L.index("end a")]
    for nm in ("4 bar rewind", "4 bar build", "breakdown", "8 bar lift", "4 bar rush", "dub out"):
        assert any(nm in l for l in a), f"{nm} on a slot"
    assert any(l.startswith("text") and l.split()[-1] == "F" for l in a), "the slots are lettered to F"
    L = ui_preview.run(["send ockm-playing float 1", "test tap 616 36", "test tap 716 548"] + ["send ockm-bar bang"] * 2)
    assert "sent ockm-build float 2" in L, "slot E: the rush"
    # settings from before: three slots. D, E and F fill from the recipes not on a slot
    mine = os.path.join(work, "my-settings.lua")
    with open(mine, "w") as f: f.write('return { ["slots"] = { 5, 3, 4 } }')
    try:
        h = Harness(); h.show("ockm-build", "ockm-filter-glide")
        h.at(100, "ockm-ui-test tap 616 36")       # Perform B
        h.at(200, "ockm-ui-test press 716 548")    # slot E
        h.at(400, "ockm-ui-test release 716 548")
        h.at(500, "ockm-ui-test press 566 480")    # slot A: sink, as it was
        h.at(700, "ockm-ui-test release 566 480")
        fp = os.path.join(work, "t_six.pd"); h.finish(900, fp)
        out = run(work, fp)
    finally:
        if os.path.exists(mine): os.remove(mine)
    assert printed(out, "ockm-build")[:1] == ["2"], f"slot E filled with the rush: {printed(out, 'ockm-build')}"
    gl = printed(out, "ockm-filter-glide")
    assert any(g.split()[0] == "-0.85" for g in gl), f"slot A still sink: {gl}"

@test
def drum_lab_renders_claps_and_snares(work):
    """The drum lab (its own patch): render a clap and a snare into samples/clap and samples/snare. Both files are
    real hits: loud enough, not clipped, and they die away. The hat renders a matching closed and open pair.
    Randomise moves the settings within their ranges."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    import wave, struct
    h = Harness(); h.show("lab-status")
    h.at(300, "lab-clap-render bang")
    h.at(3200, "lab-snare-render bang")
    h.at(5600, "lab-hat-render bang")
    h.at(7600, "lab-kick-render bang")
    h.at(10000, "lab-tom-render bang")
    h.at(12200, "lab-conga-render bang")
    h.at(13200, "lab-rim-render bang")
    h.at(13500, "lab-shaker-render bang")
    h.at(14000, "lab-clap-rand-wild bang ; lab-test dump")
    f = os.path.join(work, "t_lab.pd"); h.finish(14200, f)
    out = run(work, f, main="OCKM_DRUM_LAB.pd")
    errs = [l for l in out.splitlines() if "error" in l.lower() and "audio" not in l.lower()]
    assert not errs, f"the lab should load cleanly: {errs[:4]}"
    def read(folder, name_out=None):
        d = os.path.join(work, "samples", folder)
        names = [n for n in os.listdir(d) if n.startswith("lab-") and n.endswith(".wav")]
        if name_out is not None and names: name_out.append(names[0])
        assert names, f"no render in samples/{folder}: {printed(out, 'lab-status')}"
        w = wave.open(os.path.join(d, names[0]))
        assert w.getnchannels() == 1 and w.getsampwidth() == 3, "renders should be 24-bit mono"
        raw = w.readframes(w.getnframes()); sr = w.getframerate()
        vals = [int.from_bytes(raw[i:i + 3], "little", signed=True) / 8388608 for i in range(0, len(raw), 3)]
        return vals, sr
    for folder in ("clap", "snare"):
        v, sr = read(folder)
        peak = max(abs(x) for x in v)
        head = v[: int(sr * 0.08)]; tail = v[-int(sr * 0.05):]
        rms = (sum(x * x for x in head) / len(head)) ** 0.5
        assert 0.05 < rms and peak < 1.0, f"{folder}: the hit should be loud but not clipped (rms {rms:.3f}, peak {peak:.3f})"
        assert max(abs(x) for x in tail) < 0.2 * peak, f"{folder}: the render should catch the whole hit as it dies away"
    # the hat: one render makes a matching pair, closed (short) in samples/hat and open (long) in samples/open-hat
    nc, no = [], []
    (c, sr), (o, _) = read("hat", nc), read("open-hat", no)
    assert nc[0].replace("-closed", "") == no[0].replace("-open", ""), f"the hat pair should share a name: {nc} {no}"
    assert len(o) > 3 * len(c), f"the open hat should be much longer than the closed one: {len(c) / sr:.2f}s vs {len(o) / sr:.2f}s"
    assert max(abs(x) for x in c) > 0.2 and max(abs(x) for x in o) > 0.2, "both hats should be at a decent level"
    # the rest of the kit: a kick, a tom set (low, mid, high), and congas (low, high), a rim and a shaker in perc
    def lab_files(folder): return sorted(n for n in os.listdir(os.path.join(work, "samples", folder)) if n.startswith("lab-"))
    assert len(lab_files("kick")) == 1, f"one kick: {lab_files('kick')}"
    toms = lab_files("tom")
    assert [t.rsplit("-", 1)[1] for t in toms] == ["high.wav", "low.wav", "mid.wav"] and len({t.rsplit("-", 1)[0] for t in toms}) == 1, f"a matching tom set: {toms}"
    perc = lab_files("perc")
    assert sum(n.startswith("lab-conga") for n in perc) == 2 and any(n.startswith("lab-rim") for n in perc) and any(n.startswith("lab-shaker") for n in perc), f"congas, rim and shaker in perc: {perc}"
    for folder in ("kick", "tom", "perc"):
        for n in lab_files(folder):
            w = wave.open(os.path.join(work, "samples", folder, n)); raw = w.readframes(w.getnframes())
            pk = max(abs(int.from_bytes(raw[i:i + 3], "little", signed=True)) for i in range(0, len(raw), 3)) / 8388608
            assert 0.2 < pk < 1.0, f"{n}: should be a decent level, not clipped ({pk:.2f})"
    dump = [l for l in out.splitlines() if "ockm-lab: clap" in l]
    assert len(dump) == 13, f"every clap setting should be listed: {dump[:3]}"

@test
def drum_lab_character_and_morph(work):
    """The lab's macro sliders: the kick's punch moves its recipe the right ways (more drop, quicker drop, more click,
    shorter); pulling it the other way does the opposite; morph moves several settings at once but never the level;
    keep makes the result home, and morph back at zero then changes nothing."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness()
    mk = h.add("#X obj 10 300 r test-mark;"); pm = h.add("#X obj 10 325 print MARK;"); h.con(mk, pm)
    steps = [("home", ""), ("punch", "lab-test char kick 1"), ("soft", "lab-test char kick -1"), ("morph", "lab-test char kick 0 ; lab-test morph kick 0.7"),
             ("kept", "lab-test keep kick"), ("again", "lab-test morph kick 0")]
    t = 300
    for name, msg in steps:
        h.at(t, (msg + " ; " if msg else "") + f"test-mark {len(name)} ; lab-test dump"); t += 100
    f = os.path.join(work, "t_labmacro.pd"); h.finish(t + 100, f)
    out = run(work, f, main="OCKM_DRUM_LAB.pd")
    snaps, cur = [], None
    for line in out.splitlines():
        if line.startswith("MARK:"): cur = {}; snaps.append(cur)
        elif "ockm-lab: kick" in line and cur is not None:
            _, _, name, val = line.split()[-4:]; cur[name] = float(val)
    assert len(snaps) == len(steps), f"expected {len(steps)} snapshots, got {len(snaps)}"
    home, punch, soft, morph, kept, again = snaps
    assert punch["sweep"] > home["sweep"] and punch["sweeptime"] < home["sweeptime"] and punch["noise"] > home["noise"] and punch["decay"] < home["decay"], f"punch should move its recipe: {home} -> {punch}"
    assert soft["sweep"] < home["sweep"] and soft["decay"] > home["decay"], f"pulling punch the other way should do the opposite: {soft}"
    assert punch["pitch"] == home["pitch"], "punch shouldn't touch settings outside its recipe"
    moved = [k for k in home if abs(morph[k] - home[k]) > 1e-6]
    assert len(moved) >= 6 and "level" not in moved, f"morph should move several settings, never the level: {moved}"
    assert kept == morph and again == morph, "keep should make the morphed sound home, so morph at zero leaves it alone"

@test
def touchscreen_filter_springs_and_throw(work):
    """v1.24: on perform the pad plays the picked bus's effect (here the master's, set to its filter): lift and it springs
    back out; latched it stays in. The repeat pad (v1.17, where throw was) sends 1 then 0."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-bfx-master-on", "ockm-repeat", "ockm-bfx-master-x")
    h.at(80, "ockm-bfx-master-type 0")
    h.at(100, "ockm-ui-test tap 760 160")                   # the master bus on the pad
    h.at(150, "ockm-ui-test drag 716 300 636 300")          # sweep, let go: out again
    h.at(500, "ockm-ui-test tap 848 160")                   # latch
    h.at(550, "ockm-ui-test drag 716 300 636 300")          # sweep again, let go: it stays in
    h.at(900, "ockm-ui-test tap 886 106")                   # repeat
    f = os.path.join(work, "t_spring_ui.pd"); h.finish(1000, f)
    out = run(work, f)
    on = [int(float(v.split()[-1])) for v in printed(out, "ockm-bfx-master-on")]
    assert on == [1, 0, 1], f"in, out when lifted, then in and staying in (latched): {on}"
    xs = [float(v.split()[-1]) for v in printed(out, "ockm-bfx-master-x")]
    assert 0.5 in xs[:xs.index(0.5) + 1] and xs[-1] != 0.5, f"unlatched it springs back to the centre; latched it stays put: {xs}"
    assert [int(float(v.split()[-1])) for v in printed(out, "ockm-repeat")] == [1, 0], printed(out, "ockm-repeat")

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
    """Bass, lead and chords sit together: each part's first sound is within a few dB of the bass's (chords a little
    under, as in a mix). v1.49: measured as the ear weighs it (measure_sounds), every other sound is levelled to its
    part's first by its trim (sounds_sit_at_one_level)."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    lv = measure_sounds(work, first_only=True)
    ref = lv["bass"][0]
    for part in ("lead", "chord"):
        db = 20 * math.log10(max(lv[part][0], 1e-9) / ref)
        assert -6 < db < 2, f"{part} is out of balance with the bass: {db:+.1f} dB"

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
def drum_breakbeat_fill(work):
    """The breakbeat fill (style 4) swaps the whole of bar 4 for a breakbeat: the snare (silent in pattern 1) comes in on
    the second beat of bar 4, and the clap that normally plays is quiet for that bar."""
    h = Harness(); h.record(os.path.join(work, "bfill.wav"))
    mutes = " ; ".join(f"ockm-{t}-mute 1" for t in ["d1","d3","d4","d5","d6","d7","d8","bass","lead","chord"])
    h.at(100, f"ockm-bpm 200 ; ockm-verb-mix 0 ; ockm-delay-mix 0 ; ockm-swing 50 ; ockm-length 16 ; ockm-fill-style 4 ; ockm-fill-every 4 ; {mutes}")
    h.at(200, "ockm-play 1"); h.at(6400, "ockm-play 0")
    _, (snd, sr) = play(work, h, "t_bfill", ms=6400)
    bar = 16 * 15000 / 200 / 1000.0
    start = 0.2
    def seg(a, b): return peak(snd[int((start + a) * sr):int((start + b) * sr)])
    assert seg(0.05, 3 * bar - 0.05) < 0.01, f"bars 1-3 should have no snare: {seg(0.05, 3 * bar - 0.05):.3f}"
    assert seg(3 * bar + 0.02, 3.2 * bar) < 0.01, "the breakbeat's snare starts on beat 2, not the 1"
    assert seg(3.25 * bar, 4 * bar) > 0.05, f"bar 4 should have the breakbeat snare: {seg(3.25 * bar, 4 * bar):.3f}"
    assert seg(4 * bar + 0.15, 5 * bar - 0.05) < 0.01, "bar 5 should be back to normal (no snare)"

@test
def turnaround_goes_to_five_major(work):
    """Turnaround every 4 bars, one-chord progression in A minor, bar pads: bars 1-3 play A minor, bar 4 plays E major
    (V, with the scale's 7th raised: G#), bar 5 is back on A minor."""
    h = Harness(); h.show("ockm-chord-notes-out")
    h.at(100, "ockm-bpm 200 ; ockm-root 9 ; ockm-scale 0 ; ockm-length 16 ; ockm-chord-len 16 ; ockm-chord-prog 0 ; ockm-chord-rhythm 0 ; ockm-chord-type 0 ; ockm-turn-every 4")
    h.at(300, "ockm-play 1"); h.at(300 + int(5.2 * 16 * 75), "ockm-play 0")
    f = os.path.join(work, "t_turn.pd"); h.finish(300 + int(5.4 * 16 * 75), f)
    out = run(work, f)
    chords = [sorted({int(float(n)) % 12 for n in v.split()[:4] if float(n) > 0}) for v in printed(out, "ockm-chord-notes-out")]   # 4 notes, then the velocity
    assert len(chords) >= 5, f"expected a chord each bar: {chords}"
    am, e = [0, 4, 9], [4, 8, 11]
    assert chords[:5] == [am, am, am, e, am], f"bars 1-5 should be Am Am Am E Am: {chords[:5]}"

@test
def second_half_climbs_to_seven(work):
    """v1.04 second half, climb: turnaround every 4 bars to VII (ockm-turn-to 6). One chord in A minor: bars 1-3 Am, bar 4 G
    (the key's own G, not raised), bar 5 Am again."""
    h = Harness(); h.show("ockm-chord-notes-out")
    h.at(100, "ockm-bpm 200 ; ockm-root 9 ; ockm-scale 0 ; ockm-length 16 ; ockm-chord-len 16 ; ockm-chord-prog 0 ; ockm-chord-rhythm 0 ; ockm-chord-type 0 ; ockm-turn-to 6 ; ockm-turn-every 4")
    h.at(300, "ockm-play 1"); h.at(300 + int(5.2 * 16 * 75), "ockm-play 0")
    f = os.path.join(work, "t_climb.pd"); h.finish(300 + int(5.4 * 16 * 75), f)
    out = run(work, f)
    chords = [sorted({int(float(n)) % 12 for n in v.split()[:4] if float(n) > 0}) for v in printed(out, "ockm-chord-notes-out")]
    am, g = [0, 4, 9], [2, 7, 11]
    assert chords[:5] == [am, am, am, g, am], f"bars 1-5 should be Am Am Am G Am: {chords[:5]}"

@test
def bass_turnaround_and_walk(work):
    """A following bass moves to V on the turnaround bar (one chord, A minor: A, then E on bar 4). With walk on, over
    i then iv (Am, Dm) the last offbeat of bar 1 steps a semitone below D (C#) instead of playing A."""
    h = Harness(); h.show("ockm-bass-notes-out")
    h.at(100, "ockm-bpm 200 ; ockm-root 9 ; ockm-scale 0 ; ockm-length 16 ; ockm-chord-len 16 ; ockm-chord-prog 0 ; ockm-turn-every 4 ; "
              "ockm-bass-len 16 ; ockm-bass-sync 1 ; ockm-bass-mode 0 ; ockm-bass-walk 0 ; ockm-bass-notes 0 ; ockm-bass-rhythm 6")
    h.at(300, "ockm-play 1"); h.at(300 + int(3.97 * 16 * 75), "ockm-play 0")
    h.at(300 + int(5.0 * 16 * 75), "ockm-turn-every 0 ; ockm-length 32 ; ockm-chord-len 32 ; ockm-chord-prog 1 ; ockm-bass-len 32 ; ockm-bass-rhythm 0 ; ockm-bass-walk 1")
    h.at(300 + int(5.3 * 16 * 75), "ockm-play 1"); h.at(300 + int(6.3 * 16 * 75), "ockm-play 0")
    f = os.path.join(work, "t_bturn.pd"); h.finish(300 + int(6.5 * 16 * 75), f)
    out = run(work, f)
    notes = [int(float(v.split()[0])) for v in printed(out, "ockm-bass-notes-out") if v.split()[0] != "off"]
    pcs = [n % 12 for n in notes]
    first = pcs[:16]
    assert first[:12] == [9] * 12 and first[12:16] == [4] * 4, f"quarters: A for 3 bars, then E on the turnaround bar: {first}"
    walk = pcs[16:20]
    assert walk[:3] == [9, 9, 9] and walk[3] == 1, f"offbeats in bar 1: A A A, then C# walking into Dm: {walk}"

@test
def half_time_plays_the_pattern_over_two_loops(work):
    """Half-time on the bass: the same 16-step riff plays one of its steps every two, so it takes two loops to get through
    it (first half, then second half) and the notes come out in the same order, half as often."""
    h = Harness(); h.show("ockm-bass-notes-out")
    h.at(100, "ockm-bpm 200 ; ockm-root 9 ; ockm-scale 0 ; ockm-length 16 ; ockm-chord-len 16 ; ockm-chord-prog 0 ; ockm-turn-every 0 ; "
              "ockm-bass-len 16 ; ockm-bass-sync 0 ; ockm-bass-mode 0 ; ockm-bass-notes 4 ; ockm-bass-rhythm 2 ; ockm-bass-half 0")
    h.at(300, "ockm-play 1"); h.at(300 + int(0.97 * 16 * 75), "ockm-play 0")
    h.at(300 + int(1.5 * 16 * 75), "test-mark 1 ; ockm-bass-half 1")
    h.at(300 + int(1.6 * 16 * 75), "ockm-play 1"); h.at(300 + int(3.57 * 16 * 75), "ockm-play 0")
    h.show("test-mark")
    f = os.path.join(work, "t_half.pd"); h.finish(300 + int(4.0 * 16 * 75), f)
    out = run(work, f)
    seq, cur = {0: [], 1: []}, 0
    for line in out.splitlines():
        if line.startswith("test-mark:"): cur = 1
        elif line.startswith("ockm-bass-notes-out:"):
            v = line.split(":", 1)[1].split()
            if v and v[0] != "off": seq[cur].append(int(float(v[0])))
    assert len(seq[0]) == 16, f"normal: 16 notes in one loop, got {len(seq[0])}"
    assert len(seq[1]) == 16, f"half-time: 16 notes over two loops, got {len(seq[1])}: {seq[1]}"
    assert seq[1] == seq[0], f"half-time keeps the riff in order: {seq[1]} vs {seq[0]}"

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
    """A part switched off in a pattern goes silent; the build rise climbs step by step, and drops back to 0 when switched off by hand."""
    h = Harness(); h.record(os.path.join(work, "partoff.wav")); h.show("ockm-rise-now")
    others = " ; ".join(f"ockm-{t}-mute 1" for t in ["d1","d2","d3","d4","d5","d6","d7","d8","lead","chord"])
    h.at(100, f"ockm-bass-gen bang ; {others} ; ockm-length 16 ; ockm-bpm 120 ; ockm-rise 1 ; ockm-play 1")
    h.at(1300, "ockm-bass-on 0 ; ockm-rise 0")
    h.at(2600, "ockm-play 0")
    out, (x, sr) = play(work, h, "t_partoff", ms=2600)
    on, off = peak(x[int(0.3 * sr):int(1.2 * sr)]), peak(x[int(1.5 * sr):int(2.5 * sr)])
    assert on > 0.05 and off < 0.005, f"the bass should play, then stop when switched off ({on:.3f} then {off:.4f})"
    rise = [float(v.split()[0]) for v in printed(out, "ockm-rise-now")]   # "value" or "value ms"
    first = rise[:8]
    assert len(first) >= 8 and all(b > a for a, b in zip(first, first[1:])) and first[-1] > first[0], f"the rise should climb step by step: {first}"
    assert rise[-1] == 0, f"the rise should drop to 0 when switched off: {rise[-3:]}"

@test
def sidechain_pump_ducks_the_synths(work):
    """Held organ chords, a kick on every beat (muted, so only the chords are heard). Pump 1: the chords dip just after each kick
    and swell back. Pump 0: they don't. The chords' own sidechain (ockm-chord-sidechain 1) dips them too, with the pump off."""
    res = {}
    for pump in (0, 1, 2):     # 2: the pump off, but the chords' own sidechain all the way up
        h = Harness(); h.record(os.path.join(work, f"pump{pump}.wav"))
        mutes = " ; ".join(f"ockm-{t}-mute 1" for t in ["d1","d2","d3","d4","d5","d6","d7","d8","bass","lead"])
        h.at(100, f"ockm-bpm 120 ; ockm-length 16 ; ockm-verb-mix 0 ; ockm-delay-mix 0 ; ockm-swing 50 ; ockm-chord-engine 1 ; ockm-chord-mode 1 ; ockm-chord-scshape 1 ; {mutes}")   # v1.49 pump named (duck is the default shape now)
        h.at(150, "ockm-pat-chord-on const 0 ; ockm-pat-chord-deg const 0 ; ockm-chord-edit 0 1 0 ; ockm-chord-k3 0 ; ockm-chord-k4 1")
        h.at(170, "ockm-pat-d1 const 0 ; ockm-d1-sound 0 ; ockm-edit d1 0 2 ; ockm-edit d1 4 2 ; ockm-edit d1 8 2 ; ockm-edit d1 12 2 ; ockm-pump " + str(min(pump, 1) if pump < 2 else 0) + " ; ockm-chord-sidechain " + str(1 if pump == 2 else 0))
        h.at(300, "ockm-play 1"); h.at(2400, "ockm-play 0")
        _, (x, sr) = play(work, h, f"t_pump{pump}", ms=2400)
        rms = lambda a, b: math.sqrt(sum(v * v for v in x[int(a * sr):int(b * sr)]) / max(1, int((b - a) * sr)))
        # beat 2 of the bar: kick at 0.3 + 0.5 + 0.0625 (quarter-step lag) s
        k = 0.3 + 0.5 + 0.0625
        res[pump] = (rms(k + 0.01, k + 0.06), rms(k + 0.35, k + 0.45))
    d0, d1 = res[0][0] / res[0][1], res[1][0] / res[1][1]
    assert d0 > 0.85, f"no pump: the pads should hold steady ({d0:.2f})"
    assert d1 < 0.55, f"pump on: the pads should dip after the kick ({d1:.2f})"
    d2 = res[2][0] / res[2][1]
    assert d2 < 0.55, f"the chords' own sidechain should dip them after the kick ({d2:.2f})"

@test
def rise_builds_then_drops(work):
    """Rise on a 1-bar loop (16 steps), pressed early in the bar: the build runs to a loop start at least 2 bars away, so 2 bars
    and a bit. With 16 steps to go the riser starts (3 beats long), the gap takes the last beat, then on the 1: rise turns
    itself off, the gap ends, the riser cuts, the filter snaps back (in 5 ms, not a 100 ms glide) and the impact plays."""
    h = Harness(); h.show("ockm-rise", "ockm-gap", "ockm-riser-go", "ockm-impact-go", "ockm-rise-now", "ockm-step")
    h.at(100, "ockm-lead-sync 0 ; ockm-bpm 120 ; ockm-length 16 ; ockm-drum-len 16 ; ockm-bass-len 16 ; ockm-lead-len 16 ; ockm-chord-len 16")
    h.at(200, "ockm-play 1"); h.at(200 + 2 * 125 + 60, "ockm-rise 1")       # pressed during step 2
    f = os.path.join(work, "t_rise.pd"); h.finish(200 + 52 * 125, f)
    out = run(work, f)
    ev = [l.split(":", 1) for l in out.splitlines() if l.split(":", 1)[0] in ("ockm-rise", "ockm-gap", "ockm-riser-go", "ockm-impact-go", "ockm-rise-now", "ockm-step")]
    steps = 0; seen = []
    for k, v in ev:
        v = v.strip()
        if k == "ockm-step": steps += 1; continue
        if k == "ockm-rise-now": continue
        seen.append((k, v, steps))
    order = [k + " " + v.split()[0] for k, v, _ in seen]
    assert order[:1] == ["ockm-rise 1"], order
    want = ["ockm-riser-go", "ockm-gap 1", "ockm-rise 0", "ockm-gap 0", "ockm-impact-go"]
    got = [o for o in order if o.split()[0] in ("ockm-riser-go", "ockm-impact-go") or o in ("ockm-gap 1", "ockm-rise 0", "ockm-gap 0")]
    got = [o if not o.startswith("ockm-riser-go") else "ockm-riser-go" for o in got]
    got = [o if not o.startswith("ockm-impact-go") else "ockm-impact-go" for o in got]
    dedup = [x for i, x in enumerate(got) if i == 0 or x != got[i - 1]]
    assert [x for x in dedup if x in want][:5] == want, f"the build then the drop, in order: {dedup}"
    at = {k + " " + v.split()[0]: n for k, v, n in seen}
    drop = at["ockm-rise 0"]
    assert drop % 16 == 1 and drop >= 3 + 32, f"the drop lands on a loop start at least 2 bars on (step count {drop})"
    rn = [l.split(":", 1)[1].split() for l in out.splitlines() if l.startswith("ockm-rise-now:")]
    assert ["0", "5"] in rn, f"the filter snaps back in 5 ms on the drop: {rn[-3:]}"
    peak = max(float(x[0]) for x in rn)
    assert 0.6 < peak <= 0.86, f"the high-pass climbs most of the way: {peak}"

@test
def lead_inside_to_outside(work):
    """The lead's inside-to-outside slider, over one chord (A minor) with an arp tune (all chord notes as written). Inside: every
    note is A, C or E. A little out: passing notes off the beat. Further: some 7ths and 9ths, octave leaps, and notes outside
    the key (chromatic). The same seed gives the same line twice."""
    h = Harness()
    def grab(ms, label):
        g = h.add(f"#X obj 10 300 r test-{label};"); t = h.add("#X obj 10 330 t b b;")
        for i, nm in enumerate(["note", "on"]):
            a = h.add(f"#X obj 10 360 array get ockm-pat-lead-{nm} 0 64;"); l = h.add(f"#X obj 10 390 list prepend {label}-{nm};")
            pr = h.add("#X obj 10 420 list trim;"); pp = h.add("#X obj 10 450 print GEN;")
            h.con(t, a, 1 - i); h.con(a, l); h.con(l, pr); h.con(pr, pp)
        h.con(g, t); h.at(ms, f"test-{label} bang")
    h.at(100, "ockm-root 9 ; ockm-scale 0 ; ockm-chord-prog 0 ; ockm-length 64 ; ockm-lead-len 64 ; ockm-lead-sync 1 ; ockm-lead-seed 0 ; ockm-lead-density 1 ; ockm-lead-rhythm 1 ; ockm-lead-notes 8")
    for i, (lab, o) in enumerate([("in", 0), ("pass", 0.45), ("out", 1), ("out2", 1)]):
        h.at(200 + i * 100, f"ockm-lead-outside {o}"); grab(250 + i * 100, lab)
    f = os.path.join(work, "t_outside.pd"); h.finish(700, f)
    out = run(work, f)
    got = {v.split()[0]: [int(float(x)) for x in v.split()[1:]] for v in printed(out, "GEN")}
    def pcs(k):
        return [n % 12 for n, o in zip(got[k + "-note"], got[k + "-on"]) if o]
    chord, key = {9, 0, 4}, {9, 11, 0, 2, 4, 5, 7}
    pi, pp, po = pcs("in"), pcs("pass"), pcs("out")
    assert pi and all(p in chord for p in pi), f"inside: every note on A minor's chord notes: {sorted(set(pi))}"
    assert any(p not in chord for p in pp) and all(p in key for p in pp), f"a little out: passing notes, still in key: {sorted(set(pp))}"
    assert any(p not in key for p in po), f"outside: some chromatic notes: {sorted(set(po))}"
    assert sum(1 for p in po if p not in chord) > sum(1 for p in pp if p not in chord), "further out: more notes off the chord"
    assert got["out-note"] == got["out2-note"], "the same setting and seed: the same line"

@test
def sidechain_shapes_duck_pump_gate(work):
    """Held organ chords, a kick on every beat (muted), the chords' sidechain all the way up, in each shape. 120 bpm, so a step is
    125 ms. Duck: gone under the kick, back within a step. Pump: still deep at 100 ms, half back by 300 ms. Gate: silent for an eighth
    (250 ms), then straight back."""
    res = {}
    for shape in (-1, 0, 1, 2):     # -1: no sidechain, the reference
        h = Harness(); h.record(os.path.join(work, f"sc{shape}.wav"))
        mutes = " ; ".join(f"ockm-{t}-mute 1" for t in ["d1","d2","d3","d4","d5","d6","d7","d8","bass","lead"])
        h.at(100, f"ockm-bpm 120 ; ockm-length 16 ; ockm-verb-mix 0 ; ockm-delay-mix 0 ; ockm-swing 50 ; ockm-chord-engine 1 ; ockm-chord-mode 1 ; ockm-chord-level 0.3 ; {mutes}")   # v1.49 under the master limiter, so it measures the dip alone
        h.at(150, "ockm-pat-chord-on const 0 ; ockm-pat-chord-deg const 0 ; ockm-chord-edit 0 1 0 ; ockm-chord-k3 0 ; ockm-chord-k4 1")
        h.at(170, "ockm-pat-d1 const 0 ; ockm-d1-sound 0 ; ockm-edit d1 0 2 ; ockm-edit d1 4 2 ; ockm-edit d1 8 2 ; ockm-edit d1 12 2 ; ockm-pump 0 ; "
                  f"ockm-chord-sidechain {0 if shape < 0 else 1} ; ockm-chord-scshape {max(shape, 0)}")
        h.at(300, "ockm-play 1"); h.at(2400, "ockm-play 0")
        _, (x, sr) = play(work, h, f"t_sc{shape}", ms=2400)
        rms = lambda a, b: math.sqrt(sum(v * v for v in x[int(a * sr):int(b * sr)]) / max(1, int((b - a) * sr)))
        k = 0.3 + 0.5 + 0.03125 + 0.0045   # beat 2's kick (a quarter step late, like every hit), plus the master limiter's look-ahead (v1.49, 3 ms and a block)
        res[shape] = [rms(k + a, k + b) for a, b in [(0.005, 0.03), (0.11, 0.14), (0.29, 0.32)]]
    g = {s: [v / max(r, 1e-9) for v, r in zip(res[s], res[-1])] for s in (0, 1, 2)}
    shown = {s: [round(v, 2) for v in g[s]] for s in g}
    assert all(g[s][0] < 0.25 for s in g), f"every shape dips right after the kick: {shown}"
    assert g[0][1] > 0.7, f"duck: back within a step: {shown}"
    assert g[1][1] < 0.3 and 0.2 < g[1][2] < 0.8, f"pump: still deep at 100 ms, swelling back by 300 ms: {shown}"
    assert g[2][1] < 0.1 and g[2][2] > 0.8, f"gate: cut for the eighth, then straight back: {shown}"

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
    tap(200, 808, 100)                   # new blank project
    f = os.path.join(work, "t_touchproj.pd"); h.finish(400, f)
    out = run(work, f)
    errs = [l for l in out.splitlines() if "error" in l.lower() and "current.txt" not in l]
    made = [d for d in os.listdir(os.path.join(work, "projects")) if re.match(r"\d{4}-\d\d-\d\d-[a-z]+-[a-z]+$", d)]
    assert made, f"no new project folder: {os.listdir(os.path.join(work, 'projects'))} {errs[:3]}"
    assert os.path.exists(os.path.join(work, "projects", made[0], "loop.txt")), "the new project should be written straight away"
    assert open(os.path.join(work, "projects", "current.txt")).read().strip() == made[0] + ";"

@test
def touchscreen_save_makes_variations(work):
    """v1.10: save keeps the version you had and carries on in a new variation (-v2, -v3). A new project's first save just
    saves it, and save with nothing changed makes nothing."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-project-saveas")
    tap = lambda ms, x, y: h.at(ms, f"ockm-ui-test tap {x} {y}")
    tap(150, 919, 36); tap(151, 830, 95)   # menu, project
    tap(200, 808, 100)                     # new blank project
    tap(250, 719, 36)                              # mixer
    tap(300, 54, 300); tap(320, 865, 36)           # kick fader, then the first save: plain
    tap(400, 54, 340); tap(420, 865, 36)           # v2
    tap(500, 865, 36)                              # nothing changed: nothing made
    tap(600, 54, 380); tap(620, 865, 36)           # v3
    f = os.path.join(work, "t_variations.pd"); h.finish(800, f)
    out = run(work, f)
    P = os.path.join(work, "projects")
    made = sorted(d for d in os.listdir(P) if re.match(r"\d{4}-\d\d-\d\d-[a-z]+-[a-z]+(-v\d+)?$", d))
    assert len(made) == 3, f"a project and two variations: {made}"
    base = made[0]
    assert made[1:] == [base + "-v2", base + "-v3"], made
    assert printed(out, "ockm-project-saveas") == ["symbol " + base + "-v2", "symbol " + base + "-v3"] or \
        [v.split()[-1] for v in printed(out, "ockm-project-saveas")] == [base + "-v2", base + "-v3"], printed(out, "ockm-project-saveas")
    def lev(d):
        txt = "".join(open(os.path.join(P, d, f)).read() for f in os.listdir(os.path.join(P, d)) if f.endswith(".txt"))
        return [l for l in txt.split(";") if l.strip().startswith("ockm-d1-level ")][0].split()[-1]
    levels = [lev(base), lev(base + "-v2"), lev(base + "-v3")]
    assert len(set(levels)) == 3, f"each variation keeps its own save: {levels}"
    assert open(os.path.join(P, "current.txt")).read().strip() == base + "-v3;"

@test
def touchscreen_variation_browser_keeps_and_tidies(work):
    """v1.26: the project page's variations. Seven saves make v1 to v7; pick v2 and keep it, then tidy up (under more):
    the newest five, the kept one and the open one stay, the rest go to the trash folder. Every save is stamped with its time."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness()
    tap = lambda ms, x, y: h.at(ms, f"ockm-ui-test tap {x} {y}")
    tap(150, 919, 36); tap(151, 830, 95)   # menu, project
    tap(200, 808, 100)                     # new blank project
    tap(250, 719, 36)                      # mixer
    for i in range(7):                     # seven saves: the project, then v2 to v7
        tap(300 + i * 100, 54, 280 + i * 14); tap(320 + i * 100, 865, 36)
    tap(1100, 919, 36); tap(1101, 830, 95)   # back to the project page (the open project is picked)
    tap(1150, 885, 376)                    # v2 (newest first, three across since v1.47: v7 v6 v5 / v4 v3 v2 / v1)
    tap(1200, 830, 269)                    # keep it
    tap(1250, 876, 230)                    # more
    tap(1300, 480, 248); tap(1350, 480, 248)   # tidy up, tap again
    f = os.path.join(work, "t_browser.pd"); h.finish(1500, f)
    out = run(work, f)
    P = os.path.join(work, "projects")
    left = sorted(d for d in os.listdir(P) if re.match(r"\d{4}-\d\d-\d\d-", d))
    trash = os.listdir(os.path.join(work, "trash")) if os.path.exists(os.path.join(work, "trash")) else []
    assert len(left) == 6 and all(re.search(r"-v[234567]$", d) for d in left), f"v2 (kept) to v7 should stay: {left} trash {trash}"
    assert any(not re.search(r"-v\d+$", d) for d in trash), f"v1 should be in the trash: {trash}"
    meta = open(os.path.join(P, [d for d in left if d.endswith("-v2")][0], "variation.txt")).read()
    assert "keep = true" in meta and "saved = " in meta, meta

@test
def project_page_plays_a_variation_and_comes_back(work):
    """v1.26: ▶ on the project page plays a saved variation without leaving the page: what was open (with its unsaved
    changes) is set aside, and comes back exactly when you stop."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-project-name", "ockm-d1-level", "ockm-playing", "ockm-saved", "ockm-stash", "ockm-unstash", "ockm-project-open")
    tap = lambda ms, x, y: h.at(ms, f"ockm-ui-test tap {x} {y}")
    tap(150, 919, 36); tap(151, 830, 95)   # menu, project
    tap(200, 808, 100)                     # new blank project
    tap(700, 719, 36)                      # mixer (after the new project's own first save, 300 ms on)
    tap(750, 54, 300); tap(770, 865, 36)   # the kick's fader, saved
    tap(850, 54, 380)                      # moved again, not saved
    tap(900, 919, 36); tap(901, 830, 95)   # the project page
    tap(950, 668, 318)                     # v1's play button (v1.47: the scenes panel moved right for the table)
    h.at(1250, "ockm-play 0")              # stop
    f = os.path.join(work, "t_preview.pd"); h.finish(1450, f)
    out = run(work, f)
    names = [v.split()[-1] for v in printed(out, "ockm-project-name")]
    lv = [round(float(v.split()[-1]), 3) for v in printed(out, "ockm-d1-level")]
    assert "1" in [v.split()[-1] for v in printed(out, "ockm-playing")], "it played"
    saved, moved = lv[1], lv[2]            # the fader's two moves (before them: the new project's own value)
    assert saved != moved and saved in lv[3:-1], f"the saved level played: {lv}"
    assert lv[-1] == moved, f"stopped: the unsaved level is back: {lv}"
    assert len(set(names)) == 1, f"the same project is open at the end: {names}"
    assert open(os.path.join(work, "projects", "current.txt")).read().strip() == names[-1] + ";"

@test
def lua_generators_plain_tests(work):
    """v1.12: the generators' musical logic is plain Lua: its own tests run without Pd (tests/lua/test_*.lua)."""
    lua = shutil.which("lua5.4") or shutil.which("lua5.3") or shutil.which("lua")
    if not lua:
        raise Skip("no lua interpreter")
    tdir = os.path.join(ROOT, "tests", "lua")
    for fn in sorted(os.listdir(tdir)):
        if fn.startswith("test_") and fn.endswith(".lua"):
            p = subprocess.run([lua, os.path.join(tdir, fn), work], capture_output=True, text=True)
            assert p.returncode == 0 and p.stdout.strip().endswith("ok"), f"{fn}: {p.stdout} {p.stderr}"

# v1.14: every synth knob has to make an audible difference. Each engine's knobs are taken from 0 to 1 (the others at the
# engine's sweet spot) while a phrase plays, and the change is measured: tone (the spectrum's shape, in dB across 24
# bands) or length (how much of the time it sounds). 1.0 is clearly audible (6 dB of tone or 15% longer notes); below
# KNOB_MIN fails. Knobs whose change is movement rather than tone (detune, spread, drift, tremolo) are listed apart:
# the spectrum barely moves when they turn, so they're checked by ear. Loudness mustn't jump either (except length).
KNOB_ENGINES = {
    "lead": {2: [0.45, 0.1, 0.25, 0.5], 3: [0.4, 0.55, 0.5, 0.45], 4: [0.55, 0.3, 0.4, 0.45], 5: [0.55, 0.55, 0.3, 0.5], 6: [0.55, 0.82, 0.7, 0.35], 7: None},   # v1.45 7 is the Analog: its knobs are its own (bass_and_lead_play_the_synths)
    "bass": {0: [0.35, 0.6, 0.55, 0.4], 1: [0.45, 0.3, 0.35, 0.55], 2: [0.4, 0.35, 0.45, 0.4], 3: [0.45, 0.5, 0.35, 0.5], 5: [0.42, 0.25, 0.45, 0.45],
             6: [0.5, 0.5, 0.35, 0.45], 7: [0.3, 0.75, 0.6, 0.35], 8: None, 9: [0.35, 0.35, 0.3, 0.45]},   # v1.45 8 is the Bass synth
    "chord": {0: [0.45, 0.5, 0.0, 0.32], 6: [0.45, 0.6, 0.6, 0.3], 1: [0.5, 0.4, 0.3, 0.4], 3: [0.5, 0.3, 0.4, 0.4], 4: [0.5, 0.4, 0.3, 0.5]},
}
KNOB_MOVEMENT = {("lead", 2, 3), ("lead", 5, 1), ("lead", 5, 3), ("bass", 3, 2), ("bass", 5, 2), ("chord", 0, 2), ("chord", 4, 3)}   # (part, engine, knob 1-4)
KNOB_LENGTH = 4          # k4 is decay or length: it may change the loudness
KNOB_MIN, KNOB_LEVEL_MAX = 0.4, 10.0
def ui_sounds():
    """The sounds on each part's tab (build.py SOUNDS, as written into the screen code): {part: [(engine, k1..k4, drive, trim)]}."""
    src = open(os.path.join(ROOT, "ui", "ockm-ui.pd_lua")).read()
    line = next(l for l in src.splitlines() if l.startswith("ockm_SOUNDS = "))
    py = re.sub(r"(\w+) = \{", r'"\1": {', line[len("ockm_SOUNDS = "):]).replace("nil", "None")
    py = py.replace("{", "[").replace("}", "]")
    py = "{" + py[1:-1] + "}"
    return eval(py)


# v1.49 the second phrase each sound is measured on: long notes (the first, KNOB_PHRASE, is short and busy), so a sound
# is levelled for both kinds of part and not just the one
LONG_PHRASE = {"lead": "ockm-lead-rhythm 14 ; ockm-lead-notes 15", "bass": "ockm-bass-rhythm 5 ; ockm-bass-riff 1",
               "chord": "ockm-chord-rhythm 0 ; ockm-chord-prog 1 ; ockm-chord-type 1"}


def measure_sounds(work, parts=("bass", "lead", "chord"), use_trim=True, first_only=False):
    """Each sound's loudness, averaged (in dB) over a busy phrase and a long one (see measure_sounds_on)."""
    a = measure_sounds_on(work, KNOB_PHRASE, parts, use_trim, first_only)
    b = measure_sounds_on(work, LONG_PHRASE, parts, use_trim, first_only)
    return {pt: [10 ** ((20 * math.log10(max(x, 1e-9)) + 20 * math.log10(max(y, 1e-9))) / 40) for x, y in zip(a[pt], b[pt])] for pt in a}


def measure_sounds_on(work, phrases, parts=("bass", "lead", "chord"), use_trim=True, first_only=False):
    """Play every sound of each part in turn (a typical phrase, nothing else playing, no effects) and measure its
    loudness (RMS of the master). Returns {part: [rms per sound]}. With use_trim False, every trim is 1 (to work trims out)."""
    out = {}
    S = ui_sounds()
    for part in parts:
        h = Harness(); name = f"snd-{part}-{abs(hash(phrases[part])) % 1000}"; h.record(os.path.join(work, name + ".wav"))
        quiet = " ; ".join(f"ockm-{p}-{k} 0" for p in ("bass", "lead", "chord") for k in ("verb", "delay", "lfo-depth", "chorus", "sidechain"))
        others = " ; ".join(f"ockm-{p}-on {1 if p == part else 0}" for p in ("bass", "lead", "chord"))
        drums = " ; ".join(f"ockm-d{i}-mute 1" for i in range(1, 9))
        h.at(100, f"ockm-length 32 ; ockm-fill-every 0 ; ockm-bpm 124 ; ockm-root 9 ; ockm-scale 0 ; ockm-verb-mix 0 ; ockm-delay-mix 0 ; {quiet} ; {others} ; {drums} ; ockm-{part}-level 1 ; {phrases[part]}"
             + (" ; ockm-lead-sync 0 ; ockm-lead-len 32" if part == "lead" else ""))   # v1.49 the phrase the levels were set on (a following lead is 4 bars now)
        t, wins = 300, []
        for snd in (S[part][:1] if first_only else S[part]):
            e, k, drive, trim = snd[0], snd[1:5], snd[5], snd[6]
            msg = f"ockm-{part}-engine {e} ; ockm-{part}-trim {trim if use_trim else 1}" + ("" if use_trim else f" ; ockm-{part}-egain 1")
            if part != "chord": msg += f" ; ockm-{part}-drive {drive}"
            if k[0] is not None: msg += " ; " + " ; ".join(f"ockm-{part}-k{j + 1} {k[j]}" for j in range(4))
            elif e == 8 and part == "bass": msg += " ; ib-cutoff 0.3 ; ib-resonance 0.35 ; ib-env 0.35 ; ib-decay 0.35"
            h.at(t, msg)
            if t == 300: h.at(400, "ockm-play 1")
            wins.append((t + 700, t + 2700)); t += 2800
        f = os.path.join(work, name + ".pd"); h.finish(t, f)
        run(work, f, timeout=t / 1000 * 3 + 60)
        snd_, sr = read_wav(h.wav)
        kw = k_weighted(snd_, sr)
        def momentary(a, b):   # the loudest 400 ms in the window (how loud the notes are, not how long they ring)
            n, hop, best = int(0.4 * sr), int(0.1 * sr), 0.0
            for i in range(int(a / 1000 * sr), int(b / 1000 * sr) - n, hop):
                seg = kw[i:i + n]; best = max(best, math.sqrt(sum(v * v for v in seg) / n))
            return best
        out[part] = [momentary(a, b) for a, b in wins]   # the recording starts at 0
    return out


def k_weighted(x, sr):
    """The signal as the ear weighs loudness (ITU-R BS.1770's K-weighting: a lift above about 1.5 kHz and a cut below
    about 40 Hz), so a deep sub and a bright lead are compared fairly."""
    def biquad(sig, b, a):
        try:
            from scipy.signal import lfilter
            return list(lfilter(b, a, sig))
        except ImportError:
            y, x1, x2, y1, y2 = [], 0.0, 0.0, 0.0, 0.0
            b0, b1, b2 = (v / a[0] for v in b); a1, a2 = a[1] / a[0], a[2] / a[0]
            for v in sig:
                o = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
                x2, x1, y2, y1 = x1, v, y1, o; y.append(o)
            return y
    G, Q, fc = 3.99984385397, 0.7071752369554193, 1681.9744509555319
    A = 10 ** (G / 40); w = 2 * math.pi * fc / sr; al = math.sin(w) / (2 * Q); c = math.cos(w); sA = math.sqrt(A)
    b = [A * ((A + 1) + (A - 1) * c + 2 * sA * al), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - 2 * sA * al)]
    a = [(A + 1) - (A - 1) * c + 2 * sA * al, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - 2 * sA * al]
    y = biquad(x, b, a)
    Q, fc = 0.5003270373253953, 38.13547087613982
    w = 2 * math.pi * fc / sr; al = math.sin(w) / (2 * Q); c = math.cos(w)
    return biquad(y, [(1 + c) / 2, -(1 + c), (1 + c) / 2], [1 + al, -2 * c, 1 - al])


@test
def sounds_sit_at_one_level(work):
    """v1.49 every sound on the bass, lead and chord tabs ("analogue 2", "donk 1"...) comes out within about 3 dB of the
    part's first sound, so stepping through them never jumps the mix (each has a measured trim)."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    lv = measure_sounds(work)
    bad = []
    for part, l in lv.items():
        ref = l[0]
        for i, v in enumerate(l):
            db = 20 * math.log10(max(v, 1e-9) / ref)
            if abs(db) > 3: bad.append(f"{part} sound {i + 1}: {db:+.1f} dB")
    assert not bad, "out of level: " + ", ".join(bad)


KNOB_PHRASE = {"lead": "ockm-lead-rhythm 10 ; ockm-lead-notes 15", "bass": "ockm-bass-rhythm 0 ; ockm-bass-riff 1",
               "chord": "ockm-chord-rhythm 2 ; ockm-chord-prog 1 ; ockm-chord-type 1"}

@test
def every_synth_knob_makes_a_difference(work):
    """Every knob on every synth engine changes the sound clearly from 0 to 1, without a big jump in loudness."""
    try:
        import numpy as np
    except ImportError:
        raise Skip("numpy not installed")
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness()
    w_ = h.add("#X obj 600 40 writesf~ 1;"); r_ = h.add("#X obj 600 10 r test-wav;"); s_ = h.add("#X obj 700 10 r~ ockm-master;")
    h.con(r_, w_); h.con(s_, w_)
    cases, t = [], 300
    quiet = " ; ".join(f"ockm-{p}-{k} 0" for p in ("bass", "lead", "chord") for k in ("verb", "delay", "lfo-depth", "chorus", "sidechain"))
    h.at(200, f"ockm-length 32 ; ockm-fill-every 0 ; ockm-bpm 124 ; ockm-drum-groove 12 ; ockm-root 9 ; ockm-scale 0 ; {quiet}")
    for part, engines in KNOB_ENGINES.items():
        others = " ; ".join(f"ockm-{p}-on {1 if p == part else 0}" for p in ("bass", "lead", "chord"))
        h.at(t, f"{others} ; {KNOB_PHRASE[part]} ; ockm-play 1"); t += 100
        for eng, dk in engines.items():
            if dk is None:   # a synth engine: skipped, its time kept so the rest land on the same bars as before
                t += 8 * 2200; continue
            for j in range(4):
                for v in (0, 1):
                    k = list(dk); k[j] = v
                    path = os.path.join(work, f"knob-{part}-{eng}-{j}-{v}.wav")
                    h.at(t, f"ockm-{part}-engine {eng} ; " + " ; ".join(f"ockm-{part}-k{i+1} {k[i]}" for i in range(4)))
                    h.at(t + 150, f"test-wav open {path} , start"); h.at(t + 2100, "test-wav stop")
                    cases.append((part, eng, j, v, path)); t += 2200
    f = os.path.join(work, "t_knobs.pd"); h.finish(t + 100, f)
    p = subprocess.run([PD, "-nogui", "-nosound", "-nomidi", "-batch", "-path", PDLUA, "-lib", "pdlua", "-open", "OCKM_GENERATOR.pd", "-open", f],
                       cwd=work, capture_output=True, text=True, timeout=900)
    import wave
    edges = np.geomspace(60, 16000, 25)
    def feats(fn):
        wv = wave.open(fn); sr = wv.getframerate()
        x = np.frombuffer(wv.readframes(wv.getnframes()), np.int16 if wv.getsampwidth() == 2 else np.int32).astype(float)
        x = x.reshape(-1, wv.getnchannels())[:, 0]; x = x / (np.abs(x).max() + 1e-9) * 0.5 if False else x
        X = np.abs(np.fft.rfft(x)) ** 2; fr = np.fft.rfftfreq(len(x), 1 / sr)
        bands = np.array([10 * np.log10(X[(fr >= a) & (fr < b)].sum() + 1e-12) for a, b in zip(edges[:-1], edges[1:])]) - 10 * np.log10(X.sum() + 1e-12)
        env = np.convolve(np.abs(x), np.ones(441) / 441, "same")
        return bands, float((env > env.max() * 0.1).mean()) if env.max() > 0 else 0.0, 10 * np.log10((x ** 2).mean() + 1e-12)
    F = {}
    for part, eng, j, v, path in cases:
        assert os.path.exists(path), f"no recording for {part} engine {eng} k{j+1}={v}: {p.stdout[-300:]} {p.stderr[-300:]}"
        F[(part, eng, j, v)] = feats(path)
    weak, loud = [], []
    for part, engines in KNOB_ENGINES.items():
        for eng in engines:
            if engines[eng] is None: continue
            for j in range(4):
                (b0, o0, l0), (b1, o1, l1) = F[(part, eng, j, 0)], F[(part, eng, j, 1)]
                impact = max(float(np.mean(np.abs(b1 - b0))) / 6, abs(o1 - o0) / 0.15)
                if impact < KNOB_MIN and (part, eng, j + 1) not in KNOB_MOVEMENT:
                    weak.append(f"{part} engine {eng} k{j+1}: {impact:.2f}")
                if j + 1 != KNOB_LENGTH and abs(l1 - l0) > KNOB_LEVEL_MAX:
                    loud.append(f"{part} engine {eng} k{j+1}: {l1 - l0:+.1f} dB")
    assert not weak, "knobs that hardly change the sound: " + ", ".join(weak)
    assert not loud, "knobs that change the loudness more than the sound: " + ", ".join(loud)

@test
def several_solos_count_together(work):
    """v1.15: solo two tracks, then unsolo one: the other stays soloed (the count used to hold only the last solo pressed)."""
    h = Harness(); h.show("ockm-soloing")
    h.at(100, "ockm-lead-solo 1"); h.at(150, "ockm-chord-solo 1"); h.at(200, "ockm-chord-solo 0"); h.at(250, "ockm-lead-solo 0")
    f = os.path.join(work, "t_solos.pd"); h.finish(300, f)
    out = run(work, f)
    assert [v.split()[0] for v in printed(out, "ockm-soloing")] == ["1", "2", "1", "0"], printed(out, "ockm-soloing")

@test
def touchscreen_scene_switches_on_and_off(work):
    """v1.15: drums only is a switch: on mutes the synths, off puts back exactly what was muted before (here the bass)."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-bass-mute", "ockm-lead-mute", "ockm-d1-mute")
    tap = lambda ms, x, y: h.at(ms, f"ockm-ui-test tap {x} {y}")
    tap(100, 610, 36)                       # perform
    h.at(150, "ockm-bass-mute 1")           # the bass muted by hand
    tap(200, 74, 556)                       # drums only: on
    tap(300, 74, 556)                       # and off again
    f = os.path.join(work, "t_scene.pd"); h.finish(400, f)
    out = run(work, f)
    last = lambda n: (printed(out, n) or ["?"])[-1].split()[0]
    lead = [v.split()[0] for v in printed(out, "ockm-lead-mute")]
    assert "1" in lead and last("ockm-lead-mute") == "0", f"drums only should mute the lead, then let it back: {lead}"
    assert last("ockm-bass-mute") == "1", f"switching off should leave the bass muted, as it was: {printed(out, 'ockm-bass-mute')}"
    assert last("ockm-d1-mute") in ("0", "?"), "the kick plays throughout"

@test
def rewind_and_beat_repeat(work):
    """v1.17: rewind spins the mix back (half a second) and restarts the loop; while repeat is held the drums repeat
    themselves every slice (an eighth to start; the synths are off here so the drums can be measured)."""
    try:
        import numpy as np
    except ImportError:
        raise Skip("numpy not installed")
    def rec(name, msgs, end):
        h = Harness(); h.record(os.path.join(work, name + ".wav")); h.show("ockm-play")
        h.at(100, "ockm-bpm 124 ; ockm-drum-groove 3 ; ockm-bass-on 1 ; ockm-lead-on 1 ; ockm-chord-on 1 ; ockm-play 1")
        for ms, m in msgs: h.at(ms, m)
        h.at(end, "ockm-play 0"); f = os.path.join(work, name + ".pd"); h.finish(end + 100, f)
        p = subprocess.run([PD, "-nogui", "-nosound", "-nomidi", "-batch"] + (["-path", PDLUA, "-lib", "pdlua"] if PDLUA else []) +
                           ["-open", "OCKM_GENERATOR.pd", "-open", f], cwd=work, capture_output=True, text=True, timeout=300)
        wv = wave.open(os.path.join(work, name + ".wav")); sr = wv.getframerate()
        x = np.frombuffer(wv.readframes(wv.getnframes()), np.int16).astype(float)[::wv.getnchannels()] / 32768
        return x, sr, p.stdout + p.stderr
    x, sr, o = rec("rw", [(3000, "ockm-rewind bang")], 6000)
    during = np.sqrt((x[int(3.05 * sr):int(3.45 * sr)] ** 2).mean())
    assert during > 0.01, f"rewind should play the mix backwards, not go quiet: {during:.4f}"
    assert [l for l in o.splitlines() if l.startswith("ockm-play")][:2] == ["ockm-play: 1", "ockm-play: 1"], "rewind should restart the loop"
    x, sr, o = rec("rp", [(150, "ockm-bass-on 0 ; ockm-lead-on 0 ; ockm-chord-on 0"), (2000, "ockm-repeat 1"), (4000, "ockm-repeat 0")], 5000)
    L = int(2 * 60000 / 124 / 4 / 1000 * sr)
    sim = lambda a, b: float(np.corrcoef(x[int(a * sr):int(b * sr)], x[int(a * sr) - L:int(b * sr) - L])[0, 1])
    assert sim(2.3, 2.9) > 0.8, f"held, each eighth should repeat the one before: {sim(2.3, 2.9):.2f}"
    assert sim(1.0, 1.6) < 0.7, f"before it, the drums don't repeat every eighth: {sim(1.0, 1.6):.2f}"

@test
def two_handed_chords(work):
    """v1.20: with two hands on the piano, a left hand plays the root low down (G2 to F#3), so the 80-200 Hz band fills;
    on one hand, or on the poly (which has no left hand), it stays empty."""
    try:
        import numpy as np
    except ImportError:
        raise Skip("numpy not installed")
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    def low(name, eng, hands):
        h = Harness(); h.record(os.path.join(work, name + ".wav"))
        h.at(100, f"ockm-bpm 124 ; ockm-drums-on 0 ; ockm-bass-on 0 ; ockm-lead-on 0 ; ockm-chord-on 1 ; ockm-chord-prog 10 ; ockm-chord-rhythm 2 ; "
                  f"ockm-chord-lowcut 90 ; ockm-chord-delay 0 ; ockm-chord-engine {eng} ; ockm-chord-hands {hands} ; ockm-play 1")
        h.at(4000, "ockm-play 0"); f = os.path.join(work, name + ".pd"); h.finish(4100, f)
        subprocess.run([PD, "-nogui", "-nosound", "-nomidi", "-batch", "-path", PDLUA, "-lib", "pdlua", "-open", "OCKM_GENERATOR.pd", "-open", f],
                       cwd=work, capture_output=True, text=True, timeout=300)
        wv = wave.open(os.path.join(work, name + ".wav")); sr = wv.getframerate()
        x = np.frombuffer(wv.readframes(wv.getnframes()), np.int16).astype(float)[::wv.getnchannels()] / 32768
        x = x[int(0.3 * sr):]
        X = np.abs(np.fft.rfft(x)) ** 2; fr = np.fft.rfftfreq(len(x), 1 / sr)
        return float(X[(fr > 80) & (fr < 200)].sum() / max(1e-12, X[fr > 20].sum()))
    one, two, poly = low("h_one", 3, 0), low("h_two", 3, 2), low("h_poly", 0, 2)
    assert two > 0.03, f"two hands: the left hand should fill 80-200 Hz ({two:.3f})"
    assert one < two / 4, f"one hand: no left hand ({one:.3f} against {two:.3f})"
    assert poly < two / 4, f"the poly has no left hand ({poly:.3f})"

@test
def gap_before_the_drop(work):
    """v1.22: ockm-gap-arm 4 silences the whole mix (reverb and delay too) for the bar's last beat, then the drop comes back on the 1."""
    try:
        import numpy as np
    except ImportError:
        raise Skip("numpy not installed")
    h = Harness(); h.record(os.path.join(work, "gap.wav"))
    h.at(100, "ockm-bpm 124 ; ockm-drum-groove 3 ; ockm-verb-mix 0.6 ; ockm-delay-mix 0.5 ; ockm-play 1")
    h.at(2150, "ockm-gap-arm 4")            # early in bar 2 (bar 2 starts about 2035 ms)
    h.at(5000, "ockm-play 0"); f = os.path.join(work, "gap.pd"); h.finish(5100, f)
    subprocess.run([PD, "-nogui", "-nosound", "-nomidi", "-batch"] + (["-path", PDLUA, "-lib", "pdlua"] if PDLUA else []) +
                   ["-open", "OCKM_GENERATOR.pd", "-open", f], cwd=work, capture_output=True, text=True, timeout=300)
    wv = wave.open(os.path.join(work, "gap.wav")); sr = wv.getframerate()
    x = np.frombuffer(wv.readframes(wv.getnframes()), np.int16).astype(float)[::wv.getnchannels()] / 32768
    rms = lambda a, b: float(np.sqrt((x[int(a * sr):int(b * sr)] ** 2).mean()))
    before, gap, after = rms(2.6, 3.3), rms(3.55, 3.9), rms(4.1, 4.6)
    assert before > 0.01 and after > 0.01, f"it plays either side of the gap: {before:.4f} {after:.4f}"
    assert gap < before / 30, f"the last beat should be silent, effects and all: {gap:.5f} against {before:.4f}"

@test
def bus_effects_shape_their_bus(work):
    """v1.23: the bus effects. Crush on the drums bus changes its sound but not its level much; the music bus's filter,
    pulled left, takes the top off the music; out, the mix is untouched."""
    try:
        import numpy as np
    except ImportError:
        raise Skip("numpy not installed")
    def rec(name, msgs):
        h = Harness(); h.record(os.path.join(work, name + ".wav"))
        h.at(100, "ockm-bpm 124 ; ockm-drum-groove 3 ; ockm-chord-engine 3 ; ockm-chord-rhythm 9 ; " + msgs + " ; ockm-play 1")
        h.at(4000, "ockm-play 0"); f = os.path.join(work, name + ".pd"); h.finish(4100, f)
        subprocess.run([PD, "-nogui", "-nosound", "-nomidi", "-batch"] + (["-path", PDLUA, "-lib", "pdlua"] if PDLUA else []) +
                       ["-open", "OCKM_GENERATOR.pd", "-open", f], cwd=work, capture_output=True, text=True, timeout=300)
        wv = wave.open(os.path.join(work, name + ".wav")); sr = wv.getframerate()
        x = np.frombuffer(wv.readframes(wv.getnframes()), np.int16).astype(float)[::wv.getnchannels()] / 32768
        x = x[int(0.5 * sr):]
        X = np.abs(np.fft.rfft(x)) ** 2; fr = np.fft.rfftfreq(len(x), 1 / sr)
        return 10 * np.log10((x ** 2).mean() + 1e-12), 10 * np.log10(X[fr > 4000].sum() / max(1e-12, X[fr > 20].sum()) + 1e-12)
    drums = "ockm-bass-on 0 ; ockm-lead-on 0 ; ockm-chord-on 0"
    d0, dh0 = rec("bfx_d0", drums)
    d1, dh1 = rec("bfx_d1", drums + " ; ockm-bfx-drums-type 1 ; ockm-bfx-drums-on 1 ; ockm-bfx-drums-x 0.8 ; ockm-bfx-drums-y 0.8")
    assert abs(dh1 - dh0) > 3, f"crush should change the drums' top end: {dh0:.1f} to {dh1:.1f} dB"
    assert abs(d1 - d0) < 4, f"crush keeps the level about even: {d0:.1f} to {d1:.1f} dB"
    music = "ockm-drums-on 0 ; ockm-chord-verb 0 ; ockm-chord-delay 0 ; ockm-lead-verb 0 ; ockm-lead-delay 0"
    m0, mh0 = rec("bfx_m0", music)
    m1, mh1 = rec("bfx_m1", music + " ; ockm-bfx-music-type 0 ; ockm-bfx-music-on 1 ; ockm-bfx-music-x 0.15 ; ockm-bfx-music-y 0.3")
    assert mh1 < mh0 - 6, f"the low-pass should take the top off the music: {mh0:.1f} to {mh1:.1f} dB"
    m2, mh2 = rec("bfx_m2", music + " ; ockm-bfx-music-type 0 ; ockm-bfx-music-on 0 ; ockm-bfx-music-x 0.15")
    assert abs(m2 - m0) < 0.3 and abs(mh2 - mh0) < 0.3, "out, the effect leaves the bus alone"

@test
def gate_chops_the_music_in_time(work):
    """v1.49 the gate (bus effect 4, after PERF-1's): chords on the music bus, the gate in at 1/16 and full depth, go
    silent between the 16ths (compared window by window with the same chords ungated); at 1/8 the gaps are twice as long;
    the 3-3-2 pattern silences more than straight; at the bottom of the pad it does nothing."""
    try:
        import numpy as np
    except ImportError:
        raise Skip("numpy not installed")
    def rec(name, msgs):
        h = Harness(); h.record(os.path.join(work, name + ".wav"))
        h.at(100, "ockm-bpm 120 ; ockm-drums-on 0 ; ockm-bass-on 0 ; ockm-lead-on 0 ; ockm-chord-engine 3 ; ockm-chord-rhythm 9 ; ockm-chord-verb 0 ; ockm-chord-delay 0 ; "
             "ockm-delay-mix 0 ; ockm-verb-mix 0 ; ockm-chord-sidechain 0 ; " + msgs + " ; ockm-play 1")
        h.at(4000, "ockm-play 0"); f = os.path.join(work, name + ".pd"); h.finish(4100, f)
        r = subprocess.run([PD, "-nogui", "-nosound", "-nomidi", "-batch"] + (["-path", PDLUA, "-lib", "pdlua"] if PDLUA else []) +
                           ["-open", "OCKM_GENERATOR.pd", "-open", f], cwd=work, capture_output=True, text=True, timeout=300)
        assert "expr" not in r.stderr.lower() or "error" not in r.stderr.lower(), r.stderr[-800:]
        wv = wave.open(os.path.join(work, name + ".wav")); sr = wv.getframerate()
        x = np.frombuffer(wv.readframes(wv.getnframes()), np.int16).astype(float)[::wv.getnchannels()] / 32768
        x = x[int(1.0 * sr):int(3.8 * sr)]
        n = int(0.004 * sr); return np.sqrt((x[:len(x) // n * n].reshape(-1, n) ** 2).mean(1))
    w0 = rec("gate0", "ockm-bfx-music-on 0")
    loud = w0 > 0.2 * np.percentile(w0, 90)
    def cut(w):
        q = (w < 0.1 * w0) & loud
        runs, k = [], 0
        for v in q[loud]:
            if v: k += 1
            elif k: runs.append(k); k = 0
        return q.sum() / max(1, loud.sum()), (np.median(runs) if runs else 0)
    g = " ; ockm-bfx-music-type 4 ; ockm-bfx-music-on 1 ; ockm-bfx-music-y 1 ; ockm-bfx-music-glide 0"
    q16, r16 = cut(rec("gate16", g + " ; ockm-bfx-music-x 0.6"))
    q8, r8 = cut(rec("gate8", g + " ; ockm-bfx-music-x 0.3"))
    q332, _ = cut(rec("gate332", g + " ; ockm-bfx-music-x 0.6 ; ockm-bfx-music-gate-p 0.34"))
    qlo, _ = cut(rec("gatelo", g + " ; ockm-bfx-music-x 0.6 ; ockm-bfx-music-y 0"))
    assert loud.mean() > 0.3, f"the chords play ({loud.mean():.2f} of the time loud)"
    assert 0.25 < q16 < 0.65, f"1/16 at full depth: silent between the chops ({q16:.2f})"
    assert r8 > 1.6 * r16, f"1/8: longer gaps than 1/16 ({r8} against {r16} windows)"
    assert q332 > q16 + 0.15, f"3-3-2: more of the bar silent than straight ({q332:.2f} against {q16:.2f})"
    assert qlo < 0.05, f"the bottom of the pad: no gating ({qlo:.2f})"

@test
def gate_on_the_fx_screen(work):
    """v1.49 the gate on screen: a fifth effect button on each bus; on the pad it says its rate; its settings have four
    pattern buttons (3-3-2 sends a third)."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    L = ui_preview.run(["test tap 668 36", "test tap 300 306", "test press 760 300", "paint a", "test release 760 300", "test tap 254 352", "test tap 422 310"])
    assert "sent ockm-bfx-music-type float 4" in L, "the music bus's gate button"
    a = L[L.index("begin a"):L.index("end a")]
    assert any(l.endswith("in: 1/16") for l in a), "the pad says its rate while it plays"
    assert any(l.startswith("sent ockm-bfx-music-gate-p float 0.333") for l in L), [l for l in L if "gate-p" in l]

@test
def bass_follows_its_bus(work):
    """The fx page's bass goes with the drums (ockm-bass-bus 1) or with the music (0). A low-pass on the drums bus
    dulls the bass only while it's with the drums."""
    try:
        import numpy as np
    except ImportError:
        raise Skip("numpy not installed")
    def rec(name, bus):
        h = Harness(); h.record(os.path.join(work, name + ".wav"))
        # reese-ish analogue line, nothing else, no sends. The drums bus is a closed low-pass; the music bus is dry
        # donk, brightness up: it has harmonics for the drums' low-pass to take away
        h.at(100, "ockm-resync bang ; ockm-bpm 124 ; ockm-drums-on 0 ; ockm-lead-on 0 ; ockm-chord-on 0 ; "
                  "ockm-bass-on 1 ; ockm-bass-engine 6 ; ockm-bass-k1 0.9 ; "
                  "ockm-bass-sync 0 ; ockm-bass-notes 2 ; ockm-bass-rhythm 1 ; "
                  "ockm-bass-verb 0 ; ockm-bass-delay 0 ; ockm-bfx-drums-type 0 ; ockm-bfx-drums-on 1 ; "
                  "ockm-bfx-drums-x 0.08 ; ockm-bfx-drums-y 0.15 ; ockm-bfx-music-on 0 ; ockm-play 1")
        h.at(600, f"ockm-bass-bus {bus}")   # after the project has loaded, so its saved 1 doesn't win
        h.at(4000, "ockm-play 0"); f = os.path.join(work, name + ".pd"); h.finish(4100, f)
        subprocess.run([PD, "-nogui", "-nosound", "-nomidi", "-batch"] + (["-path", PDLUA, "-lib", "pdlua"] if PDLUA else []) +
                       ["-open", "OCKM_GENERATOR.pd", "-open", f], cwd=work, capture_output=True, text=True, timeout=300)
        wv = wave.open(os.path.join(work, name + ".wav")); sr = wv.getframerate()
        x = np.frombuffer(wv.readframes(wv.getnframes()), np.int16).astype(float)[::wv.getnchannels()] / 32768
        x = x[int(1.2 * sr):int(3.6 * sr)]
        X = np.abs(np.fft.rfft(x)) ** 2; fr = np.fft.rfftfreq(len(x), 1 / sr)
        tot = max(1e-12, X[fr > 20].sum())
        return 10 * np.log10((x ** 2).mean() + 1e-12), 10 * np.log10(X[fr > 300].sum() / tot + 1e-12)
    d_lvl, d_hi = rec("bassbus_drums", 1)
    m_lvl, m_hi = rec("bassbus_music", 0)
    assert d_lvl > -40 and m_lvl > -40, f"the bass should be audible either way: drums {d_lvl:.1f} dB, music {m_lvl:.1f} dB"
    assert m_hi > d_hi + 6, f"with music, the drums' low-pass should leave the bass: {d_hi:.1f} dB above 300 Hz with drums, {m_hi:.1f} with music"

@test
def bass_bus_buttons_send(work):
    """The fx page's with drums / with music buttons send ockm-bass-bus 1 and 0."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    L = ui_preview.run(["test tap 668 36", "test tap 275 562"])
    assert "sent ockm-bass-bus float 0" in L, [l for l in L if "bass-bus" in l]
    L = ui_preview.run(["test tap 668 36", "test tap 275 562", "test tap 160 562"])
    sent = [l for l in L if l.startswith("sent ockm-bass-bus")]
    assert sent == ["sent ockm-bass-bus float 0", "sent ockm-bass-bus float 1"], sent

@test
def drum_lane_screen_sends(work):
    """v1.49 the drums tab: rolls (tap a hit: a roll of 2, then 3 ...), and the lane panel's plays-in buttons."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    pre = ["test tap 301 36", "array ockm-pat-d1 0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1"]
    L = ui_preview.run(pre + ["test tap 196 282", "test tap 106 319", "test tap 106 319"])   # (the list starts at step 0: step 1 is the first hit)
    rat = [l for l in L if l.startswith("sent ockm-rat")]
    assert len(rat) >= 1 and rat[0].endswith(" 1 2"), rat
    L = ui_preview.run(pre + ["test tap 430 364", "test tap 160 512"])
    assert "sent ockm-d1-when float 1" in L, [l for l in L if "when" in l]

@test
def synth_presets_are_whole_sounds(work):
    """v1.49 on the Bass synth's page: random, then a preset: everything the preset doesn't set goes back to the synth's
    starting point first (nothing left over from random or your knobs), and the volume is left alone."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    L = ui_preview.run(["test tap 363 36", "test tap 866 350", "test tap 859 314", "send ib-noise float 0.7", "send ib-pdecay float 0.9",
                        "test tap 349 408", "mark here", "test tap 130 408"])
    after = L[next(i for i, l in enumerate(L) if l.startswith("mark")):]
    sent = [l for l in after if l.startswith("sent ib-")]
    assert "sent ib-noise float 0" in sent and "sent ib-pdecay float 0.15" in sent, f"leftovers reset: {sent[:12]}"
    assert not any(l.startswith("sent ib-level") for l in sent), "the volume is kept"
    assert "sent ib-resonance float 0.8" in sent, "then the preset (rubber acid)"

@test
def show_page_opens_from_the_menu(work):
    """v1.49 the show page: menu, show; the chord as a shape with its name; a tap anywhere goes back."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    L = ui_preview.run(["test tap 919 36", "test tap 830 245", "paint a", "test tap 300 300", "paint b"])
    a = L[L.index("begin a"):L.index("end a")]; b = L[L.index("begin b"):L.index("end b")]
    assert any("show: tap anywhere" in l for l in a), "the show page opened"
    assert any(l.startswith("text") and l.split()[-1].startswith("A") and "m" in l.split()[-1] for l in a), "the chord's name in the middle"
    assert not any("show: tap anywhere" in l for l in b), "a tap goes back"
    # the colours button steps through the four schemes (and doesn't go back)
    L = ui_preview.run(["test tap 919 36", "test tap 830 245", "test tap 880 36", "paint c", "test tap 880 36", "test tap 880 36", "test tap 880 36", "paint d"])
    c = L[L.index("begin c"):L.index("end c")]; d = L[L.index("begin d"):L.index("end d")]
    assert any("colours: neon" in l for l in c), "one tap: the second scheme"
    assert any("colours: dusk" in l for l in d), "four taps: round to the first again"
    # v1.49 the view button: the bloom (no circle-of-fifths text), then back to the circle
    L = ui_preview.run(["test tap 919 36", "test tap 830 245", "test tap 724 36", "paint e", "test tap 724 36", "paint f"])
    e = L[L.index("begin e"):L.index("end e")]; f = L[L.index("begin f"):L.index("end f")]
    assert any("view: bloom" in l for l in e) and not any("circle of fifths" in l for l in e), "the bloom"
    assert any("view: circle" in l for l in f) and any("circle of fifths" in l for l in f), "back to the circle"

@test
def answer_button_steps_through(work):
    """v1.49 call and answer on the bass and lead tabs: one button, each tap the next of off, 2, 4 and 8 bars."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    for part, tab in (("bass", 364), ("lead", 416)):
        L = ui_preview.run([f"test tap {tab} 36"] + ["test tap 472 283"] * 4)
        sent = [l.split()[-1] for l in L if l.startswith(f"sent ockm-{part}-answer")]
        assert sent == ["2", "4", "8", "0"], f"{part}: {sent}"

@test
def touchscreen_fx_pad_plays_and_latches(work):
    """v1.23: on the fx page a finger on the pad brings the bus's effect in at that spot and lifting takes it out;
    latched, it stays in. Macros can move a bus effect too."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    L = ui_preview.run(["test tap 668 36", "test press 400 100", "test release 400 100"])
    sent = [l for l in L if l.startswith("sent ockm-bfx-drums-")]
    # lifted, not latched: it springs back to the centre (v1.25; it goes out 60 ms later: checked in Pd, the next test)
    assert "sent ockm-bfx-drums-on float 1" in sent and sent[-2:] == ["sent ockm-bfx-drums-x float 0.5", "sent ockm-bfx-drums-y float 0.5"], sent
    x = [float(l.split()[3]) for l in sent if "-x " in l][0]
    assert x < 0.2, f"near the left edge: {x}"
    L = ui_preview.run(["test tap 668 36", "test tap 100 198", "test press 700 300", "test release 700 300"])
    sent = [l for l in L if l.startswith("sent ockm-bfx-drums-on")]
    assert sent == ["sent ockm-bfx-drums-on float 1"], f"latched: stays in after lifting: {sent}"
    # v1.49 unlatching: it goes out and the pad goes back to the centre
    L = ui_preview.run(["test tap 668 36", "test tap 100 198", "test press 700 300", "test release 700 300", "mark here", "test tap 100 198"])
    after = [l for l in L[next(i for i, l in enumerate(L) if l.startswith("mark")):] if l.startswith("sent ockm-bfx-drums-")]
    assert after == ["sent ockm-bfx-drums-x float 0.5", "sent ockm-bfx-drums-y float 0.5", "sent ockm-bfx-drums-on float 0"], f"unlatched: out, the pad centred: {after}"
    # the music bus, its filter picked
    L = ui_preview.run(["test tap 668 36", "test tap 100 262", "test press 900 500", "test release 900 500"])
    assert any(l.startswith("sent ockm-bfx-music-on float 1") for l in L), "the music bus is the pad's now"
    # a macro with a drums fx move (added in the editor: + add a move, then step the move round to drums fx), tried
    s = ["test tap 919 36", "test tap 830 195", "test tap 90 216", "test tap 90 272", "test tap 260 119", "send ockm-playing float 1",
         "test tap 600 390"] + ["test tap 490 394"] * 8 + ["test press 800 550"]
    L = ui_preview.run(s)
    assert "sent ockm-bfx-drums-on float 1" in L and "sent ockm-bfx-drums-type float 1" in L, [l for l in L if "bfx" in l]

@test
def arrange_plays_a_version(work):
    """v1.28: arrange. Two scenes (A and B) in a version, four bars each, a gap between (v1.29: with the drums out over
    it): it plays A, then B on the 1 of bar 5 with the mix dropped out for the beat before, then stops and puts back what
    was open."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-project-open", "ockm-unstash", "ockm-gap-arm", "ockm-bar", "ockm-d1-mute")
    tap = lambda ms, x, y: h.at(ms, f"ockm-ui-test tap {x} {y}")
    tap(150, 919, 36); tap(151, 830, 95)   # menu, project
    tap(200, 808, 100)                     # new blank project
    tap(700, 719, 36)                      # mixer
    tap(750, 54, 300); tap(770, 865, 36)   # scene A (its first save)
    tap(850, 54, 380); tap(870, 865, 36)   # scene B
    tap(950, 805, 36)                      # arrange
    tap(1000, 245, 566); tap(1010, 60, 357)   # + A (the second tile: newest first), 4 bars
    tap(1020, 90, 566); tap(1030, 60, 357)    # + B, 4 bars
    tap(1040, 60, 200); tap(1050, 550, 392)   # section 1, its transition: gap
    tap(1060, 668, 464)                       # v1.29: and drums out over it
    tap(1100, 778, 100)                    # play from start
    f = os.path.join(work, "t_arrange.pd"); h.finish(1100 + 17500, f)
    out = run(work, f, timeout=150)
    opens = [l.split()[-1] for l in out.splitlines() if l.startswith("ockm-project-open")]
    assert len(opens) >= 2 and opens[-2] != opens[-1] and opens[-1].endswith("-v2"), f"A, then B: {opens}"
    lines = out.splitlines()
    bars = [i for i, l in enumerate(lines) if l.startswith("ockm-bar")]
    ob = [i for i, l in enumerate(lines) if l.startswith("ockm-project-open") and l.endswith("-v2")][-1]
    nbar = sum(1 for i in bars if i < ob and i > [j for j, l in enumerate(lines) if l.startswith("ockm-project-open")][-2])
    assert nbar == 5, f"B comes in on bar 5: {nbar} bars before it"
    assert any(l.startswith("ockm-gap-arm") and l.split()[-1] == "4" for l in lines), "the gap is armed before the drop"
    assert any(l.startswith("ockm-unstash") for l in lines), "at the end, what was open comes back"
    mutes = [l.split()[-1] for l in lines[:ob] if l.startswith("ockm-d1-mute")]
    assert "1" in mutes, f"the drums go out over the transition: {mutes}"
    after = [l.split()[-1] for l in lines[ob:] if l.startswith("ockm-d1-mute")]
    assert not after or after[-1] == "0", f"and come back with scene B: {after}"

@test
def save_is_a_snapshot_not_movement(work):
    """v1.28: a save keeps everything in place: a mute, and a latched bus effect (crush on the drums). Not movement: a bus
    effect only held on the pad is saved as out."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness()
    tap = lambda ms, x, y: h.at(ms, f"ockm-ui-test tap {x} {y}")
    tap(150, 919, 36); tap(151, 830, 95)   # menu, project
    tap(200, 808, 100)                     # new blank project
    tap(700, 616, 36); tap(750, 70, 190)   # perform: mute the kick
    tap(800, 668, 36)                      # fx
    tap(850, 100, 198); tap(900, 700, 250) # drums: latch, then play it (crush): it stays in
    tap(950, 100, 262)                     # the music bus on the pad
    h.at(1000, "ockm-ui-test press 700 400")   # held (not latched) while saving
    tap(1100, 865, 36)                     # save
    f = os.path.join(work, "t_snapshot.pd"); h.finish(1400, f)
    run(work, f)
    P = os.path.join(work, "projects")
    made = [d for d in os.listdir(P) if re.match(r"\d{4}-", d)]
    assert made, os.listdir(P)
    txt = "".join(open(os.path.join(P, made[0], fn)).read() for fn in ("loop.txt", "project.txt"))
    kv = dict(re.findall(r"(ockm-[\w-]+) ([-\d.]+);", txt))
    assert kv.get("ockm-d1-mute") == "1", f"the kick's mute is saved: {kv.get('ockm-d1-mute')}"
    assert kv.get("ockm-bfx-drums-on") == "1", f"the latched crush is saved in: {kv.get('ockm-bfx-drums-on')}"
    assert kv.get("ockm-bfx-music-on") == "0", f"the held (not latched) filter is saved out: {kv.get('ockm-bfx-music-on')}"

@test
def midi_learn_maps_pads_and_knobs(work):
    """v1.30: MIDI learn (from the menu). v1.31: knobs pick up, a key on a fader plays it by velocity and lets go back.
    Tap rise on perform, hit pad 40: learned. Tap the bass's knob 1, move knob 21:
    learned. Done; then from the mixer, pad 40 turns rise on and knob 21 moves the bass's knob 1, wherever you are. The
    learning is kept in my-settings.lua."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-rise", "ockm-bass-k1", "ockm-delay-mix")
    tap = lambda ms, x, y: h.at(ms, f"ockm-ui-test tap {x} {y}")
    tap(100, 616, 36)                      # perform
    tap(150, 919, 36); tap(160, 830, 345)  # menu, MIDI learn (v1.49 a row lower: show is above it)
    tap(200, 540, 106)                     # rise
    h.at(250, "ockm-midi-note 40 100 ; ockm-midi-note 40 0")
    tap(300, 363, 36); tap(350, 600, 396)  # bass tab, its knob 1
    h.at(400, "ockm-midi-cc 64 21")
    tap(420, 616, 36); tap(430, 520, 406)  # v1.31: perform, the delay level (v1.49 40 higher: six slots)
    h.at(440, "ockm-midi-note 41 100 ; ockm-midi-note 41 0")
    tap(450, 896, 579)                     # done
    tap(500, 719, 36)                      # mixer
    h.at(600, "ockm-midi-note 40 100 ; ockm-midi-note 40 0")
    h.at(650, "ockm-midi-cc 127 21")      # v1.31 pick-up: the knob is far from the setting, so nothing happens yet
    h.at(700, "ockm-midi-cc 0 21 ; ockm-midi-cc 30 21 ; ockm-midi-cc 60 21 ; ockm-midi-cc 90 21 ; ockm-midi-cc 127 21")   # turned through it: it takes over
    h.at(750, "ockm-midi-note 41 64")      # key 41 on the delay: velocity sets it, about half
    h.at(780, "ockm-midi-note 41 0")       # let go: back
    f = os.path.join(work, "t_learn.pd"); h.finish(900, f)
    out = run(work, f)
    rise = [v.split()[-1] for v in printed(out, "ockm-rise")]
    assert rise and rise[-1] == "1", f"pad 40 turned rise on from the mixer: {rise}"
    k1 = [float(v.split()[-1]) for v in printed(out, "ockm-bass-k1")]
    assert k1 and abs(k1[-1] - 1) < 0.01, f"knob 21 turned through the setting and on to the top: the bass's knob 1 at 1: {k1}"
    assert 0.9 not in k1[:1] and len(k1) <= 5, f"it didn't jump before it picked up: {k1}"
    dl = [float(v.split()[-1]) for v in printed(out, "ockm-delay-mix")]
    assert any(abs(x - 0.5) < 0.05 for x in dl) and abs(dl[-1] - dl[0]) < 0.01, f"key 41: about half while held, then back: {dl}"
    me = open(os.path.join(work, "my-settings.lua")).read()
    assert '"note:40"' in me and '"cc:21"' in me, "learned controls are kept"

@test
def four_bar_rewind_spins_into_the_drop(work):
    """v1.49: slot A is the 4 bar rewind: drums out and the high-pass climbs to 0.5 over the 4 bars, then on the way out it
    arms a rewind of a beat (4 steps), which the patch spins on the bar's last beat and stops right on the drop."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    L = ui_preview.run(["send ockm-playing float 1", "test tap 566 500"] + ["send ockm-bar bang"] * 5)
    gl = [l for l in L if l.startswith("sent ockm-filter-glide ")]
    assert gl and abs(float(gl[0].split()[3]) - 0.5) < 1e-6, f"the high-pass up to 0.5: {gl}"
    ms = float(gl[0].split()[4]); assert 7000 < ms < 8500, f"over four bars at 124 bpm (about 7.7 s): {ms}"
    assert any(l.startswith("sent ockm-d1-mute-q ") and l.endswith(" 1") for l in L), "the drums go"
    assert any(l.startswith("sent ockm-rewind-arm ") and l.split()[3] == "4" for l in L), "a beat's rewind armed before the drop"
    # the patch: armed, it spins on step 12 of the bar for the 4 steps to the bar line
    h = Harness(); h.show("ockm-rewind-to")
    h.at(100, "ockm-bpm 120 ; ockm-rewind-arm 4"); h.at(200, "ockm-play 1"); h.at(2400, "ockm-play 0")
    f = os.path.join(work, "t_rw.pd"); h.finish(2500, f)
    out = run(work, f)
    got = printed(out, "ockm-rewind-to")
    assert len(got) == 1 and abs(float(got[0]) - (4 * 125 - 4)) < 1, f"one rewind, a beat long, just short of the bar line: {got}"

@test
def drum_grooves_fill_every_slot(work):
    """A groove lands on each slot by the sound it plays, makes the drums 1 bar (a groove's natural length) and sets the swing."""
    h = Harness(); h.show("ockm-drum-len")
    h.at(100, "ockm-resync bang ; ockm-length 32")
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
    rows = {n: [[round(float(x), 2) for x in v.split()] for v in printed(out, n)] for n in outs}
    kick = [2,0,0,0,1,0,0,0,2,0,0,0,1,0,0,0] * 2
    assert rows["D1"][0][:16] == kick[:16], f"slot 1 (kick) should get the tech house kick: {rows['D1'][0]}"
    assert printed(out, "ockm-drum-len")[-1] == "16", f"a groove makes the drums 1 bar: {printed(out, 'ockm-drum-len')}"
    og = [0.65, 0.35, 0, 1]   # v0.86: the hats breathe: soft, ghost, (open hat), hit
    assert rows["D4"][0][:16] == og * 4, f"slot 4 (hat) should get the hats, with ghost and soft notes: {rows['D4'][0]}"
    assert rows["D5"][0][:16] == [0,0,2,0,0,0,2,0,0,0,2,0,0,0,2,0], f"slot 5 (open hat) should get the open hats: {rows['D5'][0]}"
    assert "54" in [v.split()[0].split(".")[0] for v in printed(out, "SWING")], f"tech house should set swing 54: {printed(out, 'SWING')}"
    assert all(v == 0 for n in ("D1", "D4", "D5") for v in rows[n][1][:16]), "clear should empty every slot"

@test
def suggest_chords_fit_the_melody(work):
    """Song screen, fit the chords to my lead: scores every progression against your lead's notes and picks the best fit;
    a second tap gives the next one."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    def picks(notes):
        on = " ".join("1" if i % 4 == 0 else "0" for i in range(64))
        nt = " ".join(str(notes[(i // 4) % len(notes)]) for i in range(64))
        lines = ui_preview.run(["send ockm-length float 64", f"array ockm-pat-lead-on {on}", f"array ockm-pat-lead-note {nt}",
                                "send ockm-lead-mode float 1", "test tap 239 36", "test tap 324 402", "test tap 324 402"])
        return [int(float(l.split()[3])) for l in lines if l.startswith("sent ockm-chord-prog")]
    a_minor = picks([57, 60, 64])           # A C E: the home chord
    assert a_minor[0] == 0, f"a melody on A C E should suggest one chord first: {a_minor}"
    assert len(a_minor) == 2 and a_minor[1] != a_minor[0], f"a second tap should give the next suggestion: {a_minor}"
    # a melody that walks A minor, F, C, G one bar each: the pop progression (i VI III VII) should come first
    pop = picks([57, 60, 64, 57, 65, 69, 72, 65, 60, 64, 67, 60, 67, 71, 74, 67])
    assert ui_preview_shapes()[pop[0]] == [(0, 16), (5, 16), (2, 16), (6, 16)], f"expected the pop progression first: {pop}"
    empty = ui_preview.run(["test tap 239 36", "test tap 324 402"])
    assert not any(l.startswith("sent ockm-chord-prog") for l in empty), "no melody, no suggestion"

@test
def song_styles_set_the_lot(work):
    """Builder styles, house through to techno. Peak time sets 132 bpm, straight swing, the techno groove, F phrygian, a harder
    lower kick, the bass round the kick on the home note, and a lead. Deep house: 122, F dorian, Rhodes chords, no lead.
    v0.97: every tap rolls a fresh take from the style's own lists, and classic gives the first of each (the values checked
    here); shuffle rolls the lit style again. A kick on a kit sample goes back to the synth; one on your own sample keeps it."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    def sent(lines):
        out = {}
        for l in lines:
            if l.startswith("sent "):
                v = l.split()
                out[v[1]] = float(v[3]) if len(v) > 3 and v[3] not in ("bang",) else None
        return out
    PEAK, DEEP, SHUFFLE, CLASSIC = "test tap 584 174", "test tap 83 142", "test tap 896 142", "test tap 896 174"
    t = sent(ui_preview.run(["test tap 239 36", PEAK, CLASSIC]))
    assert t["ockm-bpm"] == 132 and t["ockm-swing"] == 50 and t["ockm-drum-groove"] == 5, t
    assert t["ockm-root"] == 5 and t["ockm-scale"] == 3, "F phrygian"
    assert t["ockm-d1-drive"] == 0.5 and t["ockm-d1-tune"] == -2, "the kick gets harder and lower"
    assert t["ockm-lead-on"] == 1 and t["ockm-bass-rhythm"] == 2 and t["ockm-bass-sync"] == 0 and t["ockm-chord-on"] == 1, t
    assert t["ockm-style"] == 13, t
    d = sent(ui_preview.run(["test tap 239 36", DEEP, CLASSIC]))
    assert d["ockm-bpm"] == 122 and d["ockm-scale"] == 2 and d["ockm-chord-engine"] == 4 and d["ockm-lead-on"] == 0, d
    lines = ui_preview.run(["test tap 239 36", DEEP] + [SHUFFLE] * 4)
    chunks, cur = [], []
    for l in lines:
        if l.startswith("sent "):
            cur.append(l)
            if l.startswith("sent ockm-style "): chunks.append(sent(cur)); cur = []
    seen = set()
    for sh in chunks:   # the tap, then four shuffles: every one a fresh take
        assert sh["ockm-style"] == 0 and sh["ockm-bpm"] == 122, "shuffle stays in deep house"
        assert sh["ockm-drum-groove"] in (2, 16, 17, 21) and sh["ockm-root"] in (5, 2, 7, 0) and sh["ockm-chord-prog"] in (13, 1, 3, 15, 6), sh
        assert sh["ockm-bass-seed"] >= 1, "a shuffled riff is a variation"
        seen.add((sh["ockm-root"], sh["ockm-chord-prog"], sh["ockm-drum-groove"], sh["ockm-bass-seed"]))
    assert len(chunks) == 5, f"four shuffles: {len(chunks)}"
    assert len(seen) > 1, "shuffle should come out differently"
    kit = ["send ockm-sample-counts list 31 6 0 0 0 0 0", "send ockm-sample-name list 0 31 kit-breaks", "send ockm-d1-sample float 31",
           "test tap 239 36", DEEP]
    k = sent(ui_preview.run(kit))
    assert k.get("ockm-d1-sample") == 0, "a kick on a kit goes back to the synth kick"
    own = sent(ui_preview.run(["send ockm-d1-sample float 2", "test tap 239 36", PEAK]))
    # every style's lists only point at presets that exist
    import re as _re
    src = open(os.path.join(ROOT, "ui", "ockm-ui.pd_lua")).read()
    sizes = {n: len(_re.findall(r"\{ \"", _re.search(r"^local " + n + r" = (.*)$", src, _re.M).group(1))) for n in ("RHYTHMS", "BASS_RHYTHMS", "CHORD_RHY", "PROGS")}
    sizes["GROOVES"] = len(_re.findall(r'"', _re.search(r"^local GROOVES = (.*)$", src, _re.M).group(1))) // 2
    sizes["MONO_NOTES"] = len(_re.findall(r'"', _re.search(r"^local MONO_NOTES = (.*)$", src, _re.M).group(1))) // 2
    block = src[src.index("local STYLES = {"):src.index("\n}\n", src.index("local STYLES = {"))]
    def ints(v): return [int(x) for x in _re.findall(r"-?\d+", v)]
    bad = []
    for key, table in (("groove", "GROOVES"), ("prog", "PROGS")):
        for m in _re.finditer(r"\b" + key + r"=(\{[^}]*\}|\d+)", block):
            bad += [(key, i) for i in ints(m.group(1)) if not 0 <= i < sizes[table]]
    for part, table in (("bass", "BASS_RHYTHMS"), ("chord", "CHORD_RHY"), ("lead", "RHYTHMS")):
        for m in _re.finditer(part + r"=\{ engine=[^\n]*?rhythm=(\{[^}]*\}|\d+)", block):
            bad += [(part, i) for i in ints(m.group(1)) if not 0 <= i < sizes[table]]
    for m in _re.finditer(r"notes=(\{[^}]*\}|\d+)", block):
        bad += [("notes", i) for i in ints(m.group(1)) if not 0 <= i < sizes["MONO_NOTES"]]
    assert not bad, f"styles point at presets that don't exist: {bad}"
    assert "ockm-d1-drive" not in own and own.get("ockm-d1-sample") != 0, "a kick on your own sample keeps it"

@test
def phrase_sets_the_fill_and_turnaround(work):
    """The phrase on the builder drives both end-of-phrase moves. From off, picking a fill style on the drums tab brings the
    phrase in at 8 bars; no fill switches just the fill off; the turnaround comes on at the same length."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    def sends(lines, key):
        return [float(l.split()[3]) for l in lines if l.startswith("sent " + key + " ")]
    L = ui_preview.run(["send ockm-fill-every float 0", "send ockm-turn-every float 0",
                        "test tap 301 36", "test tap 900 569",       # drums tab: breakbeat fill
                        "test tap 239 36", "test tap 810 406",       # builder: turnaround on
                        "test tap 301 36", "test tap 600 529"])      # drums tab: no fill
    assert sends(L, "ockm-fill-style")[-1:] == [4], "breakbeat picked"
    assert sends(L, "ockm-fill-every")[-2:] == [8, 0], f"the fill every 8, then off: {sends(L, 'ockm-fill-every')}"
    assert sends(L, "ockm-turn-every")[-1:] == [8], f"the turnaround on the same 8-bar phrase: {sends(L, 'ockm-turn-every')}"

@test
def drums_tab_swipes_to_all_drums(work):
    """Drums tab: swipe left across the drum slots for all drums (a tap on the snare lane edits d2), swipe right across the
    names to come back to one drum (a tap on the step row edits the selected drum, d1)."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    L = ui_preview.run(["test tap 301 36", "test drag 600 134 200 134",      # swipe left across the slots
                        "test tap 259 165",                                   # all drums: snare lane, step 2
                        "test drag 40 200 300 200",                           # swipe right across the names
                        "test tap 45 212"])                                   # one drum: step 1 of the kick
    edits = [l.split()[2:] for l in L if l.startswith("sent ockm-edit ")]   # "sent ockm-edit d2 1 1": the drum, the step, the value
    assert edits and edits[0][:2] == ["d2", "1"], f"all drums: the snare lane, step 2: {edits}"
    assert any(e[:2] == ["d1", "0"] for e in edits[1:]), f"back on one drum: the kick's step 1: {edits}"

@test
def perform_rewind_taps_and_repeat_holds(work):
    """v1.17: Perform's rewind (where pump was) is a tap; repeat (where throw was) is held: 1 while held, 0 on release."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    L = ui_preview.run(["test press 660 106", "test release 660 106", "test press 886 106", "test release 886 106"])
    assert len([l for l in L if l.startswith("sent ockm-rewind")]) == 1, f"one tap, one rewind: {[l for l in L if 'rewind' in l]}"
    rp = [float(l.split()[3]) for l in L if l.startswith("sent ockm-repeat ")]
    assert rp == [1, 0], f"repeat held then let go: {rp}"

@test
def breakdown_recipe_runs_for_bars_or_while_held(work):
    """v0.93 performance recipe (breakdown, slot C): drums out with the filter down and reverb and delay up. A tap runs it
    for 4 bars: its mutes wait for the bar, they're asked back at the start of bar 4 so they land on the 1 of bar 5, and the
    effects come back on that same 1. A hold lasts while held: let go and it all comes back on the next bar."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    def sent(lines, hook): return [l for l in lines if l.startswith("sent " + hook + " ")]
    BAR = "send ockm-bar bang"
    steps = [f"send ockm-step float {i}" for i in (1, 2)]
    L = ui_preview.run(["send ockm-playing float 1", "test press 865 500"] + steps + ["test release 865 500", "mark tapped", BAR, BAR, BAR, "mark bar3",
                        BAR, "mark bar4", BAR, "mark bar5"])
    def upto(mark): return L[:L.index("mark " + mark)] if ("mark " + mark) in L else L
    assert sent(L, "ockm-mute-bar")[:1] == ["sent ockm-mute-bar float 1"], f"its mutes should wait for the bar: {sent(L, 'ockm-mute-bar')}"
    kick_out = [l for l in upto("tapped") if l.startswith("sent ockm-d1-mute-q ")]
    assert kick_out and kick_out[-1].endswith(" 1"), f"the kick should go: {kick_out}"
    assert not [l for l in upto("bar3") if l.startswith("sent ockm-d1-mute-q ") and l.endswith(" 0")], "a tap: drums stay out for the bars"
    back = [l for l in upto("bar4") if l.startswith("sent ockm-d1-mute-q ") and l.endswith(" 0")]
    assert back, "at the start of bar 4 the drums are asked back (to land on the 1 of bar 5)"
    b4 = L.index("mark bar4"); b5 = L.index("mark bar5")
    assert "sent ockm-mute-bar float 0" in L[b4:b5], f"the effects come back with the drums, on the 1: {L[b4:b5]}"
    # hold: let go after a beat and a bit, and it drops on the next bar
    steps = [f"send ockm-step float {i}" for i in range(1, 7)]
    H = ui_preview.run(["send ockm-playing float 1", "test press 865 500"] + steps + ["test release 865 500", "mark let-go", BAR, "mark bar1"])
    lg = H.index("mark let-go")
    assert [l for l in H[:lg] if l.startswith("sent ockm-d1-mute-q ") and l.endswith(" 0")], "a hold: let go and the drums are asked back"
    assert "sent ockm-mute-bar float 0" in H[lg:H.index("mark bar1")], "and the rest lands with them on the next bar"

@test
def midi_pads_and_knobs(work):
    """A MIDI controller (v0.95, v0.96). Pads read like the screen, top row first. As notes: 40 (bank A, top left) mutes the
    kick and again brings it back; 49 (bank B, top row, second) holds macro slot B while held; 51 (top right) is pump, 1
    while held. In program change mode (the MPK mini's PROG CHANGE): program 4 (top left) toggles the kick too; program 13
    (bank B, slot B) taps lift, which runs its bars; program 15 (bank B top right, pump) toggles. Knob CC 70 sweeps the
    filter (64, the middle, is off), CC 74 sets k1 of the synth on screen, CC 1 works too. Keys outside the pads do nothing."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    N = lambda n, v: f"send ockm-midi-note list {n} {v} 10"
    C = lambda cc, v: f"send ockm-midi-cc list {v} {cc} 1"
    P = lambda pg: f"send ockm-midi-pgm list {pg} 10"
    L = ui_preview.run([N(40, 100), N(40, 0), "send ockm-d1-mute float 1", N(40, 100), N(49, 100), "mark held", N(49, 0), "mark up", N(51, 90), N(51, 0),
                        C(70, 0), C(70, 64), C(70, 127), "test tap 425 36", C(74, 127), C(1, 127), "mark keys", N(60, 100), N(60, 0), "mark pgm",
                        "send ockm-d1-mute float 0", "send ockm-playing float 1", P(4), P(13), "mark tapped", P(15), P(15)])
    kick = [l.split()[3] for l in L[:L.index("mark keys")] if l.startswith("sent ockm-d1-mute-q ")]
    assert kick[:2] == ["1", "0"], f"the top-left pad toggles the kick: {kick}"
    held = L.index("mark held")
    assert any(l.startswith("sent ockm-filter-glide ") for l in L[:held]), "slot B (lift) moves the filter while held"
    rw = [l for l in L[:L.index("mark keys")] if l.startswith("sent ockm-rewind")]
    assert len(rw) == 1, f"the top-right pad of bank B rewinds (v1.17, where pump was): {rw}"
    fl = [float(l.split()[3]) for l in L if l.startswith("sent ockm-filter ")]
    assert fl[:3] == [-1, 0, 1], f"knob 1 is the filter, off in the middle: {fl}"
    assert [float(l.split()[3]) for l in L if l.startswith("sent ockm-lead-k1 ")][-1:] == [1], "knob 5 is k1 of the synth on screen (the lead tab)"
    assert not [l for l in L[L.index("mark keys"):L.index("mark pgm")] if l.startswith("sent ") and not l.startswith("sent ockm-midi-")], "keys do nothing"
    pg = L[L.index("mark pgm"):]
    assert any(l.startswith("sent ockm-d1-mute-q ") and l.endswith(" 1") for l in pg), "program 4 (top left) toggles the kick"
    assert any(l.startswith("sent ockm-filter-glide ") for l in pg[:pg.index("mark tapped")]), "program 13 taps lift"
    assert len([l for l in pg if l.startswith("sent ockm-rewind")]) == 2, "program 15 rewinds, each time"

@test
def retired_engines_move_on_and_engines_load_their_sweet_spot(work):
    """v0.98: a project saved on a retired engine moves to its replacement, set to sound like the old one: bass pluck (4)
    to analogue with a long decay; lead juno (1) to analogue with the chorus; chord strings (5) to poly with a slow attack
    and chorus I+II. Picking an engine on its tab loads that engine's own knob settings."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    L = ui_preview.run(["send ockm-bass-engine float 4", "mark bass", "send ockm-lead-engine float 1", "mark lead",
                        "send ockm-chord-engine float 5", "mark chord", "test tap 363 36", "mark tab"])
    def after(mark, until=None):
        i = L.index("mark " + mark); j = L.index("mark " + until) if until else len(L)
        return {l.split()[1]: float(l.split()[3]) for l in L[i:j] if l.startswith("sent ") and len(l.split()) > 3}
    def before(mark, start=None):
        i = L.index("mark " + start) if start else 0; j = L.index("mark " + mark)
        return {l.split()[1]: float(l.split()[3]) for l in L[i:j] if l.startswith("sent ") and len(l.split()) > 3}
    b = before("bass")
    assert b.get("ockm-bass-engine") == 5 and b.get("ockm-bass-k4") == 0.7, f"pluck becomes analogue with a long decay: {b}"
    l = before("lead", "bass")
    assert l.get("ockm-lead-engine") == 4 and l.get("ockm-lead-chorus") == 2, f"juno becomes analogue with the chorus (on): {l}"
    c = before("chord", "lead")
    assert c.get("ockm-chord-engine") == 0 and c.get("ockm-chord-k3") == 0.7 and c.get("ockm-chord-chorus") == 2, f"strings become poly: {c}"
    # the bass tab's engine row: analogue, acid, sub 808, wide, fm, donk. Tap acid (the second)
    lines = ui_preview.run(["test tap 363 36", "paint tab"])
    import re as _re
    shot = [l for l in lines if l.startswith("text ")]
    names = [" ".join(l.split()[4:]) for l in shot]
    for nm in ("analogue", "acid", "sub 808", "wide", "fm", "donk"):
        assert nm in names, f"the bass tab should offer {nm}: {[n for n in names if n in ('pluck', 'reese')]}"
    assert "pluck" not in names and "reese" not in names, "pluck is retired; reese shows as wide"

@test
def evolve_moves_one_part_a_phrase_and_comes_home(work):
    """v1.00 evolve, gentle, on deep house (phrase 8 bars). From play, phrases start at bars 9, 17, 25, 33, 41. One part moves
    each phrase, in turn: the bass to its next variation (seed + 1), then the lead, then the chords (the next of the style's
    chord rhythms), then the drums (the next of its grooves); then the bass again, which comes home (gentle: A B A C...)."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    BAR = "send ockm-bar bang"
    script = ["test tap 239 36", "test tap 83 142", "send ockm-lead-on float 1", "test tap 190 438", "send ockm-playing float 1", "mark start"]
    for b in range(1, 42):
        script += [BAR, f"mark bar{b}"]
    L = ui_preview.run(script)
    def sent_between(a, b, hook):
        i, j = L.index("mark " + a), L.index("mark " + b)
        return [float(l.split()[3]) for l in L[i:j] if l.startswith("sent " + hook + " ")]
    def last_before(mark, hook):
        v = [float(l.split()[3]) for l in L[:L.index("mark " + mark)] if l.startswith("sent " + hook + " ")]
        return v[-1] if v else None
    seed0 = last_before("start", "ockm-bass-seed"); lead0 = last_before("start", "ockm-lead-seed") or 0   # deep house has no lead: we switch it on
    rhy0 = last_before("start", "ockm-chord-rhythm"); gr0 = last_before("start", "ockm-drum-groove")
    assert "sent ockm-evolve-every float 8" in L and last_before("start", "ockm-evolve-mode") == 1, "gentle, on an 8-bar phrase"
    assert not [l for l in L[L.index("mark start"):L.index("mark bar8")] if l.startswith("sent ockm-") and "seed" in l], "nothing moves in the first phrase"
    assert sent_between("bar8", "bar9", "ockm-bass-seed") == [seed0 + 1], "phrase 2: the bass moves to its next variation"
    assert sent_between("bar16", "bar17", "ockm-lead-seed") == [lead0 + 1], "phrase 3: the lead"
    r = sent_between("bar24", "bar25", "ockm-chord-rhythm")
    assert len(r) == 1 and r[0] != rhy0, f"phrase 4: the chords move to another of the style's rhythms: {r} (was {rhy0})"
    g = sent_between("bar32", "bar33", "ockm-drum-groove")
    assert len(g) == 1 and g[0] != gr0, f"phrase 5: the drums move to another of the style's grooves: {g} (was {gr0})"
    assert sent_between("bar40", "bar41", "ockm-bass-seed") == [seed0], "phrase 6: the bass comes home"

@test
def refit_my_line_when_the_harmony_moves(work):
    """A lead that's yours, all on A over A minor. The harmony changes to E minor under it: the lead tab says the notes no
    longer fit, and refit moves each one to the nearest chord note (G), keeping the rhythm."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    on = " ".join("1" if i % 4 == 0 else "0" for i in range(64))
    nt = " ".join("57" for i in range(64))
    lines = ui_preview.run(["send ockm-lead-len float 64", "send ockm-chord-len float 64", f"array ockm-pat-lead-on {on}", f"array ockm-pat-lead-note {nt}",
                            "array ockm-pat-chord-deg " + " ".join("0" for _ in range(64)), "send ockm-lead-mode float 1",
                            "test tap 425 36", "test tap 5 595",                     # lead tab: remembers the harmony it was written over
                            "array ockm-pat-chord-deg " + " ".join("4" for _ in range(64)), "send ockm-chord-prog float 5",
                            "test tap 425 36", "test tap 395 283"])                  # the harmony moved: refit my line
    edits = [l.split()[3:] for l in lines if l.startswith("sent ockm-lead-edit")]
    assert len(edits) == 16, f"every note on the beat should be refitted: {len(edits)} {edits[:2]}"
    assert all(int(float(e[1])) == 55 for e in edits), f"A moves to G, the nearest note of E minor: {edits[:3]}"

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
    h.at(200, "ockm-ui-test tap 301 36")              # drums tab
    h.at(300, "ockm-ui-test drag 45 336 45 302")      # velocity: drag step 1 to the top (accent)
    h.at(400, "ockm-ui-test tap 145 282")             # timing
    h.at(500, "ockm-ui-test drag 45 319 45 336")      # pull step 1 early
    h.at(600, "ockm-ui-test tap 612 88")              # drum length: 1 bar (navigation strip)
    h.at(700, "ockm-ui-test tap 909 88")              # double
    h.at(800, "ockm-ui-test tap 900 354")             # bank 2 (techno)
    h.at(900, "ockm-ui-test tap 531 389")             # its first groove
    f = os.path.join(work, "t_lane_ui.pd"); h.finish(1000, f)
    out = run(work, f)
    edits = [e for e in printed(out, "ockm-edit") if e.startswith("d1 0")]
    assert edits and edits[-1].split()[-1] == "2", f"dragging to the top should make it an accent: {edits}"
    nud = [float(e.split()[-1]) for e in printed(out, "ockm-nudge") if e.startswith("d1 0")]
    assert nud and nud[-1] < -0.2, f"dragging down should pull it early: {nud}"
    loops = [int(float(v)) for v in printed(out, "ockm-drum-len")]
    assert 32 in loops and loops[-1] == 16, f"double should give 2 bars, then the groove makes the drums 1 bar again: {loops}"
    assert printed(out, "ockm-drum-groove")[-1:] == ["3"], f"bank 2's first groove is number 3: {printed(out, 'ockm-drum-groove')}"

@test
def touchscreen_exports_audio_stems_and_midi(work):
    """Project screen, export: the loop once, with the mix, stems and MIDI. The WAVs have sound in them,
    and the MIDI file is a proper type 1 file with drums on channel 10 and notes for each part."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness()
    h.at(100, "ockm-bass-gen bang ; ockm-chord-gen bang ; ockm-bpm 160")
    h.at(300, "ockm-ui-test tap 919 36 ; ockm-ui-test tap 830 95")      # project
    h.at(400, "ockm-ui-test tap 902 100")     # export...
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
    assert len(wavs) == 7, f"expected the mix and 6 stems: {files}"
    mix = [n for n in wavs if not any(n.endswith(f"-{s}.wav") for s in ["drums", "bass", "lead", "chord", "vox", "fx"])][0]
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
    h.at(300, "ockm-ui-test tap 919 36 ; ockm-ui-test tap 830 95"); h.at(400, "ockm-ui-test tap 902 100")   # project, export...
    h.at(500, "ockm-ui-test tap 224 162")     # the loop plays once
    h.at(600, "ockm-ui-test tap 644 544")     # export (stereo mix)
    h.at(8000, "ockm-ui-test tap 919 36 ; ockm-ui-test tap 830 95"); h.at(8100, "ockm-ui-test tap 902 100")
    h.at(8200, "ockm-ui-test tap 154 544")    # record what I play
    h.at(8300, "ockm-play 1")
    h.at(9800, "ockm-ui-test tap 815 36")     # stop recording
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
def drum_slot_lab_sounds_randomise_and_character(work):
    """A slot plays the drum lab's sounds: the kick, then the perc slot's rim, conga and shaker (ockm-<slot>-synth 0, 1, 2),
    each different. Randomise (a seed and an amount) changes the sound and the same seed gives it back; character and
    morph change it too; tone darkens or brightens it and drive makes it denser."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.record(os.path.join(work, "lab.wav"))
    others = " ; ".join(f"ockm-{t}-mute 1" for t in ["d2","d3","d4","d5","d6","d7","d8","bass","lead","chord"])
    h.at(100, f"ockm-verb-mix 0 ; ockm-delay-mix 0 ; ockm-d1-sound 0 ; ockm-d1-sample 0 ; ockm-d1-verb 0 ; ockm-d1-delay 0 ; ockm-d1-synth 0 ; {others}")
    steps = [
        "ockm-d1-sound 0",                                                         # 0 kick
        "ockm-d1-sound 3 ; ockm-d1-synth 0",                                       # 1 rim
        "ockm-d1-synth 1",                                                         # 2 conga
        "ockm-d1-synth 2",                                                         # 3 shaker
        "ockm-d1-sound 0 ; ockm-d1-synth 0 ; ockm-d1-labrseed 77 ; ockm-d1-labramt 1",   # 4 kick, randomised
        "ockm-d1-labrseed 0 ; ockm-d1-labramt 0",                                  # 5 kick again (back to the start)
        "ockm-d1-labrseed 77 ; ockm-d1-labramt 1",                                 # 6 the same randomise again
        "ockm-d1-labrseed 0 ; ockm-d1-labramt 0 ; ockm-d1-labchar 1",              # 7 character up
        "ockm-d1-labchar 0 ; ockm-d1-labmorph 0.7 ; ockm-d1-labpseed 3",           # 8 morph
        "ockm-d1-labmorph 0 ; ockm-d1-tone -0.8",                                  # 9 darker
        "ockm-d1-tone 0.8",                                                        # 10 brighter
        "ockm-d1-tone 0 ; ockm-d1-drive 1",                                        # 11 driven
    ]
    for i, m in enumerate(steps):
        t0 = 300 + i * 1600
        h.at(t0, m)
        h.at(t0 + 100, "ockm-d1-audition 1")
    n = len(steps)
    out, (x, sr) = play(work, h, "t_lab", ms=300 + n * 1600 + 200)
    segs = [x[int((0.4 + i * 1.6) * sr):int((0.4 + i * 1.6 + 0.7) * sr)] for i in range(n)]
    pk = [peak(sg) for sg in segs]
    assert min(pk) > 0.03, f"every version should sound: {[round(p, 3) for p in pk]}"
    def env(sg, k=1024):     # loudness in windows longer than a low drum's cycle, so the oscillator's start point doesn't matter
        return [math.sqrt(sum(v * v for v in sg[j:j + k]) / k) for j in range(0, len(sg) - k, k)]
    def diff(a, b):
        ea, eb = env(a), env(b)
        return sum(abs(p - q) for p, q in zip(ea, eb)) / (sum(ea) + sum(eb) + 1e-9)
    def bright(sg): return sum(abs(sg[i] - sg[i - 1]) for i in range(1, len(sg))) / (sum(abs(v) for v in sg) + 1e-9)
    b4 = [bright(sg) for sg in segs[:4]]
    for i in range(4):
        for j in range(i + 1, 4):
            assert diff(segs[i], segs[j]) > 0.1 or abs(b4[i] - b4[j]) > 0.1 * max(b4[i], b4[j]), f"sounds {i} and {j} should differ"
    assert diff(segs[4], segs[5]) > 0.08 or abs(bright(segs[4]) - bright(segs[5])) > 0.05 * bright(segs[5]), "randomise should change the kick"
    assert diff(segs[4], segs[6]) < 0.045, f"the same seed should give the same sound ({diff(segs[4], segs[6]):.3f})"
    assert diff(segs[7], segs[5]) > 0.05 or abs(bright(segs[7]) - bright(segs[5])) > 0.05 * bright(segs[5]), "character should change the kick"
    assert diff(segs[8], segs[5]) > 0.05 or abs(bright(segs[8]) - bright(segs[5])) > 0.05 * bright(segs[5]), "morph should change the kick"
    assert bright(segs[9]) < bright(segs[5]) < bright(segs[10]), f"tone should darken then brighten: {bright(segs[9]):.3f} {bright(segs[5]):.3f} {bright(segs[10]):.3f}"
    rms = lambda sg: math.sqrt(sum(v * v for v in sg) / len(sg))
    crest = lambda sg: max(abs(v) for v in sg) / (rms(sg) + 1e-9)
    # v1.14: drive keeps the loudness, so denser means a lower crest factor: the quiet parts pushed up towards the peaks
    assert crest(segs[11]) < crest(segs[5]) * 0.9, f"drive should make it denser: crest {crest(segs[11]):.2f} vs {crest(segs[5]):.2f}"

@test
def touchscreen_demud_listens_and_cuts(work):
    """Mixer, while the demo groove plays: de-mud listens for 4 seconds, then sets low cuts from what it heard.
    The hats get a real low cut; the kick and bass are left alone."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-d1-lowcut", "ockm-d4-lowcut", "ockm-bass-lowcut", "ockm-spec-all")
    h.at(100, "ockm-bass-gen bang ; ockm-chord-gen bang ; ockm-play 1")
    h.at(600, "ockm-ui-test tap 719 36")      # mixer
    h.at(700, "ockm-ui-test tap 908 232")     # de-mud (master strip)
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
    h.at(500, "ockm-ui-test tap 719 36")      # mixer
    h.at(550, "ockm-ui-test tap 908 232")     # de-mud while stopped: fixed low cuts, with an undo button
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
def touchscreen_steps_act_on_press(work):
    """A drum step changes the moment a finger lands (before it lifts), like a drum machine pad.
    Pressing a step and swiping sideways puts the step back and turns the page instead."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-edit", "ockm-page")
    h.at(50, "ockm-length 32")                        # 2 bars, so there's a second page to swipe to
    h.at(100, "ockm-ui-test tap 301 36")              # drums
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
def a_following_lead_is_at_least_four_bars(work):
    """v1.49 a one-chord progression is one bar: a bass that follows it loops that bar, but the lead stays 4 bars.
    A length set by hand still goes to every part that follows."""
    h = Harness(); h.show("ockm-bass-len", "ockm-lead-len")
    h.at(100, "ockm-bass-sync 1 ; ockm-lead-sync 1 ; ockm-bass-len 64 ; ockm-lead-len 64 ; ockm-chord-mode 0")
    h.at(200, "ockm-resync bang ; ockm-chord-rhythm 0 ; ockm-chord-prog 4")   # a 2-bar progression: the chords fit themselves to 2 bars
    h.at(300, "ockm-chord-len 128")     # a length set by hand: both follow
    f = os.path.join(work, "t_lead_four.pd"); h.finish(500, f)
    out = run(work, f)
    bl, ll = printed(out, "ockm-bass-len"), printed(out, "ockm-lead-len")
    assert "32" in bl, f"the bass follows a 2-bar progression: {bl}"
    assert "16" not in ll and "32" not in ll, f"the lead stays 4 bars: {ll}"
    assert ll[-1] == "128", f"the lead still follows longer chords: {ll}"

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
    h.at(100, "ockm-ui-test tap 363 36")              # bass tab
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
def sample_library_names_the_files(work):
    """The sample library reports each file's name with its number, so a style can find a kit (kit-<name>) in each folder."""
    kd, sd = os.path.join(work, "samples", "kick"), os.path.join(work, "samples", "snare")
    write_tone(os.path.join(kd, "01.wav"), 110, 0.1); write_tone(os.path.join(kd, "kit-breaks.wav"), 110, 0.1)
    write_tone(os.path.join(sd, "kit-boom.wav"), 300, 0.1)
    h = Harness(); h.show("ockm-sample-name"); h.at(100, "ockm-samples-scan bang")
    f = os.path.join(work, "t_names.pd"); h.finish(400, f)
    names = printed(run(work, f), "ockm-sample-name")
    assert "0 2 kit-breaks" in names and "1 1 kit-boom" in names, f"kick 2 and snare 1 named: {names}"

@test
def touchscreen_picks_samples_and_kits(work):
    """Drums tab: arrows step through the folder (and stop at the end), and the box plays it."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    kd = os.path.join(work, "samples", "kick")
    write_tone(os.path.join(kd, "01.wav"), 110, 0.2); write_tone(os.path.join(kd, "02.wav"), 220, 0.2)
    h = Harness(); h.show("ockm-d1-sample", "ockm-d1-audition")
    h.at(100, "ockm-ui-test tap 301 36")      # drums tab: counts the folders
    for t_ in (250, 300, 350): h.at(t_, "ockm-ui-test tap 264 364")   # v1.49 past the synth kits: 808, 909, 909 long
    h.at(400, "ockm-ui-test tap 264 364")     # the synth kick -> sample 1
    h.at(500, "ockm-ui-test tap 264 364")     # 2
    h.at(700, "ockm-ui-test tap 264 364")     # only 2 kicks: stays put
    h.at(900, "ockm-ui-test tap 200 364")     # tap the box: hear it
    f = os.path.join(work, "t_samples_ui.pd"); h.finish(1300, f)
    out = run(work, f)
    d1 = [int(float(v)) for v in printed(out, "ockm-d1-sample")]
    picked = [v for v in d1 if v > 0]
    assert picked == [1, 2], f"sample steps wrong: {d1}"
    assert len(printed(out, "ockm-d1-audition")) >= 3, f"should play on each change and on tapping the box: {printed(out, 'ockm-d1-audition')}"

@test
def touchscreen_saves_drum_sounds(work):
    """Drums tab: the save icon keeps the kick's synth sound as one of your sounds ("kick 1"). Change the sound and
    the arrows bring it back; on a saved sound the icon deletes it. Random and wild put morph back to 0."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-d1-labrseed", "ockm-d1-labmorph", "ockm-d1-tune")
    h.at(100, "ockm-ui-test tap 301 36 ; ockm-d1-sample 0 ; ockm-d1-labrseed 4242 ; ockm-d1-labramt 0.35 ; ockm-d1-tune 3")
    h.at(300, "ockm-ui-test tap 314 364")     # save: kick 1
    h.at(400, "ockm-d1-labrseed 0 ; ockm-d1-labramt 0 ; ockm-d1-tune 0")
    for t_ in (440, 460, 480): h.at(t_, "ockm-ui-test tap 264 364")   # v1.49 past the synth kits: 808, 909, 909 long
    h.at(500, "ockm-ui-test tap 264 364")     # arrow right: kick 1
    h.at(600, "ockm-ui-test dump")
    h.at(700, "ockm-ui-test tap 314 364")     # on kick 1 the icon is delete
    h.at(800, "ockm-ui-test dump")
    h.at(900, "ockm-d1-labmorph 0.6")
    h.at(1000, "ockm-ui-test tap 301 403")    # random: morph goes back to 0
    f = os.path.join(work, "t_save_sound.pd"); h.finish(1200, f)
    out = run(work, f)
    seeds = [int(float(v)) for v in printed(out, "ockm-d1-labrseed")]
    assert 4242 in seeds[2:], f"the arrow should bring the saved sound back: {seeds}"
    assert printed(out, "ockm-d1-tune")[-1] in ("3", "3.0"), "with its tune"
    assert "box mine kick 1" in out, "the box should show the saved sound's name"
    assert out.count("box mine kick 1") == 1, "delete should remove it"
    assert float(printed(out, "ockm-d1-labmorph")[-1]) == 0, "random puts morph back to 0"

@test
def touchscreen_drum_synth_random_and_reset(work):
    """Drums tab, the kick's synth sound: new sound gives it a new seed (near the last sound), again a different one, and
    reset puts it back to the lab's starting sound. (v1.03: random is called new sound; wild is gone)"""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-d1-labrseed", "ockm-d1-labramt", "ockm-d1-labchar")
    h.at(100, "ockm-ui-test tap 301 36 ; ockm-d1-sample 0 ; ockm-d1-labchar 0.5")
    h.at(300, "ockm-ui-test tap 316 403")     # new sound
    h.at(500, "ockm-ui-test tap 316 403")     # and another
    h.at(700, "ockm-ui-test tap 420 403")     # reset
    f = os.path.join(work, "t_labui.pd"); h.finish(900, f)
    out = run(work, f)
    seeds = [int(float(v)) for v in printed(out, "ockm-d1-labrseed")]
    amts = [float(v) for v in printed(out, "ockm-d1-labramt")]
    assert len(seeds) >= 3 and seeds[-3] > 0 and seeds[-2] > 0 and seeds[-3] != seeds[-2] and seeds[-1] == 0, f"new sound twice, then reset: {seeds}"
    assert amts[-3:] == [0.35, 0.35, 0.0], f"how far each goes: {amts}"
    assert float(printed(out, "ockm-d1-labchar")[-1]) == 0, "reset puts the character back"

@test
def touchscreen_drum_slider_previews_when_stopped(work):
    """Drums tab, stopped: dragging a slider plays the sound (while dragging and on letting go), with no message.
    While playing it doesn't. A slot playing a sample greys out character, morph, random, wild and reset."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-d1-audition", "ockm-d1-labrseed")
    h.at(100, "ockm-ui-test tap 301 36 ; ockm-d1-sample 0")
    h.at(300, "ockm-ui-test drag 200 490 360 490")       # drag the decay slider
    h.at(800, "ockm-d1-sample 1")
    h.at(900, "ockm-ui-test tap 301 403")                # random, greyed out: nothing
    f = os.path.join(work, "t_preview.pd"); h.finish(1200, f)
    out = run(work, f)
    aud = printed(out, "ockm-d1-audition")
    assert len(aud) >= 1, f"dragging a slider while stopped should play the sound: {aud}"
    assert not printed(out, "ockm-d1-labrseed"), "random is greyed out while the slot plays a sample"

INST_PHRASE = [(0, "note 36 110"), (200, "off 36"), (250, "note 48 90"), (450, "off 48"), (500, "note 43 90 1"), (700, "note 41 110 1"),
               (1000, "off 41"), (1100, "note 36 90"), (1600, "off 36")]
INST_CONTROLS = {
    "bass": [("wave", 2), ("swarm", 1), ("sub", 1), ("noise", 0.6), ("cutoff", 0.1), ("resonance", 1), ("env", 0), ("filter", 1), ("decay", 0.05),
             ("fdecay", 1), ("pitch-amt", 0.6), ("lfo-amt", 0.8), ("drive", 1), ("glide", 1), ("amode", 1)],
    "analog": [("pulse", 0), ("saw", 1), ("sub", 1), ("sub-mode", 1), ("width", 0.9), ("pwm", 1), ("cutoff", 0.1), ("resonance", 1), ("env", 0),
               ("lfo-filter", 1), ("lfo-pitch", 1), ("sustain", 0), ("attack", 0.6), ("glide", 0.6), ("noise", 0.8)],
}

@test
def instruments_play_in_tune_and_every_control_counts(work):
    """v1.39 the Bass and Analog instruments: each plays in tune, and every main control changes the sound clearly
    (the recording differs by at least a fifth of its own level) without blowing up the level."""
    try:
        import numpy as np
    except ImportError:
        raise Skip("numpy not installed")
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    import wave as wv
    for kind, pre in (("bass", "ib"), ("analog", "ia")):
        h = Harness(dut=f"ockm-inst-{kind} {pre}")
        w_ = h.add("#X obj 600 40 writesf~ 1;"); r_ = h.add("#X obj 600 10 r test-wav;"); h.con(r_, w_); h.con(h.dut, w_)
        cases, t = [], 200
        only = {"bass": {"lfo-pitch", "pulse", "saw", "width", "pwm", "sub-mode", "lfo-filter"}, "analog": {"swarm", "lfo-amt", "pitch-amt", "wave", "filter", "fdecay", "drive"}}[kind]
        def take(name, sets, phrase):
            nonlocal t
            sets = {k: v for k, v in sets.items() if k not in only}
            path = os.path.join(work, f"{kind}-{name}.wav")
            h.at(t, " ; ".join(f"{pre}-{k} {v}" for k, v in sets.items()) or f"{pre}-level 0.8")
            h.at(t + 50, f"test-wav open {path} , start")
            for dt, m in phrase: h.at(t + 100 + dt, f"test-in {m}")
            h.at(t + 2000, "test-wav stop"); h.at(t + 2050, "test-in panic")
            t += 2300; cases.append((name, path))
        # in tune: a held A, nothing moving the pitch
        flat = {"swarm": 0, "sub": 0, "cutoff": 0.9, "resonance": 0, "lfo-amt": 0, "pitch-amt": 0, "amode": 1, "lfo-pitch": 0, "pulse": 1, "saw": 0, "width": 0, "pwm": 0, "env": 0}
        take("tune", flat, [(0, "note 33 90" if kind == "bass" else "note 45 90"), (1500, "off 45"), (1500, "off 33")])
        defaults = {k: v for k, v in (("swarm", 0.3), ("sub", 0.5 if kind == "bass" else 0.4), ("cutoff", 0.35 if kind == "bass" else 0.45),
                    ("resonance", 0.6 if kind == "bass" else 0.4), ("lfo-amt", 0), ("pitch-amt", 0), ("amode", 0), ("lfo-pitch", 0), ("pulse", 0.8),
                    ("saw", 0), ("width", 0.2), ("pwm", 0), ("env", 0.55 if kind == "bass" else 0.45), ("wave", 0), ("noise", 0), ("filter", 0),
                    ("decay", 0.35 if kind == "bass" else 0.4), ("fdecay", 0.35), ("drive", 0.3), ("glide", 0.3 if kind == "bass" else 0),
                    ("sub-mode", 0), ("lfo-filter", 0), ("sustain", 0 if kind == "bass" else 0.6), ("attack", 0.02))}
        take("ref", defaults, INST_PHRASE)
        for k, v in INST_CONTROLS[kind]:
            sets = dict(defaults); sets[k] = v
            take(f"{k}-{v}", sets, INST_PHRASE)
            take(f"{k}-{v}-back", defaults, [])   # put it back (and let it ring out) before the next
        f = os.path.join(work, f"t_inst_{kind}.pd"); h.finish(t + 100, f)
        p = subprocess.run([PD, "-nogui", "-nosound", "-nomidi", "-batch", "-path", PDLUA, "-lib", "pdlua", "-open", f],
                           cwd=work, capture_output=True, text=True, timeout=900)
        errs = [l for l in (p.stdout + p.stderr).splitlines() if "error" in l.lower() or "couldn't" in l]
        assert not errs, errs[:5]
        def load(path):
            w = wv.open(path); sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
            return x, sr
        x, sr = load(os.path.join(work, f"{kind}-tune.wav"))
        seg = list(x[int(0.4 * sr):int(1.2 * sr)])
        f0 = cycles_per_second(seg, sr); want = 55 if kind == "bass" else 110
        assert abs(f0 - want) < want * 0.08, f"{kind} plays {f0:.1f} Hz for an A, expected {want}"
        ref, _ = load(os.path.join(work, f"{kind}-ref.wav"))
        rr = np.sqrt((ref ** 2).mean())
        assert rr > 0.03, f"{kind} is too quiet: rms {rr:.3f}"
        weak = []
        for name, path in cases:
            if name in ("tune", "ref") or name.endswith("-back"): continue
            y, _ = load(path); n = min(len(y), len(ref))
            d = np.sqrt(((y[:n] - ref[:n]) ** 2).mean()) / rr
            lvl = 20 * np.log10(np.sqrt((y ** 2).mean()) / rr + 1e-9)
            if d < 0.2 or abs(lvl) > 14: weak.append(f"{name}: diff {d:.2f}, level {lvl:+.1f} dB")
        assert not weak, f"{kind}: " + " | ".join(weak)
        print(f"      {kind}: in tune ({f0:.1f} Hz), rms {rr:.2f}, {len(INST_CONTROLS[kind])} controls each change it")

QUIET = "ockm-drums-on 0 ; ockm-bass-on 0 ; ockm-lead-on 0 ; ockm-chord-on 0 ; "

def smp_files(work):
    """Starter line 1 and 2 (hooks, deep) as tones, and one file of your own in samples/user."""
    folder = os.path.join(work, "samples", "vox", "hooks", "deep")
    os.makedirs(folder, exist_ok=True)
    for i in range(1, 17):
        write_tone(os.path.join(folder, f"{i:02d}.wav"), 440 if i == 1 else 330, 1.6, sr=48000)
    user = os.path.join(work, "samples", "user", "voice")
    os.makedirs(user, exist_ok=True)
    write_tone(os.path.join(user, "b-second.wav"), 220, 0.5, sr=48000)
    write_tone(os.path.join(user, "a-first.wav"), 880, 1.6, sr=44100)   # 44.1k: it must still play at its own pitch

def onset(x, sr, after=0.0, level=0.02):
    for i in range(int(after * sr), len(x)):
        if abs(x[i]) > level:
            return i / sr
    return -1

@test
def samples_steps_play_to_the_end(work):
    """v1.38 the samples part: a step starts its sample, which plays to its end (no gate), until a later step
    takes over. A one-bar part repeats inside a longer loop. Your own file is found by its place in samples/user."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    smp_files(work)
    h = Harness(); h.show("ockm-vox-load", "ockm-smp-user", "ockm-vox-which")
    h.record(os.path.join(work, "smp.wav"))
    # 120 bpm: a step is 125 ms, a bar 2 s. Step 0: line 1 (a 1.6 s tone). Step 12 (1.5 s): your first file
    h.at(800, QUIET + "ockm-vox-len 16 ; ockm-vox-level 1 ; ockm-vox-pitch 0 ; ockm-pat-vox-smp const 0 ; ockm-pat-vox-fx const 0 ; "
              "ockm-pat-vox-smp 0 1 ; ockm-pat-vox-smp 12 1001 ; ockm-bpm 120 ; ockm-play 1")
    h.at(5200, "ockm-play 0")
    out, (x, sr) = play(work, h, "t_smp", ms=5600)
    loads = [v.split()[-1] for v in printed(out, "ockm-vox-load")]
    users = [" ".join(v.split()[-2:]) for v in printed(out, "ockm-smp-user")]
    assert loads[:2] and all(l.endswith("vox/hooks/deep/01.wav") for l in loads[:2]), f"line 1 on the 1 of each bar: {loads}"
    assert users[:1] == ["voice 1"], f"your first voice file (by name) on step 12: {users}"
    which = [int(float(v.split()[-1])) for v in printed(out, "ockm-vox-which")]
    assert which[:4] == [1, 1001, 1, 1001], f"the one-bar part repeats in the loop: {which}"
    t0 = onset(x, sr)
    assert t0 > 0, "the sample should be heard: " + " | ".join(l for l in out.splitlines() if "error" in l.lower())[:400]
    def seg(a, b): return x[int((t0 + a) * sr):int((t0 + b) * sr)]
    # no gate: line 1 is still sounding a whole second in (a drum hit would be long gone), at its own pitch
    late = seg(1.0, 1.4)
    assert peak(late) > 0.02, f"the sample should play on past its step: {peak(late):.3f}"
    assert abs(cycles_per_second(late, sr) - 440) < 30, f"still line 1 at 1.0 s: {cycles_per_second(late, sr):.0f} Hz"
    # step 12 takes over: your file (880 Hz) from 1.5 s, not line 1
    took = seg(1.6, 1.9)
    assert abs(cycles_per_second(took, sr) - 880) < 60, f"the later step takes over: {cycles_per_second(took, sr):.0f} Hz"
    # stopping the transport stops it
    end = x[int(5.4 * sr):]
    assert peak(end) < 0.01, f"stop should silence the sample: {peak(end):.3f}"

@test
def samples_old_scene_stays_quiet(work):
    """The old vox settings (on, every, set, seed) make no steps, and no errors. A scene with no steps is quiet.
    The two step tables are saved with a scene, and an older scene that lacks them clears them."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    smp_files(work)
    h = Harness(); h.show("ockm-vox-load", "ockm-smp-user")
    h.record(os.path.join(work, "old.wav"))
    h.at(800, QUIET + "ockm-pat-vox-smp const 0 ; ockm-vox-on 1 ; ockm-vox-set 1 ; ockm-vox-voice 1 ; ockm-vox-every 1 ; "
              "ockm-vox-seed 3 ; ockm-vox-pick 65535 ; ockm-vox-stut 1 ; ockm-vox-level 1 ; ockm-bpm 180 ; ockm-play 1")
    h.at(3200, "ockm-play 0")
    out, (x, sr) = play(work, h, "t_smpold", ms=3400)
    assert not printed(out, "ockm-vox-load") and not printed(out, "ockm-smp-user"), "old vox settings must not invent steps"
    errs = [l for l in out.splitlines() if "ockm-vox" in l and ("error" in l.lower() or "no such" in l.lower())]
    assert not errs, errs
    assert peak(x[int(0.9 * sr):int(3.0 * sr)]) < 0.01, "no steps, no sound"
    store = open(os.path.join(work, "seq", "ockm-store.pd")).read()
    for t in ("ockm-pat-vox-smp", "ockm-pat-vox-fx"):
        assert f"add {t} 0" in store or t in store, f"{t} should be saved with a scene"
    assert "ockm-pat-vox-smp const 0" in store and "ockm-vox-len 16" in store, "an older scene should load with no samples steps"

@test
def samples_length_and_extend(work):
    """The samples part has its own length (1 to 16 bars) and counts in the loop. Growing it repeats its steps."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-len", "ockm-vox-load")
    h.at(500, "ockm-lead-sync 0 ; ockm-drum-len 16 ; ockm-bass-len 16 ; ockm-lead-len 16 ; ockm-chord-len 16 ; "
              "ockm-pat-vox-smp const 0 ; ockm-pat-vox-smp 3 5 ; ockm-pat-vox-fx 3 2 ; ockm-vox-len 16")
    h.at(700, "ockm-vox-len 64")
    h.at(900, "ockm-vox-len 256")
    h.at(1100, "ockm-vox-len 32")
    f = os.path.join(work, "t_smplen.pd"); h.finish(1300, f)
    out = run(work, f)
    lens = [int(float(v)) for v in printed(out, "ockm-len")]
    assert 64 in lens and 256 in lens and lens[-1] == 32, f"the loop follows the samples part when it's longest: {lens}"
    h2 = Harness(); h2.show("ockm-vox-load", "ockm-smp-fx", "ockm-vox-which", "ockm-smp-again")
    h2.at(500, QUIET + "ockm-pat-vox-smp const 0 ; ockm-pat-vox-fx const 0 ; ockm-vox-len 16 ; ockm-pat-vox-smp 3 5 ; ockm-pat-vox-fx 3 2")
    h2.at(700, "ockm-vox-len 32 ; ockm-drum-len 32 ; ockm-bpm 240 ; ockm-play 1")
    h2.at(4600, "ockm-play 0")
    f2 = os.path.join(work, "t_smpext.pd"); h2.finish(4800, f2)
    out2 = run(work, f2)
    loads = printed(out2, "ockm-vox-load")
    which = [int(float(v)) for v in printed(out2, "ockm-vox-which")]
    fx = [int(float(v)) for v in printed(out2, "ockm-smp-fx")]
    assert len(which) >= 2 and all(w == 5 for w in which), f"bar 2 repeats bar 1 after growing: {which}"
    assert len(loads) == 1 and loads[0].endswith("vox/hooks/deep/05.wav"), f"the file is read once, then replayed: {loads}"
    assert len(printed(out2, "ockm-smp-again")) == len(which) - 1, "the same file again replays what's loaded"
    assert fx and all(v == 2 for v in fx), f"the step's effect comes with it: {fx}"

@test
def samples_stutter_chops(work):
    """A step with stutter restarts its sample every 16th, so the level jumps back up. Off, it just plays."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    smp_files(work)
    def run_one(fx, name):
        h = Harness(); h.record(os.path.join(work, name + ".wav"))
        h.at(800, QUIET + f"ockm-vox-len 16 ; ockm-vox-level 1 ; ockm-vox-pitch 0 ; ockm-pat-vox-smp const 0 ; ockm-pat-vox-fx const 0 ; "
                  f"ockm-pat-vox-smp 0 1 ; ockm-pat-vox-fx 0 {fx} ; ockm-bpm 180 ; ockm-play 1")
        h.at(2500, "ockm-play 0")
        _, (x, sr) = play(work, h, name, ms=2800)
        return x, sr
    def rises(x, sr):
        t0 = max(0, onset(x, sr))
        a, b, w = int(t0 * sr), int((t0 + 0.4) * sr), max(1, int(0.004 * sr))
        env, i = [], a
        while i + w < b:
            seg = x[i:i + w]
            env.append((sum(v * v for v in seg) / len(seg)) ** 0.5)
            i += w // 2
        top = max(env) if env else 0
        if top < 0.01:
            return 0
        return sum(1 for i in range(1, len(env)) if env[i] > env[i - 1] + 0.2 * top)
    plain, sr = run_one(0, "t_smpplain")
    chopped, _ = run_one(1, "t_smpchop")
    assert peak(plain) > 0.02 and peak(chopped) > 0.02, "the sample should be heard either way"
    pr, cr = rises(plain, sr), rises(chopped, sr)
    assert cr >= 2 and cr > pr, f"a stutter step should restart the sample: {cr} rises, play-through {pr}"

@test
def samples_delay_step_sends(work):
    """A delay step sends the sample to the delay; an off step stays dry. Measured after the sample ends."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    folder = os.path.join(work, "samples", "vox", "hooks", "deep")
    os.makedirs(folder, exist_ok=True)
    for i in range(1, 17):
        write_tone(os.path.join(folder, f"{i:02d}.wav"), 440, 0.15, sr=48000)
    def run_one(fx, name):
        h = Harness(); h.record(os.path.join(work, name + ".wav"))
        h.at(800, QUIET + f"ockm-vox-len 16 ; ockm-vox-level 1 ; ockm-vox-verb 0 ; ockm-vox-delay 0 ; ockm-pat-vox-smp const 0 ; "
                  f"ockm-pat-vox-fx const 0 ; ockm-pat-vox-smp 0 1 ; ockm-pat-vox-fx 0 {fx} ; ockm-bpm 120 ; ockm-play 1")
        h.at(2600, "ockm-play 0")
        _, (x, sr) = play(work, h, name, ms=2800)
        return x, sr
    dry, sr = run_one(0, "t_smpdry")
    wet, _ = run_one(2, "t_smpdly")
    t0 = onset(dry, sr)
    tail = lambda x: peak(x[int((t0 + 0.3) * sr):int((t0 + 1.4) * sr)])
    assert tail(wet) > 0.01 and tail(wet) > 4 * tail(dry), f"delay echoes after the sample: wet {tail(wet):.4f}, dry {tail(dry):.4f}"

@test
def instruments_arpeggiator_and_sequencer(work):
    """v1.39: held keys through the arpeggiator play one at a time (up: 57 60 64 57...; down the other way), with no
    transport running. With the arpeggiator off a key goes straight through. The sequencer's generator writes a pattern
    in the key (every note in A minor) and plays it with the transport."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ia-note", "ib-note")
    h.at(300, "ockm-bpm 120 ; ia-arp 1 ; ia-arp-oct 1 ; ia-play note 57 100 ; ia-play note 60 100 ; ia-play note 64 100")
    h.at(1300, "ia-play off 57 ; ia-play off 60 ; ia-play off 64")
    h.at(1500, "ia-arp 2 ; ia-play note 57 100 ; ia-play note 64 100")
    h.at(2000, "ia-play off 57 ; ia-play off 64 ; ia-arp 0")
    h.at(2200, "ia-play note 50 100 ; ia-play off 50")
    h.at(2400, "ockm-root 9 ; ockm-scale 0 ; ib-on 1 ; ib-len 16 ; ib-gstyle 0 ; ib-gbusy 1 ; ib-gen bang ; ockm-play 1")
    h.at(4500, "ockm-play 0")
    f = os.path.join(work, "t_arp.pd"); h.finish(4800, f)
    out = run(work, f)
    notes = [v.split() for v in printed(out, "ia-note")]
    ons = [int(float(n[1])) for n in notes if n[0] == "note"]
    first = ons[:6]
    assert first == [57, 60, 64, 57, 60, 64], f"up: one at a time, lowest first: {ons}"
    s_ = " ".join(map(str, ons))
    assert " 64 57 64 57" in s_[s_.index("57 60 64"):].split(" 60 ")[-1] or "64 57 64 57" in s_, f"down: highest first: {ons}"
    assert 50 in ons, "arpeggiator off: a key goes straight through"
    errs = [l for l in out.splitlines() if "error" in l.lower()]
    assert not errs, errs[:4]
    bn = [int(float(v.split()[1])) for v in printed(out, "ib-note") if v.startswith("note")]
    assert len(bn) >= 8, f"the generated pattern plays with the transport: {bn}"
    minor = {9, 11, 0, 2, 4, 5, 7}
    assert all(n % 12 in minor for n in bn), f"every note in A minor: {bn}"

@test
def instruments_analog_voices(work):
    """v1.40 the Analog's voices: mono plays one note of three held, poly all three, chord mode plays the set chord from
    one key, and unison stacks detuned voices on one note (they beat)."""
    try:
        import numpy as np
    except ImportError:
        raise Skip("numpy not installed")
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    import wave as wv
    h = Harness(dut="ockm-inst-analog ia")
    w_ = h.add("#X obj 600 40 writesf~ 1;"); r_ = h.add("#X obj 600 10 r test-wav;"); h.con(r_, w_); h.con(h.dut, w_)
    common = "ia-pulse 0 ; ia-saw 1 ; ia-sub 0 ; ia-cutoff 0.9 ; ia-env 0 ; ia-resonance 0 ; ia-sustain 1 ; ia-attack 0 ; ia-glide 0 ; ia-lfo-pitch 0 ; ia-uni 0.6"
    takes, t = [], 200
    for name, mode, keys in (("mono", 0, (57, 61, 64)), ("poly", 3, (57, 61, 64)), ("chord", 2, (57,)), ("unison", 1, (57,))):
        path = os.path.join(work, f"v-{name}.wav")
        h.at(t, f"{common} ; ia-mode {mode} ; ia-ch1 4 ; ia-ch2 7 ; ia-ch3 0")
        h.at(t + 100, f"test-wav open {path} , start")
        for k in keys: h.at(t + 150, f"test-in note {k} 90")
        h.at(t + 1150, "test-wav stop")
        for k in keys: h.at(t + 1200, f"test-in off {k}")
        h.at(t + 1250, "test-in panic")
        takes.append((name, path)); t += 1600
    f = os.path.join(work, "t_voices.pd"); h.finish(t, f)
    p = subprocess.run([PD, "-nogui", "-nosound", "-nomidi", "-batch", "-path", PDLUA, "-lib", "pdlua", "-open", f], cwd=work, capture_output=True, text=True, timeout=300)
    errs = [l for l in (p.stdout + p.stderr).splitlines() if "error" in l.lower()]
    assert not errs, errs[:4]
    def energy(path):
        w = wv.open(path); sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float)
        x = x[int(0.2 * sr):]; X = np.abs(np.fft.rfft(x * np.hanning(len(x)))); fr = np.fft.rfftfreq(len(x), 1 / sr)
        band = lambda f0: X[(fr > f0 * 0.985) & (fr < f0 * 1.015)].max()
        e = {n: band(440 * 2 ** ((n - 69) / 12)) for n in (57, 61, 64)}
        top = max(e.values())
        return {n: v / top for n, v in e.items()}, x, sr
    got = {name: energy(path) for name, path in takes}
    mono, poly, chord = got["mono"][0], got["poly"][0], got["chord"][0]
    assert sum(1 for v in mono.values() if v > 0.3) == 1, f"mono plays one of the three: {mono}"
    assert all(v > 0.3 for v in poly.values()), f"poly plays all three: {poly}"
    assert all(v > 0.3 for v in chord.values()), f"one key in chord mode plays the chord (A, C#, E): {chord}"
    # unison: four detuned copies beat, so the level wobbles
    x, sr = got["unison"][1], got["unison"][2]
    env = np.array([np.sqrt((x[i:i + 480] ** 2).mean()) for i in range(0, len(x) - 480, 480)])
    assert env.std() / env.mean() > 0.05, f"unison should beat: {env.std() / env.mean():.3f}"

@test
def midi_out_plays_the_parts(work):
    """v1.40 MIDI out: on channel 2 the bass sends note on/off; an accent goes out at 120, a plain note at 90; a glide
    starts the new note before the old one stops (a slide on a TD-3); a mute lets go of what it holds; the chords send
    all their notes; on 0 (this box only) nothing goes out."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(dut="ockm-midiout bass")
    pr = h.add("#X obj 400 80 print MB;"); h.con(h.dut, pr)
    c = h.add("#X obj 600 40 ockm-midiout chord;"); pc = h.add("#X obj 600 80 print MC;"); h.con(c, pc)
    h.at(100, "ockm-bass-midi 1 ; ockm-bass-mch 2 ; ockm-stepms 125")
    h.at(150, "ockm-bass-notes-out 45 1 0 1")      # accent, held into the next
    h.at(200, "ockm-bass-notes-out 48 0 1 1")      # glides in
    h.at(250, "ockm-bass-mute 1")                  # muted: lets go
    h.at(300, "ockm-bass-notes-out 50 0 0 0")      # muted: nothing
    h.at(350, "ockm-bass-mute 0 ; ockm-bass-midi 0")
    h.at(400, "ockm-bass-notes-out 52 0 0 0")      # this box only: nothing
    h.at(450, "ockm-chord-midi 2 ; ockm-chord-mch 3 ; ockm-chord-notes-out 57 60 64 0 1")
    f = os.path.join(work, "t_midiout.pd"); h.finish(1600, f)
    out = run(work, f)
    mb = [int(float(v)) for v in printed(out, "MB")]
    trip = [tuple(mb[i:i + 3]) for i in range(0, len(mb) - 2, 3)]
    assert trip[:3] == [(145, 45, 120), (145, 48, 90), (129, 45, 0)], f"accent on, glide overlaps: {trip}"
    assert (129, 48, 0) in trip[3:], f"the mute lets go: {trip}"
    assert not any(t[1] in (50, 52) for t in trip), f"muted, or this box only: nothing goes out: {trip}"
    mc = [int(float(v)) for v in printed(out, "MC")]
    ct = [tuple(mc[i:i + 3]) for i in range(0, len(mc) - 2, 3)]
    assert [t[:2] for t in ct[:3]] == [(146, 57), (146, 60), (146, 64)], f"the chord's notes on channel 3: {ct}"
    assert (130, 57, 0) in ct, f"and they let go after their length: {ct}"

@test
def midi_out_settings(work):
    """v1.40 settings, MIDI out: the bass to MIDI, the lead's channel up: both sent, and kept."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    L = ui_preview.run(["test tap 150 36", "test tap 93 384", "test tap 450 251", "test tap 828 309"])   # v1.49 drums first
    assert "sent ockm-bass-midi float 1" in L, [l for l in L if "-midi" in l]
    assert "sent ockm-lead-mch float 3" in L, [l for l in L if "-mch" in l]

@test
def drums_go_out_over_midi(work):
    """v1.49 drums out: each hit a note on channel 10, velocity from its strength (an accent 127); by sound a kick is 36 and
    a closed hat 42, on pads slot 4 is 39; a muted slot and drums switched off send nothing. In the patch, the drum hits
    reach the MIDI out as they play, and on MIDI only the box's drums go quiet."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(dut="ockm-midiout drums")
    pr = h.add("#X obj 400 80 print MD;"); h.con(h.dut, pr)
    h.at(100, "ockm-drums-midi 1 ; ockm-drums-mch 10")
    h.at(150, "ockm-drums-notes-out d1 1")
    h.at(250, "ockm-drums-notes-out d4 0.7")
    h.at(350, "ockm-d2-mute 1 ; ockm-drums-notes-out d2 1")
    h.at(450, "ockm-drums-map 1 ; ockm-drums-notes-out d4 0.7")
    h.at(550, "ockm-drums-on 0 ; ockm-drums-notes-out d1 1")
    h.at(650, "ockm-drums-on 1 ; ockm-drums-midi 0 ; ockm-drums-notes-out d1 1")
    f = os.path.join(work, "t_dmo.pd"); h.finish(900, f)
    md = [int(float(v)) for v in printed(run(work, f), "MD")]
    ons = [tuple(md[i:i + 3]) for i in range(0, len(md) - 2, 3) if md[i] == 153]
    assert ons == [(153, 36, 127), (153, 42, 89), (153, 39, 89)], f"kick, closed hat, then slot 4 on pads; nothing muted or off: {ons}"
    assert (137, 36, 0) in [tuple(md[i:i + 3]) for i in range(0, len(md) - 2, 3)], "the notes let go"
    try:
        import numpy as np
    except ImportError:
        raise Skip("numpy not installed")
    def rec(name, midi):
        h = Harness(); h.show("ockm-drums-notes-out"); h.record(os.path.join(work, name + ".wav"))
        h.at(100, f"ockm-bass-on 0 ; ockm-lead-on 0 ; ockm-chord-on 0 ; ockm-drums-midi {midi} ; ockm-play 1")
        h.at(2100, "ockm-play 0"); f = os.path.join(work, name + ".pd"); h.finish(2300, f)
        out = run(work, f)
        wv = wave.open(os.path.join(work, name + ".wav"))
        x = np.frombuffer(wv.readframes(wv.getnframes()), np.int16).astype(float)
        return printed(out, "ockm-drums-notes-out"), np.sqrt((x ** 2).mean()) / 32768
    hits0, a0 = rec("dm0", 0)
    hits1, a1 = rec("dm1", 1)
    assert len(hits1) >= 4 and any(hh.split()[-2:][0] == "d1" for hh in hits1), f"the hits reach the MIDI out: {hits1[:6]}"
    assert a0 > 0.01 and a1 < a0 * 0.1, f"MIDI only: the box's drums go quiet ({a1:.4f} against {a0:.4f})"

@test
def drmz_plays_its_groove(work):
    """v1.40 drmz: picking a groove and new writes it, the transport plays it (kick on the beat), the drums make sound,
    a muted voice stays quiet, and nothing plays while drmz isn't picked."""
    try:
        import numpy as np
    except ImportError:
        raise Skip("numpy not installed")
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    import wave as wv
    h = Harness(); h.show("iz-hit", "test-mark")
    wav = os.path.join(work, "drmz.wav"); h.record(wav)
    h.at(300, "ockm-bpm 120 ; iz-on 1 ; iz-len 16 ; iz-gstyle 0 ; iz-gbusy 0 ; iz-gen bang")
    h.at(400, f"test-wav open {wav} , start ; ockm-play 1")
    h.at(2400, "ockm-z1-mute 1 ; test-mark 1")
    h.at(4400, "ockm-z1-mute 0 ; iz-on 0 ; test-mark 2")
    h.at(5400, "ockm-play 0 ; test-wav stop")
    f = os.path.join(work, "t_drmz.pd"); h.finish(5600, f)
    out = run(work, f)
    errs = [l for l in out.splitlines() if "error" in l.lower()]
    assert not errs, errs[:4]
    lines = out.splitlines()
    def hits(a, b):
        seg = lines[a:b]
        return [int(float(l.split(":", 1)[1].split()[0])) for l in seg if l.startswith("iz-hit:")]
    im = next(i for i, l in enumerate(lines) if l.startswith("test-mark: 1")); io = next(i for i, l in enumerate(lines) if l.startswith("test-mark: 2"))
    before, muted, off = hits(0, im), hits(im, io), hits(io, len(lines))
    assert before.count(1) >= 3, f"the kick plays on the beat: {before}"
    assert muted and 1 not in muted, f"a muted kick stays quiet, the rest play on: {muted}"
    assert not off, f"nothing plays once drmz isn't picked: {off}"
    w = wv.open(wav); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    rms = np.sqrt((x[: w.getframerate() * 2] ** 2).mean())
    assert rms > 0.02, f"the drums should be heard: rms {rms:.4f}"

@test
def bass_and_lead_play_the_synths(work):
    """v1.45 the Bass synth is the bass part's engine 8 and the Analog the lead's engine 7: each plays its part's
    pattern, at the level of the part's other engines, and the synth's own settings change the sound (cutoff up, brighter)."""
    try:
        import numpy as np
    except ImportError:
        raise Skip("numpy not installed")
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    import wave as wv
    takes = []
    def take(name, part, others, eng, extra):
        h = Harness()
        wav = os.path.join(work, name + ".wav"); h.record(wav)
        h.at(300, f"ockm-drums-on 0 ; ockm-{others[0]}-on 0 ; ockm-{others[1]}-on 0 ; ockm-{part}-on 1 ; ockm-{part}-engine {eng} ; ockm-bpm 124 ; ockm-{part}-gen bang" + extra)
        h.at(800, f"test-wav open {wav} , start ; ockm-play 1")
        h.at(4800, "ockm-play 0 ; test-wav stop")
        f = os.path.join(work, name + ".pd"); h.finish(5000, f)
        out = run(work, f, timeout=120)
        errs = [l for l in out.splitlines() if "error" in l.lower()]
        assert not errs, errs[:3]
        w = wv.open(wav); sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
        X = np.abs(np.fft.rfft(x)); fr = np.fft.rfftfreq(len(x), 1 / sr)
        P = X ** 2
        return np.sqrt((x ** 2).mean()), (X * fr).sum() / max(X.sum(), 1e-9), P[fr > 3000].sum() / max(P.sum(), 1e-12)
    b5 = take("b5", "bass", ("lead", "chord"), 5, "")
    b8 = take("b8", "bass", ("lead", "chord"), 8, " ; ib-cutoff 0.15")
    b8o = take("b8o", "bass", ("lead", "chord"), 8, " ; ib-cutoff 0.8")
    b8d = take("b8d", "bass", ("lead", "chord"), 8, "")   # v1.46 its own starting sound
    l4 = take("l4", "lead", ("bass", "chord"), 4, "")
    l7 = take("l7", "lead", ("bass", "chord"), 7, "")
    assert b8[0] > 0.004 and l7[0] > 0.004, f"the synths play their parts: bass {b8[0]:.4f}, lead {l7[0]:.4f}"
    assert 0.33 < b8o[0] / b5[0] < 3 and 0.5 < l7[0] / l4[0] < 2, f"level-matched: {b8o[0]:.4f}/{b5[0]:.4f}, {l7[0]:.4f}/{l4[0]:.4f}"
    assert b8o[1] > b8[1] * 1.3, f"the Bass synth's cutoff opens it up: {b8[1]:.0f} -> {b8o[1]:.0f} Hz"
    assert b8d[2] < 2.5 * b5[2], f"v1.46 not fizzy: the Bass synth's top end (above 3 kHz) near the default engine's: {100*b8d[2]:.2f}% vs {100*b5[2]:.2f}%"

@test
def midi_channels_play_the_parts(work):
    """v1.45 notes on the bass's channel (1) play the bass: on the Bass synth through its keys (and arpeggiator); notes on
    the lead's channel (2) play the lead, here on another engine, held until the key lets go. Other channels stay pads."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ib-note", "ockm-lead-live", "ockm-bass-live")
    h.at(400, "ockm-bass-engine 8 ; ockm-lead-engine 4")
    h.at(600, "ockm-midi-note 40 100 1"); h.at(700, "ockm-midi-note 40 0 1")
    h.at(800, "ockm-midi-note 64 80 2"); h.at(900, "ockm-midi-note 64 0 2")
    h.at(1000, "ockm-midi-note 70 90 5")
    f = os.path.join(work, "t_mch.pd"); h.finish(1300, f)
    out = run(work, f)
    errs = [l for l in out.splitlines() if "error" in l.lower()]
    assert not errs, errs[:3]
    ib = printed(out, "ib-note")
    assert any(v.startswith("note 40") for v in ib) and any(v.startswith("off 40") for v in ib), ib
    ll = printed(out, "ockm-lead-live")
    assert ll and ll[0].split()[:2] == ["64", "0"] and "off" in ll[-1], ll
    assert not printed(out, "ockm-bass-live"), "the bass is on the synth: its keys, not the engine directly"

@test
def synth_pages_from_the_part(work):
    """v1.45 on the bass tab, picking the bass synth makes its quick knobs the synth's (cutoff and so on) and shows edit;
    edit opens the synth's page (volume included) over the groovebox, which isn't switched off; back returns to the tab.
    The menu has no start screen any more."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    L = ui_preview.run(["test tap 363 36", "test tap 866 350", "test drag 520 397 640 397",
                        "test tap 859 314", "test drag 760 36 710 36", "test tap 41 36", "paint back", "test tap 919 36", "paint menu"])
    sent = [l for l in L if l.startswith("sent ")]
    assert "sent ockm-bass-engine float 8" in sent, [l for l in sent if "engine" in l]
    assert "sent ib-resonance float 0.35" in sent and "sent ib-env float 0.35" in sent, "picking it loads a starting sound that sits in the groovebox"
    cut = [float(l.split()[-1]) for l in sent if l.startswith("sent ib-cutoff float")]
    assert cut and cut[-1] > 0.4, f"the quick knob moves the synth's cutoff: {cut}"
    lv = [float(l.split()[-1]) for l in sent if l.startswith("sent ib-level float")]
    assert lv and lv[-1] < 0.5, f"the page's volume: {lv}"
    assert not any(l.startswith("sent ockm-inst-mode") or l.startswith("sent ib-on") for l in sent), "the groovebox keeps playing"
    i0, i1 = L.index("begin back"), L.index("end back")
    assert any("edit the bass synth" in l for l in L[i0:i1]), "back on the bass tab"
    i0, i1 = L.index("begin menu"), L.index("end menu")
    assert not any("start screen" in l for l in L[i0:i1]), "no start screen in the menu"

@test
def projects_table_and_the_name_under_the_tempo(work):
    """v1.47 the project screen lists projects as a table (name, made, last saved, scenes, tempo and key, style), newest
    first; tapping a heading sorts by it (name: a to z). The project you're in and its scene show under the tempo."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    L = ui_preview.run(["send ockm-project-name symbol 2026-10-22-quiet-fox-v19", "test tap 919 36", "test tap 830 95", "paint t1",
                        "test tap 120 169", "paint t2"])
    def texts(tag):
        i0, i1 = L.index("begin " + tag), L.index("end " + tag)
        return [" ".join(l.split()[4:]) for l in L[i0:i1] if l.startswith("text ")]
    t1, t2 = texts("t1"), texts("t2")
    for h in ("name", "last saved", "scenes", "tempo key", "style"):
        assert any(x.startswith(h) for x in t1), f"heading {h}: {t1[:20]}"
    rows = lambda t: [x for x in t if x in ("amber heron", "neon otter", "dusty lantern", "default")]
    assert rows(t1)[0] == "dusty lantern", f"newest first: {rows(t1)}"
    assert rows(t2)[:3] == ["amber heron", "default", "dusty lantern"], f"by name: {rows(t2)}"
    assert any("quiet fox · S" in x for x in t1), "the project and its scene under the tempo"

@test
def new_project_starts_with_the_lead_empty(work):
    """v1.47 a new blank project's lead is empty, like the bass and chords (it used to start on the same motif every time)."""
    if not PDLUA:
        raise Skip("pdlua not found (set PDLUA=/folder/with/pdlua)")
    h = Harness(); h.show("ockm-lead-notes-out", "test-mark")
    m = "ockm-ui-test"
    h.at(500, f"{m} tap 919 36"); h.at(600, f"{m} tap 830 95"); h.at(700, f"{m} tap 808 100")   # menu, project, new blank
    h.at(2000, "ockm-play 1 ; test-mark 1"); h.at(5000, "ockm-play 0")
    f = os.path.join(work, "t_newlead.pd"); h.finish(5200, f)
    out = run(work, f)
    lines = out.splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith("test-mark: 1"))
    played = [l for l in lines[i:] if l.startswith("ockm-lead-notes-out:")]
    assert not played, f"the lead should be empty: {played[:6]}"

@test
def usb_audio_outputs(work):
    """v1.48 USB audio out: besides the mix (outputs 1-2), the box sends drum slot 1 (the kick) to 3, the rest of the drums
    to 4 (the drums less the kick, so the parts add up to the mix), then bass, lead, chords, samples and effects to 5-9.
    The Pi start-up opens 9 outputs and the USB device has 9 channels."""
    rec = open(os.path.join(work, "seq", "ockm-recorder.pd")).read()
    for n in range(3, 10):
        assert f"dac~ {n};" in rec, f"output {n}"
    assert "catch~ ockm-usb-kick" in rec and "-~;" in rec, "the kick, and the drums less the kick"
    main = open(os.path.join(work, "OCKM_GENERATOR.pd")).read()
    assert main.count("throw~ ockm-usb-kick") == 1, "only drum slot 1 goes to the kick channel"
    st = open(os.path.join(ROOT, "tools", "pi", "ockm-start.sh")).read()
    ua = open(os.path.join(ROOT, "tools", "pi", "ockm-usb-audio.sh")).read()
    assert "-outchannels 9" in st and "0x1ff > $F/p_chmask" in ua, "9 outputs, 9 USB channels"
    assert "aplay -l 2>/dev/null | grep -q UAC2Gadget" in st, "only when the USB device is there: otherwise the DAC as before"

@test
def saves_are_power_cut_safe(work):
    """v1.49 saving writes each file as <file>.new first, then renames it over the old one (one step), so a power cut
    can't leave a half-written or empty file. After saving: the files are whole, nothing .new is left lying about, and
    a file left half-written by a cut (here: a stray .new) doesn't stop the project loading."""
    h = Harness()
    h.at(300, "ockm-bpm 131 ; ockm-save bang")
    f = os.path.join(work, "t_safe.pd"); h.finish(1200, f)
    out = run(work, f)
    errs = [l for l in out.splitlines() if "error" in l.lower()]
    assert not errs, errs[:4]
    left = [os.path.join(dp, fn) for dp, _, fns in os.walk(os.path.join(work, "projects")) for fn in fns if fn.endswith(".new")]
    assert not left, f"nothing half-written left: {left}"
    pj = open(os.path.join(work, "projects", "default", "project.txt")).read()
    assert "ockm-bpm 131" in pj, "the save is in the file"
    open(os.path.join(work, "projects", "default", "project.txt.new"), "w").write("ockm-bpm 9")   # a cut mid-save
    h = Harness(); h.show("ockm-bpm")
    f = os.path.join(work, "t_safe2.pd"); h.finish(800, f)
    out = run(work, f)
    assert "131" in " ".join(printed(out, "ockm-bpm")) or not printed(out, "ockm-bpm"), "the whole file is the one read"

@test
def menu_shut_down_asks_first(work):
    """v1.43 on the Pi, the menu has shut down: the first tap asks, the second switches the Pi off (a stand-in command
    here). Off the Pi it isn't there."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    flag = os.path.join(work, "shutdown-ran")
    old = dict(os.environ)
    try:
        os.environ["OCKM_KIOSK"] = "1"; os.environ["OCKM_SHUTDOWN_CMD"] = f"touch {flag}"
        L = ui_preview.run(["test screen perform", "test tap 919 36", "paint m1", "test tap 830 445", "paint m2"])
        import time; time.sleep(0.3)
        def texts(tag):
            i0, i1 = L.index("begin " + tag), L.index("end " + tag)
            return " ".join(l for l in L[i0:i1] if l.startswith("text "))
        assert "shut down" in texts("m1"), "the menu offers shut down on the Pi"
        assert "tap again to shut down" in texts("m2"), "the first tap asks"
        assert not os.path.exists(flag), "one tap doesn't switch it off"
        L = ui_preview.run(["test screen perform", "test tap 919 36", "test tap 830 445", "test tap 830 445"])
        time.sleep(0.5)
        assert os.path.exists(flag), "the second tap switches it off"
    finally:
        os.environ.clear(); os.environ.update(old)
    L = ui_preview.run(["test screen perform", "test tap 919 36", "paint m3"])
    i0, i1 = L.index("begin m3"), L.index("end m3")
    assert not any("shut down" in l for l in L[i0:i1]), "not on the Mac"

@test
def drmz_voices_start_on_their_own_sounds(work):
    """v1.41 each drmz voice starts on its own sound (kick, snare, clap, perc, hat, open hat, tom, perc 2), even with a
    scene from before drmz, which has none of its settings."""
    t = open(os.path.join(work, "voices", "ockm-drmz.pd")).read()
    for k in range(8):
        assert f"ockm-z{k + 1}-sound {k}" in t, f"voice {k + 1} should start on sound {k}"

@test
def samples_screen_places_steps(work):
    """v1.38 the samples tab: your files are listed, arming one plays it, a step takes the sample and effect,
    the same pair clears it and a different one replaces it. The part's length and bar pages work like the others."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import ui_preview
    if not ui_preview.LUA:
        raise Skip("no lua to run the screen")
    L = ui_preview.run([
        "test tap 530 36",                       # the samples tab (scans samples/user)
        "test tap 64 322",                       # your first file
        "test tap 740 318",                      # delay
        "test tap 46 166", "test tap 46 166",    # place it, then the same pair clears it
        "test tap 46 166", "test tap 870 318", "test tap 46 166",   # place it, then verb replaces it
        "test tap 724 88",                       # 4 bars
        "test tap 194 88", "test tap 46 166",    # the next bar, its first step
        "test tap 866 426", "test tap 866 426",  # clear all (asks first)
        "paint smp",
    ])
    sent = [l for l in L if l.startswith("sent ockm-pat-vox") or l.startswith("sent ockm-smp-play") or l.startswith("sent ockm-vox-len")]
    assert "sent ockm-samples-scan bang " in L or any(l.startswith("sent ockm-samples-scan") for l in L), "opening the tab looks for new files"
    assert sent[0] == "sent ockm-smp-play list 1001 0", sent
    want = [
        "sent ockm-pat-vox-smp list 0 1001", "sent ockm-pat-vox-fx list 0 2",
        "sent ockm-pat-vox-smp list 0 0", "sent ockm-pat-vox-fx list 0 0",
        "sent ockm-pat-vox-smp list 0 1001", "sent ockm-pat-vox-fx list 0 2",
        "sent ockm-pat-vox-smp list 0 1001", "sent ockm-pat-vox-fx list 0 3",
        "sent ockm-vox-len float 64",
        "sent ockm-pat-vox-smp list 16 1001", "sent ockm-pat-vox-fx list 16 3",
        "sent ockm-pat-vox-smp const 0", "sent ockm-pat-vox-fx const 0",
    ]
    assert sent[1:] == want, sent
    txt = [l for l in L if l.startswith("text ")]
    assert any("everybody" in l for l in txt), "your file's name should show"
    # the robot tab: all the computer voices in one place, set and voice picked inside
    R = ui_preview.run(["test tap 530 36", "test tap 335 272", "test tap 170 318", "test tap 600 318", "test tap 64 370"])
    plays = [l for l in R if l.startswith("sent ockm-smp-play")]
    assert plays == ["sent ockm-smp-play list 49 0"], f"robot, jack, flat, line 1 is 32 + 16 + 1: {plays}"

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
