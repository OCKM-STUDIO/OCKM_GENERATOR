-- OCKM Drum Lab brain: plays the clap and snare (their envelopes), randomises around the sound you have,
-- loops them against a kick, and renders a hit to a WAV in samples/clap or samples/snare.
-- Written by tools/build_lab.py: change it there.
local lab = pd.Class:new():register("ockm-lab")
local PARAMS = { clap = { { "bursts", 1, 6, 4 }, { "gap", 4, 25, 10 }, { "jitter", 0, 1, 0.3 }, { "bdecay", 2, 15, 6 }, { "toneA", 600, 2500, 1150 }, { "toneB", 1500, 6000, 2600 }, { "width", 0.5, 6, 2.2 }, { "balance", 0, 1, 0.4 }, { "tail", 30, 600, 180 }, { "tailtone", 500, 3000, 1200 }, { "room", 0, 0.9, 0.35 }, { "drive", 0, 1, 0.35 }, { "level", 0, 1, 0.8 } }, snare = { { "pitch", 120, 320, 190 }, { "ratio", 1.2, 2.2, 1.6 }, { "drop", 0, 12, 5 }, { "droptime", 5, 60, 20 }, { "bodydec", 30, 300, 110 }, { "wires", 1500, 8000, 3800 }, { "wwidth", 0.3, 3, 0.9 }, { "wdecay", 40, 400, 170 }, { "click", 0, 1, 0.4 }, { "mix", 0, 1, 0.55 }, { "drive", 0, 1, 0.3 }, { "level", 0, 1, 0.8 } } }

function lab:initialize(sel, atoms)
  self.inlets, self.outlets = 1, 0
  self.v = { clap = {}, snare = {} }
  for which, list in pairs(PARAMS) do for _, p in ipairs(list) do self.v[which][p[1]] = p[4] end end
  self.loop = { clap = false, snare = false }
  self.beat = 0
  math.randomseed(os.time())
  return true
end

