"""Passive game screenshot editor. All draft geometry is client-relative."""
import tkinter as tk
from tkinter import ttk,messagebox
from PIL import Image,ImageTk
from leveling import binding_for
from settings import validate
from copy import deepcopy

LABELS={'chat':'Chat','level':'Level','percent':'Experience %'}
COLOURS={'chat':'#42e8ed','level':'#ffd35b','percent':'#b9a0ff'}

def inside(r,w,h):
    return isinstance(r,dict) and all(type(r.get(k)) is int for k in ('left','top','width','height')) and min(r['left'],r['top'])>=0 and min(r['width'],r['height'])>=3 and r['left']+r['width']<=w and r['top']+r['height']<=h

def draft_regions(target,previous,chat,status):
    result={}
    if previous and previous.title==target.title and previous.window_class==target.window_class and inside(chat,target.width,target.height):
        result['chat']=dict(chat)
    binding=status.get('binding')
    if binding and binding[:2]==binding_for(target)[:2]:
        for k,r in status.get('regions',{}).items():
            if k in ('level','percent') and inside(r,target.width,target.height):result[k]=dict(r)
    return result

def rect_from_points(a,b,w,h):
    l,r=sorted((max(0,min(w,a[0])),max(0,min(w,b[0]))))
    t,b=sorted((max(0,min(h,a[1])),max(0,min(h,b[1]))))
    return dict(left=l,top=t,width=r-l,height=b-t)

def move_region(r,dx,dy,w,h):
    return dict(r,left=max(0,min(w-r['width'],r['left']+dx)),top=max(0,min(h-r['height'],r['top']+dy)))

def calibration_data(target,regions,pitch,old_status,hud_position=None):
    data=dict(schema=1,title=target.title,window_class=target.window_class,width=target.width,height=target.height,pitch=pitch,region=dict(regions.get('chat',{})))
    if hud_position is not None:data['hud_position']=list(hud_position)
    validate(data)
    for key in ('level','percent'):
        if key in regions and not inside(regions[key],target.width,target.height):raise ValueError(f'{LABELS[key]} must be inside the game and at least 3 × 3 pixels.')
    status=dict(old_status,binding=binding_for(target),regions={k:dict(regions[k]) for k in ('level','percent') if k in regions})
    return data,status

