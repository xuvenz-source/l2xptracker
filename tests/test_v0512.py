import unittest
from sp_forecast import reward_stats,kills_until_level,kills_label,project
from hud_layout import clean,panel_config,PRESETS,WIDGETS,geometry

def reward(xp,sp,who='You',kind='xp'):
    return ('a',kind,who,'XP / SP',xp,sp,'')

class KillsLeftTests(unittest.TestCase):
    def test_mixed_rewards_and_rounding(self):
        s=reward_stats([reward(100,10)]*10+[reward(50,5)]*5)
        self.assertEqual(kills_until_level(s,5000),60)
        self.assertEqual(kills_until_level(s,5001),61)
        self.assertEqual(project(s,5000)['kills'],60)
    def test_sp_not_required_and_missing_xp_excluded(self):
        s=reward_stats([reward(100,10),reward(200,None),reward(None,10),reward(1000,100,'Friend'),reward(500,0,kind='item')])
        self.assertEqual(s['xp_sample'],2)
        self.assertEqual(kills_until_level(s,301),3)
        self.assertEqual(project(s,301)['kills'],4)
    def test_waiting_cap_and_stale(self):
        s=reward_stats([])
        self.assertEqual(kills_label(s,None),'—')
        self.assertEqual(kills_label(s,100),'Calc…')
        self.assertEqual(kills_label(s,0,True),'MAX')
        s=reward_stats([reward(353,None)])
        self.assertEqual(kills_label(s,129640,stale=True),'~368*')
        self.assertEqual(kills_label(s,0),'~0')
    def test_layout_and_preset(self):
        self.assertIn('killsnext',WIDGETS)
        self.assertIn('killsnext',PRESETS['Leveling'])
        old=clean(dict(enabled=['xp','ad']))
        self.assertEqual(old['enabled'],['ad','xp'])
        c=dict(enabled=['xp','ad','killsnext'])
        self.assertIn('killsnext',panel_config(c,'progression')['enabled'])
        self.assertNotIn('killsnext',panel_config(c,'loot')['enabled'])
        self.assertEqual(len(geometry(panel_config(c,'progression'))['cells']),2)
