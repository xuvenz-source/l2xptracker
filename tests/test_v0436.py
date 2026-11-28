import unittest
from collections import Counter
from unittest.mock import patch
import numpy as np
from tracker import parse, configured_ocr_rows, colour_ocr_row, xp_numeric_candidate
from chat_style import CUSTOM_COLOURS, DEFAULT_COLOURS
from review import ReviewQueue,review_fields,candidates
from history import totals_for
from loot_values import loot_report

TAG='You have earned Turek Dog Tag.'
CASH='You have earned 190 Adena.'
ROW=np.zeros((21,340,3),np.uint8)
ROW[4:16,10:250]=(255,255,0)

class QuestRewardTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse(TAG),('item','You','Turek Dog Tag',1,0))
        self.assertEqual(parse('You have earned 3 Turek Dog Tag.'),('item','You','Turek Dog Tag',3,0))
        self.assertEqual(parse('Alpha has earned Turek Dog Tag.'),('item','Alpha','Turek Dog Tag',1,0))
        self.assertEqual(parse(CASH),('adena','You','Adena',190,0))
        for line in ('You have earned 8&5 Adena.','You have earned S?/ Adena.','You have earned 190 Aden4.','You have earned 190.','You have earned Adena.'):
            self.assertIsNone(parse(line),line)
    def test_yellow_routes_to_item(self):
        for palette in (CUSTOM_COLOURS,DEFAULT_COLOURS):
            with patch('tracker.single_ocr',return_value=TAG):
                self.assertEqual(list(configured_ocr_rows([ROW],palette)),[('line',TAG)])
        with patch('tracker.single_ocr',return_value=TAG):
            self.assertEqual(colour_ocr_row(ROW,'adena'),('line',TAG))
    def test_conflicting_rewards_require_review(self):
        with patch('tracker.single_ocr',side_effect=[TAG,CASH,'']):
            result=list(configured_ocr_rows([ROW],CUSTOM_COLOURS))
        self.assertEqual(result[0][0],'uncertain')
    def test_old_review_and_loot(self):
        q=ReviewQueue();r=q.add('t',TAG+' [colour OCR: '+TAG+' | (blank)]',category='adena')
        self.assertEqual(review_fields(r,parse,xp_numeric_candidate)['kind'],'item')
        self.assertIn(TAG,candidates(r,parse,xp_numeric_candidate))
        events=[];totals=Counter();q.approve(r.id,TAG,parse,events,totals)
        self.assertEqual(totals[('You','Turek Dog Tag')],1)
        self.assertEqual(totals_for(events),totals)
        self.assertEqual(loot_report([dict(events=events,loot_prices={'turek dog tag':'10'})])['value'],10)
    def test_cash_review_still_protected(self):
        q=ReviewQueue();r=q.add('t','You have earned 8&5 Adena.',category='adena')
        with self.assertRaises(ValueError):q.approve(r.id,TAG,parse,[],Counter())
