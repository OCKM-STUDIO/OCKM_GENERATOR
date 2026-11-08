# OCKM GENERATOR for Mac

A standalone SwiftUI/AppKit Mac app using the same Pure Data sound engine and
Lua instrument behaviour as the Raspberry Pi version. Players do not need Pd,
plugdata, Lua or Python installed. Build tools are needed only by contributors.

## Try the early alpha

> [!WARNING]
> **Very early experimental software.** Expect bugs, audio glitches and possible crashes or lost work. Keep project backups and use a low listening volume while testing. This build is not ready to depend on for live performance.

Download **[Mac alpha 0.1.1](https://github.com/OCKM-STUDIO/OCKM_GENERATOR/releases/tag/mac-preview-0.1.1)** and choose `OCKM-GENERATOR-Mac-0.1.1-arm64.zip` under Assets. Unzip it and open `OCKM GENERATOR.app`. The download is for **Apple silicon** Macs running **macOS 13 or later**. Intel Macs have not been tested.

The app is locally signed for development, **not Developer ID signed or notarised**. macOS may block the downloaded app. Building from source is available below; a notarised download remains future work. This is a standalone app, not an Audio Unit plug-in.

The Mac wrapper uses version 0.1.x; the shared instrument currently shows v1.49 inside its screens. Both are early-stage work. See [verification notes](VERIFICATION.md) for the actual test coverage.

## Build

On macOS 13 or later, install the Xcode command-line tools, Git and Python 3:

```sh
python3 mac/scripts/build.py
open "mac/dist/OCKM GENERATOR.app"
```

The first build downloads the exact commits in `dependencies.json`, including
their pinned submodules. Later builds can use `--skip-fetch`. Builds target the
current Mac's architecture; the initial tested build is Apple Silicon.

## Play

The existing instrument screens, sounds, generators, scenes, arrangement and
export controls are retained. Start with **build**, choose a style, then play.
Space starts/stops, Command-S saves a scene, Command-O opens the projects screen.
Command-1/2/3 open the builder, perform screen and mixer.
Command-4/5/6/7/8/9/0 open drums, bass, lead, chords, samples, FX and arrangement.
Command-E opens export options; Command-comma opens instrument settings.

Performance keys: 1–8 mute the drum tracks; 9, 0, minus and equals mute bass,
lead, chords and samples. R toggles rise, W rewinds, hold D for drop and B for
beat repeat. Z/X/C/V/N/M play recipe pads A–F with the same tap/hold behaviour
as the screen. Held effects release on key-up or when the app loses focus.
Help > Keyboard Shortcuts (Command-K) shows the complete reference.

Audio follows the Mac's default output. Select physical or virtual MIDI devices
from the Mac **MIDI** menu, then set channels, clock and MIDI learn in the shared
instrument settings. No MIDI devices are connected until selected. Use Refresh
Devices after connecting hardware.

**File > Show Project Files** opens the Mac working folder:

`~/Library/Application Support/OCKM GENERATOR/Workspace`

Projects, samples and settings live there, outside the app bundle and source
checkout. App updates refresh managed engine files and preserve those user files.
Quit keeps unsaved edits in the existing recovery stash. Saving a scene is still
an explicit action. File > Show Exports opens rendered files.

## One shared instrument, two hosts

The existing root `voices/`, `seq/`, `ui/`, `lab/` and `tools/build.py` remain the
shared source of truth. No directory moves are needed for the Pi.

- `scripts/prepare_runtime.py` builds an isolated engine from those sources. It
  includes a fresh blank project and synthesised sounds, never personal projects,
  sample audio, settings, Pi credentials or recordings.
- `native-ui.lua` is appended to the shared UI only inside the generated Mac
  bundle. It translates its drawing commands and mouse events, without copying
  style tables, generators, scene logic or sound definitions into Swift.
- Swift draws those commands directly with Core Graphics in a native view hosted
  by SwiftUI. It does not open a Pd window, web view or plugdata process.
- A C++ worker owns Pd/Lua. The hardware audio callback only drains a preallocated
  audio buffer. UI rendering, saves and engine changes never lock that callback.
- CoreMIDI connects the engine's MIDI to the Mac's selected endpoints.

This first version keeps the touchscreen layout, scaled to the Mac window. It
does not yet replace each control with a standard SwiftUI control; full VoiceOver
navigation, desktop-specific layouts and multiple simultaneous project windows
remain future work. The Pi's USB gadget interface is hardware-specific and is
not installed on Mac. Stereo playback and file exports are the Mac routes today.

The audio buffer adds roughly 21 ms at 48 kHz before the hardware buffer. Very
slow file operations may exhaust it; Help > Engine Diagnostics reports underruns.
This needs listening and hardware validation before a public performance release.

## Verification

`Tests/engine_smoke.cpp` runs the actual bundled engine in an isolated workspace:
generation, playback, native drawing and scene saving. The existing plain Lua
generator tests are also reusable. Full Pi regression tests remain under `tests/`.
Run the Mac checks with `python3 mac/scripts/test.py` after building.

## Dependencies and licence

OCKM remains GPL-3.0. Dependency licence notices are bundled under
`Contents/Resources/Engine/Licenses`. `dependencies.json` records source locations
and exact revisions. The build contains documented compatibility adjustments:
pd-lua text/path helper replacements and removal of a noisy Pd allocation diagnostic.
Keep these build instructions and dependency sources available with distributions.
