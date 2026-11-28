"""Monster library and bulk kill identification review."""
import tkinter as tk
from tkinter import ttk,messagebox
from copy import deepcopy
from monster_library import expected,counts,assign,learn,save,reward

class MonsterLibraryWindow:
    def __init__(self,app):
        self.app=app;self.win=tk.Toplevel(app.root);self.win.title('Monster Library');self.win.geometry('850x520');self.win.minsize(650,420)
        self.full=tk.BooleanVar(value=app.monster_library['full_solo'])
        self.status=tk.StringVar()
        ttk.Label(self.win,text='Monster Library',style='Title.TLabel',padding=10).pack(anchor='w')
        ttk.Label(self.win,text='Select monsters you are farming (Ctrl / Shift for multiple). Apply selection to change the active roster. Import once; reuse later.',wraplength=780,padding=8).pack(anchor='w')
        panel=ttk.Frame(self.win,padding=8);panel.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(panel,columns=('name','base','expected','targets'),show='headings',selectmode='extended')
        for k,title,w in [('name','Monster',220),('base','Base XP / SP',135),('expected','Predicted reward',145),('targets','Desired drops',120)]:
            self.tree.heading(k,text=title);self.tree.column(k,width=w)
        self.tree.pack(side='left',fill='both',expand=True);sb=ttk.Scrollbar(panel,command=self.tree.yview);sb.pack(side='right',fill='y');self.tree.configure(yscrollcommand=sb.set)
        ttk.Checkbutton(self.win,text='Enable exact reward matching: solo, full stamina, normal rewards',variable=self.full).pack(anchor='w',padx=10)
        ttk.Label(self.win,text='Disable when stamina or reward conditions change. Identical signatures and unknown rewards need review.',wraplength=780,padding=8).pack(anchor='w')
        row=ttk.Frame(self.win,padding=8);row.pack(fill='x')
        ttk.Button(row,text='Import monster…',command=self.import_new).pack(side='left')
        ttk.Button(row,text='Edit selected…',command=self.edit).pack(side='left',padx=5)
        ttk.Button(row,text='Review kills…',command=app.open_monster_reviews).pack(side='left')
        ttk.Button(row,text='Apply selection',style='Primary.TButton',command=self.apply).pack(side='right')
        ttk.Label(self.win,textvariable=self.status,padding=8).pack(anchor='w')
        app.appearance.restyle(self.win);self.refresh()
    def refresh(self):
        lib=self.app.monster_library;level=self.app.monster_level()
        self.tree.delete(*self.tree.get_children())
        for k,p in lib['profiles'].items():
            pair=expected(p,level)
            self.tree.insert('','end',iid=k,values=(p['drop']['monster'],f"{p['xp']} / {p['sp']}" if p['xp'] is not None else 'Not verified',f'{pair[0]} / {pair[1]}' if pair else '—',len(p['drop']['selected'])))
        self.tree.selection_set(lib['active']);self.full.set(lib['full_solo'])
        self.status.set(f'{len(lib["active"])} active monsters · player level {level or "unknown"}')
    def apply(self):
        lib=deepcopy(self.app.monster_library);lib['active']=list(self.tree.selection());lib['full_solo']=bool(self.full.get())
        try:self.app.set_monster_library(lib)
        except OSError as e:messagebox.showerror('Monster Library',str(e),parent=self.win);return
        self.refresh()
    def import_new(self):self.win.destroy();self.app.capture_drop_window()
    def edit(self):
        ids=self.tree.selection()
        if len(ids)!=1:messagebox.showinfo('Monster Library','Select one monster to edit.',parent=self.win);return
        self.win.destroy();self.app.edit_monster(ids[0])

