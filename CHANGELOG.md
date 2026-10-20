# Changelog

## v1.25 (20 October 2026)

- **The pad springs back:** not latched, lifting your finger sends the effect back to the centre of the pad as it goes out (a filter sweeps back open, like the old DJ filter strip), and the crosshair returns to the middle. Latched, it stays where you left it

## v1.24 (20 October 2026)

- **The bus effects are on the perform page too,** beside the mutes: pick drums, music or master above the pad, latch, and **set** (its settings sheet, which now also picks the effect). The pad takes the place of the DJ filter strip and the drive: the master bus's filter, unlatched, plays and springs back the same way. The fx tab keeps the big pad and the bass switch
- The master's delay and reverb stay on perform, with the volume beside them. The master drive moved into the master bus's settings
- The three macros are shorter (100 px, still an easy hold)
- The master DJ filter is still there underneath: the lifts, breakdown and your MIDI knob drive it as before

## v1.23 (20 October 2026)

- **FX page** (next to perform): three buses, each with one effect: **drums**, **music** (lead and chords) and **master**. Pick a bus and its effect (**filter**, **crush**, **drive** or **saturate**), then play it on the **XY pad**: put a finger down and it comes in, move to play it, lift and it goes
- **Latch** keeps a bus's effect in after you lift. The screen takes one finger at a time, so latch one bus and play another
- **Settings** per bus and effect: mix (dry to wet), the effect's own setting (crush tone, drive character, saturate bias) and glide (how slowly it follows your finger)
- **The bass** goes with the drums (the default: it carries the floor while you filter the music) or with the music
- The pad: filter is low-pass to the left, open in the middle, high-pass to the right, resonance up; crush is sample rate across, bits up; drive is drive across, tone up; saturate is amount across, warmth up. Each is level-matched so it doesn't jump
- **Macros can play bus effects:** new moves drums fx, music fx and master fx, each with its effect and an amount, over a time and back like any other move. Recipes can now have six moves
- Reverb and delay stay shared on the master, so a filter on the music bus doesn't filter its reverb tail
- Mono for now: stereo, flanger and phaser come later
- The perform tab is narrower to make room for fx; everything else stays where it was

## v1.22 (20 October 2026)

- **A gap before the drop:** the lifts now take the whole mix out, reverb and delay tails included, just before everything slams back on the 1. A beat on the 8 bar lift, half a beat on the 4 bar lift. Each recipe with a length has a gap button in the macro editor (no gap, half a beat, a beat). Hold a lift and let go late in the bar and the gap is skipped rather than cut short
- **The lifts' filters:** the 8 bar lift's high-pass stops at 0.6, the 4 bar lift's goes to 0.5 (was 0.3). Saved lifts on the old amounts move over; ones you've changed keep yours

## v1.21 (20 October 2026)

- **The 8 bar lift's filter goes further and gets there sooner:** the high-pass climbs to 0.65 (was 0.45), 60% of the way over the first four bars and all the way by the end of bar 7, then holds for the last bar. A saved 8 bar lift still on the old setting moves over

## v1.20 (20 October 2026)

- **Two-handed chords** on the piano, organ and Rhodes: the left hand plays the chord's root between G2 and F#3 (an octave over the bass), in one of five patterns: **anchor** (root and octave when the chord changes, and each bar), **pulse** (every beat), **synco** (1, the and of 2, 4), **broken** (root on the beats, fifth and octave on the ands) and **answer** (the beats the right hand leaves empty)
- With the left hand playing, the right hand moves up out of its way: nothing below G3, and four-note chords drop their root
- On the chord tab: **two hands** and the left hand's pattern, next to strum. Voicing is now one button (close, open, wide)
- Deep house (Rhodes), classic house, filter house and Italo piano play with two hands, their chords' low cut at 90 Hz instead of 150 so the left hand comes through
- MIDI export writes the left hand on the chords track
- The left hand is a second, two-voice copy of the engine (voices/ockm-chord-<engine>-lh.pd), switched off unless two hands is on

## v1.19 (20 October 2026)

