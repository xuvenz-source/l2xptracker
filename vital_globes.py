"""Shared globe paint geometry; no capture, OCR or native resources."""
from functools import lru_cache
from math import sqrt,isfinite

PALETTE={
    'hp':((77,36,37),(117,32,38),(161,44,47),(212,72,68)),
    'mp':((28,47,78),(23,61,124),(36,100,178),(70,155,224)),
}
RIM=(158,133,90)
EMPTY=(30,33,43)
UNKNOWN=(48,49,55)
SURFACE={'hp':(247,128,112),'mp':(128,201,255)}

def fill_steps(fraction):
    if fraction is None or not isinstance(fraction,(int,float)) or not isfinite(fraction):return None
    return max(0,min(100,round(fraction*100)))

def globe_rectangles(kind,diameter,fraction):
    return _rectangles(kind,diameter,fill_steps(fraction))

@lru_cache(maxsize=128)
def _rectangles(kind,d,steps):
    """Circle scanlines with a fixed metal rim, liquid surface and tonal bands.

    Coordinates are half-open and relative to the globe's top-left.
    None is deliberately distinguished from a verified zero fill.
    """
    if kind not in PALETTE or d<12:return ()
    out=[];center=d/2;radius=center-1;inner=radius-3
    level=d-4 if steps==0 else 4 if steps==100 else d-4-round((d-8)*(steps or 0)/100)
    for y in range(d):
        dy=y+.5-center
        if abs(dy)>=radius:continue
        extent=sqrt(radius*radius-dy*dy)
        left=max(0,round(center-extent));right=min(d,round(center+extent))
        out.append((left,y,right,y+1,RIM))
        if abs(dy)>=inner:continue
        extent=sqrt(inner*inner-dy*dy)
        l=round(center-extent);r=round(center+extent)
        if steps is None:colour=UNKNOWN
        elif steps==0 or y<level:colour=EMPTY
        elif y==level and steps<100:colour=SURFACE[kind]
        else:colour=PALETTE[kind][max(0,min(3,3-int(4*y/d)))]
        if r>l:out.append((l,y,r,y+1,colour))
    return tuple(out)
