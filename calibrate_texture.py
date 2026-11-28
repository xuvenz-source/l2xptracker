"""Offline font-texture hypotheses: source raster, scaling, sampling phase.

Neither this script nor its JSON results are imported by live recognition.
Fit on verified glyphs; score held-out chat fixtures only after selection.
"""
import ast,base64,json,sys,zlib,argparse
from pathlib import Path
from itertools import product
import numpy as np
from PIL import Image
from font_library import verified_profiles,mask_string
from calibrate_tahoma import trim,compare,COVERAGE_THRESHOLDS
from calibrate_rasterisation import word_profiles,details
from gdi_tahoma import GdiTahoma
from chat_native import THRESHOLDS,PATTERNS,colour_mask,parts,recognise

TARGETS={'Fixed status':(10,11,12),'Level badge':(10,11,12),
         'Large chat':(15,16,17),'Medium chat':(12,13,14),'Small chat':(11,12,13)}
SOURCES=(10,11,12,13,14,16,20,24,32)
FILTERS={'Nearest':Image.Resampling.NEAREST,'Bilinear':Image.Resampling.BILINEAR,'Box':Image.Resampling.BOX}
PHASES=((0.,0.),(.5,0.),(0.,.5),(.5,.5))
QUALITIES={'Monochrome':3,'Grayscale':4,'Default':0}

def sample_texture(raster,source,target,filter_name,phase):
    """Scale full padded raster with fractional sampling origin.

    Preserve source bearings/spacing rather than scaling trimmed glyphs.
    A hypothesis, not an assertion about the client's renderer.
    """
    if source<=0 or target<=0:raise ValueError('Invalid font size')
    ratio=source/target
    a=np.pad(np.asarray(raster,dtype=np.uint8),4)
    w,h=a.shape[1],a.shape[0]
    ow=max(1,int((w-ratio)/ratio));oh=max(1,int((h-ratio)/ratio))
    x,y=(p*ratio for p in phase)
    # PIL resize box accepts fractional coordinates, including BOX filtering.
    return np.asarray(Image.fromarray(a).resize((ow,oh),FILTERS[filter_name],
        box=(x,y,x+ow*ratio,y+oh*ratio)))

def mask_at(raster,t):
    return trim(raster>=t)

def add_reference(groups,profile,label,mask):
    mask=trim(mask)
    if mask is not None:groups.setdefault(profile,{}).setdefault(label,{})[mask_string(mask)]=mask

def holdout_words(path=None):
    """Read existing labelled held-out chat fixture, not the training library.

    Only rows whose expected result is confirmed by the original full-line
    recogniser are segmented; report how many were usable. No new labels
    are inferred from OCR or candidate renderers.
    """
    path=Path(path) if path else Path(__file__).parent/'tests'/'test_chat_native.py'
    tree=ast.parse(path.read_text(encoding='utf-8'))
    data=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
              and any(isinstance(t,ast.Name) and t.id=='DATA' for t in node.targets))
    groups={};used=0;total=0
    for size,kind,text,expected,shape,lo,hi in json.loads(zlib.decompress(base64.b64decode(data))):
        if expected is None:continue
        total+=1;row=np.zeros((*shape,3),np.uint8)
        for threshold,bits in zip(THRESHOLDS[kind],(lo,hi)):
            mask=np.unpackbits(np.frombuffer(bytes.fromhex(bits),np.uint8),count=shape[0]*shape[1]).reshape(shape).astype(bool)
            i=255 if threshold==THRESHOLDS[kind][-1] else threshold
            row[mask]=(i,0,i) if kind=='xp' else (i,i,0) if kind=='adena' else (0,170,i)
        if recognise(row,kind)!=tuple(expected):continue
        used+=1
        for t in THRESHOLDS[kind]:
            mask=colour_mask(row,kind,t);words=parts(mask,4 if size=='Small' else 5)
            if len(words)!=len(PATTERNS[kind]):continue
            for label,(a,b) in zip(PATTERNS[kind],words):
                if label is not None:add_reference(groups,size+' chat',label,mask[:,a:b])
    return {p:{k:tuple(v.values()) for k,v in group.items()} for p,group in groups.items()},dict(eligible_rows=total,usable_rows=used)

