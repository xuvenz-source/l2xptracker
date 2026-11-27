import unittest
from unittest.mock import patch
from collections import Counter
import numpy as np
from tracker import colour_category, colour_ocr_row, parse, rows_of, xp_numeric_candidate
from review import ReviewQueue, review_fields, correction_message
from history import totals_for, consumables_for, review_queue
from dataclasses import asdict

class ColourTests(unittest.TestCase):
    def row(self,rgb):
        a=np.zeros((18,220,3),np.uint8);a[4:13,10:80]=rgb
        return a
    def test_sampled_colours(self):
        for rgb,kind in [((255,13,255),'xp'),((255,255,13),'adena'),((13,255,13),'item'),((13,194,255),'consumable')]:
            row=self.row(rgb)
            self.assertEqual(colour_category(row),kind)
            self.assertGreater(rows_of(row,18).sum(),24)
        self.assertIsNone(colour_category(self.row((180,160,110))))
    def test_exact_configured_colours(self):
        for rgb,kind in [((255,0,255),'xp'),((255,255,0),'adena'),((0,255,0),'item'),((0,170,255),'consumable')]:
            with self.subTest(kind=kind):
                row=self.row(rgb)
                self.assertEqual(colour_category(row),kind)
                self.assertGreater(rows_of(row,18).sum(),24)
                from tracker import colour_masks
                for threshold,contrast in [(140,75),(115,60),(165,95)]:
                    self.assertEqual(int(colour_masks(row,threshold,contrast)[kind].sum()),9*70)
    def test_ocr(self):
        for rgb,kind,line in [((255,13,255),'xp','You have acquired 389 XP and 15 SP.'),((255,255,13),'adena','You have obtained 101 Adena.'),((13,255,13),'item','You have obtained Suede.'),((13,194,255),'consumable','Use Soulshot: No Grade.')]:
            with patch('tracker.single_ocr',return_value=line):
                result=colour_ocr_row(self.row(rgb),kind)
                self.assertEqual(result,('line',line))
                self.assertEqual(parse(line)[0],kind)
    def test_conflicting_and_blank(self):
        with patch('tracker.single_ocr',side_effect=['Use Soulshot: No Grade.','Use Spiritshot: No Grade.','']):
            self.assertEqual(colour_ocr_row(self.row((13,194,255)),'consumable')[0],'uncertain:consumable')
        with patch('tracker.single_ocr',return_value=''):
            self.assertEqual(colour_ocr_row(self.row((13,255,13)),'item')[0],'uncertain:item')
    def test_consumable_and_loot_separate(self):
        use='Use Soulshot: No Grade.'; loot='You have obtained Soulshot: No Grade.'
        self.assertIsNone(parse('Your soulshots are enabled.'))
        self.assertIsNone(parse('You use Mortal Blow.'))
        events=[('t',*parse(use),use),('t',*parse(use),use),('t',*parse(loot),loot)]
        self.assertEqual(consumables_for(events),{'Soulshot: No Grade':2})
        self.assertEqual(totals_for(events),{('You','Soulshot: No Grade'):1})
    def test_review_archive(self):
        q=ReviewQueue();r=q.add('t','(blank)',category='consumable')
        q=review_queue(dict(reviews=[asdict(r)],next_review=2));r=q.pending[1]
        self.assertEqual(review_fields(r,parse,xp_numeric_candidate)['kind'],'consumable')
        events=[]; totals=Counter()
        with self.assertRaises(ValueError):q.approve(1,'You have obtained Suede.',parse,events,totals)
        q.approve(1,correction_message(r,'consumable',full='Use Soulshot: No Grade.'),parse,events,totals)
        self.assertEqual(consumables_for(events),{'Soulshot: No Grade':1})
        self.assertEqual(totals,Counter())
