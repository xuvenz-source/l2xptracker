"""Passive monster screenshot import. All rows require user confirmation."""
import tkinter as tk
from tkinter import ttk,messagebox,filedialog
from PIL import Image,ImageOps,ImageTk
import threading,queue
from drop_targets import parse_ocr,parse_table,format_table,chance,clean,save
from region_editor import rect_from_points
from monster_library import profile,header as reward_header

def read_monster(image):
    import pytesseract
    w,h=image.size
    im=ImageOps.invert(ImageOps.grayscale(image.crop((round(w*.054),round(h*.064),round(w*.98),round(h*.94)))))
    im=im.resize((im.width*3,im.height*3),Image.Resampling.LANCZOS)
    text=pytesseract.image_to_string(im,config='--psm 6',timeout=20)
    return text,parse_ocr(text)

class CropWindow:
    def __init__(self,root,shot,done,cancel):
        self.win=tk.Toplevel(root);self.win.title('Select the entire monster Drop window');self.win.attributes('-topmost',True)
        self.shot=shot;self.done=done;self.cancel=cancel;self.start=None;self.rect=None;self.box=None
        self.scale=min(1,(self.win.winfo_screenwidth()-80)/shot.width,(self.win.winfo_screenheight()-170)/shot.height)
        w,h=round(shot.width*self.scale),round(shot.height*self.scale)
        ttk.Label(self.win,text='Drag around the entire monster window, including its name and visible drop rows.').pack(padx=8,pady=6)
        self.canvas=tk.Canvas(self.win,width=w,height=h,highlightthickness=0);self.canvas.pack()
        self.photo=ImageTk.PhotoImage(shot.resize((w,h),Image.Resampling.NEAREST));self.canvas.create_image(0,0,anchor='nw',image=self.photo)
        self.canvas.bind('<Button-1>',self.down);self.canvas.bind('<B1-Motion>',self.move);self.canvas.bind('<ButtonRelease-1>',self.move)
        row=ttk.Frame(self.win);row.pack(fill='x',pady=6)
        ttk.Button(row,text='Cancel',command=self.close).pack(side='right',padx=6)
        ttk.Button(row,text='Read selected monster window',command=self.apply).pack(side='right')
        self.win.protocol('WM_DELETE_WINDOW',self.close)
    def down(self,e):self.start=(e.x,e.y);self.move(e)
    def move(self,e):
        if self.start is None:return
        a=self.start;b=(e.x,e.y)
        if self.box:self.canvas.delete(self.box)
        self.box=self.canvas.create_rectangle(*a,*b,outline='#42e8ed',width=2)
        self.rect=rect_from_points(tuple(round(x/self.scale) for x in a),tuple(round(x/self.scale) for x in b),self.shot.width,self.shot.height)
    def close(self):self.win.destroy();self.cancel()
    def apply(self):
        r=self.rect
        if not r or r['width']<150 or r['height']<100:messagebox.showwarning('Monster window','Select the entire monster window.',parent=self.win);return
        image=self.shot.crop((r['left'],r['top'],r['left']+r['width'],r['top']+r['height']))
        self.win.destroy();self.done(image)

