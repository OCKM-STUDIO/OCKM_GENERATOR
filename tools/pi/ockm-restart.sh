#!/bin/sh
# Restart the app on the Pi (after copying a new version over), without the desktop coming up: the login start-up
# (tools/pi/labwc-autostart) sees the flag and starts the app again. Run over SSH: ~/OCKM_GENERATOR/tools/pi/ockm-restart.sh
touch /tmp/ockm-restart
pkill -x pd
