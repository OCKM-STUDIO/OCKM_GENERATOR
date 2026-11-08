-- [ockm-build]  v1.49 the 4 bar build: the drums play a build pattern (ockm-buildx, 8 drums x 64 steps) in place of
-- yours for four bars, then the drop. Hand-written: edit this file.
--   ockm-build 1   arms it: it starts on the next bar line (the bar a recipe's mutes land on)
--   ockm-build 2   the same with the rush pattern (the kick back in the last bar, the open hat on every 8th)
--   ockm-build 0   lets go at once
-- Outlet 1: 1 while the build plays (into v ockm_build_on), outlet 2: which of its four bars (0-3, into v ockm_build_bar),
-- outlet 3: which pattern (0 the build, 1 the rush; into v ockm_build_pat).
-- After its fourth bar it lets go by itself, on the bar line, before the drums read that bar's first step, so the
-- drop always lands on your own groove.
local b = pd.Class:new():register("ockm-build")

function b:initialize()
  self.inlets, self.outlets = 0, 3
  self.arm, self.on, self.bar, self.pat = false, false, 0, 0
  return true
end

function b:postinitialize()
  self.recv = {
    pd.Receive:new():register(self, "ockm-build", "r_build"),
    pd.Receive:new():register(self, "ockm-bar", "r_bar"),
    pd.Receive:new():register(self, "ockm-playing", "r_play"),
  }
end

function b:finalize()
  for _, r in ipairs(self.recv or {}) do r:destruct() end
end

function b:set(on, bar)
  self.on, self.bar = on, bar
  self:outlet(2, "float", { bar })
  self:outlet(1, "float", { on and 1 or 0 })
end

function b:r_build(sel, atoms)
  local x = tonumber((atoms or {})[1]) or 0
  if x ~= 0 then self.arm = true; self.pat = (x >= 2) and 1 or 0; self:outlet(3, "float", { self.pat })
  else self.arm = false; if self.on then self:set(false, 0) end end
end

function b:r_bar()
  if self.arm then self.arm = false; self:set(true, 0)
  elseif self.on then
    if self.bar >= 3 then self:set(false, 0) else self:set(true, self.bar + 1) end
  end
end

function b:r_play(sel, atoms)
  if (tonumber((atoms or {})[1]) or 0) == 0 then self.arm = false; if self.on then self:set(false, 0) end end
end
