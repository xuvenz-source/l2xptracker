import json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import numpy as np
from tracker import configured_ocr_rows,padded
from chat_style import CUSTOM_COLOURS
from ocr_evidence import OcrEvidence
from ocr_fixture import reward_mask,EXPECTED

class EvidenceTests(unittest.TestCase):
    def test_evidence_capture_and_bounded_export(self):
        row=np.zeros((21,292,3),np.uint8)
        row[reward_mask()==0]=(255,0,255)
        e=OcrEvidence();e.frame(row,(21,0,True),21)
        with patch('tracker.single_ocr',return_value='Var have scanirad DAF YD ana 11 CD'):
            for _ in range(14):
                r=list(configured_ocr_rows([row],CUSTOM_COLOURS,evidence=e))
                self.assertTrue(r[0][0].startswith('uncertain'))
        with patch('tracker.single_ocr',return_value=EXPECTED):
            self.assertEqual(list(configured_ocr_rows([row],CUSTOM_COLOURS,evidence=e)),[('line',EXPECTED)])
        self.assertEqual(e.count(),(12,1))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'evidence.zip';e.export(p,{'pitch':21})
            with zipfile.ZipFile(p) as z:
                m=json.loads(z.read('manifest.json'))
                self.assertEqual(len(m['samples']),13)
                self.assertEqual(len(m['samples'][0]['passes']),5)
                self.assertIn('latest-queued-chat.png',z.namelist())
                import io
                im=Image.open(io.BytesIO(z.read('row-01/ocr-01.png')))
                self.assertTrue(np.array_equal(np.asarray(im),np.asarray(padded(reward_mask()))))
    def test_no_evidence_no_export(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'no.zip'
            with self.assertRaises(ValueError):OcrEvidence().export(p,{})
            self.assertFalse(p.exists())
