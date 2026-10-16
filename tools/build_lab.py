# OCKM Drum Lab: a separate patch for designing claps and snares and rendering them to WAV.
# Run by tools/build.py (it uses P, D and R from there). Writes OCKM_DRUM_LAB.pd and lab/.
# Nothing in the instrument depends on it: the lab only writes WAVs into samples/clap and samples/snare.

LAB_CLAP = [  # name, low, high, start, label
    ("bursts", 1, 6, 4, "bursts"), ("gap", 4, 25, 10, "gap between bursts (ms)"), ("jitter", 0, 1, 0.3, "looseness"),
    ("bdecay", 2, 15, 6, "burst length (ms)"), ("toneA", 600, 2500, 1150, "body tone (Hz)"), ("toneB", 1500, 6000, 2600, "air tone (Hz)"),
    ("width", 0.5, 6, 2.2, "tone focus"), ("balance", 0, 1, 0.4, "body to air"), ("tail", 30, 600, 180, "tail (ms)"),
    ("tailtone", 500, 3000, 1200, "tail tone (Hz)"), ("room", 0, 0.9, 0.35, "room"), ("drive", 0, 1, 0.35, "snap / drive"),
    ("level", 0, 1, 0.8, "level"),
]
LAB_SNARE = [
    ("pitch", 120, 320, 190, "body pitch (Hz)"), ("ratio", 1.2, 2.2, 1.6, "second tone ratio"), ("drop", 0, 12, 5, "pitch drop (semitones)"),
    ("droptime", 5, 60, 20, "drop time (ms)"), ("bodydec", 30, 300, 110, "body decay (ms)"), ("wires", 1500, 8000, 3800, "wires tone (Hz)"),
    ("wwidth", 0.3, 3, 0.9, "wires focus"), ("wdecay", 40, 400, 170, "wires decay (ms)"), ("click", 0, 1, 0.4, "click"),
    ("mix", 0, 1, 0.55, "body to wires"), ("drive", 0, 1, 0.3, "drive"), ("level", 0, 1, 0.8, "level"),
]
os.makedirs(os.path.join(R, "lab"), exist_ok=True)
MK_CLAP, MK_SNARE = 1.4, 1.0      # makeup gain before the drive (set by ear and by measuring renders)

# ---- a band-pass whose frequency and focus come from two receive names (RBJ, 0 dB at the centre)
q = P()
q.add("#X text 20 10 Band-pass for the lab: args are the receive names for frequency and focus (Q).;")
inl = q.add("#X obj 30 40 inlet~;")
bq = q.add("#X obj 30 200 biquad~;"); out = q.add("#X obj 30 230 outlet~;")
rf = q.add(f"#X obj 200 40 r {D}1;"); rq = q.add(f"#X obj 300 40 r {D}2;"); tq = q.add("#X obj 300 65 t b f;")
lb = q.add("#X obj 420 40 loadbang;"); sr = q.add("#X obj 420 65 samplerate~;"); tsr = q.add("#X obj 420 90 t b f;")
S = f"(if({D}f3>1 \\, {D}f3 \\, 48000))"; Qx = f"(max({D}f2 \\, 0.1))"; W = f"(6.2831853*{D}f1/{S})"; A = f"(sin({W})/(2*{Qx}))"
ex = q.add(f"#X obj 200 120 expr 2*cos({W})/(1+{A}) \\; -(1-{A})/(1+{A}) \\; {A}/(1+{A}) \\; 0 \\; -{A}/(1+{A});")
pk = q.add("#X obj 200 160 pack f f f f f;")
for c in [(inl, 0, bq, 0), (bq, 0, out, 0), (rf, 0, ex, 0), (rq, 0, tq, 0), (tq, 1, ex, 1), (tq, 0, ex, 0), (lb, 0, sr, 0), (sr, 0, tsr, 0),
          (tsr, 1, ex, 2), (tsr, 0, ex, 0), (pk, 0, bq, 0)]: q.con(*c)
for i in range(5): q.con(ex, i, pk, i)
q.save("lab/ockm-lab-bp.pd", "#N canvas 200 200 700 260 12;")

