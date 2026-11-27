import unittest
import numpy as np
from chat_style import aligned_rows,row_bounds,bottom_clipped,CUSTOM_COLOURS
from tracker import overlap

def frame(ids,height=187):
    # Actual failing geometry: height 187, pitch 22, phase 20.
    rgb=np.zeros((height,300,3),dtype=np.uint8)
    rgb[:]=(45,30,20)
    for i,j in enumerate(ids):
        y=-2+22*i+6
        rgb[max(0,y):min(height,y+12),4:40+7*j]=(255,0,255)
        rgb[max(0,y):min(height,y+12),100+8*j:107+8*j]=(255,0,255)
    return rgb

class BottomRowTests(unittest.TestCase):
    def test_reported_geometry_excludes_cut_row(self):
        rgb=frame(range(9))
        self.assertEqual(row_bounds(187,22,20),(-2,174))
        self.assertTrue(bottom_clipped(rgb,22,20,CUSTOM_COLOURS))
        masks,rows=aligned_rows(rgb,22,20,CUSTOM_COLOURS)
        self.assertEqual(rows.shape,(8,22,300,3))
        self.assertTrue(np.array_equal(rows[-1],rgb[152:174]))
        self.assertTrue(rows[-1].any(axis=(1,2)).all())
    def test_delayed_message_counted_once_after_scroll(self):
        a,b=frame(range(9)),frame(range(1,10))
        old,_=aligned_rows(a,22,20,CUSTOM_COLOURS)
        new,rows=aligned_rows(b,22,20,CUSTOM_COLOURS)
        self.assertEqual(overlap(old,new),1)
        # The previously clipped message is now a complete row.
        self.assertTrue(np.array_equal(rows[-1],b[152:174]))
        self.assertEqual(overlap(new,new),0)
    def test_extend_crop_retains_last_row(self):
        rgb=frame(range(9),196)
        self.assertFalse(bottom_clipped(rgb,22,20,CUSTOM_COLOURS))
        masks,rows=aligned_rows(rgb,22,20,CUSTOM_COLOURS)
        self.assertEqual(len(rows),9)
        self.assertTrue(np.array_equal(rows[-1],rgb[174:196]))
    def test_every_offset_never_pads_bottom(self):
        for p in range(16,24):
            for phase in range(p):
                rgb=np.full((187,300,3),100,dtype=np.uint8)
                _,rows=aligned_rows(rgb,p,phase,CUSTOM_COLOURS)
                self.assertTrue((rows[-1]==100).all(),(p,phase))
