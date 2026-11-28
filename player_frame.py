"""Locate the native compact player frame from its HP/MP bar geometry."""
import numpy as np

def fit_player_frame(rgb):
    """Return local level/XP rectangles, or abstain on ambiguous geometry.

    Supports the native compact frame, not the detailed Character Status
    window. Use full red/blue bar geometry, not OCR guesses from HP/MP.
    """
    if rgb.ndim!=3 or rgb.shape[2]!=3:return None
    h,w=rgb.shape[:2]
    if not (65<=h<=180 and 180<=w<=500):return None
    r,g,b=rgb.astype(np.int16).transpose(2,0,1)
    red=(r>80)&(r>1.5*g)&(r>1.5*b)
    blue=(b>65)&(b>1.5*r)&(b>1.15*g)
    def bands(mask):
        ys=np.flatnonzero(mask.sum(1)>=50)
        return [(int(z[0]),int(z[-1])+1) for z in np.split(ys,np.where(np.diff(ys)>1)[0]+1) if 7<=len(z)<=13]
    def edges(mask,t,e):
        xs=np.flatnonzero(mask[t:e].sum(0)>=3)
        return (int(xs[0]),int(xs[-1])+1) if len(xs) else None
    candidates=[]
    for t,e in bands(red):
        for u,v in bands(blue):
            if not 1<=u-e<=5 or not 10<=u-t<=15:continue
            re,be=edges(red,t,e),edges(blue,u,v)
            if not re or not be:continue
            x,right=be
            if abs(re[0]-x)>3 or not 180<=right-x<=350 or re[1]>right+4:continue
            lv=dict(left=x+1,top=t-36,width=18,height=17)
            xp=dict(left=(x+right)//2-40,top=v+1,width=80,height=14)
            if any(z['left']<0 or z['top']<0 or z['left']+z['width']>w or z['top']+z['height']>h for z in (lv,xp)):continue
            candidates.append(dict(level=lv,percent=xp))
    return candidates[0] if len(candidates)==1 else None

def verified_player_frame(image,reader):
    """Confirm both candidate fields with the existing fixed-font reader."""
    regions=fit_player_frame(np.asarray(image.convert('RGB')))
    if regions is None:return None
    values={}
    for kind,r in regions.items():
        x,y,w,h=(r[k] for k in ('left','top','width','height'))
        value=reader(image.crop((x,y,x+w,y+h)),kind)
        if value is None:return None
        values[kind]=value
    return regions,values