def env_sq(p, x, y, name):
    """[r name] -> vline~ -> squared (so the decay sounds natural)"""
    r = p.add(f"#X obj {x} {y} r {name};"); v = p.add(f"#X obj {x} {y+25} vline~;"); s = p.add(f"#X obj {x} {y+50} *~;")
    p.con(r, 0, v, 0); p.con(v, 0, s, 0); p.con(v, 0, s, 1)
    return s

def drive_out(p, x, y, src, pre, makeup):
    """src -> makeup gain -> tanh drive (lab-<pre>-drive) -> level (lab-<pre>-level) -> outlet~"""
    mk = p.add(f"#X obj {x} {y} *~ {makeup};")
    rd = p.add(f"#X obj {x+150} {y} r lab-{pre}-drive;"); dx = p.add(f"#X obj {x+150} {y+25} expr 1+{D}f1*4;")
    th = p.add(f"#X obj {x} {y+50} expr~ tanh({D}v1*{D}f2)/tanh({D}f2);")
    lv = p.add(f"#X obj {x} {y+80} *~ 0.8;"); rl = p.add(f"#X obj {x+150} {y+55} r lab-{pre}-level;")
    o = p.add(f"#X obj {x} {y+110} outlet~;")
    lb = p.add(f"#X obj {x+300} {y} loadbang;"); one = p.add(f"#X msg {x+300} {y+25} 1;")
    for c in [(src, 0, mk, 0), (mk, 0, th, 0), (rd, 0, dx, 0), (dx, 0, th, 1), (lb, 0, one, 0), (one, 0, th, 1), (th, 0, lv, 0), (rl, 0, lv, 1), (lv, 0, o, 0)]: p.con(*c)

# ---- clap: bursts of two noise bands, a tail of its own, a little room
q = P()
q.add("#X text 20 10 Lab clap: bursts (lab-clap-burst) of two band-passed noise colours \\, a separate tail (lab-clap-tailenv) \\, a small room \\, then drive.;")
nz = q.add("#X obj 30 50 noise~;")
ba = q.add("#X obj 30 90 ockm-lab-bp lab-clap-toneA lab-clap-width;"); bb = q.add("#X obj 300 90 ockm-lab-bp lab-clap-toneB lab-clap-width;")
ga = q.add("#X obj 30 130 *~ 0.6;"); gb = q.add("#X obj 300 130 *~ 0.4;")
rbal = q.add("#X obj 560 90 r lab-clap-balance;"); tbal = q.add("#X obj 560 115 t f f;"); inv = q.add(f"#X obj 560 140 expr 1-{D}f1;")
sm = q.add("#X obj 30 170 +~;")
be = env_sq(q, 700, 50, "lab-clap-burst")
mb = q.add("#X obj 30 210 *~;")
bt = q.add("#X obj 30 260 ockm-lab-bp lab-clap-tailtone lab-clap-tailq;")
lbq = q.add("#X obj 560 200 loadbang;"); mq = q.add("#X msg 560 225 \\; lab-clap-tailq 1.2;")
te = env_sq(q, 700, 200, "lab-clap-tailenv")
mt = q.add("#X obj 30 300 *~;"); tg = q.add("#X obj 30 325 *~ 0.5;")
mix = q.add("#X obj 30 350 +~;"); hp = q.add("#X obj 30 375 hip~ 120;")
# room: a short feedback network of three taps
fb = q.add("#X obj 30 410 +~;"); dw = q.add(f"#X obj 200 440 delwrite~ {D}0-room 100;")
d1 = q.add(f"#X obj 200 470 delread~ {D}0-room 7.3;"); d2 = q.add(f"#X obj 330 470 delread~ {D}0-room 11.1;"); d3 = q.add(f"#X obj 460 470 delread~ {D}0-room 13.7;")
ds = q.add("#X obj 200 500 +~;"); ds2 = q.add("#X obj 200 525 +~;"); dm = q.add("#X obj 200 550 *~ 0.33;"); rm = q.add("#X obj 200 575 *~ 0.35;")
rr = q.add("#X obj 330 550 r lab-clap-room;")
for c in [(nz, 0, ba, 0), (nz, 0, bb, 0), (ba, 0, ga, 0), (bb, 0, gb, 0), (rbal, 0, tbal, 0), (tbal, 1, gb, 1), (tbal, 0, inv, 0), (inv, 0, ga, 1),
          (ga, 0, sm, 0), (gb, 0, sm, 1), (sm, 0, mb, 0), (be, 0, mb, 1), (nz, 0, bt, 0), (bt, 0, mt, 0), (te, 0, mt, 1), (mt, 0, tg, 0),
          (lbq, 0, mq, 0), (mb, 0, mix, 0), (tg, 0, mix, 1), (mix, 0, hp, 0), (hp, 0, fb, 0), (fb, 0, dw, 0),
          (d1, 0, ds, 0), (d2, 0, ds, 1), (ds, 0, ds2, 0), (d3, 0, ds2, 1), (ds2, 0, dm, 0), (dm, 0, rm, 0), (rr, 0, rm, 1), (rm, 0, fb, 1)]: q.con(*c)
