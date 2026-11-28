"""Separate native, click-through, non-activating Windows HUD. No game hooks."""
import ctypes as c
from ctypes import wintypes as w
import os, time
from decimal import Decimal
from diagnostics import diagnostic
from preferences import HUD_OPACITY_DEFAULT, validate_hud_opacity
from hud_layout import geometry as layout_geometry, WIDGETS, overlaps

WIDTH, HEIGHT = 310, 86
PAUSE_RECT = (174, 60, 244, 82)
RESET_RECT = (248, 60, 304, 82)
LOCK_RECT = (288, 2, 309, 24)
SETTINGS_RECT = (266, 2, 288, 24)



def safe_position(geo, chat, desktop, preferred, size=(WIDTH,HEIGHT), extra=()):
    WIDTH,HEIGHT=size
    x,y,width,height=geo
    low_x,low_y=0,0
    high_x,high_y=width-WIDTH,height-HEIGHT
    if desktop:
        low_x=max(low_x,desktop['left']-x); low_y=max(low_y,desktop['top']-y)
        high_x=min(high_x,desktop['left']+desktop['width']-x-WIDTH)
        high_y=min(high_y,desktop['top']+desktop['height']-y-HEIGHT)
    if low_x>high_x or low_y>high_y:return None
    a=min(high_x,max(low_x,preferred[0])); d=min(high_y,max(low_y,preferred[1]))
    if any(overlaps(a,d,WIDTH,HEIGHT,r) for r in (chat,*extra) if r):return None
    return x+a,y+d


def hud_position(geo, chat, desktop=None, preferred=None, size=(WIDTH,HEIGHT), extra=()):
    WIDTH,HEIGHT=size
    if preferred is not None:
        pos=safe_position(geo,chat,desktop,preferred,size,extra)
        if pos is not None:return pos
    x,y,width,height=geo
    if width<WIDTH+24 or height<HEIGHT+24: return None
    l,t,r,b=chat['left'],chat['top'],chat['width'],chat['height']
    for a,d in ((width-WIDTH-12,12),(12,12),(width-WIDTH-12,height-HEIGHT-12),(12,height-HEIGHT-12)):
        if any(overlaps(a,d,WIDTH,HEIGHT,r) for r in (chat,*extra) if r):continue
        if desktop and not (desktop['left']<=x+a and desktop['top']<=y+d and x+a+WIDTH<=desktop['left']+desktop['width'] and y+d+HEIGHT<=desktop['top']+desktop['height']): continue
        return x+a,y+d
    return None


def rate_text(total, seconds):
    return f'{Decimal(str(total))*3600/Decimal(str(seconds)):,.0f}' if seconds>=1 else '—'


def adena_metric(adena,seconds,consumable_cost=None,unpriced_uses=0):
    if consumable_cost is None:return 'ADENA / HR',rate_text(adena,seconds)
    label='NET ADENA/H*' if unpriced_uses else 'NET ADENA/H'
    return label,rate_text(Decimal(str(adena))-Decimal(str(consumable_cost)),seconds)


