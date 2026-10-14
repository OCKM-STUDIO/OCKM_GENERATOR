--[[
OCKM_GENERATOR touchscreen UI

One object, three screens:
  perform  : play, tempo, patterns 1-8, a picture of what's playing now, length
  drums    : one drum slot at a time: its sound, its 16 steps, its level/tune/decay/sends
  synth    : one synth part at a time: key and scale, 16 steps with notes, sound and fill

It only talks to the engine through the named ockm-* hooks, and listens to the
same hooks (plus ockm-show-*) to know what to draw. It never touches the audio.

Gestures (mouse on the Mac, finger on the Pi):
  tap            press a button, cycle a step (off > on > accent > off)
  swipe sideways on the step row: next or previous block of 16 steps
  drag up/down   on a synth step: change its note.  On the tempo: change the tempo
  drag           on a slider: set it

Args: [ockm-ui <scale> <theme>]   scale 1 = 960x600 (Mac), 2 = 1920x1200 (10" Pi screen)
                                  theme dark or light

Tests drive it headless through the receive name ockm-ui-test:
  tap x y | drag x0 y0 x1 y1 | screen perform|drums|synth
]]

local ui = pd.Class:new():register("ockm-ui")

local W, H = 960, 600
local VERSION = "v0.19"   -- shown on screen, so you can tell which version plugdata has loaded

local THEMES = {
  dark  = { bg="#141414", card="#1e1e1e", off="#2a2a2a", on="#ededed", acc="#ff5a24", mute="#7a7a7a", txt="#ededed", dim="#3a3a3a" },
  light = { bg="#f4f3ef", card="#ffffff", off="#e4e2dc", on="#1a1a1a", acc="#ff4f1a", mute="#9a9890", txt="#1a1a1a", dim="#cfccc4" },
}

local SLOTS   = { "d1","d2","d3","d4","d5","d6","d7","d8" }
local SOUNDS  = { "kick","snare","clap","rim","closed hat","open hat","tom","rimshot" }
local SHORT   = { "kick","snare","clap","rim","hat","open hat","tom","rimshot" }
local SYNTHS  = { "bass","lead","chord" }
local TRACKS  = { "d1","d2","d3","d4","d5","d6","d7","d8","bass","lead","chord" }
local NOTES   = { "C","C#","D","D#","E","F","F#","G","G#","A","A#","B" }
local SCALES  = { {0,2,3,5,7,8,10}, {0,2,4,5,7,9,11}, {0,2,3,5,7,9,10}, {0,1,3,5,7,8,10}, {0,2,4,5,7,9,10}, {0,2,3,5,7,8,11} }
local SCALE_NAMES = { "minor","major","dorian","phrygian","mixo","harm min" }
local MONO_ENG  = { "acid","sub","fm","reese","pluck","saw" }
local CHORD_ENG = { "stab","organ","pad" }
local KNOBS = {
  acid  = {"cutoff","resonance","env amount","decay"},
  sub   = {"tone","drive","pitch drop","decay"},
  fm    = {"brightness","ratio","env","decay"},
  reese = {"cutoff","detune","env amount","decay"},
  pluck = {"brightness","saw-square","snap","decay"},
  saw   = {"tone","detune","sub","decay"},
  stab  = {"brightness","detune","snap","length"},
  organ = {"drawbars","click","sub","length"},
  pad   = {"brightness","detune","attack","length"},
}
-- BEGIN PRESETS (written by tools/build.py from its preset lists: edit them there, not here)
local RHYTHMS = { { "offbeat" }, { "rolling" }, { "gallop" }, { "acid classic" }, { "sparse dub" }, { "tech bounce" }, { "acid 16ths" }, { "trip hop" } }
local MONO_NOTES = { "root", "octaves", "root fifth", "acid riff", "walk up", "minor stab", "dub", "pedal", "arp up", "arp updown", "call", "descend" }
local CHORD_RHY = { { "bar pads" }, { "two beat" }, { "offbeat" }, { "dub stabs" }, { "house organ" }, { "tresillo" }, { "syncopated" }, { "garage skip" }, { "call answer" }, { "eighths" } }
local PROGS = { { "one chord", "i" }, { "vamp", "i iv" }, { "dub techno", "i . . VII" }, { "deep house", "i iv VI v" }, { "garage", "i VI iv v" }, { "pop", "i VI III VII" }, { "uplift", "VI VII i" }, { "andalusian", "i VII VI V" }, { "trip hop", "i VII VI v" }, { "soul", "ii V I" } }
local SPICE = { { 0, "triad" }, { 1, "7th" }, { 6, "9th" }, { 7, "11th" } }
-- END PRESETS
local ROMAN = { "i","ii","iii","iv","v","vi","vii" }
local OCT_OFFSET = { bass = 0, lead = 24 }   -- matches ockm-monogen args

local DRUM_PARAMS = {
  { "level", 0, 1 }, { "tune", -12, 12 }, { "decay", 10, 400 }, { "verb", 0, 1, "reverb" }, { "delay", 0, 1 },
}

-- ------------------------------------------------------------------ helpers
local function hex(c)
  return tonumber(c:sub(2,3),16), tonumber(c:sub(4,5),16), tonumber(c:sub(6,7),16)
end
local function clamp(v, lo, hi) if v < lo then return lo elseif v > hi then return hi end return v end
local function inside(w, x, y) return x >= w.x and x < w.x + w.w and y >= w.y and y < w.y + w.h end
local function fmt(v)
  if math.abs(v - math.floor(v + 0.5)) < 0.001 then return tostring(math.floor(v + 0.5)) end
  return string.format("%.2f", v)
end

-- ------------------------------------------------------------------ object
function ui:initialize(sel, atoms)
  self.inlets, self.outlets = 0, 0
  self.s = tonumber(atoms[1]) or 1
  self.theme = THEMES[atoms[2]] or THEMES.dark
  self.v = {}                 -- every hook value we know about
  self.screen = "perform"
  self.slot = 1               -- open drum slot
  self.part = 1               -- open synth part
  self.perf_part = 1          -- synth on the perform screen's sound strip
  self.sel_step = 0           -- selected synth step (on the current block)
  self.page = 0
  self.step = 0
  self.playing = 0
  self.cur = 0                -- pattern slot playing
  self.want = nil             -- pattern slot queued
  self.tables = {}
  self:defaults()
  self:set_size(W * self.s, H * self.s)
  return true
end

function ui:defaults()
  local v = self.v
  v["ockm-chord-smooth"] = 1
  v["ockm-volume"] = 1; v["ockm-verb-mix"] = 0.5; v["ockm-delay-mix"] = 0.5
  v["ockm-drive"] = 0; v["ockm-delay-fb"] = 0.4; v["ockm-delay-steps"] = 3; v["ockm-verb-size"] = 0.6; v["ockm-verb-tone"] = 0.5
  for _, t in ipairs(SYNTHS) do v["ockm-"..t.."-level"] = 1 end
  v["ockm-bass-mode"] = 0; v["ockm-lead-mode"] = 1; v["ockm-chord-mode"] = 0   -- 0 auto, 1 manual
  v["ockm-bass-sync"] = 1; v["ockm-lead-sync"] = 0
  v["ockm-bpm"] = 124; v["ockm-len"] = 16; v["ockm-filter"] = 0; v["ockm-root"] = 9; v["ockm-scale"] = 0
  for i, nm in ipairs(SLOTS) do
    v["ockm-"..nm.."-sound"] = ({0,1,2,4,5,7,3,6})[i]
    v["ockm-"..nm.."-level"] = 1; v["ockm-"..nm.."-tune"] = 0; v["ockm-"..nm.."-decay"] = 100
    v["ockm-"..nm.."-verb"] = 0; v["ockm-"..nm.."-delay"] = 0
  end
  for _, t in ipairs(SYNTHS) do
    for _, k in ipairs({"engine","k1","k2","k3","k4","drive","verb","delay","rhythm","notes","type","prog"}) do v["ockm-"..t.."-"..k] = 0 end
  end
end

function ui:hooks()
  local h = { "ockm-bpm","ockm-len","ockm-root","ockm-scale","ockm-filter" }
  for _, nm in ipairs(SLOTS) do
    for _, p in ipairs(DRUM_PARAMS) do h[#h+1] = "ockm-"..nm.."-"..p[1] end
    h[#h+1] = "ockm-"..nm.."-sound"
  end
  for _, t in ipairs({"bass","lead"}) do
    for _, k in ipairs({"engine","k1","k2","k3","k4","drive","verb","delay","rhythm","notes"}) do h[#h+1] = "ockm-"..t.."-"..k end
  end
  for _, k in ipairs({"engine","k1","k2","k3","k4","type","smooth","verb","delay","rhythm","prog"}) do h[#h+1] = "ockm-chord-"..k end
  for _, t in ipairs(TRACKS) do h[#h+1] = "ockm-"..t.."-mute"; h[#h+1] = "ockm-"..t.."-solo" end
  for _, t in ipairs(SYNTHS) do h[#h+1] = "ockm-"..t.."-level"; h[#h+1] = "ockm-"..t.."-mode" end
  h[#h+1] = "ockm-bass-sync"; h[#h+1] = "ockm-lead-sync"
  for _, k in ipairs({ "ockm-volume", "ockm-verb-mix", "ockm-delay-mix", "ockm-drive", "ockm-delay-fb", "ockm-delay-steps", "ockm-verb-size", "ockm-verb-tone" }) do h[#h+1] = k end
  return h
end

function ui:postinitialize()
  self.recv = {}
  local function listen(name, fn)
    local m = "r_" .. #self.recv
    self[m] = fn
    self.recv[#self.recv + 1] = pd.Receive:new():register(self, name, m)
  end
  for _, hook in ipairs(self:hooks()) do
    local function set(o, sel, atoms)
      local x = (sel == "float" or sel == "set" or sel == "list") and tonumber(atoms[1]) or nil
      if x then o.v[hook] = x; o:dirty() end
    end
    listen(hook, set)
    listen("ockm-show-" .. hook:sub(6), set)
  end
  listen("ockm-playing", function(o, sel, a) o.playing = tonumber(a[1]) or 0; o:dirty() end)
  listen("ockm-load",    function(o, sel, a) o.cur = math.floor(tonumber(a[1]) or 0); o.want = nil; o:dirty() end)
  listen("ockm-want",    function(o, sel, a)
    local n = tonumber(a[1]); if n and (o.playing ~= 0) and n ~= o.cur then o.want = n end; o:dirty() end)
  listen("ockm-page",    function(o, sel, a) o.page = math.floor(tonumber(a[1]) or 0); o:dirty() end)
  listen("ockm-step",    function(o, sel, a) o:on_step(math.floor(tonumber(a[1]) or 0)) end)
  for _, n in ipairs({ "ockm-refresh","ockm-edit","ockm-extend","ockm-bass-edit","ockm-lead-edit","ockm-chord-edit",
                       "ockm-bass-gen","ockm-lead-gen","ockm-chord-gen" }) do
    listen(n, function(o) o:dirty() end)
  end
  listen("ockm-ui-test", function(o, sel, a) o:test(sel, a) end)
  self.clock = pd.Clock:new():register(self, "redraw")
  self.msgclock = pd.Clock:new():register(self, "clear_msg")
end

function ui:finalize()
  for _, r in ipairs(self.recv or {}) do r:destruct() end
  if self.clock then self.clock:destruct() end
  if self.msgclock then self.msgclock:destruct() end
  for _, t in pairs(self.tables) do if t.destruct then t:destruct() end end
end

-- one repaint for a burst of changes
function ui:dirty() if self.clock then self.clock:delay(5) end end
-- a short message under the steps, gone after a few seconds
function ui:say(text) self.msg = text; if self.msgclock then self.msgclock:delay(4000) end; self:dirty() end
function ui:clear_msg() self.msg = nil; self:repaint() end
-- the camera's manual mode: editing a step in auto hands the part over to you
function ui:to_manual()
  local part = SYNTHS[self.part]
  if (self.v["ockm-"..part.."-mode"] or 0) == 0 then
    self:send("ockm-"..part.."-mode", 1)
    self:say(part .. " is now manual: your edits stay put. Tap auto to hand it back to the generator")
  end
end
function ui:redraw() self:repaint() end

function ui:on_step(n)
  local old = math.floor(self.step / 16)
  self.step = n
  if math.floor(n / 16) ~= old then self:repaint() else self:repaint(2) end
end

-- ------------------------------------------------------------------ data
function ui:tab(name)
  local t = self.tables[name]
  if not t then t = pd.Table:new(); self.tables[name] = t end
  if t:sync(name) then return t end
  return nil
end
function ui:get(name, i)
  local t = self:tab(name)
  if t and i < t:length() then return t:get(i) or 0 end
  return 0
end
function ui:blocks() return math.max(1, math.ceil((self.v["ockm-len"] or 16) / 16)) end
function ui:play_block() return math.floor(self.step / 16) end
function ui:set_page(p)
  p = clamp(math.floor(p), 0, self:blocks() - 1)
  self.page = p
  pd.send("ockm-page", "float", { p })
end

function ui:send(hook, x)
  self.v[hook] = x
  pd.send(hook, "float", { x })
  self:dirty()
end

-- mono notes: base MIDI note for degree 0, matching ockm-monogen
function ui:mono_base(part)
  local r = self.v["ockm-root"] or 9
  local b = (36 + r > 40) and (24 + r) or (36 + r)
  return b + (OCT_OFFSET[part] or 0)
end
function ui:scale() return SCALES[(self.v["ockm-scale"] or 0) + 1] or SCALES[1] end
function ui:deg_to_midi(part, d)
  local sc = self:scale()
  local o = math.floor(d / 7)
  return self:mono_base(part) + sc[(d % 7) + 1] + 12 * o
end
function ui:midi_to_deg(part, m)
  local sc = self:scale()
  local rel = m - self:mono_base(part)
  local o = math.floor(rel / 12)
  local pc = rel % 12
  local idx = 0
  for i = 1, 7 do if sc[i] <= pc then idx = i - 1 end end
  return idx + 7 * o
end
function ui:note_name(m) return NOTES[(math.floor(m) % 12) + 1] end

-- ------------------------------------------------------------------ layout
-- A screen is a list of widgets. Paint and touch both use the same list.
function ui:layout()
  local L = {}
  local function add(w) L[#L+1] = w; return w end
  self:layout_top(add)
  if self.screen == "perform" then self:layout_perform(add)
  elseif self.screen == "drums" then self:layout_drums(add)
  elseif self.screen == "mixer" then self:layout_mixer(add)
  else self:layout_synth(add) end
  return L
end

-- Screen hierarchy, top to bottom:
--   1. top bar: play, tempo, the six screens as tabs, save and revert
--   2. navigation strip: pattern, length, which block of 16 steps
--   3. what you're editing (drum slot tabs on the drums screen), then the steps
--   4. sound shaping at the bottom
local TABS = { { "perform", "perform" }, { "drums", "drums" }, { "synth", "bass", 1 }, { "synth", "lead", 2 }, { "synth", "chord", 3 }, { "mixer", "mixer" } }
local NAV_Y, NAV_H = 70, 36
function ui:layout_top(add)
  add{ kind="play", x=16, y=12, w=64, h=48, tap=function() self:send("ockm-play", self.playing ~= 0 and 0 or 1) end }
  add{ kind="bpm", x=92, y=12, w=140, h=48 }
  for i, t in ipairs(TABS) do
    local sel = (self.screen == t[1]) and (t[3] == nil or t[3] == self.part)
    add{ kind="tab", x=244 + (i - 1) * 92, y=12, w=86, h=48, label=t[2], sel=sel, tap=function()
      if t[3] then
        if self.part ~= t[3] then self.part = t[3]; self.sel_step = 0; self.msg = nil end
      end
      if self.screen ~= t[1] then self:open(t[1]) end
    end }
  end
  add{ kind="btn", x=W - 144, y=12, w=62, h=48, label="save", quiet=true, tap=function() pd.send("ockm-save", "bang", {}) end }
  add{ kind="btn", x=W - 78, y=12, w=62, h=48, label="revert", quiet=true, tap=function() pd.send("ockm-revert", "bang", {}) end }
  self:layout_nav(add)
end

-- the navigation strip: pattern 1-8, length, and the blocks of 16 steps (only as many as the length allows)
function ui:layout_nav(add)
  local y, h = NAV_Y, NAV_H
  add{ kind="text", x=16, y=y + 12, w=60, h=12, label="pattern", size=10 }
  for i = 0, 7 do
    add{ kind="pattern", x=66 + i * 34, y=y, w=30, h=h, n=i, tap=function()
      pd.send("ockm-want", "float", { i })
      if self.playing ~= 0 and i ~= self.cur then self.want = i end
    end }
  end
  add{ kind="text", x=354, y=y + 12, w=50, h=12, label="length", size=10 }
  for i, n in ipairs({ 16, 32, 64, 128 }) do
    add{ kind="choice", x=398 + (i - 1) * 44, y=y, w=40, h=h, label=tostring(n), small=true,
         sel=(self.v["ockm-len"] == n), tap=function() pd.send("ockm-length", "float", { n }) end }
  end
  add{ kind="text", x=584, y=y + 12, w=50, h=12, label="steps", size=10 }
  -- back, the steps you're looking at, forward
  local n = self:blocks()
  add{ kind="arrow", x=622, y=y, w=48, h=h, dir=-1, on=(self:shown_block() > 0), tap=function() self:set_page(self:shown_block() - 1) end }
  add{ kind="steps", x=676, y=y, w=W - 16 - 676 - 54, h=h }
  add{ kind="arrow", x=W - 16 - 48, y=y, w=48, h=h, dir=1, on=(self:shown_block() < n - 1), tap=function() self:set_page(self:shown_block() + 1) end }
end

-- the block on screen: perform follows the playhead while playing, the edit screens stay where you put them
function ui:shown_block()
  if self.screen == "perform" and self.playing ~= 0 then return clamp(self:play_block(), 0, self:blocks() - 1) end
  return clamp(self.page, 0, self:blocks() - 1)
end

local LANE_Y, LANE_H, LANE_P, LANE_X = 124, 26, 28, 192
function ui:lane_y(i) return LANE_Y + (i - 1) * LANE_P + ((i > 8) and 8 or 0) end

function ui:layout_perform(add)
  -- now: 8 drum lanes and 3 synth lanes, a picture of the block that is playing. Tap a name to open it
  for i = 1, 11 do
    local isdrum = i <= 8
    local y = self:lane_y(i)
    local name = isdrum and SHORT[(self.v["ockm-"..SLOTS[i].."-sound"] or 0) + 1] or SYNTHS[i - 8]
    local tr = TRACKS[i]
    add{ kind="ms", x=108, y=y, w=36, h=LANE_H, label="M", hook="ockm-"..tr.."-mute" }
    add{ kind="ms", x=148, y=y, w=36, h=LANE_H, label="S", hook="ockm-"..tr.."-solo" }
    add{ kind="lanename", x=16, y=y, w=88, h=LANE_H, label=name, tap=function()
      if isdrum then self.slot = i; self:open("drums") else self.part = i - 8; self:open("synth") end
    end }
    add{ kind="lane", x=LANE_X, y=y, w=W - LANE_X - 16, h=LANE_H, track=i }
  end
  -- bottom: the chosen synth's four main knobs on the left, master effects on the right (the way the sound flows)
  local half = (W - 32 - 16) / 2
  local lx, rx = 16, 16 + half + 16
  add{ kind="text", x=rx, y=441, w=200, h=10, label="master fx", size=9 }
  local MFX = { { "ockm-filter", -1, 1, "filter" }, { "ockm-drive", 0, 1, "drive" }, { "ockm-delay-mix", 0, 1, "delay" }, { "ockm-delay-fb", 0, 0.9, "feedback" },
                { "ockm-delay-steps", 1, 8, "time" }, { "ockm-verb-mix", 0, 1, "reverb" }, { "ockm-verb-size", 0, 1, "size" }, { "ockm-verb-tone", 0, 1, "tone" } }
  local mw = (half - 3 * 6) / 4
  for i, m in ipairs(MFX) do
    local col, row = (i - 1) % 4, math.floor((i - 1) / 4)
    add{ kind="hbar", x=rx + col * (mw + 6), y=456 + row * 68, w=mw, h=60, hook=m[1], lo=m[2], hi=m[3], label=m[4], bold=true }
  end
  local part = SYNTHS[self.perf_part or 1]
  local tw = (half - 2 * 6) / 3
  for i, t in ipairs(SYNTHS) do
    add{ kind="choice", x=lx + (i - 1) * (tw + 6), y=452, w=tw, h=30, label=t, small=true, sel=((self.perf_part or 1) == i),
         tap=function() self.perf_part = i end }
  end
  local eng = (part == "chord") and CHORD_ENG or MONO_ENG
  local kn = KNOBS[eng[(self.v["ockm-"..part.."-engine"] or 0) + 1]] or KNOBS.acid
  local kw = (half - 6) / 2
  for k = 1, 4 do
    local col, row = (k - 1) % 2, math.floor((k - 1) / 2)
    add{ kind="hbar", x=lx + col * (kw + 6), y=490 + row * 52, w=kw, h=46, hook="ockm-"..part.."-k"..k, lo=0, hi=1, label=kn[k], bold=true }
  end
end

function ui:open(screen)
  self.msg = nil
  self.screen = screen
  self.sel_step = 0
  self:set_page(self:play_block())
end

local D_STEP_Y, D_STEP_H = 166, 92      -- drums screen step pads
local S_STEP_Y, S_STEP_H = 116, 84      -- synth screens step pads

function ui:step_row(add, y, h, kind)
  local pitch = (W - 32) / 16
  add{ kind="steprow", x=0, y=y - 8, w=W, h=h + 16, swipe=true }   -- swipe anywhere along the row
  for i = 0, 15 do
    add{ kind=kind, x=16 + i * pitch + 3, y=y, w=pitch - 6, h=h, i=i, swipe=true }
  end
end

function ui:layout_drums(add)
  local nm = SLOTS[self.slot]
  local tw = (W - 32 - 7 * 8) / 8
  -- which drum: the 8 slots, named by their sound
  for i = 1, 8 do
    add{ kind="choice", x=16 + (i - 1) * (tw + 8), y=114, w=tw, h=40,
         label=SHORT[(self.v["ockm-"..SLOTS[i].."-sound"] or 0) + 1], sel=(i == self.slot), tap=function() self.slot = i end }
  end
  self:step_row(add, D_STEP_Y, D_STEP_H, "dstep")
  -- sound shaping
  add{ kind="text", x=16, y=276, w=200, h=12, label="sound", size=10 }
  for s = 0, 7 do
    add{ kind="choice", x=16 + s * (tw + 8), y=290, w=tw, h=44, label=SOUNDS[s + 1], accent=true,
         sel=(self.v["ockm-"..nm.."-sound"] == s), tap=function() self:send("ockm-"..nm.."-sound", s) end }
  end
  for j, p in ipairs(DRUM_PARAMS) do
    add{ kind="slider", x=16, y=350 + (j - 1) * 46, w=W - 32, h=36, hook="ockm-"..nm.."-"..p[1], lo=p[2], hi=p[3], label=p[4] or p[1] }
  end
end

function ui:layout_synth(add)
  local part = SYNTHS[self.part]
  local mono = part ~= "chord"
  self:step_row(add, S_STEP_Y, S_STEP_H, mono and "mstep" or "cstep")
  -- note (or chord) for the selected step
  if mono then
    local bw = (W - 32) / 15
    for d = -7, 7 do
      add{ kind="deg", x=16 + (d + 7) * bw + 2, y=216, w=bw - 4, h=40, d=d, tap=function() self:mono_set_deg(d) end }
    end
  else
    local bw = (W - 32) / 7
    for d = 0, 6 do
      add{ kind="deg", x=16 + d * bw + 3, y=216, w=bw - 6, h=40, d=d, tap=function() self:chord_set_deg(d) end }
    end
  end
  -- key and scale (shared by all three synths), slide for the selected step
  for k = 0, 11 do
    add{ kind="choice", x=16 + k * 36, y=266, w=33, h=34, label=NOTES[k + 1], small=true, sel=(self.v["ockm-root"] == k),
         tap=function() self:send("ockm-root", k) end }
  end
  for sc = 0, 5 do
    add{ kind="choice", x=456 + sc * 64, y=266, w=60, h=34, label=SCALE_NAMES[sc + 1], small=true, sel=(self.v["ockm-scale"] == sc),
         tap=function() self:send("ockm-scale", sc) end }
  end
  if mono then
    add{ kind="choice", x=W - 102, y=266, w=86, h=34, label="slide", accent=true, small=true, sel=self:mono_get(self.sel_step, "slide") > 0,
         tap=function() self:mono_toggle_slide() end }
  end
  -- sound shaping underneath: sound or fill
  local view = self.synth_view or "sound"
  add{ kind="tab", x=16, y=312, w=110, h=32, label="sound", sel=(view == "sound"), tap=function() self.synth_view = "sound" end }
  add{ kind="tab", x=132, y=312, w=110, h=32, label="fill", sel=(view == "fill"), tap=function() self.synth_view = "fill" end }
  add{ kind="text", x=260, y=322, w=470, h=12, label=self.msg or self:step_info(), size=11, col=self.msg and "acc" or nil }
  local mkey = "ockm-"..part.."-mode"
  local manual = (self.v[mkey] or 0) > 0
  add{ kind="choice", x=W - 16 - 180, y=312, w=88, h=32, label="auto", small=true, sel=not manual, tap=function()
    if manual then self:send(mkey, 0); pd.send("ockm-"..part.."-gen", "bang", {}); self:say(part .. " is back on auto") end
  end }
  add{ kind="choice", x=W - 16 - 88, y=312, w=88, h=32, label="manual", small=true, sel=manual, tap=function()
    if not manual then self:send(mkey, 1) end
  end }
  if view == "sound" then self:layout_synth_sound(add, part, mono) else self:layout_synth_fill(add, part, mono) end
end

function ui:layout_synth_sound(add, part, mono)
  local eng = mono and MONO_ENG or CHORD_ENG
  local ew = (W - 32) / #eng
  for e = 0, #eng - 1 do
    add{ kind="choice", x=16 + e * ew, y=356, w=ew - 6, h=40, label=eng[e + 1], sel=(self.v["ockm-"..part.."-engine"] == e),
         tap=function() self:send("ockm-"..part.."-engine", e) end }
  end
  local kn = KNOBS[eng[(self.v["ockm-"..part.."-engine"] or 0) + 1]] or KNOBS.acid
  local cw = (W - 32 - 16) / 2
  for k = 1, 4 do
    local col, row = (k - 1) % 2, math.floor((k - 1) / 2)
    add{ kind="slider", x=16 + col * (cw + 16), y=410 + row * 46, w=cw, h=36, hook="ockm-"..part.."-k"..k, lo=0, hi=1, label=kn[k] }
  end
  local third = {}
  if mono then third[#third + 1] = { "drive", "drive" } end
  third[#third + 1] = { "verb", "reverb" }; third[#third + 1] = { "delay", "delay" }
  local tw = (W - 32 - 16 * (#third - 1)) / #third
  for j, t in ipairs(third) do
    add{ kind="slider", x=16 + (j - 1) * (tw + 16), y=510, w=tw, h=36, hook="ockm-"..part.."-"..t[1], lo=0, hi=1, label=t[2] }
  end
  add{ kind="slider", x=16, y=556, w=cw, h=36, hook="ockm-"..part.."-level", lo=0, hi=1, label="level" }
end

-- a row of numbered presets: big number, name underneath
function ui:preset_row(add, y, h, list, hook, label)
  add{ kind="text", x=16, y=y - 14, w=200, h=12, label=label, size=10 }
  local n = #list
  local bw = (W - 32) / n
  for i = 0, n - 1 do
    local item = list[i + 1]
    add{ kind="preset", x=16 + i * bw, y=y, w=bw - 6, h=h, num=i + 1, label=item[1], sub=item[2],
         sel=(self.v[hook] == i), tap=function() self:send(hook, i) end }
  end
end

function ui:layout_synth_fill(add, part, mono)
  if mono then
    self:preset_row(add, 370, 60, RHYTHMS, "ockm-"..part.."-rhythm", "rhythm")
    local list = {}
    for i, nm in ipairs(MONO_NOTES) do list[i] = { nm } end
    self:preset_row(add, 456, 48, list, "ockm-"..part.."-notes", "notes")
    local skey = "ockm-"..part.."-sync"
    add{ kind="choice", x=W - 136 - 186, y=530, w=176, h=56, label="follow chords", accent=true, sel=(self.v[skey] or 0) > 0,
         tap=function()
           self:send(skey, ((self.v[skey] or 0) > 0) and 0 or 1)
           -- a part in auto regenerates to follow (or stop following); a manual part keeps your notes
           if (self.v["ockm-"..part.."-mode"] or 0) == 0 then pd.send("ockm-"..part.."-gen", "bang", {}) end
         end }
    add{ kind="btn", x=W - 136, y=530, w=120, h=56, label="new", accent=true,
         tap=function() pd.send("ockm-"..part.."-gen", "bang", {}); self:dirty() end }
    return
  end
  -- chords: progression, rhythm, spice. Picking a progression or rhythm rewrites the chord part straight away
  self:preset_row(add, 370, 58, PROGS, "ockm-chord-prog", "progression")
  self:preset_row(add, 456, 44, CHORD_RHY, "ockm-chord-rhythm", "rhythm")
  add{ kind="text", x=16, y=528, w=200, h=12, label="spice", size=10 }
  for i, sp in ipairs(SPICE) do
    add{ kind="preset", x=16 + (i - 1) * 118, y=542, w=112, h=44, num=i, label=sp[2], inline=true,
         sel=(self.v["ockm-chord-type"] == sp[1]), tap=function() self:send("ockm-chord-type", sp[1]) end }
  end
  add{ kind="choice", x=500, y=542, w=150, h=44, label="smooth", accent=true, sel=(self.v["ockm-chord-smooth"] or 1) > 0,
       tap=function() self:send("ockm-chord-smooth", ((self.v["ockm-chord-smooth"] or 1) > 0) and 0 or 1) end }
  add{ kind="btn", x=W - 136, y=542, w=120, h=44, label="new", accent=true,
       tap=function() pd.send("ockm-chord-gen", "bang", {}); self:dirty() end }
end

-- ------------------------------------------------------------------ mute, solo, mixer
function ui:soloing()
  for _, t in ipairs(TRACKS) do if (self.v["ockm-"..t.."-solo"] or 0) > 0 then return true end end
  return false
end
function ui:silent(t)
  if (self.v["ockm-"..t.."-mute"] or 0) > 0 then return true end
  return self:soloing() and (self.v["ockm-"..t.."-solo"] or 0) <= 0
end
function ui:track_name(i)
  if i <= 8 then return SHORT[(self.v["ockm-"..SLOTS[i].."-sound"] or 0) + 1] end
  return SYNTHS[i - 8]
end

-- one channel strip per track, plus master: sends on top, level fader, mute and solo
function ui:layout_mixer(add)
  local n = #TRACKS + 1
  local sw = (W - 32) / n
  local top = 116
  for i = 1, n do
    local x = 16 + (i - 1) * sw
    local cx, cw = x + 3, sw - 6
    if i <= #TRACKS then
      local t = TRACKS[i]
      add{ kind="strip", x=x, y=top, w=sw - 2, h=H - top - 8, label=self:track_name(i), silent=self:silent(t) }
      add{ kind="stripname", x=x, y=top, w=sw - 2, h=32,     -- tap the name to open that track
           tap=function() if i <= 8 then self.slot = i; self:open("drums") else self.part = i - 8; self:open("synth") end end }
      add{ kind="hbar", x=cx, y=top + 34, w=cw, h=26, hook="ockm-"..t.."-verb", lo=0, hi=1, label="rev" }
      add{ kind="hbar", x=cx, y=top + 66, w=cw, h=26, hook="ockm-"..t.."-delay", lo=0, hi=1, label="dly" }
      add{ kind="vfader", x=cx, y=top + 100, w=cw, h=250, hook="ockm-"..t.."-level", lo=0, hi=1 }
      add{ kind="ms", x=cx, y=top + 364, w=cw, h=50, label="M", hook="ockm-"..t.."-mute" }
      add{ kind="ms", x=cx, y=top + 420, w=cw, h=50, label="S", hook="ockm-"..t.."-solo" }
    else
      add{ kind="strip", x=x, y=top, w=sw - 2, h=H - top - 8, label="master", master=true }
      add{ kind="hbar", x=cx, y=top + 34, w=cw, h=26, hook="ockm-verb-mix", lo=0, hi=1, label="rev" }
      add{ kind="hbar", x=cx, y=top + 66, w=cw, h=26, hook="ockm-delay-mix", lo=0, hi=1, label="dly" }
      add{ kind="vfader", x=cx, y=top + 100, w=cw, h=250, hook="ockm-volume", lo=0, hi=1, master=true }
      add{ kind="btn", x=cx, y=top + 364, w=cw, h=106, label="clear", quiet=true, tap=function()
        for _, t in ipairs(TRACKS) do
          if (self.v["ockm-"..t.."-mute"] or 0) > 0 then self:send("ockm-"..t.."-mute", 0) end
          if (self.v["ockm-"..t.."-solo"] or 0) > 0 then self:send("ockm-"..t.."-solo", 0) end
        end
      end }
    end
  end
end

-- ------------------------------------------------------------------ step edits
function ui:abs(i) return self.page * 16 + i end

function ui:drum_tap(i)
  local nm = SLOTS[self.slot]
  local v = self:get("ockm-pat-"..nm, self:abs(i))
  local nv = (v <= 0) and 1 or ((v < 2) and 2 or 0)
  pd.send("ockm-edit", nm, { self:abs(i), nv })
  self:dirty()
end

function ui:mono_get(i, f) return self:get("ockm-pat-"..SYNTHS[self.part].."-"..f, self:abs(i)) end
function ui:mono_write(i, note, on, acc, slide)
  self:to_manual()
  local part = SYNTHS[self.part]
  pd.send("ockm-"..part.."-edit", "list", { self:abs(i), note, on, acc, slide })
  self:dirty()
end
function ui:mono_note_or_default(i)
  local n = self:mono_get(i, "note")
  if n <= 0 then n = self:deg_to_midi(SYNTHS[self.part], 0) end
  return n
end
function ui:mono_tap(i)
  self.sel_step = i
  local on, acc = self:mono_get(i, "on"), self:mono_get(i, "acc")
  local n_on, n_acc
  if on <= 0 then n_on, n_acc = 1, 0 elseif acc <= 0 then n_on, n_acc = 1, 1 else n_on, n_acc = 0, 0 end
  self:mono_write(i, self:mono_note_or_default(i), n_on, n_acc, self:mono_get(i, "slide"))
end
function ui:mono_set_deg(d)
  local i = self.sel_step
  local on = self:mono_get(i, "on")
  self:mono_write(i, self:deg_to_midi(SYNTHS[self.part], d), (on > 0) and on or 1, self:mono_get(i, "acc"), self:mono_get(i, "slide"))
end
function ui:mono_toggle_slide()
  local i = self.sel_step
  self:mono_write(i, self:mono_note_or_default(i), self:mono_get(i, "on"), self:mono_get(i, "acc"),
                  (self:mono_get(i, "slide") > 0) and 0 or 1)
end

function ui:chord_get(i, f) return self:get("ockm-pat-chord-"..f, self:abs(i)) end
function ui:chord_tap(i)
  self:to_manual()
  self.sel_step = i
  local v = self:chord_get(i, "on")
  local nv = (v <= 0) and 1 or ((v < 2) and 2 or 0)
  pd.send("ockm-chord-edit", "list", { self:abs(i), nv, self:chord_get(i, "deg") })
  self:dirty()
end
function ui:chord_set_deg(d)
  self:to_manual()
  local i = self.sel_step
  local v = self:chord_get(i, "on")
  pd.send("ockm-chord-edit", "list", { self:abs(i), (v > 0) and v or 1, d })
  self:dirty()
end

function ui:step_info()
  local i = self.sel_step
  local s = string.format("step %d", math.floor(self:abs(i) + 1))
  if SYNTHS[self.part] == "chord" then
    if self:chord_get(i, "on") > 0 then s = s .. "   chord " .. (ROMAN[(math.floor(self:chord_get(i, "deg")) % 7) + 1]) end
  elseif self:mono_get(i, "on") > 0 then
    local m = self:mono_get(i, "note")
    s = s .. "   " .. self:note_name(m) .. (math.floor(m / 12) - 1)
  end
  return s
end

-- ------------------------------------------------------------------ touch
function ui:hit(x, y)
  local L = self:layout()
  for k = #L, 1, -1 do
    local w = L[k]
    if inside(w, x, y) and (w.tap or w.swipe or w.kind == "slider" or w.kind == "bpm" or w.kind == "vfader" or w.kind == "hbar" or w.kind == "ms"
       or w.kind == "dstep" or w.kind == "mstep" or w.kind == "cstep") then return w end
  end
  return nil
end

function ui:press(x, y)
  local w = self:hit(x, y)
  self.touch = { w = w, x0 = x, y0 = y, mode = nil }
  if not w then return end
  if w.kind == "slider" or w.kind == "vfader" or w.kind == "hbar" then self.touch.mode = "slider"; self:slide(w, x, y)
  elseif w.kind == "bpm" then self.touch.mode = "bpm"; self.touch.v0 = self.v["ockm-bpm"] or 124
  elseif w.kind == "mstep" or w.kind == "cstep" then
    self.touch.v0 = (w.kind == "mstep") and self:midi_to_deg(SYNTHS[self.part], self:mono_note_or_default(w.i))
                                         or math.floor(self:chord_get(w.i, "deg"))
  end
end

function ui:slide(w, x, y)
  local f
  if w.kind == "vfader" then f = clamp(1 - (y - w.y - 8) / (w.h - 16), 0, 1)
  elseif w.kind == "hbar" then f = clamp((x - w.x) / w.w, 0, 1)
  else f = clamp((x - (w.x + 110)) / (w.w - 180), 0, 1) end
  local v = w.lo + f * (w.hi - w.lo)
  if w.hi - w.lo > 4 then v = math.floor(v + 0.5) else v = math.floor(v * 100 + 0.5) / 100 end
  self:send(w.hook, v)
end

function ui:move(x, y)
  local t = self.touch
  if not t or not t.w then return end
  local dx, dy = x - t.x0, y - t.y0
  if t.mode == "slider" then self:slide(t.w, x, y); return end
  if t.mode == "bpm" then
    self:send("ockm-bpm", clamp(math.floor(t.v0 - dy / 3 + 0.5), 40, 200)); return
  end
  if t.mode == nil and (math.abs(dx) > 24 or math.abs(dy) > 16) then
    if t.w.swipe and math.abs(dx) > math.abs(dy) then t.mode = "swipe"
    elseif (t.w.kind == "mstep" or t.w.kind == "cstep") and math.abs(dy) > math.abs(dx) then t.mode = "note"
    else t.mode = "cancel" end
  end
  if t.mode == "note" then
    local d = t.v0 - math.floor(dy / 18 + 0.5)
    self.sel_step = t.w.i
    if t.w.kind == "mstep" then
      d = clamp(d, -7, 14)
      if d ~= t.last then
        t.last = d
        local i = t.w.i
        local on = self:mono_get(i, "on")
        self:mono_write(i, self:deg_to_midi(SYNTHS[self.part], d), (on > 0) and on or 1, self:mono_get(i, "acc"), self:mono_get(i, "slide"))
      end
    else
      d = clamp(d, 0, 6)
      if d ~= t.last then t.last = d; self:chord_set_deg(d) end
    end
  end
end

function ui:release(x, y)
  local t = self.touch
  self.touch = nil
  if not t or not t.w then return end
  local w = t.w
  if t.mode == "swipe" then
    local dx = x - t.x0
    self:set_page(self.page + ((dx < 0) and 1 or -1))
  elseif t.mode == nil and inside(w, x, y) then
    if w.kind == "dstep" then self:drum_tap(w.i)
    elseif w.kind == "mstep" then self:mono_tap(w.i)
    elseif w.kind == "cstep" then self:chord_tap(w.i)
    elseif w.kind == "ms" then self:send(w.hook, ((self.v[w.hook] or 0) > 0) and 0 or 1)
    elseif w.tap then w.tap() end
  end
  self:dirty()
end

function ui:mouse_down(x, y) self:press(x / self.s, y / self.s); self:repaint() end
function ui:mouse_drag(x, y) self:move(x / self.s, y / self.s); self:repaint() end
function ui:mouse_up(x, y) self:release(x / self.s, y / self.s); self:repaint() end

-- headless test hook: same code paths as the mouse
function ui:test(sel, a)
  if sel == "tap" then self:press(a[1], a[2]); self:release(a[1], a[2])
  elseif sel == "drag" then
    self:press(a[1], a[2])
    for k = 1, 8 do self:move(a[1] + (a[3] - a[1]) * k / 8, a[2] + (a[4] - a[2]) * k / 8) end
    self:release(a[3], a[4])
  elseif sel == "screen" then self.screen = a[1]
  elseif sel == "dump" then
    local L = self:layout()
    pd.post(string.format("ockm-ui: screen %s page %d widgets %d", self.screen, self.page, #L))
  end
end

-- ------------------------------------------------------------------ paint
function ui:col(g, name) local r, gg, b = hex(self.theme[name] or name); g:set_color(r, gg, b) end
function ui:text(g, s, x, y, size, colname, w)
  self:col(g, colname or "mute")
  g:draw_text(s, x, y, w or 400, size or 12)
end
function ui:ctext(g, s, w, size, colname, dy)
  local tw = #s * size * 0.6
  self:text(g, s, w.x + (w.w - tw) / 2, w.y + (w.h - size) / 2 + (dy or 0) - 1, size, colname, w.w)
end

function ui:paint(g)
  if self.s ~= 1 then g:scale(self.s, self.s) end
  self:col(g, "bg"); g:fill_all()
  for _, w in ipairs(self:layout()) do self:draw(g, w) end
end

-- layer 2: the playhead only, so the clock doesn't redraw the whole screen
function ui:paint_layer_2(g)
  if self.s ~= 1 then g:scale(self.s, self.s) end
  if self.playing == 0 then return end
  local i = self.step % 16
  local pitch = (W - 32) / 16
  if self.screen == "perform" then
    local lw = (W - LANE_X - 16) / 16
    self:col(g, "acc"); g:fill_rect(LANE_X + i * lw + 2, LANE_Y - 6, lw - 4, 3)
  elseif (self.screen == "drums" or self.screen == "synth") and self:play_block() == self.page then
    -- under the step pads, over the beat marks
    local y = (self.screen == "drums") and (D_STEP_Y + D_STEP_H + 3) or (S_STEP_Y + S_STEP_H + 3)
    self:col(g, "acc"); g:fill_rect(16 + i * pitch + 3, y, pitch - 6, 4)
  end
end

function ui:draw(g, w)
  local k = w.kind
  local th = self.theme
  if k == "btn" then
    self:col(g, w.accent and "acc" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, w, 14, w.accent and "#ffffff" or (w.quiet and "mute" or "txt"))
  elseif k == "tab" then
    self:col(g, w.sel and "on" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, w, 15, w.sel and "bg" or "txt")
  elseif k == "play" then
    local on = self.playing ~= 0
    self:col(g, on and "acc" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:col(g, on and "#ffffff" or "txt")
    local cx, cy = w.x + w.w / 2, w.y + w.h / 2
    if on then g:fill_rect(cx - 9, cy - 9, 18, 18)
    else local p = Path(cx - 7, cy - 11); p:line_to(cx + 11, cy); p:line_to(cx - 7, cy + 11); p:close(); g:fill_path(p) end
  elseif k == "bpm" then
    local s = fmt(self.v["ockm-bpm"] or 124)
    self:text(g, s, w.x + 4, w.y + 4, 32, "txt")
    self:text(g, "bpm", w.x + 8 + #s * 19, w.y + 26, 12, "mute")
    self:text(g, VERSION, w.x + 8 + #s * 19, w.y + 8, 9, "mute")
  elseif k == "text" then
    self:text(g, w.label, w.x, w.y, w.size or 12, w.col or "mute", w.w)
  elseif k == "pattern" then
    local playing = (w.n == self.cur)
    self:col(g, playing and "on" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    if self.want == w.n then self:col(g, "acc"); g:stroke_rounded_rect(w.x + 1, w.y + 1, w.w - 2, w.h - 2, 6, 2) end
    self:ctext(g, string.format("%d", math.floor(w.n + 1)), w, (w.h > 44) and 22 or 13, playing and "bg" or "txt")
  elseif k == "choice" then
    local sel = w.sel
    self:col(g, sel and (w.accent and "acc" or "on") or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, w, w.small and 11 or 13, sel and (w.accent and "#ffffff" or "bg") or "txt")
  elseif k == "preset" then
    local sel = w.sel
    self:col(g, sel and "on" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    local tc, sc = sel and "bg" or "txt", sel and "bg" or "mute"
    if w.inline then
      self:ctext(g, w.num .. "  " .. w.label, w, 13, tc)
    else
      local lines = w.sub and 3 or 2
      local top = w.y + (w.h - (lines == 3 and 46 or 32)) / 2
      self:ctext(g, tostring(w.num), { x=w.x, y=top, w=w.w, h=16 }, 16, tc)
      self:ctext(g, w.label, { x=w.x, y=top + 18, w=w.w, h=12 }, 10, tc)
      if w.sub then self:ctext(g, w.sub, { x=w.x, y=top + 32, w=w.w, h=12 }, 9, sc) end
    end
  elseif k == "ms" then
    local on = (self.v[w.hook] or 0) > 0
    local solo = w.label == "S"
    self:col(g, on and (solo and "acc" or "on") or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 4)
    self:ctext(g, w.label, w, (w.h > 30) and 15 or 11, on and (solo and "#ffffff" or "bg") or "mute")
  elseif k == "strip" then
    self:col(g, "card"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, { x=w.x, y=w.y + 6, w=w.w, h=16 }, 11, w.silent and "mute" or "txt")
  elseif k == "hbar" then
    local v = self.v[w.hook] or 0
    local f = clamp((v - w.lo) / (w.hi - w.lo), 0, 1)
    self:col(g, "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 4)
    if w.bold then
      -- grey fill up to the value (from the middle for controls centred on zero), orange line at the value
      local vx = w.x + w.w * f
      local x0 = (w.lo < 0) and (w.x + w.w * (-w.lo) / (w.hi - w.lo)) or w.x
      self:col(g, "dim"); g:fill_rounded_rect(math.min(x0, vx), w.y, math.max(4, math.abs(vx - x0)), w.h, 4)
      self:col(g, "acc"); g:fill_rect(clamp(vx - 2, w.x, w.x + w.w - 3), w.y, 3, w.h)
    else
      self:col(g, "dim"); g:fill_rounded_rect(w.x, w.y, math.max(6, w.w * f), w.h, 4)
    end
    if w.h >= 40 then
      self:ctext(g, w.label, { x=w.x, y=w.y + w.h / 2 - 16, w=w.w, h=14 }, 12, "txt")
      self:ctext(g, fmt(v), { x=w.x, y=w.y + w.h / 2 + 2, w=w.w, h=12 }, 10, "txt")
    else
      self:ctext(g, w.label, w, 10, "txt")
    end
  elseif k == "vfader" then
    local v = self.v[w.hook] or 0
    local f = clamp((v - w.lo) / (w.hi - w.lo), 0, 1)
    local tx = w.x + w.w / 2 - 4
    self:col(g, "off"); g:fill_rounded_rect(tx, w.y + 8, 8, w.h - 16, 4)
    local fy = w.y + 8 + (w.h - 16) * (1 - f)
    self:col(g, w.master and "on" or "acc"); g:fill_rounded_rect(tx, fy, 8, w.y + w.h - 8 - fy, 4)
    g:fill_rounded_rect(w.x + 4, fy - 7, w.w - 8, 14, 4)
    self:ctext(g, string.format("%d", math.floor(v * 100 + 0.5)), { x=w.x, y=w.y + w.h - 2, w=w.w, h=12 }, 10, "mute")
  elseif k == "lanename" then
    self:text(g, w.label, w.x, w.y + 4, 13, "txt", w.w)
  elseif k == "lane" then
    self:draw_lane(g, w)
  elseif k == "blockinfo" then
    local b = w.follow and self:play_block() or self.page
    local n = self:blocks()
    b = clamp(b, 0, n - 1)
    local s = string.format("steps %d-%d", b * 16 + 1, math.min((b + 1) * 16, self.v["ockm-len"] or 16))
    if n > 1 then s = s .. string.format("   block %d of %d", b + 1, n) end
    if w.follow then s = (self.playing ~= 0 and "playing " or "") .. s end
    self:text(g, s, w.x, w.y + w.h / 2 - 8, 13, "mute", w.w)
  elseif k == "dot" then
    local cur = (w.b == self.page)
    self:col(g, cur and "on" or "off"); g:fill_rounded_rect(w.x + 4, w.y + 8, w.w - 8, w.h - 16, 4)
    if self.playing ~= 0 and w.b == self:play_block() and not cur then
      self:col(g, "acc"); g:fill_rect(w.x + 4, w.y + w.h - 5, w.w - 8, 3)
    end
  elseif k == "arrow" then
    self:col(g, "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:col(g, w.on and "txt" or "dim")
    local cx, cy = w.x + w.w / 2, w.y + w.h / 2
    local p
    if w.dir < 0 then p = Path(cx + 5, cy - 8); p:line_to(cx - 5, cy); p:line_to(cx + 5, cy + 8)
    else p = Path(cx - 5, cy - 8); p:line_to(cx + 5, cy); p:line_to(cx - 5, cy + 8) end
    p:close(); g:fill_path(p)
  elseif k == "steps" then
    local n, b = self:blocks(), self:shown_block()
    local len = self.v["ockm-len"] or 16
    local s = string.format("%d-%d", b * 16 + 1, math.min((b + 1) * 16, len))
    self:col(g, "card"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, s, { x=w.x, y=w.y + 3, w=w.w, h=18 }, 13, "txt")
    if n > 1 then
      local dw = 10
      local x0 = w.x + (w.w - n * dw) / 2
      for i = 0, n - 1 do
        local playing = self.playing ~= 0 and i == self:play_block()
        self:col(g, (i == b) and "on" or (playing and "acc" or "dim"))
        if playing and i == b then self:col(g, "acc") end
        g:fill_ellipse(x0 + i * dw + 2, w.y + w.h - 10, 6, 6)
      end
    end
  elseif k == "block" then
    -- the block you're looking at is filled; an orange bar marks the one that's playing
    local shown = (self.screen == "perform" and self.playing ~= 0) and self:play_block() or self.page
    local cur = (w.b == shown)
    self:col(g, cur and "on" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, w, 11, cur and "bg" or "txt")
    if self.playing ~= 0 and w.b == self:play_block() then
      self:col(g, "acc"); g:fill_rect(w.x + 4, w.y + w.h - 4, w.w - 8, 3)
    end
  elseif k == "steprow" or k == "stripname" then
    -- nothing to draw: it only catches swipes between the pads
  elseif k == "dstep" then
    local v = self:get("ockm-pat-"..SLOTS[self.slot], self:abs(w.i))
    self:col(g, (v >= 2) and "acc" or ((v > 0) and "on" or "off")); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    if w.i % 4 == 0 then self:col(g, "mute"); g:fill_rect(w.x, w.y + w.h + 4, w.w, 2) end
  elseif k == "mstep" then
    local on, acc = self:mono_get(w.i, "on"), self:mono_get(w.i, "acc")
    self:col(g, (on > 0) and ((acc > 0) and "acc" or "on") or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    if on > 0 then
      local m = self:mono_get(w.i, "note")
      local tc = (acc > 0) and "#ffffff" or "bg"
      self:ctext(g, self:note_name(m), w, 15, tc, -8)
      self:ctext(g, tostring(math.floor(m / 12) - 1), w, 11, tc, 12)
      if self:mono_get(w.i, "slide") > 0 then self:col(g, "acc"); g:fill_rect(w.x + w.w - 2, w.y + w.h / 2 - 3, 10, 6) end
    end
    if w.i == self.sel_step then self:col(g, "mute"); g:stroke_rounded_rect(w.x - 2, w.y - 2, w.w + 4, w.h + 4, 7, 2) end
    if w.i % 4 == 0 then self:col(g, "mute"); g:fill_rect(w.x, w.y + w.h + 4, w.w, 2) end
  elseif k == "cstep" then
    local v = self:chord_get(w.i, "on")
    self:col(g, (v >= 2) and "acc" or ((v > 0) and "on" or "off")); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    if v > 0 then self:ctext(g, ROMAN[(math.floor(self:chord_get(w.i, "deg")) % 7) + 1], w, 15, (v >= 2) and "#ffffff" or "bg") end
    if w.i == self.sel_step then self:col(g, "mute"); g:stroke_rounded_rect(w.x - 2, w.y - 2, w.w + 4, w.h + 4, 7, 2) end
    if w.i % 4 == 0 then self:col(g, "mute"); g:fill_rect(w.x, w.y + w.h + 4, w.w, 2) end
  elseif k == "deg" then
    local part = SYNTHS[self.part]
    local sel, label
    if part == "chord" then
      sel = math.floor(self:chord_get(self.sel_step, "deg")) == w.d and self:chord_get(self.sel_step, "on") > 0
      label = ROMAN[w.d + 1]
    else
      local on = self:mono_get(self.sel_step, "on") > 0
      sel = on and self:midi_to_deg(part, self:mono_get(self.sel_step, "note")) == w.d
      local m = self:deg_to_midi(part, w.d)
      label = self:note_name(m)
      w.oct = tostring(math.floor(m / 12) - 1)
    end
    self:col(g, sel and "acc" or ((w.d == 0) and "dim" or "off")); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, label, w, 13, sel and "#ffffff" or "txt", w.oct and -6 or 0)
    if w.oct then self:ctext(g, w.oct, w, 10, sel and "#ffffff" or "mute", 10) end
  elseif k == "slider" then
    local v = self.v[w.hook] or w.lo
    local f = clamp((v - w.lo) / (w.hi - w.lo), 0, 1)
    self:text(g, w.label, w.x, w.y + w.h / 2 - 7, 13, "txt", 100)
    local sx, sw = w.x + 110, w.w - 180
    self:col(g, "off"); g:fill_rounded_rect(sx, w.y + w.h / 2 - 5, sw, 10, 5)
    self:col(g, "acc"); g:fill_rounded_rect(sx, w.y + w.h / 2 - 5, math.max(10, sw * f), 10, 5)
    g:fill_ellipse(sx + sw * f - 10, w.y + w.h / 2 - 10, 20, 20)
    self:text(g, fmt(v), w.x + w.w - 56, w.y + w.h / 2 - 7, 13, "mute", 56)
  end
end

function ui:draw_lane(g, w)
  local n = w.track
  local cw = w.w / 16
  local base = self:play_block() * 16
  if self.playing == 0 then base = self.page * 16 end
  for i = 0, 15 do
    local st = 0
    if n <= 8 then st = self:get("ockm-pat-"..SLOTS[n], base + i)
    elseif n <= 10 then
      local part = SYNTHS[n - 8]
      if self:get("ockm-pat-"..part.."-on", base + i) > 0 then st = (self:get("ockm-pat-"..part.."-acc", base + i) > 0) and 2 or 1 end
    else st = self:get("ockm-pat-chord-on", base + i) end
    if self:silent(TRACKS[n]) then self:col(g, (st > 0) and "dim" or "off")
    else self:col(g, (st >= 2) and "acc" or ((st > 0) and "on" or "off")) end
    g:fill_rounded_rect(w.x + i * cw + 2, w.y + 4, cw - 4, w.h - 8, 3)
  end
end
