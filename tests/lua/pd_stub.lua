-- Just enough of pdlua's `pd` to load a generator object outside Pure Data, so its pure functions can be tested.
-- Usage: dofile("tests/lua/pd_stub.lua"); local cls = load_pd_lua("seq/ockm-chordmaker.pd_lua")
pd = { sent = {} }
local Class = {}
Class.__index = Class
function Class:new() return setmetatable({}, Class) end
function Class:register(name) self._name = name; pd.last_class = self; return self end
pd.Class = Class
pd.Receive = { new = function() return { register = function() return {} end, destruct = function() end } end }
pd.Clock = { new = function() return { register = function() return { delay = function() end, destruct = function() end } end } end }
pd.Table = { new = function() return { sync = function() return nil end } end }
function pd.send(name, sel, atoms) pd.sent[#pd.sent + 1] = { name, sel, atoms } end
function pd.post(...) print(...) end
function load_pd_lua(path)
  pd.last_class = nil
  dofile(path)
  return pd.last_class
end
