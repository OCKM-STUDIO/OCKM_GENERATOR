-- The note brain for the instruments (v1.39): Bass and Analog. Notes in, envelope and pitch moves out, as
-- vline~ messages, so the sound side in Pd stays simple. One per voice.
--
-- [ockm-instvoice <kind> <prefix>]   kind: bass or analog. prefix: where its settings arrive (<prefix>-attack ...)
--
-- Inlet:
--   note <midi> <velocity 0-127> [slide 0/1]   a key down, or a step
--   off <midi>                                 a key up (a step's end)
--   panic                                      everything off, now
-- Outlets (vline~ messages unless said):
--   1 pitch, in MIDI notes (glides on slides, or always on analog with glide up)
--   2 amp envelope, 0 to 1
--   3 filter envelope, 0 to 1
--   4 pitch envelope, 1 falling to 0 (bass: the zap)
--   5 accent, a float: 0 or 1
--
-- Settings (0 to 1 unless said), from <prefix>-<name>:
--   attack, decay, sustain, release   the envelope. Bass: decay is the amp's, sustain 0 in decay mode
--   fdecay                            bass: the filter envelope's own decay
--   pdecay                            bass: the pitch envelope's decay
--   amode                             0 decay (it fades by itself), 1 gate (held while the key is)
--   glide                             0 to 1: glide time
-- Mono with last-note priority: hold one key, press another, it glides there without starting the envelopes again.

local iv = pd.Class:new():register("ockm-instvoice")

local function ms_attack(x) return 1 + 1999 * x * x * x end        -- 1 ms to 2 s, most of the travel short
local function ms_decay(x) return 15 + 3985 * x * x end            -- 15 ms to 4 s
local function ms_release(x) return 5 + 2995 * x * x end           -- 5 ms to 3 s
local function ms_glide(x) return 400 * x * x end                  -- 0 to 400 ms

function iv:initialize(sel, atoms)
  self.inlets, self.outlets = 1, 5
  self.kind = tostring(atoms[1] or "bass")
  self.prefix = tostring(atoms[2] or "inst")
  self.p = { attack = 0.02, decay = 0.35, sustain = 0, release = 0.15, fdecay = 0.35, pdecay = 0.15, amode = 0, glide = 0.3 }
  if self.kind == "analog" then self.p.sustain, self.p.decay, self.p.glide = 0.6, 0.4, 0 end
  self.held = {}      -- keys down, in order
  self.cur = nil      -- the note sounding
  return true
end

function iv:postinitialize()
  self.recv = {}
  for name in pairs(self.p) do
    local m = "set_" .. name
    self[m] = function(o, sel, at) o.p[name] = tonumber(at and at[1]) or o.p[name] end
    self.recv[#self.recv + 1] = pd.Receive:new():register(self, self.prefix .. "-" .. name, m)
  end
end

function iv:finalize() for _, r in ipairs(self.recv or {}) do r:destruct() end end

function iv:in_1_set(at) local k = tostring(at[1]); if self.p[k] ~= nil then self.p[k] = tonumber(at[2]) or self.p[k] end end

-- the amp envelope from where it is now: up over attack, down to sustain over decay
function iv:amp_on(acc)
  local p = self.p
  local a, d = ms_attack(p.attack), ms_decay(p.decay)
  local top = acc > 0 and 1 or 0.8
  local s = (p.amode >= 0.5) and top or p.sustain * top
  if self.kind == "bass" and p.amode < 0.5 and acc > 0 then d = d * 0.7 end   -- an accent snaps, like the 303
  self:outlet(2, "list", { top, a })
  self:outlet(2, "list", { s, d, a })
end

function iv:filter_on(acc)
  local p = self.p
  local a = ms_attack(p.attack)
  local d = (self.kind == "bass") and ms_decay(p.fdecay) or ms_decay(p.decay)
  local s = (self.kind == "bass") and 0 or p.sustain
  if acc > 0 then d = math.min(d, 220) end   -- the accent sweep is short and sharp
  self:outlet(3, "list", { 1, a })
  self:outlet(3, "list", { s, d, a })
end

function iv:start(note, vel, slide)
  local acc = (vel >= 100) and 1 or 0
  local legato = self.cur ~= nil and (slide > 0 or #self.held > 1)
  local glide = 0
  if legato and (self.kind == "bass" or self.p.glide > 0) then glide = math.max(ms_glide(self.p.glide), slide > 0 and 30 or 0) end
  if self.kind == "analog" and self.cur ~= nil and self.p.glide > 0 then glide = ms_glide(self.p.glide) end
  self:outlet(5, "float", { acc })
  self:outlet(1, "list", { note, glide })
  if not legato then
    self:amp_on(acc)
    self:filter_on(acc)
    self:outlet(4, "list", { 1 })
    self:outlet(4, "list", { 0, ms_decay(self.p.pdecay) * 0.25 })
  end
  self.cur = note
end

function iv:release()
  local p = self.p
  local r = ms_release(p.release)
  if self.kind == "bass" and p.amode < 0.5 then r = math.max(r, 30) end
  self:outlet(2, "list", { 0, r })
  if self.kind == "analog" then self:outlet(3, "list", { 0, r }) end
  self.cur = nil
end

function iv:in_1_note(at)
  local note, vel, slide = tonumber(at[1]) or 60, tonumber(at[2]) or 100, tonumber(at[3]) or 0
  if vel <= 0 then return self:in_1_off({ note }) end
  for i = #self.held, 1, -1 do if self.held[i] == note then table.remove(self.held, i) end end
  self.held[#self.held + 1] = note
  self:start(note, vel, slide)
end

function iv:in_1_off(at)
  local note = tonumber(at[1]) or -1
  for i = #self.held, 1, -1 do if self.held[i] == note then table.remove(self.held, i) end end
  if self.cur == nil then return end
  if #self.held > 0 then
    -- back to the key still held, gliding, no new envelope
    local back = self.held[#self.held]
    if back ~= self.cur then
      self:outlet(1, "list", { back, (self.p.glide > 0 or self.kind == "bass") and math.max(ms_glide(self.p.glide), 20) or 0 })
      self.cur = back
    end
    return
  end
  if note == self.cur or note < 0 then self:release() end
end

function iv:in_1_panic()
  self.held, self.cur = {}, nil
  self:outlet(2, "list", { 0, 5 }); self:outlet(3, "list", { 0, 5 })
end
