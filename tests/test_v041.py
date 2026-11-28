import unittest,tempfile
from pathlib import Path
import tkinter as tk
from unittest.mock import patch
from history import Archive
from test_v016 import data
from tracker import App
from scroll_ui import ScrollPage

class ResponsiveTests(unittest.TestCase):
    def test_small_window_history_and_pages(self):
        try:root=tk.Tk()
        except tk.TclError:self.skipTest('No desktop display')
        try:
            with tempfile.TemporaryDirectory() as d:
                archive=Archive(Path(d)/'history.sqlite3');archive.save('a','First',data(100,20,30))
                with patch('tracker.Windows',side_effect=RuntimeError('test')),patch('tracker.Hud',side_effect=RuntimeError('test')),patch('tracker.Archive',return_value=archive),patch('tracker.load_auto_update',return_value=False):
                    app=App(root);root.geometry('850x600');root.update_idletasks()
                    app.navigate('history');app.page_changed();root.update_idletasks()
                    h=app.history_window;h.refresh(['a']);root.update_idletasks()
                    self.assertIn('First',h.summary_text.get('1.0','end'))
                    self.assertTrue(h.summary_text.winfo_ismapped())
                    self.assertGreater(h.summary_text.winfo_height(),15)
                    h.details.set('\n'.join('Detail '+str(i) for i in range(50)));root.update_idletasks()
                    h.summary_text.yview_moveto(1);self.assertAlmostEqual(h.summary_text.yview()[1],1)
                    self.assertTrue(h.tree.cget('xscrollcommand'))
                    h.detail_tabs.select(1);root.update_idletasks();self.assertTrue(h.loot.winfo_ismapped())
                    app.navigate('dashboard');root.update_idletasks()
                    self.assertIsInstance(app.dashboard_scroll,ScrollPage)
                    self.assertTrue(app.updates.button.winfo_ismapped())
                    self.assertLessEqual(app.updates.button.winfo_rooty()+app.updates.button.winfo_height(),root.winfo_rooty()+root.winfo_height())
                    app.dashboard_scroll.canvas.yview_moveto(1);root.update_idletasks()
                    self.assertAlmostEqual(app.dashboard_scroll.canvas.yview()[1],1)
                    app.navigate('settings');root.update_idletasks()
                    for page in app.settings_scroll.values():self.assertIsInstance(page,ScrollPage)
        finally:root.destroy()