drive_out(q, 30, 620, fb, "clap", MK_CLAP)
q.save("lab/ockm-lab-clap.pd", "#N canvas 200 200 900 760 12;")

# ---- snare: a tuned body with a pitch drop, a wires layer, a click
q = P()
q.add("#X text 20 10 Lab snare: two tones with a pitch drop (lab-snare-freq \\, lab-snare-body) \\, band-passed noise wires (lab-snare-wenv) \\, a click (lab-snare-cenv) \\, then drive.;")
rfq = q.add("#X obj 30 50 r lab-snare-freq;"); vf = q.add("#X obj 30 75 vline~;")
o1 = q.add("#X obj 30 110 osc~;"); rrt = q.add("#X obj 200 75 r lab-snare-ratio;"); mr = q.add("#X obj 200 110 *~ 1.6;"); o2 = q.add("#X obj 200 140 osc~;")
g2 = q.add("#X obj 200 170 *~ 0.6;"); bs = q.add("#X obj 30 200 +~;")
benv = env_sq(q, 700, 50, "lab-snare-body")
bm = q.add("#X obj 30 230 *~;")
nz = q.add("#X obj 30 280 noise~;"); wb = q.add("#X obj 30 310 ockm-lab-bp lab-snare-wires lab-snare-wwidth;")
wenv = env_sq(q, 700, 200, "lab-snare-wenv")
wm = q.add("#X obj 30 350 *~;")
ch = q.add("#X obj 300 310 hip~ 3000;"); cenv = env_sq(q, 700, 350, "lab-snare-cenv"); cm = q.add("#X obj 300 350 *~;")
rck = q.add("#X obj 450 330 r lab-snare-click;"); cg = q.add("#X obj 300 380 *~ 0.4;")
rmx = q.add("#X obj 500 200 r lab-snare-mix;"); tmx = q.add("#X obj 500 225 t f f;"); imx = q.add(f"#X obj 500 250 expr (1-{D}f1)*0.5;")
bg = q.add("#X obj 30 260 *~ 0.25;"); wg = q.add("#X obj 30 380 *~ 0.55;")
s1 = q.add("#X obj 30 420 +~;"); s2 = q.add("#X obj 30 450 +~;")
for c in [(rfq, 0, vf, 0), (vf, 0, o1, 0), (vf, 0, mr, 0), (rrt, 0, mr, 1), (mr, 0, o2, 0), (o2, 0, g2, 0), (o1, 0, bs, 0), (g2, 0, bs, 1),
          (bs, 0, bm, 0), (benv, 0, bm, 1), (bm, 0, bg, 0), (nz, 0, wb, 0), (wb, 0, wm, 0), (wenv, 0, wm, 1), (wm, 0, wg, 0),
          (nz, 0, ch, 0), (ch, 0, cm, 0), (cenv, 0, cm, 1), (cm, 0, cg, 0), (rck, 0, cg, 1),
          (rmx, 0, tmx, 0), (tmx, 1, wg, 1), (tmx, 0, imx, 0), (imx, 0, bg, 1),
          (bg, 0, s1, 0), (wg, 0, s1, 1), (s1, 0, s2, 0), (cg, 0, s2, 1)]: q.con(*c)
drive_out(q, 30, 490, s2, "snare", MK_SNARE)
q.save("lab/ockm-lab-snare.pd", "#N canvas 200 200 900 640 12;")

