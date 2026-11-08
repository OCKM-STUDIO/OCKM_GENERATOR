#!/usr/bin/env python3
"""Build the native Mac app with pinned, locally compiled engine dependencies."""
import argparse
import json
import os
import plistlib
import shutil
import subprocess
from pathlib import Path
from prepare_runtime import prepare

MAC = Path(__file__).resolve().parents[1]


def run(args, cwd=None, env=None):
    subprocess.run([str(x) for x in args], cwd=cwd, env=env, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=MAC.parent)
    parser.add_argument("--deps", type=Path, default=MAC / ".build/deps")
    parser.add_argument("--skip-fetch", action="store_true", help="use the already downloaded pinned dependencies")
    args = parser.parse_args()
    deps = args.deps.resolve()
    deps.mkdir(parents=True, exist_ok=True)
    lock = json.loads((MAC / "dependencies.json").read_text())
    for name, info in lock.items():
        folder = deps / name
        if not args.skip_fetch:
            if not (folder / ".git").exists():
                run(["git", "init", folder])
                run(["git", "remote", "add", "origin", info["url"]], cwd=folder)
            run(["git", "fetch", "--depth", "1", "origin", info["commit"]], cwd=folder)
            run(["git", "checkout", "--detach", info["commit"]], cwd=folder)
            run(["git", "submodule", "update", "--init", "--recursive", "--depth", "1"], cwd=folder)
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=folder, text=True).strip()
        if actual != info["commit"]:
            raise SystemExit(f"{name}: expected {info['commit']}, found {actual}")

    env = dict(os.environ, MACOSX_DEPLOYMENT_TARGET="13.0", OCKM_DEPS=str(deps))
    cache = MAC / ".build/ModuleCache"
    env.update(CLANG_MODULE_CACHE_PATH=str(cache), SWIFTPM_MODULECACHE_OVERRIDE=str(cache))
    stamp = deps / ".macos-target"
    if not stamp.exists() or stamp.read_text() != "13.0":
        run(["make", "clean"], cwd=deps / "libpd", env=env)
        stamp.write_text("13.0")
    # The pinned Pd release accidentally prints every expr allocation. Remove
    # only this diagnostic in the downloaded build tree (never shared sources).
    expr = deps / "libpd/pure-data/src/x_vexp.c"
    original = expr.read_text()
    patched = original.replace('    printf ("realloc called with %zu bytes\\n", size);', '    /* Allocation diagnostic disabled in the Mac host. */')
    if patched != original:
        expr.write_text(patched)
    run(["make", "-j", str(min(os.cpu_count() or 2, 8)), "STATIC=true", "EXTRA=true", "UTIL=true"], cwd=deps / "libpd", env=env)

    # pd-lua still calls a removed text helper. The replacement is the supported
    # equivalent in the exact pinned Pd headers. Keep the upstream file intact.
    lua_source = (deps / "pd-lua/pdlua.c").read_text()
    old = "glist_findrtext(o->canvas, x)"
    assert lua_source.count(old) == 1, "Review pd-lua compatibility patch after upgrading"
    lua_source = lua_source.replace(old, "glist_getrtext(o->canvas, x, 0)")
    old_decl = "int sys_trytoopenone(const char *dir, const char *name, const char* ext,\n    char *dirresult, char **nameresult, unsigned int size, int bin);"
    assert lua_source.count(old_decl) == 1
    lua_source = lua_source.replace(old_decl, old_decl.replace("sys_trytoopenone", "sys_trytoopenit").replace("int bin);", "int bin, int okgui);"))
    old_macro = '#define trytoopenone(dir, name, ...) sys_trytoopenone(sys_isabsolutepath(name) ? "" : dir, name, __VA_ARGS__)'
    assert lua_source.count(old_macro) == 1
    lua_source = lua_source.replace(old_macro, old_macro.replace("sys_trytoopenone", "sys_trytoopenit").replace("__VA_ARGS__)", "__VA_ARGS__, 0)"))
    (deps / "pd-lua/pdlua-mac.c").write_text(lua_source)
    run(["clang", "-O2", "-DPD", "-Wno-deprecated-declarations", "-I" + str(deps / "libpd/pure-data/src"),
         "-I" + str(deps / "pd-lua/lua"), "-c", deps / "pd-lua/pdlua-mac.c", "-o", deps / "pdlua.o"], env=env)
    run(["clang", "-O2", "-DMAKE_LIB", "-DLUA_USE_MACOSX", "-c", deps / "pd-lua/lua/onelua.c", "-o", deps / "lua.o"], env=env)
    run(["ar", "rcs", deps / "libpdlua.a", deps / "pdlua.o", deps / "lua.o"])
    run(["swift", "build", "--disable-sandbox", "--cache-path", MAC / ".build/Cache", "-c", "release"], cwd=MAC, env=env)
    binary_dir = Path(subprocess.check_output(["swift", "build", "--disable-sandbox", "--cache-path", str(MAC / ".build/Cache"),
                                              "-c", "release", "--show-bin-path"], cwd=MAC, env=env, text=True).strip())
    output = MAC / "dist"
    output.mkdir(exist_ok=True)
    staging = output / "OCKM GENERATOR.building.app"
    if staging.exists(): shutil.rmtree(staging)
    contents = staging / "Contents"
    executable = contents / "MacOS"
    resources = contents / "Resources"
    executable.mkdir(parents=True)
    resources.mkdir()
    shutil.copy2(binary_dir / "OCKMGenerator", executable / "OCKMGenerator")
    prepare(args.root.resolve(), resources / "Engine", deps, MAC / "native-ui.lua")
    shutil.copy2(MAC / "dependencies.json", resources / "Engine/Licenses/dependencies.json")
    shutil.copy2(MAC / "Assets/AppIcon.icns", resources / "AppIcon.icns")
    plist = {
        "CFBundleExecutable": "OCKMGenerator", "CFBundleIdentifier": "studio.ockm.generator.mac",
        "CFBundleName": "OCKM GENERATOR", "CFBundleDisplayName": "OCKM GENERATOR",
        "CFBundlePackageType": "APPL", "CFBundleShortVersionString": "0.1.0", "CFBundleVersion": "1",
        "CFBundleIconFile": "AppIcon",
        "LSMinimumSystemVersion": "13.0", "NSHighResolutionCapable": True, "NSPrincipalClass": "NSApplication",
        "NSHumanReadableCopyright": "OCKM GENERATOR contributors. GPL-3.0."
    }
    (contents / "Info.plist").write_bytes(plistlib.dumps(plist))
    run(["codesign", "--force", "--sign", "-", staging])
    final = output / "OCKM GENERATOR.app"
    if final.exists(): shutil.rmtree(final)
    staging.rename(final)
    print(f"Built {final}")


if __name__ == "__main__": main()
