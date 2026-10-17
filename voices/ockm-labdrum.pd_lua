-- A drum slot's synth sounds: the drum lab's voices, with randomise, character and morph.
-- Written by tools/build_lab.py: change it there.
local labdrum = pd.Class:new():register("ockm-labdrum")
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
local CHARACTER = { clap = { name = "room", w = { tail = 0.6, room = 0.7, jitter = 0.4, tailtone = -0.4, bdecay = 0.2 } }, snare = { name = "crack", w = { wires = 0.4, wdecay = 0.3, bodydec = -0.4, click = 0.6, drive = 0.4, mix = 0.4 } }, hat = { name = "metal", w = { ring = 0.7, focus = 0.5, bright = -0.4, tone = -0.2 } }, kick = { name = "punch", w = { sweep = 0.5, sweeptime = -0.5, noise = 0.6, decay = -0.3, drive = 0.3 } }, tom = { name = "boom", w = { pitch = -0.4, decay = 0.5, sweep = 0.4, noise = -0.4 } }, conga = { name = "slap", w = { noise = 0.6, ntone = 0.4, decay = -0.3, second = 0.4 } }, rim = { name = "wood", w = { ratio = -0.6, decay = 0.4, noise = -0.4, pitch = -0.2 } }, shaker = { name = "shake", w = { attack = 0.5, decay = 0.5, grit = 0.6, tone = -0.2 } } }
local MORPH_SCALE = { level = 0, pitch = 0.2, ratio = 0.25, bursts = 0.3, drive = 0.3, sweep = 0.3 }
local MORPH_POINTS = 4
local TYPES = { "kick", "snare", "clap", "hat", "tom", "rim", "conga", "shaker" }
-- the settings each voice listens for (the rest only shape its envelopes, played from here)
local LISTEN = { kick = { ["body"] = true, ["drive"] = true, ["level"] = true, ["mul"] = true, ["nenv"] = true, ["nfocus"] = true, ["noise"] = true, ["ntone"] = true, ["pitch"] = true, ["ratio"] = true, ["second"] = true, ["st"] = true }, snare = { ["body"] = true, ["cenv"] = true, ["click"] = true, ["drive"] = true, ["freq"] = true, ["level"] = true, ["mix"] = true, ["ratio"] = true, ["wenv"] = true, ["wires"] = true, ["wwidth"] = true }, clap = { ["balance"] = true, ["burst"] = true, ["drive"] = true, ["level"] = true, ["room"] = true, ["tailenv"] = true, ["tailq"] = true, ["tailtone"] = true, ["toneA"] = true, ["toneB"] = true, ["width"] = true }, hat = { ["bright"] = true, ["drive"] = true, ["env"] = true, ["focus"] = true, ["level"] = true, ["pitch"] = true, ["ring"] = true, ["tone"] = true }, tom = { ["body"] = true, ["drive"] = true, ["level"] = true, ["mul"] = true, ["nenv"] = true, ["nfocus"] = true, ["noise"] = true, ["ntone"] = true, ["pitch"] = true, ["ratio"] = true, ["second"] = true, ["st"] = true }, rim = { ["body"] = true, ["drive"] = true, ["level"] = true, ["mul"] = true, ["nenv"] = true, ["nfocus"] = true, ["noise"] = true, ["ntone"] = true, ["pitch"] = true, ["ratio"] = true, ["second"] = true, ["st"] = true }, conga = { ["body"] = true, ["drive"] = true, ["level"] = true, ["mul"] = true, ["nenv"] = true, ["nfocus"] = true, ["noise"] = true, ["ntone"] = true, ["pitch"] = true, ["ratio"] = true, ["second"] = true, ["st"] = true }, shaker = { ["drive"] = true, ["env"] = true, ["focus"] = true, ["grit"] = true, ["level"] = true, ["lowcut"] = true, ["tone"] = true } }
local ACT = {}; for i, t in ipairs(TYPES) do ACT[t] = i - 1 end
-- which sound each drum plays (perc slots choose: ockm-<slot>-synth 0, 1, 2)
local SOUND_TYPE = { [0] = "kick", [1] = "snare", [2] = "clap", [4] = "hat", [5] = "hat", [6] = "tom" }
local PERC = { [3] = { "rim", "conga", "shaker" }, [7] = { "conga", "shaker", "rim" } }
-- what the slot's tune moves (times 2^(tune/12)) and what its decay stretches (times decay/100)
local TUNE = { kick = { "pitch" }, tom = { "pitch" }, conga = { "pitch" }, rim = { "pitch" }, snare = { "pitch", "wires" },
               hat = { "pitch", "tone" }, clap = { "toneA", "toneB", "tailtone" }, shaker = { "tone" } }
local STRETCH = { kick = { "decay" }, tom = { "decay" }, conga = { "decay" }, rim = { "decay" }, snare = { "bodydec", "wdecay" },
                  hat = { "closed", "open" }, clap = { "tail" }, shaker = { "decay" } }

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

