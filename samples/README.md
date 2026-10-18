# Samples

One folder per drum sound: kick, snare, clap, perc, hat, open-hat, tom. Perc 1 and perc 2 both pick from the perc folder, so you can mix and match.

- WAV or AIFF, 16 or 24 bit, 44.1 or 48 kHz. Mono is best for drums
- Short one-shots, trimmed so the hit starts right at the beginning of the file
- The screen shows samples by number, in file-name order: `01.wav` is sample 1. Numbering your files keeps it predictable
- Mono or stereo (only the left channel plays), any sample rate
- Up to about 64 per folder keeps browsing quick on the 10-inch screen

Audio files in here aren't saved to git (they're big). Back the folder up yourself.

**Kits:** a file called `kit-<name>` in a folder belongs to that kit (`kick/kit-breaks.wav`, `snare/kit-breaks.wav`). Styles on the builder load kits by name. Letters sort after numbers, so kit files come after your numbered samples and never shift them.
