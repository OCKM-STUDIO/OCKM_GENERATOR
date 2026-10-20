-- Plain-Lua tests for two-handed chords (v1.20), through the chord sequencer's notes object: lua tests/lua/test_twohands.lua [built folder]
local root = arg[1] or "."
local here = arg[0]:match("^(.*)/[^/]*$") or "."
dofile(here .. "/pd_stub.lua")
local cn = load_pd_lua(root .. "/seq/ockm-chordnotes.pd_lua")
local fails = 0
local function check(cond, what) if not cond then fails = fails + 1; print("FAIL " .. what) end end

-- a notes object that records what it plays: out[1] the right hand, out[2] the left
local function make(engine, hands)
  local o = setmetatable({}, { __index = cn })
  o:initialize("ockm-chordnotes", {})
  o.out = { {}, {} }
  function o:outlet(k, sel, a) self.out[k][#self.out[k] + 1] = a end
  o:in_1_root({ 9 })                       -- A minor
  o:in_1_scale({ 0, 2, 3, 5, 7, 8, 10 })
  o:in_1_engine({ engine }); o:in_1_hands({ hands })
  return o
end
-- play a bar of one chord (scale step deg) with the right hand on the steps in rh; returns the left hand's steps
local function bar(o, deg, rh)
  local steps = {}
  for i = 0, 15 do
    local on = rh[i] and 1 or 0
    local before = #o.out[2]
    o:in_1_lh({ i, deg, 0, on })
    if #o.out[2] > before then steps[#steps + 1] = i end
    if on > 0 then o:in_1_hit({ 0.75, deg, 0, i }) end
  end
  return table.concat(steps, " ")
end

-- one hand (or a poly): the left hand stays silent and the right hand plays as before
local o = make(3, 0)
check(bar(o, 0, { [0] = true }) == "", "one hand: no left hand")
o = make(0, 2)
check(bar(o, 0, { [0] = true }) == "", "poly: no left hand even with hands set")

-- the five patterns
check(bar(make(3, 1), 0, {}) == "0", "anchor: once a bar on one chord")
check(bar(make(3, 2), 0, {}) == "0 4 8 12", "pulse: every beat")
check(bar(make(3, 3), 0, {}) == "0 6 12", "syncopated: 1, the and of 2, 4")
check(bar(make(3, 4), 0, {}) == "0 2 4 6 8 10 12 14", "broken: beats and ands")
check(bar(make(3, 5), 0, { [0] = true, [8] = true }) == "4 12", "answer: the beats the right hand leaves")

-- anchor strikes again when the chord changes mid-bar
o = make(3, 1)
local hits = {}
for i = 0, 15 do
  local before = #o.out[2]
  o:in_1_lh({ i, (i < 8) and 0 or 3, 0, 0 })
  if #o.out[2] > before then hits[#hits + 1] = i end
end
check(table.concat(hits, " ") == "0 8", "anchor: strikes on the change")

-- the left hand's notes: A (pc 9) between G2 (43) and F#3 (54), with its octave
o = make(3, 2); bar(o, 0, {})
local n = o.out[2][1]
check(n[1] == 45 and n[2] == 57, "left hand: A2 and A3 (got " .. tostring(n[1]) .. " " .. tostring(n[2]) .. ")")
check(n[5] > 0 and n[5] <= 1, "left hand has a strength")
-- broken: root on the beat, the fifth (E3) on the and of 1, the octave on the and of 2
o = make(3, 4); bar(o, 0, {})
check(o.out[2][1][1] == 45 and o.out[2][1][2] == 0, "broken: the root alone")
check(o.out[2][2][1] == 52, "broken: the fifth on the and of 1")
check(o.out[2][4][1] == 57, "broken: the octave on the and of 2")
-- the iv chord (D, scale step 3) sits at D3 (50)
o = make(3, 2); bar(o, 3, {})
check(o.out[2][1][1] == 50, "left hand: iv at D3")

-- the right hand with two hands: nothing below G3, and a four-note chord drops its root
o = make(3, 2); o:in_1_type({ 1 })          -- 7ths
bar(o, 0, { [0] = true })
local r = o.out[1][1]
local lowest, root_in = 200, false
for k = 1, 4 do if r[k] > 0 then lowest = math.min(lowest, r[k]); if r[k] % 12 == 9 then root_in = true end end end
check(lowest >= 55, "right hand: nothing below G3")
check(not root_in, "right hand: the 7th chord drops its root")
local o1 = make(3, 0); o1:in_1_type({ 1 }); bar(o1, 0, { [0] = true })
local has = false
for k = 1, 4 do if o1.out[1][1][k] % 12 == 9 and o1.out[1][1][k] > 0 then has = true end end
check(has, "one hand: the root stays")

if fails == 0 then print("ok") else os.exit(1) end
