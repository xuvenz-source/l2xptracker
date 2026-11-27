"""Integrated release updater; only the file replacement helper is separate."""
import queue, sys, threading, shutil
from pathlib import Path
from tkinter import ttk, messagebox
import tkinter as tk
from updater import check_release, stage_update, launch_helper
from preferences import failed_update

CHECK_INTERVAL_MS=30*60*1000

class UpdateUI:
    def __init__(self,app,frame):
        self.app=app;self.queue=queue.Queue();self.checking=False
        self.frozen=getattr(sys,'frozen',False)
        self.available=None;self.attempted=set();self.failed_version=failed_update()
        self.button=ttk.Button(frame,text='Check for updates',command=lambda:self.check(True))
        self.button.pack(side='right',padx=6)
        app.root.after(200,self.poll)
        if self.frozen:app.root.after(1200,self.periodic_check)

    def periodic_check(self):
        self.check(False)
        self.app.root.after(CHECK_INTERVAL_MS,self.periodic_check)

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
        if a.running or a.pending or a.selecting or a.closing or a.update_busy or getattr(a,'reset_request',None) is not None:return False
        tabs=getattr(a,'tabs',None)
        if isinstance(tabs,ttk.Notebook) and tabs.select()!=str(a.pages['dashboard']):return False
        # Do not restart while reviewing OCR, editing settings, exporting a file,
        # or interacting with another tracker dialog.
        try:
            if a.root.grab_current() is not None:return False
            if any(isinstance(w,tk.Toplevel) and w.winfo_exists() and w.winfo_viewable() for w in a.root.winfo_children()):return False
        except tk.TclError:return False
        return True

    def show_available(self):
        if not self.available:return
        v=self.available['version']
        label=f'Retry update v{v}' if v==self.failed_version or v in self.attempted else f'Update v{v} available'
        self.button.configure(text=label,state='normal',command=self.manual_offer)

    def manual_offer(self):
        if not self.available:return self.check(True)
        if not self.idle():
            messagebox.showinfo('Update available','Stop tracking, finish queued OCR, return to Dashboard and close other tracker windows before installing.',parent=self.app.root)
            return
        info=self.available
        if messagebox.askyesno('Tracker update',
            f"Version {info['version']} is available.\n\n{info['notes']}\n\nDownload, verify and install? The tracker will restart and retain a backup.",
            parent=self.app.root):
            self.begin_install(info)

    def maybe_auto_install(self):
        info=self.available
        if (not info or self.checking or not self.app.auto_update or not self.idle()
                or info['version'] in self.attempted or info['version']==self.failed_version):
            return
        self.begin_install(info)

    def begin_install(self,info):
        if not self.idle():return
        version=info['version']
        # Limit unattended attempts to once per version per process, including
        # failures to save. Manual retry is always available.
        self.attempted.add(version)
        if not self.app.save_session():
            self.show_available();return
        self.app.update_busy=True
        self.button.configure(text=f'Downloading v{version}…',state='disabled')
        self.app.start_btn.configure(state='disabled')
        self.app.status.set(f'Updating to v{version} — verifying download; the tracker will restart.')
        root=Path(sys.executable).resolve().parent
        def work():
            try:self.queue.put(('staged',(root,stage_update(info,root,lambda msg:self.queue.put(('progress',msg,False))),version),True))
            except Exception as e:self.queue.put(('install_error',str(e),True))
        threading.Thread(target=work,daemon=True).start()

    def reset(self):
        self.app.update_busy=False;self.app.start_btn.configure(state='normal')
        self.button.configure(text='Check for updates',state='normal',command=lambda:self.check(True))
        self.show_available()

    def fail(self,error):
        self.reset()
        self.app.status.set('Update failed — current tracker preserved. Use the update button to retry.')
        self.app.append(f'WARNING: Update failed: {error}')

    def poll(self):
        try:
            while True:
                kind,payload,manual=self.queue.get_nowait()
                if kind in ('checked','error'):
                    self.checking=False
                    self.button.configure(text='Check for updates',state='normal',command=lambda:self.check(True))
                    if kind=='error':
                        if manual:messagebox.showwarning('Update check',payload,parent=self.app.root)
                        self.show_available()
                    elif payload:
                        self.available=payload;self.show_available()
                        if manual and not self.app.auto_update:self.manual_offer()
                    else:
                        self.available=None
                        if manual:messagebox.showinfo('Updates','No newer published release is available.',parent=self.app.root)
                elif kind=='progress':
                    self.app.status.set(payload)
                    self.app.append('UPDATE: '+payload)
                elif kind=='install_error':
                    self.fail(payload)
                elif kind=='staged':
                    root,staging,version=payload
                    try:
                        if not self.app.save_session():raise RuntimeError('Session could not be saved')
                        launch_helper(root,staging,version)
                    except Exception as e:
                        shutil.rmtree(staging,ignore_errors=True);self.fail(str(e));continue
                    try:
                        if self.app.hud:self.app.hud.close()
                    finally:self.app.root.destroy()
                    return
        except queue.Empty:pass
        self.maybe_auto_install()
        self.app.root.after(200,self.poll)
