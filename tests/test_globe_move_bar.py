import unittest
from unittest.mock import Mock,patch
from globe_hud import GlobeHud
from hud_layout import geometry
from ornate_globe import render_globe,with_move_bar,MOVE_BAR_HEIGHT
from tracker import App

class GlobeMoveBarTests(unittest.TestCase):
    def globe(self):
        h=GlobeHud.__new__(GlobeHud)
        h.layout=geometry({},'HP GLOBE');h.editing=False;h.locked=True
        h.surface_key=None;h.preferred=(200,300);h.position=(300,400)
        h.shown=True;h.drag_context=((100,100,1000,700),{},None)
        h.hwnd=3;h.u=Mock();h.g=Mock();h.drag=None;h.placement=None
        h.press_handled=False;h.on_move=Mock();h.set_interactive=Mock()
        h.widget_values={'hp':('HP','89%'),'hp_fill':.89};h.opacity=92
        return h
    def test_move_bar_and_lock_without_position_jump(self):
        h=self.globe();self.assertFalse(h.wants_input((320,405)))
        h.begin_move()
        self.assertEqual(h.dimensions(),(120,120+MOVE_BAR_HEIGHT))
        self.assertEqual(h.preferred,(200,300-MOVE_BAR_HEIGHT))
        h.position=(300,400-MOVE_BAR_HEIGHT)
        self.assertTrue(h.wants_input((320,380)))
        self.assertFalse(h.wants_input((320,420)))
        h.handle_press((320,380))
        self.assertIsNotNone(h.drag)
        h.preferred=(250,310);h.position=(350,410)
        h.finish_drag();h.on_move.assert_not_called()
        h.press_handled=False
        h.handle_press((465,420))
        self.assertFalse(h.editing);self.assertTrue(h.locked)
        self.assertEqual(h.dimensions(),(120,120))
        h.on_move.assert_called_once_with((250,310+MOVE_BAR_HEIGHT))
        self.assertFalse(h.wants_input((365,450)))
        h.set_interactive.assert_called_with(False)
    def test_cancel_restores_saved_position(self):
        h=self.globe();h.begin_move();h.preferred=(20,30)
        h.cancel_placement()
        self.assertEqual(h.preferred,(200,300))
        self.assertFalse(h.editing);h.on_move.assert_not_called()
    def test_surface_changes_when_bar_toggled(self):
        h=self.globe()
        with patch('globe_hud.present') as show:
            h.present_surface();h.begin_move();h.present_surface()
            self.assertEqual(show.call_count,2)
            self.assertEqual(show.call_args.args[3].size,(120,146))
            h.end_move(False);h.present_surface()
            self.assertEqual(show.call_args.args[3].size,(120,120))
        art=render_globe('mp',80,.31,'31%')
        expanded=with_move_bar(art,'mp')
        self.assertEqual(expanded.crop((0,MOVE_BAR_HEIGHT,80,106)).tobytes(),art.tobytes())
    def test_menu_moves_only_selected_globe_without_shift_placement(self):
        a=App.__new__(App);a.hud=Mock();a.hud_enabled=Mock(get=Mock(return_value=True))
        a.hud_config=dict(show_vitals=True,vital_style='Globes',enabled=['hp','mp'])
        a.running=True;a.status=Mock()
        hp,mp=Mock(editing=False),Mock(editing=False);a.hud.globes={'hp':hp,'mp':mp}
        a.place_globe('hp')
        hp.begin_move.assert_called_once();hp.arm_placement.assert_not_called();mp.begin_move.assert_not_called()
        hp.editing=True;a.place_globe('hp')
        hp.end_move.assert_called_once_with(save=False)
