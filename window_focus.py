"""Windows window metadata only; no process handles, inputs or memory access."""
from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import os

@dataclass(frozen=True)
class Target:
    hwnd: int
    pid: int
    title: str
    width: int
    height: int
    window_class: str = ""

class Windows:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('Window tracking requires Windows.')
        self.u = ctypes.WinDLL('user32', use_last_error=True)
        self.enum_callback=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
        for name, args, result in [
            ('GetClassNameW', [wintypes.HWND,wintypes.LPWSTR,ctypes.c_int],ctypes.c_int),
            ('EnumWindows', [self.enum_callback,wintypes.LPARAM],wintypes.BOOL),
            ('GetForegroundWindow', [], wintypes.HWND),
            ('GetWindowThreadProcessId', [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)], wintypes.DWORD),
            ('GetWindowTextLengthW', [wintypes.HWND], ctypes.c_int),
            ('GetWindowTextW', [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            ('IsWindow', [wintypes.HWND], wintypes.BOOL),
            ('IsWindowVisible', [wintypes.HWND], wintypes.BOOL),
            ('IsIconic', [wintypes.HWND], wintypes.BOOL),
            ('GetWindowRect', [wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            ('GetWindow', [wintypes.HWND, wintypes.UINT], wintypes.HWND),
            ('GetClientRect', [wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            ('ClientToScreen', [wintypes.HWND, ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
        ]:
            f = getattr(self.u, name); f.argtypes = args; f.restype = result
    def foreground(self):
        return self.u.GetForegroundWindow()
    def pid(self, hwnd):
        p = wintypes.DWORD()
        self.u.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        return p.value
    def title(self, hwnd):
        n = self.u.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        self.u.GetWindowTextW(hwnd, buf, n + 1)
        return buf.value
    def window_class(self,hwnd):
        buf=ctypes.create_unicode_buffer(256)
        self.u.GetClassNameW(hwnd,buf,len(buf))
        return buf.value
    def find_saved(self,data):
        from settings import select_match
        matches=[]
        @self.enum_callback
        def visit(h,_):
            if (self.usable(h) and self.pid(h)!=os.getpid() and self.title(h)==data["title"] and self.window_class(h)==data["window_class"]):
                geo=self.geometry(h)
                if geo and geo[2:]==(data["width"],data["height"]):
                    matches.append(Target(h,self.pid(h),data["title"],geo[2],geo[3],data["window_class"]))
            return True
        self.u.EnumWindows(visit,0)
        return select_match(matches,self.foreground())
    def usable(self, hwnd):
        return bool(hwnd and self.u.IsWindow(hwnd) and self.u.IsWindowVisible(hwnd) and not self.u.IsIconic(hwnd))
    def region_clear(self,hwnd,region):
        """Reject visible windows above the game that overlap the chat region."""
        try:
            dwm=ctypes.WinDLL('dwmapi',use_last_error=True).DwmGetWindowAttribute
            dwm.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
            dwm.restype=ctypes.c_long
        except (OSError,AttributeError):dwm=None
        visited={hwnd};h=self.u.GetWindow(hwnd,3)
        while h:
            if h in visited or len(visited)>2048:return False
            visited.add(h)
            if self.usable(h):
                cloaked=wintypes.DWORD()
                hidden=bool(dwm and dwm(h,14,ctypes.byref(cloaked),ctypes.sizeof(cloaked))==0 and cloaked.value)
                if not hidden:
                    rect=wintypes.RECT()
                    if not self.u.GetWindowRect(h,ctypes.byref(rect)):return False
                    if intersects(region,(rect.left,rect.top,rect.right,rect.bottom)):return False
            h=self.u.GetWindow(h,3)
        return bool(self.usable(hwnd))
    def geometry(self, hwnd):
        r = wintypes.RECT(); p = wintypes.POINT(0, 0)
        if not self.u.GetClientRect(hwnd, ctypes.byref(r)) or not self.u.ClientToScreen(hwnd, ctypes.byref(p)):
            return None
        return (p.x, p.y, r.right-r.left, r.bottom-r.top)
    def bind_foreground(self):
        h = self.foreground()
        if not self.usable(h): raise RuntimeError('No usable foreground window.')
        pid, title, geo = self.pid(h), self.title(h), self.geometry(h)
        if not pid or pid == os.getpid() or not title or not geo or min(geo[2:]) < 100:
            raise RuntimeError('Focus the actual Lineage 2 game window, not the tracker or desktop.')
        if title.lower() in ('program manager', 'task switching'):
            raise RuntimeError('Focus the game window, not the desktop.')
        return Target(h, pid, title, geo[2], geo[3], self.window_class(h))


def intersects(region,bounds):
    x,y,r,b=bounds
    return x<region['left']+region['width'] and r>region['left'] and y<region['top']+region['height'] and b>region['top']

def capture_region(api, target, local, desktop, pause_on_blur=True):
    """Return only visible and unobstructed original game pixels."""
    h = target.hwnd
    if not api.usable(h) or api.pid(h) != target.pid:
        return None, 'Game window unavailable; reopen it and select the chat area again.'
    if pause_on_blur and api.foreground() != h:
        return None, 'Paused — Lineage 2 is not focused. Return to the game to resume.'
    geo = api.geometry(h)
    if not geo: return None, 'Paused — game window geometry unavailable.'
    x, y, w, height = geo
    if (w, height) != (target.width, target.height):
        return None, 'Paused — game size changed. Restore its size or stop and reselect chat.'
    l,t,r,b = local['left'],local['top'],local['width'],local['height']
    if min(l,t)<0 or min(r,b)<=0 or l+r>w or t+b>height:
        return None, 'Paused — selected chat is outside the game client.'
    region = dict(left=x+l, top=y+t, width=r, height=b)
    if (region['left']<desktop['left'] or region['top']<desktop['top'] or
        region['left']+r>desktop['left']+desktop['width'] or region['top']+b>desktop['top']+desktop['height']):
        return None, 'Paused — chat is outside the visible desktop.'
    if not api.region_clear(h,region):
        return None, 'Waiting — game chat is covered. Keep the chat visible to continue tracking.'
    return region, None
