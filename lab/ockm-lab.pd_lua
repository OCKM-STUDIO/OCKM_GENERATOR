-- OCKM Drum Lab brain: plays each sound (its envelopes), randomises around the sound you have, loops them
-- against a kick, and renders hits to WAVs in the samples folders. Sets (hats, toms, congas) render as matching files.
-- Written by tools/build_lab.py: change it there.
local lab = pd.Class:new():register("ockm-lab")
local KIT = {
  clap = { params = { { "bursts", 1, 6, 4 }, { "gap", 4, 25, 10 }, { "jitter", 0, 1, 0.3 }, { "bdecay", 2, 15, 6 }, { "toneA", 600, 2500, 1150 }, { "toneB", 1500, 6000, 2600 }, { "width", 0.5, 6, 2.2 }, { "balance", 0, 1, 0.4 }, { "tail", 30, 600, 180 }, { "tailtone", 500, 3000, 1200 }, { "room", 0, 0.9, 0.35 }, { "drive", 0, 1, 0.35 }, { "level", 0, 1, 0.8 } }, folder = "clap", variants = {  } },
  snare = { params = { { "pitch", 120, 320, 190 }, { "ratio", 1.2, 2.2, 1.6 }, { "drop", 0, 12, 5 }, { "droptime", 5, 60, 20 }, { "bodydec", 30, 300, 110 }, { "wires", 1500, 8000, 3800 }, { "wwidth", 0.3, 3, 0.9 }, { "wdecay", 40, 400, 170 }, { "click", 0, 1, 0.4 }, { "mix", 0, 1, 0.55 }, { "drive", 0, 1, 0.3 }, { "level", 0, 1, 0.8 } }, folder = "snare", variants = {  } },
  hat = { params = { { "pitch", 0.5, 2, 1 }, { "ring", 0, 1, 0.55 }, { "tone", 4000, 12000, 8000 }, { "focus", 0.4, 3, 1 }, { "bright", 3000, 10000, 6000 }, { "closed", 10, 120, 45 }, { "open", 150, 900, 420 }, { "drive", 0, 1, 0.25 }, { "level", 0, 1, 0.7 } }, folder = nil, variants = { { "closed", 1 }, { "open", 1 } } },
  kick = { params = { { "pitch", 35, 90, 48 }, { "sweep", 0, 48, 28 }, { "sweeptime", 5, 150, 35 }, { "decay", 80, 1200, 420 }, { "second", 0, 1, 0 }, { "ratio", 1.2, 3, 1.5 }, { "noise", 0, 1, 0.35 }, { "ntone", 1000, 8000, 3500 }, { "nfocus", 0.4, 3, 0.8 }, { "ndecay", 2, 40, 6 }, { "drive", 0, 1, 0.3 }, { "level", 0, 1, 0.8 } }, folder = "kick", variants = {  } },
  tom = { params = { { "pitch", 60, 300, 120 }, { "sweep", 0, 12, 5 }, { "sweeptime", 10, 150, 60 }, { "decay", 80, 900, 350 }, { "second", 0, 1, 0.3 }, { "ratio", 1.2, 2.5, 1.5 }, { "noise", 0, 1, 0.25 }, { "ntone", 500, 5000, 1800 }, { "nfocus", 0.4, 3, 1 }, { "ndecay", 5, 120, 40 }, { "drive", 0, 1, 0.25 }, { "level", 0, 1, 0.8 } }, folder = "tom", variants = { { "low", 0.75 }, { "mid", 1 }, { "high", 1.33 } } },
  conga = { params = { { "pitch", 150, 450, 220 }, { "sweep", 0, 7, 2 }, { "sweeptime", 5, 60, 20 }, { "decay", 60, 500, 220 }, { "second", 0, 1, 0.35 }, { "ratio", 1.3, 2.8, 1.6 }, { "noise", 0, 1, 0.4 }, { "ntone", 1500, 6000, 3000 }, { "nfocus", 0.5, 3, 1.2 }, { "ndecay", 3, 40, 12 }, { "drive", 0, 1, 0.2 }, { "level", 0, 1, 0.8 } }, folder = "perc", variants = { { "low", 1 }, { "high", 1.5 } } },
  rim = { params = { { "pitch", 300, 1200, 500 }, { "sweep", 0, 5, 0 }, { "sweeptime", 2, 20, 5 }, { "decay", 5, 80, 25 }, { "second", 0, 1, 0.7 }, { "ratio", 2, 4, 3.4 }, { "noise", 0, 1, 0.5 }, { "ntone", 1000, 8000, 3500 }, { "nfocus", 0.5, 4, 1.5 }, { "ndecay", 1, 15, 4 }, { "drive", 0, 1, 0.4 }, { "level", 0, 1, 0.8 } }, folder = "perc", variants = {  } },
  shaker = { params = { { "tone", 3000, 12000, 7000 }, { "focus", 0.4, 3, 1 }, { "lowcut", 1000, 8000, 3000 }, { "attack", 1, 40, 8 }, { "decay", 15, 250, 70 }, { "grit", 0, 1, 0.3 }, { "drive", 0, 1, 0.2 }, { "level", 0, 1, 0.75 } }, folder = "perc", variants = {  } }
}
local TUNED = { kick = true, tom = true, conga = true, rim = true }
local CHARACTER = { clap = { name = "room", w = { tail = 0.6, room = 0.7, jitter = 0.4, tailtone = -0.4, bdecay = 0.2 } }, snare = { name = "crack", w = { wires = 0.4, wdecay = 0.3, bodydec = -0.4, click = 0.6, drive = 0.4, mix = 0.4 } }, hat = { name = "metal", w = { ring = 0.7, focus = 0.5, bright = -0.4, tone = -0.2 } }, kick = { name = "punch", w = { sweep = 0.5, sweeptime = -0.5, noise = 0.6, decay = -0.3, drive = 0.3 } }, tom = { name = "boom", w = { pitch = -0.4, decay = 0.5, sweep = 0.4, noise = -0.4 } }, conga = { name = "slap", w = { noise = 0.6, ntone = 0.4, decay = -0.3, second = 0.4 } }, rim = { name = "wood", w = { ratio = -0.6, decay = 0.4, noise = -0.4, pitch = -0.2 } }, shaker = { name = "shake", w = { attack = 0.5, decay = 0.5, grit = 0.6, tone = -0.2 } } }
local MORPH_SCALE = { level = 0, pitch = 0.2, ratio = 0.25, bursts = 0.3, drive = 0.3, sweep = 0.3 }
local MORPH_POINTS = 4

