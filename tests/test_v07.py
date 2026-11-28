import unittest
from unittest.mock import patch
import numpy as np
from tracker import xp_numeric_candidate, verified_xp, xp_retry, parse

FIRST='You have acquired 261 XP and 12 SF.'
BAD='Ypu cB ee ita? and 12 sp, :'
GOOD='You haveyatquired®261 XP and 12 SP.'
ROW=np.zeros((18,340,3),dtype=np.uint8)
class XPTests(unittest.TestCase):
    def test_reported_case(self):
        with patch('tracker.single_ocr',side_effect=[BAD,GOOD]) as ocr:
            line,reads=xp_retry(ROW,FIRST)
        self.assertEqual(parse(line),('xp','You','XP / SP',261,12))
        self.assertEqual(reads,[BAD,GOOD]); self.assertEqual(ocr.call_count,2)
    def test_conflict_xp(self):
        self.assertIsNone(verified_xp([FIRST,GOOD,'You have acquired 267 XP and 12 SP.']))
    def test_conflict_sp(self):
        self.assertIsNone(verified_xp([FIRST,'261 XP and 13 SP.']))
    def test_single_vote(self):
        self.assertIsNone(verified_xp([FIRST,BAD,'']))
    def test_bad_digits(self):
        self.assertIsNone(xp_numeric_candidate('221 XP and © SF,'))
        self.assertIsNone(xp_numeric_candidate('261 XP and 1?2 SP.'))
    def test_retry_third(self):
        with patch('tracker.single_ocr',side_effect=['',BAD,GOOD]) as ocr:
            line,_=xp_retry(ROW,FIRST)
        self.assertEqual(parse(line)[3:],(261,12));self.assertEqual(ocr.call_count,3)
    def test_disagree(self):
        with patch('tracker.single_ocr',side_effect=[GOOD,'261 XP and 13 SP.']):
            self.assertIsNone(xp_retry(ROW,FIRST)[0])
    def test_normal_parser_unchanged(self):
        self.assertIsNone(parse(FIRST));self.assertEqual(parse('You have acquired 261 XP and 12 SP.')[3:],(261,12))
    def test_two_retry_votes(self):
        with patch('tracker.single_ocr',side_effect=['221 XP and 9 SP.','You have acquired 221 XP and 9 SP.']):
            self.assertEqual(parse(xp_retry(ROW,'You have acquired 221 XP and © SF,')[0])[3:],(221,9))
if __name__=='__main__':unittest.main()
