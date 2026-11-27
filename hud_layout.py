"""Persisted, pure HUD layout geometry."""
from preferences import read_preferences,write_preference
WIDGETS={'ad':('Adena/hr','ADENA/H',(247,202,102)),'xp':('Experience/hr','EXP/H',(134,224,183)),'kills':('Kills/hr','KILLS/H',(214,224,245)),'eta':('Time to next level','NEXT LVL',(170,200,255)),'level':('Current level','LEVEL',(170,200,255)),'progress':('Experience percentage','EXP %',(170,200,255)),'loot':('Estimated loot value/hr','LOOT/H',(203,177,242)),'cost':('Consumable costs/hr','COST/H',(255,165,165))}
PRESETS={'Classic':['ad','xp','kills'],'Minimal':['ad','eta'],'Leveling':['xp','eta','level','progress'],'Farming':['ad','loot','cost','kills']}
SIZES={'compact':(91,48,11,17),'standard':(103,54,14,19),'large':(120,63,16,22)}
def clean(raw=None):
    r=raw if isinstance(raw,dict) else {}
    order=list(dict.fromkeys(i for i in r.get('order',[]) if isinstance(i,str) and i in WIDGETS)) if isinstance(r.get('order'),list) else []
    order+= [i for i in WIDGETS if i not in order]
    enabled=r.get('enabled',PRESETS['Classic'])
    enabled=[i for i in order if isinstance(enabled,list) and i in enabled]
    return dict(order=order,enabled=enabled,size=r.get('size') if r.get('size') in SIZES else 'compact',layout=r.get('layout') if r.get('layout') in ('single','double') else 'single',**{k:r[k] if type(r.get(k)) is bool else True for k in ('status','pause','reset','visible')})
def load(path=None):return clean(read_preferences(path).get('hud_layout'))
def save(value,path=None):write_preference('hud_layout',clean(value),path)

def geometry(config):
    c=clean(config);ids=c['enabled'];cell,rh,small,large=SIZES[c['size']]
    cols=max(1,(len(ids)+1)//2 if c['layout']=='double' else len(ids));rows=max(1,(len(ids)+cols-1)//cols)
    # Reserve lock space in the header and a separate footer for buttons.
    footer=c['status'] or c['pause'] or c['reset']
    width=max(cols*cell+24, (120 if c['status'] else 0)+(72 if c['pause'] else 0)+(60 if c['reset'] else 0)+12,115)
    height=rows*rh+8+(32 if footer else 0)
    cells=[(k,8+(i%cols)*cell,5+(i//cols)*rh,cell,rh) for i,k in enumerate(ids)]
    right=width-6
    reset=(right-54,height-26,right,height-4) if c['reset'] else None
    if reset:right-=60
    pause=(right-68,height-26,right,height-4) if c['pause'] else None
    return dict(width=width,height=height,small=small,large=large,cells=cells,lock=(width-22,0,width,24),reset=reset,pause=pause,status=c['status'],footer=footer)

def overlaps(a,b,w,h,r):
    return a<r['left']+r['width'] and a+w>r['left'] and b<r['top']+r['height'] and b+h>r['top']
