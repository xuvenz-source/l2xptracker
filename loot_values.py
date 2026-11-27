"""Manual per-unit sale estimates. Never add estimates to observed cash totals."""
from decimal import Decimal
import csv
from consumable_costs import key,clean_prices,money
from preferences import read_preferences,write_preference

def load_loot_prices(path=None):
    return clean_prices(read_preferences(path).get('loot_prices',{}))

def save_loot_prices(prices,path=None):
    write_preference('loot_prices',clean_prices(prices),path)

def loot_report(parts):
    rows={}
    for part in parts:
        prices=clean_prices(part.get('loot_prices',{}))
        for _,typ,who,item,qty,_,_ in part.get('events',[]):
            if typ!='item' or qty is None or qty<=0:continue
            r=rows.setdefault((who,item),dict(who=who,item=item,qty=0,priced=0,unpriced=0,value=Decimal(0),prices=set()))
            r['qty']+=qty
            k=key(item)
            if k in prices:
                unit=Decimal(prices[k]);r['priced']+=qty;r['value']+=unit*qty;r['prices'].add(unit)
            else:r['unpriced']+=qty
    out=sorted(rows.values(),key=lambda r:(r['who'].casefold(),r['item'].casefold()))
    personal=[r for r in out if r['who'].casefold()=='you']
    party=[r for r in out if r['who'].casefold()!='you']
    return dict(rows=out,value=sum((r['value'] for r in personal),Decimal(0)),
                unpriced=sum(r['unpriced'] for r in personal),
                party_value=sum((r['value'] for r in party),Decimal(0)),
                party_unpriced=sum(r['unpriced'] for r in party))

def unit_label(row):
    if not row['prices']:return 'Not set'
    return money(next(iter(row['prices']))) if len(row['prices'])==1 else 'Mixed'

def loot_summary(report,seconds):
    value=report['value']
    hourly=f'{value*3600/Decimal(str(seconds)):,.0f}' if seconds>0 else '—'
    return f"Personal estimated loot value: {money(value)} Adena ({hourly}/h)"+(f"  |  {report['unpriced']:,} unpriced items" if report['unpriced'] else '')+(f"  |  Other players: {money(report['party_value'])} estimated" if report['party_value'] or report['party_unpriced'] else '')

def write_loot_csv(path,report):
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['player','item','quantity','priced_quantity','unpriced_quantity','adena_per_unit','estimated_sale_value'])
        for r in report['rows']:
            w.writerow([r['who'],r['item'],r['qty'],r['priced'],r['unpriced'],' / '.join(format(x,'f') for x in sorted(r['prices'])),format(r['value'],'f')])
