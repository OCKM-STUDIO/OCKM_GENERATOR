#!/bin/sh
# Start OCKM_GENERATOR full screen on the Pi (run at login by ~/.config/autostart/ockm.desktop).
# Sound goes to the DAC Pro when it's fitted, otherwise Pd starts without sound.
cd "$(dirname "$0")/../.." || exit 1
export OCKM_KIOSK=1
# Pd numbers its sound devices its own way (each card twice, "hardware" and "plug-in", counting from 1 on the command line),
# so ask Pd for its list and pick the DAC's hardware entry by name. Card numbers from aplay don't match.
N=$(timeout 10 pd -nogui -alsa -listdev -send "pd quit" 2>&1 \
    | sed -n '/^audio output devices:/,/^API/p' \
    | grep -i "dac.*(hardware)" | head -1 | sed 's/^\([0-9]*\)\..*/\1/')
if [ -n "$N" ]; then
    SOUND="-alsa -audiooutdev $((N + 1)) -noadc -r 48000 -audiobuf 30"
else
    SOUND="-nosound"
fi
# v1.48 USB audio out: when the Pi is a USB audio interface (tools/pi/ockm-usb-audio.sh made it at start-up), the box
# plays through PipeWire instead: 9 outputs (the mix, then the kick and a channel per part), the mix to the DAC and all 9 to the USB
# port, with PipeWire keeping the DAC and the computer's clocks in step. Anything missing: the DAC on its own, as before
USB_AUDIO=""
if [ -n "$N" ] && aplay -l 2>/dev/null | grep -q UAC2Gadget && command -v pw-jack >/dev/null; then
    USB_AUDIO=1
    SOUND="-jack -nojackconnect -jackname ockm -inchannels 0 -outchannels 9 -r 48000"
    "$(dirname "$0")/ockm-audio-links.sh" &
fi
# v1.49 Pd's messages (errors included) go to /tmp/ockm-pd.log, fresh each start
# MIDI: Pd's own ALSA input and output (clock out to a follower, clock and pads and knobs in); controllers are
# connected to it as they're plugged in (v0.95)
"$(dirname "$0")/ockm-midi-connect.sh" &
if [ -n "$USB_AUDIO" ]; then
    exec pw-jack -p 256 pd $SOUND -alsamidi -midiindev 1 -midioutdev 1 -path tools/pi -path /usr/lib/pd/extra/pdlua -lib pdlua -stderr -open OCKM_GENERATOR.pd 2>/tmp/ockm-pd.log
fi
exec pd $SOUND -alsamidi -midiindev 1 -midioutdev 1 -path tools/pi -path /usr/lib/pd/extra/pdlua -lib pdlua -stderr -open OCKM_GENERATOR.pd 2>/tmp/ockm-pd.log
