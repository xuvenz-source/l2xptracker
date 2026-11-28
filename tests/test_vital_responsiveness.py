import unittest
from unittest.mock import patch,Mock
import numpy as np
from vitals import vital_signature,read_vital_pair
from vital_monitor import VitalMonitor,CACHE_LIMIT
from leveling import binding_for
from test_v06 import TARGET

def digits():
    a=np.zeros((12,246,3),np.uint8)
    a[2:10,100:104]=255;a[2:10,109:113]=255;a[2:10,118:122]=255
    return a

class VitalResponsivenessTests(unittest.TestCase):
    def test_signature(self):
        a=digits();b=a.copy();b[3,101]=0
        self.assertNotEqual(vital_signature(a),vital_signature(b))
        b=a.copy();b[:,:50]=35
        self.assertEqual(vital_signature(a),vital_signature(b))
        self.assertNotEqual(vital_signature(np.zeros_like(a)),vital_signature(a))
    def test_preserve_consensus(self):
        with patch('pytesseract.image_to_string',side_effect=['58/187']*3) as ocr:
            self.assertEqual(read_vital_pair(digits(),.31),(58,187))
            self.assertEqual(ocr.call_count,3)
        with patch('pytesseract.image_to_string',side_effect=['58/187','58/187','59/187','58/187','58/187']):
            self.assertIsNone(read_vital_pair(digits(),.31))
    def test_cache_current_pixels_and_fill(self):
        m=VitalMonitor();sig=vital_signature(digits())
        m.remember('hp',sig,(90,100))
        self.assertEqual(m.cached('hp',sig,.92),(90,100))
        self.assertIsNone(m.cached('hp',sig,.8))
        self.assertIsNone(m.cached('mp',sig,.92))
        self.assertIsNone(m.cached('hp',('changed',),.92))
        m.remember('hp',sig,(91,100))
        self.assertIsNone(m.cached('hp',sig,.92))
        m.remember('hp',sig,(90,100))
        self.assertIsNone(m.cached('hp',sig,.92))
        for i in range(CACHE_LIMIT+2):m.remember('hp',i,(90,100))
        self.assertEqual(len(m.cache['hp']),CACHE_LIMIT)
        m.clear_evidence();self.assertFalse(m.cache['hp'])
    def test_old_worker_does_not_display_different_pixels(self):
        m=VitalMonitor();a=Mock();a.target=TARGET;a.running=True;a.selecting=False;a.run_id=1
        a.pause_gate.capture_policy.return_value=(False,0,False)
        config={'binding':binding_for(TARGET),'vitals':{'frame':{},'bars':{}}}
        key=(1,0,1,TARGET.hwnd,TARGET.pid);m.key=key;m.capture_busy=True
        m.sample=(10,{'hp':.92,'mp':None})
        sig=vital_signature(digits());m.latest={'hp':(10,digits(),.92,('new',))}
        m.numbers.put((key,9.8,'hp',sig,.92,(90,100)))
        with patch('vital_monitor.threading.Thread') as worker:
            values=m.tick(a,config,1,10)
        self.assertEqual(values['hp'],('HP','— - ~92%'))
        worker.assert_called_once()
        m.latest={'hp':(10,digits(),.92,sig)}
        self.assertEqual(m.tick(a,config,1,10.1)['hp'],('HP','90/100 - 90%'))
        a.pause_gate.capture_policy.return_value=(True,1,False)
        self.assertEqual(m.tick(a,config,1,10.2)['hp'],('HP','— - —'))
        self.assertFalse(m.cache['hp'])
