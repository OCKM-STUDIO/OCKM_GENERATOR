# OCKM GENERATOR manual

A drum machine and easy-to-program synths in one box. Built in Pure Data, designed to run on a Raspberry Pi with a touchscreen and a few knobs.

The full manual: every screen, every engine, every hook. For what it is and how to get it running, start with the [README](../README.md). Version history is in the [changelog](../CHANGELOG.md).

## How to open it

Open `OCKM_GENERATOR.pd` in plugdata. Keep the folder together: the main patch finds everything else in the subfolders.

The window is the instrument: three touch screens, drawn in Lua (plugdata has Lua built in). Click with the mouse on the Mac, tap with a finger on the Pi. If clicks do nothing, the patch is in edit mode: press Cmd+E.

**How every screen is laid out**, top to bottom:
1. **Top bar:** play, tempo, then the screens as tabs in three blocks, each on its own faint plate (v1.49 order): making (**build, drums, bass, lead, chord, samples**), playing (**perform**, **fx**, **mixer**) and **arrange**. On the right, **save** (a disc, in your colour when there's something to save) and **☰**, the menu: project, export, settings, **show** (v1.49), revert (and quit to desktop on the Pi). The version number sits next to the tempo
2. **Navigation strip:** on the left, right above the steps, the **steps** navigator: back and forward arrows either side of the steps you're looking at (for example "17-32"). The dots show every block of 16: the strong grey is the one on screen, your colour is the one playing. You can also swipe the step row sideways. In the middle, how long the loop is and which part sets it, like "loop 4 bars (bass, lead, chords)". On the drums, bass, lead and chord tabs, the right of the strip has that part's **length** (1, 2, 4, 8 or 16 bars) and **double**. See "Part lengths" below
3. **What you're editing:** the steps (and, on the drums screen, which of the 8 drum slots)
4. **Sound shaping** at the bottom

Tap a track's name on the mixer, or in the drums tab's all drums view, to jump straight to it.

**Rewind and repeat** (v1.17, on Perform's top row in place of pump and throw; the macros still use those). **Rewind** (tap): the last moments of the mix spin backwards, up to 6 times speed within 100 ms, for half a second; then the loop restarts from the top and drops straight back in. **Repeat** (hold), on the drums only, the music carrying on under it: from the next step, the slice you're on loops in time, an eighth to start, halving every half bar you hold (a sixteenth, a 32nd). Let go and the drums carry on where they would have been. Hooks: `ockm-rewind`, `ockm-repeat 1/0`

**Arrange: versions** (v1.28). A version is a running order of the project's scenes with a transition on each join. On the arrange tab, **+ add** puts a scene on the end. Tap a section to set its length (whole loops of its scene, 4 to 64 bars), name it, move it, swap its scene (tap swap scene, then swap in on a scene) or remove it. Tap the round button on a join for its transition: cut, rise, echo out, filter swap or gap (over 1, 2, 4 or 8 bars), or any of your macro recipes that run for a length. Under them, **mutes** (v1.29): keep all, drums out, kick out, synths out or kick + bass, over the transition and back on the 1; a recipe's own mutes show there and can be changed. A transition runs over the end of the section, then the next scene drops in on the 1; a change of tempo glides over it. **Play from start** plays it through (what you had open comes back at the end); **export...** records it as it plays, the mix and optionally stems. Up to 6 versions a project, kept in versions/<project>.lua beside projects/. A save is a snapshot of everything in place but not movement: mutes, solos and latched bus effects are saved; a bus effect only held on the pad, the DJ filter, rise and pump are saved off.

**What's open** (v1.47): the project you're in and its scene show under the tempo on every screen (orange when there are unsaved changes, like the save button). **Open** on the project page switches to working on that project; if the one you're leaving has unsaved changes, they're saved as a new scene first. **▶** only listens.

**Saving** (v1.10; scenes since v1.27): every save is a new **scene**. Save keeps the scene you had and carries on in a new one (A, then B, C and so on, then AA, AB...), so nothing is ever overwritten. A project holds up to 64 scenes. The project page (v1.26; a table since v1.47) lists your projects with the date made, when last saved, how many scenes, tempo and key, and style. Newest first; tap a heading to sort by it, again to flip; drag to scroll. Beside it, the one you picked: its scenes in a grid of their own, newest first, kept ones outlined in your colour. **▶** on a project plays its latest scene, on a scene that one, without leaving the page: what you had open, unsaved changes and all, is set aside (in stash/, beside projects/) and comes back when you stop or leave the page. Stop your own music first. Pick a scene and **open**, **export...** (it exports that scene, then puts back what you had open), **keep** and **delete** act on it. **More...** has copy as a new project, **tidy up** (clears all but the kept ones, the newest five and the one you're in, to the trash folder) and delete the whole project. Hooks: `ockm-stash` and `ockm-unstash <name>`.

**Perform** (home: no steps, just mutes and effects, big enough for thumbs. Until v0.87 this was Perform B; Perform A's drum grid is now the drums tab's **all drums** view)
- **Play** and **tempo** top left. Drag the tempo number up or down. One loop per project: everything you play live works on it. **Save** (the disc) keeps the loop and the kit, and turns your colour when there's something unsaved
- **A tile per track.** The corner tile is **samples** (see below). Tap a tile to mute it or bring it back; **S** in its corner solos (several can be soloed at once). **Synths**, on the bottom row (v1.49; it was on the mutes row), mutes or brings back bass, lead and chord together, lit while they're out. The light flashes as the track plays. A part switched off on the builder shows "off in scene"
- **Samples** (v1.38, the tab after mixer; inside it's still called vox). One row of steps for vocals, one-shots and loops, with the length and bar pages along the top like the other parts (1, 2, 4, 8 or 16 bars, and double). Underneath, the brush: pick a sample on the left from **voice**, **loops** or **hits** (your files, in `samples/user/voice`, `loops` and `hits`) or **robot** (the computer voices: hooks, jack or techno, deep or flat) and an effect on the right (**off**, **stutter**, **delay**, **verb**). Then tap steps. The same sample and effect again clears a step; anything else replaces it. While stopped, picking a sample plays it; **hear it** plays it any time. **Clear all** asks first. **Pitch** changes the speed of every sample in the part
  - A sample plays whole: from its start to its end, until the next sample starts or you stop. No gate, and it's not the drum sampler
  - Stutter restarts the start of the file every 16th. Delay and verb are sends to the shared delay and reverb, for as long as that sample plays
  - The steps, effects and length are saved with the scene. An older scene has no steps, so it stays quiet. Styles leave it alone. It's on the music bus, with its own fader and EQ on the mixer
- **Mutes land:** **now** (straight away, like an MPC's track mute), **next beat** or **next bar**. A change that's waiting gets an outline in your colour and says when it lands, so you can tap several and have them all switch together. Stopped, they land at once
- **Mute presets** along the bottom: drums only, no drums, kick + bass, synths (v1.49: synths took all in's place; a lit preset tapped again puts back what was there, and bank B's last MIDI pad is still all in). They clear any solos and go through the same timing
- **Master effects:** **rise** (a build to the next loop start at least 2 bars away, then the drop), **pump** (hold it: everything dips deep on each kick until you let go; how each part pumps the rest of the time is its own sidechain, on its tab), **drop** (hold it: nothing new plays, the effects ring on, and everything comes back on the next bar after you let go) and **throw** (hold it: the whole mix into its own echo line; let go and the echoes ring out). A big **filter** (drag left for low-pass, right for high-pass; let go and it snaps back, or tap **hold** to make it stay); drive and master volume; delay level, feedback and time; reverb level and size. Reverb tone is in settings
- **On perform** (v1.24): the same pad sits beside the mutes, smaller, with the bus picked above it (drums, music, master), latch and set (the settings sheet, which picks the effect too). It replaced the DJ filter strip and the drive slider: the master DJ filter still runs underneath for the macros and MIDI, and the master drive is in the master bus's settings
- **MIDI learn** (v1.30, menu): tap a control on any screen, then move a knob or hit a pad; from then on it plays that control wherever you are. It follows the slot (a synth's knob 1, macro slot A, a track's mute), not what's in it. The fx pad learns two knobs (across, then up). Learned controls are outlined while learning; forget it clears the one picked; done finishes. Kept in my-settings.lua. Unlearned controls keep the built-in mapping. Knobs pick up (v1.31): they take over once they reach the control's setting. A key on a fader or slider plays it by how hard you hit it and puts it back when you let go; in settings, MIDI, a key can instead hold it to the amount it had when learned, or nudge it up or down 5% a press. Settings, MIDI lists everything learned, with forget and forget all
- **FX page** (v1.23, the fx tab next to perform): three buses, each with one effect slot: **drums** (all eight drum slots, after beat repeat, plus the bass when it's with the drums), **music** (lead and chords, plus the bass when it's with them, and the vox) and **master** (after the master effects and rewind). Each bus card picks its effect (filter, crush, drive, saturate or **gate**), **latch** and **settings**. The **gate** (v1.49, after PERF-1's) chops the bus in time: across the pad the rate (1/4, 1/8, 1/16, 1/32, one per quarter, and the pad says which), up the pad the depth (nothing at the bottom, silence between the chops at the top). Each chop is open for just over half its length, and it swings with the drums. Its settings pick the pattern: **straight**, **3-3-2**, **off-beats** or **dotted**. Put it on the music bus for the trance gate on the synths. In a macro, a gate move's amount is its depth, at 1/16. Tap the card's name to put it on the pad. On the **XY pad**, a finger down brings the effect in at that spot, moving plays it, lifting takes it out (latched, it stays in where you left it). One finger at a time: latch one bus, then play another. **Bass goes** with drums or with music, and the bass follows that choice (v1.33). Settings: mix, the effect's setting (crush tone, drive character, saturate bias) and glide. Reverb and delay are shared on the master, but each bus's sends go through its effect first (v1.30), so a bus filter takes the tails with it. Hooks: `ockm-bfx-<bus>-type` (0 filter, 1 crush, 2 drive, 3 saturate), `-on`, `-x`, `-y`, `-glide`, `-<effect>-mix`, `-<effect>-p`; `ockm-bass-bus` (1 drums, 0 music)
- **Macros:** six slots, A to F, in two rows of three (three before v1.49; the XY pad gave up a little height to make room). Hold one to play it; let go and everything goes back (a macro with a move that stays lights up and waits: tap it again to let go). The small **v** on each picks which of your six macros is on that slot. Out of the box (v1.49): **4 bar rewind**, **4 bar build** and **breakdown** on the top row, **8 bar lift**, **4 bar rush** and **dub out** on the bottom. Settings from before keep A, B and C, and D, E and F get the 8 bar lift, the rush and dub out (or, failing those, the first recipes not already on a slot), once. MIDI bank B still plays A, B and C. The **4 bar build** plays a build on the drums in place of your groove: the snare climbs from quarters (bar 1) to 8ths (bar 2) to 16ths (bar 3) to rolls (bar 4), the clap joins in bar 3, the hats go to 16ths, and the kick and everything else drop out for the last bar; the high-pass and reverb rise under it; the last beat is silent and the drop lands on the 1 with your own groove. Its drums come from the **snare build** move (hook `ockm-build 1`/`0`: it starts on the next bar line and lets go by itself after four bars), so any recipe can use it; the pattern is `BUILD` in tools/build.py. Your settings move over once: it joins your recipes and takes slot B if B still had the 4 bar lift. The **4 bar rush** is the other build (move **rush build**, `ockm-build 2`): the kick and the rest drop out while the snare climbs, then in the last bar the kick comes back four to the floor with the open hat on every 8th; two 16ths of silence, then the drop with a crash. It joins your recipes (not on a slot). Any recipe with a length can have a **crash** on its drop and a **key change** (up 2, 3, 5 or 7 semitones), both in the recipe editor next to its length; the key comes back down when a recipe with a length but no drop starts (a breakdown). Parts you've edited yourself don't follow a key change. The recipe list and the slot picker show up to nine recipes. The 4 bar rewind is the 4 bar lift, but on its last beat the whole mix spins back like a record dragged back, and stops right on the 1 as the drums come back in (in the macro editor, the gap button also offers **rewind: half a beat** and **rewind: a beat**). Your settings move over once: the 4 bar rewind joins your recipes and takes the 8 bar lift's slot (the 8 bar lift is still there to pick with the v). Before v1.49 the slots were **8 bar lift**, **4 bar lift** and **breakdown**. The lifts take the drums out while the high-pass climbs and a little reverb and delay come up, then everything slams back on the 1; the 8 bar lift's high-pass goes to 0.6: 60% of the way over the first four bars, all the way by the end of bar 7, then it holds for the last bar (a filter move marked late). The 4 bar lift's goes to 0.5. Both drop the whole mix out just before the 1 (a **gap**: a beat on the 8 bar lift, half a beat on the 4 bar lift; set it per recipe in the macro editor, next to its length). Recipes can now move over 8 bars. Breakdown: drums out, the low-pass closes in, reverb and delay up. Lift: drums out, the high-pass climbs, a gentle touch of reverb and delay. Tap it and it runs for 4 bars, then everything comes back together on the 1; hold it and it lasts until you let go, then drops on the next bar; tap it while it runs to drop early. Its mutes always land on the bar
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
- **Steps**: tap cycles empty, hit (the strong grey), accent (the same grey, with a bar in your colour)
- Move between blocks of 16 with the **steps** arrows in the navigation strip, or swipe the step row sideways
- **Level, tune, decay, reverb, delay** for this slot. These belong to the kit, so they stay when you change pattern
- **Grooves** (right of the sliders): tap one to fill all 8 drums at once. Each slot gets the part for the sound it plays, so a groove's hats land on whichever slot is your hat. A groove is one bar, so it makes the drums 1 bar long (go longer and it repeats), and sets a swing to suit. In two banks (the chips above them): house and techno, twelve each. **Clear** empties the drums. A groove replaces your drum steps, so the message that pops up has an **undo** button
- **Fills** (under the grooves): the fill at the end of each **phrase**, whose length (4, 8 or 16 bars, counted from play) is set on the builder. **No fill** switches it off; picking a style switches it on. Styles: **snare roll** (builds through the second half of the bar), **tom run**, **cut out** (kick and claps out for the last half bar, hats out for the last beat, so the next downbeat lands harder), **snare build** (snare 16ths rising over the whole bar). Renamed in v0.84 from drop and build, which are the Perform pad and a macro, **breakbeat** (the whole bar becomes a breakbeat: broken kick and snare with ghost notes, straight hats, the rest quiet). A fill only replaces the drums it uses; everything else keeps playing your pattern, and your steps are never changed. Saved with each pattern, so a breakdown can have fills off

**Builder** (where compose used to be): what's in this pattern, and the harmony everything follows.
- **Styles** (two rows along the top, house through to techno): deep house, Chicago, classic house, filter house, Italo piano, nu disco, tech house, minimal, progressive, trance, dub techno, Detroit, acid, peak time and hard techno. Each tap sets the tempo, swing and groove, the key and scale (deep house in F dorian, peak time in F phrygian and so on), the kick and clap character, which parts are in, what each one plays and on which sound, the progression and chord colour, sends and sidechain. The lead is on in nine of them; filter house has none. Every tap rolls a fresh take from the style's own lists (v0.97): a different key, groove, progression, engines, rhythms, and a variation of the riffs, all still inside the style. **Shuffle** (right of the chips) rolls the lit style again; **classic** (under it) plays the first of every list, the canonical version. Other styles leave a drum slot that plays one of your own samples or saved sounds alone, and take a slot that's on a kit back to the synth sound. The message that pops up has **undo**. The last style you picked stays lit; it's a starting point, so tweak away
- **Four tiles: drums, bass, chords, lead**, each with an **on/off** switch. Tap one to switch that part **off** in this pattern, tap again to switch it back **on**. Off is different from muted: an off part is silent, its tiles on Perform go dim and say "off in scene", and nothing on Perform (mutes, scenes, all in, macros) brings it back. Saved with each pattern, so an intro can leave the bass out. Each part's own tab has the same **on/off** switch, top right
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
- Bass and lead also have: **density** (left for fewer notes, right for more; the middle is the preset as written); **mutate** (a new variation of the same idea: the notes move, and since v0.86 a hit or two of the rhythm too, while accents and held notes stay), **back** (the variation before, as many times as you like), **original**, and **back to auto** (v1.49, was "make it for me": once you have edited the line yourself, hands it back to the box, which follows the key and chords again and writes a fresh line)
- **Chords:** **rhythm**, and the chords themselves: built **from the key** (triads, 7ths, 9ths or 11ths) or **one shape moved around** with the progression (m9, m11, dub m7, 4ths, maj9: the chord memory sound of deep house, Detroit and dub techno)
- **Sound** (bottom right): engine, its four knobs (named for the engine), drive, reverb and delay sends, level, and **chorus** (tap: off, I, II, I+II, like a Juno's buttons; off is exactly the dry sound. The juno lead engine also has its own chorus knob)
- **Movement** (under the sound): an LFO on one of the four knobs. Tap the boxes to step through the shape (sine, triangle, square, saw, random), which knob it moves, and how often (from a 16th to 8 bars, in time with the loop); drag depth to set how far it swings. At depth 0 the knob is exactly where you set it. It's saved with the loop
- **Chords only:** **voicing** (close; open, with the second note up an octave; or wide, with the lowest down and the second and fourth up), **smooth** (on by default: every chord kept at about the same height) and **strum** (each note of the chord a little later than the last, up to about 75 ms across the chord)
- **Two hands** (piano, organ and Rhodes, v1.20): a left hand plays the chord's root between G2 and F#3, an octave over the bass, and the right hand moves up out of its way (nothing below G3; four-note chords drop their root). The button next to it picks the left hand's pattern: **anchor** (root and octave when the chord changes, and on each bar), **pulse** (every beat), **synco** (1, the and of 2, 4), **broken** (root on the beats, fifth and octave on the ands) or **answer** (the beats the right hand leaves empty). The left hand follows edits to the chord pattern, push and the turnaround. Styles that use it set the chords' low cut to 90 Hz

**Settings** (☰, or tap the tempo).
- **MIDI controller** (v0.95): plug in an MPK mini, an MPC or most pad controllers; on the Pi it's connected as soon as it's plugged in. **Pads** read like the screen, top row first. Bank A: the top row mutes or brings back kick, snare, clap and hat, the bottom row the other four drums, landing like the Perform tiles. Bank B: the top row is macro slots A, B and C and rewind, the bottom row drop, repeat, rise and all in. Pads as notes (36 to 51, any channel) are held while the pad is held, so a tap runs breakdown or lift for 4 bars and a hold lasts; pads in program change mode (the MPK's PROG CHANGE, programs 0 to 15) have no let go, so a macro pad taps (build and wash stay on until the next tap) and drop and repeat toggle. **Knobs** (CC 70 to 77, or 1 to 8): filter (the middle is off), drive, delay, reverb, then k1 to k4 of the synth whose tab you last opened. Keys aren't used yet. Hooks: `ockm-midi-note <note> <velocity> <channel>`, `ockm-midi-cc <value> <cc> <channel>`, `ockm-midi-pgm <program> <channel>`
- **This project** (saved with it): tempo with -5, -1, +1, +5 and a slider, swing, how strong accents are, reverb tone, and MIDI clock: lead (send clock out) or follow (play to incoming clock). Dragging the tempo up or down in the top bar still changes it directly
- **New projects:** how a new blank project starts: drums 1, 2 or 4 bars; synths 2, 4 or 8 bars; the lead on notes 1 and rhythm 1 (like everything else), or as motif, call and answer, or arp
- **This device:** theme (dark or light), colour (red, or orange, blue, teal, wine, green, violet, or plain), how fast the filter lets go (snap, quick, slow), and where Perform's mutes start (now, next beat, next bar). The colour is only for what is happening: play, a part waiting to change, the playhead, an unsaved save. Anything you've chosen is the strong grey. Plain turns that colour off
- **Macros:** your six macros. Each is up to four moves: what (filter, delay, feedback, reverb, size, drive, pump, volume, rise, throw or a set of mutes), how much, how it gets there (jump, or over a beat, a bar, 2 or 4 bars) and how it lets go (snap back, glide back over a bar, or stay). A macro can also have a **length** (1, 2, 4 or 8 bars): a tap plays it for that long and then it all comes back on the 1, a hold lasts while held and drops on the next bar, and its mutes wait for the bar. Tap a box to step through its choices. Pick which slot it's on (A to F) and hold **try it** to hear it. Names come from a list (there's no keyboard on the Pi)

New projects, this device and macros are yours, not a project's: they're kept in `my-settings.lua` beside the patch, so they're the same in every project.

**Mixer**
- One strip per track: reverb and delay sends at the top, a level fader, then **M** and **S**. Tap a strip's name to open that track
- **Faders are in dB** (v1.08), like a desk: a track's 0 dB is three quarters up, with +10 dB above it, and the master's 0 dB is half way. New projects start with the kick at 0 dB and the rest set back from it, so every track has room to come up. The master's 0 dB is as loud as before; the mix runs 6 dB lower into the master effects, so a pushed track doesn't just hit the limiter
- New projects start dry: every reverb and delay send at 0. The reverb and delay themselves are set up, so turning a send up is all it takes
- **Master** on the right: the reverb and delay return levels, the master volume, and **clear** to undo every mute and solo
- **EQ** on every strip opens that track's EQ: low cut, a low shelf at 100 Hz, a mid bell you can move, and a high shelf at 8 kHz (each ±12 dB). A curve shows what you've set. While the song plays, bars behind the curve show where that track's sound sits, so you can see what to cut. The EQ button lights when it isn't flat. EQ belongs to the project
- **De-mud** on the master strip clears low-mid fog. Press it while playing and it listens to the mix for 4 seconds, then gives each track (except the kick and bass) a low cut just below where its own sound starts. If the mix piles up around 250 to 500 Hz, the chords, lead and snare get a small scoop there too. Stopped, it sets safe starting low cuts instead. **Undo** takes it back
- Drum levels belong to the kit (the project). Bass, lead and chord levels belong to each pattern, like the rest of their sound

Everything is on the screens now, so `pd test-panel` is only for testing.

**Arrange** (the last tab) lines this project's scenes up into a version, with a transition on each join. How that works is under "Arrange: versions" near the top. Song mode, the 8 pattern slots and the old Arrange were removed in v0.47.

**Under the screen:** `pd engine` is the sound and sequencer (open it only if you're curious). `pd test-panel` is the old v0.12 panel with every control on one sheet, kept for testing.

**Projects** (the **project** button, top right). A project is one loop plus the drum kit, tempo and effects. It opens on the one you used last.
- **Save** writes the loop and the project. **Back to last save** throws away everything since
- **Undo** (one step): arrange, a groove, clear and de-mud each put an **undo** button in the message that follows. It takes everything (the loop, kit, EQ, tempo) back to just before. Only the last one can be undone, and opening another project or going back to last save forgets it. The copy lives in `undo/` beside `projects/`
- **New blank project** starts from nothing: an empty loop, the default kit and sounds. It's named for you with two random words and the date, like "velvet heron · 14 Oct"
- **Save as a copy** keeps the project you were in as it was last saved, and carries on in a copy
- **Your projects**, newest first. Tap one, then **save mine, then open**, **open without saving**, or **delete** (tap twice). Deleting moves the files to a `trash` folder next to `projects/`, so nothing is lost by accident

Everything is remembered: drum kit, synth sounds, effects, tempo, swing, key and the steps.

**Light or dark, and the colour, are in settings** (this device). They're kept on this machine, not in the project. Dark and red are the defaults. `--ui-scale 2` sizes the screens for the 10" Pi display (1920 x 1200). The Mac size is 960 x 600.

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
| Screen power | From the GPIO header: the screen's two-wire lead plugs onto the top of the header, outer row (red 5V, black GND), through the DAC Pro's pass-through. A USB power adapter was bought but isn't used | In use |
| Controller | Endless knobs with light rings. Front runners: Novation Launch Control 3 (16 knobs, screen) or Behringer X-Touch Mini (8 knobs, 16 buttons). Maybe a Launchpad Mini later for a hands-on step grid | To choose |
| Storage | microSD card | Set up |
| MIDI | USB only for now: the controller plugs straight into the Pi. If syncing with gear that only has 5-pin MIDI sockets is ever needed, add a Roland UM-ONE mk2 (avoid cheap unbranded cables) | Decided |

## On the Pi

The Pi runs the same app as the Mac, drawn at double size (`--ui-scale 2`), so the 960 x 600 layout fills the 1920 x 1200 screen exactly. It starts by itself when the Pi powers on.

- **System:** Raspberry Pi OS (Debian 13, 64-bit) with the desktop. The scripts assume the hostname `ockm` and the app in `/home/simon/OCKM_GENERATOR`: change `simon` to your user in `tools/pi/ockm.desktop`, `tools/pi/ockm-session.desktop` and `tools/pi/labwc-autostart`. Pure Data 0.55 and pd-lua 0.12.23 from the Pi's own software catalogue (`sudo apt install puredata pd-lua lua5.4`)
- **The app** lives in `~/OCKM_GENERATOR`. After copying a new version over, rebuild it there with `python3 tools/build.py --ui-scale 2`. Don't copy `projects/` over the Pi's own projects
- **Switching off:** use **shut down** in the menu (v1.43), then unplug when the screen goes dark. Don't pull the power while it's running: on 29 October that left the Wi-Fi settings (`/etc/netplan/90-NM-*.yaml`) empty, and the Wi-Fi had to be set up again. The Wi-Fi is now a NetworkManager keyfile (`/etc/NetworkManager/system-connections/SKY4E97D.nmconnection`). The screen is turned 180 degrees by kanshi (`~/.config/kanshi/config`, `transform 90`); touch follows it (`mapToOutput` in `~/.config/labwc/rc.xml`)
- **Start-up, straight into the app (no desktop):** the Pi logs in to its own session (`/usr/share/wayland-sessions/ockm.desktop`, set as `autologin-session=ockm` in `/etc/lightdm/lightdm.conf`). That's `tools/pi/ockm-session.sh`: Raspberry Pi OS's own labwc start-up without `-m`, so the system start-up (desktop, taskbar) doesn't run, only `~/.config/labwc/autostart` (a copy of `tools/pi/labwc-autostart`): screen rotation, then the app. Quit to desktop from the menu and the desktop and taskbar start then. To restart the app (say after copying a new version over), run `tools/pi/ockm-restart.sh` over SSH: it leaves a flag so the start-up runs the app again instead of bringing the desktop up. It keeps unsaved work (v1.49): first it sends "keep;" to the app (UDP port 3091, with `pdsend`), and if there are unsaved changes they're stashed in `stash/` with a note (`stash/kept-on-restart.txt`); at the next start, when that project opens, they come back from the stash, still unsaved. To go back to the normal desktop, set `autologin-session=rpd-labwc` again. The app itself starts with `tools/pi/ockm-start.sh`. That picks the DAC Pro for sound when it's fitted (otherwise it starts silent) and opens the patch full screen. It finds the DAC by name in Pd's own device list (`pd -alsa -listdev`): Pd lists each card twice (hardware and plug-in) and counts from 1 on the command line, so the card number from `aplay -l` points at the wrong device (that sent the sound to the second HDMI port)
- **`tools/pi/ockm-kiosk-plugin.tcl`** only acts when started by that script: full screen, no menu bar, no scrollbars, Pd's console hidden. It also makes touch work: a finger jumps from place to place without the pointer moving, so the plugin reports a move before each press and after each lift. Without that, single taps get lost
- **Drum steps, M and S act the moment a finger lands,** like pads on a drum machine. Everything else acts when the finger lifts. Swiping sideways after pressing a step puts the step back and turns the page
- **Screen rotation** is in `~/.config/kanshi/config` (`transform 270`; 90 turns it the other way up. To flip it: edit the file, then `kanshictl reload`). Touch follows it automatically
- **Remote access:** SSH (`ssh <user>@ockm.local`) and Raspberry Pi Connect
- **Screen recording (v1.49):** `tools/pi/ockm-screenrec.sh start`, play, then `tools/pi/ockm-screenrec.sh stop`: a video of the screen with the box's sound, in `exports/screen-<date-time>.mp4` (1280 x 800, 25 frames a second). It reads the display directly with ffmpeg (needs sudo) at the lowest priority with the CPU held at full speed, about three quarters of a core: the first version used more and made the sound click
- **Load:** Pd does the sound and draws the screen on one core. The sound engine is cheap (about 8% of a core with everything playing); drawing is the expensive part at double size, so redraws are capped at 25 a second. To check: `top -H -p $(pgrep -x pd)` over SSH while it plays
- **Tests run on the Pi too:** `PDLUA=/usr/lib/pd/extra/pdlua python3 tests/run_tests.py`. They only ever use a clean copy of the blank project, never yours

## Roadmap

1. ~~Pattern saving and swing~~ (v0.1)
2. ~~Bass rhythm presets, note patterns, keys and scales~~ (v0.2). Still to do: editing single bass steps
3. ~~Drum accents per step, plus tune, decay and level per drum~~ (v0.3)
4. ~~More drum voices, up to 8: snare, rim, toms, percussion~~ (v0.3)
5. ~~Front panel for testing on the Mac~~ (v0.12). ~~Touchscreen interface in Lua: perform, drum and synth screens, swipe between blocks~~ (v0.13). Still to come: a settings strip for swing, accent, effects and MIDI
6. ~~Knobs for live control~~: MIDI learn (v1.30), with knob pick-up and key modes (v1.31)
7. ~~Bass engines (acid, sub, FM, Reese, pluck) and master effects (drive, delay, filter)~~ (v0.4)
8. ~~MIDI clock sync~~ (v0.5)
9. ~~Move to the Pi and start on boot~~
10. ~~6 flexible drum slots and patterns up to 128 steps~~ (v0.9)
11. ~~8 drum slots, chord and lead synth tracks~~ (v0.10)
12. ~~One central settings store: projects, patterns and the drum kit, saved and restored~~ (v0.11)
13. ~~Your drum samples, chosen per slot~~ (v0.36). Later: load sample folders from a USB stick or SD card on the Pi
14. ~~Song mode, MPC style~~ (v0.26). ~~Export: mix, stems, MIDI and live recording~~ (v0.41). ~~Scenes and versions: arrange a project's scenes into versions with transitions~~ (v1.27 to v1.29)
15. ~~A usability pass~~ (v0.26). Keep going after each round of playing
16. ~~A setup screen for tempo, swing, accents, volume and MIDI clock~~ (v0.26)
17. **iPad app, once the screens and sounds are right on the Mac and Pi.** The sound engine moves across on libpd; the screens get a native drawing layer fed by the same widget list; pdlua (GPL) is replaced for the App Store. Until then: keep screen logic apart from drawing, add no new Lua inside Pd unless it earns its place, keep file paths in one place, and keep Mac/Pi-only things (USB scan, kiosk) at the edges. Reese, acid, Bass, Analog, swarm and pulse filter with bob~ (v1.40, for the Pi's sake), which may not be in the iPad's Pd: check, or port bob~ (it's small) rather than going back to the state-variable filter, which is too heavy

18. **Next up** (October 2026): MIDI export of a version; names for scenes; learning the controls inside pop-up panels; stereo bus effects with flanger and phaser; MIDI map banks; playing drums and synths live from pads and keys

## Decisions made

- **Arrange is versions of scenes** (decided October 2026, v1.28). Every save is a scene (A, B, C..., up to 64 a project); a version is a running order of scenes with a transition on each join. Versions stay inside one project: a project can hold anything, so cross-project sets aren't needed.
- **A save is a snapshot of everything in place, but not movement** (v1.28): mutes, solos and latched bus effects are saved; the DJ filter, rise, pump and a bus effect only held on the pad are saved off.
- **Raspberry Pi, not Daisy or Arduino.** No hardware skills needed, and it runs full Pd, so nothing has to be rewritten.
- **11 step tracks: 8 drum slots plus 3 synths (bass, lead, chord).** Between a TR-6S and a TR-8. More step tracks would make the screen too busy without making the music better. **Samples** (v1.38, was vox) is a twelfth track: one row of steps that each start a whole sample. It takes the corner tile on perform.
- **One loop, a length per part** (decided October 2026). Drums, bass, lead and chords each 1 to 16 bars; the loop is the longest. Shown 16 steps at a time.
- **Drum slots are flexible.** Each of the 8 slots can play any of the 8 drum sounds, and later any of your samples.
- **One key for all synths.** Bass, lead and chord share the key and scale, so they always agree.
- **A self-contained box.** Pi, 10" screen and DAC Pro in one unit, a USB MIDI controller alongside, audio out on RCA to the mixer. No iRig, no MIDI interface for now.
- **Touchscreen plus a hardware controller.** The screen is for editing and overview. The knobs are for playing. The screen is the official 10" (decided October 2026): the 7" would make mute, solo and step buttons too small for a finger.
- **Minimal modern look.** Flat, two greys (light and dark), and one colour for what is happening. Red is the default; orange, blue, teal, wine, green, violet and plain are in settings. Chosen things are the strong grey, not the colour.
- **Build and test on the Mac first.** Everything runs in plugdata; the Pi only adds audio setup, screen rotation and start-up.
- **Lua for the screens.** Plain Pd controls can't tell a tap from a swipe, or show one screen at a time. The screens are one Lua object (`ui/ockm-ui.pd_lua`) that only sends and listens to the `ockm-*` hooks. The sound engine stays plain Pd.
- **Three screens, one level deep.** Perform is home. Drum and synth screens go deep on one part at a time. See `docs/architecture-and-ui-brief.md`.
- **Synthesised drums for now.** Samples can be swapped in later, one voice at a time.
- **Projects and patterns saved as readable text files** in `projects/`, so saving works on the Pi without a keyboard.
- **The drum kit belongs to the project; synth sounds belong to the loop.** See "How it's organised".
- **Touchscreen first, MIDI learn for playing** (October 2026). Everything is reachable on the screen, landscape only. A USB controller maps through MIDI learn (v1.30): a learned control stays with its slot (a synth's knob 1, macro slot A) whatever's in it. An iPad app is a likely phase two: same Pd engine (via libpd), screens rebuilt natively.
- **One loop per scene** (decided October 2026, replacing song mode and the 8 pattern slots). Each scene is one loop (each part 1 to 16 bars). Arrangement happens in versions, out of scenes (see above).

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

**Version history.** The folder is a git repository. Every version is saved, and you can go back to any of them. The public copy is on GitHub.

**Two kinds of change.**
- *Sound tweaks* (tune, levels, knobs, patterns): use the controls in the patch, as normal.
- *Structural changes* (new objects, new voices, rewiring): made in `tools/build.py`, then rebuilt with `python3 tools/build.py`. Don't rewire the generated `.pd` files by hand, because the next rebuild would overwrite it. The build only creates project files that are missing, so your saved work is never overwritten. `--reset-patterns` rewrites the starter project, which deletes your saved patterns.

**Tests.** `python3 tests/run_tests.py` runs 114 checks in about ten minutes (`python3 tests/run_tests.py <name>` runs the ones whose names contain it). It needs vanilla Pure Data's `pd` command, which comes with the Pi's `puredata` package. The touchscreen test also needs pdlua (set `PDLUA=/folder/with/pdlua`); without it, that test is skipped. It works on a temporary copy, so your patterns are safe.

**Internal names.** Every shared name starts with `ockm-` so nothing clashes with other patches. Pattern tables are `ockm-pat-<track>`, slot banks are `ockm-bank-<track>`, and the step squares are `ockm-sq-<track>-<square>`. Drum tracks are `d1` to `d8`, synth tracks are `bass`, `lead` and `chord`.

## How it's organised

The data model, smallest first:

1. **Step:** one slot in time on one track. Drums: off, on or accent. Bass and lead: note, on, accent and slide. Chord: on or accent plus a chord root.
2. **Track:** one lane. 8 drum slots, plus bass, lead and chord.
3. **Sound:** what a track plays. A drum slot: its sound, tune, decay, level and sends. A synth: engine, k1 to k4, drive (bass and lead), chord type (chord) and sends.
4. **Kit:** the 8 drum sounds together.
5. **Loop:** the steps for all 11 tracks, plus each part's length (1 to 16 bars), swing, key and scale, generator choices and **the three synth sounds**.
6. **Project:** a whole set. The loop, **the drum kit**, tempo, master effects, MIDI settings and accent amount.
7. **Scene** (v1.27): one save of a project. On disk each scene is its own folder in `projects/`: `2026-10-20-misty-otter` is scene A, `...-v2` scene B and so on, each holding `loop.txt`, `project.txt` and `variation.txt` (when it was saved, and keep).
8. **Version** (v1.28): a running order of a project's scenes with a transition on each join, kept in `versions/<project>.lua` beside `projects/`.

Beside `projects/` there are also `stash/` (what was open, set aside while a scene plays from the project page or arrange), `trash/` (deleted scenes), `undo/` (the one-step undo) and `my-settings.lua` (your macros, MIDI learn and device settings: yours, not any project's).

| Setting | Lives in |
|---|---|
| Drum kit (all 8 drum slots) | Project |
| Tempo, master effects, MIDI sync, accent | Project |
| Steps, length, swing, key and scale | Loop |
| Synth sounds (bass, lead, chord) | Loop |
| Generator choices | Loop |

**Rules**
- **Save** writes a new scene (v1.27): the scene you were in stays as it was. **Revert** reloads the scene from disk. Closing without saving loses unsaved changes.
- A save is a snapshot of everything in place, but not movement (v1.28): mutes, solos and latched bus effects are kept; the DJ filter, rise, pump and a bus effect only held on the pad are saved off.
- Files are plain text, one setting or one track per line, so they're easy to read, copy and back up.

## Named hooks

These let other things control the patch: tests now, and the touchscreen, knobs and MIDI later.

| Name | Does |
|---|---|
| `ockm-play` | 1 to start, 0 to stop |
| `ockm-gap-arm` | <steps>: silences the whole mix for the bar's last <steps> (the gap before a drop, v1.22); 0 lets go |
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
| `ockm-pat-vox-smp`, `ockm-pat-vox-fx` | The samples part's step tables (v1.38): which sample on each step (0 none, 1-96 the robot lines as set × 32 + voice × 16 + line, 1001 on voice, 2001 on loops, 3001 on hits: the nth file of that folder), and its effect (0 off, 1 stutter, 2 delay, 3 verb). Saved with the scene |
| `ockm-vox-len` | The samples part's length in steps, 16 to 256 (`ockm-vox-extend`, `ockm-vox-double` like the other parts) |
| `ockm-smp-play <sample> <effect>` | Play one now (the samples tab's audition) |
| `ockm-smp-user <folder> <n>` | The player: play the nth file in `samples/user/<folder>`. `ockm-vox-load <path>` plays a file under `samples/`, `ockm-smp-again` replays what's loaded |
| `ockm-smp-stut`, `ockm-smp-fx` | Sent with each hit: stutter on or off, and the effect (for the delay and verb sends) |
| `ockm-smp-count <g> <n>`, `ockm-smp-name <g> <n> <name>` | Sent by the sample library after a scan, for each folder (g 1 voice, 2 loops, 3 hits): how many files, and each one's name |
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
| `ockm-chord-hands` | 0 one hand; 1 anchor, 2 pulse, 3 syncopated, 4 broken, 5 answer (piano, organ and Rhodes only) |
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

## Knobs

Every synth knob is meant to make a clear difference from its first quarter turn, across its whole travel, without the loudness jumping (v1.14). `every_synth_knob_makes_a_difference` in the tests measures each one from 0 to 1 and fails the build if one stops counting.

## Drums

**Hat choke** (v1.09): a slot playing the closed hat cuts any slot playing the open hat in 8 ms, as on an 808 or 909.

Eight drum slots, d1 to d8. Each slot can play any of 8 sounds: 0 kick, 1 snare, 2 clap, 3 perc 1, 4 closed hat, 5 open hat, 6 tom, 7 perc 2. The synth sounds are the drum lab's (see **Drum lab**); perc 1 and perc 2 choose between rim, conga and shaker. Only the chosen sound runs. The default line-up is kick, snare, clap, closed hat, open hat, perc 2, perc 1 and tom.

Each slot's sound is fixed (slot 1 kick, 2 snare, 3 clap, 4 hat, 5 open hat, 6 perc 2, 7 perc 1, 8 tom); what changes is its sample. Tapping a step cycles off, on and accent. Accented steps play at full strength; normal steps play at full strength minus the accent amount.

### Velocity and timing

The lane under the steps has two modes. **Velocity**: drag a step's bar up or down, or swipe across to draw a shape; the top tenth snaps to accent. **Timing**: drag up to push a hit late, down to pull it early, up to a quarter of a step either way.

To make early hits possible, the whole engine plays a quarter of a step behind the clock (about 30 ms at 124 bpm). Everything moves together, so you won't hear it. Since v1.49 the MIDI clock goes out that much late too, so gear following it lands with the box.

### Part lengths

Every part has its own length: the drums (all 8 rows together), bass, lead, chords and samples, each 1, 2, 4, 8 or 16 bars. **The loop is as long as the longest part,** and shorter parts repeat inside it. So you can draw a 1-bar beat under a 4-bar bassline and hear it all.

- **Set a part's length** on its tab, on the right of the navigation strip. The steps and the playhead on that tab follow the part's own length; perform shows every lane repeating at its own length
- **Longer** repeats the part's own bars to fill the new ones. **Shorter** keeps the bars beyond (nothing is deleted, go longer again and they come back), and the message has an **undo** button
- **Double** copies the part's bars (steps, velocity and timing) after themselves: 1 bar becomes 2, up to 16
- **New projects** start with drums at 1 bar, the bass, lead and chords at 4 bars, and samples at 1 bar
- **Generators write their natural length:** a groove makes the drums 1 bar; a chord progression sets the chords to the progression's length. A bass or melody that follows the chords takes the chords' length too (v1.49: when the chords take their length from the progression, the lead keeps at least 4 bars, so a one-chord, one-bar progression doesn't leave it repeating every bar; the bass can loop the bar. A length you set yourself goes to the lead as it is)

### Kits

A kit is one file in each sound folder named `kit-<name>`: `samples/kick/kit-909.wav`, `samples/snare/kit-909.wav` and so on. Names starting with a letter sort after numbered files, so adding a kit never renumbers your samples. A kit can leave sounds out: those slots stay on the synth. The drums tab shows "909 kit" instead of a number.

Since v0.89 every style loads one, tuned the way the style tunes that drum. Without the files (as in a fresh download), it plays the synth kit of the same name instead (v1.49: 808, 909 or 909 long; before, the lab's own sounds):
- **909** (Analog Drums 909: the fast-attack kick, the bright long snare, clap, closed and open hats, rim, mid tom): Chicago, classic house, tech house, Detroit, acid, peak time, hard techno
- **909 long** (the long kick, the low snare, the low tom): deep house, progressive, dub techno
- **808** (Analog Drums 808: kick, snare, clap, hats, claves, mid tom): nu disco, minimal
- breaks, boom and dusty (from the CM Lofi packs) are still there for your own use

**Punch** (drums tab, beside no fill): the drum bus, on all eight drums together. A squashed copy of the drums (parallel compression: a 2 ms attack lets each hit's front edge through) is blended under them for body, then a soft saturator rounds only the very top, so the transients keep their edge. 0 leaves the drums alone; at 1 they're about 6 dB fuller with the peaks kept. Each style sets its own (0.4 deep house and dub techno, up to 1 for hard techno). Saved with the project. Samples also play about 5 dB louder than before (they're normalised to full scale but were being turned down), to sit with the synth drums

### Grooves


Since v0.86 the house and techno grooves have dynamics: hats with loud offbeats and ghosted 16ths, and the odd ghost before a backbeat. In a groove line `g` is a ghost note (about a third) and `o` a soft one (about two thirds), alongside `x` and `X`.
Two banks (v1.07): house and techno, 12 each. Loops saved on a groove that has left the banks still play. Minimal and dub techno have a flat, even kick on every beat. A groove rewrites all 8 drums and sets the swing; **undo** takes it back.

Slot sounds, samples, tune, decay, level and sends are part of the drum kit, which is saved with the project and shared by every pattern.

### Samples

Each slot has its built-in synth sound (perc 1 and perc 2 have three: rim, conga and shaker), then the samples in its folder in `samples/` (perc 1 and perc 2 share `perc`). On the drums tab, the sound box picks it: the arrows step through **the synth sounds → your saved sounds → your samples**, each change plays the new sound, and tapping the box plays it again.

**Synth kits (v1.49):** each synth sound also comes as **808**, **909** and **909 long** ("909 kick", "808 clap"): the lab's own voices set up like the classic machines, no samples involved (the idea is from the PERF-1 firmware, whose kits work the same way). The 808 kick is a near-pure, long, low boom with almost no click; the 909's drops fast with a hard click and a short body; 909 long rings on. The 808 snare is more tone than rattle, the 909's a dropping body with bright snap; 808 hats are strongly metallic, 909 hats brighter and noisier. Tune, decay, character, morph and new sound all work on top. They live in `tools/build_lab.py` (`SYNTH_KITS`), and a slot's kit is `ockm-<slot>-labkit` (0 the lab's own, 1 808, 2 909, 3 909 long), saved with the project and with your saved sounds. How to add your own samples: `samples/README.md`.

The synth sounds are the drum lab's voices, each slot running its own copy, so they start from the same sounds you hear in `OCKM_DRUM_LAB.pd`. The lab's small settings stay in the lab; on the drums tab each synth sound has:

- **Level, tune, decay, tone, drive.** Tune moves the sound's pitches; decay stretches its lengths
- **Character:** the lab's named recipe for that sound (punch, crack, room, metal, boom, wood, slap, shake), moving several settings at once, some up and some down
- **Morph:** walks a smooth path through nearby sounds. New sound picks a new path and puts morph back to 0
- **New sound** moves the sound a little from where it starts. **Reset** goes back to the starting sound
- These sit above the sliders and grey out while the slot plays a sample. While stopped, moving any slider plays the sound
- Under the sliders: this drum's **reverb** and **delay** sends (the same as on the mixer)
- **Save** (the disc next to the sound box) keeps the sound as one of yours, named like "kick 1", in `my-settings.lua`, so every project can use it. The arrows step through the synth, your saved sounds, then samples. On a saved sound the disc becomes a bin, to delete it. Perc slots share rim, conga and shaker sounds; closed and open hats share hat sounds

All of it is saved with the project as seeds and slider positions, so a project always gets the same sound back.

The sliders change with the source. **Synth:** as above. **Sample:** level, pitch, length, tone, start (skips up to 40% into the sample, to trim a slow attack). Reverb and delay sends are on the mixer.

- Samples are numbered in file-name order, so `01.wav` is sample 1. WAV and AIFF, mono or stereo (only the left channel plays), any sample rate
- Tune changes the playback speed, like an MPC: +12 is an octave up and twice as short. Decay below 100 fades the tail early; at 100 or more the whole sample plays
- Files added while it's running show up next time you open the drums tab
- **The samples part** has its own folders, `samples/user/voice`, `loops` and `hits`, each a list on the samples tab in file-name order. WAV, mono is best (only the left channel plays), any sample rate. Each plays whole, so trim loops to a bar or two at your tempo
- `tools/pick_samples.py` fills the folders from a big sample library: 20 per sound, grouped by source, with `samples/sources.csv` (kept out of git) saying where each came from

## Bass engines

The bass has six engines (v0.98). Only the chosen engine runs, so the others cost no processing power. Every engine uses four knobs, 0 to 1; k4 is always decay. Picking an engine loads its own sweet spot for the four knobs, so it sounds right straight away (a style that sets its own knobs uses those).

The screen shows them by family: analogue first (the default), then acid, sub 808, wide, FM and donk. Engine numbers stay as they were so saved projects load: pluck (4) is retired, and a project saved on it moves to analogue with a long decay.

| Engine | k1 | k2 | k3 | Character |
|---|---|---|---|---|
| 0 acid | cutoff | resonance | envelope amount | The 303 squelch |
| 1 sub 808 | tone (v1.14: how hard the sine is driven, clean to a growl, the filter opening with it) | weight (the second harmonic: body on small speakers) | pitch drop (up to 36 semitones) | Deep and clean. Turn the decay up and it rings on past the step like an 808 boom. Its k2 was a second drive, beside the drive slider |
| 2 FM | brightness | ratio | envelope on brightness | Punchy, metallic, plucky |
| 3 wide (was reese) | cutoff | detune (width) | envelope amount | The detuned-saw techno bass: three saws beating over a steady sine sub |
| 5 analogue | cutoff | saw to square | filter envelope | The workhorse house and techno bass (Minimoog, SH-101, Pro-One): saw to square with a square sub an octave down, through a resonant 24 dB low-pass. Past decay 0.6 a note rings on after its step and fades, so a long decay is a pluck. The default |
| 6 donk | brightness (organ harmonics) | bounce (pitch drop onto the note) | hollow (woodier) | Bassline house, garage and the M1 organ bass: a hollow tone that bounces onto each note and rings out |
| 7 raw | cutoff | resonance (screams past about 0.85) | wave (triangle to saw) | v1.08, MS-20 style: a triangle or saw into a resonant filter that self-oscillates at the top, driven hard after. Put the LFO on cutoff over 4 or 8 bars for the hypnotic sweep. Minimal uses it sometimes |
| 8 bass synth | cutoff | resonance | envelope | v1.45: the full Bass synth (it was swarm, a cut-down copy of it). Edit opens its page with every control |
| 9 pulse | cutoff | pulse width (square to thin) | PWM (a slow sweep of the width) | v1.39, from the Analog instrument: a pulse with a square sub, the classic 101 bass |

The drive comes after the engine, so it works on all of them. At 0 it's completely clean; it only colours the sound as you turn it up. The bass starts on analogue.

## Lead engines

The lead has its own engines, made for melodies (it plays two octaves above the bass). Every lead engine glides on slide steps and adds a gentle vibrato that fades in on held notes, like easing in a mod wheel. k4 is decay, as on the bass. Four engines (v0.98), shown as analogue, dx, sync, supersaw; picking one loads its sweet spot. Acid (0) and juno (1) are retired: a project saved on acid moves to analogue with the emphasis up, one on juno to analogue with the chorus on.

| Engine | k1 | k2 | k3 | Character |
|---|---|---|---|---|
| 2 dx | brightness | character: tine, reed, bell, glass | detune | Two-operator FM. Notes ring and fade like an electric piano; accents hit brighter |
| 3 sync | sync amount | tone | sweep | A hard-synced saw that sweeps with the envelope. Tech house and electro |
| 4 analogue (was mini) | cutoff | emphasis | contour | Three oscillators driven into a ladder filter. Big and warm. The default |
| 5 supersaw | spread (one saw to seven) | cutoff | drift (each saw wanders a little) | Seven detuned saws: the trance and peak-time stack, and a hoover with a long decay and the envelope sweeping the filter |
| 6 raw | cutoff | resonance (screams past about 0.85) | wave (triangle to saw) | v1.08, MS-20 style, as the bass engine but with the high-pass up: hypnotic techno sequences and big tech house riffs. Tech house, peak time and hard techno use it with a slow sweep on the cutoff |
| 7 analog | cutoff | resonance | envelope | v1.45: the full Analog synth (it was pulse, a cut-down copy). Edit opens its page: every control, the voices and the arpeggiator |

Five more are planned: whistle, supersaw, hoover, melodica and vox. Until then, a lead engine number past the last one plays mini.

## The synths: Bass and Analog (v1.39, in the groovebox since v1.45)

Two full synths, played by the groovebox's own parts: the **Bass synth** is the bass part's engine 8, the **Analog** the lead part's engine 7. Pick them on the part's tab like any engine. (v1.39 to v1.44 they were separate instruments with a start screen; v1.45 put them in the groovebox, so they play with everything else, from the same generator, scenes and arrange. The start screen is gone: the box opens on the groovebox.)

- **On the part's tab:** the four quick knobs are the synth's cutoff, resonance, envelope and decay. Picking the bass synth loads a starting point that sits with the other bass engines (v1.46: cutoff 0.3, resonance 0.35, envelope 0.35, decay 0.35; `ui.INSTK.pick_k`); its other settings stay as they are **Edit the bass synth** (or **edit the analog**) opens its page over the groovebox, which keeps playing. The arrow goes back
- **Its page, perform:** every control on one page, a few sounds to start from (the arrows), **random**, and your own sounds: the disc saves "bass 1", "analog 1" and so on (kept in the settings file, for every project); the bin deletes the one you're on. **Volume** is in the top bar (`<prefix>-level`)
- **Its page, keys:** two octaves on screen, octave arrows and **hold**. On the Analog, the voices (mono, unison, chord, poly) and the arpeggiator. The keys play over whatever the part is playing
- **MIDI channels:** a note coming in on the bass's channel plays the bass, on the lead's channel the lead (the same channels as MIDI out: bass 1, lead 2, set in settings, MIDI out). On a synth it goes through its keys (`<prefix>-play`, so the arpeggiator too); on another engine it plays the engine directly (`ockm-<part>-live`: `<note> <accent> 0 1` held, then `off`). So the MPC can play the box's bass, and a keyboard on channel 1 plays it live. Other channels are pads and learned controls, as before
- **How it's built:** `voices/ockm-mono-swarm.pd` (bass engine 8) and `voices/ockm-lead-pulse.pd` (lead engine 7) are `synth_engine` in build.py: the part's notes go through `seq/ockm-partvoice.pd_lua` (accent: velocity 120, otherwise 90; a glide slides; a held step holds; otherwise the note lets go after just over half a step) into `ockm-inst-bass ib` or `ockm-inst-analog ia`, switched off unless picked. Level-matched with the parts' other engines. The settings are `ib-<name>` and `ia-<name>`, saved with the scene. `seq/ockm-instseq.pd_lua` stays for the keys and the arpeggiator (its own steps don't play any more)
- **drmz** became the drums tab's **pads** view: a column per drum (pad, mute, level, pitch, length, drive or tone, new sound). Its own engine (`voices/ockm-drmz.pd`, `seq/ockm-drmzseq.pd_lua`) is still in the patch, switched off, so scenes that mention it load cleanly
- Still to move across: the instruments' **filter move per step** (the drawn sweep) to the bass and lead tabs

- **Bass** (after the Erica Synths Bassline, not a copy): saw, square or both, a swarm of detuned copies (wide), a sub and noise. An aggressive low-pass or band-pass filter. Three envelopes (amp, filter, pitch for zaps). An LFO to the filter, the oscillator (FM, fast) or pitch. Drive and glide. Velocity 100 and up is an accent: a snappier, brighter note
- **Analog** (after the SH-101 and S-1): pulse with PWM, saw, a sub (one or two octaves down, or a narrow pulse) and noise in a mixer. A smooth 24 dB low-pass. One ADSR, with gate mode. An LFO (triangle, square, random, noise) to pitch, pulse width and the filter. Glide. An **arpeggiator** (off, up, down, up and down, random; 1 to 3 octaves) on the perform screen: hold keys on a MIDI keyboard and they play one at a time, a 16th apart, in time with the transport when it's running. **Voices** (v1.40, `mode`): 0 mono, 1 unison (four voices on one note, spread by `uni`, up to a third of a semitone), 2 chord (each key plays itself plus `ch1`, `ch2`, `ch3` semitones above; 0 is unused), 3 poly (four notes, the oldest is taken when you play a fifth). Done by `seq/ockm-instpoly.pd_lua` in front of four copies of `voices/ockm-inst-analog-voice.pd`; mono runs one voice and switches the other three off, so it costs no more than before
- **drmz** (v1.40): eight voices (each starts on its own sound, v1.41) from the groovebox's drum lab (`ockm-drum z1` to `z8`, the same sound, start, tune, decay, tone and drive settings as the drum slots, as `ockm-z<n>-<name>`). Its steps are `ockm-pat-z1` to `z8` (0 off, 1 a hit, 2 an accent, between a ghost). `seq/ockm-drmzseq.pd_lua` (written by the build from `seq/ockm-drmzseq.lua.in`, with the 24 grooves put in) plays them and generates: `iz-gstyle` picks the groove, `iz-gbusy` adds ghosts, drops and pickups, `iz-gen` and `iz-mutate` write. `iz-tap <n>` plays a voice now, `ockm-z<n>-mute` mutes one. It sends `iz-hit <n> <strength>` to `voices/ockm-drmz.pd`
- **Filters** (v1.40): Bass and Analog use bob~ (a Moog-style ladder) for low-pass and vcf~ for the Bass band-pass, as do the groovebox's swarm and pulse engines. The state-variable filter they had cost too much on the Pi
- **Play them now** from a MIDI keyboard: open `INST_BASS.pd` or `INST_ANALOG.pd`. Settings arrive on `ib-<name>` and `ia-<name>` (0 to 1), and `ib-note` / `ia-note` take `note <n> <velocity> [slide]` or `off <n>`
- Settings, Bass: `wave` (0 saw, 1 both, 2 square), `swarm`, `sub`, `noise`, `tune` (0.5 is in tune, the ends are an octave), `cutoff`, `resonance`, `env`, `accent`, `key`, `filter` (0 low-pass, 1 band-pass), `attack`, `decay`, `fdecay`, `pitch-amt`, `pdecay`, `amode` (0 decay, 1 gate), `release`, `lfo-rate`, `lfo-amt`, `lfo-to` (0 filter, 1 FM, 2 pitch), `drive`, `glide`, `level`
- Settings, Analog: `pulse`, `saw`, `sub`, `sub-mode` (0 one octave down, 1 two, 2 a narrow pulse two down), `noise`, `width`, `pwm`, `tune`, `cutoff`, `resonance`, `env`, `key`, `lfo-filter`, `attack`, `decay`, `sustain`, `release`, `amode`, `lfo-rate`, `lfo-shape` (0 triangle, 1 square, 2 random, 3 noise), `lfo-pitch`, `glide`, `level`, `mode`, `uni`, `ch1`, `ch2`, `ch3`


**Sounds and random** (v1.49): picking a sound sets the whole synth (everything goes back to its starting point first, except the volume and mono, poly or chord), so nothing from random or earlier knob turns carries over. Random starts from the same point, in ranges that suit the synth.

## Chord synth

Plays up to four notes at once, worked out as it plays from the step's chord root, the shared key and scale, and the chord type. Change the key or the type and the chords follow straight away. The notes come from one small piece of Lua (`seq/ockm-chordnotes.pd_lua`, written by the build), which the screen uses too, so chord names and MIDI export always match what plays.

**Chord types** come in two kinds:

- **From the key:** triad, 7th, 9th, 11th (plus sus2, power, sus4 and sixth by number). Each chord is stacked from the scale, so it changes quality as the progression moves (minor on i, major on VI). The 9th and 11th leave the root out (third, fifth, seventh, ninth; third, seventh, ninth, eleventh): the bass plays it, and the chord stays clear. A flat 9th (v in a minor key) becomes the root instead, so it doesn't grind
- **Fixed shapes:** m9 (b3 5 b7 9), m11 (b3 b7 9 11), dub m7 (root 5 b7 b3, spread), 4ths (stacked fourths) and maj9 (3 5 7 9). One shape moved as a block with the progression, whatever the key says, like a sampler with one chord on it or a synth's chord memory. That's the deep house, Detroit and dub techno sound. On the turnaround a minor shape turns major

**Smooth** (on by default) keeps every chord at about the same height (around D4, and never below D3, out of the bass's way): chords from the key pick the inversion that sits there, fixed shapes move by octaves. Off plays every chord from its root upwards, exactly parallel.

Every hit varies a little in strength, and accents hit harder. On the poly engine, how hard a hit is also opens the filter, so accents bite. Styles set the chord track's low cut (mixer EQ) to 150 Hz, leaving the low end to the kick and bass.

| Engine | k1 | k2 | k3 | k4 | Character |
|---|---|---|---|---|---|
| 0 poly (was stab) | brightness | detune | attack (the bottom third is a stab; up from there a pad) | length (up to about 3 s) | Two detuned saws through a filter. The dub techno stab at attack 0, a pad further up, and a string machine with the chorus on. Replaces pad and strings (v0.98). Four saws since v1.09: detune spreads them round the note, gentle up to half way and wide at the top |
| 6 hard stab | cutoff | resonance | drive | length | v1.08: three wide saws and a square through a resonant filter that snaps shut, then driven. The bark for techno and tech house (tech house, peak time, hard techno) |
| 1 organ | upper drawbars | percussion click | sub drawbar | length | House organ |
| 3 piano | brightness | octave (the even partials) | snap (how fast the first bright hit drops away) | length | House piano (v0.92): a struck string. Ten slightly stretched partials, the first four doubled by a second string that beats against them, the upper ones dying first, a hammer knock. Brighter the harder you hit. Classic house and Italo piano |
| 4 rhodes | tone (body and tine brightness) | bark (how much a hard hit drives it) | tremolo | length | Electric piano (v0.84): a warm body with the tine ringing on the attack (the 14:1 partial of the DX7 pianos), barks when hit hard. Deep house |


Four engines (v0.98): poly, organ, piano, rhodes, each loading its own sweet spot when picked. Pad (2) and strings (5) are retired: a project saved on pad moves to poly with a slow attack, one on strings to poly with a slow attack and the chorus on I+II.

## Effects

Reverb and delay work like a mixing desk: each track has a **send** that sets how much of it goes to the effect, and the effect's **level** sets how loud the result comes back. Defaults: clap, snare, rimshot and tom get some reverb, the rim and rimshot get a little delay, the kick and bass stay dry. Both effect returns pass through the DJ filter, so a filter sweep takes the echoes and tails with it.

v1.49, ideas from the PERF-1 firmware:
- **The delay's repeats** get darker and thinner each time round (a high-pass at 180 Hz and a low-pass at 3.8 kHz inside the echo loop), and the feedback is capped at 0.85, so even all the way up it dies away instead of building forever
- **The reverb and delay returns duck** a little under each kick (the same quick dip as the duck sidechain), so tails don't cloud the kick. `ockm-fx-duck` sets how far: 0 off, 1 all the way, 0.3 out of the box
- **A light duck by default** on the synths: bass 0.15, lead 0.1, chords 0.2, in the quick "duck" shape. New projects start with it, and so does any style that doesn't set its own sidechain. Old scenes keep what they had
- **The master**, at the very end after the master fader: a gentle glue compressor (2:1 above about -10 dB, slow), then a look-ahead limiter (the sound waits 3 ms while the limiter turns it down ahead of each peak, so peaks are caught cleanly, ceiling about 0.79). The soft limiter after it is now just a last safety

## MIDI clock

- **Leader** (sync 0, the default). OCKM_GENERATOR keeps time and sends MIDI clock, start and stop out of the MIDI port. Your other gear follows it. Clock is sent straight, without swing, so other gear applies its own groove.
- **Follower** (sync 1). OCKM_GENERATOR waits for MIDI start, then steps in time with incoming clock. The BPM box shows the measured tempo. Stop on the other gear stops it too.

Pick the MIDI port in plugdata's audio and MIDI settings. On the Pi, the iRig Pro Duo's MIDI ports should work for this.

## MIDI out (v1.40)

Settings, **MIDI out**: for drums, bass, lead and chord, **this box** (the box plays it), **MIDI** (your synth or drum machine plays it and the box's sound goes quiet) or **both**, and the channel (drums 10, bass 1, lead 2, chord 3 to start). Hooks: `ockm-<part>-midi` (0, 1, 2) and `ockm-<part>-mch`.

**Sequencer mode** (v1.49): one tap sends every part out, so the box becomes the brain and your MPC, MC-101 or synths make the sound. **All on this box** puts them all back. You can still set each part by itself after, say the drums back on the box and the rest out. **Device** sets the channels and drum notes to suit: **general** (drums 10, bass 1, lead 2, chords 3, drums by sound), **MPC** (the same channels, drums on pads 36-43, so set the MPC drum program's notes to chromatic from C1), **MC-101** (drums 1, bass 2, lead 3, chords 4: its four tracks, plugged straight into the Pi's USB). **Drum notes**: by sound (kick 36, rim 37, snare 38, clap 39, closed hat 42, tom 45, open hat 46, cowbell 56, the General MIDI notes most drum machines use) or pads (slot 1 to 8 on notes 36 to 43). The bus effects, mixer and sidechain only work on what the box plays itself.

- Bass and lead go out as they play: accents at velocity 120, others 90; a slide starts the next note before the last one stops (legato, which is how a TD-3 and most monos glide); a held step doesn't let go
- Chords go out as four notes, as long as the chord's length setting
- A muted part, or one that isn't soloed while something else is, sends nothing and lets go of anything it holds. Stop lets go of everything
- `seq/ockm-midiout.pd_lua` does it, one per part, into Pd's MIDI out. On the Pi, `tools/pi/ockm-midi-connect.sh` connects Pd's MIDI out to every USB MIDI device, and keeps doing it, so a synth plugged in later gets it within a couple of seconds. The clock goes out the same way
- Drums (v1.49) go out a note per hit as they play: velocity from the hit's strength (an accent 127), rolls and flams as real repeated notes, a muted or un-soloed slot sends nothing. Each note lets go 40 ms later. On MIDI only, the box's own drums go quiet, but the kick and snare still drive the pump and the links
- The clock (v1.49) goes out a quarter step late, with the engine, so the gear following it lines up with the notes

## USB audio out (v1.48)

The Pi's USB-C port, through the 8086 USB-C/PWR splitter, makes the box a USB audio interface with 9 channels to a computer: **1-2** the mix, **3** the kick (drum slot 1), **4** the rest of the drums (the drums less slot 1, so the parts add up), **5** bass, **6** lead, **7** chords, **8** samples, **9** effects. The DAC still plays the mix.

- **Wiring:** the Pi's USB-C socket to the splitter's Pi side with a short 5A USB-C cable, the Pi's power supply into the splitter's power input, the splitter's data socket to the computer
- **On the Mac** it shows as "Capture Inactive (9 In, 0 Out)" (the name comes from the Pi's USB audio driver; a proper name is still to do). In Ableton: Preferences, Audio, Audio Input Device, then **Input Config** to switch on the inputs. Ableton takes input from one device at a time: for this plus your usual interface, make an aggregate device in Audio MIDI Setup
- **How it works:** `/boot/firmware/config.txt` has `dtoverlay=dwc2,dr_mode=peripheral` (the port as a USB device) and `usb_max_current_enable=1` (the splitter makes the Pi think it has a 3A supply; this gives the USB sockets full power anyway). The original is kept as `config.txt.before-usb-audio`. `tools/pi/ockm-usb-audio.sh`, run at start-up by `ockm-usb-audio.service` (in /etc/systemd/system), makes the USB audio device (`p_chmask 0x1ff`). When it's there, `ockm-start.sh` starts Pd through PipeWire (`pw-jack -p 256 pd -jack -outchannels 9`, from the pipewire-jack package) and `tools/pi/ockm-audio-links.sh` connects outputs 1-2 to the DAC and 1-9 to the USB device, every few seconds; PipeWire resamples the USB side so the two clocks don't drift. Without the USB device it starts on the DAC as before. The patch: `dac~ 3` to `dac~ 9` in `seq/ockm-recorder.pd`, from the stems (`ockm-usb-kick` is drum slot 1)
- **Power:** the splitter only advertises 3A (fixed resistors, no USB-PD), so the Pi's supply stays at 3A. With a lot plugged into the USB sockets, put the AudioBox and keyboards on a powered hub
- **Restarting:** after this change, asking the Pi to restart once switched it off instead; the power button brought it back

## The mood (v1.49)

One dial from **chill** to **peak**: on Perform under the fx pad, and on the builder in the style chips' spare place (they're the same dial). The middle is the loop exactly as you set it; either side moves several things at once, on top of your settings (never overwriting them):

| | towards chill | towards peak |
|---|---|---|
| Hats, percussion, toms | the off-beat 16ths drop out, then the 8ths | ghost notes on the empty 16ths |
| Kick, snare, clap | unchanged | unchanged |
| Bass and lead (made for you) | fewer notes; the lead rests more | more notes, more slides |
| Reverb and delay | up to a quarter more | up to a quarter less |
| Drive, pump | | a touch of drive; a little pump on the synths near the top |

Each style starts it somewhere: dub techno 0.3, deep house 0.35, minimal 0.4, most styles 0.5, tech house and filter house 0.55, acid 0.6, trance 0.65, peak time 0.7, hard techno 0.8. It's saved with each scene, so an arrangement can move through moods. A part you've edited yourself keeps its notes (the mood changes only what the box writes). Hook: `ockm-mood` (0 to 1). In the code: `lm.moodded` in seq/ockm-linemaker.pd_lua, the mood lines in `lane.decide` (seq/ockm-lane.pd_lua), `mood_on` in build.py's master effects, and `ockm_moodpump` in the synths' sidechain.

## The show page (v1.49)

For when the box is on display while you play: menu, **show**. A tap anywhere goes back (the play button still works).

- **The circle of fifths,** with C at the top as on any chart (sharps on the right, flats on the left) and the relative minors on the inside. The key's seven notes sit side by side on it, so the key lights up as one arc, and a change of key turns the arc round. The chord playing is a shape joining its notes, so you watch a progression step round the circle (a turnaround jumps out of the arc). The bass's note is ringed in red, the lead's in green
- **The middle:** the chord's name and its number in the key (i, IV and so on), four dots ticking the beat, and eight petals, one per drum, that flash as each drum hits and fade after
- **The outer ring** fills over the phrase
- **View** (top right): the circle of fifths, or **bloom**: an evolving fractal that plays along, like a screensaver. A branching tree mirrored round the centre into a kaleidoscope, five to seven levels deep (deeper with the mood), with a smaller one inside turning the other way. The chord shapes it without being named: six arms for a three-note chord, eight for four, and the angle the branches split at. The kick pushes it out, the hats light the outer twigs, the snare and clap light the inner bloom. It turns, curls and breathes slowly even while stopped. It's the heaviest thing on screen, so it redraws every other step
- **Colours** (top right): four schemes, dusk, neon, sunset and ink (all greys). Tap to step through them; your choice is kept in your settings
- **On the right:** where you are (bar 3 of 4; in a macro with a length, "drop in 2 bars"), each part lighting as it plays, and the mood

## Sound versions (v1.49)

Every engine on the bass, lead and chord tabs has versions: tap its button to pick it, tap again for version 2, again for 3, and round. The dots under the name show which version is playing and how many there are. A version sets the engine's four knobs (and, on bass and lead, the drive); the knobs are still yours to move after.

Every engine and every version is levelled, so changing sound doesn't jump the mix. Each engine has a measured gain (`ockm-<part>-egain`, set by the patch when the engine changes) and each version a trim on top (`ockm-<part>-trim`, saved with the scene; a new engine sets it back to 1). The versions live in tools/build.py (`SOUNDS`); after changing one, run `python3 tools/measure_sounds.py` (it needs Pd, as the tests do) and copy its trims in. Loudness is measured as the ear weighs it (K-weighted, the loudest 400 ms), averaged over a busy phrase and a long one.

## More from PERF-1 (v1.49)

- **Links** (`ockm-bass-link`, `ockm-chord-link`, 0-1): each kick pushes the bass's first knob (the filter on most engines) up, each snare or clap the chords', closing again over about a beat. On the bass and chord tabs as **kick link** and **snare link**, in the sidechain row
- **Drum drift** (`ockm-drum-drift-every` 0, 4, 8, 16 bars; `ockm-drum-drift-mode` 1 shift, 2 morph): your drums for that many bars, then a variation, then yours again, a new variation each time round. Shift moves the odd hit a step later; morph also adds the odd ghost note on an off-beat 16th and takes out the odd weak hit. The kick, the clap and a snare on a beat never move. On the drums tab: **drift**
- **Rolls**: `ockm-rat` 7 is a flam (a soft grace note, then the hit an eighth of a step later), 8 a swell (four hits across the step getting louder). On the drums tab, rolls: after x6 a tap gives flam, then swell, then one hit
- **Humanize** (`ockm-humanize` 0-1): each hit up to a fifth softer and up to an eighth of a step late, at random. On the drums tab
- **Slice** (`ockm-slice`): 0 off, 1 halves swapped, 2 stutter (the first beat of each half twice), 3 reverse, 4 mirror (the second half backwards), 5 double (the first half twice), 6 auto (one of them on the last bar of every four). On the drums tab: **slice**

None of these play in fills or builds. All are saved with the scene.

## Drum lanes and call and answer (v1.49)

On screen (v1.49), on the drums tab with one drum picked:

- **Rolls:** next to velocity and timing under the steps. Tap a hit for a roll of two, again for three, up to six, then back to one hit. Each roll shows its hits and x2 to x6
- **The lane:** the **lane** button at the end of the sound row swaps the sound controls for the drum's lane: **chance**, **thin** (what goes: the 16ths, the 8ths, 2 and 4, leaving the 1), **drift**, and **plays in** (every bar, bars 1 and 3, bars 2 and 4, the last or first of four, fills only, not in fills). **sound** swaps back

All of it is saved with the scene. Underneath, the hooks:

**Drum lanes**, per drum (d1 to d8):
- `ockm-d1-chance` 0 to 1: how likely each hit is to play (1, every time)
- `ockm-d1-thin` 0 to 1: drops the least important steps first. A quarter takes out the off-beat 16ths, a half leaves just the beats, three quarters the 1 and the 3, all the way just the 1
- `ockm-d1-when`: 0 every bar, 1 bars 1 and 3, 2 bars 2 and 4, 3 the last bar of four, 4 the first bar of four, 5 only in fills, 6 never in fills
- `ockm-d1-drift` 0 to 1: each bar a little different. Off-beat hits drop out now and then and ghost notes turn up on empty 16ths. The beats and accents stay put, and the same bar always drifts the same way
- `ockm-rat d1 <step> <hits>`: a roll of 2 to 6 hits on that step (1 for a single hit)

In a fill, the fill plays as written: only "only in fills" and "never in fills" apply.

**Call and answer**, on the bass and the lead: `ockm-bass-answer` and `ockm-lead-answer`, 0 off, or 2, 4 or 8 bars. The last bar of each group answers the bar before it: up an octave (or down, for a high lead), up a fifth, up a third, mirrored, backwards, a beat later, thinned, or just the accents. It's picked by the part's variation, so mutate gives a new answer. Answers stay in the key. On screen (v1.49): the **answer** button on the bass and lead tabs, next to half-time. Tap it to step through off, 2 bars, 4 bars and 8 bars. Like the other settings, it rebuilds a part made for you.

**Saving** writes to a new file and swaps it in when it's complete, so a power cut mid-save leaves the last good copy.

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

**The lead** (v1.06): rhythms phrase, question answer, pickup, arp gate, hook, sparse melody, offbeat, rolling, acid, long, stab; tunes one note, octaves, arp up, arp up-down, arp evolve, motif, question, answer the bass (tune 19: the bass's riff in the gaps of the bass). **Register** (`ockm-lead-octave` -1, 0, 1), **repeat** (`ockm-lead-repeat` 0 tight, 1 loose) and **rests** (`ockm-lead-rests` 0-1; v1.49: no longer on the lead tab, where **density** does the job, since it already thins differently in every bar. Styles and old scenes still set it). A four-bar tune over a longer lead plays A then A'.

**Rhythm siblings** (v1.05): one-bar bass rhythms and the one-bar lead rhythms are written as three bars: the rhythm and two siblings (other last bars). The original plays the first bar throughout; a variation (seed above 0) plays the last bar of the part as sibling A (odd seeds) or B (even). Bass rhythms on the stepper: offbeat, 8ths, 16ths, dotted, octave, held, on the beat, cluster, bounce, acid, house pickup.

**Synth tab controls** (v1.03): four knobs, drive (bass and lead), reverb and delay sends, chorus on/off, movement (a sine on the first knob, every bar, 2 or 4 bars, with depth), sidechain and half-time. Level is on the mixer only. Half-time for all three synths is also on the builder's phrase row.

**Bass riffs, slide and octave** (v1.02): the bass has its own eight riffs (root, octaves, fifth, seventh below, dub, walk up, acid, arp: scale steps from the chord root, `ockm-bass-riff` 0-7; -1 keeps an older loop's notes setting). **Slide** (`ockm-bass-slideamt` 0-1) makes more notes glide into the next; **low/high** (`ockm-bass-octave` 0/1) moves the riff an octave up.

**Chord vary, sustained and drift** (v1.01): on the chord tab, **vary** is still, breathe (the loop's last bar changes: a push before the 1 on stab rhythms, a rest on the last beat for pads) or move (bars alternate A B A B', one hit fewer, then one more). **Sustained** is a chord rhythm that hits only where the chord changes. **Drift** (voicing row) lifts chords built from the key one inversion every second time round. Hooks: `ockm-chord-vary` (0 still, 1 breathe, 2 move), `ockm-chord-drift` (0/1); chord rhythm 11 is sustained (6 and 7 are retired).

**Evolve** (v1.00, on the builder under the phrase row): off, gentle or lively, plus a tick per part. At the start of each phrase one ticked part moves to a variation, in turn (bass, lead, chords, drums), and comes home: gentle plays A B A C A B A D, lively A B C D. The bass and lead step their mutate seed; the chords and drums step through the lit style's chord rhythms and grooves. Parts that are yours, engines, knobs and the progression are never touched. **keep** on Perform makes what's playing the new original; each part's tab shows its variation and when it's due home. Hooks: `ockm-evolve-every` (bars, 0 off), `ockm-evolve-mode` (1 gentle, 2 lively), `ockm-evolve-parts` (1 drums + 2 bass + 4 lead + 8 chords).

**Rate and push** (v0.99, on the builder beside the progression): **rate** sets how long each chord lasts, half a bar, a bar (the table below) or two bars, so every progression comes at three speeds. **Push** lands every chord change an eighth early; a chord hit that fell on the change moves to just before the 1 and holds over it, and the bass follows. Both are saved with the loop (`ockm-chord-rate` 0, 1, 2; `ockm-chord-push` 0, 1) and set by styles.

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
| 13 | seven | i VII | 2 |
| 14 | six | i VI | 2 |
| 15 | five | i v | 2 |
| 16 | two five | ii v | 2 |
| 17 | lift | i VII VI VII | 4 |
| 18 | seven four | i VII iv (iv held two bars) | 4 |
| 19 | gospel | I vi ii V (written for a major key) | 4 |

The stepper shows them by chord count (one, two, four, then soul); garage (5) and trip hop (9) are off it since v1.04 but still play in loops saved on them. **Second half** (`ockm-turn-to`): the turnaround bar goes to V (4) or climbs to VII (6), every `ockm-turn-every` bars.

The presets live in `tools/build.py` (`PRE` and `PROGS`). The build writes their names and shapes into the touchscreen too, so they always match.

**Suggest chords** (melody or bass leads) scores each progression against the leading part's notes: a note on the chord's root scores 3, another note of the chord 2, anything else -1. Notes on the beat and accented notes count for more. The best average wins.

**Chord types**: 0 triad, 1 seventh, 2 sus2, 3 power, 4 sus4, 5 sixth, 6 ninth, 7 eleventh, 8 m9, 9 m11, 10 dub m7, 11 4ths, 12 maj9

**Scales**: 0 minor, 1 major, 2 dorian, 3 phrygian, 4 mixolydian, 5 harmonic minor

The presets live in `tools/build.py` (in `PRE`), so they survive rebuilds. To add or change one, ask me, or edit the lists there and rebuild. Rhythm codes are 0 rest, 1 note, 2 accent, 3 note plus slide, 4 accent plus slide. Notes are scale steps: 0 root, 2 third, 4 fifth, 7 octave, minus numbers go below the root.
