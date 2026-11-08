#!/usr/bin/env python3
"""Render tools/vox_lines.txt to samples/vox/<set>/<voice>/NN.wav.

The Pi only plays the files. This runs on a computer, once.

  PIPER=/tmp/ockm-piper/piper/piper python3 tools/make_vox.py

Voices are Piper models. Each one used here allows the audio to be shipped
with this project. See samples/vox/VOICES.md. Never a real person's voice.
"""
import os, sys, wave, struct, math, subprocess, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINES = os.path.join(ROOT, "tools", "vox_lines.txt")
OUT = os.path.join(ROOT, "samples", "vox")
PIPER = os.environ.get("PIPER", "/tmp/ockm-piper/piper/piper")
VOICE_DIR = os.environ.get("VOX_MODELS", "/tmp/ockm-piper/voices")
SR = 48000
# speech sits near -20 dBFS, so the fader lines up with the lead
TARGET_RMS = 0.1
PEAK_CAP = 0.55

# Both trained from scratch on public-domain LibriVox readings (see samples/vox/VOICES.md).
# Noise off, so the delivery stays flat. Deep is the slower male voice. Flat is the quicker female voice.
VOICES = {
    "deep": {"model": "en_US-norman-medium.onnx", "length": 1.2, "noise": 0.0, "noise_w": 0.0},
    "flat": {"model": "en_GB-cori-medium.onnx", "length": 1.05, "noise": 0.0, "noise_w": 0.0},
}


def read_lines(path):
    sets, cur = {}, None
    for raw in open(path):
        line = raw.strip()
        if not line: continue
        if line.startswith("#"):
            cur = line[1:].strip()
            sets[cur] = []
        elif cur:
            sets[cur].append(line)
    return sets


def read_wav(path):
    w = wave.open(path)
    n, ch, sr, sw = w.getnframes(), w.getnchannels(), w.getframerate(), w.getsampwidth()
    raw = w.readframes(n)
    w.close()
    if sw == 2:
        data = struct.unpack("<" + "h" * (n * ch), raw)
        scale = 32768.0
    elif sw == 1:
        data = struct.unpack("<" + "B" * (n * ch), raw)
        data = [v - 128 for v in data]
        scale = 128.0
    else:
        raise SystemExit(f"{path}: unsupported sample width {sw}")
    if ch > 1:
        data = data[::ch]
    return [v / scale for v in data], sr


def write_wav(path, samples):
    w = wave.open(path, "w")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    frames = b"".join(struct.pack("<h", max(-32767, min(32767, int(v * 32767)))) for v in samples)
    w.writeframes(frames); w.close()


def resample(samples, src, dst):
    if src == dst: return samples
    n = max(1, int(round(len(samples) * dst / src)))
    out = []
    for i in range(n):
        x = i * src / dst
        j = int(x)
        f = x - j
        a = samples[min(j, len(samples) - 1)]
        b = samples[min(j + 1, len(samples) - 1)]
        out.append(a + (b - a) * f)
    return out


def trim(samples):
    """The word starts straight away. A stall in the middle is shortened, and the tail after the last word goes."""
    thr = 0.02
    loud = [i for i, v in enumerate(samples) if abs(v) >= thr]
    if not loud:
        return samples
    samples = samples[max(0, loud[0] - int(0.01 * SR)): loud[-1] + 1 + int(0.04 * SR)]
    gap_at, leave = int(0.22 * SR), int(0.06 * SR)
    out, i, n = [], 0, len(samples)
    while i < n:
        if abs(samples[i]) >= thr:
            out.append(samples[i]); i += 1
            continue
        j = i
        while j < n and abs(samples[j]) < thr:
            j += 1
        if j - i > gap_at:
            out.extend(samples[i:i + leave])
        else:
            out.extend(samples[i:j])
        i = j
    return out or samples


def normalise(samples):
    if not samples: return samples
    rms = math.sqrt(sum(v * v for v in samples) / len(samples)) or 1e-9
    g = TARGET_RMS / rms
    peak = max(abs(v) for v in samples) * g
    if peak > PEAK_CAP: g *= PEAK_CAP / peak
    return [v * g for v in samples]


def render(text, model, length, noise, noise_w, dest):
    cmd = [PIPER, "--model", model, "--output_file", dest,
           "--length_scale", str(length), "--noise_scale", str(noise), "--noise_w", str(noise_w),
           "--sentence_silence", "0"]
    env = os.environ.copy()
    lib = os.path.dirname(PIPER)
    env["LD_LIBRARY_PATH"] = lib + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    env["DYLD_LIBRARY_PATH"] = lib
    subprocess.run(cmd, input=text + "\n", text=True, check=True, capture_output=True, env=env)


def main():
    if not os.path.isfile(PIPER):
        sys.exit(f"piper not found at {PIPER}. Set PIPER= to the binary.")
    sets = read_lines(LINES)
    for name, lines in sets.items():
        if len(lines) != 16:
            sys.exit(f"{name} has {len(lines)} lines, want 16")
    for voice, cfg in VOICES.items():
        model = os.path.join(VOICE_DIR, cfg["model"])
        if not os.path.isfile(model):
            sys.exit(f"missing voice model {model}")
        for name, lines in sets.items():
            folder = os.path.join(OUT, name, voice)
            os.makedirs(folder, exist_ok=True)
            for i, text in enumerate(lines, 1):
                dest = os.path.join(folder, f"{i:02d}.wav")
                raw = dest + ".raw.wav"
                render(text, model, cfg["length"], cfg["noise"], cfg["noise_w"], raw)
                samples, sr = read_wav(raw)
                samples = normalise(trim(resample(samples, sr, SR)))
                write_wav(dest, samples)
                os.remove(raw)
                print(f"{name}/{voice}/{i:02d}  {len(samples) / SR:.2f}s  {text}")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