def rank_key(row):
    return (row['exact'],row['mean_agreement'],row['same_dimensions'])

def shortlist(rows,limit=8):
    # Do not let identical phase/threshold results monopolise the shortlist.
    rows.sort(key=rank_key,reverse=True);out=[];seen=set()
    for r in rows:
        key=(r['source'],r['target'],r['weight'],r['quality'],r['filter'],tuple(r['phase']))
        if key in seen:continue
        seen.add(key);out.append(r)
        if len(out)==limit:break
    return out

def run():
    refs=verified_profiles();words=word_profiles();holdout,coverage=holdout_words()
    glyphs=sorted(set().union(*(set(v) for v in refs.values())))
    ranks={p:[] for p in refs};trials=0
    targets=sorted(set().union(*TARGETS.values()))
    for source,weight,quality in product(SOURCES,('Regular','Bold'),QUALITIES):
        with GdiTahoma(source,400 if weight=='Regular' else 700,QUALITIES[quality]) as font:
            rasters={c:font.render(c) for c in glyphs}
        for target,filter_name,phase in product(targets,FILTERS,PHASES):
            relevant=[p for p in refs if target in TARGETS[p]]
            if not relevant:continue
            scaled={c:sample_texture(a,source,target,filter_name,phase) for c,a in rasters.items()}
            for threshold in COVERAGE_THRESHOLDS:
                masks={c:m for c,a in scaled.items() if (m:=mask_at(a,threshold)) is not None}
                trials+=1
                for p in relevant:
                    ranks[p].append(dict(source=source,target=target,weight=weight,quality=quality,
                        filter=filter_name,phase=phase,threshold=threshold,**compare(masks,refs[p])))
    best={}
    for p,rows in ranks.items():
        best[p]=[]
        for r in shortlist(rows):
            labels=set(refs[p])|set(words.get(p,{}))|set(holdout.get(p,{}))
            with GdiTahoma(r['source'],400 if r['weight']=='Regular' else 700,QUALITIES[r['quality']]) as font:
                def masks_for(tracking):
                    out={}
                    for label in labels:
                        raster=font.render(label,tracking if len(label)>1 else 0)
                        a=sample_texture(raster,r['source'],r['target'],r['filter'],r['phase'])
                        m=mask_at(a,r['threshold'])
                        if m is not None:out[label]=m
                    return out
                # Tune tracking on training words only; the held-out score
                # is never used to choose source, phase, threshold or spacing.
                choices=[]
                for tracking in (-1,0,1,2):
                    masks=masks_for(tracking);score=compare(masks,words.get(p,{}))
                    choices.append((tracking,score,masks))
                tracking,score,masks=max(choices,key=lambda v:(v[1]['exact'],v[1]['mean_agreement'],v[1]['same_dimensions'],-abs(v[0])))
                best[p].append(dict(**r,tracking_source_px=tracking,training_words=score,
                    heldout_words=compare(masks,holdout.get(p,{})),**details(masks,refs[p])))
    return dict(status='research_only',threshold_combinations=trials,holdout_coverage=coverage,
        reference_characters={p:''.join(sorted(v)) for p,v in refs.items()},
        best=best,notes='Held-out word labels repeat training vocabulary. This is pixel-shape generalisation, not independent OCR accuracy. Parameters are hypotheses; no runtime templates changed.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args()
    if sys.platform!='win32':p.error('Windows GDI and installed Tahoma required')
    report=run();result=json.dumps(report,indent=2)
    if a.output:a.output.write_text(result+'\n',encoding='utf-8')
    print(result)

if __name__=='__main__':main()
