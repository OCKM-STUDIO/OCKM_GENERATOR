# Mac preview validation

8 November 2026, Apple Silicon Mac, Swift 6.3.3 command-line tools.

Passed:
- Release build with statically linked libpd and Lua; app bundle code signing verification
- Real shared-engine playback with finite, non-silent audio
- Native drawing commands for 12 instrument screens
- Drop key down/up releases the held effect
- Scene saving and reopening in a separate process, including a workspace path with spaces
- All four existing plain-Lua test programs (chords, lines, lanes and two-handed voicings)
- Native window inspection: builder, perform, mixer and bass; playback, save and navigation shortcuts

Both automated playback runs reported zero audio-buffer underruns. These are short
integration tests, not a sustained live-performance benchmark.

Not yet validated: physical MIDI hardware/clock accuracy, long performance sessions,
all legacy Pi integration tests, Intel Macs and older supported macOS releases.
The engine currently logs two pre-existing limiter division warnings at silence;
the audio remained finite in these checks. No shared audio formulas were changed
for this port.

This build is locally signed, not Developer ID signed or notarised.