- **8 bar lift** (macro slot A, in build's place): the 4 bar lift over twice as long, its high-pass going further (0.45), most of it in the last two bars: half way over the first six, the rest as it lands
- **Lift is now called 4 bar lift.** Saved settings move over: build (as it came, with pump) becomes the 8 bar lift; a build you've changed stays
- Macro moves can run over 8 bars, and a filter move can be **late** (half way over three quarters of the time, the rest in the last quarter)

## v1.18 (20 October 2026)

- **Rewind is twice as fast:** up to 6 times speed backwards within 100 ms, half a second in all, then the loop drops back in from the top
- **Repeat is on the drums only,** with the bass, chords and lead carrying on under it (much clearer than repeating the whole loop, which already repeats). It starts on an eighth and halves every half bar you hold it (a sixteenth, then a 32nd)

## v1.17 (20 October 2026)

- **Rewind** (Perform, in place of pump): tap and the last few seconds of the mix spin backwards, speeding up like a hand dragging the record, then the loop restarts from the top and drops straight back in
- **Repeat** (Perform, in place of throw): hold and the slice you're on loops in time from the next step, a quarter to start, halving every bar you hold (an eighth, a sixteenth, a 32nd). Let go and the mix carries on as if it never stopped
- **Rise is subtler:** its noise riser is 7 dB quieter, sweeps to 6 kHz (not 9) and is narrower: a lift, not a whoosh. The filter build and the drop are as before
- Both act on the whole mix, after the effects (seq/ockm-stutter.pd: a 20-second recording of the mix, read back at a moving delay). Pump and throw stay for the macros (dub out, build). On the MIDI pads, bank B: rewind where pump was, repeat where throw was

## v1.16 (20 October 2026)

- **Perform's scenes are switches:** drums only, no drums and kick + bass light up when on; tap again and exactly what was muted and soloed before comes back. Change a mute by hand while one is on and it lets go. All in stays a one-shot (everything in, solos cleared)
- **M and S on every instrument page,** beside the on/off switch: bass, lead and chords each have their own; on the drums tab they mute or solo all eight drums together (lit when every drum is)

## v1.15 (20 October 2026)

First ear test of the knobs, sound by sound.

- **Analogue lead:** cutoff opens right out (the top 15% of the knob fades in the unfiltered sound; the filter itself stops at 9 kHz, where it behaves), emphasis reaches the edge of self-oscillation, contour is a much bigger, snappier opening on each note (up to 16 times the cutoff, on a cubed curve, so it falls away and leaves the cutoff in charge)
- **Drive (bass and lead):** a real overdrive: up to 60 times the gain into tanh plus its square (even harmonics), the level kept where it was. It was heard as a little compression
- **DX detune is a stack:** at 0 one clean voice; turning up fades in two more, sharp and flat, spreading to 60 cents apart
- **Fix: solo with more than one track.** Soloing two tracks and then unsoloing one brought everything back: the count of soloed tracks only remembered the last one pressed. A new test checks it

## v1.14 (20 October 2026)

Every synth knob now makes a clear difference, from the first quarter turn, without the loudness jumping. Each one was measured (rendered at 0, a quarter, half and full, and the change in tone, length, movement and level compared), fixed where it was weak, and measured again. A new test fails the build if a knob stops making a difference.

- **Lead decay rings:** notes sound for the decay time (60 ms to 2 s) instead of stopping about 95 ms after every step whatever the knob said
- **Cutoff that counts:** on the analogue and raw leads (and raw bass) the envelope opens the filter by a multiple of the cutoff, so the knob works across its whole travel (the envelope used to add a fixed amount that swamped it)
- **Supersaw:** spread and drift went from almost nothing to a real detuned stack (outer saws up to 85 cents); the cutoff no longer goes silent at the top (a ladder filter replaces vcf~, which broke down)
- **Sync** sweeps up to 9 times the note (it was 4), with a steeper tone filter that never hides it; **DX detune** up to 35 cents (it was 10), and the DX lead loses a hidden DC offset
- **Emphasis and resonance** (analogue lead, acid, raw, hard stab) keep their level instead of dropping up to 12 dB, and bite from early on
- **Sub 808:** tone now drives the sine from clean to a growl (it only filtered a sine); weight and the pitch drop go much further
- **Donk:** bounce up to two octaves; brightness from the first touch. **Wide:** detune up to 80 cents. **Acid:** decay 25 ms to 2 s
- **Bass decay** starts at 60 ms, so a quarter turn already counts
- **Poly:** attack works from the first touch (the bottom third used to be all stab); detune keeps its level
- **Hard stab:** a resonant ladder filter (resonance doubled), drive up to 30 that's heard as grit, not volume
- **Organ:** drawbars and click twice as far. **Piano:** snap from soft (600 ms) to hard (20 ms), brightness and octave much further, length from 150 ms. **Rhodes:** tremolo up to 75% deep (it was 35%), tone further, length from 150 ms
- **Drum drive:** up to 15, a touch asymmetric, and no longer a volume knob (it added 10 to 14 dB)

Saved projects sound different where they lean on these knobs: leads ring longer, the sub is grittier at its default, and stabs saved with an old snap setting get a slower attack.

## v1.13 (20 October 2026)

- **The bass and lead generator is Lua** (`seq/ockm-linemaker.pd_lua`, replacing `seq/ockm-monogen.pd`): rhythms and siblings, riffs and tunes, answer the bass, lock to the kick, density, mutate, rests, slides, octave, repeat, and the lead's inside-to-outside decorations, in one readable file. The random choices still work in 32-bit floats as Pd's did. Checked against the old one on 664 mixes of every setting, bass and lead: 654 note for note the same; the other 10 each differ by one coin flip at one step, where the old version's 32-bit sine landed exactly on a threshold (Pd's sine also differs slightly between the Mac and the Pi, so the Lua version is the steadier of the two). Saved loops keep their notes, so nothing saved changes
- More plain-Lua tests (`tests/lua/test_linemaker.lua`)

## v1.12 (20 October 2026)

Under the hood: the musical logic moves out of Pd and into Lua, one generator at a time. Pd keeps making the sound.

- **The chord generator is Lua** (`seq/ockm-chordmaker.pd_lua`, replacing `seq/ockm-chordgen.pd`): rhythm, progression, rate, push and sustained, in about a hundred readable lines. Checked against the old one on every rhythm, progression, rate and push, at the progression's own length and after a length change: all 2,736 patterns identical. Nothing sounds different
- **Plain-Lua tests:** `tests/lua/` runs the generators' logic without Pd (a small stand-in for pdlua, `pd_stub.lua`). The main test run includes them

## v1.11 (20 October 2026)

- **Variation browser:** on the project screen, pick a project and tap **browse all** to see every variation, newest first, each with its style, tempo, key, progression, which parts are in, and when it was saved. Each one can be opened, **kept**, exported (it opens, then the export sheet comes up) or deleted (tap twice). The one you're in can't be deleted
- **Tidy up** (in the browser): clears everything except the kept ones, the newest three and the one you're in, to the trash folder. Tap twice
- Each save now writes `variation.txt` in its folder: when it was saved, and whether it's kept

## v1.10 (20 October 2026)

- **Every save is a variation:** save keeps the version you had exactly as it was and carries on in a new one (velvet heron, then velvet heron v2, v3...). Nothing is ever overwritten. A brand-new project's first save just saves it, and save with nothing changed makes nothing
- **The project list shows each project once,** with its latest variation number. Pick one and its variations appear in a row underneath (the last 12): tap any to open it or delete it

## v1.09 (20 October 2026)

- **Hard stab, more punch:** each hit starts with a spike that drops to the body in 35 ms, the pitch knocks down onto the note from 3 semitones up over the first 15 ms, and the saws spread wider
- **Poly detune you can hear:** four saws spread round the note (it was two), up to about three quarters of a semitone at the top. Width, not a slow wobble
- **Hat choke:** a closed hat cuts the open hat in 8 ms, as on an 808 or 909. It goes by the sound a slot plays (closed hat, open hat), samples included. Both on the same step still opens
- **Less fizz on the analogue and raw basses:** the drive's top harmonics are rolled off after it, and the raw's saw is band-limited (the plain one aliased). The raw lead keeps more top, so it can still scream
- **Fix:** v1.08 started the master 6 dB too quiet (the start-up level skipped the make-up gain)

## v1.08 (20 October 2026)

First listen on the Pi: harder sounds for techno, trance, and a mixer with room to push.

- **Hard stab** (chord engine): three wide saws and a square through a resonant filter that snaps shut, then driven. Cutoff, resonance, drive, length. Tech house rolls it first (tresillo, skank or call answer); peak time and hard techno use it sparsely, one call a bar or tresillo, pumping under the kick. Hard techno has chords again
- **Raw** (bass and lead engine, MS-20 style): a triangle or saw into a resonant filter that screams at the top of its resonance, driven hard after. Cutoff, resonance, wave, decay. Tech house now has a raw riff on top; peak time and hard techno roll it first for the lead; minimal sometimes uses it for the bass
- **Styles can set the LFO:** a slow sweep on the cutoff over 4 or 8 bars, the hypnotic move. Styles that don't set it switch it off
- **Trance** (new style, after progressive): 138, the rolling offbeat bass, minor-key progressions two bars a chord, gated 8ths chords on the poly with the string chorus pumping under the kick, a supersaw arp on top
- **Poly detune** goes much further: gentle up to half way (as before), up to about a semitone at the top
- **Mixer faders are in dB:** a track's 0 dB is three quarters up with +10 dB above, the master's 0 dB half way up. Each fader shows its dB. Saved mixes keep their levels. The mix runs 6 dB lower into the master effects and the master makes it back, so pushing a track is heard instead of squashed; a last soft limiter keeps a pushed master clean

