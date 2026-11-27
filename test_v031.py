import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from chat_style import *
from tracker import configured_ocr_rows, parse

class ChatStyleTests(unittest.TestCase):
    def row(self,colour,pitch=18):
        a=np.zeros((pitch,220,3),np.uint8)
        a[3:12,10:90]=[int(colour[i:i+2],16) for i in (1,3,5)]
        return a
    def test_measured_pitches(self):
        # Full-resolution in-game screenshots: small 16, medium 17, large 19.
        self.assertEqual(TEXT_SIZES,{'Small':16,'Medium':17,'Large':19})
        with tempfile.TemporaryDirectory() as d:
            import json
            p=Path(d)/'prefs.json'
            p.write_text(json.dumps({'chat_style':dict(colours=CUSTOM_COLOURS,size='Large',pitch=18)}))
            self.assertEqual(load_style(p)['pitch'],19)
            self.assertEqual(load_style(p)['colours'],CUSTOM_COLOURS)
            save_style(dict(colours=CUSTOM_COLOURS,size='Manual',pitch=18),p)
            self.assertEqual(load_style(p)['pitch'],18)
    def test_pitches_and_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prefs.json'
            self.assertEqual(load_style(p)['colours'],DEFAULT_COLOURS)
            self.assertEqual(load_style(p,21)['size'],'Manual')
            for size,pitch in TEXT_SIZES.items():
                save_style(dict(colours=CUSTOM_COLOURS,size=size,pitch=20),p)
                self.assertEqual(load_style(p)['pitch'],pitch)
            self.assertEqual(save_style(dict(colours=CUSTOM_COLOURS,size='Manual',pitch=21),p)['pitch'],21)
            with self.assertRaises(ValueError):save_style(dict(colours=dict(CUSTOM_COLOURS,xp='red'),size='Small',pitch=16),p)
    def test_exact_and_shared(self):
        for kind in ('xp','adena','item','consumable'):
            for size,pitch in TEXT_SIZES.items():
                row=self.row(CUSTOM_COLOURS[kind],pitch)
                self.assertEqual(row_group(row,CUSTOM_COLOURS),(kind,))
                self.assertEqual(styled_rows(row,pitch,CUSTOM_COLOURS).shape,(1,pitch,220))
        self.assertEqual(set(row_group(self.row('#FFFF00'),DEFAULT_COLOURS)),{'adena','item'})
        self.assertEqual(set(row_group(self.row('#B09B79'),DEFAULT_COLOURS)),{'xp','consumable','other'})
    def test_shared_text_routing(self):
        for key,line in [('xp','You have acquired 389 XP and 15 SP.'),('adena','You have obtained 102 Adena.'),('item','You have obtained Suede.'),('consumable','Use Soulshot: No Grade.')]:
            with patch('tracker.single_ocr',return_value=line):
                self.assertEqual(list(configured_ocr_rows([self.row(DEFAULT_COLOURS[key])],DEFAULT_COLOURS)),[('line',line)])
                self.assertEqual(parse(line)[0],key)
        for line in ['Your soulshots are enabled.','You use Mortal Blow.']:
            with patch('tracker.single_ocr',return_value=line):
                self.assertEqual(list(configured_ocr_rows([self.row('#B09B79')],DEFAULT_COLOURS)),[])
    def test_small_font_reported_errors(self):
        self.assertEqual(parse('You haye obtained 102 Adena.'),('adena','You','Adena',102,0))
        for text in ['Use Soulshot: Hi Grade.','Use Soulshot: fo Grade.','Use Soulshot: No Grades.']:
            self.assertIsNone(parse(text))
    def test_custom_colour(self):
        colours=dict(CUSTOM_COLOURS,xp='#FF5500')
        self.assertEqual(row_group(self.row('#FF5500'),colours),('xp',))
        with patch('tracker.single_ocr',return_value=''):
            self.assertEqual(list(configured_ocr_rows([self.row('#FF5500')],colours))[0][0],'uncertain:xp')
    def test_shared_conflict_not_counted(self):
        with patch('tracker.single_ocr',side_effect=['You have obtained 102 Adena.','You have obtained Suede.','']):
            self.assertTrue(list(configured_ocr_rows([self.row('#FFFF00')],DEFAULT_COLOURS))[0][0].startswith('uncertain'))
