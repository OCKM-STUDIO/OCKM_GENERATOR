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
local VERSION = "v0.33"   -- shown on screen, so you can tell which version plugdata has loaded

local THEMES = {
  dark  = { bg="#141414", card="#1e1e1e", off="#2a2a2a", on="#ededed", acc="#ff5a24", mute="#7a7a7a", txt="#ededed", dim="#3a3a3a" },
  light = { bg="#f4f3ef", card="#ffffff", off="#e4e2dc", on="#1a1a1a", acc="#ff4f1a", mute="#9a9890", txt="#1a1a1a", dim="#cfccc4" },
}

local SLOTS   = { "d1","d2","d3","d4","d5","d6","d7","d8" }
local SOUNDS  = { "kick","snare","clap","rim","closed hat","open hat","tom","rimshot" }
local START = { bass = "start the bass line", lead = "start a melody", chord = "start the chords" }
local SHORT   = { "kick","snare","clap","rim","hat","open hat","tom","rimshot" }
local SYNTHS  = { "bass","lead","chord" }
local TRACKS  = { "d1","d2","d3","d4","d5","d6","d7","d8","bass","lead","chord" }
local NOTES   = { "C","C#","D","D#","E","F","F#","G","G#","A","A#","B" }
local SCALES  = { {0,2,3,5,7,8,10}, {0,2,4,5,7,9,11}, {0,2,3,5,7,9,10}, {0,1,3,5,7,8,10}, {0,2,4,5,7,9,10}, {0,2,3,5,7,8,11} }
local SCALE_NAMES = { "minor","major","dorian","phrygian","mixo","harm min" }
local MONO_ENG  = { "acid","sub","fm","reese","pluck","saw","house" }
local CHORD_ENG = { "stab","organ","pad" }
local KNOBS = {
  acid  = {"cutoff","resonance","env amount","decay"},
  sub   = {"tone","drive","pitch drop","decay"},
  fm    = {"brightness","ratio","env","decay"},
  reese = {"cutoff","detune","env amount","decay"},
  pluck = {"brightness","saw-square","snap","decay"},
  saw   = {"tone","detune","sub","decay"},
  house = {"tone","body","pluck","decay"},
  stab  = {"brightness","detune","snap","length"},
  organ = {"drawbars","click","sub","length"},
  pad   = {"brightness","detune","attack","length"},
}
-- BEGIN PRESETS (written by tools/build.py from its preset lists: edit them there, not here)
local RHYTHMS = { { "offbeat" }, { "rolling" }, { "gallop" }, { "acid classic" }, { "sparse dub" }, { "tech bounce" }, { "acid 16ths" }, { "trip hop" }, { "hook" }, { "sparse melody" } }
local MONO_NOTES = { "root", "octaves", "root fifth", "acid riff", "walk up", "minor stab", "dub", "pedal", "arp up", "arp updown", "call", "descend", "melody", "melody steps", "melody high" }
local CHORD_RHY = { { "bar pads" }, { "two beat" }, { "offbeat" }, { "dub stabs" }, { "house organ" }, { "tresillo" }, { "syncopated" }, { "garage skip" }, { "call answer" }, { "eighths" } }
local PROGS = { { "one chord", "i" }, { "vamp", "i iv" }, { "dub techno", "i . . VII" }, { "deep house", "i iv VI v" }, { "garage", "i VI iv v" }, { "pop", "i VI III VII" }, { "uplift", "VI VII i" }, { "andalusian", "i VII VI V" }, { "trip hop", "i VII VI v" }, { "soul", "ii V I" } }
local SPICE = { { 0, "triad" }, { 1, "7th" }, { 6, "9th" }, { 7, "11th" } }
local FILLS = { "snare roll", "tom run", "drop", "build" }
local GROOVES = { "four floor", "house", "deep house", "tech house", "minimal", "techno", "dub techno", "garage", "breakbeat", "boom bap", "trip hop", "electro", "clear" }
local PROG_SHAPES = { { { 0, 16 } }, { { 0, 16 }, { 3, 16 } }, { { 0, 48 }, { 6, 16 } }, { { 0, 16 }, { 3, 16 }, { 5, 16 }, { 4, 16 } }, { { 0, 8 }, { 5, 8 }, { 3, 8 }, { 4, 8 } }, { { 0, 16 }, { 5, 16 }, { 2, 16 }, { 6, 16 } }, { { 5, 16 }, { 6, 16 }, { 0, 32 } }, { { 0, 16 }, { 6, 16 }, { 5, 16 }, { 4, 16 } }, { { 0, 32 }, { 6, 32 }, { 5, 32 }, { 4, 32 } }, { { 1, 16 }, { 4, 16 }, { 0, 32 } } }
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
-- every message out goes through psend, so the save button knows when there are unsaved changes
local UI_NOW
local NOT_CHANGES = { ["ockm-play"]=1, ["ockm-want"]=1, ["ockm-page"]=1, ["ockm-save"]=1, ["ockm-revert"]=1, ["ockm-song-start"]=1,
  ["ockm-project-list"]=1, ["ockm-project-open"]=1, ["ockm-project-new"]=1, ["ockm-project-saveas"]=1, ["ockm-project-delete"]=1,
  ["ockm-resync"]=1, ["ockm-filter"]=1, ["ockm-filter-glide"]=1, ["ockm-delay-throw"]=1 }
