import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from hud_layout import clean,save,load,geometry,main_config,panel_config
from hud_pair import HudPair
from hud import Hud
from tracker import App
from test_v06 import TARGET,REG

class MainHudTests(unittest.TestCase):
    def test_visibility_and_row_preferences(self):
        c=clean(dict(enabled=['xp','eta','ad'],widgets_per_row=3,panel_rows={'progression':'1'},show_xp=False))
        self.assertFalse(c['show_xp']);self.assertTrue(c['show_loot'])
        self.assertEqual(panel_config(c,'progression')['widgets_per_row'],1)
        self.assertEqual(panel_config(c,'loot')['widgets_per_row'],3)
        self.assertFalse(panel_config(c,'progression')['footer'] if 'footer' in panel_config(c,'progression') else panel_config(c,'progression')['pause'])
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'p.json';save(c,f);self.assertEqual(load(f),c)
    def test_main_buttons_and_shared_controls(self):
        for size in ('compact','standard','large'):
            g=geometry(main_config(dict(size=size)),'MAIN HUD',main_controls=True)
            self.assertEqual(g['cells'],[]);self.assertIsNotNone(g['pause']);self.assertIsNotNone(g['reset'])
            self.assertEqual(g['toggles'],{});self.assertIsNone(g['title']);self.assertFalse(g['status'])
            self.assertEqual(g['height'],28);self.assertLess(g['width'],200)
            self.assertLess(g['pause'][2],g['reset'][0]);self.assertLess(g['reset'][2],g['lock'][0])
    def test_tracker_toolbar_does_not_consume_widget_width(self):
        from hud_layout import SIZES
        for size in SIZES:
            cell=SIZES[size][0]
            for kind,title,enabled in [('progression','XP / SP',['xp','eta','killsnext']),('loot','ADENA / LOOT',['ad','loot','cost'])]:
                g=geometry(panel_config(dict(size=size,enabled=enabled),kind),title,select_loot=kind=='loot')
                self.assertEqual(g['width'],2*cell+min(cell,round(54*max(SIZES[size][2]/11,SIZES[size][3]/17)))+8 if kind=='progression' else 3*cell+16)
                self.assertEqual(g['toolbar'],24)
                self.assertTrue(all(y>=g['lock'][3] and y>=g['settings'][3] and x+w<=g['width'] for _,x,y,w,_ in g['cells']))
                self.assertEqual(g['toggles'],{})
    def test_native_compact_controls_hit_without_drag(self):
        h=Hud.__new__(Hud);h.layout=geometry(main_config({}),'MAIN HUD',main_controls=True)
        h.shown=True;h.position=(100,100);h.placement=None;h.drag=None;h.lock_first=None
        h.on_settings=Mock();h.on_reset=Mock();h.on_pause=Mock()
        for locked in (True,False):
            h.locked=locked
            for k in ('settings','reset','lock','pause'):
                l,t,_,_=h.layout[k];point=(l+101,t+101)
                self.assertTrue(h.wants_input(point));self.assertFalse(h.body_hit(point))
            h.press_handled=False
            l,t,_,_=h.layout['settings'];h.handle_press((l+101,t+101));h.handle_press((l+101,t+101))
        self.assertEqual(h.on_settings.call_count,2)
    def test_main_visible_when_both_trackers_hidden(self):
        p,l,m=Mock(),Mock(),Mock()
        for h in (p,l,m):h.shown=False
        pair=HudPair(p,l,m);pair.configure_layout(dict(enabled=['xp','ad'],show_xp=False,show_loot=False))
        api=Mock();api.geometry.return_value=(0,0,1000,700)
        pair.update(api,TARGET,REG,True,100,20,30)
        p.hide.assert_called_once();l.hide.assert_called_once()
        p.update.assert_not_called();l.update.assert_not_called();m.update.assert_called_once()
        self.assertFalse(p.configure_layout.call_args.args[0]['pause'])
        self.assertFalse(l.configure_layout.call_args.args[0]['reset'])
        m.set_panel_visibility.assert_called_with(dict(progression=False,loot=False))
    def test_toggle_does_not_reset_session(self):
        a=App.__new__(App);a.running=True;a.events=['reward'];a.active_seconds=100
        a.hud_show={'show_xp':Mock(get=Mock(return_value=True))};a.apply_hud_config=Mock()
        a.toggle_tracker_panel('progression')
        a.hud_show['show_xp'].set.assert_called_once_with(False);a.apply_hud_config.assert_called_once()
        self.assertEqual(a.events,['reward']);self.assertEqual(a.active_seconds,100)
    def test_loot_menu_scope(self):
        from hud_layout import WIDGETS,LOOT
        a=App.__new__(App);a.running=True;a.root=Mock();a.root.winfo_pointerxy.return_value=(10,20)
        a.hud_vars={k:Mock() for k in WIDGETS};a.hud_panel_rows={'loot':Mock()};a.hud_net_adena_var=Mock()
        menu,widgets,rows=Mock(),Mock(),Mock()
        with patch('tracker.tk.Menu',side_effect=[menu,widgets,rows]):a.show_hud_settings('loot')
        labels=[c.kwargs['label'] for c in menu.add_command.call_args_list]
        self.assertIn('Monster Library…',labels);self.assertNotIn('Set level / XP %…',labels)
        self.assertEqual([c.kwargs['variable'] for c in widgets.add_checkbutton.call_args_list],[a.hud_vars[k] for k in LOOT])
