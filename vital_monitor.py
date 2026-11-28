"""Independent, bounded passive sampling for live HP/MP widgets."""
import queue,threading
from collections import OrderedDict
import numpy as np
from leveling import binding_for
from vitals import crop_bar,bar_fraction,read_vital_pair,display_value,vital_signature,compatible_pair

CACHE_LIMIT=96
RETRY_SECONDS=.75
CHANGE_INTERVAL=.35

class VitalMonitor:
    def __init__(self):
        self.frames=queue.Queue();self.numbers=queue.Queue()
        self.capture_busy=False;self.ocr_busy=set();self.key=None
        self.next_capture=0;self.sample=None;self.readings={};self.invalid_since=0
        self.clear_evidence()
    def tick(self,a,config,generation,now):
        layout=config.get('vitals');target=a.target
        gate=a.pause_gate
        paused,revision,focus_only=gate.capture_policy()
        active=bool(layout and target and config['binding']==binding_for(target) and a.running and not paused and not a.selecting)
        key=(generation,revision,a.run_id,target.hwnd,target.pid) if active else None
        if key!=self.key:
            self.key=key;self.sample=None;self.next_capture=0;self.invalid_since=now
            self.clear_evidence()
        while True:
            try:token,stamp,rgb=self.frames.get_nowait()
            except queue.Empty:break
            self.capture_busy=False
            if token!=key or key is None:continue
            if rgb is None:
                self.sample=None;self.invalid_since=stamp;self.clear_evidence();continue
            bars={k:crop_bar(rgb,r) for k,r in layout['bars'].items()}
            fractions={k:bar_fraction(b,k) for k,b in bars.items()}
            # Keep the fill crop exact; the text reader needs one extra row
            # on each side to preserve antialiased digit strokes.
            numeric_bars={k:rgb[max(0,r['top']-1):r['top']+r['height']+1,r['left']:r['left']+r['width']] for k,r in layout['bars'].items()}
            self.sample=(stamp,fractions)
            self.latest={k:(stamp,bar,fractions[k],vital_signature(bar)) for k,bar in numeric_bars.items() if fractions[k] is not None}
        while True:
            try:token,stamp,k,signature,seen_fraction,result=self.numbers.get_nowait()
            except queue.Empty:break
            self.ocr_busy.discard(k)
            if token==key and key is not None and stamp>=self.invalid_since and compatible_pair(result,seen_fraction):
                self.remember(k,signature,result)
        # Only the newest capture is scheduled. Old results may populate
        # the cache, but cannot overwrite different current pixels.
        for k,(stamp,bar,fraction,signature) in self.latest.items():
            if key is None or now-stamp>1.5 or k in self.ocr_busy:continue
            if self.cached(k,signature,fraction) is not None:continue
            previous,last=self.attempts.get(k,(None,-1e9))
            if now-last<(RETRY_SECONDS if signature==previous else CHANGE_INTERVAL):continue
            self.ocr_busy.add(k);self.attempts[k]=(signature,now)
            def read(token=key,stamp=stamp,k=k,bar=bar,fraction=fraction,signature=signature):
                result=None
                try:result=read_vital_pair(bar,fraction)
                except Exception:pass
                finally:self.numbers.put((token,stamp,k,signature,fraction,result))
            threading.Thread(target=read,daemon=True).start()
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
        values={};self.readings={}
        for k in ('hp','mp'):
            fraction=self.sample[1].get(k) if active and self.sample and now-self.sample[0]<=1.5 else None
            latest=self.latest.get(k)
            pair=self.cached(k,latest[3],fraction) if latest is not None and fraction is not None else None
            self.readings[k]=(fraction,pair)
            values[k]=(k.upper(),display_value(fraction,pair))
        return values

    def clear_evidence(self):
        self.cache={k:OrderedDict() for k in ('hp','mp')}
        self.attempts={};self.latest={}

    def remember(self,k,signature,pair):
        cache=self.cache[k]
        if signature in cache and cache[signature]!=pair:
            cache[signature]=None
        else:cache[signature]=pair
        cache.move_to_end(signature)
        while len(cache)>CACHE_LIMIT:cache.popitem(last=False)

    def cached(self,k,signature,fraction):
        cache=self.cache[k];pair=cache.get(signature)
        if not compatible_pair(pair,fraction):return None
        cache.move_to_end(signature)
        return pair
