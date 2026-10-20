-- The bass and lead generator: a rhythm, a riff (or tune) and the shared key and chords, written across a mono part.
-- Hand-written: edit this file. Only the PRESETS block is filled in by tools/build.py (from its PRE lists).
--
-- [ockm-linemaker <track> <octave> <rhythm> <notes> <mode> <sync> <lead>]
--   octave: semitones added to every note (the lead sits 24 up); rhythm, notes: defaults; mode 0 auto; sync 1: follow
--   the chords; lead 1: the lead's rules (notes snap to the chord, inside to outside, no pickup bar).
-- Writes ockm-pat-<track>-note, -on, -acc and -slide. Listens to ockm-<track>-<setting> for rhythm, notes, riff, repeat,
-- octave, lock, density, seed, outside, rests, slideamt, sync, mode, gen and len, plus ockm-root, ockm-scale,
-- ockm-loading, ockm-chord-changed, ockm-chord-edit, ockm-chord-len, ockm-edit, ockm-drums-changed and ockm-bass-riff.
--
-- Two kinds of trigger: picking a preset or a setting (or pressing new) always rebuilds and puts the part on auto.
-- The rest (key, scale, the chords changing, the kick changing under a locked part, a new length) only rebuilds a part
-- that's on auto. Nothing rebuilds while a project loads.
--
-- The random choices (mutate, density, rests, slides, the lead's decorations) are hashes of the step and the mutate seed,
-- so a variation repeats exactly. They're worked out in 32-bit floats, as Pd's expr did, so loops made before v1.13
-- come out note for note the same.

local lm = pd.Class:new():register("ockm-linemaker")

-- BEGIN PRESETS (written by tools/build.py: edit the lists there, not here)
local RHYTHMS = {
 bass = {
  { 0, 0, 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 1, 1, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 0, 0 },   -- offbeat
  { 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 1, 0, 1, 0, 1, 1, 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 1, 0, 0, 0, 0, 0 },   -- 8ths
  { 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 2, 1, 3, 5, 5, 6 },   -- 16ths
  { 2, 0, 0, 1, 0, 0, 1, 0, 0, 2, 0, 0, 1, 0, 0, 1, 2, 0, 0, 1, 0, 0, 1, 0, 0, 2, 0, 1, 0, 1, 0, 1, 2, 0, 0, 1, 0, 0, 1, 0, 0, 2, 0, 0, 1, 0, 0, 0 },   -- dotted
  { 1, 0, 2, 0, 1, 0, 2, 0, 1, 0, 2, 0, 1, 0, 2, 0, 1, 0, 2, 0, 1, 0, 2, 0, 1, 0, 2, 0, 1, 0, 1, 0, 1, 2, 1, 2, 1, 2, 1, 2, 1, 0, 2, 0, 1, 0, 2, 0 },   -- octave
  { 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6, 4, 5, 5, 5, 5, 5, 5, 6, 4, 5, 5, 5, 5, 5, 5, 6, 3, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6 },   -- held
  { 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 1, 1, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 1, 0, 1, 0 },   -- on-the-beat
  { 2, 0, 0, 1, 0, 0, 1, 0, 2, 0, 0, 1, 0, 0, 1, 0 },   -- dembow
  { 2, 0, 0, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 2, 0, 0, 0, 1, 0, 2, 0, 0, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0 },   -- two-step
  { 2, 1, 1, 0, 1, 1, 0, 2, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1, 1, 2, 0, 1, 1, 0, 1, 1, 2, 0, 2, 1, 1, 0, 1, 1, 0, 2, 1, 1, 0, 1, 1, 1, 1, 1 },   -- cluster
  { 0, 2, 1, 1, 0, 2, 1, 1, 0, 2, 1, 1, 0, 2, 1, 1 },   -- round-the-kick
  { 0, 0, 2, 1, 0, 1, 2, 0, 0, 0, 2, 1, 0, 1, 2, 0 },   -- gallop
  { 2, 0, 3, 1, 2, 0, 3, 0, 1, 3, 2, 0, 3, 0, 4, 1, 2, 0, 3, 1, 2, 0, 3, 0, 1, 3, 2, 0, 3, 3, 4, 1, 2, 0, 3, 1, 2, 0, 3, 0, 0, 0, 0, 0, 3, 0, 4, 1 },   -- acid
  { 2, 1, 3, 1, 2, 1, 1, 3, 2, 1, 3, 1, 2, 3, 1, 1 },   -- acid-16ths
  { 0, 0, 2, 0, 0, 1, 0, 0, 0, 0, 2, 0, 0, 1, 0, 1, 0, 0, 2, 0, 0, 1, 0, 0, 0, 0, 2, 0, 1, 1, 1, 1, 0, 0, 2, 0, 0, 1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0 },   -- bounce
  { 2, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0 },   -- sparse-dub
  { 2, 0, 0, 0, 0, 0, 3, 1, 0, 0, 0, 0, 0, 0, 1, 0 },   -- trip-hop
  { 4, 6, 0, 1, 0, 0, 4, 6, 0, 1, 0, 0, 1, 0, 1, 0, 4, 6, 0, 1, 0, 0, 4, 6, 0, 0, 1, 0, 4, 6, 1, 0, 4, 6, 0, 1, 0, 0, 4, 6, 0, 1, 0, 0, 1, 0, 1, 0, 4, 6, 0, 1, 0, 0, 4, 6, 0, 1, 0, 1, 4, 6, 0, 0 },   -- speed-garage
  { 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 1, 0, 1, 1, 1, 1 },   -- house-pickup
 },
 lead = {
  { 0, 0, 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 1, 1 },   -- offbeat
  { 0, 2, 1, 1, 0, 2, 1, 1, 0, 2, 1, 1, 0, 2, 1, 1, 0, 2, 1, 1, 0, 2, 1, 1, 0, 2, 1, 1, 0, 2, 1, 0, 0, 2, 1, 1, 0, 2, 1, 1, 0, 2, 1, 1, 0, 2, 1, 1 },   -- rolling
  { 0, 0, 2, 1, 0, 1, 2, 0, 0, 0, 2, 1, 0, 1, 2, 0 },   -- gallop
  { 2, 1, 0, 1, 3, 4, 1, 0, 2, 1, 3, 1, 0, 2, 1, 3, 2, 1, 0, 1, 3, 4, 1, 0, 2, 1, 3, 1, 0, 2, 1, 0, 2, 1, 0, 1, 3, 4, 1, 0, 2, 1, 3, 1, 0, 2, 1, 3 },   -- acid
  { 2, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0 },   -- sparse-dub
  { 0, 0, 2, 0, 0, 1, 0, 0, 0, 0, 2, 0, 0, 1, 0, 1 },   -- tech-bounce
  { 2, 1, 3, 1, 2, 1, 1, 3, 2, 1, 3, 1, 2, 3, 1, 1 },   -- acid-16ths
  { 2, 0, 0, 0, 0, 0, 3, 1, 0, 0, 0, 0, 0, 0, 1, 0 },   -- trip-hop
  { 2, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 2, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 2, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1 },   -- hook
  { 2, 0, 0, 0, 0, 0, 1, 0, 0, 3, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 0, 0, 1, 0, 0, 3, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 1, 0, 0, 3, 0, 0, 1, 0, 0, 1 },   -- sparse-melody
  { 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 0, 0, 1, 0, 1, 0, 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 1, 0, 1, 0, 1, 0, 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0 },   -- phrase
  { 2, 0, 1, 0, 1, 0, 0, 1, 2, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 1, 0, 1, 0, 0, 1, 2, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0 },   -- question-answer
  { 2, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 2, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 2, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 2, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0 },   -- pickup
  { 2, 1, 1, 1, 2, 1, 1, 0, 2, 1, 1, 1, 2, 1, 1, 0, 2, 1, 1, 1, 2, 1, 1, 0, 2, 1, 1, 1, 2, 1, 1, 0, 2, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 0, 2, 1, 1, 0, 2, 0, 1, 0, 2, 0, 0, 0 },   -- arp-gate
  { 2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },   -- long
  { 2, 0, 0, 2, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 2, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 2, 0, 0, 2, 0, 2, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },   -- stab
 } }
local NOTES = {
  { 0 },   -- root
  { 0, 7 },   -- octaves
  { 0, 4 },   -- root-fifth
  { 0, 0, 7, 0, 2, 0, 6, 4 },   -- acid-riff
  { 0, 1, 2, 4 },   -- walk-up
  { 0, 2, 4, 2 },   -- minor-stab
  { 0, 0, -3, -2 },   -- dub
  { 0, 0, 0, 1 },   -- pedal
  { 0, 2, 4, 7 },   -- arp-up
  { 0, 2, 4, 7, 4, 2 },   -- arp-updown
  { 4, 4, 2, 0, 2, 4, 5, 4 },   -- call
  { 7, 6, 4, 2 },   -- descend
  { -1, 2, 4, 2, 2, 2, 4, 0, -1, -3, 0, 0, 2, -1, -1, 0, 2, 0, -1, -3, -1, -3, 0, 0, 6, 7, 9, 11, 11, 11, 9, 0, 2, 7, 11, 9, 11, 11, 9, 4, 2, 0, 2, 4, 9, 9, 11, 0, -1, 0, 4, 7, 9, 11, 7, 0, 2, 0, 2, 0, 4, 6, 7, 0 },   -- melody
  { 3, 6, 4, 3, 4, 3, 2, 0, 3, 4, 5, 7, 8, 7, 9, 4, 6, 8, 9, 9, 9, 9, 8, 0, -1, -3, -3, -3, -2, 1, 0, 4, 5, 6, 8, 9, 9, 8, 9, 0, 3, 2, 3, 4, 3, 2, 2, 4, 5, 5, 6, 7, 9, 9, 9, 0, 3, 4, 6, 8, 9, 8, 9, 4 },   -- melody-steps
  { 6, 7, 6, 7, 9, 6, 4, 11, 9, 7, 13, 13, 16, 16, 18, 7, 6, 4, 9, 7, 4, 6, 4, 7, 6, 4, 7, 7, 9, 13, 14, 11, 9, 11, 11, 16, 18, 16, 14, 7, 6, 7, 9, 13, 13, 16, 18, 11, 13, 16, 18, 18, 18, 18, 18, 7, 9, 7, 9, 11, 9, 11, 13, 11 },   -- melody-high
  { 0, 0, -1, 0, 0, 1, 2, 3, 4, 4, 3, 2, 2, 2, 3, 2, 0, 0, -1, 0, 0, 1, 2, 3, 4, 4, 3, 2, 2, 2, 3, 2, 0, 0, 1, 0, 0, 1, 2, 3, 4, 4, 5, 4, 4, 4, 3, 4, 0, -1, -2, -2, -3, -2, -2, -1, 0, 0, -1, 0, 0, 0, 1, 0, 4, 5, 6, 6, 7, 8, 9, 10, 11, 11, 11, 11, 11, 11, 11, 11, 4, 5, 6, 6, 7, 8, 9, 10, 11, 11, 11, 11, 11, 11, 11, 11, 4, 5, 6, 6, 7, 8, 9, 10, 11, 11, 11, 11, 11, 11, 11, 11, 4, 4, 3, 2, 2, 2, 1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, 1, 2, 2, 2, 1, 2, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 4, 4, 5, 4, 4, 5, 6, 6, 7, 8, 8, 8, 9, 9, 8, 9, 4, 4, 5, 4, 4, 5, 6, 6, 7, 8, 8, 8, 9, 9, 8, 9, 4, 4, 3, 4, 4, 5, 6, 6, 7, 8, 9, 10, 11, 11, 10, 11, 4, 4, 3, 2, 2, 2, 1, 0, 0, 0, 1, 0, 0, 0, -1, 0, 0, 0, 1, 2, 2, 2, 3, 4, 4, 4, 3, 2, 2, 2, 3, 2, 0, 0, 1, 2, 2, 2, 3, 4, 4, 4, 3, 2, 2, 2, 3, 2, 0, 0, 1, 2, 2, 2, 3, 4, 4, 4, 5, 4, 4, 4, 5, 4, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 4, 4, 3, 2, 2, 2, 3, 4, 4, 5, 6, 8, 9, 9, 8, 9, 4, 4, 3, 2, 2, 2, 3, 4, 4, 5, 6, 8, 9, 9, 8, 9, 4, 4, 3, 2, 2, 2, 3, 4, 4, 6, 8, 9, 11, 11, 11, 11, 4, 2, 0, -1, -3, -2, -2, -1, 0, 0, -1, 0, 0, 0, 1, 0, 4, 5, 6, 8, 9, 9, 10, 9, 9, 9, 8, 9, 9, 9, 10, 9, 4, 5, 6, 8, 9, 9, 10, 9, 9, 9, 8, 9, 9, 9, 10, 9, 4, 5, 6, 8, 9, 9, 10, 9, 9, 10, 10, 10, 11, 11, 10, 11, 4, 2, 0, -1, -3, -2, -2, -1, 0, 0, -1, 0, 0, 0, -1, 0, 0, 0, 1, 2, 2, 2, 3, 4, 4, 5, 6, 6, 7, 7, 8, 7, 0, 0, 1, 2, 2, 2, 3, 4, 4, 5, 6, 6, 7, 7, 8, 7, 0, 0, 1, 2, 2, 2, 3, 4, 4, 5, 6, 8, 9, 9, 8, 9, 0, -1, -2, -2, -3, -2, -2, -1, 0, 0, 1, 0, 0, 0, -1, 0 },   -- motif
  { 0, 1, 2, 3, 4, 5, 6, 6, 7, 6, 4, 3, 2, 2, 3, 2, 0, 2, 4, 5, 7, 6, 6, 5, 4, 4, 5, 4, 4, 4, 3, 4, 0, 1, 2, 3, 4, 5, 6, 6, 7, 6, 4, 3, 2, 2, 3, 2, 0, -1, -2, -2, -3, -2, -2, -1, 0, 0, -1, 0, 0, 0, -1, 0, 0, 0, 1, 2, 2, 2, 1, 2, 2, 2, 3, 4, 4, 4, 3, 4, 0, 0, 1, 2, 2, 2, 3, 4, 4, 4, 5, 4, 4, 4, 3, 4, 0, 0, 1, 2, 2, 2, 1, 2, 2, 2, 3, 4, 4, 4, 3, 4, 0, -1, -2, -2, -3, -2, -2, -1, 0, 0, 1, 0, 0, 0, 1, 0, 2, 2, 3, 4, 4, 4, 3, 4, 4, 4, 3, 2, 2, 2, 3, 2, 2, 2, 1, 2, 2, 2, 3, 4, 4, 4, 5, 4, 4, 4, 5, 4, 2, 2, 3, 4, 4, 4, 3, 4, 4, 4, 3, 2, 2, 2, 3, 2, 2, 1, 0, -2, -3, -2, -2, -1, 0, 0, -1, 0, 0, 0, 1, 0, 0, -1, -2, -2, -3, -3, -2, -3, -3, -2, 0, 1, 2, 2, 1, 2, 0, 2, 4, 5, 7, 6, 6, 5, 4, 4, 5, 4, 4, 4, 5, 4, 0, -1, -2, -2, -3, -3, -2, -3, -3, -2, 0, 1, 2, 2, 1, 2, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 2, 2, 3, 4, 4, 5, 6, 8, 9, 8, 8, 8, 7, 7, 6, 7, 2, 3, 4, 6, 7, 6, 6, 5, 4, 4, 3, 4, 4, 4, 5, 4, 2, 2, 3, 4, 4, 5, 6, 8, 9, 8, 8, 8, 7, 7, 6, 7, 2, 2, 1, 2, 2, 2, 1, 0, 0, 0, 1, 0, 0, 0, -1, 0, 2, 2, 3, 2, 2, 1, 0, -2, -3, -2, -2, -1, 0, 0, 1, 0, 2, 3, 4, 6, 7, 6, 6, 5, 4, 4, 5, 4, 4, 4, 5, 4, 2, 2, 3, 2, 2, 1, 0, -2, -3, -2, -2, -1, 0, 0, 1, 0, 2, 2, 1, 2, 2, 2, 1, 0, 0, 0, 1, 0, 0, 0, -1, 0, 0, -1, -2, -2, -3, -2, 0, 1, 2, 2, 1, 0, 0, 0, -1, 0, 0, 2, 4, 5, 7, 6, 6, 5, 4, 4, 3, 4, 4, 4, 5, 4, 0, -1, -2, -2, -3, -2, 0, 1, 2, 2, 1, 0, 0, 0, -1, 0, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 4, 5, 6, 6, 7, 8, 8, 8, 9, 10, 10, 10, 11, 11, 10, 11, 4, 4, 3, 2, 2, 2, 3, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 5, 6, 6, 7, 8, 8, 8, 9, 10, 10, 10, 11, 11, 10, 11, 4, 4, 3, 2, 2, 2, 1, 0, 0, 0, -1, 0, 0, 0, -1, 0 },   -- motif-call
  { 11, 11, 10, 9, 9, 10, 11, 13, 14, 14, 15, 14, 14, 14, 15, 14, 11, 11, 10, 9, 9, 10, 11, 13, 14, 14, 15, 14, 14, 14, 15, 14, 11, 11, 10, 9, 9, 10, 11, 13, 14, 15, 15, 15, 16, 16, 17, 16, 11, 9, 7, 6, 4, 5, 5, 6, 7, 7, 6, 7, 7, 7, 6, 7, 9, 9, 10, 11, 11, 12, 13, 15, 16, 16, 17, 16, 16, 16, 17, 16, 9, 9, 10, 11, 11, 12, 13, 15, 16, 16, 17, 16, 16, 16, 17, 16, 9, 9, 10, 11, 11, 12, 13, 15, 16, 17, 17, 17, 18, 18, 18, 18, 9, 8, 7, 5, 4, 5, 5, 6, 7, 7, 8, 7, 7, 7, 6, 7, 11, 11, 10, 11, 11, 11, 10, 11, 11, 11, 12, 11, 11, 11, 10, 11, 11, 11, 10, 11, 11, 11, 10, 11, 11, 11, 12, 11, 11, 11, 10, 11, 11, 11, 10, 11, 11, 11, 12, 11, 11, 12, 13, 13, 14, 14, 15, 14, 11, 11, 10, 9, 9, 9, 8, 7, 7, 7, 8, 7, 7, 7, 8, 7, 7, 6, 5, 5, 4, 5, 5, 6, 7, 6, 5, 5, 4, 4, 4, 4, 7, 6, 5, 5, 4, 5, 5, 6, 7, 6, 5, 5, 4, 4, 4, 4, 7, 6, 5, 5, 4, 5, 5, 6, 7, 7, 8, 7, 7, 7, 6, 7, 7, 6, 5, 5, 4, 5, 5, 6, 7, 7, 8, 7, 7, 7, 6, 7, 7, 6, 5, 5, 4, 4, 5, 4, 4, 5, 7, 8, 9, 9, 10, 9, 7, 6, 5, 5, 4, 4, 5, 4, 4, 5, 7, 8, 9, 9, 10, 9, 7, 6, 5, 5, 4, 4, 5, 4, 4, 6, 7, 9, 11, 11, 12, 11, 7, 6, 5, 5, 4, 5, 5, 6, 7, 7, 6, 7, 7, 7, 6, 7, 7, 7, 8, 7, 7, 6, 5, 5, 4, 5, 5, 6, 7, 7, 6, 7, 7, 7, 8, 7, 7, 6, 5, 5, 4, 5, 5, 6, 7, 7, 6, 7, 7, 7, 6, 7, 7, 6, 5, 5, 4, 5, 7, 8, 9, 9, 10, 9, 7, 7, 8, 9, 9, 9, 8, 7, 7, 7, 8, 7, 7, 7, 8, 7, 9, 10, 11, 13, 14, 15, 15, 15, 16, 15, 15, 15, 14, 14, 13, 14, 9, 10, 11, 13, 14, 15, 15, 15, 16, 15, 15, 15, 14, 14, 13, 14, 9, 10, 11, 13, 14, 15, 15, 15, 16, 16, 17, 16, 16, 16, 17, 16, 9, 8, 7, 5, 4, 5, 5, 6, 7, 7, 6, 7, 7, 7, 8, 7, 11, 11, 12, 11, 11, 12, 13, 13, 14, 13, 13, 12, 11, 11, 10, 11, 11, 11, 12, 11, 11, 12, 13, 13, 14, 13, 13, 12, 11, 11, 10, 11, 11, 11, 12, 11, 11, 12, 13, 13, 14, 14, 13, 14, 14, 14, 15, 14, 11, 9, 7, 6, 4, 5, 5, 6, 7, 7, 8, 7, 7, 7, 6, 7 },   -- motif-high
  { 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4, 0, 2, 0, 4, 0, 7, 0, 2, 0, 4, 0, 7, 0, 2, 0, 4, 0, 2, 0, 4, 0, 7, 0, 2, 0, 4, 0, 7, 0, 2, 0, 4, 2, 4, 2, 7, 2, 9, 2, 4, 2, 7, 2, 9, 2, 4, 2, 7, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 0, 2, 0, 4, 0, 7, 0, 2, 0, 4, 0, 7, 0, 2, 0, 4, 0, 2, 0, 4, 0, 7, 0, 2, 0, 4, 0, 7, 0, 2, 0, 4, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 0, 4, 2, 7, 0, 4, 2, 7, 0, 4, 2, 7, 0, 4, 2, 7, 0, 4, 2, 7, 0, 4, 2, 7, 0, 4, 2, 7, 0, 4, 2, 7, 2, 7, 4, 9, 2, 7, 4, 9, 2, 7, 4, 9, 2, 7, 4, 9, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, 0, 2, 4, 7, 0, 2, 4, 7, 0, 2, 4, 7, 0, 2, 4, 7, 0, 2, 4, 7, 0, 2, 4, 7, 0, 2, 4, 7, 0, 2, 4, 7, 0, 2, 4, 7, 4, 2, 0, 2, 4, 7, 4, 2, 0, 2, 4, 7, 0, 2, 4, 7, 4, 2, 0, 2, 4, 7, 4, 2, 0, 2, 4, 7, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, -3, 0, 2, 4, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 7, 4, 2, 0, 9, 7, 4, 2, 9, 7, 4, 2, 9, 7, 4, 2, 9, 7, 4, 2, 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4, 0, 4, 7, 4 },   -- arp-evolve
  { 0 },   -- answer-the-bass
  { 0, 0, -1, 0, 0, 1, 2, 3, 4, 4, 3, 2, 2, 2, 3, 2, 0, 0, -1, 0, 0, 1, 2, 3, 4, 4, 3, 2, 2, 2, 3, 2, 2, 2, 3, 2, 2, 3, 4, 6, 7, 6, 6, 5, 4, 4, 5, 4, 0, -1, -2, -2, -3, -2, -2, -1, 0, 0, -1, 0, 0, 0, -1, 0, 4, 5, 6, 6, 7, 8, 9, 10, 11, 11, 11, 11, 11, 11, 11, 11, 4, 5, 6, 6, 7, 8, 9, 10, 11, 11, 11, 11, 11, 11, 11, 11, 7, 8, 8, 8, 9, 10, 10, 10, 11, 11, 10, 11, 11, 11, 10, 11, 4, 4, 3, 2, 2, 2, 1, 0, 0, 0, 1, 0, 0, 0, -1, 0, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 0, -1, -2, -2, -3, -2, -2, -1, 0, 0, -1, 0, 0, 0, 1, 0, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 4, 4, 5, 4, 4, 5, 6, 6, 7, 8, 8, 8, 9, 9, 8, 9, 4, 4, 5, 4, 4, 5, 6, 6, 7, 8, 8, 8, 9, 9, 8, 9, 7, 7, 6, 7, 7, 8, 8, 8, 9, 10, 10, 10, 11, 11, 10, 11, 4, 4, 3, 2, 2, 2, 1, 0, 0, 0, 1, 0, 0, 0, -1, 0, 0, 0, 1, 2, 2, 2, 3, 4, 4, 4, 3, 2, 2, 2, 3, 2, 0, 0, 1, 2, 2, 2, 3, 4, 4, 4, 3, 2, 2, 2, 3, 2, 2, 2, 3, 4, 4, 5, 6, 6, 7, 6, 6, 5, 4, 4, 5, 4, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 4, 4, 3, 2, 2, 2, 3, 4, 4, 5, 6, 8, 9, 9, 8, 9, 4, 4, 3, 2, 2, 2, 3, 4, 4, 5, 6, 8, 9, 9, 8, 9, 7, 6, 6, 5, 4, 5, 6, 6, 7, 8, 9, 10, 11, 11, 11, 11, 4, 2, 0, -1, -3, -2, -2, -1, 0, 0, -1, 0, 0, 0, 1, 0, 4, 5, 6, 8, 9, 9, 10, 9, 9, 9, 8, 9, 9, 9, 10, 9, 4, 5, 6, 8, 9, 9, 10, 9, 9, 9, 8, 9, 9, 9, 10, 9, 4, 3, 2, 1, 0, 0, 1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 4, 2, 0, -1, -3, -2, -2, -1, 0, 0, -1, 0, 0, 0, -1, 0, 0, 0, 1, 2, 2, 2, 3, 4, 4, 5, 6, 6, 7, 7, 8, 7, 0, 0, 1, 2, 2, 2, 3, 4, 4, 5, 6, 6, 7, 7, 8, 7, 2, 2, 3, 4, 4, 5, 6, 6, 7, 8, 8, 8, 9, 9, 8, 9, 0, -1, -2, -2, -3, -2, -2, -1, 0, 0, 1, 0, 0, 0, -1, 0 },   -- motif-loose
  { 0, 1, 2, 3, 4, 5, 6, 6, 7, 6, 4, 3, 2, 2, 3, 2, 0, 2, 4, 5, 7, 6, 6, 5, 4, 4, 5, 4, 4, 4, 3, 4, 0, -1, -2, -2, -3, -3, -3, -3, -3, -3, -3, -3, -3, -3, -3, -3, 0, -1, -2, -2, -3, -2, -2, -1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 2, 2, 2, 1, 2, 2, 2, 3, 4, 4, 4, 3, 4, 0, 0, 1, 2, 2, 2, 3, 4, 4, 4, 5, 4, 4, 4, 3, 4, 2, 2, 3, 4, 4, 4, 5, 4, 4, 5, 6, 6, 7, 7, 8, 7, 0, -1, -2, -2, -3, -2, -2, -1, 0, 0, 1, 0, 0, 0, 1, 0, 2, 2, 3, 4, 4, 4, 3, 4, 4, 4, 3, 2, 2, 2, 3, 2, 2, 2, 1, 2, 2, 2, 3, 4, 4, 4, 5, 4, 4, 4, 5, 4, 2, 2, 1, 0, 0, 0, -1, 0, 0, 0, 1, 2, 2, 2, 3, 2, 2, 1, 0, -2, -3, -2, -2, -1, 0, 0, -1, 0, 0, 0, -1, 0, 0, -1, -2, -2, -3, -3, -2, -3, -3, -2, 0, 1, 2, 2, 1, 2, 0, 2, 4, 5, 7, 6, 6, 5, 4, 4, 5, 4, 4, 4, 5, 4, 2, 2, 1, 0, 0, 0, 1, 0, 0, 1, 2, 3, 4, 4, 5, 4, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 2, 2, 3, 4, 4, 5, 6, 8, 9, 8, 8, 8, 7, 7, 6, 7, 2, 3, 4, 6, 7, 6, 6, 5, 4, 4, 3, 4, 4, 4, 5, 4, 4, 5, 6, 6, 7, 8, 9, 10, 11, 10, 10, 10, 9, 9, 8, 9, 2, 2, 3, 2, 2, 2, 1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 2, 2, 3, 2, 2, 1, 0, -2, -3, -2, -2, -1, 0, 0, 1, 0, 2, 3, 4, 6, 7, 6, 6, 5, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4, 3, 4, 4, 3, 2, 1, 0, 0, 1, 2, 2, 2, 3, 2, 2, 2, 1, 2, 2, 2, 1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 0, -1, -2, -2, -3, -2, 0, 1, 2, 2, 1, 0, 0, 0, -1, 0, 0, 2, 4, 5, 7, 6, 6, 5, 4, 4, 3, 4, 4, 4, 5, 4, 2, 2, 1, 0, 0, 1, 2, 3, 4, 4, 3, 2, 2, 2, 3, 2, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 4, 5, 6, 6, 7, 8, 8, 8, 9, 10, 10, 10, 11, 11, 10, 11, 4, 4, 3, 2, 2, 2, 3, 4, 4, 4, 5, 4, 4, 4, 5, 4, 4, 4, 3, 2, 2, 2, 1, 0, 0, -1, -2, -2, -3, -3, -3, -3, 4, 4, 3, 2, 2, 2, 1, 0, 0, 0, -1, 0, 0, 0, 1, 0 },   -- call-loose
}
local BASS_RIFFS = {
  { 0 },   -- root
  { 0, 7 },   -- octaves
  { 0, 4 },   -- fifth
  { 0, 0, -1 },   -- seventh-below
  { 0, 0, -3, -2 },   -- dub
  { 0, 1, 2, 4 },   -- walk-up
  { 0, 0, 7, 0, 2, 0, 6, 4 },   -- acid
  { 0, 2, 4, 7 },   -- arp
}
local SCALES = {
  { 0, 2, 3, 5, 7, 8, 10 },   -- minor
  { 0, 2, 4, 5, 7, 9, 11 },   -- major
  { 0, 2, 3, 5, 7, 9, 10 },   -- dorian
  { 0, 1, 3, 5, 7, 8, 10 },   -- phrygian
  { 0, 2, 4, 5, 7, 9, 10 },   -- mixolydian
  { 0, 2, 3, 5, 7, 8, 11 },   -- harmonic-minor
}
-- END PRESETS

local REPEAT_LOOSE = { [15] = 20, [16] = 21 }   -- repeat loose: motif and question swap for their loose versions
local ANSWER = 19                               -- the tune that answers the bass (plays the bass riff in its gaps)

-- ---------------------------------------------------------------- 32-bit floats, as Pd's expr
local spack, sunpack = string.pack, string.unpack
local function f(x) return (sunpack("f", spack("f", x))) end
local function trunc(x) return x >= 0 and math.floor(x) or -math.floor(-x) end
-- frac(abs(sin(a*i + b*seed + c) * m)): the hash every random choice uses
local function hash(i, a, seed, b, c, m)
  local x = f(f(f(f(i) * f(a)) + f(f(seed) * f(b))) + f(c))
  local y = f(math.abs(f(f(math.sin(x)) * f(m))))
  return f(y - math.floor(y))
end
local function h_std(i, seed, k) return hash(i, 12.9898, seed, 78.233, k, 43758.5453) end

-- ---------------------------------------------------------------- one step
-- v: the rhythm code (0 rest, 1 note, 2 accent, 3 note+slide, 4 accent+slide, 5 hold+slide, 6 hold)
-- lock: 0 own rhythm, 1 lock to the kick, 2 fill the gaps; other: the kick (or, answering, the bass) on this step
local function locked(v, other, lock)
  if lock == 1 then
    if other > 0 then return (v == 2 or v == 4 or other >= 2) and 2 or 1 end
    return 0
  elseif lock == 2 then
    return other > 0 and 0 or v
  end
  return v
end
-- density below 1 thins plain notes, above 1 adds notes in the rests
local function thinned(v, density, seed, i)
  local H = h_std(i, seed, 1.7)
  if v > 0 and v < 5 and density < 1 and v ~= 2 and v ~= 4 and H > density then return 0 end
  if v == 0 and density > 1 and H < f(f(density - 1) * f(0.5)) then return 1 end
  return v
end
-- mutate (seed above 0): a note on about one 8th-note rest in five, about one plain note in seven dropped; the bass's
-- last bar of a loop of 2 bars or more gets a pickup on its last 8th
local function mutated(v, i, seed, len, lead)
  local H = h_std(i, seed, 7.7)
  if seed > 0 and v == 0 and trunc(i) % 2 == 0 and H < f(0.2) then return 1 end
  if seed > 0 and v == 1 and H > f(0.85) then return 0 end
  if not lead and len >= 32 and i >= len - 16 and trunc(i) % 16 == 14 and v == 0 then return 1 end
  return v
end
-- rests (0-1): a share of the notes rest, different in every bar
local function rested(v, i, rests, seed)
  if v > 0 and v < 5 and rests > 0 then
    local x = f(f(f(f(i) * f(1.731)) + f(f(seed) * f(5.21))) + f(f(math.floor(f(i / 16))) * f(3.3)))
    x = f(x + f(0.37))
    local y = f(math.abs(f(f(math.sin(x)) * f(6151.7))))
    if f(y - math.floor(y)) < f(f(rests) * f(0.5)) then return 0 end
  end
  return v
end
local function slides(v, i, seed, amt)
  if v >= 3 and v ~= 6 then return 1 end
  if v > 0 and amt > 0 and hash(i, 3.917, seed, 11.3, 2.9, 7919.3) < f(f(amt) * f(0.7)) then return 1 end
  return 0
end
-- the lead: a note off the chord moves onto it on the beat; from inside (0) to outside (1) it gains passing notes,
-- colour (7ths, 9ths), octave leaps and chromatic slips. d counts scale steps from the chord's root
local function snapped(d, i, outside, seed)
  local R = trunc(d) % 7
  local SN = d - ((R == 1 or R == 3 or R == 5) and 1 or 0) + (R == 6 and 1 or 0)
  if outside < f(0.25) then return SN end
  local IN
  if trunc(i) % 4 == 0 then
    if outside >= f(0.5) and h_std(i, seed, 1.1) < f(outside - f(0.5)) then
      IN = d - R + 6 + 2 * ((h_std(i, seed, 2.3) < f(0.5)) and 1 or 0)
    else IN = SN end
  else
    if h_std(i, seed, 3.7) < f(f(outside - f(0.25)) * f(1.2)) then
      IN = d + 1 - 2 * ((h_std(i, seed, 4.1) < f(0.5)) and 1 or 0)
    else IN = d end
  end
  local LP = (outside >= f(0.75) and h_std(i, seed, 5.3) < f(f(outside - f(0.75)) * f(1.2))) and 7 or 0
  return IN + LP
end

-- The whole line. s: the settings; t: the tables it reads (rhythm, notes, scale, chord degrees, kick, bass hits);
-- last: the note a hold repeats if the line starts on one. Returns the four lists (1-based, len long) and the last note.
-- A rest leaves its note alone (nil): the old note stays in the table, as it always has.
function lm.line(s, t, len, last)
  local note, on, acc, slide = {}, {}, {}, {}
  local r, n, sc = t.rhythm, t.notes, t.scale
  local R, L = #r, #n
  local base = ((36 + s.root > 40) and (24 + s.root) or (36 + s.root)) + 12 * s.octave + s.offset
  local is19 = (math.floor(s.notes) == ANSWER)
  local lock = is19 and 2 or s.lock
  local k = 0
  for i = 0, len - 1 do
    -- the rhythm: a one-bar rhythm with siblings is 48 long (the bar, then two alternative last bars for variations)
    local idx
    if R == 48 then
      if s.seed > 0 and i >= trunc(len) - 16 then idx = 16 * (1 + (trunc(s.seed) - 1) % 2) + i % 16 else idx = i % 16 end
    else idx = i % math.max(R, 1) end
    local v = r[math.max(0, math.min(63, idx)) + 1] or 0
    local other = is19 and (t.bass_on[i + 1] or 0) or (t.kick[i + 1] or 0)
    v = locked(v, other, lock)
    v = thinned(v, s.density, s.seed, i)
    v = mutated(v, i, s.seed, len, s.lead)
    v = rested(v, i, s.rests, s.seed)
    on[i + 1] = (v > 0) and 1 or 0
    acc[i + 1] = (v == 2 or v == 4) and 1 or 0
    slide[i + 1] = slides(v, i, s.seed, s.slideamt)
    if v >= 5 then
      note[i + 1] = last                         -- a hold: the note before, sliding on
    elseif v > 0 then
      local ix
      if L == 512 then ix = ((trunc(s.seed) + math.floor(i / 64)) % 8) * 64 + i % 64   -- a four-bar tune: A, then A'
      else ix = (k + trunc(s.seed)) % L end
      k = k + 1
      local d = n[math.max(0, math.min(511, ix)) + 1] or 0
      if L ~= 512 and s.seed > 0 and hash(i, 7.13, s.seed, 3.7, 0.3, 9137.21) < f(0.2) then d = d + 7 end   -- an octave jump
      if s.lead then d = snapped(d, i, s.outside, s.seed) end
      local cd = trunc(t.chord_deg[i + 1] or 0)
      if cd >= 4 then cd = cd - 7 end            -- V, VI and VII sit below the root
      d = d + cd * (s.sync and 1 or 0)
      local x = trunc(d)
      local nn = (sc[x % 7 + 1] or 0) + 12 * math.floor(d / 7) + base
      if s.lead and s.outside >= f(0.75) and trunc(i) % 4 ~= 0 and h_std(i, s.seed, 6.7) < f(f(s.outside - f(0.75)) * f(1.6)) then
        nn = nn - 1                              -- a chromatic slip
      end
      note[i + 1] = nn; last = nn
    end
  end
  return note, on, acc, slide, last
end

-- ---------------------------------------------------------------- the Pd object
function lm:initialize(sel, atoms)
  self.inlets, self.outlets = 0, 0
  local a = function(j, d) return tonumber(atoms[j]) or d end
  self.track = tostring(atoms[1] or "bass")
  self.s = { offset = a(2, 0), rhythm = a(3, 0), notes = a(4, 0), lead = (a(7, 0) > 0),
             root = 9, scale = 0, octave = 0, lock = 0, density = 1, seed = 0, outside = f(0.35), rests = 0, slideamt = 0,
             riff = -1, rep = 0, sync = (a(6, 0) ~= 0) }
  self.bass_riff = 0
  self.mode = a(5, 0)
  self.len = 128
  self.loading = false
  self.last = 0
  return true
end

function lm:postinitialize()
  local t, s = self.track, self.s
  self.recv = {}
  local function on(name, fn)
    local m = "r_" .. #self.recv
    self[m] = function(o, sel, at) fn(tonumber(at[1]) or 0) end
    self.recv[#self.recv + 1] = pd.Receive:new():register(self, name, m)
  end
  -- settings: store, then rebuild and go back to auto
  for hook, key in pairs({ rhythm = "rhythm", notes = "notes", riff = "riff", ["repeat"] = "rep", octave = "octave", lock = "lock",
                            density = "density", seed = "seed", outside = "outside", rests = "rests", slideamt = "slideamt" }) do
    on("ockm-" .. t .. "-" .. hook, function(x) s[key] = x; self:explicit() end)
  end
  on("ockm-" .. t .. "-gen", function() self:explicit() end)
  -- the key: only an auto part follows
  on("ockm-root", function(x) s.root = x; self:implicit() end)
  on("ockm-scale", function(x) s.scale = x; self:implicit() end)
  on("ockm-" .. t .. "-mode", function(x) self.mode = x end)
  on("ockm-loading", function(x) self.loading = (x ~= 0) end)
  on("ockm-bass-riff", function(x) self.bass_riff = x end)
  on("ockm-" .. t .. "-sync", function(x) s.sync = (x ~= 0) end)
  -- the chords changed: a synced part follows
  on("ockm-chord-changed", function() if s.sync then self:implicit() end end)
  on("ockm-chord-edit", function() if s.sync then self:implicit() end end)
  -- the chords' length: a synced part takes it too
  on("ockm-chord-len", function(x)
    if not self.loading and s.sync then pd.send("ockm-" .. t .. "-len", "float", { x }) end
  end)
  -- the kick changed under a part locked to it
  local function drums() if s.lock ~= 0 then self:implicit() end end
  on("ockm-edit", drums); on("ockm-drums-changed", drums)
  -- a new length: an auto part rebuilds to fill it, once everything else has heard the new length
  on("ockm-" .. t .. "-len", function(x) self.len = x; if not self.loading then self.lenclock:delay(0) end end)
  self.lenclock = pd.Clock:new():register(self, "refill")
end

function lm:finalize()
  for _, r in ipairs(self.recv or {}) do r:destruct() end
  if self.lenclock then self.lenclock:destruct() end
end

function lm:explicit()
  if self.loading then return end
  self.mode = 0; pd.send("ockm-" .. self.track .. "-mode", "float", { 0 })
  self:build()
end
function lm:implicit() if not self.loading and self.mode == 0 then self:build() end end
function lm:refill() if self.mode == 0 then self:build() end end

local function read_table(name, n)
  local tb = pd.Table:new():sync(name)
  local out = {}
  if tb then for i = 0, math.min(n, tb:length()) - 1 do out[i + 1] = tb:get(i) end end
  return out
end

-- the tables this line reads, picked by the settings
function lm:tables()
  local s = self.s
  local notes
  if s.riff >= 0 then notes = BASS_RIFFS[math.floor(s.riff) + 1]
  else
    local nn = math.floor(s.notes)
    if s.rep > 0 and REPEAT_LOOSE[nn] then nn = REPEAT_LOOSE[nn] end
    if nn == ANSWER then notes = BASS_RIFFS[math.max(0, math.floor(self.bass_riff)) + 1]
    else notes = NOTES[nn + 1] end
  end
  return { rhythm = RHYTHMS[self.track == "lead" and "lead" or "bass"][math.floor(s.rhythm) + 1],
           notes = notes, scale = SCALES[math.floor(s.scale) + 1] }
end

function lm:build()
  local t, len = self:tables(), math.floor(self.len)
  -- a preset that doesn't exist leaves the line alone (and keeps whatever it had)
  self.cache = self.cache or {}
  for _, k in ipairs({ "rhythm", "notes", "scale" }) do
    if t[k] then self.cache[k] = t[k] else t[k] = self.cache[k] end
    if not t[k] then return end
  end
  t.chord_deg = read_table("ockm-pat-chord-deg", len)
  t.kick = read_table("ockm-pat-d1", len)
  t.bass_on = read_table("ockm-pat-bass-on", len)
  local note, on, acc, slide, last = lm.line(self.s, t, len, self.last)
  self.last = last
  local tr = self.track
  local tn, to, ta, ts = pd.Table:new():sync("ockm-pat-" .. tr .. "-note"), pd.Table:new():sync("ockm-pat-" .. tr .. "-on"),
                         pd.Table:new():sync("ockm-pat-" .. tr .. "-acc"), pd.Table:new():sync("ockm-pat-" .. tr .. "-slide")
  if not (tn and to and ta and ts) then return end
  for i = 1, math.min(len, tn:length(), to:length(), ta:length(), ts:length()) do
    if note[i] ~= nil then tn:set(i - 1, note[i]) end
    to:set(i - 1, on[i]); ta:set(i - 1, acc[i]); ts:set(i - 1, slide[i])
  end
  tn:redraw(); to:redraw(); ta:redraw(); ts:redraw()
end
