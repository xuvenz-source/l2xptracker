"""Grouped reports with drag-and-drop and original-session review."""
import csv, json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from pathlib import Path
from history import duration,rate,history_forest,group_drop_plan,Archive,folder_move_plan,folder_options,deletion_plan
from party import display_rows as party_rows, summary_text as party_summary
from history import consumables_for
from consumable_costs import cost_summary, money, write_cost_csv
from loot_values import loot_summary, unit_label, write_loot_csv
from scroll_ui import table_scroll

class FolderPicker(simpledialog.Dialog):
    def __init__(self,parent,records,title,current=''):
        self.options=folder_options(records);self.current=current
        super().__init__(parent,title)
    def body(self,master):
        ttk.Label(master,text='Choose a destination:').pack(anchor='w')
        self.list=tk.Listbox(master,width=55,height=min(12,max(4,len(self.options))),exportselection=False)
        self.list.pack(fill='both',expand=True,pady=6)
        for _,label in self.options:self.list.insert('end',label)
        index=next((i for i,(k,_) in enumerate(self.options) if k==self.current),0)
        self.list.selection_set(index);self.list.see(index)
        self.list.bind('<Double-1>',lambda e:self.ok())
        return self.list
    def validate(self):return bool(self.list.curselection())
    def apply(self):self.result=self.options[self.list.curselection()[0]][0]


