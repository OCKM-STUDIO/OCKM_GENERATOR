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
local VERSION = "v0.80"   -- shown on screen, so you can tell which version plugdata has loaded

local THEMES = {
  dark  = { bg="#141414", card="#1e1e1e", off="#2a2a2a", on="#ededed", acc="#ff5a24", mute="#7a7a7a", txt="#ededed", dim="#3a3a3a", beat="#383838" },
  light = { bg="#f4f3ef", card="#ffffff", off="#e4e2dc", on="#1a1a1a", acc="#ff4f1a", mute="#9a9890", txt="#1a1a1a", dim="#cfccc4", beat="#d6d3cc" },
}

local SLOTS   = { "d1","d2","d3","d4","d5","d6","d7","d8" }
local SOUNDS  = { "kick","snare","clap","perc 1","closed hat","open hat","tom","perc 2" }
local START = { bass = "start the bass line", lead = "start a melody", chord = "start the chords" }
local SHORT   = { "kick","snare","clap","perc 1","hat","open hat","tom","perc 2" }
-- sample folders (same order as ockm-sample-counts), and which folder each sound plays from
local FOLDERS   = { "kick","snare","clap","perc","hat","open hat","tom" }
local SOUND_DIR = { 1, 2, 3, 4, 5, 6, 7, 4 }   -- perc 1 and perc 2 share the perc folder
local SYNTHS  = { "bass","lead","chord" }
local TRACKS  = { "d1","d2","d3","d4","d5","d6","d7","d8","bass","lead","chord" }
local NOTES   = { "C","C#","D","D#","E","F","F#","G","G#","A","A#","B" }
local SCALES  = { {0,2,3,5,7,8,10}, {0,2,4,5,7,9,11}, {0,2,3,5,7,9,10}, {0,1,3,5,7,8,10}, {0,2,4,5,7,9,10}, {0,2,3,5,7,8,11} }
local SCALE_NAMES = { "minor","major","dorian","phrygian","mixo","harm min" }
local MONO_ENG  = { "acid","sub 808","fm","reese","pluck","analogue","donk" }
-- the order the bass engines are shown in: analogue (the default) first, then by family
local MONO_ORDER = { 5, 1, 0, 3, 2, 4, 6 }
-- the lead has its own engines. Numbers match ockm-lead-engine; LEAD_ORDER is the order they're shown in
local LEAD_ENG  = { "acid","juno","dx","sync","mini" }
local LEAD_ORDER = { 4, 1, 2, 0, 3 }
local CHORD_ENG = { "stab","organ","pad","piano","rhodes","strings" }
local function engines_of(part) if part == "chord" then return CHORD_ENG elseif part == "lead" then return LEAD_ENG end return MONO_ENG end
local KNOBS = {
  acid  = {"cutoff","resonance","env amount","decay"},
  ["sub 808"] = {"tone","drive","pitch drop","decay"},
  fm    = {"brightness","ratio","env","decay"},
  reese = {"cutoff","detune","env amount","decay"},
  pluck = {"brightness","saw-square","snap","decay"},
  analogue = {"cutoff","saw-square","envelope","decay"},
  donk  = {"brightness","bounce","hollow","decay"},
  stab  = {"brightness","detune","snap","length"},
  organ = {"drawbars","click","sub","length"},
  pad   = {"brightness","detune","attack","length"},
  mini  = {"cutoff","emphasis","contour","decay"},
  juno  = {"cutoff","pulse width","chorus","decay"},
  dx    = {"brightness","character","detune","decay"},
  sync  = {"sync","tone","sweep","decay"},
  piano = {"brightness","octave","snap","length"},
  rhodes = {"tone","bark","tremolo","length"},
  strings = {"tone","ensemble","attack","release"},
}
-- BEGIN PRESETS (written by tools/build.py from its preset lists: edit them there, not here)
local RHYTHMS = { { "offbeat" }, { "rolling" }, { "gallop" }, { "acid classic" }, { "sparse dub" }, { "tech bounce" }, { "acid 16ths" }, { "trip hop" }, { "hook" }, { "sparse melody" }, { "phrase" }, { "question answer" }, { "pickup" }, { "arp gate" } }
local BASS_RHYTHMS = { { "offbeat donk" }, { "straight 8ths" }, { "rolling 16ths" }, { "dotted 8ths" }, { "octave jump" }, { "sustained" }, { "quarters" }, { "dembow" }, { "two step" }, { "3 2 3 cluster" }, { "round the kick" }, { "gallop" }, { "acid classic" }, { "acid 16ths" }, { "tech bounce" }, { "sparse dub" }, { "trip hop" }, { "speed garage" } }
local MONO_NOTES = { "root", "octaves", "root fifth", "acid riff", "walk up", "minor stab", "dub", "pedal", "arp up", "arp updown", "call", "descend", "melody", "melody steps", "melody high", "motif", "motif call", "motif high", "arp evolve" }
local CHORD_RHY = { { "bar pads" }, { "two beat" }, { "offbeat" }, { "dub stabs" }, { "house organ" }, { "tresillo" }, { "syncopated" }, { "garage skip" }, { "call answer" }, { "eighths" } }
local PROGS = { { "one chord", "i" }, { "vamp", "i iv" }, { "dub techno", "i . . VII" }, { "deep house", "i iv VI v" }, { "garage", "i VI iv v" }, { "pop", "i VI III VII" }, { "uplift", "VI VII i" }, { "andalusian", "i VII VI V" }, { "trip hop", "i VII VI v" }, { "soul", "ii V I" } }
local SPICE = { { 0, "triad" }, { 1, "7th" }, { 6, "9th" }, { 7, "11th" } }
local FILLS = { "snare roll", "tom run", "drop", "build", "breakbeat" }
local GROOVES = { "four floor", "house", "deep house", "tech house", "minimal", "techno", "dub techno", "garage", "breakbeat", "boom bap", "trip hop", "electro", "clear", "chicago", "jackin", "disco", "soulful", "afro house", "lofi house", "2 step", "speed garage", "funky house", "ghetto house", "nu disco", "rolling", "detroit", "berlin", "industrial", "hypnotic", "acid techno", "think break", "jungle", "big beat", "downtempo", "one drop", "half time", "lofi hip hop", "hard house", "dnb two step", "dnb rolling" }
local GROOVE_BANKS = { { "classics", 0 }, { "house + garage", 13 }, { "techno + breaks", 25 }, { "hard + fast", 37 } }
local CHORD_TYPES = { { 0, 2, 4, -1 }, { 0, 2, 4, 6 }, { 0, 1, 4, -1 }, { 0, 4, 7, -1 }, { 0, 3, 4, -1 }, { 0, 2, 4, 5 }, { 0, 2, 6, 8 }, { 0, 6, 8, 10 } }
local PROG_SHAPES = { { { 0, 16 } }, { { 0, 16 }, { 3, 16 } }, { { 0, 48 }, { 6, 16 } }, { { 0, 16 }, { 3, 16 }, { 5, 16 }, { 4, 16 } }, { { 0, 8 }, { 5, 8 }, { 3, 8 }, { 4, 8 } }, { { 0, 16 }, { 5, 16 }, { 2, 16 }, { 6, 16 } }, { { 5, 16 }, { 6, 16 }, { 0, 32 } }, { { 0, 16 }, { 6, 16 }, { 5, 16 }, { 4, 16 } }, { { 0, 32 }, { 6, 32 }, { 5, 32 }, { 4, 32 } }, { { 1, 16 }, { 4, 16 }, { 0, 32 } } }
-- END PRESETS
-- the rhythm list for a part (the bass has its own, the classic dance bass rhythms)
local function rhythms_for(part) return (part == "bass") and BASS_RHYTHMS or RHYTHMS end
local ROMAN = { "i","ii","iii","iv","v","vi","vii" }
local OCT_OFFSET = { bass = 0, lead = 24 }   -- matches ockm-monogen args
local LFO_SHAPES = { "sine", "triangle", "square", "saw", "random" }
local CHORUS = { "off", "I", "II", "I+II" }
local LFO_RATES = { "1/16", "1/8", "beat", "1/2 bar", "bar", "2 bars", "4 bars", "8 bars" }

-- every drum slot setting the screen listens to; the sliders shown depend on synth or sample
local DRUM_PARAMS = {
  { "level", 0, 1 }, { "tune", -12, 12 }, { "decay", 10, 400 }, { "verb", 0, 1, "reverb" }, { "delay", 0, 1 },
  { "tone", -1, 1 }, { "drive", 0, 1 }, { "start", 0, 1 }, { "synth", 0, 2 },
  { "labchar", -1, 1 }, { "labmorph", 0, 1 }, { "labrseed", 0, 99999 }, { "labramt", 0, 1 }, { "labpseed", 0, 99999 },
}
local SYNTH_SLIDERS  = { { "level", 0, 1 }, { "tune", -12, 12 }, { "decay", 10, 400 }, { "tone", -1, 1 }, { "drive", 0, 1 } }
local SAMPLE_SLIDERS = { { "level", 0, 1 }, { "tune", -12, 12, "pitch" }, { "decay", 10, 100, "length" }, { "tone", -1, 1 }, { "start", 0, 1 } }
-- the built-in sounds are the drum lab's. Each drum has one; the perc slots choose rim, conga or shaker (ockm-<slot>-synth 0-2)
local LAB_SOUND = { [0] = "kick", [1] = "snare", [2] = "clap", [4] = "closed hat", [5] = "open hat", [6] = "tom" }
local LAB_PERC = { [3] = { "rim", "conga", "shaker" }, [7] = { "conga", "shaker", "rim" } }
-- what the character slider is called for each sound (its recipe in the lab)
local LAB_CHAR = { kick = "punch", snare = "crack", clap = "room", ["closed hat"] = "metal", ["open hat"] = "metal", tom = "boom",
                   rim = "wood", conga = "slap", shaker = "shake" }

-- ------------------------------------------------------------------ helpers
local function hex(c)
  return tonumber(c:sub(2,3),16), tonumber(c:sub(4,5),16), tonumber(c:sub(6,7),16)
end
-- every message out goes through psend, so the save button knows when there are unsaved changes
local UI_NOW
local NOT_CHANGES = { ["ockm-play"]=1, ["ockm-want"]=1, ["ockm-page"]=1, ["ockm-save"]=1, ["ockm-revert"]=1, 
  ["ockm-project-list"]=1, ["ockm-project-open"]=1, ["ockm-project-new"]=1, ["ockm-project-saveas"]=1, ["ockm-project-delete"]=1,
  ["ockm-resync"]=1, ["ockm-snapshot"]=1, ["ockm-usb-scan"]=1, ["ockm-exports-ask"]=1, ["ockm-mkdir"]=1, ["ockm-rec-stop"]=1, ["ockm-filter"]=1, ["ockm-filter-glide"]=1, ["ockm-delay-throw"]=1 }
local function psend(name, sel, atoms)
  if UI_NOW and not NOT_CHANGES[name] and not name:match("^ockm%-rec%-") and not name:match("%-mute$") and not name:match("%-mute%-q$") and not name:match("%-solo$") and not name:match("%-audition$")
     and name ~= "ockm-samples-scan" then UI_NOW.unsaved = true end
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
  v["ockm-volume"] = 1; v["ockm-verb-mix"] = 0.3; v["ockm-delay-mix"] = 0.5
  v["ockm-drive"] = 0; v["ockm-delay-fb"] = 0.4; v["ockm-delay-steps"] = 3; v["ockm-verb-size"] = 0.6; v["ockm-verb-tone"] = 0.5
  for _, t in ipairs(SYNTHS) do v["ockm-"..t.."-level"] = 1 end
  for _, t in ipairs(TRACKS) do
    v["ockm-"..t.."-lowcut"] = 20; v["ockm-"..t.."-eqlow"] = 0; v["ockm-"..t.."-eqmid"] = 0; v["ockm-"..t.."-eqmidf"] = 400; v["ockm-"..t.."-eqhigh"] = 0
  end
  v["ockm-bass-on"] = 1; v["ockm-lead-on"] = 1; v["ockm-chord-on"] = 1; v["ockm-drums-on"] = 1; v["ockm-turn-every"] = 0; v["ockm-bass-walk"] = 0; v["ockm-lead-freedom"] = 1; v["ockm-rise"] = 0; v["ockm-end"] = 0; v["ockm-impact"] = 0; v["ockm-pump"] = 0
  v["ockm-bass-scshape"] = 1; v["ockm-lead-scshape"] = 1; v["ockm-chord-scshape"] = 1
  v["ockm-style"] = -1; v["ockm-bass-half"] = 0; v["ockm-lead-half"] = 0; v["ockm-chord-half"] = 0
  v["ockm-bass-mode"] = 0; v["ockm-lead-mode"] = 0; v["ockm-chord-mode"] = 0   -- 0 auto, 1 manual
  v["ockm-bass-sync"] = 1; v["ockm-lead-sync"] = 1; v["ockm-leader"] = 0; v["ockm-drum-groove"] = -1
  v["ockm-drum-len"] = 16; v["ockm-bass-len"] = 64; v["ockm-lead-len"] = 64; v["ockm-chord-len"] = 64
  v["ockm-drum-loop"] = 0; v["ockm-fill-every"] = 0; v["ockm-fill-style"] = 0; v["ockm-swing"] = 56; v["ockm-accent"] = 0.3; v["ockm-sync"] = 0; v["ockm-volume"] = 1
  for _, p in ipairs({ "bass", "lead" }) do v["ockm-"..p.."-lock"] = 0; v["ockm-"..p.."-density"] = 1; v["ockm-"..p.."-seed"] = 0 end
  v["ockm-bpm"] = 124; v["ockm-len"] = 128; v["ockm-filter"] = 0; v["ockm-root"] = 9; v["ockm-scale"] = 0
  for i, nm in ipairs(SLOTS) do
    v["ockm-"..nm.."-sound"] = ({0,1,2,4,5,7,3,6})[i]
    v["ockm-"..nm.."-level"] = 1; v["ockm-"..nm.."-tune"] = 0; v["ockm-"..nm.."-decay"] = 100
    v["ockm-"..nm.."-verb"] = 0; v["ockm-"..nm.."-delay"] = 0; v["ockm-"..nm.."-sample"] = 0; v["ockm-"..nm.."-synth"] = 0
    v["ockm-"..nm.."-tone"] = 0; v["ockm-"..nm.."-drive"] = 0; v["ockm-"..nm.."-start"] = 0
    v["ockm-"..nm.."-labchar"] = 0; v["ockm-"..nm.."-labmorph"] = 0; v["ockm-"..nm.."-labrseed"] = 0; v["ockm-"..nm.."-labramt"] = 0; v["ockm-"..nm.."-labpseed"] = 1
  end
  for _, t in ipairs(SYNTHS) do
    for _, k in ipairs({"engine","k1","k2","k3","k4","drive","verb","delay","rhythm","notes","type","prog"}) do v["ockm-"..t.."-"..k] = 0 end
    v["ockm-"..t.."-chorus"] = 0; v["ockm-"..t.."-lfo-shape"] = 0; v["ockm-"..t.."-lfo-rate"] = 4; v["ockm-"..t.."-lfo-depth"] = 0; v["ockm-"..t.."-lfo-target"] = 1
  end
end

