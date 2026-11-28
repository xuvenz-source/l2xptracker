import unittest,tempfile
from pathlib import Path
from unittest.mock import Mock
from vitals import display_value
from vital_globes import globe_rectangles,EMPTY,UNKNOWN,PALETTE
from hud_layout import clean,geometry,panel_config,save,load
from tracker import App

class GlobeTests(unittest.TestCase):
    def test_modes_keep_slots(self):
        for mode,exact,estimate,missing in [
            ('Value','58/187','—','—'),
            ('Percent','31%','~31%','—'),
            ('Both','58/187 - 31%','— - ~31%','— - —')]:
            self.assertEqual(display_value(.309,(58,187),mode),exact)
            self.assertEqual(display_value(.309,None,mode),estimate)
            self.assertEqual(display_value(None,None,mode),missing)
        self.assertEqual(display_value(1,(100,100)),'100/100 - 100%')
    def test_preferences_and_layout(self):
        c=clean(dict(enabled=['hp','mp','xp'],vital_style='Globes',vital_modes={'hp':'Both','mp':'Percent'},panel_rows={'vitals':'1'}))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prefs.json';save(c,p);self.assertEqual(load(p),c)
        g=geometry(panel_config(c,'vitals'),'HP / MP')
        self.assertEqual(g['orb_diameter'],84)
        self.assertEqual(len(g['cells']),2)
        self.assertGreater(g['cells'][1][2],g['cells'][0][2])
        for k,x,y,w,h in g['cells']:
            self.assertLessEqual(x+w,g['width'])
            self.assertLessEqual(y+h,g['height'])
        self.assertEqual(geometry(panel_config(c,'progression'),'XP / SP')['orb_diameter'],0)
        self.assertEqual(clean({'vital_style':'bad','vital_modes':{'hp':'bad'}})['vital_modes'],{'hp':'Both','mp':'Both'})
    def test_empty_full_partial_and_unknown(self):
        for k in ('hp','mp'):
            colors=lambda f:{r[-1] for r in globe_rectangles(k,84,f)}
            self.assertIn(UNKNOWN,colors(None));self.assertNotIn(UNKNOWN,colors(0))
            self.assertIn(EMPTY,colors(0));self.assertTrue(colors(0).isdisjoint(PALETTE[k]))
            self.assertTrue(colors(1).intersection(PALETTE[k]));self.assertNotIn(EMPTY,colors(1))
            self.assertIn(EMPTY,colors(.5));self.assertTrue(colors(.5).intersection(PALETTE[k]))
            for l,t,r,b,_ in globe_rectangles(k,84,.5):
                self.assertTrue(0<=l<r<=84 and 0<=t<b<=84)
    def test_globe_preview(self):
        a=App.__new__(App);a.hud_preview=Mock()
        a.hud_preview.winfo_width.return_value=900;a.hud_preview.cget.return_value='110'
        a.hud_opacity=92;a.hud_net_adena=False
        a.hud_config=clean(dict(enabled=['hp','mp'],vital_style='Globes',vital_modes={'hp':'Both','mp':'Percent'}))
        a.preview_hud()
        values=[c.kwargs.get('text') for c in a.hud_preview.create_text.call_args_list]
        self.assertIn('449/505 - 89%',values);self.assertIn('31%',values)
        self.assertGreater(a.hud_preview.create_rectangle.call_count,100)
