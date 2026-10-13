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

local THEMES = {
  dark  = { bg="#141414", card="#1e1e1e", off="#2a2a2a", on="#ededed", acc="#ff5a24", mute="#7a7a7a", txt="#ededed", dim="#3a3a3a" },
  light = { bg="#f4f3ef", card="#ffffff", off="#e4e2dc", on="#1a1a1a", acc="#ff4f1a", mute="#9a9890", txt="#1a1a1a", dim="#cfccc4" },
}

local SLOTS   = { "d1","d2","d3","d4","d5","d6","d7","d8" }
local SOUNDS  = { "kick","snare","clap","rim","closed hat","open hat","tom","rimshot" }
local SHORT   = { "kick","snare","clap","rim","hat","open hat","tom","rimshot" }
local SYNTHS  = { "bass","lead","chord" }
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
local RHYTHMS = { "offbeat","rolling","gallop","acid","dub","bounce","acid 16","trip-hop" }
local MONO_NOTES = { "root","octaves","fifth","acid riff","walk up","stab","dub","pedal","arp up","arp up-dn","call","descend" }
local CHORD_RHY = { "offbeat","dub","bar pad","organ","two beat","synco","eighths","sparse" }
local PROGS = { "i","i-VI-VII","i-iv","i-VII-VI","i-v","i-III-VII","i-VI-iv-v","ii-V-i" }
local CHORD_TYPES = { "triad","7th","sus2","power" }
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
  v["ockm-bpm"] = 124; v["ockm-len"] = 16; v["ockm-filter"] = 0; v["ockm-root"] = 9; v["ockm-scale"] = 0
  for i, nm in ipairs(SLOTS) do
    v["ockm-"..nm.."-sound"] = ({0,1,2,4,5,7,3,6})[i]
    v["ockm-"..nm.."-level"] = 1; v["ockm-"..nm.."-tune"] = 0; v["ockm-"..nm.."-decay"] = 100
    v["ockm-"..nm.."-verb"] = 0; v["ockm-"..nm.."-delay"] = 0
  end
  for _, t in ipairs(SYNTHS) do
    for _, k in ipairs({"engine","k1","k2","k3","k4","drive","rhythm","notes","type","prog"}) do v["ockm-"..t.."-"..k] = 0 end
  end
end

