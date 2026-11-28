"""Character status OCR regression; only numeric crops from supplied game sample."""
import base64,zlib,unittest,shutil
from decimal import Decimal
from unittest.mock import patch
from PIL import Image
from leveling import read_number,parse_number

CROPS={
'level':((20,17),'eJxdkDtPwlAYhn+BtOAlIZoYE893vmMa4sGUSL/2XCg1pmXVwSBeZjajP4DZsRMDTYnEwQH9hxYaF5/xmd73CSjSZjCwRmtbYXQUXgaIKLZgDUfq86B2WVa7QJg+RyWBAVUwxqTq4hWhkKkCmQAk50BZFzFRQsC4LIsJwO28zBPOwWqBjOTupOhQ/rT/NmUAQ42o0+ji7nMv+zmEh8XJmYgVJ9/rZS/vjlnvXA9XLS0GIQ99z3/+8Np63UjjlbNxiCYdl8qNs2+3d79wxdYxtbDNgCh/jF+nLnAbcs5mX2WxtOxmvsxPDwAscZTpUcNtOceJcJvtDoAhrL5Vo/6+RRIU4aZMlWE0qssQUoj4v1b4C5f0T74='),
'percent':((46,12),'eJw9kT9v00AYh78EPp8V+Xw+nx3c2I7/yE7sRLUVYnAydCgS7FSBHbKxIFUwsTB1ytC1EzPqhMSQAdFQWBASslnCwMQHMO+5gmd49XvufYeTfhY3BFzAdMZNbjCdUqozpus6qAkLUwxxVgoyrqp2Xs7n5Q2JQZwuzBzNv1t6xJoMaQReVdUi1d/8aJ5Z83vVsuqwNg1ZLBdVaT+8psvlk1+v+HCrwyLPi4Ke/1bwtxMLYt7hla1SFMVh//h7q8xmdX7Fz9YKLCaAsg9kK22U6XRyQ4pbkOnB0fa5CLXy7kGNOSxGgNwSL5FbeTz6BwhMdf1Fgdfxqn55uUI8GY8d13WlVrIHMNz/CHGcx3sDAndVabC/vz0mnjcEUHOHaAeN5AsZ+gBqEaSrP7td+7bne/jy5GP61Qz8ENAe7RH6+VQKCep5YRhFNlzfDgKMJAg4Mo5qqUbXgzBMgIicfvp8ihj8/dAAH2mb3UaL4zihr9+/YCNytrq1bi/kOM4Eoa5gWc8y9iGwhQ81LKsphIBizLKY9UyKkZmmomZo2YDCmYG4RKHvrnVNg/6p0TXO+30Odxr5C8m6lbI=')}
def crop(kind):
    size,data=CROPS[kind];return Image.frombytes('L',size,zlib.decompress(base64.b64decode(data)))

class StatusOCRTests(unittest.TestCase):
    def test_punctuation_spacing(self):
        self.assertEqual(parse_number('0. 14 %','percent'),Decimal('0.14'))
        for text in ('014%','0.14','0.1 4%','/','505/505','101.00%'):
            self.assertIsNone(parse_number(text,'percent'))
    def test_fallback_and_conflict(self):
        with patch('pytesseract.image_to_string',side_effect=['','20','20']) as read:
            self.assertEqual(read_number(crop('level'),'level'),20);self.assertEqual(read.call_count,3)
        with patch('pytesseract.image_to_string',side_effect=['0.14%','0.74%']) as read:
            self.assertIsNone(read_number(crop('percent'),'percent'));self.assertEqual(read.call_count,2)
        with patch('pytesseract.image_to_string',side_effect=['','0.14%','','0.74%']):
            self.assertIsNone(read_number(crop('percent'),'percent'))
    def test_no_invented_digits(self):
        with patch('pytesseract.image_to_string',return_value='014%'):
            self.assertIsNone(read_number(crop('percent'),'percent'))
    @unittest.skipUnless(shutil.which('tesseract'),'Tesseract not on PATH')
    def test_supplied_status_pixels(self):
        self.assertEqual(read_number(crop('level'),'level'),20)
        self.assertEqual(read_number(crop('percent'),'percent'),Decimal('0.14'))