## v1.07 (19 October 2026)

Step 11 of the harmony and generator proposal: the grooves cut to house and techno, and a new style.

- **Groove banks, two:** house (four floor, house, deep house, Chicago, jackin, disco, soulful, afro house, funky house, ghetto house, nu disco, rolling) and techno (tech house, minimal, techno, dub techno, Detroit, Berlin, industrial, hypnotic, acid techno, electro and two harder ones), twelve each, with clear. Garage, breaks, trip hop, drum and bass and the rest are off the screen; loops saved on them still play
- **Filter house** (new style, between classic house and Italo piano): the house groove at 124, two chords changing every half bar (seven or vamp), 8ths chords on piano or organ pumping hard under the kick, the analogue bass on octaves ringing out, no lead

## v1.06 (19 October 2026)

Step 10 of the harmony and generator proposal: the lead.

- **Eleven lead rhythms:** phrase, question answer, pickup, arp gate, hook, sparse melody, offbeat, rolling, acid, and two new four-bar ones: **long** (the Detroit string line) and **stab** (the rave riff: peak time and hard techno now use it). Gallop, tech bounce, sparse dub, trip hop and acid 16ths are off the list
- **Eight tunes:** one note, octaves, arp up, arp up-down, arp evolve, motif, question (was motif call) and the new **answer the bass**: the bass's riff, two octaves up, played only in the gaps of the bass rhythm. Call and response between the two parts. The melodies, motif high and the bass-shaped fragments are off the list
- **Register** (low, mid, high): where the tune lives, for every tune (replaces motif high)
- **Repeat** (tight, loose): how much bar 3 changes from bar 1 in the motifs. Tight is a hook (bar 3 is bar 1 with its last beat moved), loose a solo
- **Rests** (0 to 1): a share of the notes rest, different in every bar. Density thins the rhythm the same way every bar
- **A then A':** a four-bar tune over a longer lead plays its next version in the second half, not the same four bars again
- New projects start the lead on motif and phrase; the setting for it in Settings is gone (styles set the lead)
- Detroit's lead plays long with arp evolve on the dx

## v1.05 (19 October 2026)

Step 9 of the harmony and generator proposal: rhythms with siblings, and the bass rhythm list cut to house and techno.

- **Siblings:** every one-bar bass rhythm, and the one-bar lead rhythms (offbeat, rolling, acid, hook, sparse melody), carries two alternative last bars. The original plays the plain bar throughout; a variation (mutate, or evolve) ends the part on one of the siblings: a pickup 16th, a dropped last note, a held last beat, a 16th run, depending on the rhythm. Fewer presets, more music
- **Bass rhythms, eleven:** offbeat, 8ths, 16ths, dotted, octave, held, on the beat, cluster, bounce, acid (acid classic and acid 16ths merged) and the new **house pickup** (four bars of 8ths that walk into the next phrase). Dembow, two step, round the kick, gallop, sparse dub, trip hop and speed garage are off the list; loops saved on them still play

## v1.04 (19 October 2026)

Step 8 of the harmony and generator proposal: more progressions, and how the phrase ends.

