"""Independent, per-pixel-alpha, click-through resource globe."""
from hud import Hud
from preferences import validate_hud_opacity
from ornate_globe import render_globe,with_move_bar,MOVE_BAR_HEIGHT
from vital_globes import fill_steps
from layered_globe import setup,present

class GlobeHud(Hud):
    standalone_globe=True
    def __init__(self,*args,**kwargs):
        self.surface_key=None;self.editing=False;self.saved_preferred=None
        super().__init__(*args,**kwargs)
        try:setup(self.u,self.g)
        except Exception:self.close();raise
    def set_opacity(self,percent):
        # UpdateLayeredWindow owns alpha. Calling SetLayeredWindowAttributes
        # on this HWND would prevent subsequent per-pixel-alpha updates.
        self.opacity=validate_hud_opacity(percent)
    def dimensions(self):
        w,h=super().dimensions()
        return w,h+(MOVE_BAR_HEIGHT if getattr(self,'editing',False) else 0)
    def begin_move(self):
        if self.editing:return
        self.saved_preferred=self.preferred
        # Preferences store the globe origin, not the temporary toolbar.
        # Start at the actual visible position, even after safe-placement fallback.
        origin=self.preferred
        if self.shown and self.position and self.drag_context:
            geo=self.drag_context[0]
            origin=(self.position[0]-geo[0],self.position[1]-geo[1])
        self.preferred=(origin[0],max(0,origin[1]-MOVE_BAR_HEIGHT)) if origin is not None else None
        self.editing=True;self.locked=False;self.surface_key=None
    def finish_drag(self):
        # Drag release updates the draft. Only the lock commits it.
        callback=self.on_move
        if getattr(self,'editing',False):self.on_move=None
        try:super().finish_drag()
        finally:self.on_move=callback
    def end_move(self,save=True):
        if not getattr(self,'editing',False):return
        self.finish_drag()
        if save:
            origin=self.preferred
            if self.shown and self.position and self.drag_context:
                geo=self.drag_context[0]
                origin=(self.position[0]-geo[0],self.position[1]-geo[1])
            self.preferred=(origin[0],origin[1]+MOVE_BAR_HEIGHT) if origin is not None else self.saved_preferred
        else:self.preferred=self.saved_preferred
        self.editing=False;self.locked=True;self.surface_key=None
        self.saved_preferred=None
        self.set_interactive(False)
        if save and self.preferred is not None and self.on_move:self.on_move(self.preferred)
    def cancel_placement(self):
        super().cancel_placement()
        self.end_move(save=False)
    def lock_hit(self,point):
        if not getattr(self,'editing',False):return False
        w,_=self.dimensions()
        return self.hit_rect(point,(w-26,0,w,MOVE_BAR_HEIGHT))
    def body_hit(self,point):
        if not getattr(self,'editing',False):return False
        w,_=self.dimensions()
        return self.hit_rect(point,(0,0,w-26,MOVE_BAR_HEIGHT))
    def wants_input(self,point):
        return bool(getattr(self,'editing',False) and (self.drag is not None or self.lock_hit(point) or self.body_hit(point)))
    def handle_press(self,point):
        if not getattr(self,'editing',False) or self.press_handled:return
        self.press_handled=True
        if self.lock_hit(point):self.end_move()
        elif self.body_hit(point):self.begin_drag(point)
    def paint_buffered(self,dc):
        # WM_PAINT is acknowledged by the parent; ULW supplies the pixels.
        return
    def update(self,*args,**kwargs):
        super().update(*args,**kwargs)
        if self.shown and self.hwnd:self.present_surface()
    def present_surface(self):
        g=self.layout;kind=g['cells'][0][0];d=g['orb_diameter']
        values=getattr(self,'widget_values',{})
        _,value=values.get(kind,(kind.upper(),'—'))
        fraction=values.get(kind+'_fill')
        editing=getattr(self,'editing',False)
        key=(kind,d,fill_steps(fraction),value,self.opacity,editing)
        if key==self.surface_key:return
        image=render_globe(kind,d,fraction,value)
        if editing:image=with_move_bar(image,kind)
        present(self.u,self.g,self.hwnd,image,self.opacity)
        self.surface_key=key
