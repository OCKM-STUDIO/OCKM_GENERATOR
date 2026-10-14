# OCKM_GENERATOR

A drum machine and easy-to-program synths in one box. Built in Pure Data, designed to run on a Raspberry Pi with a touchscreen and a few knobs.

Current version: **v0.21**

## How to open it

Open `OCKM_GENERATOR.pd` in plugdata. Keep the folder together: the main patch finds everything else in the subfolders.

The window is the instrument: three touch screens, drawn in Lua (plugdata has Lua built in). Click with the mouse on the Mac, tap with a finger on the Pi. If clicks do nothing, the patch is in edit mode: press Cmd+E.

**How every screen is laid out**, top to bottom:
1. **Top bar:** play, tempo, then the screens as tabs: **perform, drums, bass, lead, chord, mixer**. Save and **project** on the right. The version number sits next to the tempo
2. **Navigation strip:** **pattern** 1 to 8 (small), **length** (16, 32, 64, 128), and **steps**: back and forward arrows either side of the steps you're looking at (for example "17-32"). The dots underneath show every block of 16: white is the one on screen, orange is the one playing. You can also swipe the step row sideways
3. **What you're editing:** the steps (and, on the drums screen, which of the 8 drum slots)
4. **Sound shaping** at the bottom

Tap a track's name on perform or the mixer to jump straight to it.