# ---- the brain: burst timing, envelopes, randomise, loop against a kick, render to WAV (Lua)
def lua_params(lst): return "{ " + ", ".join(f'{{ "{n}", {lo}, {hi}, {st} }}' for n, lo, hi, st, _ in lst) + " }"
open(os.path.join(R, "lab", "ockm-lab.pd_lua"), "w").write('''-- OCKM Drum Lab brain: plays the clap and snare (their envelopes), randomises around the sound you have,
-- loops them against a kick, and renders a hit to a WAV in samples/clap or samples/snare.
-- Written by tools/build_lab.py: change it there.
local lab = pd.Class:new():register("ockm-lab")
local PARAMS = { clap = ''' + lua_params(LAB_CLAP) + ''', snare = ''' + lua_params(LAB_SNARE) + ''' }

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
''')

# ---- the lab patch: two columns of controls, the sounds, a kick for the loop, the recorder
q = P()
q.raw("#X declare -path lab -path voices;")
q.add("#X text 20 10 OCKM DRUM LAB: design claps and snares \\, then render them into samples/clap and samples/snare for OCKM (or the SP-404). Click to play \\, drag the sliders \\, randomise around what you have.;")
brain = q.add("#X obj 820 60 ockm-lab;")
clap = q.add("#X obj 820 120 ockm-lab-clap;"); snare = q.add("#X obj 980 120 ockm-lab-snare;")
rk = q.add("#X obj 1140 90 r lab-kick;"); kick = q.add("#X obj 1140 120 ockm-kick labkick;")
mixs = q.add("#X obj 820 170 +~;"); allm = q.add("#X obj 820 200 +~;"); vol = q.add("#X obj 820 230 *~ 0.8;"); dac = q.add("#X obj 820 260 dac~;")
rec = q.add("#X obj 1000 200 writesf~ 1;"); rrec = q.add("#X obj 1000 170 r lab-rec;")
kg = q.add("#X obj 1140 150 *~ 0.7;")
lbd = q.add("#X obj 1140 200 loadbang;"); dsp = q.add("#X msg 1140 225 \\; pd dsp 1;")
for c in [(clap, 0, mixs, 0), (snare, 0, mixs, 1), (mixs, 0, allm, 0), (rk, 0, kick, 0), (kick, 0, kg, 0), (kg, 0, allm, 1), (allm, 0, vol, 0),
          (vol, 0, dac, 0), (vol, 0, dac, 1), (mixs, 0, rec, 0), (rrec, 0, rec, 0), (lbd, 0, dsp, 0)]: q.con(*c)
COL = "#fcfcfc #000000 #000000"
def column(x, which, title, params):
    q.add(f"#X text {x} 50 {title};")
    btn = lambda bx, by, send, label: q.add(f"#X obj {bx} {by} bng 30 250 50 0 {send} empty {label} 36 15 0 12 {COL};")
    btn(x, 80, f"lab-{which}-play", "play")
    q.add(f"#X obj {x+120} 80 tgl 30 0 lab-{which}-loop empty loop_with_kick 36 15 0 12 {COL} 0 1;")
    q.add(f"#X text {x} 128 randomise:;")
    for i, (k, lab_) in enumerate([("small", "small"), ("medium", "medium"), ("wild", "wild")]):
        btn(x + 100 + i * 90, 122, f"lab-{which}-rand-{k}", lab_)
    btn(x, 164, f"lab-{which}-render", "render_to_samples/" + which)
    btn(x + 260, 164, f"lab-{which}-reset", "reset")
    y = 230
    for name, lo, hi, st, label in params:
        w = 300
        val = int(round((st - lo) / (hi - lo) * (w - 1) * 100))
        q.add(f"#X obj {x} {y} hsl {w} 22 {lo} {hi} 0 1 lab-{which}-{name} lab-{which}-{name}-ui {label.replace(' ', '_')} 0 -10 0 12 {COL} {val} 1;")
        y += 46
column(20, "clap", "CLAP", LAB_CLAP)
column(420, "snare", "SNARE", LAB_SNARE)
q.add("#X text 20 840 last:;")
q.add("#X symbolatom 70 840 70 0 0 0 - lab-status -;")
q.save("OCKM_DRUM_LAB.pd", "#N canvas 40 40 1300 900 12;")
