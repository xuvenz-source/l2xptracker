import unittest,base64,zlib,json
from unittest.mock import patch
import numpy as np
from numeric_templates import strict_adena,recognise
from tracker import configured_ocr_rows,recover_adena_digits
from chat_style import CUSTOM_COLOURS

# Verified live glyph masks at 175 and 180; no scene background.
DATA='eJztnF124yAMhffS5z5IggJeS08fUmrvfwlzhTMz7cRFdEJ/YnPP9KR2HFkGhi8SqI+PjyL3juLTfYj3dzS0HwVK5dVvvMdELi0zEf6lFmOe19eti4UYpzNxJm7yLPvfTmzcCObUnkv6S4Om5JIXkpnnwIzniSmmZ5lpoSWpvzDzkGJ2+QE/dVt8grnkKQQKXnwg5sRTCkEcO2LYwyM+6zU5Z7KMZeEJDsCeTy94MLQhCw6TwF/H+vwiglPlKsMYPi36kRSnycGRBc8Lg9OS1b5Db5P3XuKCqxajyeCEuiDsJhZfOmLOST1h9QRv41lhNxEMWr0AJ7y6AIuSSnPDKz2k4i9cI22HifTJt8bia6XfTZZ81EEVSEqTZSpNpp/XdnDlHmaTSXDlSvQgehG9GgK81b7L5AT2ObmAa2DQGSMXd0/uBG/4hdJ5lKEjta1nHayil4ToXfbiTm0jd6hddwNOu9KAU/wLJ9cEJzpRukk48dVw8p8JJxpwGrpKd0/3iKPcGkclP1C1KxmoWgpgUiNd6qjCjOConS51VGFSwlTwsO34pYw4SudMEGjRk/ip2zLiqCllPGJgx4zpjy1jVVTxzLzS5cwgw1gVVQETJBXKLrMXbYSqDFRlfIdxy5kus9ULBqoUwuq6tNCljqq1mdT1ctpushqq0MUYt2i5jJOCHraarIaqWMYt5RkjDJ77tpE79D0aMdm+dEjQIU6KtIJuLjHZGXSxCXRGTHYF6KYBum8AnVRA5wfoDqq38R0P7O1K4Zwrexd7Ul7bSKUZJdW72Cu8aSSVhT3wEwBqy5Ga8R3uwl4POJo5Oj5xPb5DY/ksOFxBXzeWXTW+08ZSUq0IMow5A3v6/YXPh2bC1cIejjWlWUiVrV6wsCcrqXwLqSi5OvY8lbvlcjvDVonvYiW+wxl6wVcZNFnOxsg1sJcieoCnF4wySnNqG7lD36MR3+1LhwRd/nfN7Q/o5ibQGYnMj4GuHt99CHRWfDdAt9FkVdD5nqCjAbrb0Vi/27NM7Olae+vuEBN7PySteRnfuc7rdy64Na057WD97nlrH+TbtKbF0NfYy++kNd23rd/V4rv/TWtmXi7iO3Qv/r9hlOWR1vzpGvHdvtSyftcOuhtZv3sFuvP63aeBbg8bVZ7t9bvbBt0Xrt8N0N2I3sR3MQzs7Up17PGSNQfou5QSgKCZepUSUNnWLX3q3KhMQQ/UVkpQxx6eEhbxS49SAsygKfUqJaCs2/87lRJwcbRPKYEOQulVSgDeYJj1KiXAt5hupQRex/4oJbgRjfhuXzok6P7dn/kKdOnamrlrQHexfjdAt6XOoKvsz8QbPEB3SL2J78JYv9uXzFJxnbe7lYp/JEdqlorHbvFd0pgN2Ovzd0w0GdYpvsM82w97mjfsWCoel46l4qVHe5WKn2scesR3gfphryT0B/ZuRCO+25eaQNcnvvs5oMtXgY4+DXQX8d0A3Za+EHQyQHdQjfhuzzL2Z34wvqvuz/w52PuC+K7bnwLriD2+Gnv5PewFw5ixbWX32NNU98DeLWnEd/vSIeO7DdDJAeK760F3tPhORnx3VN09Pf0CrQ3y1w=='
def samples():
    for shape,value,a,b in json.loads(zlib.decompress(base64.b64decode(DATA))):
        row=np.zeros((*shape,3),np.uint8)
        for raw,colour in [(a,(177,177,0)),(b,(255,255,0))]:
            mask=np.unpackbits(np.frombuffer(bytes.fromhex(raw),dtype=np.uint8),count=shape[0]*shape[1]).reshape(shape).astype(bool)
            row[mask]=colour
        yield value,row
def line(v):return f'You have earned {v} Adena.'

class AdenaDigitRecoveryTests(unittest.TestCase):
    def test_live_glyphs(self):
        for value,row in samples():
            self.assertEqual(strict_adena(row)[0],value)
            self.assertEqual(recognise(row,'adena'),(value,))
    def test_five_live_review_cases(self):
        reads=[['6/7','6/','6/'],['84','64','84'],['81','@1','Si'],['84','64','84'],['7/6','76','7/6']]
        for (value,row),tokens in zip(samples(),reads):
            with patch('tracker.single_ocr',side_effect=[line(x) for x in tokens]),patch('tracker.pytesseract.image_to_string',return_value=str(value)):
                self.assertEqual(list(configured_ocr_rows([row],CUSTOM_COLOURS)),[('template_line',line(value))])
    def test_conflicting_numeric_verifier_does_not_override(self):
        value,row=list(samples())[1]
        self.assertIsNone(recover_adena_digits(row,[line(84),line(64)],lambda crop,nearest:'64'))
        self.assertIsNone(recover_adena_digits(row,[line(84),line(94)],lambda crop,nearest:'84'))
        self.assertIsNone(recover_adena_digits(row,[line(64)],lambda crop,nearest:'84'))
        self.assertIsNone(recover_adena_digits(row,[line(84),'You have earned Turek Dog Tag.'],lambda crop,nearest:'84'))
    def test_no_global_slash_substitution(self):
        value,row=next(samples())
        self.assertIsNone(recover_adena_digits(row,[line('6/7')],lambda crop,nearest:'677'))
        self.assertIsNone(strict_adena(row[:12]))
