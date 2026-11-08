-- Appended to the shared UI in the Mac build only. Musical and project behaviour
-- stays in ui/ockm-ui.pd_lua; this adapter replaces drawing and mouse transport.
;(function(cls)
  local function emit(kind, values) pd.send("ockm-native-draw", kind, values or {}) end
  local G = {}
  function G:set_color(r,g,b) emit("color", {r,g,b}) end
  function G:fill_all() emit("background") end
  function G:scale(x,y) emit("scale", {x,y}) end
  function G:fill_rect(x,y,w,h) emit("rect", {x,y,w,h}) end
  function G:fill_rounded_rect(x,y,w,h,r) emit("round", {x,y,w,h,r}) end
  function G:stroke_rounded_rect(x,y,w,h,r,t) emit("outline", {x,y,w,h,r,t}) end
  function G:fill_ellipse(x,y,w,h) emit("ellipse", {x,y,w,h}) end
  function G:draw_text(s,x,y,w,size) emit("text", {x,y,w,size,tostring(s)}) end
  function G:fill_path(p) emit("path", p.points) end
  Path = function(x,y)
    local p = {points={x,y}}
    function p:line_to(a,b) self.points[#self.points+1]=a; self.points[#self.points+1]=b end
    function p:close() end
    return p
  end
  function cls:set_size() end
  function cls:repaint() self.native_dirty = true end
  local start = cls.postinitialize
  function cls:postinitialize()
    start(self)
    self.recv[#self.recv+1] = pd.Receive:new():register(self,"ockm-native","native_command")
    self.native_dirty = true
  end
  function cls:native_command(sel,a)
    if sel == "frame" then
      if not self.native_dirty then return end
      self.native_dirty = false
      emit("begin")
      self:paint(G)
      self:paint_layer_2(G)
      emit("state", {self.playing or 0,self.v["ockm-bpm"] or 124,self.unsaved and 1 or 0,self.project or "default",self.screen,self.pad_on or "",self.macro and self.macro.slot or 0})
      emit("end")
      return
    elseif sel == "press" then self:press(a[1],a[2])
    elseif sel == "move" then self:move(a[1],a[2])
    elseif sel == "release" then self:release(a[1],a[2])
    elseif sel == "play" then self:send("ockm-play",self.playing == 0 and 1 or 0)
    elseif sel == "save" then self:save_variation()
    elseif sel == "keep" then pd.send("ockm-keep","bang",{})
    elseif sel == "style" then self:apply_style(a[1], a[2] == 1)
    elseif sel == "screen" then
      local parts={bass=1,lead=2,chord=3}
      if parts[a[1]] then self.part=parts[a[1]];self:open("synth") else self:open(a[1]) end
    elseif sel == "undo" then self:undo()
    elseif sel == "export-sheet" then
      pd.send("ockm-usb-scan","bang",{});pd.send("ockm-exports-ask","bang",{});self.sheet="export"
    elseif sel == "key-down" or sel == "key-up" then
      local key,down=a[1],sel=="key-down"
      local macros={z=1,x=2,c=3,v=4,n=5,m=6}
      if key=="d" or key=="b" then self:pad_action(key=="d" and 13 or 14,down)
      elseif macros[key] then if down then self:macro_down(macros[key]) else self:macro_up(macros[key]) end
      elseif down then
        if key==" " then self:send("ockm-play",self.playing==0 and 1 or 0)
        elseif key=="r" then self:send("ockm-rise",(self.v["ockm-rise"] or 0)>0 and 0 or 1)
        elseif key=="w" then self:pad_action(12,true)
        elseif key=="escape" then
          if self.sheet then self.sheet=nil
          else self:macro_finish();self:send("ockm-rise",0);self:pad_action(13,false);self:pad_action(14,false) end
        else
          local n=tonumber(key)
          if key=="0" then n=10 elseif key=="-" then n=11 elseif key=="=" then n=12 end
          local track=n and TRACKS[n]
          if track and self:track_in(track) then self:qmute(track,self:mute_target(track)>0 and 0 or 1) end
        end
      end
      self:dirty()
    elseif sel == "cancel-touch" then
      if self.touch then self:release(-100,-100) end
    end
    self.native_dirty = true
  end
end)(ui)
