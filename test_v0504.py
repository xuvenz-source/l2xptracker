import queue,unittest
from unittest.mock import Mock,patch
import numpy as np
from tracker import App
from session_pause import PauseGate
from window_focus import capture_region,BACKGROUND_WAIT
from test_v06 import TARGET,REG,DESK

class BackgroundTests(unittest.TestCase):
    def test_covered_and_minimised_only_with_focus_disabled(self):
        api=Mock();api.usable.return_value=True;api.pid.return_value=TARGET.pid
        api.geometry.return_value=(100,100,TARGET.width,TARGET.height);api.foreground.return_value=2;api.region_clear.return_value=False
        self.assertTrue(capture_region(api,TARGET,REG,DESK,False)[1].startswith(BACKGROUND_WAIT))
        self.assertFalse(capture_region(api,TARGET,REG,DESK,True)[1].startswith(BACKGROUND_WAIT))
        api.usable.return_value=False;api.minimized.return_value=True
        self.assertTrue(capture_region(api,TARGET,REG,DESK,False)[1].startswith(BACKGROUND_WAIT))
        api.pid.return_value=99
        self.assertFalse(capture_region(api,TARGET,REG,DESK,False)[1].startswith(BACKGROUND_WAIT))
    def run_capture(self,policy,wait_reason,manual=False):
        a=App.__new__(App);a.inbox=queue.Queue();a.active_seconds=0
        gate=PauseGate(policy);jobs=queue.Queue();clock=[0];calls=[]
        class Halt:
            stopped=False
            def is_set(self):return self.stopped
            def set(self):self.stopped=True
            def wait(self,seconds):
                clock[0]+=1;calls.append(seconds)
                if manual and len(calls)==1:gate.toggle()
                if manual and len(calls)==3:gate.toggle()
                if len(calls)==4:self.set()
        h=Halt();screen=Mock();screen.monitors=[DESK];screen.grab.return_value=np.zeros((REG['height'],REG['width'],4),np.uint8)
        cm=Mock();cm.__enter__=Mock(return_value=screen);cm.__exit__=Mock(return_value=False)
        def region(*args,**kw):
            if len(calls) in (1,2):return None,wait_reason
            return REG,None
        with patch('tracker.time.monotonic',side_effect=lambda:clock[0]),patch('tracker.Windows'),patch('tracker.mss.mss',return_value=cm),patch('tracker.capture_region',side_effect=region),patch('tracker.rows_of',return_value=np.ones((10,18,REG['width']),bool)),patch('tracker.overlap',return_value=1) as overlap:
            a.capture(TARGET,REG,18,h,jobs,gate)
        return a,screen,overlap,jobs
    def test_background_clock_and_recoverable_overlap(self):
        a,screen,overlap,jobs=self.run_capture(False,BACKGROUND_WAIT)
        self.assertEqual(a.active_seconds,3);self.assertEqual(screen.grab.call_count,2)
        overlap.assert_called_once();self.assertEqual(jobs.get_nowait()[1].shape,(1,18,REG['width'],3));self.assertIsNone(jobs.get_nowait())
        self.assertFalse(any(k=='gap' for k,v in a.inbox.queue))
    def test_enabled_focus_pause_excludes_time(self):
        a,screen,overlap,jobs=self.run_capture(True,'Paused — not focused')
        self.assertEqual(a.active_seconds,0);overlap.assert_not_called();self.assertIsNone(jobs.get_nowait())
    def test_manual_pause_still_excludes_time(self):
        a,screen,overlap,jobs=self.run_capture(False,BACKGROUND_WAIT,True)
        self.assertEqual(a.active_seconds,0);overlap.assert_not_called();self.assertIsNone(jobs.get_nowait())
