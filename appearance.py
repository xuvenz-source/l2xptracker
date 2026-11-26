"""Shared desktop theme and live metric cards. No additional dependencies."""
import json, os, tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from settings import settings_path
from history import rate

PALETTES={
    'dark':dict(bg='#131820',panel='#1D2531',field='#10161E',text='#E6EDF5',muted='#A7B4C6',border='#39485A',hover='#344359',selected='#344C69',disabled='#758397',gold='#F5C66A',green='#83DDB0',blue='#AAC8FF',warn='#F1B578',red='#FFA5A5',primary='#275D4C',primary_hover='#32755E',primary_text='#FFFFFF'),
    'light':dict(bg='#F2F5F9',panel='#FFFFFF',field='#FFFFFF',text='#202C3B',muted='#526377',border='#C7D1DE',hover='#DFE7F1',selected='#CEDFF5',disabled='#65758B',gold='#81520A',green='#176748',blue='#285D9E',warn='#92500E',red='#A62938',primary='#21664E',primary_hover='#17543F',primary_text='#FFFFFF')
}

def preference_path():
    return settings_path().with_name('appearance.json')

def load_mode(path=None):
    try:
        mode=json.loads(Path(path or preference_path()).read_text(encoding='utf-8')).get('mode')
        return mode if mode in PALETTES else 'dark'
    except (OSError,ValueError,AttributeError,TypeError):return 'dark'

def save_mode(mode,path=None):
    if mode not in PALETTES:raise ValueError('Unknown appearance')
    path=Path(path or preference_path());path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.appearance-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as out:json.dump({'mode':mode},out)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def metric_values(seconds,adena,xp,kills):
    return tuple((rate(n,seconds),f'Total {n:,}') for n in (adena,xp,kills))

