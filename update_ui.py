"""Main-thread Tk update controls, with background network and verification."""
import queue, sys, threading, shutil
from pathlib import Path
from tkinter import ttk, messagebox
from updater import check_release, stage_update, launch_helper

class UpdateUI:
    def __init__(self,app,frame):
        self.app=app;self.queue=queue.Queue();self.checking=False
        self.frozen=getattr(sys,'frozen',False)
        self.button=ttk.Button(frame,text='Check for updates',command=lambda:self.check(True))
        self.button.pack(side='right',padx=6)
        app.root.after(200,self.poll)
        if self.frozen:app.root.after(1800,lambda:self.check(False))

    def check(self,manual):
        if self.checking or self.app.update_busy:return
        if not self.frozen:
            if manual:messagebox.showinfo('Updates','Automatic installation is available in the portable Windows build.',parent=self.app.root)
            return
        self.checking=True;self.button.configure(text='Checking…',state='disabled')
        def work():
            try:self.queue.put(('checked',check_release(),manual))
            except Exception as e:self.queue.put(('error',str(e),manual))
        threading.Thread(target=work,daemon=True).start()

    def idle(self):
        a=self.app
        return not (a.running or a.pending or a.selecting or a.closing or a.update_busy)

    def offer(self,info):
        self.button.configure(text='Update available',command=lambda:self.offer(info))
        if not self.idle():
            return
        if not messagebox.askyesno('Tracker update',
            f"Version {info['version']} is available.\n\n{info['notes']}\n\nDownload, verify and install? The tracker will restart and retain a backup.",
            parent=self.app.root):return
        if not self.idle() or not self.app.save_session():return
        self.app.update_busy=True;self.button.configure(text='Downloading update…',state='disabled')
        self.app.start_btn.configure(state='disabled')
        root=Path(sys.executable).resolve().parent
        def work():
            try:self.queue.put(('staged',(root,stage_update(info,root),info['version']),True))
            except Exception as e:self.queue.put(('install_error',str(e),True))
        threading.Thread(target=work,daemon=True).start()

    def reset(self):
        self.app.update_busy=False;self.app.start_btn.configure(state='normal')
        self.button.configure(text='Check for updates',state='normal',command=lambda:self.check(True))

    def poll(self):
        try:
            while True:
                kind,payload,manual=self.queue.get_nowait()
                if kind in ('checked','error'):
                    self.checking=False
                    self.button.configure(text='Check for updates',state='normal',command=lambda:self.check(True))
                    if kind=='error':
                        if manual:messagebox.showwarning('Update check',payload,parent=self.app.root)
                    elif payload:self.offer(payload)
                    elif manual:messagebox.showinfo('Updates','No newer published release is available.',parent=self.app.root)
                elif kind=='install_error':
                    self.reset();messagebox.showerror('Update failed',payload,parent=self.app.root)
                elif kind=='staged':
                    root,staging,version=payload
                    try:
                        if not self.app.save_session():raise RuntimeError('Session could not be saved')
                        launch_helper(root,staging,version)
                    except Exception as e:
                        shutil.rmtree(staging,ignore_errors=True);self.reset()
                        messagebox.showerror('Update failed',str(e),parent=self.app.root);continue
                    try:
                        if self.app.hud:self.app.hud.close()
                    finally:self.app.root.destroy()
                    return
        except queue.Empty:pass
        self.app.root.after(200,self.poll)
