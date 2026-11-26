import unittest, tempfile
from collections import Counter
from pathlib import Path
from history import count_kills, rate, Archive, totals_for
from tracker import parse
from review import ReviewQueue
from test_v016 import data
from test_v08 import DragTests

class KillTests(unittest.TestCase):
    def test_repeat_and_non_xp(self):
        xp=('t','xp','You','XP / SP',221,9,'XP')
        self.assertEqual(count_kills([xp,xp,('t','adena','You','Adena',75,0,'loot'),('t','xp','Other','XP / SP',221,9,'XP')]),2)
    def test_partial_and_review(self):
        q=ReviewQueue()
        events=[('t','xp','You','XP / SP',None,9,'partial'),('t','xp','You','XP / SP',221,None,'partial')]
        totals=totals_for(events)
        self.assertEqual(count_kills(events),2)
        a=q.add('t','partial',0,None,9)
        b=q.add('t','partial',1,221,None)
        q.approve(a.id,'You have acquired 221 XP and 9 SP.',parse,events,totals)
        q.approve(b.id,'You have acquired 221 XP and 9 SP.',parse,events,totals)
        self.assertEqual(count_kills(events),2)
        c=q.add('t','uncertain')
        q.approve(c.id,'You have acquired 221 XP and 9 SP.',parse,events,totals)
        self.assertEqual(count_kills(events),3)
        with self.assertRaises(ValueError):q.approve(c.id,'You have acquired 221 XP and 9 SP.',parse,events,totals)
        self.assertEqual(count_kills(events),3)
    def test_history_merge(self):
        with tempfile.TemporaryDirectory() as d:
            arc=Archive(Path(d)/'history.sqlite3')
            a=data(1800,221,85); b=data(3600,261,92)
            a['events'].append(a['events'][0])
            arc.save('a','a',a);arc.save('b','b',b)
            self.assertEqual(arc.summary('a')['kills'],2)
            m=arc.merge(['a','b'],'both');s=arc.summary(m)
            self.assertEqual(s['kills'],3)
            self.assertEqual(rate(s['kills'],s['seconds']),'2')
    def test_hud(self):
        h,api,tick=DragTests().make_hud()
        from test_v08 import TARGET, REG
        h.update(api,TARGET,REG,True,1800,1000,5000,90)
        self.assertEqual(h.values,('2,000','10,000','180'))
