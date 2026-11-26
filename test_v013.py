import unittest
from collections import Counter
from review import ReviewQueue,candidates
from tracker import parse,xp_numeric_candidate

class ReviewTests(unittest.TestCase):
    def setUp(self):self.q=ReviewQueue(); self.events=[]; self.totals=Counter()
    def approve(self,r,text):return self.q.approve(r.id,text,parse,self.events,self.totals)
    def test_adena_correction(self):
        r=self.q.add('t','You have eamed 8&5 Adena. [numeric OCR: (blank) | 85]')
        self.assertEqual(candidates(r,parse,xp_numeric_candidate),['You have earned 85 Adena.'])
        self.approve(r,'You have earned 85 Adena.'); self.assertEqual(self.totals['You','Adena'],85)
        self.assertEqual(self.events[0][0],'t'); self.assertFalse(self.q.pending)
        with self.assertRaises(ValueError):self.approve(r,'You have earned 85 Adena.')
        self.assertEqual(self.totals['You','Adena'],85)
    def test_conflict(self):
        r=self.q.add('t','You have acquired 221 XP and 8 SP, [XP retry: You have acquired 221 XP and 9 SP,]')
        self.assertEqual(candidates(r,parse,xp_numeric_candidate),['You have acquired 221 XP and 8 SP.','You have acquired 221 XP and 9 SP.'])
        self.approve(r,'You have acquired 221 XP and 9 SP.'); self.assertEqual(self.totals['You','XP / SP'],221); self.assertEqual(self.totals['You','SP'],9)
    def test_partial(self):
        self.events.append(('t','xp','You','XP / SP',221,None,'partial')); self.totals['You','XP / SP']=221
        r=self.q.add('t','You have acquired 221 XP; SP unknown. [SP conflict: You have acquired 221 XP and 8 SP. | You have acquired 221 XP and 9 SP.]',0,221)
        self.assertEqual(len(candidates(r,parse,xp_numeric_candidate)),2)
        with self.assertRaises(ValueError):self.approve(r,'You have acquired 222 XP and 9 SP.')
        self.approve(r,'You have acquired 221 XP and 9 SP.'); self.assertEqual(self.totals['You','XP / SP'],221);self.assertEqual(self.totals['You','SP'],9);self.assertEqual(len(self.events),1);self.assertEqual(self.events[0][5],9)
    def test_distinct_identical(self):
        a=self.q.add('t','85?'); b=self.q.add('t','85?'); self.assertNotEqual(a.id,b.id)
        for r in (a,b):self.approve(r,'You have earned 85 Adena.')
        self.assertEqual(self.totals['You','Adena'],170)
    def test_invalid_does_not_remove(self):
        r=self.q.add('t','unknown')
        for s in ('combat message','You have earned 0 Adena.'):
            with self.assertRaises(ValueError):self.approve(r,s)
        self.assertIn(r.id,self.q.pending); self.assertFalse(self.events)
    def test_dismiss(self):
        r=self.q.add('t','unknown'); self.q.discard(r.id); self.assertFalse(self.q.pending); self.assertFalse(self.events)
    def test_party(self):
        r=self.q.add('t','ExamplePartyMember has obtained Suede.'); self.approve(r,'ExamplePartyMember has obtained 2 Suede.'); self.assertEqual(self.totals['ExamplePartyMember','Suede'],2)
    def test_no_unreadable_guess(self):
        r=self.q.add('t','You have earned S?/ Adena. [numeric OCR: (blank) | (blank)]'); self.assertEqual(candidates(r,parse,xp_numeric_candidate),[])
