"""Separate native, click-through, non-activating Windows HUD. No game hooks."""
import ctypes as c
from ctypes import wintypes as w
import os, time
from diagnostics import diagnostic

WIDTH, HEIGHT = 310, 86
PAUSE_RECT = (210, 60, 304, 82)
LOCK_RECT = (288, 2, 309, 24)



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
    def __init__(self, preferred=None, on_move=None, on_pause=None):
        self.hwnd=None; self.shown=False; self.position=None; self.values=('—','—','—')
        self.preferred=preferred; self.on_move=on_move; self.drag=None; self.interactive=False
        self.locked=True; self.lock_first=None; self.press_handled=False
        self.last_mouse_down=None; self.placement=None; self.on_pause=on_pause; self.paused=False; self.pause_pressed=False
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
        sig(self.u,'GetDoubleClickTime',[],w.UINT)
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
        self.callback=self.proc_type(self.safe_wndproc)
        wc=WNDCLASS(0,self.callback,0,0,self.instance,None,None,None,None,self.name)
        if not self.u.RegisterClassW(c.byref(wc)): raise c.WinError(c.get_last_error())
        self.brush=self.g.CreateSolidBrush(self.rgb(20,25,33))
        self.divider=self.g.CreateSolidBrush(self.rgb(75,84,97))
        self.small=self.font(14,400); self.large=self.font(19,600)
        self.control=self.g.CreateSolidBrush(self.rgb(46,61,78))
        self.lock_brush=self.g.CreateSolidBrush(self.rgb(235,240,248))
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
    def hit_rect(self,point,rect):
        if not self.shown or not self.position or point is None or getattr(self,'placement',None) is not None:return False
        x,y=self.position;l,t,r,b=rect
        return x+l<=point[0]<x+r and y+t<=point[1]<y+b
    def lock_hit(self,point):
        return self.hit_rect(point,LOCK_RECT)
    def body_hit(self,point):
        return self.hit_rect(point,(0,0,WIDTH,HEIGHT)) and not self.lock_hit(point) and not self.pause_hit(point)
    def wants_input(self,point):
        return self.drag is not None or self.lock_hit(point) or self.pause_hit(point) or (not self.locked and self.body_hit(point))
    def toggle_lock_press(self):
        # Unlock requires two distinct presses within Windows' double-click interval.
        # Lock immediately on the first click while unlocked.
        now=time.monotonic()
        if not self.locked:
            self.finish_drag();self.locked=True;self.lock_first=None
        elif self.lock_first is not None and 0<=now-self.lock_first<=self.double_click_seconds():
            self.locked=False;self.lock_first=None
        else:
            self.lock_first=now;return
        self.u.InvalidateRect(self.hwnd,None,False)
    def double_click_seconds(self):
        try:return max(.1,min(2.,int(self.u.GetDoubleClickTime())/1000))
        except (ValueError,TypeError):return .5
    def handle_press(self,point):
        # Native messages and polling share one latch: one physical press
        # cannot be counted twice or accidentally unlock the HUD.
        if self.press_handled:return
        self.press_handled=True
        if self.lock_hit(point):
            self.toggle_lock_press();return
        self.lock_first=None
        if self.pause_hit(point):self.pause_click()
        elif not self.locked and self.body_hit(point):self.begin_drag(point)
    def release_press(self):
        self.finish_drag();self.press_handled=False;self.pause_pressed=False
    def pause_hit(self,point):
        if not getattr(self,'on_pause',None) or not self.shown or not self.position or point is None or getattr(self,'placement',None) is not None:return False
        x,y=self.position;l,t,r,b=PAUSE_RECT
        return x+l<=point[0]<x+r and y+t<=point[1]<y+b
    def pause_click(self):
        if not getattr(self,'on_pause',None) or getattr(self,'pause_pressed',False):return
        self.pause_pressed=True
        self.on_pause()
    def safe_wndproc(self,h,msg,wp,lp):
        try:return self.wndproc(h,msg,wp,lp)
        except Exception:
            diagnostic('Native HUD callback exception, message=%s',msg,exc_info=True)
            return self.u.DefWindowProcW(h,msg,wp,lp)
    def wndproc(self,h,msg,wp,lp):
        if msg==0x84:return 1 if self.interactive and self.wants_input(self.cursor()) else -1 # HTCLIENT / HTTRANSPARENT
        if msg in (0x201,0x203): # WM_LBUTTONDOWN / DBLCLK
            if self.interactive:self.handle_press(self.cursor())
            return 0
        if msg==0x202: # polling also detects release outside HUD
            self.release_press();return 0
        if msg==0x21:return 3 # MA_NOACTIVATE
        if msg==0x14:return 1
        if msg==0xF:
            ps=self.PAINTSTRUCT();dc=self.u.BeginPaint(h,c.byref(ps))
            if dc:
                try:
                    self.u.FillRect(dc,c.byref(w.RECT(0,0,WIDTH,HEIGHT)),self.brush)
                    for x in (103,206):self.u.FillRect(dc,c.byref(w.RECT(x,12,x+1,50)),self.divider)
                    self.g.SetBkMode(dc,1)
                    for i,(label,value,colour) in enumerate(zip(('ADENA / HR','EXP / HR','KILLS / HR'),self.values,((247,202,102),(134,224,183),(214,224,245)))):
                        x=i*103+8
                        self.text(dc,label,(x,7,288 if i==2 else x+91,24),self.small,(180,190,205))
                        self.text(dc,value,(x,26,x+91,53),self.large,colour)
                    # Small vector padlock: no emoji/font dependency.
                    parts=[(295,11,304,12),(295,18,304,19),(295,12,296,18),(303,12,304,18),(299,14,300,17)]
                    parts += ([(297,7,302,8),(297,8,298,11),(301,8,302,11)] if self.locked else [(297,6,302,7),(297,7,298,11),(301,7,302,9)])
                    for part in parts:self.u.FillRect(dc,c.byref(w.RECT(*part)),self.lock_brush)
                    self.u.FillRect(dc,c.byref(w.RECT(8,56,302,57)),self.divider)
                    self.u.FillRect(dc,c.byref(w.RECT(*PAUSE_RECT)),self.control)
                    paused=getattr(self,'paused',False)
                    self.text(dc,'PAUSED' if paused else 'SESSION ACTIVE',(9,60,200,82),self.small,(247,202,102) if paused else (134,224,183))
                    self.text(dc,'  Resume' if paused else '  Pause',(210,60,304,82),self.small,(235,240,248))
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
        if self.locked or self.drag is not None or not self.body_hit(point):return
        x,y=self.position
        if x<=point[0]<x+WIDTH and y<=point[1]<y+HEIGHT:
            self.drag=(point[0]-x,point[1]-y)
    def finish_drag(self):
        if self.drag is None:return
        self.drag=None
        if self.preferred is not None and self.on_move:self.on_move(self.preferred)
    def arm_placement(self):
        self.finish_drag(); self.lock_first=None; self.set_interactive(False)
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
    def update(self,api,target,chat,running,seconds,adena,xp,kills=0,paused=False):
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
        if not mouse_down:self.release_press()
        if getattr(self,'placement',None) is not None:
            self.set_interactive(False)
            # No overlay clicks or mouse routing: move with pointer and tap Shift.
            candidate=self.placement_position(geo,chat,desktop,shift,self.cursor())
            pos=candidate or hud_position(geo,chat,desktop,self.preferred)
        else:
            point=self.cursor()
            self.set_interactive(self.wants_input(point))
            # Polling fallback catches missed native mouse messages without
            # starting a drag when the button was already held on entry.
            if mouse_down and previous is False:self.handle_press(point)
            pos=hud_position(geo,chat,desktop,self.preferred)
            if self.drag is not None:
                if not self.locked and mouse_down and point is not None:
                    candidate=safe_position(geo,chat,desktop,(point[0]-self.drag[0]-geo[0],point[1]-self.drag[1]-geo[1]))
                    if candidate is not None:
                        pos=candidate; self.preferred=(pos[0]-geo[0],pos[1]-geo[1])
                else:self.finish_drag()
        if pos is None:self.hide();return
        values=(rate_text(adena,seconds),rate_text(xp,seconds),rate_text(kills,seconds))
        if values!=self.values or paused!=getattr(self,'paused',False):
            self.values=values;self.paused=paused;self.u.InvalidateRect(self.hwnd,None,False)
        if not self.shown or pos!=self.position:
            if self.u.SetWindowPos(self.hwnd,c.c_void_p(-1),*pos,WIDTH,HEIGHT,0x0010|0x0040|0x0200):
                self.shown=True;self.position=pos
        # Recheck after showing; never intentionally keep HUD over another app.
        if api.foreground()!=target.hwnd:
            if getattr(self,"placement",None) and self.placement["seen"]:self.cancel_placement()
            self.hide()
    def hide(self):
        self.release_press();self.set_interactive(False);self.last_mouse_down=None;self.lock_first=None
        if self.hwnd and self.shown:self.u.ShowWindow(self.hwnd,0);self.shown=False;self.position=None
    def close(self):
        self.cancel_placement(); self.finish_drag()
        if self.hwnd:self.u.DestroyWindow(self.hwnd);self.hwnd=None
        for obj in (self.brush,self.divider,self.small,self.large,self.control,self.lock_brush):
            if obj:self.g.DeleteObject(obj)
        self.u.UnregisterClassW(self.name,self.instance)
