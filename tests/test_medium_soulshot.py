"""Regression for the observed Medium No Grade Soulshot OCR readings."""
import unittest
from unittest.mock import patch,Mock
import numpy as np
from tracker import configured_ocr_rows,recover_no_grade_soulshot,parse
from chat_style import CUSTOM_COLOURS,DEFAULT_COLOURS

GOOD='Use Soulshot: No Grade.'
BAD=['Use Soulshot: No Grads,','Use Soulshot: Ne Grace,','s= Soulshot: No Grads,']

class MediumSoulshotTests(unittest.TestCase):
    def test_reported_readings(self):
        self.assertEqual(recover_no_grade_soulshot(BAD),GOOD)
        self.assertEqual(recover_no_grade_soulshot([GOOD,BAD[0],'']),GOOD)
        self.assertIsNone(parse(BAD[0]))
        self.assertIsNone(parse(BAD[1]))
    def test_single_hint_and_conflicts(self):
        for reads in ([BAD[0],'',''],[BAD[0],BAD[2],''],[BAD[0],BAD[1],'Use Soulshot: D Grade.'],[BAD[0],BAD[1],'Use Soulshot: D Grads,'],[BAD[0],BAD[1],'Use Spiritshot: No Grads,'],[BAD[0],BAD[1],'Use Blessed Soulshot: No Grads,'],[BAD[0],BAD[1],'You have obtained Suede.'],['Use Soulshot: No Gradz,']*3):
            with self.subTest(reads=reads):self.assertIsNone(recover_no_grade_soulshot(reads))
    def test_configured_pipeline_counts_once_per_row(self):
        row=np.zeros((17,180,3),np.uint8);row[4:13,8:151]=(0,170,255)
        with patch('tracker.single_ocr',side_effect=BAD*2) as read:
            out=list(configured_ocr_rows([row,row],CUSTOM_COLOURS))
        self.assertEqual(out,[('line',GOOD),('line',GOOD)])
        self.assertEqual(read.call_count,6)
        self.assertEqual(parse(out[0][1]),('consumable','You','Soulshot: No Grade',1,0))
    def test_clean_path_unchanged(self):
        row=np.zeros((17,180,3),np.uint8);row[4:13,8:151]=(0,170,255)
        with patch('tracker.single_ocr',return_value=GOOD) as read:
            self.assertEqual(list(configured_ocr_rows([row],CUSTOM_COLOURS)),[('line',GOOD)])
        self.assertEqual(read.call_count,2)
    def test_non_blue_and_shared_colour_still_review(self):
        for palette in (CUSTOM_COLOURS,DEFAULT_COLOURS):
            row=np.zeros((17,180,3),np.uint8);row[4:13,8:151]=(176,155,121) if palette==DEFAULT_COLOURS else (255,255,0)
            with patch('tracker.single_ocr',side_effect=BAD):
                out=list(configured_ocr_rows([row],palette))
            self.assertTrue(out[0][0].startswith('uncertain'),out)
