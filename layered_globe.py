"""Present a premultiplied 32-bit surface through Win32 UpdateLayeredWindow."""
import ctypes as c
from ctypes import wintypes as w
from ornate_globe import premultiplied_bgra

class BitmapInfoHeader(c.Structure):
    _fields_=[('size',w.DWORD),('width',w.LONG),('height',w.LONG),('planes',w.WORD),('bits',w.WORD),('compression',w.DWORD),('image_size',w.DWORD),('xppm',w.LONG),('yppm',w.LONG),('used',w.DWORD),('important',w.DWORD)]

class Blend(c.Structure):
    _fields_=[('op',c.c_ubyte),('flags',c.c_ubyte),('alpha',c.c_ubyte),('format',c.c_ubyte)]

def setup(user,gdi):
    H=w.HANDLE
    user.UpdateLayeredWindow.argtypes=[H,H,c.POINTER(w.POINT),c.POINTER(w.SIZE),H,c.POINTER(w.POINT),w.DWORD,c.POINTER(Blend),w.DWORD]
    user.UpdateLayeredWindow.restype=w.BOOL
    gdi.CreateDIBSection.argtypes=[H,c.POINTER(BitmapInfoHeader),w.UINT,c.POINTER(c.c_void_p),H,w.DWORD]
    gdi.CreateDIBSection.restype=H

def present(user,gdi,hwnd,image,opacity):
    width,height=image.size
    pixels=premultiplied_bgra(image)
    dc=gdi.CreateCompatibleDC(None)
    if not dc:raise RuntimeError('Could not create globe surface DC')
    bitmap=None;old=None
    try:
        header=BitmapInfoHeader(c.sizeof(BitmapInfoHeader),width,-height,1,32,0,len(pixels),0,0,0,0)
        data=c.c_void_p()
        bitmap=gdi.CreateDIBSection(dc,c.byref(header),0,c.byref(data),None,0)
        if not bitmap or not data.value:raise RuntimeError('Could not create globe alpha bitmap')
        c.memmove(data,pixels,len(pixels))
        old=gdi.SelectObject(dc,bitmap)
        if not old or old==c.c_void_p(-1).value:raise RuntimeError('Could not select globe bitmap')
        size=w.SIZE(width,height);origin=w.POINT(0,0)
        blend=Blend(0,0,round(255*opacity/100),1)
        if not user.UpdateLayeredWindow(hwnd,None,None,c.byref(size),dc,c.byref(origin),0,c.byref(blend),2):
            raise RuntimeError('Could not present globe alpha surface')
    finally:
        if old and old!=c.c_void_p(-1).value:gdi.SelectObject(dc,old)
        if bitmap:gdi.DeleteObject(bitmap)
        gdi.DeleteDC(dc)
