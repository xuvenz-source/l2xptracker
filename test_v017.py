import unittest, tempfile
from pathlib import Path
from unittest.mock import patch
from tracker import recover_sp_only, parse_xp_resolution, ocr_rows, parse, xp_numeric_candidate
from review import ReviewQueue, candidates
from history import Archive, totals_for, review_queue
from test_v010 import A, ROWS, batch
from test_v016 import data
from dataclasses import asdict
FIRST=["You have acquired '2G6i=XP and 12 SP.", 'TOCee MEME iRX? and12SP w+', 'You have SagitfeqweiexP and 12 SP.', 'You lave acquired“26ieXP and 12 SP.']
SECOND=['You have acquired 271 XP and 9 SP,', '', 'Yoti havPeapiuitioel: xP and 9 SP,', 'You have acquired.291 XP and 9 SP.']
class IndependentSPTests(unittest.TestCase):
    def test_exact_reports(self):
        for reads,sp in [(FIRST,12),(SECOND,9)]:
            kind,line=recover_sp_only(reads)
            self.assertEqual(kind,'sp_partial')
            self.assertEqual(parse_xp_resolution(kind,line)[3:],(None,sp))
            for t in reads:
                if t:self.assertIn(t,line)
    def test_requires_agreement(self):
        for reads in [['','and 9 SP.'],['and 8 SP.','and 9 SP.'],['and 9 SP.','and 9 SP.','and 8 SP.'],['and 1?2 SP.','and & SP.']]:
            self.assertIsNone(recover_sp_only(reads))
    def test_pipeline(self):
        # Force isolated rows and exact OCR evidence, independently per row.
        with patch('tracker.row_images',return_value=(A,False)),patch('tracker.pytesseract.image_to_data',return_value=batch(FIRST[0],SECOND[0])),patch('tracker.single_ocr',side_effect=FIRST+SECOND):
            events=list(ocr_rows(ROWS))
        self.assertEqual([parse_xp_resolution(*r)[3:] for r in events],[(None,12),(None,9)])
    def test_approval_only_adds_xp(self):
        kind,line=recover_sp_only(SECOND);event=parse_xp_resolution(kind,line)
        events=[('t',*event,line)]; totals=totals_for(events); q=ReviewQueue(); r=q.add('t',line,0,None,9)
        self.assertEqual(totals['You','XP / SP'],0); self.assertEqual(totals['You','SP'],9)
        self.assertEqual(set(candidates(r,parse,xp_numeric_candidate)),{'You have acquired 271 XP and 9 SP.','You have acquired 291 XP and 9 SP.'})
        with self.assertRaises(ValueError):q.approve(r.id,'You have acquired 271 XP and 8 SP.',parse,events,totals)
        q.approve(r.id,'You have acquired 271 XP and 9 SP.',parse,events,totals)
        self.assertEqual((totals['You','XP / SP'],totals['You','SP']),(271,9));self.assertEqual(len(events),1)
        with self.assertRaises(ValueError):q.approve(r.id,'You have acquired 271 XP and 9 SP.',parse,events,totals)
    def test_saved_merge_and_review(self):
        with tempfile.TemporaryDirectory() as d:
            archive=Archive(Path(d)/'sessions.sqlite3'); a=data(3600,100,100); b=data(3600,200,200)
            kind,line=recover_sp_only(FIRST);q=ReviewQueue();r=q.add('t',line,0,None,12);a['events'][0]=('t',*parse_xp_resolution(kind,line),line);a['reviews']=[asdict(r)];a['next_review']=2
            archive.save('a','First',a);archive.save('b','Second',b);m=archive.merge(['a','b'],'Combined');t=archive.summary(m)['totals'];self.assertEqual((t['You','XP / SP'],t['You','SP']),(200,21))
            a=archive.records()['a']['data'];q=review_queue(a);events=[tuple(e) for e in a['events']];t=totals_for(events);q.approve(1,'You have acquired 261 XP and 12 SP.',parse,events,t);a['events']=events;a['reviews']=[];archive.save('a','First',a)
            t=archive.summary(m)['totals'];self.assertEqual((t['You','XP / SP'],t['You','SP']),(461,21))
    def test_old_review_loads(self):
        q=review_queue({'reviews':[dict(id=1,timestamp='t',text='old',event_index=0,xp_counted=221)],'next_review':2});self.assertIsNone(q.pending[1].sp_counted)
