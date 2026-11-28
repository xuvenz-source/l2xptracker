import unittest
from decimal import Decimal
from unittest.mock import patch
import numpy as np
from vitals import layout_from_regions,clean_vitals,bar_fraction,parse_pair,verified_pair,display_value
from leveling import clean_status
from hud_layout import clean,panel_config

class VitalsTests(unittest.TestCase):
    def test_layout_and_persistence(self):
        frame=dict(left=20,top=30,width=274,height=82)
        regions={'level':dict(left=23,top=6,width=18,height=17),'percent':dict(left=105,top=66,width=80,height=14)}
        v=layout_from_regions(frame,regions)
        self.assertEqual(v['bars']['hp'],dict(left=22,top=42,width=246,height=10))
        self.assertEqual(v['bars']['mp']['top'],55)
        raw=dict(binding=['game','class',800,600],regions={},vitals=v)
        self.assertEqual(clean_status(raw)['vitals'],v)
        self.assertNotIn('vitals',clean_status(dict(raw,vitals={'frame':frame,'bars':{}})))
        self.assertNotIn('vitals',clean_status(dict(binding=raw['binding'],regions={})))
    def test_bar_estimates_and_text_gaps(self):
        for k,colour,fill in [('hp',(145,81,74),219),('mp',(17,87,194),76)]:
            bar=np.zeros((10,246,3),np.uint8);bar[:,:fill]=colour
            bar[:,10:22]=(255,255,255)
            if fill>150:bar[:,100:144]=(255,255,255)
            self.assertAlmostEqual(bar_fraction(bar,k),fill/246)
            self.assertIsNone(bar_fraction(np.zeros_like(bar),k))
        bar=np.zeros((10,246,3),np.uint8);bar[:,:12]=(145,81,74);bar[:,230:]=(145,81,74)
        self.assertIsNone(bar_fraction(bar,'hp'))
    def test_numeric_confirmation_and_no_guesses(self):
        self.assertEqual(parse_pair('58 / 187'),(58,187))
        for t in ('58/0','188/187','58187','58/187/1','-1/187'):self.assertIsNone(parse_pair(t))
        self.assertEqual(verified_pair(['58/187','58/187','98/187'],.309),(58,187))
        self.assertIsNone(verified_pair(['58/187','98/187',''],.309))
        self.assertIsNone(verified_pair(['58/187','58/187','59/187'],.309))
        self.assertIsNone(verified_pair(['58/187']*3,None))
        self.assertEqual(display_value(.309,(58,187)),'58/187')
        self.assertEqual(display_value(.309),'~31%')
        self.assertEqual(display_value(None),'—')
    def test_widgets_opt_in(self):
        self.assertNotIn('hp',clean()['enabled'])
        c=clean({'enabled':['hp','mp','ad']})
        self.assertEqual(panel_config(c,'progression')['enabled'],[])
        self.assertEqual(set(panel_config(c,'vitals')['enabled']),{'hp','mp'})
        self.assertEqual(panel_config(c,'loot')['enabled'],['ad'])
