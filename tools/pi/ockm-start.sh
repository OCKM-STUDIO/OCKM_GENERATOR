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
exec pd $SOUND -nomidi -path tools/pi -path /usr/lib/pd/extra/pdlua -lib pdlua -open OCKM_GENERATOR.pd
