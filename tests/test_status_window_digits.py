"""Native-size XP crop from the supplied Character Status window."""
import base64,zlib,unittest
from decimal import Decimal
from unittest.mock import patch
from PIL import Image,ImageOps
from status_digits import recognise_status
from leveling import read_number

DATA='eJyl0r9P20AUwPH/gdj3w7HPwZwJJf6Bgw0XFIPAqpciJBhYEEOpXNZKzQBzBFOljsysTIgNhBALQ4ZIiQICwWSqSjAgsVUdKhMuuQ5dEOUzvafvG1+hwJFXUf9HxFWLmqoZQSTM2iRvlOaeJ0t3osjWzIqjl0WOOXMj/XG+a8aC/eHs9mrKiuP3IzNNNY7X77ap2yiIHHI4i1yXkFBQr9bg/K0SVt9Zv6o4DNOZFt2pYZErnJshhOlkRRj6AtThDFVcu1EDBptI0dFyiqjIARdlvx/OdRoIY0N5eF+XAn0ju277pp+kW8cJoOP9XOIwlnLfWnLpL0LSrzmlBG42c4sHRVOVRu+WGotavzqcvqJR3JEcoUCaHxEqOnImY/kmIRY8/tRkF7SfPa58Og8+H8qeR4BidXfUqUv5uuaBP9/p3GOZDC6kUgo6o71rz+dAcvl4UkXdIZs2uju+brc7bejr7Od+axXa2k4i1bI90Lv2GRdQjBF2GBs8Gxvp7sMKAAgiNmliDGGRlQ3F1KFs9q7ZPw8yYAzkX36j133qWzwBU0+09Q=='
def sample():return Image.frombytes('L',(53,15),zlib.decompress(base64.b64decode(DATA)))

class StatusWindowTests(unittest.TestCase):
    def test_xp_crop(self):
        with patch('leveling.read_number_ocr',side_effect=AssertionError('pixel path should suffice')):
            self.assertEqual(read_number(sample(),'percent'),Decimal('5.26'))
    def test_margin_and_clipping(self):
        self.assertEqual(recognise_status(ImageOps.expand(sample(),border=3),'percent'),Decimal('5.26'))
        self.assertIsNone(recognise_status(sample().crop((8,0,53,15)),'percent'))
