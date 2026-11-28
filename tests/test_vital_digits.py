"""Regression masks from three supplied compact player-frame screenshots.

Only thresholded numerical crops are stored. No background or player name.
The first frame supplies the slash; other frames verify distinct values.
"""
import base64,zlib,unittest
from unittest.mock import Mock,patch
import numpy as np
from vital_digits import recognise_vital_pair,decode,LOOKUP
from vital_monitor import VitalMonitor
from leveling import binding_for
from test_v06 import TARGET

SAMPLES=[
("505/505",1.0,"eJzlkksOwCAIBX1z/0P3a6FGrOyalgWIExljLOUfAWirglu/7jzwecVZxbGmQQOedtSBkaPD5x1gs7D+2op5ztNcGpdj/i6HP4/vXe7zjKS+r/3NvUpj/sVYAPxYANg="),
("187/187",1.0,"eJzlkVsOgCAMBNm5/6HVWA2FgilfRpvAkk7C8CjlHyXOBCywjh54orjnerQR8GXHcXJNHBVPO/bAN7rrtDztQMR7D/mCw60CR8df5hCy8G90/eyIf7E2wLAAuA=="),
("449/505",.8902439024,"eJzlkkEOwCAIBGH+/+gmKso2TRNsemjKZd2oDKBmfwlEIbyHbwsH8TUEWVnQ6TtC9oqIqN9uGWFeYbD6a4w1ywLiVOKcN/mMNFWEQC8s9DLTQ0a+MtTF5vyYzLIQjui0g4X+O9t4j8/EAfrFANk="),
("58/187",.3089430894,"eJzlklEKwCAMQ5Pc/9DbsC3t/Fp1MFhBA1F8mBb4T0miqTkcu+LcJC48RiRVsVT8dP4a4yyyy/AIVHBZbn6Tcy2qvu3/CH8DAzkdYM6qj5h7up/hs0nZsHpnOUY6/LWovl8HmugArA=="),
("505/505",1.0,"eJzlkksOwCAIBX1z/0P3a6FGrOyalgWIExljLOUfAWirglu/7jzwecVZxbGmQQOedtSBkaPD5x1gs7D+2op5ztNcGpdj/i6HP4/vXe7zjKS+r/3NvUpj/sVYAPxYANg="),
("91/187",.4756097561,"eJzlkksOgDAIRJl3/0NLDETBHYaNTtJO+aRTKGb/AXCySI+KHXHIxIFErNyvAyXOPWNJwyEtaThR/RMRULmiMuK9Rn9317BHnQNklxc1ckYVLcufDdup1flRHG0RAJY="),
]
def sample(i):
    text,fraction,data=SAMPLES[i]
    levels=np.frombuffer(zlib.decompress(base64.b64decode(data)),np.uint8).reshape(12,100)
    rgb=np.repeat(np.array([0,140,175],np.uint8)[levels][:,:,None],3,axis=2)
    return tuple(map(int,text.split('/'))),fraction,rgb

class NativeVitalTests(unittest.TestCase):
    def test_native_screenshot_masks(self):
        for i in range(len(SAMPLES)):
            expected,fraction,rgb=sample(i)
            with self.subTest(text=SAMPLES[i][0]):
                self.assertEqual(recognise_vital_pair(rgb,fraction),expected)
    def test_full_digit_library(self):
        for lookup in LOOKUP.values():self.assertEqual(set(lookup.values()),set('0123456789/'))
    def test_conflicts_clipping_and_bad_fill(self):
        expected,fraction,rgb=sample(2)
        self.assertIsNone(recognise_vital_pair(rgb,.5))
        self.assertIsNone(recognise_vital_pair(rgb,None))
        self.assertIsNone(recognise_vital_pair(np.zeros_like(rgb),fraction))
        broken=rgb.copy();broken[0,50]=255
        self.assertIsNone(recognise_vital_pair(broken,fraction))
        # Keep the low-threshold glyph intact but corrupt the high read.
        broken=rgb.copy();y,x=np.argwhere(broken[:,:,0]==175)[0];broken[y,x]=140
        self.assertIsNone(recognise_vital_pair(broken,fraction))
    def test_native_read_bypasses_busy_ocr(self):
        m=VitalMonitor();a=Mock();a.target=TARGET;a.running=True;a.selecting=False;a.run_id=1
        a.pause_gate.capture_policy.return_value=(False,0,False)
        config={'binding':binding_for(TARGET),'vitals':{'frame':{},'bars':{'hp':dict(left=0,top=1,width=246,height=10),'mp':dict(left=0,top=14,width=246,height=10)}}}
        key=(1,0,1,TARGET.hwnd,TARGET.pid);m.key=key;m.capture_busy=True;m.ocr_busy={'hp','mp'}
        frame=np.zeros((25,246,3),np.uint8)
        frame[:12,73:173]=sample(2)[2];frame[13:25,73:173]=sample(3)[2]
        m.frames.put((key,10,frame));m.next_capture=20
        with patch('vital_monitor.bar_fraction',side_effect=[sample(2)[1],sample(3)[1]]),patch('vital_monitor.threading.Thread') as worker:
            values=m.tick(a,config,1,10)
        self.assertEqual(values['hp'],('HP','449/505 - 89%'))
        self.assertEqual(values['mp'],('MP','58/187 - 31%'))
        worker.assert_not_called()
        self.assertEqual(m.tick(a,config,1,12)['hp'],('HP','— - —'))
