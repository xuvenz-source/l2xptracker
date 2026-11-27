"""Grouped reports with drag-and-drop and original-session review."""
import csv, json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from pathlib import Path
from history import duration,rate,history_forest,group_drop_plan,Archive
from party import display_rows as party_rows, summary_text as party_summary

class HistoryWindow:
    def __init__(self,app,parent=None):
        self.app=app;self.archive=app.archive;self.embedded=parent is not None;self.win=parent if self.embedded else tk.Toplevel(app.root)
        if not self.embedded:self.win.title('Farming session history');self.win.geometry('1110x710');self.win.minsize(950,600)
        ttk.Label(self.win,text='Session history',style='Title.TLabel',padding=(12,10,12,0)).pack(anchor='w')
        ttk.Label(self.win,text='Drag a session onto another to merge, or onto a group to add it. Ctrl/Shift selects multiple rows. Expand groups to see their sessions.',padding=10).pack(fill='x')
        frame=ttk.Frame(self.win);frame.pack(fill='both',expand=True,padx=10)
        cols=[('kind','Type',90),('start','Started',145),('active','Active time',80),('xp','EXP/hr',100),('ad','Adena/hr',100),('kills','Kills/hr',85),('review','Reviews',65)]
        self.tree=ttk.Treeview(frame,columns=[c[0] for c in cols],show='tree headings',selectmode='extended',height=10)
        self.tree.heading('#0',text='Session name');self.tree.column('#0',width=270,minwidth=180,stretch=True)
        self.row_records={};self.drag_origin=None;self.drag_ids=[];self.dragging=False;self.drop_row=None
        for c,t,w in cols:self.tree.heading(c,text=t);self.tree.column(c,width=w,minwidth=50)
        scroll=ttk.Scrollbar(frame,orient='vertical',command=self.tree.yview);self.tree.config(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');self.tree.pack(fill='both',expand=True)
        buttons=ttk.Frame(self.win,padding=10);buttons.pack(fill='x')
        for title,cmd in [('Refresh',self.refresh),('Rename…',self.rename),('Merge selected…',self.merge),('Open original for review',self.reopen),('Export selected CSV',self.export)]:ttk.Button(buttons,text=title,command=cmd).pack(side='left',padx=3)
        self.details=tk.StringVar(value='Select a saved session.');ttk.Label(self.win,textvariable=self.details,padding=10,wraplength=1020).pack(fill='x')
        f=ttk.Frame(self.win);f.pack(fill='both',expand=True,padx=10,pady=(0,10));self.loot=ttk.Treeview(f,columns=('who','item','qty'),show='headings',height=8)
        for c,t,w in [('who','Player',160),('item','Item',500),('qty','Quantity',140)]:self.loot.heading(c,text=t);self.loot.column(c,width=w)
        sb=ttk.Scrollbar(f,orient='vertical',command=self.loot.yview);self.loot.config(yscrollcommand=sb.set);sb.pack(side='right',fill='y');self.loot.pack(fill='both',expand=True)
        self.drag_hint=tk.StringVar(value='Drag sessions to organise groups.')
        ttk.Label(self.win,textvariable=self.drag_hint,style='Muted.TLabel',padding=(10,0,10,4)).pack(fill='x',before=buttons)
        self.tree.tag_configure('drop_target',background='#365e83',foreground='#ffffff')
        self.tree.bind('<ButtonPress-1>',self.drag_start,add='+')
        self.tree.bind('<B1-Motion>',self.drag_motion)
        self.tree.bind('<ButtonRelease-1>',self.drag_end,add='+')
        self.tree.bind('<Escape>',self.cancel_drag)
        self.tree.bind('<<TreeviewSelect>>',self.detail);self.refresh()
        if hasattr(app,'appearance'):app.appearance.restyle(self.win)
    def refresh(self,select=None):
        self.cancel_drag()
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
    def drag_start(self,event):
        self.cancel_drag()
        row=self.tree.identify_row(event.y)
        if row not in self.row_records or self.tree.identify_region(event.x,event.y) not in ('tree','cell'):return
        # Let disclosure-arrow clicks and modifier selection work normally.
        if 'indicator' in self.tree.identify_element(event.x,event.y) or event.state&0x0005:return
        self.drag_origin=(event.x,event.y)
        rows=self.tree.selection() if row in self.tree.selection() else (row,)
        self.drag_ids=list(dict.fromkeys(self.row_records[r] for r in rows if r in self.row_records))
    def drop_action(self,row):
        target=self.row_records.get(row)
        if not target or target in self.drag_ids:return None
        if self.records[target]['kind']=='merged':
            try:return ('add',target) if group_drop_plan(self.records,target,self.drag_ids) else None
            except ValueError:return None
        # Don't create a new parent containing an original already included
        # in one of the dragged groups.
        sources=Archive.sources(self.drag_ids,self.records)
        if target in sources:return None
        return ('merge',target)
    def set_drop_target(self,row):
        if self.drop_row and self.tree.exists(self.drop_row):
            self.tree.item(self.drop_row,tags=tuple(t for t in self.tree.item(self.drop_row,'tags') if t!='drop_target'))
        self.drop_row=row
        if row:self.tree.item(row,tags=(*self.tree.item(row,'tags'),'drop_target'))
    def drag_motion(self,event):
        if self.drag_origin is None:return
        x,y=self.drag_origin
        if not self.dragging and max(abs(event.x-x),abs(event.y-y))<7:return
        self.dragging=True
        self.tree.configure(cursor='hand2')
        height=self.tree.winfo_height()
        if event.y<35:self.tree.yview_scroll(-1,'units')
        elif event.y>height-22:self.tree.yview_scroll(1,'units')
        row=self.tree.identify_row(event.y) if 0<=event.x<self.tree.winfo_width() and 0<=event.y<height else ''
        action=self.drop_action(row)
        self.set_drop_target(row if action else None)
        if action:
            verb='Add to' if action[0]=='add' else 'Merge with'
            self.drag_hint.set(f"{verb} {self.records[action[1]]['name']} — release to confirm.")
        else:self.drag_hint.set('Drag onto another session or a compatible group.')
        return 'break'
    def cancel_drag(self,*_):
        self.set_drop_target(None)
        self.drag_origin=None;self.drag_ids=[];self.dragging=False
        self.tree.configure(cursor='')
        self.drag_hint.set('Drag sessions to organise groups.')
    def drag_end(self,event):
        if not self.dragging:self.cancel_drag();return
        row=self.tree.identify_row(event.y) if 0<=event.x<self.tree.winfo_width() and 0<=event.y<self.tree.winfo_height() else ''
        action=self.drop_action(row);ids=list(self.drag_ids)
        self.cancel_drag()
        if not action:return 'break'
        kind,target=action
        try:
            if kind=='add':
                if self.archive.add_to_group(target,ids):self.refresh([target])
            else:
                name=simpledialog.askstring('Merge sessions','Name the parent session:',initialvalue=self.records[target]['name'],parent=self.win)
                if name is not None:
                    group=self.archive.merge([target,*ids],name);self.refresh([group])
        except Exception as e:messagebox.showerror('Merge',str(e),parent=self.win)
        return 'break'
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
