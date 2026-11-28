"""Independent, passive player status calibration and HUD settings."""
import tkinter as tk
from tkinter import ttk,messagebox
from decimal import Decimal,InvalidOperation
import threading,time,queue
from PIL import Image,ImageTk
from leveling import Progress,load_status,save_status,binding_for,read_number,eta,XP
from hud_layout import WIDGETS,PRESETS,SIZES,clean,load,save,geometry
from hud import rate_text

class PlayerStatus:
    def __init__(self,app):
        self.app=app;self.config=load_status();self.progress=Progress()
        self.results=queue.Queue();self.busy=False;self.generation=0;self.next_read=0
        self.source=tk.StringVar(value='Calibrate player status or enter manually.')
        self.summary=tk.StringVar(value='Player progress: not calibrated')
        self.last_run=None;self.last_xp=0;self.last_binding=None
        self.calibration_results=queue.Queue();self.calibration_preview={}
        self.percent_var=tk.DoubleVar(value=0)
        self.details=tk.StringVar(value='')
    def build_dashboard(self,parent):
        panel=ttk.Frame(parent);panel.pack(fill='x',pady=(0,5))
        ttk.Label(panel,textvariable=self.summary,style='Section.TLabel',wraplength=870).pack(anchor='w')
        ttk.Progressbar(panel,variable=self.percent_var,maximum=100).pack(fill='x',pady=(2,0))
        ttk.Label(panel,textvariable=self.details,style='Muted.TLabel',wraplength=870).pack(anchor='w')
    def save(self):
        try:save_status(self.config)
        except OSError as e:self.source.set('Could not save: '+str(e))
    def build(self,parent):
        ttk.Label(parent,text='Player status',style='Title.TLabel').pack(anchor='w')
        ttk.Label(parent,text='Chronicle 1 XP curve • offline • cap configurable',style='Muted.TLabel').pack(anchor='w',pady=(0,8))
        self.mode=tk.StringVar(value=self.config['mode']);self.cap=tk.StringVar(value=str(self.config['cap']));self.interval=tk.StringVar(value=str(self.config['interval']))
        row=ttk.Frame(parent);row.pack(fill='x')
        for label,var,values in [('Mode',self.mode,('auto','manual')),('Level cap',self.cap,tuple(str(i) for i in range(2,76))),('Read interval (s)',self.interval,('1','2','5','10'))]:
            ttk.Label(row,text=label).pack(side='left',padx=(0,5))
            cb=ttk.Combobox(row,textvariable=var,values=values,width=8,state='readonly');cb.pack(side='left',padx=(0,16));cb.bind('<<ComboboxSelected>>',self.change)
        ttk.Label(parent,text='Automatic capture: select only the level digits and XP percentage. View or edit all bound areas while paused.',wraplength=650).pack(anchor='w',pady=(16,6))
        self.regions=tk.StringVar();self.region_labels()
        row=ttk.Frame(parent);row.pack(fill='x')
        ttk.Button(row,text='Select level digits…',command=lambda:self.calibrate('level')).pack(side='left')
        ttk.Button(row,text='Select XP %…',command=lambda:self.calibrate('percent')).pack(side='left',padx=6)
        ttk.Label(parent,textvariable=self.regions,style='Muted.TLabel').pack(anchor='w',pady=6)
        ttk.Separator(parent).pack(fill='x',pady=10)
        ttk.Label(parent,text='Manual calibration (switches to manual mode)',style='Section.TLabel').pack(anchor='w')
        row=ttk.Frame(parent);row.pack(fill='x',pady=6)
        self.level=tk.StringVar(value='');self.percent=tk.StringVar(value='')
        for name,var in [('Level',self.level),('XP %',self.percent)]:
            ttk.Label(row,text=name).pack(side='left',padx=4);ttk.Entry(row,textvariable=var,width=9).pack(side='left',padx=4)
        ttk.Button(row,text='Apply manual reading',command=self.manual).pack(side='left',padx=6)
        ttk.Label(parent,textvariable=self.source,wraplength=680).pack(anchor='w',pady=8)
        ttk.Label(parent,textvariable=self.summary,wraplength=680,style='Section.TLabel').pack(anchor='w')
    def region_labels(self):
        self.regions.set('  |  '.join(k+': '+(self.calibration_preview.get(k,'selected') if k in self.config['regions'] else 'not selected') for k in ('level','percent')))
    def change(self,*_):
        mode=self.mode.get()
        if mode!=self.config['mode']:self.progress.clear();self.generation+=1
        self.config.update(mode=mode,cap=int(self.cap.get()),interval=int(self.interval.get()));self.save()
    def manual(self):
        try:
            lv=int(self.level.get());p=Decimal(self.percent.get())
            if lv>int(self.cap.get()):raise ValueError('Above level cap')
            self.progress.manual(lv,p,self.app.totals['You','XP / SP'])
            self.last_run=self.app.run_id;self.last_xp=self.app.totals['You','XP / SP']
        except (ValueError,InvalidOperation):messagebox.showwarning('Player status','Enter a valid level and XP percentage (0–100).',parent=self.app.root);return
        self.mode.set('manual');self.config['mode']='manual';self.generation+=1;self.save()
    def calibrate(self,kind):
        self.app.select(kind)
    def protected(self):
        if self.app.target and self.config['binding']==binding_for(self.app.target):return tuple(self.config['regions'].values())
        return ()
    def tick(self,finished=False):
        a=self.app;p=self.progress;now=time.monotonic();xp=a.totals['You','XP / SP'] if a.running or a.pending or finished else self.last_xp
        binding=binding_for(a.target) if a.target else None
        if self.config['mode']=='auto' and binding!=self.last_binding:
            p.clear();self.generation+=1;self.last_binding=binding
        try:
            while True:
                binding,kind,region,value=self.calibration_results.get_nowait()
                if binding==self.config['binding'] and self.config['regions'].get(kind)==region:
                    self.calibration_preview[kind]=('unreadable — reselect' if value is None else str(value)+('%' if kind=='percent' else ''))
                    self.region_labels()
        except queue.Empty:pass
        if self.config['mode']=='manual':
            if self.last_run!=a.run_id:
                p.rebase(self.last_xp,self.config['cap']);self.last_run=a.run_id;self.last_xp=0
            if a.running or a.pending or finished:p.advance(xp,self.config['cap']);self.last_xp=xp
        try:
            while True:
                gen,level,percent=self.results.get_nowait();self.busy=False
                if gen==self.generation and self.config['mode']=='auto':p.observe(level,percent,self.config['cap'])
        except queue.Empty:pass
        if self.config['mode']=='auto' and a.running and not a.pause_gate.snapshot()[0] and not a.selecting and not self.busy and now>=self.next_read and len(self.protected())==2:
            self.busy=True;self.next_read=now+self.config['interval'];target=a.target;regions=dict(self.config['regions']);gen=self.generation
            def work():
                level=percent=None
                try:
                    import mss
                    from window_focus import Windows,capture_region
                    api=Windows()
                    with mss.mss() as screen:
                        images={}
                        for k,r in regions.items():
                            rect,_=capture_region(api,target,r,screen.monitors[0])
                            if not rect:break
                            shot=screen.grab(rect)
                            if capture_region(api,target,r,screen.monitors[0])[0]!=rect:break
                            images[k]=Image.frombytes('RGB',(rect['width'],rect['height']),shot.rgb)
                        if len(images)==2:
                            level=read_number(images['level'],'level');percent=read_number(images['percent'],'percent')
                except Exception:pass
                self.results.put((gen,level,percent))
            threading.Thread(target=work,daemon=True).start()
        stale=self.config['mode']=='auto' and (p.seen is None or now-p.seen>max(15,self.config['interval']*4))
        label,remaining=eta(p.level,p.percent,a.totals['You','XP / SP'],a.active_seconds,self.config['cap']) if p.level is not None else ('—',None)
        flag='*' if stale and p.level is not None else ''
        self.widgets={'eta':('NEXT LVL',label+flag),'level':('LEVEL',str(p.level)+flag if p.level is not None else '—'),'progress':('EXP %',f'{p.percent:.2f}%'+flag if p.percent is not None else '—')}
        self.source.set(('Manual: chat XP estimate; recalibrate after death or character change.' if self.config['mode']=='manual' else 'Automatic: last reading stale' if stale else 'Automatic: verified reading'))
        self.summary.set(f'Level {p.level}{flag}  •  {p.percent:.2f}%  •  Next level: {label}{flag}  •  Remaining XP: {remaining:,}' if p.level is not None else 'Player progress: not calibrated')
        self.percent_var.set(float(p.percent) if p.percent is not None else 0)
        self.details.set(f'XP in level: {round(XP[p.level-1]*p.percent/100):,} / {XP[p.level-1]:,}  |  XP/hr: {rate_text(a.totals["You","XP / SP"],a.active_seconds)}  |  {self.source.get()}' if p.level is not None else 'Configure level and XP regions in Settings → Player status.')
