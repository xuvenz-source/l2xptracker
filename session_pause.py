"""Manual capture gate. A revision detects pause/resume between sampled frames."""
import threading

class PauseGate:
    def __init__(self,pause_on_blur=False):
        self.lock=threading.Lock()
        self.paused=False
        self.revision=0
        self.pause_on_blur=bool(pause_on_blur)
    def snapshot(self):
        with self.lock:return self.paused,self.revision
    def capture_policy(self):
        with self.lock:return self.paused,self.revision,self.pause_on_blur
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
