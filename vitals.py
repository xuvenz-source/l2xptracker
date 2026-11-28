"""Passive HP/MP sampling from the compact player frame. No game input."""
import re
from collections import Counter
import numpy as np
from PIL import Image,ImageOps

def inside(r,w,h):
    return isinstance(r,dict) and all(type(r.get(k)) is int for k in ('left','top','width','height')) and min(r['left'],r['top'])>=0 and min(r['width'],r['height'])>=3 and r['left']+r['width']<=w and r['top']+r['height']<=h

def clean_vitals(value,w,h):
    if not isinstance(value,dict):return None
    frame=value.get('frame')
    if not inside(frame,w,h) or not (65<=frame['height']<=180 and 180<=frame['width']<=500):return None
    bars=value.get('bars')
    if not isinstance(bars,dict):return None
    hp,mp=bars.get('hp'),bars.get('mp')
    if not all(inside(r,frame['width'],frame['height']) for r in (hp,mp)):return None
    if hp['left']!=mp['left'] or hp['width']!=mp['width'] or not 180<=hp['width']<=350 or not 7<=hp['height']<=13 or not 7<=mp['height']<=13 or not 10<=mp['top']-hp['top']<=15:return None
    return dict(frame=dict(frame),bars={'hp':dict(hp),'mp':dict(mp)})

def layout_from_regions(frame,regions):
    # The verified auto-fit supplies the level and XP rectangles in local
    # coordinates. Their anchors identify the compact native bar track.
    lv,xp=regions['level'],regions['percent']
    x=lv['left']-1;top=lv['top']+36
    width=2*(xp['left']+xp['width']//2-x)
    mp_top=xp['top']-11
    bars={k:dict(left=x,top=y,width=width,height=10) for k,y in (('hp',top),('mp',mp_top))}
    return clean_vitals(dict(frame=frame,bars=bars),frame['left']+frame['width'],frame['top']+frame['height'])

def crop_bar(rgb,r):
    x,y,w,h=(r[k] for k in ('left','top','width','height'))
    return rgb[y:y+h,x:x+w]

def bar_fraction(bar,kind):
    """Estimate the coloured fill; abstain on blank or irregular pixels."""
    if bar.ndim!=3 or bar.shape[2]!=3 or bar.shape[0]<7 or bar.shape[1]<180:return None
    r,g,b=bar.astype(np.int16).transpose(2,0,1)
    mask=(r>95)&(r-g>45)&(r-b>50) if kind=='hp' else (b>100)&(b-r>85)&(b-g>45)
    xs=np.flatnonzero(mask.sum(0)>=3)
    if not len(xs) or xs[0]>5:return None
    end=int(xs[-1])+1
    # Text overlays can obscure sections of the fill. A disconnected tail
    # or mostly empty region is not reliable evidence of a filled bar.
    if len(xs)/end<.5:return None
    if len(xs)>1 and np.max(np.diff(xs))>75:return None
    return min(1.,end/bar.shape[1])

def parse_pair(text):
    m=re.fullmatch(r'\s*([0-9]{1,7})\s*/\s*([0-9]{1,7})\s*',text)
    if not m:return None
    current,maximum=map(int,m.groups())
    return (current,maximum) if 0<=current<=maximum and maximum>0 else None

def verified_pair(readings,fraction):
    if fraction is None:return None
    compatible=[p for text in readings if (p:=parse_pair(text)) and abs(p[0]/p[1]-fraction)<=.04]
    counts=Counter(compatible)
    if len(counts)==1 and next(iter(counts.values()))>=2:return next(iter(counts))
    return None

def current_pair(fraction,seen_fraction,pair,age):
    """Use the same fill tolerance as OCR, but invalidate on actual fill movement."""
    if fraction is None or seen_fraction is None or pair is None or age>4 or age<0:return None
    if abs(fraction-seen_fraction)>.012 or abs(pair[0]/pair[1]-fraction)>.04:return None
    return pair

def vital_masks(bar):
    w=bar.shape[1];a=bar[:,max(0,w//2-50):min(w,w//2+50)].astype(np.int16)
    neutral=a.max(2)-a.min(2)
    gray=(a[:,:,0].astype(np.int32)*299+a[:,:,1].astype(np.int32)*587+a[:,:,2].astype(np.int32)*114)//1000
    return tuple((a.min(2)>=t)&(neutral<=45) for t in (115,140,100))+tuple((gray>=t)&(neutral<=80) for t in (140,175))

def vital_signature(bar):
    """Identity of the exact OCR inputs, never fuzzy glyph similarity."""
    masks=vital_masks(bar)
    if any(m.sum()<20 for m in masks):
        w=bar.shape[1];crop=bar[:,max(0,w//2-50):min(w,w//2+50)]
        return ('raw',crop.shape,crop.tobytes())
    return (masks[0].shape,*(np.packbits(m).tobytes() for m in masks))

def compatible_pair(pair,fraction):
    return pair is not None and fraction is not None and abs(pair[0]/pair[1]-fraction)<=.04

def read_vital_pair(bar,fraction):
    """Use isolated white digits and require two matching, fill-checked reads."""
    if fraction is None:return None
    import pytesseract
    masks=vital_masks(bar)
    reads=[]
    def read(mask,psm=7,scale=6):
        im=Image.fromarray(np.where(mask,0,255).astype(np.uint8))
        im=ImageOps.expand(im.resize((im.width*scale,im.height*scale),Image.Resampling.LANCZOS),border=12,fill=255)
        try:reads.append(pytesseract.image_to_string(im,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789/',timeout=2))
        except RuntimeError:pass
    # Stop at the original three-mask consensus, or try the two
    # alternate luminance masks if necessary. Do not skip a conflicting
    # third standard read just because the first two matched.
    for mask in masks[:3]:read(mask)
    answer=verified_pair(reads,fraction)
    if answer is not None:return answer
    for mask in masks[3:]:read(mask,psm=8,scale=8)
    return verified_pair(reads,fraction)

DISPLAY_MODES=('Value','Percent','Both')

def display_value(fraction,pair=None,mode='Both'):
    """Keep the chosen format even when exact OCR is temporarily unavailable."""
    exact=f'{pair[0]}/{pair[1]}' if fraction is not None and pair is not None else '—'
    percent=('—' if fraction is None else
             f'{round(pair[0]*100/pair[1])}%' if pair is not None else f'~{round(fraction*100)}%')
    if mode=='Value':return exact
    if mode=='Percent':return percent
    return exact+' - '+percent

