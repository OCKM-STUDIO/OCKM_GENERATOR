-- Plain-Lua tests for the smarter drum lanes (v1.49): lua tests/lua/test_lane.lua [built folder]
local root = arg[1] or "."
local here = arg[0]:match("^(.*)/[^/]*$") or "."
dofile(here .. "/pd_stub.lua")
local lane = load_pd_lua(root .. "/seq/ockm-lane.pd_lua")
local fails = 0
local function check(cond, what) if not cond then fails = fails + 1; print("FAIL " .. what) end end
local function S(over) local s = { chance = 1, thin = 0, when = 0, drift = 0, id = 1 }; for k, v in pairs(over or {}) do s[k] = v end; return s end
local always = function() return 0 end

-- out of the box nothing changes
for step = 0, 15 do check(lane.decide(S(), 1, step, 0, false, always) == 1, "default: every hit plays " .. step) end
check(lane.decide(S(), 0, 3, 0, false, always) == 0, "default: an empty step stays empty")
check(lane.decide(S(), 2, 0, 0, false, always) == 2, "default: an accent stays an accent")

-- thin: the 16ths go first, then the 8ths, then beats 2 and 4, then beat 3; the 1 always stays
local function kept(thin) local n = {} for step = 0, 15 do if lane.decide(S({ thin = thin }), 1, step, 0, false, always) > 0 then n[#n + 1] = step end end return table.concat(n, ",") end
check(kept(0.25) == "0,2,4,6,8,10,12,14", "thin 1/4: the off 16ths go: " .. kept(0.25))
check(kept(0.5) == "0,4,8,12", "thin 1/2: just the beats: " .. kept(0.5))
check(kept(0.75) == "0,8", "thin 3/4: the 1 and the 3: " .. kept(0.75))
check(kept(1) == "0", "thin all the way: just the 1: " .. kept(1))

-- chance: about that share of hits play
math.randomseed(7)
local n = 0
for i = 1, 2000 do if lane.decide(S({ chance = 0.3 }), 1, 4, 0, false) > 0 then n = n + 1 end end
check(n > 500 and n < 700, "chance 0.3: about 30% play: " .. n)

-- conditions
local function bars(when, fill) local t = {} for bar = 0, 7 do t[#t + 1] = (lane.decide(S({ when = when }), 1, 0, bar, fill or false, always) > 0) and "x" or "." end return table.concat(t) end
check(bars(1) == "x.x.x.x.", "bars 1 and 3: " .. bars(1))
check(bars(2) == ".x.x.x.x", "bars 2 and 4: " .. bars(2))
check(bars(3) == "...x...x", "last of four: " .. bars(3))
check(bars(4) == "x...x...", "first of four: " .. bars(4))
check(bars(5) == "........" and bars(5, true) == "xxxxxxxx", "only in fills")
check(bars(6) == "xxxxxxxx" and bars(6, true) == "........", "never in fills")
-- a fill plays as written, whatever the thinning
check(lane.decide(S({ thin = 1, chance = 0 }), 1, 3, 0, true, always) == 1, "a fill plays as written")

-- drift: the backbone (beats and accents) never moves, the rest changes from bar to bar, and a bar is repeatable
local backbone, changed = true, 0
local function bar_of(b) local t = {} for step = 0, 15 do t[step] = lane.decide(S({ drift = 1 }), (step % 2 == 0) and 1 or 0, step, b, false, always) end return t end
local first = bar_of(0)
for b = 0, 31 do
  local t = bar_of(b)
  for step = 0, 15, 4 do if t[step] ~= 1 then backbone = false end end
  for step = 0, 15 do if t[step] ~= first[step] then changed = changed + 1; break end end
end
check(backbone, "drift: the beats always play")
check(changed > 15, "drift: most bars differ from the first: " .. changed)
local again = bar_of(5); local same = true
for step = 0, 15 do if again[step] ~= bar_of(5)[step] then same = false end end
check(same, "drift: the same bar comes out the same")
check(lane.decide(S({ drift = 1 }), 2, 6, 3, false, always) == 2, "drift: an accent off the beat stays")

-- rolls: n hits, the first as written, then a little softer each time
local r = lane.roll(2, 4)
check(#r == 4 and r[1] == 2 and r[2] < 1 and r[4] < r[2], "a roll of four")
check(#lane.roll(1, 0) == 1 and #lane.roll(1, 1) == 1 and #lane.roll(1, 9) == 6, "rolls: 0 and 1 a single hit, at most six")

-- v1.49 the mood: chill thins a hat's off-beats, peak adds ghost notes; the kick (not texture) never changes
do
  local HAT = {}; for st = 0, 15 do HAT[st] = (st % 2 == 0) and 1 or 0 end
  local function count(mood, texture)
    local n, ghosts = 0, 0
    for bar = 0, 15 do for st = 0, 15 do
      local o = lane.decide(S({ mood = mood, texture = texture }), HAT[st], st, bar, false, always)
      if o > 0 then n = n + 1; if HAT[st] == 0 then ghosts = ghosts + 1 end end
    end end
    return n, ghosts
  end
  local mid = count(0.5, true)
  local chill = count(0, true)
  local peak, ghosts = count(1, true)
  check(mid == 128, "mood in the middle: the hats as written: " .. mid)
  check(chill == 64, "full chill: just the beats left on the hats: " .. chill)
  check(peak > 128 and ghosts > 5, "peak: ghost notes join the hats: " .. peak)
  check(count(0, false) == 128 and count(1, false) == 128, "the kick ignores the mood")
end

-- v1.49 the build's values carry their own rolls: 22 an accent twice, 31 a hit three times; below 10 as it is
do
  local v, n = lane.split(22); check(v == 2 and n == 2, "22: an accent rolled twice")
  v, n = lane.split(31); check(v == 1 and n == 3, "31: a hit three times")
  v, n = lane.split(0.6); check(v == 0.6 and n == nil, "a soft hit stays itself")
end

-- v1.49 flams, swells and humanize
do
  local f = lane.hits(2, 7, 0.3, 120, 0)
  check(#f == 2 and f[1][1] == 0 and f[1][2] < 0.5 and f[2][1] == 15 and f[2][2] == 2, "a flam: a soft grace note, the hit an eighth of a step later")
  local sw = lane.hits(1, 8, 0.3, 120, 0)
  check(#sw == 4 and sw[1][2] < sw[2][2] and sw[2][2] < sw[3][2] and sw[4][2] == 1 and sw[4][1] == 90, "a swell: four hits getting louder, the last as written")
  local r = lane.hits(1, 3, 0.3, 120, 0)
  check(#r == 3 and r[2][1] == 40 and r[3][1] == 80, "a roll of three, evenly across the step")
  local hu = lane.hits(1, 1, 0.3, 120, 1, function() return 1 end)
  check(math.abs(hu[1][2] - 0.56) < 0.001 and hu[1][1] == 15, "humanize all the way, at its most: a fifth softer, an eighth of a step late")
  local none = lane.hits(1, 1, 0.3, 120, 0)
  check(none[1][2] == 1 and none[1][1] == 0, "no humanize: as written")
end

-- v1.49 drum drift: your pattern, then a variation, every N bars; the kick never moves
do
  local HAT = {}; for j = 0, 15 do HAT[j] = (j % 2 == 0) and 1 or 0 end
  local get = function(j) return HAT[j % 16] end
  local function bar_of(bar, sound, mode)
    local out = {}; for i = 0, 15 do out[i] = lane.drift_value(get, i, 16, sound, bar, 4, mode, 5) end; return out
  end
  local function same(a) for i = 0, 15 do if a[i] ~= HAT[i] then return false end end return true end
  check(same(bar_of(0, 4, 1)) and same(bar_of(3, 4, 2)), "bars 1-4: your pattern")
  local differs = false
  for b = 4, 7 do if not same(bar_of(b, 4, 2)) then differs = true end end
  check(differs, "bars 5-8: a variation (morph)")
  check(same(bar_of(8, 4, 2)), "bars 9-12: yours again")
  for b = 4, 7 do check(same(bar_of(b, 0, 2)), "the kick never moves") end
  local n = 0; for i = 0, 15 do if bar_of(5, 4, 1)[i] > 0 then n = n + 1 end end
  check(n == 8, "shift moves hits, it doesn't add or lose them: " .. n)
end

if fails == 0 then print("ok") else os.exit(1) end
