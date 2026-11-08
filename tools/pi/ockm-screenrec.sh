#!/bin/sh
# Record the Pi's screen and the box's sound into one video (v1.49), for demos.
#   tools/pi/ockm-screenrec.sh start    starts recording (screen and sound)
#   tools/pi/ockm-screenrec.sh stop     stops, and writes exports/screen-<date-time>.mp4
# Run over SSH. Needs ffmpeg (it comes with Raspberry Pi OS) and sudo. The screen is read straight from the display
# (ffmpeg's kmsgrab: wf-recorder hangs on this setup), turned the right way up, and recorded at 1280 x 800 and 25 frames
# a second with the fastest encoder setting, so it takes as little from the sound as it can. The sound comes straight
# from what goes to the speakers (the DAC), mixed in when you stop.
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0} XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
cd "$(dirname "$0")/../.." || exit 1
T=$HOME/.cache/ockm-rec   # on the card, not /tmp: /tmp is memory (2 GB on a 4 GB Pi), so a long take would eat into what Pd needs
# How long it can go: the working files grow by about 1 GB an hour (sound 0.7, picture 0.25), the finished video about
# 0.3 GB an hour, so the card's free space is the limit (tens of hours)
case "$1" in
start)
    mkdir -p $T; rm -f $T/*
    CARD=""
    for c in /dev/dri/card*; do
        if sudo timeout 3 ffmpeg -loglevel quiet -device "$c" -f kmsgrab -i - -frames:v 1 -f null - 2>/dev/null; then CARD=$c; break; fi
    done
    [ -n "$CARD" ] || { echo "can't read the screen"; exit 1; }
    # gently: the lowest priority, two encoder threads, scaled down before it's turned round, 25 frames a second, and
    # the CPU held at full speed while it records (so the sound never waits for it to speed up: it clicked without)
    cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor > $T/governor 2>/dev/null
    echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null 2>&1
    sudo nice -n 19 ffmpeg -y -loglevel error -device "$CARD" -framerate 25 -f kmsgrab -i - \
        -vf "hwdownload,format=bgr0,scale=800:-2,transpose=2,format=yuv420p" \
        -c:v libx264 -preset ultrafast -crf 22 -threads 2 $T/screen.mp4 >$T/video.log 2>&1 &
    echo $! > $T/wf.pid
    SINK=$(pw-cli ls Node 2>/dev/null | grep -o 'alsa_output[^"]*sound[^"]*' | head -1)
    pw-record --target "$SINK" -P "{ stream.capture.sink=true }" --rate 48000 --channels 2 $T/sound.wav >$T/pw.log 2>&1 &
    echo $! > $T/pw.pid
    date +%s > $T/started
    echo "recording (screen and sound)"
    ;;
stop)
    [ -f $T/wf.pid ] || { echo "not recording"; exit 1; }
    sudo kill -INT "$(cat $T/wf.pid)" 2>/dev/null; kill -INT "$(cat $T/pw.pid)" 2>/dev/null
    sleep 2
    mkdir -p exports
    OUT="exports/screen-$(date +%Y-%m-%d-%H%M).mp4"
    ffmpeg -y -loglevel error -i $T/screen.mp4 -i $T/sound.wav -c:v copy -c:a aac -b:a 256k -shortest "$OUT"
    rm -f $T/wf.pid $T/pw.pid
    [ -f $T/governor ] && cat $T/governor | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null 2>&1
    echo "$OUT"
    ;;
*)
    echo "usage: $0 start|stop"; exit 1
    ;;
esac
