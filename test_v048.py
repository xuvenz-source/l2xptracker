import unittest
from decimal import Decimal
from unittest.mock import Mock,patch
from sp_forecast import parse_balance,reward_stats,project,clean_anchor
from player_ui import PlayerStatus

def event(ts,xp,sp,who='You'):
    return (ts,'xp',who,'XP / SP',xp,sp,'reward')

class SPForecastTests(unittest.TestCase):
    def test_weighted_average_and_projection(self):
        events=[event('a',100,10)]*10+[event('b',50,5)]*5
        stats=reward_stats(events,dict(balance=2000,at=''))
        self.assertEqual(stats['earned'],125);self.assertEqual(stats['average_sp'],Decimal(125)/15)
        self.assertEqual(stats['current'],2125)
        self.assertEqual(project(stats,5000),dict(kills=60,gain=500,total=2625))
    def test_partial_and_other_rewards(self):
        events=[event('a',100,10),event('b',None,8),event('c',200,None),event('d',900,90,'Alpha')]
        stats=reward_stats(events,dict(balance=500,at='a'))
        self.assertEqual((stats['kills'],stats['sample'],stats['earned'],stats['current'],stats['unknown']),(3,1,18,508,1))
        self.assertEqual(project(stats,250),dict(kills=3,gain=25,total=533))
    def test_late_review_does_not_double_count_balance(self):
        anchor=dict(balance=500,at='2026-11-28T12:00:00.500000')
        events=[event('2026-11-28T12:00:01.000000',100,10),event('2026-11-28T12:00:00.100000',100,20)]
        stats=reward_stats(events,anchor)
        self.assertEqual(stats['current'],510);self.assertEqual(stats['earned'],30)
        self.assertEqual(project(stats,100)['total'],525)
    def test_zero_missing_cap_and_validation(self):
        self.assertEqual(parse_balance('0'),0);self.assertEqual(parse_balance('12,345'),12345)
        for value in ('','-1','1.5','1,2','10 SP'): 
            with self.assertRaises(ValueError):parse_balance(value)
        self.assertIsNone(project(reward_stats([]),100))
        r=reward_stats([event('a',100,0)])
        self.assertEqual(project(r,100),dict(kills=1,gain=0,total=None))
        self.assertIsNone(project(r,100,True));self.assertIsNone(project(r,None))
        self.assertIsNone(clean_anchor(dict(balance=True,at='')))
    def test_staged_balance_and_new_session(self):
        p=PlayerStatus.__new__(PlayerStatus);p.app=Mock();p.sp_input=Mock();p.sp_next=1234
        p.begin_sp_session();self.assertEqual(p.app.sp_anchor,dict(balance=1234,at=''))
        self.assertIsNone(p.sp_next);self.assertTrue(p.app.sp_live)
        p.begin_sp_session();self.assertIsNone(p.app.sp_anchor)
    def test_current_balance_during_session(self):
        p=PlayerStatus.__new__(PlayerStatus);p.app=Mock();p.app.running=True;p.app.pending=2
        p.sp_input=Mock();p.sp_input.get.return_value='5,000';p.sp_cache={}
        p.set_sp_balance();self.assertEqual(p.app.sp_anchor['balance'],5000);self.assertTrue(p.app.sp_anchor['at'])
        self.assertIsNone(p.sp_cache);p.app.save_session.assert_called_once_with(quiet=True)
