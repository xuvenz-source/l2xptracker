import tempfile, unittest
from pathlib import Path
from decimal import Decimal
from unittest.mock import Mock, patch
from collections import Counter
from preferences import load_hud_net_adena,save_hud_net_adena,write_preference
from hud import adena_metric
from tracker import App
import test_v08
from test_v06 import TARGET,REG

class NetHudTests(unittest.TestCase):
    def test_preference(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prefs.json'
            self.assertFalse(load_hud_net_adena(p))
            save_hud_net_adena(True,p);self.assertTrue(load_hud_net_adena(p))
            save_hud_net_adena(False,p);self.assertFalse(load_hud_net_adena(p))
            write_preference('hud_net_adena','true',p);self.assertFalse(load_hud_net_adena(p))
            with self.assertRaises(ValueError):save_hud_net_adena(1,p)
    def test_rates(self):
        self.assertEqual(adena_metric(12000,3600),('ADENA / HR','12,000'))
        self.assertEqual(adena_metric(12000,3600,Decimal('3000')),('NET ADENA/H','9,000'))
        self.assertEqual(adena_metric(100,1800.5,Decimal('150.25'),2),('NET ADENA/H*','-100'))
        self.assertEqual(adena_metric(1,0,Decimal('1')),('NET ADENA/H','—'))
    def test_label_only_change_repaints(self):
        h,api,tick=test_v08.DragTests().make_hud();tick()
        h.u.InvalidateRect.reset_mock()
        h.update(api,TARGET,REG,True,100,20,30,consumable_cost=Decimal(0))
        self.assertEqual(h.adena_label,'NET ADENA/H');self.assertEqual(h.values[0],'720')
        h.u.InvalidateRect.assert_called_once()
        h.update(api,TARGET,REG,True,100,20,30,consumable_cost=Decimal(25),unpriced_uses=1)
        self.assertEqual(h.adena_label,'NET ADENA/H*');self.assertEqual(h.values[0],'-180')
        h.update(api,TARGET,REG,True,100,20,30)
        self.assertEqual(h.adena_label,'ADENA / HR');self.assertEqual(h.values[0],'720')
    def test_app_toggle_and_hud_integration(self):
        a=App.__new__(App);a.hud_net_adena_var=Mock();a.hud_net_adena_var.get.return_value=True
        a.hud=Mock();a.api=Mock();a.target=TARGET;a.region=REG;a.running=True;a.hud_enabled=Mock();a.hud_enabled.get.return_value=True
        a.active_seconds=3600;a.totals=Counter({('You','Adena'):12000,('You','XP / SP'):10000});a.kills=100
        a.pause_gate=Mock();a.pause_gate.snapshot.return_value=(False,0);a.consumable_report={'cost':Decimal('3000.5'),'unpriced':3};a.move_btn=Mock();a.root=Mock()
        with patch('tracker.save_hud_net_adena') as save:
            a.change_hud_net_adena();save.assert_called_once_with(True)
        a.hud_tick();self.assertEqual(a.hud.update.call_args.kwargs['consumable_cost'],Decimal('3000.5'))
        self.assertEqual(a.hud.update.call_args.kwargs['unpriced_uses'],3)
        self.assertEqual(a.totals['You','Adena'],12000)
        a.hud_net_adena=False;a.hud_tick();self.assertIsNone(a.hud.update.call_args.kwargs['consumable_cost'])
