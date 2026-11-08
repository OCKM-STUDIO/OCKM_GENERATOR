-- The samples part (v1.38; it was the spoken-lines shuffler). A row of steps, like the other parts.
-- Each step holds a sample number (table ockm-pat-vox-smp, 0 = nothing) and an effect (ockm-pat-vox-fx:
-- 0 off, 1 stutter, 2 delay, 3 verb). A step with a sample starts it. It plays to its end: only the next
-- sample or stopping the transport cuts it. The player is ockm-voxplay.
--
-- Sample numbers:
--   1 to 96   the spoken lines: set * 32 + voice * 16 + line (set 0 hooks, 1 jack, 2 techno; voice 0 deep, 1 flat; line 1-16)
--   1001 on   your own files: 1000 * g + n is the nth audio file (name order) in samples/user/voice (g 1),
--             loops (g 2) or hits (g 3)
--
-- ockm-vox-len is the part's length in steps (16 to 256). Shorter than the loop, it repeats inside it.
-- ockm-smp-play <sample> <effect> plays one now (the screen's audition).
-- The old vox settings (set, voice, every, pick, on, seed) are still sent by old scenes and styles: they're heard and ignored.

local vox = pd.Class:new():register("ockm-vox")

local SETS = { "hooks", "jack", "techno" }
local VOICES = { "deep", "flat" }
local SMP, FX = "ockm-pat-vox-smp", "ockm-pat-vox-fx"
local USER = { "voice", "loops", "hits" }

-- the path or user number for a sample: returns kind ("vox" or "user"), value
local function where(id)
  id = math.floor(id)
  if id >= 1 and id <= 96 then
    local k = id - 1
    local set = SETS[(k // 32) + 1]
    local voice = VOICES[((k % 32) // 16) + 1]
    return "vox", string.format("vox/%s/%s/%02d.wav", set, voice, (k % 16) + 1)
  elseif id >= 1001 and id < 4000 then
    return "user", { USER[id // 1000], id % 1000 }
  end
  return nil
end
vox.where = where

function vox:initialize()
  self.inlets, self.outlets = 0, 0
  self.len, self.stepms, self.playing = 16, 125, 0
  self.pending = nil
  return true
end

function vox:postinitialize()
  self.recv = {}
  local function on(name, fn)
    local m = "r_" .. #self.recv
    self[m] = function(o, sel, at)
      if sel == "bang" then fn({}) else fn(at or {}) end
    end
    self.recv[#self.recv + 1] = pd.Receive:new():register(self, name, m)
  end
  local function num(a, i) return tonumber(a[i or 1]) or 0 end
  on("ockm-step", function(a) self:step(num(a)) end)
  on("ockm-vox-len", function(a)
    local l = math.floor(num(a))
    self.len = math.max(16, math.min(256, l))
  end)
  on("ockm-stepms", function(a) local m = num(a); if m > 0 then self.stepms = m end end)
  on("ockm-playing", function(a)
    self.playing = (num(a) ~= 0) and 1 or 0
    if self.playing == 0 then self.pending = nil; if self.clock then self.clock:unset() end end
  end)
  on("ockm-vox-extend", function(a) self:extend(num(a, 1), num(a, 2)) end)
  on("ockm-smp-play", function(a) self:fire(num(a, 1), num(a, 2)) end)
  on("ockm-smp-count", function() self.loaded = nil end)   -- the folder was read again: numbers may point at other files
  -- old scenes and styles: heard, and nothing happens (no steps are made up from them)
  for _, k in ipairs({ "ockm-vox-set", "ockm-vox-voice", "ockm-vox-every", "ockm-vox-pick", "ockm-vox-on", "ockm-vox-seed", "ockm-vox-stut" }) do
    on(k, function() end)
  end
  self.clock = pd.Clock:new():register(self, "late")
end

function vox:finalize()
  for _, r in ipairs(self.recv or {}) do r:destruct() end
  if self.clock then self.clock:destruct() end
end

local function tab(name)
  local t = pd.Table:new():sync(name)
  return t
end

-- the engine plays a quarter step behind the step message: start the sample with it
function vox:step(s)
  local i = math.floor(s) % self.len
  local ts, tf = tab(SMP), tab(FX)
  if not ts then return end
  local id = ts:get(i) or 0
  if id <= 0 then return end
  local fx = tf and tf:get(i) or 0
  self.pending = { id, fx }
  local ms = self.stepms
  if pd.getvalue then ms = tonumber(pd.getvalue("ockm_stepms")) or ms end
  if ms <= 0 then ms = self.stepms end
  self.clock:delay(ms * 0.25)
end

function vox:late()
  local p = self.pending
  self.pending = nil
  if p then self:fire(p[1], p[2]) end
end

function vox:fire(id, fx)
  local kind, v = where(id)
  if not kind then return end
  fx = math.floor(fx or 0)
  pd.send("ockm-smp-stut", "float", { fx == 1 and 1 or 0 })
  pd.send("ockm-smp-fx", "float", { fx })
  pd.send("ockm-vox-which", "float", { math.floor(id) })
  -- the same file as last time is already in the player: play it again without reading the disc (long loops)
  local key = kind .. ":" .. ((type(v) == "table") and (v[1] .. "/" .. v[2]) or tostring(v))
  if key == self.loaded then
    pd.send("ockm-smp-again", "bang", {})
  elseif kind == "vox" then
    self.loaded = key
    pd.send("ockm-vox-load", "symbol", { v })
  else
    self.loaded = key
    pd.send("ockm-smp-user", "list", v)
  end
end

-- the part got longer: repeat its steps into the new ones (old is how far it had reached)
function vox:extend(old, new)
  old, new = math.floor(old), math.floor(new)
  if old < 1 or new <= old then return end
  for _, name in ipairs({ SMP, FX }) do
    local t = tab(name)
    if t then
      for i = old, math.min(new, t:length()) - 1 do t:set(i, t:get(i % old)) end
      t:redraw()
    end
  end
end
