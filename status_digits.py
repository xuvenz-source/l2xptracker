"""Native character-status glyphs extracted from verified game crops.

Level badge and white status text have separate templates. Only binary glyph
shapes are retained. Unknown shapes abstain; no approximate matching.
"""
import re
from decimal import Decimal
import numpy as np

# Public aliases retained for existing callers and regression fixtures.
from font_library import TEMPLATES,VARIANTS,mask_string as signature,status_lookup

def recognise_mask(mask,kind,threshold):
    # Reject clipped glyphs and extra UI details rather than cropping them away.
    if mask.ndim!=2 or min(mask.shape)<3 or mask[0].any() or mask[-1].any() or mask[:,0].any() or mask[:,-1].any():return None
    xs=np.flatnonzero(mask.any(axis=0))
    if not len(xs):return None
    groups=np.split(xs,np.where(np.diff(xs)>1)[0]+1)
    if not 1<=len(groups)<=7:return None
    glyphs=[]
    lookup=status_lookup(kind,threshold)
    for group in groups:
        left,right=int(group[0]),int(group[-1])+1
        part=mask[:,left:right];ys=np.flatnonzero(part.any(axis=1))
        if not len(ys):return None
        top,bottom=int(ys[0]),int(ys[-1])+1
        char=lookup.get(signature(part[top:bottom]))
        if char is None:return None
        glyphs.append((char,left,right,top,bottom))
    text=''.join(g[0] for g in glyphs)
    if kind=='level':
        if not re.fullmatch(r'[1-9][0-9]?',text) or not 1<=int(text)<=75:return None
    elif not re.fullmatch(r'(?:0|[1-9][0-9]{0,2})\.[0-9]{2}%',text):return None
    # All full-height glyphs share a baseline; the dot sits at the bottom.
    tops={g[3] for g in glyphs if g[0]!='.'}
    if len(tops)!=1:return None
    top=next(iter(tops))
    if any((g[3]!=top+7 or g[4]!=top+9) if g[0]=='.' else g[4]!=top+8 for g in glyphs):return None
    for a,b in zip(glyphs,glyphs[1:]):
        gap=b[1]-a[2]
        if not 1<=gap<=(10 if kind=='percent' else 5):return None
    return text

def recognise_status(image,kind):
    """Return a value only if two native-resolution masks agree exactly."""
    if kind not in TEMPLATES:return None
    gray=np.asarray(image.convert('L'))
    if not (9<=gray.shape[0]<=40 and 3<=gray.shape[1]<=100):return None
    reads=[recognise_mask(gray>=t,kind,t) for t in TEMPLATES[kind]]
    if reads[0] is None or reads[0]!=reads[1]:return None
    if kind=='level':return int(reads[0])
    value=Decimal(reads[0][:-1]);return value if 0<=value<=100 else None
