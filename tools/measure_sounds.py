#!/usr/bin/env python3
"""Work out the trims for build.py's SOUNDS (v1.49): plays every sound on the bass, lead and chord tabs with no trim,
measures its loudness, and prints the trim that brings it to the level of the part's first sound.
Needs Pure Data and pdlua, as the tests do: python3 tools/measure_sounds.py [bass] [lead] [chord]   (PDLUA=/folder/with/pdlua if needed)"""
import os, sys, math, shutil, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import run_tests as rt

work = tempfile.mkdtemp(prefix="ockm-measure-")
for item in ["OCKM_GENERATOR.pd", "voices", "seq", "ui"]:
    src = os.path.join(ROOT, item)
    (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, os.path.join(work, item))
os.makedirs(os.path.join(work, "projects")); shutil.copytree(os.path.join(ROOT, "projects", "default"), os.path.join(work, "projects", "default"))
open(os.path.join(work, "projects", "current.txt"), "w").write("default;\n")
subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build.py"), "--out", work, "--reset-patterns", "--demo"], check=True, capture_output=True)
lv = rt.measure_sounds(work, parts=tuple(sys.argv[1:]) or ("bass", "lead", "chord"), use_trim=False)
S = rt.ui_sounds()
for part, l in lv.items():
    print(f"{part}:")
    for i, (snd, v) in enumerate(zip(S[part], l)):
        trim = min(2.5, max(0.25, l[0] / max(v, 1e-9)))
        print(f"  {i + 1:2d} engine {snd[0]}  {20 * math.log10(max(v, 1e-9) / l[0]):+5.1f} dB  trim {trim:.2f}")
shutil.rmtree(work, ignore_errors=True)
