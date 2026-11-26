import unittest
from unittest.mock import patch
import numpy as np
from tracker import recover_sp_conflict, parse_xp_resolution, ocr_rows
from test_v010 import A, ROWS, batch
FIRST='You have acquired 221 XP and 8 SP,'
GOOD='You have acquired 221 XP and 9 SP,'
ROW=ROWS[0]
class SPConflictTests(unittest.TestCase):
    def test_reported_recovered(self):
        with patch('tracker.single_ocr',side_effect=[GOOD,GOOD]):
            kind,line=recover_sp_conflict(ROW,FIRST,[GOOD])
        self.assertEqual(kind,'xp_recovered')
        self.assertEqual(parse_xp_resolution(kind,line)[3:],(221,9))
        self.assertIn(FIRST,line)
    def test_reported_unresolved_keeps_xp(self):
        with patch('tracker.single_ocr',side_effect=['','']):
            kind,line=recover_sp_conflict(ROW,FIRST,[GOOD])
        self.assertEqual(kind,'xp_partial')
        self.assertEqual(parse_xp_resolution(kind,line)[3:],(221,None))
    def test_tie(self):
        with patch('tracker.single_ocr',side_effect=[GOOD,FIRST]):
            self.assertEqual(recover_sp_conflict(ROW,FIRST,[GOOD])[0],'xp_partial')
    def test_xp_disagreement(self):
        with patch('tracker.single_ocr',side_effect=[GOOD,'You have acquired 222 XP and 9 SP.']):
            self.assertEqual(recover_sp_conflict(ROW,FIRST,[GOOD])[0],'uncertain')
    def test_initial_xp_disagreement(self):
        with patch('tracker.single_ocr') as ocr:
            self.assertIsNone(recover_sp_conflict(ROW,FIRST,['222 XP and 9 SP.']))
            ocr.assert_not_called()
    def test_pipeline_repeated_rows(self):
        with patch('tracker.row_images',return_value=(A,False)), patch('tracker.pytesseract.image_to_data',return_value=batch(FIRST,GOOD)), patch('tracker.single_ocr',side_effect=[FIRST,GOOD,GOOD,GOOD,GOOD,GOOD,GOOD]):
            result=list(ocr_rows(ROWS))
        self.assertEqual(result[0][0],'xp_recovered')
        self.assertEqual(parse_xp_resolution(*result[0])[3:],(221,9))
        self.assertEqual(result[1],('line','You have acquired 221 XP and 9 SP.'))
if __name__=='__main__': unittest.main()
