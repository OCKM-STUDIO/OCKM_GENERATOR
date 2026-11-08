-- Smarter drum lanes (v1.49): sits in each drum row between the pattern and the drum voice, and decides what plays.
--
-- [ockm-lane d1]
-- Inlet 1: the step's value from the pattern (0 off, 1 hit, 2 accent, between 0 and 1 a softer hit), after any fill
-- Inlet 2: the step number in the drum loop (sent before the value)
-- Outlet: the hits that play: the value, then any ratchet repeats spread across the step
--
-- Per lane (saved with the scene):
--   ockm-<lane>-chance  0..1  how likely each hit is to play (1 every time)
--   ockm-<lane>-thin    0..1  density by importance: the off-beat 16ths go first, then the 8ths, beats 2 and 4, beat 3.
--                             The 1 always stays
--   ockm-<lane>-when    0 every bar, 1 bars 1 and 3, 2 bars 2 and 4, 3 the last bar of four, 4 the first bar of four,
--                       5 only in fills, 6 never in fills
--   ockm-<lane>-drift   0..1  each bar a little different: some off-beat hits drop out, the odd ghost note turns up.
--                             The beats and the accents (the backbone) never move
-- Per step: the table ockm-pat-<lane>-rat, 0 or 1 a single hit, 2 to 6 a roll of that many hits in the step.
-- In a fill the fill plays as written (only "only in fills" and "never in fills" apply).

local lane = pd.Class:new():register("ockm-lane")

-- how much a step matters in the bar: 4 the 1, 3 beat 3, 2 beats 2 and 4, 1 the 8ths between, 0 the 16ths between
function lane.importance(step)
  local s = step % 16
  if s == 0 then return 4 elseif s == 8 then return 3 elseif s % 4 == 0 then return 2 elseif s % 2 == 0 then return 1 end
  return 0
end

-- a repeatable number from 0 to 1 for this lane, bar and step: drift is the same all the way through a bar
function lane.hash(a, b, c)
  local x = math.sin(a * 12.9898 + b * 78.233 + c * 37.719) * 43758.5453
  return x - math.floor(x)
end

-- v1.49 drum drift (after PERF-1): every <every> bars the drums swap between your pattern and a variation of it (a new
-- one each time round). mode 1 shift: now and then a hit moves a step later; mode 2 morph: that, plus the odd ghost note
-- added and the odd weak hit taken out. The kick, the clap and a snare on a beat never move. get(j) reads the pattern's
-- step j (0-based, wrapping at len); returns the value to play at step i in this bar
function lane.drift_value(get, i, len, sound, bar, every, mode, id)
  local v = get(i)
  if (every or 0) < 1 or (mode or 0) < 1 then return v end
  local period = math.floor(bar / every)
  if period % 2 == 0 then return v end          -- your pattern, then the variation, then yours again
  local seed = 1000 + period
  local function fixed(j) return sound == 0 or sound == 2 or (sound == 1 and j % 4 == 0) end
  local function moves(j)
    local x = get(j)
    return not fixed(j) and x > 0 and x <= 1 and get((j + 1) % len) <= 0 and lane.hash(id, seed, j % 16) < 0.3
  end
  local prev = (i - 1) % len
  if moves(i) then v = 0 end
  if moves(prev) then v = get(prev) end
  if mode >= 2 and not fixed(i) then
    if v <= 0 and i % 2 == 1 and not moves(prev) and lane.hash(id, seed, i % 16 + 500) < 0.12 then v = 0.45 end
    if v > 0 and v <= 1 and i % 4 ~= 0 and lane.hash(id, seed, i % 16 + 900) < 0.15 then v = 0 end
  end
  return v
end

-- whether a bar plays, by the lane's condition. bar counts from 0 (the first bar)
function lane.bar_plays(when, bar, fill)
  when = math.floor(when or 0)
  local b4 = bar % 4
  if when == 1 then return b4 % 2 == 0
  elseif when == 2 then return b4 % 2 == 1
  elseif when == 3 then return b4 == 3
  elseif when == 4 then return b4 == 0
  elseif when == 5 then return fill
  elseif when == 6 then return not fill end
  return true
end

