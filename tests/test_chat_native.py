"""Held-out screenshot masks, not used to construct the template library."""
import base64,json,zlib,unittest
from unittest.mock import patch
import numpy as np
from chat_native import recognise,THRESHOLDS
from tracker import configured_ocr_rows
from chat_style import CUSTOM_COLOURS

DATA='eNrtWclu3EYQ/ZVgznOoqm6R1f+QnHIUfGB6mkkA2TGSGMjn571qksORvEiwpEh2OBCXZrF6e682XV8ffpz+/LUdjoe/fvvjb1wOx+s3x2v1o4725niQJzlMPK5a48yG5ahxl/pr34ma7UV9E+3nC9Est0Wn7e4sOsoYok2lSLOGm1kpikHhmr3JACGIFnF3iKpC1CQlXB0ibhgUroOo8whRhWBy3kHUFB2xv2JZQ6vwBS4hOmP67ROiDWrwAiJo58CwKiGqbRP1KUQti1NrTEtLTD5E8cUdUZVNVPaiehYdckxuE8W8McEs2XhXLPHaV2DgtlSIqheIZMEyyuiSKq61aDVlQ4hysxPUVMe6epZXdBxeARHyIxFh+BwR5III9phEGD5NBL1FBP0PiSA7ItgXiJA+SgTbEyG9MiLANxx+aqffP7wFJ/55jxOW9gc1uA3cHNXoPIaj2fBkzuPLR75X277FV1Ltj441bGGKLc7z1oxtA2Vh51Q/16ErttrMbG1pQuxp4D8BZAqj6Bm0qVpT9WI+SPSSg3jAxqjRQtbloPhEhQKAFY0uiFvL/b0F6YRYA8DXFv6cf1CoHfkSVMnoEM8xBQ8rQdgXZYvzE+KYYI8Os9vYJBcSFB2OjcglGdAhUK7o0Nkh16I02TokS2i1Ljo06aYF/fnaYR8Vl6bP0J1Gkdakz5Cd6faeGnuHfU/4SzBUYOSksGg41zEPMCijnkC3sWG7hGqGomypYwsWfmzv9DGRd59DX6f7em4q6ldTUW5RUfZUlE5FX6l4ukPF0yUVZaOiPDcV646K1bsloMieivJiqOipU1HuUFG+MyrSgf78drq5ASmnU3s34YoFg//Emc7zCplXejrnCVjLLswMuuXexL1y0S0+tFtMzLotEXarVEatyypjixsQ+guiNUOoOKdTG9XAVux0DoxAIDnei1wxcgra2IAgqCRsfNHEh4inKJDImWDKlXIcNT4xn2TIRCkHG0nZ8lQJSSPG8WWZoSizm5znEvYC2lKLp2TBI6ovTGugaMKHJVixDJZMifdYA2gZOgOwcJUqOVgO30gWxWhTDIPL5+jZAHUFnuusZcJ3szIjGsFLsNZnvnd5VcfTuY9u6x8djIiwd2Bs9gAwaoCRBm0Do94GY97AaBdglOUpPyUYF3Ocz2C0DYwcrW1ghGXdwOjfDhgvMpCtaPXuw81NZB56JU+YefgOrBeepiOZmXTg2TtUe2beVuQueXneqcJ9ilbfqUqeIp3G1hOmA+IRpuOMLAzZ+Cy1J+MBNWKgxyEWaW/nDJ2pM3el4kEZSmzJMXAD8dF6qsuPWprp8enGm/FKvhUqQ6gB1z4TL+GxI/HmbVeFbBoP0LOo0pWhDFJ0HZX2oM0jSiBf+cOyIJ7CBB0uqXKsmCByejkhOm/5ezOFLwNapxVaXX6BlnRoyRla8gBotc9Dy+8HLflaaLHSepIXDC0atrUYv0WGuWy2zY+m6XmrKlXPlcKtYnnGmfXkCchUP7vmy+rjlqft7lknrDXQuzaru1zGAh1q53vkETUnuLid5lyjsKYjIk5B8IX9v6ojssEy0s0xKtSJ4zFPDbYFf5DJmpiGYQRInJDZ2JASR5VrzQOiPaAuiis2QFBL8UCPUjqYkAcn8ko4bEJabUnZECNGbVRyz2aMNKEsxmfjzJyQidyI3CvNZUkFaXuB1DwjXNHI1nKPLAvT0E41wL3l4EWkemOUhPgBPX8q3UpQIalwFakZmYPh4tkjW42MrUY7A5YSCeM6qQyyVFkmZZzUsCaHvhRpS1ceXqcOfJ2SVPzhTfUB62RcrOK9vEtgDBWCUDVE7lth1zFf1o1ip0ZnhQbjwE4xIpJecE5pYmVXTyrf5nF4mRSWB1HYWJJ4FArnPYXbJYVZPpcw9qSwNogGhTVH4X2lsDPQtQdROHcKy10K2/dB4XxBYf7XZqGw/0/he/jqN/8CpSVVDQ=='

