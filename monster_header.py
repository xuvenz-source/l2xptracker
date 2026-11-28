"""Independent OCR fields from the top of a cropped monster information window."""
import re
from PIL import Image,ImageOps

def split_name(text):
    text=text.strip()
    m=re.fullmatch(r"(.*?)[,\s]+L[vV][.,:]?\s*(\d{1,3})\s*[.]?",text,re.I)
    if not m:return text,''
    name=m[1].strip(' ,.|\\')
    if name.startswith('Q '):name=name[2:].strip()
    level=int(m[2])
    return name,str(level) if 1<=level<=100 else ''

def labelled_rewards(text):
    def field(label):
        m=re.search(r'\b'+label+r'\s*[:;]\s*([0-9]+(?:,[0-9]{3})*)(?![\d,/.])',text,re.I)
        return m[1].replace(',','') if m else ''
    return field('(?:EXP|XP)'),field('SP')

def read_header(image,whole_text,monster,ocr):
    w,h=image.size
    warnings=[]
    def read(box,mode,numeric=False):
        a=ImageOps.grayscale(image.crop(tuple(round(v*n) for v,n in zip(box,(w,h,w,h)))))
        a=ImageOps.invert(a) if mode==0 else a.point(lambda n:0 if n>115 else 255)
        a=a.resize((a.width*3,a.height*3),Image.Resampling.LANCZOS)
        return ocr(a,config='--psm 7'+(' -c tessedit_char_whitelist=0123456789,' if numeric else ''),timeout=8).strip()
    name,level=split_name(monster)
    # Whole-table OCR normally reads the title correctly. Dedicated title
    # crop is a fallback, with enough width for longer names.
    if not name or not level:
        candidates=[split_name(read((.04,.09,.96,.15),m)) for m in (0,1)]
        if candidates[0]==candidates[1] and all(candidates[0]):name,level=candidates[0]
    hints=labelled_rewards(whole_text)
    values=[]
    for label,box,hint in [('EXP',(.28,.155,.48,.23),hints[0]),('SP',(.73,.155,.95,.23),hints[1])]:
        reads=[]
        for mode in (0,1):
            v=read(box,mode,True)
            if re.fullmatch(r'(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)',v):reads.append(str(int(v.replace(',',''))))
        # Never silently resolve conflicting readings. A missing label in
        # the whole-window pass must not invalidate agreeing numeric crops.
        if len(reads)==2 and reads[0]==reads[1] and (not hint or hint==reads[0]):
            value=reads[0]
        elif len(reads)==1 and hint==reads[0]:value=reads[0]
        else:value='';warnings.append('Verify base '+label+' manually (inconsistent or unreadable OCR).')
        values.append(value)
    if not level:warnings.append('Verify monster level manually.')
    return dict(name=name,level=level,xp=values[0],sp=values[1]),warnings
