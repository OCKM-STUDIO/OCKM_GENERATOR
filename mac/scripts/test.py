#!/usr/bin/env python3
"""Exercise the real engine in temporary workspaces; never touch player saves."""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

MAC = Path(__file__).resolve().parents[1]


def run(command, **kwargs):
    return subprocess.run([str(x) for x in command], check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=MAC.parent)
    parser.add_argument("--deps", type=Path, default=MAC / ".build/deps")
    args = parser.parse_args()
    deps = args.deps.resolve()
    root = args.root.resolve()
    runtime = MAC / "dist/OCKM GENERATOR.app/Contents/Resources/Engine"
    if not runtime.is_dir(): raise SystemExit("Build the app first.")
    env = dict(os.environ, MACOSX_DEPLOYMENT_TARGET="13.0")
    test_binary = MAC / ".build/engine-smoke"
    run(["clang++", "-std=c++17", "-O2", "-I" + str(MAC / "Sources/EngineBridge/include"),
         "-I" + str(deps / "libpd/libpd_wrapper"), "-I" + str(deps / "libpd/pure-data/src"),
         MAC / "Tests/engine_smoke.cpp", MAC / "Sources/EngineBridge/EngineBridge.cpp",
         deps / "libpdlua.a", deps / "libpd/libs/libpd.a", "-framework", "CoreMIDI",
         "-framework", "CoreFoundation", "-o", test_binary], env=env)
    with tempfile.TemporaryDirectory(prefix="ockm-native-test-") as temp:
        work = Path(temp) / "Workspace with spaces"
        shutil.copytree(runtime, work)
        result = run([test_binary, work], capture_output=True, text=True)
        print(result.stdout)
        if "lua: error" in result.stdout or "couldn't create" in result.stdout:
            raise AssertionError("An engine object failed to load")
        frames = list(work.glob("frame*.json"))
        assert len(frames) >= 12, "Missing screen or keyboard coverage"
        allowed = {"color", "background", "scale", "rect", "round", "outline", "ellipse", "text", "path", "state"}
        for frame in frames:
            drawing = json.loads(frame.read_text())
            assert drawing and all(row[0] in allowed for row in drawing), frame.name
        projects = [p for p in (work / "projects").iterdir() if p.is_dir() and p.name != "default"]
        assert len(projects) == 1
        saved = projects[0]
        assert (saved / "project.txt").stat().st_size > 0
        assert (saved / "loop.txt").stat().st_size > 0
        result = run([test_binary, work, "resume"], capture_output=True, text=True)
        print(result.stdout)
        assert saved.name in (work / "frame-resume.json").read_text()
    lua = deps / "lua-test"
    run(["clang", "-O2", "-DLUA_USE_MACOSX", deps / "pd-lua/lua/onelua.c", "-o", lua], env=env)
    for test in sorted((root / "tests/lua").glob("test_*.lua")):
        run([lua, test, root], cwd=root)
    print("PASS: native audio, 12 screens, keyboard holds, scene save/reopen, and shared Lua generators")


if __name__ == "__main__": main()
