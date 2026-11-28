import unittest
from unittest.mock import Mock,patch
from selection_overlay import clamp_toolbar,screen_origin
from region_editor import OverlayRegionEditor,rect_from_points
from drop_ui import OverlayCropWindow
from tracker import App
from test_v06 import TARGET

class OverlayTests(unittest.TestCase):
    def test_signed_monitor_coordinates(self):
        self.assertEqual(screen_origin(dict(left=-1920,top=-100)),(-1920,-100))
        self.assertEqual(clamp_toolbar(-8,900,1000,700,500,120),(0,580))
    def test_native_scale_selection(self):
        self.assertEqual(rect_from_points((300,200),(100,50),1000,700),dict(left=100,top=50,width=200,height=150))
        self.assertEqual(clamp_toolbar(800,600,1000,700,500,120),(500,580))
    def test_direct_target_does_not_bind_other_foreground(self):
        a=App.__new__(App);a.target=TARGET;api=Mock();api.usable.return_value=True;api.pid.return_value=TARGET.pid;api.foreground.return_value=99
        self.assertEqual(a.selection_target(api,True),TARGET);api.bind_foreground.assert_not_called()
        api.foreground.return_value=TARGET.hwnd;api.bind_foreground.return_value=TARGET
        self.assertEqual(a.selection_target(api,True),TARGET)
    def test_direct_finish_preserves_pause_unless_resume(self):
        a=App.__new__(App);a.running=True;a.selecting=True;a.selection_direct=True;a.root=Mock();a.pause_gate=Mock();a.pause_gate.snapshot.return_value=(True,1);a.toggle_pause=Mock()
        a.finish_region_editor(False);self.assertFalse(a.selecting);a.root.iconify.assert_called_once();a.toggle_pause.assert_not_called()
        a.selection_direct=True;a.finish_region_editor(True);a.toggle_pause.assert_called_once()
    def test_direct_select_no_countdown(self):
        a=App.__new__(App);a.running=True;a.pending=2;a.selecting=False;a.closing=False;a.pause_gate=Mock();a.pause_gate.snapshot.return_value=(False,0);a.toggle_pause=Mock();a.player=Mock();a.player.generation=1;a.root=Mock();a.hud=Mock()
        with patch('tracker.messagebox.askokcancel') as prompt:a.select('chat',direct=True)
        prompt.assert_not_called();a.toggle_pause.assert_called_once();a.root.withdraw.assert_called_once()
        self.assertEqual(a.root.after.call_args.args[0],150);self.assertTrue(a.selecting)
