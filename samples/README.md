# Samples

One folder per drum sound: kick, snare, clap, perc, hat, open-hat, tom. Perc 1 and perc 2 both pick from the perc folder, so you can mix and match.

- WAV or AIFF, 16 or 24 bit, 44.1 or 48 kHz. Mono is best for drums
- Short one-shots, trimmed so the hit starts right at the beginning of the file
- The screen shows samples by number, in file-name order: `01.wav` is sample 1. Numbering your files keeps it predictable
- Mono or stereo (only the left channel plays), any sample rate
- Up to about 64 per folder keeps browsing quick on the 10-inch screen

**Vox** (`vox/<set>/<voice>/01.wav` and on): spoken lines, mono 48 kHz, played whole. The lines are in `tools/vox_lines.txt`. `tools/make_vox.py` renders them. The box never makes the voice itself.

**Samples part** (`user/voice`, `user/loops`, `user/hits`): your own sounds for the samples tab, one folder per tab on the screen. Drop WAVs in and they show in that tab in file-name order. Each plays whole, from the start to its end, so trim loops to a bar or two at your tempo. Mono is best. The spoken lines above are under **robot**.

Audio files in here aren't saved to git (they're big). Back the folder up yourself.
