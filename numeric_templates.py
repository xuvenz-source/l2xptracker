"""Conservative, passive numeric recognition for verified Large chat glyphs."""
import numpy as np
import json,base64,zlib
from functools import lru_cache

# Binary glyph masks only; no screenshots, names or game background.
# Derived from 11 verified Large-text samples; 32 distinct digit masks.
DATA = 'eNrNV02P2zYQ/S8+CwWHQ1PD3PoPAuTSoNiDNCTbvWzQbdIcgv3vfUPJktaWvd4CBSJgbZlP8+ZxvsT9cciPfzx+/fvw4cfBHT78fiDf9R1LGkhJ2EXXvjKTukO3j8o5Ot60HW/Z5j30AfCs7dh5YgmeXPtIdbbFOl9f1+062Pyy0z4lIeddIIlOvIPrvi566l2o3oXqhMI7z95j1w8Mbifq8CicjDpZnyO8Qeo4IQXMQBIQcIZlR+awJx+DDASHwTUVJ1UTOpyjYDiuMSnTpl111O4q8ZqjS5R3Udmi4I8LP6kpdzXJMGeZNjVwiaZ9lO5Bxx00S9mi0NYv2qqF1bJFKEGxSOPHmtNLlF1jkDWnI0skzSUP7SatOT1DcjHLdNl1khE98+BZ1t5Ib6O8QdnQh5fu8P3Lc279/fnLt9mXP3bYAi4ULT5J7NMFJTQKBSIrL3KKloEX65tA1kHeJbTRDIQQIzkoyrOIRmpEni5IORDfRarXSHkmVSONE2nksZEKbOMeqTTSohGOWWlqvz+Hf8ocB3ZdE2mBmK7Tz0IloipVTZfpJu/BF1g11UKcyKN3goQjihwuSSEgKJpcC0G9UJk28JaL0lzo5IL3XaRdF3q3C/hoLvjcxUhxx0XeuKgWsUH/+vb4XPJpBh+72Q+98jpd4dWvEZlihDCh3jExNISUXELnRB/d5BRxdZBQkX1kMAjX5Oq89QQ6lFNAScPMqjXwaiZOeiaKuPBESmlED/ShhxmVpYTeK7ef5BYyufpTy62v5KrGvJUrV+XGW3JlI7fncSuXV7lTL/32ca4Jih1aXCN7u9CaVkz4E/wQxrz1DmsOGHzYAD29kmCo+4Z49a+G8YphgWEPQ75m+Mqj1fLTqYy979aQTrE+Fl+sShWJtyCQla70yW4tYJjadotuCpoznOV5Su1T0f9KNd6gwkY/ffzllJvUIXFi0xCD0U5CyLpTZ6PRYUr3IHdsdebNaxAMW7JesIfnYF+nqHZIuY+inyn0/RTYUBmen5YZFGK33xW0XUYyKR7VRg9eEHi1JBHFqqDe0QwIGqZgCXYuVJzS8LK25fYCMxhPoQcctacjllsv2KkMV3XFlq1zpw3eJ6nOkpDRVZJel5T/g6SKsf0eSbRIiiXGnnKTRNck1bcllUWSrFFCDn/N5Wk41WXApJNVSlneW+64ivV4k6KXIcD5iEME2bFa7IiSbK7ZCVYw3or5cPZlwji1c4BvotphIEmbePjHAlMyQmdkxzxQsXY5lSgEoVTeFIThUpog/ikERd0I4o0guSWo2lS8KajgNAnmOgt6eHn5FxjpMGo='

def trim(mask):
    y,x=np.nonzero(mask)
    if not len(x):return None
    return mask[y.min():y.max()+1,x.min():x.max()+1]

def decode(value):
    h,w,raw=value.split(',');h,w=int(h),int(w)
    return np.unpackbits(np.frombuffer(bytes.fromhex(raw),dtype=np.uint8),count=h*w).reshape(h,w).astype(bool)

@lru_cache(maxsize=1)
def library():
    data=json.loads(zlib.decompress(base64.b64decode(DATA)))
    return {kind:{k:tuple(decode(v) for v in vals) for k,vals in group.items()} for kind,group in data.items()}

def score(glyph,templates):
    return max((1-float(np.mean(glyph!=t)) for t in templates if t.shape==glyph.shape),default=0.)

