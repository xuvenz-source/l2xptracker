"""Persistent monster profiles and separate, auditable kill identification."""
from bisect import bisect_right
from collections import Counter
from decimal import Decimal
import re
from preferences import read_preferences,write_preference
from drop_targets import clean as clean_drop,display as display_drop,combined_wait

from monster_header import split_name,labelled_rewards as header

def whole(value,low,high):
    try:n=int(str(value).strip())
    except (ValueError,TypeError):raise ValueError('Enter whole numbers for level, base XP and base SP.')
    if not low<=n<=high:raise ValueError(f'Value must be between {low} and {high}.')
    return n

def profile(drop,level,xp,sp,legacy=False):
    d=clean_drop(drop)
    name=d['monster'].strip()
    if not name:raise ValueError('Enter the monster name.')
    name,suffix=split_name(name)
    if suffix and not str(level).strip():level=suffix
    if not name:raise ValueError('Enter the monster name.')
    level=whole(level,1,100) if str(level).strip() else None
    if level is None and not legacy:raise ValueError('Enter monster level.')
    xp=whole(xp,1,10**9) if str(xp).strip() else None
    sp=whole(sp,0,10**9) if str(sp).strip() else None
    if (xp is None or sp is None) and not legacy:raise ValueError('Verify the base XP and SP values from the monster window.')
    label=name+(f' Lv.{level}' if level is not None else '')
    d['monster']=label
    return dict(id=name.casefold()+'|'+str(level or 0),name=name,level=level,xp=xp,sp=sp,drop=d)

def empty():return dict(profiles={},active=[],full_solo=False,learned=[],default=None)

def load(path=None):
    prefs=read_preferences(path);raw=prefs.get('monster_library')
    if isinstance(raw,dict):
        result=empty()
        for p in raw.get('profiles',{}).values():
            try:
                q=profile(p['drop'],p['level'] or '',p['xp'] if p['xp'] is not None else '',p['sp'] if p['sp'] is not None else '',True)
                result['profiles'][q['id']]=q
            except (ValueError,KeyError,TypeError):continue
        result['active']=[k for k in dict.fromkeys(raw.get('active',[])) if k in result['profiles']]
        default=raw.get('default')
        # Migrate a previously selected single farming monster when exact matching was off.
        if 'default' not in raw and len(result['active'])==1 and not raw.get('full_solo'):default=result['active'][0]
        result['default']=default if isinstance(default,str) and default in result['active'] else None
        result['full_solo']=raw.get('full_solo') is True
        result['learned']=[x for x in raw.get('learned',[]) if isinstance(x,dict) and x.get('id') in result['profiles'] and type(x.get('level')) is int and type(x.get('xp')) is int and type(x.get('sp')) is int]
        return result
    result=empty();old=clean_drop(prefs.get('drop_targets'))
    if old['monster']:
        p=profile(old,'','','',True);result['profiles'][p['id']]=p;result['active']=[p['id']];result['default']=p['id']
    return result

def save(lib,path=None):write_preference('monster_library',lib,path)

def expected(p,level):
    if type(level) is not int or p['level'] is None or p['xp'] is None or p['sp'] is None:return None
    factor=Decimal('1.1')**max(0,level-p['level'])
    return int(Decimal(p['xp'])/factor),int(Decimal(p['sp'])/factor)

def context(lib,level,solo):
    # Formula is a candidate model, not a proven rule for every server state.
    enabled=bool(lib['full_solo'] and solo and type(level) is int)
    candidates=[]
    for k in lib['active']:
        p=lib['profiles'][k];pair=expected(p,level) if enabled else None
        pairs=[list(pair)] if pair is not None else []
        if enabled:
            pairs.extend([x['xp'],x['sp']] for x in lib['learned'] if x['id']==k and x['level']==level)
        candidates.append(dict(id=k,name=p['drop']['monster'],pairs=pairs))
    default=next((dict(id=p['id'],name=p['name']) for p in candidates if p['id']==lib.get('default')),None)
    return dict(level=level,normal=enabled,candidates=candidates,default=default)

def at_context(timeline,ts):
    i=bisect_right([c['at'] for c in timeline],ts)-1
    return timeline[i]['context'] if i>=0 else dict(level=None,normal=False,candidates=[])

def reward(e):
    return e[1]=='xp' and e[2].casefold()=='you' and (e[4] is not None or e[5] is not None)