local VEL_CURVE = { kick = 0.66, snare = 0.56, clap = 0.51, hat = 0.5, tom = 0.61, rim = 0.8, conga = 0.63, shaker = 0.65 }
local function seg(name, target, time, delay) pd.send(name, "list", { target, time, delay }) end
-- play one hit. pre: where the voice listens (lab-kick, ockm-d1-kick); v: its settings; var: which of a set
-- (hats 1 closed 2 open; toms low mid high; congas low high); vel: how hard (0 to 1)
local function play_voice(pre, which, v, var, vel, k)
  -- every voice squares its envelopes (for the curve) and its drive squashes loud hits, so each sound has a power
  -- that makes its loudness follow vel (a half-strength hit about half as loud), measured by the tests
  var, vel = var or 1, math.max(0, vel or 1) ^ (VEL_CURVE[which] or 0.6)
  if which == "hat" then
    seg(pre .. "-env", 0, 0, 0); seg(pre .. "-env", vel, 0.2, 0); seg(pre .. "-env", 0, (var == 2) and v.open or v.closed, 0.2)
  elseif which == "clap" then
    -- the bursts: each a quick hit of the two noise colours, a gap apart (looser with jitter); then the tail
    local t, n = 0, math.max(1, math.floor(v.bursts + 0.5))
    seg(pre .. "-burst", 0, 0, 0); seg(pre .. "-tailenv", 0, 0, 0)
    for b = 1, n do
      seg(pre .. "-burst", vel, 0.3, t)
      seg(pre .. "-burst", 0, v.bdecay, t + 0.3)
      if b < n then t = t + v.gap * (1 + v.jitter * (math.random() - 0.5)) end
    end
    seg(pre .. "-tailenv", vel, 1, t)
    seg(pre .. "-tailenv", 0, v.tail, t + 1)
  elseif which == "snare" then
    seg(pre .. "-freq", v.pitch * 2 ^ (v.drop / 12), 0, 0); seg(pre .. "-freq", v.pitch, v.droptime, 0)
    seg(pre .. "-body", 0, 0, 0); seg(pre .. "-body", vel, 0.5, 0); seg(pre .. "-body", 0, v.bodydec, 0.5)
    seg(pre .. "-wenv", 0, 0, 0); seg(pre .. "-wenv", vel, 0.5, 0); seg(pre .. "-wenv", 0, v.wdecay, 0.5)
    seg(pre .. "-cenv", 0, 0, 0); seg(pre .. "-cenv", vel, 0.1, 0); seg(pre .. "-cenv", 0, 3, 0.1)
  elseif which == "shaker" then
    seg(pre .. "-env", 0, 0, 0); seg(pre .. "-env", vel, v.attack, 0); seg(pre .. "-env", 0, v.decay, v.attack)
  else
    -- the tuned drums: kick, tom, conga, rim
    local mul = (k and k.variants[var] and k.variants[var][2]) or 1
    pd.send(pre .. "-mul", "float", { mul })
    seg(pre .. "-st", v.sweep, 0, 0); seg(pre .. "-st", 0, v.sweeptime, 0)
    seg(pre .. "-body", 0, 0, 0); seg(pre .. "-body", vel, 0.3, 0); seg(pre .. "-body", 0, v.decay, 0.3)
    seg(pre .. "-nenv", 0, 0, 0); seg(pre .. "-nenv", vel, 0.1, 0); seg(pre .. "-nenv", 0, v.ndecay, 0.1)
  end
