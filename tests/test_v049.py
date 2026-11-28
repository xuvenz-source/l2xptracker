import unittest
from decimal import Decimal
from drop_targets import parse_ocr,parse_table,format_table,chance,estimate,display,clean
from hud_layout import panel_config,geometry,WIDGETS,PROGRESSION,LOOT
from hud_pair import HudPair
from unittest.mock import Mock
TEXT="""Q Pincher, Lv.16
EXP: 471 SP: 19
* Item Group Chance: 70.0%.
Adena 97 151 100.0%
* Item Group Chance: 2.7071%.
Cat's Eye Earring 1 1 4.8116%
Ring of Wisdom iL 1 7.2255%
Necklace of Wisdom 1 1 3.5945%
Necklace of Wisdom Chain 1 1 84.3684%
* Item Group Chance: 6.0526%.
Thread 1 1 63.7725%
Suede 1 1 21.2575%
Recipe: Blue Diamond Necklace 1 1 14.97%"""
class DropTests(unittest.TestCase):
    def test_pincher_import(self):
        monster,rows,warnings=parse_ocr(TEXT)
        self.assertEqual(monster,'Pincher Lv.16');self.assertEqual(len(rows),7)
        self.assertTrue(warnings);self.assertEqual(rows[1]['name'],'Ring of Wisdom')
        self.assertEqual(chance(rows[0]),Decimal('2.7071')*Decimal('4.8116')/10000)
        self.assertEqual(parse_table(format_table(rows)),rows)
    def test_forecasts_individual_and_override(self):
        monster,rows,_=parse_ocr(TEXT)
        c=clean(dict(monster=monster,rows=rows,selected=[0,2],rate='120'))
        rate,result=display(c,0,0);self.assertEqual(rate,120);self.assertEqual(len(result),2)
        self.assertAlmostEqual(estimate(rows[0],120),3600/(120*float(chance(rows[0]))))
        c['rate']='';self.assertEqual(display(c,0,0)[1][0][1],'Calc…')
        self.assertEqual(display(c,10,300)[0],120)
    def test_bad_percent_not_confirmed(self):
        for t in ('Item\t0\t5','Item\t101\t5','Item\t2\tNaN','Item\t2\t7/'):
            with self.assertRaises(ValueError):parse_table(t)
    def test_panel_partition_and_geometry(self):
        c=dict(enabled=list(WIDGETS),widgets_per_row=2)
        p=panel_config(c,'progression');l=panel_config(c,'loot')
        self.assertEqual(set(p['enabled']),set(PROGRESSION));self.assertEqual(set(l['enabled']),set(LOOT))
        g=geometry(l,'ADENA / LOOT',3)
        self.assertGreaterEqual(g['height'],g['detail_y']+63)
        self.assertEqual(g['details'],3)
    def test_pair_applies_separate_configs(self):
        p,l=Mock(),Mock();h=HudPair(p,l);h.configure_layout(dict(enabled=['xp','ad']))
        self.assertEqual(p.configure_layout.call_args.args[0]['enabled'],['xp'])
        self.assertEqual(l.configure_layout.call_args.args[0]['enabled'],['ad'])
        h.set_targets('Pincher',[('Ring','5h')]);self.assertEqual(l.detail_rows,[('Ring','5h')])
        h.hide();p.hide.assert_called_once();l.hide.assert_called_once()
