import unittest
from unittest.mock import patch
import numpy as np
from tracker import xp_numeric_candidate, verified_xp, xp_retry, xp_like, parse

FIRST = 'You have acquired 221 XP and & SP.'
READS = ['You have acquired 221 XPand9SP, x', 'You have acquired 221 XPand9SP. 4', 'You have acquired 221 XP and 9 SP. ,']
ROW = np.zeros((18,340,3),dtype=np.uint8)
class XPSpacingTests(unittest.TestCase):
    def test_reported_candidates(self):
        self.assertIsNone(xp_numeric_candidate(FIRST))
        for text in READS:
            with self.subTest(text=text):
                self.assertEqual(xp_numeric_candidate(text),(221,9))
    def test_reported_retry(self):
        with patch('tracker.single_ocr',side_effect=READS) as ocr:
            line,reads=xp_retry(ROW,FIRST)
        self.assertEqual(parse(line)[3:],(221,9))
        self.assertEqual(ocr.call_count,2)
    def test_all_reported_votes(self):
        self.assertEqual(verified_xp([FIRST,*READS]),(221,9))
    def test_compact_conflict(self):
        with patch('tracker.single_ocr',side_effect=[READS[0],'You have acquired 221 XPand8SP. 4']):
            self.assertIsNone(xp_retry(ROW,FIRST)[0])
    def test_missing_votes(self):
        self.assertIsNone(verified_xp([FIRST,READS[0],'']))
    def test_invalid_suffix_and_digits(self):
        for text in ['221 XPand&SP. x','221 XPand9SP4','221 XPand9SP 4','221 XPand9SP. 42','221 XPand9SP. and 4','221 XPand1?2SP.','221 XPand9SP. You have acquired 222 XP']:
            with self.subTest(text=text): self.assertIsNone(xp_numeric_candidate(text))
    def test_compact_detection(self):
        self.assertTrue(xp_like('221XPand9SP'))
        self.assertFalse(xp_like('You use Soul Cry.'))
    def test_grouped_numbers(self):
        self.assertEqual(xp_numeric_candidate('You have acquired 1,221XPand1,009SP. ,'),(1221,1009))
if __name__=='__main__': unittest.main()
