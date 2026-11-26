"""Party configuration and reusable local presets."""
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from party import roster
from party_presets import load_presets,save_preset,rename_preset,delete_preset

class PartySetup:
    def __init__(self,app,parent=None):
        self.app=app;self.embedded=parent is not None
        win=self.win=parent if self.embedded else tk.Toplevel(app.root)
        if not self.embedded:
            win.title('Party setup');win.transient(app.root);win.geometry('650x440');win.minsize(610,420)
        content=ttk.Frame(win,padding=18);content.pack(fill='both',expand=True)
        ttk.Label(content,text='Party setup',style='Title.TLabel').pack(anchor='w')
        ttk.Label(content,text='Choose a saved party or enter the other character names for your next session.',style='Muted.TLabel',wraplength=570).pack(anchor='w',pady=(4,14))
        ttk.Label(content,text='Saved presets',style='Section.TLabel').pack(anchor='w')
        row=ttk.Frame(content);row.pack(fill='x',pady=(6,4))
        self.selected=tk.StringVar(master=win)
        self.combo=ttk.Combobox(row,textvariable=self.selected,state='readonly')
        self.combo.pack(side='left',fill='x',expand=True)
        self.combo.bind('<<ComboboxSelected>>',lambda _:self.load_selected())
        ttk.Button(row,text='Load',command=self.load_selected).pack(side='left',padx=(8,0))
        manage=ttk.Frame(content);manage.pack(fill='x',pady=(0,10))
        ttk.Button(manage,text='Save as new…',command=self.save_new).pack(side='left')
        self.update_btn=ttk.Button(manage,text='Update preset',command=self.update_selected);self.update_btn.pack(side='left',padx=6)
        self.rename_btn=ttk.Button(manage,text='Rename…',command=self.rename_selected);self.rename_btn.pack(side='left')
        self.delete_btn=ttk.Button(manage,text='Delete…',command=self.delete_selected,style='Danger.TButton');self.delete_btn.pack(side='right')
        ttk.Separator(content).pack(fill='x',pady=6)
        ttk.Label(content,text='Other party members',style='Section.TLabel').pack(anchor='w',pady=(6,4))
        self.members=tk.StringVar(master=win,value=', '.join(app.next_party_members))
        entry=ttk.Entry(content,textvariable=self.members);entry.pack(fill='x')
        ttk.Label(content,text='Comma-separated character names, up to 8. Do not include yourself. Adena estimates assume equal shares.',style='Muted.TLabel',wraplength=570).pack(anchor='w',pady=(5,8))
        self.feedback=tk.StringVar(master=win)
        ttk.Label(content,textvariable=self.feedback,style='Muted.TLabel',wraplength=570).pack(anchor='w')
        actions=ttk.Frame(content);actions.pack(side='bottom',fill='x',pady=(10,0))
        ttk.Button(actions,text='Solo / clear',command=self.clear).pack(side='left')
        ttk.Button(actions,text='Cancel',command=self.cancel).pack(side='right')
        ttk.Button(actions,text='Use party',command=self.apply,style='Primary.TButton').pack(side='right',padx=8)
        self.refresh()
        app.appearance.restyle(win)
        if not self.embedded:
            win.bind('<Escape>',lambda _:self.cancel());win.bind('<Return>',lambda _:self.apply());win.grab_set();entry.focus_set()
    def refresh(self,selection=''):
        self.presets=load_presets()
        self.combo.configure(values=list(self.presets))
        self.selected.set(selection if selection in self.presets else '')
        self.controls()
    def controls(self):
        state='normal' if self.selected.get() in self.presets else 'disabled'
        for button in (self.update_btn,self.rename_btn,self.delete_btn):button.configure(state=state)
    def error(self,e):
        messagebox.showwarning('Party presets',str(e),parent=self.win)
    def load_selected(self):
        name=self.selected.get()
        self.controls()
        if name in self.presets:
            self.members.set(', '.join(self.presets[name]))
            self.feedback.set(f'Loaded {name}. Choose Use party to apply to the next session.')
    def save_new(self):
        try:members=roster(self.members.get())
        except ValueError as e:self.error(e);return
        name=simpledialog.askstring('Save party preset','Preset name:',parent=self.win)
        if name is None:return
        try:name=save_preset(name,members)
        except (ValueError,OSError) as e:self.error(e);return
        self.refresh(name);self.feedback.set(f'Saved {name}.')
    def update_selected(self):
        name=self.selected.get()
        if name not in self.presets:return
        try:members=roster(self.members.get())
        except ValueError as e:self.error(e);return
        if not messagebox.askyesno('Update preset',f'Replace the saved members in {name}? Existing sessions will not change.',parent=self.win):return
        try:save_preset(name,members,replace=True)
        except (ValueError,OSError) as e:self.error(e);return
        self.refresh(name);self.feedback.set(f'Updated {name}.')
    def rename_selected(self):
        old=self.selected.get()
        if old not in self.presets:return
        name=simpledialog.askstring('Rename party preset','New name:',initialvalue=old,parent=self.win)
        if name is None:return
        try:name=rename_preset(old,name)
        except (ValueError,OSError) as e:self.error(e);return
        self.refresh(name);self.feedback.set(f'Renamed to {name}.')
    def delete_selected(self):
        name=self.selected.get()
        if name not in self.presets:return
        if not messagebox.askyesno('Delete preset',f'Delete {name}? Recorded sessions will not change.',parent=self.win):return
        try:delete_preset(name)
        except (ValueError,OSError) as e:self.error(e);return
        self.refresh();self.feedback.set(f'Deleted {name}. Current entry is unchanged.')
    def clear(self):
        self.selected.set('');self.members.set('');self.controls()
        self.feedback.set('Solo selected. Choose Use party to apply.')
    def apply(self):
        if self.app.running or self.app.pending or self.app.update_busy:
            self.error('Stop tracking before changing the next party.');return
        try:members=roster(self.members.get())
        except ValueError as e:self.error(e);return
        self.app.next_party_members=list(members)
        self.app.party_status.set('Next session: '+(', '.join(members) or 'solo / no estimates'))
        if self.embedded:self.app.navigate('dashboard')
        else:self.win.destroy()
    def cancel(self):
        if self.embedded:
            self.members.set(', '.join(self.app.next_party_members));self.selected.set('');self.controls();self.app.navigate('dashboard')
        else:self.win.destroy()
