import unittest
import numpy as np
from chat_style import row_alignment,aligned_rows,CUSTOM_COLOURS

class AlignmentSafetyTests(unittest.TestCase):
    def test_three_lines_infer_spacing_across_crop_offsets(self):
        for pitch in (16,17,18,19,21,22):
            for offset in range(pitch):
                rgb=np.zeros((offset+5*pitch+20,320,3),np.uint8)
                starts=[offset+3+i*pitch for i in (0,1,3)]
                for y in starts:rgb[y:y+12,10:160]=(255,0,255)
                p,phase,confirmed=row_alignment(rgb,19,CUSTOM_COLOURS)
                self.assertEqual((p,confirmed),(pitch,True),(pitch,offset,p,phase))
                for y in starts:self.assertEqual((y-phase)//p,(y+11-phase)//p)
                masks,rows=aligned_rows(rgb,p,phase,CUSTOM_COLOURS)
                self.assertEqual(sum(int((r[:,:,0]>200).sum()) for r in rows),3*12*150)
    def test_single_line_phase_without_inventing_pitch(self):
        for pitch in (16,18,19,21):
            for offset in range(pitch):
                rgb=np.zeros((pitch*3,320,3),np.uint8)
                y=offset+2;rgb[y:y+12,10:160]=(255,255,0)
                p,phase,confirmed=row_alignment(rgb,pitch,CUSTOM_COLOURS)
                self.assertEqual((p,confirmed),(pitch,False))
                self.assertEqual((y-phase)//p,(y+11-phase)//p)
    def test_conflicting_sparse_lines_do_not_invent_pitch(self):
        rgb=np.zeros((100,320,3),np.uint8)
        rgb[5:17,10:160]=(255,0,255);rgb[27:39,10:160]=(255,255,0)
        self.assertEqual(row_alignment(rgb,19,CUSTOM_COLOURS)[0],19)
