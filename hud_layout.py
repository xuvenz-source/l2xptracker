"""Persisted, pure HUD layout geometry."""
from preferences import read_preferences,write_preference
WIDGETS={'ad':('Adena/hr','ADENA/H',(228,193,139)),'xp':('Experience/hr','EXP/H',(155,223,192)),'kills':('Kills/hr','KILLS/H',(214,224,245)),'eta':('Time to next level','NEXT LVL',(177,193,239)),'level':('Current level','LEVEL',(177,193,239)),'progress':('Experience percentage','EXP %',(177,193,239)),'loot':('Estimated loot value/hr','LOOT/H',(194,169,228)),'cost':('Consumable costs/hr','COST/H',(255,165,165)),'sp':('Session SP gained','SP GAINED',(177,193,239)),'spnext':('Estimated SP at next level','SP NEXT',(177,193,239)),'killsnext':('Kills until next level','KILLS LEFT',(177,193,239))}
PRESETS={'Classic':['ad','xp','kills'],'Minimal':['ad','eta'],'Leveling':['xp','eta','level','progress','killsnext'],'Farming':['ad','loot','cost','kills']}
SIZES={'compact':(91,48,11,17),'standard':(103,54,14,19),'large':(120,63,16,22)}
ROW_OPTIONS=('Auto (one row)','Auto (two rows)',*tuple(str(i) for i in range(1,len(WIDGETS)+1)))

def row_choice(config):
    n=config.get('widgets_per_row')
    return str(n) if type(n) is int and 1<=n<=len(WIDGETS) else ROW_OPTIONS[1 if config.get('layout')=='double' else 0]

def row_settings(choice):
    if choice in ROW_OPTIONS[2:]:return dict(layout='single',widgets_per_row=int(choice))
    return dict(layout='double' if choice==ROW_OPTIONS[1] else 'single',widgets_per_row=None)

def clean(raw=None):
    r=raw if isinstance(raw,dict) else {}
    order=list(dict.fromkeys(i for i in r.get('order',[]) if isinstance(i,str) and i in WIDGETS)) if isinstance(r.get('order'),list) else []
    order+= [i for i in WIDGETS if i not in order]
    enabled=r.get('enabled',PRESETS['Classic'])
    enabled=[i for i in order if isinstance(enabled,list) and i in enabled]
    n=r.get('widgets_per_row')
    n=n if type(n) is int and 1<=n<=len(WIDGETS) else None
    overrides=r.get('panel_rows',{})
    overrides={k:v for k,v in overrides.items() if k in ('progression','loot') and v in ROW_OPTIONS} if isinstance(overrides,dict) else {}
    return dict(panel_rows=overrides,show_xp=r.get('show_xp') if type(r.get('show_xp')) is bool else True,show_loot=r.get('show_loot') if type(r.get('show_loot')) is bool else True,order=order,enabled=enabled,widgets_per_row=n,size=r.get('size') if r.get('size') in SIZES else 'compact',layout=r.get('layout') if r.get('layout') in ('single','double') else 'single',**{k:r[k] if type(r.get(k)) is bool else True for k in ('status','pause','reset','visible')})
def load(path=None):return clean(read_preferences(path).get('hud_layout'))
def save(value,path=None):write_preference('hud_layout',clean(value),path)

PROGRESSION=('xp','kills','eta','level','progress','sp','spnext','killsnext')
LOOT=('ad','loot','cost')

def panel_config(config,kind):
    c=clean(config);keys=PROGRESSION if kind=='progression' else LOOT
    c['enabled']=[k for k in c['enabled'] if k in keys]
    if kind in c['panel_rows']:c.update(row_settings(c['panel_rows'][kind]))
    c.update(status=False,pause=False,reset=False)
    return c

def main_config(config):
    c=clean(config);c['enabled']=[];c['status']=False;return c

def geometry(config,title=None,details=0,select_loot=False,main_controls=False):
    c=clean(config);ids=c['enabled'];cell,rh,small,large=SIZES[c['size']]
    if main_controls:
        # Single control strip: no title, status or visibility buttons.
        # Keep the lock and gear accessible even if Pause/Reset are disabled.
        x=6
        pause=(x,3,x+68,25) if c['pause'] else None
        if pause:x+=72
        reset=(x,3,x+54,25) if c['reset'] else None
        if reset:x+=60
        width=max(64,x+48)
        return dict(toggles={},width=width,height=28,small=small,large=large,cells=[],title=None,detail_y=28,details=0,select_loot=None,lock=(width-44,0,width-22,28),settings=(width-22,0,width,28),reset=reset,pause=pause,status=False,footer=bool(pause or reset),toolbar=0)
    limit=c['widgets_per_row']
    cols=max(1,min(len(ids),limit) if limit is not None else (len(ids)+1)//2 if c['layout']=='double' else len(ids));rows=max(1,(len(ids)+cols-1)//cols)
    # Titled tracker panels have a dedicated toolbar above the widget grid.
    # Preserve the legacy untitled layout for callers that use it.
    footer=c['status'] or c['pause'] or c['reset']
    width=max(cols*cell+(16 if title else 56), (120 if c['status'] else 0)+(72 if c['pause'] else 0)+(60 if c['reset'] else 0)+12,115)
    header=24 if title else 0
    width=max(width,300 if details else 115,180 if select_loot else 0)
    content_height=header+(rows*rh if ids or not title and not select_loot else 0)+8
    action_y=content_height+details*21
    action=(8,action_y+3,width-8,action_y+26) if select_loot else None
    toggles={}
    height=action_y+(30 if select_loot else 0)+(32 if footer else 0)
    cells=[(k,8+(i%cols)*cell,header+5+(i//cols)*rh,cell,rh) for i,k in enumerate(ids)]
    right=width-6
    reset=(right-54,height-26,right,height-4) if c['reset'] else None
    if reset:right-=60
    pause=(right-68,height-26,right,height-4) if c['pause'] else None
    return dict(toggles=toggles,width=width,height=height,small=small,large=large,cells=cells,title=title,detail_y=content_height,details=details,select_loot=action,lock=(width-44,0,width-22,24),settings=(width-22,0,width,24),reset=reset,pause=pause,status=c['status'],footer=footer,toolbar=header)

def overlaps(a,b,w,h,r):
    return a<r['left']+r['width'] and a+w>r['left'] and b<r['top']+r['height'] and b+h>r['top']
