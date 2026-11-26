import unittest
import test_v08

class PollDragTests(unittest.TestCase):
    def make_hud(self):
        return test_v08.DragTests().make_hud()
    def test_no_native_message_needed(self):
        h,api,tick=self.make_hud();tick();h.keys={0x10};tick()
        h.keys.add(1);tick();self.assertEqual(h.drag,(22,13))
        h.cursor.return_value=(500,300);tick();self.assertEqual(h.position,(478,287))
        h.keys.remove(1);tick();h.on_move.assert_called_once_with((378,187))
        self.assertIsNone(h.drag)
    def test_click_outside_cannot_start_by_moving_inside(self):
        h,api,tick=self.make_hud();tick();h.cursor.return_value=(500,300)
        h.keys={0x10,1};tick();h.cursor.return_value=(800,125);tick()
        self.assertIsNone(h.drag);h.on_move.assert_not_called()
    def test_plain_click_then_shift_does_not_start(self):
        h,api,tick=self.make_hud();tick();h.keys={1};tick();h.keys.add(0x10);tick()
        self.assertIsNone(h.drag)
    def test_return_with_button_held(self):
        h,api,tick=self.make_hud();tick();api.foreground.return_value=2;tick()
        h.keys={0x10,1};api.foreground.return_value=1;tick();tick();self.assertIsNone(h.drag)
        h.keys.remove(1);tick();h.keys.add(1);tick();self.assertEqual(h.drag,(22,13))
    def test_native_and_poll_do_not_reset_drag(self):
        h,api,tick=self.make_hud();tick();h.keys={0x10,1};tick()
        h.cursor.return_value=(820,135);h.wndproc(33,0x201,0,0);self.assertEqual(h.drag,(22,13))
    def test_release_shift_ends_and_saves(self):
        h,api,tick=self.make_hud();tick();h.keys={0x10,1};tick()
        h.cursor.return_value=(500,300);tick();h.keys.remove(0x10);tick()
        h.on_move.assert_called_once_with((378,187));self.assertFalse(h.interactive)
    def test_drag_avoids_chat(self):
        h,api,tick=self.make_hud();tick();h.keys={0x10,1};tick()
        h.cursor.return_value=(150,650);tick();self.assertEqual(h.position,(778,112))
        h.cursor.return_value=(500,300);tick();self.assertEqual(h.position,(478,287))

if __name__=='__main__':unittest.main()
