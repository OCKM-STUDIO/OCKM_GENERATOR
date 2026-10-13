# OCKM_GENERATOR

A drum machine and an easy-to-program bass synth in one box. Built in Pure Data, designed to run on a Raspberry Pi with a 7" touchscreen and a few knobs.

Current version: **v0.7**

## How to open it

Open `OCKM_GENERATOR.pd` in plugdata. Keep the folder together: the main patch finds everything else in the subfolders.

- Click **start/stop** to play
- Click squares to switch steps on and off
- Pick a **pattern** slot (1 to 8). While playing, it switches at the end of the bar
- Press **save** to store the grid in the current slot. It's written to disk straight away
- **Swing %**: 50 is straight. 56 to 62 is the MPC zone
- **Accent**: how much quieter normal hits are than accented ones. 0 means no difference
- **pd drum-settings** (bottom left): tune, decay, level, reverb send and delay send for each drum
- **Bass**: pick an engine (0 acid, 1 sub, 2 FM, 3 reese, 4 pluck, 5 saw), then drag k1 to k4 and drive while it plays. All knobs run 0 to 1
- **pd master-fx** (bottom): reverb and delay levels, reverb size and tone, bass sends, DJ filter and drive
- **pd midi-sync** (bottom): leader (sends MIDI clock) or follower (plays to incoming clock)
- **Bass generator** (temporary controls at the bottom): pick a rhythm, a note pattern, a key and a scale, and it builds the bassline. Press save to keep it in the current slot

## The idea

