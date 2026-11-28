"""Temporary pixel-aligned frozen game surface, not a game input hook."""
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk
import ctypes as c
from ctypes import wintypes as w
import os

def clamp_toolbar(x,y,width,height,bar_w,bar_h):
    return max(0,min(width-bar_w,x)),max(0,min(height-bar_h,y))

def screen_origin(rect):
    return int(rect['left']),int(rect['top'])

def align_window(win,rect):
    """Tk negative geometry offsets are monitor-relative, not absolute.
    Use a native position for the overlay's own window, including left monitors.
    """
    x,y=screen_origin(rect);width,height=rect['width'],rect['height']
    win.geometry(f'{width}x{height}+0+0')
    win.update_idletasks()
    if os.name=='nt':
        u=c.WinDLL('user32',use_last_error=True)
        u.GetAncestor.argtypes=[w.HWND,w.UINT];u.GetAncestor.restype=w.HWND
        u.SetWindowPos.argtypes=[w.HWND,w.HWND,c.c_int,c.c_int,c.c_int,c.c_int,w.UINT]
        u.SetWindowPos.restype=w.BOOL
        hwnd=u.GetAncestor(win.winfo_id(),2)
        if not hwnd or not u.SetWindowPos(hwnd,c.c_void_p(-1),x,y,width,height,0x0010|0x0040):
            raise RuntimeError('Could not position selection overlay.')
    else:
        win.geometry(f'{width}x{height}{x:+d}{y:+d}')
    win.update_idletasks()

class SelectionSurface:
    def __init__(self,root,shot,rect):
        self.width,self.height=shot.size
        if (self.width,self.height)!=(rect['width'],rect['height']):raise ValueError('Screenshot size does not match the game client.')
        self.win=tk.Toplevel(root)
        try:
            self.win.overrideredirect(True);self.win.attributes('-topmost',True)
            self.canvas=tk.Canvas(self.win,width=self.width,height=self.height,highlightthickness=0,borderwidth=0,takefocus=True,cursor='crosshair')
            self.canvas.pack(fill='both',expand=True)
            self.photo=ImageTk.PhotoImage(shot,master=self.win)
            self.canvas.create_image(0,0,anchor='nw',image=self.photo)
            align_window(self.win,rect)
            if (self.canvas.winfo_rootx(),self.canvas.winfo_rooty(),self.canvas.winfo_width(),self.canvas.winfo_height())!=(rect['left'],rect['top'],self.width,self.height):
                raise RuntimeError('Overlay is not pixel-aligned. Use the preview editor instead.')
        except Exception:
            self.win.destroy();raise
    def toolbar(self):
        frame=ttk.Frame(self.canvas,padding=5,relief='raised')
        grip=ttk.Label(frame,text='≡  Drag toolbar',cursor='fleur')
        grip.pack(anchor='w')
        self.bar=frame;self.grip=grip
        return frame
    def finish_toolbar(self):
        self.bar.update_idletasks()
        bw,bh=self.bar.winfo_reqwidth(),self.bar.winfo_reqheight()
        if bw>self.width or bh>self.height:raise RuntimeError('Game client is too small for the selection toolbar.')
        self.bar_xy=clamp_toolbar((self.width-bw)//2,8,self.width,self.height,bw,bh)
        self.bar_id=self.canvas.create_window(*self.bar_xy,anchor='nw',window=self.bar)
        def down(e):self.drag_bar=(e.x_root,e.y_root,*self.bar_xy)
        def move(e):
            if not getattr(self,'drag_bar',None):return
            x,y,bx,by=self.drag_bar
            self.bar_xy=clamp_toolbar(bx+e.x_root-x,by+e.y_root-y,self.width,self.height,bw,bh)
            self.canvas.coords(self.bar_id,*self.bar_xy)
        self.grip.bind('<Button-1>',down);self.grip.bind('<B1-Motion>',move)
        self.grip.bind('<ButtonRelease-1>',lambda e:setattr(self,'drag_bar',None))
        self.win.bind('<Tab>',self.toggle_toolbar)
        self.win.grab_set();self.win.focus_force();self.canvas.focus_set()
    def toggle_toolbar(self,e=None):
        state=self.canvas.itemcget(self.bar_id,'state')
        self.canvas.itemconfigure(self.bar_id,state='normal' if state=='hidden' else 'hidden')
        self.canvas.focus_set();return 'break'
    def destroy(self):
        self.win.destroy()
