# Vox voices

The lines are in `tools/vox_lines.txt`. `tools/make_vox.py` speaks them once, on a computer, and writes the WAVs here. The box only plays the files.

Two voices, both Piper, both trained from scratch on public-domain LibriVox readings. Not an impression of anyone.

- **deep** is `en_US-norman-medium`. US English, male. Dataset public domain (LibriVox). Model card: rhasspy/piper-voices, `en/en_US/norman/medium`.
- **flat** is `en_GB-cori-medium`. British English, female. Dataset public domain (LibriVox). Model card: rhasspy/piper-voices, `en/en_GB/cori/medium`.

The render turns the noise off and slows the deep voice a little, so they stay even rather than chatty. Piper itself is MIT.
