import unittest,tempfile
from pathlib import Path
from unittest.mock import Mock
from settings import load,save,select_match
from hud import Hud,hud_position,rate_text
from window_focus import Target,capture_region

REG=dict(left=10,top=500,width=350,height=180)
DATA=dict(schema=1,title='Lineage II',window_class='GameClass',width=1000,height=700,pitch=18,region=REG)
TARGET=Target(1,20,'Lineage II',1000,700,'GameClass')
DESK=dict(left=0,top=0,width=1920,height=1080)
class Tests(unittest.TestCase):
    def test_settings(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'shared'/'settings.json'; self.assertIsNone(load(p)); save(DATA,p); self.assertEqual(load(p),DATA); self.assertFalse(p.with_suffix('.tmp').exists())
    def test_invalid_region(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):save(dict(DATA,region=dict(REG,top=650)),Path(d)/'settings.json')
    def test_matches(self):
        other=Target(2,30,'Lineage II',1000,700,'GameClass');self.assertEqual(select_match([TARGET],99),TARGET); self.assertIsNone(select_match([TARGET,other],99));self.assertEqual(select_match([TARGET,other],2),other)
    def test_position(self):
        self.assertEqual(hud_position((100,100,1000,700),REG),(778,112))
        self.assertEqual(hud_position((100,100,1000,700),dict(left=650,top=0,width=350,height=100)),(112,112))
        self.assertIsNone(hud_position((0,0,1000,700),dict(left=0,top=0,width=1000,height=700)))
    def test_rate(self):
        self.assertEqual(rate_text(10745,1800),'21,490');self.assertEqual(rate_text(0,0),'—')
    def test_hud_focus(self):
        h=Hud.__new__(Hud);h.hwnd=33;h.shown=False;h.position=None;h.values=('—','—');h.preferred=None;h.drag=None;h.interactive=False;h.on_move=None;h.u=Mock();h.u.GetAsyncKeyState.return_value=0;h.u.GetSystemMetrics.side_effect=lambda i:{76:0,77:0,78:1920,79:1080}[i];h.u.SetWindowPos.return_value=True
        api=Mock();api.usable.return_value=True;api.pid.return_value=20;api.foreground.return_value=1;api.geometry.return_value=(100,100,1000,700)
        h.update(api,TARGET,REG,True,1800,10745,65450);self.assertTrue(h.shown);self.assertEqual(h.values,('21,490','130,900'))
        api.foreground.return_value=2;h.update(api,TARGET,REG,True,1800,10745,65450);self.assertFalse(h.shown);h.u.ShowWindow.assert_called_with(33,0)
        api.foreground.return_value=1;h.update(api,TARGET,REG,True,1800,10745,65450);self.assertTrue(h.shown)
        h.update(api,TARGET,REG,False,1800,10745,65450);self.assertFalse(h.shown)
    def test_window_move_and_resize(self):
        api=Mock();api.usable.return_value=True;api.pid.return_value=20;api.foreground.return_value=1;api.geometry.return_value=(100,100,1000,700)
        self.assertEqual(capture_region(api,TARGET,REG,DESK)[0],dict(left=110,top=600,width=350,height=180))
        api.geometry.return_value=(100,100,900,700);self.assertIsNone(capture_region(api,TARGET,REG,DESK)[0])
if __name__=='__main__':unittest.main()
