"""Exact native compact-frame HP/MP digits, with no learned or fuzzy matches.

The shared status-font digits and the observed slash are binary masks at
two native luminance thresholds. A complete pair must agree at both
thresholds, fit the native baseline and agree with the measured bar fill.
"""
import re
import numpy as np
from PIL import Image
from font_library import EXTRA,mask_string as signature,vital_lookup

LOOKUP={threshold:vital_lookup(threshold) for threshold in (140,175)}

def decode(mask,threshold):
    if mask.ndim!=2 or min(mask.shape)<3 or mask[0].any() or mask[-1].any() or mask[:,0].any() or mask[:,-1].any():return None
    xs=np.flatnonzero(mask.any(0))
    if not len(xs):return None
    groups=np.split(xs,np.where(np.diff(xs)>1)[0]+1)
    if not 3<=len(groups)<=15:return None
    if abs((int(xs[0])+int(xs[-1]))/2-(mask.shape[1]-1)/2)>12:return None
    glyphs=[]
    for group in groups:
        left,right=int(group[0]),int(group[-1])+1
        part=mask[:,left:right];ys=np.flatnonzero(part.any(1))
        if not len(ys):return None
        top,bottom=int(ys[0]),int(ys[-1])+1
        char=LOOKUP[threshold].get(signature(part[top:bottom]))
        if char is None:return None
        glyphs.append((char,left,right,top,bottom))
    text=''.join(g[0] for g in glyphs)
    if not re.fullmatch(r'(?:0|[1-9][0-9]{0,6})/[1-9][0-9]{0,6}',text):return None
    tops={g[3] for g in glyphs if g[0]!='/'}
    if len(tops)!=1:return None
    top=next(iter(tops))
    for char,_,_,t,b in glyphs:
        expected=(top+1,top+7) if char=='/' and threshold==175 else (top,top+8)
        if (t,b)!=expected:return None
    for a,b in zip(glyphs,glyphs[1:]):
        gap=b[1]-a[2]
        distance=(b[1]+b[2]-a[1]-a[2])/2
        if not 1<=gap<=9 or not 5<=distance<=11:return None
    current,maximum=map(int,text.split('/'))
    return (current,maximum) if current<=maximum else None

def recognise_vital_pair(bar,fraction):
    """Return exact current/max or abstain; accepts only native-size pixels."""
    if fraction is None or not 0<=fraction<=1:return None
    if bar.ndim!=3 or bar.shape[2]!=3 or not 10<=bar.shape[0]<=16 or bar.shape[1]<40:return None
    w=bar.shape[1]
    crop=bar[:,max(0,w//2-50):min(w,w//2+50)]
    gray=np.asarray(Image.fromarray(crop).convert('L'))
    low=decode(gray>=140,140)
    if low is None:return None
    high=decode(gray>=175,175)
    if high!=low or abs(low[0]/low[1]-fraction)>.04:return None
    return low