**Perform** (home)
- **Play** and **tempo** top left. Drag the tempo number up or down
- Patterns are in the navigation strip: tap to switch. While playing it waits for the end of the bar; the queued one gets an orange outline
- **Now**: all 11 tracks for the 16 steps on screen, with the playhead running above them. **Tap a drum lane's steps to edit them** (empty, hit, accent), just like the drums screen. The bass, lead and chord lanes are a picture: edit those on their own tabs
- Tap a track's **name** to open it
- **M** mutes a track and **S** solos it (several can be soloed at once). Silent tracks go dim. Mutes and solos are for playing live, so they aren't saved
- **Bottom left, synth:** pick bass, lead or chord, then play its four main knobs (named for the engine it's using)
- **Bottom right, master FX:** filter (centre is off: left is low-pass, right is high-pass), drive, delay level, feedback and time (in steps), reverb level, size and tone
- These are bars: drag along them. The orange line shows the value
- **Length** is in the navigation strip. Making a pattern longer repeats what's there
- **Save** and **project**, top right

**Drum** (one slot at a time)
- The 8 slots along the top, named by the sound they play
- **Sound**: 8 pads, one per drum sound
- **Steps**: tap cycles empty, hit (white), accent (orange)
- Move between blocks of 16 with the **steps** arrows in the navigation strip, or swipe the step row sideways
- **Level, tune, decay, reverb, delay** for this slot. These belong to the kit, so they stay when you change pattern
- **Grooves** (right of the sliders): tap one to fill all 8 drums at once. Each slot gets the part for the sound it plays, so a groove's hats land on whichever slot is your hat. It fills the whole pattern length and sets a swing to suit. Twelve to pick from: four floor, house, deep house, tech house, minimal, techno, dub techno, garage, breakbeat, boom bap, trip hop, electro. **Clear** empties the drums. A groove replaces your drum steps, so **back to last save** (on the project screen) is your undo

**Compose** (a tab between drums and the synths): how the pattern is put together.
- **Who leads the harmony:**
  - **chords:** the progression leads; bass and lead follow it
  - **melody:** start with a tune. Write the lead by hand, then tap **suggest chords for the melody**. It tries all 10 progressions against your notes and picks the best fit. Tap again for the next best. The bass follows the chords it picks
  - **bass:** the same, starting from the bass line. The lead follows the chords
  - **key only:** no connections. Every part just uses the key
- **Key and scale**, shared by every part
- **The chain:** which part leads, which follow, and which are on manual
- **A column each for chord, bass and lead** with their generator settings. Use the arrows to step through the presets. A change rewrites the part straight away
  - Chord: progression, rhythm, spice and smooth voicing
  - Bass and lead: notes and rhythm, then:
  - **own rhythm | on the kick | fill gaps:** use the preset rhythm, play only where the kick plays, or play only where it doesn't. Locked parts redraw when you edit the kick
  - **density:** drag left for fewer notes, right for more. The middle is the preset as written
  - **mutate:** a new variation of the same idea (different note order, the odd octave jump). Tap again for another. **Original** goes back

**The rule: compose decides the notes, the synth tabs decide the sound.** Every synth part is on **auto** or **manual**, like a camera:
- **Auto:** the notes come from compose and follow the chain. On the synth tab its steps are drawn as outlines and locked; tapping one just reminds you it's on auto
- **Manual:** your notes. Switch to manual on the synth tab (or on compose) and edit the steps. Compose greys the part out and never changes it. **Back to auto** hands it back to the generator and replaces your notes
- Sound controls (engine, knobs, drive, sends, level) always work, in either mode
- Bass and chord start on auto; the lead starts on manual, because it's the melody

**Bass, lead and chord** (a tab each)
- **Key** and **scale** at the top, shared by all three
- **Steps**: tap cycles off, on, accent. **Drag a step up or down** to change its note. Or tap a step, then pick its note from the row underneath (the dimmed one is the key's root). **Slide** applies to the selected step
- Chord steps show the chord on that step of the scale (i, ii, iii...)
- The **auto | manual** switch, and a line saying where the notes come from
- **Sound**: engine, its four knobs (named for the engine), drive, reverb and delay sends, level
- On manual: the note (or chord) picker for the selected step, and slide

**Mixer**
- One strip per track: reverb and delay sends at the top, a level fader, then **M** and **S**. Tap a strip's name to open that track
- **Master** on the right: the reverb and delay return levels, the master volume, and **clear** to undo every mute and solo
- Drum levels belong to the kit (the project). Bass, lead and chord levels belong to each pattern, like the rest of their sound

Swing, accent amount and MIDI clock aren't on the screens yet. They're still saved, and they're in **pd test-panel**.

**Under the screen:** `pd engine` is the sound and sequencer (open it only if you're curious). `pd test-panel` is the old v0.12 panel with every control on one sheet, kept for testing.

**Projects** (the **project** button, top right). A project is 8 patterns plus the drum kit, tempo and effects. It opens on the one you used last.
- **Save** writes all 8 patterns and the project. **Back to last save** throws away everything since
- **New blank project** starts from nothing: every pattern empty, the default kit and sounds. It's named for you with two random words and the date, like "velvet heron · 14 Oct"
- **Save as a copy** keeps the project you were in as it was last saved, and carries on in a copy
- **Your projects**, newest first. Tap one, then **save mine, then open**, **open without saving**, or **delete** (tap twice). Deleting moves the files to a `trash` folder next to `projects/`, so nothing is lost by accident

Everything is remembered: drum kit, synth sounds, effects, tempo, swing, key and the steps. Switching patterns keeps unsaved edits in memory until you save.

**Light or dark, Mac or Pi.** Rebuild with `python3 tools/build.py --theme light` for the light version. `--ui-scale 2` sizes the screens for the 10" Pi display (1920 x 1200). The defaults are dark and Mac size (960 x 600).

## The idea

- **Drums plus synths in one box.** 8 drum slots, plus bass, lead and chord synths that are easy to sequence. 303-style acid is one flavour, not the only one.
- **Screen for editing, knobs for playing.** A 7" touchscreen shows the pattern. A few physical knobs for live bass control.
- **Runs on a Raspberry Pi.** No soldering. Everything plugs in over USB.

## Principles

1. **Easy to program beats deep.** If it takes more than a tap or two, rethink it.
2. **Works without a keyboard.** Everything, including saving, must be possible from the screen and knobs.
3. **Plain Pure Data.** Stick to standard objects so it runs the same in plugdata and on the Pi.
4. **Every sound is a swappable box.** Sequencers say "go". Voices make sound. Either can change without touching the other.
5. **Musical by default.** Presets and starter patterns that sound good the moment you press play.

## Hardware (planned)

| Part | Choice | Status |
|---|---|---|
| Computer | Raspberry Pi 5, 2GB (plenty: the patch uses about 11MB), with Active Cooler and the official 27W power supply | Not bought |
| Screen | Official Raspberry Pi Touch Display 2, 10" (1920 x 1200, Pi 5 only). Decided: big enough for finger-sized steps | Not bought |
| Audio | Raspberry Pi DAC Pro on the GPIO pins (the Pi 5 has no audio socket). RCA outputs, then a 2 x RCA to 2 x 1/4" TS lead into a stereo channel of the mixer (Zoom L6, channels 3/4 or 5/6). The iRig Pro Duo works for testing on the Mac | Not bought |
| Screen power | Small USB power adapter for the screen, because the DAC Pro covers the GPIO pins the screen would normally take power from | Not bought |
| Controller | Endless knobs with light rings. Front runners: Novation Launch Control 3 (16 knobs, screen) or Behringer X-Touch Mini (8 knobs, 16 buttons). Maybe a Launchpad Mini later for a hands-on step grid | To choose |
| Storage | microSD card, 32GB | Not bought |
| MIDI | USB only for now: the controller plugs straight into the Pi. If syncing with gear that only has 5-pin MIDI sockets is ever needed, add a Roland UM-ONE mk2 (avoid cheap unbranded cables) | Decided |

## Roadmap

1. ~~Pattern saving and swing~~ (v0.1)
2. ~~Bass rhythm presets, note patterns, keys and scales~~ (v0.2). Still to do: editing single bass steps
3. ~~Drum accents per step, plus tune, decay and level per drum~~ (v0.3)
4. ~~More drum voices, up to 8: snare, rim, toms, percussion~~ (v0.3)
5. ~~Front panel for testing on the Mac~~ (v0.12). ~~Touchscreen interface in Lua: perform, drum and synth screens, swipe between blocks~~ (v0.13). Still to come: a settings strip for swing, accent, effects and MIDI
6. Knobs for live bass control: MIDI mapping, plus drive and accent level (waiting on a controller to test with)
7. ~~Bass engines (acid, sub, FM, Reese, pluck) and master effects (drive, delay, filter)~~ (v0.4)
8. ~~MIDI clock sync~~ (v0.5)
9. Move to the Pi and start on boot
10. ~~6 flexible drum slots and patterns up to 128 steps~~ (v0.9)
11. ~~8 drum slots, chord and lead synth tracks~~ (v0.10)
12. ~~One central settings store: projects, patterns and the drum kit, saved and restored~~ (v0.11)
13. Your drum samples, chosen per slot

## Decisions made

- **Raspberry Pi, not Daisy or Arduino.** No hardware skills needed, and it runs full Pd, so nothing has to be rewritten.
- **11 tracks: 8 drum slots plus 3 synths (bass, lead, chord).** Between a TR-6S and a TR-8. More would make the screen too busy without making the music better.
- **8 pattern slots, each up to 128 steps.** One length per pattern, shown 16 steps at a time.
- **Drum slots are flexible.** Each of the 8 slots can play any of the 8 drum sounds, and later any of your samples.
- **One key for all synths.** Bass, lead and chord share the key and scale, so they always agree.
- **A self-contained box.** Pi, 10" screen and DAC Pro in one unit, a USB MIDI controller alongside, audio out on RCA to the mixer. No iRig, no MIDI interface for now.
- **Touchscreen plus a hardware controller.** The screen is for editing and overview. The knobs are for playing. The screen is the official 10" (decided October 2026): the 7" would make mute, solo and step buttons too small for a finger.
- **Minimal modern look.** Flat, one accent colour (orange), lots of space, light and dark themes. Dark is the default.
- **Build and test on the Mac first.** Everything runs in plugdata; the Pi only adds audio setup, screen rotation and start-up.
- **Lua for the screens.** Plain Pd controls can't tell a tap from a swipe, or show one screen at a time. The screens are one Lua object (`ui/ockm-ui.pd_lua`) that only sends and listens to the `ockm-*` hooks. The sound engine stays plain Pd.
- **Three screens, one level deep.** Perform is home. Drum and synth screens go deep on one part at a time. See `docs/architecture-and-ui-brief.md`.
- **Synthesised drums for now.** Samples can be swapped in later, one voice at a time.
- **Projects and patterns saved as readable text files** in `projects/`, so saving works on the Pi without a keyboard.
- **The drum kit belongs to the project; synth sounds belong to each pattern.** See "How it's organised".

## Parked ideas

- FM drum and bass voices (likely to come back with the bass engines)
- Probability, ratchets and Euclidean patterns
- Different lengths per row (one length per pattern for now)
- An Arduino-built custom control panel
- The Daisy route for a fully embedded box

## Reference

- [Acid Drip](https://github.com/lonesoulsurfer/Acid_Drip_Bassline_and_Drum_Synth): a similar acid plus drums box on a Raspberry Pi Pico. Good reference for easy bass entry: tap a step, long-press for accent or slide, notes locked to a scale.

## What's in the folder

| Path | What it is |
|---|---|
| `OCKM_GENERATOR.pd` | Main patch: clock, swing, pattern slots, mixer |
| `voices/` | One file per sound: 8 drums plus `ockm-drum` (a slot that plays any of them); the mono synth used for bass and lead (`ockm-mono`, one file per engine, shared `ockm-mono-core`); the chord synth (`ockm-chord`, one file per engine); the reverb (`ockm-verb`); and the master effects (`ockm-fx`) |
| `ui/` | The touchscreen: `ockm-ui.pd_lua` (all three screens) |
| `docs/` | The architecture review and the brief for the screens |
| `seq/` | The old test panel (`ockm-panel`), plus sequencers and generators: drum row, mono pattern and generator (bass and lead), chord pattern and generator, the shared presets (`ockm-presets`) and MIDI clock |
| `projects/` | One folder per project, named like `2026-10-14-velvet-heron`, each holding `project.txt` (tempo, effects, MIDI, accent, drum kit) and `p1.txt` to `p8.txt`. `current.txt` names the one that opens at start-up. `default` is the blank starter |
| `trash/` | Deleted projects. Empty it by hand when you're sure |
| `sketches/` | Early experiments, kept for reference |
| `tools/build.py` | Builds every `.pd` file (the panel's layout and colours are in `tools/panel.py`). Structural changes are made here, then the patch files are rebuilt |
| `tests/run_tests.py` | Plays the patch headless and checks it still works (sounds, accents, patterns, swing, bass, effects, MIDI clock, both panels) |
| `tests/ui_preview.py` | Draws the touch screens to PNG files without Pd (needs `lua` and Pillow) |

## Working on the project

**Version history.** The folder is a git repository. Every version is saved, and you can go back to any of them. It all stays on your Mac. Pushing a copy to GitHub as an off-site backup is optional.

**Two kinds of change.**
- *Sound tweaks* (tune, levels, knobs, patterns): use the controls in the patch, as normal.
- *Structural changes* (new objects, new voices, rewiring): made in `tools/build.py`, then rebuilt with `python3 tools/build.py`. Don't rewire the generated `.pd` files by hand, because the next rebuild would overwrite it. The build only creates project files that are missing, so your saved work is never overwritten. `--reset-patterns` rewrites the starter project, which deletes your saved patterns.

**Tests.** `python3 tests/run_tests.py` runs 24 checks in about two and a half minutes. It needs vanilla Pure Data's `pd` command, which comes with the Pi's `puredata` package. The touchscreen test also needs pdlua (set `PDLUA=/folder/with/pdlua`); without it, that test is skipped. It works on a temporary copy, so your patterns are safe.

**Internal names.** Every shared name starts with `ockm-` so nothing clashes with other patches. Pattern tables are `ockm-pat-<track>`, slot banks are `ockm-bank-<track>`, and the step squares are `ockm-sq-<track>-<square>`. Drum tracks are `d1` to `d8`, synth tracks are `bass`, `lead` and `chord`.

## How it's organised

The data model, smallest first:

1. **Step:** one slot in time on one track. Drums: off, on or accent. Bass and lead: note, on, accent and slide. Chord: on or accent plus a chord root.
2. **Track:** one lane. 8 drum slots, plus bass, lead and chord.
3. **Sound:** what a track plays. A drum slot: its sound, tune, decay, level and sends. A synth: engine, k1 to k4, drive (bass and lead), chord type (chord) and sends.
4. **Kit:** the 8 drum sounds together.
5. **Pattern:** a loop. The steps for all 11 tracks, plus length (1 to 128), swing, key and scale, generator choices and **the three synth sounds**.
6. **Project:** a whole set. 8 patterns, **the drum kit**, tempo, master effects, MIDI settings and accent amount.

| Setting | Lives in |
|---|---|
| Drum kit (all 8 drum slots) | Project, shared by every pattern |
| Tempo, master effects, MIDI sync, accent | Project |
| Steps, length, swing, key and scale | Pattern |
| Synth sounds (bass, lead, chord) | Pattern |
| Generator choices | Pattern |

**Rules**
- A new, empty pattern starts with blank steps but keeps the synth sounds, key and swing of the pattern you came from.
- Switching patterns keeps unsaved edits in memory, so you can go back and forth. **Save** writes all 8 patterns and the project to disk. **Revert** reloads the whole project from disk. Closing without saving loses unsaved changes.
- Files are plain text, one setting or one track per line, so they're easy to read, copy and back up.

## Named hooks

These let other things control the patch: tests now, and the touchscreen, knobs and MIDI later.

| Name | Does |
|---|---|
| `ockm-play` | 1 to start, 0 to stop |
| `ockm-want` | Pick a pattern slot, 0 to 7 |
| `ockm-save` | Save all 8 patterns and the project to disk |
| `ockm-revert` | Throw away unsaved changes: reload the whole project from disk |
| `ockm-project-new <name>` | Make a blank project in `projects/<name>` and open it |
| `ockm-project-open <name>` | Open a project (unsaved changes in the current one are dropped) |
| `ockm-project-saveas <name>` | Save the current project into `projects/<name>` and carry on there |
| `ockm-project-delete <name>` | Move a project's files to `trash/<name>` |
| `ockm-project-list` | Reply with `ockm-project-list-start`, one `ockm-project-item <name>` per project, then `ockm-project-list-end` |
| `ockm-project-name` | Sent by the engine: the open project's name |
| `ockm-resync` | Ask the store to send every current value to the on-screen boxes (`ockm-show-<name>`) |
| `ockm-tempo` | Sent when the tempo box changes (the store listens to this) |
| `ockm-swing` | Set the swing. `ockm-swing-now` is sent when it changes |
| `ockm-loading` | 1 while a pattern is loading, 0 after. Generators don't rebuild while it's 1 |
| `ockm-refresh` | Sent after a pattern loads, so the squares update |
| `ockm-step` | Sends the current step as it plays, counting from 0 |
| `ockm-length` | Set the current pattern's length, 1 to 128. Lengthening repeats existing steps |
| `ockm-len` | Sent whenever the active length changes (for example when a pattern loads) |
| `ockm-page` | Which 16 steps the squares show: 0 is steps 1 to 16, 1 is 17 to 32, up to 7 |
| `ockm-extend` | Internal: tells every track to repeat its steps to fill a longer pattern |
| `ockm-master` | The final audio mix |
| `ockm-root` | Key for all synths, 0 to 11 (0 = C, 9 = A). Rebuilds bass and lead, and re-voices chords |
| `ockm-scale` | Scale for all synths, 0 to 5 |
| `ockm-bass-rhythm`, `ockm-lead-rhythm` | Rhythm preset, 0 to 7, and rebuild that track |
| `ockm-bass-notes`, `ockm-lead-notes` | Note pattern, 0 to 11, and rebuild that track |
| `ockm-bass-gen`, `ockm-lead-gen`, `ockm-chord-gen` | Rebuild that track with the current settings |
| `ockm-bass-lock`, `ockm-lead-lock` | 0 own rhythm, 1 play on the kick, 2 fill the gaps between kicks |
| `ockm-bass-density`, `ockm-lead-density` | 0 to 2: fewer to more notes, 1 is the preset as written |
| `ockm-bass-seed`, `ockm-lead-seed` | Variation number: 0 is the original, anything else a mutation |
| `ockm-bass-mode`, `ockm-lead-mode`, `ockm-chord-mode` | 0 auto (generated), 1 manual (your notes) |
| `ockm-bass-sync`, `ockm-lead-sync` | 1 follow the chords, 0 follow the key only |
| `ockm-leader` | Who leads the harmony: 0 chords, 1 melody, 2 bass, 3 key only |
| `ockm-drum-groove` | Fill every drum slot with a groove, 0 to 11, or 12 to clear. Sets the swing too |
| `ockm-chord-rhythm` | Chord rhythm preset, 0 to 7, and rebuild |
| `ockm-chord-prog` | Chord progression, 0 to 9, and rebuild |
| `ockm-chord-type` | 0 triad, 1 seventh, 2 sus2, 3 power chord. Applies straight away |
| `ockm-edit` | Set one drum step: slot, step (0 to 127), value (0 off, 1 on, 2 accent). For example `d1 4 2` |
| `ockm-bass-edit`, `ockm-lead-edit` | Set one bass or lead step: step (0 to 127), note (MIDI), on, accent, slide. For example `0 33 1 1 0` |
| `ockm-chord-edit` | Set one chord step: step, 0 off / 1 on / 2 accent, chord root as a scale step (0 is the key's root). For example `4 1 5` |
| `ockm-accent` | Accent amount, 0 to 1 |
| `ockm-<synth>-engine` | bass and lead: 0 acid, 1 sub, 2 FM, 3 reese, 4 pluck, 5 saw, 6 house. chord: 0 stab, 1 organ, 2 pad |
| `ockm-<synth>-k1` to `-k4` | Synth knobs, 0 to 1. What they do depends on the engine (see below) |
| `ockm-bass-drive`, `ockm-lead-drive` | Distortion, 0 to 1 |
| `ockm-filter` | Master DJ filter, -1 to 1. Below 0 cuts the top, above 0 cuts the bottom, 0 is off |
| `ockm-drive` | Master drive, 0 to 1 |
| `ockm-delay-mix` | Delay return level, 0 to 1 |
| `ockm-delay-fb` | Delay feedback, 0 to 0.9 |
| `ockm-delay-steps` | Delay time in steps. 3 is a dotted 8th |
| `ockm-verb-mix` | Reverb return level, 0 to 1 |
| `ockm-verb-size` | Reverb size, 0 (small room, about 0.4s) to 1 (big hall, about 3s) |
| `ockm-verb-tone` | Reverb tone, 0 dark to 1 bright |
| `ockm-<slot>-sound` | Which sound a drum slot plays: 0 kick, 1 snare, 2 clap, 3 rim, 4 closed hat, 5 open hat, 6 tom, 7 rimshot |
| `ockm-<slot>-verb` | How much of that slot goes to the reverb, 0 to 1 |
| `ockm-<slot>-delay` | How much of that slot goes to the delay, 0 to 1 |
| `ockm-<synth>-verb`, `ockm-<synth>-delay` | Reverb and delay sends for bass, lead and chord |
| `ockm-stepms` | Sent by the clock: length of one step in ms |
| `ockm-sync` | 0 leader (internal clock, sends MIDI clock), 1 follower (plays to incoming MIDI clock) |
| `ockm-clock-out` | 1 to send MIDI clock when leading, 0 to keep quiet |
| `ockm-bpm` | Set the tempo. In follower mode the measured tempo is sent here |
| `ockm-playing` | Sent by the start/stop toggle: 1 playing, 0 stopped |
| `ockm-tick` | Advance one step (used by the follower) |
| `ockm-reset` | Next step will be step 1 |
| `ockm-midi-rt` | Feed in MIDI clock bytes from somewhere other than a MIDI port |
| `ockm-<slot>-tune` | Tune in semitones, -12 to 12. Slots: d1 to d8 |
| `ockm-<slot>-decay` | Decay in %, 100 is normal |
| `ockm-<slot>-level` | Level, 0 to 1 |

## Drums

Eight drum slots, d1 to d8. Each slot can play any of 8 sounds: 0 kick, 1 snare, 2 clap, 3 rim, 4 closed hat, 5 open hat, 6 tom, 7 rimshot (the old cowbell is in `sketches/`). Only the chosen sound runs. The default line-up is kick, snare, clap, closed hat, open hat, rimshot, rim and tom.

Each step can be off, on or accented. Accented steps play at full strength. Normal steps play at full strength minus the accent amount. For now, accents are set with the `ockm-edit` hook. The squares show on or off only, until the touchscreen work.

Slot sounds, tune, decay, level and sends are part of the drum kit, which is saved with the project and shared by every pattern.

## Bass and lead engines

Bass and lead are the same mono synth, so each has the same seven engines (the lead plays two octaves higher). Only the chosen engine runs, so the others cost no processing power. Every engine uses the same four knobs, 0 to 1. k4 is always decay.

| Engine | k1 | k2 | k3 | Character |
|---|---|---|---|---|
| 0 acid | cutoff | resonance | envelope amount | The 303 squelch |
| 1 sub | tone | drive | pitch drop | Deep and clean, 808-ish |
| 2 FM | brightness | ratio | envelope on brightness | Punchy, metallic, plucky |
| 3 reese | cutoff | detune (width) | envelope amount | Dark and wide |
| 4 pluck | brightness | saw to square | filter snap | Rings out and fades over the decay time, with a sub an octave down. Ignores the short 303-style note length |
| 5 saw | tone (1 = fully raw) | second saw detune (0 = single saw) | sub saw an octave down | Hard and buzzy. Notes play at full level for the decay time, then stop |
| 6 house | tone | body (sub sine an octave down) | pluck (filter snap) | Deep house and garage: a clean square and a sub sine through a warm filter |

The drive comes after the engine, so it works on all of them. At 0 it's completely clean; it only colours the sound as you turn it up. Defaults: bass on acid, lead on pluck.

## Chord synth

Plays up to four notes at once, worked out as it plays from the step's chord root, the shared key and scale, and the chord type. Change the key or the spice and the chords follow straight away.

**Spice** picks the chord type: 1 triad, 2 seventh, 3 ninth (root, third, seventh, ninth), 4 eleventh (root, seventh, ninth, eleventh). The old test panel also offers sus2, power, sus4 and sixth.

**Smooth** (on by default) folds every chord into the octave above the key's root, so each chord is played in the shape closest to the last. Off plays every chord from its root upwards.

| Engine | k1 | k2 | k3 | k4 | Character |
|---|---|---|---|---|---|
| 0 stab | brightness | detune | filter snap | length | Dub techno stabs. Great with the delay |
| 1 organ | upper drawbars | percussion click | sub drawbar | length | House organ |
| 2 pad | brightness | detune (width) | attack | length | Slow, wide chords |

## Effects

Reverb and delay work like a mixing desk: each track has a **send** that sets how much of it goes to the effect, and the effect's **level** sets how loud the result comes back. Defaults: clap, snare, rimshot and tom get some reverb, the rim and rimshot get a little delay, the kick and bass stay dry. Both effect returns pass through the DJ filter, so a filter sweep takes the echoes and tails with it.

## MIDI clock

- **Leader** (sync 0, the default). OCKM_GENERATOR keeps time and sends MIDI clock, start and stop out of the MIDI port. Your other gear follows it. Clock is sent straight, without swing, so other gear applies its own groove.
- **Follower** (sync 1). OCKM_GENERATOR waits for MIDI start, then steps in time with incoming clock. The BPM box shows the measured tempo. Stop on the other gear stops it too.

Pick the MIDI port in plugdata's audio and MIDI settings. On the Pi, the iRig Pro Duo's MIDI ports should work for this.

## Generators

**Bass and lead** are built from a rhythm, a note pattern, and the shared key and scale. Then the rhythm lock (own, on the kick, fill gaps), density and mutate are applied, in that order. Change any one and the track rebuilds straight away, filling the whole pattern length. The 16-step rhythm repeats, and the note pattern carries on across bars. Changing the key rebuilds both bass and lead.

**Chords** are built from a progression and a chord rhythm. Each progression has its own length (1, 2, 4 or 8 bars) and its own timing: some change chord every half bar, some hold a chord for two. If the pattern is shorter than the progression, picking it makes the pattern longer. It never makes a pattern shorter.

**Rhythms** (when it plays): 0 offbeat, 1 rolling, 2 gallop, 3 acid classic, 4 sparse dub, 5 tech bounce, 6 acid 16ths, 7 trip hop

**Note patterns** (what it plays, used in turn on each note): 0 root, 1 octaves, 2 root and fifth, 3 acid riff, 4 walk up, 5 minor stab, 6 dub, 7 pedal, 8 arp up, 9 arp up-down, 10 call, 11 descend

**Chord rhythms**, simplest first: 1 bar pads, 2 two beat, 3 offbeat, 4 dub stabs, 5 house organ, 6 tresillo (3-3-2), 7 syncopated, 8 garage skip (2 bars), 9 call and answer (2 bars), 10 eighths

**Progressions**, simplest first (chords in the minor key, they follow whatever key and scale you pick):

| # | Name | Chords | Bars |
|---|---|---|---|
| 1 | one chord | i | 1 |
| 2 | vamp | i iv | 2 |
| 3 | dub techno | i i i VII | 4 |
| 4 | deep house | i iv VI v | 4 |
| 5 | garage | i VI iv v, half a bar each | 2 |
| 6 | pop | i VI III VII | 4 |
| 7 | uplift | VI VII i (held two bars) | 4 |
| 8 | andalusian | i VII VI V | 4 |
| 9 | trip hop | i VII VI v, two bars each | 8 |
| 10 | soul | ii V I (held two bars) | 4 |

The presets live in `tools/build.py` (`PRE` and `PROGS`). The build writes their names and shapes into the touchscreen too, so they always match.

**Suggest chords** (melody or bass leads) scores each progression against the leading part's notes: a note on the chord's root scores 3, another note of the chord 2, anything else -1. Notes on the beat and accented notes count for more. The best average wins.

**Chord types**: 0 triad, 1 seventh, 2 sus2, 3 power

**Scales**: 0 minor, 1 major, 2 dorian, 3 phrygian, 4 mixolydian, 5 harmonic minor

The presets live in `tools/build.py` (in `PRE`), so they survive rebuilds. To add or change one, ask me, or edit the lists there and rebuild. Rhythm codes are 0 rest, 1 note, 2 accent, 3 note plus slide, 4 accent plus slide. Notes are scale steps: 0 root, 2 third, 4 fifth, 7 octave, minus numbers go below the root.
