import unittest
from unittest.mock import patch
import numpy as np
from chat_native import recognise_small_shot,SMALL_SHOT_MASKS
from tracker import configured_ocr_rows
from chat_style import CUSTOM_COLOURS

GOOD='Use Soulshot: No Grade.'
def sample(variant=0):
    low=np.unpackbits(np.frombuffer(next(iter(SMALL_SHOT_MASKS[230])),dtype=np.uint8),count=1215).reshape(9,135).astype(bool)
    high=np.unpackbits(np.frombuffer(sorted(SMALL_SHOT_MASKS[250])[variant],dtype=np.uint8),count=1215).reshape(9,135).astype(bool)
    rgb=np.zeros((16,165,3),np.uint8)
    rgb[3:12,10:145][low]=(0,170,230)
    rgb[3:12,10:145][high]=(0,170,255)
    return rgb

class SmallShotTests(unittest.TestCase):
    def test_exact_masks_and_margins(self):
        for i in range(2):
            row=sample(i)
            self.assertTrue(recognise_small_shot(row))
            self.assertTrue(recognise_small_shot(np.pad(row,((1,2),(5,3),(0,0)))))
    def test_reject_changes(self):
        row=sample()
        self.assertFalse(recognise_small_shot(row[:,11:]))
        self.assertFalse(recognise_small_shot(np.zeros_like(row)))
        bad=row.copy();bad[3,10]=0
        self.assertFalse(recognise_small_shot(bad))
        bad=row.copy();bad[7,150]=(0,170,255)
        self.assertFalse(recognise_small_shot(bad))
    def test_ocr_failure_recovers_without_experimental_setting(self):
        with patch('tracker.single_ocr',side_effect=['Use Soulshot: Ao Grade,']*3):
            self.assertEqual(list(configured_ocr_rows([sample()],CUSTOM_COLOURS)),[('template_line',GOOD)])
    def test_conflicting_grade_stays_review(self):
        with patch('tracker.single_ocr',side_effect=['Use Soulshot: Ao Grade,','Use Soulshot: A Grade.','Use Soulshot: Ho Grade,']):
            result=list(configured_ocr_rows([sample()],CUSTOM_COLOURS))
        self.assertEqual(result[0][0],'uncertain:consumable')