class KillReviewWindow:
    def __init__(self,app):
        self.app=app;self.session=app.session_id;self.win=tk.Toplevel(app.root);self.win.title('Monster identification reviews');self.win.geometry('880x580');self.win.minsize(650,420)
        self.all=tk.BooleanVar(value=False);self.learn=tk.BooleanVar(value=False);self.status=tk.StringVar()
        ttk.Label(self.win,text='Monster identification',style='Title.TLabel',padding=10).pack(anchor='w')
        ttk.Label(self.win,text='XP/SP is already counted. Select one or multiple kills and assign a monster. Shared damage: leave learning unchecked.',wraplength=820,padding=8).pack(anchor='w')
        row=ttk.Frame(self.win,padding=8);row.pack(fill='x')
        ttk.Checkbutton(row,text='Include identified kills (correct mistakes)',variable=self.all,command=self.refresh).pack(side='left')
        ttk.Button(row,text='Refresh',command=self.refresh).pack(side='left',padx=6)
        ttk.Button(row,text='Select matching rewards',command=self.matching).pack(side='left')
        panel=ttk.Frame(self.win,padding=8);panel.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(panel,columns=('time','xp','sp','level','status','suggestions'),show='headings',selectmode='extended')
        for k,title,w in [('time','Captured',175),('xp','XP',75),('sp','SP',60),('level','Level',55),('status','Identification',170),('suggestions','Exact candidates',210)]:
            self.tree.heading(k,text=title);self.tree.column(k,width=w)
        self.tree.pack(side='left',fill='both',expand=True);sb=ttk.Scrollbar(panel,command=self.tree.yview);sb.pack(side='right',fill='y');self.tree.configure(yscrollcommand=sb.set)
        row=ttk.Frame(self.win,padding=8);row.pack(fill='x')
        ttk.Label(row,text='Assign to:').pack(side='left');self.choice=ttk.Combobox(row,state='readonly',width=32);self.choice.pack(side='left',padx=5)
        ttk.Button(row,text='Assign selected',style='Primary.TButton',command=self.apply).pack(side='left')
        ttk.Button(row,text='Mark unknown',command=lambda:self.apply(True)).pack(side='left',padx=5)
        ttk.Checkbutton(self.win,text='Remember as normal reward signature (not shared damage)',variable=self.learn).pack(anchor='w',padx=8)
        ttk.Label(self.win,textvariable=self.status,padding=8).pack(anchor='w')
        app.appearance.restyle(self.win);self.refresh()
    def valid(self):
        if self.session!=self.app.session_id:
            self.status.set('Session changed. Close and reopen this review window.');return False
        return True
    def refresh(self):
        if not self.valid():return
        a=self.app;self.tree.delete(*self.tree.get_children())
        self.profiles=list(a.monster_library['profiles'].values());self.choice['values']=[p['drop']['monster'] for p in self.profiles]
        for i,e in enumerate(a.events):
            if not reward(e):continue
            r=a.monster_kills.get(str(i),{})
            if r.get('id') and not self.all.get():continue
            ctx=r.get('context',{});matches=[p['name'] for p in ctx.get('candidates',[]) if list(e[4:6]) in p['pairs']]
            self.tree.insert('','end',iid=str(i),values=(e[0],e[4] if e[4] is not None else '?',e[5] if e[5] is not None else '?',ctx.get('level') or '?',r.get('name') or r.get('method','unknown'),', '.join(matches)))
        self.status.set(f'{len(self.tree.get_children())} displayed kills. Review does not modify XP, SP or overall kills.')
    def matching(self):
        ids=self.tree.selection()
        if not ids:return
        e=self.app.events[int(ids[0])]
        self.tree.selection_set([i for i in self.tree.get_children() if self.app.events[int(i)][4:6]==e[4:6]])
    def apply(self,unknown=False):
        if not self.valid():return
        ids=[int(i) for i in self.tree.selection()]
        if not ids:return
        index=self.choice.current()
        if not unknown and index<0:self.status.set('Choose a monster first.');return
        p=None if unknown else self.profiles[index]
        a=self.app;records=deepcopy(a.monster_kills);lib=deepcopy(a.monster_library)
        try:
            assign(records,a.events,ids,p)
            if p and self.learn.get():
                if not messagebox.askyesno('Learn signature','Confirm these are normal full-stamina solo rewards, not shared damage or another reward modifier.',parent=self.win):return
                learn(lib,records,ids,p);a.set_monster_library(lib)
        except (ValueError,OSError) as e:self.status.set(str(e));return
        a.monster_kills=records;a.monster_counts_cache=None;a.update_drop_targets();a.save_session(quiet=True)
        self.learn.set(False);self.refresh()
