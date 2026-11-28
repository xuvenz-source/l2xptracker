"""Supersampled original glass globe art, shared by the HUD and settings preview."""
import os
from pathlib import Path
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from vital_globes import fill_steps

SS=3

def text_lines(value):
    # Both mode has a large percentage, with the exact value below.
    value=str(value)
    if ' - ' in value:
        exact,percent=value.split(' - ',1)
        return (percent,exact.replace('/',' / '))
    return (value.replace('/',' / '),)

@lru_cache(maxsize=6)
def art_layers(d):
    n=d*SS
    axis=(np.arange(n,dtype=np.float32)+.5)*2/n-1
    x,y=np.meshgrid(axis,axis)
    r=np.sqrt(x*x+y*y)
    # Directional metal gradient plus concentric bevels.
    light=np.clip(.52-.32*x-.38*y,0,1)
    def shade(a,b,t):
        return np.asarray(a,dtype=np.float32)+t[...,None]*(np.asarray(b,dtype=np.float32)-a)
    metal=shade((72,61,42),(185,161,109),light)
    rgb=metal.copy()
    for radius,col in ((.884,(18,18,22)),(.849,(118,99,69)),(.836,(10,11,14)),(.797,(69,57,48))):
        rgb[r<radius]=col
    cavity=r<.784
    vignette=np.clip(1-r/.82,0,1)
    dark=shade((12,13,16),(38,42,50),vignette)
    rgb[cavity]=dark[cavity]
    alpha=np.where(r<=.925,255,0).astype(np.uint8)
    # Top and bottom diamond-shaped bronze finials, like the reference.
    diamond=(np.abs(x)/.151+np.abs(np.abs(y)-.885)/.105<=1)
    diamond_inner=(np.abs(x)/.126+np.abs(np.abs(y)-.885)/.082<=1)
    finial=diamond & (np.abs(y)>=.862)
    rgb[finial]=(176,153,104)
    rgb[diamond_inner & finial]=(62,53,38)
    alpha[finial]=255
    # Elliptical glass reflection, tilted upward to the right.
    xx=x+.26;yy=y+.43
    u=.82*xx-.57*yy;v=.57*xx+.82*yy
    gloss=np.clip(1-((u/.31)**2+(v/.135)**2),0,1)**.35*.15
    gloss*=cavity
    return x,y,r,rgb.astype(np.uint8),alpha,cavity,gloss

@lru_cache(maxsize=48)
def font_at(size):
    root=Path(os.environ.get('WINDIR',r'C:\Windows'))/'Fonts'
    for path in (root/'segoeui.ttf', 'DejaVuSans.ttf'):
        try:return ImageFont.truetype(str(path),size)
        except OSError:pass
    try:return ImageFont.load_default(size=size)
    except TypeError:return ImageFont.load_default()

def centered(draw,text,n,y,size,maximum,stroke):
    font=font_at(max(8,size))
    while size>8 and draw.textbbox((0,0),text,font=font,stroke_width=stroke)[2]>maximum:
        size-=1;font=font_at(size)
    box=draw.textbbox((0,0),text,font=font,stroke_width=stroke)
    draw.text(((n-(box[2]-box[0]))/2-box[0],y-(box[3]-box[1])/2-box[1]),text,font=font,fill=(250,247,242,255),stroke_width=stroke,stroke_fill=(11,10,14,255))

@lru_cache(maxsize=24)
def _render(kind,d,steps,value):
    x,y,r,base,alpha,cavity,gloss=art_layers(d)
    rgb=base.astype(np.float32)
    if steps is None:
        rgb[cavity]=rgb[cavity]*.77+np.array((13,13,15))
    elif steps>0:
        # Fill height is proportional to the measured fraction, not guessed
        # from text. At full and empty the wave never leaves a false gap.
        surface=.784-1.568*steps/100
        wave=.045*np.sin((x+.15)*3.8)*min(1,steps/10,(100-steps)/10)
        liquid=cavity & ((y>=surface+wave) if steps<100 else True)
        depth=np.clip((y+.784)/1.568,0,1)
        hotspot=np.exp(-(((x+.28)/.40)**2+((y-surface-.13)/.35)**2))
        if kind=='hp':top=np.array((173,24,31));bottom=np.array((65,8,16));highlight=np.array((95,66,51))
        else:top=np.array((25,88,179));bottom=np.array((5,19,68));highlight=np.array((81,146,120))
        colour=top+(bottom-top)*depth[...,None]**1.4+hotspot[...,None]*highlight
        colour*=np.clip(1.04-.18*(r/.784)**2,.75,1.04)[...,None]
        rgb[liquid]=colour[liquid]
        edge=liquid & (y<surface+wave+.012) & (steps<100)
        rgb[edge]=rgb[edge]*.82+np.array((30,25,23))
    rgb=rgb+(255-rgb)*gloss[...,None]
    rgba=np.dstack((np.clip(rgb,0,255).astype(np.uint8),alpha))
    im=Image.fromarray(rgba,'RGBA')
    draw=ImageDraw.Draw(im);n=d*SS
    lines=text_lines(value)
    if len(lines)==2:
        centered(draw,lines[0],n,n*.465,round(n*.144),n*.69,max(1,n//240))
        centered(draw,lines[1],n,n*.625,round(n*.078),n*.66,max(1,n//360))
    else:
        centered(draw,lines[0],n,n*.50,round(n*(.144 if '%' in lines[0] else .11)),n*.70,max(1,n//240))
    return im.resize((d,d),Image.Resampling.LANCZOS)

def render_globe(kind,d,fraction,value):
    if kind not in ('hp','mp') or type(d) is not int or not 80<=d<=240:raise ValueError('Invalid globe dimensions or resource')
    # The cached image is read-only by convention; callers copy before edits.
    return _render(kind,d,fill_steps(fraction),str(value))

def premultiplied_bgra(image):
    rgba=np.asarray(image.convert('RGBA'),dtype=np.uint16)
    a=rgba[:,:,3:4]
    rgb=(rgba[:,:,:3]*a+127)//255
    return np.concatenate((rgb[:,:,::-1],a),axis=2).astype(np.uint8).tobytes()
