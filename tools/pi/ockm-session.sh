#!/bin/sh
# The Pi's login session for OCKM_GENERATOR: Raspberry Pi OS's own labwc-pi, without -m. With -m labwc merges the
# system config, so the system start-up (desktop, taskbar) runs as well as ours; without it only ~/.config/labwc is used,
# so the screen goes straight to the app (see tools/pi/labwc-autostart). Picked at login by /usr/share/wayland-sessions/ockm.desktop.
. /usr/bin/setup_env
if [ ! -f "$HOME/.config/kanshi/config" ] ; then mkdir -p "$HOME/.config/kanshi"; touch "$HOME/.config/kanshi/config"; fi
if raspi-config nonint is_pi ; then
    export WLR_DRM_FORCE_LIBLIFTOFF=1
    if ! raspi-config nonint gpu_has_mmu ; then export WLR_RENDERER=pixman; fi
fi
exec /usr/bin/labwc "$@"
