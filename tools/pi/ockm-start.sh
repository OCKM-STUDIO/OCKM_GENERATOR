#!/bin/sh
# Start OCKM_GENERATOR full screen on the Pi (run at login by ~/.config/autostart/ockm.desktop).
# Sound goes to the DAC Pro when it's fitted, otherwise Pd starts without sound.
cd "$(dirname "$0")/../.." || exit 1
export OCKM_KIOSK=1
if aplay -l 2>/dev/null | grep -qi "dacpro\|DAC"; then
    CARD=$(aplay -l | grep -i "dacpro\|DAC" | head -1 | sed 's/^card \([0-9]*\).*/\1/')
    SOUND="-alsa -audiooutdev $((CARD + 1)) -noadc -r 48000 -audiobuf 20"
else
    SOUND="-nosound"
fi
exec pd $SOUND -nomidi -path tools/pi -path /usr/lib/pd/extra/pdlua -lib pdlua -open OCKM_GENERATOR.pd
