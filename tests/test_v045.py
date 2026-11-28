import unittest,tempfile,queue
from pathlib import Path
from collections import Counter
from unittest.mock import Mock,patch
import numpy as np
from party import roster,report,load_party_choices,load_current_party,remember_party
from preferences import write_preference,read_preferences
from history import Archive
from tracker import App
from session_pause import PauseGate

class LivePartyTests(unittest.TestCase):
    def test_eleven_slots_and_migration(self):
        self.assertEqual(len(roster(','.join('P'+str(i) for i in range(11)))),11)
        with self.assertRaises(ValueError):roster(','.join('P'+str(i) for i in range(12)))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prefs.json';write_preference('party_presets',{'Duo':['Alpha'],'Other':['alpha','Beta']},p)
            self.assertEqual(load_party_choices(p),['Alpha','Beta'])
            remember_party(['Gamma'],p);self.assertEqual(load_party_choices(p),['Alpha','Beta','Gamma'])
            self.assertEqual(load_current_party(p),['Gamma'])
            self.assertIn('party_presets',read_preferences(p))
            remember_party([],p);self.assertEqual(load_current_party(p),[])
    def part(self):
        def event(ts,q):return (ts,'adena','You','Adena',q,0,'reward')
        # Delayed review appended out of chronological order.
        return dict(start='2026-11-28T00:00:00',end='2026-11-28T00:04:00',seconds=240,party_members=['Beta'],
            party_periods=[dict(at='',seconds=0,members=[]),dict(at='2026-11-28T00:01:00.000001',seconds=60,members=['Alpha']),dict(at='2026-11-28T00:02:00.000001',seconds=120,members=['Alpha','Beta']),dict(at='2026-11-28T00:03:00.000001',seconds=180,members=['Beta'])],
            events=[event('2026-11-28T00:00:59.900000',50),event('2026-11-28T00:01:10.000000',100),event('2026-11-28T00:03:30.000000',300),event('2026-11-28T00:02:10.000000',200)],raw=[],reviews=[],next_review=1,gaps=0,complete=True)
    def test_membership_periods_and_late_review(self):
        part=self.part();r=report([part])
        self.assertEqual(r['estimated_party'],1400)
        self.assertEqual(r['seconds'],180)
        self.assertEqual([(x['name'],x['estimate'],x['seconds']) for x in r['rows']],[('Alpha',300,120),('Beta',500,120)])
        with tempfile.TemporaryDirectory() as d:
            a=Archive(Path(d)/'history.db');a.save('a','A',part)
            self.assertEqual(a.summary('a')['party'],r)
    def test_live_change_preserves_running_session(self):
        a=App.__new__(App);a.running=True;a.pending=2;a.update_busy=False;a.pause_gate=PauseGate()
        a.party_members=[];a.party_periods=[dict(at='',seconds=0,members=[])];a.active_seconds=60;a.party_status=Mock();a.refresh_totals=Mock();a.save_session=Mock();a.stop=Mock()
        with patch('tracker.remember_party'):
            a.apply_party_members(['Alpha']);a.apply_party_members(['Alpha']);a.apply_party_members([])
        self.assertEqual(len(a.party_periods),3);self.assertEqual(a.party_periods[1]['seconds'],60)
        self.assertTrue(a.running);a.stop.assert_not_called();self.assertEqual(a.next_party_members,[])
    def test_worker_preserves_capture_timestamps(self):
        a=App.__new__(App);a.inbox=queue.Queue();a.session_colours={'xp':'#FF00FF'};jobs=queue.Queue()
        for ts in ['a','b']:jobs.put((ts,np.zeros((1,21,100,3),np.uint8)))
        jobs.put(None)
        with patch('tracker.configured_ocr_rows',return_value=[('line','You have earned 10 Adena.')]):a.worker(jobs)
        self.assertEqual([v[0] for k,v in list(a.inbox.queue) if k=='line'],['a','b'])