- **Drums plus bass in one box.** A drum machine with a bass synth that's easy to sequence. 303-style acid is one flavour of bass, not the only one.
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
| Screen | Official Raspberry Pi 7" touchscreen | Not bought |
| Audio | iRig Pro Duo (already owned, check it's recognised) | Owned |
| Knobs | Small USB MIDI knob controller | To choose |
| Storage | microSD card | Not bought |

## Roadmap

1. ~~Pattern saving and swing~~ (v0.1)
2. ~~Bass rhythm presets, note patterns, keys and scales~~ (v0.2). Still to do: editing single bass steps
3. ~~Drum accents per step, plus tune, decay and level per drum~~ (v0.3)
4. ~~More drum voices, up to 8: snare, rim, toms, percussion~~ (v0.3)
5. Touchscreen interface: Lua grid with a drums page, a bass page and a top bar
6. Knobs for live bass control: MIDI mapping, plus drive and accent level (waiting on a controller to test with)
7. ~~Bass engines (acid, sub, FM, Reese, pluck) and master effects (drive, delay, filter)~~ (v0.4)
8. ~~MIDI clock sync~~ (v0.5)
9. Move to the Pi and start on boot

## Decisions made

- **Raspberry Pi, not Daisy or Arduino.** No hardware skills needed, and it runs full Pd, so nothing has to be rewritten.
- **8 drum tracks plus 2 synth tracks.** Fits the screen and stays playable.
- **7" touchscreen plus a few knobs.** The screen is for editing. The knobs are for playing.
- **Toggles first, Lua grid later.** Toggles kept everything visible while learning. The touchscreen needs the Lua grid.
- **Synthesised drums for now.** Samples can be swapped in later, one voice at a time.
- **Patterns saved as text files** in `patterns/`, so saving works on the Pi without a keyboard.

## Parked ideas

- FM drum and bass voices (likely to come back with the bass engines)
- Probability, ratchets and Euclidean patterns
- Different lengths per row
- An Arduino-built custom control panel
- The Daisy route for a fully embedded box

## Reference

- [Acid Drip](https://github.com/lonesoulsurfer/Acid_Drip_Bassline_and_Drum_Synth): a similar acid plus drums box on a Raspberry Pi Pico. Good reference for easy bass entry: tap a step, long-press for accent or slide, notes locked to a scale.

## What's in the folder

| Path | What it is |
|---|---|
| `OCKM_GENERATOR.pd` | Main patch: clock, swing, pattern slots, mixer |
| `voices/` | One file per sound: 8 drums, the reverb (`ockm-verb`), the bass (`ockm-bass` plus one file per engine and a shared `ockm-bass-core`), and the master effects (`ockm-fx`) |
| `seq/` | Sequencers: the drum row, the bass pattern and the bass generator (which also holds the bass presets) |
| `patterns/` | Saved pattern slots, 8 per track. Edited by the patch, not by hand |
| `sketches/` | Early experiments, kept for reference |

## Named hooks

These let other things control the patch: tests now, and the touchscreen, knobs and MIDI later.

| Name | Does |
|---|---|
| `ockm-play` | 1 to start, 0 to stop |
| `ockm-want` | Pick a pattern slot, 0 to 7 |
| `ockm-save` | Save the current slot |
| `ockm-step` | Sends the current step, 0 to 15, as it plays |
| `ockm-master` | The final audio mix |
| `ockm-bass-rhythm` | Bass rhythm preset, 0 to 7, and rebuild |
| `ockm-bass-notes` | Note pattern, 0 to 7, and rebuild |
| `ockm-bass-root` | Key, 0 to 11 (0 = C, 9 = A), and rebuild |
| `ockm-bass-scale` | Scale, 0 to 5, and rebuild |
| `ockm-bass-gen` | Rebuild the bassline with the current settings |
| `ockm-edit` | Set one drum step: track, step (0 to 15), value (0 off, 1 on, 2 accent). For example `kick 4 2` |
| `ockm-bass-edit` | Set one bass step: step, note (MIDI), on, accent, slide. For example `0 33 1 1 0` |
| `ockm-accent` | Accent amount, 0 to 1 |
| `ockm-bass-engine` | Bass engine: 0 acid, 1 sub, 2 FM, 3 reese, 4 pluck, 5 saw |
| `ockm-bass-k1` to `ockm-bass-k4` | Bass knobs, 0 to 1. What they do depends on the engine (see below) |
| `ockm-bass-drive` | Bass distortion, 0 to 1 |
| `ockm-filter` | Master DJ filter, -1 to 1. Below 0 cuts the top, above 0 cuts the bottom, 0 is off |
| `ockm-drive` | Master drive, 0 to 1 |
| `ockm-delay-mix` | Delay return level, 0 to 1 |
| `ockm-delay-fb` | Delay feedback, 0 to 0.9 |
| `ockm-delay-steps` | Delay time in steps. 3 is a dotted 8th |
| `ockm-verb-mix` | Reverb return level, 0 to 1 |
| `ockm-verb-size` | Reverb size, 0 (small room, about 0.4s) to 1 (big hall, about 3s) |
| `ockm-verb-tone` | Reverb tone, 0 dark to 1 bright |
| `ockm-<drum>-verb` | How much of that drum goes to the reverb, 0 to 1 |
| `ockm-<drum>-delay` | How much of that drum goes to the delay, 0 to 1 |
| `ockm-bass-verb`, `ockm-bass-delay` | Bass reverb and delay sends |
| `ockm-stepms` | Sent by the clock: length of one step in ms |
| `ockm-sync` | 0 leader (internal clock, sends MIDI clock), 1 follower (plays to incoming MIDI clock) |
| `ockm-clock-out` | 1 to send MIDI clock when leading, 0 to keep quiet |
| `ockm-bpm` | Set the tempo. In follower mode the measured tempo is sent here |
| `ockm-playing` | Sent by the start/stop toggle: 1 playing, 0 stopped |
| `ockm-tick` | Advance one step (used by the follower) |
| `ockm-reset` | Next step will be step 1 |
| `ockm-midi-rt` | Feed in MIDI clock bytes from somewhere other than a MIDI port |
| `ockm-<drum>-tune` | Tune in semitones, -12 to 12. Drums: kick, snare, clap, rim, chat, ohat, tom, perc |
| `ockm-<drum>-decay` | Decay in %, 100 is normal |
| `ockm-<drum>-level` | Level, 0 to 1 |

## Drums

Eight tracks: kick, snare, clap, rim, closed hat, open hat, tom and perc (a 909-style rimshot; the old cowbell is in `sketches/`). Each step can be off, on or accented. Accented steps play at full strength. Normal steps play at full strength minus the accent amount. For now, accents are set with the `ockm-edit` hook. The squares show on or off only, until the touchscreen work.

Per-drum tune, decay and level aren't saved with patterns yet. Saved drum kits will come later.

## Bass engines

One bass track, six engines. Only the chosen engine runs, so the others cost no processing power. Every engine uses the same four knobs, 0 to 1. k4 is always decay.

| Engine | k1 | k2 | k3 | Character |
|---|---|---|---|---|
| 0 acid | cutoff | resonance | envelope amount | The 303 squelch |
| 1 sub | tone | drive | pitch drop | Deep and clean, 808-ish |
| 2 FM | brightness | ratio | envelope on brightness | Punchy, metallic, plucky |
| 3 reese | cutoff | detune (width) | envelope amount | Dark and wide |
| 4 pluck | brightness | saw to square | filter snap | Rings out and fades over the decay time, with a sub an octave down. Ignores the short 303-style note length |
| 5 saw | tone (1 = fully raw) | second saw detune (0 = single saw) | sub saw an octave down | Hard and buzzy. Notes play at full level for the decay time, then stop |

The bass drive comes after the engine, so it works on all of them.

## Effects

Reverb and delay work like a mixing desk: each track has a **send** that sets how much of it goes to the effect, and the effect's **level** sets how loud the result comes back. Defaults: clap, snare, rimshot and tom get some reverb, the rim and rimshot get a little delay, the kick and bass stay dry. Both effect returns pass through the DJ filter, so a filter sweep takes the echoes and tails with it.

## MIDI clock

- **Leader** (sync 0, the default). OCKM_GENERATOR keeps time and sends MIDI clock, start and stop out of the MIDI port. Your other gear follows it. Clock is sent straight, without swing, so other gear applies its own groove.
- **Follower** (sync 1). OCKM_GENERATOR waits for MIDI start, then steps in time with incoming clock. The BPM box shows the measured tempo. Stop on the other gear stops it too.

Pick the MIDI port in plugdata's audio and MIDI settings. On the Pi, the iRig Pro Duo's MIDI ports should work for this.

## Bass presets

The bassline is built from three choices. Change any one and it rebuilds straight away.

**Rhythms** (when it plays): 0 offbeat, 1 rolling, 2 gallop, 3 acid classic, 4 sparse dub, 5 tech bounce, 6 acid 16ths, 7 trip hop

**Note patterns** (what it plays, used in turn on each note): 0 root, 1 octaves, 2 root and fifth, 3 acid riff, 4 walk up, 5 minor stab, 6 dub, 7 pedal

**Scales**: 0 minor, 1 major, 2 dorian, 3 phrygian, 4 mixolydian, 5 harmonic minor

To add or change presets, open `seq/ockm-bassgen.pd`, double-click the preset lists, edit and save. Rhythm codes are 0 rest, 1 note, 2 accent, 3 note plus slide, 4 accent plus slide. Notes are scale steps: 0 root, 2 third, 4 fifth, 7 octave, minus numbers go below the root.