def samples():
    for size,kind,text,expected,shape,lo,hi in json.loads(zlib.decompress(base64.b64decode(DATA))):
        row=np.zeros((*shape,3),np.uint8)
        for threshold,bits in zip(THRESHOLDS[kind],(lo,hi)):
            mask=np.unpackbits(np.frombuffer(bytes.fromhex(bits),dtype=np.uint8),count=shape[0]*shape[1]).reshape(shape).astype(bool)
            # Bright core pixels must also pass the configured colour gate.
            # 255 is a valid representative for the upper-threshold mask.
            intensity=255 if threshold==THRESHOLDS[kind][-1] else threshold
            row[mask]=(intensity,0,intensity) if kind=='xp' else (intensity,intensity,0) if kind=='adena' else (0,170,intensity)
        yield size,kind,text,None if expected is None else tuple(expected),row

class ChatNativeTests(unittest.TestCase):
    def test_held_out_pixels(self):
        for size,kind,text,expected,row in samples():
            with self.subTest(size=size,kind=kind,text=text):
                self.assertEqual(recognise(row,kind),expected)
    def test_clipped_blank_and_wrong_colour(self):
        for _,kind,_,expected,row in samples():
            if expected is not None:
                self.assertIsNone(recognise(np.zeros_like(row),kind))
                self.assertIsNone(recognise(row[:,4:],kind))
                self.assertIsNone(recognise(row,'shot' if kind!='shot' else 'xp'))
    def test_pipeline_enabled_and_disabled(self):
        for _,kind,text,expected,row in samples():
            if expected is None:continue
            line='Use Soulshot: No Grade.' if kind=='shot' else ('You have obtained '+text+' Adena.' if kind=='adena' else f'You have acquired {expected[0]} XP and {expected[1]} SP.')
            with patch('tracker.recognise_numeric',return_value=None),patch('tracker.single_ocr',side_effect=AssertionError('native match should bypass OCR')):
                self.assertEqual(list(configured_ocr_rows([row],CUSTOM_COLOURS,use_templates=True)),[('template_line',line)])
            with patch('tracker.recognise_native_chat',side_effect=AssertionError('disabled')),patch('tracker.single_ocr',return_value=line):
                self.assertEqual(list(configured_ocr_rows([row],CUSTOM_COLOURS)),[('line',line)])
    def test_unmatched_falls_back(self):
        for _,kind,text,expected,row in samples():
            if expected is not None:continue
            line='Use Soulshot: No Grade.' if kind=='shot' else 'You have obtained '+text+' Adena.'
            with patch('tracker.recognise_numeric',return_value=None),patch('tracker.single_ocr',return_value=line) as ocr:
                self.assertEqual(list(configured_ocr_rows([row],CUSTOM_COLOURS,use_templates=True)),[('line',line)])
                self.assertGreaterEqual(ocr.call_count,2)