-- a repeatable random sequence from a seed, so a saved seed always gives the same sound
local function rng(seed)
  local s = math.floor(seed) % 2147483647; if s <= 0 then s = s + 2147483646 end
  return function() s = (s * 16807) % 2147483647; return (s - 1) / 2147483646 end
end

function labdrum:initialize(sel, atoms)
  self.inlets, self.outlets = 1, 0
  self.slot = tostring(atoms[1] or "d1")
  self.s = { sound = 0, sample = 0, synth = 0, tune = 0, decay = 100, level = 1, labchar = 0, labmorph = 0, labrseed = 0, labramt = 0, labpseed = 1 }
  self.sent = {}
  return true
end

function labdrum:postinitialize()
  self.recv = {}
  for k in pairs(self.s) do
    local m = "r_" .. k
    self[m] = function(o, sel, a) local x = tonumber(a[1]); if x then o.s[k] = x; o:update() end end
    self.recv[#self.recv + 1] = pd.Receive:new():register(self, "ockm-" .. self.slot .. "-" .. k, m)
  end
  -- once loading is done (the voices' own loadbangs have run), send everything again
  self.clock = pd.Clock:new():register(self, "resend")
  self.clock:delay(0)
end
function labdrum:resend() self.sent = {}; self.act = nil; self:update() end
function labdrum:finalize()
  for _, r in ipairs(self.recv or {}) do r:destruct() end
  if self.clock then self.clock:destruct() end
end

function labdrum:kind()
  local snd = math.floor(self.s.sound)
  if PERC[snd] then return PERC[snd][math.max(0, math.min(2, math.floor(self.s.synth))) + 1] end
  return SOUND_TYPE[snd] or "kick"
end

-- the settings this slot's sound plays with
function labdrum:settings(t)
  local k, s = KIT[t], self.s
  local v = {}
  for _, p in ipairs(k.params) do v[p[1]] = p[4] end
  if s.labrseed > 0 and s.labramt > 0 then
    local r = rng(s.labrseed)
    for _, p in ipairs(k.params) do
      local name, lo, hi = p[1], p[2], p[3]
      local u = r()
      if name ~= "level" then
        if s.labramt >= 1 then v[name] = lo + u * (hi - lo) else v[name] = v[name] + (u * 2 - 1) * s.labramt * (hi - lo) end
      end
    end
  end
  local ch = CHARACTER[t]
  local m = math.max(0, math.min(1, s.labmorph))
  local pts
  if m > 0 then
    local r = rng(s.labpseed * 7919 + ACT[t] + 1)
    pts = { {} }
    for _, p in ipairs(k.params) do pts[1][p[1]] = 0 end
    for j = 2, MORPH_POINTS + 1 do
      pts[j] = {}
      for _, p in ipairs(k.params) do pts[j][p[1]] = (r() * 2 - 1) * (MORPH_SCALE[p[1]] or 0.45) * (p[3] - p[2]) * math.min(1, j / 2.5) end
    end
  end
  for _, p in ipairs(k.params) do
    local name, lo, hi = p[1], p[2], p[3]
    local x = v[name]
    if ch and ch.w[name] then x = x + s.labchar * ch.w[name] * (hi - lo) end
    if pts then
      local pos = math.min(m, 0.9999) * MORPH_POINTS; local i = math.floor(pos); local f = pos - i; f = f * f * (3 - 2 * f)
      x = x + pts[i + 1][name] * (1 - f) + pts[i + 2][name] * f
    end
    x = math.max(lo, math.min(hi, x))
    if name == "bursts" then x = math.floor(x + 0.5) end
    v[name] = x
  end
  for _, n in ipairs(TUNE[t] or {}) do v[n] = v[n] * 2 ^ (s.tune / 12) end
  for _, n in ipairs(STRETCH[t] or {}) do v[n] = v[n] * s.decay / 100 end
  v.level = v.level * s.level
  return v
end

-- switch on the right voice (or the sample player) and send it its settings (only the ones that changed)
function labdrum:update()
  local t = self:kind()
  local act = (self.s.sample > 0) and 8 or ACT[t]
  if act ~= self.act then
    self.act = act
    pd.send("ockm-" .. self.slot .. "-labact", "float", { act })
    self.sent = {}
  end
  if act == 8 then return end
  self.t, self.v = t, self:settings(t)
  local pre = "ockm-" .. self.slot .. "-" .. t
  for name, x in pairs(self.v) do
    if LISTEN[t][name] and self.sent[name] ~= x then self.sent[name] = x; pd.send(pre .. "-" .. name, "float", { x }) end
  end
end

-- a hit (0 to 1)
function labdrum:in_1_float(vel)
  if vel <= 0 or self.act == 8 or not self.v then return end
  local var = (self.t == "hat" and math.floor(self.s.sound) == 5) and 2 or 1
  play_voice("ockm-" .. self.slot .. "-" .. self.t, self.t, self.v, var, math.min(1, vel), KIT[self.t])
end
