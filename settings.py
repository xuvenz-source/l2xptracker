"""Version-independent chat calibration, with validated client-relative geometry."""
import json, os
from pathlib import Path


def settings_path():
    return Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'L2LegacyTracker' / 'settings.json'


def validate(data):
    if not isinstance(data, dict) or data.get('schema') != 1:
        raise ValueError('Unsupported settings format')
    for key in ('title', 'window_class'):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError('Missing window identity')
    w,h,p = (data.get(k) for k in ('width','height','pitch'))
    if any(type(x) is not int for x in (w,h,p)) or min(w,h)<100 or not 10<=p<=40:
        raise ValueError('Invalid calibration dimensions')
    region=data.get('region')
    if not isinstance(region,dict): raise ValueError('Missing chat region')
    l,t,r,b=(region.get(k) for k in ('left','top','width','height'))
    if any(type(x) is not int for x in (l,t,r,b)) or min(l,t)<0 or r<100 or b//p<3 or l+r>w or t+b>h:
        raise ValueError('Invalid chat region')
    hud=data.get('hud_position')
    # Optional fields must not invalidate an otherwise usable old calibration.
    if hud is not None and (not isinstance(hud,(list,tuple)) or len(hud)!=2 or any(type(x) is not int or x<0 for x in hud)):
        data=dict(data); data.pop('hud_position',None)
    return data


def load(path=None):
    path=Path(path) if path is not None else settings_path()
    if not path.exists(): return None
    return validate(json.loads(path.read_text(encoding='utf-8')))


def save(data,path=None):
    path=Path(path) if path is not None else settings_path()
    data=validate(data); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(data,indent=2),encoding='utf-8'); os.replace(tmp,path)


def select_match(matches, foreground):
    # Never arbitrarily select a client when several have the same identity.
    if len(matches)==1: return matches[0]
    return next((m for m in matches if m.hwnd==foreground),None)
