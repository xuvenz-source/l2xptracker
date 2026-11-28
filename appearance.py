"""Shared desktop theme and live metric cards. No additional dependencies."""
import json, os, tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from settings import settings_path
from history import rate

PALETTES={
    'dark':dict(bg='#0E1117',panel='#191E27',field='#121720',text='#E8ECF3',muted='#A0ABBA',border='#303844',hover='#282F3A',selected='#3B3B37',disabled='#778393',gold='#E7BD7A',green='#7DDCB0',blue='#A7BBF2',warn='#F1B578',red='#FFA5A5',primary='#285F4B',primary_hover='#32765C',primary_text='#FFFFFF'),
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
        s.configure('Title.TLabel',font=('Segoe UI',20,'bold'))
        s.configure('Brand.TLabel',font=('Segoe UI',15,'bold'),foreground=p['gold'])
        s.configure('Sidebar.TFrame',background=p['panel'])
        s.configure('SidebarCaption.TLabel',background=p['panel'],foreground=p['muted'],font=('Segoe UI',9,'bold'))
        s.configure('Nav.TButton',background=p['panel'],foreground=p['muted'],anchor='w',padding=(13,10),borderwidth=0,relief='flat')
        s.map('Nav.TButton',background=[('pressed',p['selected']),('selected',p['selected']),('active',p['hover'])],foreground=[('selected',p['gold']),('active',p['text'])])
        s.configure('Workspace.TNotebook',background=p['bg'],borderwidth=0,tabmargins=(0,0,0,0))
        s.layout('Workspace.TNotebook.Tab',[])
        s.configure('CardTitle.TLabel',background=p['panel'],foreground=p['text'],font=('Segoe UI',12,'bold'))
        s.configure('CardBody.TLabel',background=p['panel'],foreground=p['text'],font=('Segoe UI',10))
        s.configure('TProgressbar',background=p['green'],troughcolor=p['field'],borderwidth=0,thickness=9)
        s.configure('Section.TLabel',font=('Segoe UI',11,'bold'))
        s.configure('Muted.TLabel',foreground=p['muted'],font=('Segoe UI',9))
        s.configure('Status.TLabel',foreground=p['muted'],font=('Segoe UI',10))
        s.configure('Card.TFrame',background=p['panel'],relief='solid',borderwidth=1)
        s.configure('CardLabel.TLabel',background=p['panel'],foreground=p['muted'],font=('Segoe UI',9,'bold'))
        s.configure('CardTotal.TLabel',background=p['panel'],foreground=p['muted'],font=('Segoe UI',10))
        for name,colour in [('Gold','gold'),('Green','green'),('Blue','blue')]:
            s.configure(name+'.Metric.TLabel',background=p['panel'],foreground=p[colour],font=('Segoe UI',25,'bold'))
        s.configure('TNotebook',background=p['bg'],borderwidth=0,tabmargins=(0,0,0,5))
        s.configure('TNotebook.Tab',background=p['panel'],foreground=p['muted'],padding=(14,8),font=('Segoe UI',10,'bold'),borderwidth=0)
        s.map('TNotebook.Tab',background=[('selected',p['selected']),('active',p['hover'])],foreground=[('selected',p['text'])])
        s.configure('TButton',background=p['panel'],foreground=p['text'],padding=(11,7),borderwidth=1,relief='flat')
        s.map('TButton',background=[('disabled',p['bg']),('pressed',p['selected']),('active',p['hover'])],foreground=[('disabled',p['disabled'])])
        s.configure('Compact.TButton',padding=(8,4))
        s.configure('Compact.TNotebook.Tab',padding=(12,5))
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
        for orientation in ('Vertical','Horizontal'):
            s.configure(orientation+'.TScrollbar',background=p['border'],troughcolor=p['bg'],arrowcolor=p['text'],borderwidth=0)
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
        elif isinstance(widget,tk.Canvas) and widget.master.__class__.__name__=='ScrollPage':
            widget.configure(background=p['bg'])
        elif isinstance(widget,tk.Text):
            widget.configure(background=p['field'],foreground=p['text'],insertbackground=p['text'],selectbackground=p['selected'],selectforeground=p['text'],highlightbackground=p['border'],highlightcolor=p['blue'],highlightthickness=1,borderwidth=0,padx=9,pady=7,font=('Consolas',10))
            widget.tag_configure('accepted',foreground=p['green'])
            widget.tag_configure('review',foreground=p['warn'])
            widget.tag_configure('ignored',foreground=p['muted'])
        if isinstance(widget,RateTrend):widget.redraw()
        for child in widget.winfo_children():self.restyle(child)

class Dashboard(ttk.Frame):
    def __init__(self,parent):
        super().__init__(parent)
        self.values=[];self.totals=[];self.labels=[]
        for i,(label,colour) in enumerate((('ADENA / HR','Gold'),('EXP / HR','Green'),('KILLS / HR','Blue'))):
            self.columnconfigure(i,weight=1,uniform='metrics')
            card=ttk.Frame(self,style='Card.TFrame',padding=(16,12))
            card.grid(row=0,column=i,sticky='nsew',padx=(0 if i==0 else 5,0 if i==2 else 5))
            value=tk.StringVar(master=self,value='—');total=tk.StringVar(master=self,value='Total 0')
            self.values.append(value);self.totals.append(total)
            label_var=tk.StringVar(master=self,value=label);self.labels.append(label_var)
            ttk.Label(card,textvariable=label_var,style='CardLabel.TLabel').pack(anchor='w')
            ttk.Label(card,textvariable=value,style=colour+'.Metric.TLabel').pack(anchor='w',pady=(3,0))
            ttk.Label(card,textvariable=total,style='CardTotal.TLabel').pack(anchor='w')
    def update_metrics(self,seconds,adena,xp,kills,cost=None,unpriced=0):
        metrics=list(metric_values(seconds,adena,xp,kills))
        if cost is not None:
            net=adena-float(cost);metrics[0]=(rate(net,seconds),f'Gross {adena:,} · known costs {cost:,.0f}')
        self.labels[0].set(('NET ADENA / HR*' if unpriced else 'NET ADENA / HR') if cost is not None else 'ADENA / HR')
        for v,t,(number,total) in zip(self.values,self.totals,metrics):
            if v.get()!=number:v.set(number)
            if t.get()!=total:t.set(total)

class RateTrend(ttk.Frame):
    """Live session-average XP rate samples, indexed by active session time."""
    def __init__(self,parent,appearance):
        super().__init__(parent,style='Card.TFrame',padding=12)
        self.appearance=appearance;self.key=None;self.points=[]
        ttk.Label(self,text='XP rate over time',style='CardTitle.TLabel').pack(anchor='w')
        ttk.Label(self,text='Session-average XP/hr · last 60 active minutes',style='CardLabel.TLabel').pack(anchor='w',pady=(2,3))
        self.canvas=tk.Canvas(self,height=150,highlightthickness=0,borderwidth=0)
        self.canvas.pack(fill='x');self.canvas.bind('<Configure>',lambda e:self.redraw())
    def sample(self,key,seconds,xp,running):
        changed=key!=self.key or bool(self.points and seconds<self.points[-1][0])
        if changed:self.key=key;self.points=[]
        if running and seconds>=1 and (not self.points or seconds-self.points[-1][0]>=30):
            self.points.append((seconds,xp*3600/seconds))
            self.points=[p for p in self.points if p[0]>=seconds-3600];changed=True
        if changed:self.redraw()
    def redraw(self):
        p=self.appearance.palette;cv=self.canvas;cv.configure(background=p['panel']);cv.delete('all')
        w=max(1,cv.winfo_width());h=max(1,cv.winfo_height())
        if w<100 or h<60:return
        if len(self.points)<2:
            cv.create_text(w/2,h/2,text='Live trend appears after 30 active seconds.',fill=p['muted'],font=('Segoe UI',10));return
        l,t,r,b=58,10,w-12,h-24
        max_y=max(1,max(v for _,v in self.points));lo=self.points[0][0];hi=self.points[-1][0]
        for i in range(4):
            y=b-(b-t)*i/3;value=max_y*i/3
            cv.create_line(l,y,r,y,fill=p['border'],dash=(3,4))
            cv.create_text(l-6,y,text=f'{value:,.0f}',anchor='e',fill=p['muted'],font=('Segoe UI',9))
        xy=[v for x,y in self.points for v in (l+(r-l)*(x-lo)/max(1,hi-lo),b-(b-t)*y/max_y)]
        cv.create_line(*xy,fill=p['green'],width=2)
        cv.create_text(l,b+13,text=f'{lo/60:.1f}m',anchor='w',fill=p['muted'],font=('Segoe UI',9))
        cv.create_text(r,b+13,text=f'{hi/60:.1f}m',anchor='e',fill=p['muted'],font=('Segoe UI',9))
