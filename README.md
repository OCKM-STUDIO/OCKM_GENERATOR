# OCKM_GENERATOR

A drum machine and easy-to-program synths in one box. Built in Pure Data, designed to run on a Raspberry Pi with a touchscreen and a few knobs.

Current version: **v0.14**

## How to open it

Open `OCKM_GENERATOR.pd` in plugdata. Keep the folder together: the main patch finds everything else in the subfolders.

The window is the instrument: three touch screens, drawn in Lua (plugdata has Lua built in). Click with the mouse on the Mac, tap with a finger on the Pi. If clicks do nothing, the patch is in edit mode: press Cmd+E.

**Moving between screens:** the tabs along the top (**perform**, **drums**, **synths**) are on every screen, next to play and tempo. Or tap a track's name on perform to jump straight to it.

**Perform** (home)
- **Play** and **tempo** top left. Drag the tempo number up or down
- **Patterns 1 to 8**: tap to switch. While playing it waits for the end of the bar; the queued one gets an orange outline
- **Now**: all 11 tracks for the 16 steps that are playing, with the playhead running above them. It's a picture, not an editor
- Tap a track's **name** to open it
- **Sound strip**: pick bass, lead or chord, then play its four main knobs (named for the engine it's using). The **filter** next to length is the master DJ filter
- **Length**: 16, 32, 64 or 128 steps. Making it longer repeats what's there
- **Save** and **revert**, top right

**Drum** (one slot at a time)
- The 8 slots along the top, named by the sound they play
- **Sound**: 8 pads, one per drum sound
- **Steps**: tap cycles empty, hit (white), accent (orange)
- **Swipe** the step row sideways to move between blocks of 16. The dots underneath show which block you're on; an orange mark shows where the playhead is if it's somewhere else
- **Level, tune, decay, reverb, delay** for this slot. These belong to the kit, so they stay when you change pattern

**Synth** (bass, lead or chord)
- **Key** and **scale** at the top, shared by all three
- **Steps**: tap cycles off, on, accent. **Drag a step up or down** to change its note. Or tap a step, then pick its note from the row underneath (the dimmed one is the key's root). **Slide** applies to the selected step
- Chord steps show the chord on that step of the scale (i, ii, iii...). Chord type is with the sound
- **Sound**: engine and its four knobs (named for the engine), plus drive, or chord type for the chord
- **Fill**: pick a rhythm and notes (or a chord rhythm and progression) and press **new** to write the whole pattern. Then swipe and tweak single steps

Swing, accent amount, the other master effects and MIDI clock aren't on the screens yet. They're still saved, and they're in **pd test-panel**.

**Under the screen:** `pd engine` is the sound and sequencer (open it only if you're curious). `pd test-panel` is the old v0.12 panel with every control on one sheet, kept for testing.

Everything is remembered: drum kit, synth sounds, effects, tempo, swing, key and the steps. Switching patterns keeps unsaved edits in memory.

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
| Computer | Raspberry Pi 5, 2GB or 4GB, with Active Cooler and official power supply | Not bought |
| Screen | Official Raspberry Pi Touch Display 2, 10" (1920 x 1200, Pi 5 only) is the favourite; the 7" is the compact option | Not bought |
| Audio | iRig Pro Duo (already owned, check it's recognised) | Owned |
| Knobs | Small USB MIDI knob controller | To choose |
| Storage | microSD card | Not bought |

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
- **Touchscreen plus a few knobs.** The screen is for editing. The knobs are for playing. Leaning towards the official 10" screen for bigger steps.
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
| `projects/default/` | The project: `project.txt` (tempo, effects, MIDI, accent, drum kit) and `p1.txt` to `p8.txt` (one per pattern). Written by the patch when you save |
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
- Switching patterns keeps unsaved edits in memory, so you can go back and forth. **Save** writes the current pattern and the project to disk. **Revert** reloads them from disk. Closing without saving loses unsaved changes.
- Files are plain text, one setting or one track per line, so they're easy to read, copy and back up.

## Named hooks

These let other things control the patch: tests now, and the touchscreen, knobs and MIDI later.

| Name | Does |
|---|---|
| `ockm-play` | 1 to start, 0 to stop |
| `ockm-want` | Pick a pattern slot, 0 to 7 |
| `ockm-save` | Save the current pattern and the project to disk |
| `ockm-revert` | Throw away unsaved changes: reload the current pattern and the project from disk |
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
| `ockm-chord-rhythm` | Chord rhythm preset, 0 to 7, and rebuild |
| `ockm-chord-prog` | Chord progression, 0 to 7, and rebuild |
| `ockm-chord-type` | 0 triad, 1 seventh, 2 sus2, 3 power chord. Applies straight away |
| `ockm-edit` | Set one drum step: slot, step (0 to 127), value (0 off, 1 on, 2 accent). For example `d1 4 2` |
| `ockm-bass-edit`, `ockm-lead-edit` | Set one bass or lead step: step (0 to 127), note (MIDI), on, accent, slide. For example `0 33 1 1 0` |
| `ockm-chord-edit` | Set one chord step: step, 0 off / 1 on / 2 accent, chord root as a scale step (0 is the key's root). For example `4 1 5` |
| `ockm-accent` | Accent amount, 0 to 1 |
| `ockm-<synth>-engine` | bass and lead: 0 acid, 1 sub, 2 FM, 3 reese, 4 pluck, 5 saw. chord: 0 stab, 1 organ, 2 pad |
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

Bass and lead are the same mono synth, so each has the same six engines (the lead plays two octaves higher). Only the chosen engine runs, so the others cost no processing power. Every engine uses the same four knobs, 0 to 1. k4 is always decay.

| Engine | k1 | k2 | k3 | Character |
|---|---|---|---|---|
| 0 acid | cutoff | resonance | envelope amount | The 303 squelch |
| 1 sub | tone | drive | pitch drop | Deep and clean, 808-ish |
| 2 FM | brightness | ratio | envelope on brightness | Punchy, metallic, plucky |
| 3 reese | cutoff | detune (width) | envelope amount | Dark and wide |
| 4 pluck | brightness | saw to square | filter snap | Rings out and fades over the decay time, with a sub an octave down. Ignores the short 303-style note length |
| 5 saw | tone (1 = fully raw) | second saw detune (0 = single saw) | sub saw an octave down | Hard and buzzy. Notes play at full level for the decay time, then stop |

The drive comes after the engine, so it works on all of them. Defaults: bass on acid, lead on pluck.

## Chord synth

Plays up to four notes at once, worked out as it plays from the step's chord root, the shared key and scale, and the chord type (triad, seventh, sus2 or power). Change the key and the chords follow straight away.

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

**Bass and lead** are built from a rhythm, a note pattern, and the shared key and scale. Change any one and the track rebuilds straight away, filling the whole pattern length. The 16-step rhythm repeats, and the note pattern carries on across bars. Changing the key rebuilds both bass and lead.

**Chords** are built from a chord rhythm and a progression. The progression moves one chord per 16-step bar, so set the length to 32 or 64 to hear it move.

**Rhythms** (when it plays): 0 offbeat, 1 rolling, 2 gallop, 3 acid classic, 4 sparse dub, 5 tech bounce, 6 acid 16ths, 7 trip hop

**Note patterns** (what it plays, used in turn on each note): 0 root, 1 octaves, 2 root and fifth, 3 acid riff, 4 walk up, 5 minor stab, 6 dub, 7 pedal, 8 arp up, 9 arp up-down, 10 call, 11 descend

**Chord rhythms**: 0 offbeat stabs, 1 dub stabs, 2 bar pads, 3 house organ, 4 two beat, 5 syncopated, 6 eighths, 7 sparse

**Progressions**: 0 i, 1 i-VI-VII, 2 i-iv, 3 i-VII-VI-VII, 4 i-v, 5 i-III-VII-iv, 6 i-VI-iv-v, 7 ii-V-i-i

**Chord types**: 0 triad, 1 seventh, 2 sus2, 3 power

**Scales**: 0 minor, 1 major, 2 dorian, 3 phrygian, 4 mixolydian, 5 harmonic minor

The presets live in `tools/build.py` (in `PRE`), so they survive rebuilds. To add or change one, ask me, or edit the lists there and rebuild. Rhythm codes are 0 rest, 1 note, 2 accent, 3 note plus slide, 4 accent plus slide. Notes are scale steps: 0 root, 2 third, 4 fifth, 7 octave, minus numbers go below the root.
