# Changelog

## v0.12 (13 October 2026)

**Added**
- Front panel at the top of the main patch, in a minimal modern style: flat, one orange accent, dark by default
- Top bar: play, tempo, swing, accent amount, pattern 1 to 8, save, revert, length (16, 32, 64, 128) and page
- Drum grid: 8 rows of 16 steps, coloured by state (empty, hit, accented hit), with a playhead and an accent-tap switch
- Per slot: sound choice, level, tune, decay, reverb and delay sends
- Synths: shared key and scale, plus engine, knobs, drive or chord type, sends, generator choices and a "new" button for each of bass, lead and chord
- Effects row with MIDI clock switches
- Light theme: `python3 tools/build.py --theme light`
- 1 new test: the panel drives the engine (step clicks, accents, length, page, pattern buttons, redraw and playhead)

**Changed**
- The engine now sits below the panel in the main patch. Nothing in it changed, and the old controls still work

## v0.11 (13 October 2026)

**Added**
- Central settings store: every setting and every pattern is saved and restored. Nothing resets when you reopen the patch
- Projects: `projects/default/project.txt` holds tempo, master effects, MIDI, accent and the drum kit; `p1.txt` to `p8.txt` hold one pattern each
- Synth sounds belong to each pattern; the drum kit belongs to the project
- New, empty patterns keep the current synth sounds, key and swing
- Switching patterns keeps unsaved edits in memory; **revert** reloads from disk
- On-screen settings boxes show the stored values (via `ockm-show-...` hooks)
- 3 new tests: kit versus pattern sounds and inheritance, save, quit and reopen, and revert

**Changed**
- The old per-track `patterns/` files were replaced by the project files. The starter patterns carried over
- Generators no longer rebuild while a pattern is loading

## v0.10 (13 October 2026)

**Added**
- 8 drum slots (was 6). The new slots default to rim and tom
- Lead synth: the same six engines as the bass, two octaves up, with its own pattern and generator
- Chord synth with three engines (stab, organ, pad), four chord types and eight progressions. Chords are worked out as they play, so key changes apply instantly
- Shared key and scale for bass, lead and chord (`ockm-root`, `ockm-scale`)
- Four lead-friendly note patterns: arp up, arp up-down, call, descend
- A synth-settings panel for all synth controls; reverb and delay sends for lead and chord
- Starter lead and chord parts in the starter patterns
- 3 new tests: lead octave, chord voicing (key, scale, type, accent) and chord engines

**Changed**
- The bass voice became a general mono synth (`ockm-mono`), used for both bass and lead
- `ockm-bass-root` and `ockm-bass-scale` replaced by the shared `ockm-root` and `ockm-scale`
- Presets moved into one shared object (`ockm-presets`)
- Building no longer overwrites saved patterns: it only creates pattern files that are missing

## v0.9 (13 October 2026)

**Added**
- Patterns up to 128 steps, with one length per pattern, saved per slot
- Pages: the squares show 16 steps at a time, and the page control moves through the pattern
- Making a pattern longer repeats its existing steps to fill the new ones (all tracks)
- The bass generator now fills the whole pattern length
- Drum slots: each of the 6 drum tracks can play any of the 8 drum sounds
- 3 new tests: slot sound switching, long patterns and pages, and the generator filling long patterns

**Changed**
- 6 drum slots instead of 8 fixed drums. Defaults: kick, snare, clap, closed hat, open hat, rimshot
- Switching patterns, and pressing play, now start from step 1
- Pattern files are now `d1` to `d6` (8 slots x 128 steps), plus `length.txt`. The old per-drum files were retired; the starter patterns were carried over

**Fixed**
- Two places where Pd's wiring order wasn't guaranteed are now explicit, so a pattern switch always starts cleanly

## v0.8 (13 October 2026)

Housekeeping release. Sounds and behaviour are unchanged.

**Added**
- Git version history for the whole folder
- `tools/build.py`: the generator that writes every patch file now lives in the project
- `tests/run_tests.py`: 12 automatic checks covering voices, accents, step edits, pattern saving, swing, bar-locked switching, the bass generator, all six bass engines, delay, reverb, MIDI clock and mix level

