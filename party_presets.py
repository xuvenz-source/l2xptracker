"""Saved, named party rosters. Local preferences, not session data."""
from preferences import read_preferences, write_preference
from party import roster

KEY='party_presets'

def preset_name(name):
    name=name.strip()
    if not name or len(name)>60 or any(ord(c)<32 for c in name):
        raise ValueError('Enter a preset name between 1 and 60 characters.')
    return name

def load_presets(path=None):
    raw=read_preferences(path).get(KEY,{})
    if not isinstance(raw,dict):return {}
    result={};seen=set()
    for name,members in raw.items():
        try:
            name=preset_name(name)
            if not isinstance(members,list) or not all(isinstance(x,str) for x in members):continue
            members=roster(','.join(members))
            if not members or name.casefold() in seen:continue
            result[name]=members;seen.add(name.casefold())
        except (ValueError,TypeError):continue
    return dict(sorted(result.items(),key=lambda kv:kv[0].casefold()))

def save_preset(name,members,path=None,replace=False):
    name=preset_name(name);members=roster(','.join(members))
    if not members:raise ValueError('Enter at least one other party member to save a preset.')
    current=load_presets(path)
    existing=next((n for n in current if n.casefold()==name.casefold()),None)
    if existing is not None and not replace:raise ValueError('A preset with this name already exists.')
    if existing is not None:del current[existing]
    current[name]=members
    write_preference(KEY,current,path)
    return name

def rename_preset(old,new,path=None):
    current=load_presets(path)
    if old not in current:raise ValueError('Preset not found.')
    new=preset_name(new)
    if any(n!=old and n.casefold()==new.casefold() for n in current):
        raise ValueError('A preset with this name already exists.')
    current[new]=current.pop(old)
    write_preference(KEY,current,path)
    return new

def delete_preset(name,path=None):
    current=load_presets(path)
    if name not in current:raise ValueError('Preset not found.')
    del current[name]
    write_preference(KEY,current,path)
