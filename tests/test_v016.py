import tempfile, unittest
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
from history import Archive, rate, totals_for, review_queue, snapshot
from review import ReviewQueue
from tracker import parse, App
from unittest.mock import Mock, patch


def data(seconds, xp, ad, ts='2026-11-27T01:00:00'):
    return dict(start=ts,end=ts,seconds=seconds,events=[(ts,'xp','You','XP / SP',xp,9,'XP'),(ts,'adena','You','Adena',ad,0,'Adena'),(ts,'item','ExamplePartyMember','Suede',1,0,'loot')],raw=[],reviews=[],next_review=1,gaps=0,complete=True)

class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'sessions.sqlite3';self.a=Archive(self.path)
        self.a.save('a','First',data(3600,1000,2000));self.a.save('b','Second',data(7200,8000,10000,'2026-11-27T03:00:00'))
    def test_reopen_disk(self):
        s=Archive(self.path).summary('a');self.assertEqual(s['totals']['You','Adena'],2000);self.assertEqual(s['seconds'],3600)
    def test_rename_survives_checkpoint(self):
        self.a.rename('a','Dre Vanul');self.a.save('a','Default',data(3610,1001,2001));self.assertEqual(self.a.summary('a')['name'],'Dre Vanul')
    def test_weighted_merge(self):
        i=self.a.merge(['a','b'],'Dre Vanul total');s=self.a.summary(i);self.assertEqual(s['seconds'],10800);self.assertEqual(rate(s['totals']['You','XP / SP'],s['seconds']),'3,000');self.assertEqual(rate(s['totals']['You','Adena'],s['seconds']),'4,000');self.assertEqual(s['totals']['ExamplePartyMember','Suede'],2);self.assertEqual(len(self.a.records()),3)
    def test_nested_merge_no_double_count(self):
        g=self.a.merge(['a','b'],'Group');self.a.save('c','Third',data(100,20,30));h=self.a.merge([g,'a','c'],'Combined');s=self.a.summary(h);self.assertEqual(set(s['sources']),{'a','b','c'});self.assertEqual(s['totals']['You','Adena'],12030);self.assertEqual(s['seconds'],10900)
    def test_single_duplicate_rejected(self):
        with self.assertRaises(ValueError):self.a.merge(['a','a'],'Duplicate')
    def test_merge_updates_after_review(self):
        d=data(3600,221,85);d['events'][0]=(d['start'],'xp','You','XP / SP',221,None,'partial');d['reviews']=[dict(id=1,timestamp=d['start'],text='uncertain',event_index=0,xp_counted=221)];d['next_review']=2
        self.a.save('a','First',d);g=self.a.merge(['a','b'],'Group');self.assertEqual(self.a.summary(g)['pending'],1)
        restored=self.a.records()['a']['data'];q=review_queue(restored);events=[tuple(e) for e in restored['events']];totals=totals_for(events);q.approve(1,'You have acquired 221 XP and 9 SP.',parse,events,totals);restored['events']=events;restored['reviews']=[];self.a.save('a','First',restored)
        s=self.a.summary(g);self.assertEqual(s['pending'],0);self.assertEqual(s['totals']['You','XP / SP'],8221);self.assertEqual(s['totals']['You','SP'],18)
    def test_invalid_name(self):
        with self.assertRaises(ValueError):self.a.rename('a',' ')
    def test_zero_rate(self):self.assertEqual(rate(100,0),'—')
    def test_snapshot_checkpoint(self):
        app=SimpleNamespace(session_date='start',session_end=None,session_complete=None,active_seconds=55,events=[],raw=[],gaps=1,reviews=ReviewQueue(),running=True,pending=2)
        app.reviews.add('t','uncertain');d=snapshot(app);self.assertFalse(d['complete']);self.assertEqual(d['seconds'],55);self.assertEqual(review_queue(d).next_id,2)
    def test_final_save_updates_same_id(self):
        d=data(10,100,20);d['complete']=False;self.a.save('a','First',d);d['complete']=True;d['seconds']=20;self.a.save('a','First',d);self.assertEqual(len(self.a.records()),2);self.assertTrue(self.a.summary('a')['complete']);self.assertEqual(self.a.summary('a')['seconds'],20)
    def test_failed_save_keeps_session(self):
        app=App.__new__(App);app.session_id='a';app.archive=Mock();app.archive.save.side_effect=OSError('disk full');app.session_date='start';app.session_end=None;app.session_complete=None;app.active_seconds=1;app.events=[];app.raw=[];app.gaps=0;app.reviews=ReviewQueue();app.running=False;app.pending=0
        with patch('tracker.messagebox.showerror'):self.assertFalse(app.save_session())
        self.assertEqual(app.session_id,'a')
