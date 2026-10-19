# OCKM_GENERATOR

A drum machine and easy-to-program synths in one box. Built in Pure Data, designed to run on a Raspberry Pi with a touchscreen and a few knobs.

Current version: **v0.89**

## How to open it

Open `OCKM_GENERATOR.pd` in plugdata. Keep the folder together: the main patch finds everything else in the subfolders.

The window is the instrument: three touch screens, drawn in Lua (plugdata has Lua built in). Click with the mouse on the Mac, tap with a finger on the Pi. If clicks do nothing, the patch is in edit mode: press Cmd+E.

**How every screen is laid out**, top to bottom:
1. **Top bar:** play, tempo, then the screens as tabs in three groups: playing (**perform**, **mixer**), making (**builder, drums, bass, lead, chord**) and **arrange**. On the right, **save** (a disc, orange when there's something to save) and **☰**, the menu: project, export, settings, revert (and quit to desktop on the Pi). The version number sits next to the tempo
2. **Navigation strip:** on the left, right above the steps, the **steps** navigator: back and forward arrows either side of the steps you're looking at (for example "17-32"). The dots show every block of 16: white is the one on screen, orange is the one playing. You can also swipe the step row sideways. In the middle, how long the loop is and which part sets it, like "loop 4 bars (bass, lead, chords)". On the drums, bass, lead and chord tabs, the right of the strip has that part's **length** (1, 2, 4, 8 or 16 bars) and **double**. See "Part lengths" below
3. **What you're editing:** the steps (and, on the drums screen, which of the 8 drum slots)
4. **Sound shaping** at the bottom

Tap a track's name on the mixer, or in the drums tab's all drums view, to jump straight to it.

**Perform** (home: no steps, just mutes and effects, big enough for thumbs. Until v0.87 this was Perform B; Perform A's drum grid is now the drums tab's **all drums** view)
- **Play** and **tempo** top left. Drag the tempo number up or down. One loop per project: everything you play live works on it. **Save** (the disc) keeps the loop and the kit, and turns orange when there's something unsaved
- **A tile per track**, plus **all synths**. Tap anywhere on a tile to mute it or bring it back; **S** in its corner solos (several can be soloed at once). The light flashes as the track plays. Mutes and solos are for playing live, so they aren't saved. A part switched off on the builder shows "off in this pattern" and nothing here brings it back
- **Mutes land:** **now** (straight away, like an MPC's track mute), **next beat** or **next bar**. A change that's waiting gets an orange outline and says when it lands, so you can tap several and have them all switch together. Stopped, they land at once
- **Mute presets** along the bottom: drums only, no drums, kick + bass, all in. They clear any solos and go through the same timing
- **Master effects:** **rise** (a build to the next loop start at least 2 bars away, then the drop), **pump** (hold it: everything dips deep on each kick until you let go; how each part pumps the rest of the time is its own sidechain, on its tab), **drop** (hold it: nothing new plays, the effects ring on, and everything comes back on the next bar after you let go) and **throw** (hold it: the whole mix into its own echo line; let go and the echoes ring out). A big **filter** (drag left for low-pass, right for high-pass; let go and it snaps back, or tap **hold** to make it stay); drive and master volume; delay level, feedback and time; reverb level and size. Reverb tone is in settings
- **Macros:** three slots, A, B and C. Hold one to play it; let go and everything goes back (a macro with a move that stays lights up and waits: tap it again to let go). The small **v** on each picks which of your six macros is on that slot. Out of the box: build, wash and **breakdown**, a performance recipe: drums out, filter down, reverb and delay up. Tap it and it runs for 4 bars, then everything comes back together on the 1; hold it and it lasts until you let go, then drops on the next bar; tap it while it runs to drop early. Its mutes always land on the bar
- Mutate, original and density for the bass and lead are on their own tabs

**Drum lab** (its own patch: open `OCKM_DRUM_LAB.pd` in plugdata on the Mac). For designing a whole kit of your own, then rendering it as samples. Eight sounds, in two rows of four:
- **Clap:** how many bursts, the gap between them and how loose it is, burst length, two noise colours (body and air) with their focus and balance, a separate tail with its own tone, a small room, snap and drive
- **Snare:** two tuned tones with a pitch drop, a noise "wires" layer with its own tone, focus and decay, a click, the body-to-wires balance, and drive
- **Hats:** one metallic sound (six clashing square waves, the 808 recipe, mixed with noise) with metal pitch, noise to metal, tone and focus, low cut, drive, and two lengths: **closed** and **open**. Play either; the loop puts closed hats on the offbeats with an open one before the 1. **Render closed and open** saves a matching pair with the same name: the closed one in `samples/hat`, the open one in `samples/open-hat`
- **Kick, toms, congas, rim:** tuned drums built the same way: a sine diving in pitch (pitch, drop, drop time, decay), an overtone (amount and ratio) and a noise layer (the kick's click, the tom's skin, the conga's slap) with its own tone, focus and length. Toms play and render as a **low, mid and high** set; congas as **low and high**
- **Shaker:** band-passed noise with an attack (the swell) and a decay, low cut and grit
- **Two macro sliders per sound** (the peach ones), each moving several settings at once:
  - **Character:** a named slider with its own recipe (clap **room**, snare **crack**, hats **metal**, kick **punch**, toms **boom**, congas **slap**, rim **wood**, shaker **shake**). Centre is your sound; right is more, left is the opposite
  - **Morph:** at zero, your sound; push it up to travel a smooth path through nearby sounds (further along, further away). Pitch and tuning move a little, colour more, level never. **New path** picks a different route
  - **Keep** makes what you hear the new starting point and puts both sliders back to zero. Moving any other slider by hand does the same, so nothing jumps
- Where renders go: kick to `samples/kick`, toms to `samples/tom`, congas, rim and shaker to `samples/perc`. Sets share a name, ending in low, mid, high (or closed, open)
- The loop (at 120): kicks on the beat (your lab kick if its loop is on), clap or snare on 2 and 4, hats on the offbeats, shaker on every half beat, rim and congas off the beat, and a tom run at the end of the bar. Turn on as many loops as you like
- **play**, **loop with kick** (a kick on every beat, the clap or snare on 2 and 4), **randomise** small, medium or wild (around the sound you have), and **reset**
- **render** records one hit to `samples/clap` or `samples/snare` as a 24-bit mono WAV, named `lab-clap-` or `lab-snare-` plus the date and time. Pick it on the drums tab like any other sample (it's yours, so it can go on the SP-404 or into Ableton too)
- Nothing in the instrument depends on the lab: it only writes WAVs

**Drum** (one slot at a time, or **all drums**: tap the button right of the slots, or swipe left across them, for all eight lanes at once with M and S. Tap a step for a hit, again for an accent, again to clear; tap a name, swipe right across the names, or tap **one drum** to come back)
- The 8 slots along the top, named by the sound they play
- **Sound**: 8 pads, one per drum sound
- **Steps**: tap cycles empty, hit (white), accent (orange)
- Move between blocks of 16 with the **steps** arrows in the navigation strip, or swipe the step row sideways
- **Level, tune, decay, reverb, delay** for this slot. These belong to the kit, so they stay when you change pattern
- **Grooves** (right of the sliders): tap one to fill all 8 drums at once. Each slot gets the part for the sound it plays, so a groove's hats land on whichever slot is your hat. A groove is one bar, so it makes the drums 1 bar long (go longer and it repeats), and sets a swing to suit. In four banks (the chips above them): classics, house + garage, techno + breaks, and hard + fast. **Clear** empties the drums. A groove replaces your drum steps, so the message that pops up has an **undo** button
- **Fills** (under the grooves): the fill at the end of each **phrase**, whose length (4, 8 or 16 bars, counted from play) is set on the builder. **No fill** switches it off; picking a style switches it on. Styles: **snare roll** (builds through the second half of the bar), **tom run**, **cut out** (kick and claps out for the last half bar, hats out for the last beat, so the next downbeat lands harder), **snare build** (snare 16ths rising over the whole bar). Renamed in v0.84 from drop and build, which are the Perform pad and a macro, **breakbeat** (the whole bar becomes a breakbeat: broken kick and snare with ghost notes, straight hats, the rest quiet). A fill only replaces the drums it uses; everything else keeps playing your pattern, and your steps are never changed. Saved with each pattern, so a breakdown can have fills off

**Builder** (where compose used to be): what's in this pattern, and the harmony everything follows.
- **Styles** (two rows along the top, house through to techno): deep house, Chicago, classic house, Italo piano, nu disco, tech house, minimal, progressive, dub techno, Detroit, acid, peak time and hard techno. One tap sets the tempo, swing and groove, the key and scale (deep house in F dorian, peak time in F phrygian and so on), the kick and clap character, which parts are in, what each one plays and on which sound, the progression and chord colour, sends and sidechain. The lead is on in seven of them. **Shuffle** (right of the chips) re-rolls the lit style from its own choices: a different key, groove, progression, engines, rhythms, and a variation of the riffs, all still inside the style. Other styles leave a drum slot that plays one of your own samples or saved sounds alone, and take a slot that's on a kit back to the synth sound. The message that pops up has **undo**. The last style you picked stays lit; it's a starting point, so tweak away
- **Four tiles: drums, bass, chords, lead**, each with an **on/off** switch. Tap one to switch that part **off** in this pattern, tap again to switch it back **on**. Off is different from muted: an off part is silent, its tiles on Perform go dim and say "off in this pattern", and nothing on Perform (mutes, scenes, all in, macros) brings it back. Saved with each pattern, so an intro can leave the bass out. Each part's own tab has the same **on/off** switch, top right
- **The harmony:** the progression, the key and the scale. The bass, chords and lead all follow it, and it keeps steering even when the chords are out (so the bass still moves with it). The progression lives here now, not on the chord tab
- **Or fit the chords to my bass / my lead:** when you've written a line of your own, this picks the progression that fits it best (it scores every progression against your notes; tap again for the next best). Only lit when that part is yours
- **Phrase: off, 4, 8 or 16 bars,** counted from play, and what happens at the end of each one: **drum fill** (the style is picked on the drums tab) and **turnaround** (the harmony goes to the V chord, made major (E in A minor), which leads back round; the chords play it, a following bass moves with it, and the lead's notes bend to fit). One length for both, so the fill and the turnaround always land together. Saved with each pattern. (Until v0.85 the fill and the turnaround each had their own every-so-many-bars setting, on two tabs.)
- **The map, bar by bar:** the progression's chords, named in your key (Am, Dm, F, Em), with the bar that's playing lit

**Made for you, or yours.** There are no modes any more. Every bass, lead or chord part is either:
- **Made for you:** generated from its settings, and it follows the harmony: change the progression, key or scale and it rewrites itself to fit
- **Yours:** as soon as you edit a step it's yours, and nothing rewrites it. If the harmony then changes under it, its tab says how many notes no longer fit, with **refit my line** (each of those notes moves to the nearest chord note, keeping your rhythm, accents and slides) or **leave it**. **Make it for me** hands a part back to its generator

**Starting from empty.** A synth part with no notes says so: on the drums and synth tabs it reads "empty: tap to start", and its tab shows a **start** button. For the lead you can also just write a tune by hand on the lead tab.

**Bass, lead and chord** (a tab each)
- **Steps**: tap cycles off, on, accent. **Drag a step up or down** to change its note. Or tap a step, then pick its note from the row underneath (the dimmed one is the key's root). **Slide** applies to the selected step. Editing any step makes the part yours
- Chord steps show the chord on that step of the scale (i, ii, iii...)
- **On/off** (top right): the part in or out of this pattern, the same as its tile on the builder
- **Bass:** **riff** (which notes it plays inside each chord: root, octaves, root and fifth, acid riff and so on), **rhythm**, and **movement**: **pedal** (the riff stays on the key's home note while the chords move above it), **follows** (moves with each chord) or **walks** (follows, and the last notes of a bar step a semitone below the next chord's root, walking into the change)
- **Lead:** **tune** (the shape of the line: root, arps, motifs and so on), **rhythm**, and **inside to outside**, one slider for how far the tune strays from the chords. It builds up as you go right: **chord notes** (every note on the chord), **passing notes** (the notes on the beat stay on the chord, more and more of the ones between step to a neighbour), **colour** (some notes on the beat become the chord's 7th or 9th) and **outside** (octave leaps, and off-beat notes that slip a semitone outside the key). Mutate decides which notes get decorated, so each variation goes somewhere different but repeats steadily. The steps show what it plays. It works on one chord too. Moving it rewrites a lead that's made for you
- **Half-time** (top right, next to on/off): the part plays its own pattern at half speed, one of its steps every two, so a 16-step riff takes two loops (first half, then second half). Under drums at full speed it's the drum and bass feel, or a breakdown that suddenly opens out. Saved with each pattern
- **Sidechain shape** (bass, lead and chords): **duck** (a quick dip under the kick, back within a step: makes room, barely heard), **pump** (dips hard, holds a moment, swells back over the beat: the house breathing) or **gate** (cut for an eighth note, then straight back in). The little picture shows one beat at the amount you've set
- Bass, lead and chords each have a **sidechain** slider: how far that part dips each time the kick hits (it swells back over an eighth note). The **pump** on Perform does all three at once
- Bass and lead also have: **density** (left for fewer notes, right for more; the middle is the preset as written); **mutate** (a new variation of the same idea: the notes move, and since v0.86 a hit or two of the rhythm too, while accents and held notes stay), **back** (the variation before, as many times as you like), **original**, and **make it for me**
- **Chords:** **rhythm**, and the chords themselves: built **from the key** (triads, 7ths, 9ths or 11ths) or **one shape moved around** with the progression (m9, m11, dub m7, 4ths, maj9: the chord memory sound of deep house, Detroit and dub techno)
- **Sound** (bottom right): engine, its four knobs (named for the engine), drive, reverb and delay sends, level, and **chorus** (tap: off, I, II, I+II, like a Juno's buttons; off is exactly the dry sound. The juno lead engine also has its own chorus knob)
- **Movement** (under the sound): an LFO on one of the four knobs. Tap the boxes to step through the shape (sine, triangle, square, saw, random), which knob it moves, and how often (from a 16th to 8 bars, in time with the loop); drag depth to set how far it swings. At depth 0 the knob is exactly where you set it. It's saved with the loop
- **Chords only:** **voicing** (close; open, with the second note up an octave; or wide, with the lowest down and the second and fourth up), **smooth** (on by default: every chord kept at about the same height) and **strum** (each note of the chord a little later than the last, up to about 75 ms across the chord)

**Settings** (☰, or tap the tempo). Four sections:
- **This project** (saved with it): tempo with -5, -1, +1, +5 and a slider, swing, how strong accents are, reverb tone, and MIDI clock: lead (send clock out) or follow (play to incoming clock). Dragging the tempo up or down in the top bar still changes it directly
- **New projects:** how a new blank project starts: drums 1, 2 or 4 bars; synths 2, 4 or 8 bars; the lead on notes 1 and rhythm 1 (like everything else), or as motif, call and answer, or arp
- **This device:** theme (dark or light), how fast the filter lets go (snap, quick, slow), and where Perform's mutes start (now, next beat, next bar)
- **Macros:** your six macros. Each is up to four moves: what (filter, delay, feedback, reverb, size, drive, pump, volume, rise, throw or a set of mutes), how much, how it gets there (jump, or over a beat, a bar, 2 or 4 bars) and how it lets go (snap back, glide back over a bar, or stay). A macro can also have a **length** (1, 2, 4 or 8 bars): a tap plays it for that long and then it all comes back on the 1, a hold lasts while held and drops on the next bar, and its mutes wait for the bar. Tap a box to step through its choices. Pick which slot it's on (A, B or C) and hold **try it** to hear it. Names come from a list (there's no keyboard on the Pi)

New projects, this device and macros are yours, not a project's: they're kept in `my-settings.lua` beside the patch, so they're the same in every project.

**Mixer**
- One strip per track: reverb and delay sends at the top, a level fader, then **M** and **S**. Tap a strip's name to open that track
- New projects start dry: every reverb and delay send at 0. The reverb and delay themselves are set up, so turning a send up is all it takes
- **Master** on the right: the reverb and delay return levels, the master volume, and **clear** to undo every mute and solo
- **EQ** on every strip opens that track's EQ: low cut, a low shelf at 100 Hz, a mid bell you can move, and a high shelf at 8 kHz (each ±12 dB). A curve shows what you've set. While the song plays, bars behind the curve show where that track's sound sits, so you can see what to cut. The EQ button lights when it isn't flat. EQ belongs to the project
- **De-mud** on the master strip clears low-mid fog. Press it while playing and it listens to the mix for 4 seconds, then gives each track (except the kick and bass) a low cut just below where its own sound starts. If the mix piles up around 250 to 500 Hz, the chords, lead and snare get a small scoop there too. Stopped, it sets safe starting low cuts instead. **Undo** takes it back
- Drum levels belong to the kit (the project). Bass, lead and chord levels belong to each pattern, like the rest of their sound

Everything is on the screens now, so `pd test-panel` is only for testing.

**Arrange** (the last tab) is being rebuilt: your loop will become a track as a row of 16-bar units, with a transition at every joint. For now the tab says so. Song mode, the 8 pattern slots and the old Arrange were removed in v0.47.

**Under the screen:** `pd engine` is the sound and sequencer (open it only if you're curious). `pd test-panel` is the old v0.12 panel with every control on one sheet, kept for testing.

**Projects** (the **project** button, top right). A project is one loop plus the drum kit, tempo and effects. It opens on the one you used last.
- **Save** writes the loop and the project. **Back to last save** throws away everything since
- **Undo** (one step): arrange, a groove, clear and de-mud each put an **undo** button in the message that follows. It takes everything (the loop, kit, EQ, tempo) back to just before. Only the last one can be undone, and opening another project or going back to last save forgets it. The copy lives in `undo/` beside `projects/`
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
- **Start-up, straight into the app (no desktop):** the Pi logs in to its own session (`/usr/share/wayland-sessions/ockm.desktop`, set as `autologin-session=ockm` in `/etc/lightdm/lightdm.conf`). That's `tools/pi/ockm-session.sh`: Raspberry Pi OS's own labwc start-up without `-m`, so the system start-up (desktop, taskbar) doesn't run, only `~/.config/labwc/autostart` (a copy of `tools/pi/labwc-autostart`): screen rotation, then the app. Quit to desktop from the menu and the desktop and taskbar start then. To restart the app (say after copying a new version over), run `tools/pi/ockm-restart.sh` over SSH: it leaves a flag so the start-up runs the app again instead of bringing the desktop up. To go back to the normal desktop, set `autologin-session=rpd-labwc` again. The app itself starts with `tools/pi/ockm-start.sh`. That picks the DAC Pro for sound when it's fitted (otherwise it starts silent) and opens the patch full screen. It finds the DAC by name in Pd's own device list (`pd -alsa -listdev`): Pd lists each card twice (hardware and plug-in) and counts from 1 on the command line, so the card number from `aplay -l` points at the wrong device (that sent the sound to the second HDMI port)
- **`tools/pi/ockm-kiosk-plugin.tcl`** only acts when started by that script: full screen, no menu bar, no scrollbars, Pd's console hidden. It also makes touch work: a finger jumps from place to place without the pointer moving, so the plugin reports a move before each press and after each lift. Without that, single taps get lost
- **Drum steps, M and S act the moment a finger lands,** like pads on a drum machine. Everything else acts when the finger lifts. Swiping sideways after pressing a step puts the step back and turns the page
- **Screen rotation** is in `~/.config/kanshi/config` (`transform 270`: turned round from 90 in October 2026, to suit how the Pi sits). Touch follows it automatically
- **Remote access:** SSH (`ssh simon@ockm.local`) and Raspberry Pi Connect. Claude reaches it through your Mac with the key in `.pi/` (kept out of git)
- **Load:** Pd does the sound and draws the screen on one core. The sound engine is cheap (about 8% of a core with everything playing); drawing is the expensive part at double size, so redraws are capped at 25 a second. To check: `top -H -p $(pgrep -x pd)` over SSH while it plays
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
17. **iPad app, once the screens and sounds are right on the Mac and Pi.** The sound engine moves across on libpd; the screens get a native drawing layer fed by the same widget list; pdlua (GPL) is replaced for the App Store. Until then: keep screen logic apart from drawing, add no new Lua inside Pd unless it earns its place, keep file paths in one place, and keep Mac/Pi-only things (USB scan, kiosk) at the edges. Reese and acid filter with bob~, which may not be in the iPad's Pd: move them onto the analogue engine's state-variable filter (core Pd only)

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
| `voices/` | `ockm-drum` (a drum slot: the lab's voices or a sample) and `ockm-labdrum.pd_lua` (its brain: picks the sound, randomise, character, morph); the mono synth used for bass and lead (`ockm-mono`, one file per engine, shared `ockm-mono-core`); the chord synth (`ockm-chord`, one file per engine); the reverb (`ockm-verb`); and the master effects (`ockm-fx`) |
| `lab/` | The drum lab's voices (shared with the drum slots) and its brain. Built by `tools/build_lab.py` |
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
| `ockm-bass-rhythm`, `ockm-lead-rhythm` | Rhythm preset (bass 0 to 16, lead 0 to 13; each has its own list), and rebuild that track |
| `ockm-bass-notes`, `ockm-lead-notes` | Note pattern, 0 to 11, and rebuild that track |
| `ockm-bass-gen`, `ockm-lead-gen`, `ockm-chord-gen` | Rebuild that track with the current settings |
| `ockm-bass-lock`, `ockm-lead-lock` | Retired from the screen in v0.75 (0 own rhythm, 1 on the kick, 2 the gaps between kicks) |
| `ockm-<synth>-sidechain` | How far bass, lead or chord dips on each kick, 0 to 1 |
| `ockm-drum-punch` | The drum bus, 0 (off) to 1: parallel compression and saturation on all eight drums (project setting, default 0.5) |
| `ockm-<synth>-scshape` | Sidechain shape: 0 duck, 1 pump (default), 2 gate |
| `ockm-<synth>-half` | Half-time: 1 plays the part's pattern at half speed (one step every two, over two loops) |
| `ockm-bass-density`, `ockm-lead-density` | 0 to 2: fewer to more notes, 1 is the preset as written |
| `ockm-bass-seed`, `ockm-lead-seed` | Variation number: 0 is the original, anything else a mutation |
| `ockm-bass-mode`, `ockm-lead-mode`, `ockm-chord-mode` | 0 auto (generated), 1 manual (your notes) |
| `ockm-bass-sync`, `ockm-lead-sync` | 1 follow the chords, 0 follow the key only (the bass's pedal) |
| `ockm-bass-walk` | 1: the last notes of each bar walk into the next chord (a semitone below its root) |
| `ockm-lead-outside` | Inside to outside, 0 to 1 (default 0.35): below 0.25 chord notes only, then passing notes, colour (7ths, 9ths) from 0.5, leaps and chromatic notes from 0.75. Replaces ockm-lead-freedom |
| `ockm-drums-on`, `ockm-bass-on`, `ockm-lead-on`, `ockm-chord-on` | 1 in this pattern, 0 out (silent; Perform can't bring it back). Saved with each pattern |
| `ockm-turn-every` | Turnaround: 0 off, or 4, 8, 16: the last bar of every so many (counted from play) goes to V major |
| `ockm-sample-name` | From the sample library after each scan: folder (0-6), sample number, file name without the extension. One message per file |
| `ockm-style` | The last style picked on the builder (0-11), -1 for none. Only lights its chip: the screen sends the style's settings |
| `ockm-leader` | Retired in v0.74 (there are no modes). Older patterns saved with one open with the lead following the harmony |
| `ockm-pattern-copy <from> <to>` | Copy a pattern (0-7) to another slot |
| `ockm-pattern-clear <n>` | Empty a pattern |
| `ockm-bar` | Sent by the clock at the start of every bar |
| `ockm-fill-every` | 0 no fills, or 4, 8, 16: the last bar of every so many bars plays a drum fill |
| `ockm-fill-style` | 0 snare roll, 1 tom run, 2 drop, 3 build, 4 breakbeat |
| `ockm-drum-groove` | Fill every drum slot with a groove, 0 to 11, or 12 to clear. Sets the swing too |
| `ockm-chord-rhythm` | Chord rhythm preset, 0 to 7, and rebuild |
| `ockm-chord-prog` | Chord progression, 0 to 9, and rebuild |
| `ockm-chord-type` | From the key: 0 triad, 1 seventh, 2 sus2, 3 power, 4 sus4, 5 sixth, 6 ninth, 7 eleventh. Fixed shapes: 8 m9, 9 m11, 10 dub m7, 11 4ths, 12 maj9. Applies straight away |
| `ockm-edit` | Set one drum step: slot, step (0 to 127), value (0 off, 1 on, 2 accent, anything between 0 and 1 a velocity). For example `d1 4 2` |
| `ockm-nudge` | One drum step's timing: slot, step, -0.25 (a quarter step early) to 0.25 (late). Saved with the pattern |
| `ockm-drum-loop` | Older screens: the drums' length when shorter than the synths (0 = not shorter). Setting it sets the drum length |
| `ockm-bass-edit`, `ockm-lead-edit` | Set one bass or lead step: step (0 to 127), note (MIDI), on, accent, slide. For example `0 33 1 1 0` |
| `ockm-chord-edit` | Set one chord step: step, 0 off / 1 on / 2 accent, chord root as a scale step (0 is the key's root). For example `4 1 5` |
| `ockm-accent` | Accent amount, 0 to 1 |
| `ockm-<synth>-engine` | bass: 0 acid, 1 sub 808, 2 FM, 3 reese, 4 pluck, 5 analogue (default), 6 donk. chord: 0 stab, 1 organ, 2 pad |
| `ockm-<synth>-k1` to `-k4` | Synth knobs, 0 to 1. What they do depends on the engine (see below) |
| `ockm-bass-drive`, `ockm-lead-drive` | Distortion, 0 to 1 |
| `ockm-filter` | Master DJ filter, -1 to 1. Below 0 cuts the top, above 0 cuts the bottom, 0 is off. Smoothed, so moves don't click |
| `ockm-filter-glide <to> <ms>` | Glide the filter to a value, for example `0 50` to snap back to off |
| `ockm-<track>-mute-q` | Ask for a mute (0 or 1) that lands on the next beat or bar, by `ockm-mute-quant` (0 now, 1 beat, 2 bar) |
| `ockm-mute-bar` | 1: every mute asked for waits for the next bar, whatever `ockm-mute-quant` says (a recipe with a length sets it while it plays); 0: back to the setting |
| `ockm-beat` | Sent by the engine on every beat, before that step's hits (like `ockm-bar`) |
| `ockm-<synth>-lfo-shape`, `-lfo-rate`, `-lfo-depth`, `-lfo-target` | The synth's LFO: shape 0-4 (sine, triangle, square, saw, random), rate 0-7 (1/16 to 8 bars), depth 0-1, target 1-4 (which knob). Engines read `ockm-<synth>-k1-m` to `-k4-m`, the knobs after the LFO |
| `ockm-<synth>-chorus` | 0 off, 1 I, 2 II, 3 I+II |
| `ockm-chord-voicing`, `ockm-chord-strum` | Voicing 0 close, 1 open, 2 wide; strum 0-1 |
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
| `ockm-<slot>-synth` | Perc slots only, which synth sound: perc 1 0 rim, 1 conga, 2 shaker; perc 2 0 conga, 1 shaker, 2 rim |
| `ockm-<slot>-labchar`, `-labmorph` | The synth sound's character (-1 to 1, its lab recipe) and morph (0 to 1) |
| `ockm-<slot>-labrseed`, `-labramt`, `-labpseed` | Randomise: a seed (0 off) and how far (0.35 near, 1 anywhere); the morph path's seed. Saved, so a project gets the same sound back |
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

Eight drum slots, d1 to d8. Each slot can play any of 8 sounds: 0 kick, 1 snare, 2 clap, 3 perc 1, 4 closed hat, 5 open hat, 6 tom, 7 perc 2. The synth sounds are the drum lab's (see **Drum lab**); perc 1 and perc 2 choose between rim, conga and shaker. Only the chosen sound runs. The default line-up is kick, snare, clap, closed hat, open hat, perc 2, perc 1 and tom.

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

### Kits

A kit is one file in each sound folder named `kit-<name>`: `samples/kick/kit-909.wav`, `samples/snare/kit-909.wav` and so on. Names starting with a letter sort after numbered files, so adding a kit never renumbers your samples. A kit can leave sounds out: those slots stay on the synth. The drums tab shows "909 kit" instead of a number.

Since v0.89 every style loads one (where the files are there; without them it voices the synth kit instead), tuned the way the style tunes that drum:
- **909** (Analog Drums 909: the fast-attack kick, the bright long snare, clap, closed and open hats, rim, mid tom): Chicago, classic house, tech house, Detroit, acid, peak time, hard techno
- **909 long** (the long kick, the low snare, the low tom): deep house, progressive, dub techno
- **808** (Analog Drums 808: kick, snare, clap, hats, claves, mid tom): nu disco, minimal
- breaks, boom and dusty (from the CM Lofi packs) are still there for your own use

**Punch** (drums tab, beside no fill): the drum bus, on all eight drums together. A squashed copy of the drums (parallel compression: a 2 ms attack lets each hit's front edge through) is blended under them for body, then a soft saturator rounds only the very top, so the transients keep their edge. 0 leaves the drums alone; at 1 they're about 6 dB fuller with the peaks kept. Each style sets its own (0.4 deep house and dub techno, up to 1 for hard techno). Saved with the project. Samples also play about 5 dB louder than before (they're normalised to full scale but were being turned down), to sit with the synth drums

### Grooves


Since v0.86 the house and techno grooves have dynamics: hats with loud offbeats and ghosted 16ths, and the odd ghost before a backbeat. In a groove line `g` is a ghost note (about a third) and `o` a soft one (about two thirds), alongside `x` and `X`.
Four banks: classics, house + garage, techno + breaks (12 each), and hard + fast (hard house, drum and bass two-step, drum and bass rolling). Minimal and dub techno have a flat, even kick on every beat. A groove rewrites all 8 drums and sets the swing; **undo** takes it back.

Slot sounds, samples, tune, decay, level and sends are part of the drum kit, which is saved with the project and shared by every pattern.

### Samples

Each slot has its built-in synth sound (perc 1 and perc 2 have three: rim, conga and shaker), then the samples in its folder in `samples/` (perc 1 and perc 2 share `perc`). On the drums tab, the sound box picks it: the arrows step through **the synth → your samples**, each change plays the new sound, and tapping the box plays it again.

The synth sounds are the drum lab's voices, each slot running its own copy, so they start from the same sounds you hear in `OCKM_DRUM_LAB.pd`. The lab's small settings stay in the lab; on the drums tab each synth sound has:

- **Level, tune, decay, tone, drive.** Tune moves the sound's pitches; decay stretches its lengths
- **Character:** the lab's named recipe for that sound (punch, crack, room, metal, boom, wood, slap, shake), moving several settings at once, some up and some down
- **Morph:** walks a smooth path through nearby sounds. Random and wild pick a new path and put morph back to 0
- **Random** shifts the sound a little from where it starts; **wild** goes anywhere. **Reset** goes back to the starting sound
- These sit above the sliders and grey out while the slot plays a sample. While stopped, moving any slider plays the sound
- Under the sliders: this drum's **reverb** and **delay** sends (the same as on the mixer)
- **Save** (the disc next to the sound box) keeps the sound as one of yours, named like "kick 1", in `my-settings.lua`, so every project can use it. The arrows step through the synth, your saved sounds, then samples. On a saved sound the disc becomes a bin, to delete it. Perc slots share rim, conga and shaker sounds; closed and open hats share hat sounds

All of it is saved with the project as seeds and slider positions, so a project always gets the same sound back.

The sliders change with the source. **Synth:** as above. **Sample:** level, pitch, length, tone, start (skips up to 40% into the sample, to trim a slow attack). Reverb and delay sends are on the mixer.

- Samples are numbered in file-name order, so `01.wav` is sample 1. WAV and AIFF, mono or stereo (only the left channel plays), any sample rate
- Tune changes the playback speed, like an MPC: +12 is an octave up and twice as short. Decay below 100 fades the tail early; at 100 or more the whole sample plays
- Files added while it's running show up next time you open the drums tab
- `tools/pick_samples.py` fills the folders from a big sample library: 20 per sound, grouped by source, with `samples/sources.csv` (kept out of git) saying where each came from

## Bass engines

The bass has seven engines. Only the chosen engine runs, so the others cost no processing power. Every engine uses the same four knobs, 0 to 1. k4 is always decay.

The screen shows them by family: analogue first (the default), then sub 808, acid, reese, FM, pluck and donk.

| Engine | k1 | k2 | k3 | Character |
|---|---|---|---|---|
| 0 acid | cutoff | resonance | envelope amount | The 303 squelch |
| 1 sub 808 | tone | drive | pitch drop (quick, up to 30 semitones) | Deep and clean. Turn the decay up and it rings on past the step like an 808 boom |
| 2 FM | brightness | ratio | envelope on brightness | Punchy, metallic, plucky |
| 3 reese | cutoff | detune (width) | envelope amount | Dark and wide: three detuned saws beating over a steady sine sub. Keep the envelope low for drum and bass |
| 4 pluck | brightness | saw to square | filter snap | Rings out and fades over the decay time, with a sub an octave down. Ignores the short 303-style note length |
| 5 analogue | cutoff | saw to square | filter envelope | The workhorse house and techno bass (Minimoog, SH-101, Pro-One): saw to square with a square sub an octave down, through a resonant 24 dB low-pass. The default |
| 6 donk | brightness (organ harmonics) | bounce (pitch drop onto the note) | hollow (woodier) | Bassline house, garage and the M1 organ bass: a hollow tone that bounces onto each note and rings out |

The drive comes after the engine, so it works on all of them. At 0 it's completely clean; it only colours the sound as you turn it up. The bass starts on analogue.

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

Plays up to four notes at once, worked out as it plays from the step's chord root, the shared key and scale, and the chord type. Change the key or the type and the chords follow straight away. The notes come from one small piece of Lua (`seq/ockm-chordnotes.pd_lua`, written by the build), which the screen uses too, so chord names and MIDI export always match what plays.

**Chord types** come in two kinds:

- **From the key:** triad, 7th, 9th, 11th (plus sus2, power, sus4 and sixth by number). Each chord is stacked from the scale, so it changes quality as the progression moves (minor on i, major on VI). The 9th and 11th leave the root out (third, fifth, seventh, ninth; third, seventh, ninth, eleventh): the bass plays it, and the chord stays clear. A flat 9th (v in a minor key) becomes the root instead, so it doesn't grind
- **Fixed shapes:** m9 (b3 5 b7 9), m11 (b3 b7 9 11), dub m7 (root 5 b7 b3, spread), 4ths (stacked fourths) and maj9 (3 5 7 9). One shape moved as a block with the progression, whatever the key says, like a sampler with one chord on it or a synth's chord memory. That's the deep house, Detroit and dub techno sound. On the turnaround a minor shape turns major

**Smooth** (on by default) keeps every chord at about the same height (around D4, and never below D3, out of the bass's way): chords from the key pick the inversion that sits there, fixed shapes move by octaves. Off plays every chord from its root upwards, exactly parallel.

Every hit varies a little in strength, and accents hit harder. On the stab engine, how hard a hit is also opens the filter, so accents bite. Styles set the chord track's low cut (mixer EQ) to 150 Hz, leaving the low end to the kick and bass.

| Engine | k1 | k2 | k3 | k4 | Character |
|---|---|---|---|---|---|
| 0 stab | brightness | detune | filter snap | length | Dub techno stabs. Great with the delay |
| 1 organ | upper drawbars | percussion click | sub drawbar | length | House organ |
| 2 pad | brightness | detune (width) | attack | length | Slow, wide chords |
| 3 piano | brightness | octave (the even partials) | snap (how fast the first bright hit drops away) | length | House piano (v0.92): a struck string. Ten slightly stretched partials, the first four doubled by a second string that beats against them, the upper ones dying first, a hammer knock. Brighter the harder you hit. Classic house and Italo piano |
| 4 rhodes | tone (body and tine brightness) | bark (how much a hard hit drives it) | tremolo | length | Electric piano (v0.84): a warm body with the tine ringing on the attack (the 14:1 partial of the DX7 pianos), barks when hit hard. Deep house |
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

**Bass rhythms** (the bass has its own list, the classic dance bass rhythms first): 0 offbeat donk (on the "and" of every beat, between the kicks), 1 straight 8ths, 2 rolling 16ths (a continuous motor, accents on the offbeats), 3 dotted 8ths (a note every three 16ths, a forward bounce), 4 octave jump (8ths, root then octave: picking it brings the octaves notes with it), 5 sustained (one note held across the bar, sliding on, then a fresh note next bar), 6 quarters (on the four beats), 7 dembow (3-3-2, reggaeton and moombahton), 8 two step (asymmetric garage, four bars), 9 3-2-3 cluster (rolling groups of three, two and three 16ths). Then the older ones: 10 round the kick (16ths in the gaps around the kick), 11 gallop, 12 acid classic, 13 acid 16ths, 14 tech bounce, 15 sparse dub, 16 trip hop. Older projects keep the bass they had; picking a rhythm uses the new list

**Lead rhythms** (when it plays): 0 offbeat, 1 rolling, 8 hook, 9 sparse melody. Four bars long: 10 phrase (says it, says it again, changes it, lands), 11 question answer (busy then sparse, twice), 12 pickup (notes that lead into the next bar), 13 arp gate (16ths with gaps, fuller in bar 3). Numbers 2 to 7 (copies of bass rhythms) are hidden from the stepper since v0.84; a saved project that uses one still plays it

**Note patterns** (what it plays, used in turn on each note): 0 root, 1 octaves, 2 root and fifth, 3 acid riff, 4 walk up, 5 minor stab, 6 dub, 7 pedal, 8 arp up, 9 arp up-down, 10 call, 11 descend, 12 to 14 the older melodies (hidden from the stepper since v0.84: the motifs replaced them; saved projects still play them). The melodies wander over the chord tones (root, 3rd, 5th, 7th of the chord playing), mostly in small steps, and come home to the root or fifth every 8 notes; "steps" adds passing notes. They run 64 notes before repeating, and mutate starts them somewhere else. Four-bar melodies that follow the bar, with a pitch for every step so the shape lines up with the phrase whatever the rhythm: 15 motif (a short idea in bar 1, again in bar 2, changed in bar 3, home to the root in bar 4: made for singing along), 16 motif call (bars 1 and 2 end up on the fifth, bars 3 and 4 answer on the root), 17 motif high (motif an octave up), 18 arp evolve (an arpeggio over the chord playing, the same shape twice, then lifted or changed). Each has 8 versions: mutate steps through them (the ninth comes back round to the original)

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
| 11 | piano house | I V vi IV (written for a major key) | 4 |
| 12 | anthem | vi IV I V (written for a major key) | 4 |

The presets live in `tools/build.py` (`PRE` and `PROGS`). The build writes their names and shapes into the touchscreen too, so they always match.

**Suggest chords** (melody or bass leads) scores each progression against the leading part's notes: a note on the chord's root scores 3, another note of the chord 2, anything else -1. Notes on the beat and accented notes count for more. The best average wins.

**Chord types**: 0 triad, 1 seventh, 2 sus2, 3 power, 4 sus4, 5 sixth, 6 ninth, 7 eleventh, 8 m9, 9 m11, 10 dub m7, 11 4ths, 12 maj9

**Scales**: 0 minor, 1 major, 2 dorian, 3 phrygian, 4 mixolydian, 5 harmonic minor

The presets live in `tools/build.py` (in `PRE`), so they survive rebuilds. To add or change one, ask me, or edit the lists there and rebuild. Rhythm codes are 0 rest, 1 note, 2 accent, 3 note plus slide, 4 accent plus slide. Notes are scale steps: 0 root, 2 third, 4 fifth, 7 octave, minus numbers go below the root.
