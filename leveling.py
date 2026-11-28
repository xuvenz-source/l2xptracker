"""Native C1 XP curve and passive player-status OCR."""
from decimal import Decimal
from math import ceil
from bisect import bisect_right
from itertools import accumulate
import re,time
from preferences import read_preferences,write_preference

# XP needed to fill each bar, native C1: https://l2tools.org/c1/tools/xp-curve
XP=(68,295,805,1716,3154,5249,8136,11955,16851,22973,30475,39516,50261,62876,77537,94421,113712,135596,160266,187922,218762,252997,290836,332497,378201,428173,482647,541857,606042,675450,750330,830937,917531,1010378,1109744,1215906,1329143,1449736,1577978,1714158,1858578,2011538,2173347,2344318,2524767,2715019,2915398,3126237,3347873,5370971,5737357,6121498,6523923,6945178,9847742,10461823,11103227,11772715,12471057,19798547,20936137,22120557,23353014,24634736,34622619,36467935,38383956,40372393,42434976,44573456,58487000,73627796,90058594,107843995,127050464)
TOTAL=(0,*accumulate(XP))
DEFAULT=dict(mode='auto',cap=60,interval=2,regions={},binding=None)

def clean_status(raw):
    out=dict(DEFAULT,regions={})
    if not isinstance(raw,dict):return out
    for key,allowed in [('mode',('auto','manual')),('interval',(1,2,5,10))]:
        if raw.get(key) in allowed:out[key]=raw[key]
    if type(raw.get('cap')) is int and 2<=raw['cap']<=75:out['cap']=raw['cap']
    binding=raw.get('binding')
    if isinstance(binding,list) and len(binding)==4 and all(isinstance(x,str) for x in binding[:2]) and all(type(x) is int and x>0 for x in binding[2:]):
        out['binding']=binding
        regions=raw.get('regions',{})
        if isinstance(regions,dict):
            for key in ('level','percent'):
                r=regions.get(key)
                if isinstance(r,dict) and all(type(r.get(k)) is int for k in ('left','top','width','height')) and min(r['left'],r['top'])>=0 and min(r['width'],r['height'])>=3 and r['left']+r['width']<=binding[2] and r['top']+r['height']<=binding[3]:out['regions'][key]=r
        from vitals import clean_vitals
        vitals=clean_vitals(raw.get('vitals'),binding[2],binding[3])
        if vitals is not None:out['vitals']=vitals
    return out

def load_status(path=None):return clean_status(read_preferences(path).get('player_status'))
def save_status(value,path=None):write_preference('player_status',clean_status(value),path)
def binding_for(target):return [target.title,target.window_class,target.width,target.height]
def manual_values(level,percent,cap):
    """Accept displayed percentages, including a trailing percent sign."""
    level=str(level).strip();percent=str(percent).strip().removesuffix('%').strip()
    if not re.fullmatch(r'[0-9]{1,2}',level) or not re.fullmatch(r'[0-9]{1,3}(?:\.[0-9]{1,8})?',percent):
        raise ValueError('Enter a whole level and XP percentage from 0 to 100.')
    lv=int(level);pct=Decimal(percent)
    if not 1<=lv<=cap or not 0<=pct<=100:raise ValueError(f'Level must be 1–{cap}; XP percentage must be 0–100.')
    return lv,pct

def xp_after(events,anchor):
    """Only personal verified XP captured after the entered balance."""
    return sum(e[4] for e in events if e[0]>anchor and e[1]=='xp' and e[2].casefold()=='you' and type(e[4]) is int and e[4]>=0)

def absolute_xp(level,percent):
    p=Decimal(str(percent))
    if not 1<=level<=75 or not p.is_finite() or not 0<=p<=100:raise ValueError('Invalid level or XP percentage')
    return Decimal(TOTAL[level-1])+Decimal(XP[level-1])*p/100
def from_absolute(value,cap):
    level=min(cap,max(1,bisect_right(TOTAL,value)))
    pct=max(Decimal(0),min(Decimal(100),(value-TOTAL[level-1])*100/XP[level-1]))
    return level,pct
def eta(level,pct,xp,seconds,cap):
    if level is None:return '—',None
    if level>=cap:return 'MAX',0
    remaining=ceil(Decimal(XP[level-1])*(100-Decimal(str(pct)))/100)
    if seconds<30 or xp<=0:return 'Calc…',remaining
    minutes=ceil(remaining*seconds/xp/60)
    h,m=divmod(minutes,60)
    return (f'{h}h {m:02}m' if h else f'{m}m'),remaining

