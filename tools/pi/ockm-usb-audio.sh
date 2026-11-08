#!/bin/sh
# USB audio out (v1.48): the Pi's USB-C port, through the power/data splitter, shows up on a computer as a USB audio
# interface called "OCKM" with 9 channels coming from the box: the mix (1-2), then the kick, the rest of the drums,
# bass, lead, chords, samples and effects (3-9, one each). Run as root at start-up by ockm-usb-audio.service. Needs, in /boot/firmware/config.txt:
#   dtoverlay=dwc2,dr_mode=peripheral
# Undo: sudo systemctl disable ockm-usb-audio, and take that line out of config.txt.
set -e
G=/sys/kernel/config/usb_gadget/ockm
for i in 1 2 3 4 5 6 7 8 9 10; do [ -n "$(ls /sys/class/udc 2>/dev/null)" ] && break; sleep 1; done   # the port's driver may still be loading
modprobe libcomposite
mountpoint -q /sys/kernel/config || mount -t configfs none /sys/kernel/config
if [ -d "$G" ]; then exit 0; fi   # already made
mkdir -p "$G"
cd "$G"
echo 0x1d6b > idVendor            # Linux Foundation
echo 0x0104 > idProduct           # multifunction composite gadget
echo 0x0100 > bcdDevice
echo 0x0200 > bcdUSB
mkdir -p strings/0x409
echo "OCKM" > strings/0x409/manufacturer
echo "OCKM groovebox" > strings/0x409/product
echo "ockm-$(cat /proc/device-tree/serial-number 2>/dev/null | tr -d '\0' | tail -c 8)" > strings/0x409/serialnumber
mkdir -p configs/c.1/strings/0x409
echo "USB audio" > configs/c.1/strings/0x409/configuration
echo 250 > configs/c.1/MaxPower
mkdir -p functions/uac2.usb0
F=functions/uac2.usb0
echo 0x1ff > $F/p_chmask          # 9 channels from the Pi to the computer
echo 48000 > $F/p_srate
echo 4 > $F/p_ssize               # 32-bit samples
echo 0x3 > $F/c_chmask            # 2 channels the other way (unused; some computers want both directions)
echo 48000 > $F/c_srate
echo 4 > $F/c_ssize
[ -f $F/function_name ] && echo "OCKM" > $F/function_name || true
ln -s $F configs/c.1/
ls /sys/class/udc | head -1 > UDC
