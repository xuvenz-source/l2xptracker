import unittest
from unittest.mock import Mock,patch
from hud_layout import geometry
from hud_pair import HudPair
from hud import Hud
from tracker import App
from drop_ui import DropEditor
from test_v036 import ResetTests

class LootButtonTests(unittest.TestCase):
    def test_button_geometry(self):
        for count in (0,1,12):
            for footer in (True,False):
                g=geometry(dict(enabled=['ad'],status=footer,pause=footer,reset=footer),'ADENA / LOOT',count,True)
                l,t,r,b=g['select_loot']
                self.assertGreaterEqual(t,g['detail_y']+count*21)
                self.assertLessEqual(b,g['height']-(32 if footer else 0))
                self.assertLessEqual(r,g['width'])
        self.assertIsNone(geometry({},'XP / SP')['select_loot'])
    def test_locked_and_unlocked_button_is_not_drag(self):
        h=Hud.__new__(Hud);h.layout=geometry({},'ADENA / LOOT',0,True)
        h.shown=True;h.position=(100,100);h.placement=None;h.drag=None;h.lock_first=None
        h.on_select_loot=Mock();h.on_pause=Mock();h.on_reset=Mock();h.on_settings=Mock()
        l,t,_,_=h.layout['select_loot'];point=(100+l+2,100+t+2)
        for locked in (True,False):
            h.locked=locked;h.press_handled=False
            self.assertTrue(h.wants_input(point));self.assertFalse(h.body_hit(point))
            h.handle_press(point);h.handle_press(point)
            self.assertIsNone(h.drag);self.assertEqual(h.locked,locked)
        self.assertEqual(h.on_select_loot.call_count,2)
        h.on_pause.assert_not_called();h.on_reset.assert_not_called();h.on_settings.assert_not_called()
    def test_run_tagged_callback(self):
        a=ResetTests().app();a.last_archive_save=float('inf');a.capture_drop_window=Mock()
        a.inbox.put(('select_loot',a.run_id-1));a.process_inbox();a.capture_drop_window.assert_not_called()
        a.queue_select_loot();a.capture_drop_window.assert_not_called()
        a.process_inbox();a.capture_drop_window.assert_called_once_with()
    def test_replacement_cancel_preserves_old_table(self):
        e=DropEditor.__new__(DropEditor);e.busy=False;e.win=Mock();e.app=Mock()
        e.app.drop_config=dict(monster='Old',rows=[dict(name='Old item',group='1',chance='1')],selected=[0],rate='100')
        e.rows=[dict(name='New item',group='2',chance='3')];e.committed_text='New item\t2\t3'
        e.table=Mock();e.table.get.return_value=e.committed_text;e.list=Mock();e.list.curselection.return_value=(0,)
        e.monster=Mock();e.monster.get.return_value='New';e.rate=Mock();e.rate.get.return_value='';e.status=Mock()
        original=e.app.drop_config
        with patch('drop_ui.messagebox.askyesno',return_value=False),patch('drop_ui.save') as save:e.apply()
        save.assert_not_called();self.assertIs(e.app.drop_config,original);e.win.destroy.assert_not_called()
        with patch('drop_ui.messagebox.askyesno',return_value=True),patch('drop_ui.save') as save:e.apply()
        self.assertEqual(e.app.drop_config['monster'],'New');save.assert_called_once_with(e.app.drop_config)
        e.win.destroy.assert_called_once()
