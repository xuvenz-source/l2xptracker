"""Conservative native reward recognition. No runtime font synthesis or learning."""
import base64,json,zlib
from functools import lru_cache
import numpy as np
from chat_native_data import DATA

HEIGHT={'Large':12,'Medium':10,'Small':9}
THRESHOLDS={'xp':(235,245),'shot':(235,245),'adena':(180,195)}
PATTERNS={'xp':('You','have','acquired',None,'XP','and',None,'SP.'),
          'adena':('You','have','obtained',None,'Adena.'),
          'shot':('Use','Soulshot:','No','Grade.')}

@lru_cache(maxsize=1)
def library():
    raw=json.loads(zlib.decompress(base64.b64decode(DATA)))
    return {k:{label:tuple((s.split(':')[0],int(s.split(':')[1],16)) for s in variants) for label,variants in d.items()} for k,d in raw.items()}

def colour_mask(row,kind,threshold):
    r,g,b=row.astype(np.int16).transpose(2,0,1)
    if kind=='xp':return (r>=threshold)&(b>=threshold)&(g<100)
    if kind=='adena':return (r>=threshold)&(g>=threshold)&(b<100)
    return (r<90)&(g>=120)&(b>=threshold)&(b-r>=120)

def parts(mask,gap):
    xs=np.flatnonzero(mask.any(0))
    return [(int(g[0]),int(g[-1])+1) for g in np.split(xs,np.where(np.diff(xs)>gap)[0]+1) if len(g)]

def signature(mask):
    ys=np.flatnonzero(mask.any(1))
    if not len(ys):return None
    mask=mask[ys[0]:ys[-1]+1]
    return (f'{mask.shape[0]}x{mask.shape[1]}',int.from_bytes(np.packbits(mask).tobytes(),'big'))

def matches(sig,variants,tolerance=0):
    return sig is not None and any(sig[0]==shape and (sig[1]^bits).bit_count()<=tolerance for shape,bits in variants)

def recognise_mask(mask,size,kind,threshold):
    if mask.ndim!=2 or min(mask.shape)<3 or mask[0].any() or mask[-1].any() or mask[:,0].any() or mask[:,-1].any():return None
    ys=np.flatnonzero(mask.any(1))
    if not len(ys) or ys[-1]-ys[0]+1!=HEIGHT[size]+(3 if kind=='xp' else 0):return None
    mask=mask[ys[0]:ys[-1]+1]
    words=parts(mask,4 if size=='Small' else 5);pattern=PATTERNS[kind]
    if len(words)!=len(pattern) or any(not 4<=b-c<=9 for (_,c),(b,_) in zip(words,words[1:])):return None
    lib=library().get(f'{size}:{kind}:{threshold}',{});values=[]
    for label,(a,b) in zip(pattern,words):
        word=mask[:,a:b]
        if label is not None:
            if not matches(signature(word),lib.get('w:'+label,()),0 if kind=='shot' else 2):return None
        else:
            digits=parts(word,1)
            if not 1<=len(digits)<=7 or any(not 1<=b-c<=4 for (_,c),(b,_) in zip(digits,digits[1:])):return None
            text=''
            for left,right in digits:
                sig=signature(word[:,left:right]);choices=[d for d in '0123456789' if matches(sig,lib.get('d:'+d,()))]
                if len(choices)!=1:return None
                text+=choices[0]
            if len(text)>1 and text.startswith('0'):return None
            values.append(int(text))
    if values and values[0]<=0:return None
    return tuple(values)

def recognise(row,kind):
    if kind not in THRESHOLDS or row.ndim!=3 or row.shape[2]!=3 or not 12<=row.shape[0]<=26:return None
    masks=[colour_mask(row,kind,t) for t in THRESHOLDS[kind]]
    results=[]
    for size in HEIGHT:
        reads=[recognise_mask(m,size,kind,t) for m,t in zip(masks,THRESHOLDS[kind])]
        if reads[0] is not None and reads[0]==reads[1]:results.append(reads[0])
    return results[0] if len(results)==1 else None
