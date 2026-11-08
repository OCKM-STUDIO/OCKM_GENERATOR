#!/bin/sh
# Connect every MIDI controller (USB keyboards, pad controllers, an MPC) to OCKM_GENERATOR, and every synth plugged in to
# its MIDI out (v1.40: clock, and the parts set to MIDI out in settings), and keep doing it, so a device plugged in later is
# picked up within a couple of seconds. Started by ockm-start.sh; one copy at a time.
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
        # Pd's MIDI output: its readable port (the last one Pd lists) to every hardware device's input
        OUT=$(aconnect -i 2>/dev/null | awk -v pd="$PD" '
            /^client [0-9]+:/ { c = $2; sub(":", "", c); next }
            c == pd && /^ +[0-9]+ / { p = $1 } END { if (p != "") print p }')
        if [ -n "$OUT" ]; then
            aconnect -o 2>/dev/null | awk '
                /^client [0-9]+:/ { hw = ($0 ~ /card=/); c = $2; sub(":", "", c); next }
                hw && /^ +[0-9]+ / { print c ":" $1 }' |
            while read -r DST; do
                aconnect "$PD:$OUT" "$DST" 2>/dev/null
            done
        fi
    fi
    sleep 2
done
