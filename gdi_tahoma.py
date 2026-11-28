"""Offline native Windows Tahoma rasterisation. No live tracker imports."""
import ctypes as c
from ctypes import wintypes as w
import numpy as np

WIDTH,HEIGHT=512,96
QUALITIES={'Default':0,'Monochrome':3,'Grayscale':4,'ClearType requested':5}

class BitmapInfoHeader(c.Structure):
    _fields_=[('size',w.DWORD),('width',w.LONG),('height',w.LONG),('planes',w.WORD),('bits',w.WORD),('compression',w.DWORD),('image_size',w.DWORD),('xppm',w.LONG),('yppm',w.LONG),('used',w.DWORD),('important',w.DWORD)]

def bind(g,name,args,result):
    fn=getattr(g,name);fn.argtypes=args;fn.restype=result;return fn

class GdiTahoma:
    """A reusable memory DC; negative height requests character height."""
    def __init__(self,pixels,weight,quality,height_mode='Character'):
        self.g=c.WinDLL('gdi32',use_last_error=True)
        H=w.HANDLE;I=c.c_int;D=w.DWORD;B=w.BOOL
        for name,args,result in (
            ('CreateCompatibleDC',[H],H),('DeleteDC',[H],B),
            ('CreateDIBSection',[H,c.POINTER(BitmapInfoHeader),w.UINT,c.POINTER(c.c_void_p),H,D],H),
            ('SelectObject',[H,H],H),('DeleteObject',[H],B),
            ('CreateFontW',[I,I,I,I,I,D,D,D,D,D,D,D,D,w.LPCWSTR],H),
            ('SetTextColor',[H,D],D),('SetBkMode',[H,I],I),
            ('GetTextFaceW',[H,I,w.LPWSTR],I),
            ('GetTextExtentPoint32W',[H,w.LPCWSTR,I,c.POINTER(w.SIZE)],B),
            ('TextOutW',[H,I,I,w.LPCWSTR,I],B),('GdiFlush',[],B)):
            bind(self.g,name,args,result)
        self.dc=self.bitmap=self.font=self.old_bitmap=self.old_font=None
        self.data=c.c_void_p()
        try:
            self.dc=self.g.CreateCompatibleDC(None)
            if not self.dc:raise OSError('CreateCompatibleDC failed')
            info=BitmapInfoHeader(c.sizeof(BitmapInfoHeader),WIDTH,-HEIGHT,1,32,0,WIDTH*HEIGHT*4,0,0,0,0)
            self.bitmap=self.g.CreateDIBSection(self.dc,c.byref(info),0,c.byref(self.data),None,0)
            if not self.bitmap or not self.data.value:raise OSError('CreateDIBSection failed')
            self.old_bitmap=self.g.SelectObject(self.dc,self.bitmap)
            if not self.old_bitmap or self.old_bitmap==c.c_void_p(-1).value:raise OSError('SelectObject bitmap failed')
            height=-pixels if height_mode=='Character' else pixels
            self.font=self.g.CreateFontW(height,0,0,0,weight,0,0,0,1,0,0,quality,0,'Tahoma')
            if not self.font:raise OSError('CreateFontW failed')
            self.old_font=self.g.SelectObject(self.dc,self.font)
            if not self.old_font or self.old_font==c.c_void_p(-1).value:raise OSError('SelectObject font failed')
            face=c.create_unicode_buffer(64)
            if not self.g.GetTextFaceW(self.dc,len(face),face) or face.value.casefold()!='tahoma':
                raise OSError('Requested Tahoma was not selected: '+face.value)
            self.g.SetTextColor(self.dc,0xffffff);self.g.SetBkMode(self.dc,1)
        except Exception:self.close();raise
    def render(self,text):
        size=w.SIZE()
        if not self.g.GetTextExtentPoint32W(self.dc,text,len(text),c.byref(size)):
            raise OSError('GetTextExtentPoint32W failed')
        if size.cx+12>WIDTH or size.cy+12>HEIGHT:raise ValueError('Text exceeds calibration surface')
        self.g.GdiFlush()
        c.memset(self.data,0,WIDTH*HEIGHT*4)
        if not self.g.TextOutW(self.dc,6,6,text,len(text)):raise OSError('TextOutW failed')
        self.g.GdiFlush()
        bgra=np.ctypeslib.as_array((c.c_ubyte*(WIDTH*HEIGHT*4)).from_address(self.data.value)).reshape(HEIGHT,WIDTH,4)
        # Keep enough padding for overhangs, then convert BGR to luminance.
        a=bgra[:size.cy+12,:size.cx+12,:3].astype(np.uint32)
        return ((114*a[:,:,0]+587*a[:,:,1]+299*a[:,:,2]+500)//1000).astype(np.uint8)
    def close(self):
        if self.dc:
            for old in (self.old_font,self.old_bitmap):
                if old and old!=c.c_void_p(-1).value:self.g.SelectObject(self.dc,old)
            for obj in (self.font,self.bitmap):
                if obj:self.g.DeleteObject(obj)
            self.g.DeleteDC(self.dc);self.dc=None
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
