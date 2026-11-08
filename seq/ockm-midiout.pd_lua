-- MIDI out for a groovebox part (v1.40): plays the part on a synth plugged into the box (a TD-3, an SH-01A, an FM-1 ...).
--
-- [ockm-midiout <part>]   part: bass, lead or chord. Outlet: raw MIDI bytes, one at a time, for [midiout]
-- Listens to:
--   ockm-<part>-notes-out   the part's notes, as its sequencer plays them. Bass and lead: <note> <accent> <glide> <hold>,
--                           or off. Chord: <n1> <n2> <n3> <n4> <strength 0-1>
--   ockm-<part>-midi        0 this box only (nothing goes out), 1 MIDI only, 2 both
--   ockm-<part>-mch         the MIDI channel, 1 to 16
--   ockm-<part>-mute, ockm-<part>-solo, ockm-soloing   a muted part sends nothing (and lets go of what it holds)
--   ockm-playing, ockm-stepms, ockm-chord-k4 (the chords' length)
-- v1.49 [ockm-midiout drums]: the 8 drum slots. Listens to ockm-drums-notes-out <slot d1-d8> <strength 0-1> (each hit as
-- it plays: rolls and flams are real repeated hits), ockm-drums-midi, ockm-drums-mch (10 to start), ockm-drums-map
-- (0 by sound, General MIDI style: kick 36, snare 38, clap 39, rim 37, closed hat 42, open hat 46, tom 45, cowbell 56;
-- 1 pads: slot 1-8 on notes 36-43, for an MPC drum program on chromatic), ockm-<slot>-sound, ockm-<slot>-mute and -solo,
-- ockm-drums-on. Velocity follows the strength (an accent 127). Each note lets go 40 ms later.
-- An accent goes out harder (velocity 120, others 90). A glide overlaps the notes (the new one starts before the old one
-- stops), which is how a TD-3 slides and how a mono synth with legato glide glides. A held step doesn't let go.

local mo = pd.Class:new():register("ockm-midiout")

function mo:initialize(sel, atoms)
  self.inlets, self.outlets = 0, 1
  self.part = tostring(atoms[1] or "bass")
  self.mode, self.ch = 0, 1
  self.mute, self.solo, self.soloing = 0, 0, 0
  self.stepms, self.clen = 125, 0.5
  self.sounding = {}   -- notes held right now
  if self.part == "drums" then
    self.ch, self.map, self.on = 10, 0, 1
    self.snd, self.dmute, self.dsolo = {}, {}, {}
    for i = 1, 8 do self.snd[i] = ({ 0, 1, 2, 4, 5, 7, 3, 6 })[i]; self.dmute[i] = 0; self.dsolo[i] = 0 end
  end
  return true
end

function mo:postinitialize()
  self.recv = {}
  local function on(name, fn)
    local m = "r_" .. #self.recv
    self[m] = function(o, sel, at) fn(sel, at or {}) end
    self.recv[#self.recv + 1] = pd.Receive:new():register(self, name, m)
  end
  local p = "ockm-" .. self.part
  local num = function(a, d) return tonumber(a[1]) or d end
  if self.part == "drums" then
    on("ockm-drums-notes-out", function(sel, a) self:drum(sel, a) end)
    on("ockm-drums-map", function(_, a) self:all_off(); self.map = num(a, 0) end)
    on("ockm-drums-on", function(_, a) self.on = num(a, 1); if self.on <= 0 then self:all_off() end end)
    for i = 1, 8 do
      on("ockm-d" .. i .. "-sound", function(_, a) self.snd[i] = math.floor(num(a, 0)) end)
      on("ockm-d" .. i .. "-mute", function(_, a) self.dmute[i] = num(a, 0) end)
      on("ockm-d" .. i .. "-solo", function(_, a) self.dsolo[i] = num(a, 0) end)
    end
  else
    on(p .. "-notes-out", function(sel, a) self:notes(sel, a) end)
  end
  on(p .. "-midi", function(_, a) local m = math.floor(num(a, 0)); if m ~= self.mode then self:all_off() end; self.mode = m end)
  on(p .. "-mch", function(_, a) self:all_off(); self.ch = math.max(1, math.min(16, math.floor(num(a, 1)))) end)
  on(p .. "-mute", function(_, a) self.mute = num(a, 0); if not self:live() then self:all_off() end end)
  on(p .. "-solo", function(_, a) self.solo = num(a, 0); if not self:live() then self:all_off() end end)
  on("ockm-soloing", function(_, a) self.soloing = num(a, 0); if not self:live() then self:all_off() end end)
  on("ockm-playing", function(_, a) if num(a, 0) == 0 then self:all_off() end end)
  on("ockm-stepms", function(_, a) local m = num(a, 0); if m > 0 then self.stepms = m end end)
  if self.part == "chord" then on("ockm-chord-k4", function(_, a) self.clen = num(a, 0.5) end) end
  self.offclock = pd.Clock:new():register(self, "gate_off")
end

function mo:finalize()
  for _, r in ipairs(self.recv or {}) do r:destruct() end
  if self.offclock then self.offclock:destruct() end
end

function mo:live()
  if self.mode < 1 or self.mute > 0 then return false end
  if self.part == "drums" then return self.on > 0 end
  if self.soloing > 0 and self.solo <= 0 then return false end
  return true
end

function mo:send3(a, b, c) self:outlet(1, "float", { a }); self:outlet(1, "float", { b }); self:outlet(1, "float", { c }) end
function mo:on_(n, v) n = math.floor(n); if n <= 0 or n > 127 then return end; self:send3(0x90 + self.ch - 1, n, v); self.sounding[n] = true end
function mo:off_(n) if self.sounding[n] then self:send3(0x80 + self.ch - 1, n, 0); self.sounding[n] = nil end end
function mo:all_off()
  for n in pairs(self.sounding) do self:send3(0x80 + self.ch - 1, n, 0) end
  self.sounding = {}
  if self.offclock then self.offclock:unset() end
end
function mo:gate_off() for n in pairs(self.sounding) do self:off_(n) end end

function mo:notes(sel, a)
  if sel == "off" or sel == "bang" then self.offclock:unset(); self:gate_off(); return end
  if not self:live() then return end
  local ms = self.stepms
  if pd.getvalue then ms = tonumber(pd.getvalue("ockm_stepms")) or ms end
  if self.part == "chord" then
    local v = math.floor(40 + 80 * math.max(0, math.min(1, tonumber(a[5]) or 0.75)))
    self:gate_off()
    for k = 1, 4 do local n = tonumber(a[k]) or 0; if n > 0 then self:on_(n, v) end end
    self.offclock:unset(); self.offclock:delay(ms * (0.6 + 15 * self.clen * self.clen))
    return
  end
  local n, acc, glide, hold = tonumber(a[1]) or 0, tonumber(a[2]) or 0, tonumber(a[3]) or 0, tonumber(a[4]) or 0
  if n <= 0 then return end
  local v = (acc > 0) and 120 or 90
  local old = {}
  for k in pairs(self.sounding) do old[#old + 1] = k end
  if glide > 0 then
    -- the new note first, then the old one goes: an overlap, so the synth slides
    if not self.sounding[n] then self:on_(n, v) end
    for _, k in ipairs(old) do if k ~= n then self:off_(k) end end
  else
    for _, k in ipairs(old) do self:off_(k) end
    self:on_(n, v)
  end
  self.offclock:unset()
  if hold <= 0 then self.offclock:delay(ms * 0.55) end
end

-- v1.49 drums: a note per hit, by sound (General MIDI style) or by slot (pads 36-43)
local GM = { [0] = 36, 38, 39, 37, 42, 46, 45, 56 }
function mo.drum_note(map, slot, sound)
  if map >= 1 then return 35 + slot end
  return GM[(math.floor(sound or 0)) % 8] or 36
end
function mo.drum_vel(strength) return math.max(1, math.min(127, math.floor(1 + 126 * (tonumber(strength) or 0) + 0.5))) end
function mo:drum(sel, a)
  if sel ~= "list" and sel ~= "float" then a = { sel, a[1] } end
  local slot = tonumber(tostring(a[1] or ""):match("(%d+)")) or 0
  if slot < 1 or slot > 8 or not self:live() then return end
  if self.dmute[slot] > 0 or (self.soloing > 0 and self.dsolo[slot] <= 0) then return end
  local n = mo.drum_note(self.map, slot, self.snd[slot])
  if self.sounding[n] then self:off_(n) end
  self:on_(n, mo.drum_vel(a[2]))
  self.offclock:unset(); self.offclock:delay(40)
end