class RegionEditor:
    def __init__(self,app,target,shot,regions,kind,commit,close):
        self.app=app;self.target=target;self.shot=shot;self.regions=deepcopy(regions)
        self.commit=commit;self.on_close=close;self.drag=None
        win=self.win=tk.Toplevel(app.root);win.title(f'Bound areas — {target.title}');win.attributes('-topmost',True)
        self.selected=tk.StringVar(master=win,value=kind);self.mode=tk.StringVar(master=win,value='move');self.zoom=tk.StringVar(master=win,value='Fit')
        self.info=tk.StringVar(master=win)
        header=ttk.Frame(win,padding=(10,6));header.pack(fill='x')
        ttk.Label(header,text='Edit bound areas',style='Title.TLabel').pack(anchor='w')
        ttk.Label(header,text='Select an area, drag to move it, or choose Redraw to resize or replace it. Arrow keys nudge by one pixel. Include the complete bottom chat line.',wraplength=760).pack(anchor='w',pady=(3,5))
        bar=ttk.Frame(header);bar.pack(fill='x')
        for k,label in LABELS.items():
            ttk.Radiobutton(bar,text=label,value=k,variable=self.selected,command=self.draw).pack(side='left',padx=(0,8))
        for mode,label in [('move','Move'),('draw','Redraw / resize')]:
            ttk.Radiobutton(bar,text=label,value=mode,variable=self.mode,command=self.draw).pack(side='left',padx=4)
        ttk.Label(bar,text='Zoom:').pack(side='left',padx=(12,3))
        combo=ttk.Combobox(bar,state='readonly',values=('Fit','100%','200%'),textvariable=self.zoom,width=7);combo.pack(side='left');combo.bind('<<ComboboxSelected>>',self.render)
        footer=ttk.Frame(win,padding=(10,6));footer.pack(side='bottom',fill='x')
        ttk.Label(footer,textvariable=self.info,wraplength=760).pack(fill='x',pady=(0,4))
        row=ttk.Frame(footer);row.pack(fill='x')
        ttk.Button(row,text='Clear selected',command=self.clear).pack(side='left')
        ttk.Button(row,text='Cancel',command=self.cancel).pack(side='right')
        ttk.Button(row,text='Save areas',style='Primary.TButton',command=lambda:self.save(False)).pack(side='right',padx=5)
        if app.running:ttk.Button(row,text='Save & resume',style='Primary.TButton',command=lambda:self.save(True)).pack(side='right',padx=5)
        panel=ttk.Frame(win);panel.pack(fill='both',expand=True)
        panel.rowconfigure(0,weight=1);panel.columnconfigure(0,weight=1)
        self.fit=min(1,max(100,win.winfo_screenwidth()-100)/shot.width,max(100,win.winfo_screenheight()-300)/shot.height)
        self.canvas=tk.Canvas(panel,width=round(shot.width*self.fit),height=round(shot.height*self.fit),background='#13171d',highlightthickness=0,takefocus=True)
        self.canvas.grid(row=0,column=0,sticky='nsew')
        x=ttk.Scrollbar(panel,orient='horizontal',command=self.canvas.xview);x.grid(row=1,column=0,sticky='ew')
        y=ttk.Scrollbar(panel,orient='vertical',command=self.canvas.yview);y.grid(row=0,column=1,sticky='ns')
        self.canvas.configure(xscrollcommand=x.set,yscrollcommand=y.set)
        self.canvas.bind('<Button-1>',self.down);self.canvas.bind('<B1-Motion>',self.motion);self.canvas.bind('<ButtonRelease-1>',self.up)
        for key,dx,dy in [('Left',-1,0),('Right',1,0),('Up',0,-1),('Down',0,1)]:
            self.canvas.bind('<'+key+'>',lambda e,x=dx,y=dy:self.nudge(x,y))
        win.bind('<Escape>',lambda e:self.cancel());win.protocol('WM_DELETE_WINDOW',self.cancel)
        app.appearance.restyle(win);self.render();win.grab_set();self.canvas.focus_set()
    def render(self,*_):
        self.drag=None
        self.scale={'Fit':self.fit,'100%':1,'200%':2}[self.zoom.get()]
        w,h=round(self.shot.width*self.scale),round(self.shot.height*self.scale)
        self.photo=ImageTk.PhotoImage(self.shot.resize((w,h),Image.Resampling.NEAREST))
        self.canvas.delete('all');self.canvas.create_image(0,0,image=self.photo,anchor='nw')
        self.canvas.configure(scrollregion=(0,0,w,h))
        self.draw()
        # Keep the selected small field in view when zooming.
        r=self.regions.get(self.selected.get())
        if r and self.zoom.get()!='Fit':
            self.canvas.xview_moveto(max(0,(r['left']-40)/self.shot.width));self.canvas.yview_moveto(max(0,(r['top']-40)/self.shot.height))
    def draw(self):
        cv=self.canvas;cv.delete('area')
        for k,r in self.regions.items():
            l,t,w,h=(r[x]*self.scale for x in ('left','top','width','height'))
            cv.create_rectangle(l,t,l+w,t+h,outline=COLOURS[k],width=3 if self.selected.get()==k else 1,tags='area')
            cv.create_text(l,max(0,t-2),text=LABELS[k],fill=COLOURS[k],anchor='sw' if t>15 else 'nw',tags='area')
        r=self.regions.get(self.selected.get())
        desc=f"{r['left']}, {r['top']}  •  {r['width']} × {r['height']} px" if r else 'Not bound — drag to draw'
        self.info.set(f"{LABELS[self.selected.get()]}: {desc}   |   "+('Session paused; totals retained.' if self.app.running else 'Save to use these areas next session.'))
    def point(self,e):
        return (max(0,min(self.shot.width,round(self.canvas.canvasx(e.x)/self.scale))),max(0,min(self.shot.height,round(self.canvas.canvasy(e.y)/self.scale))))
    def down(self,e):
        self.canvas.focus_set();p=self.point(e);k=self.selected.get();r=self.regions.get(k)
        if self.mode.get()=='move' and r:
            if not (r['left']<=p[0]<=r['left']+r['width'] and r['top']<=p[1]<=r['top']+r['height']):return
            self.drag=(k,p,dict(r),'move')
        else:self.drag=(k,p,dict(r) if r else None,'draw')
    def motion(self,e):
        if not self.drag:return
        k,a,old,mode=self.drag;b=self.point(e)
        r=move_region(old,b[0]-a[0],b[1]-a[1],self.shot.width,self.shot.height) if mode=='move' else rect_from_points(a,b,self.shot.width,self.shot.height)
        if min(r['width'],r['height'])>=3:self.regions[k]=r;self.draw()
    def up(self,e):
        if self.drag:self.motion(e);self.drag=None
    def nudge(self,dx,dy):
        k=self.selected.get()
        if k in self.regions:self.regions[k]=move_region(self.regions[k],dx,dy,self.shot.width,self.shot.height);self.draw()
        return 'break'
    def clear(self):
        self.regions.pop(self.selected.get(),None);self.draw()
    def cancel(self):
        self.win.destroy();self.on_close(False)
    def save(self,resume):
        try:self.commit(self.target,self.regions)
        except Exception as e:messagebox.showerror('Bound areas',str(e),parent=self.win);return
        self.win.destroy();self.on_close(resume)
