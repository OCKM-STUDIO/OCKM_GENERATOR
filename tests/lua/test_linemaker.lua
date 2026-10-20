-- Plain-Lua tests for the bass and lead generator's line logic (no Pd needed): lua tests/lua/test_linemaker.lua [built folder]
local root = arg[1] or "."
local here = arg[0]:match("^(.*)/[^/]*$") or "."
dofile(here .. "/pd_stub.lua")
local lm = load_pd_lua(root .. "/seq/ockm-linemaker.pd_lua")
local fails = 0
local function check(cond, what) if not cond then fails = fails + 1; print("FAIL " .. what) end end
local function zeros(n) local t = {} for i = 1, n do t[i] = 0 end return t end
local MINOR = { 0, 2, 3, 5, 7, 8, 10 }
local function settings(over)
  local s = { offset = 0, rhythm = 0, notes = 0, lead = false, root = 9, scale = 0, octave = 0, lock = 0, density = 1, seed = 0,
              outside = 0.35, rests = 0, slideamt = 0, riff = -1, rep = 0, sync = true }
  for k, v in pairs(over or {}) do s[k] = v end
  return s
end
local function tables(rhythm, notes, over)
  local t = { rhythm = rhythm, notes = notes, scale = MINOR, chord_deg = zeros(64), kick = zeros(64), bass_on = zeros(64) }
  for k, v in pairs(over or {}) do t[k] = v end
  return t
end
local OFFBEAT = { 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0 }

-- an offbeat root bass in A minor: A1 (MIDI 33) on every offbeat
local note, on = lm.line(settings(), tables(OFFBEAT, { 0 }), 16, 0)
check(on[3] == 1 and on[1] == 0 and note[3] == 33, "offbeat bass: A1 on the offbeat")
check(note[1] == nil, "a rest leaves its note alone")

-- following the chords: over iv (scale step 3) the root moves to D
local deg = zeros(16); for i = 1, 16 do deg[i] = 3 end
note = lm.line(settings(), tables(OFFBEAT, { 0 }, { chord_deg = deg }), 16, 0)
check(note[3] == 38, "the bass follows the chord: D2 over iv")

-- V, VI and VII sit below the root (step 4 is the fifth below, not above)
for i = 1, 16 do deg[i] = 4 end
note = lm.line(settings(), tables(OFFBEAT, { 0 }, { chord_deg = deg }), 16, 0)
check(note[3] == 28, "V sits below: E1")

-- lock to the kick: notes land exactly where the kick is
local kick = zeros(16); kick[1], kick[5], kick[9], kick[13] = 2, 1, 1, 1
local _, on2, acc2 = lm.line(settings({ lock = 1 }), tables(OFFBEAT, { 0 }, { kick = kick }), 16, 0)
check(on2[1] == 1 and on2[5] == 1 and on2[3] == 0 and acc2[1] == 1, "lock to kick: on the kick, accented with it")

-- mutate is repeatable: the same seed gives the same line
local a = { lm.line(settings({ seed = 3 }), tables(OFFBEAT, { 0, 4, 7 }), 64, 0) }
local b = { lm.line(settings({ seed = 3 }), tables(OFFBEAT, { 0, 4, 7 }), 64, 0) }
local same = true
for i = 1, 64 do if a[2][i] ~= b[2][i] or a[1][i] ~= b[1][i] then same = false end end
check(same, "the same seed gives the same variation")

-- density 0 thins every plain note; accents stay
local ACC = { 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 1, 0, 1, 0, 1, 0 }
local _, on3 = lm.line(settings({ density = 0 }), tables(ACC, { 0 }), 16, 0)
check(on3[1] == 1 and on3[9] == 1 and on3[3] == 0, "density 0: only the accents are left")

-- a hold repeats the note before it
local HOLD = { 1, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }
note = lm.line(settings(), tables(HOLD, { 4 }), 16, 0)
check(note[2] == note[1] and note[1] == 40, "a hold repeats the note before")

-- the lead (lead rules, inside): an off-chord note on the beat moves onto the chord
local QUARTERS = { 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0 }
note = lm.line(settings({ lead = true, outside = 0, offset = 24 }), tables(QUARTERS, { 1 }), 16, 0)
check(note[1] == 57, "inside: the 2nd moves down onto the root (A3)")

if fails == 0 then print("ok") else os.exit(1) end
