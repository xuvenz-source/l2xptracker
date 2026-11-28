"""Passive game screenshot editor. All draft geometry is client-relative."""
import tkinter as tk
from tkinter import ttk,messagebox
from PIL import Image,ImageTk
from leveling import binding_for,read_number
from player_frame import verified_player_frame
import threading,queue
from settings import validate
from copy import deepcopy
import numpy as np
from chat_style import fit_chat_panel

LABELS={'chat':'Chat','level':'Level','percent':'Experience %','frame':'Player frame'}
COLOURS={'chat':'#42e8ed','level':'#ffd35b','percent':'#b9a0ff','frame':'#83dcb0'}

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
        ttk.Label(header,text='For chat, draw around the whole system-message panel (including its border), then click Auto-fit chat. Verify the fitted outline before saving. For player status, select Player frame, draw around the compact frame and click Auto-fit player; or select individual digits. Arrow keys nudge.',wraplength=760).pack(anchor='w',pady=(3,5))
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
        ttk.Button(row,text='Auto-fit chat',command=self.auto_fit_chat).pack(side='left',padx=5)
        ttk.Button(row,text='Auto-fit player',command=self.auto_fit_player).pack(side='left',padx=5)
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
    def auto_fit_chat(self):
        r=self.regions.get('chat')
        if not r:
            self.info.set('Draw a rough rectangle around the system-message panel first.');return
        self.selected.set('chat')
        x,y,w,h=(r[k] for k in ('left','top','width','height'))
        style=self.app.chat_style
        pitch=self.app.session_pitch if self.app.running else int(self.app.pitch.get())
        colours=getattr(self.app,'session_colours',None) if self.app.running else style['colours']
        if not colours:colours=style['colours']
        rgb=np.asarray(self.shot.crop((x,y,x+w,y+h)).convert('RGB'))
        fit=fit_chat_panel(rgb,pitch,colours)
        if fit is None:
            self.draw();self.info.set('Auto-fit could not verify a complete chat lattice. Include only the system-message panel with at least three visible lines and a small bottom margin, or adjust manually.');return
        local,actual,count=fit
        self.regions['chat']=dict(left=x+local['left'],top=y+local['top'],width=local['width'],height=local['height'])
        self.draw();self.info.set(f'Auto-fit: {count} message bands, {actual}px spacing. Removed {h-local["height"]}px bottom margin. Check the outline includes the last message, then save.')
    def auto_fit_player(self):
        if getattr(self,'player_fit_busy',False):return
        r=self.regions.get('frame')
        if not r:
            self.selected.set('frame');self.mode.set('draw');self.draw()
            self.info.set('Draw around the compact player frame including the level, HP, MP and XP bars. Then click Auto-fit player.');return
        snapshot=dict(r);x,y,w,h=(snapshot[k] for k in ('left','top','width','height'))
        shot=self.shot.crop((x,y,x+w,y+h))
        previous={k:deepcopy(self.regions.get(k)) for k in ('level','percent')}
        self.player_fit_busy=True;self.info.set('Finding the level badge and verifying both status readings…')
        result=queue.Queue()
        def work():
            try:result.put(verified_player_frame(shot,read_number))
            except Exception:result.put(None)
        def poll():
            try:fit=result.get_nowait()
            except queue.Empty:
                self.win.after(75,poll);return
            self.player_fit_busy=False
            if self.regions.get('frame')!=snapshot or any(self.regions.get(k)!=v for k,v in previous.items()):
                self.info.set('Selection changed. Run Auto-fit player again.');return
            if fit is None:
                self.info.set('Could not verify both player readings. Include the complete compact frame with visible HP/MP bars, or clear the frame and bind level and XP separately.');return
            regions,values=fit
            for k,z in regions.items():
                self.regions[k]=dict(z,left=x+z['left'],top=y+z['top'])
            self.regions.pop('frame',None);self.selected.set('level');self.draw()
            self.info.set(f"Auto-fit verified level {values['level']} and {values['percent']}% XP. Check the two outlines and save.")
        threading.Thread(target=work,daemon=True).start();self.win.after(75,poll)
    def clear(self):
        self.regions.pop(self.selected.get(),None);self.draw()
    def cancel(self):
        self.win.destroy();self.on_close(False)
    def save(self,resume):
        if getattr(self,'player_fit_busy',False):
            self.info.set('Player verification is still running. Save when both readings have been checked.');return
        if 'frame' in self.regions:
            self.info.set('Auto-fit the drawn player frame or clear it before saving. Existing digit bindings are unchanged.');return
        try:self.commit(self.target,self.regions)
        except Exception as e:messagebox.showerror('Bound areas',str(e),parent=self.win);return
        self.win.destroy();self.on_close(resume)