class HistoryWindow:
    def __init__(self,app,parent=None):
        self.app=app;self.archive=app.archive;self.embedded=parent is not None;self.win=parent if self.embedded else tk.Toplevel(app.root)
        if not self.embedded:self.win.title('Farming session history');self.win.geometry('1110x710');self.win.minsize(950,600)
        header=ttk.Frame(self.win);header.pack(fill='x',padx=4,pady=(0,5))
        ttk.Label(header,text='Session history',style='Title.TLabel').pack(side='left')
        ttk.Button(header,text='Refresh',command=self.refresh,style='Compact.TButton').pack(side='right')
        tools=ttk.Frame(self.win);tools.pack(fill='x',pady=(0,4))
        for title,cmd in [('New section',self.new_section),('New folder',self.new_folder),('Move to…',self.move_selected),('Rename…',self.rename),('Delete…',self.delete_selected),('New logs here…',self.choose_destination)]:
            ttk.Button(tools,text=title,command=cmd,style='Compact.TButton').pack(side='left',padx=(0,5))
        self.destination=tk.StringVar(value='New sessions: History root')
        self.drag_hint=tk.StringVar(value='Drag to folders to organise; drag onto sessions to merge.')
        for var in (self.destination,self.drag_hint):
            label=ttk.Label(self.win,textvariable=var,style='Muted.TLabel');label.pack(fill='x',pady=(0,2))
            label.bind('<Configure>',lambda e,w=label:w.configure(wraplength=max(100,e.width-8)))
        self.split=ttk.Panedwindow(self.win,orient='vertical');self.split.pack(fill='both',expand=True,pady=(4,0))
        frame=ttk.Frame(self.split);self.split.add(frame,weight=3)
        cols=[('kind','Type',85),('start','Started',145),('active','Active time',80),('xp','EXP/hr',85),('ad','Adena/hr',85),('kills','Kills/hr',72),('review','Reviews',65)]
        self.tree=ttk.Treeview(frame,columns=[c[0] for c in cols],show='tree headings',selectmode='extended',height=5)
        self.tree.heading('#0',text='Section / folder / session');self.tree.column('#0',width=235,minwidth=155,stretch=True)
        self.row_records={};self.drag_origin=None;self.drag_ids=[];self.dragging=False;self.drop_row=None
        for c,t,w in cols:self.tree.heading(c,text=t);self.tree.column(c,width=w,minwidth=w,stretch=False)
        table_scroll(frame,self.tree)
        lower=ttk.Frame(self.split);self.split.add(lower,weight=2)
        actions=ttk.Frame(lower);actions.pack(fill='x',pady=(3,4))
        for title,cmd in [('Merge selected…',self.merge),('Open for review',self.reopen),('Edit values/costs',self.reopen_costs),('Export CSV',self.export)]:
            ttk.Button(actions,text=title,command=cmd,style='Compact.TButton').pack(side='left',padx=(0,5))
        self.detail_tabs=ttk.Notebook(lower,style='Compact.TNotebook');self.detail_tabs.pack(fill='both',expand=True)
        overview=ttk.Frame(self.detail_tabs);loot=ttk.Frame(self.detail_tabs)
        self.detail_tabs.add(overview,text='Summary');self.detail_tabs.add(loot,text='Loot & expenses')
        self.details=tk.StringVar(value='Select a saved session.')
        self.summary_text=tk.Text(overview,height=5,wrap='word',state='disabled',takefocus=True)
        sb=ttk.Scrollbar(overview,orient='vertical',command=self.summary_text.yview);sb.pack(side='right',fill='y')
        self.summary_text.configure(yscrollcommand=sb.set);self.summary_text.pack(fill='both',expand=True)
        self.details.trace_add('write',self.show_summary);self.show_summary()
        self.loot=ttk.Treeview(loot,columns=('who','item','qty'),show='headings',height=5)
        for c,t,w in [('who','Player',125),('item','Item',320),('qty','Quantity / value',230)]:
            self.loot.heading(c,text=t);self.loot.column(c,width=w,minwidth=w,stretch=c=='item')
        table_scroll(loot,self.loot)
        self.tree.tag_configure('drop_target',background='#365e83',foreground='#ffffff')
        self.tree.bind('<ButtonPress-1>',self.drag_start,add='+')
        self.tree.bind('<B1-Motion>',self.drag_motion)
        self.tree.bind('<ButtonRelease-1>',self.drag_end,add='+')
        self.tree.bind('<Escape>',self.cancel_drag)
        self.tree.bind('<Delete>',lambda e:self.delete_selected())
        self.tree.bind('<<TreeviewSelect>>',self.detail);self.refresh()
        if hasattr(app,'appearance'):app.appearance.restyle(self.win)
    def show_summary(self,*_):
        self.summary_text.configure(state='normal');self.summary_text.delete('1.0','end');self.summary_text.insert('1.0',self.details.get());self.summary_text.configure(state='disabled');self.summary_text.yview_moveto(0)
    def refresh(self,select=None):
        self.cancel_drag()
        try:
            self.records=self.archive.organised_records(); self.summaries={i:self.archive.summary(i,self.records) for i,r in self.records.items() if r['kind']!='folder'}
            self.destination.set('New sessions: '+dict(folder_options(self.records)).get(self.archive.default_folder(),'History root'))
        except Exception as e:messagebox.showerror('History',str(e),parent=self.win);return
        old_paths=tuple(self.tree.selection())
        old_records=[self.row_records.get(i) for i in old_paths]
        opened={i for i in self.row_records if self.tree.exists(i) and self.tree.item(i,'open')}
        self.tree.delete(*self.tree.get_children());self.row_records={}
        preferred={}
        for path in history_forest(self.records,self.summaries):
            i=path[-1];record=self.records[i]
            row=json.dumps(path,separators=(',',':'));parent=json.dumps(path[:-1],separators=(',',':')) if len(path)>1 else ''
            if record['kind']=='folder':
                typ='Section' if not record.get('folder') else 'Folder'
                self.tree.insert(parent,'end',iid=row,text=record['name'],open=row in opened or i in (select or []),values=(typ,'','','','','',''))
            else:
                s=self.summaries[i];t=s['totals']
                typ=f"Report ({len(s['sources'])})" if s['kind']=='merged' else ('Session' if s['complete'] else 'Checkpoint')
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
        if self.records[target]['kind']=='folder':
            try:return ('move',target) if folder_move_plan(self.records,self.drag_ids,target) else None
            except ValueError:return None
        if any(self.records[i]['kind']=='folder' for i in self.drag_ids):return None
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
            verb={'add':'Add to report','merge':'Merge with','move':'Move into'}[action[0]]
            self.drag_hint.set(f"{verb} {self.records[action[1]]['name']} — release to confirm.")
        else:self.drag_hint.set('Drag onto a folder, another session or a compatible report.')
        return 'break'
    def cancel_drag(self,*_):
        self.set_drop_target(None)
        self.drag_origin=None;self.drag_ids=[];self.dragging=False
        self.tree.configure(cursor='')
        self.drag_hint.set('Drag to folders to organise, or to sessions/reports to merge.')
    def drag_end(self,event):
        if not self.dragging:self.cancel_drag();return
        row=self.tree.identify_row(event.y) if 0<=event.x<self.tree.winfo_width() and 0<=event.y<self.tree.winfo_height() else ''
        action=self.drop_action(row);ids=list(self.drag_ids)
        self.cancel_drag()
        if not action:return 'break'
        kind,target=action
        try:
            if kind=='move':
                self.archive.move_entries(ids,target);self.refresh([target])
            elif kind=='add':
                if self.archive.add_to_group(target,ids):self.refresh([target])
            else:
                name=simpledialog.askstring('Merge sessions','Name the parent session:',initialvalue=self.records[target]['name'],parent=self.win)
                if name is not None:
                    group=self.archive.merge([target,*ids],name);self.refresh([group])
        except Exception as e:messagebox.showerror('History',str(e),parent=self.win)
        return 'break'
    def selected_records(self):
        return list(dict.fromkeys(self.row_records[r] for r in self.tree.selection() if r in self.row_records))
    def detail(self,*_):
        ids=self.selected_records();self.loot.delete(*self.loot.get_children())
        if len(ids)!=1:self.details.set(f'{len(ids)} selected. Select one to inspect loot, or merge two or more.');return
        record=self.records[ids[0]]
        if record['kind']=='folder':
            children=[r for r in self.records.values() if r.get('folder')==record['id']]
            self.details.set(f"{record['name']}  |  {sum(r['kind']=='folder' for r in children)} folders  |  {sum(r['kind']!='folder' for r in children)} sessions/reports\nOrganisational folder — statistics are not merged.")
            return
        s=self.summaries[ids[0]];t=s['totals']
        self.details.set(f"{s['name']}  |  {len(s['sources'])} original session(s)  |  Active {duration(s['seconds'])}  |  EXP {t['You','XP / SP']:,}  |  SP {t['You','SP']:,}  |  Adena {t['You','Adena']:,}\nPending reviews: {s['pending']}  |  Capture/OCR warnings: {s['gaps']}"+('\nExpand the group above to inspect individual sessions.' if s['kind']=='merged' else ''))
        self.details.set(self.details.get()+f"\nKills: {s['kills']:,} ({rate(s['kills'],s['seconds'])}/h; XP events)")
        valued={(r['who'],r['item']):r for r in s['loot_report']['rows']}
        for (who,item),q in sorted(t.items()):
            if item in ('XP / SP','SP'):continue
            r=valued.get((who,item))
            suffix='' if r is None else (f" | {money(r['value'])} est." if r['priced'] else ' | unpriced')
            if r and r['priced'] and r['unpriced']:suffix+=f" ({r['unpriced']:,} unpriced)"
            self.loot.insert('','end',values=(who,item,f'{q:,}'+suffix))
        self.details.set(self.details.get()+'\n'+loot_summary(s['loot_report'],s['seconds']))
        for r in s['consumable_report']['rows']:
            suffix=f" | {money(r['cost'])} Adena known" if r['priced'] else ' | unpriced'
            if r['priced'] and r['unpriced']:suffix+=f" ({r['unpriced']:,} unpriced)"
            self.loot.insert('','end',values=('You','Used: '+r['item'],f"{r['uses']:,} uses"+suffix))
        self.details.set(self.details.get()+'\n'+cost_summary(s['consumable_report'],t['You','Adena'],s['seconds']))
        for row in party_rows(s['party']):self.loot.insert('','end',values=row)
        m=s.get('monsters',{})
        if m.get('counts') or m.get('unknown'):
            self.details.set(self.details.get()+'\nMonster kills: '+', '.join(f'{name}: {n:,}' for name,n in m.get('counts',{}).items())+f" | Unidentified: {m.get('unknown',0):,}")
        extra=party_summary(s['party'])
        if extra:self.details.set(self.details.get()+'\n'+extra)
    def single(self):
        ids=self.selected_records()
        if len(ids)!=1:messagebox.showinfo('History','Select exactly one entry.',parent=self.win);return None
        return ids[0]
    def selected_folder(self):
        ids=self.selected_records()
        if len(ids)!=1:return ''
        r=self.records[ids[0]]
        return r['id'] if r['kind']=='folder' else r.get('folder','')
    def make_folder(self,parent,title):
        name=simpledialog.askstring(title,'Name:',parent=self.win)
        if name is None:return
        try:i=self.archive.create_folder(name,parent);self.refresh([i])
        except Exception as e:messagebox.showerror(title,str(e),parent=self.win)
    def new_section(self):self.make_folder('','New character / section')
    def new_folder(self):self.make_folder(self.selected_folder(),'New folder')
    def move_selected(self):
        ids=self.selected_records()
        if not ids:return
        picker=FolderPicker(self.win,self.records,'Move selected entries',self.selected_folder())
        if picker.result is None:return
        try:self.archive.move_entries(ids,picker.result);self.refresh(ids)
        except Exception as e:messagebox.showerror('Move',str(e),parent=self.win)
    def choose_destination(self):
        picker=FolderPicker(self.win,self.records,'Save new sessions in',self.selected_folder() or self.archive.default_folder())
        if picker.result is None:return
        try:self.archive.set_default_folder(picker.result);self.refresh()
        except Exception as e:messagebox.showerror('New sessions',str(e),parent=self.win)
    def delete_selected(self):
        ids=self.selected_records()
        if not ids:return
        current=getattr(self.app,'session_id',None)
        protected=[current] if self.app.running or self.app.pending else []
        try:removed,_,_=deletion_plan(self.records,ids,protected)
        except ValueError as e:messagebox.showwarning('Delete',str(e),parent=self.win);return
        originals=sum(self.records[i]['kind']=='original' for i in removed)
        groups=sum(self.records[i]['kind']=='merged' for i in removed)
        folders=sum(self.records[i]['kind']=='folder' for i in removed)
        if not messagebox.askyesno('Delete selected entries',f'Delete {originals} saved session(s), {groups} merged report(s) and {folders} folder(s)?\n\nDeleted sessions are permanently removed from all reports. Deleting a report keeps its original sessions. Deleting a folder moves its remaining contents up one level.',parent=self.win):return
        try:
            removed=self.archive.delete_entries(ids,protected)
            if current in removed:self.app.clear_deleted_session()
            self.refresh()
        except Exception as e:messagebox.showerror('Delete',str(e),parent=self.win)
    def rename(self):
        i=self.single()
        if not i:return
        n=simpledialog.askstring('Rename entry','Name:',initialvalue=self.records[i]['name'],parent=self.win)
        if n is None:return
        try:self.archive.rename(i,n);self.refresh([i])
        except Exception as e:messagebox.showerror('Rename',str(e),parent=self.win)
    def merge(self):
        ids=self.selected_records()
        if len(ids)<2:messagebox.showinfo('Merge','Select at least two entries with Ctrl or Shift.',parent=self.win);return
        if any(self.records[i]['kind']=='folder' for i in ids):messagebox.showinfo('Merge','Select sessions or merged reports, not organisational folders.',parent=self.win);return
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
    def reopen_costs(self):
        i=self.single()
        if not i:return
        if self.records[i]['kind']!='original':
            messagebox.showinfo('Consumable costs','Expand the group and open an original session to edit its costs.',parent=self.win);return
        if self.app.restore_session(i):
            if not self.embedded:self.win.destroy()
            self.app.navigate('loot')
    def export(self):
        i=self.single()
        if not i:return
        if self.records[i]['kind']=='folder':messagebox.showinfo('Export','Select a session or merged report to export.',parent=self.win);return
        s=self.archive.summary(i);path=filedialog.asksaveasfilename(parent=self.win,defaultextension='.csv',filetypes=[('CSV','*.csv')],initialfile='l2-history.csv')
        if not path:return
        try:
            with open(path,'w',newline='',encoding='utf-8-sig') as f:
                w=csv.writer(f);w.writerow(['timestamp','type','player','item','quantity_or_xp','sp','raw_text']);w.writerows(s['events'])
            with open(str(Path(path).with_suffix(''))+'-summary.csv','w',newline='',encoding='utf-8-sig') as f:
                w=csv.writer(f);t=s['totals'];w.writerow(['name','active_seconds','xp','sp','adena','xp_per_hour','adena_per_hour','kills','kills_per_hour','pending_reviews']);w.writerow([s['name'],s['seconds'],t['You','XP / SP'],t['You','SP'],t['You','Adena'],rate(t['You','XP / SP'],s['seconds']),rate(t['You','Adena'],s['seconds']),s['kills'],rate(s['kills'],s['seconds']),s['pending']])
            write_cost_csv(str(Path(path).with_suffix(''))+'-consumables.csv',s['consumable_report'])
            write_loot_csv(str(Path(path).with_suffix(''))+'-loot-values.csv',s['loot_report'])
            messagebox.showinfo('Export','Events, summary, consumable costs and loot values exported.',parent=self.win)
        except Exception as e:messagebox.showerror('Export',str(e),parent=self.win)
