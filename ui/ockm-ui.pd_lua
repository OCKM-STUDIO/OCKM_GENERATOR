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
local VERSION = "v1.23"   -- shown on screen, so you can tell which version plugdata has loaded

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
local MONO_ENG  = { "acid","sub 808","fm","reese","pluck","analogue","donk","raw" }
-- the order the engines are shown in (v0.98: six bass, four lead, four chord). Numbers match ockm-<part>-engine, which
-- keep their old values so saved projects load; retired ones (bass pluck, lead acid and juno, chord pad and strings) are
-- left off and moved on to their replacements (RETIRED, below)
local MONO_ORDER = { 5, 0, 1, 3, 2, 6, 7 }
local LEAD_ENG  = { "acid","juno","dx","sync","mini","supersaw","raw" }
local LEAD_ORDER = { 4, 2, 3, 5, 6 }
local CHORD_ENG = { "stab","organ","pad","piano","rhodes","strings","hard" }
local CHORD_ORDER = { 0, 6, 1, 3, 4 }
local HIDE_CHORD_RHY = { [6]=true, [7]=true }
-- v1.04 progressions on the stepper, by how many chords: one, two, four, then soul (garage 4 and trip hop 8 are off the list)
-- v1.05 bass rhythms on the stepper (the rest are retired: they still play in loops saved on them)
local BASS_RHY_ORDER = { 0, 1, 2, 3, 4, 5, 6, 9, 14, 12, 18 }
-- v1.06 the lead: eleven rhythms and eight tunes on the steppers (the rest retired, still playing in old loops), and the
-- tunes' names where the lead's differ from the shared list
local LEAD_RHY_ORDER = { 10, 11, 12, 13, 8, 9, 0, 1, 3, 14, 15 }
local LEAD_TUNE_ORDER = { 0, 1, 8, 9, 18, 15, 16, 19 }
local LEAD_TUNE_NAME = { [0] = "one note", [16] = "question", [19] = "answer the bass" }
local PROG_ORDER = { 0, 1, 12, 13, 14, 15, 3, 16, 17, 5, 6, 7, 2, 10, 11, 18, 9 }   -- v1.01: retired (syncopated, garage skip); old loops move to tresillo
-- names shown on screen, where they differ from the engine's own
-- v1.23 bus effects: three buses, one effect slot each, played from the fx page's XY pad (one finger) and from macros
local BUSES = { "drums", "music", "master" }
local BFX = { "filter", "crush", "drive", "saturate" }          -- ockm-bfx-<bus>-type 0-3
local BFX_DEF = { drums = 1, music = 0, master = 3 }
local BFX_P = { filter = 0, crush = 0.2, drive = 0.3, saturate = 0.4 }
-- what the pad's two directions do, and the effect's own setting (nil: none)
local BFX_AXES = { filter = { "low-pass  <  open  >  high-pass", "resonance" }, crush = { "sample rate (lower to the right)", "bits (fewer up)" },
                   drive = { "drive", "tone (brighter up)" }, saturate = { "amount", "warmth" } }
