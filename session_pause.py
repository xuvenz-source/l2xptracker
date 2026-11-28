"""Manual capture gate. A revision detects pause/resume between sampled frames."""
import threading

class PauseGate:
    def __init__(self,pause_on_blur=False):
        self.lock=threading.Lock()
        self.paused=False
        self.revision=0
        self.pause_on_blur=bool(pause_on_blur)
        self.binding=None
    def snapshot(self):
        with self.lock:return self.paused,self.revision
    def capture_policy(self):
        with self.lock:return self.paused,self.revision,self.pause_on_blur
    def capture_context(self,target,region):
        with self.lock:
            if self.binding is not None:target,region=self.binding
            return self.paused,self.revision,self.pause_on_blur,target,dict(region)
    def replace_binding(self,target,region):
        with self.lock:
            if not self.paused:raise RuntimeError('Pause tracking before changing bound areas.')
            self.binding=(target,dict(region));self.revision+=1
    def set_focus_policy(self,value):
        with self.lock:
            if self.pause_on_blur!=bool(value):
                self.pause_on_blur=bool(value);self.revision+=1
    def toggle(self):
        with self.lock:
            self.paused=not self.paused
            self.revision+=1
            return self.paused
    def accepts(self, revision):
        # Caller must hold lock while committing a captured frame.
        return not self.paused and self.revision==revision
