#!/usr/bin/env python3
"""Build a clean, self-contained runtime from shared sources, never user projects."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def prepare(root, destination, deps, adapter):
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("voices", "seq", "ui", "lab"):
        shutil.copytree(root / name, destination / name, dirs_exist_ok=True)
    # Rebuild from source into the isolated bundle; do not copy personal samples,
    # projects, settings, private Pi keys, or generated local recordings.
    subprocess.run([sys.executable, str(root / "tools/build.py"), "--out", str(destination),
                    "--reset-patterns"], check=True)
    ui = destination / "ui/ockm-ui.pd_lua"
    ui.write_text(ui.read_text() + "\n" + adapter.read_text())
    # The Pi's restart service uses a UDP socket. The native host calls keep
    # directly, so retain the object position/wiring without opening a socket.
    store = destination / "seq/ockm-store.pd"
    store.write_text(store.read_text().replace("netreceive -u 3091", "r ockm-native-keep-request"))
    pdlua = destination / "pdlua"
    pdlua.mkdir(exist_ok=True)
    shutil.copy2(deps / "pd-lua/pd.lua", pdlua / "pd.lua")
    shutil.copy2(deps / "pd-lua/pdlua/tutorial/examples/pdx.lua", pdlua / "pdx.lua")
    licenses = destination / "Licenses"
    licenses.mkdir(exist_ok=True)
    for source, target in ((root / "LICENSE", "OCKM-GPL-3.0.txt"),
                           (deps / "libpd/LICENSE.txt", "libpd.txt"),
                           (deps / "libpd/pure-data/LICENSE.txt", "PureData.txt"),
                           (deps / "pd-lua/COPYING", "pd-lua.txt")):
        shutil.copy2(source, licenses / target)
    # Lua's copyright and permission notice is in lua.h.
    shutil.copy2(deps / "pd-lua/lua/lua.h", licenses / "Lua-header-and-license.txt")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--deps", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.root.resolve(), args.out.resolve(), args.deps.resolve(),
            Path(__file__).resolve().parents[1] / "native-ui.lua")