function ui:hooks()
  local h = { "ockm-bpm","ockm-len","ockm-root","ockm-scale","ockm-filter" }
  for _, nm in ipairs(SLOTS) do
    for _, p in ipairs(DRUM_PARAMS) do h[#h+1] = "ockm-"..nm.."-"..p[1] end
    h[#h+1] = "ockm-"..nm.."-sound"; h[#h+1] = "ockm-"..nm.."-sample"
  end
  for _, t in ipairs({"bass","lead"}) do
    for _, k in ipairs({"engine","k1","k2","k3","k4","drive","verb","delay","rhythm","notes"}) do h[#h+1] = "ockm-"..t.."-"..k end
  end
  for _, k in ipairs({"engine","k1","k2","k3","k4","type","smooth","verb","delay","rhythm","prog","voicing","strum"}) do h[#h+1] = "ockm-chord-"..k end
  for _, t in ipairs(SYNTHS) do for _, k in ipairs({ "lfo-shape", "lfo-rate", "lfo-depth", "lfo-target", "chorus" }) do h[#h+1] = "ockm-"..t.."-"..k end end
  for _, t in ipairs(TRACKS) do h[#h+1] = "ockm-"..t.."-mute"; h[#h+1] = "ockm-"..t.."-solo" end
  for _, t in ipairs(SYNTHS) do h[#h+1] = "ockm-"..t.."-level"; h[#h+1] = "ockm-"..t.."-mode" end
  for _, t in ipairs(SYNTHS) do h[#h+1] = "ockm-"..t.."-on" end
  for _, t in ipairs(TRACKS) do for _, k in ipairs({ "lowcut", "eqlow", "eqmid", "eqmidf", "eqhigh" }) do h[#h+1] = "ockm-"..t.."-"..k end end
  h[#h+1] = "ockm-rise"; h[#h+1] = "ockm-end"; h[#h+1] = "ockm-impact"; h[#h+1] = "ockm-pump"
  h[#h+1] = "ockm-bass-sync"; h[#h+1] = "ockm-lead-sync"; h[#h+1] = "ockm-leader"; h[#h+1] = "ockm-drum-groove"
  for _, p in ipairs({ "bass", "lead" }) do
    for _, k in ipairs({ "lock", "density", "seed" }) do h[#h+1] = "ockm-"..p.."-"..k end
  end
  for _, k in ipairs({ "ockm-drum-len", "ockm-bass-len", "ockm-lead-len", "ockm-chord-len" }) do h[#h+1] = k end
  for _, k in ipairs({ "ockm-drum-loop", "ockm-swing", "ockm-accent", "ockm-sync", "ockm-fill-every", "ockm-fill-style" }) do h[#h+1] = k end
  for _, k in ipairs({ "ockm-drums-on", "ockm-turn-every", "ockm-bass-walk", "ockm-lead-freedom", "ockm-bass-sidechain", "ockm-lead-sidechain", "ockm-chord-sidechain",
                         "ockm-style", "ockm-bass-half", "ockm-lead-half", "ockm-chord-half",
                         "ockm-bass-scshape", "ockm-lead-scshape", "ockm-chord-scshape" }) do h[#h+1] = k end
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
  for _, t in ipairs(TRACKS) do listen("ockm-"..t.."-mute", function(o) if o.mpend then o.mpend[t] = nil end end) end
  listen("ockm-project-name", function(o, sel, a) o.project = tostring(a[1] or "default"); o:dirty() end)
  listen("ockm-project-list-start", function(o) o.incoming = {} end)
  listen("ockm-filter-now", function(o, sel, a)
    local t = o.touch
    if t and t.w and t.w.hook == "ockm-filter" then return end
    local f = tonumber(a[1]) or 0
    if o.filter_springing then          -- on its way back to off: the screen already shows it there
      if f == 0 then o.filter_springing = nil end
      return
    end
    o.v["ockm-filter"] = f; o:dirty()
  end)
  self.roleclock = pd.Clock:new():register(self, "check_roles")
  listen("ockm-refresh", function(o) if o.roleclock then o.roleclock:delay(0) end end)
  listen("ockm-sample-counts", function(o, sel, a)
    o.scount = {}
    for k = 1, #FOLDERS do o.scount[k] = math.floor(tonumber(a[k]) or 0) end
    o.snames = o.snames or {}
    for k = 1, #FOLDERS do   -- forget names past the end (files removed since the last scan)
      local t = o.snames[k] or {}
      for n in pairs(t) do if n > o.scount[k] then t[n] = nil end end
      o.snames[k] = t
    end
    o:dirty()
  end)
  -- each sample's file name (v0.77): folder 0-6, sample number, name. Kits are files called kit-<name>
  listen("ockm-sample-name", function(o, sel, a)
    local f, n = math.floor(tonumber(a[1]) or -1) + 1, math.floor(tonumber(a[2]) or 0)
    if f < 1 or f > #FOLDERS or n < 1 then return end
    local parts = {}
    for k = 3, #a do parts[#parts + 1] = tostring(a[k]) end
    o.snames = o.snames or {}
    o.snames[f] = o.snames[f] or {}
    o.snames[f][n] = table.concat(parts, " ")
  end)
  listen("ockm-spec", function(o, sel, a)
    -- "d4 7 63.5" arrives with the track name as the selector
    local t, b, db = tostring(sel), math.floor(tonumber(a[1]) or 0), tonumber(a[2]) or 0
    o.spec = o.spec or {}; o.spec[t] = o.spec[t] or {}
    o.spec[t][b] = 0.7 * (o.spec[t][b] or db) + 0.3 * db
    if o.listening then
      local acc = o.listening[t] or {}; o.listening[t] = acc
      acc[b] = (acc[b] or 0) + 10 ^ (db / 10); acc["n" .. b] = (acc["n" .. b] or 0) + 1
    end
    if b == 7 and o.sheet == "eq" then o:dirty() end
  end)
  listen("ockm-exports-dir", function(o, sel, a) o.exports_dir = tostring(a[1]) end)
  listen("ockm-usb-list-start", function(o) o.usb_in = {} end)
  listen("ockm-usb-item", function(o, sel, a)
    local pth = tostring(a[1]); local nm = pth:match("[^/]+$") or ""
    if o.usb_in and not USB_SKIP[nm] and not nm:match("^com%.apple") then o.usb_in[#o.usb_in + 1] = pth end
  end)
  listen("ockm-usb-list-end", function(o) o.usb = o.usb_in or {}; o.usb_in = nil; o:dirty() end)
  listen("ockm-playing", function(o, sel, a)
    if o.exporting and o.exporting.song and (tonumber(a[1]) or 0) == 0 and not o.exporting.tail then o:export_end() end
  end)
  listen("ockm-project-name", function(o) if o.new_pending then o.new_pending = nil; if o.newclock then o.newclock:delay(300) end end end)
  for _, n in ipairs({ "ockm-saved", "ockm-revert", "ockm-project-name" }) do listen(n, function(o) o.unsaved = false; o:dirty() end) end
  for _, n in ipairs({ "ockm-revert", "ockm-project-name" }) do listen(n, function(o) o.undo_label = nil end) end
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
  self.audclock = pd.Clock:new():register(self, "audition")
  self.flashclock = pd.Clock:new():register(self, "flash_off")
  self.prevclock = pd.Clock:new():register(self, "preview_fire")
  self.jobclock = pd.Clock:new():register(self, "job_step")
  self.expclock = pd.Clock:new():register(self, "export_end")
  self.tickclock = pd.Clock:new():register(self, "tick")
  self.demudclock = pd.Clock:new():register(self, "demud_finish")
  self.rampclock = pd.Clock:new():register(self, "ramp_tick")
  self.newclock = pd.Clock:new():register(self, "apply_new_defaults")
  self.initclock = pd.Clock:new():register(self, "init_sends")
  self:load_settings()
end

-- play a drum slot once. After a sample change it waits a moment, so the new file is loaded first
function ui:audition(slot)
  local s = slot or self.aud_slot
  if s then psend("ockm-"..SLOTS[s].."-audition", "float", { 1 }) end
end
function ui:audition_soon(slot) self.aud_slot = slot; if self.audclock then self.audclock:delay(30) end end
function ui:sample_count(slot)
  local snd = math.floor(self.v["ockm-"..SLOTS[slot].."-sound"] or 0)
  return (self.scount or {})[SOUND_DIR[snd + 1]] or 0
end
-- your saved drum sounds: the slot settings each one keeps
local SOUND_KEYS = { "labchar", "labmorph", "labrseed", "labramt", "labpseed", "tune", "decay", "tone", "drive" }
local SOUND_DEF = { labchar = 0, labmorph = 0, labrseed = 0, labramt = 0, labpseed = 1, tune = 0, decay = 100, tone = 0, drive = 0 }
-- which lab voice a slot plays (closed and open hats share the hat)
function ui:voice_type(slot)
  local n = self:synth_name(slot)
  return (n == "closed hat" or n == "open hat") and "hat" or n
end
-- the saved sounds a slot can play: its voice, or for perc any of rim, conga and shaker
function ui:presets_for(slot)
  local snd = math.floor(self.v["ockm-"..SLOTS[slot].."-sound"] or 0)
  local ok = {}
  if LAB_PERC[snd] then for _, t in ipairs(LAB_PERC[snd]) do ok[t] = true end else ok[self:voice_type(slot)] = true end
  local out = {}
  for i, p in ipairs((self.me and self.me.sounds) or {}) do if ok[p.type] then out[#out + 1] = i end end
  return out
end
-- the saved sound this slot is playing right now, if any (index into self.me.sounds)
function ui:current_preset(slot)
  local nm = SLOTS[slot]
  if math.floor(self.v["ockm-"..nm.."-sample"] or 0) > 0 then return nil end
  local t = self:voice_type(slot)
  for _, i in ipairs(self:presets_for(slot)) do
    local p = self.me.sounds[i]
    if p.type == t then
      local same = true
      for _, k in ipairs(SOUND_KEYS) do
        if math.abs((self.v["ockm-"..nm.."-"..k] or SOUND_DEF[k]) - (p[k] or SOUND_DEF[k])) > 0.001 then same = false; break end
      end
      if same then return i end
    end
  end
  return nil
end
function ui:apply_preset(slot, i)
  local nm, p = SLOTS[slot], self.me.sounds[i]
  local snd = math.floor(self.v["ockm-"..nm.."-sound"] or 0)
  self:send("ockm-"..nm.."-sample", 0)
  if LAB_PERC[snd] then for j, t in ipairs(LAB_PERC[snd]) do if t == p.type then self:send("ockm-"..nm.."-synth", j - 1) end end end
  for _, k in ipairs(SOUND_KEYS) do self:send("ockm-"..nm.."-"..k, p[k] or SOUND_DEF[k]) end
end
-- save this slot's synth sound, named by its voice and the next free number ("kick 3")
function ui:save_sound(slot)
  local nm, t = SLOTS[slot], self:voice_type(slot)
  local used, n = {}, 1
  for _, p in ipairs(self.me.sounds) do used[p.name] = true end
  while used[t .. " " .. n] do n = n + 1 end
  local p = { name = t .. " " .. n, type = t }
  for _, k in ipairs(SOUND_KEYS) do p[k] = self.v["ockm-"..nm.."-"..k] or SOUND_DEF[k] end
  table.insert(self.me.sounds, p)
  self:save_settings()
  self:flash_btn("save")
end
function ui:delete_sound(i)
  table.remove(self.me.sounds, i)
  self:save_settings()
  self:flash_btn("save")
end

-- where a slot is in its list: first its synth sound(s) (one, or rim / conga / shaker for perc), then your saved
-- sounds for it, then sample 1 and up
function ui:synth_count(slot)
  return LAB_PERC[math.floor(self.v["ockm-"..SLOTS[slot].."-sound"] or 0)] and 3 or 1
end
function ui:synth_name(slot)
  local nm = SLOTS[slot]
  local snd = math.floor(self.v["ockm-"..nm.."-sound"] or 0)
  if LAB_PERC[snd] then return LAB_PERC[snd][clamp(math.floor(self.v["ockm-"..nm.."-synth"] or 0), 0, 2) + 1] end
  return LAB_SOUND[snd] or "kick"
end
function ui:drum_pos(slot)
  local nm = SLOTS[slot]
  local smp = math.floor(self.v["ockm-"..nm.."-sample"] or 0)
  local ns, ps = self:synth_count(slot), self:presets_for(slot)
  if smp > 0 then return smp + ns + #ps - 1 end
  local cur = self:current_preset(slot)
  if cur then for j, i in ipairs(ps) do if i == cur then return ns + j - 1 end end end
  return clamp(math.floor(self.v["ockm-"..nm.."-synth"] or 0), 0, ns - 1)
end
function ui:set_drum_pos(slot, pos)
  local nm = SLOTS[slot]
  local ns, ps = self:synth_count(slot), self:presets_for(slot)
  local was = self:drum_pos(slot)
  if pos < ns then
    -- back to a synth sound from a saved one: start from the lab's sound
    if was >= ns and was < ns + #ps then for _, k in ipairs(SOUND_KEYS) do self:send("ockm-"..nm.."-"..k, SOUND_DEF[k]) end end
    self:send("ockm-"..nm.."-sample", 0); self:send("ockm-"..nm.."-synth", pos)
  elseif pos < ns + #ps then
    self:apply_preset(slot, ps[pos - ns + 1])
  else
    self:send("ockm-"..nm.."-sample", pos - ns - #ps + 1)
  end
  self:audition_soon(slot)
end
-- the synth sound's shape: randomise (a seed and how far), and back to the lab's starting sound
function ui:lab_random(slot, amt)
  local nm = SLOTS[slot]
  self:snapshot("randomise")
  self:send("ockm-"..nm.."-labrseed", math.random(1, 99999)); self:send("ockm-"..nm.."-labramt", amt)
  self:send("ockm-"..nm.."-labpseed", math.random(1, 99999))
  self:send("ockm-"..nm.."-labmorph", 0)     -- a new path: morph starts again from the new sound
  self:flash_btn((amt >= 1) and "wild" or "random")
  self:audition_soon(slot)
end
function ui:lab_reset(slot)
  local nm = SLOTS[slot]
  self:snapshot("reset sound")
  for _, k in ipairs({ "labrseed", "labramt", "labchar", "labmorph" }) do self:send("ockm-"..nm.."-"..k, 0) end
  self:flash_btn("reset")
  self:audition_soon(slot)
end
-- a button lights up for a moment when tapped, so you can see it took
function ui:flash_btn(key)
  self.flashing = key
  if self.flashclock then self.flashclock:delay(250) end
end
function ui:flash_off() self.flashing = nil; self:dirty() end
-- while stopped, moving a drum slider plays the sound (at most every 200 ms while dragging, and once on letting go)
function ui:preview(slot, final)
  if self.playing ~= 0 then return end
  self.prev_slot = slot
  if final then self.prev_busy = nil; if self.prevclock then self.prevclock:unset() end; self:audition_soon(slot); return end
  if not self.prev_busy then self.prev_busy = true; if self.prevclock then self.prevclock:delay(200) end end
end
function ui:preview_fire() self.prev_busy = nil; self:audition(self.prev_slot) end
function ui:set_sample(slot, n)
  self:send("ockm-"..SLOTS[slot].."-sample", n)
  self:audition_soon(slot)
end
function ui:finalize()
  for _, r in ipairs(self.recv or {}) do r:destruct() end
  if self.clock then self.clock:destruct() end
  if self.msgclock then self.msgclock:destruct() end
  if self.audclock then self.audclock:destruct() end
  if self.flashclock then self.flashclock:destruct() end
  if self.prevclock then self.prevclock:destruct() end
  if self.jobclock then self.jobclock:destruct() end
  if self.expclock then self.expclock:destruct() end
  if self.tickclock then self.tickclock:destruct() end
  if self.demudclock then self.demudclock:destruct() end
  for _, t in pairs(self.tables) do if t.destruct then t:destruct() end end
end

-- one repaint for a burst of changes
function ui:dirty() if self.clock then self.clock:delay(5) end end
-- a short message under the steps, gone after a few seconds
function ui:say(text) self.msg = text; self.msg_undo = nil; if self.msgclock then self.msgclock:delay(4000) end; self:dirty() end
function ui:clear_msg() self.msg = nil; self.msg_undo = nil; self:repaint() end
-- one-step undo: before a big change, the engine copies everything (patterns, project, song) aside.
-- say_undo shows the message with an undo button for 8 seconds
function ui:snapshot(label) psend("ockm-snapshot", "bang", {}); self.undo_label = label end
function ui:say_undo(text)
  self.msg = text; self.msg_undo = true
  if self.msgclock then self.msgclock:delay(8000) end
  self:dirty()
end
function ui:undo()
  if not self.undo_label then return end
  local label = self.undo_label
  self.undo_label = nil
  psend("ockm-undo", "bang", {})
  self:say("undone: " .. label)
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
-- each part has its own length (in steps); the loop is as long as the longest part
local PART_NAMES = { drum = "drums", bass = "bass", lead = "lead", chord = "chords" }
function ui:plen(p) return math.max(16, math.floor(self.v["ockm-" .. p .. "-len"] or 64)) end
function ui:track_part(n) if n <= 8 then return "drum" end return SYNTHS[n - 8] end
function ui:loop_len() return math.max(self:plen("drum"), self:plen("bass"), self:plen("lead"), self:plen("chord")) end
function ui:screen_part()
  if self.screen == "drums" then return "drum" elseif self.screen == "synth" then return SYNTHS[self.part] end
  return nil
end
-- the steps shown on this screen: the part's own length on its tab, the whole loop elsewhere
function ui:shown_len()
  local p = self:screen_part()
  if p then return self:plen(p) end
  return self:loop_len()
end
function ui:blocks() return math.max(1, math.ceil(self:shown_len() / 16)) end
function ui:play_block()
  local s = self.step
  if self:screen_part() then s = s % self:shown_len() end
  return math.floor(s / 16)
end
-- "loop 4 bars (bass)": how long the loop is, and which part makes it that long
function ui:loop_label()
  local L = self:loop_len()
  local bars = math.floor(L / 16)
  local who = {}
  for _, p in ipairs({ "drum", "bass", "lead", "chord" }) do if self:plen(p) >= L then who[#who + 1] = PART_NAMES[p] end end
  local by = (#who == 4) and "every part" or table.concat(who, ", ")
  return string.format("loop %d %s (%s)", bars, (bars == 1) and "bar" or "bars", by)
end
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
  elseif self.screen == "live" then self:layout_live(add)
  elseif self.screen == "drums" then self:layout_drums(add)
  elseif self.screen == "mixer" then self:layout_mixer(add)
  elseif self.screen == "compose" then self:layout_compose(add)
  elseif self.screen == "project" then self:layout_project(add)
  elseif self.screen == "arrange" then self:layout_arrange(add)
  elseif self.screen == "setup" then self:layout_setup(add)
  else self:layout_synth(add) end
  if self.sheet == "export" then self:layout_export(add) end
  if self.sheet == "eq" then self:layout_eq(add) end
  if self.sheet == "slotpick" then self:layout_slotpick(add) end
  -- messages on screens that have no message line of their own
  if self.msg and (self.screen == "perform" or self.screen == "live" or self.screen == "compose" or self.screen == "mixer" or self.screen == "arrange" or self.screen == "setup" or self.screen == "drums"
                   or (self.msg_undo and self.undo_label)) then
    if self.msg_undo and self.undo_label then
      add{ kind="toast", x=W / 2 - 330, y=H - 50, w=556, h=38, label=self.msg }
      add{ kind="btn", x=W / 2 + 232, y=H - 50, w=98, h=38, label="undo", accent=true, tap=function() self:undo() end }
    else
      add{ kind="toast", x=W / 2 - 330, y=H - 50, w=660, h=38, label=self.msg }
    end
  end
  if self.menu then self:layout_menu(add) end      -- last, so it sits on top and gets the taps
  return L
end

-- Screen hierarchy, top to bottom:
--   1. top bar: play, tempo, the screens as tabs (playing, making, arranging), save, and a menu for the rest
--   2. navigation strip: pattern, length, which block of 16 steps
--   3. what you're editing (drum slot tabs on the drums screen), then the steps
--   4. sound shaping at the bottom
-- the tabs, in three groups: playing (perform A, perform B, mixer), making (compose and the four parts), arranging.
-- { screen, label, part, width, gap before }
local TABS = { { "perform", "perform A", nil, 72 }, { "live", "perform B", nil, 72 }, { "mixer", "mixer", nil, 58 },
               { "compose", "builder", nil, 58, 8 }, { "drums", "drums", nil, 58 }, { "synth", "bass", 1, 58 }, { "synth", "lead", 2, 58 }, { "synth", "chord", 3, 58 },
               { "arrange", "arrange", nil, 58, 8 } }
local NAV_Y, NAV_H = 70, 36
local KIOSK = os.getenv and os.getenv("OCKM_KIOSK")
function ui:layout_top(add)
  add{ kind="play", x=16, y=12, w=64, h=48, tap=function()
    if self.playing ~= 0 then self:send("ockm-play", 0) else self:send("ockm-play", 1) end
  end }
  add{ kind="bpm", x=92, y=12, w=124, h=48, tap=function() if self.screen ~= "setup" then self:open("setup") end end }
  local busy = self.recording or self.exporting
  local x = 226
  for i, t in ipairs(TABS) do
    x = x + (t[5] or 0)
    local sel = (self.screen == t[1]) and (t[3] == nil or t[3] == self.part)
    if not (busy and t[1] == "arrange") then
      add{ kind="tab", x=x, y=12, w=t[4], h=48, label=t[2], sel=sel, tap=function()
        self.menu = nil
        if t[3] then
          if self.part ~= t[3] then self.part = t[3]; self.sel_step = 0; self.msg = nil end
        end
        if self.screen ~= t[1] then self:open(t[1]) end
      end }
    end
    x = x + t[4] + 4
  end
  if busy then
    local secs = os.time() - busy.t0
    add{ kind="btn", x=766, y=12, w=124, h=48, accent=true, small=true, label=string.format("%s %d:%02d stop", self.recording and "rec" or "export", math.floor(secs / 60), secs % 60),
         tap=function() if self.recording then self:record_stop() else self:export_cancel() end end }
  else
    -- save: a disc, orange when there's something to save
    add{ kind="disc", x=W - 120, y=12, w=50, h=48, tap=function()
      psend("ockm-save", "bang", {}); self:say("saved " .. ockm_pretty(self.project) .. ": the loop and the kit") end }
  end
  add{ kind="menubtn", x=W - 66, y=12, w=50, h=48, sel=(self.menu or self.screen == "project" or self.screen == "setup"), tap=function() self.menu = not self.menu end }
  if self.screen ~= "project" and self.screen ~= "setup" and self.screen ~= "live" then self:layout_nav(add) end
end

-- the menu (top right): everything that isn't a screen you play or make on
function ui:layout_menu(add)
  local items = {
    { "project", "open, new, save as, delete", function() self:open("project") end },
    { "export", "audio, stems, MIDI", function() psend("ockm-usb-scan", "bang", {}); psend("ockm-exports-ask", "bang", {}); self.sheet = "export" end },
    { "settings", "tempo, swing, clock, sound", function() self:open("setup") end },
    { "revert", "back to the last save", function() psend("ockm-revert", "bang", {}); self:say("back to the last save of " .. ockm_pretty(self.project)) end },
  }
  if KIOSK then items[#items + 1] = { "quit to desktop", "", function() psend("pd", "quit", {}) end } end
  -- a tap anywhere else closes it
  add{ kind="scrim", x=0, y=62, w=W, h=H - 62, tap=function() self.menu = nil end }
  local mx, my, mw = W - 16 - 230, 66, 230
  add{ kind="menupanel", x=mx, y=my, w=mw, h=12 + #items * 50 - 4 }
  for i, it in ipairs(items) do
    add{ kind="menuitem", x=mx + 6, y=my + 6 + (i - 1) * 50, w=mw - 12, h=46, label=it[1], sub=it[2], tap=function() self.menu = nil; it[3]() end }
  end
end

-- the navigation strip: pattern 1-8, length, and the blocks of 16 steps (only as many as the length allows)
function ui:layout_nav(add)
  local y, h = NAV_Y, NAV_H
  -- left, right above the steps: back, the steps you're looking at, forward
  local n = self:blocks()
  add{ kind="arrow", x=16, y=y, w=44, h=h, dir=-1, on=(self:shown_block() > 0), tap=function() self:set_page(self:shown_block() - 1) end }
  add{ kind="steps", x=64, y=y, w=104, h=h }
  add{ kind="arrow", x=172, y=y, w=44, h=h, dir=1, on=(self:shown_block() < n - 1), tap=function() self:set_page(self:shown_block() + 1) end }
  -- middle: how long the loop is, and which part sets it
  add{ kind="text", x=236, y=y + 12, w=300, h=12, label=self:loop_label(), size=11 }
  -- right, on a part's tab: that part's length in bars, and double
  local p = self:screen_part()
  if p then
    local cur = self:plen(p)
    local cw, dw = 52, 70
    local x0 = W - 16 - dw - 8 - 5 * (cw + 4)
    add{ kind="text", x=x0 - 50, y=y + 12, w=48, h=12, label="length", size=10 }
    for i, len in ipairs({ 16, 32, 64, 128, 256 }) do
      local bars = len // 16
      add{ kind="choice", x=x0 + (i - 1) * (cw + 4), y=y, w=cw, h=h, small=true, sel=(cur == len),
           label=bars .. ((bars == 1) and " bar" or " bars"), tap=function() self:set_part_len(p, len) end }
    end
    add{ kind="btn", x=W - 16 - dw, y=y, w=dw, h=h, small=true, label="double", disabled=(cur >= 256), tap=function()
      if cur < 256 then
        psend("ockm-" .. p .. "-double", "bang", {})
        self:say(PART_NAMES[p] .. " doubled: " .. math.floor(cur / 8) .. " bars, the first " .. math.floor(cur / 16) .. " copied after themselves")
      end
    end }
  end
end

-- a part's length. Shorter keeps the bars beyond (go longer again and they come back), so it's offered as undo too;
-- longer repeats the part's own bars to fill the new ones
function ui:set_part_len(p, len)
  local old = self:plen(p)
  if len == old then return end
  local bars = math.floor(len / 16)
  local what = PART_NAMES[p] .. " now " .. bars .. ((bars == 1) and " bar" or " bars")
  if len < old then
    self:snapshot(PART_NAMES[p] .. " length")
    psend("ockm-" .. p .. "-len", "float", { len })
    self:say_undo(what .. ": the rest is kept, go longer to bring it back")
  else
    psend("ockm-" .. p .. "-len", "float", { len })
    self:say(what .. ": its bars repeat to fill")
  end
  self:set_page(self.page)
end

-- the block on screen: perform follows the playhead while playing, the edit screens stay where you put them
function ui:shown_block()
  if self.screen == "perform" and self.playing ~= 0 then return clamp(self:play_block(), 0, self:blocks() - 1) end
  return clamp(self.page, 0, self:blocks() - 1)
end

local LANE_Y, LANE_H, LANE_P, LANE_X = 124, 31, 35, 192
function ui:lane_y(i) return LANE_Y + (i - 1) * LANE_P end
-- the bottom half of perform: the synths on the left, master effects on the right, each on its own card
local PB_Y, PB_H = 412, 176
local PART_Y, PART_H = 418, 40
local half_w = (W - 32 - 16) / 2
local function part_x(i) local tw = (half_w - 12 - 12) / 3; return 22 + (i - 1) * (tw + 6), tw end

function ui:layout_perform(add)
  -- the drums: 8 lanes, a picture of the block that is playing. Tap a name to open it, a step to change it
  for i = 1, 8 do
    local y = self:lane_y(i)
    local name = SHORT[(self.v["ockm-"..SLOTS[i].."-sound"] or 0) + 1]
    local tr = TRACKS[i]
    add{ kind="ms", x=108, y=y, w=38, h=LANE_H, label="M", hook="ockm-"..tr.."-mute" }
    add{ kind="ms", x=150, y=y, w=38, h=LANE_H, label="S", hook="ockm-"..tr.."-solo" }
    add{ kind="lanename", x=16, y=y, w=88, h=LANE_H, label=name, tap=function() self.slot = i; self:open("drums") end }
    add{ kind="lane", x=LANE_X, y=y, w=W - LANE_X - 16, h=LANE_H, track=i }
    -- tap cycles empty, hit, accent on the block on screen
    local cw = (W - LANE_X - 16) / 16
    for c = 0, 15 do
      local st = (self:shown_block() * 16 + c) % self:plen("drum")
      add{ kind="pcell", x=LANE_X + c * cw, y=y, w=cw, h=LANE_H, slot=i, step=st, tap=function() self:drum_cycle(i, st) end }
    end
  end
  local lx, rx = 16, 16 + half_w + 16
  add{ kind="card", x=lx, y=PB_Y, w=half_w, h=PB_H }
  add{ kind="card", x=rx, y=PB_Y, w=half_w, h=PB_H }
  local iw = half_w - 12
  -- synths. Each part: tap to pick it (its controls below), a light that flashes as it plays, mute and solo
  local pi = self.perf_part or 1
  for i, p in ipairs(SYNTHS) do
    local x, tw = part_x(i)
    add{ kind="partbtn", x=x, y=PART_Y, w=tw, h=PART_H, label=p, sel=(pi == i), tap=function() self.perf_part = i end }
    add{ kind="ms", x=x + tw - 64, y=PART_Y + 6, w=28, h=PART_H - 12, label="M", hook="ockm-"..p.."-mute" }
    add{ kind="ms", x=x + tw - 32, y=PART_Y + 6, w=28, h=PART_H - 12, label="S", hook="ockm-"..p.."-solo" }
  end
  local part = SYNTHS[pi]
  local ay, ah = PART_Y + PART_H + 6, 34
  if self:part_empty(part) then
    add{ kind="btn", x=lx + 6, y=ay, w=iw, h=ah, small=true, accent=true, label=START[part], tap=function() self:start_part(part) end }
  elseif part == "chord" then
    -- chords: step through the rhythms while it plays
    self:stepper(add, lx + 6, ay, iw, ah, CHORD_RHY, "ockm-chord-rhythm")
  elseif not self:part_auto(part) or self:mode() == 3 then
    add{ kind="locked", x=lx + 6, y=ay, w=iw, h=ah, label="manual: your notes. Pick a priority on compose for new ones" }
  else
    -- new: a fresh variation of the line; orig: back to the one you started with; busy: fewer or more notes
    local skey = "ockm-"..part.."-seed"
    local seed = math.floor(self.v[skey] or 0)
    local bw = 80
    add{ kind="btn", x=lx + 6, y=ay, w=bw, h=ah, small=true, accent=true, label="new", tap=function()
      self:send(skey, seed + 1); self:say(part .. ": variation " .. (seed + 1) .. ". orig goes back") end }
    add{ kind="btn", x=lx + 12 + bw, y=ay, w=bw, h=ah, small=true, quiet=(seed == 0), label="orig", tap=function() self:send(skey, 0) end }
    add{ kind="hbar", x=lx + 18 + 2 * bw, y=ay, w=iw - 12 - 2 * bw, h=ah, hook="ockm-"..part.."-density", lo=0, hi=2, label="busy", bold=true }
  end
  local eng = engines_of(part)
  local kn = KNOBS[eng[(self.v["ockm-"..part.."-engine"] or 0) + 1]] or KNOBS.acid
  local kw = (iw - 6) / 2
  for k = 1, 4 do
    local col, row = (k - 1) % 2, math.floor((k - 1) / 2)
    add{ kind="hbar", x=lx + 6 + col * (kw + 6), y=504 + row * 44, w=kw, h=40, hook="ockm-"..part.."-k"..k, lo=0, hi=1, label=kn[k], bold=true }
  end
  -- master effects. Top row: the moves you play (rise and pump switch on and off, drop and throw while held)
  local mx = rx + 6
  local mw = (iw - 18) / 4
  local rise = (self.v["ockm-rise"] or 0) > 0
  local pump = self.v["ockm-pump"] or 0
  add{ kind="choice", x=mx, y=PART_Y, w=mw, h=PART_H, label="rise", sel=rise, accent=true, tap=function()
    self:send("ockm-rise", rise and 0 or 1)
    self:say(rise and "rise off" or "rise on: the filter climbs across the loop, then drops as it starts again")
  end }
  local plab = (pump <= 0) and "pump" or ((pump < 0.75) and "pump ·" or "pump ··")
  add{ kind="choice", x=mx + (mw + 6), y=PART_Y, w=mw, h=PART_H, label=plab, sel=(pump > 0), accent=true, tap=function()
    local nx = (pump <= 0) and 0.5 or ((pump < 0.75) and 1 or 0)
    self:send("ockm-pump", nx)
    self:say((nx == 0) and "pump off" or ((nx < 0.75) and "pump: the kick ducks the synths, lightly" or "pump: deep, house-style"))
  end }
  add{ kind="pad", x=mx + 2 * (mw + 6), y=PART_Y, w=mw, h=PART_H, hook="ockm-drop", label="drop" }
  add{ kind="pad", x=mx + 3 * (mw + 6), y=PART_Y, w=mw, h=PART_H, hook="ockm-delay-throw", label="throw" }
  -- the filter: springs back to off when you let go, unless held. Drive beside it
  local fw = math.floor((iw - 6) * 2 / 3)
  local hold = self.filter_hold
  add{ kind="hbar", x=mx, y=ay, w=fw, h=78, hook="ockm-filter", lo=-1, hi=1, label=hold and "filter (held)" or "filter", bold=true, spring=not hold }
  add{ kind="choice", x=mx + fw - 52, y=ay + 6, w=46, h=24, label="hold", small=true, onbar=true, sel=hold, tap=function()
    self.filter_hold = not hold
    if hold then self:filter_spring() end
  end }
  add{ kind="hbar", x=mx + fw + 6, y=ay, w=iw - fw - 6, h=78, hook="ockm-drive", lo=0, hi=1, label="drive", bold=true }
  local ROW2 = { { "ockm-delay-mix", 0, 1, "delay" }, { "ockm-delay-fb", 0, 0.9, "feedback" }, { "ockm-delay-steps", 1, 8, "time" },
                 { "ockm-verb-mix", 0, 1, "reverb" }, { "ockm-verb-size", 0, 1, "size" } }
  self:fx_groups(add, ROW2, mx, 548, iw, 40)
end

-- let go of the filter: it snaps back to off. The screen shows it there at once rather than drawing the glide
local SPRING_MS = 50
function ui:filter_spring()
  self.v["ockm-filter"] = 0; self.filter_springing = true
  psend("ockm-filter-glide", "list", { 0, SPRING_MS })
end

-- does a synth part play on this step (and can it be heard)? For the lights on perform
function ui:part_sounding(p)
  if (self.v["ockm-"..p.."-mute"] or 0) > 0 then return false end
  if self:soloing() and (self.v["ockm-"..p.."-solo"] or 0) <= 0 then return false end
  return self:get("ockm-pat-"..p.."-on", self.step % self:plen(p)) > 0
end

-- ------------------------------------------------------------------ live
-- Perform 2: no steps, just the mutes and the master effects, big enough to play with your thumbs.
-- Mutes can land now, on the next beat or on the next bar (the engine holds them until then).
local LV_Y = 72
local LV_GRID_Y, LV_ROW_H, LV_COL_W = 122, 128, (448 - 12 - 18) / 4
local function live_tile(n)   -- n: 1-8 drums, 9-11 synths, 12 all synths
  local c, r = (n - 1) % 4, math.floor((n - 1) / 4)
  return 22 + c * (LV_COL_W + 6), LV_GRID_Y + r * (LV_ROW_H + 8)
end
local QUANT = { { 0, "now" }, { 1, "next beat" }, { 2, "next bar" } }

-- ask for a mute: the engine applies it now or holds it for the beat or bar. The tile shows it waiting
function ui:qmute(t, val)
  self.mpend = self.mpend or {}
  local now = (self.playing == 0) or ((self.v["ockm-mute-quant"] or 0) == 0)
  if not now and (self.v["ockm-"..t.."-mute"] or 0) ~= val then self.mpend[t] = val end
  psend("ockm-"..t.."-mute-q", "float", { val })
end
function ui:pending(t)
  local p = self.mpend and self.mpend[t]
  if p == nil or self.playing == 0 then return nil end
  if (self.v["ockm-"..t.."-mute"] or 0) == p then return nil end
  return p
end
-- where a mute is heading: what it will be once anything waiting has landed
function ui:mute_target(t) local p = self:pending(t); if p ~= nil then return p end; return self.v["ockm-"..t.."-mute"] or 0 end

-- scenes: which tracks play. Everything else is muted; solos are cleared so the scene is what you hear
function ui:scene(keep)
  for _, t in ipairs(TRACKS) do
    if (self.v["ockm-"..t.."-solo"] or 0) > 0 then self:send("ockm-"..t.."-solo", 0) end
    local want = keep(t) and 0 or 1
    if self:mute_target(t) ~= want then self:qmute(t, want) end
  end
end

function ui:kick_slots() local k = {}; for _, nm in ipairs(self:drum_slots({ kick = true })) do k[nm] = true end; return k end

function ui:layout_live(add)
  local lx, rx = 16, 16 + half_w + 16
  add{ kind="card", x=lx, y=LV_Y, w=half_w, h=H - 12 - LV_Y }
  add{ kind="card", x=rx, y=LV_Y, w=half_w, h=H - 12 - LV_Y }
  -- mutes: when they land
  add{ kind="text", x=24, y=89, w=90, h=12, label="mutes land", size=11 }
  local q = math.floor(self.v["ockm-mute-quant"] or 0)
  local qw = (458 - 116 - 12) / 3
  for i, o in ipairs(QUANT) do
    add{ kind="choice", x=116 + (i - 1) * (qw + 6), y=80, w=qw, h=34, label=o[2], small=true, sel=(q == o[1]),
         tap=function() self.v["ockm-mute-quant"] = o[1]; pd.send("ockm-mute-quant", "float", { o[1] }) end }
  end
  -- a tile per track: tap anywhere to mute or bring it back; S in the corner
  for n = 1, 12 do
    local x, y = live_tile(n)
    if n <= 11 then
      local t = TRACKS[n]
      add{ kind="mtile", x=x, y=y, w=LV_COL_W, h=LV_ROW_H, track=t, label=self:track_name(n),
           tap=function()
             if not self:track_in(t) then self:say(self:track_name(n) .. " is off in this pattern: switch it on on the builder"); return end
             self:qmute(t, (self:mute_target(t) > 0) and 0 or 1)
           end }
      add{ kind="ms", x=x + LV_COL_W - 40, y=y + LV_ROW_H - 36, w=34, h=30, label="S", hook="ockm-"..t.."-solo" }
    else
      add{ kind="mtile", x=x, y=y, w=LV_COL_W, h=LV_ROW_H, group=SYNTHS, label="all synths", tap=function()
        local any = false
        for _, p in ipairs(SYNTHS) do if self:mute_target(p) == 0 then any = true end end
        for _, p in ipairs(SYNTHS) do if self:track_in(p) and self:mute_target(p) ~= (any and 1 or 0) then self:qmute(p, any and 1 or 0) end end
      end }
    end
  end
  -- scenes
  local kicks = self:kick_slots()
  local SC = { { "drums only", function(t) return t:match("^d%d") ~= nil end },
               { "no drums", function(t) return t:match("^d%d") == nil end },
               { "kick + bass", function(t) return kicks[t] or t == "bass" end },
               { "all in", function() return true end } }
  local sw = (436 - 18) / 4
  for i, sc in ipairs(SC) do
    add{ kind="btn", x=22 + (i - 1) * (sw + 6), y=530, w=sw, h=52, small=true, label=sc[1], edge=true, flash="scene" .. i,
         tap=function() self:scene(sc[2]); self:flash_btn("scene" .. i) end }
  end
  -- master effects, big
  local mx, iw = rx + 6, half_w - 12
  local mw = (iw - 18) / 4
  local rise = (self.v["ockm-rise"] or 0) > 0
  local pump = self.v["ockm-pump"] or 0
  add{ kind="choice", x=mx, y=80, w=mw, h=52, label="rise", sel=rise, accent=true, tap=function() self:send("ockm-rise", rise and 0 or 1) end }
  add{ kind="choice", x=mx + (mw + 6), y=80, w=mw, h=52, label=(pump <= 0) and "pump" or ((pump < 0.75) and "pump ·" or "pump ··"), sel=(pump > 0), accent=true,
       tap=function() self:send("ockm-pump", (pump <= 0) and 0.5 or ((pump < 0.75) and 1 or 0)) end }
  add{ kind="pad", x=mx + 2 * (mw + 6), y=80, w=mw, h=52, hook="ockm-drop", label="drop", sub="hold" }
  add{ kind="pad", x=mx + 3 * (mw + 6), y=80, w=mw, h=52, hook="ockm-delay-throw", label="throw", sub="hold" }
  local hold = self.filter_hold
  add{ kind="hbar", x=mx, y=140, w=iw, h=150, hook="ockm-filter", lo=-1, hi=1, label=hold and "filter (held)" or "filter", bold=true, spring=not hold }
  add{ kind="choice", x=mx + iw - 64, y=148, w=56, h=30, label="hold", small=true, onbar=true, sel=hold, tap=function()
    self.filter_hold = not hold
    if hold then self:filter_spring() end
  end }
  local hw = (iw - 6) / 2
  add{ kind="hbar", x=mx, y=298, w=hw, h=56, hook="ockm-drive", lo=0, hi=1, label="drive", bold=true }
  add{ kind="hbar", x=mx + hw + 6, y=298, w=hw, h=56, hook="ockm-volume", lo=0, hi=1, label="volume", bold=true }
  local ROW2 = { { "ockm-delay-mix", 0, 1, "delay" }, { "ockm-delay-fb", 0, 0.9, "feedback" }, { "ockm-delay-steps", 1, 8, "time" },
                 { "ockm-verb-mix", 0, 1, "reverb" }, { "ockm-verb-size", 0, 1, "size" } }
  self:fx_groups(add, ROW2, mx, 362, iw, 56)
  local w3 = (iw - 12) / 3
  for i = 1, 3 do
    -- your three slots (pick them in settings, or with the small v on each)
    local rc = self.me.macros[self.me.slots[i]]
    local x = mx + (i - 1) * (w3 + 6)
    local lit = self.macro and self.macro.slot == i
    add{ kind="hold", x=x, y=426, w=w3, h=156, label=(rc and #rc.moves > 0) and rc.name or "empty",
         sub=(lit and self.macro.latched) and "tap to let go" or ("slot " .. string.char(64 + i)),
         on=lit, down=function() self:macro_down(i) end, up=function() self:macro_up(i) end }
    add{ kind="btn", x=x + w3 - 40, y=432, w=34, h=30, small=true, quiet=true, label="v", tap=function() self.pick_slot = i; self.sheet = "slotpick" end }
  end
end

-- ------------------------------------------------------------------ my settings
-- Things that belong to you, not to a project: your macros, which three are on Perform B, defaults for new
-- projects and how this device behaves. Kept in my-settings.lua beside the patch (not inside any project).
local TARGETS = {
  { id = "filter",   hook = "ockm-filter",      lo = -1, hi = 1 },
  { id = "delay",    hook = "ockm-delay-mix",   lo = 0, hi = 1 },
  { id = "feedback", hook = "ockm-delay-fb",    lo = 0, hi = 0.9 },
  { id = "reverb",   hook = "ockm-verb-mix",    lo = 0, hi = 1 },
  { id = "size",     hook = "ockm-verb-size",   lo = 0, hi = 1 },
  { id = "drive",    hook = "ockm-drive",       lo = 0, hi = 1 },
  { id = "pump",     hook = "ockm-pump",        lo = 0, hi = 1 },
  { id = "volume",   hook = "ockm-volume",      lo = 0, hi = 1 },
  { id = "rise",     hook = "ockm-rise",        switch = true },
  { id = "throw",    hook = "ockm-delay-throw", switch = true },
  { id = "mutes",    choices = { "kick + bass", "drums only", "no drums", "no kick" } },
}
local TARGET = {}; for _, t in ipairs(TARGETS) do TARGET[t.id] = t end
local HOW = { { "jump", 0 }, { "1 beat", 4 }, { "1 bar", 16 }, { "2 bars", 32 }, { "4 bars", 64 } }   -- in steps
local BACK = { "snap back", "glide back", "stay" }
local MACRO_NAMES = { "build", "wash", "strip", "sink", "dub out", "lift", "blur", "freeze", "smash", "swell", "haze",
                      "tunnel", "pressure", "drop out", "air", "grit" }
local function default_settings()
  return {
    sounds = {},     -- your saved drum sounds: { name, type, and the slot settings in SOUND_KEYS }
    macros = {
      { name = "build", moves = { { t = "filter", v = 0.6, how = 4, back = 1 }, { t = "reverb", v = 0.65, how = 1, back = 2 },
                                  { t = "delay", v = 0.45, how = 1, back = 1 }, { t = "pump", v = 1, how = 1, back = 1 } } },
      { name = "wash", moves = { { t = "delay", v = 0.85, how = 1, back = 1 }, { t = "feedback", v = 0.78, how = 1, back = 1 },
                                 { t = "reverb", v = 0.9, how = 1, back = 1 }, { t = "filter", v = -0.5, how = 2, back = 1 } } },
      { name = "strip", moves = { { t = "mutes", v = 1, how = 1, back = 1 } } },
      { name = "sink", moves = { { t = "filter", v = -0.85, how = 3, back = 1 }, { t = "drive", v = 0.7, how = 3, back = 1 } } },
      { name = "dub out", moves = { { t = "throw", v = 1, how = 1, back = 1 }, { t = "feedback", v = 0.85, how = 1, back = 3 },
                                    { t = "delay", v = 0.8, how = 1, back = 3 } } },
      { name = "lift", moves = { { t = "filter", v = 0.35, how = 3, back = 2 }, { t = "size", v = 0.95, how = 1, back = 2 } } },
    },
    slots = { 1, 2, 3 },
    new = { drum = 16, synth = 64, lead = 1 },
    device = { theme = "dark", snap = 1, mutes = 0 },
  }
end
local SNAP_MS = { 50, 150, 400 }
local NEW_LEAD = { { "1 and 1", 0, 0 }, { "motif", 10, 15 }, { "call and answer", 11, 16 }, { "arp", 13, 18 } }   -- name, rhythm, notes (the first is how the engine starts)

-- writing and reading the file: plain Lua, so it can be read back with no parser
local function ser(v, ind)
  ind = ind or ""
  if type(v) == "table" then
    local out, n = {}, #v
    for i = 1, n do out[#out + 1] = ind .. "  " .. ser(v[i], ind .. "  ") end
    for k, x in pairs(v) do
      if type(k) ~= "number" or k > n or k < 1 then out[#out + 1] = ind .. "  " .. string.format("[%q]", k) .. " = " .. ser(x, ind .. "  ") end
    end
    return "{\n" .. table.concat(out, ",\n") .. "\n" .. ind .. "}"
  elseif type(v) == "string" then return string.format("%q", v) end
  return tostring(v)
end
function ui:settings_path()
  if not self._loadpath or self._loadpath == "" then return nil end
  return self._loadpath .. "../my-settings.lua"
end
function ui:load_settings()
  local d = default_settings()
  local path = self:settings_path()
  local f = path and io.open(path, "r")
  if f then
    local src = f:read("a"); f:close()
    local fn = load(src, "my-settings", "t", {})
    local ok, t = pcall(fn or function() end)
    if ok and type(t) == "table" then
      for k, x in pairs(t) do if d[k] ~= nil and type(x) == type(d[k]) then d[k] = x end end
    end
  end
  self.me = d
  local dev = d.device
  self.theme = THEMES[dev.theme] or self.theme
  SPRING_MS = SNAP_MS[dev.snap] or 50
  self.v["ockm-mute-quant"] = dev.mutes or 0
  if self.initclock then self.initclock:delay(0) end     -- tell the engine once everything has loaded
end
function ui:init_sends() pd.send("ockm-mute-quant", "float", { self.v["ockm-mute-quant"] or 0 }) end
function ui:save_settings()
  local path = self:settings_path()
  if not path then return end
  local f = io.open(path, "w")
  if f then f:write("-- OCKM_GENERATOR: your macros and settings (not part of any project)\nreturn " .. ser(self.me) .. "\n"); f:close() end
end

-- a line describing a recipe: "filter up over 2 bars, reverb, pump"
local function move_label(m)
  local t = TARGET[m.t]
  if not t then return "?" end
  if t.choices then return t.choices[m.v] or "mutes" end
  local word = m.t
  if m.t == "filter" then word = (m.v >= 0) and "filter up" or "filter down" end
  if t.switch then return word end
  if HOW[m.how] and HOW[m.how][2] > 0 then word = word .. " over " .. HOW[m.how][1] end
  return word
end
local function recipe_summary(r)
  if not r or #r.moves == 0 then return "empty: tap to make one" end
  local out = {}
  for _, m in ipairs(r.moves) do out[#out + 1] = move_label(m) end
  return table.concat(out, ", ")
end

-- ------------------------------------------------------------------ playing a macro
-- press: each move goes to its amount (straight away or over its time); let go: each comes back (snap or glide),
-- unless it stays, in which case the macro stays lit until you tap it again
local function steps_ms(self, steps) return steps * 15000 / math.max(40, self.v["ockm-bpm"] or 124) end
function ui:mset(hook, x) self.v[hook] = x; pd.send(hook, "float", { x }) end
function ui:ramp(hook, to, ms)
  self.ramps = self.ramps or {}
  if ms <= 0 then self.ramps[hook] = nil; self:mset(hook, to); return end
  self.ramps[hook] = { from = self.v[hook] or 0, to = to, t = 0, dur = ms }
  if self.rampclock then self.rampclock:delay(30) end
end
function ui:ramp_tick()
  local any = false
  for hook, r in pairs(self.ramps or {}) do
    r.t = r.t + 30
    local f = math.min(1, r.t / r.dur)
    self:mset(hook, r.from + (r.to - r.from) * f)
    if f >= 1 then self.ramps[hook] = nil else any = true end
  end
  self:dirty()
  if any and self.rampclock then self.rampclock:delay(30) end
end
local function keep_for(kind, kicks)
  if kind == 1 then return function(t) return kicks[t] or t == "bass" end
  elseif kind == 2 then return function(t) return t:match("^d%d") ~= nil end
  elseif kind == 3 then return function(t) return t:match("^d%d") == nil end
  else return function(t) return not kicks[t] end end
end
function ui:macro_down(slot)
  local mc = self.macro
  if mc and mc.slot == slot and mc.latched then self:macro_finish(); return end   -- a macro that stayed: tap again to let it go
  if mc then self:macro_finish() end
  local r = (slot == 4) and self.me.macros[self.try_sel or 1] or self.me.macros[self.me.slots[slot]]
  if not r then return end
  local saved = { set = {}, mutes = {}, filter = self.v["ockm-filter"] or 0 }
  for _, m in ipairs(r.moves) do
    local t = TARGET[m.t]
    local ms = steps_ms(self, HOW[m.how] and HOW[m.how][2] or 0)
    if t and t.choices then
      local keep = keep_for(m.v, self:kick_slots())
      for _, tr in ipairs(TRACKS) do
        saved.mutes[tr] = self:mute_target(tr)
        local want = keep(tr) and 0 or 1
        if want ~= saved.mutes[tr] then self:qmute(tr, want) end
      end
    elseif t and t.id == "filter" then
      pd.send("ockm-filter-glide", "list", { m.v, math.max(30, ms) }); self.v["ockm-filter"] = m.v
    elseif t then
      saved.set[t.hook] = self.v[t.hook] or 0
      self:ramp(t.hook, t.switch and 1 or m.v, t.switch and 0 or ms)
    end
  end
  self.macro = { slot = slot, recipe = r, saved = saved }
end
-- put moves back: on letting go, all but the ones that stay; when finishing, everything
function ui:macro_restore(all)
  local mc = self.macro
  local r, saved = mc.recipe, mc.saved
  local stays = false
  for _, m in ipairs(r.moves) do
    local back = m.back or 1
    if back == 3 and not all then stays = true
    elseif not (all and back ~= 3 and mc.latched) then
      local t = TARGET[m.t]
      local glide = (back == 2) and steps_ms(self, 16) or 0
      if t and t.choices then
        for tr, x in pairs(saved.mutes) do if self:mute_target(tr) ~= x then self:qmute(tr, x) end end
      elseif t and t.id == "filter" then
        if self.filter_hold then pd.send("ockm-filter-glide", "list", { saved.filter, math.max(50, glide) }); self.v["ockm-filter"] = saved.filter
        elseif glide > 0 then pd.send("ockm-filter-glide", "list", { 0, glide }); self.v["ockm-filter"] = 0
        else self:filter_spring() end
      elseif t then
        self:ramp(t.hook, saved.set[t.hook] or 0, t.switch and 0 or glide)
      end
    end
  end
  return stays
end
function ui:macro_up(slot)
  local mc = self.macro
  if not mc or mc.slot ~= slot or mc.latched then return end
  if self:macro_restore(false) then mc.latched = true else self.macro = nil end
end
function ui:macro_finish()
  if not self.macro then return end
  self:macro_restore(true)
  self.macro = nil
end

-- ------------------------------------------------------------------ settings screen
local SECTIONS = { "this project", "new projects", "this device", "macros" }
local SX = 184                       -- where a section's content starts
function ui:layout_setup(add)
  local sec = self.set_sec or 1
  for i, nm in ipairs(SECTIONS) do
    add{ kind="choice", x=16, y=80 + (i - 1) * 56, w=154, h=48, label=nm, sel=(sec == i), tap=function() self.set_sec = i; self.edit_move = nil end }
  end
  add{ kind="text", x=16, y=H - 40, w=160, h=12, label="OCKM " .. VERSION, size=10 }
  add{ kind="text", x=16, y=H - 26, w=160, h=12, label=ockm_pretty(self.project), size=10 }
  if sec == 1 then self:layout_set_project(add)
  elseif sec == 2 then self:layout_set_new(add)
  elseif sec == 3 then self:layout_set_device(add)
  else self:layout_set_macros(add) end
end

function ui:layout_set_project(add)
  local cw = W - 16 - SX
  local bpm = math.floor(self.v["ockm-bpm"] or 124)
  add{ kind="text", x=SX, y=80, w=200, h=12, label="tempo", size=10 }
  add{ kind="text", x=SX, y=96, w=200, h=40, label=bpm .. " bpm", size=34, col="txt" }
  for i, d in ipairs({ -5, -1, 1, 5 }) do
    add{ kind="btn", x=SX + 230 + (i - 1) * 82, y=88, w=76, h=52, label=(d > 0 and "+" or "") .. d, tap=function() self:send("ockm-bpm", clamp(bpm + d, 40, 200)) end }
  end
  add{ kind="slider", x=SX, y=156, w=cw, h=40, hook="ockm-bpm", lo=60, hi=180, label="tempo" }
  add{ kind="slider", x=SX, y=212, w=cw, h=40, hook="ockm-swing", lo=50, hi=75, label="swing" }
  add{ kind="text", x=SX + 110, y=252, w=cw - 110, h=12, label="50 is straight, 58 a gentle house shuffle, 66 heavy", size=10 }
  add{ kind="slider", x=SX, y=276, w=cw, h=40, hook="ockm-accent", lo=0, hi=1, label="accents" }
  add{ kind="text", x=SX + 110, y=316, w=cw - 110, h=12, label="how much quieter an ordinary hit is than an accented one", size=10 }
  add{ kind="slider", x=SX, y=340, w=cw, h=40, hook="ockm-verb-tone", lo=0, hi=1, label="reverb tone" }
  add{ kind="text", x=SX, y=404, w=300, h=12, label="MIDI clock", size=10 }
  local half = (cw - 8) / 2
  local sync = math.floor(self.v["ockm-sync"] or 0)
  add{ kind="choice", x=SX, y=420, w=half, h=52, label="lead: my tempo, send clock out", sel=(sync == 0), tap=function() self:send("ockm-sync", 0) end }
  add{ kind="choice", x=SX + half + 8, y=420, w=half, h=52, label="follow incoming MIDI clock", sel=(sync == 1), tap=function() self:send("ockm-sync", 1) end }
  add{ kind="text", x=SX, y=492, w=cw, h=12, label="these belong to the project: save to keep them", size=10 }
end

-- a row of choices with a name on the left
function ui:set_row(add, y, name, note, opts, cur, pick)
  add{ kind="text", x=SX, y=y + 12, w=170, h=14, label=name, size=13, col="txt" }
  if note and note ~= "" then add{ kind="text", x=SX, y=y + 30, w=170, h=12, label=note, size=9 } end
  local x0, cw = SX + 180, W - 16 - SX - 180
  local ow = (cw - 6 * (#opts - 1)) / #opts
  for i, o in ipairs(opts) do
    add{ kind="choice", x=x0 + (i - 1) * (ow + 6), y=y, w=ow, h=48, label=o, small=true, sel=(cur == i), tap=function() pick(i) end }
  end
end

function ui:layout_set_new(add)
  local n = self.me.new
  add{ kind="text", x=SX, y=80, w=600, h=12, label="how a new blank project starts (yours, not the project's)", size=10 }
  local DL = { 16, 32, 64 }
  local SL = { 32, 64, 128 }
  local function idx(t, x) for i, v in ipairs(t) do if v == x then return i end end return 1 end
  self:set_row(add, 104, "drums", "you can build up from here", { "1 bar", "2 bars", "4 bars" }, idx(DL, n.drum), function(i) n.drum = DL[i]; self:save_settings() end)
  self:set_row(add, 164, "synths", "bass, lead and chords", { "2 bars", "4 bars", "8 bars" }, idx(SL, n.synth), function(i) n.synth = SL[i]; self:save_settings() end)
  local LN = {}; for i, l in ipairs(NEW_LEAD) do LN[i] = l[1] end
  self:set_row(add, 224, "lead starts as", "its notes and rhythm", LN, n.lead, function(i) n.lead = i; self:save_settings() end)
end

function ui:layout_set_device(add)
  local d = self.me.device
  add{ kind="text", x=SX, y=80, w=600, h=12, label="this device: kept here, not in projects", size=10 }
  self:set_row(add, 104, "theme", "", { "dark", "light" }, (d.theme == "light") and 2 or 1, function(i)
    d.theme = (i == 2) and "light" or "dark"; self.theme = THEMES[d.theme]; self:save_settings() end)
  self:set_row(add, 164, "filter lets go", "how fast it goes home", { "snap", "quick", "slow" }, d.snap, function(i)
    d.snap = i; SPRING_MS = SNAP_MS[i]; self:save_settings() end)
  self:set_row(add, 224, "mutes land", "where Perform B starts", { "now", "next beat", "next bar" }, (d.mutes or 0) + 1, function(i)
    d.mutes = i - 1; self.v["ockm-mute-quant"] = i - 1; pd.send("ockm-mute-quant", "float", { i - 1 }); self:save_settings() end)
  add{ kind="text", x=SX, y=300, w=W - 16 - SX, h=12, label="audio out (DAC or headphones) comes here once the DAC is fitted", size=10 }
  if KIOSK then
    add{ kind="btn", x=SX, y=H - 76, w=220, h=56, label="quit to desktop", tap=function() psend("pd", "quit", {}) end }
  end
end

-- macros: your six recipes on the left, the one you're editing on the right, and which slot it's on
function ui:layout_set_macros(add)
  local me = self.me
  local sel = self.mac_sel or 1
  local lw = 236
  for i = 1, 6 do
    local r = me.macros[i]
    local slot
    for s = 1, 3 do if me.slots[s] == i then slot = string.char(64 + s) end end
    add{ kind="recipe", x=SX, y=80 + (i - 1) * 84, w=lw, h=78, label=(r and #r.moves > 0) and r.name or "empty", sub=recipe_summary(r), slot=slot, sel=(sel == i),
         tap=function() self.mac_sel = i end }
  end
  local r = me.macros[sel]
  local ex, ew = SX + lw + 12, W - 16 - (SX + lw + 12)
  add{ kind="card", x=ex, y=80, w=ew, h=H - 12 - 80 }
  local ix, iw = ex + 8, ew - 16
  -- name: step through a list of names (there's no keyboard on the Pi)
  local ni = 1; for k, nm in ipairs(MACRO_NAMES) do if nm == r.name then ni = k end end
  add{ kind="arrow", x=ix, y=88, w=44, h=44, dir=-1, on=true, tap=function() r.name = MACRO_NAMES[(ni - 2) % #MACRO_NAMES + 1]; self:save_settings() end }
  add{ kind="preset", x=ix + 50, y=88, w=iw - 100, h=44, num="", label=r.name, sel=true, inline=true }
  add{ kind="arrow", x=ix + iw - 44, y=88, w=44, h=44, dir=1, on=true, tap=function() r.name = MACRO_NAMES[ni % #MACRO_NAMES + 1]; self:save_settings() end }
  -- the moves: what, how much, how it gets there, how it lets go. Tap a box to step through its choices
  local cols = { 112, iw - 112 - 104 - 104 - 34 - 24, 104, 104, 34 }
  local function colx(c) local x = ix; for k = 1, c - 1 do x = x + cols[k] + 6 end; return x end
  add{ kind="text", x=colx(1), y=140, w=100, h=10, label="move", size=9 }
  add{ kind="text", x=colx(2), y=140, w=100, h=10, label="amount", size=9 }
  add{ kind="text", x=colx(3), y=140, w=100, h=10, label="gets there", size=9 }
  add{ kind="text", x=colx(4), y=140, w=100, h=10, label="lets go", size=9 }
  for k, m in ipairs(r.moves) do
    local y = 154 + (k - 1) * 54
    local t = TARGET[m.t]
    add{ kind="btn", x=colx(1), y=y, w=cols[1], h=48, small=true, label=m.t, tap=function()
      local ti = 1; for q, tt in ipairs(TARGETS) do if tt.id == m.t then ti = q end end
      local nt = TARGETS[ti % #TARGETS + 1]
      m.t = nt.id; m.v = nt.choices and 1 or (nt.switch and 1 or ((nt.lo + nt.hi) / 2)); self:save_settings() end }
    if t.choices then
      add{ kind="btn", x=colx(2), y=y, w=cols[2], h=48, small=true, label=t.choices[m.v] or "?", tap=function() m.v = m.v % #t.choices + 1; self:save_settings() end }
    elseif t.switch then
      add{ kind="locked", x=colx(2), y=y, w=cols[2], h=48, label="on while held" }
    else
      local hk = "macro-edit-" .. k
      self.v[hk] = m.v
      add{ kind="hbar", x=colx(2), y=y, w=cols[2], h=48, hook=hk, lo=t.lo, hi=t.hi, label=m.t, bold=true, edit=function(x) m.v = x; self:save_settings() end }
    end
    add{ kind="btn", x=colx(3), y=y, w=cols[3], h=48, small=true, label=HOW[m.how][1], tap=function() m.how = m.how % #HOW + 1; self:save_settings() end }
    add{ kind="btn", x=colx(4), y=y, w=cols[4], h=48, small=true, label=BACK[m.back or 1], tap=function() m.back = (m.back or 1) % #BACK + 1; self:save_settings() end }
    add{ kind="btn", x=colx(5), y=y, w=cols[5], h=48, small=true, quiet=true, label="x", tap=function() table.remove(r.moves, k); self:save_settings() end }
  end
  if #r.moves < 4 then
    add{ kind="btn", x=ix, y=154 + #r.moves * 54, w=iw, h=40, small=true, quiet=true, label="+ add a move (up to 4)", tap=function()
      r.moves[#r.moves + 1] = { t = "reverb", v = 0.6, how = 1, back = 1 }; self:save_settings() end }
  end
  -- which slot on Perform B, and try it
  add{ kind="text", x=ix, y=H - 62, w=60, h=12, label="on slot", size=10 }
  for s = 1, 3 do
    add{ kind="choice", x=ix + 64 + (s - 1) * 62, y=H - 76, w=56, h=56, label=string.char(64 + s), sel=(me.slots[s] == sel), accent=true,
         tap=function() me.slots[s] = sel; self:save_settings() end }
  end
  local tw = iw - 64 - 3 * 62 - 6
  add{ kind="hold", x=ix + iw - tw, y=H - 76, w=tw, h=56, label="try it", sub="hold", on=(self.macro and self.macro.slot == 4),
       down=function() self.try_sel = sel; self:macro_down(4) end, up=function() self:macro_up(4) end }
end

-- Perform B: choose which recipe is on a slot
function ui:layout_slotpick(add)
  local s = self.pick_slot or 1
  add{ kind="scrim", x=0, y=0, w=W, h=H, tap=function() self.sheet = nil end }
  local x0, y0, w0 = W / 2 - 220, 110, 440
  add{ kind="sheet", x=x0, y=y0, w=w0, h=6 * 56 + 70 }
  add{ kind="text", x=x0 + 16, y=y0 + 16, w=w0 - 32, h=14, label="slot " .. string.char(64 + s) .. ": play which macro?", size=13, col="txt" }
  for i = 1, 6 do
    local r = self.me.macros[i]
    add{ kind="recipe", x=x0 + 16, y=y0 + 44 + (i - 1) * 56, w=w0 - 32, h=50, label=(r and #r.moves > 0) and r.name or "empty", sub=recipe_summary(r),
         sel=(self.me.slots[s] == i), tap=function() self.me.slots[s] = i; self:save_settings(); self.sheet = nil end }
  end
end

-- a new blank project starts the way you like (only what differs from how the engine starts one)
function ui:apply_new_defaults()
  local n = self.me.new
  if n.drum ~= 16 then psend("ockm-drum-len", "float", { n.drum }) end
  if n.synth ~= 64 then for _, p in ipairs(SYNTHS) do psend("ockm-" .. p .. "-len", "float", { n.synth }) end end
  local l = NEW_LEAD[n.lead or 1]
  if l and (n.lead or 1) ~= 1 then psend("ockm-lead-rhythm", "float", { l[2] }); psend("ockm-lead-notes", "float", { l[3] }) end
  if n.drum ~= 16 or n.synth ~= 64 or (n.lead or 1) ~= 1 then psend("ockm-save", "bang", {}) end
end

-- is a track playing a note on this step (and can it be heard)? For the lights on live
function ui:track_sounding(n)
  local t = TRACKS[n]
  if self:silent(t) then return false end
  if n <= 8 then return self:get("ockm-pat-"..t, self.step % self:plen("drum")) > 0 end
  return self:part_sounding(t)
end

function ui:open(screen)
  self.msg = nil
  self.screen = screen
  self.pick, self.confirm, self.sheet = nil, nil, nil
  if screen == "project" then psend("ockm-project-list", "bang", {}) end
  if screen == "drums" then psend("ockm-samples-scan", "bang", {}) end   -- pick up files added since
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
    local smp = math.floor(self.v["ockm-"..SLOTS[i].."-sample"] or 0)
    add{ kind="choice", x=16 + (i - 1) * (tw + 8), y=114, w=tw, h=40,
         label=SHORT[(self.v["ockm-"..SLOTS[i].."-sound"] or 0) + 1] .. (smp > 0 and string.format(" %02d", smp) or ""),
         sel=(i == self.slot), tap=function() self.slot = i; self:preview(i, true) end }
  end
  self:step_row(add, D_STEP_Y, D_STEP_H, "dstep")
  -- the lane under the steps: velocity or timing, dragged up and down per step
  local lane = self.lane or "vel"
  for i, m in ipairs({ { "vel", "velocity" }, { "time", "timing" } }) do
    add{ kind="choice", x=16 + (i - 1) * 90, y=270, w=84, h=24, small=true, label=m[2], sel=(lane == m[1]), tap=function()
      self.lane = m[1]
      self:say((m[1] == "vel") and "velocity: drag the bars up and down, or swipe across them" or "timing: drag up to push a hit late, down to pull it early")
    end }
  end
  add{ kind="hbar", x=196, y=270, w=190, h=24, hook="ockm-swing", lo=50, hi=75, label="swing" }
  -- the drums in or out of this pattern (the same as their tile on the builder)
  add{ kind="onoff", x=W - 16 - 110, y=267, w=110, h=30, on=(self.v["ockm-drums-on"] or 1) > 0,
       tap=function() self:send("ockm-drums-on", ((self.v["ockm-drums-on"] or 1) > 0) and 0 or 1) end }
  add{ kind="vlane", x=0, y=300, w=W, h=38 }
  -- this slot's sound on the left, grooves for the whole kit on the right
  local half = (W - 48) / 2
  -- sample: 0 is the built-in synth sound, then the files in this sound's folder. Tap the box to hear it
  local slot, smp, cnt = self.slot, math.floor(self.v["ockm-"..nm.."-sample"] or 0), self:sample_count(self.slot)
  local snd = math.floor(self.v["ockm-"..nm.."-sound"] or 0)
  local folder = FOLDERS[SOUND_DIR[snd + 1]]
  local pos = self:drum_pos(slot)
  local ns = self:synth_count(slot)
  local sname = self:synth_name(slot)
  -- the sound box: arrows either side, then save (your own sound) or, on one of your saved sounds, delete
  local cur = self:current_preset(slot)
  local nps = #self:presets_for(slot)
  local last = ns + nps + cnt - 1
  local bw = 260
  add{ kind="arrow", x=16, y=346, w=44, h=36, dir=-1, on=(pos > 0), tap=function() if pos > 0 then self:set_drum_pos(slot, pos - 1) end end }
  add{ kind="preset", x=66, y=346, w=bw, h=36, inline=true, sel=(smp > 0),
       num=(smp > 0) and string.format("%02d", smp) or (cur and "mine" or "synth"),
       label=(smp > 0) and (self:kit_of(slot) and (self:kit_of(slot) .. " kit") or ("of " .. cnt .. "  " .. folder)) or (cur and self.me.sounds[cur].name or sname),
       tap=function() self:audition(slot) end }
  add{ kind="arrow", x=66 + bw + 6, y=346, w=44, h=36, dir=1, on=(pos < last), tap=function() if pos < last then self:set_drum_pos(slot, pos + 1) end end }
  if cur then
    add{ kind="bin", x=66 + bw + 56, y=346, w=44, h=36, lit=(self.flashing == "save"), tap=function() self:delete_sound(cur) end }
  else
    add{ kind="disc", x=66 + bw + 56, y=346, w=44, h=36, lit=(self.flashing == "save"), off=(smp > 0) or nil, tap=function() self:save_sound(slot) end }
  end
  -- the synth's shape: character (its lab recipe) and morph sweep several settings at once; randomise and reset.
  -- Greyed out while the slot plays a sample
  local off = (smp > 0) or nil
  local y = 388
  add{ kind="hbar", x=16, y=y, w=128, h=30, hook="ockm-"..nm.."-labchar", lo=-1, hi=1, label=off and "character" or (LAB_CHAR[sname] or "character"), bold=true, off=off, preview=slot }
  add{ kind="hbar", x=150, y=y, w=110, h=30, hook="ockm-"..nm.."-labmorph", lo=0, hi=1, label="morph", bold=true, off=off, preview=slot }
  add{ kind="btn", x=266, y=y, w=70, h=30, small=true, label="random", off=off, flash="random", tap=function() self:lab_random(slot, 0.35) end }
  add{ kind="btn", x=342, y=y, w=56, h=30, small=true, label="wild", off=off, flash="wild", tap=function() self:lab_random(slot, 1) end }
  add{ kind="btn", x=404, y=y, w=half - 388, h=30, small=true, quiet=true, label="reset", off=off, flash="reset", tap=function() self:lab_reset(slot) end }
  for j, p in ipairs((smp > 0) and SAMPLE_SLIDERS or SYNTH_SLIDERS) do
    add{ kind="slider", x=16, y=424 + (j - 1) * 27, w=half, h=24, hook="ockm-"..nm.."-"..p[1], lo=p[2], hi=p[3], label=p[4] or p[1], preview=slot }
  end
  -- this drum's reverb and delay sends (the same as on the mixer)
  local sw = (half - 6) / 2
  self:group(add, 16, 562, half, 30)
  add{ kind="hbar", x=16, y=562, w=sw, h=30, hook="ockm-"..nm.."-verb", lo=0, hi=1, label="reverb", bold=true, preview=slot }
  add{ kind="hbar", x=16 + sw + 6, y=562, w=sw, h=30, hook="ockm-"..nm.."-delay", lo=0, hi=1, label="delay", bold=true, preview=slot }
  local gx = 16 + half + 16
  -- grooves, in banks of 12 (plus clear)
  local cur = math.floor(self.v["ockm-drum-groove"] or -1)
  if not self.bank then
    self.bank = 1
    for b, bk in ipairs(GROOVE_BANKS) do if cur >= bk[2] then self.bank = b end end
  end
  local nb = #GROOVE_BANKS
  local bkw = (half - (nb - 1) * 4) / nb
  for b, bk in ipairs(GROOVE_BANKS) do
    add{ kind="choice", x=gx + (b - 1) * (bkw + 4), y=342, w=bkw, h=24, small=true, label=bk[1], sel=(self.bank == b), tap=function() self.bank = b end }
  end
  local gw = (half - 4 * 6) / 5
  local first = GROOVE_BANKS[self.bank][2]
  local shown = {}
  for n = first, first + 11 do if GROOVES[n + 1] and GROOVES[n + 1] ~= "clear" then shown[#shown + 1] = n end end
  shown[#shown + 1] = 12   -- clear
  for k, n in ipairs(shown) do
    local name = GROOVES[n + 1]
    local col, row = (k - 1) % 5, math.floor((k - 1) / 5)
    local clear = (name == "clear")
    add{ kind=clear and "btn" or "choice", x=gx + col * (gw + 6), y=372 + row * 40, w=gw, h=34, label=name, small=true, quiet=clear,
         sel=(not clear) and (cur == n) or nil, tap=function()
           self:snapshot(clear and "clear" or name)
           self:send("ockm-drum-groove", n)
           self:say_undo(clear and "drums cleared" or (name .. ": all 8 drums rewritten"))
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
  local sw = (half - (#FILLS - 1) * 6) / #FILLS
  for i, name in ipairs(FILLS) do
    add{ kind="choice", x=gx + (i - 1) * (sw + 6), y=552, w=sw, h=34, small=true, label=name, sel=(style == i - 1), disabled=(every == 0),
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
function ui:locked(part) return false end   -- v0.74: no modes; any part's steps can be edited (and editing makes it yours)
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
    parts[#parts + 1] = ((rhythms_for(part)[(self.v["ockm-"..part.."-rhythm"] or 0) + 1] or {""})[1])
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
  if true then
    -- pick the note (or chord) for the selected step (editing makes the part yours)
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
  -- yours or made for you; when the harmony has moved under your line, offer to refit it; on/off top right (as on the builder)
  local yours = self:part_yours(part)
  local HTX = W - 16 - 110 - 6 - 86 - 6 - 100   -- the half-time switch; slide and on/off sit to its right
  local hk = "ockm-"..part.."-half"
  local ht = (self.v[hk] or 0) > 0
  add{ kind="choice", x=HTX, y=266, w=100, h=34, small=true, accent=true, sel=ht, label="half-time",
       tap=function() self:send(hk, ht and 0 or 1); self:say(ht and (part .. " back to full speed") or (part .. " at half speed: its pattern over two loops")) end }
  local moved = (part ~= "chord") and self:harmony_moved(part)
  local clash = moved and self:clashes(part) or {}
  if #clash > 0 then
    add{ kind="text", x=16, y=276, w=W - 570, h=12, size=11, col="acc",
         label="the harmony changed: " .. #clash .. ((#clash == 1) and " note no longer fits" or " notes no longer fit") }
    add{ kind="btn", x=HTX - 6 - 80 - 6 - 130, y=266, w=130, h=34, small=true, accent=true, label="refit my line", tap=function() self:refit(part) end }
    add{ kind="btn", x=HTX - 6 - 80, y=266, w=80, h=34, small=true, quiet=true, label="leave it", tap=function() self.claim_harm[part] = self:harm_sig() end }
  else
    local info = self.msg or (yours and ("yours: " .. self:step_info()) or ((part == "chord") and "plays the harmony from the builder. Edit a step and it becomes yours"
      or "made for you: follows the harmony. Edit a step and it becomes yours"))
    add{ kind="text", x=16, y=276, w=HTX - 32, h=12, label=info, size=11, col=self.msg and "acc" or nil }
    if mono then
      add{ kind="choice", x=W - 16 - 110 - 6 - 86, y=266, w=86, h=34, label="slide", accent=true, small=true, sel=self:mono_get(self.sel_step, "slide") > 0,
           tap=function() self:mono_toggle_slide() end }
    end
  end
  local onk = "ockm-"..part.."-on"
  add{ kind="onoff", x=W - 16 - 110, y=268, w=110, h=30, on=(self.v[onk] or 1) > 0, tap=function() self:send(onk, ((self.v[onk] or 1) > 0) and 0 or 1) end }
  self:layout_synth_sound(add, part, mono)
end

function ui:layout_synth_sound(add, part, mono)
  local half = (W - 48) / 2
  -- left: where the notes come from (the same settings as this part's column on compose)
  add{ kind="card", x=16, y=306, w=half, h=H - 306 - 6 }
  self:gen_controls(add, part, 28, 290, half - 24, 0.88)
  -- right: the sound
  local rx, rw = 16 + half + 16, half
  add{ kind="text", x=rx, y=314, w=200, h=12, label="sound", size=10 }
  local eng = engines_of(part)
  local ew = rw / #eng
  for i = 1, #eng do
    local e = (part == "lead") and LEAD_ORDER[i] or (part == "bass") and MONO_ORDER[i] or (i - 1)
    add{ kind="choice", x=rx + (i - 1) * ew, y=330, w=ew - 4, h=40, label=eng[e + 1], small=true, sel=(self.v["ockm-"..part.."-engine"] == e),
         tap=function() self:send("ockm-"..part.."-engine", e) end }
  end
  local kn = KNOBS[eng[(self.v["ockm-"..part.."-engine"] or 0) + 1]] or KNOBS.acid
  local kw = (rw - 6) / 2
  for k = 1, 4 do
    local col, row = (k - 1) % 2, math.floor((k - 1) / 2)
    add{ kind="hbar", x=rx + col * (kw + 6), y=376 + row * 44, w=kw, h=40, hook="ockm-"..part.."-k"..k, lo=0, hi=1, label=kn[k], bold=true }
  end
  -- drive on its own, the reverb and delay sends on one panel, then level and chorus
  local n = mono and 5 or 4
  local gaps = mono and (6 + 6 + 14 + 14) or (6 + 6 + 14)
  local tw = (rw - gaps) / n
  local x = rx
  if mono then
    add{ kind="hbar", x=x, y=466, w=tw, h=40, hook="ockm-"..part.."-drive", lo=0, hi=1, label="drive", bold=true }
    x = x + tw + 14
  end
  self:group(add, x, 466, 2 * tw + 6, 40)
  add{ kind="hbar", x=x, y=466, w=tw, h=40, hook="ockm-"..part.."-verb", lo=0, hi=1, label="reverb", bold=true }
  add{ kind="hbar", x=x + tw + 6, y=466, w=tw, h=40, hook="ockm-"..part.."-delay", lo=0, hi=1, label="delay", bold=true }
  x = x + 2 * tw + 6 + 14
  add{ kind="hbar", x=x, y=466, w=tw, h=40, hook="ockm-"..part.."-level", lo=0, hi=1, label="level", bold=true }
  -- chorus, Juno-style: tap to step through off, I, II, I+II
  local ch = math.floor(self.v["ockm-"..part.."-chorus"] or 0)
  add{ kind="choice", x=x + tw + 6, y=466, w=tw, h=40, small=true, accent=true, sel=(ch > 0), label="chorus " .. CHORUS[ch + 1],
       tap=function() self:send("ockm-"..part.."-chorus", (ch + 1) % #CHORUS) end }
  -- movement: an LFO on one of the four knobs, in time with the loop. Tap a box to step through it
  local key = function(k) return "ockm-"..part.."-lfo-"..k end
  local shape, rate, tgt = math.floor(self.v[key("shape")] or 0), math.floor(self.v[key("rate")] or 4), math.floor(self.v[key("target")] or 1)
  local lw = (rw - 18) / 4
  self:group(add, rx, 514, rw, 34)
  add{ kind="btn", x=rx, y=514, w=lw, h=34, small=true, label="lfo " .. LFO_SHAPES[shape + 1], tap=function() self:send(key("shape"), (shape + 1) % #LFO_SHAPES) end }
  add{ kind="btn", x=rx + (lw + 6), y=514, w=lw, h=34, small=true, label="on " .. (kn[tgt] or "?"), tap=function() self:send(key("target"), tgt % 4 + 1) end }
  add{ kind="btn", x=rx + 2 * (lw + 6), y=514, w=lw, h=34, small=true, label="every " .. LFO_RATES[rate + 1], tap=function() self:send(key("rate"), (rate + 1) % #LFO_RATES) end }
  add{ kind="hbar", x=rx + 3 * (lw + 6), y=514, w=lw, h=34, hook=key("depth"), lo=0, hi=1, label="depth", bold=true }
  if part == "chord" then
    local vo = math.floor(self.v["ockm-chord-voicing"] or 0)
    local cw = (rw - 24) / 5
    for i, nm in ipairs({ "close", "open", "wide" }) do
      add{ kind="choice", x=rx + (i - 1) * (cw + 6), y=558, w=cw, h=34, label=nm, small=true, sel=(vo == i - 1), tap=function() self:send("ockm-chord-voicing", i - 1) end }
    end
    add{ kind="hbar", x=rx + 3 * (cw + 6), y=558, w=2 * cw + 6, h=34, hook="ockm-chord-strum", lo=0, hi=1, label="strum", bold=true }
  end
end

-- v0.74: there are no modes. A pattern saved with one (melody or bass priority, or manual) opens with the lead following
-- the harmony again; parts you'd edited stay yours, and a bass that ignored the chords keeps doing so (pedal)
function ui:check_roles()
  if self:mode() ~= 0 then
    self:send("ockm-leader", 0)
    self:send("ockm-lead-sync", 1)
  end
  -- the rhythm lock (on the kick, fill gaps) is gone: a part made for you goes back to its own rhythm
  for _, p in ipairs({ "bass", "lead" }) do
    if (self.v["ockm-"..p.."-lock"] or 0) ~= 0 and not self:part_yours(p) then self:send("ockm-"..p.."-lock", 0) end
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
  local L = self:plen(src)      -- the leading part repeats at its own length
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

-- a group of controls that belong together sits on one panel (drawn first, so it's behind them)
local GROUP_PAD = 3
function ui:group(add, x, y, w, h)
  add{ kind="group", x=x - GROUP_PAD, y=y - GROUP_PAD, w=w + 2 * GROUP_PAD, h=h + 2 * GROUP_PAD }
end
-- the master delay (amount, feedback, time) and reverb (amount, size), each on its own panel
function ui:fx_groups(add, row, x, y, w, h)
  local cw = (w - 3 * 6 - 14) / 5
  local x2 = x + 3 * (cw + 6) + 8
  self:group(add, x, y, 3 * cw + 12, h)
  self:group(add, x2, y, 2 * cw + 6, h)
  for i, m in ipairs(row) do
    local cx = (i <= 3) and (x + (i - 1) * (cw + 6)) or (x2 + (i - 4) * (cw + 6))
    add{ kind="hbar", x=cx, y=y, w=cw, h=h, hook=m[1], lo=m[2], hi=m[3], label=m[4], bold=true }
  end
end

-- a stepper: back, the current choice (number, name, detail), forward
function ui:stepper(add, x, y, w, h, list, hook, after)
  local n = #list
  local v = math.floor(self.v[hook] or 0)
  add{ kind="arrow", x=x, y=y, w=44, h=h, dir=-1, on=(v > 0), tap=function() if v > 0 then self:send(hook, v - 1); if after then after(v - 1) end end end }
  local item = list[v + 1] or { "" }
  add{ kind="preset", x=x + 50, y=y, w=w - 100, h=h, num=v + 1, label=type(item) == "table" and item[1] or item,
       sub=type(item) == "table" and item[2] or nil, sel=true }
  add{ kind="arrow", x=x + w - 44, y=y, w=44, h=h, dir=1, on=(v < n - 1), tap=function() if v < n - 1 then self:send(hook, v + 1); if after then after(v + 1) end end end }
end

-- ------------------------------------------------------------------ the song screen (internally "compose")
-- What's in this pattern (each part in or out: out is silent and Perform can't bring it back) and the harmony: the
-- progression, key and scale every part follows, with a turnaround, and fitting the chords to a line of your own.
local PART_ON = { drums = "ockm-drums-on", bass = "ockm-bass-on", chords = "ockm-chord-on", lead = "ockm-lead-on" }
local ROMAN = { "i", "ii", "iii", "iv", "v", "vi", "vii" }
function ui:part_in(p) return (self.v[PART_ON[p] or ("ockm-"..p.."-on")] or 1) > 0 end
-- is a track (d1-d8, bass, lead, chord) in this pattern?
function ui:track_in(t)
  if string.sub(t, 1, 1) == "d" then return (self.v["ockm-drums-on"] or 1) > 0 end
  return (self.v["ockm-"..t.."-on"] or 1) > 0
end
function ui:part_yours(p) return (self.v["ockm-"..p.."-mode"] or 0) > 0 and not self:part_empty(p) end
-- a chord's name from its scale step: "Am", "F", "Bdim", with 7/9/11 when the chords are coloured; turn = the turnaround's V
function ui:chord_name(d, turn)
  local sc, root = self:scale(), math.floor(self.v["ockm-root"] or 9)
  d = ((math.floor(d) % 7) + 7) % 7
  local r = sc[d + 1]
  local third = (sc[((d + 2) % 7) + 1] - r) % 12
  local fifth = (sc[((d + 4) % 7) + 1] - r) % 12
  if turn then third = 4; fifth = 7 end
  local q = (third == 3) and ((fifth == 6) and "dim" or "m") or ""
  local ext = ({ [1] = "7", [6] = "9", [7] = "11" })[math.floor(self.v["ockm-chord-type"] or 0)] or ""
  if q == "dim" and ext ~= "" then q = "m" end
  local rn = ROMAN[d + 1]
  if third == 4 then rn = string.upper(rn) end
  return NOTES[((root + r) % 12) + 1] .. q .. ext, rn
end
-- kits (v0.77): a kit is one file per sound folder called kit-<name> (samples/kick/kit-breaks.wav and so on)
function ui:sample_name(slot, n)
  local snd = math.floor(self.v["ockm-"..SLOTS[slot].."-sound"] or 0)
  local t = (self.snames or {})[SOUND_DIR[snd + 1]]
  return t and t[n]
end
-- the sample number of this slot's sound in a kit, or nil when the kit has none for it
function ui:kit_sample(slot, kit)
  local snd = math.floor(self.v["ockm-"..SLOTS[slot].."-sound"] or 0)
  for n, name in pairs((self.snames or {})[SOUND_DIR[snd + 1]] or {}) do
    if name == "kit-" .. kit then return n end
  end
end
-- the kit this slot is playing from, if any
function ui:kit_of(slot)
  local smp = math.floor(self.v["ockm-"..SLOTS[slot].."-sample"] or 0)
  local name = smp > 0 and self:sample_name(slot, smp)
  return name and name:match("^kit%-(.+)$")
end

-- styles (v0.76): one tap sets the tempo, swing, groove, the kick/clap/snare character, what each part plays and on
-- which sound, the harmony, sends and half-time. Drum slots playing a sample or a saved sound keep it. Undo puts it all back.
-- drums: per voice { tune, decay, drive, character }. Parts: false = out of the pattern. Bass move 0 pedal, 1 follows, 2 walks.
local STYLES = {
  { "house", bpm=124, swing=56, groove=1, prog=1, type=1,
    drums={ kick={ 0, 100, 0.1, 0.2 }, clap={ 0, 100, 0, 0 } },
    bass={ engine=5, rhythm=0, notes=2, move=1 },
    chord={ engine=0, rhythm=2, verb=0.15, delay=0.15 },
    lead={ engine=1, rhythm=10, notes=15, freedom=1, verb=0.15, delay=0.2 } },
  { "deep house", bpm=123, swing=56, groove=2, prog=3, type=6,
    drums={ kick={ -1, 110, 0.1, 0 }, clap={ 0, 100, 0, 0.1 } },
    bass={ engine=5, rhythm=9, notes=2, move=1, k={ 0.35, 0.2, 0.4, 0.45 } },
    chord={ engine=4, rhythm=6, verb=0.25, delay=0.15 },
    lead=false },
  { "tech house", bpm=125, swing=54, groove=3, prog=0, type=1,
    drums={ kick={ 0, 90, 0.3, 0.4 }, clap={ 0, 80, 0, -0.5 } },
    bass={ engine=5, rhythm=14, notes=0, move=1, sidechain=0.3, k={ 0.35, 0.3, 0.5, 0.35 } },
    chord={ engine=0, rhythm=3, delay=0.25 },
    lead=false },
  { "techno", bpm=132, swing=50, groove=5, prog=0, type=0,
    drums={ kick={ -2, 150, 0.5, 0.5 }, clap={ 0, 70, 0.2, -0.6 } },
    bass={ engine=5, rhythm=10, notes=0, move=0, sidechain=0.5, k={ 0.25, 0.2, 0.35, 0.3 } },
    chord={ engine=0, rhythm=3, delay=0.35 },
    lead=false },
  { "hard house", bpm=145, swing=50, groove=37, prog=1, type=0,
    drums={ kick={ 0, 110, 0.7, 0.8 }, clap={ 0, 90, 0.3, -0.3 } },
    bass={ engine=6, rhythm=0, notes=1, move=1 },
    chord=false,
    lead={ engine=3, rhythm=0, notes=1, freedom=0, delay=0.15 } },
  { "acid", bpm=128, swing=50, groove=29, prog=0, type=0,
    drums={ kick={ 0, 110, 0.4, 0.4 }, clap={ 0, 90, 0.1, -0.3 } },
    bass={ engine=0, rhythm=13, notes=3, move=0, delay=0.15 },
    chord=false, lead=false },
  { "dub techno", bpm=120, swing=52, groove=6, prog=2, type=1,
    drums={ kick={ -1, 130, 0.2, 0 }, clap={ 0, 100, 0, 0.3 } },
    bass={ engine=1, rhythm=5, notes=0, move=1 },
    chord={ engine=0, rhythm=3, verb=0.3, delay=0.5 },
    lead=false },
  { "garage", bpm=132, swing=62, groove=7, prog=4, type=1,
    drums={ kick={ 0, 90, 0.1, 0.3 }, clap={ 1, 90, 0, 0 } },
    bass={ engine=1, rhythm=8, notes=2, move=1 },
    chord={ engine=1, rhythm=7, verb=0.1 },
    lead=false },
  { "speed garage", bpm=135, swing=60, groove=20, prog=1, type=1,
    drums={ kick={ 0, 110, 0.3, 0.4 }, clap={ 0, 90, 0.1, -0.2 }, snare={ 1, 70, 0.1, 0.3 } },
    bass={ engine=1, rhythm=17, notes=1, move=1, sidechain=0.2, k={ 0.55, 0.6, 0.5, 0.55 } },
    chord={ engine=1, rhythm=7, verb=0.1 },
    lead=false },
  -- the drum + bass, boom bap and lofi kits are samples (kit-breaks, kit-boom, kit-dusty); without them, the synth kit as below
  { "drum + bass", bpm=174, swing=50, groove=39, prog=3, type=6, kit="breaks",
    drums={ kick={ 3, 70, 0.6, 0.9 }, snare={ 2, 80, 0.5, 0.9 }, hat={ 2, 40, 0, 0.5 } },
    bass={ engine=3, rhythm=5, notes=0, move=1, half=1, sidechain=0.3, shape=0, k={ 0.5, 0.45, 0.05, 0.6 } },
    chord={ engine=2, rhythm=0, half=1, verb=0.3 },
    lead=false },
  { "boom bap", bpm=90, swing=62, groove=9, prog=9, type=1, kit="boom",
    drums={ kick={ -1, 160, 0.4, 0.6 }, snare={ -1, 110, 0.4, 0.6 }, hat={ 0, 60, 0, 0 } },
    bass={ engine=1, rhythm=15, notes=2, move=1, k={ 0.35, 0.3, 0.2, 0.6 } },
    chord={ engine=3, rhythm=8, verb=0.15 },
    lead=false },
  { "lofi", bpm=80, swing=64, groove=36, prog=3, type=6, kit="dusty",
    drums={ kick={ -2, 140, 0.2, -0.3 }, snare={ -2, 100, 0.2, -0.3 }, hat={ -1, 60, 0, -0.5 } },
    bass={ engine=1, rhythm=16, notes=2, move=1, k={ 0.25, 0.1, 0.1, 0.6 } },
    chord={ engine=4, rhythm=6, verb=0.25, delay=0.1 },
    lead=false },
}
function ui:layout_compose(add)
  -- style: one tap sets the lot
  add{ kind="text", x=16, y=114, w=W - 32, h=12, size=10,
       label="style: sets the tempo, groove, drums, sounds and parts in one go (undo puts it back)" }
  local per = math.ceil(#STYLES / 2)
  local stw = (W - 32 - (per - 1) * 4) / per
  local cst = math.floor(self.v["ockm-style"] or -1)
  for i, st in ipairs(STYLES) do
    local col, row = (i - 1) % per, math.floor((i - 1) / per)
    add{ kind="choice", x=16 + col * (stw + 4), y=128 + row * 32, w=stw, h=28, small=true, label=st[1], sel=(cst == i - 1),
         tap=function() self:apply_style(i) end }
  end
  -- in this pattern: four tiles
  add{ kind="text", x=16, y=196, w=W - 32, h=12, size=10,
       label="in this pattern: tap a part to switch it on or off (off is silent, and nothing on Perform brings it back)" }
  local tw = (W - 32 - 3 * 8) / 4
  local eng = function(part) local e = engines_of(part); return e[(math.floor(self.v["ockm-"..part.."-engine"] or 0)) + 1] or "" end
  for i, p in ipairs({ "drums", "bass", "chords", "lead" }) do
    local on = self:part_in(p)
    local l1, l2
    if p == "drums" then
      local gi = math.floor(self.v["ockm-drum-groove"] or -1)
      l1 = (gi >= 0 and GROOVES[gi + 1]) and (GROOVES[gi + 1] .. " groove") or "your pattern"; l2 = "8 slots"
    elseif p == "chords" then
      l1 = eng("chord") .. ", " .. ((CHORD_RHY[(self.v["ockm-chord-rhythm"] or 0) + 1] or {""})[1]); l2 = "plays the harmony"
    else
      l1 = eng(p); l2 = self:part_yours(p) and "yours: you've edited it" or "made for you: follows the harmony"
    end
    if not on then l1 = "off in this pattern"; l2 = (p == "chords") and "silent: the harmony still steers" or "Perform won't bring it back" end
    add{ kind="parttile", x=16 + (i - 1) * (tw + 8), y=210, w=tw, h=80, label=p, on=on, l1=l1, l2=l2, tap=function()
      self:send(PART_ON[p], on and 0 or 1)
    end }
  end
  -- the harmony
  add{ kind="text", x=16, y=298, w=W - 32, h=12, size=10,
       label="harmony: the map the bass, chords and lead all follow (it steers even when the chords are out)" }
  self:stepper(add, 16, 312, 330, 66, PROGS, "ockm-chord-prog", function() self.ranking = nil end)
  local rx = 16 + 330 + 12
  local rw = W - 16 - rx
  local kw = (rw - 11 * 3) / 12
  for k = 0, 11 do
    add{ kind="choice", x=rx + k * (kw + 3), y=312, w=kw, h=31, label=NOTES[k + 1], small=true, sel=(self.v["ockm-root"] == k),
         tap=function() self:send("ockm-root", k) end }
  end
  local sw = (rw - 5 * 3) / 6
  for sc = 0, 5 do
    add{ kind="choice", x=rx + sc * (sw + 3), y=347, w=sw, h=31, label=SCALE_NAMES[sc + 1], small=true, sel=(self.v["ockm-scale"] == sc),
         tap=function() self:send("ockm-scale", sc) end }
  end
  -- or fit the chords to a line of your own; and the turnaround
  add{ kind="text", x=16, y=397, w=140, h=12, label="or fit the chords to", size=10 }
  for i, src in ipairs({ "bass", "lead" }) do
    local ok = self:part_yours(src)
    add{ kind="choice", x=150 + (i - 1) * 118, y=388, w=112, h=28, small=true, disabled=not ok, sel=ok and self.rank_src == src and self.ranking ~= nil,
         label=(self.rank_src == src and self.ranking) and ("next for my " .. src) or ("my " .. src),
         tap=ok and function() self:fit_chords(src) end or nil }
  end
  add{ kind="text", x=W - 16 - 4 * 70 - 90, y=397, w=88, h=12, label="turnaround", size=10 }
  local te = math.floor(self.v["ockm-turn-every"] or 0)
  for i, e in ipairs({ 0, 4, 8, 16 }) do
    add{ kind="choice", x=W - 16 - (5 - i) * 70, y=388, w=64, h=28, small=true, sel=(te == e), label=(e == 0) and "off" or ("every " .. e),
         tap=function() self:send("ockm-turn-every", e) end }
  end
  -- the map, bar by bar
  local shape = PROG_SHAPES[(math.floor(self.v["ockm-chord-prog"] or 0)) + 1] or { { 0, 16 } }
  local bars, at = {}, 0
  for _, seg in ipairs(shape) do
    local b = math.floor(at / 16) + 1
    bars[b] = bars[b] or {}
    local nm, rn = self:chord_name(seg[1])
    if #bars[b] == 0 or bars[b][#bars[b]].name ~= nm then bars[b][#bars[b] + 1] = { name = nm, roman = rn } end
    at = at + seg[2]
    while at > b * 16 do b = b + 1; bars[b] = { { name = nm, roman = rn } } end
  end
  local nb = math.min(#bars, 8)
  local key = NOTES[(math.floor(self.v["ockm-root"] or 9) % 12) + 1] .. " " .. SCALE_NAMES[(self.v["ockm-scale"] or 0) + 1]
  add{ kind="text", x=16, y=426, w=W - 32, h=12, size=10,
       label="the map, bar by bar (" .. key .. ")" .. ((te > 0) and ("   turnaround: the last bar of every " .. te .. " goes to " .. self:chord_name(4, true)) or "") }
  local playing_bar = (self.playing ~= 0) and (math.floor((self.step or 0) % math.max(16, nb * 16) / 16) + 1) or nil
  local bw = (W - 32 - (nb - 1) * 6) / nb
  for i = 1, nb do
    local names, romans = {}, {}
    for _, c in ipairs(bars[i]) do names[#names + 1] = c.name; romans[#romans + 1] = c.roman end
    add{ kind="bar", x=16 + (i - 1) * (bw + 6), y=440, w=bw, h=146, n=i, label=table.concat(names, "  "), sub=table.concat(romans, " "),
         now=(playing_bar == i) }
  end
end

-- fit the chords to your own bass or lead: rank every progression against its notes, and step through the best
function ui:fit_chords(src)
  local what = (src == "lead") and "lead" or "bass line"
  if self.rank_src ~= src then self.ranking = nil end
  self.rank_src = src
  if not self.ranking then
    local r = {}
    for pi = 1, #PROG_SHAPES do
      local sc = self:score_prog(pi, src)
      if not sc then self:say("the " .. what .. " has no notes yet"); return end
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
  self:say(string.format("chords for your %s, %d of %d: %s (fits %d%%)", what, self.rank_at, #self.ranking, (PROGS[pick[1] + 1] or { "" })[1], fit))
end

function ui:apply_style(i)
  local st = STYLES[i]
  if not st then return end
  self:snapshot(st[1])
  self:send("ockm-bpm", st.bpm)
  self:send("ockm-drums-on", 1)
  self:send("ockm-drum-groove", st.groove)   -- the groove sets its own swing: the style's comes after
  self:send("ockm-swing", st.swing)
  self:send("ockm-turn-every", 0)
  for slot = 1, #SLOTS do
    local nm, t = SLOTS[slot], self:voice_type(slot)
    local d = st.drums[t]
    local ks = st.kit and self:kit_sample(slot, st.kit)
    if ks then   -- the style's kit has this sound: play it as it is
      self:send("ockm-"..nm.."-sample", ks); self:send("ockm-"..nm.."-tune", 0); self:send("ockm-"..nm.."-decay", 100)
      self:send("ockm-"..nm.."-tone", 0); self:send("ockm-"..nm.."-verb", 0); self:send("ockm-"..nm.."-delay", 0)
      d = nil
    elseif self:kit_of(slot) then   -- on another style's kit: back to the synth sound (your own samples stay)
      self:send("ockm-"..nm.."-sample", 0)
    end
    if d and math.floor(self.v["ockm-"..nm.."-sample"] or 0) == 0 and not self:current_preset(slot) then
      self:send("ockm-"..nm.."-tune", d[1]); self:send("ockm-"..nm.."-decay", d[2])
      self:send("ockm-"..nm.."-drive", d[3]); self:send("ockm-"..nm.."-labchar", d[4])
    end
    if d then self:send("ockm-"..nm.."-verb", 0); self:send("ockm-"..nm.."-delay", 0) end
  end
  self:send("ockm-chord-prog", st.prog)
  self:send("ockm-chord-type", st.type)
  for _, part in ipairs({ "bass", "chord", "lead" }) do
    local ps = st[part]
    self:send("ockm-"..part.."-on", ps and 1 or 0)
    if ps then
      self:send("ockm-"..part.."-engine", ps.engine)
      if ps.k then for j = 1, 4 do self:send("ockm-"..part.."-k"..j, ps.k[j]) end end
      self:send("ockm-"..part.."-rhythm", ps.rhythm)
      if ps.notes then self:send("ockm-"..part.."-notes", ps.notes) end
      if ps.move then self:set_bass_move(ps.move) end
      if ps.freedom then self:send("ockm-lead-freedom", ps.freedom) end
      self:send("ockm-"..part.."-half", ps.half or 0)
      self:send("ockm-"..part.."-sidechain", ps.sidechain or 0)
      self:send("ockm-"..part.."-scshape", ps.shape or 1)
      self:send("ockm-"..part.."-verb", ps.verb or 0); self:send("ockm-"..part.."-delay", ps.delay or 0)
      if part ~= "chord" then self:send("ockm-"..part.."-mode", 0) end   -- made for you again, so it follows the new style
    end
  end
  self:send("ockm-style", i - 1)
  self:say_undo(st[1] .. ": tempo, groove, sounds and parts set")
end

-- a part's settings on its own tab (v0.74): what it plays and how it sits on the harmony
local COLOURS = { { 0, "triads" }, { 1, "7ths" }, { 6, "9ths" }, { 7, "11ths" } }
local MOVES = { { "pedal", "stays on the key" }, { "follows", "moves with the chords" }, { "walks", "steps into changes" } }
local FREEDOM = { "chord notes", "passing notes", "free" }
local SC_SHAPES = { "duck", "pump", "gate" }   -- ockm-<part>-scshape 0, 1, 2
-- how far a sidechain shape has dipped, t beats after the kick (0 to 1): the same curves as the engine
local function sc_dip(shape, t)
  if shape == 0 then return math.max(0, 1 - t / 0.2) end
  if shape == 2 then return (t < 0.5) and 1 or 0 end
  if t < 0.125 then return 1 end
  return math.sqrt(math.max(0, 1 - (t - 0.125) / 0.875))
end
function ui:bass_move()
  if (self.v["ockm-bass-sync"] or 1) <= 0 then return 0 end
  return ((self.v["ockm-bass-walk"] or 0) > 0) and 2 or 1
end
function ui:set_bass_move(m)
  self:send("ockm-bass-sync", (m == 0) and 0 or 1)
  self:send("ockm-bass-walk", (m == 2) and 1 or 0)
end
-- mutate keeps a short history, so back can step through earlier variations
function ui:mutate(p)
  local key = "ockm-"..p.."-seed"
  self.seedhist = self.seedhist or {}
  local h = self.seedhist[p] or {}
  local cur = math.floor(self.v[key] or 0)
  h[#h + 1] = cur
  if #h > 16 then table.remove(h, 1) end
  self.seedhist[p] = h
  self.seedmax = self.seedmax or {}
  self.seedmax[p] = math.max(self.seedmax[p] or 0, cur) + 1
  self:send(key, self.seedmax[p])
end
function ui:mutate_back(p)
  local h = (self.seedhist or {})[p]
  if not h or #h == 0 then return end
  self:send("ockm-"..p.."-seed", table.remove(h))
end
function ui:gen_controls(add, p, ix, cy, iw, k)
  local half = (iw - 8) / 2
  if p == "chord" then
    add{ kind="text", x=ix, y=318, w=iw, h=12, label="rhythm", size=10 }
    self:stepper(add, ix, 332, iw, 44, CHORD_RHY, "ockm-chord-rhythm")
    add{ kind="text", x=ix, y=388, w=iw, h=12, label="colour: how rich the chords are", size=10 }
    local cw = (iw - 18) / 4
    for i, c in ipairs(COLOURS) do
      add{ kind="choice", x=ix + (i - 1) * (cw + 6), y=402, w=cw, h=38, label=c[2], small=true,
           sel=(math.floor(self.v["ockm-chord-type"] or 0) == c[1]), tap=function() self:send("ockm-chord-type", c[1]) end }
    end
    add{ kind="choice", x=ix, y=450, w=iw, h=34, label="smooth voicing", accent=true, small=true, sel=(self.v["ockm-chord-smooth"] or 1) > 0,
         tap=function() self:send("ockm-chord-smooth", ((self.v["ockm-chord-smooth"] or 1) > 0) and 0 or 1) end }
    add{ kind="hbar", x=ix, y=494, w=iw, h=30, hook="ockm-chord-sidechain", lo=0, hi=1, label="sidechain from the kick", bold=true }
    if self:part_empty("chord") then
      add{ kind="btn", x=ix, y=532, w=iw, h=34, accent=true, label=START.chord, tap=function() self:start_part("chord") end }
    end
    add{ kind="text", x=ix, y=548, w=iw, h=12, size=11,
         label="the progression, key and scale are on the builder" }
    return
  end
  local notes = {}
  for i, nm in ipairs(MONO_NOTES) do notes[i] = { nm } end
  add{ kind="text", x=ix, y=318, w=half, h=12, label=(p == "bass") and "riff: which notes, in each chord" or "tune: the shape of the line", size=10 }
  self:stepper(add, ix, 332, half, 44, notes, "ockm-"..p.."-notes")
  add{ kind="text", x=ix + half + 8, y=318, w=half, h=12, label="rhythm", size=10 }
  self:stepper(add, ix + half + 8, 332, half, 44, rhythms_for(p), "ockm-"..p.."-rhythm", function(v)
    -- the octave jump is a rhythm and a note pattern together: it brings the octaves notes with it
    if p == "bass" and (BASS_RHYTHMS[v + 1] or {})[1] == "octave jump" then self:send("ockm-bass-notes", 1) end
  end)
  local w3 = (iw - 12) / 3
  if p == "bass" then
    add{ kind="text", x=ix, y=386, w=iw, h=12, label="movement: how the riff follows the chords", size=10 }
    local m = self:bass_move()
    for i, mv in ipairs(MOVES) do
      add{ kind="choice", x=ix + (i - 1) * (w3 + 6), y=400, w=w3, h=38, label=mv[1], small=true, sel=(m == i - 1), tap=function() self:set_bass_move(i - 1) end }
    end
  else
    add{ kind="text", x=ix, y=386, w=iw, h=12, label="freedom: how loosely it hugs the chords", size=10 }
    local fr = math.floor((self.v["ockm-lead-freedom"] or 1) + 0.5)
    for i, nm in ipairs(FREEDOM) do
      add{ kind="choice", x=ix + (i - 1) * (w3 + 6), y=400, w=w3, h=38, label=nm, small=true, sel=(fr == i - 1), tap=function() self:send("ockm-lead-freedom", i - 1) end }
    end
  end
  -- sidechain: how far it dips each time the kick hits (the Perform pump does all the synths at once)
  if p == "bass" then
    -- v0.79 (bass first, to try it): how far it dips, and how: duck, pump or gate, with a picture of one beat
    local shk = "ockm-"..p.."-scshape"
    local shp = math.floor((self.v[shk] or 1) + 0.5)
    local bw, cw = math.floor(iw * 0.38), math.floor(iw * 0.13)
    add{ kind="hbar", x=ix, y=446, w=bw, h=30, hook="ockm-"..p.."-sidechain", lo=0, hi=1, label="sidechain", bold=true }
    for i, nm in ipairs(SC_SHAPES) do
      add{ kind="choice", x=ix + bw + 6 + (i - 1) * (cw + 4), y=446, w=cw, h=30, label=nm, small=true, sel=(shp == i - 1),
           tap=function() self:send(shk, i - 1) end }
    end
    local px = ix + bw + 6 + 3 * (cw + 4) + 2
    add{ kind="scpic", x=px, y=446, w=ix + iw - px, h=30, shape=shp, amt=self.v["ockm-"..p.."-sidechain"] or 0 }
  else
    add{ kind="hbar", x=ix, y=446, w=iw, h=30, hook="ockm-"..p.."-sidechain", lo=0, hi=1, label="sidechain from the kick", bold=true }
  end
  add{ kind="hbar", x=ix, y=482, w=iw, h=30, hook="ockm-"..p.."-density", lo=0, hi=2, label="density", bold=true }
  local skey = "ockm-"..p.."-seed"
  local seed = math.floor(self.v[skey] or 0)
  if self:part_empty(p) then
    add{ kind="btn", x=ix, y=520, w=iw, h=34, accent=true, label=START[p], tap=function() self:start_part(p) end }
  else
    local h = (self.seedhist or {})[p]
    local mw = (iw - 18) / 4
    add{ kind="btn", x=ix, y=520, w=mw, h=34, label="mutate", tap=function() self:mutate(p) end }
    add{ kind="btn", x=ix + (mw + 6), y=520, w=mw, h=34, label="back", quiet=not (h and #h > 0), tap=function() self:mutate_back(p) end }
    add{ kind="btn", x=ix + 2 * (mw + 6), y=520, w=mw, h=34, label="original", quiet=(seed == 0), tap=function()
      self.seedhist = self.seedhist or {}; self.seedhist[p] = {}; self:send(skey, 0) end }
    add{ kind="btn", x=ix + 3 * (mw + 6), y=520, w=mw, h=34, small=true, label="make it for me", quiet=not self:part_yours(p), tap=function()
      self:send("ockm-"..p.."-mode", 0); psend("ockm-"..p.."-gen", "bang", {}); self.claim_harm = self.claim_harm or {}; self.claim_harm[p] = nil end }
  end
  add{ kind="text", x=ix, y=564, w=iw, h=14, size=11,
       label=(self:part_yours(p) and "yours: you've edited it, so nothing rewrites it" or "made for you: it follows the harmony")
         .. ((seed > 0) and ("  ·  variation " .. seed) or "") }
end

-- the harmony as a signature, so a part that's yours can tell when the chords have changed under it
function ui:harm_sig()
  return string.format("%d/%d/%d", math.floor(self.v["ockm-chord-prog"] or 0), math.floor(self.v["ockm-root"] or 9), math.floor(self.v["ockm-scale"] or 0))
end
-- the chord tones (pitch classes) under step i, from the chord part's roots and the chord colour
function ui:chord_pcs(i)
  local cl = self:plen("chord")
  local d = math.floor(self:get("ockm-pat-chord-deg", i % cl))
  local sc, root = self:scale(), math.floor(self.v["ockm-root"] or 9)
  local pcs = {}
  for _, o in ipairs(CHORD_TYPES[(math.floor(self.v["ockm-chord-type"] or 0)) + 1] or { 0, 2, 4 }) do
    if o >= 0 then local dd = d + o; pcs[(root + sc[(dd % 7) + 1]) % 12] = true end
  end
  return pcs
end
-- notes of your line that no longer sit on the chords (the bass: every note; the lead: notes on the beat)
function ui:clashes(p)
  local L, out = self:plen(p), {}
  for i = 0, L - 1 do
    if self:get("ockm-pat-"..p.."-on", i) > 0 and (p == "bass" or i % 4 == 0) then
      local pc = math.floor(self:get("ockm-pat-"..p.."-note", i)) % 12
      if not self:chord_pcs(i)[pc] then out[#out + 1] = i end
    end
  end
  return out
end
function ui:harmony_moved(p)
  self.claim_harm = self.claim_harm or {}
  if not self:part_yours(p) then return false end
  if not self.claim_harm[p] then self.claim_harm[p] = self:harm_sig(); return false end
  return self.claim_harm[p] ~= self:harm_sig()
end
-- refit: move each clashing note to the nearest chord tone, keeping your rhythm, accents and slides
function ui:refit(p)
  for _, i in ipairs(self:clashes(p)) do
    local n = math.floor(self:get("ockm-pat-"..p.."-note", i))
    local pcs = self:chord_pcs(i)
    local best
    for dlt = 1, 6 do
      if pcs[(n - dlt) % 12] then best = n - dlt; break end
      if pcs[(n + dlt) % 12] then best = n + dlt; break end
    end
    if best then
      psend("ockm-"..p.."-edit", "list", { i, best, self:get("ockm-pat-"..p.."-on", i), self:get("ockm-pat-"..p.."-acc", i), self:get("ockm-pat-"..p.."-slide", i) })
    end
  end
  self.claim_harm[p] = self:harm_sig()
  self:dirty()
end

-- is a synth part empty across the whole pattern?
function ui:part_empty(p)
  local L = self:plen(p)
  for i = 0, L - 1 do
    if self:get("ockm-pat-"..p.."-on", i) > 0 then return false end
  end
  return true
end
-- start a part: hand it to its generator (auto) and make notes now
function ui:start_part(p)
  self:send("ockm-"..p.."-mode", 0)
  psend("ockm-"..p.."-gen", "bang", {})
  self:say(p .. " started: made for you, following the harmony")
end

-- the slots of the drum kit by what they play: kick, snare (snare and clap), hat, ohat, perc, tom
local KIND_OF = { [0] = "kick", [1] = "snare", [2] = "snare", [3] = "perc", [4] = "hat", [5] = "ohat", [6] = "tom", [7] = "perc" }
function ui:drum_slots(kinds)
  local out = {}
  for i, nm in ipairs(SLOTS) do
    if kinds[KIND_OF[math.floor(self.v["ockm-"..nm.."-sound"] or 0)]] then out[#out + 1] = nm end
  end
  return out
end
-- run the whole job as a short queue, so generators settle before the next pattern opens
function ui:job_step()
  local f = table.remove(self.jobs or {}, 1)
  if f then f() end
  if self.jobs and #self.jobs > 0 then self.jobclock:delay(80) else self.jobs = nil; self:dirty() end
end
-- ------------------------------------------------------------------ arrange
-- One loop, many arrangements: a row of 16-bar units with a transition at each joint. Being built in steps
-- (see the design doc); for now the tab says what's coming.
function ui:layout_arrange(add)
  add{ kind="text", x=40, y=150, w=W - 80, h=24, label="Arrange is being rebuilt", size=22, col="txt" }
  add{ kind="text", x=40, y=192, w=W - 80, h=14, size=13,
       label="Soon: your loop becomes a track here, as a row of 16-bar units with a transition at every joint." }
  add{ kind="text", x=40, y=214, w=W - 80, h=14, size=13,
       label="Generate one, or build it by hand. Your loop is never changed." }
end

-- ------------------------------------------------------------------ export
-- Audio (a stereo mix and/or stems: drums, bass, lead, chords, effects) is recorded as it plays, in real time.
-- MIDI is written straight away from the patterns. Files go to the exports folder, or a USB stick when one is in.
local STEM_NAMES = { "drums", "bass", "lead", "chord", "fx" }
local GM_DRUM = { [0] = 36, [1] = 38, [2] = 39, [3] = 37, [4] = 42, [5] = 46, [6] = 45, [7] = 56 }   -- by sound
local USB_SKIP = { ["Macintosh HD"] = 1, ["Recovery"] = 1, ["Data"] = 1, ["Preboot"] = 1, ["VM"] = 1, ["Update"] = 1 }

function ui:exp_opts()
  if not self.exp then self.exp = { times = 2, mix = 1, stems = 0, midi = 0, dest = 1 } end
  return self.exp
end
function ui:exp_dir()
  local e = self:exp_opts()
  if e.dest == 2 and self.usb and self.usb[1] then
    local d = self.usb[1] .. "/OCKM_EXPORTS"
    psend("ockm-mkdir", "symbol", { d })
    return d, "your USB stick (" .. self.usb[1]:match("[^/]+$") .. ")"
  end
  return self.exports_dir or "exports", "the exports folder"
end
function ui:exp_name(what)
  local n = (self.project or "ockm"):gsub("[^%w%-]", "-")
  return n .. "-" .. what .. "-" .. os.date("%H%M%S")
end
-- open the writers for this take and start them together
function ui:rec_open(dir, base, stems)
  psend("ockm-rec-mix-open", "symbol", { dir .. "/" .. base .. ".wav" })
  if stems then for _, st in ipairs(STEM_NAMES) do psend("ockm-rec-" .. st .. "-open", "symbol", { dir .. "/" .. base .. "-" .. st .. ".wav" }) end end
end
function ui:rec_start(stems)
  psend("ockm-rec-mix-start", "bang", {})
  if stems then for _, st in ipairs(STEM_NAMES) do psend("ockm-rec-" .. st .. "-start", "bang", {}) end end
end
function ui:tick() if self.recording or self.exporting then self:dirty(); self.tickclock:delay(500) end end

-- live recording: whatever you play, from now until you stop it
function ui:record_live()
  local e = self:exp_opts()
  local dir, where = self:exp_dir()
  local base = self:exp_name("live")
  self:rec_open(dir, base, e.stems > 0); self:rec_start(e.stems > 0)
  self.recording = { t0 = os.time(), where = where, base = base }
  self.tickclock:delay(500)
  self:say("recording to " .. where .. ". Tap the red button to stop")
end
function ui:record_stop()
  psend("ockm-rec-stop", "bang", {})
  local r = self.recording; self.recording = nil
  if r then self:say("saved " .. r.base .. ".wav to " .. r.where) end
end

-- export: MIDI first (instant for a pattern, a quick pass through the patterns for a song), then the audio as it plays
function ui:export()
  local e = self:exp_opts()
  if self.playing ~= 0 then psend("ockm-play", "float", { 0 }) end
  local dir, where = self:exp_dir()
  self.exp_where = where
  local jobs = {}
  if e.midi > 0 then
    local base = self:exp_name("loop")
    jobs[#jobs + 1] = function() self:write_midi(dir .. "/" .. base .. ".mid", { { self:collect_pattern(), e.times } }) end
  end
  if e.mix > 0 or e.stems > 0 then
    jobs[#jobs + 1] = function() self:export_audio(dir) end
  else
    jobs[#jobs + 1] = function() self:say("exported MIDI to " .. where) end
  end
  self.jobs = jobs; self.jobclock:delay(10)
end
function ui:export_audio(dir)
  local e = self:exp_opts()
  local base = self:exp_name("loop")
  self:rec_open(dir, base, e.stems > 0)
  self.exporting = { t0 = os.time(), base = base }
  self:rec_start(e.stems > 0)
  psend("ockm-play", "float", { 1 })
  local bars = e.times * math.max(1, math.floor(self:loop_len() / 16))
  self.expclock:delay(bars * 16 * 15000 / (self.v["ockm-bpm"] or 124))
  self.tickclock:delay(500)
end
-- the loop's time is up: stop, let the effects ring out, then close the files
function ui:export_end()
  local x = self.exporting
  if not x then return end
  if not x.tail then
    x.tail = true
    if self.playing ~= 0 then psend("ockm-play", "float", { 0 }) end
    self.expclock:delay(2500)
    return
  end
  psend("ockm-rec-stop", "bang", {})
  self.exporting = nil
  self:say("exported " .. x.base .. " to " .. (self.exp_where or "the exports folder"))
end
function ui:export_cancel()
  if self.exporting then
    psend("ockm-play", "float", { 0 }); psend("ockm-rec-stop", "bang", {})
    self.exporting = nil; self:say("export stopped. The part already written is in the file")
  end
end

-- everything MIDI needs from the pattern that's open
function ui:collect_pattern()
  local d = { len = self:loop_len(), root = math.floor(self.v["ockm-root"] or 9), scale = self:scale(),
              ctype = math.floor(self.v["ockm-chord-type"] or 0), smooth = (self.v["ockm-chord-smooth"] or 1) > 0,
              loop = 0, on = {}, drums = {}, mono = {}, chord = {} }
  -- every step of the loop, each part repeating inside it at its own length
  local dl, bl, ll, cl = self:plen("drum"), self:plen("bass"), self:plen("lead"), self:plen("chord")
  for _, t in ipairs(SYNTHS) do d.on[t] = (self.v["ockm-"..t.."-on"] or 1) > 0 end
  for _, nm in ipairs(SLOTS) do
    local sl = { sound = math.floor(self.v["ockm-"..nm.."-sound"] or 0), v = {}, n = {} }
    for st = 0, d.len - 1 do sl.v[st] = self:get("ockm-pat-"..nm, st % dl); sl.n[st] = self:get("ockm-pat-"..nm.."-nudge", st % dl) end
    d.drums[nm] = sl
  end
  for _, part in ipairs({ "bass", "lead" }) do
    local m, pl = {}, (part == "bass") and bl or ll
    for st = 0, d.len - 1 do
      local i = st % pl
      m[st] = { note = self:get("ockm-pat-"..part.."-note", i), on = self:get("ockm-pat-"..part.."-on", i),
                acc = self:get("ockm-pat-"..part.."-acc", i), slide = self:get("ockm-pat-"..part.."-slide", i) }
    end
    d.mono[part] = m
  end
  for st = 0, d.len - 1 do d.chord[st] = { on = self:get("ockm-pat-chord-on", st % cl), deg = self:get("ockm-pat-chord-deg", st % cl) } end
  return d
end
-- a chord's notes, worked out the way the chord sequencer does it
local function chord_notes(d, deg)
  local rox = (d.root <= 7) and (48 + d.root) or (36 + d.root)
  local ty = CHORD_TYPES[d.ctype + 1] or CHORD_TYPES[1]
  local out = {}
  for k = 1, 4 do
    if ty[k] >= 0 then
      local a = math.floor(deg) + ty[k]
      local n = rox + 12 * math.floor(a / 7) + d.scale[(a % 7) + 1]
      if d.smooth then n = n - 12 * math.floor((n - rox) / 12) end
      out[#out + 1] = n
    end
  end
  return out
end
local function vlq(n)
  local b = { n % 128 }
  n = math.floor(n / 128)
  while n > 0 do table.insert(b, 1, 128 + n % 128); n = math.floor(n / 128) end
  return string.char(table.unpack(b))
end
local function be(n, bytes) local t = {} for i = bytes - 1, 0, -1 do t[#t + 1] = math.floor(n / 256 ^ i) % 256 end return string.char(table.unpack(t)) end
local function track_chunk(name, ev)
  table.sort(ev, function(a, b) if a[1] ~= b[1] then return a[1] < b[1] end return a[3] < b[3] end)   -- note offs first at the same time
  local out, last = { "\0\255\3" .. vlq(#name) .. name }, 0
  for _, e in ipairs(ev) do out[#out + 1] = vlq(e[1] - last) .. e[2]; last = e[1] end
  out[#out + 1] = "\0\255\47\0"
  local body = table.concat(out)
  return "MTrk" .. be(#body, 4) .. body
end
-- chain: { { pattern data, repeats }, ... }. 96 ticks a beat, so a step is 24
function ui:write_midi(path, chain)
  local Q = 24
  local tr = { drums = {}, bass = {}, lead = {}, chord = {} }
  local function note(list, ch, t, n, vel, dur)
    if t < 0 then t = 0 end
    list[#list + 1] = { t, string.char(0x90 + ch, n, vel), 1 }
    list[#list + 1] = { t + dur, string.char(0x80 + ch, n, 0), 0 }
  end
  local t0 = 0
  for _, link in ipairs(chain) do
    local d, reps = link[1], link[2]
    for _ = 1, reps do
      for _, sl in pairs(d.drums) do
        for st = 0, d.len - 1 do
          local i = (d.loop > 0) and (st % d.loop) or st
          local v = sl.v[i] or 0
          if v > 0 then
            local vel = clamp(math.floor(self:drum_vel(v) * 127 + 0.5), 1, 127)
            note(tr.drums, 9, t0 + st * Q + math.floor((sl.n[i] or 0) * Q + 0.5), GM_DRUM[sl.sound] or 36, vel, 12)
          end
        end
      end
      for ch, part in ipairs({ "bass", "lead" }) do
        if d.on[part] then
          local m = d.mono[part]
          for st = 0, d.len - 1 do
            if m[st].on > 0 then
              local dur = (st + 1 < d.len and m[st + 1].on > 0 and m[st + 1].slide > 0) and (Q + 2) or (Q - 4)
              note(tr[part], ch - 1, t0 + st * Q, clamp(math.floor(m[st].note), 0, 127), (m[st].acc > 0) and 120 or 92, dur)
            end
          end
        end
      end
      if d.on.chord then
        for st = 0, d.len - 1 do
          local c = d.chord[st]
          if c.on > 0 then
            local nx = st + 1
            while nx < d.len and nx - st < 16 and d.chord[nx].on <= 0 do nx = nx + 1 end
            for _, n in ipairs(chord_notes(d, c.deg)) do note(tr.chord, 2, t0 + st * Q, clamp(n, 0, 127), (c.on > 1) and 120 or 95, (nx - st) * Q - 2) end
          end
        end
      end
      t0 = t0 + d.len * Q
    end
  end
  local tempo = math.floor(60000000 / (self.v["ockm-bpm"] or 124))
  local head = track_chunk("OCKM_GENERATOR", { { 0, "\255\81\3" .. be(tempo, 3), 0 }, { 0, "\255\88\4\4\2\24\8", 0 } })
  local body = { head, track_chunk("drums", tr.drums), track_chunk("bass", tr.bass), track_chunk("lead", tr.lead), track_chunk("chords", tr.chord) }
  local f = io.open(path, "wb")
  if not f then self:say("couldn't write " .. path); return end
  f:write("MThd" .. be(6, 4) .. be(1, 2) .. be(#body, 2) .. be(96, 2) .. table.concat(body)); f:close()
  self.last_midi = path
end

function ui:layout_export(add)
  local e = self:exp_opts()
  add{ kind="zone", x=0, y=0, w=W, h=H, tap=function() end }
  local x, y, w, h = 24, 56, W - 48, H - 72
  add{ kind="sheet", x=x, y=y, w=w, h=h }
  add{ kind="text", x=x + 20, y=y + 16, w=w - 40, h=20, label="Export", size=18, col="txt" }
  add{ kind="text", x=x + 20, y=y + 42, w=w - 40, h=12, size=11,
       label="Audio is recorded as it plays (you'll hear it). MIDI is written straight away." }
  local lx, cx = x + 20, x + 150
  local function row(yy, label, list, cur, fn, wd)
    add{ kind="text", x=lx, y=yy + 10, w=120, h=12, label=label, size=11 }
    for i, it in ipairs(list) do
      add{ kind="choice", x=cx + (i - 1) * ((wd or 150) + 6), y=yy, w=wd or 150, h=32, small=true, label=it, sel=(cur == i), tap=function() fn(i) end }
    end
  end
  -- the loop, played a number of times (exporting an arrangement comes with arrangements)
  local times = { 1, 2, 4, 8 }
  local labs = {}; for i, t in ipairs(times) do labs[i] = (t == 1) and "once" or (t .. " times") end
  local cur = 1; for i, t in ipairs(times) do if t == e.times then cur = i end end
  row(y + 90, "the loop plays", labs, cur, function(i) e.times = times[i] end, 100)
  add{ kind="text", x=lx, y=y + 160, w=120, h=12, label="files", size=11 }
  for i, f in ipairs({ { "mix", "stereo mix (WAV)" }, { "stems", "stems (5 WAVs)" }, { "midi", "MIDI (.mid)" } }) do
    local on = (e[f[1]] or 0) > 0
    add{ kind="choice", x=cx + (i - 1) * 226, y=y + 150, w=220, h=32, small=true, accent=true, label=f[2], sel=on, tap=function() e[f[1]] = on and 0 or 1 end }
  end
  local usb = self.usb and self.usb[1]
  if e.dest == 2 and not usb then e.dest = 1 end
  row(y + 200, "save to", { "exports folder", usb and ("USB: " .. usb:match("[^/]+$")) or "USB (none found)" }, e.dest,
      function(i) if i == 2 and not usb then psend("ockm-usb-scan", "bang", {}); return end e.dest = i end, 220)
  add{ kind="text", x=lx, y=y + 250, w=w - 40, h=12, size=11,
       label="Stems: drums, bass, lead, chords and effects, each on its own (before the master filter and drive)." }
  add{ kind="text", x=lx, y=y + 270, w=w - 40, h=12, size=11,
       label="The MIDI file has a track each for drums (GM drum notes, channel 10), bass, lead and chords." }
  local any = (e.mix + e.stems + e.midi) > 0
  local by = y + h - 64
  add{ kind="btn", x=lx, y=by, w=220, h=48, label="record what I play", tap=function()
         self.sheet = nil; self:record_live() end }
  add{ kind="btn", x=x + w - 20 - 160, y=by, w=160, h=48, label="cancel", quiet=true, tap=function() self.sheet = nil end }
  add{ kind="btn", x=x + w - 20 - 160 - 12 - 200, y=by, w=200, h=48, accent=any, disabled=not any, label="export",
       tap=function() if any then self.sheet = nil; self:export() end end }
end

-- ------------------------------------------------------------------ setup (tap the tempo)

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
  add{ kind="text", x=16, y=130, w=W - 32, h=14, label=self.msg or "the loop, plus the drum kit, tempo and effects", size=11, col=self.msg and "acc" or nil }
  local bw = (W - 32 - 4 * 8) / 5
  local acts = {
    { "save", function() psend("ockm-save", "bang", {}); self:say("saved " .. ockm_pretty(cur) .. ": the loop and the kit") end },
    { "back to last save", function() psend("ockm-revert", "bang", {}); self:say("back to the last save of " .. ockm_pretty(cur)) end },
    { "save as a copy", function()
        local n = self:new_name(); psend("ockm-project-saveas", "symbol", { n }); psend("ockm-project-list", "bang", {})
        self:say("saved a copy as " .. ockm_pretty(n) .. ". You're now working in the copy") end },
    { "new blank project", function()
        local n = self:new_name(); self.exists = 1; self.new_pending = true; psend("ockm-project-new", "symbol", { n }); psend("ockm-project-list", "bang", {})
        self.pick = nil; self:say("new project: " .. ockm_pretty(n) .. ". The last one stays as you last saved it") end },
    { "export...", function() psend("ockm-usb-scan", "bang", {}); psend("ockm-exports-ask", "bang", {}); self.sheet = "export" end },
  }
  for i, a in ipairs(acts) do
    add{ kind="btn", x=16 + (i - 1) * (bw + 8), y=152, w=bw, h=52, label=a[1], accent=(i == 4 or i == 5), tap=a[2] }
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
      add{ kind="choice", x=cx, y=top + 100, w=cw, h=32, small=true, label="EQ", sel=not self:eq_flat(t), accent=true,
           tap=function() self:eq_open(i) end }
      add{ kind="vfader", x=cx, y=top + 140, w=cw, h=210, hook="ockm-"..t.."-level", lo=0, hi=1 }
      add{ kind="ms", x=cx, y=top + 364, w=cw, h=50, label="M", hook="ockm-"..t.."-mute" }
      add{ kind="ms", x=cx, y=top + 420, w=cw, h=50, label="S", hook="ockm-"..t.."-solo" }
    else
      add{ kind="strip", x=x, y=top, w=sw - 2, h=H - top - 8, label="master", master=true }
      add{ kind="hbar", x=cx, y=top + 34, w=cw, h=26, hook="ockm-verb-mix", lo=0, hi=1, label="rev" }
      add{ kind="hbar", x=cx, y=top + 66, w=cw, h=26, hook="ockm-delay-mix", lo=0, hi=1, label="dly" }
      add{ kind="btn", x=cx, y=top + 100, w=cw, h=32, small=true, label="de-mud", tap=function() self:demud() end }
      add{ kind="vfader", x=cx, y=top + 140, w=cw, h=210, hook="ockm-volume", lo=0, hi=1, master=true }
      add{ kind="btn", x=cx, y=top + 364, w=cw, h=106, label="clear", quiet=true, tap=function()
        for _, t in ipairs(TRACKS) do
          if (self.v["ockm-"..t.."-mute"] or 0) > 0 then self:send("ockm-"..t.."-mute", 0) end
          if (self.v["ockm-"..t.."-solo"] or 0) > 0 then self:send("ockm-"..t.."-solo", 0) end
        end
      end }
    end
  end
end

-- ------------------------------------------------------------------ track EQ
-- low cut, then a low shelf at 100 Hz, a mid bell and a high shelf at 8 kHz (each -12 to +12 dB). Same maths as the engine
local EQ_DEF = { lowcut = 20, eqlow = 0, eqmid = 0, eqmidf = 400, eqhigh = 0 }
local EQ_SLIDERS = { { "lowcut", 20, 800, "low cut", true }, { "eqlow", -12, 12, "low" }, { "eqmid", -12, 12, "mid" },
                     { "eqmidf", 150, 6000, "mid freq", true }, { "eqhigh", -12, 12, "high" } }
function ui:eq_flat(t)
  for k, d in pairs(EQ_DEF) do if math.abs((self.v["ockm-"..t.."-"..k] or d) - d) > 0.01 then return false end end
  return true
end
local function biquad_db(kind, db, f0, f, sr)
  local A = 10 ^ (db / 40)
  local w0 = 2 * math.pi * f0 / sr
  local c, sn = math.cos(w0), math.sin(w0)
  local b0, b1, b2, a0, a1, a2
  if kind == "peak" then
    local al = sn / 2
    b0, b1, b2, a0, a1, a2 = 1 + al * A, -2 * c, 1 - al * A, 1 + al / A, -2 * c, 1 - al / A
  else
    local r = 2 * math.sqrt(A) * sn * 0.70711
    if kind == "low" then
      b0, b1, b2 = A * ((A + 1) - (A - 1) * c + r), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - r)
      a0, a1, a2 = (A + 1) + (A - 1) * c + r, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - r
    else
      b0, b1, b2 = A * ((A + 1) + (A - 1) * c + r), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - r)
      a0, a1, a2 = (A + 1) - (A - 1) * c + r, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - r
    end
  end
  local w = 2 * math.pi * f / sr
  local cw, sw, c2, s2 = math.cos(w), math.sin(w), math.cos(2 * w), math.sin(2 * w)
  local nr, ni = b0 + b1 * cw + b2 * c2, -(b1 * sw + b2 * s2)
  local dr, di = a0 + a1 * cw + a2 * c2, -(a1 * sw + a2 * s2)
  return 10 * math.log((nr * nr + ni * ni) / (dr * dr + di * di), 10)
end
function ui:eq_response(t, f)
  local function g(k) return self.v["ockm-"..t.."-"..k] or EQ_DEF[k] end
  local sr = 48000
  local lc = g("lowcut")
  local x = (f / lc) ^ 2
  local db = 2 * 10 * math.log(x / (1 + x), 10)       -- two one-pole high-passes
  db = db + biquad_db("low", g("eqlow"), 100, f, sr) + biquad_db("peak", g("eqmid"), g("eqmidf"), f, sr) + biquad_db("high", g("eqhigh"), 8000, f, sr)
  return db
end
-- one tap to clear the low-mid fog: low cuts on everything except the kick and bass, a scoop on the chords
local DEMUD = { kick = { 30 }, snare = { 120, -2, 400 }, perc = { 200 }, hat = { 300 }, ohat = { 250 }, tom = { 60 },
                bass = { 30 }, lead = { 180 }, chord = { 160, -3, 300 } }
local SPEC_F = { 60, 120, 250, 500, 1000, 2000, 4000, 8000 }
function ui:demud()
  if self.playing ~= 0 then
    self.listening = {}
    psend("ockm-spec-all", "float", { 1 })
    self.demudclock:delay(4000)
    self:say("de-mud is listening to the mix for 4 seconds...")
    return
  end
  self:demud_fixed()
end
-- after listening: each track's low cut goes an octave below where its own energy starts, and if the mix piles up
-- at 250-500 Hz, the chords, lead and snare get a scoop there
function ui:demud_finish()
  psend("ockm-spec-all", "float", { 0 })
  self:snapshot("de-mud")
  local L = self.listening or {}
  self.listening = nil
  if self.sheet == "eq" and self.eq_track then psend("ockm-spec-" .. TRACKS[self.eq_track], "float", { 1 }) end
  local avg, mix, changed = {}, {}, {}
  for i, t in ipairs(TRACKS) do
    local acc = L[t]
    if acc then
      avg[t] = {}
      for b = 0, 7 do
        local p = (acc[b] or 0) / math.max(1, acc["n" .. b] or 1)
        avg[t][b] = (p > 0) and 10 * math.log(p, 10) or 0
        mix[b] = (mix[b] or 0) + p
      end
    end
  end
  local mud = false
  if mix[2] and mix[1] and mix[4] and mix[5] then
    mud = (mix[2] + mix[3]) / 2 > 2 * (mix[1] + mix[4] + mix[5]) / 3
  end
  for i, t in ipairs(TRACKS) do
    local kind = (i <= 8) and KIND_OF[math.floor(self.v["ockm-"..t.."-sound"] or 0)] or t
    local a = avg[t]
    if a and kind ~= "kick" and kind ~= "bass" then
      local peak = 0
      for b = 0, 7 do peak = math.max(peak, a[b]) end
      if peak > 25 then
        local from = 7
        for b = 7, 0, -1 do if a[b] >= peak - 15 then from = b end end
        local lc = clamp(math.floor(SPEC_F[from + 1] / 2 / 10 + 0.5) * 10, 30, 400)
        self:send("ockm-"..t.."-lowcut", lc); changed[#changed + 1] = self:track_name(i) .. " " .. lc
        if mud and (kind == "chord" or kind == "lead" or kind == "snare") and math.max(a[2], a[3]) >= peak - 6 then
          self:send("ockm-"..t.."-eqmid", -3); self:send("ockm-"..t.."-eqmidf", 320)
          changed[#changed] = changed[#changed] .. " and a scoop"
        end
      end
    end
  end
  if #changed == 0 then self:say("de-mud heard nothing to fix: play a busier part and try again")
  else self:say_undo("de-mud: " .. table.concat(changed, ", ") .. " Hz") end
end
function ui:demud_fixed()
  self:snapshot("de-mud")
  for i, t in ipairs(TRACKS) do
    local kind
    if i <= 8 then kind = KIND_OF[math.floor(self.v["ockm-"..t.."-sound"] or 0)] else kind = t end
    local d = DEMUD[kind]
    if d then
      self:send("ockm-"..t.."-lowcut", d[1])
      if d[2] then self:send("ockm-"..t.."-eqmid", d[2]); self:send("ockm-"..t.."-eqmidf", d[3]) end
    end
  end
  self:say_undo("de-mud: starting low cuts on all but the kick and bass. Play first and it listens instead")
end
function ui:eq_open(i)
  if self.eq_track and self.sheet == "eq" then psend("ockm-spec-" .. TRACKS[self.eq_track], "float", { 0 }) end
  self.eq_track = i; self.sheet = "eq"
  psend("ockm-spec-" .. TRACKS[i], "float", { 1 })
end
function ui:eq_close()
  if self.eq_track then psend("ockm-spec-" .. TRACKS[self.eq_track], "float", { 0 }) end
  self.sheet = nil
end
function ui:layout_eq(add)
  local i = clamp(self.eq_track or 1, 1, #TRACKS)
  local t = TRACKS[i]
  add{ kind="zone", x=0, y=0, w=W, h=H, tap=function() end }
  local x, y, w, h = 110, 64, W - 220, H - 80
  add{ kind="sheet", x=x, y=y, w=w, h=h }
  add{ kind="arrow", x=x + 16, y=y + 12, w=44, h=36, dir=-1, on=(i > 1), tap=function() if i > 1 then self:eq_open(i - 1) end end }
  add{ kind="text", x=x + 70, y=y + 20, w=300, h=20, label="EQ: " .. self:track_name(i), size=18, col="txt" }
  add{ kind="arrow", x=x + w - 60, y=y + 12, w=44, h=36, dir=1, on=(i < #TRACKS), tap=function() if i < #TRACKS then self:eq_open(i + 1) end end }
  add{ kind="eqcurve", x=x + 20, y=y + 60, w=w - 40, h=130, track=t }
  for j, sl in ipairs(EQ_SLIDERS) do
    add{ kind="slider", x=x + 20, y=y + 204 + (j - 1) * 40, w=w - 40, h=32, hook="ockm-"..t.."-"..sl[1], lo=sl[2], hi=sl[3], label=sl[4], log=sl[5] }
  end
  add{ kind="btn", x=x + 20, y=y + h - 60, w=140, h=44, label="flat", quiet=true, tap=function()
    for k, d in pairs(EQ_DEF) do self:send("ockm-"..t.."-"..k, d) end
  end }
  add{ kind="btn", x=x + w - 20 - 160, y=y + h - 60, w=160, h=44, label="done", accent=true, tap=function() self:eq_close() end }
  if self.playing == 0 then
    add{ kind="text", x=x + 180, y=y + h - 46, w=300, h=12, size=11, label="press play to see this track's spectrum" }
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
function ui:drum_tap(i) self:drum_cycle(self.slot, self:dabs(i)) end
-- with a drums loop on, every bar shows (and edits) the loop
function ui:dabs(i) return (self.page * 16 + i) % self:plen("drum") end
-- how hard a step plays, 0 to 1: 2 = accent (full), 1 = normal (full minus the accent amount), between = drawn
function ui:drum_vel(v)
  if v >= 2 then return 1 elseif v > 0.999 then return 1 - (self.v["ockm-accent"] or 0.3) end
  return math.max(v, 0)
end
-- drag in the lane: velocity or timing for the step under the finger (only steps that play)
function ui:lane_set(w, x, y)
  local pitch = (W - 32) / 16
  local i = clamp(math.floor((x - 16) / pitch), 0, 15)
  local nm, step = SLOTS[self.slot], self:dabs(i)
  if self:get("ockm-pat-"..nm, step) <= 0 then return end
  local f = clamp(1 - (y - w.y) / w.h, 0, 1)
  if (self.lane or "vel") == "vel" then
    local v = (f >= 0.9) and 2 or math.min(0.99, math.max(0.05, math.floor(f * 100 + 0.5) / 100))   -- the top tenth snaps to accent
    psend("ockm-edit", nm, { step, v })
  else
    local n = (f - 0.5) * 0.5
    if math.abs(n) < 0.02 then n = 0 end
    psend("ockm-nudge", nm, { step, math.floor(n * 1000 + 0.5) / 1000 })
  end
  self:dirty()
end

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
    if not w.off and inside(w, x, y) and (w.tap or w.swipe or w.kind == "slider" or w.kind == "bpm" or w.kind == "vfader" or w.kind == "hbar" or w.kind == "ms"
       or w.kind == "dstep" or w.kind == "mstep" or w.kind == "cstep" or w.kind == "pad" or w.kind == "vlane" or w.kind == "hold") then return w end
  end
  return nil
end

function ui:press(x, y)
  local w = self:hit(x, y)
  self.touch = { w = w, x0 = x, y0 = y, mode = nil }
  if not w then return end
  if w.kind == "pad" then self.touch.mode = "pad"; self.pad_on = w.hook; psend(w.hook, "float", { 1 })
  elseif w.kind == "hold" then self.touch.mode = "hold"; w.down()
  elseif w.kind == "slider" or w.kind == "vfader" or w.kind == "hbar" then self.touch.mode = "slider"; self:slide(w, x, y)
  elseif w.kind == "bpm" then self.touch.v0 = self.v["ockm-bpm"] or 124
  elseif w.kind == "vlane" then self.touch.mode = "vlane"; self:lane_set(w, x, y)
  elseif w.kind == "dstep" or w.kind == "pcell" or w.kind == "ms" then
    -- drum steps, mute and solo act the moment a finger lands, like the pads on a drum machine
    if w.kind == "ms" then
      self:send(w.hook, ((self.v[w.hook] or 0) > 0) and 0 or 1)
    else
      local slot, step = w.slot, w.step
      if w.kind == "dstep" then slot, step = self.slot, self:dabs(w.i) end
      local nm = SLOTS[slot]
      self.touch.undo = { nm, step, self:get("ockm-pat-"..nm, step) }   -- in case this turns into a swipe
      self:drum_cycle(slot, step)
    end
    self.touch.mode = "pressed"
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
  if w.log then v = math.floor(w.lo * (w.hi / w.lo) ^ f + 0.5) end
  if w.hi - w.lo > 4 then v = math.floor(v + 0.5) else v = math.floor(v * 100 + 0.5) / 100 end
  if w.edit then self.v[w.hook] = v; w.edit(v); return end
  local changed = (self.v[w.hook] ~= v)
  self:send(w.hook, v)
  if w.preview and changed then self:preview(w.preview) end
end

function ui:move(x, y)
  local t = self.touch
  if not t or not t.w then return end
  local dx, dy = x - t.x0, y - t.y0
  if t.mode == "slider" then self:slide(t.w, x, y); return end
  if t.mode == "vlane" then self:lane_set(t.w, x, y); return end
  if t.mode == nil and t.w.kind == "bpm" and math.abs(dy) > 8 then t.mode = "bpm" end
  if t.mode == "bpm" then
    self:send("ockm-bpm", clamp(math.floor(t.v0 - dy / 3 + 0.5), 40, 200)); return
  end
  -- a step that was pressed, then swiped sideways: put the step back and turn the page instead
  if t.mode == "pressed" and t.w.swipe and math.abs(dx) > 24 and math.abs(dx) > math.abs(dy) then
    if t.undo then psend("ockm-edit", t.undo[1], { t.undo[2], t.undo[3] }) end
    t.mode = "swipe"
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
  elseif t.mode == "hold" then w.up()
  elseif t.mode == "slider" and w.spring then
    self:filter_spring()     -- let go: snap back to off
  elseif t.mode == "slider" and w.preview then
    self:preview(w.preview, true)
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

-- redraw on a press only when the press itself changed something (most buttons act when the finger lifts)
function ui:mouse_down(x, y) self:press(x / self.s, y / self.s); if self.touch and self.touch.mode then self:repaint() end end
function ui:mouse_drag(x, y) self:move(x / self.s, y / self.s); self:repaint() end
function ui:mouse_up(x, y) self:release(x / self.s, y / self.s); self:repaint() end

-- headless test hook: same code paths as the mouse
function ui:test(sel, a)
  if sel == "tap" then self:press(a[1], a[2]); self:release(a[1], a[2])
  elseif sel == "drag" then
    self:press(a[1], a[2])
    for k = 1, 8 do self:move(a[1] + (a[3] - a[1]) * k / 8, a[2] + (a[4] - a[2]) * k / 8) end
    self:release(a[3], a[4])
  elseif sel == "press" then self:press(a[1], a[2])
  elseif sel == "release" then self:release(a[1], a[2])
  elseif sel == "screen" then self.screen = a[1]
  elseif sel == "dump" then
    local L = self:layout()
    pd.post(string.format("ockm-ui: screen %s page %d widgets %d", self.screen, self.page, #L))
    for _, w in ipairs(L) do if w.kind == "preset" and w.inline then pd.post("ockm-ui: box " .. tostring(w.num) .. " " .. tostring(w.label)) end end
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
  local i = self.step % 16      -- every part's length is whole bars, so the step within the bar is the same for all
  local pitch = (W - 32) / 16
  if self.screen == "perform" then
    local lw = (W - LANE_X - 16) / 16
    self:col(g, "acc"); g:fill_rect(LANE_X + i * lw + 2, LANE_Y - 6, lw - 4, 3)
    for n, p in ipairs(SYNTHS) do
      if self:part_sounding(p) then
        local x = part_x(n)
        g:fill_rounded_rect(x + 10, PART_Y + PART_H / 2 - 5, 10, 10, 5)
      end
    end
  elseif self.screen == "live" then
    self:col(g, "acc")
    for n = 1, 11 do
      if self:track_sounding(n) then local x, y = live_tile(n); g:fill_rounded_rect(x + 10, y + 14, 10, 10, 5) end
    end
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
    if w.h < 50 then
      self:ctext(g, w.label, w, 13, on and "#ffffff" or "txt")
    else
      self:ctext(g, w.label, { x=w.x, y=w.y + 8, w=w.w, h=20 }, 14, on and "#ffffff" or "txt")
      self:ctext(g, w.sub or "", { x=w.x, y=w.y + 32, w=w.w, h=16 }, 10, on and "#ffffff" or "mute")
    end
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
    local lit = w.accent or (w.flash and self.flashing == w.flash and not w.off)
    self:col(g, lit and "acc" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    if w.edge and not lit then self:col(g, "acc"); g:stroke_rounded_rect(w.x + 1, w.y + 1, w.w - 2, w.h - 2, 6, 2) end
    self:ctext(g, w.label, w, w.small and 12 or 14, lit and "#ffffff" or ((w.quiet or w.off) and "mute" or "txt"))
  elseif k == "tab" then
    self:col(g, w.sel and "on" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, w, 12, w.sel and "bg" or "txt")
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
    if playing or w.used == nil or w.used then self:col(g, playing and "on" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    else self:col(g, "off"); g:stroke_rounded_rect(w.x + 1, w.y + 1, w.w - 2, w.h - 2, 6, 1.5) end
    if self.want == w.n then self:col(g, "acc"); g:stroke_rounded_rect(w.x + 1, w.y + 1, w.w - 2, w.h - 2, 6, 2) end
    self:ctext(g, string.format("%d", math.floor(w.n + 1)), w, (w.h > 44) and 22 or 13, playing and "bg" or ((w.used == false) and "mute" or "txt"))
  elseif k == "choice" then
    local sel = w.sel
    self:col(g, sel and (w.accent and "acc" or "on") or (w.onbar and "dim" or "off")); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, w, w.small and 11 or 13, sel and (w.accent and "#ffffff" or "bg") or (w.disabled and "mute" or "txt"))
  elseif k == "recipe" then
    self:col(g, w.sel and "on" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 8)
    self:text(g, w.label, w.x + 12, w.y + w.h / 2 - 17, 14, w.sel and "bg" or "txt", w.w - 70)
    self:text(g, w.sub or "", w.x + 12, w.y + w.h / 2 + 3, 9, w.sel and "dim" or "mute", w.w - 20)
    if w.slot then
      self:col(g, "acc"); g:fill_rounded_rect(w.x + w.w - 56, w.y + 8, 48, 20, 4)
      self:ctext(g, "slot " .. w.slot, { x=w.x + w.w - 56, y=w.y + 8, w=48, h=20 }, 10, "#ffffff")
    end
  elseif k == "disc" then
    -- save: a floppy disc, orange when there's something unsaved
    local on = self.unsaved
    if w.lit ~= nil then on = w.lit end
    self:col(g, on and "acc" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    local c = on and "#ffffff" or (w.off and "mute" or "txt")
    local cx, cy = w.x + w.w / 2, w.y + w.h / 2
    self:col(g, c); g:stroke_rounded_rect(cx - 11, cy - 11, 22, 22, 3, 2)
    g:fill_rect(cx - 6, cy - 11, 12, 7)
    self:col(g, on and "acc" or "off"); g:fill_rect(cx - 2, cy - 10, 4, 5)
    self:col(g, c); g:fill_rect(cx - 7, cy + 3, 14, 6)
  elseif k == "bin" then
    -- delete one of your saved sounds: a small bin
    self:col(g, w.lit and "acc" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    local cx, cy = w.x + w.w / 2, w.y + w.h / 2
    self:col(g, w.lit and "#ffffff" or "txt")
    g:fill_rect(cx - 9, cy - 8, 18, 2); g:fill_rect(cx - 3, cy - 11, 6, 3)
    g:stroke_rounded_rect(cx - 7, cy - 5, 14, 16, 2, 2)
    g:fill_rect(cx - 2, cy - 2, 1, 10); g:fill_rect(cx + 1, cy - 2, 1, 10)
  elseif k == "menubtn" then
    self:col(g, w.sel and "on" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:col(g, w.sel and "bg" or "txt")
    for j = -1, 1 do g:fill_rect(w.x + w.w / 2 - 11, w.y + w.h / 2 + j * 7 - 1, 22, 3) end
  elseif k == "scrim" then
    -- nothing to draw: it only catches taps outside the menu
  elseif k == "menupanel" then
    self:col(g, "bg"); g:fill_rounded_rect(w.x - 3, w.y - 3, w.w + 6, w.h + 6, 12)
    self:col(g, "card"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 10)
    self:col(g, "dim"); g:stroke_rounded_rect(w.x, w.y, w.w, w.h, 10, 1)
  elseif k == "menuitem" then
    self:col(g, "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    if w.sub ~= "" then
      self:text(g, w.label, w.x + 12, w.y + 7, 13, "txt", w.w - 16)
      self:text(g, w.sub, w.x + 12, w.y + 27, 9, "mute", w.w - 16)
    else
      self:text(g, w.label, w.x + 12, w.y + 15, 13, "txt", w.w - 16)
    end
  elseif k == "hold" then
    if w.on then self:col(g, "acc"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 8)
    else self:col(g, "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 8); self:col(g, "acc"); g:stroke_rounded_rect(w.x + 1, w.y + 1, w.w - 2, w.h - 2, 8, 2) end
    self:ctext(g, w.label, { x=w.x, y=w.y + w.h / 2 - 20, w=w.w, h=20 }, 17, w.on and "#ffffff" or "txt")
    self:ctext(g, w.sub or "", { x=w.x, y=w.y + w.h / 2 + 6, w=w.w, h=14 }, 10, w.on and "#ffffff" or "mute")
  elseif k == "mtile" then
    -- a track on live: bright while it plays, dark when muted, an orange outline while a change waits for the beat or bar
    local muted, armed, txt
    if w.group then
      muted = true
      for _, p in ipairs(w.group) do if self:mute_target(p) == 0 then muted = false end end
      txt = muted and "all muted" or "tap to mute all"
    else
      local p = self:pending(w.track)
      muted = (self.v["ockm-"..w.track.."-mute"] or 0) > 0
      armed = p ~= nil
      local q = math.floor(self.v["ockm-mute-quant"] or 0)
      local when = (q == 1) and "beat" or "bar"
      if not self:track_in(w.track) then muted = true; armed = false; txt = "off in this pattern"
      elseif armed then txt = (p > 0 and "out on " or "in on ") .. when
      elseif muted then txt = "muted"
      elseif self:silent(w.track) then txt = "not soloed"
      else txt = "playing" end
    end
    self:col(g, muted and "card" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 8)
    if muted then self:col(g, "dim"); g:stroke_rounded_rect(w.x + 1, w.y + 1, w.w - 2, w.h - 2, 8, 1.5) end
    if armed then self:col(g, "acc"); g:stroke_rounded_rect(w.x + 1.5, w.y + 1.5, w.w - 3, w.h - 3, 8, 3) end
    if not w.group then self:col(g, "dim"); g:fill_rounded_rect(w.x + 10, w.y + 14, 10, 10, 5) end
    self:text(g, w.label, w.x + (w.group and 10 or 26), w.y + 10, 14, muted and "mute" or "txt", w.w - 30)
    self:text(g, txt, w.x + 10, w.y + w.h - 26, 10, armed and "acc" or "mute", w.w - 50)
  elseif k == "partbtn" then
    local out = not self:track_in(w.label)
    self:col(g, w.sel and "on" or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:col(g, "dim"); g:fill_rounded_rect(w.x + 10, w.y + w.h / 2 - 5, 10, 10, 5)
    self:text(g, out and (w.label .. " (off)") or w.label, w.x + 28, w.y + w.h / 2 - 8, 13, w.sel and "bg" or (out and "mute" or "txt"), w.w - 96)
  elseif k == "card" then
    self:col(g, "card"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 8)
  elseif k == "locked" then
    self:col(g, "card"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, w, 12, "mute")
  elseif k == "group" then
    self:col(g, "card"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 8)
    self:col(g, "dim"); g:stroke_rounded_rect(w.x, w.y, w.w, w.h, 8, 1)
  elseif k == "onoff" then
    local hw = w.w / 2
    self:col(g, "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, w.h / 2)
    self:col(g, w.on and "acc" or "dim"); g:fill_rounded_rect(w.on and w.x or (w.x + hw), w.y, hw, w.h, w.h / 2)
    self:ctext(g, "on", { x=w.x, y=w.y, w=hw, h=w.h }, 11, w.on and "bg" or "mute")
    self:ctext(g, "off", { x=w.x + hw, y=w.y, w=hw, h=w.h }, 11, w.on and "mute" or "txt")
  elseif k == "scpic" then   -- one beat of the sidechain: the part's level after each kick
    self:col(g, "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    local n, ih = 24, w.h - 8
    local cw = (w.w - 8) / n
    self:col(g, "acc")
    for i = 0, n - 1 do
      local lvl = 1 - (w.amt or 0) * sc_dip(w.shape or 1, (i + 0.5) / n)
      local bh = math.max(1, lvl * ih)
      g:fill_rect(w.x + 4 + i * cw, w.y + 4 + ih - bh, math.max(1, cw - 1), bh)
    end
  elseif k == "parttile" then
    self:col(g, w.on and "card" or "bg"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 8)
    self:col(g, w.on and "dim" or "off"); g:stroke_rounded_rect(w.x, w.y, w.w, w.h, 8, 1)
    self:text(g, w.label, w.x + 14, w.y + 12, 20, w.on and "txt" or "mute", w.w - 104)
    -- the same on/off switch as on each part's tab
    local sx, sy, sw, sh = w.x + w.w - 90, w.y + 12, 78, 24
    local hw = sw / 2
    self:col(g, "off"); g:fill_rounded_rect(sx, sy, sw, sh, sh / 2)
    self:col(g, w.on and "acc" or "dim"); g:fill_rounded_rect(w.on and sx or (sx + hw), sy, hw, sh, sh / 2)
    self:ctext(g, "on", { x=sx, y=sy, w=hw, h=sh }, 11, w.on and "bg" or "mute")
    self:ctext(g, "off", { x=sx + hw, y=sy, w=hw, h=sh }, 11, w.on and "mute" or "txt")
    self:text(g, w.l1 or "", w.x + 14, w.y + w.h - 44, 11, "mute", w.w - 24)
    self:text(g, w.l2 or "", w.x + 14, w.y + w.h - 25, 11, "mute", w.w - 24)
  elseif k == "bar" then
    self:col(g, w.now and "off" or "card"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 8)
    if w.now then self:col(g, "acc"); g:stroke_rounded_rect(w.x, w.y, w.w, w.h, 8, 2) end
    self:text(g, "bar " .. w.n, w.x + 12, w.y + 14, 11, "mute", w.w - 20)
    self:text(g, w.label, w.x + 12, w.y + w.h / 2 - 16, (w.w > 150) and 28 or 20, "txt", w.w - 20)
    self:text(g, w.sub or "", w.x + 12, w.y + w.h - 30, 11, "mute", w.w - 20)
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
    if w.off then
      -- not in use: no value shown
    elseif w.bold then
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
      self:ctext(g, w.label, w, 10, w.off and "mute" or "txt")
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
    self:text(g, w.label, w.x, w.y + math.max(4, (w.h - 15) / 2), 13, ((self.v["ockm-drums-on"] or 1) > 0) and "txt" or "mute", w.w)
  elseif k == "lane" then
    self:draw_lane(g, w)
  elseif k == "blockinfo" then
    local b = w.follow and self:play_block() or self.page
    local n = self:blocks()
    b = clamp(b, 0, n - 1)
    local s = string.format("steps %d-%d", b * 16 + 1, math.min((b + 1) * 16, self:shown_len()))
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
    local len = self:shown_len()
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
    local v = self:get("ockm-pat-"..SLOTS[self.slot], self:dabs(w.i))
    local c = (v >= 2) and "acc" or ((v > 0) and "on" or "off")
    self:col(g, c); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    if w.i % 4 == 0 then self:col(g, "mute"); g:fill_rect(w.x, w.y + w.h + 4, w.w, 2) end
  elseif k == "vlane" then
    local pitch = (W - 32) / 16
    local nm, timing = SLOTS[self.slot], (self.lane or "vel") == "time"
    for i = 0, 15 do
      local x, bw = 16 + i * pitch + 3, pitch - 6
      local step = self:dabs(i)
      local v = self:get("ockm-pat-"..nm, step)
      self:col(g, "card"); g:fill_rounded_rect(x, w.y, bw, w.h, 4)
      if v > 0 then
        if timing then
          local n = self:get("ockm-pat-"..nm.."-nudge", step)
          local hh = math.abs(n) / 0.25 * (w.h / 2)
          local mid = w.y + w.h / 2
          self:col(g, "mute"); g:fill_rect(x, mid - 1, bw, 2)
          if hh >= 1 then self:col(g, "acc"); g:fill_rect(x + 4, (n > 0) and (mid - hh) or mid, bw - 8, hh) end
        else
          local hv = self:drum_vel(v) * w.h
          self:col(g, (v >= 2) and "acc" or "on"); g:fill_rounded_rect(x + 4, w.y + w.h - hv, bw - 8, hv, 3)
        end
      end
    end
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
    if w.log then f = clamp(math.log(math.max(v, w.lo) / w.lo) / math.log(w.hi / w.lo), 0, 1) end
    self:text(g, w.label, w.x, w.y + w.h / 2 - 7, 13, "txt", 100)
    local sx, sw = w.x + 110, w.w - 180
    self:col(g, "off"); g:fill_rounded_rect(sx, w.y + w.h / 2 - 5, sw, 10, 5)
    self:col(g, "acc"); g:fill_rounded_rect(sx, w.y + w.h / 2 - 5, math.max(10, sw * f), 10, 5)
    g:fill_ellipse(sx + sw * f - 10, w.y + w.h / 2 - 10, 20, 20)
    self:text(g, fmt(v) .. (w.log and " Hz" or ""), w.x + w.w - 56, w.y + w.h / 2 - 7, 13, "mute", 70)
  elseif k == "eqcurve" then
    -- the response from 20 Hz to 20 kHz, +-15 dB, as thin columns from the 0 dB line
    self:col(g, "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    local mid = w.y + w.h / 2
    self:col(g, "dim"); g:fill_rect(w.x, mid, w.w, 1)
    for _, hz in ipairs({ 100, 1000, 10000 }) do
      local fx = w.x + w.w * math.log(hz / 20) / math.log(1000)
      g:fill_rect(fx, w.y + 4, 1, w.h - 8)
    end
    -- the track's spectrum (while it plays): one bar per octave band, behind the curve
    local sp = self.spec and self.spec[w.track]
    if sp and self.playing ~= 0 then
      self:col(g, "dim")
      for b, f in ipairs(SPEC_F) do
        local db = sp[b - 1]
        if db then
          local x0 = w.x + w.w * math.log(f / 1.41 / 20) / math.log(1000)
          local x1 = w.x + w.w * math.log(f * 1.41 / 20) / math.log(1000)
          local hh = clamp((db - 30) / 70, 0, 1) * (w.h - 8)
          g:fill_rect(x0 + 1, w.y + w.h - 4 - hh, x1 - x0 - 2, hh)
        end
      end
    end
    self:col(g, "acc")
    local cols = 90
    for c = 0, cols - 1 do
      local f = 20 * 1000 ^ ((c + 0.5) / cols)
      local db = clamp(self:eq_response(w.track, f), -15, 15)
      local hh = db / 15 * (w.h / 2 - 4)
      local cx = w.x + c * w.w / cols
      if hh >= 0 then g:fill_rect(cx, mid - hh, w.w / cols - 1, math.max(hh, 1)) else g:fill_rect(cx, mid, w.w / cols - 1, -hh) end
    end
    self:text(g, "100", w.x + w.w * math.log(5) / math.log(1000) + 3, w.y + w.h - 16, 10, "mute", 40)
    self:text(g, "1k", w.x + w.w * math.log(50) / math.log(1000) + 3, w.y + w.h - 16, 10, "mute", 40)
    self:text(g, "10k", w.x + w.w * math.log(500) / math.log(1000) + 3, w.y + w.h - 16, 10, "mute", 40)
  end
end

function ui:draw_lane(g, w)
  local n = w.track
  local cw = w.w / 16
  local base = self:play_block() * 16
  if self.playing == 0 then base = self.page * 16 end
  local plen = self:plen(self:track_part(n))
  for i = 0, 15 do
    local st, ix = 0, (base + i) % plen      -- a shorter part repeats inside the loop
    if n <= 8 then st = self:get("ockm-pat-"..SLOTS[n], ix)
    elseif n <= 10 then
      local part = SYNTHS[n - 8]
      if self:get("ockm-pat-"..part.."-on", ix) > 0 then st = (self:get("ockm-pat-"..part.."-acc", ix) > 0) and 2 or 1 end
    else st = self:get("ockm-pat-chord-on", ix) end
    -- an empty step on the beat (1, 5, 9, 13) is a shade lighter, so the bar reads in fours
    local empty = (i % 4 == 0) and "beat" or "off"
    if self:silent(TRACKS[n]) then self:col(g, (st > 0) and "dim" or "off")
    else self:col(g, (st >= 2) and "acc" or ((st > 0) and "on" or empty)) end
    g:fill_rounded_rect(w.x + i * cw + 2, w.y + 4, cw - 4, w.h - 8, 3)
  end
end