-- The decision, with no Pd in it (so it can be tested): s holds chance, thin, when, drift and id (a number for the lane).
-- Returns the value to play (0 for nothing). rnd gives a number from 0 to 1 for the chance
function lane.decide(s, v, step, bar, fill, rnd)
  v = v or 0
  if not lane.bar_plays(s.when, bar, fill) then return 0 end
  if fill then return v end
  local imp = lane.importance(step)
  local drift = s.drift or 0
  -- v1.49 the mood, on the hats, percussion and toms (s.texture): towards chill their off-beats thin out (the 16ths,
  -- then the 8ths), towards peak ghost notes fill the empty 16ths. The kick, snare and clap stay as written
  local mood = s.texture and (s.mood or 0.5) or 0.5
  if v <= 0 then
    -- drift: the odd ghost note on an empty 16th between the 8ths
    if drift > 0 and imp == 0 and lane.hash(s.id or 1, bar, step) < drift * 0.12 then return 0.4 end
    if mood > 0.5 and imp == 0 and lane.hash(s.id or 1, bar, step + 600) < (mood - 0.5) * 2 * 0.15 then return 0.35 end
    return 0
  end
  local level = math.floor((s.thin or 0) * 4 + 0.5)
  if mood < 0.5 then level = math.max(level, math.floor((0.5 - mood) * 4 + 0.5)) end
  if level > 0 and imp < 4 and imp < level then return 0 end
  if drift > 0 and imp < 2 and v <= 1 and lane.hash(s.id or 1, bar, step + 300) < drift * 0.35 then return 0 end
  local chance = s.chance or 1
  if chance < 1 and (rnd or math.random)() >= chance then return 0 end
  return v
end

-- the hits of a roll: n of them evenly across one step, each a little softer than the one before. The first goes as
-- written; the rest are a strength (below 1), worked out from how hard the first one plays (a plain hit is 1 minus accent)
function lane.roll(v, n, acc)
  n = math.max(1, math.min(6, math.floor(n or 1)))
  local hits = { v }
  local base = (v > 1) and 1 or ((v > 0.999) and (1 - (acc or 0.3)) or v)
  for i = 2, n do hits[i] = math.max(0.25, base * (1 - 0.12 * (i - 1))) end
  return hits
end

