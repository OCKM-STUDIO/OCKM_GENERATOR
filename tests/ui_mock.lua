-- Runs ui/ockm-ui.pd_lua outside Pure Data, with a stand-in for the pd module.
-- Used by tests/ui_preview.py to draw the screens to PNG and to check gestures.
-- Usage: lua ui_mock.lua <ui file> <script file> <out file>
-- The script is lines of: send <name> <sel> <atoms...> | test <sel> <atoms...> | paint <label>
local uifile, script, outfile = arg[1], arg[2], arg[3]
local out = assert(io.open(outfile, "w"))
local function emit(s) out:write(s, "\n") end

local arrays, receivers = {}, {}
local function arr(name, n) if not arrays[name] then arrays[name] = {}; for i = 0, (n or 128) - 1 do arrays[name][i] = 0 end end return arrays[name] end

pd = {}
function pd.post(s) emit("post " .. s) end
local Class = {}
Class.__index = Class
pd.Class = {}
function pd.Class:new() return setmetatable({}, { __index = Class }) end
function Class:register(name) self._name = name; pd._cls = self; return self end
function Class:set_size(w, h) self._w, self._h = w, h end
function Class:repaint(layer) self._wants = true end
function Class:error(m) emit("error " .. m) end

pd.Receive = {}
function pd.Receive:new() return setmetatable({}, { __index = pd.Receive }) end
function pd.Receive:register(obj, name, method)
  self.obj, self.name, self.method = obj, name, method
  receivers[name] = receivers[name] or {}
  table.insert(receivers[name], self)
  return self
end
function pd.Receive:destruct() end

pd.Clock = {}
function pd.Clock:new() return setmetatable({}, { __index = pd.Clock }) end
function pd.Clock:register(obj, method) self.obj, self.method = obj, method; return self end
function pd.Clock:delay(ms) self.armed = true end
function pd.Clock:unset() self.armed = false end
function pd.Clock:destruct() end

pd.Table = {}
function pd.Table:new() return setmetatable({}, { __index = pd.Table }) end
function pd.Table:sync(name) if arrays[name] then self.a = arrays[name]; return self end return nil end
function pd.Table:get(i) return self.a[i] end
function pd.Table:length() return 128 end

-- a tiny engine: enough for edits to land in the tables
local function engine(name, sel, atoms)
  if name == "ockm-edit" then arr("ockm-pat-" .. sel)[atoms[1]] = atoms[2] end
  local part = name:match("^ockm%-(%a+)%-edit$")
  if part == "bass" or part == "lead" then
    local f = { "note", "on", "acc", "slide" }
    for k = 1, 4 do arr("ockm-pat-" .. part .. "-" .. f[k])[atoms[1]] = atoms[k + 1] end
  elseif part == "chord" then
    arr("ockm-pat-chord-on")[atoms[1]] = atoms[2]; arr("ockm-pat-chord-deg")[atoms[1]] = atoms[3]
  end
  if name == "ockm-length" then pd.send("ockm-len", "float", { atoms[1] }) end
  if name == "ockm-play" then pd.send("ockm-playing", "float", { atoms[1] }) end
  -- projects: a pretend projects folder
  if name == "ockm-project-list" then
    projects = projects or { "default", "2026-10-02-amber-heron", "2026-10-09-neon-otter", "2026-10-12-dusty-lantern" }
    pd.send("ockm-project-list-start", "bang", {})
    for _, p in ipairs(projects) do pd.send("ockm-project-item", "symbol", { p }) end
    pd.send("ockm-project-list-end", "bang", {})
  end
  if name == "ockm-project-new" or name == "ockm-project-saveas" then
    projects = projects or { "default" }; projects[#projects + 1] = atoms[1]; pd.send("ockm-project-name", "symbol", { atoms[1] })
  end
  if name == "ockm-song-list" then pd.send("ockm-song-show", sel == "bang" and "bang" or "list", atoms) end
  if name == "ockm-samples-scan" then pd.send("ockm-sample-counts", "list", { 20, 20, 21, 19, 20, 20, 17 }) end
  if name == "ockm-project-open" then pd.send("ockm-project-name", "symbol", { atoms[1] }) end
end

function pd.send(name, sel, atoms)
  local a = {}
  for _, x in ipairs(atoms or {}) do a[#a + 1] = tostring(x) end
  emit("sent " .. name .. " " .. sel .. " " .. table.concat(a, " "))
  engine(name, sel, atoms or {})
  -- Pd only has floats: hand numbers on as floats, like plugdata does
  local fa = {}
  for k, x in ipairs(atoms or {}) do fa[k] = (type(x) == "number") and (x + 0.0) or x end
  for _, r in ipairs(receivers[name] or {}) do r.obj[r.method](r.obj, sel, fa) end
end

-- drawing: record every call
local G = {}
G.__index = G
function G:set_color(r, g, b) emit(string.format("color %d %d %d", r, g, b)) end
function G:fill_all() emit("fill_all") end
function G:scale(x, y) emit("scale " .. x) end
function G:fill_rect(x, y, w, h) emit(string.format("rect %g %g %g %g", x, y, w, h)) end
function G:fill_rounded_rect(x, y, w, h, r) emit(string.format("rrect %g %g %g %g %g", x, y, w, h, r)) end
function G:stroke_rounded_rect(x, y, w, h, r, t) emit(string.format("srrect %g %g %g %g %g %g", x, y, w, h, r, t)) end
function G:fill_ellipse(x, y, w, h) emit(string.format("ellipse %g %g %g %g", x, y, w, h)) end
function G:draw_text(s, x, y, w, size) emit(string.format("text %g %g %g %s", x, y, size, s)) end
function G:fill_path(p) emit("path " .. table.concat(p.pts, " ")) end
function Path(x, y)
  local p = { pts = { x, y } }
  function p:line_to(a, b) table.insert(self.pts, a); table.insert(self.pts, b) end
  function p:close() end
  return p
end

dofile(uifile)
local cls = pd._cls
local obj = setmetatable({}, { __index = cls })
local args = {}
for w in (os.getenv("UI_ARGS") or "1 dark"):gmatch("%S+") do args[#args + 1] = tonumber(w) or w end
assert(obj:initialize("ockm-ui", args))
obj:postinitialize()

local function flush() if obj.clock and obj.clock.armed then obj.clock.armed = false; obj[obj.clock.method](obj) end end

for line in io.lines(script) do
  local t = {}
  for w in line:gmatch("%S+") do t[#t + 1] = tonumber(w) or w end
  if t[1] == "send" then
    local atoms = {}
    for k = 4, #t do atoms[#atoms + 1] = t[k] end
    pd.send(t[2], t[3], atoms)
  elseif t[1] == "array" then
    local a = arr(t[2])
    for k = 3, #t do a[k - 3] = t[k] end
  elseif t[1] == "test" then
    local atoms = {}
    for k = 3, #t do atoms[#atoms + 1] = t[k] end
    obj:test(t[2], atoms)
  elseif t[1] == "paint" then
    flush()
    emit("begin " .. t[2])
    obj:paint(setmetatable({}, G))
    if obj.paint_layer_2 then obj:paint_layer_2(setmetatable({}, G)) end
    emit("end " .. t[2])
  end
  flush()
end
out:close()
