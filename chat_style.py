"""User-selected chat palette and row pitch; passive pixel matching only."""
import re
import numpy as np
from preferences import read_preferences, write_preference

TEXT_SIZES={'Small':16,'Medium':17,'Large':19}
DEFAULT_COLOURS={'xp':'#B09B79','adena':'#FFFF00','item':'#FFFF00','consumable':'#B09B79','other':'#B09B79'}
CUSTOM_COLOURS={'xp':'#FF00FF','adena':'#FFFF00','item':'#00FF00','consumable':'#00AAFF','other':'#B09B79'}
LABELS={'xp':'XP / SP','adena':'Adena','item':'Items','consumable':'Consumables','other':'Other messages'}

def validate_colours(colours):
    if not isinstance(colours,dict):raise ValueError('Expected a colour mapping.')
    result={}
    for key in DEFAULT_COLOURS:
        value=colours.get(key)
        if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value.strip()):
            raise ValueError(f'{LABELS[key]}: enter a hex colour such as #FF00FF.')
        result[key]=value.strip().upper()
    return result

def validate_style(value):
    if not isinstance(value,dict):raise ValueError('Invalid chat settings.')
    colours=validate_colours(value.get('colours'))
    size=value.get('size')
    if size not in (*TEXT_SIZES,'Manual'):raise ValueError('Select a text size.')
    pitch=value.get('pitch')
    if size!='Manual':pitch=TEXT_SIZES[size]
    if type(pitch) is not int or not 10<=pitch<=40:raise ValueError('Manual line spacing must be 10–40 px.')
    return dict(colours=colours,size=size,pitch=pitch)

def load_style(path=None, fallback_pitch=18):
    value=read_preferences(path).get('chat_style')
    try:return validate_style(value)
    except ValueError:
        # Preserve any old calibration while making the vanilla palette the default.
        if type(fallback_pitch) is not int or not 10<=fallback_pitch<=40:fallback_pitch=18
        size=next((k for k,v in TEXT_SIZES.items() if v==fallback_pitch),'Manual')
        return dict(colours=dict(DEFAULT_COLOURS),size=size,pitch=fallback_pitch)

def save_style(value,path=None):
    value=validate_style(value);write_preference('chat_style',value,path)
    return value

def palette_groups(colours):
    grouped={}
    for kind,colour in colours.items():grouped.setdefault(colour,[]).append(kind)
    return {colour:tuple(kinds) for colour,kinds in grouped.items()}

def pixel_masks(rgb,colours,tolerance=40):
    """Match each distinct colour once. Nearest match wins for close colours."""
    groups=palette_groups(colours)
    pixels=np.asarray(rgb,dtype=np.int16)
    distances=[]; matches=[]
    for colour in groups:
        target=np.array([int(colour[i:i+2],16) for i in (1,3,5)],dtype=np.int16)
        diff=np.abs(pixels-target)
        distance=diff.max(axis=-1)
        chroma=target.max()-target.min()
        # Avoid dim backgrounds masquerading as light text; tolerate antialiasing
        # and the client renderer's slightly altered colours.
        close=(distance<=tolerance)
        if target.max()>=100:close &= pixels.max(axis=-1)>=max(100,int(target.max()*.68))
        if chroma>=30:
            hi=int(target.argmax());lo=int(target.argmin())
            close &= pixels[...,hi]-pixels[...,lo]>=max(12,int(chroma*.42))
        distances.append(np.where(close,distance,32767));matches.append(close)
    best=np.argmin(np.stack(distances),axis=0)
    return {groups[colour]:matches[i]&(best==i) for i,colour in enumerate(groups)}

def row_group(rgb,colours):
    masks=pixel_masks(rgb,colours)
    counts=sorted(((int(m.sum()),k) for k,m in masks.items()),reverse=True)
    if not counts or counts[0][0]<20 or (len(counts)>1 and counts[0][0]<2*counts[1][0]):return ()
    return counts[0][1]

