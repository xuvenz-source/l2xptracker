"""Shared verified Lineage II glyph inventory.

Profiles describe observed rasterisation, not assumed Tahoma point sizes.
No generated font or calibration output is trusted by the live recognisers.
Existing public recogniser APIs retain their original data and policies.
"""
import base64,json,zlib
from functools import lru_cache
import numpy as np
from chat_native_data import DATA as CHAT_DATA

# White bar digits use the same shapes across HP/MP and XP in supplied samples.
# Keep additional exact masks for known contrast variations; never fuzzy-match.
TEMPLATES={
 'level': {
  120: {'2':'01110/00001/00001/00001/00010/00100/01000/11111','0':'01110/10000/10001/10001/10001/10001/10000/01110'},
  140: {'2':'1110/0001/0001/0001/0010/0100/1000/1111','0':'01110/10000/10001/10001/10001/10001/10000/01110'},
 },
 'percent': {
  140: {'2':'01110/10001/00001/00010/00100/01000/10000/11111','6':'00010/00100/01000/01110/10001/10001/11001/01110','9':'01110/10001/10001/10001/01111/00010/00100/01100','0':'011100/110010/100001/100001/100001/100001/010010/001100','1':'110/010/010/010/010/010/010/111','4':'000010/000110/001010/001010/010010/111111/000010/000110','5':'01111/10000/10000/11110/00001/00001/10001/01110','7':'11111/10001/00011/00010/00010/00100/00100/00100','8':'01110/10001/10001/01010/11110/10001/10001/11110','.':'1/1','%':'0100010/1010100/1010100/0101000/0001010/0010101/0010101/0100011'},
  175: {'2':'01110/10001/00001/00010/00100/01000/10000/11111','6':'00010/00100/01000/01110/10001/10001/10001/01110','9':'01110/10001/10001/10001/01110/00010/00000/00100','0':'001100/010010/100001/100001/100001/100001/010010/001100','1':'1/1/1/1/1/1/1/1','4':'000010/000110/001010/001010/010010/111111/000010/000010','5':'01110/10000/10000/11110/00001/00001/10001/01110','7':'11111/10001/00000/00010/00010/00100/00100/00100','8':'01110/10001/10001/01010/10110/10001/10001/01010','.':'1/1','%':'0100010/1010000/1010100/0101000/0001010/0010101/0010101/0000010'},
 }
}

VARIANTS={('percent',140):{'01111/10000/10000/11110/00011/00001/10001/01110':'5'}}

# Digit 3 from the 23.03% compact-frame sample. Slash from the HP/MP bars.
EXTRA={
    140:{'3':'01110/10001/00001/00110/00001/00001/10001/01110',
         '/':'001/001/001/001/010/010/010/110'},
    175:{'3':'01110/10001/00001/00010/00001/00001/10001/01110',
         '/':'01/01/01/10/10/10'},
}

# Binary glyph masks only; no screenshots, names or game background.
# Derived from 11 verified Large-text samples; 32 distinct digit masks.
LARGE_DATA = 'eNrNV02P2zYQ/S8+CwWHQ1PD3PoPAuTSoNiDNCTbvWzQbdIcgv3vfUPJktaWvd4CBSJgbZlP8+ZxvsT9cciPfzx+/fvw4cfBHT78fiDf9R1LGkhJ2EXXvjKTukO3j8o5Ot60HW/Z5j30AfCs7dh5YgmeXPtIdbbFOl9f1+062Pyy0z4lIeddIIlOvIPrvi566l2o3oXqhMI7z95j1w8Mbifq8CicjDpZnyO8Qeo4IQXMQBIQcIZlR+awJx+DDASHwTUVJ1UTOpyjYDiuMSnTpl111O4q8ZqjS5R3Udmi4I8LP6kpdzXJMGeZNjVwiaZ9lO5Bxx00S9mi0NYv2qqF1bJFKEGxSOPHmtNLlF1jkDWnI0skzSUP7SatOT1DcjHLdNl1khE98+BZ1t5Ib6O8QdnQh5fu8P3Lc279/fnLt9mXP3bYAi4ULT5J7NMFJTQKBSIrL3KKloEX65tA1kHeJbTRDIQQIzkoyrOIRmpEni5IORDfRarXSHkmVSONE2nksZEKbOMeqTTSohGOWWlqvz+Hf8ocB3ZdE2mBmK7Tz0IloipVTZfpJu/BF1g11UKcyKN3goQjihwuSSEgKJpcC0G9UJk28JaL0lzo5IL3XaRdF3q3C/hoLvjcxUhxx0XeuKgWsUH/+vb4XPJpBh+72Q+98jpd4dWvEZlihDCh3jExNISUXELnRB/d5BRxdZBQkX1kMAjX5Oq89QQ6lFNAScPMqjXwaiZOeiaKuPBESmlED/ShhxmVpYTeK7ef5BYyufpTy62v5KrGvJUrV+XGW3JlI7fncSuXV7lTL/32ca4Jih1aXCN7u9CaVkz4E/wQxrz1DmsOGHzYAD29kmCo+4Z49a+G8YphgWEPQ75m+Mqj1fLTqYy979aQTrE+Fl+sShWJtyCQla70yW4tYJjadotuCpoznOV5Su1T0f9KNd6gwkY/ffzllJvUIXFi0xCD0U5CyLpTZ6PRYUr3IHdsdebNaxAMW7JesIfnYF+nqHZIuY+inyn0/RTYUBmen5YZFGK33xW0XUYyKR7VRg9eEHi1JBHFqqDe0QwIGqZgCXYuVJzS8LK25fYCMxhPoQcctacjllsv2KkMV3XFlq1zpw3eJ6nOkpDRVZJel5T/g6SKsf0eSbRIiiXGnnKTRNck1bcllUWSrFFCDn/N5Wk41WXApJNVSlneW+64ivV4k6KXIcD5iEME2bFa7IiSbK7ZCVYw3or5cPZlwji1c4BvotphIEmbePjHAlMyQmdkxzxQsXY5lSgEoVTeFIThUpog/ikERd0I4o0guSWo2lS8KajgNAnmOgt6eHn5FxjpMGo='

