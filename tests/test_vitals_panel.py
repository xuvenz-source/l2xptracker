import unittest
from unittest.mock import Mock,patch
from hud_layout import clean,panel_config,geometry,WIDGETS,VITALS,PROGRESSION
from hud_pair import HudPair
from tracker import App
from test_v06 import TARGET,REG

class VitalsPanelTests(unittest.TestCase):
    def test_migration_and_scope(self):
        c=clean({'enabled':['xp','hp','mp','ad'],'panel_rows':{'vitals':'1'}})
        self.assertTrue(c['show_vitals'])
        self.assertFalse(clean()['show_vitals'])
        self.assertFalse(clean(dict(c,show_vitals=False))['show_vitals'])
        self.assertEqual(panel_config(c,'progression')['enabled'],['xp'])
        v=panel_config(c,'vitals')
        self.assertEqual(v['enabled'],['hp','mp'])
        self.assertEqual(v['widgets_per_row'],1)
        self.assertEqual(len(geometry(v,'HP / MP')['cells']),2)
    def test_independent_visibility_and_cleanup(self):
        p,l,m,v=Mock(),Mock(),Mock(),Mock()
        for h in (p,l,m,v):h.shown=False
        pair=HudPair(p,l,m,v)
        pair.configure_layout(dict(enabled=['xp','hp','mp'],show_xp=False,show_loot=False))
        api=Mock();api.geometry.return_value=(0,0,1000,700)
        pair.update(api,TARGET,REG,True,100,20,30)
        v.update.assert_called_once();p.update.assert_not_called();l.update.assert_not_called()
        pair.configure_layout(dict(enabled=['xp','hp','mp'],show_vitals=False))
        pair.update(api,TARGET,REG,True,100,20,30)
        v.hide.assert_called_once()
        pair.close()
        for h in (p,l,m,v):h.close.assert_called_once()
    def test_menu_scope(self):
        a=App.__new__(App);a.running=True;a.root=Mock();a.root.winfo_pointerxy.return_value=(10,20)
        a.hud_vars={k:Mock() for k in WIDGETS};a.hud_panel_rows={'vitals':Mock()}
        a.vital_style=Mock();a.vital_modes={k:Mock() for k in VITALS}
        menu,style,hp,mp,widgets,rows=(Mock() for _ in range(6))
        with patch('tracker.tk.Menu',side_effect=[menu,style,hp,mp,widgets,rows]):a.show_hud_settings('vitals')
        self.assertEqual([c.kwargs['value'] for c in style.add_radiobutton.call_args_list],['Numbers','Globes'])
        for k,m in (('hp',hp),('mp',mp)):
            self.assertEqual([c.kwargs['value'] for c in m.add_radiobutton.call_args_list],['Value','Percent','Both'])
            self.assertTrue(all(c.kwargs['variable'] is a.vital_modes[k] for c in m.add_radiobutton.call_args_list))
        self.assertEqual([c.kwargs['variable'] for c in widgets.add_checkbutton.call_args_list],[a.hud_vars[k] for k in VITALS])
        self.assertNotIn('hp',PROGRESSION)