def suggestions(e,ctx):
    """Exact matches first; reduced shares are hints only, not assignments.

    The observed XP and SP must be compatible with one common fraction
    (allow one unit of truncation in both rewards). This is a heuristic,
    not a verified implementation of Reborn's damage-sharing mechanics.
    """
    xp,sp=e[4:6]
    if type(xp) is not int or type(sp) is not int or xp<=0 or sp<0:return []
    exact=[];reduced=[]
    for p in ctx.get('candidates',[]):
        if [xp,sp] in p['pairs']:
            exact.append(p['name']);continue
        for base_xp,base_sp in p['pairs']:
            if not 0<xp<base_xp or not 0<=sp<=base_sp:continue
            lo=max(Decimal(xp)/base_xp,Decimal(sp)/base_sp if base_sp else Decimal(0))
            hi=min(Decimal(xp+1)/base_xp,Decimal(sp+1)/base_sp if base_sp else Decimal(1))
            if lo<hi:
                reduced.append(p['name']+f' (~{100*xp/base_xp:.0f}% XP)');break
    return exact+reduced

def classify(e,ctx):
    xp,sp=e[4:6]
    result=dict(id=None,name=None,method='unknown',xp=xp,sp=sp,context=ctx)
    if type(xp) is int and type(sp) is int and ctx.get('normal'):
        matches=[p for p in ctx['candidates'] if [xp,sp] in p['pairs']]
        # A verified unique signature takes priority over an assumed default.
        if len(matches)==1 and all(p['pairs'] for p in ctx['candidates']):
            result.update(id=matches[0]['id'],name=matches[0]['name'],method='signature')
            return result
        if len(matches)>1:result['method']='ambiguous'
    default=ctx.get('default')
    if default and reward(e) and (type(xp) is int and xp>0 or type(sp) is int and sp>0):
        result.update(id=default['id'],name=default['name'],method='default')
    return result

def sync(events,records,timeline):
    # Indexes are stable: OCR reviews append or replace in place, never reorder.
    for i,e in enumerate(events):
        if not reward(e):continue
        key=str(i);old=records.get(key)
        if old and old['method'] in ('manual','manual_unknown'):continue
        if old and (old['xp'],old['sp'])==tuple(e[4:6]):continue
        ctx=old['context'] if old else at_context(timeline,e[0])
        records[key]=classify(e,ctx)

def assign(records,events,indices,p):
    for i in indices:
        if i<0 or i>=len(events) or not reward(events[i]):raise ValueError('Kill no longer exists.')
    for i in indices:
        e=events[i];key=str(i);old=records.get(key,{})
        records[key]=dict(id=p['id'] if p else None,name=p['drop']['monster'] if p else None,method='manual' if p else 'manual_unknown',xp=e[4],sp=e[5],context=old.get('context',dict(level=None,normal=False,candidates=[])))

def learn(lib,records,indices,p):
    # Explicit normal reward only, scoped to verified solo/full-stamina level.
    entries=[records[str(i)] for i in indices]
    keys={(e['context']['level'],e['xp'],e['sp']) for e in entries if e['context']['normal'] and type(e['xp']) is int and type(e['sp']) is int}
    if len(keys)!=1 or not all(e['context']['normal'] and (e['context']['level'],e['xp'],e['sp']) in keys for e in entries):raise ValueError('Learning requires the same complete reward and verified solo/full-stamina level for every selected kill.')
    level,xp,sp=next(iter(keys))
    if xp<=0 or sp<0:raise ValueError('Invalid reward.')
    item=dict(id=p['id'],level=level,xp=xp,sp=sp)
    if item not in lib['learned']:lib['learned'].append(item)

def counts(events,records):
    result=Counter();names={};unknown=0
    for i,e in enumerate(events):
        if not reward(e):continue
        r=records.get(str(i),{})
        if r.get('id'):
            result[r['id']]+=1;names[r['id']]=r['name']
        else:unknown+=1
    return result,names,unknown

def history_counts(parts):
    total=Counter();unknown=0
    for p in parts:
        c,n,u=counts(p['events'],p.get('monster_kills',{}))
        for k,v in c.items():total[n[k]]+=v
        unknown+=u
    return dict(counts=dict(total),unknown=unknown)

def forecasts(lib,c,seconds):
    rows=[]
    for k in lib['active']:
        p=lib['profiles'][k];rate,drops=display_drop(p['drop'],c[k],seconds)
        for name,value in drops:rows.append((p['drop']['monster']+' · '+name,value))
        if len(drops)>1:rows.append((p['drop']['monster']+' · Any selected',combined_wait(p['drop'],rate)))
    return rows
