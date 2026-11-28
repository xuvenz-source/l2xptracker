"""Independent, bounded passive sampling for live HP/MP widgets."""
import queue,threading
import numpy as np
from leveling import binding_for
from vitals import crop_bar,bar_fraction,read_vital_pair,display_value

class VitalMonitor:
    def __init__(self):
        self.frames=queue.Queue();self.numbers=queue.Queue()
        self.capture_busy=False;self.ocr_busy=False;self.key=None
        self.next_capture=0;self.next_ocr=0;self.sample=None;self.exact={}
    def tick(self,a,config,generation,now):
        layout=config.get('vitals');target=a.target
        gate=a.pause_gate
        paused,revision,focus_only=gate.capture_policy()
        active=bool(layout and target and config['binding']==binding_for(target) and a.running and not paused and not a.selecting)
        key=(generation,revision,a.run_id,target.hwnd,target.pid) if active else None
        if key!=self.key:
            self.key=key;self.sample=None;self.exact={};self.next_capture=0;self.next_ocr=0
        while True:
            try:token,stamp,rgb=self.frames.get_nowait()
            except queue.Empty:break
            self.capture_busy=False
            if token!=key or key is None:continue
            if rgb is None:
                self.sample=None;self.exact={};continue
            bars={k:crop_bar(rgb,r) for k,r in layout['bars'].items()}
            fractions={k:bar_fraction(b,k) for k,b in bars.items()}
            self.sample=(stamp,fractions)
            if not self.ocr_busy and now>=self.next_ocr and any(v is not None for v in fractions.values()):
                self.ocr_busy=True;self.next_ocr=now+2
                def read(token=token,stamp=stamp,bars=bars,fractions=fractions):
                    result={}
                    try:
                        for k,b in bars.items():result[k]=read_vital_pair(b,fractions[k])
                    except Exception:pass
                    finally:self.numbers.put((token,stamp,result))
                threading.Thread(target=read,daemon=True).start()
        while True:
            try:token,stamp,result=self.numbers.get_nowait()
            except queue.Empty:break
            self.ocr_busy=False
            if token==key and key is not None:self.exact={k:(stamp,v) for k,v in result.items() if v is not None}
        if active and not self.capture_busy and now>=self.next_capture:
            self.capture_busy=True;self.next_capture=now+.25
            region=dict(layout['frame'])
            def capture(token=key,stamp=now,target=target,region=region,revision=revision,focus_only=focus_only):
                rgb=None
                try:
                    import mss
                    from window_focus import Windows,capture_region
                    api=Windows()
                    with mss.mss() as screen:
                        rect,_=capture_region(api,target,region,screen.monitors[0],pause_on_blur=focus_only)
                        if rect:
                            shot=screen.grab(rect)
                            if capture_region(api,target,region,screen.monitors[0],pause_on_blur=focus_only)[0]==rect:
                                rgb=np.asarray(shot)[:,:,:3][:,:,::-1].copy()
                    with gate.lock:
                        if not gate.accepts(revision):rgb=None
                except Exception:rgb=None
                finally:self.frames.put((token,stamp,rgb))
            threading.Thread(target=capture,daemon=True).start()
        values={}
        for k in ('hp','mp'):
            fraction=self.sample[1].get(k) if active and self.sample and now-self.sample[0]<=1.5 else None
            stamp,pair=self.exact.get(k,(0,None))
            if fraction is None or pair is None or now-stamp>4 or abs(pair[0]/pair[1]-fraction)>.015:pair=None
            values[k]=(k.upper(),display_value(fraction,pair))
        return values
