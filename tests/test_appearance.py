import tempfile,unittest
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch
from appearance import load_mode,save_mode,metric_values,Appearance,Dashboard,PALETTES

class AppearanceTests(unittest.TestCase):
    def test_preferences(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'appearance.json'
            self.assertEqual(load_mode(p),'dark')
            save_mode('light',p);self.assertEqual(load_mode(p),'light')
            save_mode('dark',p);self.assertEqual(load_mode(p),'dark')
            p.write_text('invalid')
            self.assertEqual(load_mode(p),'dark')
            with self.assertRaises(ValueError):save_mode('invalid',p)
    def test_rates(self):
        self.assertEqual(metric_values(1800,1000,5000,90),(('2,000','Total 1,000'),('10,000','Total 5,000'),('180','Total 90')))
        self.assertEqual(metric_values(0,0,0,0),(('—','Total 0'),)*3)
    def test_widgets(self):
        try:root=tk.Tk()
        except tk.TclError:self.skipTest('No desktop display')
        try:
            root.withdraw()
            with patch('appearance.load_mode',return_value='dark'):a=Appearance(root)
            cards=Dashboard(root);cards.pack()
            log=tk.Text(root,state='disabled');log.pack()
            popup=tk.Toplevel(root);popup.withdraw()
            ttk.Entry(popup).pack();ttk.Treeview(popup).pack()
            cards.update_metrics(1800,1000,5000,90)
            for mode in ('dark','light','dark'):
                a.apply(mode);root.update_idletasks()
                self.assertEqual(log.cget('background'),PALETTES[mode]['field'])
                self.assertEqual(popup.cget('background'),PALETTES[mode]['bg'])
                self.assertEqual(cards.values[2].get(),'180')
                self.assertEqual(a.style.lookup('Gold.Metric.TLabel','foreground'),PALETTES[mode]['gold'])
        finally:root.destroy()
