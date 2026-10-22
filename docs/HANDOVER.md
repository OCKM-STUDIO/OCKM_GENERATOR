# Handover: working on OCKM_GNR8R

This is a developer's map of the project: where things live, how to build, test and deploy, the traps that have already cost time, and what's next. The [manual](manual.md) covers what every screen and hook does; [CONTRIBUTING](../CONTRIBUTING.md) has the ground rules. Read both, then this.

State at handover: **v1.31** (22 October 2026), 114 tests passing.

## Who it's for, and how to work with Simon

Simon designs and plays it; the code has been written with an AI pair. He works in short rounds: tries it on the Pi, sends notes, wants them acted on.

- **Writing:** plain, conversational UK English, punchy sentences, no em dashes, no jargon. That goes for on-screen text, docs, changelog and messages to him
- **Controls must be impactful.** If a knob or effect is subtle, it's wrong. Measure it (see "Checking sound" below)
- **Easy beats deep.** One or two taps for anything
- **Batch small changes** into one version: each version has a fixed overhead (tests, docs, ship)
- **Big or ambiguous jobs:** discuss first, and show mock-ups (PNG at 960x600 in the app's style) before building screens. Small, clear requests: just do them
- **Every version:** bump `VERSION` in `ui/ockm-ui.pd_lua`, add a `CHANGELOG.md` entry, update `docs/manual.md`, run the tests, then ship to the Mac repo and the Pi

## The shape of it

| Layer | Where | Notes |
|---|---|---|
| Sound engine | Pure Data, **generated** by `tools/build.py` into `OCKM_GENERATOR.pd`, `voices/`, `seq/` | Never edit the `.pd` files by hand |
| Musical decisions | pd-lua generators: `seq/ockm-chordmaker.pd_lua`, `seq/ockm-linemaker.pd_lua` (hand-written), `seq/ockm-chordnotes.pd_lua` (generated from `CHORD_LUA` in build.py) | Write pattern tables when a setting changes, never at step time |
| Screens | `ui/ockm-ui.pd_lua`, one pd-lua object, hand-written (about 5,600 lines) | build.py fills its `PRESETS` block between markers |
| Save/load | `seq/ockm-store.pd` (generated, "settings store" section of build.py) | Keys listed in `PROJECT_KEYS` and `PATTERN_KEYS` in build.py |
| Tests | `tests/run_tests.py` (Pd headless), `tests/lua/` (plain Lua), `tests/ui_preview.py` + `tests/ui_mock.lua` (draws screens to PNG without Pd) | |
| Pi | `tools/pi/` start, kiosk and restart scripts | Pi 5, 10" Touch Display 2, DAC Pro |

Everything talks over named Pd messages, all prefixed `ockm-` (see the manual's "Named hooks"). The UI only sends and listens to those.

### build.py, by section

Search for `# =================` to jump between sections: track gate, oscillators, bass core and engines, lead engines, rewind and beat repeat (`ockm-stutter`), bus effects (`ockm-busfx`), master effects, reverb, MIDI clock, shared presets (`PRE`, `PROGS`, `CHORD_LUA`), part lengths, LFO, chorus, chord sequencer, chord generator, drum grooves, chord sound (`chord_voice`, `CHORD_ENGINES`, the two-hand `-lh` copies), settings store, project files. The main patch is built near the top (clock, mixer, master chain with the gap/hush, the `SYN` loop for bass, lead and chord).

Helpers: `P()` builds a patch (`add` returns an object index, `con(a, outlet, b, inlet)`), `D` is an escaped `$` for abstraction arguments.

### ui/ockm-ui.pd_lua, by section

Sections start with `-- ------------------------------------------------------------------`. The model: `ui:layout()` builds a list of widgets for the current screen (`add{ kind=..., x, y, w, h, label, tap=function... }`); `ui:draw(g, w)` paints each kind; `ui:press/move/release` handle touch, using the same list. State the screen shows lives in `self.v[hook]` (every hook in `ui:hooks()` is listened to). `self:send(hook, value)` sets it and tells Pd.

Screens: `live` (perform), `fx`, `mixer`, `compose` (builder), `drums`, `synth` (bass/lead/chord by `self.part`), `arrange`, `project`, `setup` (settings). Pop-up sheets: `self.sheet` (`export`, `eq`, `fxset`, `pmore`, `vpick`, `vexport`, `slotpick`).

Key systems and where to find them:
- **Styles:** `STYLES` table and the function that applies one
- **Macros:** `default_settings().macros`, `TARGETS`, `macro_down` / `macro_go` / `macro_end` / `macro_restore` / `on_bar`
- **Bus effects:** `BUSES`, `BFX`, `bfx_pad`, `layout_fx` (and the pad on `layout_live`)
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
ssh simon@ockm.local 'cd OCKM_GENERATOR && python3 tools/build.py --ui-scale 2 && tools/pi/ockm-restart.sh'
```

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

**Next feature, agreed with Simon (22 October 2026): robot voices.** Spoken robot vocal phrases that shuffle, on a new vox track. The plan:
- **Make the phrases offline, once.** Write a few hundred short lines in sets: hooks ("feel it", "all night long"), commands ("move", "jack your body"), spoken lines ("this is the sound of the underground"), counts and numbers. Render each with three or four voices (deep, flat, female...) using Piper text-to-speech (github.com/rhasspy/piper) on a computer, and ship them as WAVs in `samples/vox/<set>/`. Only use Piper voices whose licence allows release (check each voice's model card), and never imitate a real person. The Pi then never runs the voice engine: it only plays files
- **The vox track:** plays one phrase on chosen bars (every 4, 8 or 16), shuffled from the current set, with a send to the delay and a pitch amount. Phrases are one-shots, played whole (no chopping: an earlier decision). Its settings are saved with the scene
- **Styles pick the set** (peak time and hard techno: techno lines; Chicago: jack; deep house: soulful hooks)
- **Mixer and buses:** a twelfth track on the mixer, on the music bus by default
- **Later:** a vocoder in Pd so the chord synth sings the phrase (Daft Punk, Laurent Garnier), and an on-screen way to make new phrases on the box
- Check impact like everything else: the phrase must sit clearly in the mix, level-matched, and the track must cost little CPU on the Pi

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
- Publishing: the repo (OCKM_GNR8R, GPL-3.0) hasn't been pushed to GitHub yet; a Reddit post for collaborators is waiting on that