class Appearance:
    def __init__(self,root):
        self.root=root;self.mode=load_mode()
        self.style=ttk.Style(root)
        self.apply(self.mode)
    def apply(self,mode):
        p=PALETTES[mode];self.mode=mode;self.palette=p
        s=self.style;s.theme_use('clam')
        s.configure('.',background=p['bg'],foreground=p['text'],font=('Segoe UI',10),bordercolor=p['border'],lightcolor=p['border'],darkcolor=p['border'],focuscolor=p['blue'],troughcolor=p['bg'],selectbackground=p['selected'],selectforeground=p['text'])
        for style in ('TFrame','TLabel','TLabelframe','TLabelframe.Label','TCheckbutton','TRadiobutton'):
            s.configure(style,background=p['bg'],foreground=p['text'])
        s.configure('Title.TLabel',font=('Segoe UI',19,'bold'))
        s.configure('Section.TLabel',font=('Segoe UI',11,'bold'))
        s.configure('Muted.TLabel',foreground=p['muted'],font=('Segoe UI',9))
        s.configure('Status.TLabel',foreground=p['muted'],font=('Segoe UI',10))
        s.configure('Card.TFrame',background=p['panel'],relief='solid',borderwidth=1)
        s.configure('CardLabel.TLabel',background=p['panel'],foreground=p['muted'],font=('Segoe UI',9,'bold'))
        s.configure('CardTotal.TLabel',background=p['panel'],foreground=p['muted'],font=('Segoe UI',10))
        for name,colour in [('Gold','gold'),('Green','green'),('Blue','blue')]:
            s.configure(name+'.Metric.TLabel',background=p['panel'],foreground=p[colour],font=('Segoe UI',25,'bold'))
        s.configure('TButton',background=p['panel'],foreground=p['text'],padding=(11,7),borderwidth=1,relief='flat')
        s.map('TButton',background=[('disabled',p['bg']),('pressed',p['selected']),('active',p['hover'])],foreground=[('disabled',p['disabled'])])
        s.configure('Primary.TButton',background=p['primary'],foreground=p['primary_text'],font=('Segoe UI',10,'bold'))
        s.map('Primary.TButton',background=[('disabled',p['panel']),('pressed',p['primary_hover']),('active',p['primary_hover'])],foreground=[('disabled',p['disabled']),('!disabled',p['primary_text'])])
        s.configure('Danger.TButton',foreground=p['red'])
        s.map('Danger.TButton',foreground=[('disabled',p['disabled']),('!disabled',p['red'])])
        for style in ('TEntry','TCombobox'):
            s.configure(style,fieldbackground=p['field'],background=p['panel'],foreground=p['text'],insertcolor=p['text'],arrowcolor=p['text'],padding=6)
            s.map(style,fieldbackground=[('disabled',p['panel']),('readonly',p['panel'])],foreground=[('disabled',p['disabled']),('readonly',p['muted'])],selectbackground=[('!disabled',p['selected'])],selectforeground=[('!disabled',p['text'])])
        for style in ('TCheckbutton','TRadiobutton'):
            s.configure(style,indicatorbackground=p['field'],indicatorforeground=p['blue'],indicatormargin=(0,0,6,0))
            s.map(style,background=[('active',p['bg'])],foreground=[('disabled',p['disabled'])],indicatorbackground=[('selected',p['selected']),('disabled',p['panel']),('!selected',p['field'])])
        s.configure('Treeview',background=p['panel'],fieldbackground=p['panel'],foreground=p['text'],rowheight=29,borderwidth=0,relief='flat')
        s.map('Treeview',background=[('selected',p['selected'])],foreground=[('selected',p['text'])])
        s.configure('Treeview.Heading',background=p['bg'],foreground=p['muted'],font=('Segoe UI',9,'bold'),padding=(8,7),relief='flat')
        s.map('Treeview.Heading',background=[('active',p['hover'])])
        s.configure('Vertical.TScrollbar',background=p['panel'],troughcolor=p['bg'],arrowcolor=p['muted'],borderwidth=0)
        s.map('Vertical.TScrollbar',background=[('active',p['hover'])])
        # Classic widgets and pop-downs do not inherit ttk styles.
        for name,value in [('Background',p['bg']),('Foreground',p['text']),('Font','{Segoe UI} 10'),('selectBackground',p['selected']),('selectForeground',p['text']),('insertBackground',p['text']),('TCombobox*Listbox.background',p['field']),('TCombobox*Listbox.foreground',p['text'])]:
            self.root.option_add('*'+name,value)
        self.restyle(self.root)
    def restyle(self,widget):
        p=self.palette
        if isinstance(widget,(tk.Tk,tk.Toplevel)):
            widget.configure(background=p['bg'])
            # Best effort dark native title bar on supported Windows versions.
            if os.name=='nt':
                try:
                    import ctypes
                    widget.update_idletasks()
                    u=ctypes.windll.user32
                    from ctypes import wintypes
                    u.GetParent.argtypes=[wintypes.HWND];u.GetParent.restype=wintypes.HWND
                    hwnd=u.GetParent(widget.winfo_id()) or widget.winfo_id()
                    value=ctypes.c_int(int(self.mode=='dark'))
                    fn=ctypes.windll.dwmapi.DwmSetWindowAttribute
                    fn.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
                    if fn(hwnd,20,ctypes.byref(value),ctypes.sizeof(value))!=0:
                        fn(hwnd,19,ctypes.byref(value),ctypes.sizeof(value))
                except Exception:pass
        elif isinstance(widget,tk.Text):
            widget.configure(background=p['field'],foreground=p['text'],insertbackground=p['text'],selectbackground=p['selected'],selectforeground=p['text'],highlightbackground=p['border'],highlightcolor=p['blue'],highlightthickness=1,borderwidth=0,padx=9,pady=7,font=('Consolas',10))
            widget.tag_configure('accepted',foreground=p['green'])
            widget.tag_configure('review',foreground=p['warn'])
            widget.tag_configure('ignored',foreground=p['muted'])
        for child in widget.winfo_children():self.restyle(child)

class Dashboard(ttk.Frame):
    def __init__(self,parent):
        super().__init__(parent)
        self.values=[];self.totals=[]
        for i,(label,colour) in enumerate((('ADENA / HR','Gold'),('EXP / HR','Green'),('KILLS / HR','Blue'))):
            self.columnconfigure(i,weight=1,uniform='metrics')
            card=ttk.Frame(self,style='Card.TFrame',padding=(16,12))
            card.grid(row=0,column=i,sticky='nsew',padx=(0 if i==0 else 5,0 if i==2 else 5))
            value=tk.StringVar(master=self,value='—');total=tk.StringVar(master=self,value='Total 0')
            self.values.append(value);self.totals.append(total)
            ttk.Label(card,text=label,style='CardLabel.TLabel').pack(anchor='w')
            ttk.Label(card,textvariable=value,style=colour+'.Metric.TLabel').pack(anchor='w',pady=(3,0))
            ttk.Label(card,textvariable=total,style='CardTotal.TLabel').pack(anchor='w')
    def update_metrics(self,seconds,adena,xp,kills):
        for v,t,(number,total) in zip(self.values,self.totals,metric_values(seconds,adena,xp,kills)):
            if v.get()!=number:v.set(number)
            if t.get()!=total:t.set(total)
