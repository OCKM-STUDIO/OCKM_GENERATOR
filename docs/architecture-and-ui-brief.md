# OCKM_GENERATOR — architecture review and next UI

Status: **the three screens are built** (v0.13, `ui/ockm-ui.pd_lua`). The Pi bring-up list is still to do. The v0.12 panel is kept in `pd test-panel`, and the engine is in `pd engine`.

This file is the brief to work from. `README.md` is the reference for hooks, engines, and the data model. Where they disagree, this file is the decision for the next UI and for the Pi port.

Current version: **v0.12** (13 October 2026).

---

## What this is

A drum machine and three easy synths in one Pure Data patch, meant to run on a Raspberry Pi 5 with a touchscreen and a few knobs. It is built and tested on a Mac in plugdata. The Pi hardware is not bought yet. Audio is an iRig Pro Duo. The favourite screen is the official 10" Touch Display 2 (1920×1200). The 7" is the compact option (landscape 1280×720, or 800×480 for the older official 7").

Eleven tracks share one clock: eight drum slots (d1–d8), plus bass, lead, and chord. Eight pattern slots, each up to 128 steps, shown 16 at a time. Swing, accents, generators, a DJ filter, drive, delay, reverb, and MIDI clock (leader or follower) are already in the patch.

Open `OCKM_GENERATOR.pd` in plugdata. Keep the folder together.

---

## How it is built

The `.pd` files are generated. Structural changes go in Python, then:

```bash
python3 tools/build.py
```

`tools/build.py` writes the voices, sequencers, store, and main patch. `tools/panel.py` writes the front panel (`seq/ockm-panel.pd`). Dark is the default. Light is `python3 tools/build.py --theme light`.

Do not rewire generated `.pd` files by hand. The next rebuild overwrites them. The build only creates project files that are missing. `--reset-patterns` rewrites `projects/default` and deletes saved patterns.

```bash
python3 tests/run_tests.py
```

About 22 checks, headless, vanilla `pd`, on a temporary copy. Saved patterns stay untouched. A change to the panel needs a test that the new screen still drives the engine through the hooks.

### Folders

| Path | Role |
|---|---|
| `OCKM_GENERATOR.pd` | Clock, swing, pattern switching, mixer. Panel at the top, engine below |
| `voices/` | One file per sound, plus `ockm-drum`, `ockm-mono`, `ockm-chord`, reverb, master effects |
| `seq/` | Panel, drum rows, synth sequencers and generators, presets, MIDI clock, settings store |
| `projects/default/` | `project.txt` (tempo, effects, MIDI, accent, drum kit) and `p1.txt`–`p8.txt` |
| `sketches/` | Early experiments. The build does not touch them |
| `tools/build.py`, `tools/panel.py` | The generator |
| `tests/run_tests.py` | Headless checks |

### Rules that already hold

1. Easy to program beats deep. If it takes more than a tap or two, rethink it.
2. Works without a keyboard. Saving included.
3. Plain Pure Data, so it runs in plugdata and on the Pi. This rule is already bent: see `bob~` below.
4. Sequencers say when. Voices make sound. Either can change without the other.
5. Musical by default.

The panel may only talk to the engine through the named `ockm-*` hooks. Display comes back on `ockm-show-*`. That split is what lets a new screen replace this panel without rewiring audio. Knobs should use the same split: send the hook, listen to `ockm-show-*`.

`switch~` turns off the drum sound and the synth engine that are not selected. Eight slots do not mean sixty-four running oscillators.

### Data model

1. **Step.** Drums: off, on, or accent. Bass and lead: note, on, accent, slide. Chord: on or accent, plus a chord root as a scale step.
2. **Track.** d1–d8, bass, lead, chord.
3. **Sound.** A drum slot: sound index, tune, decay, level, sends. A synth: engine, k1–k4, drive (bass and lead) or chord type (chord), sends.
4. **Kit.** The eight drum sounds together.
5. **Pattern.** Steps for all 11 tracks, length (16, 32, 64, or 128), swing, key, scale, generator choices, and the three synth sounds.
6. **Project.** Eight patterns, the drum kit, tempo, master effects, MIDI settings, accent amount.

The drum kit belongs to the project and is shared by every pattern. Synth sounds belong to each pattern. A new empty pattern starts with blank steps and keeps the synth sounds, key, and swing of the pattern you left. Switching patterns keeps unsaved edits in memory. Save writes the current pattern and the project. Revert reloads them from disk.

Chords are worked out as they play from the step's root, the shared key and scale, and the chord type. Changing key does not rewrite the chord pattern. Bass and lead do rebuild when the key or scale changes.

Lengthening a pattern repeats existing steps into the new ones (`ockm-extend`). That behaviour stays.

### Hooks the new UI needs

Full list is in `README.md`. These are the ones the screens use.

| Hook | Does |
|---|---|
| `ockm-play` | 1 start, 0 stop. `ockm-playing` is sent back |
| `ockm-bpm` | Tempo. Store listens as `ockm-tempo`. Shown via `ockm-show-bpm` |
| `ockm-want` | Pick pattern slot 0–7. Switches at the end of the bar, starts at step 1. `ockm-load` is sent with the slot when it loads |
| `ockm-save` / `ockm-revert` | Write or reload |
| `ockm-length` | 16, 32, 64, or 128. `ockm-len` is sent when the active length changes |
| `ockm-page` | Which 16 steps the edit grid shows. 0 is steps 1–16, 1 is 17–32, up to 7 |
| `ockm-step` | Current step as it plays, from 0 |
| `ockm-edit` | One drum step: `slot step value`. Value 0 off, 1 on, 2 accent. Example: `d1 4 2` |
| `ockm-<slot>-sound` | 0 kick, 1 snare, 2 clap, 3 rim, 4 closed hat, 5 open hat, 6 tom, 7 rimshot |
| `ockm-<slot>-tune` / `-decay` / `-level` / `-verb` / `-delay` | That slot. Tune −12 to 12 semitones. Decay in percent, 100 is normal |
| `ockm-root` / `ockm-scale` | Key 0–11 (0 = C). Scale 0–5: minor, major, dorian, phrygian, mixolydian, harmonic minor |
| `ockm-bass-edit` / `ockm-lead-edit` | `step note on accent slide`. Note is MIDI. Example: `0 33 1 1 0` |
| `ockm-chord-edit` | `step value degree`. Value 0 off, 1 on, 2 accent. Degree is a scale step, 0 is the key's root |
| `ockm-<synth>-engine` | Bass and lead: 0 acid, 1 sub, 2 FM, 3 reese, 4 pluck, 5 saw. Chord: 0 stab, 1 organ, 2 pad |
| `ockm-<synth>-k1` … `-k4` | 0–1. Meaning depends on the engine. See README |
| `ockm-bass-drive` / `ockm-lead-drive` | 0–1 |
| `ockm-chord-type` | 0 triad, 1 seventh, 2 sus2, 3 power |
| `ockm-<synth>-rhythm` / `-notes` / `-prog` | Generator choice. Bass and lead use rhythm and notes. Chord uses rhythm and prog |
| `ockm-<synth>-gen` | Rebuild that track across the whole length |
| `ockm-refresh` | Sent after a pattern loads so squares redraw |
| `ockm-show-<name>` | Store pushes the current value. GUI receives this. Do not send it |

Slots are `d1`–`d8`. Synths are `bass`, `lead`, `chord`.

There is one global edit page today (`ockm-page`). The performance view and the focus grids must not share it. See "Swipe" below.

---

## Architectural review

Reviewed against a Raspberry Pi 5, a touchscreen, and the iRig. The sound engine, the pattern store, and the hook layer are the right shape. The part that will not survive the move is the screen.

### Keep

- **Hooks.** Sequencers say when. Voices make sound. The panel only talks through `ockm-*`, with `ockm-show-*` coming back. A new screen and a few MIDI knobs can use that split.
- **Voices that sleep.** `switch~` turns off the unused drum sound and the unused synth engine.
- **Kit versus pattern.** Drum kit on the project. Synth sounds, key, swing, and steps on the pattern. A new pattern keeps the sounds you were using. Already tested.
- **Readable files.** `project.txt` and `p1.txt`–`p8.txt`. Save and revert go through hooks, so the screen never needs a keyboard file dialog.
- **Chords at play time.** A chord step stores a root. Notes follow key, scale, and type.
- **Generators as the fast path, hooks as the precise path.** New fills a track. Edit hooks change one step. The new synth screen needs both.
- **The Python generator, and tests on a temporary copy.**

### Decisions that block a touch port

**1. The panel and the engine are one window.**

`seq/ockm-panel.pd` is graph-on-parent, 1100×800, placed at 0,0 in `OCKM_GENERATOR.pd`. `tools/build.py` then shifts the clock, the old controls, the eight `ockm-row` graphs, and the mixer down by 860px in the same canvas. The saved window is 1140×860, so on a Mac the engine sits just out of sight.

Fullscreen on the Pi shows the guts, including a second set of step toggles. The canvas is about 2000px tall, so a maximised window scrolls or shrinks the panel.

Before the first boot on the Pi, move the engine into a closed subpatch so the window is only the interface. Leave the old number boxes reachable for debugging, off the glass.

**2. The v0.12 panel is a mouse layout.**

Step squares are 24px. Each drum row picks its sound with eight 14px radios. Sliders are 10px tall. Tempo is a number box you drag. The sheet is a fixed 1100×800 and shows drums, three synths, and effects at once.

Touch targets want about 44px. A 10" 1920×1200 screen has the pixels and still fails a finger. A 7" landscape frame is 1280×720 or 800×480, shorter than this panel. Tk scroll and number-box drag fight with touch.

Treat the v0.12 panel as the Mac test surface it already is. The touchscreen is the three screens in the next section. Build those in `tools/panel.py` (or successor modules it calls), still only through the hooks.

**3. The default synths use `bob~`.**

> Checked in v0.13: this one is not a blocker. `bob~` ships with plain Pure Data in its `extra` folder, and the Pi's `puredata` package installs it. The headless tests run on plain Pd and the acid, reese and pluck engines pass. No replacement needed.

Acid, Reese, and pluck are built on `bob~`, a ladder filter from the ELSE library that plugdata bundles. Bass defaults to acid and lead defaults to pluck. Raspberry Pi OS `puredata` does not include `bob~`. A vanilla Pi install opens those engines with a missing filter.

Pick the runtime before drawing pixel-perfect screens.

- **plugdata on the Pi** keeps `bob~` and can show a Pd GUI as a stopgap. Touch will still be weak if the GUI is stock widgets.
- **Vanilla `pd`** matches the tests and the plain-Pd rule, and it needs `bob~` replaced with `lop~` or `vcf~` while you are still on the Mac.

Drawing the touch UI in a toolkit the Pi will not run means building it twice.

### Fix on bring-up

**Saves use a path relative to the process working directory.**

> Checked in v0.13: not the case. `qlist` resolves `read` and `write` from the abstraction's own folder. Starting Pd from another folder and saving still writes to `projects/default`. A `cd` in the start-up script does no harm, but isn't needed.
 `seq/ockm-store.pd` writes `../projects/default/project.txt` and `p1.txt`–`p8.txt` through `qlist`. That path is relative to the process working directory, not the patch file. Plugdata on the Mac usually starts in the right folder. A Pi autostart launched from the home folder writes somewhere else, or fails, with nothing on screen. The startup script should `cd` into the project folder before it starts Pd.

**`expr~` is on the mix all the time.** Master drive, the output limiter, and bass and lead drive are `expr~ tanh`. Sub, pluck, and saw use `expr~` in the voice. Pi 5 can run this patch. `expr~` is still the first thing that forces a bigger USB buffer on the iRig, and a late buffer is what makes knobs feel slow. On the first Pi session, measure at 128 and 256 samples. Add more `expr~` only if that budget is comfortable. Voice count is already in good shape because of `switch~`.

**A drum sound is an index from 0 to 7.** The panel draws that as an eight-way radio. Your own samples (roadmap item 13) need a name and a file. The hook `ockm-<slot>-sound` can grow. The v0.12 radio cannot show a sample name. The drum focus screen below is the place a sample picker goes later. Do not stretch the old radio.

### Watch, not now

**One project, global names.** Everything lives in `projects/default`. Pattern tables are global symbols (`ockm-pat-d1`, `ockm-pat-bass-note`). Right for a single box. A project browser needs a new layer on top of the store. Not a Pi bring-up task.

**Synth steps can already be edited, and the panel never does it.** `ockm-bass-edit`, `ockm-lead-edit`, and `ockm-chord-edit` exist. The v0.12 panel only offers a rhythm, a note pattern, and New. The synth focus screen below is where single-step editing becomes real. Generators stay the fast way to fill a part.

### Order of work for the Pi itself

1. Choose plugdata or vanilla `pd` on the Pi. If vanilla, replace `bob~` first.
2. Make the window contain only the interface. Point the startup script at the project folder so saves land in `projects/default`.
3. Measure the iRig at 128 and 256 samples. Then the screens below are what you are measuring the touch against.

The UI work in the next section can proceed on the Mac in plugdata before any of that, as long as it stays on the hooks and is rebuilt from Python.

---

## The next UI

Three screens. Performance is the front. Programming a drum or a synth happens on its own screen, one part at a time. Longer patterns stay 16 steps wide. You move between those blocks with a swipe.

Navigation is one level deep. Performance is home. A focus screen has a way back. There is no third level.

Swing, accent amount, master effects, and MIDI clock are not on these three screens. They can live on a settings strip later. They stay in the engine and in the project file.

### Performance

What is up while the music plays.

- **Play and tempo.** Large. Play is also on the focus screens, smaller, so you never hunt for it.
- **Patterns 1 to 8.** The main performance gesture. Choosing one still waits for the end of the bar and starts from step 1 (`ockm-want`).
- **Now.** Eight drum lanes and three synth lanes for the block that is currently sounding, playhead moving across them. These lanes are a picture. Tap a lane's name to open that part. Do not make these the step editor. Eleven rows of tappable steps is the cramped panel again.
- **Length.** 16, 32, 64, or 128 for this pattern (`ockm-length`). Making it longer repeats the steps into the new blocks. Those blocks are then reached by swiping in a focus screen.

Save can be present and quiet. It does not need to dominate.

The picture of "now" follows the playhead. It reads `ockm-step` and draws `int(step / 16)`. It does not send `ockm-page`.

### Drum focus

One slot at a time. This is where you choose that slot's sound and place its hits.

- **Eight slots**, named by the sound each one is using. The open slot is the one being edited. Moving between slots does not change pattern.
- **Sound.** Eight pads: kick, snare, clap, rim, closed hat, open hat, tom, rimshot. Sends `ockm-<slot>-sound`. This replaces the row of tiny radios. A later sample picker belongs here.
- **Sixteen steps** for this slot only. Large pads, about 44px or more. Tap cycles empty → hit → accent, which sends `ockm-edit` with 0, 1, or 2. The old "tap adds accent" mode can go away if cycling covers it.
- **Swipe** sideways on the step row to change block when the length is over 16.
- **This slot's strip.** Level, tune, decay, reverb, delay. These belong to the kit, so they stay when the pattern changes.

There are eight fixed slots, not a way to add a ninth track. "Add a drum" means assign a sound to a slot and place hits on it.

### Synth focus

One part at a time: bass, lead, or chord. Opened from the lane you tapped on performance.

- **Part switch.** Bass, lead, chord. Lands on the one you tapped.
- **Key and scale** at the top. Shared by all three (`ockm-root`, `ockm-scale`).
- **Sixteen steps.**
  - Bass and lead: tap a step to turn it on, pick a scale degree, tap again for accent. Slide is a control on the selected step, not a fourth tap in the cycle. Sends `ockm-bass-edit` or `ockm-lead-edit` (`step`, MIDI note, on, accent, slide). The screen shows scale degrees and converts to MIDI from the current key and scale.
  - Chord: the step holds a root in the scale, plus on or accent. Sends `ockm-chord-edit`. Chord type (triad, seventh, sus2, power) is the part's control, `ockm-chord-type`.
- **Fill.** Rhythm and notes, or a chord rhythm and progression, then New (`ockm-<synth>-gen` and the rhythm / notes / prog hooks). New writes the whole pattern length, including blocks off-screen. Swipe there to change single steps afterwards.
- **Engine and k1–k4** under the notes, for this part. Drive for bass and lead.

Keep it to a tap or two per step. A sideways move must not also change the note. See gestures below.

### Swipe between 16-step blocks

A pattern of 64 steps is four blocks of 16. The edit grid always shows one block.

- A horizontal move on the step row changes block.
- A tap edits a step.
- Length 16: one block, swipe does nothing.
- Length 32: two blocks. 64: four. 128: eight.
- Only that many stops. The v0.12 page radio always shows eight pages. That goes away.
- Page label is steps, not a bare index: block 2 of 4 is steps 17–32.
- Dots (or the equivalent) mark the block being edited. If the playhead is on a different block, a second mark shows that, so the grid does not look frozen.

**Two different positions.**

- Performance follows playback. It computes the block from `ockm-step` and does not send `ockm-page`.
- A focus screen stays on the block you swiped to. Swipe sends `ockm-page`, clamped to `0 .. (length / 16) - 1`.
- Opening a focus screen sets `ockm-page` to the block that is currently playing, so you land where the music is. Further swipes stay put while the playhead moves on.

Lengthening from 16 to 32 copies block 1 into block 2 (`ockm-extend`). The new block is immediately available to swipe to. Same at 64 and 128.

Plugdata and vanilla Pd have no swipe widget. On the Mac, a sideways drag on the step row must send the same `ockm-page` message a finger will send on the Pi. Prev/next buttons are acceptable only as a stand-in if a drag cannot be done with the objects you are allowed to use. The interaction to design for is the swipe.

If a drag needs an object that is not vanilla (`else/mouse` or similar), say so in the patch comment and keep it out of the audio path. The headless tests load the whole patch. A missing object must not make `tests/run_tests.py` fail. Prefer a vanilla technique if one exists.

### What leaves the v0.12 panel

| On the panel now | Where it goes |
|---|---|
| Play, tempo, patterns 1–8 | Performance, large |
| All 8 drum rows and their steps at once | Performance as a picture of the block that is playing. Editing moves to one slot in drum focus |
| Sound radios, tune, decay, level, sends | Drum focus, for the open slot |
| Key, scale, engine, knobs, New | Synth focus, for the open part |
| Page radio, always 8 buttons | Swipe on a focus grid. Only as many stops as the length allows |
| Length 16 / 32 / 64 / 128 | Performance |
| Swing, accent amount, effects, MIDI clock | Later settings strip. Still stored, still hooked |

The old engine controls under the panel (number boxes, `drum-settings`, `synth-settings`) can remain for debugging once the engine is in a closed subpatch. They must not sit on the glass.

### How to build it in this repo

- Change `tools/panel.py` and, only if the main patch layout requires it, `tools/build.py`. Rebuild with `python3 tools/build.py`.
- The new screen still only sends and receives `ockm-*` hooks. Do not reach into voice internals.
- Inactive screens must not be visible or tappable. The v0.12 panel is one graph-on-parent, 1100×800. A practical vanilla approach is to build each screen's widgets and move the inactive ones outside that rectangle with `pos`, so the graph clips them. Another is three graph-on-parent abstractions and a parent that shows one. Either is fine if only one screen receives touches.
- Targets on the focus step grids and on the sound pads need to be large enough for a finger. The performance "now" lanes are a picture, so they can be thinner. Their names still need a real hit target.
- Add a test that the screen drives the engine: a drum step edit, an accent, a page change, a pattern button, a sound change, and a bass or lead step edit. Follow the style of the existing panel test in `tests/run_tests.py`.
- Do not use `--reset-patterns` unless you mean to wipe saved work.

### Out of scope for this UI pass

- Replacing `bob~`.
- Moving the engine into a closed subpatch (do it if it is the natural way to hide the old controls, but it is not required to prove the three screens on the Mac).
- Sample playback.
- MIDI knob mapping.
- A project browser.
- Per-row pattern lengths.
- Probability, ratchets, Euclidean patterns.

---

## Suggested order for the person implementing this

1. Replace the single panel with performance, drum focus, and synth focus, rebuilt from `tools/panel.py`.
2. Wire swipe (sideways drag on the Mac) to `ockm-page`, clamped to the length. Keep performance on the playhead.
3. Drum focus: one slot, sound pads, 16 steps, tap cycles off / on / accent, slot strip.
4. Synth focus: one part, shared key and scale, 16 steps via the edit hooks, Fill still available, engine and knobs underneath.
5. A headless test that those controls reach the hooks.
6. Leave Pi runtime, `bob~`, save-path cwd, and audio buffer measurement as the separate bring-up list above.
