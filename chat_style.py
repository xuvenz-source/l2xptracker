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

def styled_rows(rgb,pitch,colours):
    m=np.zeros(rgb.shape[:2],dtype=bool)
    for mask in pixel_masks(rgb,colours).values():m|=mask
    n=len(m)//pitch
    return m[:n*pitch].reshape(n,pitch,m.shape[1])
