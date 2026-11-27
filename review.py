"""Session-local manual OCR review; no capture or game access."""
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class Review:
    id: int
    timestamp: str
    text: str
    event_index: int | None = None
    xp_counted: int | None = None
    sp_counted: int | None = None
    category: str | None = None

class ReviewQueue:
    def __init__(self):
        self.pending = {}
        self.next_id = 1
    def add(self, timestamp, text, event_index=None, xp_counted=None, sp_counted=None, category=None):
        r = Review(self.next_id, timestamp, text, event_index, xp_counted, sp_counted, category)
        self.next_id += 1
        self.pending[r.id] = r
        return r
    def discard(self, id):
        return self.pending.pop(id, None)
    def approve(self, id, corrected, parse, events, totals):
        r = self.pending.get(id)
        if r is None:
            raise ValueError('This review has already been resolved.')
        event = parse(corrected)
        if not event:
            raise ValueError('Enter a complete XP/SP, Adena, item acquisition or consumable usage message.')
        typ, who, item, qty, sp = event
        category=effective_category(r,parse)
        if category and typ!=category:
            raise ValueError('Correct the message using its detected colour category.')
        if qty <= 0 or (typ == 'xp' and (sp is None or sp < 0)):
            raise ValueError('Quantity or XP must be positive; SP must be zero or greater.')
        if r.event_index is not None:
            if typ != 'xp' or who != 'You':
                raise ValueError('Enter a complete XP/SP message for this partial event.')
            if r.xp_counted is not None and qty != r.xp_counted:
                raise ValueError(f'{r.xp_counted} XP was already counted. Keep that XP value and enter the correct SP.')
            if r.sp_counted is not None and sp != r.sp_counted:
                raise ValueError(f'{r.sp_counted} SP was already counted. Keep that SP value and enter the correct XP.')
            old = events[r.event_index]
            if old[1:6] != ('xp','You','XP / SP',r.xp_counted,r.sp_counted):
                raise ValueError('The original partial event is no longer available.')
            events[r.event_index] = (r.timestamp,typ,who,item,qty,sp,corrected)
            if r.xp_counted is None: totals[(who,item)] += qty
            if r.sp_counted is None: totals[(who,'SP')] += sp
        else:
            events.append((r.timestamp,typ,who,item,qty,sp,corrected))
            if typ!='consumable':totals[(who,item)] += qty
            if typ == 'xp': totals[(who,'SP')] += sp
        del self.pending[id]
        return r

def effective_category(r,parse):
    # Older versions classified earned quest items as Adena based on colour.
    # Reclassify only if the saved OCR evidence actually parses as an item.
    if r.category!='adena':return r.category
    first,_,tail=r.text.partition(' [')
    parts=[first]
    if tail:
        _,_,rest=tail.rstrip(']').partition(': ')
        parts.extend(rest.split(' | '))
    events=[e for t in parts if (e:=parse(t.strip()))]
    kinds={e[0] for e in events}
    if kinds=={'item'} and any(re.search(r'\b(?:earned|eamed)\b',t,re.I) for t in parts):return 'item'
    if kinds=={'item','adena'}:return None
    return r.category

def candidates(r, parse, xp_numeric_candidate):
    """Extract only observed values. Never infer an unreadable quantity."""
    out=[];category=effective_category(r,parse)
    def add(s):
        e=parse(s)
        if e and (not category or e[0]==category) and (r.xp_counted is None or (e[0]=='xp' and e[3]==r.xp_counted)) and (r.sp_counted is None or (e[0]=='xp' and e[4]==r.sp_counted)) and s not in out:
            out.append(s)
    first, _, tail=r.text.partition(' [')
    parts=[first]
    if tail:
        _,_,rest=tail.rstrip(']').partition(': ')
        parts.extend(rest.split(' | '))
    for t in parts:
        t=t.strip()
        pair=xp_numeric_candidate(t)
        if pair: add(f'You have acquired {pair[0]} XP and {pair[1]} SP.')
        e=parse(t)
        if e:
            typ,who,item,q,sp=e
            if typ=='adena' and who=='You': add(f'You have earned {q} Adena.')
            elif typ=='xp': add(f'You have acquired {q} XP and {sp} SP.')
            else: add(t)
        if tail.startswith('numeric OCR:') and re.fullmatch(r'[0-9]+',t):
            add(f'You have earned {int(t)} Adena.')
    return out


def review_fields(r, parse, xp_numeric_candidate):
    """Prefill only unambiguous evidence; locked partial values always win."""
    opts=candidates(r,parse,xp_numeric_candidate)
    events=[parse(s) for s in opts]
    events=[e for e in events if e]
    kinds={e[0] for e in events}
    first=r.text.split(' [',1)[0]
    if r.event_index is not None:
        kind='xp'
    elif effective_category(r,parse):
        kind=effective_category(r,parse)
    elif len(kinds)==1:
        kind=next(iter(kinds))
    elif len(kinds)>1:
        kind=''
    elif re.search(r'\b(?:XP|SP)\b|\bacquired\b|\[XP retry:',r.text,re.I):
        kind='xp'
    elif re.search(r'\bAdena\b|\b(?:earned|eamed)\b',first,re.I):
        kind='adena'
    elif re.search(r'\bobtained\b',first,re.I):
        kind='item'
    else:
        kind=''
    def agree(values):
        vals=set(values)
        return str(next(iter(vals))) if len(vals)==1 else ''
    xp=[e for e in events if e[0]=='xp']
    ad=[e for e in events if e[0]=='adena']
    # Preserve a named recipient; never silently assign a party drop to You.
    who=agree(e[1] for e in ad)
    if not ad:
        m=re.match(r'([\w-]+) has (?:earned|eamed|obtained)\b',first,re.I)
        who=m[1] if m else ('You' if re.match(r'You\b',first,re.I) else '')
    return dict(kind=kind,xp=str(r.xp_counted) if r.xp_counted is not None else agree(e[3] for e in xp),
                sp=str(r.sp_counted) if r.sp_counted is not None else agree(e[4] for e in xp),
                adena=agree(e[3] for e in ad),who=who,
                full=opts[0] if len(opts)==1 else '',options=opts)

def numeric_field(value,label,allow_zero=False):
    value=value.strip()
    if not re.fullmatch(r'(?:[0-9]{1,15}|[0-9]{1,3}(?:,[0-9]{3}){1,4})',value):
        raise ValueError(f'Enter a whole number for {label}.')
    n=int(value.replace(',',''))
    if n==0 and not allow_zero:raise ValueError(f'{label} must be greater than zero.')
    return n

def correction_message(r,kind,xp='',sp='',adena='',who='',full=''):
    if r.event_index is not None and kind!='xp':
        raise ValueError('This partially counted message must remain XP / SP.')
    if kind=='xp':
        x=r.xp_counted if r.xp_counted is not None else numeric_field(xp,'XP')
        s=r.sp_counted if r.sp_counted is not None else numeric_field(sp,'SP',True)
        return f'You have acquired {x} XP and {s} SP.'
    if kind=='adena':
        n=numeric_field(adena,'Adena')
        who=who.strip()
        if not re.fullmatch(r'[\w-]{1,40}',who):
            raise ValueError('Confirm the recipient: You or a character name.')
        prefix='You have' if who.casefold()=='you' else who+' has'
        return f'{prefix} earned {n} Adena.'
    if kind in ('item','consumable'):return full.strip()
    raise ValueError('Select XP / SP, Adena, Item or Consumable.')
