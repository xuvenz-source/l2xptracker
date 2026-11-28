import ctypes as c
import unittest
from unittest.mock import Mock,patch
import numpy as np
from PIL import Image
from ornate_globe import render_globe,text_lines,premultiplied_bgra
from layered_globe import present,Blend
from globe_hud import GlobeHud
from hud_layout import geometry

class OrnateGlobeTests(unittest.TestCase):
    def test_modes(self):
        self.assertEqual(text_lines('449/505 - 89%'),('89%','449 / 505'))
        self.assertEqual(text_lines('— - ~31%'),('~31%','—'))
        self.assertEqual(text_lines('58/187'),('58 / 187',))
        self.assertEqual(text_lines('31%'),('31%',))
    def test_transparent_scaled_render_and_fill(self):
        for d in (80,120,240):
            im=render_globe('hp',d,.89,'449/505 - 89%')
            a=np.asarray(im)
            self.assertEqual(im.size,(d,d))
            self.assertEqual(im.mode,'RGBA')
            self.assertEqual(a[0,0,3],0)
            self.assertEqual(a[d//2,d//2,3],255)
            self.assertTrue(np.any((a[:,:,3]>0)&(a[:,:,3]<255)))
        full=np.asarray(render_globe('mp',120,1,'100%'))
        empty=np.asarray(render_globe('mp',120,0,'0%'))
        partial=np.asarray(render_globe('mp',120,.31,'31%'))
        self.assertGreater(int(full[34,60,2]),int(empty[34,60,2])+25)
        self.assertGreater(int(partial[89,60,2]),int(empty[89,60,2])+25)
        self.assertLess(abs(int(partial[34,60,2])-int(empty[34,60,2])),5)
        self.assertFalse(np.array_equal(empty,np.asarray(render_globe('mp',120,None,'—'))))
    def test_premultiplication(self):
        im=Image.new('RGBA',(2,1));im.putdata([(200,100,50,128),(255,100,20,0)])
        self.assertEqual(premultiplied_bgra(im),bytes((25,50,100,128,0,0,0,0)))
    def test_native_surface_cleanup(self):
        u,g=Mock(),Mock();g.CreateCompatibleDC.return_value=10;g.CreateDIBSection.return_value=20;g.SelectObject.return_value=30
        memory=c.create_string_buffer(16)
        def dib(dc,header,usage,data,section,offset):
            c.cast(data,c.POINTER(c.c_void_p))[0]=c.addressof(memory);return 20
        g.CreateDIBSection.side_effect=dib
        im=Image.new('RGBA',(2,2),(200,100,50,128))
        u.UpdateLayeredWindow.return_value=True
        present(u,g,3,im,80)
        args=u.UpdateLayeredWindow.call_args.args
        self.assertEqual(args[-1],2)
        self.assertEqual(c.cast(args[-2],c.POINTER(Blend)).contents.alpha,204)
        self.assertEqual(memory.raw,bytes((25,50,100,128))*4)
        g.SelectObject.assert_called_with(10,30);g.DeleteObject.assert_called_with(20);g.DeleteDC.assert_called_with(10)
        u.UpdateLayeredWindow.return_value=False
        with self.assertRaises(RuntimeError):present(u,g,3,im,80)
        self.assertEqual(g.DeleteDC.call_count,2)
    def test_surface_refresh_only_on_change(self):
        h=GlobeHud.__new__(GlobeHud);h.layout=geometry({},'HP GLOBE')
        h.widget_values={'hp':('HP','89%'),'hp_fill':.89};h.opacity=92;h.surface_key=None
        h.u=Mock();h.g=Mock();h.hwnd=3
        with patch('globe_hud.present') as show:
            h.present_surface();h.present_surface()
            self.assertEqual(show.call_count,1)
            h.opacity=100;h.present_surface()
            self.assertEqual(show.call_count,2)
