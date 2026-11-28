"""Shared library compatibility and offline-only candidate calibration."""
import unittest,tempfile
from unittest.mock import patch
import numpy as np
from PIL import ImageFont
import font_library as f
import status_digits,vital_digits,numeric_templates,chat_native
from calibrate_tahoma import CHARACTERS,candidate_library,compare,run_calibration

class SharedFontTests(unittest.TestCase):
    def test_original_recognisers_share_verified_data(self):
        self.assertIs(status_digits.TEMPLATES,f.TEMPLATES)
        self.assertIs(status_digits.VARIANTS,f.VARIANTS)
        self.assertIs(numeric_templates.library(),f.large_library())
        self.assertIs(chat_native.library(),f.chat_library())
        for t in (140,175):
            self.assertEqual(vital_digits.LOOKUP[t],f.vital_lookup(t))
            self.assertEqual(set(f.vital_lookup(t).values()),set('0123456789/'))
    def test_profiles_and_no_word_as_character(self):
        profiles=f.verified_profiles()
        self.assertEqual(set(profiles),{'Fixed status','Level badge','Large chat','Medium chat','Small chat'})
        self.assertEqual(set(profiles['Fixed status']),set('0123456789/.%'))
        self.assertEqual(set(profiles['Level badge']),set('20'))
        for name in ('Large chat','Medium chat','Small chat'):
            self.assertTrue(profiles[name])
            self.assertTrue(set(profiles[name])<=set('0123456789'))
        for group in profiles.values():
            for variants in group.values():
                self.assertEqual(len(variants),len({f.mask_string(v) for v in variants}))
                self.assertTrue(all(v.ndim==2 and v.any() for v in variants))
    def test_candidate_generation_and_scores(self):
        font=ImageFont.load_default()
        candidates=candidate_library(font,140)
        self.assertTrue(set('0123456789Aa/%.')<=set(candidates))
        self.assertEqual(len(set(CHARACTERS)),94)
        a=np.array([[1,0],[0,1]],dtype=bool)
        reference={'1':(a,), '2':(~a,), '3':(a,)}
        self.assertEqual(compare({'1':a,'2':a,'3':np.ones((3,3),bool)},reference),
                         dict(known=3,exact=1,same_dimensions=2,mean_agreement=.3333))
    def test_missing_font_is_explicit_and_does_not_generate_runtime_data(self):
        with tempfile.TemporaryDirectory() as d:
            with patch('calibrate_tahoma.ImageFont.truetype',side_effect=AssertionError('missing font')):
                result=run_calibration(d,range(10,11))
        self.assertEqual(result['status'],'offline_candidates_only')
        self.assertEqual(result['font_files_missing'],['tahoma.ttf','tahomabd.ttf'])
        self.assertTrue(all(not v for v in result['best_candidates'].values()))
