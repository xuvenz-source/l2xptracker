import unittest
from unittest.mock import Mock,patch
from PIL import Image
from monster_header import split_name,labelled_rewards,read_header
from monster_library import profile
from hud_layout import geometry
from hud_pair import HudPair
import test_v08
from test_v06 import TARGET,REG

class HeaderTests(unittest.TestCase):
    def test_separate_name_level(self):
        for name in ('Pincher Lv.16','Pincher, Lv.16','Pincher Lv 16'):
            self.assertEqual(split_name(name),('Pincher','16'))
            self.assertEqual(profile(dict(monster=name,rows=[],selected=[],rate=''),'','471','19')['id'],'pincher|16')
    def test_split_rewards_even_if_label_misread(self):
        self.assertEqual(labelled_rewards('EXP: 471 dP: 19'),('471',''))
        im=Image.new('RGB',(575,467))
        ocr=Mock(side_effect=['471','471','19','19'])
        fields,warnings=read_header(im,'EXP: 471 dP: 19','Pincher Lv.16',ocr)
        self.assertEqual(fields,dict(name='Pincher',level='16',xp='471',sp='19'));self.assertEqual(warnings,[])
    def test_uncertain_field_not_guessed(self):
        im=Image.new('RGB',(575,467))
        fields,warnings=read_header(im,'EXP: 471 SP: 19','Pincher Lv.16',Mock(side_effect=['471','471','19','18']))
        self.assertEqual(fields['xp'],'471');self.assertEqual(fields['sp'],'');self.assertTrue(warnings)

class PaintTests(unittest.TestCase):
    def test_visible_metrics_throttled_but_pause_immediate(self):
        h,api,tick=test_v08.DragTests().make_hud();h.layout=geometry(dict(enabled=['xp']))
        def update(xp,ad=20,paused=False):
            h.update(api,TARGET,REG,True,100,ad,xp,paused=paused)
        with patch('hud.time.monotonic',return_value=100):
            update(30);h.u.InvalidateRect.reset_mock();update(40);h.u.InvalidateRect.assert_not_called()
            update(40,paused=True);h.u.InvalidateRect.assert_called_once();h.u.InvalidateRect.reset_mock()
        with patch('hud.time.monotonic',return_value=102):
            update(40,paused=True);h.u.InvalidateRect.assert_called_once();h.u.InvalidateRect.reset_mock()
        with patch('hud.time.monotonic',return_value=104):
            update(40,999,True);h.u.InvalidateRect.assert_not_called()
    def test_buffered_paint_cleans_up(self):
        h,_,_=test_v08.DragTests().make_hud();h.g=Mock();h.paint_layout=Mock()
        h.g.CreateCompatibleDC.return_value=101;h.g.CreateCompatibleBitmap.return_value=102
        h.g.SelectObject.return_value=103;h.g.BitBlt.return_value=True
        h.paint_buffered(99);h.paint_layout.assert_called_once_with(101)
        h.g.BitBlt.assert_called_once();h.g.SelectObject.assert_called_with(101,103)
        h.g.DeleteObject.assert_called_once_with(102);h.g.DeleteDC.assert_called_once_with(101)
    def test_eta_updates_do_not_reconfigure(self):
        p,l=Mock(),Mock();pair=HudPair(p,l);pair.configure_layout(dict(enabled=['ad','xp']))
        with patch('hud_pair.time.monotonic',return_value=1):pair.set_targets('Pincher',[('Ring','1h')])
        l.configure_layout.reset_mock();l.u.InvalidateRect.reset_mock()
        with patch('hud_pair.time.monotonic',return_value=1.1):pair.set_targets('Pincher',[('Ring','59m')])
        l.u.InvalidateRect.assert_not_called()
        with patch('hud_pair.time.monotonic',return_value=3):pair.set_targets('Pincher',[('Ring','59m')])
        l.configure_layout.assert_not_called();l.u.InvalidateRect.assert_called_once()
