"""Compact trailing column shares toolbar space without changing the metrics."""
import ctypes as c
from ctypes import wintypes as w
import unittest
from unittest.mock import Mock
from hud_layout import geometry,panel_config,SIZES
from hud import Hud

class CompactTailTests(unittest.TestCase):
    def test_reported_layout(self):
        g=geometry(panel_config(dict(enabled=['xp','eta','killsnext']),'progression'),'XP / SP')
        self.assertEqual(g['width'],244)
        self.assertEqual([x for _,x,_,_,_ in g['cells']],[8,99,190])
        self.assertEqual(g['cells'][-1][3],54)
        self.assertEqual(g['settings'],(222,0,244,24))
        self.assertEqual(g['lock'],(200,0,222,24))
        self.assertTrue(all(y>=24 and x+cw<=g['width'] for _,x,y,cw,_ in g['cells']))
    def test_multiple_rows_and_protected_layouts(self):
        for size in SIZES:
            for n in range(1,5):
                g=geometry(panel_config(dict(enabled=['xp','eta','level','progress','killsnext'],size=size,widgets_per_row=n),'progression'),'XP / SP')
                for _,x,y,cw,rh in g['cells']:
                    self.assertLessEqual(x+cw,g['width'])
                    self.assertLessEqual(y+rh,g['height'])
                for x in {r[1] for r in g['cells']}:
                    self.assertEqual(len({r[3] for r in g['cells'] if r[1]==x}),1)
        v=geometry(panel_config(dict(enabled=['hp','mp'],vital_style='Globes'),'vitals'),'HP / MP')
        self.assertFalse(v['tight_tail'])
        self.assertEqual(v['orb_diameter'],84)
        loot=geometry(panel_config(dict(enabled=['ad','loot','cost']),'loot'),'ADENA / LOOT',details=3,select_loot=True)
        self.assertGreaterEqual(loot['width'],300)
        self.assertFalse(geometry(dict(enabled=['killsnext']))['tight_tail'])
    def test_long_value_uses_smaller_font_and_releases_it(self):
        h=Hud.__new__(Hud);h.g=Mock();h.u=Mock();h.font=Mock(return_value=2);h.text=Mock()
        h.g.SelectObject.return_value=99
        def measure(dc,string,count,rect,flags):
            r=c.cast(rect,c.POINTER(w.RECT)).contents
            r.right=90 if h.g.SelectObject.call_args.args[1]==1 else 48
            return 10
        h.u.DrawTextW.side_effect=measure
        h.fitted_text(3,'~99,999',(0,0,51,24),1,(255,255,255),17,600)
        h.text.assert_called_once_with(3,'~99,999',(0,0,51,24),2,(255,255,255))
        h.g.DeleteObject.assert_called_once_with(2)
        h.g.SelectObject.assert_called_with(3,99)
