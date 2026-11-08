# Contributing

OCKM is a very early alpha. Issues, musical feedback, documentation improvements and small pull requests are all welcome. If you're planning something big, open an issue first so we can talk it through.

## The one rule: the .pd files are generated

Every `.pd` patch in `voices/`, `seq/` and the main `OCKM_GENERATOR.pd` is written by `tools/build.py`. Don't edit them by hand in Pd: the next build overwrites them. Change the builder instead, then rebuild:

```
python3 tools/build.py
```

Commit the builder and the rebuilt patches together. Some Lua is generated too: `seq/ockm-chordnotes.pd_lua` (by `tools/build.py`), and the drum lab's `lab/` patches, `lab/ockm-lab.pd_lua` and `voices/ockm-labdrum.pd_lua` (by `tools/build_lab.py`).

Hand-written: `ui/ockm-ui.pd_lua` (all the screens; `tools/build.py` also writes its preset tables into it between markers), the scripts in `tools/` and `tools/pi/`, and the tests.

## Musical logic lives in Lua

Pd makes the sound and keeps time; the decisions about what to play are Lua. Generators are pdlua objects that write the pattern tables when a setting changes (never at step time), so timing stays with Pd:

- `seq/ockm-chordmaker.pd_lua`: the chord generator (rhythm, progression, rate, push)
- `seq/ockm-chordnotes.pd_lua`: chord voicing
- `seq/ockm-linemaker.pd_lua`: the bass and lead generator (rhythms, riffs, tunes, lock, density, mutate, rests, slides, the lead's decorations)

Each keeps its logic in pure functions (no Pd calls), tested in plain Lua in `tests/lua/` with a small stand-in for pdlua. Preset lists still live in `tools/build.py`, which fills each file's `PRESETS` block. New musical logic goes in Lua, not in Pd `expr` chains.

## Before a pull request

```
python3 tests/run_tests.py       # needs vanilla Pure Data (pd) and pd-lua; set PDLUA=<pd-lua folder> if it isn't found
python3 tests/ui_preview.py out  # draws the screens to PNGs (needs lua and Pillow): check any screen you touched
```

All tests should pass. If you change what something does, change or add the test that checks it.

For native Mac changes, build with `python3 mac/scripts/build.py`, run
`python3 mac/scripts/test.py`, then check the affected screens and controls in the
app. Include the platform, commands run and any checks you could not complete in
your pull request. The [Mac guide](mac/README.md) explains the shared engine boundary.

## Credit and shared sources

Keep musical behaviour in the shared Pd/Lua sources so Mac and Pi benefit together.
Preserve existing credits, including the PERF-1 references. When adapting work or
ideas from another project, link the original and describe the connection; retain
any required notices with the code. Avoid committing personal projects, recordings,
sample packs, device credentials or local settings.

## House style

- **Plain Pure Data.** Vanilla objects only (plus pd-lua), so the same patch runs in plugdata and on the Pi
- **Saved projects keep working.** Presets, engines and rhythms are stored by number: don't renumber them. Retire an option by hiding it from the screen, and map old values to their replacement on load (the UI has `RETIRED` and the hidden lists for this)
- **Cheap on the Pi.** Sound and drawing share one core on a Raspberry Pi 5. Measure before adding anything that runs per sample in every voice
- **Easy beats deep.** If a feature takes more than a tap or two, rethink it
- **Plain words on screen and in docs:** UK English, short sentences
- **Changelog:** add a line to `CHANGELOG.md` for anything a player would notice

## Where things are

The [manual](docs/manual.md) explains every screen, engine and internal hook (`ockm-*` names), and how the parts are wired together. [docs/HANDOVER.md](docs/HANDOVER.md) is the developer's map: where code lives, how to build, test and deploy, the traps, and what's next.

## Working with AI

This project uses Claude and OpenAI Codex as coding partners. You're welcome to work the same way or not at all; either way, you're responsible for what you submit: run it, test it, listen to it.