CHAT_HEIGHT={'Large':12,'Medium':10,'Small':9}

def mask_string(mask):
    return '/'.join(''.join('1' if v else '0' for v in row) for row in mask)

def string_mask(value):
    return np.array([[c=='1' for c in row] for row in value.split('/')],dtype=bool)

def packed_mask(height,width,raw):
    return np.unpackbits(np.frombuffer(raw,dtype=np.uint8),count=height*width).reshape(height,width).astype(bool)

def status_lookup(kind,threshold):
    """Retain the exact original status tables and threshold-specific variants."""
    lookup={v:k for k,v in TEMPLATES[kind][threshold].items()}
    lookup.update(VARIANTS.get((kind,threshold),{}))
    return lookup

def vital_lookup(threshold):
    glyphs={s:c for s,c in status_lookup('percent',threshold).items() if c.isdigit()}
    glyphs.update({s:c for c,s in EXTRA[threshold].items()})
    return glyphs

@lru_cache(maxsize=1)
def large_library():
    data=json.loads(zlib.decompress(base64.b64decode(LARGE_DATA)))
    def decode(value):
        h,w,raw=value.split(',')
        return packed_mask(int(h),int(w),bytes.fromhex(raw))
    return {kind:{k:tuple(decode(v) for v in vals) for k,vals in group.items()} for kind,group in data.items()}

@lru_cache(maxsize=1)
def chat_library():
    raw=json.loads(zlib.decompress(base64.b64decode(CHAT_DATA)))
    return {k:{label:tuple((s.split(':')[0],int(s.split(':')[1],16)) for s in variants) for label,variants in d.items()} for k,d in raw.items()}

def verified_profiles():
    """Calibration-only inventory: profile -> character -> distinct masks.

    Thresholds and colour contexts are pooled for offline comparison only.
    Runtime matching continues to use the original separate thresholds.
    Full word/message templates are not treated as individual characters.
    """
    profiles={k:{} for k in ('Fixed status','Level badge','Large chat','Medium chat','Small chat')}
    def append(profile,char,mask):
        if not mask.any():return
        key=mask_string(mask)
        profiles[profile].setdefault(char,{})[key]=mask
    for threshold in TEMPLATES['percent']:
        for sig,char in status_lookup('percent',threshold).items():append('Fixed status',char,string_mask(sig))
        for sig,char in vital_lookup(threshold).items():append('Fixed status',char,string_mask(sig))
    for threshold in TEMPLATES['level']:
        for sig,char in status_lookup('level',threshold).items():append('Level badge',char,string_mask(sig))
    for char,masks in large_library()['digits'].items():
        for mask in masks:append('Large chat',char,mask.copy())
    for key,labels in chat_library().items():
        size=key.split(':',1)[0]
        for label,variants in labels.items():
            if not label.startswith('d:') or len(label)!=3:continue
            for shape,bits in variants:
                h,w=map(int,shape.split('x'))
                raw=bits.to_bytes((h*w+7)//8,'big')
                append(size+' chat',label[2],packed_mask(h,w,raw))
    return {p:{c:tuple(m.values()) for c,m in group.items()} for p,group in profiles.items()}