- **Seven new progressions:** seven (i VII, the house and techno two-chord), six (i VI), five (i v), two five (ii v, the Rhodes loop that never resolves), lift (i VII VI VII), seven four (i VII iv; in mixolydian I bVII IV) and gospel (I vi ii V). With rate and the scales, that's a lot of ground
- **The stepper reads by chord count:** one, two, four, then soul. Garage and trip hop are off the list (they were rates, not progressions: half-bar and two-bar changes do them now); loops saved on them still play
- **Second half** (builder, where the turnaround switch was): the last bar of each phrase stays (**end: same**), turns to V (**turnaround**, as before) or climbs to VII (**climb**, the key's own 7th). Tap to step through. Styles set it: classic house and progressive sometimes climb, Italo piano and deep house sometimes turn round
- Styles now roll the new two-chord moves: seven for Chicago, tech house and Detroit, six for deep house, five for peak time, two five for deep house and nu disco, lift and gospel for classic house and Italo piano

## v1.03 (19 October 2026)

Step 7 of the harmony and generator proposal: the tab controls trimmed to the ones you hear.

- **Movement** (the LFO) is two controls: how often (every bar, 2 bars or 4 bars) and how deep. It's always a sine on the first knob (cutoff or brightness). Older loops with another shape or target move to that
- **Chorus** is on or off (on is II). Older loops on I or I+II come in on
- **Level** lives on the mixer only (styles set the mix); the tabs are for the sound
- **Strum** goes to 1 on piano and rhodes, 0.5 on poly and organ (they don't follow it further)
- **Half-time** for all three synths together on the builder's phrase row, beside fill and turnaround (each tab keeps its own)
- **Drums tab:** random is now **new sound**; wild is gone (morph with a new path travels far); synth drums lose tone (character moves it and more). Samples keep tone

## v1.02 (19 October 2026)

Step 6 of the harmony and generator proposal: the bass gets its own riffs.

- **Eight bass riffs**, its own list (it used to step through the lead's tunes, motifs and arps included): root, octaves, fifth, seventh below (the bVII under the root every house bass does), dub, walk up, acid, arp. A loop saved before keeps the riff it had, shown as "as saved", until you pick one
- **Slide** (bass tab): how many notes glide into the next, on top of the rhythm's own slides. Any rhythm goes from clipped to 303. Acid rolls with some on
- **Low (sub) / high (mid bass)** (bass tab): the same riff an octave up. The lead has the same octave setting underneath, for step 10
- Styles pick riffs from the new list

## v1.01 (19 October 2026)

Step 5 of the harmony and generator proposal: the chords get variation.

- **Vary** (chord tab, bottom left): **still** (as before), **breathe** (the last bar of the loop changes: a stab rhythm gets a push on the last 8th before the 1, a pad rhythm rests for its last beat) or **move** (bars alternate A B A B': B drops its last hit after the downbeat, B' adds one on the latest empty 8th). Saved with the loop and set by styles
- **Sustained** (new chord rhythm): a hit only where the chord changes, so a pad hangs across the progression. It follows rate and push. Dub techno can roll it
- **Drift** (voicing row): every second time round, chords built from the key sit one inversion higher, within the smooth band, then back
- **Chord rhythms named by feel:** pads, halves, offbeat, skank, organ, tresillo, call answer, 8ths, piano riff, sustained. Syncopated and garage skip are gone; a loop saved on either moves to tresillo
- Styles set vary, drift and evolve too (deep house, nu disco, minimal, progressive and dub techno start with evolve gentle)

## v1.00 (19 October 2026)

Step 4 of the harmony and generator proposal: evolve.

- **Evolve** (builder, under the phrase row): **off**, **gentle** or **lively**, and a tick for each part (drums, bass, lead, chords). At the start of every phrase one ticked part moves to a variation, in turn: the bass, then the lead, the chords, the drums, then round again. One change a phrase reads as arrangement, not a preset flipping
- **It comes home.** Gentle plays A B A C A B A D for each part (every other change is the original), lively A B C D. A variation is a neighbour of the original: the bass and lead step their mutate seed, the chords move to the next of the style's chord rhythms, the drums to the next of its grooves (both need a style lit)
- Parts that are yours are left alone, and evolve never touches engines, knobs or the progression
- **keep** (Perform, beside mutes land, while evolve runs) makes what's playing the new original. Each part's tab says where it is: "evolving: variation B, home in about 4 phrases"
- Saved with the loop (`ockm-evolve-every`, `ockm-evolve-mode`, `ockm-evolve-parts`); it uses the builder's phrase length and counts phrases from play, as the fills do

## v0.99 (19 October 2026)

Step 3 of the harmony and generator proposal: rate and push, on the builder beside the progression.

- **Rate:** how fast the chords change: **half bar**, **a bar each** (as before) or **two bars**. Every progression works at all three, so the 12 progressions become 36. Vamp at half a bar is jackin' house; deep house at two bars is the progressive version. The map below shows it bar by bar
- **Push:** every chord change lands an eighth early. Where a chord hit fell on the change, it moves to just before the 1 and holds over it, the house piano feel. The bass follows, since it reads the same chords. The Italo piano riff did this in its own rhythm; now any rhythm can
- Both are saved with the loop, and styles set them: push on for Chicago, classic house, Italo piano and nu disco; Chicago and classic house sometimes roll half-bar changes, progressive and deep house sometimes two bars

## v0.98 (19 October 2026)

Step 2 of the harmony and generator proposal: fewer engines, each sounding right the moment it's picked.

- **Every engine has its own sweet spot.** Picking an engine loads its four knobs at settings that suit it (before, the knobs stayed where the last engine left them, so k2 at 0.25 meant something different on every engine). A style that sets its own knobs keeps them
- **Bass, seven to six:** analogue, acid, sub 808, wide, FM, donk. Pluck is gone: analogue past decay 0.6 now rings on after its step and fades, which is what pluck did. Reese is now called **wide**. Sub 808's k2 is **weight** (the second harmonic, body on small speakers) instead of a second drive
- **Lead, five to four:** analogue (was mini), dx, sync and the new **supersaw**: seven detuned saws, from one saw (spread 0) to a trance and peak-time stack, with drift, and a hoover when the decay is long. Juno and lead acid are gone (analogue with the chorus, and analogue with the emphasis up)
- **Chords, six to four:** **poly** (was stab), organ, piano, rhodes. Poly's k3 is now **attack**: the bottom third is the dub techno stab, up from there a pad, and with the chorus a string machine, so pad and strings are gone. Its length goes up to about 3 seconds
- **Saved projects still load:** engine numbers are kept, and a project on a retired engine moves to its replacement set to sound like the old one (pluck to analogue with a long decay; lead acid to analogue with emphasis 0.8; juno to analogue with the chorus; pad and strings to poly with a slow attack, strings with chorus I+II)
- Styles that used retired engines now use their replacements (progressive leads on supersaw, peak time and hard techno can roll supersaw, Detroit and nu disco chords on poly with chorus)

## v0.97 (19 October 2026)

First step of the harmony and generator proposal.

- **A style never sounds the same twice.** Every tap on a style rolls a fresh take from its own lists: groove, key, scale, progression, bass rhythm and riff, chord rhythm, lead rhythm and tune, engines, and a new variation of the riffs. It always stays inside the style. **Classic** (under shuffle) plays the first of every list, the canonical version. **Shuffle** rolls the lit style again. Undo puts the last one back
- **Wider lists, so a roll has somewhere to go:** every style now has at least three grooves, three keys, two scales, three bass rhythms, two riffs and three chord rhythms, and three progressions where the style moves chords at all (techno and acid stay on one chord)

## v0.96 (19 October 2026)

- **Pads in Prog Change mode work.** The MPK mini's pads were set to send program changes (its PROG CHANGE button), which the app ignored, so the pads did nothing useful. Now both modes work. In Prog Change there's no let go, so a macro pad is a tap (breakdown and lift run their 4 bars; build and wash stay on until the next tap) and pump, drop and throw toggle. In notes mode they're held, as before
- **Pads read like the screen, top row first.** Bank A's top row is kick, snare, clap, hat; its bottom row the other four drums. Bank B's top row is macro slots A, B, C and pump; its bottom row drop, throw, rise and all in

## v0.95 (19 October 2026)

- **MIDI controllers: pads and knobs.** Plug in an MPK mini (or an MPC, or most pad controllers) and it's picked up within a couple of seconds, no setup. Pads, by note on any channel. Bank A (36 to 43): mute or bring back drums 1 to 8, landing like the Perform tiles. Bank B (44 to 51): macro slots A, B and C (held while the pad is, so a tap runs a recipe with a length), pump, drop and throw (held), rise, all in. Knobs (CC 70 to 77, or 1 to 8): filter (the middle is off), drive, delay, reverb, then k1 to k4 of the synth whose tab you last opened. Keys do nothing for now
- On the Pi, Pd now starts with MIDI on (it was off), and `tools/pi/ockm-midi-connect.sh` connects any controller to it as it's plugged in. MIDI clock in and out work there too now
- **Lift** is gentler: the high-pass goes half as far (0.3) and climbs slowly over the whole 4 bars

## v0.94 (19 October 2026)

- **Lift, on slot B:** breakdown's high-pass twin. The drums go, the high-pass climbs over a bar so the track thins right out, with a gentle touch of reverb and delay, then it all slams back on the 1. Tap for 4 bars or hold, like breakdown. It takes strip's place in your six macros (strip was mutes only, which breakdown and lift now do with effects). Wash is still in the library

## v0.93 (19 October 2026)

- **Performance recipes: mutes and effects together, with one finger.** A recipe can now have a length. **Breakdown** (new, on slot C) takes the drums out, sweeps the filter down over a bar, and brings up the reverb and delay. Tap it and it runs for 4 bars, then the drums and the effects all come back together on the 1. Or hold it as long as you like: let go and it drops on the next bar. Tap it again while it runs to drop early. Its mutes always land on the bar, whatever the live screen's mute setting. Set any recipe's length in settings, macros (no length, 1, 2, 4 or 8 bars)
- If your saved macros still have **lift**, it becomes breakdown
- **A starting mix like a real one:** kick 100, snare and clap 75, hats 50 to 55, percussion 60 to 65, bass 85, lead 70, chords 65. Every fader now goes to 150, so there's room to push things up. Styles set this mix too (undo puts yours back)

## v0.92 (19 October 2026)

- **A fatter, more real piano.** The piano engine is rebuilt as a struck string: ten partials, each a touch sharp the way a stiff string's overtones are, the first four doubled by a second string 3 cents up so they beat. Harder hits put more into the upper partials, and the higher partials die sooner, so each note starts bright and mellows. Plus a hammer knock. About twice the energy in the body (150 to 1000 Hz) with the same top end. The knobs do the same jobs: brightness, octave (the even partials), snap, length (now up to 4 seconds)

## v0.91 (19 October 2026)

- **Italo piano style:** Italian piano house. The M1-style piano on open triads in a major key, a new two-bar **piano riff** that pushes ahead of the beat, the M1 organ bass (donk) bouncing on the offbeats, the 909 kit
- Two new progressions for major keys: **piano house** (I V vi IV) and **anthem** (vi IV I V)

## v0.90 (19 October 2026)

- **Chords that don't sound like a home keyboard.** New fixed shapes (m9, m11, dub m7, 4ths, maj9) that move as one block with the progression, the chord memory sound of deep house, Detroit and dub techno. They sit on a second row on the chord tab, under the chords built from the key
- **9ths and 11ths leave the root to the bass,** and a flat 9th becomes the root, so they no longer grind
- **Smooth voicing keeps chords up around D4** (never below D3), picking the inversion or octave that sits there. Before, it folded chords into the octave above the key's root, which was low and muddy, and squashed 9ths into semitone clusters. Smooth is now on the voicing row, next to close, open and wide
- **Every hit varies a little,** accents hit harder, and on the stab engine the hit opens the filter more or less
- **Styles:** every style with chords now uses shapes or rich chords (Chicago dub m7 organ stabs, Detroit m11 strings with chorus, deep house m9 Rhodes, dub techno dub m7 stabs and so on), sets the chorus and strum, and cuts the chord track below 150 Hz
- The chord notes are worked out in one place (`seq/ockm-chordnotes.pd_lua`), shared by the sound and the screen

## v0.89 (19 October 2026)

- **909 and 808 kits:** three kits from your Analog Drums packs (909, 909 long, 808), and every style loads one, tuned as the style tunes its drums
- **Drum bus with punch:** the eight drums now go through parallel compression and a soft saturator before the mix. Punch (drums tab) sets how much; each style sets its own. Tuned on the 909 kit: at 1, about 6 dB fuller with the peaks kept
- Samples play about 5 dB louder, level with the synth drums

## v0.88 (19 October 2026)

- **One sidechain model:** each part's tab sets how it pumps (amount, and duck, pump or gate: now on the lead and chord tabs as well as the bass). Perform's **pump** is a move you hold, like drop and throw: deep while held, gone when you let go (it was a three-way switch on top of the tab settings)

## v0.87 (19 October 2026)

- **One Perform screen.** What was Perform B (track tiles with quantised mutes, the mute presets, the effects and macros) is now **perform**, the home screen, in a wide tab where the two used to sit, so the other tabs haven't moved
- **All drums, on the drums tab:** Perform A's eight-lane grid with mute and solo. Tap **all drums** or swipe left across the drum slots to get there; tap a name, swipe right across the names, or tap **one drum** to come back
- Mutate, original and density live on the bass and lead tabs (they were also on Perform A)

## v0.86 (19 October 2026)

- **Mutate changes the rhythm too:** each variation of the bass or lead now moves a hit or two (adds a note on a resting 8th, drops a plain note), not just the notes. Accents and held notes stay, and a variation repeats steadily
- **The bass leads back round:** on loops of 2 bars or more, the last bar gets a pickup note just before the loop starts again (not the lead: its phrases already land where they mean to)
- **Grooves breathe:** the house and techno grooves have ghost and soft notes (hats with loud offbeats and ghosted 16ths, the odd ghost before a backbeat). Grooves can use g (ghost) and o (soft) as well as x and X

## v0.85 (19 October 2026)

- **Phrase on the builder:** one length (off, 4, 8 or 16 bars) for everything at the end of a phrase, with a switch for each move: drum fill and turnaround. The drums tab keeps the fill style (plus no fill) and says the phrase length. Before, the fill and the turnaround each had their own count on different tabs

## v0.84 (19 October 2026)

- **Styles, house through to techno:** deep house, Chicago, classic house, nu disco, tech house, minimal, progressive, dub techno, Detroit, acid, peak time and hard techno. Garage, speed garage, drum and bass, boom bap and lofi are gone. Each style now sets a key and scale too, uses its own engines and progressions, and seven of them bring the lead in
- **Shuffle** re-rolls the lit style within its own choices (key, groove, progression, engines, rhythms, riff variation)
- **House piano** rebuilt, M1-style: two strings beating gently, a hammer click, bright as it rings (it had decayed to an electric-piano tone). **Rhodes** rebuilt: a warm body with the tine on the attack, bark on hard hits. Chord engines get a low cut on their output (FM at a 1:1 ratio puts a sideband at 0 Hz)
- **Pruned:** the lead's six rhythms that copied the bass's, and the three older melody shapes, are hidden from the steppers (saved projects still play them)
- **Renamed:** fills drop and build are now cut out and snare build (drop is the Perform pad, build a macro). Perform A says mutate, original and density, like the tabs

## v0.83.1 (19 October 2026)

- **The Pi boots straight into the app,** with no desktop or taskbar first. It logs in to its own session that only runs our start-up (screen rotation, then the app). Quit to desktop still brings the desktop up

## v0.83 (19 October 2026)

- **Rise builds to a proper drop.** It used to lift the high-pass across the loop and glide back over 100 ms: a fizzle. Now pressing rise starts a build to the next loop start at least 2 bars away: the high-pass climbs, a noise riser comes in over the last bar's first 3 beats, the last beat drops out, and on the 1 everything slams back (the filter snaps open, the riser cuts, a crash and sub boom). Then rise switches itself off. Switched off by hand mid-build, it glides back with no drop
- ockm-rise-now takes an optional glide time ("value ms")

## v0.82 (19 October 2026)

- **The Pi no longer breaks up on build, wash and the macros.** The screen draws on the same core as the sound. A sweep that changes a value every few milliseconds made it redraw every 5 ms, which on the Pi (at double size) starved the audio. Redraws are now capped at 25 a second however many values change. Measured on the Pi: Pd went from 40 to 100% of a core to 10 to 20%. The sound engine itself is only about 8%
- The Pi's audio buffer is 30 ms (was 20), for a little more headroom

## v0.81.1 (19 October 2026)

- **Pi: sound through the DAC Pro.** The start script turned the DAC's card number into Pd's device number the wrong way, so the sound went to the second HDMI port. It now finds the DAC by name in Pd's own device list

## v0.81 (19 October 2026)

- **The lead's freedom buttons are now one slider, inside to outside.** It builds up as it goes: chord notes, then passing notes between the beats, then colour (7ths and 9ths on some beats), then outside (octave leaps and chromatic notes). It works on one chord, mutate picks where the extra notes land, and the steps show what it plays. Replaces ockm-lead-freedom with ockm-lead-outside
- Sliders between two named ends show the ends at the sides and what they're doing now in the middle

## v0.80 (19 October 2026)

- **Reese bass fixed:** each note started with a loud, bright "breath". Two causes: the filter envelope swept up to 6 kHz through a resonant filter (now up to 2.5 kHz, with gentler resonance), and the detuned saws started in phase then cancelled, so the level halved over the first half-second. A steady sine sub now holds the low end under the beating saws
- **Drum + bass** sets the reese's own knobs (cutoff, wider detune, almost no envelope, longer decay) instead of inheriting the analogue's

## v0.79 (19 October 2026)

- **Sidechain shapes, on the bass to try:** duck (a quick dip under the kick, back within a step), pump (dips hard, holds, swells back over the beat) and gate (cut for an eighth, then straight back), with a picture of one beat. At full the sidechain now dips all the way to silent. The engine has the shapes for the chords and lead too (ockm-<part>-scshape), defaulting to pump, so they pump harder than before; their tabs get the choice once the bass feels right. Drum + bass ducks its bass

## v0.78 (19 October 2026)

- **The builder's part tiles have an on/off switch** (the same as on each part's tab) instead of in/out, and say "off in this pattern" when off, here and on Perform

## v0.77 (18 October 2026)

- **Song is now Builder**
- **Kits:** a style can load a sampled kit, one file per sound folder called kit-<name>. Three kits from the CM Lofi packs: breaks (drum + bass), boom (boom bap), dusty (lofi). The drums tab names a kit sample ("breaks kit"). Without the files, the style voices the synth kit instead
- **Two new styles: boom bap and lofi.** Trap is parked (it needs hat rolls and gliding 808s)
- **Drum + bass** plays the breaks kit, with a harder synth fallback
- **Speed garage reworked:** a skippy, shuffled top end over the 4/4 kick (rim and snare ghosts, offset hats), and a new speed garage bass rhythm: held notes pushed off the kick, sliding at the end of the phrase, on a driven sub with a pitch drop
- **Deep house** at 123 (was 120), less swing, a bass that pushes
- The sample library reports file names (ockm-sample-name)

## v0.76 (18 October 2026)

- **Styles on the song screen:** house, deep house, tech house, techno, hard house, acid, dub techno, garage, speed garage, drum + bass. One tap sets tempo, swing, groove, kick and clap (or snare) character, which parts are in, their sounds, rhythms and riffs, the progression, sends and half-time. Samples and saved drum sounds are left alone. Undo puts it all back
- **Half-time** for the bass, chords and lead: a switch on each tab. The part plays its own pattern at half speed over two loops
- **New groove bank, hard + fast:** hard house, drum and bass two-step, drum and bass rolling. Minimal and dub techno now have a flat, even kick
- **Master reverb** starts lower (0.3, was 0.5)
- The song screen is a little tighter to make room for the styles

## v0.75 (18 October 2026)

- **Sidechain on the bass, chords and lead:** each tab has a sidechain slider. Turned up, that part dips on every kick and swells back over an eighth note. The Pump button on Perform still pumps all three at once, on top
- **Controls that belong together share a panel:** the LFO row and the reverb and delay sends on the bass, lead and chord tabs, the master delay (amount, feedback, time) and reverb (amount, size) on both Perform screens, and the sends on the drums tab
- **Perform B's scene buttons** (drums only, no drums, kick + bass, all in) have an orange edge and light up when tapped
- **The rhythm lock is gone** (own rhythm, on the kick, fill gaps): it fought the rhythm choice. A part made for you that used it goes back to its own rhythm

## v0.74 (18 October 2026)

- **Song replaces compose.** Four tiles say what's in this pattern (drums, bass, chords, lead): tap to take a part out or put it back. Out is silent, dims on Perform, and mutes, scenes and macros can't bring it back. Each part's tab has the same on/off switch, top right
- **One harmony, no modes.** The progression, key and scale live on the song screen and every part follows them, even with the chords out. "Fit the chords to my bass / my lead" picks the progression for a line you've written. A bar-by-bar strip names the chords
- **Turnaround:** the last bar of every 4, 8 or 16 goes to V major and leads back round; the chords, bass and lead all follow it
- **Made for you, or yours:** editing any step makes a part yours and nothing rewrites it. If the harmony changes under it, the tab offers refit my line or leave it. Make it for me hands it back
- **Bass:** riff, and movement: pedal, follows or walks (approach notes into each chord change)
- **Lead:** tune, and freedom: chord notes, passing notes or free
- **Chords:** colour (triads, 7ths, 9ths, 11ths) replaces spice
- **Mutate has back:** step through earlier variations, as well as original
- **Breakbeat fill:** a fifth fill choice on the drums tab that swaps the last bar for a one-bar breakbeat (broken kick and snare with ghost notes, straight hats, everything else quiet for the bar)

## v0.73 (18 October 2026)

- **Donk keeps its body when you cut the decay:** its decay now runs from a short donk (about 120 ms) up to about 1.4 s, and fades more gently, instead of vanishing at the bottom of the knob

## v0.72 (17 October 2026)

- **Analogue bass: the filter opens up like a real one.** Raising the cutoff or envelope now makes it brighter and fuller, never quieter. The old filter (Pd's vcf~) lost level as the cutoff rose and went silent above a quarter of the sample rate; it's now a flat-response state-variable filter

## v0.71 (17 October 2026)

- **New bass line-up, by family:** **analogue** (Minimoog, SH-101, Pro-One: saw to square, a sub, a resonant 24 dB filter) is the new default; **donk** (bassline house, garage, M1 organ bass) is new; **sub** becomes **sub 808**, ringing on like an 808 when the decay is up, with a quicker, deeper pitch drop. Saw and house are folded into analogue
- Reese is louder, level-matched with the others
- Projects that used house now use analogue, set close to how they were. Your starter project starts on analogue

## v0.70 (17 October 2026)

- **Saw bass earns its slot:** brighter by default (the tone knob was starting it dark), lightly saturated for weight, and level-matched to the other bass engines
- **Reverb and delay on the drums tab** for each drum, under its sliders (the same sends as on the mixer). While stopped, moving them plays the drum

## v0.69 (17 October 2026)

- **New projects start dry:** every reverb and delay send (drums, bass, lead, chords) starts at 0. Your saved projects keep theirs
- **Soft drum hits keep their snap.** Velocity is now a plain volume after each sound's drive, so a normal (unaccented) hit is the same sound as an accent, just quieter. Before, soft hits pushed less into the drive and the claps lost their crack

## v0.68 (17 October 2026)

- **The bass gets its own rhythm list, the classics first:** offbeat donk, straight 8ths, rolling 16ths, dotted 8ths, octave jump, sustained, quarters, dembow, two step and 3-2-3 cluster, then the older ones. The lead keeps its list
- **Held notes:** rhythms can now hold a note across steps (the sustained bass holds one note for the bar). Octave jump brings the octaves notes with it

## v0.67 (17 October 2026)

- **Tapping a drum at the top plays it** while stopped
- **Claps send less to the reverb in new projects** (0.1, was 0.35): the lab clap has its own room built in

## v0.66 (17 October 2026)

- **Save your own drum sounds.** The disc next to the sound box keeps the slot's synth sound (named like "kick 1") in my-settings.lua, so any project can use it. The arrows step through the synth, your saved sounds, then samples. On a saved sound the disc becomes a bin, to delete it
- **Random and wild put morph back to 0,** since each picks a new morph path. Character stays where you set it
- **New kit is gone,** and the sound box is narrower

## v0.65 (17 October 2026)

- **Drums tab: hear it as you change it.** While stopped, moving any drum slider plays the sound
- **Character, morph, random, wild and reset moved to the top,** above the sliders, and greyed out when the slot plays a sample. Character and morph show an orange line at their position; random, wild and reset light up when tapped, with no message

## v0.64 (17 October 2026)

- **The drum lab's sounds are now GNRTR's synth drums,** replacing 909, 808 and industrial. Every slot plays the lab voice for its sound; perc 1 and perc 2 choose rim, conga or shaker
- **Character, morph, random, wild and reset** on the drums tab for each synth sound. The lab's small settings stay in the lab. Saved with the project as seeds, so the sound comes back exactly
- Older projects: kick, snare, clap, hats and tom ignore their old 808 or industrial choice and play the lab sound; perc slots read it as rim, conga or shaker

## v0.63 (17 October 2026)

- **Drum lab: character and morph.** Every sound gets a named character slider (punch, crack, room, metal, boom, slap, wood, shake) that moves a recipe of settings, and a morph slider that walks a smooth path through nearby sounds, TR-8S style. New path, and keep to make the result your sound

## v0.62 (17 October 2026)

- **Drum lab: the full kit.** Kick, toms (a low, mid and high set), congas (low and high), rim and shaker join the clap, snare and hats. Each renders into the right samples folder; sets render as matching files. The loop plays the whole kit together

## v0.61 (17 October 2026)

- **Drum lab: hats.** One metallic hat sound with closed and open lengths. Play either, loop them on the offbeats, and render a matching pair in one go: closed into `samples/hat`, open into `samples/open-hat`, sharing a name

## v0.60 (17 October 2026)

- **Chorus on every synth:** Juno-style, with off, I, II and I+II, on the bass, lead and chord tabs. Off is exactly the dry sound, and it's saved with the loop

## v0.59 (17 October 2026)

- **An LFO on every synth** (bass, lead, chords): moves one of the four knobs in time with the loop. Five shapes, from a 16th to 8 bars, with depth. At depth 0 the knob is exactly where you left it
- **Chord voicing:** close, open or wide
- **Strum:** the notes of each chord come in one after another, from tight to a slow strum

## v0.58 (17 October 2026)

- **New projects start everything at 1:** bass and lead notes and rhythms start on the first preset, like the chords. Settings > new projects can still start the lead as motif, call and answer, or arp

## v0.57 (17 October 2026)

- **Drum lab:** a separate patch (`OCKM_DRUM_LAB.pd`) for designing claps and snares with far more control than the drums page: bursts, noise colours, tails and room for the clap; tuned body, pitch drop, wires and click for the snare. Play, loop against a kick, randomise around what you have, and render a hit straight into `samples/clap` or `samples/snare` as a WAV

## v0.56 (16 October 2026)

- **Perform A:** empty steps on the beat (1, 5, 9, 13) are a shade lighter, so each bar reads in fours

## v0.55 (16 October 2026)

- **A new top bar:** Perform A (was perform), Perform B (was live) and mixer together, then compose and the four parts, then arrange. Save is a disc that goes orange when there's something to save; **☰** opens project, export, settings and revert (and quit to desktop on the Pi)
- **Settings,** in four sections: this project (tempo, swing, accents, reverb tone, MIDI clock), new projects (starting lengths and lead style), this device (theme, filter snap speed, where mutes start) and macros
- **Your macro library:** six macros, each up to four moves with an amount, how it gets there and how it lets go (snap, glide or stay). Three slots on Perform B; the small v on each picks the macro. Kept in `my-settings.lua`, the same in every project
- New macros out of the box: sink, dub out and lift, alongside build, wash and strip

## v0.54 (16 October 2026)

- **Live, a second perform screen** (its own tab, next to perform): a big tile per track to mute, plus all synths, scenes (drums only, no drums, kick + bass, all in) and the master effects at full size
- **Mutes that land on the beat or the bar** (or now). Tap several and they switch together. The engine holds them, so they land exactly before that step's hits
- **Macros** (hold to play): build, wash and strip. Each moves several effects (or mutes) at once and puts them all back when you let go
- The tabs are a little narrower to make room for live

## v0.53 (16 October 2026)

- **909 clap re-voiced:** higher, shorter, a touch darker and a little quieter. What used to take tune +5, decay 62, tone -0.43 and level 0.91 is now where it starts, with the sliders at neutral

## v0.52 (16 October 2026)

- **Motif melodies for the lead:** motif, motif call and motif high. A short idea is stated, repeated, varied and brought home over four bars, so the lead sings rather than wanders. Each has 8 versions, and new steps through them
- **Arp evolve:** an arpeggio over whichever chord is playing that changes as it goes. New gives a different shape
- **Four-bar rhythms:** phrase, question answer, pickup and arp gate. A rhythm now repeats at its own length (one bar or four)
- **Chord notes on the beat (lead):** a note landing on a beat always belongs to the chord playing. This also tightens the existing melodies

## v0.51 (16 October 2026)

- **Perform reworked:** the bass, lead and chord lanes are gone, so the 8 drum lanes are deeper and easier to hit
- **A synth card:** bass, lead and chord buttons with M, S and a light that flashes as each part plays. For the part you pick: **new**, **orig** and **busy** (bass and lead), the chord rhythms (chords), and its four knobs
- **An effects card:** a row of moves (rise, pump, **drop**, throw), the filter with hold in its corner, drive, then delay and reverb
- **Drop** (new): hold it and nothing new plays while the effects ring on; let go and everything lands back on the next bar
- **The filter snaps back** when you let go (50 ms instead of 180), and the screen shows it home at once

## v0.50 (16 October 2026)

- **A length per part:** drums, bass, lead and chords each 1, 2, 4, 8 or 16 bars. The loop is as long as the longest part, and shorter parts repeat inside it. Loops can now be 16 bars
- **Length and double on each part's tab,** on the navigation strip. Shorter offers undo. The strip shows "loop 4 bars (bass, lead, chords)" on every screen
- **New projects:** drums 1 bar, synths 4 bars
- **Generators write their natural length:** a groove makes the drums 1 bar; a progression sets the chords' length; a bass or melody following the chords takes their length
- The old "drums loop" buttons are gone: the drum length does that job. Older loops load with their single length on every part
- MIDI export repeats each part at its own length

## v0.49 (15 October 2026)

- **Runs on the Raspberry Pi**, full screen on the 10" Touch Display 2, and starts by itself at power-on (`tools/pi/`)
- **Touch fixed for the Pi:** single taps count first time
- **Drum steps, M and S act the moment your finger lands**, and each tap redraws the screen once instead of twice
- Tests use only a clean blank project, so they pass on a machine with your own projects on it (they didn't on the Pi)

## v0.48 (15 October 2026)

- **M and S on compose**: mute and solo for chord, bass and lead, right on their cards

## v0.47 (15 October 2026)

- **One loop per project.** Pattern slots 2-8, song mode, the song tab and the old Arrange are gone. Projects save `loop.txt` instead of `p1.txt` to `p8.txt` and `song.txt`
- **Arrange tab** in place of song: it says what's coming while arrangements are rebuilt (row of 16-bar units, a transition at every joint)
- Export plays the loop 1, 2, 4 or 8 times
- Live play is unchanged: mutes, solos, filter, throw, drive, delay, reverb, rise, pump and fills all work on the loop
- Screen previews after the EQ sheet no longer show it by mistake

## v0.46 (15 October 2026)

- **Undo**: arrange, grooves, clear, new kit and de-mud now offer an undo button straight after. One step, and it takes patterns, song, kit and EQ back to just before
- **New patterns are 8 bars** (128 steps), ready for the loop-to-track arranger
- Step 1 of the new arranger (see the design doc)

## v0.45 (15 October 2026)

- **Per-track EQ** on the mixer: low cut, low shelf, a movable mid bell and high shelf for every track, with a response curve. Saved with the project
- **See each track's spectrum** behind the EQ curve while it plays (8 octave bands, 60 Hz to 8 kHz). The analyser only runs while you look, to save CPU
- **De-mud** listens to your mix for 4 seconds and sets low cuts track by track from what it hears, plus a low-mid scoop if the mix is crowded there. The kick and bass keep their low end

## v0.44 (15 October 2026)

- **Three synth sounds per drum: 909, 808 and industrial**, before your samples in the drum picker
- The 909 kick and clap rebuilt: a faster drop, a click and saturation on the kick; four hard-edged bursts, two noise bands and crunch on the clap. Snappier snare
- New 808 set: boom kick, tonal snare, loose clap, clave, metallic hats, round tom, cowbell
- New industrial set: distorted rumble kick, noise-blast snare, big-room clap, clank, harsh hats, trash ride, dirty tom, zap
- Different sliders for synth (tune, decay, tone, drive) and samples (pitch, length, tone, start). Reverb and delay sends live on the mixer

## v0.43 (15 October 2026)

- Arrange is labelled **beta**: a starting point while transitions and drops get more work

## v0.42 (15 October 2026)

- **Transitions** between song sections: each pattern can end with a fill, a riser, riser + gap or a dub out, and start with an impact (crash and sub boom). Set on the song tab
- **Sidechain pump**: the kick ducks the synths. Off, light or deep, per pattern, on perform
- **Arrange uses them**: builds end with riser + gap into drops that land with an impact and pump; breakdowns start with a crash; sections that thin out echo away
- Arrange has a "pump on the drops" option

## v0.41 (15 October 2026)

- **Export** (project screen): the song or a pattern as a stereo mix, stems (drums, bass, lead, chords, effects) and/or a MIDI file
- **Record what I play**: a live recording of the mix (and stems) until you stop it
- Saves to the exports folder, or a USB stick when one is plugged in

## v0.40 (15 October 2026)

- **Arrange**: on the song tab, turn pattern 1 into a whole track. Writes intro, groove, build, breakdown, drop B, key lift and outro variations into patterns 2-8, plus the song chain. Options for style, length, sections, builds, breakdowns, key lift and variation, and a surprise me button
- **Part on/off per pattern** on each synth tab
- **Rise**: a per-pattern build where the high-pass climbs across the pattern (on perform, by the filter)

## v0.39 (15 October 2026)

- Three new chord sounds: **piano** (M1-style house piano), **rhodes** (electric piano with bark and tremolo) and **strings** (string machine with an ensemble chorus)
- All six chord sounds sit at similar levels

## v0.38 (15 October 2026)

- **Velocity**: a lane under the drum steps. Drag each bar up and down, or swipe across to draw
- **Micro timing**: the same lane in timing mode pushes a hit up to a quarter step late or pulls it early. The engine runs a quarter step behind the clock to make early possible
- **Drums loop**: sketch the drums on 1 or 2 bars under a longer pattern, then **double** to fill it out
- **Swing** on the drums tab
- **Three groove banks**: classics, house + garage, techno + breaks. 24 new grooves
- **10 more samples per sound** (30 a folder; 27 toms and 29 percs after duplicates were skipped). The existing numbers don't move
- The sound bar is gone: each slot is its sound, and the sample picks the flavour

## v0.37 (15 October 2026)

- **The lead has its own sounds**, separate from the bass: mini (Minimoog-style, the new default), juno (with chorus), dx (DX7-style FM: tine, reed, bell, glass), acid (voiced as a lead) and sync
- Lead notes glide on slide steps and get a vibrato that fades in on held notes
- Old projects keep sensible sounds: acid stays acid, FM becomes dx, and the old default (pluck) becomes mini
- First of two batches. Next: whistle, supersaw, hoover, melodica, vox

## v0.36 (14 October 2026)

- **Drum samples.** Each slot can play a sample from its sound's folder instead of the synth sound. Pick it on the drums tab: arrows step through the folder, each change plays it, tap the box to hear it again
- **New kit** button: a random sample for every slot that has some
- The kit, samples included, belongs to the project
- Tune works like an MPC (playback speed), decay trims the tail, level and sends work as before
- The slot buttons show the sample number, e.g. "kick 03"
- Opening a project now resets project settings to their defaults first, so a setting missing from an older project file doesn't carry over from the last one

## v0.35 (14 October 2026)

- Rim and rimshot are now **perc 1** and **perc 2**. Both pick from one shared `samples/perc` folder, so you can mix and match
- Sample folders filled from your library: 20 numbered one-shots per sound, with a batch from Tape909 in each (`tools/pick_samples.py`, sources listed in `samples/sources.csv`)
- Until sample playback lands, perc 1 still plays the short rim synth and perc 2 the 909-style rimshot

## v0.34 (14 October 2026)

**Changed**
- New patterns and projects are **4 bars** long by default
- Length is shown in bars: 1, 2, 4, 8
- **Shorter keeps the start, and nothing is lost:** go longer again and the bars you'd hidden come back, instead of being overwritten with copies. The pattern remembers its longest length when saved
- **Longer** repeats what you've written; parts on auto (following parts, and preset-driven ones) are rebuilt to fill the new length, so a 4-bar progression plays in full instead of repeating its first chord
- Changing the length no longer stretches the pattern back out to the progression's length

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
