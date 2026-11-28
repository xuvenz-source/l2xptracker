import unittest
import numpy as np
from calibrate_texture import sample_texture,holdout_words,shortlist,mask_at

class TextureCalibrationTests(unittest.TestCase):
    def test_scaling_preserves_binary_nearest_and_phase(self):
        a=np.zeros((12,12),np.uint8);a[3:9,3:9]=255
        nearest=sample_texture(a,12,6,'Nearest',(0,0))
        self.assertTrue(set(np.unique(nearest))<={0,255})
        self.assertEqual(mask_at(nearest,140).shape,(3,3))
        b=sample_texture(a,12,9,'Bilinear',(0,0))
        c=sample_texture(a,12,9,'Bilinear',(.5,.5))
        self.assertTrue(np.any((b>0)&(b<255)))
        self.assertFalse(np.array_equal(b,c))
    def test_holdout_inventory(self):
        words,coverage=holdout_words()
        self.assertGreater(coverage['usable_rows'],0)
        self.assertLessEqual(coverage['usable_rows'],coverage['eligible_rows'])
        self.assertTrue(words)
        for group in words.values():
            self.assertTrue(all(m.any() for variants in group.values() for m in variants))
    def test_shortlist_deduplicates_thresholds(self):
        common=dict(source=20,target=12,weight='Regular',quality='Grayscale',filter='Box',phase=(0,0),exact=1,mean_agreement=.8,same_dimensions=5)
        rows=[dict(common,threshold=80),dict(common,threshold=175),dict(common,threshold=140,filter='Nearest')]
        self.assertEqual(len(shortlist(rows)),2)
