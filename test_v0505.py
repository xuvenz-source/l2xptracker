import unittest
from decimal import Decimal as D
from collections import Counter
from drop_targets import parse_ocr,parse_table,format_table,clean,chance,any_selected_probability,combined_wait
from monster_library import forecasts,profile
from test_v049 import TEXT

def config(rows,selected):
    return clean(dict(monster='Pincher',rows=rows,selected=selected,rate='120'))

class GroupTests(unittest.TestCase):
    def test_pincher_import_preserves_group_boundaries(self):
        _,rows,_=parse_ocr(TEXT)
        self.assertEqual([r['group_id'] for r in rows],[2,2,2,2,3,3,3])
        self.assertEqual(parse_table(format_table(rows)),rows)
        self.assertEqual(clean(config(rows,[0,1]))['rows'],rows)
        p=any_selected_probability(config(rows,[0,1,2]))
        self.assertEqual(p,D('2.7071')*(D('4.8116')+D('7.2255')+D('3.5945'))/10000)
    def test_different_groups_combine_independently(self):
        rows=parse_table('A\t10\t50\t1\nB\t10\t50\t1\nC\t10\t50\t2')
        self.assertEqual(any_selected_probability(config(rows,[0,1])),D('.1'))
        self.assertEqual(any_selected_probability(config(rows,[0,2])),D('.0975'))
        self.assertEqual(any_selected_probability(config(rows,[0,1,2])),D('.145'))
        self.assertEqual(chance(rows[0]),D('.05'))
    def test_equal_chance_headers_not_merged(self):
        _,rows,_=parse_ocr('Item Group Chance: 10%\nA 1 1 100%\nItem Group Chance: 10%\nB 1 1 100%')
        self.assertNotEqual(rows[0]['group_id'],rows[1]['group_id'])
        self.assertEqual(any_selected_probability(config(rows,[0,1])),D('.19'))
    def test_legacy_safe_and_validated(self):
        rows=parse_table('A\t10\t50\nB\t10\t50')
        c=config(rows,[0,1]);self.assertIsNone(any_selected_probability(c))
        self.assertEqual(combined_wait(c,120),'Verify groups')
        self.assertEqual(any_selected_probability(config(rows,[0])),D('.05'))
        for table in ('A\t10\t50\t1\nB\t20\t50\t1','A\t10\t60\t1\nB\t10\t60\t1','A\t10\t50\t0'):
            with self.assertRaises(ValueError):parse_table(table)
    def test_rounding_and_monster_forecast(self):
        rows=parse_table('A\t100\t50.01\t1\nB\t100\t50.01\t1')
        c=config(rows,[0,1]);self.assertEqual(any_selected_probability(c),D(1))
        p=profile(c,16,471,19);lib=dict(profiles={p['id']:p},active=[p['id']])
        result=forecasts(lib,Counter(),3600)
        self.assertEqual(result[-1],('Pincher Lv.16 · Any selected','30s'))
        self.assertEqual(len(result),3)
