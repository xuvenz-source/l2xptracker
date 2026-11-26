import unittest
from unittest.mock import Mock,patch
from session_pause import PauseGate
from tracker import App
import test_v08

class PauseTests(unittest.TestCase):
    def test_pause_resume_rejects_stale_capture(self):
        g=PauseGate(); self.assertEqual(g.snapshot(),(False,0))
        self.assertTrue(g.toggle()); self.assertFalse(g.accepts(0))
        self.assertFalse(g.toggle()); self.assertFalse(g.accepts(0));self.assertTrue(g.accepts(2))
    def test_button_preserves_totals_timer_and_review(self):
        a=App.__new__(App);a.running=True;a.pause_gate=PauseGate();a.pause_btn=Mock();a.status=Mock();a.append=Mock();a.totals={'XP':221};a.active_seconds=50;a.reviews=object();r=a.reviews
        a.toggle_pause();a.pause_btn.config.assert_called_with(text='Resume');self.assertTrue(a.pause_gate.snapshot()[0]);self.assertEqual(a.active_seconds,50)
        a.toggle_pause();a.pause_btn.config.assert_called_with(text='Pause');self.assertEqual(a.totals,{'XP':221});self.assertIs(a.reviews,r)
    def test_no_pause_when_stopped(self):
        a=App.__new__(App);a.running=False;a.pause_gate=PauseGate();a.toggle_pause();self.assertEqual(a.pause_gate.snapshot(),(False,0))

class PlacementTests(unittest.TestCase):
    def make(self):return test_v08.DragTests().make_hud()
    def test_pointer_without_mouse_click(self):
        h,api,tick=self.make();tick();h.arm_placement();h.cursor.return_value=(500,300);tick();self.assertEqual(h.position,(345,269));self.assertFalse(h.interactive);h.on_move.assert_not_called()
        h.keys={0x10};tick();self.assertIsNone(h.placement);h.on_move.assert_called_once_with((245,169));self.assertEqual(h.preferred,(245,169))
    def test_wait_for_game_then_cancel_on_alt_tab(self):
        h,api,tick=self.make();api.foreground.return_value=2;h.arm_placement();tick();self.assertIsNotNone(h.placement);self.assertFalse(h.shown)
        api.foreground.return_value=1;tick();api.foreground.return_value=2;tick();self.assertIsNone(h.placement);self.assertFalse(h.shown);h.on_move.assert_not_called()
    def test_chat_overlap_not_saved(self):
        h,api,tick=self.make();tick();h.arm_placement();tick();h.cursor.return_value=(250,650);h.keys={0x10};tick();self.assertIsNotNone(h.placement);h.on_move.assert_not_called()
    def test_shift_already_held_not_saved(self):
        h,api,tick=self.make();h.arm_placement();h.keys={0x10};tick();self.assertIsNotNone(h.placement);h.keys=set();tick();h.keys={0x10};tick();self.assertIsNone(h.placement)
    def test_stop_cancels_placement(self):
        h,api,tick=self.make();h.arm_placement();h.update(api,None,None,False,0,0,0);self.assertIsNone(h.placement)

class CapturePauseTests(unittest.TestCase):
    def test_manual_pause_skips_capture_and_resume_rebaselines(self):
        import queue, numpy as np
        from tracker import App
        from test_v06 import TARGET,REG,DESK
        a=App.__new__(App);a.inbox=queue.Queue();a.active_seconds=0
        gate=PauseGate();gate.toggle();jobs=queue.Queue(); calls=[]
        class Halt:
            stopped=False
            def is_set(self):return self.stopped
            def set(self):self.stopped=True
            def wait(self,seconds):
                calls.append('wait')
                if len(calls)==1:gate.toggle() # initially manually paused
                if len(calls)==3:gate.toggle();gate.toggle() # rapid pause/resume between frames
                if len(calls)==4:self.set()
        h=Halt(); screenshot=np.zeros((REG['height'],REG['width'],4),dtype=np.uint8)
        s=Mock();s.monitors=[DESK];s.grab.return_value=screenshot
        cm=Mock();cm.__enter__=Mock(return_value=s);cm.__exit__=Mock(return_value=False)
        with patch('tracker.Windows'),patch('tracker.mss.mss',return_value=cm,create=True),patch('tracker.capture_region',return_value=(REG,None)),patch('tracker.rows_of',return_value=[1,2,3]),patch('tracker.overlap',return_value=1) as overlap:
            a.capture(TARGET,REG,18,h,jobs,gate)
        self.assertEqual(s.grab.call_count,3);self.assertEqual(overlap.call_count,1) # resumed frames establish baseline
        self.assertIsNotNone(jobs.get_nowait());self.assertIsNone(jobs.get_nowait())
    def test_inflight_pause_discards_frame(self):
        import queue, numpy as np
        from test_v06 import TARGET,REG,DESK
        a=App.__new__(App);a.inbox=queue.Queue();a.active_seconds=0
        gate=PauseGate();jobs=queue.Queue()
        import threading
        h=threading.Event();s=Mock();s.monitors=[DESK]
        def grab(rect):
            gate.toggle();gate.toggle();h.set();return np.zeros((REG['height'],REG['width'],4),dtype=np.uint8)
        s.grab.side_effect=grab;cm=Mock();cm.__enter__=Mock(return_value=s);cm.__exit__=Mock(return_value=False)
        with patch('tracker.Windows'),patch('tracker.mss.mss',return_value=cm,create=True),patch('tracker.capture_region',return_value=(REG,None)),patch('tracker.rows_of',return_value=[1,2,3]):
            a.capture(TARGET,REG,18,h,jobs,gate)
        self.assertEqual(a.active_seconds,0);self.assertIsNone(jobs.get_nowait())
