"""Exercise the real session tick with identified kills and the Prestige overview."""
import queue,unittest
from collections import Counter
from unittest.mock import Mock,patch
from tracker import App
from monster_library import context
from review import ReviewQueue
from session_pause import PauseGate
from test_v050 import mob,library

class Variable:
    def __init__(self,value=''):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value

class KillDashboardRegression(unittest.TestCase):
    def app(self,with_drops=True):
        a=App.__new__(App)
        a.running=True;a.pending=2;a.closing=False;a.started=None;a.session_id='session'
        a.last_archive_save=float('inf');a.active_seconds=60
        a.inbox=queue.Queue();a.raw=[];a.events=[];a.totals=Counter();a.reviews=ReviewQueue();a.gaps=0
        a.pause_gate=PauseGate();a.hud=None;a.root=Mock();a.status=Mock();a.append=Mock();a.stop=Mock()
        a.tree=Mock();a.tree.get_children.return_value=()
        a.party_members=[];a.party_periods=[];a.current_party_report=Mock()
        p=mob('Pincher');q=mob('Other')
        if not with_drops:
            for profile in (p,q):profile['drop']['selected']=[]
        a.monster_library=library(p,q);a.monster_library['default']=p['id']
        a.monster_tracking=True;a.monster_kills={};a.monster_counts_cache=None;a.drop_config={}
        a.monster_contexts=[dict(at='',context=context(a.monster_library,None,False))]
        a.record_monster_context=Mock()
        a.current_farm=Variable();a.farm_kills=Variable();a.drop_summary=Variable()
        a.overview_drops=[(Variable(),Variable()) for _ in range(3)]
        return a,p
    def test_first_and_subsequent_kills_do_not_stop_tracking(self):
        for with_drops in (True,False):
            with self.subTest(with_drops=with_drops):
                a,p=self.app(with_drops)
                with patch('tracker.party_rows',return_value=[]),patch('tracker.diagnostic') as log:
                    for i in range(3):
                        a.inbox.put(('line',(str(i),'You have acquired 221 XP and 9 SP.')))
                        a.tick()
                        a.stop.assert_not_called()
                        self.assertTrue(a.running)
                        self.assertEqual(a.kills,i+1)
                        self.assertEqual(a.totals['You','XP / SP'],221*(i+1))
                        self.assertIn(f'{i+1} killed',a.drop_summary.get())
                        self.assertIn(p['drop']['monster'],a.drop_summary.get())
                        self.assertIn(f'{i+1} identified kills',a.farm_kills.get())
                    log.assert_not_called()
                self.assertEqual(a.overview_drops[0][0].get(),p['drop']['monster']+' · Ring' if with_drops else 'No targets selected')
    def test_multiple_monsters_and_empty_overview_rows(self):
        a,p=self.app()
        from monster_library import assign
        from test_v050 import event
        q=next(v for k,v in a.monster_library['profiles'].items() if k!=p['id'])
        a.events=[event(),event()];assign(a.monster_kills,a.events,[0],p);assign(a.monster_kills,a.events,[1],q)
        a.update_drop_targets()
        for m in (p,q):self.assertIn(m['drop']['monster']+': 1 killed',a.drop_summary.get())
        self.assertEqual(a.overview_drops[2][0].get(),'')
