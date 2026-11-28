"""Exact pixel recognition and safe fallback for the first fixed-font samples."""
import base64,zlib,unittest
from decimal import Decimal
from unittest.mock import patch
from PIL import Image,ImageOps
import numpy as np
from status_digits import recognise_status,recognise_mask,TEMPLATES
from leveling import read_number
from test_status_ocr import crop

def level_crop():
    raw=base64.b64decode('eJxdkM1Kw0AURp/AZlp/oCiI0Ln3joTiVFJoJplJWgOS6VYXUuvPujvRB3DtMqsuElIsLlxU39CpwY1neVbfd0IVm2Q8ThNjUkdi4igkIvELNSCNMGyUtY0KxQhJS+CgHJxzqQekSMhcg8wAsjNQdkCkhYBZXVdzgOtlXWSIYARxJXfnVV8VD/svCw5giEwen9987NnvQ7grT06FRhX4Q/v05iWbncuLdceICKPADx7f/a7ZtPLJ2nOKKMlntWYT+8WGtyUTW8V1mbZDpYr7yfOCAUaI/PWzrlYpv1quit4BgEKS+VGLdbzjTLB2t++UWyvdmL9DsXRq28I9n06bFooiov95fgA5pUt7')
    return Image.frombytes('L',(19,17),zlib.decompress(raw))

class StatusDigitTests(unittest.TestCase):
    def test_supplied_pixels_without_tesseract(self):
        with patch('leveling.read_number_ocr',side_effect=AssertionError('pixel path should suffice')):
            self.assertEqual(read_number(level_crop(),'level'),20)
            self.assertEqual(read_number(crop('percent'),'percent'),Decimal('0.14'))
    def test_translation_and_margin(self):
        for kind,im,expected in [('level',level_crop(),20),('percent',crop('percent'),Decimal('0.14'))]:
            self.assertEqual(recognise_status(ImageOps.expand(im,border=(3,2,4,3)),kind),expected)
    def test_reject_clipping_and_unknown_shapes(self):
        im=crop('percent')
        for bad in (Image.new('L',(46,12)),im.crop((5,0,46,12)),im.resize((92,24)),level_crop()):
            self.assertIsNone(recognise_status(bad,'percent'))
        a=np.array(im);a[3,3]=255
        self.assertIsNone(recognise_status(Image.fromarray(a),'percent'))
    def test_unknown_falls_back(self):
        im=Image.new('L',(46,12))
        with patch('leveling.read_number_ocr',return_value=Decimal('3.69')) as fallback:
            self.assertEqual(read_number(im,'percent'),Decimal('3.69'))
            fallback.assert_called_once_with(im,'percent')
    def test_threshold_disagreement_falls_back(self):
        with patch('status_digits.recognise_mask',side_effect=['0.14%','0.74%']):
            self.assertIsNone(recognise_status(crop('percent'),'percent'))
    def test_verified_template_inventory(self):
        self.assertEqual(set(TEMPLATES['level'][120]),set('20'))
        self.assertEqual(set(TEMPLATES['percent'][140]),set('014578.%'))
