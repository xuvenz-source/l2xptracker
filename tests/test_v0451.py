import unittest
from collections import Counter
from unittest.mock import patch
import numpy as np
from tracker import parse,configured_ocr_rows,xp_numeric_candidate
from review import ReviewQueue,review_fields,correction_message,effective_category
from party import report
from chat_style import CUSTOM_COLOURS,DEFAULT_COLOURS

BAD='You have obtained 13/7 Adena.'
EVIDENCE=BAD+' [colour OCR: You have obtainéd 13/ Adena. | You have obtained 13/ Adena.]'
GOOD='You have obtained 137 Adena.'

class CurrencyReviewTests(unittest.TestCase):
    def test_malformed_amounts_not_items(self):
        for verb in ('earned','obtained'):
            for amount in ('13/7','13/','S67','8&5','1,2',''):
                self.assertIsNone(parse(f'You have {verb} {amount} Adena.'),(verb,amount))
        self.assertEqual(parse(GOOD),('adena','You','Adena',137,0))
        self.assertEqual(parse('Alpha has obtained 137 Adena.'),('adena','Alpha','Adena',137,0))
        self.assertEqual(parse('You have obtained 2 Suede.'),('item','You','Suede',2,0))
    def test_existing_item_review_corrects_as_currency(self):
        q=ReviewQueue();r=q.add('t',EVIDENCE,category='item')
        f=review_fields(r,parse,xp_numeric_candidate)
        self.assertEqual((f['kind'],f['adena'],f['who']),('adena','','You'))
        self.assertEqual(f['options'],[])
        events=[];totals=Counter()
        q.approve(r.id,correction_message(r,'adena',adena='137',who='You'),parse,events,totals)
        self.assertEqual(totals,Counter({('You','Adena'):137}))
    def test_new_review_classification(self):
        for palette,colour in ((CUSTOM_COLOURS,(255,255,0)),(DEFAULT_COLOURS,(255,255,0)),(CUSTOM_COLOURS,(0,255,0))):
            row=np.zeros((21,340,3),np.uint8);row[4:16,10:250]=colour
            with patch('tracker.single_ocr',side_effect=[BAD,'You have obtainéd 13/ Adena.','You have obtained 13/ Adena.']):
                result=list(configured_ocr_rows([row],palette))
            self.assertEqual(result[0][0],'uncertain:adena')
    def test_cash_item_conflict_unlocked(self):
        q=ReviewQueue();r=q.add('t',BAD+' [colour OCR: You have obtained Suede. | You have obtained Suede.]',category='item')
        self.assertIsNone(effective_category(r,parse))
    def test_configured_name_case_wins(self):
        data=dict(seconds=60,party_members=['Alpha'],events=[('t','adena','alpha','Adena',5,0,'observed'),('t','adena','You','Adena',10,0,'own')])
        self.assertEqual(report([data])['rows'],[dict(name='Alpha',observed=5,estimate=10,seconds=60)])
