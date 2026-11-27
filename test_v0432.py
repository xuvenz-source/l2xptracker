import unittest
from unittest.mock import patch
import numpy as np
from tracker import configured_ocr_rows, xp_numeric_candidate, xp_field_candidate, parse, parse_xp_resolution
from chat_style import CUSTOM_COLOURS

ROW=np.zeros((19,320,3),dtype=np.uint8)
ROW[4:15,10:160]=(255,0,255)
GOOD='You have acquired 867 XP and 43 SP.'
BAD=['You have acquired 66/ XP and 43 SP.','You have acquired S67 XP and 43 SP.']

class XPRecognitionTests(unittest.TestCase):
    def recognize(self,reads):
        with patch('tracker.single_ocr',side_effect=reads):
            return list(configured_ocr_rows([ROW],CUSTOM_COLOURS))[0]
    def test_reported_screenshot_reads(self):
        result=self.recognize([GOOD,*BAD,GOOD,GOOD])
        self.assertEqual(result,('line',GOOD))
        self.assertEqual(parse(result[1])[3:],(867,43))
    def test_damaged_tokens_never_vote(self):
        for token in ('S67','66/','86/7','8?67','8 67','1,22'):
            text=f'You have acquired {token} XP and 43 SP.'
            self.assertIsNone(xp_field_candidate(text))
            if token!='8 67':self.assertIsNone(xp_numeric_candidate(text))
    def test_conflicting_xp_remains_review(self):
        result=self.recognize([GOOD,'You have acquired 367 XP and 43 SP.',GOOD,GOOD,GOOD])
        self.assertEqual(result[0],'sp_partial')
        self.assertEqual(parse_xp_resolution(*result)[3:],(None,43))
    def test_agreed_xp_conflicting_sp_is_retained(self):
        bad='You have acquired 867 XP and 48 SP.'
        result=self.recognize([GOOD,bad,GOOD,GOOD,bad])
        self.assertEqual(result[0],'xp_partial')
        self.assertEqual(parse_xp_resolution(*result)[3:],(867,None))
    def test_clean_rows_need_no_extra_ocr(self):
        self.assertEqual(self.recognize([GOOD,GOOD,GOOD]),('line',GOOD))
