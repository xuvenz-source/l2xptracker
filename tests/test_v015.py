import unittest
from unittest.mock import patch
from tracker import recover_sp_conflict, parse_xp_resolution, ocr_rows
from test_v010 import A, ROWS, batch
FIRST='You haye acquired 221 XP and 8 SP,'
GOOD='You have acquired 221 XP and 9 SP,'
BAD='YOU have acquired 221 XP and & SP.'
ROW=ROWS[0]
class SPAbstentionTests(unittest.TestCase):
    def resolve(self, first, reads, extra):
        with patch('tracker.single_ocr',side_effect=extra):
            return recover_sp_conflict(ROW,first,reads)
    def test_exact_report(self):
        result=self.resolve(FIRST,[GOOD],[GOOD,BAD])
        self.assertEqual(result[0],'xp_recovered')
        self.assertEqual(parse_xp_resolution(*result)[3:],(221,9))
        self.assertIn(BAD,result[1]);self.assertIn(FIRST,result[1])
    def test_tie_remains_partial(self):
        self.assertEqual(self.resolve(FIRST,[GOOD],[GOOD,FIRST])[0],'xp_partial')
    def test_multiple_dissent_remains_partial(self):
        self.assertEqual(self.resolve(FIRST,[GOOD,GOOD],[GOOD,FIRST])[0],'xp_partial')
    def test_xp_conflict_remains_uncertain(self):
        self.assertEqual(self.resolve(FIRST,[GOOD],[GOOD,'You have acquired 222 XP and 9 SP.'])[0],'uncertain')
    def test_no_majority_remains_partial(self):
        self.assertEqual(self.resolve(FIRST,[GOOD],['',BAD])[0],'xp_partial')
    def test_pipeline_keeps_each_repeated_row(self):
        with patch('tracker.row_images',return_value=(A,False)),patch('tracker.pytesseract.image_to_data',return_value=batch(FIRST,GOOD)),patch('tracker.single_ocr',side_effect=[FIRST,GOOD,GOOD,BAD,GOOD,GOOD,GOOD]):
            result=list(ocr_rows(ROWS))
        self.assertEqual(parse_xp_resolution(*result[0])[3:],(221,9))
        self.assertEqual(result[1],('line','You have acquired 221 XP and 9 SP.'))
if __name__=='__main__': unittest.main()
