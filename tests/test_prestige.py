import unittest
import tkinter as tk
from unittest.mock import patch
from appearance import Appearance,Dashboard,RateTrend,ProgressRing,trend_values

class PrestigeTests(unittest.TestCase):
    def test_rate_series(self):
        self.assertEqual(trend_values(1800,5000,1000,90),(10000,2000,180))
        self.assertEqual(trend_values(0,1,1,1),(0,0,0))
    def test_dashboard_and_charts(self):
        try:root=tk.Tk()
        except tk.TclError:self.skipTest('No display')
        try:
            root.withdraw()
            with patch('appearance.load_mode',return_value='dark'):a=Appearance(root)
            cards=Dashboard(root,with_eta=True);cards.pack()
            trend=RateTrend(root,a);trend.pack()
            ring=ProgressRing(root,a);ring.pack()
            cards.update_metrics(1800,1000,5000,90,100,1,'1h 08m','115')
            self.assertEqual(cards.values[3].get(),'1h 08m')
            self.assertEqual(cards.values[0].get(),'1,800')
            self.assertEqual(cards.labels[0].get(),'NET ADENA / HR*')
            trend.sample('a',1,1,True,2,3);trend.sample('a',31,100,True,200,5)
            self.assertEqual(len(trend.points),2)
            for i in range(3):trend.select(i);self.assertEqual(trend.series,i)
            trend.sample('b',0,0,False);self.assertEqual(trend.points,[])
            ring.update_metrics('19','58.4%','2,500','1h 08m')
            for mode in ('light','dark'):a.apply(mode);root.update_idletasks()
            self.assertEqual(ring.data,('19','58.4%','2,500','1h 08m'))
        finally:root.destroy()
