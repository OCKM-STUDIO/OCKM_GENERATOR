# OCKM_GENERATOR

A drum machine and easy-to-program synths in one box. Built in Pure Data, designed to run on a Raspberry Pi with a touchscreen and a few knobs.

Current version: **v0.50**

## How to open it

Open `OCKM_GENERATOR.pd` in plugdata. Keep the folder together: the main patch finds everything else in the subfolders.

The window is the instrument: three touch screens, drawn in Lua (plugdata has Lua built in). Click with the mouse on the Mac, tap with a finger on the Pi. If clicks do nothing, the patch is in edit mode: press Cmd+E.

**How every screen is laid out**, top to bottom:
1. **Top bar:** play, tempo, then the screens as tabs in three groups: playing (**Perform A, Perform B, mixer**), making (**compose, drums, bass, lead, chord**) and **arrange**. On the right, **save** (a disc, orange when there's something to save) and **☰**, the menu: project, export, settings, revert (and quit to desktop on the Pi). The version number sits next to the tempo
2. **Navigation strip:** on the left, right above the steps, the **steps** navigator: back and forward arrows either side of the steps you're looking at (for example "17-32"). The dots show every block of 16: white is the one on screen, orange is the one playing. You can also swipe the step row sideways. In the middle, how long the loop is and which part sets it, like "loop 4 bars (bass, lead, chords)". On the drums, bass, lead and chord tabs, the right of the strip has that part's **length** (1, 2, 4, 8 or 16 bars) and **double**. See "Part lengths" below
3. **What you're editing:** the steps (and, on the drums screen, which of the 8 drum slots)
4. **Sound shaping** at the bottom

Tap a track's name on Perform A or the mixer to jump straight to it.

**Perform A** (home)
- **Play** and **tempo** top left. Drag the tempo number up or down
- One loop per project: everything you play live works on it. **Save** (the disc) keeps the loop and the kit. It turns orange when there's something unsaved
- **The drums**: 8 lanes for the 16 steps on screen, with the playhead running above them. **Tap a step to edit it** (empty, hit, accent), just like the drums screen. Tap a drum's **name** to open it
- **M** mutes a track and **S** solos it (several can be soloed at once). Mutes and solos are for playing live, so they aren't saved
- **Bottom left, the synths:** bass, lead and chord buttons, each with its own **M** and **S** and a light that flashes as the part plays. Tap one to pick it, then:
  - bass or lead on auto: **new** (a fresh variation), **orig** (back to the one you started with) and **busy** (fewer or more notes)
  - chords: step through the chord **rhythms**
  - an empty part: a button to start it
  - and the part's four main knobs (named for the engine it's using)
- **Bottom right, master FX**, played like an SP-404:
  - **Moves** along the top: **rise** and **pump** switch on and off. **Drop** (hold it): nothing new plays while you hold it, the effects ring on, and everything comes back on the next bar after you let go. **Throw** (hold it): sends the whole mix into its own echo line; let go and the echoes ring out at your delay time and feedback. The dub throw
  - **Filter**: drag left for low-pass, right for high-pass. Let go and it snaps back to off. Tap **hold** (in its corner) to make it stay where you leave it; tap hold again and it snaps home
  - **Drive** beside it; then delay level, **feedback** and **time** (in steps); reverb level and **size**. Reverb tone is in settings
- These are bars: drag along them. The orange line shows the value
- **Length** is in the navigation strip. Making the loop longer repeats what's there
- **Save** and **project**, top right

