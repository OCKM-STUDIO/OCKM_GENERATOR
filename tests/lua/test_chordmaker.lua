-- Plain-Lua tests for the chord generator's pattern logic (no Pd needed): lua tests/lua/test_chordmaker.lua [built folder]
-- (run_tests.py runs it on its built copy; on your own, after python3 tools/build.py, from the repo folder)
local root = arg[1] or "."
local here = arg[0]:match("^(.*)/[^/]*$") or "."
dofile(here .. "/pd_stub.lua")
local cm = load_pd_lua(root .. "/seq/ockm-chordmaker.pd_lua")
local fails = 0
local function check(cond, what) if not cond then fails = fails + 1; print("FAIL " .. what) end end
local function steps(t, a, b) local o = {} for i = a, b do o[#o + 1] = t[i + 1] end return table.concat(o, " ") end

-- pads (rhythm 0), one chord (prog 0), a chord a bar: one accent on the 1, the home chord throughout
local on, deg = cm.pattern(0, 0, 1, false, 16)
check(steps(on, 0, 15) == "2 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0", "pads: one accent on the 1")
check(steps(deg, 0, 15) == "0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0", "one chord: the home chord")

-- vamp (prog 1, i iv) at a bar a chord: i for 16 steps, then iv (scale step 3)
on, deg = cm.pattern(0, 1, 1, false, 32)
check(deg[1] == 0 and deg[16] == 0 and deg[17] == 3 and deg[32] == 3, "vamp: i for a bar, then iv")
check(on[1] == 2 and on[17] == 2, "pads hit each bar")

-- the same at half a bar a chord: the change comes on step 8
on, deg = cm.pattern(0, 1, 0, false, 16)
check(deg[8] == 0 and deg[9] == 3, "rate 0: the chord changes every half bar")

-- push: the change to iv lands two steps early (step 14), and the pad hit on the bar line moves with it
on, deg = cm.pattern(0, 1, 1, true, 32)
check(deg[15] == 3 and deg[14] == 0, "push: iv arrives on step 14")
check(on[15] == 2 and on[17] == 0, "push: the hit moves from step 16 to 14")

-- sustained (rhythm 11): one hit per chord, on the change
on, deg = cm.pattern(11, 1, 1, false, 32)
local hits = {}
for i = 1, 32 do if on[i] > 0 then hits[#hits + 1] = i - 1 end end
check(table.concat(hits, " ") == "0 16", "sustained: hits on 0 and 16 only")

-- an unknown preset gives nothing (and the generator leaves the pattern alone)
check(cm.pattern(99, 0, 1, false, 16) == nil, "unknown rhythm: no pattern")

if fails == 0 then print("ok") else os.exit(1) end