def styled_rows(rgb,pitch,colours,tolerance=40):
    m=np.zeros(rgb.shape[:2],dtype=bool)
    for mask in pixel_masks(rgb,colours,tolerance).values():m|=mask
    n=len(m)//pitch
    return m[:n*pitch].reshape(n,pitch,m.shape[1])


def line_centres(mask,pitch):
    profile=mask.sum(axis=1)
    active=np.flatnonzero(profile>=max(5,round(mask.shape[1]*.012)))
    bands=np.split(active,np.where(np.diff(active)>2)[0]+1)
    return np.array([(x[0]+x[-1])/2 for x in bands if len(x)>=3 and x[-1]-x[0]<max(15,pitch)])

def fit_lattice(centres,pitch):
    if len(centres)<4:return None
    candidates=[]
    for p in range(max(10,pitch-4),min(40,pitch+4)+1):
        distances=np.abs(((centres[:,None]-centres[None,:]+p/2)%p)-p/2)
        scores=(distances<=1.5).sum(axis=0)
        j=int(np.argmax(scores));inliers=distances[:,j]<=1.5
        fit=centres[inliers]
        if len(fit)<4 or len(fit)/len(centres)<.8 or np.ptp(fit)<3*p:continue
        if not np.any(np.abs(np.diff(fit)-p)<=2):continue
        err=float(distances[inliers,j].mean())
        candidates.append((len(fit),-err,-abs(p-pitch),p,fit))
    if not candidates:return None
    _,_,_,actual,fit=max(candidates,key=lambda x:x[:3])
    phase=int(round((np.median(fit-np.round((fit-fit[0])/actual)*actual)-actual/2)%actual))%actual
    return actual,phase,True

def row_alignment(rgb,pitch,colours):
    """Infer line geometry from coloured text, or tightly matched full palette.

    Ordinary beige messages provide important anchors when XP and loot are
    sparse. A strict palette mask and periodic fit reject most terrain noise.
    """
    groups=pixel_masks(rgb,colours,tolerance=30)
    anchors=np.zeros(rgb.shape[:2],dtype=bool)
    for hexcolour,kinds in palette_groups(colours).items():
        colour=[int(hexcolour[i:i+2],16) for i in (1,3,5)]
        if max(colour)-min(colour)>=120:anchors|=groups[kinds]
    centres=line_centres(anchors,pitch)
    result=fit_lattice(centres,pitch)
    if result:return result
    full=np.logical_or.reduce(list(pixel_masks(rgb,colours,tolerance=22).values()))
    all_centres=line_centres(full,pitch)
    result=fit_lattice(all_centres,pitch)
    if result:
        # Require consistency with any independently visible bright lines.
        p,phase,_=result
        if not len(centres) or np.mean(np.abs(((centres-phase-p/2+p/2)%p)-p/2)<=3)>=.8:return result
    if len(centres)>=2:
        delta=np.abs(((centres-centres[0]+pitch/2)%pitch)-pitch/2)
        if np.max(delta)<=1.5:
            return pitch,int(round((centres[0]-pitch/2)%pitch))%pitch,False
    return pitch,0,False

def aligned_rows(rgb,pitch,phase,colours):
    """Return matching mask and RGB rows using identical physical boundaries."""
    start=phase if phase<=pitch//2 else phase-pitch
    count=max(0,(len(rgb)-start+pitch//2)//pitch)
    end=start+count*pitch
    a=max(0,start);b=min(len(rgb),end)
    cropped=rgb[a:b]
    pad=(max(0,-start),max(0,end-len(rgb)))
    if any(pad):cropped=np.pad(cropped,((pad[0],pad[1]),(0,0),(0,0)))
    n=len(cropped)//pitch
    rows=cropped[:n*pitch].reshape(n,pitch,rgb.shape[1],3)
    return styled_rows(cropped,pitch,colours,tolerance=25),rows
