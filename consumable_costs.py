"""Manual Adena cost per observed consumable activation, with session snapshots."""
from decimal import Decimal
import re,csv
from collections import Counter
from pathlib import Path
from preferences import read_preferences,write_preference

def key(name):
    return ' '.join(name.split()).casefold()

def price(value):
    value=str(value).strip()
    if not re.fullmatch(r'[0-9]{1,12}(?:\.[0-9]{1,4})?',value):
        raise ValueError('Enter a non-negative Adena cost (up to four decimal places), or leave blank to remove it.')
    return format(Decimal(value).normalize(),'f')

def clean_prices(value):
    result={}
    if isinstance(value,dict):
        for name,cost in value.items():
            if not isinstance(name,str) or not key(name):continue
            try:result[key(name)]=price(cost)
            except ValueError:continue
    return result

def load_prices(path=None):
    return clean_prices(read_preferences(path).get('consumable_prices',{}))

def save_prices(prices,path=None):
    write_preference('consumable_prices',clean_prices(prices),path)

def cost_report(parts):
    """Price each original independently. Missing price is not a zero price."""
    rows={}
    for part in parts:
        prices=clean_prices(part.get('consumable_prices',{}))
        for _,typ,_,item,qty,_,_ in part.get('events',[]):
            if typ!='consumable' or qty is None or qty<=0:continue
            k=key(item)
            row=rows.setdefault(k,dict(item=item,uses=0,priced=0,unpriced=0,cost=Decimal(0),prices=set()))
            row['uses']+=qty
            if k in prices:
                unit=Decimal(prices[k]);row['priced']+=qty;row['cost']+=unit*qty;row['prices'].add(unit)
            else:row['unpriced']+=qty
    out=sorted(rows.values(),key=lambda r:r['item'].casefold())
    return dict(rows=out,cost=sum((r['cost'] for r in out),Decimal(0)),unpriced=sum(r['unpriced'] for r in out))

def money(value):
    return format(value,',.4f').rstrip('0').rstrip('.') if isinstance(value,Decimal) else f'{value:,}'

def cost_summary(report,adena,seconds):
    cost=report['cost']; missing=report['unpriced']
    hourly=f'{cost*Decimal(3600)/Decimal(str(seconds)):,.0f}' if seconds>0 else '—'
    net=Decimal(adena)-cost
    net_hr=f'{net*Decimal(3600)/Decimal(str(seconds)):,.0f}' if seconds>0 else '—'
    return f'Known consumable cost: {money(cost)} Adena ({hourly}/h)  |  Adena after known costs: {money(net)} ({net_hr}/h)'+(f'  |  {missing:,} unpriced uses' if missing else '')

def write_cost_csv(path,report):
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['consumable','observed_activations','priced_activations','unpriced_activations','adena_per_activation','known_cost_adena'])
        for r in report['rows']:
            w.writerow([r['item'],r['uses'],r['priced'],r['unpriced'],' / '.join(format(x,'f') for x in sorted(r['prices'])),format(r['cost'],'f')])