**Perform B** (no steps, just mutes and effects, big enough for thumbs)
- **A tile per track**, plus **all synths**. Tap anywhere on a tile to mute it or bring it back; **S** in its corner solos. The light flashes as the track plays
- **Mutes land:** **now** (straight away, like an MPC's track mute), **next beat** or **next bar**. A change that's waiting gets an orange outline and says when it lands, so you can tap several and have them all switch together. Stopped, they land at once
- **Scenes** along the bottom: drums only, no drums, kick + bass, all in. They clear any solos and go through the same timing
- **Master effects:** rise, pump, drop and throw; a big filter with hold; drive and master volume; delay and reverb
- **Macros:** three slots, A, B and C. Hold one to play it; let go and everything goes back (a macro with a move that stays lights up and waits: tap it again to let go). The small **v** on each picks which of your six macros is on that slot. Out of the box: build, wash and strip

**Drum** (one slot at a time)
- The 8 slots along the top, named by the sound they play
- **Sound**: 8 pads, one per drum sound
- **Steps**: tap cycles empty, hit (white), accent (orange)
- Move between blocks of 16 with the **steps** arrows in the navigation strip, or swipe the step row sideways
- **Level, tune, decay, reverb, delay** for this slot. These belong to the kit, so they stay when you change pattern
- **Grooves** (right of the sliders): tap one to fill all 8 drums at once. Each slot gets the part for the sound it plays, so a groove's hats land on whichever slot is your hat. A groove is one bar, so it makes the drums 1 bar long (go longer and it repeats), and sets a swing to suit. Twelve to pick from: four floor, house, deep house, tech house, minimal, techno, dub techno, garage, breakbeat, boom bap, trip hop, electro. **Clear** empties the drums. A groove replaces your drum steps, so the message that pops up has an **undo** button
- **Fills** (under the grooves): **fill on the last bar of every** 4, 8 or 16 bars, counted from when you press play. Styles: **snare roll** (builds through the second half of the bar), **tom run**, **drop** (kick and claps out for the last half bar, hats out for the last beat, so the next downbeat lands harder), **build** (snare 16ths rising over the whole bar). A fill only replaces the drums it uses; everything else keeps playing your pattern, and your steps are never changed. Saved with each pattern, so a breakdown can have fills off

**Compose** (next to perform): how the loop is put together. Each part's card (chord, bass, lead) has **M** and **S**, the same mute and solo as on perform and the mixer.
- **Mode**, like a camera's priority modes: which part is yours. The others follow it
  - **chord priority:** the chords are yours (a progression, or edit the chord steps). Bass and melody follow the chords
  - **melody priority:** the melody is yours. The chords are picked to fit it (**suggest chords** tries all 10 progressions and picks the best; tap again for the next best), and the bass follows the chords
  - **bass priority:** the same, starting from the bass line. The melody follows the chords
  - **manual:** every part is yours, exactly as it was. Nothing is regenerated. Switch here when you want to hand-edit a part that was following
- **Key and scale**, shared by every part
- **The chain:** which part is yours and which follow
- **A column each for chord, bass and lead** with their generator settings. Use the arrows to step through the presets. A change rewrites the part straight away
  - Chord: progression, rhythm, spice and smooth voicing
  - Bass and lead: notes and rhythm, then:
  - **own rhythm | on the kick | fill gaps:** use the preset rhythm, play only where the kick plays, or play only where it doesn't. Locked parts redraw when you edit the kick
  - **density:** drag left for fewer notes, right for more. The middle is the preset as written
  - **mutate:** a new variation of the same idea (different note order, the odd octave jump). Tap again for another. **Original** goes back

**Starting from empty.** A synth part with no notes says so: on perform its lane reads "empty: tap to start", and compose and its own tab show a **start** button. Start hands the part to its generator (auto) and makes notes straight away. For the lead you can also just write a tune by hand on the lead tab.

**The rule: the priority part is yours, the other two follow it.**
- **Yours:** edit the steps freely, or use its presets as a starting point. Picking a preset replaces what's there
- **Follows:** generated to fit. Its steps are drawn as outlines and locked, but you can still shape it with its settings (notes, rhythm, lock, density, mutate). To edit its steps, switch the mode to **manual**: you keep everything that was generated
- Sound controls (engine, knobs, drive, sends, level) always work, whatever the mode
- Going from manual back to a priority regenerates the following parts. An older pattern with hand-edited following parts opens in manual, so nothing is lost

**Bass, lead and chord** (a tab each)
- **Key** and **scale** at the top, shared by all three
- **Steps**: tap cycles off, on, accent. **Drag a step up or down** to change its note. Or tap a step, then pick its note from the row underneath (the dimmed one is the key's root). **Slide** applies to the selected step
- Chord steps show the chord on that step of the scale (i, ii, iii...)
- The **auto | manual** switch, and a line saying where the notes come from
- **Notes** (bottom left): the same generator settings as this part's column on compose, so a change in either place shows in both
- **Sound** (bottom right): engine, its four knobs (named for the engine), drive, reverb and delay sends, level
- On manual: the note (or chord) picker for the selected step, and slide

**Settings** (☰, or tap the tempo). Four sections:
- **This project** (saved with it): tempo with -5, -1, +1, +5 and a slider, swing, how strong accents are, reverb tone, and MIDI clock: lead (send clock out) or follow (play to incoming clock). Dragging the tempo up or down in the top bar still changes it directly
- **New projects:** how a new blank project starts: drums 1, 2 or 4 bars; synths 2, 4 or 8 bars; the lead as hook, motif, call and answer, or arp
- **This device:** theme (dark or light), how fast the filter lets go (snap, quick, slow), and where Perform B's mutes start (now, next beat, next bar)
- **Macros:** your six macros. Each is up to four moves: what (filter, delay, feedback, reverb, size, drive, pump, volume, rise, throw or a set of mutes), how much, how it gets there (jump, or over a beat, a bar, 2 or 4 bars) and how it lets go (snap back, glide back over a bar, or stay). Tap a box to step through its choices. Pick which slot it's on (A, B or C) and hold **try it** to hear it. Names come from a list (there's no keyboard on the Pi)

New projects, this device and macros are yours, not a project's: they're kept in `my-settings.lua` beside the patch, so they're the same in every project.

**Mixer**
- One strip per track: reverb and delay sends at the top, a level fader, then **M** and **S**. Tap a strip's name to open that track
- **Master** on the right: the reverb and delay return levels, the master volume, and **clear** to undo every mute and solo
- **EQ** on every strip opens that track's EQ: low cut, a low shelf at 100 Hz, a mid bell you can move, and a high shelf at 8 kHz (each ±12 dB). A curve shows what you've set. While the song plays, bars behind the curve show where that track's sound sits, so you can see what to cut. The EQ button lights when it isn't flat. EQ belongs to the project
- **De-mud** on the master strip clears low-mid fog. Press it while playing and it listens to the mix for 4 seconds, then gives each track (except the kick and bass) a low cut just below where its own sound starts. If the mix piles up around 250 to 500 Hz, the chords, lead and snare get a small scoop there too. Stopped, it sets safe starting low cuts instead. **Undo** takes it back
- Drum levels belong to the kit (the project). Bass, lead and chord levels belong to each pattern, like the rest of their sound

Everything is on the screens now, so `pd test-panel` is only for testing.

**Arrange** (the last tab) is being rebuilt: your loop will become a track as a row of 16-bar units, with a transition at every joint. For now the tab says so. Song mode, the 8 pattern slots and the old Arrange were removed in v0.47.

**Under the screen:** `pd engine` is the sound and sequencer (open it only if you're curious). `pd test-panel` is the old v0.12 panel with every control on one sheet, kept for testing.

**Projects** (the **project** button, top right). A project is one loop plus the drum kit, tempo and effects. It opens on the one you used last.
- **Save** writes the loop and the project. **Back to last save** throws away everything since
- **Undo** (one step): arrange, a groove, clear, new kit and de-mud each put an **undo** button in the message that follows. It takes everything (the loop, kit, EQ, tempo) back to just before. Only the last one can be undone, and opening another project or going back to last save forgets it. The copy lives in `undo/` beside `projects/`
- **New blank project** starts from nothing: an empty loop, the default kit and sounds. It's named for you with two random words and the date, like "velvet heron · 14 Oct"
- **Save as a copy** keeps the project you were in as it was last saved, and carries on in a copy
- **Your projects**, newest first. Tap one, then **save mine, then open**, **open without saving**, or **delete** (tap twice). Deleting moves the files to a `trash` folder next to `projects/`, so nothing is lost by accident

Everything is remembered: drum kit, synth sounds, effects, tempo, swing, key and the steps.

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
6. **Help, don't take over.** You can do everything by hand, or let the machine do it. Whatever it makes you can change. Not a one-button song generator

## Hardware

| Part | Choice | Status |
|---|---|---|
| Computer | Raspberry Pi 5, 4GB, with Active Cooler and the official 27W power supply | Set up (October 2026) |
| Screen | Official Raspberry Pi Touch Display 2, 10" (1200 x 1920 portrait, turned to landscape). Decided: big enough for finger-sized steps | Set up |
| Audio | Raspberry Pi DAC Pro on the GPIO pins (the Pi 5 has no audio socket). RCA outputs, then a 2 x RCA to 2 x 1/4" TS lead into a stereo channel of the mixer (Zoom L6, channels 3/4 or 5/6). The iRig Pro Duo works for testing on the Mac | Not bought |
| Screen power | Small USB power adapter for the screen, because the DAC Pro covers the GPIO pins the screen would normally take power from | Not bought |
| Controller | Endless knobs with light rings. Front runners: Novation Launch Control 3 (16 knobs, screen) or Behringer X-Touch Mini (8 knobs, 16 buttons). Maybe a Launchpad Mini later for a hands-on step grid | To choose |
| Storage | microSD card | Set up |
| MIDI | USB only for now: the controller plugs straight into the Pi. If syncing with gear that only has 5-pin MIDI sockets is ever needed, add a Roland UM-ONE mk2 (avoid cheap unbranded cables) | Decided |

## On the Pi

The Pi runs the same app as the Mac, drawn at double size (`--ui-scale 2`), so the 960 x 600 layout fills the 1920 x 1200 screen exactly. It starts by itself when the Pi powers on.

- **System:** Raspberry Pi OS (Debian 13, 64-bit) with the desktop. Hostname `ockm`, user `simon`. Pure Data 0.55 and pd-lua 0.12.23 from the Pi's own software catalogue (`sudo apt install puredata pd-lua lua5.4`)
- **The app** lives in `~/OCKM_GENERATOR`. After copying a new version over, rebuild it there with `python3 tools/build.py --ui-scale 2`. Don't copy `projects/` over the Pi's own projects
- **Start-up:** `~/.config/autostart/ockm.desktop` runs `tools/pi/ockm-start.sh`. That picks the DAC Pro for sound when it's fitted (otherwise it starts silent) and opens the patch full screen
- **`tools/pi/ockm-kiosk-plugin.tcl`** only acts when started by that script: full screen, no menu bar, no scrollbars, Pd's console hidden. It also makes touch work: a finger jumps from place to place without the pointer moving, so the plugin reports a move before each press and after each lift. Without that, single taps get lost
- **Drum steps, M and S act the moment a finger lands,** like pads on a drum machine. Everything else acts when the finger lifts. Swiping sideways after pressing a step puts the step back and turns the page
- **Screen rotation** is in `~/.config/kanshi/config` (`transform 90`). Touch follows it automatically
- **Remote access:** SSH (`ssh simon@ockm.local`) and Raspberry Pi Connect. Claude reaches it through your Mac with the key in `.pi/` (kept out of git)
- **Tests run on the Pi too:** `PDLUA=/usr/lib/pd/extra/pdlua python3 tests/run_tests.py`. They only ever use a clean copy of the blank project, never yours

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
13. ~~Your drum samples, chosen per slot~~ (v0.36). Later: load sample folders from a USB stick or SD card on the Pi
14. ~~Song mode, MPC style~~ (v0.26). ~~Arrange: turn pattern 1 into a whole track~~ (v0.40, beta: needs more work on transitions and drops). ~~Export: mix, stems, MIDI and live recording~~ (v0.41)
15. ~~A usability pass~~ (v0.26). Keep going after each round of playing
16. ~~A setup screen for tempo, swing, accents, volume and MIDI clock~~ (v0.26)

## Decisions made

- **Arrange is a beta feature** (decided October 2026). It's useful as a starting point; making transitions and drops properly musical will take a lot more work, so it's parked as beta rather than polished now.
- **Raspberry Pi, not Daisy or Arduino.** No hardware skills needed, and it runs full Pd, so nothing has to be rewritten.
- **11 tracks: 8 drum slots plus 3 synths (bass, lead, chord).** Between a TR-6S and a TR-8. More would make the screen too busy without making the music better.
- **One loop, a length per part** (decided October 2026). Drums, bass, lead and chords each 1 to 16 bars; the loop is the longest. Shown 16 steps at a time.
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
- **The drum kit belongs to the project; synth sounds belong to the loop.** See "How it's organised".
- **V1 is touchscreen only** (decided October 2026). The Pi box works like a dedicated iPad app: everything is reachable on the screen, landscape only. A hardware controller and MIDI mapping come in V2. An iPad app is a likely phase two: same Pd engine (via libpd), screens rebuilt natively.
- **One loop, many arrangements** (decided October 2026, replacing song mode and the 8 pattern slots). Every project is one loop of 8 or 16 bars. An arrangement is a row of 16-bar units, each a state of the loop, with a transition from a toolkit at every joint. See the design doc, "One loop, many arrangements".

## Parked ideas

- **No sample chopping** (decided October 2026). SP-404 style slicing of loops would make this a different instrument. Samples are one-shots on drum slots only

- FM drum and bass voices (likely to come back with the bass engines)
- Probability, ratchets and Euclidean patterns
- Different lengths per drum row (the drums share one length), and odd lengths or polymeter (lengths are 1, 2, 4, 8 or 16 bars)
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
| `projects/` | One folder per project, named like `2026-10-14-velvet-heron`, each holding `project.txt` (tempo, effects, MIDI, accent, drum kit) and `loop.txt`, the loop. `current.txt` names the one that opens at start-up. `default` is the blank starter |
| `trash/` | Deleted projects. Empty it by hand when you're sure |
| `samples/` | One folder per drum sound (kick, snare, clap, perc, hat, open-hat, tom) for your own samples. Perc 1 and perc 2 share the perc folder. Not saved to git |
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
5. **Loop:** the steps for all 11 tracks, plus each part's length (1 to 16 bars), swing, key and scale, generator choices and **the three synth sounds**.
6. **Project:** a whole set. The loop, **the drum kit**, tempo, master effects, MIDI settings and accent amount.

| Setting | Lives in |
|---|---|
| Drum kit (all 8 drum slots) | Project |
| Tempo, master effects, MIDI sync, accent | Project |
| Steps, length, swing, key and scale | Loop |
| Synth sounds (bass, lead, chord) | Loop |
| Generator choices | Loop |

**Rules**
- **Save** writes the loop and the project to disk. **Revert** reloads the whole project from disk. Closing without saving loses unsaved changes.
- Files are plain text, one setting or one track per line, so they're easy to read, copy and back up.

## Named hooks

These let other things control the patch: tests now, and the touchscreen, knobs and MIDI later.

| Name | Does |
|---|---|
| `ockm-play` | 1 to start, 0 to stop |
| `ockm-want` | Pick a pattern slot, 0 to 7 |
| `ockm-save` | Save the loop and the project to disk |
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
| `ockm-drum-len`, `ockm-bass-len`, `ockm-lead-len`, `ockm-chord-len` | A part's length in steps (16, 32, 64, 128, 256). Saved with the loop. Longer repeats the part's bars; shorter keeps the rest |
| `ockm-<part>-double` | Copy a part's bars after themselves and double its length (up to 256 steps) |
| `ockm-length` | Older screens and tests: sets every part's length at once (drums stay shorter if they were) |
| `ockm-len` | Sent by the engine: the loop length, the longest part (not set directly) |
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
| `ockm-leader` | The mode: 0 chord priority, 1 melody priority, 2 bass priority, 3 manual |
| `ockm-pattern-copy <from> <to>` | Copy a pattern (0-7) to another slot |
| `ockm-pattern-clear <n>` | Empty a pattern |
| `ockm-bar` | Sent by the clock at the start of every bar |
| `ockm-fill-every` | 0 no fills, or 4, 8, 16: the last bar of every so many bars plays a drum fill |
| `ockm-fill-style` | 0 snare roll, 1 tom run, 2 drop, 3 build |
| `ockm-drum-groove` | Fill every drum slot with a groove, 0 to 11, or 12 to clear. Sets the swing too |
| `ockm-chord-rhythm` | Chord rhythm preset, 0 to 7, and rebuild |
| `ockm-chord-prog` | Chord progression, 0 to 9, and rebuild |
| `ockm-chord-type` | 0 triad, 1 seventh, 2 sus2, 3 power chord. Applies straight away |
| `ockm-edit` | Set one drum step: slot, step (0 to 127), value (0 off, 1 on, 2 accent, anything between 0 and 1 a velocity). For example `d1 4 2` |
| `ockm-nudge` | One drum step's timing: slot, step, -0.25 (a quarter step early) to 0.25 (late). Saved with the pattern |
| `ockm-drum-loop` | Older screens: the drums' length when shorter than the synths (0 = not shorter). Setting it sets the drum length |
| `ockm-bass-edit`, `ockm-lead-edit` | Set one bass or lead step: step (0 to 127), note (MIDI), on, accent, slide. For example `0 33 1 1 0` |
| `ockm-chord-edit` | Set one chord step: step, 0 off / 1 on / 2 accent, chord root as a scale step (0 is the key's root). For example `4 1 5` |
| `ockm-accent` | Accent amount, 0 to 1 |
| `ockm-<synth>-engine` | bass and lead: 0 acid, 1 sub, 2 FM, 3 reese, 4 pluck, 5 saw, 6 house. chord: 0 stab, 1 organ, 2 pad |
| `ockm-<synth>-k1` to `-k4` | Synth knobs, 0 to 1. What they do depends on the engine (see below) |
| `ockm-bass-drive`, `ockm-lead-drive` | Distortion, 0 to 1 |
| `ockm-filter` | Master DJ filter, -1 to 1. Below 0 cuts the top, above 0 cuts the bottom, 0 is off. Smoothed, so moves don't click |
| `ockm-filter-glide <to> <ms>` | Glide the filter to a value, for example `0 50` to snap back to off |
| `ockm-<track>-mute-q` | Ask for a mute (0 or 1) that lands on the next beat or bar, by `ockm-mute-quant` (0 now, 1 beat, 2 bar) |
| `ockm-beat` | Sent by the engine on every beat, before that step's hits (like `ockm-bar`) |
| `ockm-drop` | 1: nothing new plays (effects ring on). 0: everything comes back on the next bar (straight away when stopped) |
| `ockm-filter-now` | Sent by the engine: where the filter actually is (what gets saved) |
| `ockm-delay-throw` | 1 sends the whole mix into the throw echo line, 0 stops sending (the echoes ring out) |
| `ockm-drive` | Master drive, 0 to 1 |
| `ockm-delay-mix` | Delay return level, 0 to 1 |
| `ockm-delay-fb` | Delay feedback, 0 to 0.9 |
| `ockm-delay-steps` | Delay time in steps. 3 is a dotted 8th |
| `ockm-verb-mix` | Reverb return level, 0 to 1 |
| `ockm-verb-size` | Reverb size, 0 (small room, about 0.4s) to 1 (big hall, about 3s) |
| `ockm-verb-tone` | Reverb tone, 0 dark to 1 bright |
| `ockm-<slot>-sound` | Which sound a drum slot plays: 0 kick, 1 snare, 2 clap, 3 perc 1, 4 closed hat, 5 open hat, 6 tom, 7 perc 2 |
| `ockm-<slot>-sample` | 0 = a synth sound, n = the nth file in that sound's sample folder. Saved with the project |
| `ockm-<slot>-synth` | Which synth sound: 0 909, 1 808, 2 industrial |
| `ockm-<slot>-tone`, `-drive`, `-start` | Tone -1 (darker) to 1 (brighter); drive 0 to 1; start 0 to 1 (samples: skip up to 40% in) |
| `ockm-<slot>-audition` | Play the slot once (the screen uses it when you pick a sound or sample) |
| `ockm-samples-scan` | Count the files in each sample folder again. Answer: `ockm-sample-counts` with 7 numbers, in the order kick snare clap perc hat open-hat tom |
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

Eight drum slots, d1 to d8. Each slot can play any of 8 sounds: 0 kick, 1 snare, 2 clap, 3 perc 1, 4 closed hat, 5 open hat, 6 tom, 7 perc 2. Perc 1's synth sound is a short rim and perc 2's a 909-style rimshot (the old cowbell is in `sketches/`). Only the chosen sound runs. The default line-up is kick, snare, clap, closed hat, open hat, perc 2, perc 1 and tom.

Each slot's sound is fixed (slot 1 kick, 2 snare, 3 clap, 4 hat, 5 open hat, 6 perc 2, 7 perc 1, 8 tom); what changes is its sample. Tapping a step cycles off, on and accent. Accented steps play at full strength; normal steps play at full strength minus the accent amount.

### Velocity and timing

The lane under the steps has two modes. **Velocity**: drag a step's bar up or down, or swipe across to draw a shape; the top tenth snaps to accent. **Timing**: drag up to push a hit late, down to pull it early, up to a quarter of a step either way.

To make early hits possible, the whole engine plays a quarter of a step behind the clock (about 30 ms at 124 bpm). Everything moves together, so you won't hear it. Gear following OCKM's MIDI clock will play about that much ahead.

### Part lengths

Every part has its own length: the drums (all 8 rows together), bass, lead and chords, each 1, 2, 4, 8 or 16 bars. **The loop is as long as the longest part,** and shorter parts repeat inside it. So you can draw a 1-bar beat under a 4-bar bassline and hear it all.

- **Set a part's length** on its tab, on the right of the navigation strip. The steps and the playhead on that tab follow the part's own length; perform shows every lane repeating at its own length
- **Longer** repeats the part's own bars to fill the new ones. **Shorter** keeps the bars beyond (nothing is deleted, go longer again and they come back), and the message has an **undo** button
- **Double** copies the part's bars (steps, velocity and timing) after themselves: 1 bar becomes 2, up to 16
- **New projects** start with drums at 1 bar and the bass, lead and chords at 4 bars
- **Generators write their natural length:** a groove makes the drums 1 bar; a chord progression sets the chords to the progression's length. A bass or melody that follows the chords takes the chords' length too

### Grooves

Three banks of 12: classics, house + garage, and techno + breaks. A groove rewrites all 8 drums and sets the swing; **undo** takes it back.

Slot sounds, samples, tune, decay, level and sends are part of the drum kit, which is saved with the project and shared by every pattern.

### Samples

Each slot has three built-in synth sounds, then the samples in its folder in `samples/` (perc 1 and perc 2 share `perc`). On the drums tab, the sound box picks it: the arrows step through **909 → 808 → industrial → your samples**, each change plays the new sound, and tapping the box plays it again.

| Slot | 909 | 808 | Industrial |
|---|---|---|---|
| kick | fast drop, click, a little saturation | long deep boom | hard click, distorted rumble |
| snare | tuned body, bright snap | more tone, less rattle | distorted noise blast |
| clap | four hard bursts, two noise bands, crunch | loose and roomy | wide gritty bursts, big room |
| perc 1 | rim | clave | metallic clank |
| hat / open hat | bright noise | six square waves, the 808 metal | harsh metal / trash ride |
| tom | sweep tom | round 808 tom | dirty tom |
| perc 2 | rimshot | 808 cowbell | laser zap |

The sliders change with the source. **Synth:** level, tune, decay, tone (darker to brighter), drive. **Sample:** level, pitch, length, tone, start (skips up to 40% into the sample, to trim a slow attack). Reverb and delay sends are on the mixer. **New kit** picks a random sample for every slot that has some.

- Samples are numbered in file-name order, so `01.wav` is sample 1. WAV and AIFF, mono or stereo (only the left channel plays), any sample rate
- Tune changes the playback speed, like an MPC: +12 is an octave up and twice as short. Decay below 100 fades the tail early; at 100 or more the whole sample plays
- Files added while it's running show up next time you open the drums tab
- `tools/pick_samples.py` fills the folders from a big sample library: 20 per sound, grouped by source, with `samples/sources.csv` (kept out of git) saying where each came from

## Bass engines

The bass has seven engines. Only the chosen engine runs, so the others cost no processing power. Every engine uses the same four knobs, 0 to 1. k4 is always decay.

| Engine | k1 | k2 | k3 | Character |
|---|---|---|---|---|
| 0 acid | cutoff | resonance | envelope amount | The 303 squelch |
| 1 sub | tone | drive | pitch drop | Deep and clean, 808-ish |
| 2 FM | brightness | ratio | envelope on brightness | Punchy, metallic, plucky |
| 3 reese | cutoff | detune (width) | envelope amount | Dark and wide |
| 4 pluck | brightness | saw to square | filter snap | Rings out and fades over the decay time, with a sub an octave down. Ignores the short 303-style note length |
| 5 saw | tone (1 = fully raw) | second saw detune (0 = single saw) | sub saw an octave down | Hard and buzzy. Notes play at full level for the decay time, then stop |
| 6 house | tone | body (sub sine an octave down) | pluck (filter snap) | Deep house and garage: a clean square and a sub sine through a warm filter |

The drive comes after the engine, so it works on all of them. At 0 it's completely clean; it only colours the sound as you turn it up. The bass starts on acid.

## Lead engines

The lead has its own engines, made for melodies (it plays two octaves above the bass). Every lead engine glides on slide steps and adds a gentle vibrato that fades in on held notes, like easing in a mod wheel. k4 is decay, as on the bass. The screen shows them in the order mini, juno, dx, acid, sync.

| Engine | k1 | k2 | k3 | Character |
|---|---|---|---|---|
| 0 acid | cutoff | resonance | envelope amount | The 303, voiced to cut through: more resonance and a little grit |
| 1 juno | cutoff | pulse width movement | chorus: off, I, II | Saw, a slowly moving pulse and a sub through a soft filter, then the chorus. Dreamy |
| 2 dx | brightness | character: tine, reed, bell, glass | detune | Two-operator FM. Notes ring and fade like an electric piano; accents hit brighter |
| 3 sync | sync amount | tone | sweep | A hard-synced saw that sweeps with the envelope. Tech house and electro |
| 4 mini | cutoff | emphasis | contour | Three oscillators driven into a ladder filter. Big and warm. The default |

Five more are planned: whistle, supersaw, hoover, melodica and vox. Until then, a lead engine number past the last one plays mini.

## Chord synth

Plays up to four notes at once, worked out as it plays from the step's chord root, the shared key and scale, and the chord type. Change the key or the spice and the chords follow straight away.

**Spice** picks the chord type: 1 triad, 2 seventh, 3 ninth (root, third, seventh, ninth), 4 eleventh (root, seventh, ninth, eleventh). The old test panel also offers sus2, power, sus4 and sixth.

**Smooth** (on by default) folds every chord into the octave above the key's root, so each chord is played in the shape closest to the last. Off plays every chord from its root upwards.

| Engine | k1 | k2 | k3 | k4 | Character |
|---|---|---|---|---|---|
| 0 stab | brightness | detune | filter snap | length | Dub techno stabs. Great with the delay |
| 1 organ | upper drawbars | percussion click | sub drawbar | length | House organ |
| 2 pad | brightness | detune (width) | attack | length | Slow, wide chords |
| 3 piano | brightness | octave layer | snap (how fast the brightness falls) | length | M1-style house piano: a bright hit that mellows. 90s house and garage |
| 4 rhodes | tone | bark (brighter when hit hard) | tremolo | length | Warm electric piano. Deep house and trip hop |
| 5 strings | tone | ensemble depth | attack | release | String machine with an ensemble chorus. Dub techno and builds |

## Effects

Reverb and delay work like a mixing desk: each track has a **send** that sets how much of it goes to the effect, and the effect's **level** sets how loud the result comes back. Defaults: clap, snare, rimshot and tom get some reverb, the rim and rimshot get a little delay, the kick and bass stay dry. Both effect returns pass through the DJ filter, so a filter sweep takes the echoes and tails with it.

## MIDI clock

- **Leader** (sync 0, the default). OCKM_GENERATOR keeps time and sends MIDI clock, start and stop out of the MIDI port. Your other gear follows it. Clock is sent straight, without swing, so other gear applies its own groove.
- **Follower** (sync 1). OCKM_GENERATOR waits for MIDI start, then steps in time with incoming clock. The BPM box shows the measured tempo. Stop on the other gear stops it too.

Pick the MIDI port in plugdata's audio and MIDI settings. On the Pi, the iRig Pro Duo's MIDI ports should work for this.

## Transitions

The engine still has the transitions song mode used (fill, riser, riser + gap, dub out, impact on the 1). They're waiting for the new arrangements to drive them again.

**Pump** (on perform, by the filter: off, light, deep) is sidechain: every kick ducks the bass, lead and chords, and they swell back over an eighth note. It's saved with the loop.

Two settings it uses are useful by hand too: **part on/off** (on each synth tab: the part plays or doesn't) and **rise** (on perform, by the filter: the high-pass climbs across the loop and drops back as it starts again).

## Export

On the project screen, **export...** opens the export sheet.

- **What:** the loop, played once, 2, 4 or 8 times (exporting an arrangement comes with arrangements)
- **Files:** a stereo mix (24-bit WAV), stems (drums, bass, lead, chords and the effects returns, each its own WAV, before the master filter and drive), and a MIDI file (type 1: drums on channel 10 with General MIDI drum notes, bass on 1, lead on 2, chords on 3; velocity and micro timing included)
- **Save to:** the `exports` folder (on the Pi, that's on its SD card), or a USB stick when one is plugged in (into an `OCKM_EXPORTS` folder on it)

Audio is recorded as it plays, so you hear the export; the effects get 2.5 seconds to ring out at the end. A red **export / stop** button replaces save while it runs. **Record what I play** records the mix (and stems, if chosen) from now until you tap the red **rec / stop** button, tweaks and all.

`exports/` isn't saved to git.

## Generators

**Bass and lead** are built from a rhythm, a note pattern, and the shared key and scale. Then the rhythm lock (own, on the kick, fill gaps), density and mutate are applied, in that order. Change any one and the track rebuilds straight away, filling the whole pattern length. A rhythm is one bar or four bars long and repeats at its own length; the note pattern carries on across bars. Changing the key rebuilds both bass and lead. On the lead, a note that lands on a beat is always in the chord playing: if the pattern gives anything else, it moves to the nearest chord note.

**Chords** are built from a progression and a chord rhythm. Each progression has its own length (1, 2, 4 or 8 bars) and its own timing: some change chord every half bar, some hold a chord for two. If the pattern is shorter than the progression, picking it makes the pattern longer. It never makes a pattern shorter.

**Rhythms** (when it plays): 0 offbeat, 1 rolling, 2 gallop, 3 acid classic, 4 sparse dub, 5 tech bounce, 6 acid 16ths, 7 trip hop, 8 hook, 9 sparse melody. Four bars long: 10 phrase (says it, says it again, changes it, lands), 11 question answer (busy then sparse, twice), 12 pickup (notes that lead into the next bar), 13 arp gate (16ths with gaps, fuller in bar 3)

**Note patterns** (what it plays, used in turn on each note): 0 root, 1 octaves, 2 root and fifth, 3 acid riff, 4 walk up, 5 minor stab, 6 dub, 7 pedal, 8 arp up, 9 arp up-down, 10 call, 11 descend, 12 melody, 13 melody steps, 14 melody high. The melodies wander over the chord tones (root, 3rd, 5th, 7th of the chord playing), mostly in small steps, and come home to the root or fifth every 8 notes; "steps" adds passing notes. They run 64 notes before repeating, and mutate starts them somewhere else. Four-bar melodies that follow the bar, with a pitch for every step so the shape lines up with the phrase whatever the rhythm: 15 motif (a short idea in bar 1, again in bar 2, changed in bar 3, home to the root in bar 4: made for singing along), 16 motif call (bars 1 and 2 end up on the fifth, bars 3 and 4 answer on the root), 17 motif high (motif an octave up), 18 arp evolve (an arpeggio over the chord playing, the same shape twice, then lifted or changed). Each has 8 versions: mutate steps through them (the ninth comes back round to the original)

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
