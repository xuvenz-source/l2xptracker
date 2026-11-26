"""Separate native, click-through, non-activating Windows HUD. No game hooks."""
import ctypes as c
from ctypes import wintypes as w
import os

WIDTH, HEIGHT = 310, 62


def safe_position(geo, chat, desktop, preferred):
    x,y,width,height=geo
    low_x,low_y=0,0
    high_x,high_y=width-WIDTH,height-HEIGHT
    if desktop:
        low_x=max(low_x,desktop['left']-x); low_y=max(low_y,desktop['top']-y)
        high_x=min(high_x,desktop['left']+desktop['width']-x-WIDTH)
        high_y=min(high_y,desktop['top']+desktop['height']-y-HEIGHT)
    if low_x>high_x or low_y>high_y:return None
    a=min(high_x,max(low_x,preferred[0])); d=min(high_y,max(low_y,preferred[1]))
    l,t,r,b=(chat[k] for k in ('left','top','width','height'))
    if a<l+r and a+WIDTH>l and d<t+b and d+HEIGHT>t:return None
    return x+a,y+d


def hud_position(geo, chat, desktop=None, preferred=None):
    if preferred is not None:
        pos=safe_position(geo,chat,desktop,preferred)
        if pos is not None:return pos
    x,y,width,height=geo
    if width<WIDTH+24 or height<HEIGHT+24: return None
    l,t,r,b=chat['left'],chat['top'],chat['width'],chat['height']
    for a,d in ((width-WIDTH-12,12),(12,12),(width-WIDTH-12,height-HEIGHT-12),(12,height-HEIGHT-12)):
        if a<l+r and a+WIDTH>l and d<t+b and d+HEIGHT>t: continue
        if desktop and not (desktop['left']<=x+a and desktop['top']<=y+d and x+a+WIDTH<=desktop['left']+desktop['width'] and y+d+HEIGHT<=desktop['top']+desktop['height']): continue
        return x+a,y+d
    return None


def rate_text(total, seconds):
    return f'{total*3600/max(1,seconds):,.0f}' if seconds>=1 else '—'