end

function lab:initialize(sel, atoms)
  self.inlets, self.outlets = 1, 0
  self.v, self.loop = {}, {}
  for which, k in pairs(KIT) do
    self.v[which] = {}
    for _, p in ipairs(k.params) do self.v[which][p[1]] = p[4] end
    self.loop[which] = false
  end
  self.beat = 0
  math.randomseed(os.time())
  self.home, self.char, self.morph, self.path = {}, {}, {}, {}
  for which in pairs(KIT) do
    self.home[which] = {}; for n, x in pairs(self.v[which]) do self.home[which][n] = x end
    self.char[which], self.morph[which] = 0, 0
    self:new_path(which)
  end
  return true
end

function lab:postinitialize()
  self.recv = {}
  local function listen(name, fn)
    local m = "r_" .. #self.recv
    self[m] = fn
    self.recv[#self.recv + 1] = pd.Receive:new():register(self, name, m)
  end
  for which, k in pairs(KIT) do
    for _, p in ipairs(k.params) do
      -- a setting moved by hand becomes part of the sound (as if you'd pressed keep)
      listen("lab-" .. which .. "-" .. p[1], function(o, sel, a)
        local x = tonumber(a[1]); if not x then return end
        o.v[which][p[1]] = x
        if not o.applying then o:keep(which, true) end
      end)
    end
    listen("lab-" .. which .. "-play", function(o) o:play(which, 1) end)
    for i, var in ipairs(k.variants) do listen("lab-" .. which .. "-play-" .. var[1], function(o) o:play(which, i) end) end
    listen("lab-" .. which .. "-render", function(o) o:render(which) end)
    listen("lab-" .. which .. "-loop", function(o, sel, a) o.loop[which] = (tonumber(a[1]) or 0) > 0; o:loop_check() end)
    listen("lab-" .. which .. "-reset", function(o) o:reset(which) end)
    listen("lab-" .. which .. "-char", function(o, sel, a) o.char[which] = tonumber(a[1]) or 0; o:apply(which) end)
    listen("lab-" .. which .. "-morph", function(o, sel, a) o.morph[which] = tonumber(a[1]) or 0; o:apply(which) end)
    listen("lab-" .. which .. "-newpath", function(o) o:new_path(which); o:apply(which); o:play(which, 1); o:status(which .. ": a new morph path") end)
    listen("lab-" .. which .. "-keep", function(o) o:keep(which); o:status(which .. ": kept, this is the sound now") end)
    for name, amt in pairs({ small = 0.12, medium = 0.35, wild = 1 }) do
      listen("lab-" .. which .. "-rand-" .. name, function(o) o:randomise(which, amt) end)
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
  for which, k in pairs(KIT) do for _, p in ipairs(k.params) do self:set(which, p[1], self.v[which][p[1]]) end end
end
function lab:set(which, name, x)
  self.v[which][name] = x
  self.applying = true                               -- (the slider echoes it back: not a change by hand)
  pd.send("lab-" .. which .. "-" .. name .. "-ui", "float", { x })
  self.applying = false
end
function lab:reset(which)
  for _, p in ipairs(KIT[which].params) do self:set(which, p[1], p[4]) end
  self:keep(which)
  self:status(which .. ": back to the starting sound")
end

-- the two macro sliders. Home is the sound with both at zero; character moves its recipe of settings (either way);
-- morph walks a smooth, fixed path through nearby sounds (further along, further from home)
function lab:new_path(which)
  local pts = { {} }
  for _, p in ipairs(KIT[which].params) do pts[1][p[1]] = 0 end
  for k = 2, MORPH_POINTS + 1 do
    pts[k] = {}
    for _, p in ipairs(KIT[which].params) do
      local sc = MORPH_SCALE[p[1]] or 0.45
      pts[k][p[1]] = (math.random() * 2 - 1) * sc * (p[3] - p[2]) * math.min(1, k / 2.5)
    end
  end
  self.path[which] = pts
end
function lab:morph_offset(which, name)
  local m = self.morph[which] or 0
  if m <= 0 then return 0 end
  local pos = math.min(m, 0.9999) * MORPH_POINTS
  local i = math.floor(pos); local t = pos - i; t = t * t * (3 - 2 * t)
  local pts = self.path[which]
  return pts[i + 1][name] * (1 - t) + pts[i + 2][name] * t
end
function lab:apply(which)
  local ch = CHARACTER[which]
  for _, p in ipairs(KIT[which].params) do
    local name, lo, hi = p[1], p[2], p[3]
    local x = self.home[which][name]
    if ch and ch.w[name] then x = x + (self.char[which] or 0) * ch.w[name] * (hi - lo) end
    x = x + self:morph_offset(which, name)
    x = math.max(lo, math.min(hi, x))
    if name == "bursts" then x = math.floor(x + 0.5) end
    if math.abs(x - self.v[which][name]) > 1e-9 then self:set(which, name, x) end
  end
end
-- keep: the sound as it is becomes home, and both sliders go back to zero (the sound doesn't change)
function lab:keep(which, quiet)
  for n, x in pairs(self.v[which]) do self.home[which][n] = x end
  self.char[which], self.morph[which] = 0, 0
  self.applying = true
  pd.send("lab-" .. which .. "-char-ui", "float", { 0 }); pd.send("lab-" .. which .. "-morph-ui", "float", { 0 })
  self.applying = false
end

local function seg(name, target, time, delay) pd.send(name, "list", { target, time, delay }) end

-- play a sound; var picks one of a set (hats: 1 closed, 2 open; toms: low, mid, high; congas: low, high)
function lab:play(which, var) play_voice("lab-" .. which, which, self.v[which], var, 1, KIT[which]) end
-- the steady kick the loop plays against (the lab kick's starting sound, on its own voice)
function lab:ref_kick()
  local v = {}
  for _, p in ipairs(KIT.kick.params) do v[p[1]] = p[4] end
  for _, n in ipairs({ "pitch", "ratio", "second", "noise", "ntone", "nfocus", "drive", "level" }) do pd.send("labref-kick-" .. n, "float", { v[n] }) end
  play_voice("labref-kick", "kick", v, 1, 1, KIT.kick)
end

-- how long a hit lasts, so a render catches all of it
function lab:length(which, var)
  local v = self.v[which]
  if which == "hat" then return ((var == 2) and v.open or v.closed) * 1.6 + 40 end
  if which == "clap" then return math.min(2500, v.bursts * v.gap * 1.5 + v.tail * 1.6 + v.room * 400 + 60) end
  if which == "snare" then return math.min(2000, math.max(v.bodydec, v.wdecay) * 1.6 + 60) end
  if which == "shaker" then return v.attack + v.decay * 1.6 + 40 end
  return math.min(2500, math.max(v.decay, v.ndecay) * 1.6 + 40)
end

-- small, medium or wild: each setting moves at random within that share of its range
function lab:randomise(which, amt)
  for _, p in ipairs(KIT[which].params) do
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
  self:keep(which)
  self:play(which, 1)
  self:status(which .. ": randomised (" .. ((amt >= 1) and "wild" or ((amt > 0.2) and "medium" or "small")) .. ")")
end

-- loop, at 120 in half beats: a kick on every beat (your lab kick if its loop is on), clap or snare on 2 and 4,
-- closed hats on the offbeats with an open one before the 1, shaker on every half beat, rim and congas off the beat,
-- a tom run at the end of the bar
function lab:loop_check()
  local on = false
  for _, x in pairs(self.loop) do on = on or x end
  if on and not self.looping then self.looping = true; self.beat = 0; self:loop_tick()
  elseif not on then self.looping = false; self.loopclock:unset() end
end
function lab:loop_tick()
  if not self.looping or self.rendering then return end
  local b, L = self.beat, self.loop                  -- half beats, 0 to 7
  if b % 2 == 0 then
    if L.kick then self:play("kick", 1) else self:ref_kick() end
  end
  if b == 2 or b == 6 then
    if L.clap then self:play("clap", 1) end
    if L.snare then self:play("snare", 1) end
  end
  if L.hat and b % 2 == 1 then self:play("hat", (b == 7) and 2 or 1) end
  if L.shaker then self:play("shaker", 1) end
  if L.rim and (b == 3 or b == 6) then self:play("rim", 1) end
  if L.conga and (b == 1 or b == 3 or b == 4) then self:play("conga", (b == 4) and 1 or 2) end
  if L.tom and b >= 5 then self:play("tom", 8 - b) end
  self.beat = (b + 1) % 8
  self.loopclock:delay(250)
end

-- render: record to samples/<folder>/lab-<sound>-<date and time>.wav (24-bit mono). A set renders each of its
-- sounds with the same name plus low/mid/high (or closed/open): the closed hat goes in samples/hat, the open in samples/open-hat
function lab:render(which)
  if self.rendering then return end
  local k = KIT[which]
  local stamp = os.date("%Y%m%d-%H%M%S")
  self.queue = {}
  if #k.variants == 0 then
    self.queue[1] = { which = which, var = 1, path = "samples/" .. k.folder .. "/lab-" .. which .. "-" .. stamp .. ".wav" }
  else
    for i, var in ipairs(k.variants) do
      local folder = k.folder or ((var[1] == "open") and "open-hat" or "hat")
      self.queue[i] = { which = which, var = i, path = "samples/" .. folder .. "/lab-" .. which .. "-" .. stamp .. "-" .. var[1] .. ".wav" }
    end
  end
  self.saved = {}
  self:render_next()
end
function lab:render_next()
  local job = table.remove(self.queue or {}, 1)
  if not job then return end
  self.rendering = job
  pd.send("lab-rec", "open", { "-bytes", 3, job.path })
  pd.send("lab-rec", "start", {})
  self:play(job.which, job.var)
  self.stopclock:delay(self:length(job.which, job.var))
end
function lab:render_stop()
  local r = self.rendering
  if not r then return end
  pd.send("lab-rec", "stop", {})
  self.rendering = nil
  pd.post("ockm-lab: saved " .. r.path)
  self.saved[#self.saved + 1] = r.path:match("[^/]+$")
  if self.queue and #self.queue > 0 then self:render_next(); return end
  self:status("saved " .. table.concat(self.saved, ", "))
  if self.looping then self.loopclock:delay(250) end
end
function lab:status(s) pd.send("lab-status", "symbol", { s }) end

-- headless tests
function lab:test(sel, a)
  if sel == "set" then self:set(tostring(a[1]), tostring(a[2]), tonumber(a[3]))
  elseif sel == "char" or sel == "morph" then
    local which, x = tostring(a[1]), tonumber(a[2]) or 0
    if sel == "char" then self.char[which] = x else self.morph[which] = x end
    self:apply(which)
  elseif sel == "keep" then self:keep(tostring(a[1]))
  elseif sel == "dump" then
    for which, k in pairs(KIT) do for _, p in ipairs(k.params) do pd.post(string.format("ockm-lab: %s %s %.3f", which, p[1], self.v[which][p[1]])) end end
  end
end
