"""Read-only merged reports, with original session reopening for manual OCR review."""
import csv, json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from pathlib import Path
from history import duration,rate,history_forest
from party import display_rows as party_rows, summary_text as party_summary

class HistoryWindow:
    def __init__(self,app,parent=None):
        self.app=app;self.archive=app.archive;self.embedded=parent is not None;self.win=parent if self.embedded else tk.Toplevel(app.root)
        if not self.embedded:self.win.title('Farming session history');self.win.geometry('1110x710');self.win.minsize(950,600)
        ttk.Label(self.win,text='Session history',style='Title.TLabel',padding=(12,10,12,0)).pack(anchor='w')
        ttk.Label(self.win,text='Merge selected sessions into a collapsed parent. Expand its arrow to view originals or nested reports. Ctrl/Shift selects multiple rows.',padding=10).pack(fill='x')
        frame=ttk.Frame(self.win);frame.pack(fill='both',expand=True,padx=10)
        cols=[('kind','Type',90),('start','Started',145),('active','Active time',80),('xp','EXP/hr',100),('ad','Adena/hr',100),('kills','Kills/hr',85),('review','Reviews',65)]
        self.tree=ttk.Treeview(frame,columns=[c[0] for c in cols],show='tree headings',selectmode='extended',height=10)
        self.tree.heading('#0',text='Session name');self.tree.column('#0',width=270,minwidth=180,stretch=True)
        self.row_records={}
        for c,t,w in cols:self.tree.heading(c,text=t);self.tree.column(c,width=w,minwidth=50)
        scroll=ttk.Scrollbar(frame,orient='vertical',command=self.tree.yview);self.tree.config(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');self.tree.pack(fill='both',expand=True)
        buttons=ttk.Frame(self.win,padding=10);buttons.pack(fill='x')
        for title,cmd in [('Refresh',self.refresh),('Rename…',self.rename),('Merge selected…',self.merge),('Open original for review',self.reopen),('Export selected CSV',self.export)]:ttk.Button(buttons,text=title,command=cmd).pack(side='left',padx=3)
        self.details=tk.StringVar(value='Select a saved session.');ttk.Label(self.win,textvariable=self.details,padding=10,wraplength=1020).pack(fill='x')
        f=ttk.Frame(self.win);f.pack(fill='both',expand=True,padx=10,pady=(0,10));self.loot=ttk.Treeview(f,columns=('who','item','qty'),show='headings',height=8)
        for c,t,w in [('who','Player',160),('item','Item',500),('qty','Quantity',140)]:self.loot.heading(c,text=t);self.loot.column(c,width=w)
        sb=ttk.Scrollbar(f,orient='vertical',command=self.loot.yview);self.loot.config(yscrollcommand=sb.set);sb.pack(side='right',fill='y');self.loot.pack(fill='both',expand=True)
        self.tree.bind('<<TreeviewSelect>>',self.detail);self.refresh()
        if hasattr(app,'appearance'):app.appearance.restyle(self.win)
    def refresh(self,select=None):
        try:
            self.records=self.archive.records(); self.summaries={i:self.archive.summary(i,self.records) for i in self.records}
        except Exception as e:messagebox.showerror('History',str(e),parent=self.win);return
        old_paths=tuple(self.tree.selection())
        old_records=[self.row_records.get(i) for i in old_paths]
        opened={i for i in self.row_records if self.tree.exists(i) and self.tree.item(i,'open')}
        self.tree.delete(*self.tree.get_children());self.row_records={}
        preferred={}
        for path in history_forest(self.records,self.summaries):
            i=path[-1];s=self.summaries[i];t=s['totals']
            row=json.dumps(path,separators=(',',':'));parent=json.dumps(path[:-1],separators=(',',':')) if len(path)>1 else ''
            typ=f"Group ({len(s['sources'])})" if s['kind']=='merged' else ('Original' if s['complete'] else 'Checkpoint')
            self.tree.insert(parent,'end',iid=row,text=s['name'],open=row in opened,
                values=(typ,s['start'].replace('T',' '),duration(s['seconds']),rate(t['You','XP / SP'],s['seconds']),rate(t['You','Adena'],s['seconds']),rate(s['kills'],s['seconds']),s['pending']))
            self.row_records[row]=i;preferred.setdefault(i,row)
        if select is None:
            selected=[r for r in old_paths if r in self.row_records]
            selected.extend(preferred[i] for i in old_records if i in preferred and not any(self.row_records[r]==i for r in selected))
        else:selected=[preferred[i] for i in dict.fromkeys(select) if i in preferred]
        if selected:
            self.tree.selection_set(*selected);self.tree.focus(selected[0]);self.tree.see(selected[0])
        self.detail()
    def selected_records(self):
        return list(dict.fromkeys(self.row_records[r] for r in self.tree.selection() if r in self.row_records))
    def detail(self,*_):
        ids=self.selected_records();self.loot.delete(*self.loot.get_children())
        if len(ids)!=1:self.details.set(f'{len(ids)} selected. Select one to inspect loot, or merge two or more.');return
        s=self.summaries[ids[0]];t=s['totals']
        self.details.set(f"{s['name']}  |  {len(s['sources'])} original session(s)  |  Active {duration(s['seconds'])}  |  EXP {t['You','XP / SP']:,}  |  SP {t['You','SP']:,}  |  Adena {t['You','Adena']:,}\nPending reviews: {s['pending']}  |  Capture/OCR warnings: {s['gaps']}"+('\nExpand the group above to inspect individual sessions.' if s['kind']=='merged' else ''))
        self.details.set(self.details.get()+f"\nKills: {s['kills']:,} ({rate(s['kills'],s['seconds'])}/h; XP events)")
        for (who,item),q in sorted(t.items()):
            if item not in ('XP / SP','SP'):self.loot.insert('','end',values=(who,item,f'{q:,}'))
        for row in party_rows(s['party']):self.loot.insert('','end',values=row)
        extra=party_summary(s['party'])
        if extra:self.details.set(self.details.get()+'\n'+extra)
    def single(self):
        ids=self.selected_records()
        if len(ids)!=1:messagebox.showinfo('History','Select exactly one entry.',parent=self.win);return None
        return ids[0]
    def rename(self):
        i=self.single()
        if not i:return
        n=simpledialog.askstring('Rename session','Session name:',initialvalue=self.records[i]['name'],parent=self.win)
        if n is None:return
        try:self.archive.rename(i,n);self.refresh([i])
        except Exception as e:messagebox.showerror('Rename',str(e),parent=self.win)
    def merge(self):
        ids=self.selected_records()
        if len(ids)<2:messagebox.showinfo('Merge','Select at least two entries with Ctrl or Shift.',parent=self.win);return
        n=simpledialog.askstring('Merge sessions','Name the parent session:',parent=self.win)
        if n is None:return
        try:i=self.archive.merge(ids,n);self.refresh([i])
        except Exception as e:messagebox.showerror('Merge',str(e),parent=self.win)
    def reopen(self):
        i=self.single()
        if not i:return
        if self.records[i]['kind']!='original':messagebox.showinfo('Review','Expand the group and select an original session to correct reviews. Parent totals update automatically.',parent=self.win);return
        if self.app.restore_session(i):
            if not self.embedded:self.win.destroy()
            self.app.open_reviews()
    def export(self):
        i=self.single()
        if not i:return
        s=self.archive.summary(i);path=filedialog.asksaveasfilename(parent=self.win,defaultextension='.csv',filetypes=[('CSV','*.csv')],initialfile='l2-history.csv')
        if not path:return
        try:
            with open(path,'w',newline='',encoding='utf-8-sig') as f:
                w=csv.writer(f);w.writerow(['timestamp','type','player','item','quantity_or_xp','sp','raw_text']);w.writerows(s['events'])
            with open(str(Path(path).with_suffix(''))+'-summary.csv','w',newline='',encoding='utf-8-sig') as f:
                w=csv.writer(f);t=s['totals'];w.writerow(['name','active_seconds','xp','sp','adena','xp_per_hour','adena_per_hour','kills','kills_per_hour','pending_reviews']);w.writerow([s['name'],s['seconds'],t['You','XP / SP'],t['You','SP'],t['You','Adena'],rate(t['You','XP / SP'],s['seconds']),rate(t['You','Adena'],s['seconds']),s['kills'],rate(s['kills'],s['seconds']),s['pending']])
            messagebox.showinfo('Export','Events and summary exported.',parent=self.win)
        except Exception as e:messagebox.showerror('Export',str(e),parent=self.win)
