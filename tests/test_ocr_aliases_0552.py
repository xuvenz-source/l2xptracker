"""The reported shot grade and recipe disagreements must not pollute loot."""
import unittest
from unittest.mock import patch
import numpy as np
from tracker import configured_ocr_rows,parse,recover_no_grade_soulshot,recover_blue_diamond_recipe
from chat_style import CUSTOM_COLOURS,DEFAULT_COLOURS

SHOT='Use Soulshot: No Grade.'
RECIPE='You have obtained Recipe: Blue Diamond Necklace.'
WRONG='You have obtained Recipe: Blue Ciamond Necklace,'
def shot(t):return 'Use Soulshot: '+t+','
def row(colour):
    a=np.zeros((17,350,3),np.uint8);a[4:13,8:310]=colour;return a

class ReportedAliasesTests(unittest.TestCase):
    def test_shot_variants(self):
        for hints in [('Ho Grade','Wo Grade','Heo Grade'),('Ni Grade','Ni Grade',''),('Ao Grade','Ni Grade','Ao Grade')]:
            self.assertEqual(recover_no_grade_soulshot([shot(t) if t else '' for t in hints]),SHOT)
        for hints in [('Ao Grade','Ao Grade','Ao Grade'),('Ni Grade','Ho Grade','A Grade'),('Ho Grade','D Grade','Wo Grade'),('Ni Grade','Ho Grade','D Grads')]:
            self.assertIsNone(recover_no_grade_soulshot([shot(t) for t in hints]))
    def test_shot_pipeline(self):
        reads=[shot(t) for t in ('Ho Grade','Wo Grade','Heo Grade')]
        with patch('tracker.single_ocr',side_effect=reads):
            out=list(configured_ocr_rows([row((0,170,255))],CUSTOM_COLOURS))
        self.assertEqual(out,[('line',SHOT)])
        self.assertEqual(parse(out[0][1]),('consumable','You','Soulshot: No Grade',1,0))
    def test_recipe_consensus(self):
        for reads in ([WRONG,RECIPE,RECIPE],[RECIPE,WRONG,RECIPE],[RECIPE,RECIPE,WRONG]):
            self.assertEqual(recover_blue_diamond_recipe(reads),RECIPE)
        for reads in ([WRONG,WRONG,RECIPE],[RECIPE,RECIPE,'You have obtained Recipe: Blue Diamond Ring.'],[RECIPE,RECIPE,'You have obtained 2 Recipe: Blue Diamond Necklace.'],[RECIPE,RECIPE,'You have obtained 150 Adena.'],[RECIPE,WRONG,'']):
            self.assertIsNone(recover_blue_diamond_recipe(reads))
    def test_recipe_pipeline(self):
        for palette,colour in ((CUSTOM_COLOURS,(0,255,0)),(DEFAULT_COLOURS,(255,255,0))):
            with patch('tracker.single_ocr',side_effect=[WRONG,RECIPE,RECIPE]):
                out=list(configured_ocr_rows([row(colour)],palette))
            self.assertEqual(out,[('line',RECIPE)])
            self.assertEqual(parse(out[0][1]),('item','You','Recipe: Blue Diamond Necklace',1,0))
    def test_other_recipe_disagreement_remains_review(self):
        with patch('tracker.single_ocr',side_effect=['You have obtained Recipe: Blue Diamond Ring.',RECIPE,RECIPE]):
            out=list(configured_ocr_rows([row((0,255,0))],CUSTOM_COLOURS))
        self.assertEqual(out[0][0],'uncertain:item')
    def test_wrong_colour_does_not_recover(self):
        with patch('tracker.single_ocr',side_effect=[WRONG,RECIPE,RECIPE]):
            out=list(configured_ocr_rows([row((0,170,255))],CUSTOM_COLOURS))
        self.assertEqual(out[0][0],'uncertain:consumable')
