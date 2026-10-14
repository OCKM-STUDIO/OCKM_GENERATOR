# Changelog

## v0.33 (14 October 2026)

**Added**
- **Drum fills** on the drums tab: on the last bar of every 4, 8 or 16 bars the drums play a fill (snare roll, tom run, drop or build), then go straight back. Only the drums the fill uses change; your steps are never rewritten. Saved with each pattern

**Changed**
- The grooves grid is five across, to make room for the fill controls

## v0.32 (14 October 2026)

**Fixed**
- The chords were too quiet: the stab engine came out at a third of the bass's level. All three chord engines are now balanced to sit level with the bass and melody (organ was a little loud, pad a little quiet). A test keeps them balanced

## v0.31 (14 October 2026)

**Changed**
- **Mode dial on compose**, like a camera's priority modes: chord priority, melody priority, bass priority, or manual. The priority part is yours; the other two follow it. Manual makes every part yours and keeps what was generated. This replaces "who leads the harmony" and the per-part auto/manual switches
- Synth tabs and compose show each part's role: "yours", or what it follows. Following parts are locked; switch to manual to edit them
- Older patterns with hand-edited following parts open in manual, so nothing is overwritten
- The melody now starts as a following part (it used to start on manual)

**Added**
- **Melody** note patterns (melody, melody steps, melody high): a wandering line over the root, 3rd, 5th and 7th of whatever chord is playing, mostly small steps, coming home every 8 notes. 64 notes before it repeats
- Two melody rhythms with space in them: **hook** and **sparse melody**. The melody now defaults to "melody" over "hook" instead of an arpeggio over 16ths

## v0.30 (14 October 2026)

**Changed**
- The bass, lead and chord tabs show the part's generator settings (notes, rhythm, lock, density, mutate; or progression, rhythm, spice, smooth) next to the sound. They're the same settings as on compose, so they always match
- Tabs: perform and compose sit side by side (perform, compose, drums, bass, lead, chord, mixer, song)
- Delay level is back on perform's master FX, next to feedback and time

## v0.29 (14 October 2026)

**Added**
- The master filter springs back: let go and it glides back to off in about a fifth of a second, like the SP-404. **Hold** keeps it where you leave it
- **Throw** pad: hold it to send the whole mix into its own echo line; let go and the echoes ring out at your delay time and feedback
- The filter is smoothed in the engine, so sweeps and the spring back don't click

**Changed**
- Perform's master FX: a double-width filter with hold, throw, drive; then feedback, time, reverb, size
- Reverb tone moved to setup. The ordinary delay level is on the mixer's master strip
- Filter sweeps and throws don't count as unsaved changes

## v0.28 (14 October 2026)

**Changed**
- The navigation strip only shows the patterns you've made, then +. Tap + and the next number appears. A pattern started empty still counts as made
- Which patterns exist is worked out from the saved files when a project opens, so older projects (like demo grooves) show theirs too
- The step navigator is compact and sits on the left, right above the steps. Pattern in the middle, length on the right
- The song tab only offers patterns you've made
- A key on the drums tab: white is a hit, orange is an accent (louder)

## v0.27 (14 October 2026)

**Added**
- **+** next to the pattern numbers: a new pattern in the next free slot, as a copy of the one you're on or empty, then switches to it
- Empty pattern slots are drawn faint, so you can see which are in use. Remembered with the project
- **Save** turns orange with a dot when there are unsaved changes, and says what it saved (all 8 patterns, the song and the kit)
- Switching to an empty pattern tells you how to fill it

**Changed**
- The "steps" label in the navigation strip is gone, to make room for +

## v0.26 (14 October 2026)

**Added**
- **Song mode**, MPC style. A song tab with one song per project: a chain of steps, each a pattern and how many times it plays. Add, change, reorder and remove steps; loop or stop at the end; play from any step. Patterns switch exactly on the bar line. Saved with the project as `song.txt`
- The play button plays one pattern or the song, and shows the song step while it plays
- **Copy pattern** to another slot, and **clear pattern**, on the song tab
- **Setup screen** (tap the tempo): tempo buttons and slider, swing, accent strength, volume, MIDI clock lead or follow

