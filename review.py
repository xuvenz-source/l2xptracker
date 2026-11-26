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

class ReviewQueue:
    def __init__(self):
        self.pending = {}
        self.next_id = 1
    def add(self, timestamp, text, event_index=None, xp_counted=None, sp_counted=None):
        r = Review(self.next_id, timestamp, text, event_index, xp_counted, sp_counted)
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
            raise ValueError('Enter a complete XP/SP, Adena or item acquisition message.')
        typ, who, item, qty, sp = event
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
            totals[(who,item)] += qty
            if typ == 'xp': totals[(who,'SP')] += sp
        del self.pending[id]
        return r

def candidates(r, parse, xp_numeric_candidate):
    """Extract only observed values. Never infer an unreadable quantity."""
    out=[]
    def add(s):
        e=parse(s)
        if e and (r.xp_counted is None or (e[0]=='xp' and e[3]==r.xp_counted)) and (r.sp_counted is None or (e[0]=='xp' and e[4]==r.sp_counted)) and s not in out:
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