class Hud:
    def __init__(self, preferred=None, on_move=None):
        self.hwnd=None; self.shown=False; self.position=None; self.values=('—','—')
        self.preferred=preferred; self.on_move=on_move; self.drag=None; self.interactive=False
        self.last_mouse_down=None; self.placement=None
        self.u=c.WinDLL('user32',use_last_error=True); self.g=c.WinDLL('gdi32',use_last_error=True); self.k=c.WinDLL('kernel32',use_last_error=True)
        H=w.HANDLE; L=c.c_ssize_t; U=c.c_size_t
        self.proc_type=c.WINFUNCTYPE(L,w.HWND,w.UINT,U,L)
        class WNDCLASS(c.Structure):
            _fields_=[('style',w.UINT),('lpfnWndProc',self.proc_type),('cbClsExtra',c.c_int),('cbWndExtra',c.c_int),('hInstance',H),('hIcon',H),('hCursor',H),('hbrBackground',H),('lpszMenuName',w.LPCWSTR),('lpszClassName',w.LPCWSTR)]
        class PAINTSTRUCT(c.Structure):
            _fields_=[('hdc',H),('fErase',w.BOOL),('rcPaint',w.RECT),('fRestore',w.BOOL),('fIncUpdate',w.BOOL),('rgbReserved',c.c_byte*32)]
        self.PAINTSTRUCT=PAINTSTRUCT
        def sig(lib,name,args,ret):
            fn=getattr(lib,name);fn.argtypes=args;fn.restype=ret;return fn
        sig(self.k,'GetModuleHandleW',[w.LPCWSTR],H)
        sig(self.u,'RegisterClassW',[c.POINTER(WNDCLASS)],w.ATOM)
        sig(self.u,'UnregisterClassW',[w.LPCWSTR,H],w.BOOL)
        sig(self.u,'CreateWindowExW',[w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,c.c_int,c.c_int,c.c_int,c.c_int,H,H,H,c.c_void_p],H)
        sig(self.u,'DefWindowProcW',[H,w.UINT,U,L],L)
        sig(self.u,'DestroyWindow',[H],w.BOOL)
        sig(self.u,'SetLayeredWindowAttributes',[H,w.DWORD,c.c_ubyte,w.DWORD],w.BOOL)
        sig(self.u,'SetWindowPos',[H,H,c.c_int,c.c_int,c.c_int,c.c_int,w.UINT],w.BOOL)
        sig(self.u,'ShowWindow',[H,c.c_int],w.BOOL)
        sig(self.u,'InvalidateRect',[H,c.POINTER(w.RECT),w.BOOL],w.BOOL)
        sig(self.u,'BeginPaint',[H,c.POINTER(PAINTSTRUCT)],H)
        sig(self.u,'EndPaint',[H,c.POINTER(PAINTSTRUCT)],w.BOOL)
        sig(self.u,'FillRect',[H,c.POINTER(w.RECT),H],c.c_int)
        sig(self.u,'DrawTextW',[H,w.LPCWSTR,c.c_int,c.POINTER(w.RECT),w.UINT],c.c_int)
        sig(self.u,'GetSystemMetrics',[c.c_int],c.c_int)
        sig(self.u,'GetAsyncKeyState',[c.c_int],c.c_short)
        sig(self.u,'GetCursorPos',[c.POINTER(w.POINT)],w.BOOL)
        sig(self.u,'GetWindowLongW',[H,c.c_int],c.c_long)
        sig(self.u,'SetWindowLongW',[H,c.c_int,c.c_long],c.c_long)
        sig(self.g,'CreateSolidBrush',[w.DWORD],H)
        sig(self.g,'DeleteObject',[H],w.BOOL)
        sig(self.g,'SelectObject',[H,H],H)
        sig(self.g,'SetBkMode',[H,c.c_int],c.c_int)
        sig(self.g,'SetTextColor',[H,w.DWORD],w.DWORD)
        sig(self.g,'CreateFontW',[c.c_int]*5+[w.DWORD]*8+[w.LPCWSTR],H)
        self.instance=self.k.GetModuleHandleW(None)
        self.name=f'L2LegacyTrackerHud_{os.getpid()}'
        self.callback=self.proc_type(self.wndproc)
        wc=WNDCLASS(0,self.callback,0,0,self.instance,None,None,None,None,self.name)
        if not self.u.RegisterClassW(c.byref(wc)): raise c.WinError(c.get_last_error())
        self.brush=self.g.CreateSolidBrush(self.rgb(20,25,33))
        self.divider=self.g.CreateSolidBrush(self.rgb(75,84,97))
        self.small=self.font(14,400); self.large=self.font(21,600)
        # layered + transparent + noactivate + toolwindow + topmost
        ex=0x80000|0x20|0x08000000|0x80|8
        self.hwnd=self.u.CreateWindowExW(ex,self.name,'L2 Farming HUD',0x80000000,0,0,WIDTH,HEIGHT,None,None,self.instance,None)
        if not self.hwnd: self.close(); raise c.WinError(c.get_last_error())
        if not self.u.SetLayeredWindowAttributes(self.hwnd,0,235,2): self.close(); raise RuntimeError('Could not set HUD opacity')
    @staticmethod
    def rgb(r,g,b):return r|(g<<8)|(b<<16)
    def font(self,size,weight):
        return self.g.CreateFontW(-size,0,0,0,weight,0,0,0,1,0,0,5,0,'Segoe UI')
    def text(self,dc,string,rect,font,colour):
        prev=self.g.SelectObject(dc,font)
        self.g.SetTextColor(dc,self.rgb(*colour)); r=w.RECT(*rect)
        self.u.DrawTextW(dc,string,-1,c.byref(r),0x00000020|0x00000004|0x00000800) # single line, vertical centre, no prefix
        self.g.SelectObject(dc,prev)
    def wndproc(self,h,msg,wp,lp):
        if msg==0x84:return 1 if self.interactive and self.key_down(0x10) else -1 # HTCLIENT / HTTRANSPARENT
        if msg==0x201: # WM_LBUTTONDOWN on our HUD only
            if self.interactive and self.key_down(0x10):
                self.begin_drag(self.cursor())
            return 0
        if msg==0x202: # WM_LBUTTONUP; polling also detects release outside HUD
            self.finish_drag();return 0
        if msg==0x21:return 3 # MA_NOACTIVATE
        if msg==0x14:return 1
        if msg==0xF:
            ps=self.PAINTSTRUCT();dc=self.u.BeginPaint(h,c.byref(ps))
            if dc:
                try:
                    self.u.FillRect(dc,c.byref(w.RECT(0,0,WIDTH,HEIGHT)),self.brush)
                    self.u.FillRect(dc,c.byref(w.RECT(154,12,155,50)),self.divider)
                    self.g.SetBkMode(dc,1)
                    for i,(label,value,colour) in enumerate(zip(('ADENA / HR','EXP / HR'),self.values,((247,202,102),(134,224,183)))):
                        x=i*155+12
                        self.text(dc,label,(x,7,x+137,24),self.small,(180,190,205))
                        self.text(dc,value,(x,26,x+137,53),self.large,colour)
                finally:self.u.EndPaint(h,c.byref(ps))
            return 0
        return self.u.DefWindowProcW(h,msg,wp,lp)
    def key_down(self,key):
        return bool(self.u.GetAsyncKeyState(key)&0x8000)
    def cursor(self):
        p=w.POINT()
        if self.u.GetCursorPos(c.byref(p)):return p.x,p.y
        return None
    def set_interactive(self,enabled):
        if self.interactive==enabled or not self.hwnd:return
        style=self.u.GetWindowLongW(self.hwnd,-20)
        new=style&~0x20 if enabled else style|0x20
        c.set_last_error(0)
        if not self.u.SetWindowLongW(self.hwnd,-20,new) and c.get_last_error():raise c.WinError(c.get_last_error())
        self.u.SetWindowPos(self.hwnd,None,0,0,0,0,0x1|0x2|0x4|0x10|0x20)
        self.interactive=enabled
    def begin_drag(self,point):
        # Also used by polling when the layered popup does not receive mouse messages.
        if self.drag is not None or not self.shown or not self.position or point is None:return
        x,y=self.position
        if x<=point[0]<x+WIDTH and y<=point[1]<y+HEIGHT:
            self.drag=(point[0]-x,point[1]-y)
    def finish_drag(self):
        if self.drag is None:return
        self.drag=None
        if self.preferred is not None and self.on_move:self.on_move(self.preferred)
    def arm_placement(self):
        self.finish_drag(); self.set_interactive(False)
        self.placement={'seen':False,'shift_ready':False}
    def cancel_placement(self):
        self.placement=None
    def placement_position(self,geo,chat,desktop,shift,point):
        state=self.placement; state['seen']=True
        if not shift:state['shift_ready']=True
        candidate=None if point is None else safe_position(geo,chat,desktop,(point[0]-geo[0]-WIDTH//2,point[1]-geo[1]-HEIGHT//2))
        if candidate is not None and shift and state['shift_ready']:
            self.preferred=(candidate[0]-geo[0],candidate[1]-geo[1]); self.cancel_placement()
            if self.on_move:self.on_move(self.preferred)
        return candidate
    def update(self,api,target,chat,running,seconds,adena,xp):
        if not self.hwnd:return
        if not running or not target or not api.usable(target.hwnd) or api.pid(target.hwnd)!=target.pid or api.foreground()!=target.hwnd:
            if not running or (getattr(self,'placement',None) and self.placement['seen']):self.cancel_placement()
            self.hide();return
        geo=api.geometry(target.hwnd)
        if not geo or geo[2:]!=(target.width,target.height):self.cancel_placement();self.hide();return
        desktop=dict(zip(('left','top','width','height'),(self.u.GetSystemMetrics(i) for i in (76,77,78,79))))
        shift=self.key_down(0x10)
        mouse_down=self.key_down(0x01)
        previous=getattr(self,'last_mouse_down',None)
        self.last_mouse_down=mouse_down
        if getattr(self,'placement',None) is not None:
            self.set_interactive(False)
            # No overlay clicks or mouse routing: move with pointer and tap Shift.
            candidate=self.placement_position(geo,chat,desktop,shift,self.cursor())
            pos=candidate or hud_position(geo,chat,desktop,self.preferred)
        else:
            point=self.cursor() if shift or self.drag is not None else None
            # Keep the existing native hit-test path, but do not depend on the
            # window manager delivering WM_LBUTTONDOWN to a layered overlay.
            self.set_interactive(shift)
            if shift and mouse_down and previous is False:
                self.begin_drag(point)
            pos=hud_position(geo,chat,desktop,self.preferred)
            if self.drag is not None:
                if shift and mouse_down and point is not None:
                    candidate=safe_position(geo,chat,desktop,(point[0]-self.drag[0]-geo[0],point[1]-self.drag[1]-geo[1]))
                    if candidate is not None:
                        pos=candidate; self.preferred=(pos[0]-geo[0],pos[1]-geo[1])
                else:self.finish_drag()
        if pos is None:self.hide();return
        values=(rate_text(adena,seconds),rate_text(xp,seconds))
        if values!=self.values:self.values=values;self.u.InvalidateRect(self.hwnd,None,False)
        if not self.shown or pos!=self.position:
            if self.u.SetWindowPos(self.hwnd,c.c_void_p(-1),*pos,WIDTH,HEIGHT,0x0010|0x0040|0x0200):
                self.shown=True;self.position=pos
        # Recheck after showing; never intentionally keep HUD over another app.
        if api.foreground()!=target.hwnd:
            if getattr(self,"placement",None) and self.placement["seen"]:self.cancel_placement()
            self.hide()
    def hide(self):
        self.finish_drag();self.set_interactive(False);self.last_mouse_down=None
        if self.hwnd and self.shown:self.u.ShowWindow(self.hwnd,0);self.shown=False;self.position=None
    def close(self):
        self.cancel_placement(); self.finish_drag()
        if self.hwnd:self.u.DestroyWindow(self.hwnd);self.hwnd=None
        for obj in (self.brush,self.divider,self.small,self.large):
            if obj:self.g.DeleteObject(obj)
        self.u.UnregisterClassW(self.name,self.instance)
