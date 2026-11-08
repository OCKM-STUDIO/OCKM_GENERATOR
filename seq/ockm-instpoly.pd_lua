-- The Analog's voice allocator (v1.40): one note stream in, four voices out.
--
-- [ockm-instpoly <prefix>]
-- Inlet: note <n> <vel> [slide] / off <n> / panic (the same as a single voice takes)
-- Outlets 1-4: the voices (note, off, power 0/1, spread <semitones>). Outlet 5: the output gain (fewer voices, louder)
-- Settings, from <prefix>-<name>:
--   mode   0 mono (one voice, glides and legato as before), 1 unison (all four on one note, detuned),
--          2 chord (each key plays the chord: the key plus ch1, ch2, ch3 semitones; 0 is none), 3 poly (four notes at once)
--   uni    0 to 1: unison's detune, up to a third of a semitone either side
--   ch1, ch2, ch3   the chord's notes above the key, in semitones (0: not used)

local ip = pd.Class:new():register("ockm-instpoly")
local N = 4

function ip:initialize(sel, atoms)
  self.inlets, self.outlets = 1, N + 1
  self.pre = tostring(atoms[1] or "ia")
  self.mode, self.uni = 0, 0.3
  self.ch = { 3, 7, 0 }
  self.vnote = {}      -- voice -> the note it holds (nil free)
  self.age = {}        -- voice -> when it started (for stealing the oldest)
  self.t = 0
  self.held = {}       -- key -> the voices it started
  return true
end

function ip:postinitialize()
  self.recv = {}
  local function on(name, fn)
    local m = "r_" .. #self.recv
    self[m] = function(o, sel, at) fn(tonumber(at and at[1]) or 0) end
    self.recv[#self.recv + 1] = pd.Receive:new():register(self, self.pre .. "-" .. name, m)
  end
  on("mode", function(x) self:set_mode(math.floor(x + 0.5)) end)
  on("uni", function(x) self.uni = x; if self.mode == 1 then self:spread() end end)
  on("ch1", function(x) self.ch[1] = math.floor(x) end)
  on("ch2", function(x) self.ch[2] = math.floor(x) end)
  on("ch3", function(x) self.ch[3] = math.floor(x) end)
  -- once everything's wired up: power for the starting mode
  self.clock = pd.Clock:new():register(self, "start")
  self.clock:delay(0)
end
function ip:start() self:set_mode(self.mode, true) end
function ip:finalize()
  for _, r in ipairs(self.recv or {}) do r:destruct() end
  if self.clock then self.clock:destruct() end
end

local function used(mode) return (mode == 0) and 1 or N end

function ip:set_mode(m, force)
  if m == self.mode and not force then return end
  self:in_1_panic()
  self.mode = m
  for v = 1, N do self:outlet(v, "power", { (v <= used(m)) and 1 or 0 }) end
  self:spread()
  self:outlet(N + 1, "float", { (m == 0) and 1 or 0.5 })
end

function ip:spread()
  local d = { 0, 0, 0, 0 }
  if self.mode == 1 then local u = self.uni * 0.33; d = { -u, u, -u * 0.4, u * 0.4 } end
  for v = 1, N do self:outlet(v, "spread", { d[v] }) end
end

function ip:voice_on(v, n, vel, slide)
  self.vnote[v] = n; self.t = self.t + 1; self.age[v] = self.t
  self:outlet(v, "note", { n, vel, slide })
end
function ip:voice_off(v)
  if self.vnote[v] then self:outlet(v, "off", { self.vnote[v] }); self.vnote[v] = nil end
end

-- a free voice, or the oldest one
function ip:pick()
  local best, bt = nil, math.huge
  for v = 1, N do if not self.vnote[v] then return v end end
  for v = 1, N do if self.age[v] < bt then best, bt = v, self.age[v] end end
  self:voice_off(best)
  return best
end

function ip:in_1_note(at)
  local n, vel, slide = tonumber(at[1]) or 60, tonumber(at[2]) or 100, tonumber(at[3]) or 0
  if vel <= 0 then return self:in_1_off({ n }) end
  local m = self.mode
  if m == 0 then
    self:outlet(1, "note", { n, vel, slide }); return
  end
  if self.held[n] then self:in_1_off({ n }) end
  local vs = {}
  if m == 1 then
    for v = 1, N do self:voice_off(v); self:voice_on(v, n, vel, slide); vs[#vs + 1] = { v, n } end
  elseif m == 2 then
    for v = 1, N do self:voice_off(v) end
    local notes = { n }
    for _, c in ipairs(self.ch) do if c ~= 0 then notes[#notes + 1] = n + c end end
    for i, x in ipairs(notes) do if i <= N then self:voice_on(i, x, vel, slide); vs[#vs + 1] = { i, x } end end
  else
    local v = self:pick(); self:voice_on(v, n, vel, slide); vs[1] = { v, n }
  end
  self.held[n] = vs
end

function ip:in_1_off(at)
  local n = tonumber(at[1]) or -1
  if self.mode == 0 then self:outlet(1, "off", { n }); return end
  local vs = self.held[n]
  self.held[n] = nil
  if not vs then return end
  for _, p in ipairs(vs) do
    -- only if that voice is still on the note this key gave it (a later key may have taken it)
    if self.vnote[p[1]] == p[2] and self.age[p[1]] then
      local still = true
      for k, other in pairs(self.held) do for _, q in ipairs(other) do if q[1] == p[1] and q[2] == p[2] then still = false end end end
      if still then self:voice_off(p[1]) end
    end
  end
end

function ip:in_1_panic()
  for v = 1, N do self:voice_off(v); self:outlet(v, "panic", {}) end
  self.held = {}
end
