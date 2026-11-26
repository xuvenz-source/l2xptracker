import unittest
from collections import Counter
from review import ReviewQueue,review_fields,correction_message
from tracker import parse,xp_numeric_candidate
from history import count_kills

class NumericReviewTests(unittest.TestCase):
    def setUp(self):self.q=ReviewQueue();self.events=[];self.totals=Counter()
    def fields(self,r):return review_fields(r,parse,xp_numeric_candidate)
    def approve(self,r,kind,**kw):
        self.q.approve(r.id,correction_message(r,kind,**kw),parse,self.events,self.totals)
    def test_conflicting_values(self):
        r=self.q.add('t','You have acquired 221 XP and 8 SP, [XP retry: You have acquired 221 XP and 9 SP,]')
        f=self.fields(r);self.assertEqual((f['kind'],f['xp'],f['sp']),('xp','221',''))
        self.approve(r,'xp',xp=f['xp'],sp='9')
        self.assertEqual(self.totals['You','XP / SP'],221);self.assertEqual(count_kills(self.events),1)
    def test_partial_xp(self):
        self.events.append(('t','xp','You','XP / SP',221,None,'partial'));self.totals['You','XP / SP']=221
        r=self.q.add('t','You have acquired 221 XP; SP unknown.',0,221)
        self.assertEqual(self.fields(r)['xp'],'221')
        with self.assertRaises(ValueError):self.approve(r,'adena',adena='85',who='You')
        self.approve(r,'xp',xp='999',sp='9')
        self.assertEqual(self.totals['You','XP / SP'],221);self.assertEqual(self.totals['You','SP'],9);self.assertEqual(count_kills(self.events),1)
    def test_partial_sp(self):
        self.events.append(('t','xp','You','XP / SP',None,9,'partial'));self.totals['You','SP']=9
        r=self.q.add('t','SP counted; XP unknown.',0,None,9)
        self.approve(r,'xp',xp='221',sp='999')
        self.assertEqual(self.totals['You','SP'],9);self.assertEqual(self.totals['You','XP / SP'],221);self.assertEqual(count_kills(self.events),1)
    def test_adena(self):
        r=self.q.add('t','You have eamed 8&5 Adena. [numeric OCR: (blank) | 85]')
        f=self.fields(r);self.assertEqual((f['kind'],f['adena'],f['who']),('adena','85','You'))
        self.approve(r,'adena',adena='1,085',who=f['who'])
        self.assertEqual(self.totals['You','Adena'],1085)
        with self.assertRaises(ValueError):self.approve(r,'adena',adena='85',who='You')
    def test_party(self):
        r=self.q.add('t','Alpha has earned 8? Adena.')
        f=self.fields(r);self.assertEqual((f['kind'],f['who']),('adena','Alpha'))
        self.approve(r,'adena',adena='85',who=f['who'])
        self.assertEqual(self.totals['Alpha','Adena'],85);self.assertEqual(self.totals['You','Adena'],0)
    def test_invalid(self):
        r=self.q.add('t','unknown')
        for v in ('','-1','1.5','7/5','0','1,2'):
            with self.assertRaises(ValueError):self.approve(r,'adena',adena=v,who='You')
        with self.assertRaises(ValueError):self.approve(r,'adena',adena='85',who='')
        self.assertIn(r.id,self.q.pending)
        self.approve(r,'xp',xp='221',sp='0')
        self.assertEqual(self.totals['You','SP'],0)
    def test_item_fallback(self):
        r=self.q.add('t','Alpha has obtained Suede.')
        f=self.fields(r);self.assertEqual(f['kind'],'item')
        self.approve(r,'item',full='Alpha has obtained 2 Suede.')
        self.assertEqual(self.totals['Alpha','Suede'],2)
