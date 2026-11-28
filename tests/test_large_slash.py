import unittest
from unittest.mock import patch
import numpy as np
from numeric_templates import library,XP_PATTERN,AD_PATTERN,strict_reward,strict_adena
from tracker import recover_xp_slash,recover_adena_digits,configured_ocr_rows,slash_reward_tokens
from chat_style import CUSTOM_COLOURS

def xp(x,sp):return f'You have acquired {x} XP and {sp} SP.'
def ad(v):return f'You have earned {v} Adena.'

class SlashTests(unittest.TestCase):
    def test_field_trigger(self):
        self.assertEqual(slash_reward_tokens(xp('2/1','/')),('2/1','/'))
        self.assertEqual(slash_reward_tokens(xp(271,7)),(None,None))
        self.assertEqual(slash_reward_tokens('You have earned / Adena.'),(None,None))
    def test_xp_sp_verified_recovery_and_conflicts(self):
        row=np.zeros((21,300,3),np.uint8);crop=np.zeros((12,6),bool)
        # Control the verified field result to exercise evidence gates separately
        # from the existing screenshot-based recognition regression suite.
        with patch('tracker.strict_reward',return_value=((271,7),[crop,crop])):
            self.assertEqual(recover_xp_slash(row,[xp('2/1',7),xp('2/1',7)],lambda c,n:'271'),(271,7))
            self.assertEqual(recover_xp_slash(row,[xp(271,'/'),xp(271,'/')],lambda c,n:'7'),(271,7))
            self.assertIsNone(recover_xp_slash(row,[xp('2/1',7),xp(281,7)],lambda c,n:'271'))
            self.assertIsNone(recover_xp_slash(row,[xp('2/1',7),xp('2/1',7)],lambda c,n:'271' if n else '21'))
            self.assertIsNone(recover_xp_slash(row,[xp('3/1',7),xp('3/1',7)],lambda c,n:'271'))
    def test_standalone_adena_slash(self):
        row=np.zeros((21,300,3),np.uint8)
        with patch('tracker.strict_adena',return_value=(7,np.zeros((12,6),bool))):
            self.assertEqual(recover_adena_digits(row,[ad('/')]*3,lambda c,n:'7'),7)
            self.assertIsNone(recover_adena_digits(row,[ad('/')]*3,lambda c,n:'1'))
    def test_pipeline_preserves_partial_on_failed_verification(self):
        row=np.zeros((21,300,3),np.uint8);row[4:16,10:250]=(255,0,255)
        with patch('tracker.single_ocr',return_value=xp('2/1',7)),patch('tracker.strict_reward',return_value=None):
            result=list(configured_ocr_rows([row],CUSTOM_COLOURS))
        self.assertEqual(result[0][0],'sp_partial')
    def test_pipeline_recovers_xp(self):
        row=np.zeros((21,300,3),np.uint8);row[4:16,10:250]=(255,0,255)
        with patch('tracker.single_ocr',return_value=xp('2/1',7)),patch('tracker.strict_reward',return_value=((271,7),[np.zeros((12,6),bool)]*2)),patch('tracker.pytesseract.image_to_string',return_value='271'):
            self.assertEqual(list(configured_ocr_rows([row],CUSTOM_COLOURS)),[('template_line',xp(271,7))])
