"""Independent native overlays sharing one passive session."""
from hud_layout import panel_config,main_config,clean
import time
from preferences import read_preferences

def load_position(key):
    p=read_preferences().get(key)
    return tuple(p) if isinstance(p,list) and len(p)==2 and all(type(v) is int and v>=0 for v in p) else None
def load_loot_position():return load_position('loot_hud_position')
def load_main_position():return load_position('main_hud_position')
def local_rect(hud,geo):
    if not hud.shown or not hud.position or not geo:return ()
    w,h=hud.dimensions()
    return (dict(left=hud.position[0]-geo[0],top=hud.position[1]-geo[1],width=w,height=h),)
class HudPair:
    def __init__(self,primary,loot,main=None):
        self.primary=primary;self.loot=loot;self.main=main;self.config=None;self.details=[];self.title='ADENA / LOOT';self.next_detail_paint=0
    @property
    def preferred(self):return self.primary.preferred
    @preferred.setter
    def preferred(self,value):self.primary.preferred=value
    @property
    def placement(self):return self.primary.placement
    def dimensions(self):return self.primary.dimensions()
    def arm_placement(self):self.primary.arm_placement()
    def panels(self):return tuple(h for h in (self.main,self.primary,self.loot) if h is not None)
    def cancel_placement(self):
        for h in self.panels():h.cancel_placement()
    def hide(self):
        for h in self.panels():h.hide()
    def close(self):
        try:self.primary.close()
        finally:
            try:self.loot.close()
            finally:
                if self.main:self.main.close()
    def set_opacity(self,value):
        for h in self.panels():h.set_opacity(value)
    def configure_layout(self,config):
        self.config=clean(config)
        self.primary.configure_layout(panel_config(self.config,'progression'),'XP / SP')
        self.loot.configure_layout(panel_config(self.config,'loot'),self.title,len(self.details))
        if self.main:
            self.main.configure_layout(main_config(self.config),'MAIN HUD')
            self.main.set_panel_visibility(dict(progression=self.config['show_xp'],loot=self.config['show_loot']))
    def set_targets(self,monster,rows):
        title='ADENA / LOOT'+(' • '+monster if monster and rows else '')
        if rows==self.details and title==self.title:return
        geometry_changed=len(rows)!=len(self.details) or title!=self.title
        names_changed=[r[0] for r in rows]!=[r[0] for r in self.details]
        now=time.monotonic()
        if not (geometry_changed or names_changed) and now<self.next_detail_paint:return
        self.next_detail_paint=now+1
        self.details=list(rows);self.title=title;self.loot.detail_rows=self.details
        if geometry_changed and self.config is not None:self.loot.configure_layout(panel_config(self.config,'loot'),title,len(rows))
        if self.loot.hwnd:self.loot.u.InvalidateRect(self.loot.hwnd,None,False)
    def update(self,api,target,chat,running,*args,protected=(),**kwargs):
        geo=api.geometry(target.hwnd) if running and target else None
        # Hide disabled panels first, so stale rectangles never block placement.
        active={self.primary:running and self.config['show_xp'],self.loot:running and self.config['show_loot']}
        if self.main:active[self.main]=running
        for h in self.panels():
            if not active[h]:h.hide()
        # Main controls get first placement priority. Each later panel protects
        # the rectangles already placed (and existing visible peer positions).
        for h in self.panels():
            if active[h]:
                others=tuple(r for other in self.panels() if other is not h for r in local_rect(other,geo))
                h.update(api,target,chat,True,*args,protected=(*protected,*others),**kwargs)
