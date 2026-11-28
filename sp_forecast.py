"""Session-only SP estimates based on confirmed paired XP/SP observations."""
from decimal import Decimal, ROUND_HALF_UP
import re

def parse_balance(text):
    text=text.strip()
    if not re.fullmatch(r'(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)',text) or len(text.replace(',',''))>18:
        raise ValueError('Enter your current SP as a non-negative whole number.')
    return int(text.replace(',',''))

def clean_anchor(raw):
    if not isinstance(raw,dict) or type(raw.get('balance')) is not int or not 0<=raw['balance']<10**18 or not isinstance(raw.get('at'),str):return None
    return dict(balance=raw['balance'],at=raw['at'])

def reward_stats(events,anchor=None):
    anchor=clean_anchor(anchor)
    kills=sample=xp_sum=sp_sum=earned=after=unknown=0
    for ts,typ,who,_,xp,sp,_ in events:
        if typ!='xp' or who.casefold()!='you':continue
        if xp is not None or sp is not None:kills+=1
        if type(sp) is int and sp>=0:earned+=sp
        if type(xp) is int and xp>0 and type(sp) is int and sp>=0:
            sample+=1;xp_sum+=xp;sp_sum+=sp
        if anchor is not None and ts>anchor['at']:
            if type(sp) is int and sp>=0:after+=sp
            else:unknown+=1
    return dict(kills=kills,sample=sample,xp=xp_sum,sp=sp_sum,earned=earned,
                average_xp=Decimal(xp_sum)/sample if sample else None,
                average_sp=Decimal(sp_sum)/sample if sample else None,
                current=anchor['balance']+after if anchor is not None else None,unknown=unknown)

def project(stats,remaining,at_cap=False):
    """Use the unrounded expected kill count; round SP only for display."""
    if at_cap or remaining is None or not stats['sample'] or stats['xp']<=0:return None
    remaining=max(0,int(remaining))
    kills=(remaining*stats['sample']+stats['xp']-1)//stats['xp']
    gain=int((Decimal(remaining)*stats['sp']/stats['xp']).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    return dict(kills=kills,gain=gain,total=None if stats['current'] is None else stats['current']+gain)
