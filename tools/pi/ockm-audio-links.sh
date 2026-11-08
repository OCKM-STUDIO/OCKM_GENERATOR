#!/bin/sh
# v1.48 Connects the box's outputs in PipeWire once Pd is up: outputs 1-2 (the mix) to the DAC, and outputs 1-8 to the
# USB audio device (the computer's inputs 1-9: mix L, mix R, kick, the rest of the drums, bass, lead, chords, samples, effects). Started by
# ockm-start.sh when USB audio is on; it keeps the links in place (every few seconds), so a cable plugged in later works.
# v1.49: the USB outputs are linked only while a computer is plugged in. Linked with nothing on the other end, the USB
# device can't run, PipeWire stops the whole graph with it, and Pd (waiting on PipeWire) freezes: no sound, no touch
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
PIDF=/tmp/ockm-audio-links.pid
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then exit 0; fi
echo $$ > "$PIDF"
while true; do
    HOST=$(cat /sys/class/udc/*/state 2>/dev/null | head -1)   # "configured" when a computer has the box as its sound card
    OUTS=$(pw-link -o 2>/dev/null | grep -E '^ockm:' | grep -viE 'midi' | sort -t_ -k2 -n)
    if [ -n "$OUTS" ]; then
        DAC=$(pw-link -i 2>/dev/null | grep -E 'soc.*sound.*:playback_F[LR]$' | sort)
        USB=$(pw-link -i 2>/dev/null | grep -E 'usb.*multichannel-output:playback_')   # listed in the device's channel order
        i=0
        for o in $OUTS; do
            i=$((i + 1))
            if [ $i -le 2 ]; then
                d=$(echo "$DAC" | sed -n "${i}p"); [ -n "$d" ] && pw-link "$o" "$d" 2>/dev/null
            fi
            u=$(echo "$USB" | sed -n "${i}p")
            if [ -n "$u" ]; then
                if [ "$HOST" = configured ]; then pw-link "$o" "$u" 2>/dev/null; else pw-link -d "$o" "$u" 2>/dev/null; fi
            fi
        done
    fi
    sleep 3
done
