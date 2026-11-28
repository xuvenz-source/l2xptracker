import unittest
import numpy as np
from chat_style import row_alignment,aligned_rows,CUSTOM_COLOURS
from tracker import overlap

def frame(ids,pitch=21):
    rgb=np.zeros((len(ids)*pitch+4,340,3),np.uint8)
    for i,j in enumerate(ids):
        start=4+i*pitch+3
        colour=(255,0,255) if j in (3,6,9) else (255,255,0) if j in (8,11) else (176,155,121)
        rgb[start:start+12,10+j*8:45+j*8]=colour
        rgb[start:start+12,170+j*6:180+j*6]=colour
    return rgb

class SparseChatTests(unittest.TestCase):
    def test_beige_lines_resolve_sparse_reward_anchors(self):
        rgb=frame(range(9))
        pitch,phase,ok=row_alignment(rgb,19,CUSTOM_COLOURS)
        self.assertTrue(ok);self.assertEqual(pitch,21)
        masks,rows=aligned_rows(rgb,pitch,phase,CUSTOM_COLOURS)
        self.assertEqual(len(masks),len(rows));self.assertEqual(rows.shape[1],21)
    def test_reproject_previous_frame_no_message_loss(self):
        old,new=frame(range(9)),frame(range(2,11))
        p,phase,ok=row_alignment(new,19,CUSTOM_COLOURS)
        self.assertTrue(ok)
        a,_=aligned_rows(old,p,phase,CUSTOM_COLOURS)
        b,rows=aligned_rows(new,p,phase,CUSTOM_COLOURS)
        self.assertEqual(overlap(a,b),2)
        self.assertEqual(overlap(b,b),0)
    def test_blank_no_false_calibration(self):
        self.assertEqual(row_alignment(np.zeros((200,340,3),np.uint8),19,CUSTOM_COLOURS),(19,0,False))
