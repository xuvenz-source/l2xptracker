"""Party roster and reporting. Estimates never become recorded loot events."""
import re
from collections import Counter
from bisect import bisect_right
from preferences import read_preferences,write_preference

MAX_MEMBERS=11

def roster(text):
    names=[]
    seen={'you'}
    for part in text.split(','):
        name=part.strip()
        if not name: continue
        if not re.fullmatch(r'[\w-]{1,40}',name):
            raise ValueError('Enter character names separated by commas.')
        key=name.casefold()
        if key not in seen:
            seen.add(key); names.append(name)
    if len(names)>MAX_MEMBERS:
        raise ValueError('Enter at most 11 other party members.')
    return names

def saved_names(raw):
    """Normalize a contact library without imposing the active roster limit."""
    names={}
    if isinstance(raw,list):
        for name in raw:
            if isinstance(name,str):
                name=name.strip()
                if name.casefold()!='you' and re.fullmatch(r'[\w-]{1,40}',name):
                    names.setdefault(name.casefold(),name)
    return list(names.values())

def load_party_choices(path=None):
    prefs=read_preferences(path)
    if isinstance(prefs.get('party_contacts'),list):
        return sorted(saved_names(prefs['party_contacts']),key=str.casefold)
    # Migrate names, not whole party presets. Keep old stored presets intact.
    old=prefs.get('party_presets',{})
    names=[name for members in old.values() if isinstance(members,list) for name in members] if isinstance(old,dict) else []
    return sorted(saved_names(names),key=str.casefold)

def load_current_party(path=None):
    raw=read_preferences(path).get('current_party',[])
    return saved_names(raw)[:MAX_MEMBERS]

def remember_party(members,path=None):
    members=roster(','.join(members))
    choices=sorted(saved_names(members+load_party_choices(path)),key=str.casefold)
    # One atomic write for both values, using a single preference record.
    from preferences import write_preferences
    write_preferences({'party_contacts':choices,'current_party':members},path)
    return choices

def periods_for(part):
    """Older sessions keep their original fixed-roster interpretation."""
    raw=part.get('party_periods')
    if not raw:return [dict(at='',seconds=0,members=roster(','.join(part.get('party_members',[]))))]
    return raw

def report(parts):
    """Account for roster membership at capture time, including late reviews."""
    observed=Counter(); estimates=Counter(); coverage=Counter(); names={}
    total_estimate=0; configured_seconds=0; configured_count=0
    for part in parts:
        periods=periods_for(part)
        boundaries=[p['at'] for p in periods]
        seconds=max(0,part['seconds']);own=Counter(); configured=False
        for ts,typ,who,item,q,sp,raw in part['events']:
            if typ!='adena' or q is None:continue
            key=who.casefold()
            if key=='you':
                # Timestamp preserved from capture even if OCR/review completes later.
                own[max(0,bisect_right(boundaries,ts)-1)]+=q
            else:
                names.setdefault(key,who); observed[key]+=q
        for i,period in enumerate(periods):
            members=roster(','.join(period['members']))
            if not members:continue
            start=max(0,min(seconds,period['seconds']))
            end=max(start,min(seconds,periods[i+1]['seconds'])) if i+1<len(periods) else seconds
            elapsed=end-start
            configured=True;configured_seconds+=elapsed
            total_estimate+=own[i]*(1+len(members))
            for name in members:
                key=name.casefold();names.setdefault(key,name)
                estimates[key]+=own[i];coverage[key]+=elapsed
        configured_count+=int(configured)
    rows=[dict(name=name,observed=observed[key],
               estimate=estimates[key] if key in estimates else None,
               seconds=coverage[key]) for key,name in sorted(names.items())]
    return dict(rows=rows,estimated_party=total_estimate if configured_count else None,
                seconds=configured_seconds,configured_count=configured_count)

def live_report(members,seconds,totals):
    # The UI already has aggregated counters: avoid scanning all events on every tick.
    events=[('', 'adena', who, item, q, 0, '') for (who,item),q in totals.items() if item=='Adena']
    return report([dict(party_members=members,seconds=seconds,events=events)])

def display_rows(data):
    for row in data['rows']:
        if row['estimate'] is None: continue
        yield (row['name'],'Adena (equal-share estimate)',f"{row['estimate']:,}")
        if row['seconds']>0:
            yield (row['name'],'Adena/hr (estimated)',f"{row['estimate']*3600/row['seconds']:,.0f}")

def summary_text(data):
    if data['estimated_party'] is None: return ''
    seconds=data['seconds']; total=data['estimated_party']
    rate=f'{total*3600/seconds:,.0f}/h' if seconds else '—/h'
    return f'Estimated whole-party Adena: {total:,} ({rate}); configured party periods only. Assumes equal shares; do not add to observed loot.'
