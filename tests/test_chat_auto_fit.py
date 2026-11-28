"""Chat panel auto-fit preserves physical row alignment and rejects ambiguity."""
import unittest
import numpy as np
from chat_style import fit_chat_panel,row_alignment,aligned_rows,CUSTOM_COLOURS

def panel(pitch=17):
    h=8+5*pitch+9+25
    r=np.zeros((h,260,3),np.uint8)
    for i in range(6):
        top=8+i*pitch
        for x in range(24,180,7):
            r[top:top+9,x:x+4]=(255,0,255) if i%2==0 else (255,255,0)
        r[top+2,4:15]=(176,155,121)
    r[3,4:15]=(176,155,121)
    r[-3,4:15]=(176,155,121)
    return r

class ChatAutoFitTests(unittest.TestCase):
    def test_all_sizes_and_no_trailing_empty_slots(self):
        for configured,actual in ((16,16),(17,17),(19,22)):
            with self.subTest(pitch=actual):
                rgb=panel(actual)
                r,p,count=fit_chat_panel(rgb,configured,CUSTOM_COLOURS)
                self.assertEqual((p,count),(actual,6))
                self.assertEqual((r['left'],r['top'],r['width']),(0,0,260))
                self.assertLess(r['height'],len(rgb))
                cropped=rgb[:r['height']]
                alignment=row_alignment(cropped,configured,CUSTOM_COLOURS)
                masks,rows=aligned_rows(cropped,*alignment[:2],CUSTOM_COLOURS)
                self.assertEqual(rows.shape[1],actual)
                self.assertGreater(masks[-1].sum(),100)
                self.assertGreaterEqual(r['height'],8+5*actual+9)
    def test_offset_and_width_preserved(self):
        rgb=panel();r,_,_=fit_chat_panel(rgb,17,CUSTOM_COLOURS)
        padded=np.pad(rgb,((4,4),(10,10),(0,0)))
        q,_,_=fit_chat_panel(padded,17,CUSTOM_COLOURS)
        self.assertEqual(q['height'],r['height']+4)
        self.assertEqual(q['width'],280)
    def test_reject_blank_sparse_clipped_and_two_panels(self):
        rgb=panel()
        cases=[np.zeros_like(rgb),rgb[:8+5*17+7],np.concatenate([rgb,rgb]),np.pad(rgb,((0,60),(0,0),(0,0)))]
        sparse=np.zeros_like(rgb);sparse[8:17]=rgb[8:17];cases.append(sparse)
        for i,case in enumerate(cases):
            with self.subTest(case=i):self.assertIsNone(fit_chat_panel(case,17,CUSTOM_COLOURS))
