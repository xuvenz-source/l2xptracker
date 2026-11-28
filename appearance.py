"""Shared desktop theme and live metric cards. No additional dependencies."""
import json, os, tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from settings import settings_path
from history import rate

PALETTES={
    'dark':dict(bg='#101217',panel='#191C23',field='#12151B',text='#F0F1F4',muted='#A0A5B0',border='#2B3039',hover='#292D35',selected='#30291F',disabled='#77808D',gold='#D9B67A',green='#9BDFC0',blue='#B1C1EF',warn='#F1B578',red='#FFA5A5',primary='#D9B67A',primary_hover='#E8C990',primary_text='#171410'),
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
        s.configure('Sidebar.TFrame',background=p['field'])
        s.configure('SidebarBrand.TLabel',background=p['field'],foreground=p['gold'],font=('Segoe UI',18,'bold'))
        s.configure('SidebarSub.TLabel',background=p['field'],foreground=p['muted'],font=('Segoe UI',8))
        s.configure('Eyebrow.TLabel',foreground=p['gold'],font=('Segoe UI',9,'bold'))
        s.configure('Clock.TLabel',foreground=p['text'],font=('Consolas',20,'bold'))
        s.configure('Live.TLabel',foreground=p['green'],font=('Segoe UI',10,'bold'))
        s.configure('Quiet.TLabel',foreground=p['muted'],font=('Segoe UI',10))
        s.configure('Gold.CardTitle.TLabel',background=p['panel'],foreground=p['gold'],font=('Segoe UI',14,'bold'))
        s.configure('SidebarCaption.TLabel',background=p['field'],foreground=p['muted'],font=('Segoe UI',9,'bold'))
        s.configure('Nav.TButton',background=p['field'],foreground=p['muted'],anchor='w',padding=(13,10),borderwidth=0,relief='flat')
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
        s.configure('Treeview',background=p['panel'],fieldbackground=p['panel'],foreground=p['text'],rowheight=34,borderwidth=0,relief='flat')
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
        if isinstance(widget,(RateTrend,ProgressRing,PrestigeMark)):widget.redraw()
        for child in widget.winfo_children():self.restyle(child)

class Dashboard(ttk.Frame):
    def __init__(self,parent,with_eta=False):
        super().__init__(parent)
        self.values=[];self.totals=[];self.labels=[];self.with_eta=with_eta
        specs=[('ADENA / HR','Gold'),('EXP / HR','Green'),('KILLS / HR','Blue')]
        if with_eta:specs.append(('NEXT LEVEL','Blue'))
        for i,(label,colour) in enumerate(specs):
            self.columnconfigure(i,weight=1,uniform='metrics')
            card=ttk.Frame(self,style='Card.TFrame',padding=(16,12))
            card.grid(row=0,column=i,sticky='nsew',padx=(0 if i==0 else 5,0 if i==len(specs)-1 else 5))
            value=tk.StringVar(master=self,value='—');total=tk.StringVar(master=self,value='Total 0')
            self.values.append(value);self.totals.append(total)
            label_var=tk.StringVar(master=self,value=label);self.labels.append(label_var)
            ttk.Label(card,textvariable=label_var,style='CardLabel.TLabel').pack(anchor='w')
            ttk.Label(card,textvariable=value,style=colour+'.Metric.TLabel').pack(anchor='w',pady=(3,0))
            footer=ttk.Label(card,textvariable=total,style='CardTotal.TLabel',wraplength=170);footer.pack(fill='x')
            footer.bind('<Configure>',lambda e,w=footer:w.configure(wraplength=max(60,e.width-4)))
    def update_metrics(self,seconds,adena,xp,kills,cost=None,unpriced=0,eta='—',kills_left='—'):
        metrics=list(metric_values(seconds,adena,xp,kills))
        if cost is not None:
            net=adena-float(cost);metrics[0]=(rate(net,seconds),f'Gross {adena:,} · known costs {cost:,.0f}')
        self.labels[0].set(('NET ADENA / HR*' if unpriced else 'NET ADENA / HR') if cost is not None else 'ADENA / HR')
        if self.with_eta:metrics.append((eta,'Kills left: '+kills_left))
        for v,t,(number,total) in zip(self.values,self.totals,metrics):
            if v.get()!=number:v.set(number)
            if t.get()!=total:t.set(total)

class PrestigeMark(tk.Canvas):
    def __init__(self,parent,appearance):
        super().__init__(parent,width=38,height=38,highlightthickness=0,borderwidth=0)
        self.appearance=appearance;self.bind('<Configure>',lambda e:self.redraw());self.redraw()
    def redraw(self):
        p=self.appearance.palette;self.configure(background=p['field']);self.delete('all')
        self.create_polygon(19,2,36,19,19,36,2,19,fill='',outline=p['gold'],width=1)
        self.create_polygon(19,7,31,19,19,31,7,19,fill='',outline=p['border'])
        self.create_line(14,11,14,26,25,26,fill=p['gold'],width=3)

class ProgressRing(ttk.Frame):
    def __init__(self,parent,appearance):
        super().__init__(parent,style='Card.TFrame',padding=12)
        self.appearance=appearance;self.data=('—','—','—','—')
        ttk.Label(self,text='Character progression',style='CardTitle.TLabel').pack(anchor='w')
        self.canvas=tk.Canvas(self,height=174,highlightthickness=0,borderwidth=0)
        self.canvas.pack(fill='x',expand=True);self.canvas.bind('<Configure>',lambda e:self.redraw())
        self.sp=tk.StringVar(master=self,value='Session SP   —');self.eta=tk.StringVar(master=self,value='Next level   —')
        ttk.Label(self,textvariable=self.sp,style='CardBody.TLabel').pack(fill='x')
        ttk.Label(self,textvariable=self.eta,style='CardBody.TLabel').pack(fill='x',pady=(4,0))
    def update_metrics(self,level,percent,sp,eta):
        data=(str(level),str(percent),str(sp),str(eta))
        if data==self.data:return
        self.data=data;self.sp.set('Session SP   '+data[2]);self.eta.set('Next level   '+data[3]);self.redraw()
    def redraw(self):
        p=self.appearance.palette;cv=self.canvas;cv.configure(background=p['panel']);cv.delete('all')
        w,h=cv.winfo_width(),cv.winfo_height()
        if w<40 or h<40:return
        x,y=w/2,h/2;r=min(w,h)*.36;level,percent,_,_=self.data
        rect=(x-r,y-r,x+r,y+r)
        cv.create_oval(*rect,outline=p['border'],width=7)
        try:f=max(0,min(100,float(percent.rstrip('*').rstrip('%'))))
        except ValueError:f=0
        if f>=100:cv.create_oval(*rect,outline=p['gold'],width=7)
        elif f>0:cv.create_arc(*rect,start=90,extent=-f*3.6,style='arc',outline=p['gold'],width=7)
        cv.create_text(x,y-26,text='LEVEL',fill=p['muted'],font=('Segoe UI',9,'bold'))
        cv.create_text(x,y+1,text=level,fill=p['text'],font=('Segoe UI',30,'bold'))
        cv.create_text(x,y+34,text=percent+' XP' if percent!='—' else 'Not calibrated',fill=p['gold'],font=('Segoe UI',10))

def trend_values(seconds,xp,adena,kills):
    return tuple(n*3600/seconds for n in (xp,adena,kills)) if seconds>0 else (0,0,0)

class RateTrend(ttk.Frame):
    """Three live session-average rate series, sampled in active time."""
    def __init__(self,parent,appearance):
        super().__init__(parent,style='Card.TFrame',padding=12)
        self.appearance=appearance;self.key=None;self.points=[];self.series=0
        header=ttk.Frame(self,style='Card.TFrame');header.pack(fill='x')
        ttk.Label(header,text='Performance',style='CardTitle.TLabel').pack(side='left')
        self.buttons=[]
        for i,label in enumerate(('XP','Adena','Kills')):
            b=ttk.Button(header,text=label,style='Compact.TButton',command=lambda n=i:self.select(n));b.pack(side='right',padx=2);self.buttons.append(b)
        self.subtitle=tk.StringVar(master=self)
        ttk.Label(self,textvariable=self.subtitle,style='CardLabel.TLabel').pack(anchor='w',pady=(2,3))
        self.canvas=tk.Canvas(self,height=194,highlightthickness=0,borderwidth=0)
        self.canvas.pack(fill='both',expand=True);self.canvas.bind('<Configure>',lambda e:self.redraw());self.select(0)
    def select(self,i):
        self.series=i
        for j,b in enumerate(self.buttons):b.configure(style='Primary.TButton' if i==j else 'Compact.TButton')
        self.subtitle.set(('Experience','Gross Adena','Estimated kills')[i]+' / hour · session average · last 60 active minutes')
        self.redraw()
    def sample(self,key,seconds,xp,running,adena=0,kills=0):
        changed=key!=self.key or bool(self.points and seconds<self.points[-1][0])
        if changed:self.key=key;self.points=[]
        if running and seconds>=1 and (not self.points or seconds-self.points[-1][0]>=30):
            self.points.append((seconds,*trend_values(seconds,xp,adena,kills)))
            self.points=[p for p in self.points if p[0]>=seconds-3600];changed=True
        if changed:self.redraw()
    def redraw(self):
        p=self.appearance.palette;cv=self.canvas;cv.configure(background=p['panel']);cv.delete('all')
        w=max(1,cv.winfo_width());h=max(1,cv.winfo_height())
        if w<100 or h<60:return
        if len(self.points)<2:
            cv.create_text(w/2,h/2,text='Live trend appears after 30 active seconds.',fill=p['muted'],font=('Segoe UI',10));return
        l,t,r,b=58,10,w-12,h-24
        series=[(row[0],row[self.series+1]) for row in self.points]
        colour=p[('green','gold','blue')[self.series]]
        max_y=max(1,max(v for _,v in series));lo=series[0][0];hi=series[-1][0]
        for i in range(5):
            y=b-(b-t)*i/4;value=max_y*i/4
            cv.create_line(l,y,r,y,fill=p['border'],dash=(3,4))
            cv.create_text(l-6,y,text=f'{value:,.0f}',anchor='e',fill=p['muted'],font=('Segoe UI',9))
        xy=[v for x,y in series for v in (l+(r-l)*(x-lo)/max(1,hi-lo),b-(b-t)*y/max_y)]
        rgb=lambda c:tuple(int(c[i:i+2],16) for i in (1,3,5))
        shade='#%02x%02x%02x'%tuple(round(a*.12+b*.88) for a,b in zip(rgb(colour),rgb(p['panel'])))
        cv.create_polygon(l,b,*xy,r,b,fill=shade,outline='')
        cv.create_line(*xy,fill=colour,width=2)
        x,y=xy[-2:];cv.create_oval(x-3,y-3,x+3,y+3,fill=colour,outline=p['panel'])
        cv.create_text(l,b+13,text=f'{lo/60:.1f}m',anchor='w',fill=p['muted'],font=('Segoe UI',9))
        cv.create_text(r,b+13,text=f'{hi/60:.1f}m',anchor='e',fill=p['muted'],font=('Segoe UI',9))
