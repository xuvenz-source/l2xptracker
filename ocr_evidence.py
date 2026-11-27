"""Opt-in bounded local evidence. Nothing is written until explicit export."""
import io,json,threading,zipfile
from collections import deque
from PIL import Image
from version import VERSION

def png(image):
    out=io.BytesIO()
    image.save(out,format='PNG')
    return out.getvalue()

class OcrEvidence:
    def __init__(self):
        self.lock=threading.Lock()
        self.failures=deque(maxlen=12);self.successes=deque(maxlen=4)
        self.context=None
    def frame(self,rgb,alignment,pitch):
        # Only the already selected chat region, never the full desktop.
        if rgb.shape[0]*rgb.shape[1]>1000000:return
        try:
            data=png(Image.fromarray(rgb))
            with self.lock:self.context=(data,dict(configured_pitch=pitch,alignment=list(alignment) if alignment else None))
        except Exception:pass
    def record(self,row,group,passes,kind,text):
        if row.shape[0]*row.shape[1]>180000:return
        try:
            sample=(png(Image.fromarray(row)),tuple(passes),dict(group=list(group),kind=kind,text=text,row_shape=list(row.shape)))
            with self.lock:
                bucket=self.failures if kind.startswith('uncertain') or kind in ('xp_partial','sp_partial') else self.successes
                bucket.append(sample)
        except Exception:pass
    def count(self):
        with self.lock:return len(self.failures),len(self.successes)
    def export(self,path,metadata):
        with self.lock:
            entries=list(self.failures)+list(self.successes);context=self.context
        if not entries:raise ValueError('No OCR evidence yet. Enable collection, start a session and generate chat messages.')
        manifest=dict(version=VERSION,**metadata,samples=[],context=None)
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            if context:
                data,info=context
                archive.writestr('latest-queued-chat.png',data)
                manifest['context']=dict(info,note='Latest queued frame; may not correspond to individual review rows.')
            for i,(raw,passes,info) in enumerate(entries,1):
                prefix=f'row-{i:02d}'
                archive.writestr(prefix+'/raw.png',raw)
                entry=dict(info,folder=prefix,passes=[])
                for j,(data,result,nearest) in enumerate(passes,1):
                    name=f'ocr-{j:02d}.png'
                    archive.writestr(prefix+'/'+name,data)
                    entry['passes'].append(dict(image=name,text=result,nearest=nearest))
                manifest['samples'].append(entry)
            archive.writestr('manifest.json',json.dumps(manifest,indent=2,ensure_ascii=False))
