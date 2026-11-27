"""Run startup release check before constructing the tracker UI."""
import queue,sys,threading,shutil
from pathlib import Path
from version import VERSION
from preferences import load_auto_update,failed_update
from updater import check_release,stage_update,launch_helper
from updater_view import UpdateView

class StartupUpdater:
    def __init__(self,root,open_tracker):
        self.root=root;self.open_tracker=open_tracker;self.q=queue.Queue()
        self.state='checking';self.info=None;self.poll_job=None
        self.root.title('L2 Legacy Tracker — checking updates')
        self.root.resizable(False,False)
        self.view=UpdateView(root,VERSION);self.view.pack(fill='both',expand=True)
        self.view.stage('Checking for updates…')
        self.view.actions([('Continue without checking',self.continue_tracker)])
        root.protocol('WM_DELETE_WINDOW',self.close)
        threading.Thread(target=self.check,daemon=True).start()
        self.poll_job=root.after(75,self.poll)
    def check(self):
        try:self.q.put(('checked',check_release()))
        except Exception as e:self.q.put(('error',str(e)))
    def continue_tracker(self):
        if self.state in ('installing','handoff','closed'):return
        self.state='closed'
        if self.poll_job is not None:self.root.after_cancel(self.poll_job);self.poll_job=None
        self.view.destroy();self.root.resizable(True,True)
        self.open_tracker()
    def close(self):
        if self.state in ('installing','handoff'):return
        self.state='closed';self.root.destroy()
    def install(self):
        if self.state!='offer' or not self.info:return
        self.state='installing';self.view.actions([])
        info=self.info;root=Path(sys.executable).resolve().parent
        self.view.version.set(f"v{VERSION} → v{info['version']}")
        self.view.stage('Preparing update…')
        def work():
            try:
                staging=stage_update(info,root,lambda msg:self.q.put(('stage',msg)),lambda n,total:self.q.put(('bytes',(n,total))))
                self.q.put(('staged',(root,staging,info['version'])))
            except Exception as e:self.q.put(('error',str(e)))
        threading.Thread(target=work,daemon=True).start()
    def offer(self,info):
        self.info=info;self.state='offer'
        self.view.complete(f"Version {info['version']} available.")
        if load_auto_update() and info['version']!=failed_update():self.install()
        else:self.view.actions([('Install update',self.install),('Open tracker',self.continue_tracker)])
    def poll(self):
        self.poll_job=None
        if self.state=='closed':return
        try:
            while True:
                kind,value=self.q.get_nowait()
                if kind=='checked' and self.state=='checking':
                    if value:self.offer(value)
                    else:
                        self.view.complete('You are up to date.');self.state='ready'
                        self.root.after(350,self.continue_tracker)
                elif kind=='stage':self.view.stage(value)
                elif kind=='bytes':self.view.bytes(*value)
                elif kind=='error':
                    self.state='error';self.view.error(value)
                    self.view.actions([('Open tracker',self.continue_tracker)])
                elif kind=='staged':
                    root,staging,version=value
                    self.state='handoff';self.view.stage('Installing verified update…')
                    try:launch_helper(root,staging,version)
                    except Exception as e:
                        shutil.rmtree(staging,ignore_errors=True)
                        self.state='error';self.view.error(str(e));self.view.actions([('Open tracker',self.continue_tracker)])
                    else:
                        self.root.destroy();return
        except queue.Empty:pass
        if self.state!='closed':self.poll_job=self.root.after(75,self.poll)
