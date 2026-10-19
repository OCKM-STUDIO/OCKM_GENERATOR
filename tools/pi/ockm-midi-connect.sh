#!/bin/sh
# Connect every MIDI controller (USB keyboards, pad controllers, an MPC) to OCKM_GENERATOR, and keep doing it, so a
# controller plugged in later is picked up within a couple of seconds. Started by ockm-start.sh; one copy at a time.
PIDF=/tmp/ockm-midi-connect.pid
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then exit 0; fi
echo $$ > "$PIDF"
while true; do
    # Pd's MIDI input (ALSA sequencer client "Pure Data")
    PD=$(aconnect -o 2>/dev/null | sed -n "s/^client \([0-9]*\): 'Pure Data'.*/\1/p" | head -1)
    if [ -n "$PD" ]; then
        # every hardware client (a USB device: card=) and its ports, as client:port
        aconnect -i 2>/dev/null | awk '
            /^client [0-9]+:/ { hw = ($0 ~ /card=/); c = $2; sub(":", "", c); next }
            hw && /^ +[0-9]+ / { print c ":" $1 }' |
        while read -r SRC; do
            aconnect "$SRC" "$PD:0" 2>/dev/null   # already connected: nothing happens
        done
    fi
    sleep 2
done
