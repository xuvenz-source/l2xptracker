import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from preferences import load_auto_update,save_auto_update,save_focus_pause,load_focus_pause,failed_update,mark_failed_update
from update_ui import UpdateUI

class AutoUpdateTests(unittest.TestCase):
    def test_preferences_preserve_each_other(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prefs.json'
            self.assertTrue(load_auto_update(p))
            save_focus_pause(True,p);save_auto_update(False,p)
            self.assertTrue(load_focus_pause(p));self.assertFalse(load_auto_update(p))
            mark_failed_update('0.99',p)
            self.assertEqual(failed_update(p),'0.99')
            self.assertFalse(load_auto_update(p));self.assertTrue(load_focus_pause(p))
    def ui(self):
        u=UpdateUI.__new__(UpdateUI);u.app=Mock()
        u.app.running=False;u.app.pending=0;u.app.selecting=False;u.app.closing=False;u.app.update_busy=False;u.app.reset_request=None
        u.app.auto_update=True;u.app.root.grab_current.return_value=None;u.app.root.winfo_children.return_value=[]
        u.checking=False;u.available={'version':'0.99','notes':''};u.attempted=set();u.failed_version=''
        u.begin_install=Mock();u.button=Mock()
        return u
    def test_auto_when_idle(self):
        u=self.ui();u.maybe_auto_install();u.begin_install.assert_called_once_with(u.available)
    def test_manual_mode(self):
        u=self.ui();u.app.auto_update=False;u.maybe_auto_install();u.begin_install.assert_not_called()
    def test_defers_while_busy(self):
        for name,value in [('running',True),('pending',1),('selecting',True),('closing',True),('update_busy',True)]:
            with self.subTest(name=name):
                u=self.ui();setattr(u.app,name,value);u.maybe_auto_install();u.begin_install.assert_not_called()
                setattr(u.app,name,False);u.maybe_auto_install();u.begin_install.assert_called_once()
    def test_defers_session_rollover(self):
        u=self.ui();u.app.reset_request={'pitch':19};u.maybe_auto_install();u.begin_install.assert_not_called()
        u.app.reset_request=None;u.maybe_auto_install();u.begin_install.assert_called_once()
    def test_defers_dialog(self):
        u=self.ui();u.app.root.grab_current.return_value=object()
        u.maybe_auto_install();u.begin_install.assert_not_called()
    def test_no_repeat(self):
        u=self.ui();u.attempted.add('0.99');u.maybe_auto_install();u.begin_install.assert_not_called()
        u.attempted.clear();u.failed_version='0.99';u.maybe_auto_install();u.begin_install.assert_not_called()
        u.available={'version':'1.00'};u.maybe_auto_install();u.begin_install.assert_called_once_with(u.available)
    def test_save_failure(self):
        u=self.ui();u.app.save_session.return_value=False
        UpdateUI.begin_install(u,u.available)
        self.assertFalse(u.app.update_busy);self.assertIn('0.99',u.attempted)
