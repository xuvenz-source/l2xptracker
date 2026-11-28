"""Research-only Pillow vs Windows GDI Tahoma comparison.

Rank on isolated verified glyphs; report complete-word shape and spacing
agreement separately. Never promote candidates or alter live templates.
"""
import argparse,json,os,sys
from pathlib import Path
import numpy as np
from PIL import ImageFont
from font_library import verified_profiles,large_library,chat_library,packed_mask,mask_string
from calibrate_tahoma import CHARACTERS,COVERAGE_THRESHOLDS,trim,render_character,compare
from gdi_tahoma import GdiTahoma,QUALITIES

def word_profiles():
    profiles={p:{} for p in ('Large chat','Medium chat','Small chat')}
    def add(profile,label,mask):
        mask=trim(mask)
        if mask is not None:profiles[profile].setdefault(label,{})[mask_string(mask)]=mask
    for label,variants in large_library()['words'].items():
        for mask in variants:add('Large chat',label,mask)
    for key,labels in chat_library().items():
        profile=key.split(':',1)[0]+' chat'
        for label,variants in labels.items():
            if not label.startswith('w:'):continue
            for shape,bits in variants:
                h,w=map(int,shape.split('x'))
                add(profile,label[2:],packed_mask(h,w,bits.to_bytes((h*w+7)//8,'big')))
    return {p:{k:tuple(v.values()) for k,v in group.items()} for p,group in profiles.items()}

def details(candidates,reference):
    exact=[];conflicts=[]
    for label,variants in reference.items():
        glyph=candidates.get(label)
        if glyph is None:continue
        matches=lambda v:glyph.shape==v.shape and np.array_equal(glyph,v)
        if any(matches(v) for v in variants):exact.append(label)
        others=[other for other,vs in reference.items() if other!=label and any(matches(v) for v in vs)]
        if others:conflicts.append(dict(label=label,also_matches=sorted(others)))
    return dict(exact_labels=sorted(exact),cross_label_conflicts=conflicts)

def evaluate(rasters,refs,words,parameters,rankings):
    for threshold in COVERAGE_THRESHOLDS:
        masks={label:m for label,gray in rasters.items() if (m:=trim(gray>=threshold)) is not None}
        for profile,reference in refs.items():
            score=compare(masks,reference)
            # Words are not included in the ranking, so this check tests
            # whether the chosen digit parameters reproduce word spacing.
            word_score=compare(masks,words.get(profile,{}))
            rankings[profile].append(dict(**parameters,coverage_threshold=threshold,
                candidate_characters=sum(c in masks for c in CHARACTERS),
                **score,words=word_score,**details(masks,reference)))

def sort_key(r):
    return (r['exact'],r['mean_agreement'],r['same_dimensions'],-len(r['cross_label_conflicts']))

def run(font_dir,sizes=range(8,21),include_gdi=True):
    refs=verified_profiles();words=word_profiles()
    labels=tuple(sorted(set(CHARACTERS).union(*(set(v) for v in words.values()))))
    rankings={p:[] for p in refs};errors=[];rendered=0;sizes=tuple(sizes)
    for weight,name,numeric in (('Regular','tahoma.ttf',400),('Bold','tahomabd.ttf',700)):
        path=Path(font_dir)/name
        if path.is_file():
            for size in sizes:
                font=ImageFont.truetype(str(path),size)
                evaluate({label:render_character(font,label) for label in labels},refs,words,
                         dict(renderer='Pillow',weight=weight,pixels=size,height_mode='Character',quality='Pillow default'),rankings)
                rendered+=1
        if include_gdi and sys.platform=='win32':
            for size in sizes:
                for mode in ('Character','Cell'):
                    for quality,number in QUALITIES.items():
                        try:
                            with GdiTahoma(size,numeric,number,mode) as font:
                                rasters={label:font.render(label) for label in labels}
                        except (OSError,ValueError) as exc:
                            errors.append(dict(weight=weight,pixels=size,height_mode=mode,quality=quality,error=str(exc)));continue
                        evaluate(rasters,refs,words,dict(renderer='GDI',weight=weight,pixels=size,height_mode=mode,quality=quality),rankings)
                        rendered+=1
    best={}
    for profile,rows in rankings.items():
        rows.sort(key=sort_key,reverse=True)
        best[profile]={'Pillow':[r for r in rows if r['renderer']=='Pillow'][:3],
                       'GDI':[r for r in rows if r['renderer']=='GDI'][:3]}
    return dict(status='research_only',platform=sys.platform,rendered_configurations=rendered,
                threshold_combinations=rendered*len(COVERAGE_THRESHOLDS),gdi_requested=include_gdi,
                gdi_errors=len(errors),example_errors=errors[:5],
                reference_characters={p:''.join(sorted(v)) for p,v in refs.items()},
                reference_words={p:sorted(v) for p,v in words.items()},best=best,
                notes='Word comparison uses existing game-derived word templates, not independent holdout accuracy. Requested ClearType may be downgraded by a memory DC. No generated templates are activated.')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--font-dir',type=Path,default=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts')
    p.add_argument('--min-size',type=int,default=8);p.add_argument('--max-size',type=int,default=20)
    p.add_argument('--no-gdi',action='store_true');p.add_argument('--output',type=Path)
    a=p.parse_args()
    if not 6<=a.min_size<=a.max_size<=40:p.error('sizes must be between 6 and 40')
    report=run(a.font_dir,range(a.min_size,a.max_size+1),not a.no_gdi)
    result=json.dumps(report,indent=2)
    if a.output:a.output.write_text(result+'\n',encoding='utf-8')
    print(result)
    if not report['rendered_configurations']:return 1
    if sys.platform=='win32' and not a.no_gdi and not any(v['GDI'] for v in report['best'].values()):return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
