import unittest
from unittest.mock import patch, Mock
from hud import LOCK_RECT, PAUSE_RECT
import test_v08

class PollDragTests(unittest.TestCase):
    def make_hud(self):
        return test_v08.DragTests().make_hud()
    def move_to(self,h,rect):
        h.cursor.return_value=(h.position[0]+rect[0]+2,h.position[1]+rect[1]+2)
    def click(self,h,tick,native=False):
        h.keys={1};tick()
        if native:h.wndproc(33,0x201,0,0)
        h.keys=set();tick()
    def test_double_click_unlock_single_click_lock(self):
        h,api,tick=self.make_hud();tick();self.move_to(h,LOCK_RECT);tick()
        with patch('hud.time.monotonic',side_effect=[1,1.2,1.8]):
            self.click(h,tick,True);self.assertTrue(h.locked)
            self.click(h,tick,True);self.assertFalse(h.locked)
            self.click(h,tick,True);self.assertTrue(h.locked)
        self.assertIsNone(h.drag);h.on_move.assert_not_called()
    def test_native_double_click_between_polls(self):
        h,api,tick=self.make_hud();tick();self.move_to(h,LOCK_RECT);tick()
        with patch('hud.time.monotonic',side_effect=[1,1.2]):
            h.wndproc(33,0x201,0,0);h.wndproc(33,0x202,0,0)
            h.wndproc(33,0x201,0,0);h.wndproc(33,0x202,0,0)
        self.assertFalse(h.locked)
        h.keys={1};tick();self.assertFalse(h.locked)
        h.keys=set();tick()
    def test_slow_clicks_do_not_unlock(self):
        h,api,tick=self.make_hud();tick();self.move_to(h,LOCK_RECT)
        with patch('hud.time.monotonic',side_effect=[1,2]):
            self.click(h,tick);self.click(h,tick)
        self.assertTrue(h.locked)
    def test_locked_body_click_through(self):
        h,api,tick=self.make_hud();tick();h.keys={1};tick()
        self.assertFalse(h.interactive);self.assertIsNone(h.drag)
        h.cursor.return_value=(500,300);tick();self.assertEqual(h.position,(778,112))
    def test_unlocked_no_native_message_needed(self):
        h,api,tick=self.make_hud();tick();h.locked=False;tick()
        h.keys={1};tick();self.assertEqual(h.drag,(22,13))
        h.cursor.return_value=(500,300);tick();self.assertEqual(h.position,(478,287))
        h.keys=set();tick();h.on_move.assert_called_once_with((378,187))
        self.assertIsNone(h.drag)
    def test_click_outside_cannot_start_by_moving_inside(self):
        h,api,tick=self.make_hud();tick();h.locked=False;h.cursor.return_value=(500,300);tick()
        h.keys={1};tick();h.cursor.return_value=(800,125);tick()
        self.assertIsNone(h.drag);h.on_move.assert_not_called()
    def test_return_with_button_held(self):
        h,api,tick=self.make_hud();tick();h.locked=False;api.foreground.return_value=2;tick()
        h.keys={1};api.foreground.return_value=1;tick();tick();self.assertIsNone(h.drag)
        h.keys=set();tick();h.keys={1};tick();self.assertEqual(h.drag,(22,13))
    def test_native_and_poll_do_not_reset_drag(self):
        h,api,tick=self.make_hud();tick();h.locked=False;h.keys={1};tick()
        h.cursor.return_value=(820,135);h.wndproc(33,0x201,0,0);self.assertEqual(h.drag,(22,13))
    def test_drag_avoids_chat(self):
        h,api,tick=self.make_hud();tick();h.locked=False;h.keys={1};tick()
        h.cursor.return_value=(150,650);tick();self.assertEqual(h.position,(778,112))
        h.cursor.return_value=(500,300);tick();self.assertEqual(h.position,(478,287))
    def test_pause_does_not_drag_when_unlocked(self):
        h,api,tick=self.make_hud();h.on_pause=Mock();tick();h.locked=False
        self.move_to(h,PAUSE_RECT);tick();self.click(h,tick,True)
        h.on_pause.assert_called_once();self.assertIsNone(h.drag)
    def test_alt_tab_clears_first_unlock_click(self):
        h,api,tick=self.make_hud();tick();self.move_to(h,LOCK_RECT)
        self.click(h,tick);self.assertIsNotNone(h.lock_first)
        api.foreground.return_value=2;tick();self.assertIsNone(h.lock_first)
        api.foreground.return_value=1;tick();self.move_to(h,LOCK_RECT)
        self.click(h,tick);self.assertTrue(h.locked)
