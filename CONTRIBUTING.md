# Contributing

Thanks for looking. Issues, ideas and pull requests are all welcome. If you're planning something big, open an issue first so we can talk it through.

## The one rule: the .pd files are generated

Every `.pd` patch in `voices/`, `seq/` and the main `OCKM_GENERATOR.pd` is written by `tools/build.py`. Don't edit them by hand in Pd: the next build overwrites them. Change the builder instead, then rebuild:

```
python3 tools/build.py
```

Commit the builder and the rebuilt patches together. Some Lua is generated too: `seq/ockm-chordnotes.pd_lua` (by `tools/build.py`), and the drum lab's `lab/` patches, `lab/ockm-lab.pd_lua` and `voices/ockm-labdrum.pd_lua` (by `tools/build_lab.py`).

Hand-written: `ui/ockm-ui.pd_lua` (all the screens; `tools/build.py` also writes its preset tables into it between markers), the scripts in `tools/` and `tools/pi/`, and the tests.

## Before a pull request

```
python3 tests/run_tests.py       # needs vanilla Pure Data (pd) and pd-lua; set PDLUA=<pd-lua folder> if it isn't found
python3 tests/ui_preview.py out  # draws the screens to PNGs (needs lua and Pillow): check any screen you touched
```

All tests should pass. If you change what something does, change or add the test that checks it.

## House style

- **Plain Pure Data.** Vanilla objects only (plus pd-lua), so the same patch runs in plugdata and on the Pi
- **Saved projects keep working.** Presets, engines and rhythms are stored by number: don't renumber them. Retire an option by hiding it from the screen, and map old values to their replacement on load (the UI has `RETIRED` and the hidden lists for this)
- **Cheap on the Pi.** Sound and drawing share one core on a Raspberry Pi 5. Measure before adding anything that runs per sample in every voice
- **Easy beats deep.** If a feature takes more than a tap or two, rethink it
- **Plain words on screen and in docs:** UK English, short sentences
- **Changelog:** add a line to `CHANGELOG.md` for anything a player would notice

## Where things are

The [manual](docs/manual.md) explains every screen, engine and internal hook (`ockm-*` names), and how the parts are wired together.

## Working with AI

Most of this code was written with Claude as a coding partner. You're welcome to work the same way or not at all; either way, you're responsible for what you submit: run it, test it, listen to it.