function lab:postinitialize()
  self.recv = {}
  local function listen(name, fn)
    local m = "r_" .. #self.recv
    self[m] = fn
    self.recv[#self.recv + 1] = pd.Receive:new():register(self, name, m)
  end
  for which, list in pairs(PARAMS) do
    for _, p in ipairs(list) do
      listen("lab-" .. which .. "-" .. p[1], function(o, sel, a) local x = tonumber(a[1]); if x then o.v[which][p[1]] = x end end)
    end
    listen("lab-" .. which .. "-play", function(o) o:play(which) end)
    listen("lab-" .. which .. "-render", function(o) o:render(which) end)
    listen("lab-" .. which .. "-loop", function(o, sel, a) o.loop[which] = (tonumber(a[1]) or 0) > 0; o:loop_check() end)
    listen("lab-" .. which .. "-reset", function(o) o:reset(which) end)
    for k, amt in pairs({ small = 0.12, medium = 0.35, wild = 1 }) do
      listen("lab-" .. which .. "-rand-" .. k, function(o) o:randomise(which, amt) end)
    end
  end
  listen("lab-test", function(o, sel, a) o:test(sel, a) end)
  self.stopclock = pd.Clock:new():register(self, "render_stop")
  self.loopclock = pd.Clock:new():register(self, "loop_tick")
  self.initclock = pd.Clock:new():register(self, "push_all")
  self.initclock:delay(0)
end

function lab:finalize()
  for _, r in ipairs(self.recv or {}) do r:destruct() end
  for _, c in ipairs({ self.stopclock, self.loopclock, self.initclock }) do if c then c:destruct() end end
end

-- every setting out to the sliders (which pass it on to the sound)
function lab:push_all()
  for which, list in pairs(PARAMS) do for _, p in ipairs(list) do self:set(which, p[1], self.v[which][p[1]]) end end
end
function lab:set(which, name, x)
  self.v[which][name] = x
  pd.send("lab-" .. which .. "-" .. name .. "-ui", "float", { x })
end
function lab:reset(which)
  for _, p in ipairs(PARAMS[which]) do self:set(which, p[1], p[4]) end
  self:status(which .. ": back to the starting sound")
end

local function seg(name, target, time, delay) pd.send(name, "list", { target, time, delay }) end

function lab:play(which)
  local v = self.v[which]
  if which == "clap" then
    -- the bursts: each a quick hit of the two noise colours, a gap apart (looser with jitter); then the tail
    local t, n = 0, math.max(1, math.floor(v.bursts + 0.5))
    seg("lab-clap-burst", 0, 0, 0); seg("lab-clap-tailenv", 0, 0, 0)
    for b = 1, n do
      seg("lab-clap-burst", 1, 0.3, t)
      seg("lab-clap-burst", 0, v.bdecay, t + 0.3)
      if b < n then t = t + v.gap * (1 + v.jitter * (math.random() - 0.5)) end
    end
    seg("lab-clap-tailenv", 1, 1, t)
    seg("lab-clap-tailenv", 0, v.tail, t + 1)
  else
    seg("lab-snare-freq", v.pitch * 2 ^ (v.drop / 12), 0, 0); seg("lab-snare-freq", v.pitch, v.droptime, 0)
    seg("lab-snare-body", 0, 0, 0); seg("lab-snare-body", 1, 0.5, 0); seg("lab-snare-body", 0, v.bodydec, 0.5)
    seg("lab-snare-wenv", 0, 0, 0); seg("lab-snare-wenv", 1, 0.5, 0); seg("lab-snare-wenv", 0, v.wdecay, 0.5)
    seg("lab-snare-cenv", 0, 0, 0); seg("lab-snare-cenv", 1, 0.1, 0); seg("lab-snare-cenv", 0, 3, 0.1)
  end
end

-- how long a hit lasts, so a render catches all of it
function lab:length(which)
  local v = self.v[which]
  if which == "clap" then return math.min(2500, v.bursts * v.gap * 1.5 + v.tail * 1.6 + v.room * 400 + 60) end
  return math.min(2000, math.max(v.bodydec, v.wdecay) * 1.6 + 60)
end

-- small, medium or wild: each setting moves at random within that share of its range
function lab:randomise(which, amt)
  for _, p in ipairs(PARAMS[which]) do
    local name, lo, hi = p[1], p[2], p[3]
    if name ~= "level" then
      local x = self.v[which][name]
      if amt >= 1 then x = lo + math.random() * (hi - lo)
      else x = x + (math.random() * 2 - 1) * amt * (hi - lo) end
      x = math.max(lo, math.min(hi, x))
      if name == "bursts" then x = math.floor(x + 0.5) end
      self:set(which, name, x)
    end
  end
  self:play(which)
  self:status(which .. ": randomised (" .. ((amt >= 1) and "wild" or ((amt > 0.2) and "medium" or "small")) .. ")")
end

-- loop: a kick on every beat, the clap or snare on 2 and 4, at 120
function lab:loop_check()
  local on = self.loop.clap or self.loop.snare
  if on and not self.looping then self.looping = true; self.beat = 0; self:loop_tick()
  elseif not on then self.looping = false; self.loopclock:unset() end
end
function lab:loop_tick()
  if not self.looping or self.rendering then return end
  pd.send("lab-kick", "float", { 1 })
  if self.beat % 2 == 1 then
    if self.loop.clap then self:play("clap") end
    if self.loop.snare then self:play("snare") end
  end
  self.beat = (self.beat + 1) % 4
  self.loopclock:delay(500)
end

-- render: record one hit to samples/<clap or snare>/lab-<which>-<date and time>.wav (24-bit mono)
function lab:render(which)
  if self.rendering then return end
  local folder = (which == "clap") and "clap" or "snare"
  local name = "lab-" .. which .. "-" .. os.date("%Y%m%d-%H%M%S") .. ".wav"
  self.rendering = { which = which, path = "samples/" .. folder .. "/" .. name }
  pd.send("lab-rec", "open", { "-bytes", 3, self.rendering.path })
  pd.send("lab-rec", "start", {})
  self:play(which)
  self.stopclock:delay(self:length(which))
end
function lab:render_stop()
  local r = self.rendering
  if not r then return end
  pd.send("lab-rec", "stop", {})
  self.rendering = nil
  self:status("saved " .. r.path)
  pd.post("ockm-lab: saved " .. r.path)
  if self.looping then self.loopclock:delay(500) end
end
function lab:status(s) pd.send("lab-status", "symbol", { s }) end

-- headless tests
function lab:test(sel, a)
  if sel == "set" then self:set(tostring(a[1]), tostring(a[2]), tonumber(a[3]))
  elseif sel == "dump" then
    for which, list in pairs(PARAMS) do for _, p in ipairs(list) do pd.post(string.format("ockm-lab: %s %s %.3f", which, p[1], self.v[which][p[1]])) end end
  end
end
