import os,sys,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
from calibrate_rasterisation import word_profiles,details,evaluate,run
from gdi_tahoma import GdiTahoma

class RasterisationResearchTests(unittest.TestCase):
    def test_word_inventory(self):
        profiles=word_profiles()
        self.assertEqual(set(profiles),{'Large chat','Medium chat','Small chat'})
        for group in profiles.values():
            self.assertIn('You',group)
            self.assertTrue(all(m.ndim==2 and m.any() for variants in group.values() for m in variants))
    def test_word_spacing_and_conflicts(self):
        mask=np.array([[1,0,1],[1,1,1]],bool)
        ref={'1':(mask,),'7':(mask,)}
        self.assertEqual(details({'1':mask},ref),dict(exact_labels=['1'],cross_label_conflicts=[dict(label='1',also_matches=['7'])]))
        ranks={'chat':[]}
        evaluate({'1':mask.astype(np.uint8)*255,'word':np.ones((3,4),np.uint8)*255},
                 {'chat':{'1':(mask,)}},{'chat':{'word':(np.ones((3,5),bool),)}},{'renderer':'test'},ranks)
        self.assertTrue(all(r['exact']==1 and r['words']['same_dimensions']==0 for r in ranks['chat']))
    def test_missing_fonts_no_runtime_changes(self):
        with tempfile.TemporaryDirectory() as d:
            report=run(d,(11,),include_gdi=False)
        self.assertEqual(report['rendered_configurations'],0)
        self.assertEqual(report['status'],'research_only')
    @unittest.skipUnless(sys.platform=='win32' and (Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/'tahoma.ttf').is_file(),'Windows Tahoma required')
    def test_real_gdi_surface(self):
        with GdiTahoma(12,400,4) as font:
            a=font.render('123');b=font.render('You')
            self.assertGreater(a.max(),0);self.assertGreater(b.max(),0)
            self.assertTrue(np.array_equal(a,font.render('123')))
        self.assertIsNone(font.dc)
