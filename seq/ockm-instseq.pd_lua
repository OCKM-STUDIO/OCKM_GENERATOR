-- The instruments' sequencer and generator (v1.39): one per instrument.
--
-- [ockm-instseq <prefix>]   prefix: ib (Bass) or ia (Analog). Its steps live in tables:
--   ockm-pat-<prefix>-on     0 rest, 1 a note
--   ockm-pat-<prefix>-note   the MIDI note
--   ockm-pat-<prefix>-acc    1 accent
--   ockm-pat-<prefix>-slide  1 slide into this step from the one before (no gap, a glide)
--   ockm-pat-<prefix>-mod    0 to 1: the filter move on this step (the modulation track: up to 3 octaves open)
-- Listens to:
--   ockm-step, ockm-playing, ockm-stepms   the groovebox's clock (one tempo for everything)
--   <prefix>-len      16, 32 or 64 steps
--   <prefix>-on       1 while its instrument is picked: then it plays its steps with the transport
--   <prefix>-gen      bang: write a new pattern. Its settings:
--     <prefix>-gstyle   0 acid, 1 rolling, 2 offbeat, 3 octaves, 4 sparse
--     <prefix>-gbusy, -grange, -gacc, -gslide   0 to 1
--   <prefix>-mutate   bang: change about a fifth of the steps
--   ockm-root, ockm-scale   the key it writes in (the groovebox's)
--   <prefix>-play     a key from a keyboard: note <n> <vel> / off <n>. Straight to the sound, or into the arpeggiator
--   <prefix>-arp      0 off, 1 up, 2 down, 3 up and down, 4 random: held keys play one at a time, a 16th apart
--   <prefix>-arp-oct  1, 2 or 3 octaves
-- Sends <prefix>-note (note n vel slide / off n) and <prefix>-cutmod (the step's filter move).

local sq = pd.Class:new():register("ockm-instseq")

local SCALES = { { 0, 2, 3, 5, 7, 8, 10 }, { 0, 2, 4, 5, 7, 9, 11 }, { 0, 2, 3, 5, 7, 9, 10 }, { 0, 1, 3, 5, 7, 8, 10 }, { 0, 2, 4, 5, 7, 9, 10 }, { 0, 2, 3, 5, 7, 8, 11 } }
local MAXS = 64

function sq:initialize(sel, atoms)
  self.inlets, self.outlets = 1, 0
  self.pre = tostring(atoms[1] or "ib")
  self.base = (self.pre == "ib") and 33 or 57      -- A1 for the bass, A3 for the analog, moved by the key
  self.len, self.run, self.playing, self.stepms = 16, 0, 0, 125
  self.g = { style = 0, busy = 0.6, range = 0.4, acc = 0.4, slide = 0.25 }
  self.root, self.scale = 9, 0
  self.seed = os.time() % 100000
  self.sounding = nil
  self.arp, self.arpoct, self.keys, self.apos, self.adir = 0, 1, {}, 0, 1
  return true
end

function sq:postinitialize()
  self.recv = {}
  local function on(name, fn)
    local m = "r_" .. #self.recv
    self[m] = function(o, sel, at) fn(at or {}, sel) end
    self.recv[#self.recv + 1] = pd.Receive:new():register(self, name, m)
  end
  local p = self.pre
  local function num(a, d) return tonumber(a[1]) or d end
  on("ockm-step", function(a) self:step(num(a, 0)) end)
  on("ockm-playing", function(a) self.playing = num(a, 0); if self.playing == 0 then self:silence() end end)
  on("ockm-stepms", function(a) local m = num(a, 0); if m > 0 then self.stepms = m end end)
  on("ockm-root", function(a) self.root = math.floor(num(a, 9)) % 12 end)
  on("ockm-scale", function(a) self.scale = math.floor(num(a, 0)) end)
  on(p .. "-len", function(a) local l = math.floor(num(a, 16)); self.len = (l >= 64) and 64 or ((l >= 32) and 32 or 16) end)
  on(p .. "-on", function(a) self.run = num(a, 0); if self.run == 0 then self:silence() end end)   -- plays while its instrument is on
  on(p .. "-gstyle", function(a) self.g.style = math.floor(num(a, 0)) end)
  on(p .. "-gbusy", function(a) self.g.busy = num(a, 0.6) end)
  on(p .. "-grange", function(a) self.g.range = num(a, 0.4) end)
  on(p .. "-gacc", function(a) self.g.acc = num(a, 0.4) end)
  on(p .. "-gslide", function(a) self.g.slide = num(a, 0.25) end)
  on(p .. "-gen", function() self:generate() end)
  on(p .. "-mutate", function() self:mutate() end)
  on(p .. "-arp", function(a) self.arp = math.floor(num(a, 0)); if self.arp == 0 then self:arp_stop() end end)
  on(p .. "-arp-oct", function(a) self.arpoct = math.max(1, math.min(3, math.floor(num(a, 1)))) end)
  on(p .. "-play", function(a, sel) self:key(sel, a) end)   -- (not -key: that is the filter's key tracking)
  self.arpclock = pd.Clock:new():register(self, "arp_free")
  self.clock = pd.Clock:new():register(self, "late")
  self.offclock = pd.Clock:new():register(self, "gate_off")
end

function sq:finalize()
  for _, r in ipairs(self.recv or {}) do r:destruct() end
  if self.clock then self.clock:destruct() end
  if self.offclock then self.offclock:destruct() end
  if self.arpclock then self.arpclock:destruct() end
end

local function tab(name) local t = pd.Table:new(); if t:sync(name) then return t end return nil end
function sq:t(f) return tab("ockm-pat-" .. self.pre .. "-" .. f) end
function sq:get(f, i) local t = self:t(f); if t and i < t:length() then return t:get(i) or 0 end return 0 end
function sq:set(f, i, v) local t = self:t(f); if t and i < t:length() then t:set(i, v) end end
function sq:redraw() for _, f in ipairs({ "on", "note", "acc", "slide", "mod" }) do local t = self:t(f); if t then t:redraw() end end end

function sq:silence()
  if self.clock then self.clock:unset() end
  if self.offclock then self.offclock:unset() end
  if self.sounding then pd.send(self.pre .. "-note", "off", { self.sounding }); self.sounding = nil end
end

-- ---------------------------------------------------------------- keys and the arpeggiator
function sq:key(sel, a)
  local n, v = math.floor(tonumber(a[1]) or 0), tonumber(a[2]) or 0
  local down = (sel == "note" and v > 0)
  if self.arp <= 0 then
    if down then pd.send(self.pre .. "-note", "note", { n, v }) else pd.send(self.pre .. "-note", "off", { n }) end
    return
  end
  for i = #self.keys, 1, -1 do if self.keys[i] == n then table.remove(self.keys, i) end end
  if down then
    self.keys[#self.keys + 1] = n
    -- stopped: the arpeggiator runs on its own clock. Playing: it follows the steps
    -- a few ms' wait first, so the keys of a chord pressed together all count from the first note
    if #self.keys == 1 and self.playing == 0 then self.apos = 0; self.arpclock:delay(6) end
  elseif #self.keys == 0 then self:arp_stop() end
end
function sq:arp_notes()
  local ks = {}
  for _, k in ipairs(self.keys) do ks[#ks + 1] = k end
  table.sort(ks)
  local all = {}
  for o = 0, self.arpoct - 1 do for _, k in ipairs(ks) do all[#all + 1] = k + 12 * o end end
  return all
end
function sq:arp_tick()
  local all = self:arp_notes()
  if #all == 0 then return end
  local n
  if self.arp == 4 then n = all[math.floor(self:rand() * #all) + 1]
  elseif self.arp == 2 then n = all[#all - (self.apos % #all)]
  elseif self.arp == 3 and #all > 1 then
    local cyc = 2 * #all - 2
    local p = self.apos % cyc
    n = (p < #all) and all[p + 1] or all[cyc - p + 1]
  else n = all[(self.apos % #all) + 1] end
  self.apos = self.apos + 1
  if self.sounding then pd.send(self.pre .. "-note", "off", { self.sounding }) end
  pd.send(self.pre .. "-note", "note", { n, 95 })
  self.sounding = n
  self.offclock:unset(); self.offclock:delay(self.stepms * 0.5)
end
function sq:arp_free()
  if self.arp <= 0 or #self.keys == 0 or self.playing ~= 0 then return end
  self:arp_tick()
  self.arpclock:delay(self.stepms)
end
function sq:arp_stop()
  self.keys = {}
  if self.arpclock then self.arpclock:unset() end
  self:gate_off()
end

-- a quarter step late, like the rest of the engine
function sq:step(s)
  if self.arp > 0 and #self.keys > 0 and self.playing ~= 0 then   -- the arpeggiator, in time with the transport
    local ms = self.stepms
    if pd.getvalue then ms = tonumber(pd.getvalue("ockm_stepms")) or ms end
    self.stepms = ms; self.arp_due = true; self.clock:delay(ms * 0.25)
    return
  end
  if self.run <= 0 or self.playing == 0 then return end
  self.pending = math.floor(s) % self.len
  local ms = self.stepms
  if pd.getvalue then ms = tonumber(pd.getvalue("ockm_stepms")) or ms end
  self.ms = ms
  self.clock:delay(ms * 0.25)
end

function sq:late()
  if self.arp_due then self.arp_due = false; self:arp_tick(); return end
  local i = self.pending
  if i == nil then return end
  pd.send(self.pre .. "-cutmod", "float", { self:get("mod", i) })
  if self:get("on", i) <= 0 then return end
  local n = math.floor(self:get("note", i))
  local slide = self:get("slide", i) > 0 and 1 or 0
  local vel = self:get("acc", i) > 0 and 115 or 90
  if self.sounding and slide == 0 then pd.send(self.pre .. "-note", "off", { self.sounding }) end
  if self.sounding and slide == 1 and self.sounding == n then
    -- a slide onto the same note: just hold on
  else
    pd.send(self.pre .. "-note", "note", { n, vel, slide })
  end
  self.sounding = n
  self.offclock:unset()
  -- the next step slides from this one: no gap. Otherwise the note lets go after half a step
  local nx = (i + 1) % self.len
  if not (self:get("on", nx) > 0 and self:get("slide", nx) > 0) then self.offclock:delay((self.ms or self.stepms) * 0.55) end
end

function sq:gate_off()
  if self.sounding then pd.send(self.pre .. "-note", "off", { self.sounding }); self.sounding = nil end
end

-- ---------------------------------------------------------------- the generator
function sq:rand() self.seed = (1103515245 * self.seed + 12345) % 2147483648; return self.seed / 2147483648 end

-- a scale step (0 is the root, 7 the octave) as a MIDI note in this instrument's register
function sq:degree(d)
  local sc = SCALES[(self.scale % #SCALES) + 1]
  local oct = math.floor(d / 7)
  local root = self.base - 9 + self.root
  return root + oct * 12 + sc[(d % 7) + 1]
end

function sq:pick_degree()
  local g = self.g
  local span = 1 + math.floor(g.range * 9)   -- how far from the root, in scale steps
  local r = self:rand()
  if r < 0.45 - g.range * 0.25 then return 0 end                  -- the root, most of all
  if r < 0.6 then return (self:rand() < 0.5) and 7 or 0 end        -- or its octave
  return math.floor(self:rand() * (span + 1)) - math.floor(span / 3)
end

function sq:generate()
  local g, L = self.g, self.len
  for i = 0, MAXS - 1 do
    local s = i % 16
    local on, d = 0, 0
    local busy = g.busy
    if g.style == 0 then        -- acid: busy 16ths, jumping about, accents and slides
      on = (self:rand() < 0.35 + busy * 0.6) and 1 or 0
      d = self:pick_degree()
    elseif g.style == 1 then    -- rolling: the off-16ths, around the root
      on = ((s % 4 ~= 0) and self:rand() < 0.6 + busy * 0.4) and 1 or 0
      d = (self:rand() < 0.75) and 0 or self:pick_degree()
    elseif g.style == 2 then    -- offbeat: the classic house bass on the "and"
      on = (s % 4 == 2 or (busy > 0.6 and s % 4 == 3 and self:rand() < busy - 0.5)) and 1 or 0
      d = (self:rand() < 0.7) and 0 or self:pick_degree()
    elseif g.style == 3 then    -- octaves: 8ths, root and octave in turn
      on = (s % 2 == 0 and self:rand() < 0.7 + busy * 0.3) and 1 or 0
      d = (s % 4 == 0) and 0 or 7
      if self:rand() < g.range * 0.4 then d = d + self:pick_degree() end
    else                        -- sparse: a few long notes that slide
      on = (s == 0 or self:rand() < busy * 0.25) and 1 or 0
      d = self:pick_degree()
    end
    if s == 0 and g.style ~= 1 then on = 1 end   -- something on the one
    -- later bars answer the first: the same, with a few notes moved
    if i >= 16 and i < L then
      local src = i % 16
      if self:rand() > 0.3 then on = self:get("on", src); d = nil end
    end
    local n = d and self:degree(d) or self:get("note", i % 16)
    self:set("on", i, on)
    self:set("note", i, n)
    self:set("acc", i, (on > 0 and self:rand() < g.acc * 0.6) and 1 or 0)
    local sl = (on > 0 and i > 0 and self:rand() < g.slide * ((g.style == 4) and 0.9 or 0.5)) and 1 or 0
    self:set("slide", i, sl)
    -- the filter move: a gentle rise and fall over the bar, with the accents a little higher
    self:set("mod", i, math.max(0, math.min(1, 0.15 + 0.12 * math.sin((i % 16) / 16 * 2 * math.pi) + 0.12 * self:get("acc", i))))
  end
  self:redraw()
  -- (no message back: a send from inside a send trips up pdlua; the screen redraws on its own)
end

function sq:mutate()
  for i = 0, self.len - 1 do
    if self:rand() < 0.2 then
      local d = self:pick_degree()
      self:set("note", i, self:degree(d))
      if self:rand() < 0.3 then self:set("on", i, 1 - self:get("on", i)) end
      if self:rand() < 0.25 then self:set("acc", i, 1 - self:get("acc", i)) end
    end
  end
  self:redraw()
  -- (no message back: a send from inside a send trips up pdlua; the screen redraws on its own)
end

function sq:in_1_seed(at) self.seed = math.floor(tonumber(at[1]) or self.seed) end
