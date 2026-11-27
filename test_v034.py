import unittest,tempfile,csv
from pathlib import Path
from decimal import Decimal
from consumable_costs import price,load_prices,save_prices,cost_report,cost_summary,write_cost_csv
from history import Archive
from test_v016 import data

def used(name,q=1):return ('t','consumable','You',name,q,0,'Use '+name)

class ConsumableCostsTests(unittest.TestCase):
    def test_prices(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prefs.json'
            self.assertEqual(load_prices(p),{})
            save_prices({' Soulshot: No Grade ':'2.50','Potion':'0'},p)
            self.assertEqual(load_prices(p),{'soulshot: no grade':'2.5','potion':'0'})
        for value in ('-1','NaN','1e5','0.00001',''):
            with self.assertRaises(ValueError):price(value)
    def test_missing_zero_and_decimal(self):
        part=dict(events=[used('Soulshot: No Grade',4),used('Potion',2),used('Scroll',3)],consumable_prices={'soulshot: no grade':'2.5','potion':'0'})
        r=cost_report([part]);self.assertEqual(r['cost'],Decimal(10));self.assertEqual(r['unpriced'],3)
        self.assertIn('3 unpriced uses',cost_summary(r,100,3600))
        self.assertIn('90',cost_summary(r,100,3600))
    def test_archive_merge_independent_prices(self):
        with tempfile.TemporaryDirectory() as d:
            a=Archive(Path(d)/'sessions.sqlite3')
            x=data(3600,100,200);y=data(3600,100,200)
            x['events'].append(used('Shot',5));x['consumable_prices']={'shot':'2'}
            y['events'].append(used('shot',3));y['consumable_prices']={'shot':'4'}
            a.save('x','First',x);a.save('y','Second',y)
            m=a.merge(['x','y'],'Both');r=a.summary(m)['consumable_report']
            self.assertEqual(r['cost'],Decimal(22));self.assertEqual(r['rows'][0]['uses'],8)
            self.assertEqual(r['rows'][0]['prices'],{Decimal(2),Decimal(4)})
            x['consumable_prices']={'shot':'3'};a.save('x','First',x)
            self.assertEqual(a.summary(m)['consumable_report']['cost'],Decimal(27))
            p=Path(d)/'costs.csv';write_cost_csv(p,r)
            with p.open(encoding='utf-8-sig') as f:row=list(csv.DictReader(f))[0]
            self.assertEqual(row['known_cost_adena'],'22')
    def test_legacy_no_prices(self):
        r=cost_report([dict(events=[used('Shot',2)])])
        self.assertEqual(r['unpriced'],2);self.assertEqual(r['cost'],0)