local function psend(name, sel, atoms)
  if UI_NOW and not NOT_CHANGES[name] and not name:match("%-mute$") and not name:match("%-solo$") then UI_NOW.unsaved = true end
  pd["send"](name, sel, atoms)
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
  v["ockm-bass-mode"] = 0; v["ockm-lead-mode"] = 0; v["ockm-chord-mode"] = 0   -- 0 auto, 1 manual
  v["ockm-bass-sync"] = 1; v["ockm-lead-sync"] = 1; v["ockm-leader"] = 0; v["ockm-drum-groove"] = -1
  v["ockm-fill-every"] = 0; v["ockm-fill-style"] = 0; v["ockm-swing"] = 56; v["ockm-accent"] = 0.3; v["ockm-sync"] = 0; v["ockm-song-mode"] = 0; v["ockm-song-loop"] = 1; v["ockm-volume"] = 1
  for _, p in ipairs({ "bass", "lead" }) do v["ockm-"..p.."-lock"] = 0; v["ockm-"..p.."-density"] = 1; v["ockm-"..p.."-seed"] = 0 end
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
  h[#h+1] = "ockm-bass-sync"; h[#h+1] = "ockm-lead-sync"; h[#h+1] = "ockm-leader"; h[#h+1] = "ockm-drum-groove"
  for _, p in ipairs({ "bass", "lead" }) do
    for _, k in ipairs({ "lock", "density", "seed" }) do h[#h+1] = "ockm-"..p.."-"..k end
  end
  for _, k in ipairs({ "ockm-swing", "ockm-accent", "ockm-sync", "ockm-song-mode", "ockm-song-loop", "ockm-fill-every", "ockm-fill-style" }) do h[#h+1] = k end
  for _, k in ipairs({ "ockm-volume", "ockm-verb-mix", "ockm-delay-mix", "ockm-drive", "ockm-delay-fb", "ockm-delay-steps", "ockm-verb-size", "ockm-verb-tone" }) do h[#h+1] = k end
  return h
end

function ui:postinitialize()
  UI_NOW = self
  math.randomseed(os.time())
  self.project = "default"
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
  listen("ockm-project-name", function(o, sel, a) o.project = tostring(a[1] or "default"); o:dirty() end)
  listen("ockm-project-list-start", function(o) o.incoming = {} end)
  listen("ockm-filter-now", function(o, sel, a)
    local t = o.touch
    if t and t.w and t.w.hook == "ockm-filter" then return end
    o.v["ockm-filter"] = tonumber(a[1]) or 0; o:dirty()
  end)
  self.roleclock = pd.Clock:new():register(self, "check_roles")
  listen("ockm-refresh", function(o) if o.roleclock then o.roleclock:delay(0) end end)
  listen("ockm-patterns-exist", function(o, sel, a) o.exists = math.floor(tonumber(a[1]) or 1); o:dirty() end)
  for _, n in ipairs({ "ockm-saved", "ockm-revert", "ockm-project-name" }) do listen(n, function(o) o.unsaved = false; o:dirty() end) end
  listen("ockm-song-show", function(o, sel, a)
    local l = {}
    for k = 1, #a - 1, 2 do l[#l + 1] = { math.floor(tonumber(a[k]) or 0), math.floor(tonumber(a[k + 1]) or 1) } end
    o.song = l
    if (o.song_sel or 0) >= #l then o.song_sel = math.max(0, #l - 1) end
    o:dirty()
  end)
  listen("ockm-song-pos", function(o, sel, a) o.song_pos = { math.floor(tonumber(a[1]) or 0), math.floor(tonumber(a[2]) or 0) }; o:dirty() end)
  listen("ockm-project-item", function(o, sel, a) if o.incoming then o.incoming[#o.incoming + 1] = tostring(a[1]) end end)
  listen("ockm-project-list-end", function(o)
    local l = o.incoming or {}
    -- names start with the date, so newest first; anything without a date (like 'default') goes last
    local function dated(n) return n:match("^%d%d%d%d%-") ~= nil end
    table.sort(l, function(x, y) if dated(x) ~= dated(y) then return dated(x) end return x > y end)
    o.projects, o.incoming = l, nil
    o:dirty()
  end)
  listen("ockm-load",    function(o, sel, a) o.cur = math.floor(tonumber(a[1]) or 0); o.want = nil; o:dirty() end)
  listen("ockm-want",    function(o, sel, a)
    local n = tonumber(a[1]); if n and (o.playing ~= 0) and n ~= o.cur then o.want = n end; o:dirty() end)
  listen("ockm-page",    function(o, sel, a) o.page = math.floor(tonumber(a[1]) or 0); o:dirty() end)
  listen("ockm-step",    function(o, sel, a) o:on_step(math.floor(tonumber(a[1]) or 0)) end)
  for _, n in ipairs({ "ockm-refresh","ockm-edit","ockm-extend","ockm-bass-edit","ockm-lead-edit","ockm-chord-edit",
                       "ockm-bass-gen","ockm-lead-gen","ockm-chord-gen","ockm-drums-changed" }) do
    listen(n, function(o) o:dirty() end)
  end
  -- a fresh suggestion list whenever the melody, bass, key or progression changes by hand
  for _, n in ipairs({ "ockm-lead-edit", "ockm-bass-edit", "ockm-root", "ockm-scale", "ockm-load", "ockm-lead-gen", "ockm-bass-gen",
                       "ockm-lead-seed", "ockm-bass-seed", "ockm-lead-notes", "ockm-bass-notes", "ockm-lead-rhythm", "ockm-bass-rhythm", "ockm-chord-prog" }) do
    listen(n, function(o) if not o.suggesting then o.ranking = nil end end)
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
  psend("ockm-page", "float", { p })
end

function ui:send(hook, x)
  self.v[hook] = x
  psend(hook, "float", { x })
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
  elseif self.screen == "compose" then self:layout_compose(add)
  elseif self.screen == "project" then self:layout_project(add)
  elseif self.screen == "song" then self:layout_song(add)
  elseif self.screen == "setup" then self:layout_setup(add)
  else self:layout_synth(add) end
  if self.sheet == "newpat" then self:layout_newpat(add) end
  -- messages on screens that have no message line of their own
  if self.msg and (self.screen == "perform" or self.screen == "compose" or self.screen == "mixer" or self.screen == "song" or self.screen == "setup") then
    add{ kind="toast", x=W / 2 - 330, y=H - 50, w=660, h=38, label=self.msg }
  end
  return L
end

-- Screen hierarchy, top to bottom:
--   1. top bar: play, tempo, the six screens as tabs, save and revert
--   2. navigation strip: pattern, length, which block of 16 steps
--   3. what you're editing (drum slot tabs on the drums screen), then the steps
--   4. sound shaping at the bottom
local TABS = { { "perform", "perform" }, { "compose", "compose" }, { "drums", "drums" }, { "synth", "bass", 1 }, { "synth", "lead", 2 }, { "synth", "chord", 3 }, { "mixer", "mixer" }, { "song", "song" } }
local NAV_Y, NAV_H = 70, 36
function ui:layout_top(add)
  add{ kind="play", x=16, y=12, w=64, h=48, tap=function()
    if self.playing ~= 0 then self:send("ockm-play", 0)
    elseif (self.v["ockm-song-mode"] or 0) > 0 then
      if #(self.song or {}) == 0 then self:say("song mode: the song is empty. Add steps on the song tab"); self:open("song")
      else psend("ockm-song-start", "float", { self.song_sel or 0 }) end
    else self:send("ockm-play", 1) end
  end }
  add{ kind="bpm", x=92, y=12, w=140, h=48, tap=function() if self.screen ~= "setup" then self:open("setup") end end }
  for i, t in ipairs(TABS) do
    local sel = (self.screen == t[1]) and (t[3] == nil or t[3] == self.part)
    add{ kind="tab", x=244 + (i - 1) * 69, y=12, w=64, h=48, label=t[2], sel=sel, tap=function()
      if t[3] then
        if self.part ~= t[3] then self.part = t[3]; self.sel_step = 0; self.msg = nil end
      end
      if self.screen ~= t[1] then self:open(t[1]) end
    end }
  end
  add{ kind="btn", x=W - 154, y=12, w=64, h=48, label=self.unsaved and "save •" or "save", accent=self.unsaved, tap=function()
    psend("ockm-save", "bang", {}); self:say("saved " .. ockm_pretty(self.project) .. ": all 8 patterns, the song and the kit") end }
  add{ kind="tab", x=W - 84, y=12, w=68, h=48, label="project", sel=(self.screen == "project"), tap=function()
    if self.screen ~= "project" then self:open("project") end
  end }
  if self.screen ~= "project" and self.screen ~= "setup" then self:layout_nav(add) end
end

-- the navigation strip: pattern 1-8, length, and the blocks of 16 steps (only as many as the length allows)
function ui:layout_nav(add)
  local y, h = NAV_Y, NAV_H
  -- left, right above the steps: back, the steps you're looking at, forward
  local n = self:blocks()
  add{ kind="arrow", x=16, y=y, w=44, h=h, dir=-1, on=(self:shown_block() > 0), tap=function() self:set_page(self:shown_block() - 1) end }
  add{ kind="steps", x=64, y=y, w=104, h=h }
  add{ kind="arrow", x=172, y=y, w=44, h=h, dir=1, on=(self:shown_block() < n - 1), tap=function() self:set_page(self:shown_block() + 1) end }
  -- middle: the patterns you've made, then + for a new one
  add{ kind="text", x=240, y=y + 12, w=60, h=12, label="pattern", size=10 }
  local px = 290
  for i = 0, 7 do
    if self:is_used(i) or i == self.cur then
      add{ kind="pattern", x=px, y=y, w=30, h=h, n=i, tap=function() self:go_pattern(i) end }
      px = px + 34
    end
  end
  if self:free_slot() then add{ kind="btn", x=px, y=y, w=30, h=h, label="+", accent=true, tap=function() self.sheet = "newpat" end } end
  -- right: length
  add{ kind="text", x=W - 16 - 172 - 50, y=y + 12, w=50, h=12, label="length", size=10 }
  for i, len in ipairs({ 16, 32, 64, 128 }) do
    add{ kind="choice", x=W - 16 - 172 + (i - 1) * 44, y=y, w=40, h=h, label=tostring(len), small=true,
         sel=(self.v["ockm-len"] == len), tap=function() psend("ockm-length", "float", { len }) end }
  end
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
    if not isdrum and self:part_empty(SYNTHS[i - 8]) then
      local p = SYNTHS[i - 8]
      add{ kind="btn", x=LANE_X, y=y + 2, w=W - LANE_X - 16, h=LANE_H - 4, small=true, quiet=true, label="empty: tap to " .. START[p],
           tap=function() self:start_part(p) end }
    end
    if isdrum then
      -- drum lanes are editable here too: tap cycles empty, hit, accent on the block on screen
      local cw = (W - LANE_X - 16) / 16
      for c = 0, 15 do
        add{ kind="pcell", x=LANE_X + c * cw, y=y, w=cw, h=LANE_H, tap=function() self:drum_cycle(i, self:shown_block() * 16 + c) end }
      end
    end
  end
  -- bottom: the chosen synth's four main knobs on the left, master effects on the right (the way the sound flows)
  local half = (W - 32 - 16) / 2
  local lx, rx = 16, 16 + half + 16
  add{ kind="text", x=rx, y=441, w=200, h=10, label="master fx", size=9 }
  local mw = (half - 3 * 6) / 4
  -- top row: the filter (wide, springs back to off when you let go unless held), the dub throw, drive
  local hold = self.filter_hold
  add{ kind="hbar", x=rx, y=456, w=2 * mw + 6, h=60, hook="ockm-filter", lo=-1, hi=1, label=hold and "filter (held)" or "filter", bold=true, spring=not hold }
  add{ kind="choice", x=rx + 2 * mw + 6 - 50, y=460, w=46, h=22, label="hold", small=true, sel=hold, tap=function()
    self.filter_hold = not hold
    if hold then psend("ockm-filter-glide", "list", { 0, 180 }) end
  end }
  add{ kind="pad", x=rx + 2 * (mw + 6), y=456, w=mw, h=60, hook="ockm-delay-throw", label="throw", sub="hold" }
  add{ kind="hbar", x=rx + 3 * (mw + 6), y=456, w=mw, h=60, hook="ockm-drive", lo=0, hi=1, label="drive", bold=true }
  local ROW2 = { { "ockm-delay-mix", 0, 1, "delay" }, { "ockm-delay-fb", 0, 0.9, "feedback" }, { "ockm-delay-steps", 1, 8, "time" },
                 { "ockm-verb-mix", 0, 1, "reverb" }, { "ockm-verb-size", 0, 1, "size" } }
  local w5 = (half - 4 * 6) / 5
  for i, m in ipairs(ROW2) do
    add{ kind="hbar", x=rx + (i - 1) * (w5 + 6), y=524, w=w5, h=60, hook=m[1], lo=m[2], hi=m[3], label=m[4], bold=true }
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
  self.pick, self.confirm, self.sheet = nil, nil, nil
  if screen == "project" then psend("ockm-project-list", "bang", {}) end
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
  add{ kind="key", x=W - 16 - 300, y=276, w=300, h=12 }
  -- sound shaping
  add{ kind="text", x=16, y=276, w=200, h=12, label="sound", size=10 }
  for s = 0, 7 do
    add{ kind="choice", x=16 + s * (tw + 8), y=290, w=tw, h=44, label=SOUNDS[s + 1], accent=true,
         sel=(self.v["ockm-"..nm.."-sound"] == s), tap=function() self:send("ockm-"..nm.."-sound", s) end }
  end
  -- this slot's sound on the left, grooves for the whole kit on the right
  local half = (W - 48) / 2
  for j, p in ipairs(DRUM_PARAMS) do
    add{ kind="slider", x=16, y=350 + (j - 1) * 46, w=half, h=36, hook="ockm-"..nm.."-"..p[1], lo=p[2], hi=p[3], label=p[4] or p[1] }
  end
  local gx = 16 + half + 16
  add{ kind="text", x=gx, y=346, w=half, h=12, label=self.msg or "grooves: tap one to fill all 8 drums", size=self.msg and 11 or 10, col=self.msg and "acc" or nil }
  local gw = (half - 4 * 6) / 5
  local cur = math.floor(self.v["ockm-drum-groove"] or -1)
  for i, name in ipairs(GROOVES) do
    local n = i - 1
    local col, row = n % 5, math.floor(n / 5)
    local clear = (name == "clear")
    add{ kind=clear and "btn" or "choice", x=gx + col * (gw + 6), y=362 + row * 44, w=gw, h=38, label=name, small=true, quiet=clear,
         sel=(not clear) and (cur == n) or nil, tap=function()
           self:send("ockm-drum-groove", n)
           self:say(clear and "drums cleared" or (name .. ": all 8 drums rewritten (back to last save undoes it)"))
         end }
  end
  -- fills: the last bar of every 4, 8 or 16 bars plays a fill instead (your steps aren't changed)
  add{ kind="text", x=gx, y=498, w=half, h=12, label="fill on the last bar of every", size=10 }
  local fw = (half - 3 * 6) / 4
  local every = math.floor(self.v["ockm-fill-every"] or 0)
  for i, e in ipairs({ 0, 4, 8, 16 }) do
    add{ kind="choice", x=gx + (i - 1) * (fw + 6), y=512, w=fw, h=34, small=true, label=(e == 0) and "no fills" or (e .. " bars"),
         sel=(every == e), accent=(e > 0), tap=function() self:send("ockm-fill-every", e) end }
  end
  local style = math.floor(self.v["ockm-fill-style"] or 0)
  for i, name in ipairs(FILLS) do
    add{ kind="choice", x=gx + (i - 1) * (fw + 6), y=552, w=fw, h=34, small=true, label=name, sel=(style == i - 1), disabled=(every == 0),
         tap=function() self:send("ockm-fill-style", i - 1); if every == 0 then self:send("ockm-fill-every", 4) end end }
  end
end

-- the synth tabs: steps and sound. Notes come from compose while the part is on auto (steps locked, drawn as outlines);
-- switch to manual, like a camera, to edit them by hand
function ui:part_auto(part) return (self.v["ockm-"..(part or SYNTHS[self.part]).."-mode"] or 0) == 0 end
-- The mode dial (ockm-leader): 0 chord priority, 1 melody priority, 2 bass priority, 3 manual.
-- The priority part is yours; the other two follow it. In manual every part is yours.
local LEAD_PART = { [0] = "chord", [1] = "lead", [2] = "bass" }
function ui:mode() return math.floor(self.v["ockm-leader"] or 0) end
function ui:locked(part)
  part = part or SYNTHS[self.part]
  local m = self:mode()
  if m == 3 then return false end
  return LEAD_PART[m] ~= part
end
-- what a following part is following, in words
function ui:follows_what(part)
  local m = self:mode()
  if part == "chord" then return (m == 1) and "fits the melody" or "fits the bass line" end
  return "follows the chords"
end
-- you've edited a part that's yours: stop the engine regenerating it
function ui:claim(part)
  if (self.v["ockm-"..part.."-mode"] or 0) == 0 then self:send("ockm-"..part.."-mode", 1) end
end

function ui:auto_summary(part)
  if self:locked(part) then
    return part .. " " .. self:follows_what(part) .. ": shape it below. To edit the steps, set the mode to manual on compose"
  end
  local mono = part ~= "chord"
  local parts = {}
  if mono then
    parts[#parts + 1] = (MONO_NOTES[(self.v["ockm-"..part.."-notes"] or 0) + 1] or "")
    parts[#parts + 1] = ((RHYTHMS[(self.v["ockm-"..part.."-rhythm"] or 0) + 1] or {""})[1])
    parts[#parts + 1] = ((self.v["ockm-"..part.."-sync"] or 0) > 0) and "follows chords" or "follows key"
  else
    parts[#parts + 1] = ((PROGS[(self.v["ockm-chord-prog"] or 0) + 1] or {""})[1])
    parts[#parts + 1] = ((CHORD_RHY[(self.v["ockm-chord-rhythm"] or 0) + 1] or {""})[1])
  end
  return "auto: notes from compose (" .. table.concat(parts, ", ") .. "). Switch to manual to edit"
end

function ui:layout_synth(add)
  local part = SYNTHS[self.part]
  local mono = part ~= "chord"
  local auto = self:locked(part)
  self:step_row(add, S_STEP_Y, S_STEP_H, mono and "mstep" or "cstep")
  if not auto then
    -- manual: pick the note (or chord) for the selected step
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
  else
    if self:part_empty(part) then
      add{ kind="btn", x=16, y=216, w=W - 32, h=40, accent=true, label="empty: tap to " .. START[part], tap=function() self:start_part(part) end }
    else
      add{ kind="locked", x=16, y=216, w=W - 32, h=40, label=part .. " " .. self:follows_what(part) .. ": to edit the steps, set the mode to manual on compose", tap=function() self:open("compose") end }
    end
  end
  -- what's in charge, and the camera switch
  local info = self.msg or (auto and self:auto_summary(part) or ("yours: " .. self:step_info()))
  add{ kind="text", x=16, y=276, w=W - 300, h=12, label=info, size=11, col=self.msg and "acc" or nil }
  if mono and not auto then
    add{ kind="choice", x=W - 16 - 280, y=266, w=86, h=34, label="slide", accent=true, small=true, sel=self:mono_get(self.sel_step, "slide") > 0,
         tap=function() self:mono_toggle_slide() end }
  end
  add{ kind="choice", x=W - 16 - 180, y=266, w=180, h=34, small=true, accent=not auto, sel=not auto,
       label=auto and self:follows_what(part) or "yours", tap=function() self:open("compose") end }
  self:layout_synth_sound(add, part, mono)
end

function ui:layout_synth_sound(add, part, mono)
  local half = (W - 48) / 2
  -- left: where the notes come from (the same settings as this part's column on compose)
  add{ kind="card", x=16, y=306, w=half, h=H - 306 - 6 }
  add{ kind="text", x=28, y=318, w=half - 24, h=12, label="notes: the same settings as on compose", size=10 }
  self:gen_controls(add, part, 28, 290, half - 24, 0.88)
  -- right: the sound
  local rx, rw = 16 + half + 16, half
  add{ kind="text", x=rx, y=314, w=200, h=12, label="sound", size=10 }
  local eng = mono and MONO_ENG or CHORD_ENG
  local ew = rw / #eng
  for e = 0, #eng - 1 do
    add{ kind="choice", x=rx + e * ew, y=330, w=ew - 4, h=40, label=eng[e + 1], small=true, sel=(self.v["ockm-"..part.."-engine"] == e),
         tap=function() self:send("ockm-"..part.."-engine", e) end }
  end
  local kn = KNOBS[eng[(self.v["ockm-"..part.."-engine"] or 0) + 1]] or KNOBS.acid
  local kw = (rw - 6) / 2
  for k = 1, 4 do
    local col, row = (k - 1) % 2, math.floor((k - 1) / 2)
    add{ kind="hbar", x=rx + col * (kw + 6), y=380 + row * 54, w=kw, h=48, hook="ockm-"..part.."-k"..k, lo=0, hi=1, label=kn[k], bold=true }
  end
  local third = {}
  if mono then third[#third + 1] = { "drive", "drive" } end
  third[#third + 1] = { "verb", "reverb" }; third[#third + 1] = { "delay", "delay" }; third[#third + 1] = { "level", "level" }
  local tw = (rw - 6 * (#third - 1)) / #third
  for j, t in ipairs(third) do
    add{ kind="hbar", x=rx + (j - 1) * (tw + 6), y=494, w=tw, h=48, hook="ockm-"..part.."-"..t[1], lo=0, hi=1, label=t[2], bold=true }
  end
end

-- ------------------------------------------------------------------ compose
-- How the pattern is put together: who leads the harmony, the key, and each part's generator.
-- Compose decides the notes of parts on auto. Parts on manual are greyed out here and never changed.
local LEADERS = { { 0, "chord priority" }, { 1, "melody priority" }, { 2, "bass priority" }, { 3, "manual" } }

-- who follows the chords for each leader: chords lead, melody leads (bass follows), bass leads (lead follows), key only
local FOLLOW = { [0] = { bass = 1, lead = 1 }, [1] = { bass = 1, lead = 0 }, [2] = { bass = 0, lead = 1 }, [3] = { bass = 0, lead = 0 } }
function ui:set_leader(n)
  self:send("ockm-leader", n)
  self.ranking = nil
  if n == 3 then
    for _, p in ipairs(SYNTHS) do self:claim(p) end
    self:say("manual: every part is yours, exactly as it was. Nothing is regenerated")
    return
  end
  local lp = LEAD_PART[n]
  for _, p in ipairs({ "bass", "lead" }) do
    self:send("ockm-"..p.."-sync", (p == lp) and 0 or 1)
  end
  if lp == "chord" then
    for _, p in ipairs({ "bass", "lead" }) do self:send("ockm-"..p.."-mode", 0); psend("ockm-"..p.."-gen", "bang", {}) end
    self:say("chord priority: the chords are yours, bass and melody follow them")
  else
    local other = (lp == "lead") and "bass" or "lead"
    self:send("ockm-"..other.."-mode", 0)
    self:send("ockm-chord-mode", 0)
    if self:part_empty(lp) then psend("ockm-chord-gen", "bang", {}); psend("ockm-"..other.."-gen", "bang", {})
    else self:suggest_chords() end
    self:say(((lp == "lead") and "melody" or "bass") .. " priority: it's yours, the chords fit it and the " .. ((other == "lead") and "melody" or "bass") .. " follows")
  end
end

-- an older pattern can have hand-edited parts that would now be followers: open it in manual so nothing is lost
function ui:check_roles()
  local m = self:mode()
  if m == 3 then return end
  for _, p in ipairs(SYNTHS) do
    if self:locked(p) and (self.v["ockm-"..p.."-mode"] or 0) == 1 then
      if self:part_empty(p) then self:send("ockm-"..p.."-mode", 0)
      else
        self:send("ockm-leader", 3)
        self:say("this pattern has hand-edited parts, so it's in manual mode. Pick a priority to let it generate again")
        return
      end
    end
  end
end

-- melody-led or bass-led: score every progression against the leading part's notes.
-- A note on the chord's root scores 3, another chord note 2, anything else -1; downbeats and accents count more.
function ui:score_prog(pi, src)
  local shape = PROG_SHAPES[pi]
  if not shape then return -1 end
  local steps = {}
  for _, seg in ipairs(shape) do for _ = 1, seg[2] do steps[#steps + 1] = seg[1] end end
  local plen = #steps
  local L = math.max(1, math.floor(self.v["ockm-len"] or 16))
  local sc, root = self:scale(), math.floor(self.v["ockm-root"] or 9)
  local total, weight = 0, 0
  for i = 0, math.max(plen, L) - 1 do
    local j = i % L
    if self:get("ockm-pat-"..src.."-on", j) > 0 then
      local pc = math.floor(self:get("ockm-pat-"..src.."-note", j)) % 12
      local d = steps[(i % plen) + 1]
      local w = ((j % 4) == 0) and 1.5 or 1
      if self:get("ockm-pat-"..src.."-acc", j) > 0 then w = w * 1.3 end
      local rpc = (root + sc[(d % 7) + 1]) % 12
      local s3 = (root + sc[((d + 2) % 7) + 1]) % 12
      local s5 = (root + sc[((d + 4) % 7) + 1]) % 12
      if pc == rpc then total = total + 3 * w elseif pc == s3 or pc == s5 then total = total + 2 * w else total = total - w end
      weight = weight + w
    end
  end
  if weight == 0 then return nil end
  return total / weight
end

function ui:suggest_chords()
  local leader = self.v["ockm-leader"] or 0
  local src = (leader == 2) and "bass" or "lead"
  local what = (src == "lead") and "melody" or "bass line"
  if not self.ranking then
    local r = {}
    for pi = 1, #PROG_SHAPES do
      local sc = self:score_prog(pi, src)
      if not sc then self:say("the " .. what .. " has no notes yet: write some, then ask again"); return end
      r[#r + 1] = { pi - 1, sc }
    end
    table.sort(r, function(a, b) if a[2] ~= b[2] then return a[2] > b[2] end return a[1] < b[1] end)
    self.ranking, self.rank_at = r, 0
  end
  self.rank_at = (self.rank_at % #self.ranking) + 1
  local pick = self.ranking[self.rank_at]
  self.suggesting = true
  self:send("ockm-chord-prog", pick[1])
  self.suggesting = false
  local fit = math.floor(clamp((pick[2] + 1) / 4, 0, 1) * 100 + 0.5)
  self:say(string.format("suggestion %d of %d for the %s: %s, fits %d%%", self.rank_at, #self.ranking,
    what, (PROGS[pick[1] + 1] or { "" })[1], fit))
end

-- a stepper: back, the current choice (number, name, detail), forward
function ui:stepper(add, x, y, w, h, list, hook)
  local n = #list
  local v = math.floor(self.v[hook] or 0)
  add{ kind="arrow", x=x, y=y, w=44, h=h, dir=-1, on=(v > 0), tap=function() if v > 0 then self:send(hook, v - 1) end end }
  local item = list[v + 1] or { "" }
  add{ kind="preset", x=x + 50, y=y, w=w - 100, h=h, num=v + 1, label=type(item) == "table" and item[1] or item,
       sub=type(item) == "table" and item[2] or nil, sel=true }
  add{ kind="arrow", x=x + w - 44, y=y, w=44, h=h, dir=1, on=(v < n - 1), tap=function() if v < n - 1 then self:send(hook, v + 1) end end }
end

function ui:layout_compose(add)
  local half = (W - 32 - 16) / 2
  local rx = 16 + half + 16
  -- who leads, and the key
  add{ kind="text", x=16, y=118, w=300, h=12, label="mode: which part is yours (the others follow it)", size=10 }
  local lw = (half - 3 * 6) / 4
  for i, l in ipairs(LEADERS) do
    add{ kind="choice", x=16 + (i - 1) * (lw + 6), y=132, w=lw, h=44, label=l[2], small=true,
         disabled=l[3], sel=(not l[3]) and (self.v["ockm-leader"] or 0) == l[1], tap=(not l[3]) and function() self:set_leader(l[1]) end or nil }
  end
  add{ kind="text", x=rx, y=118, w=100, h=12, label="key", size=10 }
  local kw = (half - 11 * 3) / 12
  for k = 0, 11 do
    add{ kind="choice", x=rx + k * (kw + 3), y=132, w=kw, h=44, label=NOTES[k + 1], small=true, sel=(self.v["ockm-root"] == k),
         tap=function() self:send("ockm-root", k) end }
  end
  -- the chain, and the scale
  add{ kind="text", x=16, y=182, w=300, h=12, label="the chain", size=10 }
  local leader = self.v["ockm-leader"] or 0
  local order = ({ [0] = { "chord", "bass", "lead" }, [1] = { "lead", "chord", "bass" }, [2] = { "bass", "chord", "lead" },
                  [3] = { "chord", "bass", "lead" } })[leader] or { "chord", "bass", "lead" }
  local cw = (half - (#order - 1) * 22) / #order
  for i, p in ipairs(order) do
    local x = 16 + (i - 1) * (cw + 22)
    local tag
    if self:locked(p) then tag = "follows" else tag = "yours" end
    add{ kind="chain", x=x, y=196, w=cw, h=44, label=(p == "lead") and "melody" or p, sub=tag, lead=not self:locked(p) }
    if i < #order then add{ kind="text", x=x + cw + 5, y=208, w=14, h=16, label=(leader == 3) and "·" or ">", size=14 } end
  end
  add{ kind="text", x=rx, y=182, w=100, h=12, label="scale", size=10 }
  local sw = (half - 5 * 3) / 6
  for sc = 0, 5 do
    add{ kind="choice", x=rx + sc * (sw + 3), y=196, w=sw, h=44, label=SCALE_NAMES[sc + 1], small=true, sel=(self.v["ockm-scale"] == sc),
         tap=function() self:send("ockm-scale", sc) end }
  end
  -- one column per part
  local colw = (W - 32 - 24) / 3
  for ci, p in ipairs({ "chord", "bass", "lead" }) do
    local cx, cy = 16 + (ci - 1) * (colw + 12), 254
    local auto = self:part_auto(p)
    add{ kind="card", x=cx, y=cy, w=colw, h=H - cy - 8 }
    add{ kind="text", x=cx + 12, y=cy + 14, w=120, h=16, label=p, size=15, col="txt" }
    local mine = not self:locked(p)
    add{ kind="choice", x=cx + colw - 172, y=cy + 8, w=160, h=32, small=true, accent=mine, sel=mine,
         label=mine and "yours" or self:follows_what(p) }
    self:gen_controls(add, p, cx + 12, cy, colw - 24)
  end
end

-- a part's generator settings: the same on compose and on the part's own tab
function ui:gen_controls(add, p, ix, cy, iw, k)
  k = k or 1
  if self:mode() == 3 then
    add{ kind="text", x=ix, y=cy + k * 64, w=iw, h=k * 14, label="Manual: these notes are yours, edited by hand.", size=12 }
    add{ kind="text", x=ix, y=cy + k * 84, w=iw, h=k * 14, label="The generators are resting.", size=12 }
    add{ kind="text", x=ix, y=cy + k * 104, w=iw, h=k * 14, label="Pick a priority to let them write again.", size=12 }
    if self:part_empty(p) then
      add{ kind="btn", x=ix, y=cy + k * 132, w=iw, h=k * 52, label=START[p], accent=true, tap=function() self:start_part(p) end }
      add{ kind="text", x=ix, y=cy + k * 196, w=iw, h=k * 14, label="(or write it yourself on the " .. p .. " tab)", size=11 }
    end
  elseif p == "chord" then
    add{ kind="text", x=ix, y=cy + k * 52, w=iw, h=k * 12, label="progression", size=10 }
    self:stepper(add, ix, cy + k * 66, iw, k * 52, PROGS, "ockm-chord-prog")
    add{ kind="text", x=ix, y=cy + k * 124, w=iw, h=k * 12, label="rhythm", size=10 }
    self:stepper(add, ix, cy + k * 138, iw, k * 40, CHORD_RHY, "ockm-chord-rhythm")
    add{ kind="text", x=ix, y=cy + k * 184, w=iw, h=k * 12, label="spice", size=10 }
    local spw = (iw - 18) / 4
    for i, sp in ipairs(SPICE) do
      add{ kind="choice", x=ix + (i - 1) * (spw + 6), y=cy + k * 198, w=spw, h=k * 36, label=i .. " " .. sp[2], small=true,
           sel=(self.v["ockm-chord-type"] == sp[1]), tap=function() self:send("ockm-chord-type", sp[1]) end }
    end
    add{ kind="choice", x=ix, y=cy + k * 242, w=iw, h=k * 34, label="smooth voicing", accent=true, small=true, sel=(self.v["ockm-chord-smooth"] or 1) > 0,
         tap=function() self:send("ockm-chord-smooth", ((self.v["ockm-chord-smooth"] or 1) > 0) and 0 or 1) end }
    local leader = self.v["ockm-leader"] or 0
    if (leader == 0 or leader == 3) and self:part_empty("chord") then
      add{ kind="btn", x=ix, y=cy + k * 284, w=iw, h=k * 40, accent=true, label=START.chord, tap=function() self:start_part("chord") end }
    elseif leader == 1 or leader == 2 then
      add{ kind="btn", x=ix, y=cy + k * 284, w=iw, h=k * 40, accent=true,
           label=self.ranking and "next suggestion" or ((leader == 1) and "suggest chords for the melody" or "suggest chords for the bass"),
           tap=function() self:suggest_chords() end }
    end
  else
    local notes = {}
    for i, nm in ipairs(MONO_NOTES) do notes[i] = { nm } end
    add{ kind="text", x=ix, y=cy + k * 52, w=iw, h=k * 12, label="notes", size=10 }
    self:stepper(add, ix, cy + k * 66, iw, k * 52, notes, "ockm-"..p.."-notes")
    add{ kind="text", x=ix, y=cy + k * 124, w=iw, h=k * 12, label="rhythm", size=10 }
    self:stepper(add, ix, cy + k * 138, iw, k * 40, RHYTHMS, "ockm-"..p.."-rhythm")
    local lkey = "ockm-"..p.."-lock"
    local lw3 = (iw - 12) / 3
    for li, nm in ipairs({ "own rhythm", "on the kick", "fill gaps" }) do
      add{ kind="choice", x=ix + (li - 1) * (lw3 + 6), y=cy + k * 186, w=lw3, h=k * 34, label=nm, small=true,
           sel=(math.floor(self.v[lkey] or 0) == li - 1), tap=function() self:send(lkey, li - 1) end }
    end
    add{ kind="hbar", x=ix, y=cy + k * 228, w=iw, h=k * 34, hook="ockm-"..p.."-density", lo=0, hi=2, label="density", bold=true }
    local skey = "ockm-"..p.."-seed"
    local seed = math.floor(self.v[skey] or 0)
    if self:part_empty(p) then
      add{ kind="btn", x=ix, y=cy + k * 270, w=iw, h=k * 34, accent=true, label=START[p], tap=function() self:start_part(p) end }
    else
      add{ kind="btn", x=ix, y=cy + k * 270, w=(iw - 6) / 2, h=k * 34, label="mutate", tap=function() self:send(skey, seed + 1) end }
      add{ kind="btn", x=ix + (iw + 6) / 2, y=cy + k * 270, w=(iw - 6) / 2, h=k * 34, label="original", quiet=(seed == 0), tap=function() self:send(skey, 0) end }
    end
    local leader = self.v["ockm-leader"] or 0
    local leads = (leader == 1 and p == "lead") or (leader == 2 and p == "bass")
    local follows = (self.v["ockm-"..p.."-sync"] or 0) > 0
    add{ kind="text", x=ix, y=cy + k * 314, w=iw, h=k * 14, size=11,
         label=(leads and "leads the harmony" or (follows and "follows the chords" or "follows the key")) .. ((seed > 0) and ("  ·  variation " .. seed) or "") }
  end
end

-- is a synth part empty across the whole pattern?
function ui:part_empty(p)
  local L = math.max(1, math.floor(self.v["ockm-len"] or 16))
  for i = 0, L - 1 do
    if self:get("ockm-pat-"..p.."-on", i) > 0 then return false end
  end
  return true
end
-- start a part: hand it to its generator (auto) and make notes now
function ui:start_part(p)
  local leader = self.v["ockm-leader"] or 0
  if p == "chord" and (leader == 1 or leader == 2) then
    self:send("ockm-chord-mode", 0); self.ranking = nil; self:suggest_chords(); return
  end
  self:send("ockm-"..p.."-mode", 0)
  psend("ockm-"..p.."-gen", "bang", {})
  if self:mode() == 3 then self:send("ockm-"..p.."-mode", 1) end
  self:say(p .. " started on auto: change it on compose, or switch to manual to edit")
end

-- ------------------------------------------------------------------ patterns in use
function ui:is_used(n) return n == 0 or (math.floor((self.exists or 1) / 2 ^ n) % 2) == 1 end
function ui:set_used(n, on)
  local m = math.floor(self.exists or 1)
  local bit = math.floor(2 ^ n)
  local was = (math.floor(m / bit) % 2) == 1
  if was == on then return end
  self.exists = on and (m + bit) or (m - bit)
  self:dirty()
end
-- the lowest free slot, so numbers fill up in order
function ui:free_slot()
  for n = 1, 7 do if not self:is_used(n) then return n end end
  return nil
end
function ui:go_pattern(n)
  psend("ockm-want", "float", { n })
  if self.playing ~= 0 and n ~= self.cur then self.want = n end
end
function ui:layout_newpat(add)
  local cur = self.cur or 0
  local n = self:free_slot()
  add{ kind="zone", x=0, y=0, w=W, h=H, tap=function() self.sheet = nil end }
  local x, y, w, h = 200, 130, W - 400, 300
  add{ kind="sheet", x=x, y=y, w=w, h=h }
  if not n then
    add{ kind="text", x=x + 24, y=y + 28, w=w - 48, h=20, label="All 8 patterns are in use", size=20, col="txt" }
    add{ kind="text", x=x + 24, y=y + 64, w=w - 48, h=14, label="Clear one you don't need on the song tab, then try again.", size=13 }
    add{ kind="btn", x=x + 24, y=y + h - 76, w=(w - 56) / 2, h=52, label="go to the song tab", accent=true, tap=function() self.sheet = nil; self:open("song") end }
    add{ kind="btn", x=x + 32 + (w - 56) / 2, y=y + h - 76, w=(w - 56) / 2, h=52, label="cancel", quiet=true, tap=function() self.sheet = nil end }
    return
  end
  local when = (self.playing ~= 0) and " It starts at the next bar." or ""
  add{ kind="text", x=x + 24, y=y + 28, w=w - 48, h=20, label="New pattern in slot " .. (n + 1), size=20, col="txt" }
  add{ kind="text", x=x + 24, y=y + 64, w=w - 48, h=14, label="Pattern " .. (cur + 1) .. " stays as it is. Switching keeps your work,", size=13 }
  add{ kind="text", x=x + 24, y=y + 84, w=w - 48, h=14, label="and save keeps all 8 patterns." .. when, size=13 }
  local bw = (w - 48 - 16) / 3
  add{ kind="btn", x=x + 24, y=y + 140, w=bw, h=64, label="copy of " .. (cur + 1), accent=true, tap=function()
    self.sheet = nil
    psend("ockm-pattern-copy", "list", { cur, n }); self:set_used(n, true); self:go_pattern(n)
    self:say("pattern " .. (n + 1) .. ": a copy of pattern " .. (cur + 1) .. ". Change it, then save")
  end }
  add{ kind="btn", x=x + 32 + bw, y=y + 140, w=bw, h=64, label="start empty", tap=function()
    self.sheet = nil
    psend("ockm-pattern-clear", "float", { n }); self:set_used(n, false); self:go_pattern(n)
    self:say("pattern " .. (n + 1) .. ": empty, with the same sounds. Try a groove on the drums tab")
  end }
  add{ kind="btn", x=x + 40 + 2 * bw, y=y + 140, w=bw, h=64, label="cancel", quiet=true, tap=function() self.sheet = nil end }

end

-- ------------------------------------------------------------------ song
-- MPC style: a chain of steps, each a pattern and how many times it plays. One song per project.
function ui:send_song()
  local flat = {}
  for _, st in ipairs(self.song or {}) do flat[#flat + 1] = st[1]; flat[#flat + 1] = st[2] end
  if #flat == 0 then psend("ockm-song-list", "bang", {}) else psend("ockm-song-list", "list", flat) end
end
function ui:song_edit(fn, row)
  self.song = self.song or {}
  if row then self.song_sel = row - 1 end
  fn(self.song)
  self.song_sel = clamp(self.song_sel or 0, 0, math.max(0, #self.song - 1))
  self:send_song()
end

function ui:layout_song(add)
  local song = self.song or {}
  local sel = clamp(self.song_sel or 0, 0, math.max(0, #song - 1))
  local playing_song = self.playing ~= 0 and (self.v["ockm-song-mode"] or 0) > 0
  local LW = 560
  add{ kind="text", x=16, y=116, w=300, h=12, label="the song: " .. #song .. (#song == 1 and " step" or " steps") .. ", top to bottom", size=10 }
  local per = 9
  local pages = math.max(1, math.ceil(#song / per))
  self.song_page = clamp(self.song_page or 0, 0, pages - 1)
  if #song == 0 then
    add{ kind="text", x=24, y=150, w=LW, h=16, label="Empty. Tap a pattern on the right to add the first step.", size=14, col="txt" }
    add{ kind="text", x=24, y=176, w=LW, h=14, label="Each step plays one pattern, as many times as you set. Then the next step.", size=12 }
  end
  for k = 1, per do
    local i = self.song_page * per + k
    local st = song[i]
    if not st then break end
    local y = 132 + (k - 1) * 46
    local now = playing_song and self.song_pos and self.song_pos[1] == i - 1
    if sel == i - 1 then add{ kind="choice", x=16, y=y, w=LW, h=42, label="", sel=true }
    else add{ kind="card", x=16, y=y, w=LW, h=42 } end
    add{ kind="zone", x=16, y=y, w=LW, h=42, tap=function() self.song_sel = i - 1 end }
    add{ kind="text", x=26, y=y + 14, w=30, h=14, label=tostring(i), size=13, col=(sel == i - 1) and "bg" or "txt" }
    local function step_pat(d)
      local p = st[1]
      repeat p = p + d until p < 0 or p > 7 or self:is_used(p)
      if p >= 0 and p <= 7 then self:song_edit(function(l) l[i][1] = p end, i) end
    end
    add{ kind="arrow", x=60, y=y + 4, w=34, h=34, dir=-1, on=st[1] > 0, tap=function() step_pat(-1) end }
    add{ kind="btn", x=98, y=y + 4, w=104, h=34, label="pattern " .. (st[1] + 1), accent=now, tap=function() self.song_sel = i - 1 end }
    add{ kind="arrow", x=206, y=y + 4, w=34, h=34, dir=1, on=st[1] < 7, tap=function() step_pat(1) end }
    add{ kind="btn", x=262, y=y + 4, w=40, h=34, label="-", tap=function() self:song_edit(function(l) l[i][2] = math.max(1, l[i][2] - 1) end, i) end }
    add{ kind="text", x=310, y=y + 13, w=50, h=14, label="x " .. st[2], size=15, col=(sel == i - 1) and "bg" or "txt" }
    add{ kind="btn", x=360, y=y + 4, w=40, h=34, label="+", tap=function() self:song_edit(function(l) l[i][2] = math.min(64, l[i][2] + 1) end, i) end }
    if now then
      add{ kind="text", x=414, y=y + 14, w=90, h=14, label=(self.song_pos[2] + 1) .. " bar" .. ((self.song_pos[2] == 0) and "" or "s") .. " left", size=12, col="acc" }
    end
    add{ kind="btn", x=LW - 34, y=y + 4, w=40, h=34, label="x", quiet=true, tap=function() self:song_edit(function(l) table.remove(l, i) end) end }
  end
  if pages > 1 then
    add{ kind="arrow", x=16, y=550, w=60, h=40, dir=-1, on=self.song_page > 0, tap=function() self.song_page = self.song_page - 1 end }
    add{ kind="text", x=84, y=564, w=120, h=14, label="page " .. (self.song_page + 1) .. " of " .. pages, size=11 }
    add{ kind="arrow", x=200, y=550, w=60, h=40, dir=1, on=self.song_page < pages - 1, tap=function() self.song_page = self.song_page + 1 end }
  end
  if #song > 0 then
    add{ kind="btn", x=LW - 124, y=550, w=140, h=40, label=self.confirm == "song" and "tap again to clear" or "clear the song", quiet=self.confirm ~= "song", tap=function()
      if self.confirm == "song" then self.confirm = nil; self.song_sel = 0; self:song_edit(function(l) for j = #l, 1, -1 do l[j] = nil end end)
      else self.confirm = "song" end
    end }
  end
  -- right: how play works, adding steps, moving them, and pattern copy
  local rx, rw = 600, W - 616
  local hw = (rw - 8) / 2
  local sm = (self.v["ockm-song-mode"] or 0) > 0
  add{ kind="text", x=rx, y=116, w=rw, h=12, label="play button plays", size=10 }
  add{ kind="choice", x=rx, y=132, w=hw, h=48, label="one pattern", sel=not sm, tap=function() self:send("ockm-song-mode", 0) end }
  add{ kind="choice", x=rx + hw + 8, y=132, w=hw, h=48, label="the song", sel=sm, accent=true, tap=function() self:send("ockm-song-mode", 1) end }
  add{ kind="choice", x=rx, y=188, w=hw, h=40, small=true, label="loop at the end", sel=(self.v["ockm-song-loop"] or 1) > 0,
       tap=function() self:send("ockm-song-loop", ((self.v["ockm-song-loop"] or 1) > 0) and 0 or 1) end }
  add{ kind="btn", x=rx + hw + 8, y=188, w=hw, h=40, small=true, label=(#song > 0) and ("play from step " .. (sel + 1)) or "play from step", accent=(#song > 0),
       tap=function()
         if #song == 0 then return end
         self:send("ockm-song-mode", 1)
         if self.playing ~= 0 then self:send("ockm-play", 0) end
         psend("ockm-song-start", "float", { sel })
       end }
  add{ kind="text", x=rx, y=244, w=rw, h=12, label=(#song > 0) and ("add a step after step " .. (sel + 1) .. ": tap a pattern") or "add a step: tap a pattern", size=10 }
  local pw = (rw - 3 * 6) / 4
  local made = {}
  for n = 0, 7 do if self:is_used(n) then made[#made + 1] = n end end
  for k, n in ipairs(made) do
    local col, row = (k - 1) % 4, math.floor((k - 1) / 4)
    add{ kind="btn", x=rx + col * (pw + 6), y=260 + row * 50, w=pw, h=44, label=tostring(n + 1), tap=function()
      local at = (#song == 0) and 1 or (sel + 2)
      self:song_edit(function(l) table.insert(l, at, { n, 1 }) end)
      self.song_sel = at - 1
      if self.song_sel >= (self.song_page + 1) * per then self.song_page = math.floor(self.song_sel / per) end
    end }
  end
  add{ kind="btn", x=rx, y=366, w=hw, h=40, small=true, label="move step up", tap=function()
    if sel > 0 then self:song_edit(function(l) l[sel], l[sel + 1] = l[sel + 1], l[sel] end); self.song_sel = sel - 1 end
  end }
  add{ kind="btn", x=rx + hw + 8, y=366, w=hw, h=40, small=true, label="move step down", tap=function()
    if sel < #song - 1 then self:song_edit(function(l) l[sel + 1], l[sel + 2] = l[sel + 2], l[sel + 1] end); self.song_sel = sel + 1 end
  end }
  -- patterns: copy the one you're on to another slot, to make variations
  local cur = self.cur or 0
  add{ kind="text", x=rx, y=424, w=rw, h=12, label="copy pattern " .. (cur + 1) .. " (the one you're on) over:", size=10 }
  local cw8 = (rw - 7 * 4) / 8
  local k = 0
  for n = 0, 7 do
    if self:is_used(n) and n ~= cur then
      add{ kind="btn", x=rx + k * (cw8 + 4), y=440, w=cw8, h=40, small=true, label=tostring(n + 1), tap=function()
        psend("ockm-pattern-copy", "list", { cur, n }); self:say("pattern " .. (cur + 1) .. " copied over pattern " .. (n + 1))
      end }
      k = k + 1
    end
  end
  if k == 0 then add{ kind="text", x=rx, y=454, w=rw, h=12, label="(no other patterns yet: use + next to the pattern numbers)", size=11 } end
  add{ kind="btn", x=rx, y=490, w=rw, h=40, small=true, quiet=self.confirm ~= "pat",
       label=(self.confirm == "pat") and ("tap again to clear pattern " .. (cur + 1)) or ("clear pattern " .. (cur + 1)), tap=function()
    if self.confirm == "pat" then self.confirm = nil; psend("ockm-pattern-clear", "float", { cur }); self:say("pattern " .. (cur + 1) .. " cleared")
    else self.confirm = "pat" end
  end }
end

-- ------------------------------------------------------------------ setup (tap the tempo)
function ui:layout_setup(add)
  local bpm = math.floor(self.v["ockm-bpm"] or 124)
  add{ kind="text", x=16, y=80, w=200, h=12, label="tempo", size=10 }
  add{ kind="text", x=16, y=96, w=200, h=40, label=bpm .. " bpm", size=34, col="txt" }
  local steps = { -5, -1, 1, 5 }
  for i, d in ipairs(steps) do
    add{ kind="btn", x=230 + (i - 1) * 82, y=92, w=76, h=52, label=(d > 0 and "+" or "") .. d, tap=function() self:send("ockm-bpm", clamp(bpm + d, 40, 200)) end }
  end
  add{ kind="slider", x=16, y=156, w=W - 32, h=40, hook="ockm-bpm", lo=60, hi=180, label="tempo" }
  add{ kind="slider", x=16, y=212, w=W - 32, h=40, hook="ockm-swing", lo=50, hi=75, label="swing" }
  add{ kind="text", x=126, y=252, w=600, h=12, label="swing belongs to each pattern: 50 is straight, 58 is a gentle house shuffle, 66 is heavy", size=10 }
  add{ kind="slider", x=16, y=276, w=W - 32, h=40, hook="ockm-accent", lo=0, hi=1, label="accents" }
  add{ kind="text", x=126, y=316, w=600, h=12, label="how much quieter an ordinary hit is than an accented one", size=10 }
  add{ kind="slider", x=16, y=340, w=W - 32, h=40, hook="ockm-volume", lo=0, hi=1, label="volume" }
  add{ kind="text", x=16, y=404, w=300, h=12, label="MIDI clock", size=10 }
  local half = (W - 40) / 2
  local sync = math.floor(self.v["ockm-sync"] or 0)
  add{ kind="choice", x=16, y=420, w=half, h=52, label="lead: use my tempo, send clock out", sel=(sync == 0), tap=function() self:send("ockm-sync", 0) end }
  add{ kind="choice", x=24 + half, y=420, w=half, h=52, label="follow: play to incoming MIDI clock", sel=(sync == 1), tap=function() self:send("ockm-sync", 1) end }
  add{ kind="slider", x=16, y=484, w=W - 32, h=36, hook="ockm-verb-tone", lo=0, hi=1, label="reverb tone" }
  add{ kind="text", x=16, y=532, w=W - 32, h=12, label="tempo, accents, volume, reverb tone and MIDI clock belong to the project. Save to keep them", size=10 }
  add{ kind="text", x=16, y=552, w=W - 32, h=12, label="OCKM_GENERATOR " .. VERSION .. "  ·  project: " .. ockm_pretty(self.project), size=10 }
end

-- ------------------------------------------------------------------ projects
-- A project is a folder: 8 patterns plus the kit, tempo and effects. New ones get two random words and the date.
local WORDS_A = { "amber", "velvet", "copper", "hollow", "silver", "midnight", "dusty", "neon", "quiet", "golden", "lazy", "electric",
                  "crimson", "misty", "wild", "paper", "rusty", "cosmic", "frozen", "lucky", "deep", "salt", "sunny", "smoky",
                  "brass", "wooden", "liquid", "broken", "gentle", "secret", "orange", "indigo" }
local WORDS_B = { "heron", "fox", "harbour", "orchard", "comet", "lantern", "meadow", "engine", "badger", "river", "signal", "garden",
                  "falcon", "tunnel", "mirror", "kettle", "bridge", "otter", "planet", "violin", "marble", "pylon", "lighthouse", "magpie",
                  "cassette", "ferry", "thistle", "rocket", "lagoon", "beacon", "pebble", "wren" }
local MONTHS = { "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec" }
-- '2026-10-14-velvet-heron' -> 'velvet heron · 14 Oct'
function ockm_pretty(name)
  name = tostring(name or "default")
  local y, m, d, rest = name:match("^(%d%d%d%d)%-(%d%d)%-(%d%d)%-(.+)$")
  if not y then return (name:gsub("%-", " ")) end
  return rest:gsub("%-", " ") .. " · " .. tonumber(d) .. " " .. (MONTHS[tonumber(m)] or "")
end
function ui:new_name()
  local taken = {}
  for _, p in ipairs(self.projects or {}) do taken[p] = true end
  local date = os.date("%Y-%m-%d")
  for _ = 1, 50 do
    local n = date .. "-" .. WORDS_A[math.random(#WORDS_A)] .. "-" .. WORDS_B[math.random(#WORDS_B)]
    if not taken[n] then return n end
  end
  return date .. "-" .. os.date("%H%M%S")
end

function ui:layout_project(add)
  local cur = self.project or "default"
  add{ kind="text", x=16, y=80, w=300, h=12, label="open now", size=10 }
  add{ kind="text", x=16, y=96, w=W - 32, h=24, label=ockm_pretty(cur), size=22, col="txt" }
  add{ kind="text", x=16, y=130, w=W - 32, h=14, label=self.msg or "8 patterns, plus the drum kit, tempo and effects", size=11, col=self.msg and "acc" or nil }
  local bw = (W - 32 - 3 * 8) / 4
  local acts = {
    { "save", function() psend("ockm-save", "bang", {}); self:say("saved " .. ockm_pretty(cur) .. ": all 8 patterns, the song and the kit") end },
    { "back to last save", function() psend("ockm-revert", "bang", {}); self:say("back to the last save of " .. ockm_pretty(cur)) end },
    { "save as a copy", function()
        local n = self:new_name(); psend("ockm-project-saveas", "symbol", { n }); psend("ockm-project-list", "bang", {})
        self:say("saved a copy as " .. ockm_pretty(n) .. ". You're now working in the copy") end },
    { "new blank project", function()
        local n = self:new_name(); self.exists = 1; psend("ockm-project-new", "symbol", { n }); psend("ockm-project-list", "bang", {})
        self.pick = nil; self:say("new project: " .. ockm_pretty(n) .. ". The last one stays as you last saved it") end },
  }
  for i, a in ipairs(acts) do
    add{ kind="btn", x=16 + (i - 1) * (bw + 8), y=152, w=bw, h=52, label=a[1], accent=(i == 4), tap=a[2] }
  end
  -- every project, newest first
  local list = self.projects or {}
  add{ kind="text", x=16, y=222, w=300, h=12, label="your projects (" .. #list .. ")", size=10 }
  local cols, rows = 4, 4
  local per = cols * rows
  local pages = math.max(1, math.ceil(#list / per))
  self.ppage = clamp(self.ppage or 0, 0, pages - 1)
  local cw = (W - 32 - (cols - 1) * 8) / cols
  for k = 1, per do
    local name = list[self.ppage * per + k]
    if not name then break end
    local col, row = (k - 1) % cols, math.floor((k - 1) / cols)
    local is_cur = (name == cur)
    add{ kind="choice", x=16 + col * (cw + 8), y=238 + row * 52, w=cw, h=46, small=true,
         label=ockm_pretty(name) .. (is_cur and "  (open)" or ""), sel=(self.pick == name) or (self.pick == nil and is_cur),
         tap=function() self.confirm = nil; self.pick = (not is_cur) and name or nil end }
  end
  if pages > 1 then
    add{ kind="arrow", x=W - 112, y=216, w=44, h=20, dir=-1, on=self.ppage > 0, tap=function() self.ppage = self.ppage - 1 end }
    add{ kind="arrow", x=W - 60, y=216, w=44, h=20, dir=1, on=self.ppage < pages - 1, tap=function() self.ppage = self.ppage + 1 end }
  end
  -- what to do with the one you picked
  local p = self.pick
  if p then
    local y = H - 64
    add{ kind="text", x=16, y=y - 18, w=W - 32, h=12, label=ockm_pretty(p) .. ": open it, or delete it. Opening swaps out " .. ockm_pretty(cur), size=10 }
    local w3 = (W - 32 - 16) / 3
    add{ kind="btn", x=16, y=y, w=w3, h=52, label="save " .. ockm_pretty(cur):match("^[^·]+"):gsub("%s+$", "") .. ", then open", accent=true, tap=function()
      psend("ockm-save", "bang", {}); psend("ockm-project-open", "symbol", { p }); self.pick = nil; self:say("opened " .. ockm_pretty(p)) end }
    add{ kind="btn", x=16 + w3 + 8, y=y, w=w3, h=52, label="open without saving", tap=function()
      psend("ockm-project-open", "symbol", { p }); self.pick = nil; self:say("opened " .. ockm_pretty(p)) end }
    add{ kind="btn", x=16 + 2 * (w3 + 8), y=y, w=w3, h=52, label=(self.confirm == p) and "tap again to delete" or "delete", quiet=(self.confirm ~= p), tap=function()
      if self.confirm == p then
        psend("ockm-project-delete", "symbol", { p }); self.pick, self.confirm = nil, nil
        self:say(ockm_pretty(p) .. " moved to the trash folder")
      else self.confirm = p end
    end }
  end
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

function ui:drum_cycle(slot, step)
  local nm = SLOTS[slot]
  local v = self:get("ockm-pat-"..nm, step)
  local nv = (v <= 0) and 1 or ((v < 2) and 2 or 0)
  psend("ockm-edit", nm, { step, nv })
  self:dirty()
end
function ui:drum_tap(i) self:drum_cycle(self.slot, self:abs(i)) end

function ui:mono_get(i, f) return self:get("ockm-pat-"..SYNTHS[self.part].."-"..f, self:abs(i)) end
function ui:mono_write(i, note, on, acc, slide)
  local part = SYNTHS[self.part]
  psend("ockm-"..part.."-edit", "list", { self:abs(i), note, on, acc, slide })
  self:dirty()
end
function ui:mono_note_or_default(i)
  local n = self:mono_get(i, "note")
  if n <= 0 then n = self:deg_to_midi(SYNTHS[self.part], 0) end
  return n
end
function ui:mono_tap(i)
  self:claim(SYNTHS[self.part])
  self.sel_step = i
  local on, acc = self:mono_get(i, "on"), self:mono_get(i, "acc")
  local n_on, n_acc
  if on <= 0 then n_on, n_acc = 1, 0 elseif acc <= 0 then n_on, n_acc = 1, 1 else n_on, n_acc = 0, 0 end
  self:mono_write(i, self:mono_note_or_default(i), n_on, n_acc, self:mono_get(i, "slide"))
end
function ui:mono_set_deg(d)
  self:claim(SYNTHS[self.part])
  local i = self.sel_step
  local on = self:mono_get(i, "on")
  self:mono_write(i, self:deg_to_midi(SYNTHS[self.part], d), (on > 0) and on or 1, self:mono_get(i, "acc"), self:mono_get(i, "slide"))
end
function ui:mono_toggle_slide()
  self:claim(SYNTHS[self.part])
  local i = self.sel_step
  self:mono_write(i, self:mono_note_or_default(i), self:mono_get(i, "on"), self:mono_get(i, "acc"),
                  (self:mono_get(i, "slide") > 0) and 0 or 1)
end

function ui:chord_get(i, f) return self:get("ockm-pat-chord-"..f, self:abs(i)) end
function ui:chord_tap(i)
  self:claim(SYNTHS[self.part])
  self.sel_step = i
  local v = self:chord_get(i, "on")
  local nv = (v <= 0) and 1 or ((v < 2) and 2 or 0)
  psend("ockm-chord-edit", "list", { self:abs(i), nv, self:chord_get(i, "deg") })
  self:dirty()
end
function ui:chord_set_deg(d)
  self:claim(SYNTHS[self.part])
  local i = self.sel_step
  local v = self:chord_get(i, "on")
  psend("ockm-chord-edit", "list", { self:abs(i), (v > 0) and v or 1, d })
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
       or w.kind == "dstep" or w.kind == "mstep" or w.kind == "cstep" or w.kind == "pad") then return w end
  end
  return nil
end

function ui:press(x, y)
  local w = self:hit(x, y)
  self.touch = { w = w, x0 = x, y0 = y, mode = nil }
  if not w then return end
  if w.kind == "pad" then self.touch.mode = "pad"; self.pad_on = w.hook; psend(w.hook, "float", { 1 })
  elseif w.kind == "slider" or w.kind == "vfader" or w.kind == "hbar" then self.touch.mode = "slider"; self:slide(w, x, y)
  elseif w.kind == "bpm" then self.touch.v0 = self.v["ockm-bpm"] or 124
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
  if t.mode == nil and t.w.kind == "bpm" and math.abs(dy) > 8 then t.mode = "bpm" end
  if t.mode == "bpm" then
    self:send("ockm-bpm", clamp(math.floor(t.v0 - dy / 3 + 0.5), 40, 200)); return
  end
  if t.mode == nil and (math.abs(dx) > 24 or math.abs(dy) > 16) then
    if t.w.swipe and math.abs(dx) > math.abs(dy) then t.mode = "swipe"
    elseif (t.w.kind == "mstep" or t.w.kind == "cstep") and math.abs(dy) > math.abs(dx) and not self:locked() then t.mode = "note"
    else t.mode = "cancel" end
  end
  if t.mode == "note" then
    self:claim(SYNTHS[self.part])
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
  if t.mode == "pad" then
    self.pad_on = nil; psend(w.hook, "float", { 0 })
  elseif t.mode == "slider" and w.spring then
    psend("ockm-filter-glide", "list", { 0, 180 })     -- let go: glide back to off
  elseif t.mode == "swipe" then
    local dx = x - t.x0
    self:set_page(self.page + ((dx < 0) and 1 or -1))
  elseif t.mode == nil and inside(w, x, y) then
    if w.kind == "dstep" then self:drum_tap(w.i)
    elseif (w.kind == "mstep" or w.kind == "cstep") and self:locked() then
      self:say(SYNTHS[self.part] .. " " .. self:follows_what(SYNTHS[self.part]) .. ": set the mode to manual on compose to edit it")
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
  if k == "pad" then
    local on = (self.pad_on == w.hook)
    self:col(g, on and "acc" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, { x=w.x, y=w.y + 8, w=w.w, h=20 }, 14, on and "#ffffff" or "txt")
    self:ctext(g, w.sub or "", { x=w.x, y=w.y + 32, w=w.w, h=16 }, 10, on and "#ffffff" or "mute")
  elseif k == "key" then
    -- what the step colours mean
    local x = w.x + w.w - 290
    self:col(g, "on"); g:fill_rounded_rect(x, w.y, 12, 12, 3); self:text(g, "hit", x + 18, w.y - 1, 11, "mute", 40)
    self:col(g, "acc"); g:fill_rounded_rect(x + 60, w.y, 12, 12, 3); self:text(g, "accent (louder)", x + 78, w.y - 1, 11, "mute", 110)
    self:text(g, "tap a step to cycle", x + 190, w.y - 1, 11, "mute", 110)
  elseif k == "sheet" then
    self:col(g, "bg"); g:fill_rounded_rect(w.x - 4, w.y - 4, w.w + 8, w.h + 8, 14)
    self:col(g, "card"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 12)
    self:col(g, "acc"); g:stroke_rounded_rect(w.x, w.y, w.w, w.h, 12, 2)
  elseif k == "toast" then
    self:col(g, "txt"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 19)
    self:ctext(g, w.label, w, 13, "bg")
  elseif k == "btn" then
    self:col(g, w.accent and "acc" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, w, w.small and 12 or 14, w.accent and "#ffffff" or (w.quiet and "mute" or "txt"))
  elseif k == "tab" then
    self:col(g, w.sel and "on" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, w, 14, w.sel and "bg" or "txt")
  elseif k == "play" then
    local on = self.playing ~= 0
    self:col(g, on and "acc" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:col(g, on and "#ffffff" or "txt")
    local cx, cy = w.x + w.w / 2, w.y + w.h / 2
    local sm = (self.v["ockm-song-mode"] or 0) > 0
    if sm then cy = cy - 5 end
    if on then g:fill_rect(cx - 9, cy - 9, 18, 18)
    else local p = Path(cx - 7, cy - 11); p:line_to(cx + 11, cy); p:line_to(cx - 7, cy + 11); p:close(); g:fill_path(p) end
    if sm then
      local lab = "song"
      if on and self.song_pos and self.song then lab = "song " .. (self.song_pos[1] + 1) .. "/" .. #self.song end
      self:ctext(g, lab, { x=w.x, y=w.y + w.h - 20, w=w.w, h=14 }, 10, on and "#ffffff" or "txt")
    end
  elseif k == "bpm" then
    local s = fmt(self.v["ockm-bpm"] or 124)
    self:text(g, s, w.x + 4, w.y + 4, 32, "txt")
    self:text(g, "bpm", w.x + 8 + #s * 19, w.y + 26, 12, "mute")
    self:text(g, VERSION, w.x + 8 + #s * 19, w.y + 8, 9, "mute")
  elseif k == "text" then
    self:text(g, w.label, w.x, w.y, w.size or 12, w.col or "mute", w.w)
  elseif k == "pattern" then
    local playing = (w.n == self.cur)
    if playing or w.used == nil or w.used then self:col(g, playing and "on" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    else self:col(g, "off"); g:stroke_rounded_rect(w.x + 1, w.y + 1, w.w - 2, w.h - 2, 6, 1.5) end
    if self.want == w.n then self:col(g, "acc"); g:stroke_rounded_rect(w.x + 1, w.y + 1, w.w - 2, w.h - 2, 6, 2) end
    self:ctext(g, string.format("%d", math.floor(w.n + 1)), w, (w.h > 44) and 22 or 13, playing and "bg" or ((w.used == false) and "mute" or "txt"))
  elseif k == "choice" then
    local sel = w.sel
    self:col(g, sel and (w.accent and "acc" or "on") or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, w, w.small and 11 or 13, sel and (w.accent and "#ffffff" or "bg") or (w.disabled and "mute" or "txt"))
  elseif k == "card" then
    self:col(g, "card"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 8)
  elseif k == "locked" then
    self:col(g, "card"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, w, 12, "mute")
  elseif k == "chain" then
    self:col(g, w.lead and "on" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, { x=w.x, y=w.y + 5, w=w.w, h=16 }, 13, w.lead and "bg" or "txt")
    self:ctext(g, w.sub, { x=w.x, y=w.y + 25, w=w.w, h=12 }, 9, w.lead and "bg" or "mute")
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
  elseif k == "steprow" or k == "stripname" or k == "pcell" then
    -- nothing to draw: it only catches swipes between the pads
  elseif k == "dstep" then
    local v = self:get("ockm-pat-"..SLOTS[self.slot], self:abs(w.i))
    self:col(g, (v >= 2) and "acc" or ((v > 0) and "on" or "off")); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    if w.i % 4 == 0 then self:col(g, "mute"); g:fill_rect(w.x, w.y + w.h + 4, w.w, 2) end
  elseif k == "mstep" then
    local on, acc = self:mono_get(w.i, "on"), self:mono_get(w.i, "acc")
    local auto = self:locked()
    local c = (on > 0) and ((acc > 0) and "acc" or "on") or "off"
    if auto then
      -- on auto the generator wrote these: outlines, locked
      self:col(g, "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
      if on > 0 then self:col(g, c); g:stroke_rounded_rect(w.x + 1, w.y + 1, w.w - 2, w.h - 2, 6, 2) end
    else
      self:col(g, c); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    end
    if on > 0 then
      local m = self:mono_get(w.i, "note")
      local tc = auto and ((acc > 0) and "acc" or "txt") or ((acc > 0) and "#ffffff" or "bg")
      self:ctext(g, self:note_name(m), w, 15, tc, -8)
      self:ctext(g, tostring(math.floor(m / 12) - 1), w, 11, tc, 12)
      if self:mono_get(w.i, "slide") > 0 then self:col(g, "acc"); g:fill_rect(w.x + w.w - 2, w.y + w.h / 2 - 3, 10, 6) end
    end
    if w.i == self.sel_step and not auto then self:col(g, "mute"); g:stroke_rounded_rect(w.x - 2, w.y - 2, w.w + 4, w.h + 4, 7, 2) end
    if w.i % 4 == 0 then self:col(g, "mute"); g:fill_rect(w.x, w.y + w.h + 4, w.w, 2) end
  elseif k == "cstep" then
    local v = self:chord_get(w.i, "on")
    local auto = self:locked()
    local c = (v >= 2) and "acc" or ((v > 0) and "on" or "off")
    if auto then
      self:col(g, "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
      if v > 0 then self:col(g, c); g:stroke_rounded_rect(w.x + 1, w.y + 1, w.w - 2, w.h - 2, 6, 2) end
    else
      self:col(g, c); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    end
    if v > 0 then self:ctext(g, ROMAN[(math.floor(self:chord_get(w.i, "deg")) % 7) + 1], w, 15, auto and ((v >= 2) and "acc" or "txt") or ((v >= 2) and "#ffffff" or "bg")) end
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
