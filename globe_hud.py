"""Independent, per-pixel-alpha, click-through resource globe."""
from hud import Hud
from preferences import validate_hud_opacity
from ornate_globe import render_globe
from vital_globes import fill_steps
from layered_globe import setup,present

class GlobeHud(Hud):
    standalone_globe=True
    def __init__(self,*args,**kwargs):
        self.surface_key=None
        super().__init__(*args,**kwargs)
        try:setup(self.u,self.g)
        except Exception:self.close();raise
    def set_opacity(self,percent):
        # UpdateLayeredWindow owns alpha. Calling SetLayeredWindowAttributes
        # on this HWND would prevent subsequent per-pixel-alpha updates.
        self.opacity=validate_hud_opacity(percent)
    def wants_input(self,point):return False
    def handle_press(self,point):return
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
        key=(kind,d,fill_steps(fraction),value,self.opacity)
        if key==self.surface_key:return
        image=render_globe(kind,d,fraction,value)
        present(self.u,self.g,self.hwnd,image,self.opacity)
        self.surface_key=key
