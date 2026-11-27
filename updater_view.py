"""Small self-contained visual updater shared by launcher, tracker and helper."""
import tkinter as tk
from tkinter import ttk

def download_display(received,total):
    mib=1024**2
    if type(total) is int and total>0:
        pct=min(100,max(0,received*100/total))
        return pct,f'{pct:.0f}%  ·  {received/mib:.1f} / {total/mib:.1f} MiB'
    return None,f'{received/mib:.1f} MiB downloaded'

class UpdateView(ttk.Frame):
    def __init__(self,parent,version):
        super().__init__(parent,padding=24)
        self.style=ttk.Style(parent);self.style.theme_use('clam')
        self.style.configure('Update.TFrame',background='#171E29')
        self.style.configure('Update.TLabel',background='#171E29',foreground='#E6EDF5',font=('Segoe UI',10))
        self.style.configure('UpdateTitle.TLabel',background='#171E29',foreground='#E6EDF5',font=('Segoe UI',18,'bold'))
        self.style.configure('UpdateMuted.TLabel',background='#171E29',foreground='#A7B4C6',font=('Segoe UI',10))
        self.style.configure('Update.Horizontal.TProgressbar',background='#57BB95',troughcolor='#283649',bordercolor='#39485A',lightcolor='#57BB95',darkcolor='#57BB95',thickness=13)
        self.configure(style='Update.TFrame')
        ttk.Label(self,text='L2 Legacy Tracker',style='UpdateTitle.TLabel').pack(anchor='w')
        self.version=tk.StringVar(value=f'Version {version}  ·  Update manager')
        ttk.Label(self,textvariable=self.version,style='UpdateMuted.TLabel').pack(anchor='w',pady=(3,20))
        self.status=tk.StringVar(value='Checking for updates…')
        ttk.Label(self,textvariable=self.status,style='Update.TLabel',wraplength=440).pack(anchor='w',fill='x')
        self.bar=ttk.Progressbar(self,style='Update.Horizontal.TProgressbar',length=440,maximum=100)
        self.bar.pack(fill='x',pady=(12,7))
        self.detail=tk.StringVar(value='')
        ttk.Label(self,textvariable=self.detail,style='UpdateMuted.TLabel',wraplength=440).pack(anchor='w',fill='x')
        self.buttons=ttk.Frame(self,style='Update.TFrame');self.buttons.pack(fill='x',pady=(16,0))
        self.mode=None
    def mode_to(self,mode):
        if self.mode==mode:return
        self.bar.stop();self.bar.configure(mode=mode,value=0);self.mode=mode
        if mode=='indeterminate':self.bar.start(12)
    def stage(self,text):
        self.status.set(text);self.detail.set('');self.mode_to('indeterminate')
    def bytes(self,received,total):
        pct,label=download_display(received,total)
        self.mode_to('determinate' if pct is not None else 'indeterminate')
        if pct is not None:self.bar.configure(value=pct)
        self.detail.set(label)
    def complete(self,text):
        self.status.set(text);self.detail.set('');self.mode_to('determinate');self.bar.configure(value=100)
    def error(self,text):
        self.status.set('Update unavailable');self.detail.set(text);self.mode_to('determinate');self.bar.configure(value=0)
    def actions(self,items):
        for child in self.buttons.winfo_children():child.destroy()
        for name,fn in items:ttk.Button(self.buttons,text=name,command=fn).pack(side='right',padx=(6,0))
    def destroy(self):
        self.bar.stop();super().destroy()
