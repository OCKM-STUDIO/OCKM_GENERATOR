# Handover: working on OCKM GENERATOR

This is a developer's map of the project: where things live, how to build, test and deploy, the traps that have already cost time, and what's next. The [manual](manual.md) covers what every screen and hook does; [CONTRIBUTING](../CONTRIBUTING.md) has the ground rules. Read both, then this.

State at handover: **v1.49** (30 October 2026), 139 tests passing.

## Who it's for, and how to work with Simon

Simon designs and plays it; the code has been written with an AI pair. He works in short rounds: tries it on the Pi, sends notes, wants them acted on.

- **Writing:** plain, conversational UK English, punchy sentences, no em dashes, no jargon. That goes for on-screen text, docs, changelog and messages to him
- **Controls must be impactful.** If a knob or effect is subtle, it's wrong. Measure it (see "Checking sound" below)
- **Easy beats deep.** One or two taps for anything
- **Batch small changes** into one version: each version has a fixed overhead (tests, docs, ship)
- **Big or ambiguous jobs:** discuss first, and show mock-ups (PNG at 960x600 in the app's style) before building screens. Small, clear requests: just do them
- **Every version:** bump `VERSION` in `ui/ockm-ui.pd_lua`, add a `CHANGELOG.md` entry, update `docs/manual.md`, run the tests, then ship to the Mac repo and the Pi

## Native Mac preview (8 November 2026)

`mac/` now contains a SwiftUI/AppKit host, C++ libpd audio bridge, CoreMIDI
connections, keyboard performance controls and an app icon. The Pi entry point
and shared Lua/Pd source locations stay unchanged. The Mac build regenerates
its own isolated runtime and appends `mac/native-ui.lua` to the shared UI, so
screens and musical/project behaviour are not duplicated in Swift.

Read `mac/README.md` for build steps and `mac/VERIFICATION.md` for tested scope.
The app is a private preview in `OCKM-STUDIO/OCKM_GENERATOR`; do not make it public
until Simon has tried it and explicitly asks. Mac player files are separate from
this checkout, under Application Support/ OCKM GENERATOR/Workspace.

## The shape of it

| Layer | Where | Notes |
|---|---|---|
| Sound engine | Pure Data, **generated** by `tools/build.py` into `OCKM_GENERATOR.pd`, `voices/`, `seq/` | Never edit the `.pd` files by hand |
| Musical decisions | pd-lua generators: `seq/ockm-chordmaker.pd_lua`, `seq/ockm-linemaker.pd_lua` (hand-written), `seq/ockm-chordnotes.pd_lua` (generated from `CHORD_LUA` in build.py) | Write pattern tables when a setting changes, never at step time |
| Screens | `ui/ockm-ui.pd_lua`, one pd-lua object, hand-written (about 5,600 lines) | build.py fills its `PRESETS` block between markers |
| Save/load | `seq/ockm-store.pd` (generated, "settings store" section of build.py) | Keys listed in `PROJECT_KEYS` and `PATTERN_KEYS` in build.py |
| Tests | `tests/run_tests.py` (Pd headless), `tests/lua/` (plain Lua), `tests/ui_preview.py` + `tests/ui_mock.lua` (draws screens to PNG without Pd, in Pd's fonts as the Pi does), `tests/ui_review.py` (finds text spilling out of boxes, lines through words, boxes overlapping or touching; the test screens_have_no_collisions keeps it at zero) | |
| Pi | `tools/pi/` start, kiosk and restart scripts | Pi 5, 10" Touch Display 2, DAC Pro |

Everything talks over named Pd messages, all prefixed `ockm-` (see the manual's "Named hooks"). The UI only sends and listens to those.

### build.py, by section

Search for `# =================` to jump between sections: track gate, oscillators, bass core and engines, lead engines, rewind and beat repeat (`ockm-stutter`), bus effects (`ockm-busfx`), master effects, reverb, MIDI clock, shared presets (`PRE`, `PROGS`, `CHORD_LUA`), part lengths, LFO, chorus, chord sequencer, chord generator, drum grooves, chord sound (`chord_voice`, `CHORD_ENGINES`, the two-hand `-lh` copies), settings store, project files. The main patch is built near the top (clock, mixer, master chain with the gap/hush, the `SYN` loop for bass, lead and chord).

Helpers: `P()` builds a patch (`add` returns an object index, `con(a, outlet, b, inlet)`), `D` is an escaped `$` for abstraction arguments.

### ui/ockm-ui.pd_lua, by section

Sections start with `-- ------------------------------------------------------------------`. The model: `ui:layout()` builds a list of widgets for the current screen (`add{ kind=..., x, y, w, h, label, tap=function... }`); `ui:draw(g, w)` paints each kind; `ui:press/move/release` handle touch, using the same list. State the screen shows lives in `self.v[hook]` (every hook in `ui:hooks()` is listened to). `self:send(hook, value)` sets it and tells Pd.

Screens: `live` (perform), `fx`, `mixer`, `vox`, `compose` (build), `drums`, `synth` (bass/lead/chord by `self.part`), `arrange`, `project`, `setup` (settings). Pop-up sheets: `self.sheet` (`export`, `eq`, `fxset`, `pmore`, `vpick`, `vexport`, `slotpick`).

Key systems and where to find them:
- **Styles:** `STYLES` table and the function that applies one
- **Macros:** `default_settings().macros`, `TARGETS`, `macro_down` / `macro_go` / `macro_end` / `macro_restore` / `on_bar`. Slots: `me.slots` (six since v1.49, A-F on layout_live; migration `did.six`). Slot numbers 1-6 are the pads, 7 is the editor's try it, 8 an arrangement's join
- **MIDI out:** `seq/ockm-midiout.pd_lua` (one per part; `drums` since v1.49, fed by `ockm-drums-notes-out <slot> <strength>` from each drum row after its nudge pipe; the row's audio outlet sits behind a spigot shut by `ockm-drums-midi 1`). UI: `layout_set_midiout`, `ui.MOUT_PARTS`, `ui.MOUT_KITS`, `midiout_all` (sequencer mode), `midiout_kit`. The clock out runs through a `pipe` of stepms/4 in the MIDI clock patch
- **Top tabs:** `TABS` and `layout_top` (v1.49: three blocks, making / playing / arrange, each on a `plate`; a tab's 5th field is the gap before it, which starts a new block). Tests tap tabs by position, so moving them means remapping those taps
- **Bus effects:** `BUSES`, `BFX`, `bfx_pad`, `layout_fx` (and the pad on `layout_live`). v1.49 the gate (type 4): `busfx_effect` in build.py, driven by `r ockm-step` (each step schedules that step's chops on a vline~), pattern buttons in `layout_fxset` (`ui.GATE_PATS`); test gate_chops_the_music_in_time
- **Projects and scenes:** `save_variation`, `clean_saved`, `proj_groups`, `layout_project`, `preview_play` / `preview_end` (the stash), `var_*` helpers. Scenes are folders `<date>-<name>`, `<...>-v2`...; letters come from `scene_letter`
- **Arrange (versions):** `vers_load` / `vers_save`, `arr_play` / `arr_bar` / `arr_stop`, `layout_arrange`, `TR_BUILTIN`, `TR_MUTES`
- **MIDI learn:** `learn_desc`, `midi_in`, `learn_norm`, `layout_learnbar`, `layout_set_midi`. Stored in `self.me.midi`, saved to `my-settings.lua`

## Everyday commands

```
python3 tools/build.py                       # rebuild every generated file (add --ui-scale 2 on the Pi)
PDLUA=/path/to/pd-lua python3 tests/run_tests.py           # everything, about 10 minutes
PDLUA=/path/to/pd-lua python3 tests/run_tests.py arrange   # just the tests whose names contain "arrange"
python3 tests/ui_preview.py out dark          # every screen as a PNG in out/: look at any you changed
lua5.4 tests/lua/test_chordmaker.lua .        # plain-Lua generator tests (run_tests.py runs these too)
```

**Where to run them:** the Pi has everything the tests need (vanilla `pd`, pd-lua, Lua 5.4, Python with Pillow and numpy): `ssh simon@ockm.local 'cd OCKM_GENERATOR && python3 tests/run_tests.py <name>'`. The full run takes about 10 minutes; run it with the app idle, or run just the tests for what you changed. Simon's Mac has plugdata (to play it) but not command-line Pure Data, so the tests don't run there unless vanilla Pd and pd-lua are installed.

`run_tests.py` copies the built folder to a temp directory per test, so your projects are safe. Tests drive the screen with `ockm-ui-test tap <x> <y>` (coordinates in the 960x600 logical screen), `drag`, `press` and `release`, and read Pd messages with `h.show(...)` and `printed(out, name)`.

The preview list (`SHOTS` in `ui_preview.py`) is cumulative: each shot continues from the last, so a tap meant for one screen can land on another if a tab moves. `touchscreen_screens_draw` checks the number of unique shot names.

## Shipping

Simon's working copy lives on his Mac at `~/Projects/OCKM_GENERATOR` (a git repo, not yet pushed to GitHub). The Pi is `simon@ockm.local`, with the project in `~/OCKM_GENERATOR`; an SSH key is kept in `.pi/ockm_key` in the Mac repo (git-ignored).

To ship a version: commit the changed sources and the rebuilt patches on the Mac. Simon has a helper, `~/ockm-ship.sh <tag> "<message>"`, that rebuilds in a scratch copy, copies changed generated files in, commits and tags. Then update the Pi:

```
rsync tools/build.py, ui/ockm-ui.pd_lua and tests/ (and any hand-written seq/*.pd_lua you changed) to simon@ockm.local:OCKM_GENERATOR/
ssh simon@ockm.local 'cd OCKM_GENERATOR && chmod +x tools/pi/*.sh && python3 tools/build.py --ui-scale 2 && tools/pi/ockm-restart.sh'
```

Always keep `tools/pi/*.sh` executable on the Pi: if `ockm-session.sh` can't run, the Pi boots to a login screen instead of the box (v1.41, 26 October).

If git leaves `.git/*.lock` files after a commit, remove them before the next one.

## Checking sound

Nobody can listen for you, so measure. Render with the test harness (record to WAV with `h.record(path)`, play, stop) and compare RMS and band energy (numpy FFT) between settings. Every synth knob must move the sound clearly (`every_synth_knob_makes_a_difference`: tone or length change, level within 10 dB). Level-match effects so turning them up doesn't just make things louder. CPU: time a 30-second headless render on the Pi (`pd -nogui -nosound -batch -lib pdlua`); the audio engine is a few percent of one core, and drawing the screen is most of the rest.

## Traps (each has cost time)

- **build.py comments:** never put a `#` comment after statements on a line with several `;`-separated statements: it swallows the code after it
- **Escapes:** inside an f-string, a Pd comma or semicolon is `\\,` / `\\;`. In a message box `$1` is the message's argument, not the abstraction's: use `[f $2]` to get an abstraction argument
- **tabwrite** takes its index on the right inlet; an argument doesn't set it
- **vcf~** falls apart near the top of the range: use `bob~` or the `svf()` state-variable filter
- **expr** works in 32-bit float (`sinf`), so Lua emulations of Pd maths can differ in the last digit
- **Pressing play while playing** restarts the loop from step 0
- **Lua locals are file-order:** a `local` defined further down the file is `nil` inside functions defined above it. `ockm_base` and `ockm_ver` are globals for this reason
- **`self.preview`** is a method (drum audition): the project page's set-aside state is `self.pv`
- **Unsaved tracking:** `psend` marks the project unsaved unless the hook is in `NOT_CHANGES` or matches the exclusions next to it
- **A new blank project saves itself** about 300 ms after it's made (`apply_new_defaults`): tests must wait before changing things
- **Mutes and the bar:** macros queue mutes to the next bar (`set_mute_bar`); arrange transitions start on a bar line and need their mutes now, so they pass `now` to `macro_go` and switch the mute timing for a moment
- **Pd's MIDI-in order:** `ockm-midi-cc` arrives as value then controller number
- **Saved projects must keep loading:** presets, engines and rhythms are stored by number. Don't renumber; hide and map old values instead

## What's next

**Instruments (v1.39, agreed with Simon 25 October 2026).** The box becomes three instruments plus the groovebox, picked from a start screen: **Bass** (after the Erica Synths Bassline DB-01, not a copy), **Analog** (after the SH-101 and S-1) and **drmz** (the drum machine, v1.40). Each instrument: a **perform** screen with every control on one page, a **steps** sequencer and a **generator**, like the groovebox. Where things are:
- Sound: `voices/ockm-inst-bass.pd` and `ockm-inst-analog.pd`, built in the "instruments" section of build.py (`INST_PARAMS` lists every setting). Notes, envelopes, glide and accent: `seq/ockm-instvoice.pd_lua`. Steps, generator and arpeggiator: `seq/ockm-instseq.pd_lua`. Analog's four voices: `seq/ockm-instpoly.pd_lua` in front of `voices/ockm-inst-analog-voice.pd`. drmz: `voices/ockm-drmz.pd` (eight `ockm-drum z<n>`) and `seq/ockm-drmzseq.pd_lua`, generated from `seq/ockm-drmzseq.lua.in` with the grooves written in. MIDI out: `seq/ockm-midiout.pd_lua`, one per part
- CPU: the filters are bob~ and vcf~. fexpr~ filters cost about five times as much: don't bring them back
- Screens: the "instruments" section of `ui/ockm-ui.pd_lua` (`ui.INSTK`, `layout_home`, `layout_inst`, `layout_inst_steps`; widgets `knob`, `islider`, `istep`, `imod`, `tile`, `house`). The file is at Lua's 200-locals limit: put new constants in a table (`ui.INSTK`), never a new top-level `local`
- `ockm-inst-mode 1` takes the groovebox out of the mix while an instrument is open; `<prefix>-on` switches an instrument's processing on (`switch~`). Prefixes: `ib` Bass, `ia` Analog, `iz` drmz. Keyboard notes go to `<prefix>-play` (not `-key`, which the filter's key tracking uses)
- **pdlua trap:** `pd.send` to a name nobody receives, from inside another send, errors with "invalid atoms table". Give every name a Lua object sends to a receiver
- Sound versions (v1.49): `SOUNDS` in build.py (engine, k1-k4, drive, measured trim) is written into the UI as `ockm_SOUNDS` (trims made relative to the engine's first version, whose trim becomes the engine's gain, `ENGINE_GAIN`, applied in the patch via `ockm-<part>-egain` in ockm-gate). Tapping a selected engine button steps its versions (`ui:tap_engine`). Re-measure with tools/measure_sounds.py after changing any version or engine; tests sounds_sit_at_one_level and synths_sit_at_similar_levels check it
- A lead following the chords keeps at least 4 bars when the chords fit themselves to a progression: the chordmaker sends `ockm-chord-fitting <n>` just before `ockm-chord-len <n>`, and the lead's linemaker takes max(n, 64) for that one length. A length set by hand goes to every following part as it is; the bass always takes the chords' length
- The 4 bar build: `BUILD` in build.py (64 steps per drum sound, written into table ockm-buildx), run by seq/ockm-build.pd_lua (armed by `ockm-build 1`, starts on the next `ockm-bar`, off by itself after four bars, into v ockm_build_on / ockm_build_bar). Each drum row reads it after the fill (`bsel`). Values of 10 or more carry a roll (22 = accent twice): `lane.split` in seq/ockm-lane.pd_lua. The recipe's move is the switch target "snare build"
- v1.49 PERF-1 extras: the rush is `RUSH` in build.py (the second 512 values of ockm-buildx, `ockm-build 2`, v ockm_build_pat); crash and key are recipe fields (`crash`, `key`; `ui:drop_key`, `ui:key_back`); links are in the bass and chord LFO patches (seq/ockm-lfo-*.pd, ockm_<part>_kl added to knob 1; ockm-snare-hit comes from the drum rows); drift, flam/swell and humanize are in seq/ockm-lane.pd_lua (`lane.drift_value`, `lane.hits`); slice remaps the drum rows' step in the main patch (v ockm_slice_m)
- Restarting Pd loses unsaved work unless it's kept: always restart with tools/pi/ockm-restart.sh (it sends "keep;" to UDP 3091 first; the store patch's netreceive passes only "keep" on, as ockm-keep; the UI stashes and leaves stash/kept-on-restart.txt, and unstashes at the next start). Never `pkill pd` by hand while Simon is working
- Tests need pdlua: in the cloud workspace it's at /tmp/claude-0/pd-lua, so run with PDLUA=/tmp/claude-0/pd-lua or every Lua object fails to create
- USB audio (v1.49 fix): never leave Pd's outputs linked to the USB gadget's ports while no computer is attached (`/sys/class/udc/*/state` isn't "configured"): the gadget can't run, PipeWire halts the graph, and Pd, driven by it, freezes (screen stops responding; /tmp/ockm-pd.log fills with "watchdog: signaling pd"). ockm-audio-links.sh links and unlinks by that state. Pd's messages are in /tmp/ockm-pd.log
- Screen text on the Pi: Pd rounds a text size down to its own fonts (8, 10, 12, 16, 24, 36), each a fixed width: 5, 6, 7, 10, 14, 22 (so 11 draws 6 wide, 14 draws 7). Use `ockm_charw(size)` to measure, never `#s * size * 0.6`. Text wider than the width given to draw_text wraps onto more lines
- Built in v1.49 (from the PERF-1 firmware, github.com/deamonSLINKY/PERF-1): safe saves (write `<file>.new`, then rename: `ockm_write` in the UI, `safe_write` in build.py's store); call and answer in seq/ockm-linemaker.pd_lua (`lm.answer`, hook `ockm-<part>-answer`); drum lanes in seq/ockm-lane.pd_lua (chance, thin, when, drift; rolls in table ockm-pat-dN-rat, hook `ockm-rat`), sitting in each drum row between the pattern and the voice. Built since: the mood (engine and dial) and the answer button (one cycling button on the bass and lead tabs, in layout_synth's status row). All the v1.49 mock-ups are built: the drum lane panel and rolls (`ui:layout_drumlane`, `self.dpanel`, `self.lane == "roll"`, hook `ockm-rat`), and the show page (`self.screen == "show"`, `ui:draw_showpage`, from the menu: a circle of fifths, our own design, deliberately not PERF-1's sigil and eye). The master compressor and look-ahead limiter are in the main patch after the volume (build.py, by the `vol` object); the delay loop filters, feedback cap and fx-return duck are in voices/ockm-fx.pd (`P.dis` takes a connection out to insert into it)
- Built in v1.48: USB audio out (manual, USB audio out): 9 channels to a computer through the splitter, via PipeWire. Next: give the USB device a proper name on the Mac (it shows as "Capture Inactive"; try `if_ctrl_name` and the terminal names in the uac2 function). Don't stop Pd with pkill on the Pi: the session drops to the desktop; use tools/pi/ockm-restart.sh, or `sudo systemctl restart lightdm`
- Built in v1.47: the projects table, the project name under the tempo, new projects' lead empty
- Built in v1.45 (decided 29 October, replacing the modes plan): one powerful groovebox. The Bass synth is bass engine 8 and the Analog lead engine 7 (`synth_engine` in build.py, `seq/ockm-partvoice.pd_lua`); edit opens the synth's page over the groovebox; MIDI channels in play the bass and lead (`ui:midi_part_note`); drmz is the drums tab's pads view; the start screen is gone. Next: the filter move per step on the bass and lead tabs
- Built in v1.43: shut down in the menu (Pi only, two taps; `OCKM_SHUTDOWN_CMD` stands in for tests). The full suite now takes about ten minutes here: run it in the background
- Built in v1.42: the groovebox's whole generator on the Bass and Analog build tabs (style, progression, mutate, evolve). Decided 26 October: projects will each belong to one mode (groovebox, Bass, Analog, drmz), every mode gets the same generator, instruments differ by deeper sound control; Bass stays as it is (no extra engines), Analog is the lead. Not built yet: the modes and their project lists, drmz's build tab with the groovebox's drum generator
- Built in v1.41: a build tab per synth (a second ockm-linemaker writes the instrument's steps), drag a step for its note, drmz voices' own sounds at start-up (scenes from before drmz had none: watch for this with any new setting, as a pattern recall doesn't reset settings it doesn't have)
- Built in v1.40: saved sounds, the keys tab, Analog's unison/chord/poly, MIDI out for bass, lead and chord, drmz
- Not built yet: drums over MIDI out (for a TR-8S), drmz's own kits and a drum-lab page per voice

**Vox is in (v1.34).** Spoken lines on the corner tile of perform, a twelfth mixer strip, on the music bus. Every 4, 8 or 16 bars it plays the next line from the set, whole. Deep house uses hooks, Chicago uses jack, peak time and hard techno use techno lines. The lines are rendered once with Piper (`tools/make_vox.py`, `tools/vox_lines.txt`) into `samples/vox/`. The Pi only plays the files.

Still later, not built: a vocoder so the chord synth sings the phrase, and making new phrases on the box. Both need a voice engine on the Pi. More lines can be added to the text file and rendered again. Only voices whose licence allows release.

Agreed or raised, not built:
- MIDI export of a version (audio export works)
- Names for scenes (they're letters; sections in a version can be named)
- MIDI learn for controls inside pop-up sheets; map banks (a pad that flips between maps); relative encoders
- Stereo from the bus effects onwards, then flanger and phaser (agreed for later)
- MC-101 style "pulses" (tempo-synced pulsing patches): an idea Simon loves, not designed yet
- A synth "expand" page with more controls (discussed, open)
- Drum sample controls (tone, start, length) haven't had the knob audit the synths had
- Ear-testing each sound one by one (the lead's analogue engine was done; the rest are measured but not yet heard by Simon)
- Playing drums and synths live from pads and keys
- Publishing: the repo (OCKM GENERATOR, as OCKM_GENERATOR on GitHub, GPL-3.0) hasn't been pushed to GitHub yet; a Reddit post for collaborators is waiting on that
