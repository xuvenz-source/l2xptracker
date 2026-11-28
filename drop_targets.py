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
    monster='';group=None;rows=[];warnings=[]
    for line in text.splitlines():
        line=line.strip().strip('|').strip()
        m=re.search(r"([A-Za-z][\w \'-]+),?\s+Lv[.]?\s*(\d+)",line,re.I)
        if m:monster=m[1].strip().removeprefix('Q ')+' Lv.'+m[2]
        if re.search(r'item\s+group\s+chance',line,re.I):
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
        rows.append(dict(name=name,group=str(group),chance=str(ch)))
    return monster,rows,warnings

def parse_table(text):
    rows=[]
    for i,line in enumerate(text.splitlines(),1):
        if not line.strip():continue
        cols=line.split('\t')
        if len(cols)!=3 or not cols[0].strip() or len(cols[0])>120:raise ValueError(f'Row {i}: use item name, group %, item % separated by tabs.')
        rows.append(dict(name=cols[0].strip(),group=str(percent(cols[1])),chance=str(percent(cols[2]))))
    if len(rows)>150:raise ValueError('At most 150 drop rows.')
    return rows

def format_table(rows):
    return '\n'.join('\t'.join(r[k] for k in ('name','group','chance')) for r in rows)
def chance(row):return percent(row['group'])*percent(row['chance'])/10000
def estimate(row,kph):return float(Decimal(3600)/(Decimal(str(kph))*chance(row))) if kph and kph>0 else None
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
