# Setting up the GitHub page

What to paste where when the repository goes public. (This file can be deleted once it's done.)

## The repository

**Name:** `OCKM_GENERATOR` (GitHub doesn't allow spaces, and it matches the patch's file name). The project itself is **OCKM GENERATOR** everywhere people read it: the README, the manual, the app's settings page and the social image.

## About (the box on the right of the repo page)

**Description:**
> A generative groovebox for house and techno: drums, bass, lead and chords, built in Pure Data, played on a touchscreen. Runs on a Raspberry Pi 5 or in plugdata.

**Website:** https://ockm.studio (or leave blank)

**Topics:** `groovebox` `pure-data` `puredata` `plugdata` `pd-lua` `raspberry-pi` `synthesizer` `drum-machine` `sequencer` `generative-music` `house-music` `techno` `music` `lua` `touchscreen`

Untick **Packages** and **Deployments** in the About settings, so the sidebar stays clean.

## Social preview

Settings, General, Social preview: upload `docs/img/social.png` (1280 x 640). It's the picture that shows when the link is shared.

## The first release

Releases, Draft a new release. Tag `v1.49`, title **OCKM GENERATOR v1.49: first public release**. Notes:

> The first public release of OCKM GENERATOR, a generative groovebox for house and techno.
>
> - Tap one of fifteen styles and it builds a whole loop: tempo, groove, key, chords, bassline, lead, sounds and mix
> - Play it on the Perform screen: mutes on the beat or bar, rise, rewind, drop, repeat, the fx pad, the mood dial from chill to peak, and recipe pads like the 4 bar rewind
> - Every drum is synthesised, with 808, 909 and 909 long kits: no samples needed (add your own if you like)
> - Bass, lead and chord synths with several engines each, every sound levelled by measurement
> - Scenes, versions with transitions, export of the mix, stems and MIDI
> - On a Raspberry Pi 5: full screen at boot, touch, USB MIDI, and USB audio out (9 channels to your DAW)
>
> Mac and PC: open `OCKM_GENERATOR.pd` in plugdata. Raspberry Pi: see the README.

Attach nothing: the source is the download.

## Before pushing

- Commit email: GitHub, Settings, Emails shows a no-reply address (`<id>+<user>@users.noreply.github.com`). To keep your own email off the commits, set it with `git config user.email <that address>` before pushing, and rewrite the history if you want the old commits changed too
- Check `git status` shows no samples, projects of your own, `my-settings.lua` or `.pi/` (they're all in `.gitignore`)
- The screenshots: `python3 tools/screenshots.py <project folder>` redraws them from a scene of your choice
