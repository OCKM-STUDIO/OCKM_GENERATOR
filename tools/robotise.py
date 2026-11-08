#!/usr/bin/env python3
"""Make the robot lines sound like robots (v1.38).

The Piper renders sound too human. This puts each one through a channel vocoder:
the words shape a fixed-pitch buzz, so there is no human pitch, breath or warmth
left. A little noise rides the top bands so the consonants stay clear.

  python3 tools/robotise.py

The plain renders are kept in samples/vox-plain/ (made the first time this runs)
and every robot file is made from those, so it can be run again with new settings.
The box never runs this: it only plays the files.
"""
import os, sys, wave, shutil
import numpy as np
from scipy import signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOX = os.path.join(ROOT, "samples", "vox")
PLAIN = os.path.join(ROOT, "samples", "vox-plain")
SR = 48000
TARGET_RMS, PEAK_CAP = 0.1, 0.55

# deep: a low saw, a dead flat 82 Hz (E2), with a touch of ring mod. flat: a higher, buzzier pulse at 165 Hz (E3) with a ring mod wobble
VOICES = {
    "deep": {"f0": 82.41, "shape": "saw", "ring": 0.2, "noise": 0.25},
    "flat": {"f0": 164.81, "shape": "pulse", "ring": 0.35, "noise": 0.3},
}
BANDS = np.geomspace(120, 7600, 24)


def read(path):
    w = wave.open(path)
    n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32768
    w.close()
    if ch > 1: x = x.reshape(-1, ch).mean(axis=1)
    if sr != SR: x = signal.resample_poly(x, SR, sr)
    return x


def write(path, x):
    w = wave.open(path, "w"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()


def carrier(n, f0, shape):
    t = np.arange(n) / SR
    out = np.zeros(n)
    k = 1
    while k * f0 < SR / 2 * 0.9:   # band-limited, so no aliasing fizz
        amp = 1.0 / k
        if shape == "pulse": amp = amp * abs(np.sin(np.pi * k * 0.25)) * 1.6   # a 25% pulse: hollow and nasal
        out += amp * np.sin(2 * np.pi * k * f0 * t)
        k += 1
    return out / np.max(np.abs(out))


def robot(x, v):
    n = len(x)
    car = carrier(n, v["f0"], v["shape"])
    noise = np.random.default_rng(7).standard_normal(n) * 0.5
    env_lp = signal.butter(2, 40, "low", fs=SR, output="sos")
    out = np.zeros(n)
    for i in range(len(BANDS) - 1):
        lo, hi = BANDS[i], BANDS[i + 1]
        sos = signal.butter(2, [lo, hi], "band", fs=SR, output="sos")
        env = signal.sosfilt(env_lp, np.abs(signal.sosfilt(sos, x)))
        env = np.maximum(env, 0)
        src = car if hi < 3000 else (car * (1 - v["noise"]) + noise * v["noise"] * 2)
        out += signal.sosfilt(sos, src) * env
    if v["ring"] > 0:   # a slow ring mod: the metal wobble
        t = np.arange(n) / SR
        out = out * (1 - v["ring"]) + out * np.sin(2 * np.pi * 55 * t) * v["ring"]
    # a hard gate on the gaps so nothing breathes between words
    gate = signal.sosfilt(env_lp, np.abs(x)) > 0.004
    gate = signal.sosfilt(signal.butter(1, 30, "low", fs=SR, output="sos"), gate.astype(float))
    out *= gate
    rms = np.sqrt(np.mean(out ** 2)) or 1
    out *= TARGET_RMS / rms
    pk = np.max(np.abs(out))
    if pk > PEAK_CAP: out *= PEAK_CAP / pk
    return out


def main():
    if not os.path.isdir(PLAIN):
        shutil.copytree(VOX, PLAIN, ignore=shutil.ignore_patterns("*.md"))
        print("kept the plain renders in", PLAIN)
    done = 0
    for dirpath, _, files in os.walk(PLAIN):
        for f in sorted(files):
            if not f.lower().endswith(".wav"): continue
            rel = os.path.relpath(os.path.join(dirpath, f), PLAIN)
            voice = rel.split(os.sep)[1] if len(rel.split(os.sep)) > 2 else "deep"
            y = robot(read(os.path.join(dirpath, f)), VOICES.get(voice, VOICES["deep"]))
            dst = os.path.join(VOX, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            write(dst, y); done += 1
    print("robotised", done, "lines")


if __name__ == "__main__":
    main()