function ui:hooks()
  local h = { "ockm-bpm","ockm-len","ockm-root","ockm-scale","ockm-filter" }
  for _, nm in ipairs(SLOTS) do
    for _, p in ipairs(DRUM_PARAMS) do h[#h+1] = "ockm-"..nm.."-"..p[1] end
    h[#h+1] = "ockm-"..nm.."-sound"
  end
  for _, t in ipairs({"bass","lead"}) do
    for _, k in ipairs({"engine","k1","k2","k3","k4","drive","rhythm","notes"}) do h[#h+1] = "ockm-"..t.."-"..k end
  end
  for _, k in ipairs({"engine","k1","k2","k3","k4","type","rhythm","prog"}) do h[#h+1] = "ockm-chord-"..k end
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
  listen("ockm-load",    function(o, sel, a) o.cur = tonumber(a[1]) or 0; o.want = nil; o:dirty() end)
  listen("ockm-want",    function(o, sel, a)
    local n = tonumber(a[1]); if n and (o.playing ~= 0) and n ~= o.cur then o.want = n end; o:dirty() end)
  listen("ockm-page",    function(o, sel, a) o.page = tonumber(a[1]) or 0; o:dirty() end)
  listen("ockm-step",    function(o, sel, a) o:on_step(tonumber(a[1]) or 0) end)
  for _, n in ipairs({ "ockm-refresh","ockm-edit","ockm-extend","ockm-bass-edit","ockm-lead-edit","ockm-chord-edit",
                       "ockm-bass-gen","ockm-lead-gen","ockm-chord-gen" }) do
    listen(n, function(o) o:dirty() end)
  end
  listen("ockm-ui-test", function(o, sel, a) o:test(sel, a) end)
  self.clock = pd.Clock:new():register(self, "redraw")
end

function ui:finalize()
  for _, r in ipairs(self.recv or {}) do r:destruct() end
  if self.clock then self.clock:destruct() end
  for _, t in pairs(self.tables) do if t.destruct then t:destruct() end end
end

-- one repaint for a burst of changes
function ui:dirty() if self.clock then self.clock:delay(5) end end
function ui:redraw() self:repaint() end

function ui:on_step(n)
  local old = math.floor(self.step / 16)
  self.step = n
  if self.screen == "perform" and math.floor(n / 16) ~= old then self:repaint() else self:repaint(2) end
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
  else self:layout_synth(add) end
  return L
end

-- top bar, the same on every screen: play, tempo, the three screens as tabs, save and revert
local TABS = { { "perform", "perform" }, { "drums", "drums" }, { "synth", "synths" } }
function ui:layout_top(add)
  add{ kind="play", x=16, y=12, w=64, h=48, tap=function() self:send("ockm-play", self.playing ~= 0 and 0 or 1) end }
  add{ kind="bpm", x=92, y=12, w=140, h=48 }
  for i, t in ipairs(TABS) do
    add{ kind="tab", x=250 + (i - 1) * 126, y=12, w=120, h=48, label=t[2], sel=(self.screen == t[1]),
         tap=function() if self.screen ~= t[1] then self:open(t[1]) end end }
  end
  add{ kind="btn", x=W - 208, y=12, w=92, h=48, label="save", quiet=true, tap=function() pd.send("ockm-save", "bang", {}) end }
  add{ kind="btn", x=W - 108, y=12, w=92, h=48, label="revert", quiet=true, tap=function() pd.send("ockm-revert", "bang", {}) end }
end

local LANE_Y, LANE_H, LANE_P = 144, 22, 24
function ui:lane_y(i) return LANE_Y + (i - 1) * LANE_P + ((i > 8) and 6 or 0) end

function ui:layout_perform(add)
  -- patterns 1 to 8
  local pw = (W - 32 - 7 * 8) / 8
  for i = 0, 7 do
    add{ kind="pattern", x=16 + i * (pw + 8), y=72, w=pw, h=56, n=i, tap=function()
      pd.send("ockm-want", "float", { i })
      if self.playing ~= 0 and i ~= self.cur then self.want = i end
    end }
  end
  -- now: 8 drum lanes and 3 synth lanes, a picture of the block that is playing. Tap a name to open it
  for i = 1, 11 do
    local isdrum = i <= 8
    local y = self:lane_y(i)
    local name = isdrum and SHORT[(self.v["ockm-"..SLOTS[i].."-sound"] or 0) + 1] or SYNTHS[i - 8]
    add{ kind="lanename", x=16, y=y, w=120, h=LANE_H, label=name, tap=function()
      if isdrum then self.slot = i; self:open("drums") else self.part = i - 8; self:open("synth") end
    end }
    add{ kind="lane", x=148, y=y, w=W - 164, h=LANE_H, track=i }
  end
  -- live sound strip: pick a synth, play its four main knobs
  local part = SYNTHS[self.perf_part or 1]
  for i, t in ipairs(SYNTHS) do
    add{ kind="choice", x=16 + (i - 1) * 68, y=430, w=62, h=76, label=t, sel=((self.perf_part or 1) == i),
         tap=function() self.perf_part = i end }
  end
  local eng = (part == "chord") and CHORD_ENG or MONO_ENG
  local kn = KNOBS[eng[(self.v["ockm-"..part.."-engine"] or 0) + 1]] or KNOBS.acid
  local cw = (W - 236 - 16 - 12) / 2
  for k = 1, 4 do
    local col, row = (k - 1) % 2, math.floor((k - 1) / 2)
    add{ kind="slider", x=236 + col * (cw + 12), y=430 + row * 42, w=cw, h=34, hook="ockm-"..part.."-k"..k, lo=0, hi=1, label=kn[k] }
  end
  -- length, where we are, and the master filter
  local lens = { 16, 32, 64, 128 }
  add{ kind="text", x=16, y=516, w=100, h=12, label="length", size=10 }
  for i, n in ipairs(lens) do
    add{ kind="choice", x=16 + (i - 1) * 70, y=532, w=64, h=52, label=tostring(n),
         sel=(self.v["ockm-len"] == n), tap=function() pd.send("ockm-length", "float", { n }) end }
  end
  add{ kind="blockinfo", x=306, y=532, w=210, h=52, follow=true }
  add{ kind="slider", x=520, y=541, w=W - 536, h=34, hook="ockm-filter", lo=-1, hi=1, label="filter" }
end

function ui:open(screen)
  self.screen = screen
  self.sel_step = 0
  self:set_page(self:play_block())
end

-- the block bar: dots you can tap, plus which steps you're looking at
function ui:block_bar(add, y)
  local n = self:blocks()
  for b = 0, n - 1 do
    add{ kind="dot", x=16 + b * 44, y=y, w=40, h=32, b=b, tap=function() self:set_page(b) end }
  end
  add{ kind="blockinfo", x=16 + n * 44 + 12, y=y, w=400, h=32 }
end

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
  for i = 1, 8 do
    add{ kind="choice", x=16 + (i - 1) * (tw + 8), y=72, w=tw, h=48,
         label=SHORT[(self.v["ockm-"..SLOTS[i].."-sound"] or 0) + 1], sel=(i == self.slot), tap=function() self.slot = i end }
  end
  add{ kind="text", x=16, y=130, w=200, h=16, label="sound", size=11 }
  for s = 0, 7 do
    add{ kind="choice", x=16 + s * (tw + 8), y=148, w=tw, h=48, label=SOUNDS[s + 1], accent=true,
         sel=(self.v["ockm-"..nm.."-sound"] == s), tap=function() self:send("ockm-"..nm.."-sound", s) end }
  end
  self:step_row(add, 220, 96, "dstep")
  self:block_bar(add, 330)
  for j, p in ipairs(DRUM_PARAMS) do
    add{ kind="slider", x=16, y=380 + (j - 1) * 42, w=W - 32, h=34, hook="ockm-"..nm.."-"..p[1], lo=p[2], hi=p[3], label=p[4] or p[1] }
  end
end

function ui:layout_synth(add)
  local part = SYNTHS[self.part]
  local mono = part ~= "chord"
  for i, t in ipairs(SYNTHS) do
    add{ kind="choice", x=16 + (i - 1) * 118, y=72, w=110, h=44, label=t, sel=(i == self.part),
         tap=function() self.part = i; self.sel_step = 0 end }
  end
  for k = 0, 11 do
    add{ kind="choice", x=376 + k * 47, y=72, w=43, h=44, label=NOTES[k + 1], sel=(self.v["ockm-root"] == k),
         tap=function() self:send("ockm-root", k) end }
  end
  for s = 0, 5 do
    add{ kind="choice", x=16 + s * 80, y=124, w=74, h=40, label=SCALE_NAMES[s + 1], sel=(self.v["ockm-scale"] == s),
         tap=function() self:send("ockm-scale", s) end }
  end
  if mono then
    add{ kind="choice", x=W - 136, y=124, w=120, h=40, label="slide", accent=true, sel=self:mono_get(self.sel_step, "slide") > 0,
         tap=function() self:mono_toggle_slide() end }
  end
  add{ kind="text", x=500, y=136, w=300, h=20, label=self:step_info(), size=12 }
  self:step_row(add, 176, 84, mono and "mstep" or "cstep")
  self:block_bar(add, 268)
  -- note picker for the selected step
  if mono then
    local bw = (W - 32) / 15
    for d = -7, 7 do
      add{ kind="deg", x=16 + (d + 7) * bw + 2, y=306, w=bw - 4, h=44, d=d, tap=function() self:mono_set_deg(d) end }
    end
  else
    local bw = (W - 32) / 7
    for d = 0, 6 do
      add{ kind="deg", x=16 + d * bw + 3, y=306, w=bw - 6, h=44, d=d, tap=function() self:chord_set_deg(d) end }
    end
  end
  -- sound (left) and fill (right)
  local eng = mono and MONO_ENG or CHORD_ENG
  local ew = 440 / #eng
  add{ kind="text", x=16, y=360, w=100, h=16, label="sound", size=11 }
  for e = 0, #eng - 1 do
    add{ kind="choice", x=16 + e * ew, y=378, w=ew - 6, h=40, label=eng[e + 1], sel=(self.v["ockm-"..part.."-engine"] == e),
         tap=function() self:send("ockm-"..part.."-engine", e) end }
  end
  local kn = KNOBS[eng[(self.v["ockm-"..part.."-engine"] or 0) + 1]] or KNOBS.acid
  for k = 1, 4 do
    add{ kind="slider", x=16, y=426 + (k - 1) * 42, w=434, h=34, hook="ockm-"..part.."-k"..k, lo=0, hi=1, label=kn[k] }
  end
  local rx = 480
  if mono then
    add{ kind="slider", x=rx, y=378, w=W - rx - 16, h=34, hook="ockm-"..part.."-drive", lo=0, hi=1, label="drive" }
  else
    for c = 0, 3 do
      add{ kind="choice", x=rx + c * 117, y=378, w=111, h=40, label=CHORD_TYPES[c + 1], sel=(self.v["ockm-chord-type"] == c),
           tap=function() self:send("ockm-chord-type", c) end }
    end
  end
  add{ kind="text", x=rx, y=424, w=200, h=16, label="fill", size=11 }
  local rh = mono and RHYTHMS or CHORD_RHY
  local cw = (W - rx - 16) / 8
  for r = 0, 7 do
    add{ kind="choice", x=rx + r * cw, y=442, w=cw - 4, h=36, label=rh[r + 1], small=true, sel=(self.v["ockm-"..part.."-rhythm"] == r),
         tap=function() self:send("ockm-"..part.."-rhythm", r) end }
  end
  local second, key = mono and MONO_NOTES or PROGS, mono and "notes" or "prog"
  local per = mono and 6 or 4
  local nw = (W - rx - 16 - 100) / per
  for n = 0, #second - 1 do
    local row, col = math.floor(n / per), n % per
    add{ kind="choice", x=rx + col * nw, y=484 + row * 40, w=nw - 4, h=36, label=second[n + 1], small=true,
         sel=(self.v["ockm-"..part.."-"..key] == n), tap=function() self:send("ockm-"..part.."-"..key, n) end }
  end
  add{ kind="btn", x=W - 112, y=484, w=96, h=76, label="new", accent=true,
       tap=function() pd.send("ockm-"..part.."-gen", "bang", {}); self:dirty() end }
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
  self.sel_step = i
  local v = self:chord_get(i, "on")
  local nv = (v <= 0) and 1 or ((v < 2) and 2 or 0)
  pd.send("ockm-chord-edit", "list", { self:abs(i), nv, self:chord_get(i, "deg") })
  self:dirty()
end
function ui:chord_set_deg(d)
  local i = self.sel_step
  local v = self:chord_get(i, "on")
  pd.send("ockm-chord-edit", "list", { self:abs(i), (v > 0) and v or 1, d })
  self:dirty()
end

function ui:step_info()
  local i = self.sel_step
  local s = "step " .. (self:abs(i) + 1)
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
    if inside(w, x, y) and (w.tap or w.swipe or w.kind == "slider" or w.kind == "bpm"
       or w.kind == "dstep" or w.kind == "mstep" or w.kind == "cstep") then return w end
  end
  return nil
end

function ui:press(x, y)
  local w = self:hit(x, y)
  self.touch = { w = w, x0 = x, y0 = y, mode = nil }
  if not w then return end
  if w.kind == "slider" then self.touch.mode = "slider"; self:slide(w, x)
  elseif w.kind == "bpm" then self.touch.mode = "bpm"; self.touch.v0 = self.v["ockm-bpm"] or 124
  elseif w.kind == "mstep" or w.kind == "cstep" then
    self.touch.v0 = (w.kind == "mstep") and self:midi_to_deg(SYNTHS[self.part], self:mono_note_or_default(w.i))
                                         or math.floor(self:chord_get(w.i, "deg"))
  end
end

function ui:slide(w, x)
  local f = clamp((x - (w.x + 110)) / (w.w - 180), 0, 1)
  local v = w.lo + f * (w.hi - w.lo)
  if w.hi - w.lo > 4 then v = math.floor(v + 0.5) else v = math.floor(v * 100 + 0.5) / 100 end
  self:send(w.hook, v)
end

function ui:move(x, y)
  local t = self.touch
  if not t or not t.w then return end
  local dx, dy = x - t.x0, y - t.y0
  if t.mode == "slider" then self:slide(t.w, x); return end
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
    local lw = (W - 164) / 16
    self:col(g, "acc"); g:fill_rect(148 + i * lw + 2, LANE_Y - 7, lw - 4, 3)
  elseif self:play_block() == self.page then
    -- under the step pads, over the beat marks
    local y = (self.screen == "drums") and (220 + 96 + 3) or (176 + 84 + 3)
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
  elseif k == "text" then
    self:text(g, w.label, w.x, w.y, w.size or 12, w.col or "mute", w.w)
  elseif k == "pattern" then
    local playing = (w.n == self.cur)
    self:col(g, playing and "on" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    if self.want == w.n then self:col(g, "acc"); g:stroke_rounded_rect(w.x + 1, w.y + 1, w.w - 2, w.h - 2, 6, 3) end
    self:ctext(g, tostring(w.n + 1), w, 22, playing and "bg" or "txt")
  elseif k == "choice" then
    local sel = w.sel
    self:col(g, sel and (w.accent and "acc" or "on") or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, w, w.small and 11 or 13, sel and (w.accent and "#ffffff" or "bg") or "txt")
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
  elseif k == "steprow" then
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
    self:col(g, (st >= 2) and "acc" or ((st > 0) and "on" or "off"))
    g:fill_rounded_rect(w.x + i * cw + 2, w.y + 4, cw - 4, w.h - 8, 3)
  end
end
