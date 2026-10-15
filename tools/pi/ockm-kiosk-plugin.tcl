# OCKM kiosk mode (Raspberry Pi only). Pd loads every *-plugin.tcl on its search path at start-up;
# this one does nothing unless OCKM_KIOSK is set, which only tools/pi/ockm-start.sh does.
# It makes the main patch fill the screen with no menu bar, and hides the Pd console.
if {[info exists ::env(OCKM_KIOSK)]} {
    proc ::ockm_kiosk {w} {
        if {![string match "OCKM_GENERATOR.pd*" [wm title $w]]} { return }
        catch {$w configure -menu ""}
        wm attributes $w -fullscreen 1
        catch {wm withdraw .pdwindow}
        # scroll to the top-left corner once the window has its size, so the screen sits exactly on the display
        after 500 [list catch [list ::ockm_kiosk_home $w]]
    }
    proc ::ockm_kiosk_home {w} {
        $w.c xview moveto 0
        $w.c yview moveto 0
        catch {$w.c configure -xscrollincrement 0 -yscrollincrement 0}
        raise $w
        focus -force $w.c
    }
    bind PatchWindow <<Loaded>> {+::ockm_kiosk %W}
    # no scrollbars on the app window: Pd adds them whenever the patch is bigger than the screen,
    # and the engine's closed subpatches sit below the 1920x1200 screen area
    if {[catch {rename ::pdtk_canvas::pdtk_canvas_getscroll ::ockm_orig_getscroll}]} { proc ::ockm_orig_getscroll {c} {} }
    proc ::pdtk_canvas::pdtk_canvas_getscroll {tkcanvas} {
        ::ockm_orig_getscroll $tkcanvas
        set w [winfo toplevel $tkcanvas]
        if {[string match "OCKM_GENERATOR.pd*" [wm title $w]]} {
            catch {pack forget $w.xscroll}
            catch {pack forget $w.yscroll}
        }
    }
    # touch: a finger jumps from place to place with no pointer movement in between. The Lua screen only hears
    # a press land and a finger lift when the pointer moves, so: report a move to the finger before each press,
    # and a move after each lift (without it, a lift is only noticed at the next tap, and single taps get lost).
    proc ::ockm_touch_wrap {} {
        if {[info commands ::ockm_orig_mouse] ne ""} { return }
        if {[catch {rename ::pdtk_canvas_mouse ::ockm_orig_mouse}]} { return }
        proc ::pdtk_canvas_mouse {tkcanvas x y b f} {
            catch {::pdtk_canvas_motion $tkcanvas $x $y 0}
            ::ockm_orig_mouse $tkcanvas $x $y $b $f
        }
        if {[catch {rename ::pdtk_canvas_mouseup ::ockm_orig_mouseup}]} { return }
        proc ::pdtk_canvas_mouseup {tkcanvas x y b {f 0}} {
            ::ockm_orig_mouseup $tkcanvas $x $y $b $f
            catch {::pdtk_canvas_motion $tkcanvas $x $y 0}
        }
    }
    ::ockm_touch_wrap
    # if Pd posts an error later, keep the console hidden behind the app
    proc ::ockm_kiosk_keep {} {
        catch {wm withdraw .pdwindow}
        foreach w [wm stackorder .] {
            if {[string match "OCKM_GENERATOR.pd*" [wm title $w]]} {
                foreach sb [list $w.xscroll $w.yscroll] { if {[winfo exists $sb] && [winfo ismapped $sb]} { catch {pack forget $sb} } }
            }
        }
        after 2000 ::ockm_kiosk_keep
    }
    after 3000 ::ockm_kiosk_keep
}
