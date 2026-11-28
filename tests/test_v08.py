import tempfile, unittest
from pathlib import Path
from unittest.mock import Mock, patch
from hud import Hud, safe_position, hud_position
from settings import load, save
from test_v06 import DATA, TARGET, REG, DESK

GEO=(100,100,1000,700)
class DragTests(unittest.TestCase):
    def make_hud(self):
        h=Hud.__new__(Hud); h.hwnd=33; h.shown=False; h.position=None; h.values=('—','—')
        h.preferred=None; h.drag=None; h.interactive=False; h.on_move=Mock(); h.locked=True; h.lock_first=None; h.press_handled=False
        h.u=Mock(); h.u.GetSystemMetrics.side_effect=lambda i:dict(zip((76,77,78,79),DESK.values()))[i]
        h.u.SetWindowPos.return_value=True; h.u.GetDoubleClickTime.return_value=500
        h.keys=set(); h.key_down=lambda key:key in h.keys
        h.cursor=Mock(return_value=(800,125))
        h.set_interactive=lambda enabled:setattr(h,'interactive',enabled)
        api=Mock(); api.usable.return_value=True; api.pid.return_value=20; api.foreground.return_value=1; api.geometry.return_value=GEO
        def tick(): h.update(api,TARGET,REG,True,100,20,30)
        return h,api,tick
    def test_preferred_position(self):
        self.assertEqual(hud_position(GEO,REG,DESK,(200,200)),(300,300))
        self.assertEqual(hud_position((200,300,1000,700),REG,DESK,(200,200)),(400,500))
    def test_clamp_and_chat(self):
        self.assertEqual(safe_position(GEO,REG,DESK,(-10,-20)),(100,100))
        self.assertEqual(safe_position(GEO,REG,DESK,(999,999)),(790,714))
        self.assertIsNone(safe_position(GEO,REG,DESK,(20,510)))
        self.assertEqual(hud_position(GEO,REG,DESK,(20,510)),(778,112))
    def test_desktop_edges(self):
        self.assertEqual(safe_position((-100,-50,1000,700),REG,DESK,(0,0)),(0,0))
        self.assertIsNone(safe_position((1900,0,1000,700),REG,DESK,(0,0)))
    def test_drag_and_release(self):
        h,api,tick=self.make_hud(); tick(); self.assertEqual(h.wndproc(33,0x84,0,0),-1)
        h.locked=False; h.keys={0x01}; tick(); self.assertEqual(h.wndproc(33,0x84,0,0),1); self.assertEqual(h.wndproc(33,0x21,0,0),3)
        h.wndproc(33,0x201,0,0); self.assertEqual(h.drag,(22,13)); h.cursor.return_value=(500,300); tick()
        self.assertEqual(h.position,(478,287)); h.on_move.assert_not_called()
        h.keys=set(); tick(); self.assertIsNone(h.drag); h.on_move.assert_called_once_with((378,187)); self.assertTrue(h.interactive)
    def test_plain_click_does_not_drag(self):
        h,api,tick=self.make_hud(); tick(); h.wndproc(33,0x201,0,0); self.assertIsNone(h.drag)
    def test_alt_tab_during_drag(self):
        h,api,tick=self.make_hud(); tick(); h.locked=False; h.keys={0x01}; tick(); h.wndproc(33,0x201,0,0); h.cursor.return_value=(500,300); tick()
        api.foreground.return_value=2; tick(); self.assertFalse(h.shown); self.assertFalse(h.interactive); self.assertIsNone(h.drag); h.on_move.assert_called_once_with((378,187))
    def test_settings_compatible(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'settings.json'; save(DATA,p); self.assertEqual(load(p),DATA)
            new=dict(DATA,hud_position=[200,200]); save(new,p); self.assertEqual(load(p),new)
            save(dict(DATA,hud_position=['bad',0]),p); self.assertEqual(load(p),DATA)
    def test_style_switch(self):
        h=Hud.__new__(Hud); h.hwnd=33; h.interactive=False; h.u=Mock(); h.u.GetWindowLongW.return_value=0x080800a8; h.u.SetWindowLongW.return_value=0x080800a8
        with patch('hud.c.set_last_error',create=True),patch('hud.c.get_last_error',create=True,return_value=0):
            h.set_interactive(True); h.u.SetWindowLongW.assert_called_with(33,-20,0x08080088)
            h.u.GetWindowLongW.return_value=0x08080088; h.set_interactive(False); h.u.SetWindowLongW.assert_called_with(33,-20,0x080800a8)

if __name__=='__main__':unittest.main()
