import base64,json,zlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from numeric_templates import recognise,library,number
from tracker import configured_ocr_rows,parse
from chat_style import CUSTOM_COLOURS
from preferences import load_numeric_templates,save_numeric_templates

# Independent screenshot, binary reward text only, not used for templates.
FIXTURE='eNrtl8tuGzEMRf/Fay9IipaobzGycBnNsuiyn997pXHiok7RIov04THgeYhvUmfs8/nw9cvheC49jtqfjmfTo51wcZDHoWHr/MPC/DbRIUM2kbAWLysmDedRkne+S949XLxaLQWOMnYDEHUtIlkdukWvkncP6HhURyCqElfREl4YSEDLqgwufYrWwxFlSc2S4b1qMnTpMAGdatDYtAlkoGDMjiYtzLCkPbRLVzxJ947LMoOHgEnvQacIvZTC4I2JV54ExZgR0oaZ6/Roig+u6VmjFtQR4iyBudGOF3hqwhLILuemo/oGyc2EUh5l6wwx2qgo9lCkw9SYN9ZwExuLgmQoFz4QOSMyF0oh8xViwEGKJhxr9ik8+4isV09dGT4XLmwllHnTjZoUo2BITRacqS1tDoCtnu4lMNWsMi3tJYjVJWGNUQA29FqCOWXmq6cRmViqFeWqKLNqxYE4OosPPXiATcabKAGEGRuKGzzhGpNKXw2mOQUXzYabjkHV5zXHmNqc8Q4kA+GWc45VrpN1b/zet7/eu0HtL4LJAXB9sPZDWVs/jrXjV1hbP5C14fU3WJsP1j5Y+4ez9vI8Pl+AW2zXnbVi/xRr30TmTjHMIH7jcdb8tYnxJuOUXKiCEYfWq830nzkpUcAUkdONTVCpcaudAL80snkD7eopFwVtIUt9Pm4TjCBf/Y58oBH2X8dW9Lm9gjQDVZMUF6IKmyUnqrBv62RokK/mOxKmE/J0J9INW8DnXoCrbeiA3b5l+IsT7GKQjwS85WEDT2O+hnI6kRsnbaMT2Mm4B7AZE27l1cm0OhdsOVmZuBWwUcrUBoBenOApra6F6WT9beDbgFWSCSgklrlohHLCTM3EY4BsIg6vGzoBjmT1ZPQJejBJNtAbc4LqP6MnRFL83z9HDk9P3wBvdA7S'

def samples():
    for kind,values,shape,raw in json.loads(zlib.decompress(base64.b64decode(FIXTURE))):
        mask=np.unpackbits(np.frombuffer(bytes.fromhex(raw),dtype=np.uint8),count=shape[0]*shape[1]).reshape(shape).astype(bool)
        row=np.zeros((*shape,3),np.uint8)
        row[mask]=(255,0,255) if kind=='xp' else (255,255,0)
        yield kind,tuple(values),row

class NumericTemplateTests(unittest.TestCase):
    def test_library_digits(self):
        self.assertEqual(set(library()['digits']),set('0123456789'))
        for d,variants in library()['digits'].items():
            for glyph in variants:self.assertEqual(number(glyph),int(d))
    def test_held_out_reward_lines(self):
        for kind,values,row in samples():
            self.assertEqual(recognise(row,kind),values)
            with patch('tracker.single_ocr',side_effect=AssertionError('fast path should not invoke OCR')):
                result=list(configured_ocr_rows([row],CUSTOM_COLOURS))
            self.assertEqual(len(result),1)
            self.assertEqual(result[0][0],'template_line')
            event=parse(result[0][1])
            self.assertEqual(event[0],kind)
            self.assertEqual(event[3:],values if kind=='xp' else (values[0],0))
    def test_disabled_uses_ocr(self):
        kind,values,row=next(samples())
        line='You have acquired 398 XP and 19 SP.'
        with patch('tracker.single_ocr',return_value=line):
            self.assertEqual(list(configured_ocr_rows([row],CUSTOM_COLOURS,use_templates=False)),[('line',line)])
    def test_clipped_and_wrong_geometry_fallback(self):
        kind,values,row=next(samples())
        self.assertIsNone(recognise(row[:19],kind))
        self.assertIsNone(recognise(row[:,:100],kind))
        self.assertIsNone(recognise(np.zeros_like(row),kind))
        self.assertIsNone(recognise(row,'adena'))
    def test_quest_items_still_use_ocr(self):
        row=np.zeros((21,340,3),np.uint8);row[4:16,10:250]=(255,255,0)
        line='You have earned Turek Dog Tag.'
        with patch('tracker.single_ocr',return_value=line):
            self.assertEqual(list(configured_ocr_rows([row],CUSTOM_COLOURS)),[('line',line)])
    def test_preference(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'prefs.json'
            self.assertTrue(load_numeric_templates(path));save_numeric_templates(False,path)
            self.assertFalse(load_numeric_templates(path))
            save_numeric_templates(True,path);self.assertTrue(load_numeric_templates(path))
