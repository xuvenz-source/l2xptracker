import unittest
from decimal import Decimal
from unittest.mock import Mock
from PIL import Image
import numpy as np
from player_frame import fit_player_frame,verified_player_frame

def sample():
    # Synthetic geometry matching the supplied native compact frame.
    rgb=np.zeros((82,274,3),np.uint8)
    rgb[42:52,22:241]=(180,35,35)
    rgb[55:65,22:268]=(20,60,120)
    return rgb

class PlayerFrameTests(unittest.TestCase):
    def test_geometry_and_padding(self):
        a=sample()
        r=fit_player_frame(a)
        self.assertEqual(r,{'level':dict(left=23,top=6,width=18,height=17),'percent':dict(left=105,top=66,width=80,height=14)})
        shifted=fit_player_frame(np.pad(a,((7,9),(6,12),(0,0))))
        for k,z in r.items():self.assertEqual(shifted[k],dict(z,left=z['left']+6,top=z['top']+7))
    def test_missing_clipped_ambiguous(self):
        a=sample()
        for bad in (np.zeros_like(a),a[10:],a[:70],a[:,:160],np.concatenate((a,a),axis=0)):
            self.assertIsNone(fit_player_frame(bad))
    def test_verifies_both_fields(self):
        im=Image.fromarray(sample());reader=Mock(side_effect=[20,Decimal('23.03')])
        r,v=verified_player_frame(im,reader)
        self.assertEqual(v,{'level':20,'percent':Decimal('23.03')})
        self.assertEqual([call.args[0].size for call in reader.call_args_list],[(18,17),(80,14)])
        self.assertIsNone(verified_player_frame(im,Mock(side_effect=[20,None])))
        reader=Mock()
        self.assertIsNone(verified_player_frame(Image.new('RGB',(274,82)),reader))
        reader.assert_not_called()
