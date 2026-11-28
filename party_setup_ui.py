"""Eleven editable slots for the other members of a twelve-person party."""
import tkinter as tk
from tkinter import ttk,messagebox
from party import roster,MAX_MEMBERS,load_party_choices
from scroll_ui import ScrollPage

class PartySetup:
    def __init__(self,app,parent=None):
        self.app=app;self.embedded=parent is not None
        win=self.win=parent if self.embedded else tk.Toplevel(app.root)
        if not self.embedded:
            win.title('Party setup');win.transient(app.root);win.geometry('640x590');win.minsize(480,400)
        header=ttk.Frame(win,padding=(12,8));header.pack(fill='x')
        ttk.Label(header,text='Party members',style='Title.TLabel').pack(anchor='w')
        ttk.Label(header,text='Choose a remembered character or type a new name. Leave unused slots blank.',wraplength=650,style='Muted.TLabel').pack(anchor='w',pady=(4,0))
        self.feedback=tk.StringVar(master=win)
        footer=ttk.Frame(win,padding=(12,8));footer.pack(side='bottom',fill='x')
        ttk.Label(footer,textvariable=self.feedback,wraplength=650,style='Muted.TLabel').pack(fill='x',pady=(0,6))
        actions=ttk.Frame(footer);actions.pack(fill='x')
        ttk.Button(actions,text='Clear all slots',command=self.clear).pack(side='left')
        ttk.Button(actions,text='Revert edits',command=self.sync).pack(side='left',padx=6)
        ttk.Button(actions,text='Apply party changes',command=self.apply,style='Primary.TButton').pack(side='right')
        self.scroll=ScrollPage(win,padding=12);self.scroll.pack(fill='both',expand=True)
        content=self.scroll.content
        content.columnconfigure(1,weight=1)
        ttk.Label(content,text='You',style='Section.TLabel').grid(row=0,column=0,sticky='w',pady=(0,8))
        ttk.Label(content,text='Always included (your character)',style='Muted.TLabel').grid(row=0,column=1,sticky='w',pady=(0,8))
        self.slots=[];self.combos=[]
        for i in range(MAX_MEMBERS):
            ttk.Label(content,text=f'Party Member {i+1}:').grid(row=i+1,column=0,sticky='w',padx=(0,12),pady=4)
            var=tk.StringVar(master=win);self.slots.append(var)
            combo=ttk.Combobox(content,textvariable=var,state='normal',width=27)
            combo.grid(row=i+1,column=1,sticky='ew',pady=4);self.combos.append(combo)
            combo.bind('<Return>',lambda _:self.apply())
            ttk.Button(content,text='Clear',style='Compact.TButton',command=lambda v=var:v.set('')).grid(row=i+1,column=2,padx=(8,0),pady=4)
        self.sync()
        app.appearance.restyle(win)
    def refresh_choices(self):
        names=load_party_choices()
        for combo in self.combos:combo.configure(values=['',*names])
    def sync(self):
        members=self.app.party_members if self.app.running else self.app.next_party_members
        for i,v in enumerate(self.slots):v.set(members[i] if i<len(members) else '')
        self.refresh_choices()
        self.feedback.set(f'{len(members)+1}/12 party members including you. Changes apply during tracking or to the next session.')
    def clear(self):
        for v in self.slots:v.set('')
        self.feedback.set('All slots cleared. Apply party changes to switch to solo.')
    def apply(self):
        try:
            values=[v.get().strip() for v in self.slots if v.get().strip()]
            if any(',' in x for x in values):raise ValueError('Enter one character name in each slot.')
            members=roster(','.join(values))
            if len(members)!=len(values):raise ValueError('Do not include yourself or duplicate a character.')
            self.app.apply_party_members(members)
        except (ValueError,OSError,RuntimeError) as e:
            messagebox.showwarning('Party members',str(e),parent=self.win);return
        self.refresh_choices()
        self.feedback.set(f'{len(members)+1}/12 party members. '+('Applied to the active session.' if self.app.running else 'Saved for your next session.'))
        if not self.embedded:self.win.destroy()