local BFX_SET = { crush = "tone (darker)", drive = "character (grit)", saturate = "bias (tape)" }
local VOICINGS = { "close", "open", "wide" }
local LH_PATTERNS = { "anchor", "pulse", "synco", "broken", "answer" }   -- v1.20 the left hand (ockm-chord-hands 1-5)
local ENG_LABEL = { reese = "wide", mini = "analogue", stab = "poly", hard = "hard stab" }
local function eng_label(nm) return ENG_LABEL[nm] or nm end
-- each engine's sweet spot (k1-k4), loaded when it's picked, so it sounds right straight away
local ENGINE_K = {
  bass  = { [0] = { 0.35, 0.6, 0.55, 0.4 }, [1] = { 0.45, 0.3, 0.35, 0.55 }, [2] = { 0.4, 0.35, 0.45, 0.4 },
            [3] = { 0.45, 0.5, 0.35, 0.5 }, [5] = { 0.42, 0.25, 0.45, 0.45 }, [6] = { 0.5, 0.5, 0.35, 0.45 }, [7] = { 0.3, 0.75, 0.6, 0.35 } },
  lead  = { [2] = { 0.45, 0.1, 0.25, 0.5 }, [3] = { 0.4, 0.55, 0.5, 0.45 }, [4] = { 0.55, 0.3, 0.4, 0.45 }, [5] = { 0.55, 0.55, 0.3, 0.5 }, [6] = { 0.55, 0.82, 0.7, 0.35 } },
  chord = { [0] = { 0.45, 0.5, 0.0, 0.32 }, [1] = { 0.5, 0.4, 0.3, 0.4 }, [3] = { 0.5, 0.3, 0.4, 0.4 }, [4] = { 0.5, 0.4, 0.3, 0.5 }, [6] = { 0.45, 0.6, 0.6, 0.3 } },
}
-- retired engines: what a saved project's engine becomes, and the knobs that make it sound like the old one
local RETIRED = {
  bass  = { [4] = { 5, { k4 = 0.7 } } },
  lead  = { [0] = { 4, { k2 = 0.8 } }, [1] = { 4, { chorus = 2 } } },
  chord = { [2] = { 0, { k3 = 0.8, k4 = 0.6 } }, [5] = { 0, { k3 = 0.7, k4 = 0.6, chorus = 2 } } },
}
local function engines_of(part) if part == "chord" then return CHORD_ENG elseif part == "lead" then return LEAD_ENG end return MONO_ENG end
local KNOBS = {
  acid  = {"cutoff","resonance","env amount","decay"},
  ["sub 808"] = {"tone","weight","pitch drop","decay"},
  fm    = {"brightness","ratio","env","decay"},
  reese = {"cutoff","detune","env amount","decay"},
  pluck = {"brightness","saw-square","snap","decay"},
  analogue = {"cutoff","saw-square","envelope","decay"},
  donk  = {"brightness","bounce","hollow","decay"},
  stab  = {"brightness","detune","attack","length"},
  hard  = {"cutoff","resonance","drive","length"},
  raw   = {"cutoff","resonance","wave","decay"},
  supersaw = {"spread","cutoff","drift","decay"},
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
local RHYTHMS = { { "offbeat" }, { "rolling" }, { "gallop" }, { "acid" }, { "sparse dub" }, { "tech bounce" }, { "acid 16ths" }, { "trip hop" }, { "hook" }, { "sparse melody" }, { "phrase" }, { "question answer" }, { "pickup" }, { "arp gate" }, { "long" }, { "stab" } }
local BASS_RHYTHMS = { { "offbeat" }, { "8ths" }, { "16ths" }, { "dotted" }, { "octave" }, { "held" }, { "on the beat" }, { "dembow" }, { "two step" }, { "cluster" }, { "round the kick" }, { "gallop" }, { "acid" }, { "acid 16ths" }, { "bounce" }, { "sparse dub" }, { "trip hop" }, { "speed garage" }, { "house pickup" } }
local MONO_NOTES = { "root", "octaves", "root fifth", "acid riff", "walk up", "minor stab", "dub", "pedal", "arp up", "arp updown", "call", "descend", "melody", "melody steps", "melody high", "motif", "motif call", "motif high", "arp evolve", "answer the bass", "motif loose", "call loose" }
local BASS_RIFFS = { { "root" }, { "octaves" }, { "fifth" }, { "seventh below" }, { "dub" }, { "walk up" }, { "acid" }, { "arp" } }
local CHORD_RHY = { { "pads" }, { "halves" }, { "offbeat" }, { "skank" }, { "organ" }, { "tresillo" }, { " " }, { " " }, { "call answer" }, { "8ths" }, { "piano riff" }, { "sustained" } }
local PROGS = { { "one chord", "i" }, { "vamp", "i iv" }, { "dub techno", "i . . VII" }, { "deep house", "i iv VI v" }, { "garage", "i VI iv v" }, { "pop", "i VI III VII" }, { "uplift", "VI VII i" }, { "andalusian", "i VII VI V" }, { "trip hop", "i VII VI v" }, { "soul", "ii V I" }, { "piano house", "I V vi IV" }, { "anthem", "vi IV I V" }, { "seven", "i VII" }, { "six", "i VI" }, { "five", "i v" }, { "two five", "ii v" }, { "lift", "i VII VI VII" }, { "seven four", "i VII iv" }, { "gospel", "I vi ii V" } }
local SPICE = { { 0, "triad" }, { 1, "7th" }, { 6, "9th" }, { 7, "11th" } }
local FILLS = { "snare roll", "tom run", "cut out", "snare build", "breakbeat" }
local GROOVES = { "four floor", "house", "deep house", "tech house", "minimal", "techno", "dub techno", "garage", "breakbeat", "boom bap", "trip hop", "electro", "clear", "chicago", "jackin", "disco", "soulful", "afro house", "lofi house", "2 step", "speed garage", "funky house", "ghetto house", "nu disco", "rolling", "detroit", "berlin", "industrial", "hypnotic", "acid techno", "think break", "jungle", "big beat", "downtempo", "one drop", "half time", "lofi hip hop", "hard house", "dnb two step", "dnb rolling" }
local GROOVE_BANKS = { { "house", { 0, 1, 2, 13, 14, 15, 16, 17, 21, 22, 23, 24 } }, { "techno", { 3, 4, 5, 6, 25, 26, 27, 28, 29, 11, 37, 32 } } }
local CHORD_TYPES = { { k=0, name="triad", 0, 2, 4 }, { k=0, name="seventh", 0, 2, 4, 6 }, { k=0, name="sus2", 0, 1, 4 }, { k=0, name="power", 0, 4, 7 }, { k=0, name="sus4", 0, 3, 4 }, { k=0, name="sixth", 0, 2, 4, 5 }, { k=0, name="ninth", 2, 4, 6, 8 }, { k=0, name="eleventh", 2, 6, 8, 10 }, { k=1, name="m9", 3, 7, 10, 14 }, { k=1, name="m11", 3, 10, 14, 17 }, { k=1, name="m7", 0, 7, 10, 15 }, { k=1, name="4ths", 0, 5, 10, 15 }, { k=1, name="maj9", 4, 7, 11, 14 } }
local CHORD_CENTRE, CHORD_FLOOR = 62, 50   -- smooth chords sit around D4, their lowest note no lower than D3
-- a chord's notes (MIDI). deg: the chord's root as a scale step; sc: the scale (7 semitones); root: the key (0 C .. 11 B);
-- smooth: keep every chord at about the same height (inversions for chords in the key, octaves for fixed shapes), so
-- they move by small steps and stay out of the bass; voicing 0 close, 1 open, 2 wide; turn: the turnaround's major V
local function chord_voicing(deg, ctype, sc, root, smooth, voicing, turn, lift)
  local ty = CHORD_TYPES[(ctype or 0) + 1] or CHORD_TYPES[1]
  local rox = (root <= 7) and (48 + root) or (36 + root)
  local function at(a)
    local s = sc[(a % 7) + 1]
    if turn and s == 10 then s = 11 end   -- the turnaround raises the minor 7th: E major in A minor
    return rox + 12 * math.floor(a / 7) + s
  end
  deg = math.floor(deg)
  local n = {}
  if ty.k == 1 then
    local r = at(deg)
    for _, o in ipairs(ty) do
      if turn and o % 12 == 3 then o = o + 1 end   -- a minor shape turns major on the turnaround
      n[#n + 1] = r + o
    end
  else
    for _, o in ipairs(ty) do
      local v = at(deg + o)
      if o == 8 and v - at(deg) == 13 then v = at(deg + 7) end   -- a flat 9th grinds on the bass: the root instead
      n[#n + 1] = v
    end
  end
  if smooth then
    local cands = {}
    if ty.k == 1 then cands[1] = n
    else
      table.sort(n)
      for i = 0, #n - 1 do
        local c = {}
        for j, v in ipairs(n) do c[j] = (j <= i) and v + 12 or v end
        table.sort(c); cands[#cands + 1] = c
      end
    end
    local best, bc
    local all = {}
    for _, c in ipairs(cands) do
      local sum, lo = 0, c[1]
      for _, v in ipairs(c) do sum = sum + v; if v < lo then lo = v end end
      local mean = sum / #c
      local m = math.floor((CHORD_CENTRE - mean) / 12 + 0.5)
      for mm = m - 1, m + 1 do
        local cost = math.abs(mean + 12 * mm - CHORD_CENTRE)
        if lo + 12 * mm < CHORD_FLOOR then cost = cost + (CHORD_FLOOR - lo - 12 * mm) end
        for j = 2, #c do if c[j] - c[j - 1] == 1 then cost = cost + 4 end end   -- no semitone rubs inside a chord
        local cand = {}
        for j, v in ipairs(c) do cand[j] = v + 12 * mm end
        all[#all + 1] = { cand, mean + 12 * mm, cost }
        if not bc or cost < bc - 1e-9 then bc = cost; best = cand end
      end
    end
    -- drift (v1.01): one inversion higher than the best, if that stays in the band, for chords built from the key
    if lift and ty.k == 0 then
      local bm = 0; for _, v in ipairs(best) do bm = bm + v end; bm = bm / #best
      local up, um
      for _, a in ipairs(all) do
        if a[2] > bm + 1 and a[2] - CHORD_CENTRE <= 7 and a[3] < 50 and (not um or a[2] < um) then up, um = a[1], a[2] end
      end
      if up then best = up end
    end
    n = best
  end
  -- open lifts the second note an octave; wide also drops the lowest an octave and lifts the fourth
  if voicing == 1 or voicing == 2 then
    if n[2] then n[2] = n[2] + 12 end
    if voicing == 2 then n[1] = n[1] - 12; if n[4] then n[4] = n[4] + 12 end end
  end
  return n, ty
end
-- v1.20 two hands (piano, organ, Rhodes). The left hand on step i: pat 1 anchor (root and octave when the chord changes,
-- and each bar), 2 pulse (on every beat), 3 syncopated (1, the and of 2, 4), 4 broken (root on the beats, fifth and
-- octave on the ands), 5 answer (on the beats the right hand leaves empty). on: the right hand's hit here (0 none),
-- changed: the chord changed here. Returns a shape ("both" root and octave, "root", "fifth", "oct") and a strength, or nil
local function left_hand(pat, i, on, changed)
  local b = i % 16
  local top = (b == 0) and 0.9 or 0.75
  if pat == 1 then
    if changed or b == 0 then return "both", 0.9 end
  elseif pat == 2 then
    if i % 4 == 0 then return "both", top end
    if changed then return "both", 0.8 end
  elseif pat == 3 then
    if b == 0 or b == 6 or b == 12 then return "both", top end
    if changed then return "both", 0.8 end
  elseif pat == 4 then
    if i % 4 == 0 then return "root", top end
    if changed then return "root", 0.8 end
    if i % 8 == 2 then return "fifth", 0.6 end
    if i % 8 == 6 then return "oct", 0.6 end
  elseif pat == 5 then
    if (i % 4 == 0 or changed) and on == 0 then return "both", top end
  end
  return nil
end
-- the left hand's notes: the chord's root between G2 and F#3 (an octave over the bass), with its octave or fifth
local LH_LOW = 43
local function left_notes(shape, deg, sc, root)
  local d = math.floor(deg)
  local pc = (root + sc[d % 7 + 1]) % 12
  local low = LH_LOW + (pc - LH_LOW) % 12
  if shape == "root" then return { low } end
  if shape == "oct" then return { low + 12 } end
  if shape == "fifth" then return { low + (sc[(d + 4) % 7 + 1] - sc[d % 7 + 1]) % 12 } end
  return { low, low + 12 }
end
-- the right hand with the left playing: four-note chords drop their root (the left hand has it), and nothing sits
-- below G3, so the hands don't crowd each other
local function right_hand(n, deg, sc, root)
  local pc = (root + sc[math.floor(deg) % 7 + 1]) % 12
  local o = {}
  if #n >= 4 then for _, x in ipairs(n) do if x % 12 ~= pc then o[#o + 1] = x end end end
  if #o < 3 then o = {}; for _, x in ipairs(n) do o[#o + 1] = x end end
  local seen, r = {}, {}
  for _, x in ipairs(o) do
    while x < 55 do x = x + 12 end
    if not seen[x] then seen[x] = true; r[#r + 1] = x end
  end
  table.sort(r)
  return r
end
local TWO_HANDS = { [1] = true, [3] = true, [4] = true }   -- the chord engines that play with two hands: organ, piano, Rhodes
local PROG_SHAPES = { { { 0, 16 } }, { { 0, 16 }, { 3, 16 } }, { { 0, 48 }, { 6, 16 } }, { { 0, 16 }, { 3, 16 }, { 5, 16 }, { 4, 16 } }, { { 0, 8 }, { 5, 8 }, { 3, 8 }, { 4, 8 } }, { { 0, 16 }, { 5, 16 }, { 2, 16 }, { 6, 16 } }, { { 5, 16 }, { 6, 16 }, { 0, 32 } }, { { 0, 16 }, { 6, 16 }, { 5, 16 }, { 4, 16 } }, { { 0, 32 }, { 6, 32 }, { 5, 32 }, { 4, 32 } }, { { 1, 16 }, { 4, 16 }, { 0, 32 } }, { { 0, 16 }, { 4, 16 }, { 5, 16 }, { 3, 16 } }, { { 5, 16 }, { 3, 16 }, { 0, 16 }, { 4, 16 } }, { { 0, 16 }, { 6, 16 } }, { { 0, 16 }, { 5, 16 } }, { { 0, 16 }, { 4, 16 } }, { { 1, 16 }, { 4, 16 } }, { { 0, 16 }, { 6, 16 }, { 5, 16 }, { 6, 16 } }, { { 0, 16 }, { 6, 16 }, { 3, 32 } }, { { 0, 16 }, { 5, 16 }, { 1, 16 }, { 4, 16 } } }
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
  { "level", 0, 1.5 }, { "tune", -12, 12 }, { "decay", 10, 400 }, { "verb", 0, 1, "reverb" }, { "delay", 0, 1 },
  { "tone", -1, 1 }, { "drive", 0, 1 }, { "start", 0, 1 }, { "synth", 0, 2 },
  { "labchar", -1, 1 }, { "labmorph", 0, 1 }, { "labrseed", 0, 99999 }, { "labramt", 0, 1 }, { "labpseed", 0, 99999 },
}
local SYNTH_SLIDERS  = { { "level", 0, 1.5 }, { "tune", -12, 12 }, { "decay", 10, 400 }, { "drive", 0, 1 } }   -- v1.03: no tone (character does it)
local SAMPLE_SLIDERS = { { "level", 0, 1.5 }, { "tune", -12, 12, "pitch" }, { "decay", 10, 100, "length" }, { "tone", -1, 1 }, { "start", 0, 1 } }
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
  self.screen = "live"
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

-- v0.93: the starting mix, like a real one: kick loudest, hats and percussion tucked in, room above on every fader (to 1.5)
local MIX_DRUM = { [0] = 1.0, [1] = 0.75, [2] = 0.75, [3] = 0.6, [4] = 0.55, [5] = 0.5, [6] = 0.65, [7] = 0.6 }   -- by sound
local MIX_SYNTH = { bass = 0.85, lead = 0.7, chord = 0.65 }
local LEVEL_MAX = 1.5
-- v1.08 faders work in dB, like a desk: unity at u (three quarters up for a track, half way for the master), +10 dB at
-- the top, -40 dB near the bottom and off at the very bottom. The value stays a plain gain, so saved mixes don't move
local function fader_db(f, u)
  if f <= 0.01 then return nil end
  if f >= u then return (f - u) / (1 - u) * 10 end
  return (f - u) / u * 40
end
local function fader_gain(f, u)
  local db = fader_db(f, u)
  return db and 10 ^ (db / 20) or 0
end
local function fader_pos(g, u)
  if not g or g <= 0 then return 0 end
  local db = 20 * math.log(g, 10)
  if db >= 0 then return math.min(1, u + db / 10 * (1 - u)) end
  return math.max(0.02, u + db / 40 * u)
end
function ui:defaults()
  local v = self.v
  v["ockm-chord-smooth"] = 1
  v["ockm-volume"] = 1; v["ockm-verb-mix"] = 0.3; v["ockm-delay-mix"] = 0.5
  v["ockm-drive"] = 0; v["ockm-delay-fb"] = 0.4; v["ockm-delay-steps"] = 3; v["ockm-verb-size"] = 0.6; v["ockm-verb-tone"] = 0.5
  for _, t in ipairs(SYNTHS) do v["ockm-"..t.."-level"] = MIX_SYNTH[t] end
  for _, t in ipairs(TRACKS) do
    v["ockm-"..t.."-lowcut"] = 20; v["ockm-"..t.."-eqlow"] = 0; v["ockm-"..t.."-eqmid"] = 0; v["ockm-"..t.."-eqmidf"] = 400; v["ockm-"..t.."-eqhigh"] = 0
  end
  v["ockm-bass-on"] = 1; v["ockm-lead-on"] = 1; v["ockm-chord-on"] = 1; v["ockm-drums-on"] = 1; v["ockm-turn-every"] = 0; v["ockm-turn-to"] = 4; v["ockm-bass-walk"] = 0; v["ockm-lead-outside"] = 0.35; v["ockm-rise"] = 0; v["ockm-end"] = 0; v["ockm-impact"] = 0; v["ockm-pump"] = 0
  v["ockm-bass-scshape"] = 1; v["ockm-lead-scshape"] = 1; v["ockm-chord-scshape"] = 1
  v["ockm-bass-riff"] = -1; v["ockm-bass-slideamt"] = 0; v["ockm-bass-octave"] = 0; v["ockm-lead-octave"] = 0
  v["ockm-lead-repeat"] = 0; v["ockm-lead-rests"] = 0
  v["ockm-chord-rate"] = 1; v["ockm-chord-push"] = 0; v["ockm-chord-vary"] = 0; v["ockm-chord-drift"] = 0; v["ockm-chord-hands"] = 0   -- analogue, analogue, poly (as the engine starts)
  v["ockm-drum-punch"] = 0.5
  v["ockm-bass-bus"] = 1   -- v1.23: the bass with the drums for the bus effects
  for _, b in ipairs(BUSES) do
    v["ockm-bfx-"..b.."-type"] = BFX_DEF[b]; v["ockm-bfx-"..b.."-glide"] = 0.15; v["ockm-bfx-"..b.."-on"] = 0
    v["ockm-bfx-"..b.."-x"] = 0.5; v["ockm-bfx-"..b.."-y"] = 0.5
    for _, e in ipairs(BFX) do v["ockm-bfx-"..b.."-"..e.."-mix"] = 1; v["ockm-bfx-"..b.."-"..e.."-p"] = BFX_P[e] end
  end
  v["ockm-style"] = -1; v["ockm-bass-half"] = 0; v["ockm-lead-half"] = 0; v["ockm-chord-half"] = 0
  v["ockm-bass-mode"] = 0; v["ockm-lead-mode"] = 0; v["ockm-chord-mode"] = 0   -- 0 auto, 1 manual
  v["ockm-bass-sync"] = 1; v["ockm-lead-sync"] = 1; v["ockm-leader"] = 0; v["ockm-drum-groove"] = -1
  v["ockm-drum-len"] = 16; v["ockm-bass-len"] = 64; v["ockm-lead-len"] = 64; v["ockm-chord-len"] = 64
  v["ockm-evolve-every"] = 0; v["ockm-evolve-mode"] = 1; v["ockm-evolve-parts"] = 15
  v["ockm-drum-loop"] = 0; v["ockm-fill-every"] = 0; v["ockm-fill-style"] = 0; v["ockm-swing"] = 56; v["ockm-accent"] = 0.3; v["ockm-sync"] = 0; v["ockm-volume"] = 1
  for _, p in ipairs({ "bass", "lead" }) do v["ockm-"..p.."-lock"] = 0; v["ockm-"..p.."-density"] = 1; v["ockm-"..p.."-seed"] = 0 end
  v["ockm-bpm"] = 124; v["ockm-len"] = 128; v["ockm-filter"] = 0; v["ockm-root"] = 9; v["ockm-scale"] = 0
  for i, nm in ipairs(SLOTS) do
    v["ockm-"..nm.."-sound"] = ({0,1,2,4,5,7,3,6})[i]
    v["ockm-"..nm.."-level"] = MIX_DRUM[v["ockm-"..nm.."-sound"]] or 0.7; v["ockm-"..nm.."-tune"] = 0; v["ockm-"..nm.."-decay"] = 100
    v["ockm-"..nm.."-verb"] = 0; v["ockm-"..nm.."-delay"] = 0; v["ockm-"..nm.."-sample"] = 0; v["ockm-"..nm.."-synth"] = 0
    v["ockm-"..nm.."-tone"] = 0; v["ockm-"..nm.."-drive"] = 0; v["ockm-"..nm.."-start"] = 0
    v["ockm-"..nm.."-labchar"] = 0; v["ockm-"..nm.."-labmorph"] = 0; v["ockm-"..nm.."-labrseed"] = 0; v["ockm-"..nm.."-labramt"] = 0; v["ockm-"..nm.."-labpseed"] = 1
  end
  for _, t in ipairs(SYNTHS) do
    for _, k in ipairs({"engine","k1","k2","k3","k4","drive","verb","delay","rhythm","notes","type","prog"}) do v["ockm-"..t.."-"..k] = 0 end
    v["ockm-"..t.."-chorus"] = 0; v["ockm-"..t.."-lfo-shape"] = 0; v["ockm-"..t.."-lfo-rate"] = 4; v["ockm-"..t.."-lfo-depth"] = 0; v["ockm-"..t.."-lfo-target"] = 1
  end
  -- each part starts on its default engine and that engine's sweet spot, as the engine does (v0.98)
  local DEF_ENG = { bass = 5, lead = 4, chord = 0 }
  for _, t in ipairs(SYNTHS) do
    v["ockm-"..t.."-engine"] = DEF_ENG[t]
    for j = 1, 4 do v["ockm-"..t.."-k"..j] = ENGINE_K[t][DEF_ENG[t]][j] end
  end
end

function ui:hooks()
  local h = { "ockm-bpm","ockm-len","ockm-root","ockm-scale","ockm-filter" }
  for _, nm in ipairs(SLOTS) do
    for _, p in ipairs(DRUM_PARAMS) do h[#h+1] = "ockm-"..nm.."-"..p[1] end
    h[#h+1] = "ockm-"..nm.."-sound"; h[#h+1] = "ockm-"..nm.."-sample"
  end
  for _, t in ipairs({"bass","lead"}) do
    for _, k in ipairs({"engine","k1","k2","k3","k4","drive","verb","delay","rhythm","notes","octave"}) do h[#h+1] = "ockm-"..t.."-"..k end
  end
  h[#h+1] = "ockm-bass-riff"; h[#h+1] = "ockm-bass-slideamt"; h[#h+1] = "ockm-lead-repeat"; h[#h+1] = "ockm-lead-rests"
  for _, k in ipairs({"engine","k1","k2","k3","k4","type","smooth","verb","delay","rhythm","prog","voicing","strum","rate","push","vary","drift","hands"}) do h[#h+1] = "ockm-chord-"..k end
  for _, t in ipairs(SYNTHS) do for _, k in ipairs({ "lfo-shape", "lfo-rate", "lfo-depth", "lfo-target", "chorus" }) do h[#h+1] = "ockm-"..t.."-"..k end end
  for _, t in ipairs(TRACKS) do h[#h+1] = "ockm-"..t.."-mute"; h[#h+1] = "ockm-"..t.."-solo" end
  h[#h+1] = "ockm-bass-bus"   -- v1.23 bus effects
  for _, b in ipairs(BUSES) do
    h[#h+1] = "ockm-bfx-"..b.."-type"; h[#h+1] = "ockm-bfx-"..b.."-glide"
    for _, e in ipairs(BFX) do h[#h+1] = "ockm-bfx-"..b.."-"..e.."-mix"; h[#h+1] = "ockm-bfx-"..b.."-"..e.."-p" end
  end
  for _, t in ipairs(SYNTHS) do h[#h+1] = "ockm-"..t.."-level"; h[#h+1] = "ockm-"..t.."-mode" end
  for _, t in ipairs(SYNTHS) do h[#h+1] = "ockm-"..t.."-on" end
  for _, t in ipairs(TRACKS) do for _, k in ipairs({ "lowcut", "eqlow", "eqmid", "eqmidf", "eqhigh" }) do h[#h+1] = "ockm-"..t.."-"..k end end
  h[#h+1] = "ockm-rise"; h[#h+1] = "ockm-end"; h[#h+1] = "ockm-impact"; h[#h+1] = "ockm-pump"
  h[#h+1] = "ockm-bass-sync"; h[#h+1] = "ockm-lead-sync"; h[#h+1] = "ockm-leader"; h[#h+1] = "ockm-drum-groove"
  for _, p in ipairs({ "bass", "lead" }) do
    for _, k in ipairs({ "lock", "density", "seed" }) do h[#h+1] = "ockm-"..p.."-"..k end
  end
  for _, k in ipairs({ "ockm-drum-len", "ockm-bass-len", "ockm-lead-len", "ockm-chord-len" }) do h[#h+1] = k end
  for _, k in ipairs({ "ockm-drum-loop", "ockm-swing", "ockm-accent", "ockm-sync", "ockm-fill-every", "ockm-fill-style",
                       "ockm-evolve-every", "ockm-evolve-mode", "ockm-evolve-parts" }) do h[#h+1] = k end
  for _, k in ipairs({ "ockm-drums-on", "ockm-turn-every", "ockm-turn-to", "ockm-bass-walk", "ockm-lead-outside", "ockm-bass-sidechain", "ockm-lead-sidechain", "ockm-chord-sidechain",
                         "ockm-style", "ockm-bass-half", "ockm-lead-half", "ockm-chord-half",
                         "ockm-bass-scshape", "ockm-lead-scshape", "ockm-chord-scshape", "ockm-drum-punch" }) do h[#h+1] = k end
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
      if x then
        o.v[hook] = x; o:dirty()
        local part = hook:match("^ockm%-(%a+)%-engine$")
        if part and RETIRED[part] and RETIRED[part][math.floor(x)] then o:retire_engine(part, math.floor(x)) end
        if hook == "ockm-chord-rhythm" and HIDE_CHORD_RHY[math.floor(x)] then o:send("ockm-chord-rhythm", 5) end
        -- v1.03: the LFO is a sine on k1 every bar, 2 or 4 bars; the chorus is off or on (II)
        local lp, lk = hook:match("^ockm%-(%a+)%-lfo%-(%a+)$")
        if lp then
          if lk == "shape" and x ~= 0 then o:send(hook, 0) end
          if lk == "target" and x ~= 1 then o:send(hook, 1) end
          if lk == "rate" and (x < 4 or x > 6) then o:send(hook, (x < 4) and 4 or 6) end
        end
        if hook:match("^ockm%-%a+%-chorus$") and (x == 1 or x == 3) then o:send(hook, 2) end
      end
    end
    listen(hook, set)
    listen("ockm-show-" .. hook:sub(6), set)
  end
  listen("ockm-playing", function(o, sel, a)
    o.playing = tonumber(a[1]) or 0
    if o.playing == 0 and o.macro and o.macro.run then o:macro_finish() end   -- stopped: a running recipe lets go at once
    if o.playing ~= 0 and o.evo then o.evo.bar = 0 end   -- evolve counts phrases from play, as the fills do
    o:dirty()
  end)
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
  listen("ockm-bar",     function(o, sel, a) o:on_bar() end)
  listen("ockm-chord-changed", function(o) o:chord_vary() end)
  listen("ockm-midi-note", function(o, sel, a) o:midi_pad(tonumber(a[1]) or 0, tonumber(a[2]) or 0) end)
  listen("ockm-midi-cc",   function(o, sel, a) o:midi_knob(tonumber(a[2]) or 0, tonumber(a[1]) or 0) end)
  listen("ockm-midi-pgm",  function(o, sel, a) o:midi_pgm(tonumber(a[1]) or 0) end)
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
  self.lateclock = pd.Clock:new():register(self, "macro_late")
  self.gapclock = pd.Clock:new():register(self, "gap_clear")   -- v1.22: a step after the drop, clear a gap that didn't happen
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
  if self.lateclock then self.lateclock:destruct() end
  if self.gapclock then self.gapclock:destruct() end
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
-- redraws are capped at 25 a second (v0.82). The screen draws on the same core as the sound, so a sweep that changes a value
-- every few milliseconds (the filter on build, a macro) used to redraw every 5 ms and starve the audio on the Pi. Now any
-- number of changes inside one frame make one redraw at the end of it
local FRAME_MS = 40
function ui:dirty()
  if self.clock and not self.frame_due then self.frame_due = true; self.clock:delay(FRAME_MS) end
end
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
function ui:redraw() self.frame_due = nil; self:repaint() end

function ui:on_step(n)
  if self.macro then self.macro.held = (self.macro.held or 0) + 1 end
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
  elseif self.screen == "fx" then self:layout_fx(add)
  elseif self.screen == "drums" then self:layout_drums(add)
  elseif self.screen == "mixer" then self:layout_mixer(add)
  elseif self.screen == "compose" then self:layout_compose(add)
  elseif self.screen == "project" then self:layout_project(add)
  elseif self.screen == "arrange" then self:layout_arrange(add)
  elseif self.screen == "setup" then self:layout_setup(add)
  else self:layout_synth(add) end
  if self.sheet == "export" then self:layout_export(add) end
  if self.sheet == "eq" then self:layout_eq(add) end
  if self.sheet == "variations" then self:layout_variations(add) end
  if self.sheet == "slotpick" then self:layout_slotpick(add) end
  if self.sheet == "fxset" then self:layout_fxset(add) end
  -- messages on screens that have no message line of their own
  if self.msg and (self.screen == "perform" or self.screen == "live" or self.screen == "fx" or self.screen == "compose" or self.screen == "mixer" or self.screen == "arrange" or self.screen == "setup" or self.screen == "drums"
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
-- v0.87: one perform screen ("live" inside), as wide as the two it replaces so the other tabs stay where they were
local TABS = { { "live", "perform", nil, 88 }, { "fx", "fx", nil, 56 }, { "mixer", "mixer", nil, 58 },   -- v1.23: fx takes part of perform's width
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
    add{ kind="disc", x=W - 120, y=12, w=50, h=48, tap=function() self:save_variation() end }
  end
  add{ kind="menubtn", x=W - 66, y=12, w=50, h=48, sel=(self.menu or self.screen == "project" or self.screen == "setup"), tap=function() self.menu = not self.menu end }
  if self.screen ~= "project" and self.screen ~= "setup" and self.screen ~= "live" and self.screen ~= "fx" then self:layout_nav(add) end
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

-- the drums tab's all drums view (v0.87, from Perform A): 8 lanes with mute and solo, a tap cycles empty, hit, accent.
-- Tap a name (or swipe right across the names) to go back to one drum, with its sound and settings
function ui:layout_drumgrid(add)
  local back = function(dx) if dx > 0 then self.drums_all = false end end
  for i = 1, 8 do
    local y = self:lane_y(i)
    local name = SHORT[(self.v["ockm-"..SLOTS[i].."-sound"] or 0) + 1]
    local tr = TRACKS[i]
    add{ kind="ms", x=108, y=y, w=38, h=LANE_H, label="M", hook="ockm-"..tr.."-mute" }
    add{ kind="ms", x=150, y=y, w=38, h=LANE_H, label="S", hook="ockm-"..tr.."-solo" }
    add{ kind="lanename", x=16, y=y, w=88, h=LANE_H, label=name, swipe=back, tap=function() self.slot = i; self.drums_all = false end }
    add{ kind="lane", x=LANE_X, y=y, w=W - LANE_X - 16, h=LANE_H, track=i }
    local cw = (W - LANE_X - 16) / 16
    for c = 0, 15 do
      local st = (self:shown_block() * 16 + c) % self:plen("drum")
      add{ kind="pcell", x=LANE_X + c * cw, y=y, w=cw, h=LANE_H, slot=i, step=st, tap=function() self:drum_cycle(i, st) end }
    end
  end
  add{ kind="text", x=16, y=420, w=W - 160, h=12, size=10,
       label="all drums: tap a step for a hit, again for an accent, again to clear. Tap a name for that drum's sound and settings" }
  add{ kind="btn", x=W - 16 - 130, y=410, w=130, h=36, small=true, accent=true, label="one drum", tap=function() self.drums_all = false end }
end

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
    add{ kind="btn", x=lx + 6, y=ay, w=bw, h=ah, small=true, accent=true, label="mutate", tap=function()
      self:send(skey, seed + 1); self:say(part .. ": variation " .. (seed + 1) .. ". original goes back") end }
    add{ kind="btn", x=lx + 12 + bw, y=ay, w=bw, h=ah, small=true, quiet=(seed == 0), label="original", tap=function() self:send(skey, 0) end }
    add{ kind="hbar", x=lx + 18 + 2 * bw, y=ay, w=iw - 12 - 2 * bw, h=ah, hook="ockm-"..part.."-density", lo=0, hi=2, label="density", bold=true }
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
    self:say(rise and "rise off: no drop" or "rise: building to the next loop start (2 bars or more), then the drop")
  end }
  -- v1.17: rewind (a tap) and beat repeat (hold) in place of pump and throw (the macros still use those)
  add{ kind="btn", x=mx + (mw + 6), y=PART_Y, w=mw, h=PART_H, label="rewind", edge=true, flash="rewind", tap=function()
    psend("ockm-rewind", "bang", {}); self:flash_btn("rewind")
    self:say("rewind: back it spins, then the loop drops in again from the top")
  end }
  add{ kind="pad", x=mx + 2 * (mw + 6), y=PART_Y, w=mw, h=PART_H, hook="ockm-drop", label="drop" }
  add{ kind="pad", x=mx + 3 * (mw + 6), y=PART_Y, w=mw, h=PART_H, hook="ockm-repeat", label="repeat" }
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
  local now = (self.playing == 0) or ((self.v["ockm-mute-quant"] or 0) == 0 and not self.mute_bar)
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

-- does what's playing (with anything waiting to land) match this scene?
function ui:scene_matches(keep)
  for _, t in ipairs(TRACKS) do
    if (self.v["ockm-"..t.."-solo"] or 0) > 0 then return false end
    if self:mute_target(t) ~= (keep(t) and 0 or 1) then return false end
  end
  return true
end
-- a scene switch: on applies it (remembering what was muted and soloed), off puts that back; oneshot: all in
function ui:scene_switch(i, keep, oneshot)
  if oneshot then self.scene_on, self.scene_saved = nil, nil; self:scene(keep); return end
  if self.scene_on == i and self.scene_saved then
    local sv = self.scene_saved
    self.scene_on, self.scene_saved = nil, nil
    for _, t in ipairs(TRACKS) do
      if self:mute_target(t) ~= sv.mutes[t] then self:qmute(t, sv.mutes[t]) end
      if (self.v["ockm-"..t.."-solo"] or 0) ~= sv.solos[t] then self:send("ockm-"..t.."-solo", sv.solos[t]) end
    end
    return
  end
  if not self.scene_on then
    local sv = { mutes = {}, solos = {} }
    for _, t in ipairs(TRACKS) do sv.mutes[t] = self:mute_target(t); sv.solos[t] = self.v["ockm-"..t.."-solo"] or 0 end
    self.scene_saved = sv
  end
  self.scene_on = i
  self:scene(keep)
end
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
  local evo_on = math.floor(self.v["ockm-evolve-every"] or 0) > 0
  local qr = evo_on and (458 - 70) or 458   -- v1.00: keep (evolve's new original) takes the end of the row while evolve runs
  local qw = (qr - 116 - 12) / 3
  if evo_on then
    add{ kind="btn", x=458 - 64, y=80, w=64, h=34, small=true, accent=true, label="keep", tap=function() self:evo_keep() end }
  end
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
  -- v1.15: drums only, no drums and kick + bass are switches: on (orange) applies the scene, off puts back exactly what
  -- was muted and soloed before. Change a mute by hand while one is on and it lets go (what you hear is yours again).
  -- All in is a one-shot: everything in, solos cleared
  if self.scene_on and not self:scene_matches(SC[self.scene_on][2]) then self.scene_on, self.scene_saved = nil, nil end
  for i, sc in ipairs(SC) do
    local lit = (self.scene_on == i)
    add{ kind="btn", x=22 + (i - 1) * (sw + 6), y=530, w=sw, h=52, small=true, label=sc[1], edge=not lit, accent=lit, flash="scene" .. i,
         tap=function() self:scene_switch(i, sc[2], i == #SC); self:flash_btn("scene" .. i) end }
  end
  -- master effects, big
  local mx, iw = rx + 6, half_w - 12
  local mw = (iw - 18) / 4
  local rise = (self.v["ockm-rise"] or 0) > 0
  local pump = self.v["ockm-pump"] or 0
  add{ kind="choice", x=mx, y=80, w=mw, h=52, label="rise", sel=rise, accent=true, tap=function() self:send("ockm-rise", rise and 0 or 1) end }
  -- v1.17: rewind (tap: it spins back, then the loop restarts from the top) and beat repeat (hold: the slice you're on
  -- loops in time, halving every bar you hold). They replace pump and throw; the macros still use those
  add{ kind="btn", x=mx + (mw + 6), y=80, w=mw, h=52, label="rewind", edge=true, flash="rewind", tap=function()
    psend("ockm-rewind", "bang", {}); self:flash_btn("rewind") end }
  add{ kind="pad", x=mx + 2 * (mw + 6), y=80, w=mw, h=52, hook="ockm-drop", label="drop", sub="hold" }
  add{ kind="pad", x=mx + 3 * (mw + 6), y=80, w=mw, h=52, hook="ockm-repeat", label="repeat", sub="hold" }
  local hold = self.filter_hold
  add{ kind="hbar", x=mx, y=140, w=iw, h=150, hook="ockm-filter", lo=-1, hi=1, label=hold and "filter (held)" or "filter", bold=true, spring=not hold }
  add{ kind="choice", x=mx + iw - 64, y=148, w=56, h=30, label="hold", small=true, onbar=true, sel=hold, tap=function()
    self.filter_hold = not hold
    if hold then self:filter_spring() end
  end }
  local hw = (iw - 6) / 2
  add{ kind="hbar", x=mx, y=298, w=hw, h=56, hook="ockm-drive", lo=0, hi=1, label="drive", bold=true }
  add{ kind="hbar", x=mx + hw + 6, y=298, w=hw, h=56, hook="ockm-volume", lo=0, hi=1, label="volume", bold=true, db=0.5 }
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
         sub=self:macro_sub(i) or ((rc and (rc.bars or 0) > 0) and ("tap: " .. rc.bars .. " bars, or hold") or ("slot " .. string.char(64 + i))),
         on=lit, down=function() self:macro_down(i) end, up=function() self:macro_up(i) end }
    add{ kind="btn", x=x + w3 - 40, y=432, w=34, h=30, small=true, quiet=true, label="v", tap=function() self.pick_slot = i; self.sheet = "slotpick" end }
  end
end

-- ------------------------------------------------------------------ fx (v1.23)
-- Three buses (drums, music, master), one effect each. Pick a bus, pick its effect, then play it on the XY pad: put a
-- finger down and the effect comes in, move it to play it, lift and it goes (unless latched: then it stays where you
-- left it). The screen takes one finger at a time, so latch one bus, then play another on the pad
function ui:bfx_on(b) return (self.v["ockm-bfx-"..b.."-on"] or 0) > 0 end
function ui:bfx_name(b) return BFX[math.floor(self.v["ockm-bfx-"..b.."-type"] or BFX_DEF[b]) + 1] or "filter" end
function ui:bfx_set_on(b, on)
  if self:bfx_on(b) ~= on then self:send("ockm-bfx-"..b.."-on", on and 1 or 0) end
end
function ui:bfx_pad(x, y, phase)
  local b = self.fx_target or "drums"
  if phase == "up" then
    if not (self.fx_latch and self.fx_latch[b]) then self:bfx_set_on(b, false) end
    return
  end
  self:send("ockm-bfx-"..b.."-x", x); self:send("ockm-bfx-"..b.."-y", y)
  if phase == "down" then self:bfx_set_on(b, true) end
end
function ui:layout_fx(add)
  self.fx_latch = self.fx_latch or {}
  local tb = self.fx_target or "drums"
  local cx, cw, ch = 16, 320, 146
  for i, b in ipairs(BUSES) do
    local y = 80 + (i - 1) * (ch + 8)
    local on, nm = self:bfx_on(b), self:bfx_name(b)
    add{ kind="card", x=cx, y=y, w=cw, h=ch }
    add{ kind="choice", x=cx + 8, y=y + 8, w=cw - 16, h=40, sel=(tb == b), label=b .. ": " .. nm .. (on and "  (in)" or ""),
         tap=function() self.fx_target = b end }
    local fw = (cw - 16 - 18) / 4
    for k, e in ipairs(BFX) do
      add{ kind="choice", x=cx + 8 + (k - 1) * (fw + 6), y=y + 54, w=fw, h=38, small=true, label=e, sel=(nm == e), accent=true,
           tap=function() self.fx_target = b; self:send("ockm-bfx-"..b.."-type", k - 1) end }
    end
    local hw = (cw - 16 - 6) / 2
    local lat = self.fx_latch[b] and true or false
    add{ kind="choice", x=cx + 8, y=y + 98, w=hw, h=40, small=true, accent=true, sel=lat, label=lat and "latched" or "latch",
         tap=function()
           self.fx_latch[b] = not lat
           if lat then self:bfx_set_on(b, false) end   -- unlatching lets it go
         end }
    add{ kind="btn", x=cx + 8 + hw + 6, y=y + 98, w=hw, h=40, small=true, label="settings",
         tap=function() self.fx_target = b; self.sheet = "fxset" end }
  end
  -- the bass: with the drums (it goes where the kick goes) or with the music
  local bb = (self.v["ockm-bass-bus"] or 1) > 0
  local by = 80 + 3 * (ch + 8)
  add{ kind="text", x=cx + 8, y=by + 14, w=80, h=12, label="bass goes", size=11 }
  local bw = (cw - 96 - 6) / 2
  add{ kind="choice", x=cx + 90, y=by, w=bw, h=40, small=true, label="with drums", sel=bb, tap=function() self:send("ockm-bass-bus", 1) end }
  add{ kind="choice", x=cx + 90 + bw + 6, y=by, w=bw, h=40, small=true, label="with music", sel=not bb, tap=function() self:send("ockm-bass-bus", 0) end }
  -- the pad
  local nm = self:bfx_name(tb)
  add{ kind="xy", x=352, y=80, w=W - 352 - 16, h=H - 80 - 12, bus=tb, fx=nm, axes=BFX_AXES[nm],
       down=function(x, y) self:bfx_pad(x, y, "down") end, drag=function(x, y) self:bfx_pad(x, y, "move") end, up=function() self:bfx_pad(0, 0, "up") end }
end
-- an effect's settings: how much of it (mix), its own setting, and how quickly it follows the pad (glide)
function ui:layout_fxset(add)
  local b = self.fx_target or "drums"
  local nm = self:bfx_name(b)
  add{ kind="scrim", x=0, y=0, w=W, h=H, tap=function() self.sheet = nil end }
  local x0, y0, w0 = W / 2 - 240, 120, 480
  local rows = { { "ockm-bfx-"..b.."-"..nm.."-mix", "mix (dry to wet)" } }
  if BFX_SET[nm] then rows[#rows + 1] = { "ockm-bfx-"..b.."-"..nm.."-p", BFX_SET[nm] } end
  rows[#rows + 1] = { "ockm-bfx-"..b.."-glide", "glide (how slowly it follows your finger)" }
  add{ kind="sheet", x=x0, y=y0, w=w0, h=60 + #rows * 62 + 56 }
  add{ kind="text", x=x0 + 16, y=y0 + 16, w=w0 - 32, h=14, label=b .. " bus: " .. nm .. " settings", size=13, col="txt" }
  for i, r in ipairs(rows) do
    add{ kind="hbar", x=x0 + 16, y=y0 + 48 + (i - 1) * 62, w=w0 - 32, h=54, hook=r[1], lo=0, hi=1, label=r[2], bold=true }
  end
  add{ kind="btn", x=x0 + w0 - 116, y=y0 + 56 + #rows * 62, w=100, h=40, small=true, label="done", tap=function() self.sheet = nil end }
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
  -- v1.23: a bus effect (its effect picked in the move; the amount runs from none to full, or for the filter from
  -- closed low-pass through open to high-pass)
  { id = "drums fx", bus = "drums" }, { id = "music fx", bus = "music" }, { id = "master fx", bus = "master" },
}
-- where an amount puts a bus effect on the pad (x, y)
local function bus_xy(fx, v)
  local e = BFX[(fx or 0) + 1] or "filter"
  if e == "filter" then return 0.5 + 0.5 * clamp(v, -1, 1), 0.35 end
  v = clamp(v, 0, 1)
  if e == "crush" then return 0.9 * v, v end
  if e == "drive" then return v, 0.6 end
  return v, 0.4
end
local function bus_range(fx) return ((fx or 0) == 0) and -1 or 0, 1 end
local TARGET = {}; for _, t in ipairs(TARGETS) do TARGET[t.id] = t end
local HOW = { { "jump", 0 }, { "1 beat", 4 }, { "1 bar", 16 }, { "2 bars", 32 }, { "4 bars", 64 }, { "8 bars", 128 } }   -- in steps (8 bars: v1.18)
local BACK = { "snap back", "glide back", "stay" }
-- v0.93: a recipe can run for a length: a tap plays it for that many bars, then everything comes back on the 1
local RUN_BARS = { 0, 1, 2, 4, 8 }
local GAPS = { { "no gap", 0 }, { "gap: half a beat", 2 }, { "gap: a beat", 4 } }   -- v1.22, in steps
local MACRO_NAMES = { "8 bar lift", "4 bar lift", "build", "wash", "breakdown", "strip", "sink", "dub out", "lift", "blur", "freeze", "smash", "swell", "haze",
                      "tunnel", "pressure", "drop out", "air", "grit" }
local function default_settings()
  return {
    sounds = {},     -- your saved drum sounds: { name, type, and the slot settings in SOUND_KEYS }
    macros = {
      -- v1.18: the 8 bar lift (in build's place): the 4 bar lift over twice as long, its high-pass going further, most of it
      -- late (v1.21 late: 60% of the way over the first four bars, all the way by the end of bar 7, held for the last bar).
      -- v1.22: up to 0.6, and gap: the whole mix drops out for the last beat (4 steps) before the drop
      { name = "8 bar lift", bars = 8, gap = 4, moves = { { t = "mutes", v = 3, how = 1, back = 1 }, { t = "filter", v = 0.6, how = 6, back = 1, late = true },
                                                { t = "reverb", v = 0.4, how = 2, back = 1 }, { t = "delay", v = 0.3, how = 2, back = 1 } } },
      { name = "wash", moves = { { t = "delay", v = 0.85, how = 1, back = 1 }, { t = "feedback", v = 0.78, how = 1, back = 1 },
                                 { t = "reverb", v = 0.9, how = 1, back = 1 }, { t = "filter", v = -0.5, how = 2, back = 1 } } },
      -- v0.94: the breakdown's high-pass twin: drums out, the high-pass climbs slowly over the 4 bars (halfway up), a touch of
      -- reverb and delay, then it all slams back on the 1
      { name = "4 bar lift", bars = 4, gap = 2, moves = { { t = "mutes", v = 3, how = 1, back = 1 }, { t = "filter", v = 0.5, how = 5, back = 1 },
                                          { t = "reverb", v = 0.4, how = 2, back = 1 }, { t = "delay", v = 0.3, how = 2, back = 1 } } },   -- gentle
      { name = "sink", moves = { { t = "filter", v = -0.85, how = 3, back = 1 }, { t = "drive", v = 0.7, how = 3, back = 1 } } },
      { name = "dub out", moves = { { t = "throw", v = 1, how = 1, back = 1 }, { t = "feedback", v = 0.85, how = 1, back = 3 },
                                    { t = "delay", v = 0.8, how = 1, back = 3 } } },
      -- v0.93: a performance recipe. Mutes and effects together: tap and it runs for 4 bars, then the drums and the
      -- effects all come back on the 1; or hold it as long as you like and it drops on the next bar after you let go
      { name = "breakdown", bars = 4, moves = { { t = "mutes", v = 3, how = 1, back = 1 }, { t = "filter", v = -0.6, how = 3, back = 1 },
                                               { t = "reverb", v = 0.55, how = 2, back = 1 }, { t = "delay", v = 0.45, how = 2, back = 1 } } },
    },
    slots = { 1, 3, 6 },
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
  -- v1.18: lift is the 4 bar lift; build (as it came, with pump) becomes the 8 bar lift
  for i, r in ipairs(d.macros) do
    if r.name == "lift" and r.bars then r.name = "4 bar lift" end
    if r.name == "build" then
      local pumped = false
      for _, m in ipairs(r.moves or {}) do if m.t == "pump" then pumped = true end end
      if pumped then d.macros[i] = default_settings().macros[1] end
    end
  end
  -- v1.22: the lifts' high-passes go further (8 bar 0.6, from 0.45 or 0.65; 4 bar 0.5, from 0.3), and both gain a gap
  -- before the drop (a beat on the 8 bar, half a beat on the 4 bar). Ones you've changed keep your amounts
  for _, r in ipairs(d.macros) do
    if r.name == "8 bar lift" and r.bars then
      for _, m in ipairs(r.moves or {}) do if m.t == "filter" and m.late and (m.v == 0.45 or m.v == 0.65) then m.v = 0.6 end end
      if r.gap == nil then r.gap = 4 end
    elseif r.name == "4 bar lift" and r.bars then
      for _, m in ipairs(r.moves or {}) do if m.t == "filter" and m.v == 0.3 and m.how == 5 then m.v = 0.5 end end
      if r.gap == nil then r.gap = 2 end
    end
  end
  local has, hp = false, false
  for _, r in ipairs(d.macros) do if r.name == "breakdown" then has = true end; if (r.name == "lift" or r.name == "4 bar lift") and r.bars then hp = true end end
  -- v0.95: lift's high-pass goes half as far, over the 4 bars (it went to 0.6 in a bar)
  for _, r in ipairs(d.macros) do
    if (r.name == "lift" or r.name == "4 bar lift") and r.bars then
      for _, m in ipairs(r.moves) do if m.t == "filter" and m.v == 0.6 and m.how == 3 then m.v = 0.3; m.how = 5 end end
    end
  end
  if not hp then
    for i, r in ipairs(d.macros) do
      if r.name == "strip" then
        d.macros[i] = default_settings().macros[3]
        if d.slots[2] == 2 then d.slots[2] = i end
        break
      end
    end
  end
  if not has then
    for i, r in ipairs(d.macros) do
      if r.name == "lift" and not r.bars then d.macros[i] = default_settings().macros[6]; break end
    end
  end
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
  if t.bus then word = t.bus .. " " .. (BFX[(m.fx or 0) + 1] or "fx") end
  if m.t == "filter" then word = (m.v >= 0) and "filter up" or "filter down" end
  if t.switch then return word end
  if HOW[m.how] and HOW[m.how][2] > 0 then word = word .. " over " .. HOW[m.how][1] end
  return word
end
local function recipe_summary(r)
  if not r or #r.moves == 0 then return "empty: tap to make one" end
  local out = {}
  for _, m in ipairs(r.moves) do out[#out + 1] = move_label(m) end
  if (r.gap or 0) > 0 and (r.bars or 0) > 0 then out[#out + 1] = "gap before the drop" end
  return table.concat(out, ", ")
end

-- ------------------------------------------------------------------ playing a macro
-- press: each move goes to its amount (straight away or over its time); let go: each comes back (snap or glide),
-- unless it stays, in which case the macro stays lit until you tap it again
local function steps_ms(self, steps) return steps * 15000 / math.max(40, self.v["ockm-bpm"] or 124) end
function ui:mset(hook, x) self.v[hook] = x; pd.send(hook, "float", { x }) end
function ui:ramp(hook, to, ms, done)
  self.ramps = self.ramps or {}
  if ms <= 0 then self.ramps[hook] = nil; self:mset(hook, to); if done then done() end; return end
  self.ramps[hook] = { from = self.v[hook] or 0, to = to, t = 0, dur = ms, done = done }
  if self.rampclock then self.rampclock:delay(30) end
end
function ui:ramp_tick()
  local any = false
  for hook, r in pairs(self.ramps or {}) do
    r.t = r.t + 30
    local f = math.min(1, r.t / r.dur)
    self:mset(hook, r.from + (r.to - r.from) * f)
    if f >= 1 then self.ramps[hook] = nil; if r.done then r.done() end else any = true end
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
  if mc and mc.slot == slot and mc.run then   -- a recipe that's running: tap again to bring it back on the next bar
    if not mc.ending then self:macro_end() end
    return
  end
  if mc and mc.slot == slot and mc.latched then self:macro_finish(); return end   -- a macro that stayed: tap again to let it go
  if mc then self:macro_finish() end
  local r = (slot == 4) and self.me.macros[self.try_sel or 1] or self.me.macros[self.me.slots[slot]]
  if not r then return end
  local run = (r.bars or 0) > 0 and self.playing ~= 0
  if run then self:set_mute_bar(true) end   -- its mutes go on the 1, not part way through a bar
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
    elseif t and t.bus then
      -- a bus effect: in at its starting point, then over its time to the amount
      local b, pre = t.bus, "ockm-bfx-" .. t.bus .. "-"
      saved.bus = saved.bus or {}
      saved.bus[b] = { type = self.v[pre .. "type"] or BFX_DEF[b], on = self.v[pre .. "on"] or 0, x = self.v[pre .. "x"] or 0.5, y = self.v[pre .. "y"] or 0.5 }
      local x0, y0 = bus_xy(m.fx, 0)
      local x1, y1 = bus_xy(m.fx, m.v)
      self:mset(pre .. "type", m.fx or 0); self:mset(pre .. "x", x0); self:mset(pre .. "y", y0); self:mset(pre .. "on", 1)
      self:ramp(pre .. "x", x1, ms); self:ramp(pre .. "y", y1, ms)
    elseif t and t.id == "filter" and m.late and ms > 0 then
      -- late (v1.21): 60% of the way over the first half of the time, the rest by seven eighths, then held
      pd.send("ockm-filter-glide", "list", { m.v * 0.6, math.max(30, ms * 0.5) }); self.v["ockm-filter"] = m.v
      self.late = { v = m.v, ms = ms * 0.375 }; self.lateclock:delay(ms * 0.5)
    elseif t and t.id == "filter" then
      pd.send("ockm-filter-glide", "list", { m.v, math.max(30, ms) }); self.v["ockm-filter"] = m.v
    elseif t then
      saved.set[t.hook] = self.v[t.hook] or 0
      self:ramp(t.hook, t.switch and 1 or m.v, t.switch and 0 or ms)
    end
  end
  self.macro = { slot = slot, recipe = r, saved = saved, run = run and r.bars or nil, bars = 0, held = 0 }
end
-- put moves back: on letting go, all but the ones that stay; when finishing, everything (force: a recipe with a length,
-- where every move comes back together whatever it says)
function ui:gap_clear() pd.send("ockm-gap-arm", "float", { 0 }) end
function ui:macro_late()
  if self.late and self.macro then pd.send("ockm-filter-glide", "list", { self.late.v, math.max(30, self.late.ms) }) end
  self.late = nil
end
function ui:macro_restore(all, force)
  if self.lateclock then self.lateclock:unset() end; self.late = nil
  local mc = self.macro
  local r, saved = mc.recipe, mc.saved
  local stays = false
  for _, m in ipairs(r.moves) do
    local back = force and 1 or (m.back or 1)
    if back == 3 and not all then stays = true
    elseif force or not (all and back ~= 3 and mc.latched) then
      local t = TARGET[m.t]
      local glide = (back == 2) and steps_ms(self, 16) or 0
      if t and t.choices then
        for tr, x in pairs(saved.mutes) do if self:mute_target(tr) ~= x then self:qmute(tr, x) end end
      elseif t and t.bus then
        -- back to how the bus was: snap, or glide to the starting point over a bar, then out
        local b, pre = t.bus, "ockm-bfx-" .. t.bus .. "-"
        local sv = saved.bus and saved.bus[b] or { type = BFX_DEF[b], on = 0, x = 0.5, y = 0.5 }
        local function back_to()
          self:mset(pre .. "on", sv.on); self:mset(pre .. "type", sv.type); self:mset(pre .. "x", sv.x); self:mset(pre .. "y", sv.y)
        end
        if glide > 0 then
          local x0, y0 = bus_xy(m.fx, 0)
          self:ramp(pre .. "y", y0, glide); self:ramp(pre .. "x", x0, glide, back_to)
        else
          if self.ramps then self.ramps[pre .. "x"] = nil; self.ramps[pre .. "y"] = nil end
          back_to()
        end
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
function ui:set_mute_bar(on) self.mute_bar = on or nil; pd.send("ockm-mute-bar", "float", { on and 1 or 0 }) end
-- a recipe with a length, on its way out: ask for the mutes back now (they land on the next bar), and bring the
-- effects back on that same bar (on_bar)
function ui:macro_end()
  local mc = self.macro
  mc.ending = true
  -- v1.22: the gap before the drop (the mix drops out for the bar's last steps; too late in the bar and it's skipped)
  if (mc.recipe.gap or 0) > 0 and self.playing ~= 0 then pd.send("ockm-gap-arm", "float", { mc.recipe.gap }) end
  for tr, x in pairs(mc.saved.mutes) do if self:mute_target(tr) ~= x then self:qmute(tr, x) end end
end
function ui:on_bar()
  self:evo_bar()
  local mc = self.macro
  if not (mc and mc.run) then return end
  if mc.ending then
    if (mc.recipe.gap or 0) > 0 and self.gapclock then self.gapclock:delay(steps_ms(self, 1)) end
    self:macro_restore(true, true); self.macro = nil
    self:set_mute_bar(false)
    self:dirty(); return
  end
  mc.bars = mc.bars + 1   -- bar 1 is when its mutes land
  if mc.latched and mc.bars >= mc.run then self:macro_end() end   -- tapped: after its bars, back on the next 1
  self:dirty()
end
function ui:macro_up(slot)
  local mc = self.macro
  if not mc or mc.slot ~= slot or mc.latched then return end
  if mc.run then
    -- a tap (let go within a beat) runs it for its bars; a hold lasts while held, and drops on the next bar
    if (mc.held or 0) < 4 then mc.latched = true else self:macro_end() end
    return
  end
  if self:macro_restore(false) then mc.latched = true else self.macro = nil end
end
function ui:macro_finish()
  if not self.macro then return end
  pd.send("ockm-gap-arm", "float", { 0 })
  if self.macro.run then self:set_mute_bar(false); self:macro_restore(true, true); self.macro = nil; return end
  self:macro_restore(true)
  self.macro = nil
end
-- what a recipe pad says while it plays
function ui:macro_sub(i)
  local mc = self.macro
  if not (mc and mc.slot == i) then return nil end
  if mc.run then
    if mc.ending then return "back on the 1" end
    if not mc.latched then return "hold: drops when you let go" end
    return (mc.bars > 0) and ("bar " .. math.min(mc.bars, mc.run) .. " of " .. mc.run .. ": tap to drop") or "starts on the 1"
  end
  if mc.latched then return "tap to let go" end
  return nil
end

-- ------------------------------------------------------------------ chord vary (v1.01)
-- After the chord part is written (made for you, not yours), vary changes it a little. breathe: the last bar of the loop
-- changes, a stab rhythm (3 or more hits in its first bar) gets a push on the last 8th before the 1, a pad rhythm rests
-- for its last beat. move: bars alternate A B A B': B drops its last hit after the downbeat, B' adds one on the latest
-- empty 8th. Written as edits, so the part stays made for you and the next rebuild starts clean
function ui:chord_vary()
  local vy = math.floor(self.v["ockm-chord-vary"] or 0)
  if vy == 0 or (self.v["ockm-chord-mode"] or 0) > 0 then return end
  local L = self:plen("chord")
  local on = function(i) return math.floor(self:get("ockm-pat-chord-on", i)) end
  local deg = function(i) return math.floor(self:get("ockm-pat-chord-deg", i)) end
  local edit = function(i, v) psend("ockm-chord-edit", "list", { i, v, deg(i) }) end
  local hits = 0
  for i = 0, 15 do if on(i) > 0 then hits = hits + 1 end end
  if vy == 1 then
    local b = L - 16
    if hits >= 3 then
      if on(L - 2) == 0 then edit(L - 2, 1) end
    else
      for i = L - 4, L - 1 do if on(i) > 0 then edit(i, 0) end end
    end
  else
    for bar = 1, L / 16 - 1, 2 do
      local b0 = bar * 16
      if bar % 4 == 1 then
        for i = b0 + 15, b0 + 1, -1 do if on(i) > 0 then edit(i, 0); break end end
      else
        for i = b0 + 14, b0 + 2, -2 do if on(i) == 0 then edit(i, 1); break end end
      end
    end
  end
end

-- ------------------------------------------------------------------ MIDI controller (v0.95)
-- Pads and knobs from a controller such as an MPK mini or an MPC (no keys). Each bank of 8 pads reads like the screen,
-- top row first (v0.96): bank A's top row is drums 1-4, its bottom row drums 5-8 (tap: mute or bring back, landing like the
-- Perform tiles). Bank B's top row: macro slots A, B, C, pump; bottom row: drop, throw, rise, all in. Pads as notes (36-43
-- bank A, 44-51 bank B, bottom row first, on any channel) are held while the pad is; pads in program change mode (0-7,
-- 8-15) have no let go, so a macro taps (a recipe with a length runs its bars) and pump, drop and throw toggle.
-- Knobs by CC (70-77, or 1-8): filter, drive, delay, reverb, then k1-k4 of the synth whose tab you last opened.
local MIDI_KNOBS = { { "ockm-filter", -1, 1 }, { "ockm-drive", 0, 1 }, { "ockm-delay-mix", 0, 1 }, { "ockm-verb-mix", 0, 1 } }
-- pad k (0-15, bottom row first in each bank: 0-3 bottom, 4-7 top) to its place in reading order (1-16)
local function pad_place(k)
  local bank, j = math.floor(k / 8), k % 8
  return bank * 8 + ((j >= 4) and (j - 3) or (j + 5))
end
-- what pad p (1-16, in reading order) does. down: true pressed, false let go, nil a tap with no let go
function ui:pad_action(i, down)
  if i <= 8 then
    if down == false then return end
    local t = TRACKS[i]
    if not self:track_in(t) then return end
    self:qmute(t, (self:mute_target(t) > 0) and 0 or 1)
    return
  end
  local b = i - 8
  local MOVES = { [5] = "ockm-drop", [6] = "ockm-repeat" }   -- v1.17: rewind (pad 4) and repeat in place of pump and throw
  if b <= 3 then
    if down == nil then
      -- a tap with no let go: a recipe with a length runs its bars; any other macro stays on until the next tap
      local mc = self.macro
      self:macro_down(b)
      local now = self.macro
      if now and now ~= mc then
        if now.run then self:macro_up(b) else now.latched = true end
      end
    elseif down then self:macro_down(b) else self:macro_up(b) end
  elseif b == 4 then
    if down ~= false then psend("ockm-rewind", "bang", {}); self:flash_btn("rewind") end
  elseif MOVES[b] then
    local h = MOVES[b]
    local on = down
    if down == nil then on = (self.pad_on ~= h) end   -- no let go: a tap toggles it
    psend(h, "float", { on and 1 or 0 }); self.pad_on = on and h or nil
  elseif b == 7 then
    if down ~= false then self:send("ockm-rise", 1) end
  elseif down ~= false then
    self.scene_on, self.scene_saved = nil, nil
    self:scene(function() return true end)
  end
end
function ui:midi_pad(n, vel)
  n = math.floor(n)
  if n < 36 or n > 51 then return end
  self:pad_action(pad_place(n - 36), vel > 0)
  self:dirty()
end
function ui:midi_pgm(pg)
  pg = math.floor(pg)
  if pg < 0 or pg > 15 then return end
  self:pad_action(pad_place(pg), nil)
  self:dirty()
end
function ui:midi_knob(cc, val)
  cc = math.floor(cc)
  local k = (cc >= 70 and cc <= 77) and (cc - 69) or ((cc >= 1 and cc <= 8) and cc or nil)
  if not k then return end
  local x = math.max(0, math.min(127, val)) / 127
  if k <= 4 then
    local m = MIDI_KNOBS[k]
    local v = m[2] + (m[3] - m[2]) * x
    if k == 1 and math.abs(v) < 0.04 then v = 0 end   -- the filter's middle is off: give it a little room
    self:send(m[1], v)
  else
    self:send("ockm-" .. (SYNTHS[self.part or 1] or "bass") .. "-k" .. (k - 4), x)
  end
  self:dirty()
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
  -- v1.06: the lead's start isn't a setting any more: styles set it, and a blank project starts on motif and phrase
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
  local cols = { 100, iw - 100 - 90 - 90 - 34 - 24, 90, 90, 34 }
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
      m.t = nt.id
      if nt.bus then m.fx = BFX_DEF[nt.bus]; m.v = 0.6 else m.fx = nil; m.v = nt.choices and 1 or (nt.switch and 1 or ((nt.lo + nt.hi) / 2)) end
      self:save_settings() end }
    if t.bus then
      -- which effect (tap to step through), then how much
      local fw = 72
      add{ kind="btn", x=colx(2), y=y, w=fw, h=48, small=true, label=BFX[(m.fx or 0) + 1] or "filter", tap=function()
        m.fx = ((m.fx or 0) + 1) % #BFX
        local lo, hi = bus_range(m.fx); m.v = clamp(m.v or 0.5, lo, hi); self:save_settings() end }
      local hk = "macro-edit-" .. k
      self.v[hk] = m.v
      local lo, hi = bus_range(m.fx)
      add{ kind="hbar", x=colx(2) + fw + 6, y=y, w=cols[2] - fw - 6, h=48, hook=hk, lo=lo, hi=hi, label="how much", bold=true, edit=function(x) m.v = x; self:save_settings() end }
    elseif t.choices then
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
  if #r.moves < 6 then   -- v1.23: six (room for bus effects alongside a lift's four)
    add{ kind="btn", x=ix, y=154 + #r.moves * 54, w=iw, h=40, small=true, quiet=true, label="+ add a move (up to 6)", tap=function()
      r.moves[#r.moves + 1] = { t = "reverb", v = 0.6, how = 1, back = 1 }; self:save_settings() end }
  end
  -- v0.93: how long a tap plays it (hold always lasts while held)
  local rb = r.bars or 0
  local ri = 1; for q, b in ipairs(RUN_BARS) do if b == rb then ri = q end end
  add{ kind="text", x=ix, y=H - 118, w=iw, h=12, size=10,
       label=(rb > 0) and ("a tap plays it for " .. rb .. (rb == 1 and " bar" or " bars") .. ", then it all comes back on the 1 (mutes land on the bar). Or hold it") or "plays while held (moves that stay keep it lit)" }
  add{ kind="btn", x=ix + iw - 150, y=H - 104, w=150, h=24, small=true, label=(rb > 0) and ("runs " .. rb .. (rb == 1 and " bar" or " bars")) or "no length",
       tap=function() r.bars = RUN_BARS[ri % #RUN_BARS + 1]; if r.bars == 0 then r.bars = nil end; self:save_settings() end }
  -- v1.22: a gap before the drop: everything out for the last half beat or beat, then the drop on the 1
  if rb > 0 then
    local gi = 1; for q, g in ipairs(GAPS) do if g[2] == (r.gap or 0) then gi = q end end
    add{ kind="btn", x=ix + iw - 150 - 156, y=H - 104, w=150, h=24, small=true, label=GAPS[gi][1],
         tap=function() r.gap = GAPS[gi % #GAPS + 1][2]; if r.gap == 0 then r.gap = nil end; self:save_settings() end }
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
  local l = NEW_LEAD[2]   -- motif, on the phrase rhythm (a one-note lead is the worst first impression)
  psend("ockm-lead-rhythm", "float", { l[2] }); psend("ockm-lead-notes", "float", { l[3] })
  psend("ockm-save", "bang", {})
end

-- is a track playing a note on this step (and can it be heard)? For the lights on live
function ui:track_sounding(n)
  local t = TRACKS[n]
  if self:silent(t) then return false end
  if n <= 8 then return self:get("ockm-pat-"..t, self.step % self:plen("drum")) > 0 end
  return self:part_sounding(t)
end

function ui:open(screen)
  if screen == "perform" then screen = "live" end   -- v0.87: Perform A is gone; its drum grid is the drums tab's all drums view
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
  if self.drums_all then return self:layout_drumgrid(add) end
  local nm = SLOTS[self.slot]
  local AW = 96   -- the all drums button, right of the slots
  local tw = (W - 32 - 7 * 6 - 8 - AW) / 8
  -- which drum: the 8 slots, named by their sound. Swipe left across them for all eight at once
  local to_all = function(dx) if dx < 0 then self.drums_all = true end end
  for i = 1, 8 do
    local smp = math.floor(self.v["ockm-"..SLOTS[i].."-sample"] or 0)
    add{ kind="choice", x=16 + (i - 1) * (tw + 6), y=114, w=tw, h=40,
         label=SHORT[(self.v["ockm-"..SLOTS[i].."-sound"] or 0) + 1] .. (smp > 0 and string.format(" %02d", smp) or ""),
         sel=(i == self.slot), swipe=to_all, tap=function() self.slot = i; self:preview(i, true) end }
  end
  add{ kind="btn", x=W - 16 - AW, y=114, w=AW, h=40, small=true, accent=true, label="all drums", tap=function() self.drums_all = true end }
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
  -- v1.15: M and S for all eight drums together (lit when every drum is muted or soloed)
  local function all_drums(k) for _, nm in ipairs(SLOTS) do if (self.v["ockm-"..nm.."-"..k] or 0) <= 0 then return false end end return true end
  for j, ms in ipairs({ { "M", "mute" }, { "S", "solo" } }) do
    add{ kind="ms", x=W - 16 - 110 - 6 - 84 + (j - 1) * 44, y=267, w=40, h=30, label=ms[1], lit=all_drums(ms[2]),
         tap=function() local to = all_drums(ms[2]) and 0 or 1; for _, nm in ipairs(SLOTS) do self:send("ockm-"..nm.."-"..ms[2], to) end end }
  end
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
  -- v1.03: new sound (was random; wild is gone: morph with a new path travels far) and reset
  add{ kind="btn", x=266, y=y, w=100, h=30, small=true, label="new sound", off=off, flash="random", tap=function() self:lab_random(slot, 0.35) end }
  add{ kind="btn", x=372, y=y, w=half - 356, h=30, small=true, quiet=true, label="reset", off=off, flash="reset", tap=function() self:lab_reset(slot) end }
  for j, p in ipairs((smp > 0) and SAMPLE_SLIDERS or SYNTH_SLIDERS) do
    add{ kind="slider", x=16, y=424 + (j - 1) * 27, w=half, h=24, hook="ockm-"..nm.."-"..p[1], lo=p[2], hi=p[3], label=p[4] or p[1], preview=slot }
  end
  -- this drum's reverb and delay sends (the same as on the mixer)
  local sw = (half - 6) / 2
  self:group(add, 16, 562, half, 30)
  add{ kind="hbar", x=16, y=562, w=sw, h=30, hook="ockm-"..nm.."-verb", lo=0, hi=1, label="reverb", bold=true, preview=slot }
  add{ kind="hbar", x=16 + sw + 6, y=562, w=sw, h=30, hook="ockm-"..nm.."-delay", lo=0, hi=1, label="delay", bold=true, preview=slot }
  local gx = 16 + half + 16
  -- grooves: two banks of twelve, house and techno (plus clear)
  local cur = math.floor(self.v["ockm-drum-groove"] or -1)
  if not self.bank then
    self.bank = 1
    for b, bk in ipairs(GROOVE_BANKS) do for _, g in ipairs(bk[2]) do if g == cur then self.bank = b end end end
  end
  local nb = #GROOVE_BANKS
  local bkw = (half - (nb - 1) * 4) / nb
  for b, bk in ipairs(GROOVE_BANKS) do
    add{ kind="choice", x=gx + (b - 1) * (bkw + 4), y=342, w=bkw, h=24, small=true, label=bk[1], sel=(self.bank == b), tap=function() self.bank = b end }
  end
  local gw = (half - 4 * 6) / 5
  local shown = {}
  for _, n in ipairs(GROOVE_BANKS[self.bank][2]) do shown[#shown + 1] = n end
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
  local every = math.floor(self.v["ockm-fill-every"] or 0)
  local ph = self:phrase()
  add{ kind="text", x=gx, y=498, w=half, h=12, size=10,
       label="fill at the end of each phrase (" .. ((ph > 0) and ("every " .. ph .. " bars") or "phrase off") .. ": set on the builder)" }
  local nfw = (half - 6) / 2
  add{ kind="choice", x=gx, y=514, w=nfw, h=30, small=true, sel=(every == 0), label="no fill", tap=function() self:phrase_move("ockm-fill-every", false) end }
  -- v0.89: the drum bus. Punch: parallel compression and saturation on all eight drums together
  add{ kind="hbar", x=gx + nfw + 6, y=514, w=nfw, h=30, hook="ockm-drum-punch", lo=0, hi=1, label="punch (all drums)", bold=true }
  local style = math.floor(self.v["ockm-fill-style"] or 0)
  local sw = (half - (#FILLS - 1) * 6) / #FILLS
  for i, name in ipairs(FILLS) do
    add{ kind="choice", x=gx + (i - 1) * (sw + 6), y=552, w=sw, h=34, small=true, label=name, sel=(every > 0 and style == i - 1), accent=true,
         tap=function() self:send("ockm-fill-style", i - 1); if every == 0 then self:phrase_move("ockm-fill-every", true) end end }
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
  local MSX = W - 16 - 110 - 6 - 84               -- v1.15: M and S, left of on/off
  local HTX = MSX - 6 - 86 - 6 - 100              -- the half-time switch; slide, M and S, and on/off sit to its right
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
    if not self.msg and not yours then info = self:evo_status(part) or info end
    add{ kind="text", x=16, y=276, w=HTX - 32, h=12, label=info, size=11, col=self.msg and "acc" or nil }
    if mono then
      add{ kind="choice", x=MSX - 6 - 86, y=266, w=86, h=34, label="slide", accent=true, small=true, sel=self:mono_get(self.sel_step, "slide") > 0,
           tap=function() self:mono_toggle_slide() end }
    end
  end
  local onk = "ockm-"..part.."-on"
  add{ kind="ms", x=MSX, y=268, w=40, h=30, label="M", hook="ockm-"..part.."-mute" }
  add{ kind="ms", x=MSX + 44, y=268, w=40, h=30, label="S", hook="ockm-"..part.."-solo" }
  add{ kind="onoff", x=W - 16 - 110, y=268, w=110, h=30, on=(self.v[onk] or 1) > 0, tap=function() self:send(onk, ((self.v[onk] or 1) > 0) and 0 or 1) end }
  self:layout_synth_sound(add, part, mono)
end

-- pick an engine and load its sweet spot (k: the knobs to use instead, a style's own)
function ui:pick_engine(part, e, k)
  self:send("ockm-"..part.."-engine", e)
  local d = k or (ENGINE_K[part] or {})[e]
  if d then for j = 1, 4 do self:send("ockm-"..part.."-k"..j, d[j]) end end
end
-- a saved project on a retired engine: move it to the replacement, set to sound like the old one
function ui:retire_engine(part, old)
  local r = RETIRED[part][old]
  local d = (ENGINE_K[part] or {})[r[1]] or { 0.5, 0.5, 0.5, 0.5 }
  local k = { d[1], d[2], d[3], d[4] }
  for j = 1, 4 do if r[2]["k"..j] then k[j] = r[2]["k"..j] end end
  self:pick_engine(part, r[1], k)
  if r[2].chorus then self:send("ockm-"..part.."-chorus", r[2].chorus) end
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
  local order = (part == "lead") and LEAD_ORDER or (part == "bass") and MONO_ORDER or CHORD_ORDER
  ew = rw / #order
  for i, e in ipairs(order) do
    add{ kind="choice", x=rx + (i - 1) * ew, y=330, w=ew - 4, h=40, label=eng_label(eng[e + 1]), small=true, sel=(self.v["ockm-"..part.."-engine"] == e),
         tap=function() self:pick_engine(part, e) end }
  end
  local kn = KNOBS[eng[(self.v["ockm-"..part.."-engine"] or 0) + 1]] or KNOBS.acid
  local kw = (rw - 6) / 2
  for k = 1, 4 do
    local col, row = (k - 1) % 2, math.floor((k - 1) / 2)
    add{ kind="hbar", x=rx + col * (kw + 6), y=376 + row * 44, w=kw, h=40, hook="ockm-"..part.."-k"..k, lo=0, hi=1, label=kn[k], bold=true }
  end
  -- drive on its own, the reverb and delay sends on one panel, then the chorus (v1.03: level lives on the mixer only)
  local n = mono and 4 or 3
  local gaps = mono and (6 + 14 + 14) or (6 + 14)
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
  -- chorus on or off (v1.03; on is II: I and I+II are hard to tell apart on a small screen through monitors)
  local ch = math.floor(self.v["ockm-"..part.."-chorus"] or 0)
  add{ kind="choice", x=x, y=466, w=tw, h=40, small=true, accent=true, sel=(ch > 0), label=(ch > 0) and "chorus on" or "chorus off",
       tap=function() self:send("ockm-"..part.."-chorus", (ch > 0) and 0 or 2) end }
  -- movement (v1.03): a sine on the first knob (cutoff or brightness), every bar, 2 bars or 4 bars, and how deep
  local key = function(k) return "ockm-"..part.."-lfo-"..k end
  local rate = math.floor(self.v[key("rate")] or 4)
  local lw = (rw - 12) / 3
  self:group(add, rx, 514, rw, 34)
  add{ kind="text", x=rx + 8, y=525, w=lw - 8, h=12, size=11, label="movement on " .. (kn[1] or "the sound") }
  add{ kind="btn", x=rx + (lw + 6), y=514, w=lw, h=34, small=true, label="every " .. (LFO_RATES[rate + 1] or "bar"),
       tap=function() self:send(key("rate"), (rate >= 4 and rate < 6) and (rate + 1) or 4) end }
  add{ kind="hbar", x=rx + 2 * (lw + 6), y=514, w=lw, h=34, hook=key("depth"), lo=0, hi=1, label="depth", bold=true }
  if part == "chord" then
    local vo = math.floor(self.v["ockm-chord-voicing"] or 0)
    local cw = (rw - 30) / 6
    -- v1.20: voicing is one button (close, open, wide, round again), to make room for the hands
    add{ kind="btn", x=rx, y=558, w=cw, h=34, small=true, label=VOICINGS[vo + 1] or "close", tap=function() self:send("ockm-chord-voicing", (vo + 1) % 3) end }
    -- smooth: every chord at about the same height (moved here from the left in v0.90)
    add{ kind="choice", x=rx + (cw + 6), y=558, w=cw, h=34, label="smooth", accent=true, small=true, sel=(self.v["ockm-chord-smooth"] or 1) > 0,
         tap=function() self:send("ockm-chord-smooth", ((self.v["ockm-chord-smooth"] or 1) > 0) and 0 or 1) end }
    -- drift (v1.01): every second time round, chords built from the key sit an inversion higher
    local dr = (self.v["ockm-chord-drift"] or 0) > 0
    add{ kind="choice", x=rx + 2 * (cw + 6), y=558, w=cw, h=34, label="drift", accent=true, small=true, sel=dr,
         tap=function() self:send("ockm-chord-drift", dr and 0 or 1) end }
    local ce = math.floor(self.v["ockm-chord-engine"] or 0)
    add{ kind="hbar", x=rx + 3 * (cw + 6), y=558, w=cw, h=34, hook="ockm-chord-strum", lo=0, hi=(ce == 3 or ce == 4) and 1 or 0.5, label="strum", bold=true }
    -- v1.20 two hands (organ, piano, Rhodes): the left hand plays the root low down in one of five patterns
    if TWO_HANDS[ce] then
      local hd = math.floor(self.v["ockm-chord-hands"] or 0)
      local last = (hd > 0) and hd or (self.lh_last or 1)
      add{ kind="choice", x=rx + 4 * (cw + 6), y=558, w=cw, h=34, label="two hands", accent=true, small=true, sel=(hd > 0),
           tap=function() if hd > 0 then self.lh_last = hd; self:send("ockm-chord-hands", 0) else self:send("ockm-chord-hands", last) end end }
      add{ kind="btn", x=rx + 5 * (cw + 6), y=558, w=cw, h=34, small=true, label=(LH_PATTERNS[last] or "anchor"), quiet=(hd == 0),
           tap=function() self:send("ockm-chord-hands", last % #LH_PATTERNS + 1) end }
    end
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
-- hidden (v0.84): entries the arrows step over (kept in the list so their numbers, and saved projects, don't change)
function ui:stepper(add, x, y, w, h, list, hook, after, hidden, order)
  local v = math.floor(self.v[hook] or 0)
  local vis = {}
  if order then   -- v1.04: shown in this order (indices), the rest hidden unless it's the current one
    local seen = false
    for _, i in ipairs(order) do vis[#vis + 1] = i; if i == v then seen = true end end
    if not seen then table.insert(vis, 1, v) end
  else
    for i = 0, #list - 1 do if not (hidden and hidden[i]) or i == v then vis[#vis + 1] = i end end
  end
  local pos = 1
  for k, i in ipairs(vis) do if i == v then pos = k end end
  local prev, nxt = vis[pos - 1], vis[pos + 1]
  add{ kind="arrow", x=x, y=y, w=44, h=h, dir=-1, on=(prev ~= nil), tap=function() if prev then self:send(hook, prev); if after then after(prev) end end end }
  local item = list[v + 1] or { "" }
  add{ kind="preset", x=x + 50, y=y, w=w - 100, h=h, num=pos, label=type(item) == "table" and item[1] or item,
       sub=type(item) == "table" and item[2] or nil, sel=true }
  add{ kind="arrow", x=x + w - 44, y=y, w=44, h=h, dir=1, on=(nxt ~= nil), tap=function() if nxt then self:send(hook, nxt); if after then after(nxt) end end end }
end
-- v0.84 pruning: the lead's rhythms that copy the bass's (gallop, acid classic, sparse dub, tech bounce, acid 16ths, trip hop),
-- and the three older melody shapes the motifs replaced
local HIDE_LEAD_RHY = { [2]=true, [3]=true, [4]=true, [5]=true, [6]=true, [7]=true }
local HIDE_NOTES = { [12]=true, [13]=true, [14]=true }

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
  local ct = math.floor(self.v["ockm-chord-type"] or 0)
  local ty = CHORD_TYPES[ct + 1]
  local rn = ROMAN[d + 1]
  if third == 4 then rn = string.upper(rn) end
  if ty and ty.k == 1 then
    -- a fixed shape: its own quality whatever the key says (the turnaround makes a minor shape major)
    local nm = ty.name
    if turn and nm:sub(1, 1) == "m" and nm:sub(1, 3) ~= "maj" then nm = nm:sub(2) end
    if nm == "4ths" then nm = "sus" end
    return NOTES[((root + r) % 12) + 1] .. nm, rn
  end
  local q = (third == 3) and ((fifth == 6) and "dim" or "m") or ""
  local ext = ({ [1] = "7", [6] = "9", [7] = "11" })[ct] or ""
  if q == "dim" and ext ~= "" then q = "m" end
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

-- styles (v0.84: house through to techno). One tap sets the tempo, swing, groove, key and scale, the kick and clap
-- character, which parts are in, what each plays and on which sound, the progression and colour, sends, sidechain.
-- A value can be a list: each tap rolls any of them (v0.97), so every take stays inside the style; classic plays the first.
-- drums: per voice { tune, decay, drive, character }. Parts: false = out of the pattern. Bass move 0 pedal, 1 follows, 2 walks.
-- Numbers: roots 0 C .. 9 A; scales 0 minor 1 major 2 dorian 3 phrygian; grooves, progressions, rhythms and riffs as listed
-- in the presets block. Knobs (k) only go with the first engine in the list.
local STYLES = {
  { "deep house", second={ 0, 1 }, vary={ 1, 2 }, drift=1, evolve=1, rate={ 1, 1, 2 }, kit="909-long", punch=0.4, bpm=122, swing=58, groove={ 2, 16, 17, 21 }, root={ 5, 2, 7, 0 }, scale={ 2, 0 }, prog={ 13, 1, 3, 15, 6 }, type={ 8, 6, 9 },
    drums={ kick={ -1, 110, 0.1, 0 }, clap={ 0, 100, 0, 0.1 } },
    bass={ engine={ 5, 1 }, rhythm={ 9, 3, 1 }, notes={ 2, 0, 6 }, move=1, k={ 0.35, 0.2, 0.4, 0.45 } },
    chord={ engine={ 4, 3 }, rhythm={ 3, 0, 8, 11 }, verb=0.25, delay=0.12, chorus=2, strum=0.12, hands={ 1, 5 } },
    lead=false },
  { "chicago", vary=2, rate={ 1, 0 }, push=1, kit="909", punch=0.6, bpm=125, swing=62, groove={ 13, 14, 22, 1 }, root={ 7, 0, 9, 2 }, scale={ 0, 2 }, prog={ 12, 1, 0, 3 }, type={ 10, 8 },
    drums={ kick={ 0, 90, 0.2, 0.3 }, clap={ 0, 100, 0, 0.2 } },
    bass={ engine={ 5, 0 }, rhythm={ 1, 0, 4 }, notes={ 1, 2, 3 }, move=1 },
    chord={ engine={ 1, 3 }, rhythm={ 4, 2, 5 }, verb=0.12, chorus=2 },
    lead=false },
  { "classic house", second={ 2, 0 }, vary={ 2, 1 }, rate={ 1, 0 }, push=1, kit="909", punch=0.5, bpm=124, swing=56, groove={ 1, 0, 21, 16 }, root={ 0, 7, 2, 5 }, scale={ 1, 4, 0 }, prog={ 16, 5, 3, 18, 10 }, type={ 6, 1 },
    drums={ kick={ 0, 100, 0.1, 0.2 }, clap={ 0, 100, 0, 0 } },
    bass={ engine={ 5, 2 }, rhythm={ 0, 1, 18, 9, 4 }, notes={ 2, 1, 0 }, move=1, sidechain=0.2 },
    chord={ engine={ 3, 1 }, rhythm={ 0, 2, 5, 10 }, verb=0.15, delay=0.1, strum=0.1, hands={ 4, 1, 2 } },
    lead={ engine={ 4, 2 }, rhythm={ 10, 11, 8 }, notes={ 15, 16, 8 }, outside=0.4, verb=0.15, delay=0.2, chorus=2 } },
  -- v1.07: filter house (French house): the house groove, two chords changing every half bar, 8ths chords pumping hard
  -- under the kick, the bass on octaves ringing out, no lead
  { "filter house", kit="909", punch=0.6, bpm=124, swing=54, groove={ 1, 21, 0 }, root={ 9, 2, 5, 7 }, scale={ 0, 2 }, prog={ 12, 1 }, rate=0,
    type={ 1, 10 }, vary=2,
    drums={ kick={ 0, 100, 0.2, 0.3 }, clap={ 0, 90, 0, 0 } },
    bass={ engine={ 5, 2 }, rhythm={ 4, 1 }, notes=1, move=1, k={ 0.45, 0.3, 0.5, 0.7 }, sidechain=0.3 },
    chord={ engine={ 3, 1 }, rhythm=9, sidechain=0.75, verb=0.15, delay=0.08, hands=1 },
    lead=false },
  -- v0.90: Italian piano house (Black Box, Cappella, late 80s Italy): an M1-style piano playing open triads in a major key
  -- on the big four-chord turn, a riff that pushes ahead of the beat, the M1 organ bass bouncing on the offbeats
  { "italo piano", second={ 1, 0 }, vary=1, push=1, kit="909", punch=0.5, bpm=124, swing=55, groove={ 1, 21, 0, 16 }, root={ 0, 7, 5, 2 }, scale={ 1, 4 }, prog={ 10, 11, 18, 16 }, type={ 0, 1 },
    drums={ kick={ 0, 100, 0.1, 0.2 }, clap={ 0, 100, 0, 0.1 } },
    bass={ engine={ 6, 5 }, rhythm={ 0, 4, 1 }, notes={ 0, 1 }, move=1 },
    chord={ engine=3, rhythm={ 10, 5, 0 }, verb=0.2, delay=0.08, voicing=1, strum=0.04, hands={ 2, 3 } },
    lead=false },
  { "nu disco", vary=2, evolve=1, push=1, kit="808", punch=0.4, bpm=118, swing=54, groove={ 23, 15, 21 }, root={ 2, 9, 4 }, scale={ 2, 4, 0 }, prog={ 15, 12, 1, 5 }, type={ 12, 6 },
    drums={ kick={ 0, 90, 0, 0.1 }, clap={ 0, 90, 0, 0.2 } },
    bass={ engine={ 5, 2 }, rhythm={ 4, 1, 9 }, notes={ 1, 2 }, move=1, k={ 0.5, 0.3, 0.5, 0.7 } },
    chord={ engine={ 0, 3 }, rhythm={ 2, 9, 0, 5 }, verb=0.2, chorus=2, k={ 0.5, 0.5, 0.7, 0.6 } },
    lead={ engine={ 4, 2 }, chorus=2, rhythm={ 11, 10 }, notes={ 16, 15, 18 }, outside=0.45, delay=0.25 } },
  { "tech house", vary=1, kit="909", punch=0.7, bpm=126, swing=54, groove={ 3, 24, 21 }, root={ 9, 7, 2, 4 }, scale={ 0, 2 }, prog={ 0, 12, 1 }, type={ 10, 11 },
    drums={ kick={ 0, 90, 0.3, 0.4 }, clap={ 0, 80, 0, -0.5 } },
    bass={ engine={ 5, 2, 6 }, rhythm={ 14, 2, 9 }, notes={ 0, 3, 5 }, move=1, sidechain=0.3, k={ 0.35, 0.3, 0.5, 0.35 } },
    chord={ engine={ 6, 0, 1 }, rhythm={ 5, 3, 8 }, delay=0.25 },
    lead={ engine=6, rhythm={ 3, 15, 8 }, notes={ 0, 1, 16 }, octave=0, outside=0.2, delay=0.2, lfo={ { 6, 7 }, 0.3 } } },
  { "minimal", vary=1, evolve=1, kit="808", punch=0.5, bpm=125, swing=55, groove={ 4, 28, 26 }, root={ 4, 2, 9 }, scale={ 0, 3, 2 }, prog=0, type={ 11, 10 },
    drums={ kick={ 1, 70, 0.1, 0.3 }, clap={ 2, 60, 0, -0.6 } },
    bass={ engine={ 1, 5, 7 }, rhythm={ 6, 14, 5 }, notes={ 0, 6 }, move=0, lfo={ 7, 0.2 } },
    chord={ engine=0, rhythm={ 3, 0, 2 }, delay=0.4 },
    lead={ engine={ 4, 2 }, rhythm={ 9, 12 }, notes={ 0, 9, 1 }, rests=0.2, outside=0.3, verb=0.1, delay=0.35 } },
  { "progressive", second={ 2, 0 }, vary=1, drift=1, evolve=1, rate={ 2, 1 }, kit="909-long", punch=0.5, bpm=122, swing=50, groove={ 0, 2, 24 }, root={ 2, 9, 4, 7 }, scale={ 0, 5 }, prog={ 3, 13, 6, 7, 5 }, type={ 6, 7 },
    drums={ kick={ -1, 120, 0.2, 0.2 }, clap={ 0, 110, 0, 0.2 } },
    bass={ engine={ 5, 3 }, rhythm={ 2, 1, 4 }, notes={ 0, 2 }, move=1, sidechain=0.3 },
    chord={ engine=0, rhythm={ 0, 1, 9 }, verb=0.35, sidechain=0.4, chorus=2, k={ 0.45, 0.5, 0.8, 0.7 } },
    lead={ engine={ 5, 4, 2 }, rhythm={ 13, 10, 14 }, notes={ 18, 8, 9 }, rep={ 1, 0 }, outside=0.3, verb=0.2, delay=0.3 } },
  -- v1.08: trance: 138, the four-floor kick and rolling offbeat bass, minor-key progressions over two bars a chord,
  -- gated 8ths chords on the poly with the string chorus pumping under the kick, a supersaw arp on top
  { "trance", second={ 0, 2 }, evolve=1, rate={ 2, 1 }, kit="909", punch=0.6, bpm=138, swing=50, groove={ 0, 24 }, root={ 9, 2, 5, 7 }, scale=0, prog={ 5, 6, 7 }, type={ 0, 1 },
    drums={ kick={ -1, 120, 0.3, 0.3 }, clap={ 0, 90, 0.1, 0 } },
    bass={ engine={ 5, 3 }, rhythm={ 0, 1 }, notes=0, move=1, sidechain=0.5, k={ 0.4, 0.3, 0.4, 0.3 } },
    chord={ engine=0, rhythm={ 9, 0 }, verb=0.35, delay=0.25, sidechain=0.6, chorus=2, k={ 0.6, 0.7, 0.0, 0.3 } },
    lead={ engine=5, rhythm={ 13, 10 }, notes={ 18, 8, 9 }, verb=0.3, delay=0.35 } },
  { "dub techno", vary=0, evolve=1, kit="909-long", punch=0.4, bpm=120, swing=52, groove={ 6, 28, 4 }, root={ 5, 7, 9 }, scale={ 0, 2 }, prog={ 2, 0, 12 }, type={ 10, 8, 11 },
    drums={ kick={ -1, 130, 0.2, 0 }, clap={ 0, 100, 0, 0.3 } },
    bass={ engine=1, rhythm={ 5, 6, 0 }, notes={ 0, 6 }, move=1 },
    chord={ engine=0, rhythm={ 3, 11, 2 }, verb=0.35, delay=0.55 },
    lead=false },
  { "detroit", vary=1, drift=1, kit="909", punch=0.6, bpm=128, swing=53, groove={ 25, 11, 26 }, root={ 0, 9, 5 }, scale={ 0, 2 }, prog={ 12, 1, 0 }, type={ 9, 8 },
    drums={ kick={ 0, 100, 0.3, 0.3 }, clap={ 0, 90, 0.1, 0.1 } },
    bass={ engine={ 2, 5 }, rhythm={ 1, 14, 2 }, notes={ 2, 0 }, move=1 },
    chord={ engine=0, rhythm={ 0, 1, 3 }, verb=0.3, chorus=2, k={ 0.5, 0.5, 0.7, 0.6 } },
    lead={ engine={ 2, 4 }, rhythm={ 14, 10 }, notes={ 18, 15 }, outside=0.4, delay=0.2 } },
  { "acid", kit="909", punch=0.7, bpm=130, swing=52, groove={ 29, 5, 14 }, root={ 9, 4, 7 }, scale={ 3, 0 }, prog=0, type=0,
    drums={ kick={ 0, 110, 0.4, 0.4 }, clap={ 0, 90, 0.1, -0.3 } },
    bass={ engine=0, rhythm={ 12, 2, 3 }, notes={ 3, 4 }, move=0, delay=0.15, slide=0.3 },
    chord=false, lead=false },
  { "peak time", vary=1, kit="909", punch=0.8, bpm=132, swing=50, groove={ 5, 26, 24 }, root={ 5, 4, 2 }, scale={ 3, 0 }, prog={ 0, 14 }, type={ 11, 10 },
    drums={ kick={ -2, 150, 0.5, 0.5 }, clap={ 0, 70, 0.2, -0.6 } },
    bass={ engine={ 5, 1 }, rhythm={ 2, 1, 4 }, notes={ 0, 1 }, move=0, sidechain=0.5, k={ 0.25, 0.2, 0.35, 0.3 } },
    chord={ engine=6, rhythm={ 8, 5 }, delay=0.35, sidechain=0.5, k={ 0.4, 0.65, 0.7, 0.25 } },
    lead={ engine={ 6, 3, 5 }, lfo={ { 7, 6 }, 0.3 }, rhythm={ 15, 0, 1 }, notes={ 0, 1 }, outside=0.1, delay=0.2 } },
  { "hard techno", kit="909", punch=1.0, bpm=140, swing=50, groove={ 27, 26, 37 }, root={ 2, 6, 1 }, scale={ 3, 0 }, prog=0, type=0,
    drums={ kick={ -3, 170, 0.8, 0.8 }, clap={ 0, 90, 0.4, -0.3 } },
    bass={ engine={ 1, 3 }, rhythm={ 2, 1, 3 }, notes={ 0, 1 }, move=0, sidechain=0.6, k={ 0.4, 0.8, 0.3, 0.4 } },
    chord={ engine=6, rhythm={ 8, 5 }, delay=0.45, verb=0.15, sidechain=0.6, k={ 0.35, 0.75, 0.9, 0.2 } },
    lead={ engine={ 6, 4, 5 }, lfo={ 7, 0.35 }, rhythm={ 15, 1 }, notes={ 0, 1 }, outside=0.8, delay=0.3 } },
}
-- ------------------------------------------------------------------ evolve (v1.00)
-- An ongoing mutate. At the start of every phrase one ticked part steps to a variation, in turn: bass, lead, chords,
-- drums. Each part comes home: gentle plays A B A C A B A D (every other change is the original), lively A B C D. A
-- variation is a neighbour of the original: the bass and lead mutate seed, the chords' rhythm and the drums' groove move
-- to the next choice in the lit style's lists. Parts that are yours are never touched, nor are engines, knobs or the
-- progression. keep makes what's playing the new original; the part tabs say where each part is
local EVO_ORDER = { { "bass", 2 }, { "lead", 4 }, { "chord", 8 }, { "drum", 1 } }
local EVO_SEQ = { { 1, 0, 2, 0, 1, 0, 3, 0 }, { 1, 2, 3, 0 } }   -- gentle, lively: the offsets from home, in turn
local EVO_NAMES = { [0] = "A (home)", "B", "C", "D" }
-- the part's value now, and how to set it: seed (bass, lead), chord rhythm or groove (from the style's own lists)
function ui:evo_value(p)
  if p == "bass" or p == "lead" then return math.floor(self.v["ockm-"..p.."-seed"] or 0) end
  if p == "chord" then return math.floor(self.v["ockm-chord-rhythm"] or 0) end
  return math.floor(self.v["ockm-drum-groove"] or -1)
end
function ui:evo_choices(p)
  local st = STYLES[math.floor(self.v["ockm-style"] or -1) + 1]
  if not st then return nil end
  local l = (p == "chord") and (st.chord and st.chord.rhythm) or (p == "drum") and st.groove or nil
  if type(l) ~= "table" or #l < 2 then return nil end
  return l
end
function ui:evo_can(p)
  if p == "drum" then return (self.v["ockm-drums-on"] or 1) > 0 and self:evo_value("drum") >= 0 and self:evo_choices("drum") ~= nil end
  if (self.v["ockm-"..p.."-on"] or 1) == 0 or self:part_yours(p) then return false end
  if p == "chord" then return self:evo_choices("chord") ~= nil end
  return true
end
function ui:evo_set(p, off)
  local e = self.evo
  local home = e.home[p]
  if home == nil then return end
  if p == "bass" or p == "lead" then
    self:send("ockm-"..p.."-seed", home + off)
  else
    local l = self:evo_choices(p)
    if not l then return end
    local pos = 1
    for i, x in ipairs(l) do if x == home then pos = i end end
    local val = l[((pos - 1 + off) % #l) + 1]
    if p == "chord" then self:send("ockm-chord-rhythm", val) else self:send("ockm-drum-groove", val) end
  end
  e.off[p] = off
end
-- start (or restart) from what's playing now: that's home
function ui:evo_reset()
  self.evo = { home = {}, off = {}, k = {}, turn = 0, bar = 0 }
  for _, o in ipairs(EVO_ORDER) do self.evo.home[o[1]] = self:evo_value(o[1]); self.evo.off[o[1]] = 0; self.evo.k[o[1]] = 0 end
end
function ui:evo_bar()
  local n = math.floor(self.v["ockm-evolve-every"] or 0)
  if n <= 0 or self.playing == 0 then return end
  if not self.evo then self:evo_reset() end
  local e = self.evo
  e.bar = e.bar + 1
  if e.bar <= 1 or (e.bar - 1) % n ~= 0 then return end   -- bar 1 is where play started: phrases start at 1, 1+n, 1+2n
  local mask = math.floor(self.v["ockm-evolve-parts"] or 15)
  local live = {}
  for _, o in ipairs(EVO_ORDER) do
    if math.floor(mask / o[2]) % 2 == 1 and self:evo_can(o[1]) then live[#live + 1] = o[1] end
  end
  if #live == 0 then return end
  local p = live[(e.turn % #live) + 1]
  e.turn = e.turn + 1
  -- a part that moved by hand since its last turn starts again from where it is now
  local expect = e.home[p]
  if p == "bass" or p == "lead" then expect = (e.home[p] or 0) + (e.off[p] or 0) end
  if e.home[p] == nil or (p ~= "chord" and p ~= "drum" and self:evo_value(p) ~= expect) then
    e.home[p] = self:evo_value(p); e.off[p] = 0; e.k[p] = 0
  end
  local seq = EVO_SEQ[math.floor(self.v["ockm-evolve-mode"] or 1)] or EVO_SEQ[1]
  e.k[p] = (e.k[p] or 0) + 1
  self:evo_set(p, seq[((e.k[p] - 1) % #seq) + 1])
  self:dirty()
end
-- keep: what's playing becomes the new original for every part
function ui:evo_keep()
  self:evo_reset()
  self:say("kept: this is the new original")
end
-- where a part is, for its tab: "variation B, home in 2 phrases"
function ui:evo_status(p)
  local e = self.evo
  if not e or math.floor(self.v["ockm-evolve-every"] or 0) == 0 then return nil end
  local off = e.off[p] or 0
  local seq = EVO_SEQ[math.floor(self.v["ockm-evolve-mode"] or 1)] or EVO_SEQ[1]
  local mask = math.floor(self.v["ockm-evolve-parts"] or 15)
  local nlive = 0
  for _, o in ipairs(EVO_ORDER) do if math.floor(mask / o[2]) % 2 == 1 and self:evo_can(o[1]) then nlive = nlive + 1 end end
  if nlive == 0 then return nil end
  if off == 0 then return "evolving: variation A, the original" end
  local turns = 0
  for j = 1, #seq do turns = j; if seq[((e.k[p] or 0) + j - 1) % #seq + 1] == 0 then break end end
  local ph = turns * nlive
  return "evolving: variation " .. (EVO_NAMES[off] or "?") .. ", home in about " .. ph .. (ph == 1 and " phrase" or " phrases")
end

-- the phrase (v0.85): one length, set on the builder, for everything that happens at the end of a phrase. The engine still
-- counts with ockm-fill-every (the drum fill) and ockm-turn-every (the turnaround); the phrase sets both, and each part's
-- switch decides whether it does its thing. Both count bars from play, on the same counter
function ui:phrase()
  local f, t = math.floor(self.v["ockm-fill-every"] or 0), math.floor(self.v["ockm-turn-every"] or 0)
  local e = math.floor(self.v["ockm-evolve-every"] or 0)
  if f > 0 then return f end
  if t > 0 then return t end
  if e > 0 then return e end
  return 0
end
function ui:set_phrase(n)
  local fill_on = (self.v["ockm-fill-every"] or 0) > 0
  local turn_on = (self.v["ockm-turn-every"] or 0) > 0
  if self:phrase() == 0 then fill_on = true; turn_on = self.turn_wanted or false end   -- from off: fills on, the turnaround as you left it
  self:send("ockm-fill-every", (n > 0 and fill_on) and n or 0)
  self:send("ockm-turn-every", (n > 0 and turn_on) and n or 0)
  if (self.v["ockm-evolve-every"] or 0) > 0 or (n == 0) then self:send("ockm-evolve-every", n) end
  self.last_phrase = (n > 0) and n or self.last_phrase
end
-- switch one end-of-phrase move on or off (the phrase comes on at its last length if it was off)
function ui:phrase_move(key, on)
  local n = self:phrase()
  if n == 0 then n = self.last_phrase or 8 end
  if key == "ockm-turn-every" then self.turn_wanted = on end
  self:send(key, on and n or 0)
end
function ui:layout_compose(add)
  -- style: one tap sets the lot
  add{ kind="text", x=16, y=114, w=W - 32, h=12, size=10,
       label="style: a fresh take every tap (tempo, key, groove, drums, sounds, parts), always in the style. Classic is the canonical one. Undo puts it back" }
  local per = math.ceil(#STYLES / 2)
  local SHW = 96   -- the shuffle button, right of the chips
  local stw = (W - 32 - SHW - 6 - (per - 1) * 4) / per
  add{ kind="btn", x=W - 16 - SHW, y=128, w=SHW, h=28, accent=true, small=true, label="shuffle", tap=function() self:shuffle_style() end }
  add{ kind="btn", x=W - 16 - SHW, y=160, w=SHW, h=28, small=true, label="classic", tap=function() self:classic_style() end }
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
  local eng = function(part) local e = engines_of(part); return eng_label(e[(math.floor(self.v["ockm-"..part.."-engine"] or 0)) + 1] or "") end
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
  self:stepper(add, 16, 312, 236, 66, PROGS, "ockm-chord-prog", function() self.ranking = nil end, nil, PROG_ORDER)
  -- v0.99: how fast the chords change (half a bar, a bar, two bars per chord), and push (each change an eighth early)
  local rate = math.floor(self.v["ockm-chord-rate"] or 1)
  add{ kind="btn", x=258, y=312, w=88, h=31, small=true, label=({ "half bar", "a bar each", "two bars" })[rate + 1] or "a bar each",
       tap=function() self:send("ockm-chord-rate", (rate + 1) % 3); self.ranking = nil end }
  local push = (self.v["ockm-chord-push"] or 0) > 0
  add{ kind="choice", x=258, y=347, w=88, h=31, small=true, accent=true, sel=push, label="push",
       tap=function() self:send("ockm-chord-push", push and 0 or 1) end }
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
  local te = math.floor(self.v["ockm-turn-every"] or 0)
  local ph = self:phrase()
  add{ kind="text", x=396, y=391, w=50, h=12, label="phrase", size=10 }
  add{ kind="text", x=396, y=404, w=50, h=12, label="(bars)", size=9 }
  for i, e in ipairs({ 0, 4, 8, 16 }) do
    add{ kind="choice", x=448 + (i - 1) * 56, y=388, w=52, h=28, small=true, sel=(ph == e), label=(e == 0) and "off" or tostring(e),
         tap=function() self:set_phrase(e) end }
  end
  local fon, ton = (self.v["ockm-fill-every"] or 0) > 0, te > 0
  add{ kind="text", x=676, y=380, w=268, h=10, label="at the end of each phrase:                       all synths:", size=9 }
  add{ kind="choice", x=676, y=393, w=86, h=26, small=true, accent=true, sel=fon, label="drum fill",
       tap=function() self:phrase_move("ockm-fill-every", not fon) end }
  -- v1.04 second half: the last bar of each phrase stays (same), turns to V (turnaround) or climbs to VII (climb). Tap to step
  local tto = math.floor(self.v["ockm-turn-to"] or 4)
  local sh = ton and ((tto == 6) and 2 or 1) or 0
  add{ kind="choice", x=767, y=393, w=86, h=26, small=true, accent=true, sel=ton, label=({ "end: same", "turnaround", "climb" })[sh + 1],
       tap=function()
         local nx = (sh + 1) % 3
         if nx > 0 then self:send("ockm-turn-to", (nx == 2) and 6 or 4) end
         self:phrase_move("ockm-turn-every", nx > 0)
       end }
  -- v1.03: half-time for the bass, lead and chords together (each tab still has its own)
  local hon = false
  for _, sp in ipairs(SYNTHS) do if (self.v["ockm-"..sp.."-half"] or 0) > 0 then hon = true end end
  add{ kind="choice", x=858, y=393, w=86, h=26, small=true, accent=true, sel=hon, label="half-time",
       tap=function() for _, sp in ipairs(SYNTHS) do self:send("ockm-"..sp.."-half", hon and 0 or 1) end end }
  -- the map, bar by bar
  local shape0 = PROG_SHAPES[(math.floor(self.v["ockm-chord-prog"] or 0)) + 1] or { { 0, 16 } }
  local rf = ({ [0] = 0.5, [1] = 1, [2] = 2 })[math.floor(self.v["ockm-chord-rate"] or 1)] or 1
  local shape = {}
  for i, seg in ipairs(shape0) do shape[i] = { seg[1], seg[2] * rf } end
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
  -- v1.00 evolve: off, gentle, lively, and which parts it moves
  local ev = math.floor(self.v["ockm-evolve-every"] or 0)
  local em = math.floor(self.v["ockm-evolve-mode"] or 1)
  local mask = math.floor(self.v["ockm-evolve-parts"] or 15)
  add{ kind="text", x=16, y=433, w=60, h=12, label="evolve", size=10 }
  for i, o in ipairs({ { 0, "off" }, { 1, "gentle" }, { 2, "lively" } }) do
    local sel = (o[1] == 0 and ev == 0) or (o[1] > 0 and ev > 0 and em == o[1])
    add{ kind="choice", x=70 + (i - 1) * 84, y=424, w=80, h=28, small=true, sel=sel, label=o[2], tap=function()
      if o[1] == 0 then self:send("ockm-evolve-every", 0) else
        local n = self:phrase(); if n == 0 then n = self.last_phrase or 8; self:set_phrase(n) end
        self:send("ockm-evolve-mode", o[1]); self:send("ockm-evolve-every", n); self.evo = nil
      end
    end }
  end
  for i, o in ipairs({ { "drums", 1 }, { "bass", 2 }, { "lead", 4 }, { "chords", 8 } }) do
    local on = math.floor(mask / o[2]) % 2 == 1
    add{ kind="choice", x=330 + (i - 1) * 76, y=424, w=72, h=28, small=true, accent=true, sel=on and ev > 0, label=o[1],
         tap=function() self:send("ockm-evolve-parts", on and (mask - o[2]) or (mask + o[2])) end }
  end
  add{ kind="text", x=640, y=433, w=W - 656, h=12, size=9,
       label=(ev > 0) and ("one part a phrase, in turn; " .. ((em == 2) and "home every fourth" or "home every other") .. ". Yours are left alone")
             or "every phrase, one part moves to a variation and comes back" }
  add{ kind="text", x=16, y=458, w=W - 32, h=12, size=10,
       label="the map, bar by bar (" .. key .. ")" .. ((te > 0) and ("   " .. ((math.floor(self.v["ockm-turn-to"] or 4) == 6) and ("climb: the last bar of every " .. te .. " goes to " .. self:chord_name(6))
                                                                                          or ("turnaround: the last bar of every " .. te .. " goes to " .. self:chord_name(4, true)))) or "") }
  local playing_bar = (self.playing ~= 0) and (math.floor((self.step or 0) % math.max(16, nb * 16) / 16) + 1) or nil
  local bw = (W - 32 - (nb - 1) * 6) / nb
  for i = 1, nb do
    local names, romans = {}, {}
    for _, c in ipairs(bars[i]) do names[#names + 1] = c.name; romans[#romans + 1] = c.roman end
    add{ kind="bar", x=16 + (i - 1) * (bw + 6), y=472, w=bw, h=114, n=i, label=table.concat(names, "  "), sub=table.concat(romans, " "),
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
    for _, pz in ipairs(PROG_ORDER) do
      local pi = pz + 1
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

-- a style's value: a list rolls one at random (the first is the classic pick)
local function spick(v, roll)
  if type(v) ~= "table" then return v end
  return roll and v[math.random(#v)] or v[1]
end
-- v0.97: tapping a style rolls a fresh combination from its lists every time, always inside the style; classic (or
-- apply_style(i, true)) plays the first of every list, the canonical version. Undo puts the previous one back
function ui:apply_style(i, classic)
  local shuf = not classic
  local st = STYLES[i]
  if not st then return end
  self:snapshot(st[1])
  self:send("ockm-bpm", st.bpm)
  self:send("ockm-drums-on", 1)
  self:send("ockm-drum-groove", spick(st.groove, shuf))   -- the groove sets its own swing: the style's comes after
  self:send("ockm-swing", st.swing)
  local sh = spick(st.second or 0, shuf)   -- v1.04 second half: 0 same, 1 turnaround (V), 2 climb (VII), on an 8-bar phrase
  if sh > 0 then
    local n = (self:phrase() > 0) and self:phrase() or 8
    self:send("ockm-turn-to", (sh == 2) and 6 or 4); self:send("ockm-turn-every", n)
    if (self.v["ockm-fill-every"] or 0) > 0 then self:send("ockm-fill-every", n) end
  else self:send("ockm-turn-every", 0) end
  self:send("ockm-drum-punch", st.punch or 0.5)
  local root, scale = spick(st.root, shuf), spick(st.scale, shuf)
  self:send("ockm-root", root); self:send("ockm-scale", scale)
  for slot = 1, #SLOTS do
    local nm, t = SLOTS[slot], self:voice_type(slot)
    local d = st.drums[t]
    local ks = st.kit and self:kit_sample(slot, st.kit)
    if ks then   -- the style's kit has this sound: play it at its full length, tuned as the style tunes that drum
      self:send("ockm-"..nm.."-sample", ks); self:send("ockm-"..nm.."-tune", d and d[1] or 0); self:send("ockm-"..nm.."-decay", 100)
      self:send("ockm-"..nm.."-tone", 0); self:send("ockm-"..nm.."-verb", 0); self:send("ockm-"..nm.."-delay", 0)
      d = nil
    elseif self:kit_of(slot) then   -- on a kit: back to the synth sound (your own samples stay)
      self:send("ockm-"..nm.."-sample", 0)
    end
    if d and math.floor(self.v["ockm-"..nm.."-sample"] or 0) == 0 and not self:current_preset(slot) then
      self:send("ockm-"..nm.."-tune", d[1]); self:send("ockm-"..nm.."-decay", d[2])
      self:send("ockm-"..nm.."-drive", d[3]); self:send("ockm-"..nm.."-labchar", d[4])
    end
    if d then self:send("ockm-"..nm.."-verb", 0); self:send("ockm-"..nm.."-delay", 0) end
  end
  -- the starting mix (a style sets the lot; undo puts your mix back)
  for slot = 1, #SLOTS do
    local nm = SLOTS[slot]
    self:send("ockm-"..nm.."-level", MIX_DRUM[math.floor(self.v["ockm-"..nm.."-sound"] or 0)] or 0.7)
  end
  for _, t in ipairs(SYNTHS) do self:send("ockm-"..t.."-level", MIX_SYNTH[t]) end
  local prog = spick(st.prog, shuf)
  self:send("ockm-chord-rate", spick(st.rate or 1, shuf)); self:send("ockm-chord-push", spick(st.push or 0, shuf))
  self:send("ockm-chord-vary", spick(st.vary or 0, shuf)); self:send("ockm-chord-drift", spick(st.drift or 0, shuf))
  local evm = spick(st.evolve or 0, shuf)   -- evolve: 0 off, 1 gentle, 2 lively (on the phrase, or 8 bars)
  if evm > 0 then self:send("ockm-evolve-mode", evm); self:send("ockm-evolve-every", (self:phrase() > 0) and self:phrase() or 8)
  else self:send("ockm-evolve-every", 0) end
  self:send("ockm-chord-prog", prog)
  self:send("ockm-chord-type", spick(st.type, shuf))
  local said = {}
  for _, part in ipairs({ "bass", "chord", "lead" }) do
    local ps = st[part]
    self:send("ockm-"..part.."-on", ps and 1 or 0)
    if ps then
      local eng = spick(ps.engine, shuf)
      local first = (type(ps.engine) == "table") and ps.engine[1] or ps.engine
      self:pick_engine(part, eng, (ps.k and eng == first) and ps.k or nil)
      self:send("ockm-"..part.."-rhythm", spick(ps.rhythm, shuf))
      if ps.notes and part == "bass" then
        local OLD2RIFF = { [0] = 0, [1] = 1, [2] = 2, [3] = 6, [4] = 5, [5] = 3, [6] = 4, [7] = 0, [8] = 7, [9] = 7 }
        self:send("ockm-bass-riff", OLD2RIFF[spick(ps.notes, shuf)] or 0)
        self:send("ockm-bass-slideamt", ps.slide or 0); self:send("ockm-bass-octave", ps.octave or 0)
      elseif ps.notes then self:send("ockm-"..part.."-notes", spick(ps.notes, shuf)) end
      if part == "lead" then
        self:send("ockm-lead-octave", spick(ps.octave or 0, shuf)); self:send("ockm-lead-repeat", spick(ps.rep or 0, shuf))
        self:send("ockm-lead-rests", ps.rests or 0)
      end
      if ps.move then self:set_bass_move(ps.move) end
      if ps.outside then self:send("ockm-lead-outside", ps.outside) end
      self:send("ockm-"..part.."-half", ps.half or 0)
      self:send("ockm-"..part.."-sidechain", ps.sidechain or 0)
      self:send("ockm-"..part.."-scshape", ps.shape or 1)
      self:send("ockm-"..part.."-verb", ps.verb or 0); self:send("ockm-"..part.."-delay", ps.delay or 0)
      self:send("ockm-"..part.."-chorus", ps.chorus or 0)
      local lf = ps.lfo   -- v1.08: a slow sweep on the cutoff (k1), e.g. { 7, 0.3 }: over 8 bars, 0.3 deep
      if lf then
        self:send("ockm-"..part.."-lfo-target", 1); self:send("ockm-"..part.."-lfo-shape", 0)
        self:send("ockm-"..part.."-lfo-rate", spick(lf[1], shuf)); self:send("ockm-"..part.."-lfo-depth", lf[2])
      else self:send("ockm-"..part.."-lfo-depth", 0) end
      if part == "chord" then   -- v0.90: every chord kept at the same height, voiced and rolled the style's way
        self:send("ockm-chord-smooth", 1); self:send("ockm-chord-voicing", ps.voicing or 0); self:send("ockm-chord-strum", ps.strum or 0)
        local hd = spick(ps.hands or 0, shuf)   -- v1.20: two hands on piano, organ and Rhodes
        self:send("ockm-chord-hands", hd)
        self:send("ockm-chord-lowcut", ps.lowcut or ((hd > 0) and 90 or 150))   -- the low end is the kick's and the bass's (the left hand's G2 needs a little)
      end
      if part ~= "chord" then
        self:send("ockm-"..part.."-seed", shuf and math.random(1, 60) or 0)   -- shuffle: a variation of the riff too
        self:send("ockm-"..part.."-mode", 0)   -- made for you again, so it follows the new style
      end
      local e = engines_of(part)
      said[#said + 1] = eng_label(e[eng + 1])
    end
  end
  self:send("ockm-style", i - 1)
  self.evo = nil   -- evolve starts again from this take
  local key = NOTES[root + 1] .. " " .. SCALE_NAMES[scale + 1]
  self:say_undo(st[1] .. (classic and " (classic): " or ": ") .. key .. ", " .. ((PROGS[prog + 1] or { "" })[1]) .. ", " .. table.concat(said, " / "))
end
-- shuffle: the style that's lit (or any style), rolled again; classic: the lit style's first pick of everything
function ui:shuffle_style()
  local cur = math.floor(self.v["ockm-style"] or -1) + 1
  if cur < 1 or cur > #STYLES then cur = math.random(#STYLES) end
  self:apply_style(cur)
end
function ui:classic_style()
  local cur = math.floor(self.v["ockm-style"] or -1) + 1
  if cur < 1 or cur > #STYLES then cur = 1 end
  self:apply_style(cur, true)
end

-- a part's settings on its own tab (v0.74): what it plays and how it sits on the harmony
local COLOURS = { { 0, "triads" }, { 1, "7ths" }, { 6, "9ths" }, { 7, "11ths" } }
-- v0.90 fixed shapes: one chord shape moved around with the progression (chord memory), not built from the key
local SHAPES = { { 8, "m9" }, { 9, "m11" }, { 10, "dub m7" }, { 11, "4ths" }, { 12, "maj9" } }
local MOVES = { { "pedal", "stays on the key" }, { "follows", "moves with the chords" }, { "walks", "steps into changes" } }
-- the lead's inside-to-outside slider (ockm-lead-outside 0-1): what each stretch of it adds
local function outside_zone(v)
  if v < 0.25 then return "chord notes" elseif v < 0.5 then return "passing notes" elseif v < 0.75 then return "colour: 7ths and 9ths" end
  return "outside: leaps and chromatic notes"
end
local SC_SHAPES = { "duck", "pump", "gate" }   -- ockm-<part>-scshape 0, 1, 2
-- a part's sidechain (v0.79 on the bass, v0.88 on all three): how far it dips on each kick, and how (duck, pump or gate),
-- with a picture of one beat
function ui:sidechain_row(add, p, ix, y, iw)
  local shk = "ockm-"..p.."-scshape"
  local shp = math.floor((self.v[shk] or 1) + 0.5)
  local bw, cw = math.floor(iw * 0.38), math.floor(iw * 0.13)
  add{ kind="hbar", x=ix, y=y, w=bw, h=30, hook="ockm-"..p.."-sidechain", lo=0, hi=1, label="sidechain", bold=true }
  for i, nm in ipairs(SC_SHAPES) do
    add{ kind="choice", x=ix + bw + 6 + (i - 1) * (cw + 4), y=y, w=cw, h=30, label=nm, small=true, sel=(shp == i - 1),
         tap=function() self:send(shk, i - 1) end }
  end
  local px = ix + bw + 6 + 3 * (cw + 4) + 2
  add{ kind="scpic", x=px, y=y, w=ix + iw - px, h=30, shape=shp, amt=self.v["ockm-"..p.."-sidechain"] or 0 }
end
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
    self:stepper(add, ix, 332, iw, 44, CHORD_RHY, "ockm-chord-rhythm", nil, HIDE_CHORD_RHY)
    add{ kind="text", x=ix, y=388, w=iw, h=12, label="chords: built from the key, or one shape moved around", size=10 }
    local ct = math.floor(self.v["ockm-chord-type"] or 0)
    local cw = (iw - 18) / 4
    for i, c in ipairs(COLOURS) do
      add{ kind="choice", x=ix + (i - 1) * (cw + 6), y=402, w=cw, h=36, label=c[2], small=true,
           sel=(ct == c[1]), tap=function() self:send("ockm-chord-type", c[1]) end }
    end
    local sw = (iw - 24) / 5
    for i, c in ipairs(SHAPES) do
      add{ kind="choice", x=ix + (i - 1) * (sw + 6), y=444, w=sw, h=36, label=c[2], small=true,
           sel=(ct == c[1]), tap=function() self:send("ockm-chord-type", c[1]) end }
    end
    self:sidechain_row(add, "chord", ix, 494, iw)
    if self:part_empty("chord") then
      add{ kind="btn", x=ix, y=532, w=iw, h=34, accent=true, label=START.chord, tap=function() self:start_part("chord") end }
    end
    if not self:part_empty("chord") then
      -- v1.01 vary: still (every bar the same), breathe (the last bar changes), move (bars alternate A B A B')
      local vy = math.floor(self.v["ockm-chord-vary"] or 0)
      add{ kind="text", x=ix, y=544, w=50, h=12, label="vary", size=10 }
      local vw = (iw - 50 - 12) / 3
      for i, nm in ipairs({ "still", "breathe", "move" }) do
        add{ kind="choice", x=ix + 50 + (i - 1) * (vw + 6), y=532, w=vw, h=34, small=true, sel=(vy == i - 1), label=nm,
             tap=function() self:send("ockm-chord-vary", i - 1); psend("ockm-chord-gen", "bang", {}) end }
      end
    end
    return
  end
  local notes = {}
  for i, nm in ipairs(MONO_NOTES) do notes[i] = { nm } end
  add{ kind="text", x=ix, y=318, w=half, h=12, label=(p == "bass") and "riff: which notes, in each chord" or "tune: the shape of the line", size=10 }
  if p == "bass" then
    -- v1.02: the bass's own eight riffs. A loop from before keeps the riff it had (shown by name) until you pick one
    local rf = math.floor(self.v["ockm-bass-riff"] or -1)
    if rf >= 0 then
      self:stepper(add, ix, 332, half, 44, BASS_RIFFS, "ockm-bass-riff")
    else
      add{ kind="arrow", x=ix, y=332, w=44, h=44, dir=-1, on=false }
      add{ kind="preset", x=ix + 50, y=332, w=half - 100, h=44, num="", label=(MONO_NOTES[math.floor(self.v["ockm-bass-notes"] or 0) + 1] or "root"),
           sub="as saved", sel=true }
      add{ kind="arrow", x=ix + half - 44, y=332, w=44, h=44, dir=1, on=true, tap=function() self:send("ockm-bass-riff", 0) end }
    end
  else
    for i, nm in pairs(LEAD_TUNE_NAME) do notes[i + 1] = { nm } end
    self:stepper(add, ix, 332, half, 44, notes, "ockm-"..p.."-notes", nil, nil, LEAD_TUNE_ORDER)
  end
  add{ kind="text", x=ix + half + 8, y=318, w=half, h=12, label="rhythm", size=10 }
  self:stepper(add, ix + half + 8, 332, half, 44, rhythms_for(p), "ockm-"..p.."-rhythm", function(v)
    -- the octave jump is a rhythm and a note pattern together: it brings the octaves notes with it
    if p == "bass" and (BASS_RHYTHMS[v + 1] or {})[1] == "octave" then self:send("ockm-bass-riff", 1) end
  end, nil, (p == "bass") and BASS_RHY_ORDER or LEAD_RHY_ORDER)
  local w3 = (iw - 12) / 3
  if p == "bass" then
    add{ kind="text", x=ix, y=386, w=iw, h=12, label="movement: how the riff follows the chords", size=10 }
    local m = self:bass_move()
    for i, mv in ipairs(MOVES) do
      add{ kind="choice", x=ix + (i - 1) * (w3 + 6), y=400, w=w3, h=38, label=mv[1], small=true, sel=(m == i - 1), tap=function() self:set_bass_move(i - 1) end }
    end
  else
    -- v0.81: one slider, inside to outside: how far the tune strays from the chords (it rewrites a line made for you)
    add{ kind="text", x=ix, y=386, w=iw, h=12, label="inside to outside: how far the tune strays from the chords", size=10 }
    add{ kind="hbar", x=ix, y=400, w=iw, h=40, hook="ockm-lead-outside", lo=0, hi=1, label="inside to outside", ends={ "inside", "outside" }, bold=true,
         valtext=function(v) return outside_zone(v) end }
  end
  -- sidechain: how far it dips each time the kick hits (the Perform pump does all the synths at once)
  self:sidechain_row(add, p, ix, 446, iw)
  -- v1.02: density, slide (the bass: how many notes glide into the next) and the octave switch
  local okey = "ockm-"..p.."-octave"
  local oc = math.floor(self.v[okey] or 0)
  if p == "bass" then
    local w3b = (iw - 12) / 3
    add{ kind="hbar", x=ix, y=482, w=w3b, h=30, hook="ockm-bass-density", lo=0, hi=2, label="density", bold=true }
    add{ kind="hbar", x=ix + w3b + 6, y=482, w=w3b, h=30, hook="ockm-bass-slideamt", lo=0, hi=1, label="slide", bold=true }
    add{ kind="choice", x=ix + 2 * (w3b + 6), y=482, w=w3b, h=30, small=true, accent=true, sel=(oc > 0), label=(oc > 0) and "high (mid bass)" or "low (sub)",
         tap=function() self:send(okey, (oc > 0) and 0 or 1) end }
  else
    -- v1.06: density thins the rhythm the same way every bar; rests skip a few notes, different in every bar
    local hw = (iw - 6) / 2
    add{ kind="hbar", x=ix, y=482, w=hw, h=30, hook="ockm-lead-density", lo=0, hi=2, label="density", bold=true }
    add{ kind="hbar", x=ix + hw + 6, y=482, w=hw, h=30, hook="ockm-lead-rests", lo=0, hi=1, label="rests", bold=true }
  end
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
  if p == "lead" then
    -- v1.06: where the tune lives (register) and how much bar 3 changes from bar 1 (repeat: tight is a hook, loose a solo)
    local w5 = (iw - 24) / 5
    for i, o in ipairs({ { -1, "low" }, { 0, "mid" }, { 1, "high" } }) do
      add{ kind="choice", x=ix + (i - 1) * (w5 + 6), y=558, w=w5, h=28, small=true, sel=(oc == o[1]), label=o[2], tap=function() self:send(okey, o[1]) end }
    end
    local rp = math.floor(self.v["ockm-lead-repeat"] or 0)
    for i, o in ipairs({ { 0, "tight" }, { 1, "loose" } }) do
      add{ kind="choice", x=ix + (i + 2) * (w5 + 6), y=558, w=w5, h=28, small=true, accent=true, sel=(rp == o[1]), label=o[2],
           tap=function() self:send("ockm-lead-repeat", o[1]) end }
    end
  else
    add{ kind="text", x=ix, y=564, w=iw, h=14, size=11,
         label=(self:part_yours(p) and "yours: you've edited it, so nothing rewrites it" or "made for you: it follows the harmony")
           .. ((seed > 0) and ("  ·  variation " .. seed) or "") }
  end
end

-- the harmony as a signature, so a part that's yours can tell when the chords have changed under it
function ui:harm_sig()
  return string.format("%d/%d/%d", math.floor(self.v["ockm-chord-prog"] or 0), math.floor(self.v["ockm-root"] or 9), math.floor(self.v["ockm-scale"] or 0))
end
-- the chord tones (pitch classes) under step i, from the chord part's roots and the chord colour
function ui:chord_pcs(i)
  local cl = self:plen("chord")
  local d = math.floor(self:get("ockm-pat-chord-deg", i % cl))
  local pcs = {}
  for _, n in ipairs(chord_voicing(d, math.floor(self.v["ockm-chord-type"] or 0), self:scale(), math.floor(self.v["ockm-root"] or 9), false, 0, false)) do
    pcs[n % 12] = true
  end
  -- a chord that leaves its root to the bass still counts the root as a chord note
  local sc, root = self:scale(), math.floor(self.v["ockm-root"] or 9)
  pcs[(root + sc[(((d % 7) + 7) % 7) + 1]) % 12] = true
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
              voicing = math.floor(self.v["ockm-chord-voicing"] or 0),
              hands = TWO_HANDS[math.floor(self.v["ockm-chord-engine"] or 0)] and math.floor(self.v["ockm-chord-hands"] or 0) or 0,
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
-- a chord's notes, worked out the way the chord sequencer does it (the same Lua: chord_voicing, in the presets block)
local function chord_notes(d, deg)
  local n = chord_voicing(deg, d.ctype, d.scale, d.root, d.smooth, d.voicing or 0, false)
  if (d.hands or 0) > 0 then n = right_hand(n, deg, d.scale, d.root) end
  return n
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
        -- v1.20: the left hand, on the same track, each note held until its next one
        if (d.hands or 0) > 0 then
          local hits, last = {}, nil
          for st = 0, d.len - 1 do
            local c = d.chord[st]
            local shape, sv = left_hand(d.hands, st, c.on, c.deg ~= last)
            last = c.deg
            if shape then hits[#hits + 1] = { st, left_notes(shape, c.deg, d.scale, d.root), sv } end
          end
          for k, h in ipairs(hits) do
            local nx = hits[k + 1] and hits[k + 1][1] or d.len
            for _, n in ipairs(h[2]) do note(tr.chord, 2, t0 + h[1] * Q, clamp(n, 0, 127), math.floor(h[3] * 127), math.min(16, nx - h[1]) * Q - 2) end
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
-- v1.10 every save is a variation: the version you had stays as it was, and you carry on in the new one
-- (velvet-heron, velvet-heron-v2, -v3...). A brand-new project's first save just saves it; nothing to save, nothing made
local function ockm_base(n) return (tostring(n):gsub("%-v%d+$", "")) end
local function ockm_ver(n) return tonumber(tostring(n):match("%-v(%d+)$")) or 1 end
function ui:save_variation()
  local cur = self.project or "default"
  if not self.unsaved then self:say("nothing new to save in " .. ockm_pretty(cur)); return end
  if cur == self.fresh then
    self.fresh = nil; psend("ockm-save", "bang", {}); self:var_stamp(cur)
    self:say("saved " .. ockm_pretty(cur) .. ": the loop and the kit"); return
  end
  local n
  if cur == "default" then n = self:new_name()
  else
    local base, top = ockm_base(cur), ockm_ver(cur)
    local taken = { [cur] = true }
    for _, q in ipairs(self.projects or {}) do
      taken[q] = true
      if ockm_base(q) == base then top = math.max(top, ockm_ver(q)) end
    end
    repeat top = top + 1; n = base .. "-v" .. top until not taken[n]
  end
  psend("ockm-project-saveas", "symbol", { n }); psend("ockm-project-list", "bang", {}); self:var_stamp(n)
  self:say("saved as " .. ockm_pretty(n) .. ". " .. ockm_pretty(cur):match("^[^·]+"):gsub("%s+$", "") .. " stays as it was")
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
    { "save a variation", function() self:save_variation() end },
    { "back to last save", function() psend("ockm-revert", "bang", {}); self:say("back to the last save of " .. ockm_pretty(cur)) end },
    { "save as a copy", function()
        local n = self:new_name(); psend("ockm-project-saveas", "symbol", { n }); psend("ockm-project-list", "bang", {})
        self:say("saved a copy as " .. ockm_pretty(n) .. ". You're now working in the copy") end },
    { "new blank project", function()
        local n = self:new_name(); self.exists = 1; self.new_pending = true; self.fresh = n; psend("ockm-project-new", "symbol", { n }); psend("ockm-project-list", "bang", {})
        self.pick = nil; self:say("new project: " .. ockm_pretty(n) .. ". The last one stays as you last saved it") end },
    { "export...", function() psend("ockm-usb-scan", "bang", {}); psend("ockm-exports-ask", "bang", {}); self.sheet = "export" end },
  }
  for i, a in ipairs(acts) do
    add{ kind="btn", x=16 + (i - 1) * (bw + 8), y=152, w=bw, h=52, label=a[1], accent=(i == 4 or i == 5), tap=a[2] }
  end
  -- every project, newest first, one tile each: its variations are in the row under the tiles
  local list = self.projects or {}
  local groups, order = {}, {}
  for _, n in ipairs(list) do
    local b = ockm_base(n)
    if not groups[b] then groups[b] = {}; order[#order + 1] = b end
    table.insert(groups[b], n)
  end
  for _, g in pairs(groups) do table.sort(g, function(a, b) return ockm_ver(a) < ockm_ver(b) end) end
  local cur_base = ockm_base(cur)
  local shown = self.pgroup or cur_base
  add{ kind="text", x=16, y=222, w=300, h=12, label="your projects (" .. #order .. ")", size=10 }
  local cols, rows = 4, 4
  local per = cols * rows
  local pages = math.max(1, math.ceil(#order / per))
  self.ppage = clamp(self.ppage or 0, 0, pages - 1)
  local cw = (W - 32 - (cols - 1) * 8) / cols
  for k = 1, per do
    local b = order[self.ppage * per + k]
    if not b then break end
    local g = groups[b]
    local col, row = (k - 1) % cols, math.floor((k - 1) / cols)
    local is_cur = (b == cur_base)
    local latest = g[#g]
    local lbl = ockm_pretty(b) .. (#g > 1 and ("  v" .. ockm_ver(latest)) or "") .. (is_cur and "  (open)" or "")
    add{ kind="choice", x=16 + col * (cw + 8), y=238 + row * 52, w=cw, h=46, small=true,
         label=lbl, sel=(b == shown),
         tap=function()
           self.confirm = nil; self.pgroup = b
           local want = is_cur and cur or latest
           self.pick = (want ~= cur) and want or nil
         end }
  end
  -- the variations of the project picked (or open), oldest to newest: the last 12
  local g = groups[shown]
  if g and #g > 1 then
    add{ kind="text", x=16, y=444, w=W - 32, h=12, label="variations of " .. ockm_pretty(shown):match("^[^·]+"):gsub("%s+$", "") .. ": each save keeps the one before", size=10 }
    add{ kind="btn", x=W - 16 - 150, y=460, w=150, h=30, small=true, accent=true, label="browse all " .. #g,
         tap=function() self.vbase = shown; self.vpage = 0; self.vcache = {}; self.vconfirm = nil; self.sheet = "variations" end }
    local first = math.max(1, #g - 9)
    local vw = (W - 32 - 156 - 9 * 6) / 10
    for i = first, #g do
      local n = g[i]
      add{ kind="choice", x=16 + (i - first) * (vw + 6), y=460, w=vw, h=30, small=true,
           label="v" .. ockm_ver(n) .. (n == cur and " open" or ""), sel=(self.pick == n) or (self.pick == nil and n == cur),
           tap=function() self.confirm = nil; self.pick = (n ~= cur) and n or nil end }
    end
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
    add{ kind="btn", x=16, y=y, w=w3, h=52, label="save a variation, then open", accent=true, tap=function()
      self:save_variation(); psend("ockm-project-open", "symbol", { p }); self.pick = nil; self:say("opened " .. ockm_pretty(p)) end }
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

-- ------------------------------------------------------------------ variation browser (v1.11)
-- Each variation folder can hold variation.txt (when it was saved, and whether to keep it through a tidy-up). The browser
-- reads each one's loop and project files for a one-line summary, and opens, keeps, exports or deletes it
function ui:proj_dir(n)
  if not self._loadpath or self._loadpath == "" then return nil end
  return self._loadpath .. "../projects/" .. n .. "/"
end
function ui:var_meta(n)
  local d = self:proj_dir(n); local f = d and io.open(d .. "variation.txt", "r")
  if not f then return {} end
  local src = f:read("a"); f:close()
  local fn = load(src, "variation", "t", {}); local ok, t = pcall(fn or function() end)
  return (ok and type(t) == "table") and t or {}
end
function ui:var_write(n, t)
  local d = self:proj_dir(n); local f = d and io.open(d .. "variation.txt", "w")
  if not f then return end
  f:write(string.format("return { saved = %d, keep = %s }\n", math.floor(t.saved or 0), t.keep and "true" or "false")); f:close()
end
function ui:var_stamp(n)
  local m = self:var_meta(n); m.saved = os.time(); self:var_write(n, m)
  if self.vcache then self.vcache[n] = nil end
end
local function read_kv(path, into)
  local f = path and io.open(path, "r")
  if not f then return into end
  for line in f:read("a"):gmatch("[^;]+") do
    local k, v = line:match("^%s*(ockm%-[%w%-]+)%s+([%-%d%.]+)")
    if k and into[k] == nil then into[k] = tonumber(v) end
  end
  f:close(); return into
end
function ui:var_info(n)
  self.vcache = self.vcache or {}
  if self.vcache[n] then return self.vcache[n] end
  local d = self:proj_dir(n)
  local kv = {}
  if d then read_kv(d .. "loop.txt", kv); read_kv(d .. "project.txt", kv) end
  local bits = {}
  local st = kv["ockm-style"]
  if st and st >= 0 and STYLES[st + 1] then bits[#bits + 1] = STYLES[st + 1][1] end
  if kv["ockm-bpm"] then bits[#bits + 1] = string.format("%d bpm", math.floor(kv["ockm-bpm"] + 0.5)) end
  if kv["ockm-root"] then bits[#bits + 1] = (NOTES[math.floor(kv["ockm-root"]) % 12 + 1] or "") .. " " .. (SCALE_NAMES[math.floor(kv["ockm-scale"] or 0) + 1] or "") end
  local pg = kv["ockm-chord-prog"]
  if pg and PROGS[math.floor(pg) + 1] then bits[#bits + 1] = PROGS[math.floor(pg) + 1][1] end
  local parts = {}
  for _, pr in ipairs({ { "ockm-drums-on", "drums" }, { "ockm-bass-on", "bass" }, { "ockm-chord-on", "chords" }, { "ockm-lead-on", "lead" } }) do
    if (kv[pr[1]] or 1) > 0 then parts[#parts + 1] = pr[2] end
  end
  bits[#bits + 1] = table.concat(parts, " + ")
  local m = self:var_meta(n)
  local info = { summary = table.concat(bits, " · "), saved = m.saved, keep = m.keep }
  self.vcache[n] = info
  return info
end
function ui:var_group(base)
  local g = {}
  for _, q in ipairs(self.projects or {}) do if ockm_base(q) == base then g[#g + 1] = q end end
  table.sort(g, function(a, b) return ockm_ver(a) > ockm_ver(b) end)   -- newest first
  return g
end
function ui:var_open(n, then_export)
  local cur = self.project or "default"
  if n ~= cur then
    if self.unsaved then self:save_variation() end
    psend("ockm-project-open", "symbol", { n })
  end
  self.pick = nil; self.vconfirm = nil
  if then_export then psend("ockm-usb-scan", "bang", {}); psend("ockm-exports-ask", "bang", {}); self.sheet = "export"
  else self.sheet = nil end
  self:say("opened " .. ockm_pretty(n))
end
function ui:var_delete(n)
  psend("ockm-project-delete", "symbol", { n }); psend("ockm-project-list", "bang", {})
  if self.vcache then self.vcache[n] = nil end
end
function ui:layout_variations(add)
  local base = self.vbase or ockm_base(self.project or "default")
  local cur = self.project or "default"
  local g = self:var_group(base)
  add{ kind="zone", x=0, y=0, w=W, h=H, tap=function() end }
  local x, y, w, h = 24, 64, W - 48, H - 72
  add{ kind="sheet", x=x, y=y, w=w, h=h }
  add{ kind="text", x=x + 20, y=y + 16, w=w - 200, h=22, label="variations of " .. ockm_pretty(base):match("^[^·]+"):gsub("%s+$", "") .. " (" .. #g .. ")", size=18, col="txt" }
  add{ kind="btn", x=x + w - 120, y=y + 10, w=100, h=36, label="close", tap=function() self.sheet = nil; self.vconfirm = nil end }
  local per = 6
  local pages = math.max(1, math.ceil(#g / per))
  self.vpage = clamp(self.vpage or 0, 0, pages - 1)
  local rh, ry = 58, y + 56
  local bw = 78
  for k = 1, per do
    local n = g[self.vpage * per + k]
    if not n then break end
    local info = self:var_info(n)
    local yy = ry + (k - 1) * (rh + 6)
    local is_cur = (n == cur)
    add{ kind="text", x=x + 20, y=yy + 6, w=110, h=22, label="v" .. ockm_ver(n), size=20, col=is_cur and "acc" or "txt" }
    add{ kind="text", x=x + 20, y=yy + 34, w=110, h=12, size=10,
         label=is_cur and "open now" or (info.saved and os.date("%d %b %H:%M", info.saved) or "") }
    add{ kind="text", x=x + 110, y=yy + 8, w=w - 110 - 4 * (bw + 6) - 30, h=14, size=12, col="txt", label=info.summary }
    add{ kind="text", x=x + 110, y=yy + 30, w=w - 110 - 4 * (bw + 6) - 30, h=12, size=10,
         label=(is_cur and info.saved) and ("saved " .. os.date("%d %b %H:%M", info.saved)) or "" }
    local bx = x + w - 20 - 4 * bw - 3 * 6
    add{ kind="btn", x=bx, y=yy, w=bw, h=rh - 6, small=true, label="open", accent=not is_cur, off=is_cur,
         tap=function() if not is_cur then self:var_open(n) end end }
    add{ kind="btn", x=bx + (bw + 6), y=yy, w=bw, h=rh - 6, small=true, label=info.keep and "kept" or "keep", accent=info.keep and true or false,
         tap=function() local m = self:var_meta(n); m.keep = not m.keep; self:var_write(n, m); self.vcache[n] = nil end }
    add{ kind="btn", x=bx + 2 * (bw + 6), y=yy, w=bw, h=rh - 6, small=true, label="export", tap=function() self:var_open(n, true) end }
    local armed = (self.vconfirm == n)
    add{ kind="btn", x=bx + 3 * (bw + 6), y=yy, w=bw, h=rh - 6, small=true, quiet=not armed, off=is_cur,
         label=armed and "sure?" or "delete",
         tap=function()
           if is_cur then self:say("that's the one you're in: open another first"); return end
           if armed then self:var_delete(n); self.vconfirm = nil; self:say(ockm_pretty(n) .. " moved to the trash folder")
           else self.vconfirm = n end
         end }
  end
  if pages > 1 then
    add{ kind="arrow", x=x + w - 112, y=y + h - 50, w=44, h=36, dir=-1, on=self.vpage > 0, tap=function() self.vpage = self.vpage - 1 end }
    add{ kind="arrow", x=x + w - 60, y=y + h - 50, w=44, h=36, dir=1, on=self.vpage < pages - 1, tap=function() self.vpage = self.vpage + 1 end }
  end
  -- tidy up: everything except the kept ones, the newest 3 and the open one goes to the trash folder
  local gone = {}
  for i, n in ipairs(g) do
    if i > 3 and n ~= cur and not self:var_info(n).keep then gone[#gone + 1] = n end
  end
  local armed = (self.vconfirm == "tidy")
  add{ kind="btn", x=x + 20, y=y + h - 54, w=360, h=44, small=true, off=(#gone == 0), quiet=not armed,
       label=(#gone == 0) and "tidy up: nothing to clear" or (armed and string.format("tap again: %d to the trash", #gone) or string.format("tidy up: keep the kept and the newest 3 (%d go)", #gone)),
       tap=function()
         if #gone == 0 then return end
         if armed then
           for _, n in ipairs(gone) do self:var_delete(n) end
           self.vconfirm = nil; self:say(string.format("%d variations moved to the trash folder", #gone))
         else self.vconfirm = "tidy" end
       end }
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
      add{ kind="vfader", x=cx, y=top + 140, w=cw, h=210, hook="ockm-"..t.."-level", lo=0, hi=LEVEL_MAX, db=0.75 }
      add{ kind="ms", x=cx, y=top + 364, w=cw, h=50, label="M", hook="ockm-"..t.."-mute" }
      add{ kind="ms", x=cx, y=top + 420, w=cw, h=50, label="S", hook="ockm-"..t.."-solo" }
    else
      add{ kind="strip", x=x, y=top, w=sw - 2, h=H - top - 8, label="master", master=true }
      add{ kind="hbar", x=cx, y=top + 34, w=cw, h=26, hook="ockm-verb-mix", lo=0, hi=1, label="rev" }
      add{ kind="hbar", x=cx, y=top + 66, w=cw, h=26, hook="ockm-delay-mix", lo=0, hi=1, label="dly" }
      add{ kind="btn", x=cx, y=top + 100, w=cw, h=32, small=true, label="de-mud", tap=function() self:demud() end }
      add{ kind="vfader", x=cx, y=top + 140, w=cw, h=210, hook="ockm-volume", lo=0, hi=1, master=true, db=0.5 }
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
       or w.kind == "dstep" or w.kind == "mstep" or w.kind == "cstep" or w.kind == "pad" or w.kind == "vlane" or w.kind == "hold" or w.kind == "xy") then return w end
  end
  return nil
end

function ui:press(x, y)
  local w = self:hit(x, y)
  self.touch = { w = w, x0 = x, y0 = y, mode = nil }
  if not w then return end
  if w.kind == "pad" then self.touch.mode = "pad"; self.pad_on = w.hook; psend(w.hook, "float", { 1 })
  elseif w.kind == "hold" then self.touch.mode = "hold"; w.down()
  elseif w.kind == "xy" then self.touch.mode = "xy"; w.down(self:xy_at(w, x, y))
  elseif w.kind == "slider" or w.kind == "vfader" or w.kind == "hbar" then self.touch.mode = "slider"; self:slide(w, x, y)
  elseif w.kind == "bpm" then self.touch.v0 = self.v["ockm-bpm"] or 124
  elseif w.kind == "vlane" then self.touch.mode = "vlane"; self:lane_set(w, x, y)
  elseif w.kind == "dstep" or w.kind == "pcell" or w.kind == "ms" then
    -- drum steps, mute and solo act the moment a finger lands, like the pads on a drum machine
    if w.kind == "ms" then
      if w.tap then w.tap() else self:send(w.hook, ((self.v[w.hook] or 0) > 0) and 0 or 1) end
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

-- the XY pad's position, 0-1 each way (up is 1)
function ui:xy_at(w, x, y) return clamp((x - w.x) / w.w, 0, 1), clamp(1 - (y - w.y) / w.h, 0, 1) end
function ui:slide(w, x, y)
  local f
  if w.kind == "vfader" then f = clamp(1 - (y - w.y - 8) / (w.h - 16), 0, 1)
  elseif w.kind == "hbar" then f = clamp((x - w.x) / w.w, 0, 1)
  else f = clamp((x - (w.x + 110)) / (w.w - 180), 0, 1) end
  local v = w.lo + f * (w.hi - w.lo)
  if w.db then
    v = math.floor(fader_gain(f, w.db) * 1000 + 0.5) / 1000
    local changed = (self.v[w.hook] ~= v)
    self:send(w.hook, v); return
  end
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
  if t.mode == "xy" then t.w.drag(self:xy_at(t.w, x, y)); return end
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
  elseif t.mode == "xy" then w.up()
  elseif t.mode == "slider" and w.spring then
    self:filter_spring()     -- let go: snap back to off
  elseif t.mode == "slider" and w.preview then
    self:preview(w.preview, true)
  elseif t.mode == "swipe" then
    local dx = x - t.x0
    if type(w.swipe) == "function" then w.swipe(dx)   -- a widget with its own swipe (the drums tab's views)
    else self:set_page(self.page + ((dx < 0) and 1 or -1)) end
  elseif t.mode == nil and inside(w, x, y) then
    if w.kind == "dstep" then self:drum_tap(w.i)
    elseif (w.kind == "mstep" or w.kind == "cstep") and self:locked() then
      self:say(SYNTHS[self.part] .. " " .. self:follows_what(SYNTHS[self.part]) .. ": set the mode to manual on compose to edit it")
    elseif w.kind == "mstep" then self:mono_tap(w.i)
    elseif w.kind == "cstep" then self:chord_tap(w.i)
    elseif w.kind == "ms" then if w.tap then w.tap() else self:send(w.hook, ((self.v[w.hook] or 0) > 0) and 0 or 1) end
    elseif w.tap then w.tap() end
  end
  self:dirty()
end

-- redraw on a press only when the press itself changed something (most buttons act when the finger lifts)
function ui:mouse_down(x, y) self:press(x / self.s, y / self.s); if self.touch and self.touch.mode then self:repaint() end end
function ui:mouse_drag(x, y) self:move(x / self.s, y / self.s); self:dirty() end
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
  if self.screen == "drums" and self.drums_all then
    if self:play_block() == self.page then
      local lw = (W - LANE_X - 16) / 16
      self:col(g, "acc"); g:fill_rect(LANE_X + i * lw + 2, LANE_Y - 6, lw - 4, 3)
    end
  elseif self.screen == "perform" then
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
    local on = (w.lit ~= nil) and w.lit or ((self.v[w.hook or ""] or 0) > 0)
    local solo = w.label == "S"
    self:col(g, on and (solo and "acc" or "on") or "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 4)
    self:ctext(g, w.label, w, (w.h > 30) and 15 or 11, on and (solo and "#ffffff" or "bg") or "mute")
  elseif k == "strip" then
    self:col(g, "card"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 6)
    self:ctext(g, w.label, { x=w.x, y=w.y + 6, w=w.w, h=16 }, 11, w.silent and "mute" or "txt")
  elseif k == "xy" then
    -- v1.23 the bus effects' pad: quarter lines, the centre line for the filter, where it is (filled while it's in)
    self:col(g, "off"); g:fill_rounded_rect(w.x, w.y, w.w, w.h, 8)
    self:col(g, "dim")
    for q = 1, 3 do g:fill_rect(w.x + w.w * q / 4, w.y + 8, 1, w.h - 16); g:fill_rect(w.x + 8, w.y + w.h * q / 4, w.w - 16, 1) end
    if w.fx == "filter" then self:col(g, "mute"); g:fill_rect(w.x + w.w / 2 - 1, w.y + 8, 2, w.h - 16) end
    local b = w.bus
    local on = (self.v["ockm-bfx-"..b.."-on"] or 0) > 0
    self:text(g, b .. " bus: " .. w.fx, w.x + 16, w.y + 14, 16, "txt", w.w - 32)
    self:text(g, on and "in" or "touch to play it", w.x + 16, w.y + 38, 11, on and "acc" or "mute", 200)
    if w.axes then
      self:text(g, "across: " .. w.axes[1], w.x + 16, w.y + w.h - 26, 11, "mute", w.w - 32)
      self:text(g, "up: " .. w.axes[2], w.x + w.w - 16 - #("up: " .. w.axes[2]) * 6.6, w.y + 14, 11, "mute", 260)
    end
    local px = w.x + w.w * (self.v["ockm-bfx-"..b.."-x"] or 0.5)
    local py = w.y + w.h * (1 - (self.v["ockm-bfx-"..b.."-y"] or 0.5))
    self:col(g, on and "acc" or "mute")
    g:fill_rect(px - 1, w.y + 8, 2, w.h - 16); g:fill_rect(w.x + 8, py - 1, w.w - 16, 2)
    if on then g:fill_ellipse(px - 22, py - 22, 44, 44) else g:stroke_rounded_rect(px - 18, py - 18, 36, 36, 18, 2) end
  elseif k == "hbar" then
    local v = self.v[w.hook] or 0
    local f = w.db and fader_pos(v, w.db) or clamp((v - w.lo) / (w.hi - w.lo), 0, 1)
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
    if w.ends then   -- a slider between two named ends: the ends at the sides, what it's doing now in the middle
      self:text(g, w.ends[1], w.x + 10, w.y + w.h / 2 - 6, 10, "mute", 80)
      self:text(g, w.ends[2], w.x + w.w - 10 - #w.ends[2] * 6.2, w.y + w.h / 2 - 6, 10, "mute", 80)
      self:ctext(g, w.valtext and w.valtext(v) or w.label, { x=w.x, y=w.y + w.h / 2 - 7, w=w.w, h=14 }, 12, "txt")
    elseif w.h >= 40 then
      self:ctext(g, w.label, { x=w.x, y=w.y + w.h / 2 - 16, w=w.w, h=14 }, 12, "txt")
      self:ctext(g, w.valtext and w.valtext(v) or fmt(v), { x=w.x, y=w.y + w.h / 2 + 2, w=w.w, h=12 }, 10, "txt")
    else
      self:ctext(g, w.label, w, 10, w.off and "mute" or "txt")
    end
  elseif k == "vfader" then
    local v = self.v[w.hook] or 0
    local f = w.db and fader_pos(v, w.db) or clamp((v - w.lo) / (w.hi - w.lo), 0, 1)
    local tx = w.x + w.w / 2 - 4
    self:col(g, "off"); g:fill_rounded_rect(tx, w.y + 8, 8, w.h - 16, 4)
    local fy = w.y + 8 + (w.h - 16) * (1 - f)
    self:col(g, w.master and "on" or "acc"); g:fill_rounded_rect(tx, fy, 8, w.y + w.h - 8 - fy, 4)
    g:fill_rounded_rect(w.x + 4, fy - 7, w.w - 8, 14, 4)
    local lbl = string.format("%d", math.floor(v * 100 + 0.5))
    if w.db then
      local d = (v > 0) and 20 * math.log(v, 10) or nil
      lbl = (not d or d < -39.5) and "off" or (math.abs(d) < 0.5 and "0 dB" or string.format("%+d dB", math.floor(d + 0.5)))
    end
    self:ctext(g, lbl, { x=w.x, y=w.y + w.h - 2, w=w.w, h=12 }, 10, "mute")
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
