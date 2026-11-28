import unittest,tempfile
from pathlib import Path
from unittest.mock import Mock,patch
from preferences import load_hud_opacity,save_hud_opacity,write_preference
from hud import Hud
from tracker import App

class OpacityTests(unittest.TestCase):
    def test_persistence_and_validation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prefs.json'
            self.assertEqual(load_hud_opacity(p),92)
            write_preference('auto_update',False,p)
            for value in (20,50,92,100):
                save_hud_opacity(value,p);self.assertEqual(load_hud_opacity(p),value)
            from preferences import load_auto_update
            self.assertFalse(load_auto_update(p))
            for bad in (0,19,101,True,92.5,'50'):
                with self.assertRaises(ValueError):save_hud_opacity(bad,p)
                write_preference('hud_opacity',bad,p)
                self.assertEqual(load_hud_opacity(p),92)
    def test_native_alpha(self):
        h=Hud.__new__(Hud);h.hwnd=33;h.u=Mock();h.u.SetLayeredWindowAttributes.return_value=True
        for percent,alpha in ((20,51),(50,128),(92,235),(100,255)):
            h.set_opacity(percent)
            h.u.SetLayeredWindowAttributes.assert_called_with(33,0,alpha,2)
            self.assertEqual(h.opacity,percent)
        h.u.SetLayeredWindowAttributes.return_value=False
        with self.assertRaises(RuntimeError):h.set_opacity(60)
        self.assertEqual(h.opacity,100)
    def test_slider_and_reset(self):
        a=App.__new__(App);a.root=Mock();a.root.after.return_value='job';a.hud=Mock()
        a.hud_opacity=92;a.hud_opacity_save_job=None;a.hud_opacity_label=Mock();a.hud_opacity_var=Mock()
        with patch('tracker.save_hud_opacity') as save:
            a.change_hud_opacity('65.4')
            a.hud.set_opacity.assert_called_once_with(65)
            a.hud_opacity_label.set.assert_called_with('65%')
            save.assert_not_called()
            a.change_hud_opacity('80.1')
            a.root.after_cancel.assert_called_with('job')
            a.flush_hud_opacity();save.assert_called_once_with(80)
            a.reset_hud_opacity();self.assertEqual(a.hud_opacity,92)
            a.hud_opacity_var.set.assert_called_with(92)
            a.flush_hud_opacity();save.assert_called_with(92)
    def test_failed_native_change_preserves_preference(self):
        a=App.__new__(App);a.hud=Mock();a.hud.set_opacity.side_effect=RuntimeError('test')
        a.hud_opacity=92;a.hud_opacity_var=Mock();a.status=Mock()
        a.change_hud_opacity('60')
        self.assertEqual(a.hud_opacity,92);a.hud_opacity_var.set.assert_called_once_with(92)