def parse_number(text,kind):
    text=text.strip()
    if kind=='level':
        return int(text) if re.fullmatch(r'\d{1,2}',text) and 1<=int(text)<=75 else None
    # OCR may insert spaces around the printed decimal point or percent sign.
    # Never infer a missing decimal point, percent sign or digit.
    m=re.fullmatch(r'([0-9]{1,3})\s*\.\s*([0-9]{1,2})\s*%',text)
    if not m:return None
    p=Decimal(m[1]+'.'+m[2])
    return p if 0<=p<=100 else None

def read_number(image,kind):
    """Try fixed native glyphs first; retain the established OCR fallback."""
    from status_digits import recognise_status
    try:value=recognise_status(image,kind)
    except Exception:
        from diagnostics import diagnostic
        diagnostic('Status glyph recognition failed; using OCR',exc_info=True)
        value=None
    if value is not None:return value
    return read_number_ocr(image,kind)

def read_number_ocr(image,kind):
    """Read small native status glyphs independently of chat text size."""
    from PIL import ImageOps,Image
    import pytesseract
    if kind not in ('level','percent') or min(image.size)<3:return None
    gray=ImageOps.grayscale(image)
    scaled=gray.resize((gray.width*6,gray.height*6),Image.Resampling.LANCZOS)
    whitelist='0123456789' if kind=='level' else '0123456789.%'
    reads=[]
    def read(mask,psm):
        try:
            value=parse_number(pytesseract.image_to_string(mask,config=f'--psm {psm} -c tessedit_char_whitelist={whitelist}',timeout=3),kind)
        except RuntimeError:value=None
        if value is not None:reads.append(value)
    def agreed():return reads[0] if len(reads)>=2 and len(set(reads))==1 else None
    def mask(source,threshold):
        return ImageOps.expand(source.point(lambda p:255 if p<threshold else 0),border=12,fill=255)
    # Preserve the existing fast path for clean, tightly calibrated fields.
    for threshold in (100,125):read(mask(scaled,threshold),7)
    if len(set(reads))>1:return None
    if agreed() is not None:return agreed()
    # Native status digits are outlined and antialiased. A third fixed
    # threshold and a local contrast stretch handle darker badge/bar text.
    # Use single-word segmentation for the level badge as a second family.
    read(mask(scaled,150),8 if kind=='level' else 7)
    if len(set(reads))>1:return None
    if agreed() is not None:return agreed()
    contrast=ImageOps.autocontrast(gray,cutoff=1).resize(scaled.size,Image.Resampling.LANCZOS)
    read(mask(contrast,125),8 if kind=='level' else 7)
    if len(set(reads))>1:return None
    if agreed() is not None:return agreed()
    # A native-resolution mask enlarged without interpolation retains fine
    # strokes that may disappear during a LANCZOS threshold pass.
    native=gray.point(lambda p:255 if p<125 else 0).resize(scaled.size,Image.Resampling.NEAREST)
    read(ImageOps.expand(native,border=12,fill=255),8 if kind=='level' else 7)
    return agreed()

class Progress:
    def __init__(self):
        self.level=None;self.percent=None;self.seen=None;self.candidate=None;self.manual_total=None;self.baseline=0
    def clear(self):self.__init__()
    def manual(self,level,pct,chat_xp):
        self.manual_total=absolute_xp(level,pct);self.baseline=chat_xp;self.level=level;self.percent=Decimal(str(pct));self.seen=time.monotonic()
    def advance(self,chat_xp,cap):
        if self.manual_total is not None:self.level,self.percent=from_absolute(max(0,self.manual_total+chat_xp-self.baseline),cap)
    def rebase(self,chat_xp,cap):
        if self.manual_total is not None:
            self.advance(chat_xp,cap);self.manual(self.level,self.percent,0)
    def observe(self,level,pct,cap,now=None):
        if level is None or pct is None or level>cap:return False
        now=time.monotonic() if now is None else now
        unusual=self.level is None or level!=self.level or abs(pct-self.percent)>Decimal(2) or pct<self.percent
        if unusual:
            old=self.candidate
            if old is None or old[0]!=level or abs(old[1]-pct)>Decimal(2) or now-old[2]>30:
                self.candidate=(level,pct,now);return False
        self.level=level;self.percent=pct;self.seen=now;self.candidate=None
        return True
