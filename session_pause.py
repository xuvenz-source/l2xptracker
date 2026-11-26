"""Manual capture gate. A revision detects pause/resume between sampled frames."""
import threading

class PauseGate:
    def __init__(self):
        self.lock=threading.Lock()
        self.paused=False
        self.revision=0
    def snapshot(self):
        with self.lock:return self.paused,self.revision
    def toggle(self):
        with self.lock:
            self.paused=not self.paused
            self.revision+=1
            return self.paused
    def accepts(self, revision):
        # Caller must hold lock while committing a captured frame.
        return not self.paused and self.revision==revision
