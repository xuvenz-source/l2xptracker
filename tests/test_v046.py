import unittest,queue
from unittest.mock import Mock,patch
import numpy as np
from region_editor import draft_regions,move_region,rect_from_points,calibration_data
from session_pause import PauseGate
from tracker import App
from test_v06 import TARGET,REG,DESK
from window_focus import Target

OTHER=Target(2,30,TARGET.title,TARGET.width,TARGET.height,TARGET.window_class)
LEVEL=dict(left=5,top=5,width=16,height=18)
PERCENT=dict(left=50,top=70,width=60,height=13)
STATUS=dict(mode='auto',cap=60,interval=2,binding=[TARGET.title,TARGET.window_class,TARGET.width,TARGET.height],regions={'level':LEVEL,'percent':PERCENT})

class RegionTests(unittest.TestCase):
    def test_geometry_and_restart(self):
        self.assertEqual(draft_regions(OTHER,TARGET,REG,STATUS),dict(chat=REG,level=LEVEL,percent=PERCENT))
        self.assertEqual(move_region(LEVEL,-100,900,1000,700)['top'],682)
        self.assertEqual(rect_from_points((50,60),(-1,10),100,100),dict(left=0,top=10,width=50,height=50))
        data,status=calibration_data(OTHER,dict(chat=REG,level=LEVEL,percent=PERCENT),18,STATUS)
        self.assertEqual(data['region'],REG);self.assertEqual(status,STATUS)
        with self.assertRaises(ValueError):calibration_data(OTHER,dict(chat=REG,level=dict(LEVEL,left=-1)),18,STATUS)
        with self.assertRaises(ValueError):calibration_data(OTHER,dict(chat=dict(REG,height=20)),18,STATUS)
    def test_gate_requires_pause_and_invalidates_revision(self):
        g=PauseGate()
        with self.assertRaises(RuntimeError):g.replace_binding(OTHER,REG)
        g.toggle();g.replace_binding(OTHER,dict(REG,left=25));g.toggle()
        manual,revision,focus,target,region=g.capture_context(TARGET,REG)
        self.assertFalse(manual);self.assertEqual(target,OTHER);self.assertEqual(region['left'],25);self.assertEqual(revision,3)
        self.assertFalse(g.accepts(0));self.assertTrue(g.accepts(revision))
    def test_live_save_keeps_session_and_totals(self):
        a=App.__new__(App);a.running=True;a.pending=2;a.pause_gate=PauseGate();a.pause_gate.toggle();a.session_pitch=18;a.hud=None
        a.session_id='same';a.events=['old'];a.totals={'XP':500};a.active_seconds=100
        a.player=Mock();a.player.config=STATUS;a.player.generation=7;a.status=Mock();a.append=Mock()
        new=dict(REG,left=30)
        with patch('tracker.save_status'),patch('tracker.settings.save'):
            a.apply_bound_regions(OTHER,dict(chat=new,level=LEVEL,percent=PERCENT))
        self.assertEqual(a.session_id,'same');self.assertEqual(a.events,['old']);self.assertEqual(a.totals,{'XP':500});self.assertEqual(a.active_seconds,100)
        self.assertEqual(a.region,new);self.assertEqual(a.player.generation,8);self.assertTrue(a.pause_gate.snapshot()[0])
        self.assertEqual(a.pause_gate.capture_context(TARGET,REG)[3:],(OTHER,new))
    def test_failed_save_keeps_live_binding(self):
        a=App.__new__(App);a.running=True;a.pending=2;a.pause_gate=PauseGate();a.pause_gate.toggle();a.session_pitch=18;a.hud=None;a.target=TARGET;a.region=REG
        a.player=Mock();a.player.config=STATUS
        with patch('tracker.save_status') as save,patch('tracker.settings.save',side_effect=OSError('disk')):
            with self.assertRaises(OSError):a.apply_bound_regions(OTHER,dict(chat=REG))
        self.assertEqual(save.call_count,2);self.assertEqual(a.target,TARGET);self.assertIsNone(a.pause_gate.binding)
    def test_capture_uses_new_binding_after_resume(self):
        a=App.__new__(App);a.inbox=queue.Queue();a.active_seconds=0
        gate=PauseGate();gate.toggle();jobs=queue.Queue();calls=[]
        new=dict(REG,left=30)
        class Halt:
            stopped=False
            def is_set(self):return self.stopped
            def set(self):self.stopped=True
            def wait(self,seconds):
                calls.append(seconds)
                if len(calls)==1:gate.replace_binding(OTHER,new);gate.toggle()
                elif len(calls)==3:self.set()
        h=Halt();screen=Mock();screen.monitors=[DESK];screen.grab.return_value=np.zeros((REG['height'],REG['width'],4),np.uint8)
        cm=Mock();cm.__enter__=Mock(return_value=screen);cm.__exit__=Mock(return_value=False)
        def region(api,target,local,*args,**kwargs):
            self.assertEqual(target,OTHER);self.assertEqual(local,new);return local,None
        with patch('tracker.Windows'),patch('tracker.mss.mss',return_value=cm),patch('tracker.capture_region',side_effect=region) as cap,patch('tracker.rows_of',return_value=np.ones((10,18,REG['width']),bool)),patch('tracker.overlap',return_value=1):
            a.capture(TARGET,REG,18,h,jobs,gate)
        self.assertEqual(cap.call_count,4);self.assertEqual(jobs.get_nowait()[1].shape,(1,18,REG['width'],3));self.assertIsNone(jobs.get_nowait())
