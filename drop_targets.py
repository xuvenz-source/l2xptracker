"""User-confirmed drop probabilities and expected waiting times."""
from decimal import Decimal,InvalidOperation
import re,math
from preferences import read_preferences,write_preference

def percent(value):
    try:v=Decimal(str(value).strip().removesuffix('%'))
    except InvalidOperation:raise ValueError('Invalid percentage')
    if not v.is_finite() or not 0<v<=100:raise ValueError('Percentage must be above zero and at most 100.')
    return v

def parse_ocr(text):
    monster='';group=None;group_id=0;rows=[];warnings=[]
    for line in text.splitlines():
        line=line.strip().strip('|').strip()
        m=re.search(r"([A-Za-z][\w \'-]+),?\s+Lv[.]?\s*(\d+)",line,re.I)
        if m:monster=m[1].strip().removeprefix('Q ')+' Lv.'+m[2]
        if re.search(r'item\s+group\s+chance',line,re.I):
            group_id+=1
            m=re.search(r'(\d+(?:\.\d+)?)\s*%',line)
            try:group=percent(m[1]) if m else None
            except ValueError:group=None
            if group is None:warnings.append('Unreadable group: '+line)
            continue
        if group is None or '%' not in line:continue
        m=re.fullmatch(r"(.+?)\s+(\S+)\s+(\S+)\s+(\d+(?:\.\d+)?)\s*%[.\s|]*",line)
        if not m:warnings.append('Skipped row: '+line);continue
        name=m[1].strip(' |')
        if name.casefold()=='adena':continue
        try:ch=percent(m[4])
        except ValueError:warnings.append('Invalid chance: '+line);continue
        if not m[2].isdigit() or not m[3].isdigit():warnings.append('Quantity unreadable (not used for ETA): '+line)
        rows.append(dict(name=name,group=str(group),chance=str(ch),group_id=group_id))
    return monster,rows,warnings

def parse_table(text):
    rows=[]
    for i,line in enumerate(text.splitlines(),1):
        if not line.strip():continue
        cols=line.split('\t')
        if len(cols) not in (3,4) or not cols[0].strip() or len(cols[0])>120:raise ValueError(f'Row {i}: use item name, group %, item %, optional group number, separated by tabs.')
        row=dict(name=cols[0].strip(),group=str(percent(cols[1])),chance=str(percent(cols[2])))
        if len(cols)==4 and cols[3].strip():
            gid=cols[3].strip()
            if not re.fullmatch(r'[0-9]{1,4}',gid) or not 1<=int(gid)<=9999:raise ValueError(f'Row {i}: group number must be 1–9999.')
            row['group_id']=int(gid)
        rows.append(row)
    if len(rows)>150:raise ValueError('At most 150 drop rows.')
    # Distinct groups can have identical group probabilities; never infer
    # group identity from those percentages. Legacy rows remain ungrouped.
    groups={}
    for r in rows:
        gid=r.get('group_id')
        if gid is None:continue
        g,p=percent(r['group']),percent(r['chance'])
        old,total=groups.get(gid,(g,Decimal(0)))
        if old!=g:raise ValueError(f'Group {gid}: all rows must have the same group chance.')
        total+=p
        if total>Decimal('100.05'):raise ValueError(f'Group {gid}: conditional item chances exceed 100% (check OCR or group numbers).')
        groups[gid]=(g,total)
    return rows

def format_table(rows):
    return '\n'.join('\t'.join(r[k] for k in ('name','group','chance'))+('\t'+str(r['group_id']) if r.get('group_id') is not None else '') for r in rows)
def chance(row):return percent(row['group'])*percent(row['chance'])/10000
def wait_for_probability(p,kph):
    return float(Decimal(3600)/(Decimal(str(kph))*p)) if p and kph and kph>0 else None

def estimate(row,kph):return wait_for_probability(chance(row),kph)

def any_selected_probability(config):
    """Probability of >=1 selected drop on a kill.

    One weighted choice per successful group; groups roll independently.
    Return None for missing group identity instead of guessing from rates.
    """
    rows=[config['rows'][i] for i in dict.fromkeys(config['selected'])]
    if not rows:return Decimal(0)
    if len(rows)==1:return chance(rows[0])
    if any(r.get('group_id') is None for r in rows):return None
    groups={}
    for r in rows:
        gid=r['group_id'];g,p=percent(r['group']),percent(r['chance'])
        old,total=groups.get(gid,(g,Decimal(0)))
        if old!=g:return None
        total+=p
        if total>Decimal('100.05'):return None
        groups[gid]=(g,total)
    miss=Decimal(1)
    for g,total in groups.values():
        miss*=1-g*min(Decimal(100),total)/10000
    return 1-miss

def combined_wait(config,kph):
    p=any_selected_probability(config)
    if p is None:return 'Verify groups'
    return time_label(wait_for_probability(p,kph))
def time_label(seconds):
    if seconds is None:return 'Calc…'
    if seconds<60:return f'{math.ceil(seconds)}s'
    minutes=math.ceil(seconds/60);h,m=divmod(minutes,60);d,h=divmod(h,24)
    return f'{d}d {h}h' if d else f'{h}h {m:02}m' if h else f'{m}m'
def clean(raw):
    try:
        if not isinstance(raw,dict):raise ValueError()
        rows=parse_table(format_table(raw.get('rows',[])))
        selected=list(dict.fromkeys(i for i in raw.get('selected',[]) if type(i) is int and 0<=i<len(rows)))[:12]
        rate=raw.get('rate','')
        if rate!='':
            r=Decimal(str(rate))
            if not r.is_finite() or not 0<r<=100000:raise ValueError()
            rate=str(r)
        return dict(monster=str(raw.get('monster',''))[:120],rows=rows,selected=selected,rate=rate)
    except (ValueError,TypeError,KeyError,InvalidOperation):return dict(monster='',rows=[],selected=[],rate='')
def load(path=None):return clean(read_preferences(path).get('drop_targets'))
def save(config,path=None):write_preference('drop_targets',clean(config),path)
def display(config,kills,seconds):
    rate=float(config['rate']) if config['rate'] else kills*3600/seconds if seconds>=30 and kills else 0
    return rate,[(config['rows'][i]['name'],time_label(estimate(config['rows'][i],rate))) for i in config['selected']]