class Hud:
    def __init__(self, preferred=None, on_move=None, on_pause=None, opacity=HUD_OPACITY_DEFAULT, on_reset=None, on_settings=None, name_suffix='', on_select_loot=None):
        self.opacity=validate_hud_opacity(opacity)
        self.hwnd=None; self.shown=False; self.position=None; self.values=('—','—','—'); self.adena_label='ADENA / HR'
        self.preferred=preferred; self.on_move=on_move; self.drag=None; self.interactive=False
        self.locked=True; self.lock_first=None; self.press_handled=False; self.native_released=False
        self.native_drag=False; self.drag_poll_seen=False; self.drag_context=None; self.drag_rejected=False; self.native_activity=0.0; self.moving=False
        self.last_mouse_down=None; self.placement=None; self.on_pause=on_pause; self.on_reset=on_reset; self.on_settings=on_settings; self.on_select_loot=on_select_loot; self.paused=False; self.pause_pressed=False
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
        sig(self.u,'SetCapture',[H],H)
        sig(self.u,'GetCapture',[],H)
        sig(self.u,'ReleaseCapture',[],w.BOOL)
        sig(self.u,'GetWindowLongW',[H,c.c_int],c.c_long)
        sig(self.u,'SetWindowLongW',[H,c.c_int,c.c_long],c.c_long)
        sig(self.g,'CreateCompatibleDC',[H],H)
        sig(self.g,'CreateCompatibleBitmap',[H,c.c_int,c.c_int],H)
        sig(self.g,'DeleteDC',[H],w.BOOL)
        sig(self.g,'BitBlt',[H,c.c_int,c.c_int,c.c_int,c.c_int,H,c.c_int,c.c_int,w.DWORD],w.BOOL)
        sig(self.g,'CreateSolidBrush',[w.DWORD],H)
        sig(self.g,'DeleteObject',[H],w.BOOL)
        sig(self.g,'SelectObject',[H,H],H)
        sig(self.g,'SetBkMode',[H,c.c_int],c.c_int)
        sig(self.g,'SetTextColor',[H,w.DWORD],w.DWORD)
        sig(self.g,'CreateFontW',[c.c_int]*5+[w.DWORD]*8+[w.LPCWSTR],H)
        self.instance=self.k.GetModuleHandleW(None)
        self.name=f'L2LegacyTrackerHud_{os.getpid()}{name_suffix}'
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
        try:self.set_opacity(self.opacity)
        except Exception:self.close();raise
    def dimensions(self):
        g=getattr(self,'layout',None)
        return (g['width'],g['height']) if g else (WIDTH,HEIGHT)
    def protected(self):return getattr(self,'protected_regions',())
    def rect(self,name,default):
        g=getattr(self,'layout',None)
        return g[name] if g else default
    def configure_layout(self,config,title=None,details=0):
        g=layout_geometry(config,title,details,select_loot=bool(getattr(self,'on_select_loot',None)))
        if g==getattr(self,'layout',None):return
        self.finish_drag()
        # Do not briefly resize a visible overlay into a protected chat area.
        # The next HUD tick finds a safe position for the new geometry.
        if self.shown:self.hide()
        old=(self.small,self.large)
        self.small=self.font(g['small'],400);self.large=self.font(g['large'],600)
        for f in old:self.g.DeleteObject(f)
        self.layout=g;self.next_metric_paint=0
        if self.hwnd:
            self.u.SetWindowPos(self.hwnd,None,0,0,g['width'],g['height'],0x0002|0x0004|0x0010)
            self.u.InvalidateRect(self.hwnd,None,False)
    def set_opacity(self,percent):
        percent=validate_hud_opacity(percent)
        if self.hwnd and not self.u.SetLayeredWindowAttributes(self.hwnd,0,round(255*percent/100),2):
            raise RuntimeError('Could not set HUD opacity')
        self.opacity=percent
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
        if rect is None or not self.shown or not self.position or point is None or getattr(self,'placement',None) is not None:return False
        x,y=self.position;l,t,r,b=rect
        return x+l<=point[0]<x+r and y+t<=point[1]<y+b
    def lock_hit(self,point):
        return self.hit_rect(point,self.rect('lock',LOCK_RECT))
    def reset_hit(self,point):
        return bool(getattr(self,'on_reset',None)) and self.hit_rect(point,self.rect('reset',RESET_RECT))
    def settings_hit(self,point):
        return bool(getattr(self,'on_settings',None)) and self.hit_rect(point,self.rect('settings',SETTINGS_RECT))
    def select_loot_hit(self,point):
        return bool(getattr(self,'on_select_loot',None)) and self.hit_rect(point,(getattr(self,'layout',None) or {}).get('select_loot'))
    def body_hit(self,point):
        return self.hit_rect(point,(0,0,*self.dimensions())) and not self.lock_hit(point) and not self.pause_hit(point) and not self.reset_hit(point) and not self.settings_hit(point) and not self.select_loot_hit(point)
    def wants_input(self,point):
        return self.drag is not None or self.lock_hit(point) or self.pause_hit(point) or self.reset_hit(point) or self.settings_hit(point) or self.select_loot_hit(point) or (not self.locked and self.body_hit(point))
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
        if self.select_loot_hit(point):self.on_select_loot()
        elif self.settings_hit(point):self.on_settings()
        elif self.reset_hit(point):self.on_reset()
        elif self.pause_hit(point):self.pause_click()
        elif not self.locked and self.body_hit(point):self.begin_drag(point)
    def release_press(self):
        self.finish_drag();self.press_handled=False;self.pause_pressed=False;self.native_released=False

    def native_drag_start(self):
        if self.drag is None or getattr(self,'native_drag',False):return
        self.native_drag=True;self.native_activity=time.monotonic()
        # Capture is requested for our own popup only. Windows may limit
        # capture for a non-foreground window, so polling remains a fallback.
        self.u.SetCapture(self.hwnd)
        diagnostic('HUD native drag started; capture acquired=%s',self.u.GetCapture()==self.hwnd)

    def move_drag(self,point):
        if self.drag is None or self.locked or point is None or getattr(self,'moving',False):return
        ctx=getattr(self,'drag_context',None)
        if ctx is None:return
        geo,chat,desktop=ctx
        candidate=safe_position(geo,chat,desktop,(point[0]-self.drag[0]-geo[0],point[1]-self.drag[1]-geo[1]),self.dimensions(),self.protected())
        if candidate is None:
            if not getattr(self,'drag_rejected',False):diagnostic('HUD drag destination rejected: intersects selected chat or invalid bounds')
            self.drag_rejected=True;return
        self.drag_rejected=False
        if candidate==self.position:return
        self.moving=True
        try:
            if self.u.SetWindowPos(self.hwnd,c.c_void_p(-1),*candidate,*self.dimensions(),0x0010|0x0040|0x0200):
                self.position=candidate;self.shown=True
                self.preferred=(candidate[0]-geo[0],candidate[1]-geo[1])
            else:diagnostic('HUD SetWindowPos failed during drag')
        finally:self.moving=False
    def pause_hit(self,point):
        if not getattr(self,'on_pause',None) or not self.shown or not self.position or point is None or getattr(self,'placement',None) is not None:return False
        return self.hit_rect(point,self.rect('pause',PAUSE_RECT))
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
            if self.interactive:
                if getattr(self,'native_released',False):self.release_press()
                point=self.cursor()
                self.handle_press(point)
                # A native down delivered to the body is authoritative even
                # if a previous poll latched a press outside the HUD.
                if self.drag is None and not self.locked and self.body_hit(point) and not self.pause_pressed:
                    self.begin_drag(point)
                self.native_drag_start()
            return 0
        if msg==0x200: # WM_MOUSEMOVE
            if getattr(self,'native_drag',False):
                if wp & 1: # MK_LBUTTON: independent of GetAsyncKeyState
                    self.native_activity=time.monotonic()
                    self.move_drag(self.cursor())
                else:self.finish_drag()
            return 0
        if msg==0x202: # native up ends movement, but the poll may still see down
            if getattr(self,'native_drag',False):self.move_drag(self.cursor())
            self.finish_drag();self.native_released=True
            return 0
        if msg in (0x215,0x1F): # WM_CAPTURECHANGED / WM_CANCELMODE
            if getattr(self,'native_drag',False):
                # Another window took capture; continue if polling still sees
                # the physical button, otherwise cancel the drag.
                self.native_drag=False
                if not self.key_down(0x01):self.finish_drag()
            return 0
        if msg==0x21:return 3 # MA_NOACTIVATE
        if msg==0x14:return 1
        if msg==0xF:
            ps=self.PAINTSTRUCT();dc=self.u.BeginPaint(h,c.byref(ps))
            if dc:
                try:
                    if getattr(self,'layout',None):
                        self.paint_buffered(dc);return 0
                    self.u.FillRect(dc,c.byref(w.RECT(0,0,WIDTH,HEIGHT)),self.brush)
                    for x in (103,206):self.u.FillRect(dc,c.byref(w.RECT(x,12,x+1,50)),self.divider)
                    self.g.SetBkMode(dc,1)
                    for i,(label,value,colour) in enumerate(zip((getattr(self,'adena_label','ADENA / HR'),'EXP / HR','KILLS / HR'),self.values,((247,202,102),(134,224,183),(214,224,245)))):
                        x=i*103+8
                        self.text(dc,label,(x,7,(266 if getattr(self,'on_settings',None) else 288) if i==2 else x+91,24),self.small,(180,190,205))
                        self.text(dc,value,(x,26,x+91,53),self.large,colour)
                    # Small vector padlock: no emoji/font dependency.
                    parts=[(295,11,304,12),(295,18,304,19),(295,12,296,18),(303,12,304,18),(299,14,300,17)]
                    parts += ([(297,7,302,8),(297,8,298,11),(301,8,302,11)] if self.locked else [(297,6,302,7),(297,7,298,11),(301,7,302,9)])
                    for part in parts:self.u.FillRect(dc,c.byref(w.RECT(*part)),self.lock_brush)
                    self.paint_gear(dc,SETTINGS_RECT)
                    self.u.FillRect(dc,c.byref(w.RECT(8,56,302,57)),self.divider)
                    self.u.FillRect(dc,c.byref(w.RECT(*PAUSE_RECT)),self.control)
                    paused=getattr(self,'paused',False)
                    self.text(dc,'PAUSED' if paused else 'SESSION ACTIVE',(9,60,170,82),self.small,(247,202,102) if paused else (134,224,183))
                    self.text(dc,'  Resume' if paused else '  Pause',PAUSE_RECT,self.small,(235,240,248))
                    if getattr(self,'on_reset',None):
                        self.u.FillRect(dc,c.byref(w.RECT(*RESET_RECT)),self.control)
                        self.text(dc,'  Reset',RESET_RECT,self.small,(235,240,248))
                finally:self.u.EndPaint(h,c.byref(ps))
            return 0
        return self.u.DefWindowProcW(h,msg,wp,lp)
    def paint_gear(self,dc,rect):
        if not getattr(self,'on_settings',None) or not rect:return
        # Draw a small gear from filled pixel rectangles. No emoji or font
        # dependency, and no extra GDI objects to allocate on each paint.
        l,t,r,b=rect;x=(l+r)//2-7;y=(t+b)//2-7
        rows=('.....####.....','.....####.....','..##.####.##..','.############.','.############.','##############','#####....#####','#####....#####','##############','.############.','.############.','..##.####.##..','.....####.....','.....####.....')
        for j,row in enumerate(rows):
            for i,ch in enumerate(row):
                if ch=='#':self.u.FillRect(dc,c.byref(w.RECT(x+i,y+j,x+i+1,y+j+1)),self.lock_brush)
    def paint_buffered(self,dc):
        # Compose a complete frame off-screen, then copy it in one operation.
        # Always release the bitmap and DC, including on failed drawing.
        width,height=self.dimensions()
        mem=self.g.CreateCompatibleDC(dc)
        if not mem:self.paint_layout(dc);return
        bitmap=None;previous=None
        try:
            bitmap=self.g.CreateCompatibleBitmap(dc,width,height)
            if not bitmap:self.paint_layout(dc);return
            previous=self.g.SelectObject(mem,bitmap)
            if not previous or previous==c.c_void_p(-1).value:self.paint_layout(dc);return
            self.paint_layout(mem)
            if not self.g.BitBlt(dc,0,0,width,height,mem,0,0,0x00CC0020):self.paint_layout(dc)
        finally:
            if previous and previous!=c.c_void_p(-1).value:self.g.SelectObject(mem,previous)
            if bitmap:self.g.DeleteObject(bitmap)
            self.g.DeleteDC(mem)
    def paint_layout(self,dc):
        g=self.layout;width,height=self.dimensions()
        fill=lambda rect,brush:self.u.FillRect(dc,c.byref(w.RECT(*rect)),brush)
        fill((0,0,width,height),self.brush);self.g.SetBkMode(dc,1)
        if g.get('title'):self.text(dc,g['title'],(8,2,width-48,22),self.small,(180,190,205))
        values=getattr(self,'widget_values',{})
        for k,x,y,cw,rh in g['cells']:
            _,label,colour=WIDGETS[k]
            label,value=values.get(k,(label,'—'))
            self.text(dc,label,(x,y,x+cw-3,y+18),self.small,(180,190,205))
            self.text(dc,value,(x,y+18,x+cw-3,y+rh-2),self.large,colour)
        x=(g['lock'][0]+g['lock'][2])//2-4
        parts=[(x,11,x+9,12),(x,18,x+9,19),(x,12,x+1,18),(x+8,12,x+9,18),(x+4,14,x+5,17)]
        parts += [(x+2,7,x+7,8),(x+2,8,x+3,11),(x+6,8,x+7,11 if self.locked else 9)]
        for part in parts:fill(part,self.lock_brush)
        self.paint_gear(dc,g['settings'])
        for i,(name,value) in enumerate(getattr(self,'detail_rows',())[:g.get('details',0)]):
            y=g['detail_y']+i*21
            self.text(dc,name,(8,y,width-90,y+20),self.small,(180,190,205))
            self.text(dc,value,(width-85,y,width-5,y+20),self.small,(247,202,102))
        action=g.get('select_loot')
        if action:
            fill(action,self.control)
            self.text(dc,'  Select loot table…',action,self.small,(235,240,248))
        if g['footer']:
            fill((8,height-31,width-8,height-30),self.divider)
            if g['status']:self.text(dc,'PAUSED' if self.paused else getattr(self,'capture_state','SESSION ACTIVE'),(8,height-28,122,height-4),self.small,(247,202,102) if self.paused or getattr(self,'capture_state','SESSION ACTIVE')!='SESSION ACTIVE' else (134,224,183))
            for k,label in [('pause','  Resume' if self.paused else '  Pause'),('reset','  Reset')]:
                if g[k]:fill(g[k],self.control);self.text(dc,label,g[k],self.small,(235,240,248))
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
        width,height=self.dimensions()
        if x<=point[0]<x+width and y<=point[1]<y+height:
            self.drag=(point[0]-x,point[1]-y)
            self.drag_poll_seen=False;self.drag_rejected=False
            diagnostic('HUD drag started')
    def finish_drag(self):
        if self.drag is None:return
        self.drag=None;self.drag_poll_seen=False
        native=getattr(self,'native_drag',False);self.native_drag=False
        if native and self.u.GetCapture()==self.hwnd:self.u.ReleaseCapture()
        diagnostic('HUD drag ended')
        if self.preferred is not None and self.on_move:self.on_move(self.preferred)
    def arm_placement(self):
        self.finish_drag(); self.lock_first=None; self.set_interactive(False)
        self.placement={'seen':False,'shift_ready':False}
    def cancel_placement(self):
        self.placement=None
    def placement_position(self,geo,chat,desktop,shift,point):
        state=self.placement; state['seen']=True
        if not shift:state['shift_ready']=True
        width,height=self.dimensions()
        candidate=None if point is None else safe_position(geo,chat,desktop,(point[0]-geo[0]-width//2,point[1]-geo[1]-height//2),self.dimensions(),self.protected())
        if candidate is not None and shift and state['shift_ready']:
            self.preferred=(candidate[0]-geo[0],candidate[1]-geo[1]); self.cancel_placement()
            if self.on_move:self.on_move(self.preferred)
        return candidate
    def update(self,api,target,chat,running,seconds,adena,xp,kills=0,paused=False,consumable_cost=None,unpriced_uses=0,widgets=None,protected=(),capture_state='SESSION ACTIVE'):
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
        self.protected_regions=protected
        self.drag_context=(geo,chat,desktop)
        # Do not cancel a native drag just because the game/OS reports no
        # asynchronous button state. Native mouse messages remain authoritative.
        if self.drag is not None and mouse_down:self.drag_poll_seen=True
        if not mouse_down:
            native=getattr(self,'native_drag',False)
            if not native or getattr(self,'drag_poll_seen',False):
                self.release_press()
            elif time.monotonic()-self.native_activity>2 and self.u.GetCapture()!=self.hwnd and not self.hit_rect(self.cursor(),(0,0,*self.dimensions())):
                self.release_press()
        if getattr(self,'placement',None) is not None:
            self.set_interactive(False)
            # No overlay clicks or mouse routing: move with pointer and tap Shift.
            candidate=self.placement_position(geo,chat,desktop,shift,self.cursor())
            pos=candidate or hud_position(geo,chat,desktop,self.preferred,self.dimensions(),self.protected())
        else:
            point=self.cursor()
            self.set_interactive(self.wants_input(point))
            # Polling fallback catches missed native mouse messages without
            # starting a drag when the button was already held on entry.
            if mouse_down and previous is False:self.handle_press(point)
            if self.drag is not None:
                if mouse_down:
                    self.drag_poll_seen=True
                    self.move_drag(point)
                elif not getattr(self,'native_drag',False):self.finish_drag()
            pos=hud_position(geo,chat,desktop,self.preferred,self.dimensions(),self.protected())
        if pos is None:self.hide();return
        label,adena_rate=adena_metric(adena,seconds,consumable_cost,unpriced_uses)
        values=(adena_rate,rate_text(xp,seconds),rate_text(kills,seconds))
        new_widgets=dict(widgets or {},ad=(label.replace(' / HR','/H'),adena_rate),xp=('EXP/H',values[1]),kills=('KILLS/H',values[2]))
        layout=getattr(self,'layout',None)
        state_changed=capture_state!=getattr(self,'capture_state','SESSION ACTIVE') or paused!=getattr(self,'paused',False)
        self.capture_state=capture_state;self.paused=paused
        if layout:
            # Input and positioning still poll at 25 ms. Only rendered
            # metrics are sampled once a second, independently per panel.
            keys=[k for k,*_ in layout['cells']]
            visible={k:new_widgets[k] for k in keys if k in new_widgets}
            now=time.monotonic()
            due=not self.shown or now>=getattr(self,'next_metric_paint',0)
            if due:
                self.next_metric_paint=now+1
                changed=visible!=getattr(self,'widget_values',{})
                self.widget_values=visible;self.values=values;self.adena_label=label
            else:changed=False
            if state_changed or changed:self.u.InvalidateRect(self.hwnd,None,False)
        else:
            # Compatibility layout used by older callers/tests.
            if state_changed or values!=self.values or label!=getattr(self,'adena_label','ADENA / HR'):
                self.values=values;self.adena_label=label;self.u.InvalidateRect(self.hwnd,None,False)
        if not self.shown or pos!=self.position:
            if self.u.SetWindowPos(self.hwnd,c.c_void_p(-1),*pos,*self.dimensions(),0x0010|0x0040|0x0200):
                self.shown=True;self.position=pos
        # Recheck after showing; never intentionally keep HUD over another app.
        if api.foreground()!=target.hwnd:
            if getattr(self,"placement",None) and self.placement["seen"]:self.cancel_placement()
            self.hide()
    def hide(self):
        self.release_press();self.drag_context=None;self.set_interactive(False);self.last_mouse_down=None;self.lock_first=None
        if self.hwnd and self.shown:self.u.ShowWindow(self.hwnd,0);self.shown=False;self.position=None
    def close(self):
        self.cancel_placement(); self.finish_drag()
        if self.hwnd:self.u.DestroyWindow(self.hwnd);self.hwnd=None
        for obj in (self.brush,self.divider,self.small,self.large,self.control,self.lock_brush):
            if obj:self.g.DeleteObject(obj)
        self.u.UnregisterClassW(self.name,self.instance)
