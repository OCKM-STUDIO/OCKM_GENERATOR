#!/bin/sh
# Restart the app on the Pi (after copying a new version over), without the desktop coming up: the login start-up
# (tools/pi/labwc-autostart) sees the flag and starts the app again. Run over SSH: ~/OCKM_GENERATOR/tools/pi/ockm-restart.sh
# v1.49 unsaved work survives it: first it asks the app to keep what's open ("keep;" to UDP port 3091). If there are
# unsaved changes, the app stashes them (without saving) and puts them back when it starts again.
if pgrep -x pd >/dev/null && command -v pdsend >/dev/null; then
    echo "keep;" | pdsend 3091 localhost udp 2>/dev/null
    sleep 1
fi
touch /tmp/ockm-restart
pkill -x pd
