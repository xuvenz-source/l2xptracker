import unittest
from unittest.mock import Mock,patch
from hud import SETTINGS_RECT
from hud_layout import geometry, WIDGETS
from test_v08 import DragTests
from test_v036 import ResetTests

class HudSettingsTests(unittest.TestCase):
    def test_controls_do_not_overlap_widgets(self):
        for size in ('compact','standard','large'):
            for layout in ('single','double'):
                for enabled in ([],['ad'],list(WIDGETS)):
                    g=geometry(dict(size=size,layout=layout,enabled=enabled))
                    self.assertEqual(g['lock'][2],g['settings'][0])
                    self.assertEqual(g['settings'][2],g['width'])
                    for _,x,y,w,h in g['cells']:
                        self.assertLessEqual(x+w,g['lock'][0])
    def test_gear_click_locked_and_unlocked_no_drag(self):
        h,api,tick=DragTests().make_hud();h.on_settings=Mock();h.on_reset=Mock();h.on_pause=Mock();tick()
        for locked in (True,False):
            h.locked=locked;l,t,_,_=SETTINGS_RECT
            h.cursor.return_value=(h.position[0]+l+2,h.position[1]+t+2);tick()
            self.assertTrue(h.wants_input(h.cursor()));self.assertFalse(h.body_hit(h.cursor()))
            h.keys={1};tick();h.wndproc(33,0x201,0,0);tick()
            self.assertIsNone(h.drag);self.assertEqual(h.locked,locked)
            h.keys=set();tick()
        self.assertEqual(h.on_settings.call_count,2);h.on_pause.assert_not_called();h.on_reset.assert_not_called()
    def test_queue_only_and_stale_run(self):
        a=ResetTests().app();a.last_archive_save=float('inf');a.show_hud_settings=Mock()
        a.inbox.put(('hud_settings',a.run_id-1));a.process_inbox();a.show_hud_settings.assert_not_called()
        a.queue_hud_settings();a.show_hud_settings.assert_not_called()
        a.process_inbox();a.show_hud_settings.assert_called_once_with()
        self.assertTrue(a.running)
    def test_menu_not_opened_during_editor(self):
        from tracker import App
        a=App.__new__(App);a.running=True;a.selecting=True;a.root=Mock()
        with patch('tracker.tk.Menu') as menu:a.show_hud_settings();menu.assert_not_called()
    def test_menu_routes_to_editor_and_hud_settings(self):
        from tracker import App
        a=App.__new__(App);a.running=True;a.selecting=False;a.root=Mock();a.root.winfo_pointerxy.return_value=(300,400)
        a.select=Mock();a.open_hud_settings=Mock();a.hud_vars={k:Mock() for k in WIDGETS};a.hud_rows=Mock();a.apply_hud_config=Mock()
        with patch('tracker.tk.Menu',side_effect=[Mock(),Mock(),Mock()]) as ctor:
            a.show_hud_settings();menu=a.hud_settings_menu
            menu.tk_popup.assert_called_once_with(300,400);menu.grab_release.assert_called_once()
            commands=[c.kwargs['command'] for c in menu.add_command.call_args_list]
            commands[0]();commands[-1]()
            a.select.assert_called_once_with('chat');a.open_hud_settings.assert_called_once_with()