@lru_cache(maxsize=1024)
def classify_digit(height,width,packed,strict=False):
    glyph=np.unpackbits(np.frombuffer(packed,dtype=np.uint8),count=height*width).reshape(height,width).astype(bool)
    scores=sorted(((score(glyph,v),k) for k,v in library()['digits'].items()),reverse=True)
    best,digit=scores[0]
    def center(m):
        pad=7-m.shape[1];return np.pad(m,((0,0),(pad//2,pad-pad//2)))
    centered=center(glyph)
    other=max((1-float(np.mean(centered!=center(t))) for k,v in library()['digits'].items() if k!=digit for t in v),default=0.)
    return digit if best>=(.97 if strict else .90) and best-other>=(.17 if strict else .10) else None

def groups(mask,gap):
    xs=np.flatnonzero(mask.any(0))
    if not len(xs):return []
    return [(int(g[0]),int(g[-1])+1) for g in np.split(xs,np.where(np.diff(xs)>gap)[0]+1)]

def number(mask,strict=False):
    pieces=groups(mask,1)
    if not 1<=len(pieces)<=7:return None
    if any(b-c>4 or b-c<1 for (_,c),(b,_) in zip(pieces,pieces[1:])):return None
    out=[]
    for a,b in pieces:
        g=trim(mask[:,a:b])
        if g is None or g.shape[0]!=12 or not 5<=g.shape[1]<=7:return None
        d=classify_digit(*g.shape,np.packbits(g).tobytes(),strict)
        if d is None:return None
        out.append(d)
    if len(out)>1 and out[0]=='0':return None
    return int(''.join(out))

XP_PATTERN=('You','have','acquired',None,'XP','and',None,'SP.')
AD_PATTERN=('You','have','earned',None,'Adena.')

def match_mask(mask,kind,strict=False,fields=None):
    if mask.ndim!=2 or mask.shape[0] not in (20,21,22,23):return None
    ys,xs=np.nonzero(mask)
    if not len(xs) or ys.min()==0 or ys.max()==len(mask)-1 or xs.min()==0 or xs.max()==mask.shape[1]-1:return None
    band=np.flatnonzero(mask.sum(axis=1)>=4)
    if len(band)==0 or band[-1]-band[0]+1!=12:return None
    if band[0]-ys.min()>2 or ys.max()-band[-1]>3:return None
    mask=mask[band[0]:band[-1]+1]
    words=groups(mask,5);pattern=XP_PATTERN if kind=='xp' else AD_PATTERN
    if len(words)!=len(pattern):return None
    if any(not 5<=b-c<=9 for (_,c),(b,_) in zip(words,words[1:])):return None
    values=[]
    for label,(a,b) in zip(pattern,words):
        part=mask[:,a:b]
        if label is None:
            n=number(part,strict)
            if n is None:return None
            values.append(n)
            if fields is not None:fields.append(part.copy())
        else:
            glyph=trim(part)
            if glyph is None or score(glyph,library()['words'][label])<(.97 if strict else .92):return None
    if not values or values[0]<=0:return None
    return tuple(values)

def recognise(row,kind):
    """Two contrast thresholds must agree; unsupported layouts fall back."""
    if kind not in ('xp','adena') or row.ndim!=3 or row.shape[2]!=3 or row.shape[0] not in (20,21,22,23):return None
    r,g,b=row.transpose(2,0,1)
    results=[]
    for threshold in (175,180):
        mask=(r>threshold)&((b>threshold)&(g<100) if kind=='xp' else (g>threshold)&(b<100))
        result=match_mask(mask,kind)
        if result is None:return None
        results.append(result)
    return results[0] if results[0]==results[1] else None


def strict_adena(row):
    """Return the value and isolated field only for a complete verified line."""
    if row.ndim!=3 or row.shape[2]!=3 or row.shape[0] not in (20,21,22,23):return None
    r,g,b=row.transpose(2,0,1)
    results=[];crops=[]
    for threshold in (175,180):
        fields=[]
        v=match_mask((r>threshold)&(g>threshold)&(b<100),'adena',strict=True,fields=fields)
        if v is None or len(fields)!=1:return None
        results.append(v[0]);crops.append(fields[0])
    if results[0]!=results[1]:return None
    return results[0],crops[0]