**Changed**
- Shared names that lacked the `ockm-` prefix renamed: `kick-pat` is now `ockm-pat-kick`, `kick-bank` is `ockm-bank-kick`, `bass-note` is `ockm-pat-bass-note`, and the step squares are `ockm-sq-<track>-<step>`. Pattern files on disk are unchanged

## v0.7 (13 October 2026)

**Added**
- Reverb in the master effects, with size and tone controls
- Reverb and delay sends on every track (8 drums and the bass), set in drum-settings and master-fx
- Sensible default sends: clap, snare, rimshot and tom in the reverb, rim and rimshot in the delay, kick and bass dry

**Changed**
- The delay is now fed by the per-track sends instead of sitting across the whole mix. The old "delay mix" is now "delay level", the return level
- Perc track is now a 909-style rimshot. The cowbell moved to `sketches/ockm-cowbell.pd`

## v0.6 (13 October 2026)

**Added**
- Saw bass engine (engine 5): a raw sawtooth with a tone control, an optional detuned second saw and a sub saw. Turn k1 to 1 for the fully raw sound

## v0.5.1 (13 October 2026)

**Fixed**
- Pluck bass sounded almost the same as acid. Rebuilt it: notes now ring out and fade instead of being cut short, with a saw-to-square blend, a gentler filter and a sub an octave down

## v0.5 (13 October 2026)

**Added**
- MIDI clock leader: sends clock (24 per beat), start and stop
- MIDI clock follower: steps to incoming clock, follows start, continue and stop, and measures the tempo
- A midi-sync panel to switch between leader and follower and turn clock out on or off
- Hooks for tempo, sync mode and play state

## v0.4 (13 October 2026)

**Added**
- Five bass engines: acid, sub, FM, reese and pluck. Switch with one number. Only the chosen engine runs
- Bass drive, after the engine
- Master effects: DJ filter (low-pass and high-pass on one control), drive, and a delay locked to the tempo
- A soft limiter at the very end, so the output can't hard-clip

**Changed**
- Bass knobs now run 0 to 1 for every engine, ready for real knobs
- All engines share one piece of note logic (`ockm-bass-core`), so accent and slide behave the same everywhere
- The old acid voice moved to `sketches/ockm-acid-v02.pd`

## v0.3 (13 October 2026)

**Added**
- Four new drums: snare, rim, tom and perc (808-style cowbell). Eight drum tracks in total
- Accents per drum step, plus an accent amount control
- Tune, decay and level for every drum, in a drum-settings panel and as hooks
- Hooks to edit a single drum step or bass step, ready for the touchscreen
- Starter patterns now use the new drums and include accented hats

**Changed**
- Every drum voice now takes a hit strength instead of a plain trigger

## v0.2 (13 October 2026)

**Added**
- Bass generator: builds a bassline from a rhythm preset, a note pattern, a key and a scale
- 8 rhythm presets, 8 note patterns, 6 scales, all 12 keys
- Notes are always in key, whatever you pick
- Temporary number boxes to try it out. The real controls come with the touchscreen
- Hooks for rhythm, notes, key, scale and rebuild

**Fixed**
- Added a visible declare object, so the patch still finds its subfolders after you save it in plugdata

## v0.1 (13 October 2026)

First proper version, moved into the OCKM_GENERATOR folder.

**Added**
- 8 pattern slots, saved to disk with the save button
- Pattern switching waits for the end of the bar while playing
- 4 starter patterns: house, tech house, broken beat, hip hop feel
- Swing control (50 to 75%)
- Acid bass voice with accent and slide, plus cutoff, resonance, env amount and decay controls
- Fixed basslines in each starter pattern
- Named hooks for play, pattern, save, step and master output

**Fixed**
- Drum rows no longer share one pattern. Clicking a square only affects its own row
- Clap no longer clips

**Changed**
- Files renamed from `dm-` to `ockm-` and sorted into `voices/`, `seq/` and `patterns/`
