-- A groovebox part's notes into one of the synths (v1.45): the Bass synth on the bass part, the Analog on the lead.
--
-- [ockm-partvoice]
-- Inlet: what the part's sequencer sends its engine: <note> <accent> <glide> <hold> (a list), off (stop), panic
-- Outlet: what a synth takes: note <n> <velocity> <slide>, off <n>, panic
-- An accent goes in at velocity 120 (the synths' accent starts at 100), a plain note at 90. A glide slides from the note
-- before without letting it go. A held step doesn't let go; otherwise the note lets go after just over half a step,
-- as the groovebox's own engines do.

local pv = pd.Class:new():register("ockm-partvoice")

function pv:initialize()
  self.inlets, self.outlets = 1, 1
  self.cur = nil
  self.stepms = 125
  return true
end

function pv:postinitialize()
  self.clock = pd.Clock:new():register(self, "release")
end

function pv:finalize()
  if self.clock then self.clock:destruct() end
end

function pv:release()
  if self.cur then self:outlet(1, "off", { self.cur }); self.cur = nil end
end

function pv:in_1_list(a)
  local n = math.floor(tonumber(a[1]) or 0)
  if n <= 0 then return end
  local acc, glide, hold = tonumber(a[2]) or 0, tonumber(a[3]) or 0, tonumber(a[4]) or 0
  local vel = (acc > 0) and 120 or 90
  self.clock:unset()
  if self.cur and glide > 0 then
    self:outlet(1, "note", { n, vel, 1 })
    if self.cur ~= n then self:outlet(1, "off", { self.cur }) end
  else
    if self.cur then self:outlet(1, "off", { self.cur }) end
    self:outlet(1, "note", { n, vel, 0 })
  end
  self.cur = n
  if hold <= 0 then
    local ms = self.stepms
    if pd.getvalue then ms = tonumber(pd.getvalue("ockm_stepms")) or ms end
    self.clock:delay(ms * 0.55)
  end
end
function pv:in_1_float(n) self:in_1_list({ n, 0, 0, 0 }) end

function pv:in_1_off() self.clock:unset(); self:release() end

function pv:in_1_panic()
  self.clock:unset()
  self.cur = nil
  self:outlet(1, "panic", {})
end