class OverlayRegionEditor(RegionEditor):
    """Same draft/save logic as the preview editor, at native game pixels."""
    def __init__(self,app,target,shot,regions,kind,commit,close,rect):
        from selection_overlay import SelectionSurface
        self.app=app;self.target=target;self.shot=shot;self.regions=deepcopy(regions)
        self.commit=commit;self.on_close=close;self.drag=None;self.scale=1
        surface=self.surface=SelectionSurface(app.root,shot,rect)
        win=self.win=surface.win;self.canvas=surface.canvas
        try:
            self.selected=tk.StringVar(master=win,value=kind);self.mode=tk.StringVar(master=win,value='move')
            self.info=tk.StringVar(master=win)
            bar=surface.toolbar()
            row=ttk.Frame(bar);row.pack(fill='x')
            for k,label in LABELS.items():ttk.Radiobutton(row,text=label,value=k,variable=self.selected,command=self.draw).pack(side='left',padx=3)
            row=ttk.Frame(bar);row.pack(fill='x')
            for mode,label in [('move','Move'),('draw','Redraw / resize')]:ttk.Radiobutton(row,text=label,value=mode,variable=self.mode,command=self.draw).pack(side='left',padx=3)
            ttk.Button(row,text='Clear',command=self.clear).pack(side='right')
            ttk.Button(row,text='Auto-fit chat',command=self.auto_fit_chat).pack(side='right',padx=3)
            ttk.Button(row,text='Auto-fit player',command=self.auto_fit_player).pack(side='right',padx=3)
            ttk.Label(bar,textvariable=self.info,wraplength=440).pack(anchor='w',pady=3)
            ttk.Label(bar,text='Draw around the system-message panel or compact player frame, then use its Auto-fit button.',wraplength=440).pack(anchor='w')
            ttk.Label(bar,text='1/2/3/4 select · M/R move/redraw · arrows nudge · Tab hides toolbar').pack(anchor='w')
            row=ttk.Frame(bar);row.pack(fill='x')
            ttk.Button(row,text='Cancel',command=self.cancel).pack(side='left')
            ttk.Button(row,text='Save areas',command=lambda:self.save(False)).pack(side='right',padx=3)
            if app.running:ttk.Button(row,text='Save & resume',style='Primary.TButton',command=lambda:self.save(True)).pack(side='right',padx=3)
            self.canvas.bind('<Button-1>',self.down);self.canvas.bind('<B1-Motion>',self.motion);self.canvas.bind('<ButtonRelease-1>',self.up)
            for key,dx,dy in [('Left',-1,0),('Right',1,0),('Up',0,-1),('Down',0,1)]:
                win.bind('<'+key+'>',lambda e,x=dx,y=dy:self.nudge(x,y))
            def choose(k):self.selected.set(k);self.draw()
            def mode(k):self.mode.set(k);self.draw()
            for key,k in zip('1234',LABELS):win.bind(key,lambda e,k=k:choose(k))
            win.bind('m',lambda e:mode('move'));win.bind('r',lambda e:mode('draw'))
            win.bind('<Escape>',lambda e:self.cancel());win.bind('<Return>',lambda e:self.save(bool(app.running)))
            win.protocol('WM_DELETE_WINDOW',self.cancel)
            app.appearance.restyle(win);surface.finish_toolbar();self.draw()
        except Exception:
            surface.destroy();raise
    def draw(self):
        super().draw()
        if hasattr(self.surface,'bar_id'):self.canvas.tag_raise(self.surface.bar_id)
