import csv,tempfile,unittest
from decimal import Decimal
from pathlib import Path
from loot_values import load_loot_prices,save_loot_prices,loot_report,loot_summary,write_loot_csv,unit_label
from consumable_costs import save_prices,load_prices
from history import Archive
from test_v016 import data

def drop(item,qty=1,who='You'):
    return ('t','item',who,item,qty,0,'loot')

class LootValuesTests(unittest.TestCase):
    def test_preferences_separate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prefs.json'
            save_prices({'shot':'5'},p);save_loot_prices({' Suede ':'50.5','Stem':'0'},p)
            self.assertEqual(load_loot_prices(p),{'suede':'50.5','stem':'0'})
            self.assertEqual(load_prices(p),{'shot':'5'})
    def test_quantity_party_and_non_items(self):
        r=loot_report([dict(events=[drop('Suede',4),drop('Suede',3,'Other'),drop('Unknown',2),drop('Stem',1),('t','adena','You','Adena',1000,0,'cash'),('t','consumable','You','Suede',5,0,'use')],loot_prices={'suede':'50.5','stem':'0'})])
        self.assertEqual(r['value'],Decimal('202'));self.assertEqual(r['party_value'],Decimal('151.5'));self.assertEqual(r['unpriced'],2)
        self.assertIn('404/h',loot_summary(r,1800))
        self.assertEqual(len(r['rows']),4)
    def test_merged_prices_and_legacy(self):
        with tempfile.TemporaryDirectory() as d:
            a=Archive(Path(d)/'db.sqlite')
            x=data(3600,100,200);y=data(1800,100,300)
            x['events'].append(drop('Suede',3));x['loot_prices']={'suede':'50'}
            y['events'].append(drop('Suede',2));y['loot_prices']={'suede':'60'}
            a.save('x','X',x);a.save('y','Y',y);m=a.merge(['x','y'],'Both')
            s=a.summary(m);self.assertEqual(s['totals']['You','Adena'],500)
            r=s['loot_report'];self.assertEqual(r['value'],270)
            row=next(row for row in r['rows'] if row['who']=='You')
            self.assertEqual(unit_label(row),'Mixed')
            p=Path(d)/'loot.csv';write_loot_csv(p,r)
            with p.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
            self.assertEqual(next(row for row in rows if row['player']=='You')['estimated_sale_value'],'270')
            y.pop('loot_prices');a.save('y','Y',y)
            r=a.summary(m)['loot_report'];self.assertEqual(r['value'],150);self.assertEqual(r['unpriced'],2)
