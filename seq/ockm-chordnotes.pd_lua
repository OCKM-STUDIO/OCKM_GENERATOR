-- The chord sequencer's notes: a chord type, key, scale and voicing turned into up to four MIDI notes.
-- Written by tools/build.py: change it there. In: scale <7 semitones>, type <n>, root <0-11>, smooth <0/1>,
-- voicing <0-2>, drift <0/1>, hands <0-5>, engine <n>, hit <strength> <scale step> <turnaround 0/1> <step>,
-- lh <step> <scale step> <turnaround 0/1> <right hand's hit>. Out: four notes (0 for none) and the strength; right: the left hand's.
local cn = pd.Class:new():register("ockm-chordnotes")
local CHORD_TYPES = { { k=0, name="triad", 0, 2, 4 }, { k=0, name="seventh", 0, 2, 4, 6 }, { k=0, name="sus2", 0, 1, 4 }, { k=0, name="power", 0, 4, 7 }, { k=0, name="sus4", 0, 3, 4 }, { k=0, name="sixth", 0, 2, 4, 5 }, { k=0, name="ninth", 2, 4, 6, 8 }, { k=0, name="eleventh", 2, 6, 8, 10 }, { k=1, name="m9", 3, 7, 10, 14 }, { k=1, name="m11", 3, 10, 14, 17 }, { k=1, name="m7", 0, 7, 10, 15 }, { k=1, name="4ths", 0, 5, 10, 15 }, { k=1, name="maj9", 4, 7, 11, 14 } }
local CHORD_CENTRE, CHORD_FLOOR = 62, 50   -- smooth chords sit around D4, their lowest note no lower than D3
-- a chord's notes (MIDI). deg: the chord's root as a scale step; sc: the scale (7 semitones); root: the key (0 C .. 11 B);
-- smooth: keep every chord at about the same height (inversions for chords in the key, octaves for fixed shapes), so
-- they move by small steps and stay out of the bass; voicing 0 close, 1 open, 2 wide; turn: the turnaround's major V
local function chord_voicing(deg, ctype, sc, root, smooth, voicing, turn, lift)
  local ty = CHORD_TYPES[(ctype or 0) + 1] or CHORD_TYPES[1]
  local rox = (root <= 7) and (48 + root) or (36 + root)
  local function at(a)
    local s = sc[(a % 7) + 1]
    if turn and s == 10 then s = 11 end   -- the turnaround raises the minor 7th: E major in A minor
    return rox + 12 * math.floor(a / 7) + s
  end
  deg = math.floor(deg)
  local n = {}
  if ty.k == 1 then
    local r = at(deg)
    for _, o in ipairs(ty) do
      if turn and o % 12 == 3 then o = o + 1 end   -- a minor shape turns major on the turnaround
      n[#n + 1] = r + o
    end
  else
    for _, o in ipairs(ty) do
      local v = at(deg + o)
      if o == 8 and v - at(deg) == 13 then v = at(deg + 7) end   -- a flat 9th grinds on the bass: the root instead
      n[#n + 1] = v
    end
  end
  if smooth then
    local cands = {}
    if ty.k == 1 then cands[1] = n
    else
      table.sort(n)
      for i = 0, #n - 1 do
        local c = {}
        for j, v in ipairs(n) do c[j] = (j <= i) and v + 12 or v end
        table.sort(c); cands[#cands + 1] = c
      end
    end
    local best, bc
    local all = {}
    for _, c in ipairs(cands) do
      local sum, lo = 0, c[1]
      for _, v in ipairs(c) do sum = sum + v; if v < lo then lo = v end end
      local mean = sum / #c
      local m = math.floor((CHORD_CENTRE - mean) / 12 + 0.5)
      for mm = m - 1, m + 1 do
        local cost = math.abs(mean + 12 * mm - CHORD_CENTRE)
        if lo + 12 * mm < CHORD_FLOOR then cost = cost + (CHORD_FLOOR - lo - 12 * mm) end
        for j = 2, #c do if c[j] - c[j - 1] == 1 then cost = cost + 4 end end   -- no semitone rubs inside a chord
        local cand = {}
        for j, v in ipairs(c) do cand[j] = v + 12 * mm end
        all[#all + 1] = { cand, mean + 12 * mm, cost }
        if not bc or cost < bc - 1e-9 then bc = cost; best = cand end
      end
    end
    -- drift (v1.01): one inversion higher than the best, if that stays in the band, for chords built from the key
    if lift and ty.k == 0 then
      local bm = 0; for _, v in ipairs(best) do bm = bm + v end; bm = bm / #best
      local up, um
      for _, a in ipairs(all) do
        if a[2] > bm + 1 and a[2] - CHORD_CENTRE <= 7 and a[3] < 50 and (not um or a[2] < um) then up, um = a[1], a[2] end
      end
      if up then best = up end
    end
    n = best
  end
  -- open lifts the second note an octave; wide also drops the lowest an octave and lifts the fourth
  if voicing == 1 or voicing == 2 then
    if n[2] then n[2] = n[2] + 12 end
    if voicing == 2 then n[1] = n[1] - 12; if n[4] then n[4] = n[4] + 12 end end
  end
  return n, ty
end
-- v1.20 two hands (piano, organ, Rhodes). The left hand on step i: pat 1 anchor (root and octave when the chord changes,
-- and each bar), 2 pulse (on every beat), 3 syncopated (1, the and of 2, 4), 4 broken (root on the beats, fifth and
-- octave on the ands), 5 answer (on the beats the right hand leaves empty). on: the right hand's hit here (0 none),
-- changed: the chord changed here. Returns a shape ("both" root and octave, "root", "fifth", "oct") and a strength, or nil
local function left_hand(pat, i, on, changed)
  local b = i % 16
  local top = (b == 0) and 0.9 or 0.75
  if pat == 1 then
    if changed or b == 0 then return "both", 0.9 end
  elseif pat == 2 then
    if i % 4 == 0 then return "both", top end
    if changed then return "both", 0.8 end
  elseif pat == 3 then
    if b == 0 or b == 6 or b == 12 then return "both", top end
    if changed then return "both", 0.8 end
  elseif pat == 4 then
    if i % 4 == 0 then return "root", top end
    if changed then return "root", 0.8 end
    if i % 8 == 2 then return "fifth", 0.6 end
    if i % 8 == 6 then return "oct", 0.6 end
  elseif pat == 5 then
    if (i % 4 == 0 or changed) and on == 0 then return "both", top end
  end
  return nil
end
-- the left hand's notes: the chord's root between G2 and F#3 (an octave over the bass), with its octave or fifth
local LH_LOW = 43
local function left_notes(shape, deg, sc, root)
  local d = math.floor(deg)
  local pc = (root + sc[d % 7 + 1]) % 12
  local low = LH_LOW + (pc - LH_LOW) % 12
  if shape == "root" then return { low } end
  if shape == "oct" then return { low + 12 } end
  if shape == "fifth" then return { low + (sc[(d + 4) % 7 + 1] - sc[d % 7 + 1]) % 12 } end
  return { low, low + 12 }
end
-- the right hand with the left playing: four-note chords drop their root (the left hand has it), and nothing sits
-- below G3, so the hands don't crowd each other
local function right_hand(n, deg, sc, root)
  local pc = (root + sc[math.floor(deg) % 7 + 1]) % 12
  local o = {}
  if #n >= 4 then for _, x in ipairs(n) do if x % 12 ~= pc then o[#o + 1] = x end end end
  if #o < 3 then o = {}; for _, x in ipairs(n) do o[#o + 1] = x end end
  local seen, r = {}, {}
  for _, x in ipairs(o) do
    while x < 55 do x = x + 12 end
    if not seen[x] then seen[x] = true; r[#r + 1] = x end
  end
  table.sort(r)
  return r
end
local TWO_HANDS = { [1] = true, [3] = true, [4] = true }   -- the chord engines that play with two hands: organ, piano, Rhodes

function cn:initialize(sel, atoms)
  self.inlets, self.outlets = 1, 2
  self.sc, self.ty, self.root, self.smooth, self.voicing = { 0, 2, 3, 5, 7, 8, 10 }, 0, 9, true, 0
  self.drift, self.pass, self.last = false, 0, -1
  self.hands, self.engine = 0, 0
  return true
end
function cn:two() return self.hands > 0 and TWO_HANDS[self.engine] end
function cn:in_1_hands(a) self.hands = math.floor(a[1] or 0) end
function cn:in_1_engine(a) self.engine = math.floor(a[1] or 0) end
-- every step: lh <step> <chord root> <turnaround 0/1> <right hand's hit>. Out (right): the left hand's notes and strength
function cn:in_1_lh(a)
  local d = a[2] or 0
  local changed = (d ~= self.lhdeg)
  self.lhdeg = d
  if not self:two() then return end
  local shape, s = left_hand(self.hands, math.floor(a[1] or 0), a[4] or 0, changed)
  if not shape then return end
  local n = left_notes(shape, d, self.sc, self.root)
  self:outlet(2, "list", { n[1] or 0, n[2] or 0, 0, 0, math.min(1, s * (0.92 + 0.16 * math.random())) })
end
function cn:in_1_scale(a) if #a >= 7 then self.sc = a end end
function cn:in_1_type(a) self.ty = math.max(0, math.floor(a[1] or 0)) end
function cn:in_1_root(a) self.root = math.floor(a[1] or 9) % 12 end
function cn:in_1_smooth(a) self.smooth = (a[1] or 1) > 0 end
function cn:in_1_voicing(a) self.voicing = math.floor(a[1] or 0) end
function cn:in_1_drift(a) self.drift = (a[1] or 0) > 0 end
function cn:in_1_hit(a)
  local st = a[4] or 0
  if st < self.last then self.pass = self.pass + 1 end   -- the pattern came round again
  self.last = st
  local n = chord_voicing(a[2] or 0, self.ty, self.sc, self.root, self.smooth, self.voicing, (a[3] or 0) > 0, self.drift and self.pass % 2 == 1)
  if self:two() then n = right_hand(n, a[2] or 0, self.sc, self.root) end
  local out = {}
  for k = 1, 4 do out[k] = n[k] or 0 end
  out[5] = math.min(1, (a[1] or 0.75) * (0.92 + 0.16 * math.random()))   -- played, not programmed: no two hits quite the same
  self:outlet(1, "list", out)
end
