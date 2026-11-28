import unittest
from collections import Counter
from decimal import Decimal
from unittest.mock import Mock,patch
from leveling import Progress,manual_values,xp_after
from player_ui import PlayerStatus
from tracker import App

class QuickProgressTests(unittest.TestCase):
    def test_validation(self):
        self.assertEqual(manual_values('19','18.89%',60),(19,Decimal('18.89')))
        for lv,pct in [('0','20'),('61','20'),('19','101'),('19','NaN'),('19','-1'),('19.5','10')]:
            with self.assertRaises(ValueError):manual_values(lv,pct,60)
    def test_delayed_rewards(self):
        events=[('before','xp','You','XP / SP',353,14,''),('later','xp','You','XP / SP',353,14,''),('later','xp','Friend','XP / SP',353,14,''),('later','xp','You','XP / SP',None,14,'')]
        self.assertEqual(xp_after(events,'first'),353)
        p=Progress();p.manual(19,Decimal('18.89'),0);p.advance(xp_after(events,'first'),60)
        self.assertEqual(round(p.percent,2),Decimal('19.11'))
    def test_apply_uses_existing_state_and_invalidates_auto(self):
        p=PlayerStatus.__new__(PlayerStatus);p.app=Mock();p.app.running=True;p.app.pending=2;p.app.run_id=5
        p.app.totals=Counter({('You','XP / SP'):10000});p.config=dict(mode='auto',cap=60)
        p.progress=Progress();p.mode=Mock();p.level=Mock();p.percent=Mock();p.save=Mock();p.tick=Mock();p.generation=7
        p.apply_manual_values('19','18.89')
        self.assertEqual(p.config['mode'],'manual');self.assertEqual(p.progress.level,19);self.assertEqual(p.progress.percent,Decimal('18.89'))
        self.assertEqual(p.progress.baseline,0);self.assertIsNotNone(p.manual_anchor);self.assertEqual(p.generation,8)
        p.tick.assert_called_once();p.app.record_monster_context.assert_called_once()
        self.assertEqual(p.app.totals['You','XP / SP'],10000)
        self.assertEqual(p.app.run_id,5)
    def test_invalid_input_keeps_original_progress(self):
        p=PlayerStatus.__new__(PlayerStatus);p.app=Mock();p.config=dict(mode='auto',cap=60);p.progress=Progress()
        with self.assertRaises(ValueError):p.apply_manual_values('19','101')
        self.assertEqual(p.config['mode'],'auto');self.assertIsNone(p.progress.level)
    def test_hud_route_guards(self):
        a=App.__new__(App);a.running=True;a.player=Mock();a.open_quick_player_progress()
        a.player.open_quick_manual.assert_called_once()
        a.selecting=True;a.open_quick_player_progress()
        a.player.open_quick_manual.assert_called_once()
        a.selecting=False;a.player.protected.return_value=(1,2);a.enable_player_ocr()
        a.player.enable_auto.assert_called_once()
