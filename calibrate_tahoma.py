"""Offline Tahoma rasterisation comparison. Never feeds live OCR.

Run on Windows with locally installed Tahoma regular/bold. Outputs only
aggregate scores and character coverage, not font files or rendered glyphs.
"""
import argparse,json,os,string
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from font_library import verified_profiles

CHARACTERS=string.ascii_letters+string.digits+string.punctuation
COVERAGE_THRESHOLDS=(80,112,140,175,210,240)

def trim(mask):
    y,x=np.nonzero(mask)
    return mask[y.min():y.max()+1,x.min():x.max()+1] if len(x) else None

def render_character(font,char):
    # Render in an oversized canvas before trimming; never resize a glyph.
    box=font.getbbox(char)
    w=max(1,box[2]-box[0]);h=max(1,box[3]-box[1])
    im=Image.new('L',(w+8,h+8))
    ImageDraw.Draw(im).text((4-box[0],4-box[1]),char,font=font,fill=255)
    return np.asarray(im)

def candidate_library(font,threshold):
    """Generate the complete printable non-space ASCII candidate inventory."""
    result={}
    for char in CHARACTERS:
        mask=trim(render_character(font,char)>=threshold)
        if mask is not None:result[char]=mask
    return result

def compare(candidates,reference):
    """Exact agreement and best same-dimension agreement, per known char."""
    known=len(reference);exact=0;shape=0;similarities=[]
    for char,variants in reference.items():
        glyph=candidates.get(char)
        scores=[1-float(np.mean(glyph!=v)) for v in variants if glyph is not None and glyph.shape==v.shape]
        best=max(scores,default=0.)
        shape+=bool(scores);exact+=best==1.;similarities.append(best)
    return dict(known=known,exact=exact,same_dimensions=shape,mean_agreement=round(sum(similarities)/known,4) if known else 0.)

def run_calibration(font_dir,sizes=range(8,25)):
    references=verified_profiles()
    rankings={p:[] for p in references}
    available=[];missing=[]
    for style,name in (('Regular','tahoma.ttf'),('Bold','tahomabd.ttf')):
        path=Path(font_dir)/name
        if not path.is_file():missing.append(name);continue
        available.append(name)
        for size in sizes:
            font=ImageFont.truetype(str(path),size)
            # Render once per size and weight; threshold the same pixels.
            rasters={char:render_character(font,char) for char in CHARACTERS}
            for threshold in COVERAGE_THRESHOLDS:
                candidates={char:m for char,a in rasters.items() if (m:=trim(a>=threshold)) is not None}
                for profile,reference in references.items():
                    score=compare(candidates,reference)
                    rankings[profile].append(dict(weight=style,pixels=size,coverage_threshold=threshold,candidate_characters=len(candidates),**score))
    for p,rows in rankings.items():
        rows.sort(key=lambda r:(r['exact'],r['mean_agreement'],r['same_dimensions']),reverse=True)
        rankings[p]=rows[:5]
    return dict(status='offline_candidates_only',font_files_found=available,font_files_missing=missing,
                verified_characters={p:''.join(sorted(ref)) for p,ref in references.items()},
                best_candidates=rankings,
                notes='Pillow rasterisation and coverage thresholds are hypotheses, not the game renderer. Exact glyph agreement alone does not validate spacing, messages or live capture.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font-dir',type=Path,default=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts')
    parser.add_argument('--min-size',type=int,default=8)
    parser.add_argument('--max-size',type=int,default=24)
    args=parser.parse_args()
    if not 6<=args.min_size<=args.max_size<=40:parser.error('sizes must be between 6 and 40 pixels')
    report=run_calibration(args.font_dir,range(args.min_size,args.max_size+1))
    print(json.dumps(report,indent=2))
    return 0 if report['font_files_found'] else 1

if __name__=='__main__':raise SystemExit(main())
