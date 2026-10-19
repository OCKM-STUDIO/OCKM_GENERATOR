-- The chord sequencer's notes: a chord type, key, scale and voicing turned into up to four MIDI notes.
-- Written by tools/build.py: change it there. In: scale <7 semitones>, type <n>, root <0-11>, smooth <0/1>,
-- voicing <0-2>, hit <strength> <scale step> <turnaround 0/1>. Out: four notes (0 for none) and the strength.
local cn = pd.Class:new():register("ockm-chordnotes")
local CHORD_TYPES = { { k=0, name="triad", 0, 2, 4 }, { k=0, name="seventh", 0, 2, 4, 6 }, { k=0, name="sus2", 0, 1, 4 }, { k=0, name="power", 0, 4, 7 }, { k=0, name="sus4", 0, 3, 4 }, { k=0, name="sixth", 0, 2, 4, 5 }, { k=0, name="ninth", 2, 4, 6, 8 }, { k=0, name="eleventh", 2, 6, 8, 10 }, { k=1, name="m9", 3, 7, 10, 14 }, { k=1, name="m11", 3, 10, 14, 17 }, { k=1, name="m7", 0, 7, 10, 15 }, { k=1, name="4ths", 0, 5, 10, 15 }, { k=1, name="maj9", 4, 7, 11, 14 } }
local CHORD_CENTRE, CHORD_FLOOR = 62, 50   -- smooth chords sit around D4, their lowest note no lower than D3
-- a chord's notes (MIDI). deg: the chord's root as a scale step; sc: the scale (7 semitones); root: the key (0 C .. 11 B);
-- smooth: keep every chord at about the same height (inversions for chords in the key, octaves for fixed shapes), so
-- they move by small steps and stay out of the bass; voicing 0 close, 1 open, 2 wide; turn: the turnaround's major V
local function chord_voicing(deg, ctype, sc, root, smooth, voicing, turn)
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
    for _, c in ipairs(cands) do
      local sum, lo = 0, c[1]
      for _, v in ipairs(c) do sum = sum + v; if v < lo then lo = v end end
      local mean = sum / #c
      local m = math.floor((CHORD_CENTRE - mean) / 12 + 0.5)
      for mm = m - 1, m + 1 do
        local cost = math.abs(mean + 12 * mm - CHORD_CENTRE)
        if lo + 12 * mm < CHORD_FLOOR then cost = cost + (CHORD_FLOOR - lo - 12 * mm) end
        for j = 2, #c do if c[j] - c[j - 1] == 1 then cost = cost + 4 end end   -- no semitone rubs inside a chord
        if not bc or cost < bc - 1e-9 then
          bc = cost; best = {}
          for j, v in ipairs(c) do best[j] = v + 12 * mm end
        end
      end
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

function cn:initialize(sel, atoms)
  self.inlets, self.outlets = 1, 1
  self.sc, self.ty, self.root, self.smooth, self.voicing = { 0, 2, 3, 5, 7, 8, 10 }, 0, 9, true, 0
  return true
end
function cn:in_1_scale(a) if #a >= 7 then self.sc = a end end
function cn:in_1_type(a) self.ty = math.max(0, math.floor(a[1] or 0)) end
function cn:in_1_root(a) self.root = math.floor(a[1] or 9) % 12 end
function cn:in_1_smooth(a) self.smooth = (a[1] or 1) > 0 end
function cn:in_1_voicing(a) self.voicing = math.floor(a[1] or 0) end
function cn:in_1_hit(a)
  local n = chord_voicing(a[2] or 0, self.ty, self.sc, self.root, self.smooth, self.voicing, (a[3] or 0) > 0)
  local out = {}
  for k = 1, 4 do out[k] = n[k] or 0 end
  out[5] = math.min(1, (a[1] or 0.75) * (0.92 + 0.16 * math.random()))   -- played, not programmed: no two hits quite the same
  self:outlet(1, "list", out)
end
