"""Party roster and reporting. Estimates never become recorded loot events."""
import re
from collections import Counter

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
    if len(names)>8:
        raise ValueError('Enter at most eight other party members.')
    return names

def report(parts):
    """Each part is one original session; never estimate for an unknown roster."""
    observed=Counter(); estimates=Counter(); coverage=Counter(); names={}
    total_estimate=0; configured_seconds=0; configured_count=0
    for part in parts:
        members=roster(','.join(part.get('party_members',[])))
        for name in members:
            names.setdefault(name.casefold(),name)
        own=0
        for ts,typ,who,item,q,sp,raw in part['events']:
            if typ=='adena' and q is not None:
                key=who.casefold()
                if key=='you': own+=q
                else:
                    names.setdefault(key,who); observed[key]+=q
        if members:
            seconds=max(0,part['seconds'])
            configured_seconds+=seconds; configured_count+=1
            total_estimate+=own*(1+len(members))
            for name in members:
                key=name.casefold(); estimates[key]+=own; coverage[key]+=seconds
    rows=[dict(name=name,observed=observed[key],
               estimate=estimates[key] if key in estimates else None,
               seconds=coverage[key]) for key,name in sorted(names.items())]
    return dict(rows=rows,estimated_party=total_estimate if configured_count else None,
                seconds=configured_seconds,configured_count=configured_count)

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
    return f'Estimated whole-party Adena: {total:,} ({rate}); configured sessions only. Assumes equal shares; do not add to observed loot.'