-- v1.49 every hit of a step, with when it lands (ms after the step) and how hard: a roll of n (1-6) evenly across the
-- step; 7 a flam (a soft grace note, then the hit an eighth of a step later); 8 a swell (four hits getting louder,
-- the last one as written). humanize (0-1): each hit up to a fifth softer and up to an eighth of a step late, at random
function lane.hits(v, n, acc, stepms, humanize, rnd)
  n = math.floor(n or 1)
  local base = (v > 1) and 1 or ((v > 0.999) and (1 - (acc or 0.3)) or v)
  local out = {}
  if n == 7 then
    out = { { 0, math.max(0.2, base * 0.35) }, { stepms * 0.125, v } }
  elseif n == 8 then
    for i = 1, 4 do out[i] = { (i - 1) * stepms / 4, (i == 4) and v or math.max(0.2, base * (0.25 + 0.2 * i)) } end
  else
    local r = lane.roll(v, n, acc)
    for i, x in ipairs(r) do out[i] = { (i - 1) * stepms / #r, x } end
  end
  local h = humanize or 0
  if h > 0 then
    rnd = rnd or math.random
    for _, x in ipairs(out) do
      local plain = (x[2] > 1) and 1 or ((x[2] > 0.999) and (1 - (acc or 0.3)) or x[2])
      x[2] = math.max(0.15, plain * (1 - 0.2 * h * rnd()))
      x[1] = x[1] + stepms * 0.125 * h * rnd()
    end
  end
  table.sort(out, function(a, b) return a[1] < b[1] end)
  return out
end

function lane:initialize(sel, atoms)
  self.inlets, self.outlets = 2, 1
  self.name = tostring(atoms[1] or "d1")
  self.s = { chance = 1, thin = 0, when = 0, drift = 0, id = tonumber(self.name:match("%d+")) or 1 }
  self.step, self.bar, self.stepms, self.acc = 0, -1, 125, 0.3
  self.queue = {}
  return true
end

function lane:postinitialize()
  self.recv = {}
  local function on(name, fn)
    local m = "r_" .. #self.recv
    self[m] = function(o, sel, at) fn(tonumber((at or {})[1]) or 0) end
    self.recv[#self.recv + 1] = pd.Receive:new():register(self, name, m)
  end
  for _, k in ipairs({ "chance", "thin", "when", "drift" }) do
    on("ockm-" .. self.name .. "-" .. k, function(x) self.s[k] = x end)
  end
  on("ockm-mood", function(x) self.s.mood = x end)
  on("ockm-humanize", function(x) self.humanize = x end)   -- v1.49
  on("ockm-drum-drift-every", function(x) self.dd_every = x end)
  on("ockm-drum-drift-mode", function(x) self.dd_mode = x end)
  -- hats, percussion and toms follow the mood (sounds 3 perc, 4 hat, 5 open hat, 6 tom, 7 perc 2)
  on("ockm-" .. self.name .. "-sound", function(x) self.s.texture = (x >= 3); self.s.sound = x end)
  on("ockm-bar", function() self.bar = self.bar + 1 end)
  on("ockm-playing", function(x) if x == 0 then self.bar = -1; self.clock:unset(); self.queue = {} end end)
  on("ockm-accent", function(x) self.acc = x end)
  on("ockm-stepms", function(x) if x > 0 then self.stepms = x end end)
  self.clock = pd.Clock:new():register(self, "next_hit")
end

function lane:finalize()
  for _, r in ipairs(self.recv or {}) do r:destruct() end
  if self.clock then self.clock:destruct() end
end

function lane:in_2_float(n) self.step = math.floor(n) end

local function fill_now()
  if not pd.getvalue then return false end
  return (tonumber(pd.getvalue("ockm_fill_on")) or 0) ~= 0 or (tonumber(pd.getvalue("ockm_fill_end")) or 0) ~= 0
      or (tonumber(pd.getvalue("ockm_build_on")) or 0) ~= 0   -- v1.49 the 4 bar build plays as written too
end
-- v1.49 a value of 10 or more carries its own roll (from the 4 bar build): 22 is an accent rolled twice, 31 a hit three times
function lane.split(v)
  if v >= 10 then local n = math.floor(v / 10); return v - 10 * n, n end
  return v, nil
end

function lane:ratchet(step)
  local t = pd.Table:new()
  if not t:sync("ockm-pat-" .. self.name .. "-rat") then return 1 end
  local ok, r = pcall(function() return t:get(step) end)
  return (ok and tonumber(r)) or 1
end

function lane:in_1_float(v)
  self.clock:unset(); self.queue = {}
  local bar = math.max(0, self.bar)
  local fill = fill_now()
  local roll
  v, roll = lane.split(v)
  -- v1.49 drum drift: in its variation bars, the step comes from the varied pattern (never in fills or builds)
  if not fill and (self.dd_every or 0) > 0 and (self.dd_mode or 0) > 0 then v = self:drifted(v, bar) end
  local out = lane.decide(self.s, v, self.step, bar, fill)
  if out <= 0 then return end
  -- in fills and builds the hits play as written (no humanize), as they do on PERF-1
  local hits = lane.hits(out, roll or self:ratchet(self.step), self.acc, self.stepms, fill and 0 or (self.humanize or 0))
  self.queue, self.at = hits, 0
  self:next_hit()
end

function lane:drifted(v, bar)
  local t = pd.Table:new()
  if not t:sync("ockm-pat-" .. self.name) then return v end
  local len = math.max(16, math.floor(tonumber(pd.getvalue and pd.getvalue("ockm_drumlen")) or 16))
  local function get(j)
    local ok, r = pcall(function() return t:get(j % len) end)
    return (ok and tonumber(r)) or 0
  end
  return lane.drift_value(get, self.step % len, len, self.s.sound or 1, bar, self.dd_every, self.dd_mode, self.s.id or 1)
end

function lane:next_hit()
  while self.queue[1] and self.queue[1][1] <= self.at + 0.01 do
    local x = table.remove(self.queue, 1)
    self:outlet(1, "float", { x[2] })
  end
  local nx = self.queue[1]
  if nx then
    local wait = nx[1] - self.at
    self.at = nx[1]
    self.clock:delay(wait)
  end
end
