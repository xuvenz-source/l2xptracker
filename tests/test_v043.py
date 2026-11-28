import unittest
import numpy as np
from chat_style import row_alignment,aligned_rows,CUSTOM_COLOURS
from tracker import overlap

def frame(pitch,phase=4,ids=tuple(range(11))):
    rgb=np.zeros((phase+len(ids)*pitch+3,320,3),np.uint8)
    for i,j in enumerate(ids):
        start=phase+i*pitch+3
        colour=(255,255,0) if j%2 else (255,0,255)
        rgb[start:start+12,10:55+j*7]=colour
        rgb[start:start+12,70+j*8:77+j*8]=colour
    return rgb

class AlignmentTests(unittest.TestCase):
    def test_large_18_and_19(self):
        for p in (16,17,18,19,20):
            rgb=frame(p)
            actual,phase,confirmed=row_alignment(rgb,19,CUSTOM_COLOURS)
            self.assertTrue(confirmed);self.assertEqual(actual,p)
            masks,rows=aligned_rows(rgb,actual,phase,CUSTOM_COLOURS)
            self.assertEqual(len(masks),len(rows))
            self.assertEqual(rows.shape[1],p)
    def test_shift_reads_matching_rgb(self):
        a,b=frame(18),frame(18,ids=tuple(range(2,13)))
        p,phase,confirmed=row_alignment(a,19,CUSTOM_COLOURS)
        old,_=aligned_rows(a,p,phase,CUSTOM_COLOURS)
        new,rows=aligned_rows(b,p,phase,CUSTOM_COLOURS)
        self.assertEqual(overlap(old,new),2)
        self.assertTrue(rows[-1,:,:,0].any())
    def test_sparse_keeps_configured_pitch(self):
        self.assertEqual(row_alignment(frame(18,ids=(1,2)),19,CUSTOM_COLOURS)[0],19)
        self.assertEqual(row_alignment(np.zeros((180,320,3),np.uint8),19,CUSTOM_COLOURS),(19,0,False))

    def test_mixed_pitch_jobs_do_not_drop_rows(self):
        import queue
        from unittest.mock import patch
        from tracker import App
        a=App.__new__(App);a.inbox=queue.Queue();a.session_colours=CUSTOM_COLOURS
        jobs=queue.Queue()
        for pitch in (19,18,18,17):
            jobs.put(('t',np.zeros((1,pitch,320,3),dtype=np.uint8)))
        jobs.put(None)
        shapes=[]
        def recognize(rows,colours):
            shapes.append(rows.shape)
            return [('line','You have obtained 1 Adena.') for row in rows]
        with patch('tracker.configured_ocr_rows',side_effect=recognize):
            a.worker(jobs)
        self.assertEqual(shapes,[(1,19,320,3),(2,18,320,3),(1,17,320,3)])
        results=list(a.inbox.queue)
        self.assertEqual([k for k,v in results],['line','line','line','line','done'])
