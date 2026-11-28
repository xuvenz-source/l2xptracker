"""Independent colour-keyed, click-through resource globe using the native HUD."""
import ctypes as c
from ctypes import wintypes as w
from hud import Hud
from preferences import validate_hud_opacity
from vital_globes import globe_rectangles

TRANSPARENT=(255,0,255)

class GlobeHud(Hud):
    standalone_globe=True
    def set_opacity(self,percent):
        percent=validate_hud_opacity(percent)
        # LWA_COLORKEY | LWA_ALPHA: only the globe is visible.
        if self.hwnd and not self.u.SetLayeredWindowAttributes(self.hwnd,self.rgb(*TRANSPARENT),round(255*percent/100),3):
            raise RuntimeError('Could not set globe transparency')
        self.opacity=percent
    def wants_input(self,point):
        # Placement uses the existing pointer + Shift workflow; no interception.
        return False
    def handle_press(self,point):
        return
    def paint_layout(self,dc):
        g=self.layout;kind=g['cells'][0][0];d=g['orb_diameter']
        values=getattr(self,'widget_values',{})
        _,value=values.get(kind,(kind.upper(),'—'))
        brushes={}
        def fill(rect,col):
            if col not in brushes:brushes[col]=self.g.CreateSolidBrush(self.rgb(*col))
            if brushes[col]:self.u.FillRect(dc,c.byref(w.RECT(*rect)),brushes[col])
        try:
            fill((0,0,d,d),TRANSPARENT)
            for l,t,r,b,col in globe_rectangles(kind,d,values.get(kind+'_fill')):
                fill((l,t,r,b),col)
            self.g.SetBkMode(dc,1)
            lines=value.split(' - ',1)
            h=max(15,d//6);top=(d-h*len(lines))//2
            for i,line in enumerate(lines):
                y=top+i*h;rect=(d//9,y,d-d//9,y+h)
                # A simple black shadow preserves contrast on the coloured fill.
                self.fitted_text(dc,line,(rect[0]+1,y+1,rect[2]+1,y+h+1),self.large,(8,8,12),g['large'],600,center=True)
                self.fitted_text(dc,line,rect,self.large,(248,245,239),g['large'],600,center=True)
        finally:
            for brush in brushes.values():
                if brush:self.g.DeleteObject(brush)
