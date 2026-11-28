"""Persisted, pure HUD layout geometry."""
from preferences import read_preferences,write_preference
WIDGETS={'ad':('Adena/hr','ADENA/H',(247,202,102)),'xp':('Experience/hr','EXP/H',(134,224,183)),'kills':('Kills/hr','KILLS/H',(214,224,245)),'eta':('Time to next level','NEXT LVL',(170,200,255)),'level':('Current level','LEVEL',(170,200,255)),'progress':('Experience percentage','EXP %',(170,200,255)),'loot':('Estimated loot value/hr','LOOT/H',(203,177,242)),'cost':('Consumable costs/hr','COST/H',(255,165,165)),'sp':('Session SP gained','SP GAINED',(170,200,255)),'spnext':('Estimated SP at next level','SP NEXT',(170,200,255))}
PRESETS={'Classic':['ad','xp','kills'],'Minimal':['ad','eta'],'Leveling':['xp','eta','level','progress'],'Farming':['ad','loot','cost','kills']}
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
    return dict(order=order,enabled=enabled,widgets_per_row=n,size=r.get('size') if r.get('size') in SIZES else 'compact',layout=r.get('layout') if r.get('layout') in ('single','double') else 'single',**{k:r[k] if type(r.get(k)) is bool else True for k in ('status','pause','reset','visible')})
def load(path=None):return clean(read_preferences(path).get('hud_layout'))
def save(value,path=None):write_preference('hud_layout',clean(value),path)

PROGRESSION=('xp','kills','eta','level','progress','sp','spnext')
LOOT=('ad','loot','cost')

def panel_config(config,kind):
    c=clean(config);keys=PROGRESSION if kind=='progression' else LOOT
    c['enabled']=[k for k in c['enabled'] if k in keys]
    return c

def geometry(config,title=None,details=0):
    c=clean(config);ids=c['enabled'];cell,rh,small,large=SIZES[c['size']]
    limit=c['widgets_per_row']
    cols=max(1,min(len(ids),limit) if limit is not None else (len(ids)+1)//2 if c['layout']=='double' else len(ids));rows=max(1,(len(ids)+cols-1)//cols)
    # Reserve adjacent lock and gear hit targets, plus a separate footer.
    footer=c['status'] or c['pause'] or c['reset']
    width=max(cols*cell+56, (120 if c['status'] else 0)+(72 if c['pause'] else 0)+(60 if c['reset'] else 0)+12,115)
    header=22 if title else 0
    width=max(width,300 if details else 115)
    height=header+rows*rh+8+details*21+(32 if footer else 0)
    cells=[(k,8+(i%cols)*cell,header+5+(i//cols)*rh,cell,rh) for i,k in enumerate(ids)]
    right=width-6
    reset=(right-54,height-26,right,height-4) if c['reset'] else None
    if reset:right-=60
    pause=(right-68,height-26,right,height-4) if c['pause'] else None
    return dict(width=width,height=height,small=small,large=large,cells=cells,title=title,detail_y=header+rows*rh+8,details=details,lock=(width-44,0,width-22,24),settings=(width-22,0,width,24),reset=reset,pause=pause,status=c['status'],footer=footer)

def overlaps(a,b,w,h,r):
    return a<r['left']+r['width'] and a+w>r['left'] and b<r['top']+r['height'] and b+h>r['top']
