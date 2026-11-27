"""Tracking and updater preferences, separate from calibration."""
import json, os, tempfile
from pathlib import Path
from settings import settings_path

def preference_path():
    return settings_path().with_name('tracker_preferences.json')

def read_preferences(path=None):
    try:
        value=json.loads(Path(path or preference_path()).read_text(encoding='utf-8'))
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError,TypeError):return {}

def read_bool(key,default,path=None):
    value=read_preferences(path).get(key,default)
    return value if type(value) is bool else default

def write_preference(key,value,path=None):
    p=Path(path or preference_path());p.parent.mkdir(parents=True,exist_ok=True)
    data=read_preferences(p);data[key]=value
    fd,tmp=tempfile.mkstemp(prefix='.preferences-',dir=p.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as out:json.dump(data,out)
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def load_focus_pause(path=None):return read_bool('pause_on_blur',False,path)
def save_focus_pause(value,path=None):
    if type(value) is not bool:raise ValueError('Expected a boolean')
    write_preference('pause_on_blur',value,path)

def load_auto_update(path=None):return read_bool('auto_update',True,path)
def save_auto_update(value,path=None):
    if type(value) is not bool:raise ValueError('Expected a boolean')
    write_preference('auto_update',value,path)

def failed_update(path=None):
    value=read_preferences(path).get('failed_update','')
    return value if isinstance(value,str) else ''

def mark_failed_update(version,path=None):
    write_preference('failed_update',version,path)

# 92% corresponds to the previous hard-coded alpha value of 235/255.
HUD_OPACITY_DEFAULT=92
HUD_OPACITY_MIN=20
HUD_OPACITY_MAX=100

def validate_hud_opacity(value):
    if type(value) is not int or not HUD_OPACITY_MIN<=value<=HUD_OPACITY_MAX:
        raise ValueError('HUD opacity must be a whole percentage from 20 to 100.')
    return value

def load_hud_opacity(path=None):
    try:return validate_hud_opacity(read_preferences(path).get('hud_opacity',HUD_OPACITY_DEFAULT))
    except ValueError:return HUD_OPACITY_DEFAULT

def save_hud_opacity(value,path=None):
    write_preference('hud_opacity',validate_hud_opacity(value),path)

def load_hud_net_adena(path=None):return read_bool('hud_net_adena',False,path)

def save_hud_net_adena(value,path=None):
    if type(value) is not bool:raise ValueError('Expected a boolean')
    write_preference('hud_net_adena',value,path)

# Zero means unlimited; never automatically remove the last rollback copy.
def load_backup_retention(path=None):
    value=read_preferences(path).get('backup_retention',2)
    return value if type(value) is int and value in (0,1,2) else 2

def save_backup_retention(value,path=None):
    if type(value) is not int or value not in (0,1,2):raise ValueError('Choose one, two or all backups')
    write_preference('backup_retention',value,path)


def load_numeric_templates(path=None):
    return read_preferences(path).get('numeric_templates',True) is not False

def save_numeric_templates(value,path=None):
    if type(value) is not bool:raise ValueError('Expected a boolean')
    write_preference('numeric_templates',value,path)
