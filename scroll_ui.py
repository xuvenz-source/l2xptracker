"""Scrollable content pages; leave native table/text wheel behaviour intact."""
import tkinter as tk
from tkinter import ttk

class ScrollPage(ttk.Frame):
    def __init__(self,parent,padding=0):
        super().__init__(parent)
        self.canvas=tk.Canvas(self,highlightthickness=0,borderwidth=0,takefocus=0)
        self.bar=ttk.Scrollbar(self,orient='vertical',command=self.canvas.yview)
        self.bar.pack(side='right',fill='y');self.canvas.pack(side='left',fill='both',expand=True)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.content=ttk.Frame(self.canvas,padding=padding)
        self.window=self.canvas.create_window(0,0,window=self.content,anchor='nw')
        self.content.bind('<Configure>',self.sync)
        self.canvas.bind('<Configure>',self.resize)
        self.canvas.configure(background=ttk.Style(self).lookup('TFrame','background'))
        top=self.winfo_toplevel()
        if not getattr(top,'_scroll_page_wheel',False):
            top._scroll_page_wheel=True
            for event in ('<MouseWheel>','<Button-4>','<Button-5>'):
                top.bind(event,self.dispatch_wheel,add='+')
    def sync(self,event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    def resize(self,event):
        self.canvas.itemconfigure(self.window,width=event.width);self.sync()
    @staticmethod
    def dispatch_wheel(event):
        w=event.widget
        if isinstance(w,(tk.Text,tk.Listbox,ttk.Treeview,ttk.Combobox,ttk.Scale,tk.Scale)):return
        while w is not None:
            if isinstance(w,ScrollPage):
                n=getattr(event,'num',0)
                delta=-1 if n==4 else 1 if n==5 else -int(event.delta/120) or (-1 if event.delta>0 else 1)
                w.canvas.yview_scroll(delta*3,'units');return 'break'
            w=getattr(w,'master',None)

def table_scroll(parent,tree,horizontal=True):
    parent.rowconfigure(0,weight=1);parent.columnconfigure(0,weight=1)
    tree.grid(row=0,column=0,sticky='nsew')
    y=ttk.Scrollbar(parent,orient='vertical',command=tree.yview);y.grid(row=0,column=1,sticky='ns')
    tree.configure(yscrollcommand=y.set)
    if horizontal:
        x=ttk.Scrollbar(parent,orient='horizontal',command=tree.xview);x.grid(row=1,column=0,sticky='ew');tree.configure(xscrollcommand=x.set)
    return y