**Changed**
- Messages now show on every screen (compose's "suggest chords" result was invisible before)
- The save button no longer looks greyed out
- Tapping the tempo opens setup; dragging it still changes the tempo
- Tapping a song row's buttons selects that row

**Fixed**
- Deleting a project left an empty folder behind if it had a song

## v0.25 (14 October 2026)

**Added**
- Start buttons for empty synth parts: "empty: tap to start" on the perform lanes, and a start button on compose and on each synth tab
- A `samples` folder with one folder per drum sound, ready for your own samples

**Fixed**
- A blank project was silent even once the synths had notes: pattern 1 never got the default synth sounds, so the filters sat shut. Blank projects now start with the default sounds

## v0.24 (14 October 2026)

**Added**
- Projects. The **project** button opens a screen to save, go back to the last save, save as a copy, start a new blank project, and open or delete any project
- New projects are named with two random words and the date, like "velvet heron · 14 Oct"
- The project you used last opens at start-up
- Deleting moves the files to a `trash` folder, so nothing is lost by accident

**Changed**
- The starter project is completely blank. The old demo grooves are still there with `python3 tools/build.py --reset-patterns --demo`
- **Save** now writes all 8 patterns, not just the one you're on. Before, edits to patterns you'd switched away from were never saved
- **Revert** (now "back to last save") reloads the whole project
- The top-right **revert** button is replaced by **project**

## v0.23 (14 October 2026)

**Added**
- Drum grooves on the drums tab: 12 presets (four floor to electro) plus clear. One tap fills all 8 drum slots, matched by the sound each slot plays, across the whole pattern, and sets the swing
- A bass or lead locked to the kick follows a new groove straight away

**Changed**
- The drum sliders sit on the left half of the drums tab, to make room for the grooves

## v0.22 (14 October 2026)

**Added**
- Melody-led and bass-led harmony. Write the lead (or let the bass generate), then tap **suggest chords**: every progression is scored against your notes and the best fit is picked. Tap again for the next best
- Rhythm lock for bass and lead: own rhythm, on the kick, or fill the gaps between kicks. Editing the kick redraws a locked part
- Density for bass and lead: fewer or more notes than the preset
- Mutate: a new variation of the bass or lead line. Original brings the preset back
- The chain on compose shows the order for each leader

## v0.21 (14 October 2026)

**Added**
- **Compose** tab: who leads the harmony (chords, or key only; melody-led and bass-led coming), key and scale, the chain of who follows whom, and a column each for the chord, bass and lead generators
- Camera-style lock: a synth part on auto has its steps locked (drawn as outlines). Switch to manual to edit. Manual parts are greyed out on compose and never changed by it
- The leader is saved with each pattern

**Changed**
- Generator settings, key, scale, spice and smooth voicing moved from the synth tabs to compose. The synth tabs are now steps and sound
- Tabs: perform, drums, compose, bass, lead, chord, mixer
- The separate "follow chords" switches are replaced by the leader setting

## v0.20 (14 October 2026)

**Added**
- House bass engine (engine 6, bass and lead): a clean square plus a sub sine an octave down, through a warm low-pass with a short pluck. Knobs: tone, body, pluck, decay
- Band-limited saw and square oscillators (`ockm-blsaw`, `ockm-blsquare`), so new engines don't alias
- The drum lanes on perform are editable: tap a step to cycle empty, hit, accent

**Fixed**
- Fizzy bass and lead. Every note was going through three saturation stages even with drive at 0. The bass/lead drive and the master drive are now completely clean at 0, and the limiter only touches peaks above 80% of full level

## v0.19 (14 October 2026)

**Added**
- Auto and manual for every synth part, like a camera. Auto parts are generated from their presets and follow the chords, key, scale and length. Manual parts keep your notes. Editing a step in auto switches to manual; the auto button hands it back
- The bass follows the chords: with "follow chords" on, the bass pattern sits on each chord's root (V, VI and VII below). Changing the progression moves the bass straight away
- The lead can follow the chords too (off by default)
- Bass and chord start in auto; the lead starts in manual
- 1 new test: the bass follows a deep house progression, stays put in manual, and goes back to auto when you pick a preset

**Changed**
- Changing the key or scale no longer rewrites a part that's in manual

## v0.18 (14 October 2026)

**Added**
- The master effects are back on screen: the bottom of perform is now half synth on the left (bass, lead or chord selector, then its four main knobs) and half master FX on the right (filter, drive, delay level, feedback and time, reverb level, size and tone)
- Compact bar controls with the name and value inside and an orange line at the value. The filter fills from the middle

## v0.17.1 (14 October 2026)

**Changed**
- Step navigation is now back and forward arrows around the steps on screen ("17-32"), with a dot per block: white for the one on screen, orange for the one playing

## v0.17 (14 October 2026)

**Changed**
- Clearer layout on every screen: navigation at the top, sound shaping at the bottom
- Bass, lead and chord each have their own tab and screen (tabs: perform, drums, bass, lead, chord, mixer), so it's obvious what you're editing
- A navigation strip under the tabs on every screen: small pattern buttons, length, and one button per block of 16 steps (only as many as the length allows), with an orange bar for the block that's playing
- Pattern buttons are much smaller on perform, leaving taller track lanes and bigger mute and solo buttons
- Synth screens: key and scale moved into one slim row; a level slider joins the sound view

## v0.16 (13 October 2026)

**Added**
- Mute and solo for every track, on the perform screen (**M** and **S** on each lane) and on the mixer. They fade in and out over 10 ms, so they don't click, and they also silence that track's reverb and delay sends. Silent lanes go dim
- A **mixer** screen: a strip per track with reverb and delay sends, a level fader, mute and solo, plus a master strip with the reverb and delay returns, master volume and a "clear" for mutes and solos
- A level for bass, lead and chord (saved with each pattern) and a master volume (saved with the project)
- 1 new test for mute, solo and level. The touchscreen test now mutes from perform and uses the mixer

**Fixed**
- The step screens' playhead no longer shows on other screens

## v0.15.2 (13 October 2026)

**Added**
- The version number is shown on the screen, top right, so it's obvious which version plugdata has loaded

## v0.15.1 (13 October 2026)

**Fixed**
- The synths screen showed "step 1.0" instead of "step 1"
- The note under the screen no longer names an old version
- The screen tests now pass numbers the way plugdata does, and fail if a number is drawn as a decimal

## v0.15 (13 October 2026)

**Added**
- Chord generator, rebuilt: 10 progressions and 10 rhythms, each ordered from simplest to busiest, plus **spice** 1 to 4 (triad, 7th, 9th, 11th)
- Progressions have their own timing (half-bar to two-bar chords) and length (1 to 8 bars). Picking one makes a shorter pattern long enough to hold it
- **Smooth** voicing for chords, on by default: each chord is played in the shape closest to the last
- Synths screen: **sound** and **fill** views underneath the steps. Sound now includes the reverb and delay sends
- 1 new test: progressions fill and lengthen the pattern. The chord test now covers smooth voicing and the eleventh

**Changed**
- Chord rhythm and progression numbers now point at the new lists. Saved chord parts are untouched until you pick a new progression or rhythm
- Preset names are written into the touchscreen by the build, so the screen and the engine always agree

## v0.14 (13 October 2026)

**Added**
- Tabs for **perform**, **drums** and **synths** on every screen, in the top bar next to play and tempo. They replace the "< perform" button
- A sound strip on perform: pick bass, lead or chord and play its four main knobs, named for the engine
- The master filter on perform

**Changed**
- Perform's track lanes are a little thinner to make room

## v0.13 (13 October 2026)

**Added**
- Touchscreen UI in Lua (`ui/ockm-ui.pd_lua`), following `docs/architecture-and-ui-brief.md`. Three screens:
  - **Perform**: play, tempo, patterns 1 to 8 (queued pattern outlined), a picture of all 11 tracks for the 16 steps playing now, length, save and revert. Tap a track name to open it
  - **Drum**: one slot at a time, 8 sound pads, 16 big steps (tap cycles off, hit, accent), the slot's level, tune, decay and sends
  - **Synth**: bass, lead or chord; key and scale; 16 steps with note names (drag up or down to change a note, or pick from the note row); slide; engine and named knobs; drive or chord type; fill and new
- Swipe the step row sideways to move between blocks of 16. Only as many blocks as the length allows. Perform follows the playhead; the edit screens stay where you put them
- Light and dark themes, and a Pi size: `--theme light`, `--ui-scale 2`
- `tests/ui_preview.py` draws the screens to PNG without Pd
- 2 new tests: tapping and swiping through the screens reaches the engine, and every screen draws without errors

**Changed**
- The main window is now just the screen. The engine moved into `pd engine`, and the v0.12 panel into `pd test-panel`
- The v0.12 panel no longer prints an error when a drum step is edited

**Checked**
- `bob~` comes with plain Pure Data (it's in the Pi's standard `puredata` install), so the acid, reese and pluck engines don't need replacing
- Saving writes to `projects/default` whichever folder Pd was started from

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
