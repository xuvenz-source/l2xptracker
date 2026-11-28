import unittest,queue
from collections import Counter
from unittest.mock import Mock
from session_pause import PauseGate
from tracker import App
from review import ReviewQueue
from hud import RESET_RECT
import test_v08

class ResetTests(unittest.TestCase):
    def app(self):
        a=App.__new__(App);a.running=True;a.pending=2;a.closing=False;a.update_busy=False
        a.reset_request=None;a.run_id=8;a.session_pitch=19;a.session_colours={'xp':'#FF00FF'}
        a.session_prices={'shot':'4'};a.session_loot_prices={'suede':'50'};a.party_members=['Friend'];a.pause_gate=PauseGate()
        a.inbox=queue.Queue();a.status=Mock();a.hud=None;a.halt=Mock()
        a.stop_btn=Mock();a.pause_btn=Mock();a.start_btn=Mock();a.reset_btn=Mock()
        a.session_id='old';a.started=None;a.last_archive_save=0;a.events=[];a.raw=[]
        a.totals=Counter();a.reviews=ReviewQueue();a.gaps=0;a.append=Mock();a.refresh_totals=Mock()
        a.save_session=Mock(return_value=True);a.start=Mock();a.history_window=None
        return a
    def test_reset_waits_for_both_workers_and_saves_buffer(self):
        a=self.app();a.pause_gate.toggle();a.reset_session()
        self.assertFalse(a.running);self.assertTrue(a.reset_request['paused']);a.halt.set.assert_called_once()
        a.reset_session();a.halt.set.assert_called_once()
        a.inbox.put(('done','capture'));a.process_inbox();a.start.assert_not_called()
        a.inbox.put(('line',('t','You have acquired 221 XP and 9 SP.')))
        a.inbox.put(('done','ocr'));a.process_inbox()
        a.save_session.assert_called_once_with(quiet=False)
        self.assertEqual(a.totals['You','XP / SP'],221)
        a.start.assert_called_once_with(rollover=dict(pitch=19,colours={'xp':'#FF00FF'},prices={'shot':'4'},loot_prices={'suede':'50'},party=['Friend'],paused=True))
        self.assertIsNone(a.reset_request)
    def test_failed_save_cancels_reset(self):
        a=self.app();a.save_session.return_value=False;a.reset_session()
        a.inbox.put(('done','capture'));a.inbox.put(('done','ocr'));a.process_inbox()
        a.start.assert_not_called();self.assertIsNone(a.reset_request)
    def test_stale_hud_reset_ignored(self):
        a=self.app();a.inbox.put(('hud_reset',7))
        a.last_archive_save=float('inf');a.process_inbox();self.assertTrue(a.running)
        a.queue_hud_reset();a.process_inbox();self.assertFalse(a.running)
    def test_hud_reset_click_locked_and_unlocked(self):
        h,api,tick=test_v08.DragTests().make_hud();h.on_reset=Mock();h.on_pause=Mock();tick()
        for locked in (True,False):
            h.locked=locked;l,t,_,_=RESET_RECT
            h.cursor.return_value=(h.position[0]+l+2,h.position[1]+t+2);tick()
            h.keys={1};tick();h.wndproc(33,0x201,0,0);tick()
            self.assertIsNone(h.drag)
            h.keys=set();tick()
        self.assertEqual(h.on_reset.call_count,2);h.on_pause.assert_not_called()
