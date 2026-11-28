import unittest
from unittest.mock import Mock
from hud_layout import clean,geometry
from hud_pair import HudPair
from globe_hud import GlobeHud
from vitals import current_pair
from test_v06 import TARGET,REG

class DetachedGlobesTests(unittest.TestCase):
    def test_independent_sizes_and_no_toolbar(self):
        c=clean(dict(globe_sizes={'hp':90,'mp':210}))
        for k,d in [('hp',90),('mp',210)]:
            g=geometry(c,k.upper()+' GLOBE')
            self.assertEqual((g['width'],g['height']),(d,d))
            self.assertIsNone(g['lock']);self.assertIsNone(g['settings'])
            self.assertEqual(g['toolbar'],0)
        self.assertEqual(clean({'globe_sizes':{'hp':10,'mp':True}})['globe_sizes'],{'hp':120,'mp':120})
    def test_switch_and_visibility(self):
        p,l,m,v,hp,mp=(Mock() for _ in range(6))
        for h in (p,l,m,v,hp,mp):h.shown=False
        pair=HudPair(p,l,m,v);pair.globes={'hp':hp,'mp':mp}
        pair.configure_layout(dict(enabled=['hp','mp'],vital_style='Globes',show_xp=False,show_loot=False))
        api=Mock();api.geometry.return_value=(0,0,1000,700)
        pair.update(api,TARGET,REG,True,100,20,30)
        hp.update.assert_called_once();mp.update.assert_called_once();v.update.assert_not_called()
        pair.configure_layout(dict(enabled=['hp'],vital_style='Globes',show_xp=False,show_loot=False))
        hp.update.reset_mock();mp.update.reset_mock()
        pair.update(api,TARGET,REG,True,100,20,30)
        hp.update.assert_called_once();mp.update.assert_not_called()
        pair.configure_layout(dict(enabled=['hp','mp'],vital_style='Numbers'))
        pair.update(api,TARGET,REG,True,100,20,30);v.update.assert_called_once()
        pair.close()
        for h in (p,l,m,v,hp,mp):h.close.assert_called_once()
    def test_colour_key_and_click_through(self):
        h=GlobeHud.__new__(GlobeHud);h.hwnd=3;h.u=Mock()
        h.set_opacity(100)
        h.u.SetLayeredWindowAttributes.assert_called_once_with(3,0xff00ff,255,3)
        self.assertFalse(h.wants_input((20,20)))
    def test_verified_pair_survives_static_bar_offset_not_movement(self):
        self.assertEqual(current_pair(.92,.92,(90,100),1),(90,100))
        self.assertIsNone(current_pair(.94,.92,(90,100),1))
        self.assertIsNone(current_pair(.92,.92,(90,100),5))
        self.assertIsNone(current_pair(None,.92,(90,100),1))
        self.assertIsNone(current_pair(.92,.92,(80,100),1))
