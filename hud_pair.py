"""Independent native overlays sharing one passive session."""
from hud_layout import panel_config
import time
from preferences import read_preferences

def load_loot_position():
    p=read_preferences().get('loot_hud_position')
    return tuple(p) if isinstance(p,list) and len(p)==2 and all(type(v) is int and v>=0 for v in p) else None
def local_rect(hud,geo):
    if not hud.shown or not hud.position or not geo:return ()
    w,h=hud.dimensions()
    return (dict(left=hud.position[0]-geo[0],top=hud.position[1]-geo[1],width=w,height=h),)
class HudPair:
    def __init__(self,primary,loot):
        self.primary=primary;self.loot=loot;self.config=None;self.details=[];self.title='ADENA / LOOT';self.next_detail_paint=0
    @property
    def preferred(self):return self.primary.preferred
    @preferred.setter
    def preferred(self,value):self.primary.preferred=value
    @property
    def placement(self):return self.primary.placement
    def dimensions(self):return self.primary.dimensions()
    def arm_placement(self):self.primary.arm_placement()
    def cancel_placement(self):self.primary.cancel_placement();self.loot.cancel_placement()
    def hide(self):self.primary.hide();self.loot.hide()
    def close(self):
        try:self.primary.close()
        finally:self.loot.close()
    def set_opacity(self,value):self.primary.set_opacity(value);self.loot.set_opacity(value)
    def configure_layout(self,config):
        self.config=config
        self.primary.configure_layout(panel_config(config,'progression'),'XP / SP')
        self.loot.configure_layout(panel_config(config,'loot'),self.title,len(self.details))
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
        p=panel_config(self.config,'progression');l=panel_config(self.config,'loot')
        self.primary.update(api,target,chat,running and bool(p['enabled']),*args,protected=(*protected,*local_rect(self.loot,geo)),**kwargs)
        self.loot.update(api,target,chat,running,*args,protected=(*protected,*local_rect(self.primary,geo)),**kwargs)
