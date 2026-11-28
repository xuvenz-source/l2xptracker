import unittest
from unittest.mock import Mock
from test_v08 import DragTests

class NativeDragTests(unittest.TestCase):
    def make(self):
        h,api,tick=DragTests().make_hud()
        h.u.GetCapture.return_value=h.hwnd
        tick();h.locked=False;tick()
        return h,api,tick
    def test_native_move_without_async_button(self):
        h,api,tick=self.make()
        h.wndproc(33,0x201,1,0)
        self.assertTrue(h.native_drag);h.u.SetCapture.assert_called_once_with(33)
        tick();self.assertIsNotNone(h.drag)
        h.cursor.return_value=(500,300);h.wndproc(33,0x200,1,0)
        self.assertEqual(h.position,(478,287))
        tick();self.assertEqual(h.position,(478,287))
        h.wndproc(33,0x202,0,0)
        self.assertIsNone(h.drag);h.u.ReleaseCapture.assert_called_once()
        h.on_move.assert_called_once_with((378,187))
    def test_native_reject_chat_then_resume(self):
        h,api,tick=self.make();h.wndproc(33,0x201,1,0)
        h.cursor.return_value=(150,650);h.wndproc(33,0x200,1,0)
        self.assertEqual(h.position,(778,112));self.assertTrue(h.drag_rejected)
        h.cursor.return_value=(500,300);h.wndproc(33,0x200,1,0)
        self.assertEqual(h.position,(478,287));self.assertFalse(h.drag_rejected)
    def test_capture_loss_releases_when_not_held(self):
        h,api,tick=self.make();h.wndproc(33,0x201,1,0)
        h.cursor.return_value=(500,300);h.wndproc(33,0x200,1,0)
        h.wndproc(33,0x215,0,99);self.assertIsNone(h.drag)
        h.on_move.assert_called_once_with((378,187))
    def test_native_release_after_poll_press(self):
        h,api,tick=self.make();h.keys={1};tick()
        h.wndproc(33,0x201,1,0);h.cursor.return_value=(500,300);tick()
        h.keys=set();tick();self.assertIsNone(h.drag)
        h.wndproc(33,0x202,0,0);h.on_move.assert_called_once_with((378,187))
    def test_move_failure_does_not_save_invalid_position(self):
        h,api,tick=self.make();h.wndproc(33,0x201,1,0)
        h.u.SetWindowPos.return_value=False;h.cursor.return_value=(500,300);h.wndproc(33,0x200,1,0)
        self.assertEqual(h.position,(778,112));self.assertIsNone(h.preferred)
        h.wndproc(33,0x202,0,0);h.on_move.assert_not_called()
