import unittest,tempfile
from pathlib import Path
from decimal import Decimal
from leveling import XP,TOTAL,eta,Progress,parse_number,absolute_xp
from hud_layout import geometry,clean,load,save
from hud import safe_position

class LevelingTests(unittest.TestCase):
    def test_level19_user_calibration(self):
        self.assertEqual(XP[18],160266)
        self.assertEqual(TOTAL[18],675596)
        p=Progress();p.manual(19,'18.89',0);p.advance(353,60)
        self.assertEqual(round(p.percent,2),Decimal('19.11'))
    def test_manual_level_up_and_reset(self):
        p=Progress();p.manual(19,'99.90',0);p.advance(500,60);self.assertEqual(p.level,20)
        old=p.percent;p.rebase(500,60);p.advance(0,60);self.assertEqual(p.percent,old)
    def test_ocr_confirmation(self):
        p=Progress();self.assertFalse(p.observe(19,Decimal('16.91'),60,1))
        self.assertTrue(p.observe(19,Decimal('16.92'),60,2))
        self.assertFalse(p.observe(20,Decimal('0.1'),60,3))
        self.assertTrue(p.observe(20,Decimal('0.2'),60,4))
        self.assertIsNone(parse_number('343/485','percent'))
        self.assertEqual(parse_number('16.91%','percent'),Decimal('16.91'))
    def test_eta(self):
        self.assertEqual(eta(60,0,100,3600,60),('MAX',0))
        self.assertEqual(eta(19,Decimal('19.11'),35000,3600,60)[1],129640)
        self.assertEqual(eta(19,20,0,10,60)[0],'Calc…')
    def test_layout_geometry(self):
        g=geometry(dict(enabled=['ad','eta'],status=False,pause=False,reset=False))
        self.assertEqual(len(g['cells']),2);self.assertIsNone(g['reset']);self.assertLess(g['width'],310)
        self.assertIsNone(safe_position((0,0,800,600),dict(left=0,top=500,width=200,height=100),None,(0,0),(g['width'],g['height']),(dict(left=0,top=0,width=100,height=100),)))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prefs.json';save(dict(enabled=['eta','ad'],order=['eta','ad']),p)
            self.assertEqual(load(p)['enabled'],['eta','ad'])
