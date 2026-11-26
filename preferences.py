"""Tracking preferences, separate from calibration."""
import json, os, tempfile
from pathlib import Path
from settings import settings_path

def preference_path():
    return settings_path().with_name('tracker_preferences.json')

def load_focus_pause(path=None):
    try:
        value=json.loads(Path(path or preference_path()).read_text(encoding='utf-8')).get('pause_on_blur',False)
        return value if type(value) is bool else False
    except (OSError,ValueError,AttributeError,TypeError):return False

def save_focus_pause(value,path=None):
    if type(value) is not bool:raise ValueError('Expected a boolean')
    p=Path(path or preference_path());p.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.preferences-',dir=p.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as out:json.dump({'pause_on_blur':value},out)
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