class DropEditor:
    def __init__(self,app,image=None):
        self.app=app;self.win=tk.Toplevel(app.root);self.win.title('Desired monster drops');self.win.geometry('840x640');self.win.minsize(630,480)
        self.win.attributes('-topmost',True);self.result=queue.Queue();self.busy=False;self.rows=[];self.committed_text=None
        existing=getattr(app,'drop_edit_profile',None)
        config=existing['drop'] if existing else (clean({}) if isinstance(getattr(app,'monster_library',None),dict) else app.drop_config)
        self.level=tk.StringVar(value=str(existing['level'] or '') if existing else '')
        self.xp=tk.StringVar(value=str(existing['xp']) if existing and existing['xp'] is not None else '')
        self.sp=tk.StringVar(value=str(existing['sp']) if existing and existing['sp'] is not None else '')
        self.monster=tk.StringVar(value=config['monster']);self.rate=tk.StringVar(value=config['rate']);self.status=tk.StringVar()
        header=ttk.Frame(self.win,padding=8);header.pack(fill='x')
        ttk.Label(header,text='Desired drops',style='Title.TLabel').pack(anchor='w')
        row=ttk.Frame(header);row.pack(fill='x',pady=4)
        ttk.Button(row,text='Read game window…',command=self.capture).pack(side='left')
        self.import_btn=ttk.Button(row,text='Import screenshot…',command=self.import_image);self.import_btn.pack(side='left',padx=6)
        ttk.Label(row,text='Monster:').pack(side='left',padx=5);ttk.Entry(row,textvariable=self.monster).pack(side='left',fill='x',expand=True)
        rewards=ttk.Frame(header);rewards.pack(fill='x',pady=4)
        for label,var in [('Monster level',self.level),('Base XP',self.xp),('Base SP',self.sp)]:
            ttk.Label(rewards,text=label+':').pack(side='left',padx=(4,2));ttk.Entry(rewards,textvariable=var,width=10).pack(side='left',padx=(0,8))
        ttk.Label(header,text='Verify or edit the table against the Drop tab. Each row: item name [Tab] group % [Tab] item %. Confirm, then select your targets.',wraplength=740).pack(anchor='w')
        self.table=tk.Text(self.win,height=9,wrap='none',undo=True);self.table.pack(fill='both',expand=True,padx=8);self.table.insert('1.0',format_table(config['rows']))
        ttk.Button(self.win,text='Confirm table / refresh choices',command=self.confirm).pack(anchor='w',padx=8,pady=4)
        ttk.Label(self.win,text='Select desired drops (Ctrl / Shift for multiple, up to 12)',padding=(8,3)).pack(anchor='w')
        panel=ttk.Frame(self.win);panel.pack(fill='both',expand=True,padx=8)
        self.list=tk.Listbox(panel,selectmode='extended',exportselection=False,height=7);self.list.pack(side='left',fill='both',expand=True)
        sb=ttk.Scrollbar(panel,command=self.list.yview);sb.pack(side='right',fill='y');self.list.configure(yscrollcommand=sb.set)
        footer=ttk.Frame(self.win,padding=8);footer.pack(fill='x')
        row=ttk.Frame(footer);row.pack(fill='x')
        ttk.Label(row,text='Monster kills/hr override (blank = session rate):').pack(side='left')
        ttk.Entry(row,textvariable=self.rate,width=10).pack(side='left',padx=5)
        ttk.Button(row,text='Save targets',style='Primary.TButton',command=self.apply).pack(side='right')
        ttk.Button(row,text='Cancel',command=self.win.destroy).pack(side='right',padx=6)
        ttk.Label(footer,text='Uses identified monster kills per session hour unless overridden. Estimates are average waits, not guarantees.',wraplength=750).pack(anchor='w',pady=4)
        ttk.Label(footer,textvariable=self.status,wraplength=750).pack(anchor='w')
        app.appearance.restyle(self.win);self.confirm(config['selected'])
        if image is not None:self.read(image)
    def capture(self):
        if self.busy:return
        self.app.capture_drop_window()
    def import_image(self):
        if self.busy:return
        path=filedialog.askopenfilename(parent=self.win,filetypes=[('Images','*.png *.jpg *.jpeg *.bmp')])
        if path:
            try:
                with Image.open(path) as im:self.read(im.convert('RGB'))
            except Exception as e:messagebox.showerror('Monster screenshot',str(e),parent=self.win)
    def read(self,image):
        self.busy=True;self.import_btn.config(state='disabled');self.status.set('Reading screenshot…')
        def work():
            try:self.result.put((True,read_monster(image)))
            except Exception as e:self.result.put((False,str(e)))
        threading.Thread(target=work,daemon=True).start();self.win.after(100,self.poll)
    def poll(self):
        try:ok,result=self.result.get_nowait()
        except queue.Empty:self.win.after(100,self.poll);return
        self.busy=False;self.import_btn.config(state='normal')
        if not ok:self.status.set('OCR failed: '+result);return
        raw,(monster,rows,warnings)=result
        self.rate.set('')  # New table: never reuse another monster's rate override.
        import re
        m=re.search(r'Lv\.?\s*(\d+)$',monster,re.I);self.level.set(m[1] if m else '')
        xp,sp=reward_header(raw);self.xp.set(xp);self.sp.set(sp)
        self.monster.set(monster);self.table.delete('1.0','end');self.table.insert('1.0',format_table(rows))
        self.list.delete(0,'end');self.committed_text=None
        self.status.set(f'{len(rows)} rows read. Verify all names and percentages, then confirm. '+(' | '.join(warnings) if warnings else ''))
        win=tk.Toplevel(self.win);win.title('Raw OCR — verify against monster window');win.geometry('600x380')
        t=tk.Text(win,wrap='word');t.pack(fill='both',expand=True);t.insert('1.0',raw);t.config(state='disabled')
    def confirm(self,selected=()):
        if self.busy:return
        text=self.table.get('1.0','end-1c')
        try:self.rows=parse_table(text)
        except ValueError as e:self.status.set(str(e));return
        self.committed_text=text;self.list.delete(0,'end')
        for r in self.rows:self.list.insert('end',f"{r['name']}  |  {chance(r)*100:.6f}% per kill")
        for i in selected:
            if i<len(self.rows):self.list.selection_set(i)
        self.status.set('Select desired drops, then Save targets.')
    def apply(self):
        if self.busy:return
        if self.table.get('1.0','end-1c')!=self.committed_text:self.status.set('Confirm the edited table before saving.');return
        chosen=list(self.list.curselection())
        if len(chosen)>12:self.status.set('Select up to 12 targets.');return
        raw=dict(monster=self.monster.get().strip(),rows=self.rows,selected=chosen,rate=self.rate.get().strip())
        config=clean(raw)
        if raw['rate'] and not config['rate']:self.status.set('Enter a positive kills/hr rate up to 100,000, or leave blank.');return
        if chosen and not raw['monster']:self.status.set('Enter the monster name.');return
        if isinstance(getattr(self.app,'monster_library',None),dict):
            try:p=profile(config,self.level.get(),self.xp.get(),self.sp.get())
            except ValueError as e:self.status.set(str(e));return
            if p['id'] in self.app.monster_library['profiles'] and p!=self.app.monster_library['profiles'][p['id']]:
                if not messagebox.askyesno('Update monster','Replace this monster’s saved profile and drop targets?',parent=self.win):return
            try:self.app.save_monster_profile(p)
            except OSError as e:self.status.set(str(e));return
            self.win.destroy();return
        if self.app.drop_config['rows'] and config!=self.app.drop_config:
            if not messagebox.askyesno('Replace loot table','Replace the saved loot table and selected targets with these settings?',parent=self.win):return
        try:save(config)
        except OSError as e:self.status.set(str(e));return
        self.app.drop_config=config;self.app.update_drop_targets();self.win.destroy()
