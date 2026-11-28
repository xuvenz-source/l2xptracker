import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk
from tracker import App
from history import Archive
from test_v016 import data

class TabbedUITests(unittest.TestCase):
    def test_tabs_and_review_reset(self):
        try:root=tk.Tk()
        except tk.TclError:self.skipTest('No desktop display')
        try:
            root.withdraw()
            with tempfile.TemporaryDirectory() as d:
                archive=Archive(Path(d)/'sessions.sqlite3')
                archive.save('a','First',data(100,20,30))
                with patch('tracker.Windows',side_effect=RuntimeError('test no game')),patch('tracker.Hud',side_effect=RuntimeError('test no HUD')),patch('tracker.Archive',return_value=archive),patch('tracker.load_focus_pause',return_value=False),patch('tracker.load_auto_update',return_value=False),patch('appearance.load_mode',return_value='dark'),patch('party_setup_ui.load_party_choices',return_value=[]),patch('tracker.load_current_party',return_value=[]),patch('tracker.remember_party',return_value=['Alpha']):
                    a=App(root)
                    self.assertEqual(len(a.tabs.tabs()),10)
                    self.assertEqual(len(a.nav_buttons),9)
                    self.assertEqual(a.tabs.cget('style'),'Workspace.TNotebook')
                    self.assertIsInstance(a.tabs,ttk.Notebook)
                    for key in ('history','party','settings','activity','review','progression','loot','monsters','dashboard'):
                        a.navigate(key);a.page_changed();root.update_idletasks()
                        self.assertEqual(a.tabs.select(),str(a.pages[key]))
                    self.assertIs(a.history_window.win,a.pages['history'])
                    self.assertIs(a.party_setup_window.win,a.pages['party'])
                    self.assertIs(a.review_win,a.pages['review'])
                    self.assertIs(a.monster_window.win,a.pages['monsters'])
                    self.assertTrue(a.nav_buttons['dashboard'].instate(['selected']))
                    self.assertEqual(set(a.settings_scroll),{'Tracking','HUD','Player status','Appearance','Updates','Advanced'})
                    a.reviews.add('t','You have earned 8? Adena.')
                    a.refresh_reviews();self.assertEqual(len(a.review_tree.get_children()),1)
                    self.assertTrue(a.restore_session('a'))
                    a.open_monster_reviews();root.update_idletasks()
                    self.assertIs(a.kill_review_window.win,a.pages['kill_review'])
                    self.assertTrue(a.nav_buttons['review'].instate(['selected']))
                    self.assertEqual(len(a.review_tree.get_children()),0)
                    self.assertTrue(a.pages['review'].winfo_exists())
                    a.navigate('party');a.page_changed()
                    self.assertEqual(len(a.party_setup_window.combos),11)
                    a.party_setup_window.slots[0].set('Alpha');a.party_setup_window.apply()
                    self.assertEqual(a.next_party_members,['Alpha'])
                    self.assertEqual(a.tabs.select(),str(a.pages['party']))
                    self.assertFalse(any(isinstance(w,tk.Toplevel) for w in root.winfo_children()))
                    # Main button and queued HUD click share one pause gate.
                    a.running=True;a.session_id=None;a.started=None;a.pause_btn.configure(state='normal')
                    a.pause_btn.invoke();self.assertTrue(a.pause_gate.snapshot()[0])
                    a.queue_hud_pause();a.process_inbox();self.assertFalse(a.pause_gate.snapshot()[0])
                    self.assertEqual(a.pause_btn.cget('text'),'Pause')
                    a.running=False
        finally:root.destroy()
