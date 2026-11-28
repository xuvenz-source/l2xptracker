import queue,unittest,threading
from unittest.mock import Mock,patch
from tracker import App
from session_pause import PauseGate
from window_focus import capture_region
from test_v06 import TARGET,REG,DESK
import test_v08
from hud import PAUSE_RECT

class CaptureHotfixTests(unittest.TestCase):
    def test_focused_capture_not_blocked_by_overlay_rectangles(self):
        api=Mock();api.usable.return_value=True;api.pid.return_value=20
        api.geometry.return_value=(100,100,1000,700)
        api.foreground.return_value=1;api.region_clear.return_value=False
        for policy in (True,False):
            self.assertEqual(capture_region(api,TARGET,REG,DESK,pause_on_blur=policy)[0],dict(left=110,top=600,width=350,height=180))
        api.region_clear.assert_not_called()
        api.foreground.return_value=2
        self.assertIsNone(capture_region(api,TARGET,REG,DESK,pause_on_blur=False)[0])
        api.region_clear.return_value=True
        self.assertIsNotNone(capture_region(api,TARGET,REG,DESK,pause_on_blur=False)[0])
    def test_hud_callback_does_not_touch_tk_or_gate(self):
        a=App.__new__(App);a.inbox=queue.Queue();a.run_id=7;a.running=True
        a.pause_gate=PauseGate();a.pause_btn=Mock();a.status=Mock();a.append=Mock()
        h,api,tick=test_v08.DragTests().make_hud();h.on_pause=a.queue_hud_pause
        tick();l,t,_,_=PAUSE_RECT;h.cursor.return_value=(h.position[0]+l+2,h.position[1]+t+2);tick()
        # Native callback must return even while the capture lock is held.
        with a.pause_gate.lock:
            h.keys={1};h.wndproc(33,0x201,0,0)
            self.assertEqual(a.inbox.get_nowait(),('hud_pause',7))
            self.assertFalse(a.pause_gate.paused)
            a.pause_btn.config.assert_not_called()
        a.queue_hud_move((100,200))
        self.assertEqual(a.inbox.get_nowait(),('hud_move',(100,200)))
    def test_native_release_does_not_duplicate_polling_click(self):
        h,api,tick=test_v08.DragTests().make_hud();h.on_pause=Mock();tick()
        l,t,_,_=PAUSE_RECT;h.cursor.return_value=(h.position[0]+l+2,h.position[1]+t+2);tick()
        h.keys={1};h.wndproc(33,0x201,0,0);h.wndproc(33,0x202,0,0);tick()
        h.on_pause.assert_called_once()
        h.keys=set();tick()
        h.keys={1};tick();self.assertEqual(h.on_pause.call_count,2)
    def test_native_callback_exception_is_contained(self):
        h,api,tick=test_v08.DragTests().make_hud()
        h.wndproc=Mock(side_effect=RuntimeError('test'));h.u.DefWindowProcW.return_value=0
        self.assertEqual(h.safe_wndproc(33,0x201,0,0),0)
