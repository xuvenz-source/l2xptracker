import unittest
from unittest.mock import patch
import numpy as np
from tracker import ocr_rows, repeated_row_indices, overlap, parse

XP='You have acquired 221 XP and 9 SP.'
XP2='You have acquired 261 XP and 12 SP.'
# Synthetic row masks, enough pixels to trigger visual repeat detection.
A=np.full((18,340),255,np.uint8); A[3:14,20:70]=0
B=np.full_like(A,255); B[3:14,110:160]=0
C=np.full_like(A,255); C[3:14,200:250]=0
ROWS=np.zeros((2,18,340,3),np.uint8)
EMPTY={'text':[],'top':[],'height':[]}

def batch(*lines):
    return {'text':list(lines),'top':[4*(14+46*i) for i in range(len(lines))],'height':[16]*len(lines)}

class RepeatTests(unittest.TestCase):
    def test_visual_repeats(self):
        self.assertEqual(repeated_row_indices([(A,False),(A.copy(),False),(B,False)]),{0,1})
        self.assertEqual(repeated_row_indices([(A,False),(A,True)]),set())
    def test_identical_xp_independently_counted(self):
        with patch('tracker.row_images',return_value=(A,False)), patch('tracker.pytesseract.image_to_data',return_value=batch(XP,XP)), patch('tracker.single_ocr',return_value=XP) as single:
            result=list(ocr_rows(ROWS))
        self.assertEqual(result,[('line',XP),('line',XP)])
        self.assertEqual(sum(parse(line)[3] for _,line in result),442)
        self.assertEqual(single.call_count,6)
    def test_similar_different_xp_not_copied(self):
        with patch('tracker.row_images',return_value=(A,False)), patch('tracker.pytesseract.image_to_data',return_value=batch(XP,XP)), patch('tracker.single_ocr',side_effect=[XP,XP,XP,XP2,XP2,XP2]):
            result=list(ocr_rows(ROWS))
        self.assertEqual(result,[('line',XP),('line',XP2)])
    def test_conflicting_row_stays_review(self):
        with patch('tracker.row_images',return_value=(A,False)), patch('tracker.pytesseract.image_to_data',return_value=batch(XP,XP)), patch('tracker.single_ocr',side_effect=[XP,XP,XP,XP,XP2]):
            result=list(ocr_rows(ROWS))
        self.assertEqual(result[0],('line',XP)); self.assertEqual(result[1][0],'uncertain')
    def test_omitted_row_recovered(self):
        with patch('tracker.row_images',return_value=(A,False)), patch('tracker.pytesseract.image_to_data',return_value=EMPTY), patch('tracker.single_ocr',return_value=XP):
            self.assertEqual(list(ocr_rows(ROWS)),[('line',XP),('line',XP)])
    def test_repeated_adena(self):
        # Deliberately use a mask with no five-word split, exercising existing
        # full-line alternative validation separately for each yellow row.
        text='You have earned 85 Adena.'
        with patch('tracker.row_images',return_value=(A,True)), patch('tracker.pytesseract.image_to_data',return_value=EMPTY), patch('tracker.single_ocr',return_value=text) as single:
            result=list(ocr_rows(ROWS))
        self.assertEqual(result,[('line',text),('line',text)]); self.assertEqual(single.call_count,4)
    def test_scroll_with_anchor(self):
        a,b,c=(x<128 for x in (A,B,C))
        self.assertEqual(overlap(np.array([a,b,c,c]),np.array([b,c,c,c])),1)
        self.assertEqual(overlap(np.array([a,b,c,c]),np.array([a,b,c,c])),0)
    def test_identical_frames_no_invented_drop(self):
        a=A<128; self.assertEqual(overlap(np.array([a]*4),np.array([a]*4)),0)
if __name__=='__main__': unittest.main()
