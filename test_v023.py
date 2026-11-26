import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from preferences import load_focus_pause,save_focus_pause
from session_pause import PauseGate
from window_focus import capture_region,intersects
from hud import PAUSE_RECT
from test_v06 import TARGET,REG,DESK
import test_v08

class FocusSettingsTests(unittest.TestCase):
    def test_prefs(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'preferences.json'
            self.assertFalse(load_focus_pause(p))
            save_focus_pause(True,p);self.assertTrue(load_focus_pause(p))
            save_focus_pause(False,p);self.assertFalse(load_focus_pause(p))
            p.write_text('{"pause_on_blur":"yes"}');self.assertFalse(load_focus_pause(p))
    def test_policy_revision(self):
        g=PauseGate();self.assertEqual(g.capture_policy(),(False,0,False))
        g.set_focus_policy(True);self.assertFalse(g.accepts(0))
        self.assertEqual(g.capture_policy(),(False,1,True))
        g.toggle();g.set_focus_policy(False)
        self.assertEqual(g.capture_policy(),(True,3,False))
    def test_background_visible(self):
        api=Mock();api.usable.return_value=True;api.pid.return_value=20;api.foreground.return_value=2
        api.geometry.return_value=(100,100,1000,700);api.region_clear.return_value=True
        self.assertIsNotNone(capture_region(api,TARGET,REG,DESK,pause_on_blur=False)[0])
        self.assertIsNone(capture_region(api,TARGET,REG,DESK,pause_on_blur=True)[0])
        api.region_clear.return_value=False
        self.assertIsNone(capture_region(api,TARGET,REG,DESK,pause_on_blur=False)[0])
        api.usable.return_value=False;api.region_clear.return_value=True
        self.assertIsNone(capture_region(api,TARGET,REG,DESK,pause_on_blur=False)[0])
    def test_overlap(self):
        r=dict(left=10,top=20,width=30,height=40)
        self.assertTrue(intersects(r,(39,59,50,70)))
        self.assertFalse(intersects(r,(40,20,50,60)))
    def test_hud_pause_click_once(self):
        h,api,tick=test_v08.DragTests().make_hud();h.on_pause=Mock();tick()
        l,t,_,_=PAUSE_RECT;h.cursor.return_value=(h.position[0]+l+2,h.position[1]+t+2);tick()
        self.assertTrue(h.interactive)
        h.keys={1};tick();h.wndproc(33,0x201,0,0);tick()
        h.on_pause.assert_called_once()
        h.keys=set();tick();h.keys={1};h.wndproc(33,0x201,0,0);tick()
        self.assertEqual(h.on_pause.call_count,2)
        api.foreground.return_value=2;tick();self.assertFalse(h.shown)
    def test_shift_does_not_pause(self):
        h,api,tick=test_v08.DragTests().make_hud();h.on_pause=Mock();tick()
        l,t,_,_=PAUSE_RECT;h.cursor.return_value=(h.position[0]+l+2,h.position[1]+t+2)
        h.keys={0x10,1};tick();h.wndproc(33,0x201,0,0)
        h.on_pause.assert_not_called();self.assertIsNotNone(h.drag)
