"""Passive screen-only Lineage II farming tracker. Windows desktop prototype."""
import csv, os, queue, re, shutil, threading, time, sys
from collections import Counter
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, colorchooser
import numpy as np
from PIL import Image, ImageTk, ImageOps
import mss
import pytesseract
from window_focus import Windows, capture_region
import settings
from hud import Hud, WIDTH, HEIGHT, safe_position, hud_position
from session_pause import PauseGate
from review import ReviewQueue, candidates, review_fields, correction_message
from history import Archive, new_id, now, snapshot, totals_for, review_queue, count_kills, rate, consumables_for
from consumable_costs import key as cost_key, price as validate_price, load_prices, save_prices, clean_prices, cost_report, cost_summary, money, write_cost_csv
from loot_values import load_loot_prices, save_loot_prices, loot_report, loot_summary, unit_label, write_loot_csv
from history_ui import HistoryWindow
from runtime_ocr import configure_ocr
from version import VERSION
from diagnostics import setup_diagnostics, diagnostic
from appearance import Appearance, Dashboard, save_mode
from preferences import load_focus_pause, save_focus_pause, load_auto_update, save_auto_update, load_hud_opacity, save_hud_opacity, HUD_OPACITY_MIN, HUD_OPACITY_MAX, HUD_OPACITY_DEFAULT, load_hud_net_adena, save_hud_net_adena
from party_setup_ui import PartySetup
from update_ui import UpdateUI
from preferences import load_backup_retention,save_backup_retention
from scroll_ui import ScrollPage,table_scroll
from player_ui import PlayerStatus
from hud_layout import WIDGETS, PRESETS, clean as clean_hud, load as load_hud, save as save_hud, geometry as hud_geometry
from hud import rate_text
from chat_style import TEXT_SIZES, DEFAULT_COLOURS, CUSTOM_COLOURS, LABELS, load_style, save_style, validate_style, pixel_masks, row_group, styled_rows, row_alignment, aligned_rows
from party import roster, live_report as live_party_report, display_rows as party_rows, summary_text as party_summary


def parse(line):
    s = re.sub(r'\s+', ' ', line).strip(' .,;:|')
    # Only correct known word-level errors, never guess XP or SP digits.
    s = re.sub(r'^You haye (?=acquired |obtained |earned |used )', 'You have ', s, flags=re.I)
    n = r'(\d[\d,]*)'
    def num(t): return int(t.replace(',', ''))
    m = re.fullmatch(r'You have acquired '+n+r' XP and '+n+r' SP', s, re.I)
    if m: return ('xp', 'You', 'XP / SP', num(m[1]), num(m[2]))
    m = re.fullmatch(r'(You have|[\w\-]+ has) (?:earned|eamed) '+n+r' Adena', s, re.I)
    if m:
        who='You' if m[1].lower()=='you have' else m[1].rsplit(' ',1)[0]
        return ('adena',who,'Adena',num(m[2]),0)
    m = re.fullmatch(r'(You have|[\w\-]+ has) obtained (.+)', s, re.I)
    if m:
        who = 'You' if m[1].lower() == 'you have' else m[1].rsplit(' ',1)[0]
        item = m[2].strip(); qty = 1
        # These explicit quantity formats are provisional, not confirmed in C1.
        for pat, reverse in [(r'(\d[\d,]*) (.+)',False),(r'(.+?)\s*\(\s*(?:x\s*)?(\d[\d,]*)\s*\)',True),(r'(.+?)\s+x\s*(\d[\d,]*)',True)]:
            q = re.fullmatch(pat,item,re.I)
            if q:
                item, qty = (q[1],num(q[2])) if reverse else (q[2],num(q[1])); break
        if item.lower() == 'adena': return ('adena',who,'Adena',qty,0)
        return ('item',who,item,qty,0)
    # The blue message reports an activation, not necessarily the number of shots consumed.
    m = re.fullmatch(r'(?:Use|You have used) (.+)', s, re.I)
    if m:
        item=m[1].strip()
        # Reject damaged grade words rather than creating fictitious consumables.
        if re.match(r'(?:Blessed\s+)?(?:Soulshot|Spiritshot)\s*:',item,re.I):
            if not re.fullmatch(r'(?:Blessed\s+)?(?:Soulshot|Spiritshot)\s*:\s*(?:No|[DCSBA]) Grade',item,re.I):return None
        if item: return ('consumable','You',item,1,0)
    return None


def colour_masks(rgb, threshold=140, contrast=75):
    r,g,b=np.moveaxis(rgb.astype(np.int16),-1,0)
    return {
        'xp': (np.minimum(r,b)>threshold)&(np.minimum(r,b)-g>contrast),
        'adena': (np.minimum(r,g)>threshold)&(np.minimum(r,g)-b>contrast),
        'item': (g>threshold)&(g-np.maximum(r,b)>contrast),
        'consumable': (b>threshold)&(g>threshold-50)&(np.minimum(g,b)-r>contrast)&(b-g>15),
    }


def colour_category(rgb):
    masks=colour_masks(rgb)
    counts=sorted(((int(m.sum()),k) for k,m in masks.items()),reverse=True)
    if counts[0][0]<24 or counts[0][0]<2*counts[1][0]:return None
    return counts[0][1]


def mask(rgb):
    r,g,b = np.moveaxis(rgb.astype(np.int16),-1,0)
    return (r>145)&(g>125)&(r-b>15)&(g-b>10)


def rows_of(rgb,pitch):
    m = mask(rgb)
    for coloured in colour_masks(rgb).values():m |= coloured
    n = len(m)//pitch
    return m[:n*pitch].reshape(n,pitch,m.shape[1])


def overlap(old,new):
    # Compare the physical rows, not global text hashes. Repeated lines count
    # independently when their movement can be observed.
    n=len(old); scores=[]
    if n != len(new) or n<3: return None
    for shift in range(n-1):
        a,b=old[shift:],new[:n-shift]
        ca=a.sum(axis=(1,2)); cb=b.sum(axis=(1,2)); shared=(a&b).sum(axis=(1,2))
        active=(ca+cb)>24
        if active.sum()<2: continue
        dice=2*shared[active]/(ca[active]+cb[active])
        score=float(np.mean(dice))
        if score>=.68 and (dice>=.55).mean()>=.75: scores.append((shift,score))
    if not scores: return None
    best=max(s for _,s in scores)
    return min(k for k,s in scores if s>=best-.07)


def yellow_strength(rgb):
    r,g,b=np.moveaxis(rgb.astype(np.int16),-1,0)
    return np.minimum(r,g)-b


def row_images(rgb):
    # Isolate yellow loot text by colour contrast before thresholding.
    y=yellow_strength(rgb)
    yellow=(y>105)&(rgb[:,:,0]>155)&(rgb[:,:,1]>155)
    is_yellow=yellow.sum()>35
    if is_yellow:
        img=np.where(y>105,0,255).astype(np.uint8)
    else:
        img=np.where(mask(rgb),0,255).astype(np.uint8)
    return img,is_yellow


def padded(im,scale=4,nearest=False):
    im=np.pad(im,((8,8),(12,12)),constant_values=255)
    return Image.fromarray(im).resize((im.shape[1]*scale,im.shape[0]*scale),Image.Resampling.NEAREST if nearest else Image.Resampling.LANCZOS)


def single_ocr(im,config='--psm 7',nearest=False):
    return pytesseract.image_to_string(padded(im,nearest=nearest),config=config,timeout=5).strip()


def adena_like(line):
    return bool(re.search(r'\b(?:earned|eamed|ear[nm]ed)\b|\badena\b',line,re.I))


def xp_like(line):
    return bool(re.search(r'\bacquired\b|(?<=[0-9\s])XP\s*and(?=\s|[0-9])',line,re.I))


# Known OCR punctuation after introductory words; never accept a digit
# suffix of a malformed token such as S67, 8.67 or 86/7.
XP_TOKEN_START=r'(?:^|(?<=\s)|(?<=®)|(?<=[A-Za-z]\.))'

def xp_numeric_candidate(line):
    # Only use this in the XP retry path, which is gated by xp_like(first).
    # Ignore damaged introductory words, but require both numeric fields and
    # the XP/and/SP labels. SF is a known OCR substitution for SP. Never
    # substitute or invent digits; malformed numbers yield no vote.
    n = r'([0-9]+(?:,[0-9]{3})*)'
    # OCR can merge adjacent words (XPand9SP), and capture a small stray
    # glyph after the sentence punctuation. Only allow a single isolated
    # digit or x after explicit punctuation, not arbitrary trailing text.
    # Do not remove any characters from either numeric field.
    tail = r'(?:\s*[.,;:]+(?:\s+[0-9x])?\s*[.,;:]*)?\s*$'
    m = re.search(XP_TOKEN_START+n+r'\s*XP\s*and\s*'+n+r'\s*S[PF]'+tail,line.strip(),re.I)
    if not m: return None
    prefix=line.strip()[:m.start(1)].strip()
    if prefix and re.search(r'(?:^|\s)[0-9,./?&+-]+$',prefix):return None
    return tuple(int(x.replace(',', '')) for x in m.groups())


def verified_xp(reads):
    valid=[v for t in reads if (v:=xp_numeric_candidate(t)) is not None]
    if len(valid)<2 or len(set(valid))!=1: return None
    return valid[0]


def xp_retry(row, first):
    # Compare numeric pairs rather than requiring a perfect sentence in each
    # retry. Failed reads are abstentions; contradictory pairs require review.
    r,g,b=np.moveaxis(row.astype(np.int16),-1,0)
    reads=[]
    for threshold in (90,110,130):
        m=(r>threshold)&(g>threshold-15)&(r-b>15)&(g-b>10)
        reads.append(single_ocr(np.where(m,0,255).astype(np.uint8)))
        votes={v for t in [first,*reads] if (v:=xp_numeric_candidate(t)) is not None}
        if len(votes)>1: return None,reads
        if len(reads)>=2:
            pair=verified_xp([first,*reads])
            if pair is not None:
                return f'You have acquired {pair[0]} XP and {pair[1]} SP.',reads
    return None,reads



def sp_numeric_candidate(line):
    # In a row already identified as an XP/SP message, SP may be readable
    # even when the XP amount or its label is damaged. Never guess digits.
    m=re.search(r'and\s*([0-9]+(?:,[0-9]{3})*)\s*S[PF](?:\s*[.,;:]+(?:\s+[0-9x])?\s*[.,;:]*)?\s*$',line.strip(),re.I)
    return int(m[1].replace(',', '')) if m else None


def recover_sp_only(reads):
    votes=[v for t in reads if (v:=sp_numeric_candidate(t)) is not None]
    if len(votes)<2 or len(set(votes))!=1:
        return None
    evidence=' | '.join(t or '(blank)' for t in reads)
    return ('sp_partial',f'You have acquired {votes[0]} SP; XP unknown. [XP conflict or unreadable: {evidence}]')


def recover_sp_conflict(row, first, reads):
    """Resolve SP-only disagreement from this row, never from adjacent events.

    XP is retained only if every valid pair agrees on it. SP needs at least
    two matching votes against exactly one dissent after additional passes.
    For a 2:1 result require at least four attempts (one unreadable).
    Preserve all readings for the review/export log.
    """
    votes=[v for t in [first,*reads] if (v:=xp_numeric_candidate(t)) is not None]
    if len(votes)<2 or len({v[0] for v in votes})!=1 or len({v[1] for v in votes})<2:
        return None
    r,g,b=np.moveaxis(row.astype(np.int16),-1,0)
    extra=[]
    for threshold,nearest in ((115,True),(145,False)):
        m=(r>threshold)&(g>threshold-15)&(r-b>15)&(g-b>10)
        extra.append(single_ocr(np.where(m,0,255).astype(np.uint8),nearest=nearest))
    all_reads=[first,*reads,*extra]
    votes=[v for t in all_reads if (v:=xp_numeric_candidate(t)) is not None]
    if len({v[0] for v in votes})!=1:
        return recover_sp_only(all_reads) or ('uncertain',f'{first} [XP retry: {" | ".join(t or "(blank)" for t in [*reads,*extra])}]')
    xp=votes[0][0]
    counts=Counter(v[1] for v in votes)
    sp,n=counts.most_common(1)[0]
    evidence=' | '.join(t or '(blank)' for t in all_reads)
    if n>=2 and sum(counts.values())-n==1 and (n>=3 or len(all_reads)>=4):
        return ('xp_recovered',f'You have acquired {xp} XP and {sp} SP. [SP majority: {evidence}]')
    return ('xp_partial',f'You have acquired {xp} XP; SP unknown. [SP conflict: {evidence}]')


def parse_xp_resolution(kind,line):
    if kind=='xp_recovered':
        return parse(line.split(' [SP majority: ',1)[0])
    if kind=='xp_partial':
        m=re.match(r'^You have acquired ([0-9]+) XP; SP unknown\. \[SP conflict: ',line)
        if m: return ('xp','You','XP / SP',int(m[1]),None)
    if kind=='sp_partial':
        m=re.match(r'^You have acquired ([0-9]+) SP; XP unknown\. \[XP conflict or unreadable: ',line)
        if m: return ('xp','You','XP / SP',None,int(m[1]))
    return None


def verified_amount(reads, event=None):
    # Blank/non-numeric reads are failures, not votes. Never majority-vote
    # over a conflicting valid numeric reading.
    valid=[int(t) for t in reads if re.fullmatch(r'[0-9]+',t)]
    if len(valid)<2 or len(set(valid))!=1:
        return None
    if event is not None and (event[0]!='adena' or event[3]!=valid[0]):
        return None
    return valid[0]


def adena_numeric_retry(raw, event):
    y=yellow_strength(raw)
    config='--psm 7 -c tessedit_char_whitelist=0123456789'
    reads=[]
    for threshold in (90,120,65,105):
        crop=np.where(y>threshold,0,255).astype(np.uint8)
        reads.append(single_ocr(crop,config=config))
        valid={int(t) for t in reads if re.fullmatch(r'[0-9]+',t)}
        if len(valid)>1 or (event is not None and valid and (event[0]!='adena' or event[3] not in valid)):
            return None,reads
        if len(reads)>=2:
            amount=verified_amount(reads,event)
            if amount is not None:
                return amount,reads
    return None,reads


def repeated_row_indices(processed):
    # Compare adjacent line images, not recognised text. Similar-looking rows
    # are a signal to isolate OCR, never a reason to merge drop events.
    repeated=set()
    for i in range(1,len(processed)):
        a,ay=processed[i-1]; b,by=processed[i]
        if ay!=by: continue
        a=a<128; b=b<128
        total=int(a.sum()+b.sum())
        if total>=48 and 2*int((a&b).sum())/total>=.72:
            repeated.update((i-1,i))
    return repeated


def legacy_ocr_rows(rows):
    # Map OCR words back to fixed row positions, even when a row is omitted.
    processed=[row_images(row) for row in rows]
    h,w=rows.shape[1:3]; step=h+28
    sheet=np.full((len(rows)*step+10,w+24),255,np.uint8)
    for i,(im,is_yellow) in enumerate(processed):
        if not is_yellow: sheet[14+i*step:14+i*step+h,12:12+w]=im
    scale=4
    big=Image.fromarray(sheet).resize((sheet.shape[1]*scale,sheet.shape[0]*scale),Image.Resampling.LANCZOS)
    data=pytesseract.image_to_data(big,config='--psm 6',output_type=pytesseract.Output.DICT,timeout=10)
    lines=[[] for _ in rows]
    for word,top,height in zip(data['text'],data['top'],data['height']):
        if word.strip():
            idx=int((top+height/2)/scale//step)
            if 0<=idx<len(lines): lines[idx].append(word)
    repeats=repeated_row_indices(processed)
    for i,(row,(im,is_yellow),words) in enumerate(zip(rows,processed,lines)):
        batch=' '.join(words)
        # Yellow lines already use isolated OCR. For beige repeated lines,
        # bypass the shared OCR sheet, which can join neighbouring glyphs.
        # Recover missing/malformed XP rows with the same isolated pass.
        isolated=is_yellow or i in repeats or len(rows)==1 or (not batch and (im<128).sum()>24) or (xp_like(batch) and not parse(batch))
        first=single_ocr(im) if isolated else batch
        event=parse(first)
        if is_yellow and adena_like(first):
            # The amount is normally the penultimate word. Read just that word
            # with a numeric alphabet, independent of full-line language OCR.
            cols=np.flatnonzero((im<128).any(axis=0))
            groups=np.split(cols,np.where(np.diff(cols)>3)[0]+1)
            phrase=re.fullmatch(r'You have (?:earned|eamed) (.+) Adena[.,]?',first,re.I)
            if phrase and len(groups)==5 and all(len(g) for g in groups):
                g=groups[-2]; x0,x1=int(g[0]),int(g[-1])+1
                raw=row[:,x0:x1]
                amount,reads=adena_numeric_retry(raw,event)
                if amount is not None:
                    yield ('line',f'You have earned {amount} Adena.'); continue
                yield ('uncertain',f"{first} [numeric OCR: {' | '.join(t or '(blank)' for t in reads)}]"); continue
            # When the word boundaries cannot be located, require two readings.
            alt=single_ocr(np.where(mask(row),0,255).astype(np.uint8)); alt_event=parse(alt)
            if event and event==alt_event:
                yield ('line',first); continue
            yield ('uncertain',f'{first} [alternative: {alt}]'); continue
        if is_yellow and not event:
            alt=single_ocr(np.where(mask(row),0,255).astype(np.uint8)); alt_event=parse(alt)
            # Do not assume an unrecognised yellow message is a valid drop.
            yield ('uncertain',f'{first} [alternative: {alt}]'); continue

        # A repeated XP row receives independent verification even when its
        # initial isolated reading parses. A malformed batch is only a hint
        # that this row is XP, never a numeric vote from a neighbouring line.
        xp_hint=xp_like(first) or xp_like(batch)
        if not is_yellow and xp_hint and (not event or (i in repeats and event[0]=='xp') or (isolated and not parse(batch) and event[0]=='xp')):
            corrected,reads=xp_retry(row,first)
            if corrected:
                yield ('line',corrected); continue
            resolution=recover_sp_conflict(row,first,reads) or recover_sp_only([first,*reads])
            if resolution:
                yield resolution; continue
            yield ('uncertain',f"{first} [XP retry: {' | '.join(t or '(blank)' for t in reads)}]"); continue
        if not first and isolated and (batch or i in repeats):
            yield ('uncertain',f'Isolated row unreadable [batch hint: {batch or "(blank)"}]'); continue
        if first:
            yield ('uncertain' if not event and (adena_like(first) or xp_like(first)) else 'line',first)

def colour_ocr_row(row,category):
    # Each read is isolated from the background and other message colours.
    reads=[]
    for threshold,contrast,nearest in ((140,75,False),(115,60,True),(165,95,False)):
        m=colour_masks(row,threshold,contrast)[category]
        reads.append(single_ocr(np.where(m,0,255).astype(np.uint8),nearest=nearest))
    votes=[parse(s) for s in reads]
    # Yellow was the old loot colour. Preserve verified legacy yellow item drops.
    allowed={category} if category!='adena' else {'adena','item'}
    valid=[e for e in votes if e and e[0] in allowed]
    if category=='xp':
        pairs=[v for s in reads if (v:=xp_numeric_candidate(s)) is not None]
        if len(pairs)>=2 and len(set(pairs))==1:
            x,sp=pairs[0]
            if x>0:return ('line',f'You have acquired {x} XP and {sp} SP.')
        partial=recover_sp_only(reads)
        if partial:return partial
    elif len(valid)>=2 and len(set(valid))==1 and valid[0][3]>0:
        return ('line',reads[votes.index(valid[0])])
    # Keep the category even if the text was completely unreadable.
    return ('uncertain:'+category, f'{reads[0] or "(blank)"} [colour OCR: {" | ".join(s or "(blank)" for s in reads[1:])}]')


def ocr_rows(rows):
    # Keep physical order and the original OCR path for uncustomised clients.
    # Legacy beige skill/activation messages do not parse as consumable use.
    start=0
    for i,row in enumerate(rows):
        category=colour_category(row)
        if category is None:continue
        if i>start:yield from legacy_ocr_rows(rows[start:i])
        yield colour_ocr_row(row,category)
        start=i+1
    if start<len(rows):yield from legacy_ocr_rows(rows[start:])


def xp_field_candidate(text):
    # Reject numeric suffixes of damaged tokens and split numeric fields.
    m=re.search(XP_TOKEN_START+r'([0-9]+(?:,[0-9]{3})*)\s*XP\s*and(?=\s|[0-9&©?])',text.strip(),re.I)
    if not m:return None
    prefix=text.strip()[:m.start(1)].strip()
    if prefix and re.search(r'(?:^|\s)[0-9,./?&+-]+$',prefix):return None
    value=int(m[1].replace(',',''))
    return value if value>0 else None

def configured_xp_resolution(row,reads):
    # A second independent preprocessing family is particularly useful for
    # magenta text, where exact RGB thresholds can fragment thin digits.
    # Keep any conflicting *valid* values in the evidence: never outvote XP.
    def fields():
        x=[v for text in reads if (v:=xp_field_candidate(text)) is not None]
        sp=[v for text in reads if (v:=sp_numeric_candidate(text)) is not None]
        return x,sp
    def agreed(v):return v[0] if len(v)>=2 and len(set(v))==1 else None
    x,sp=fields()
    if agreed(x) is None or agreed(sp) is None:
        if colour_category(row)=='xp':
            for threshold,contrast in ((110,72),(170,110)):
                m=colour_masks(row,threshold=threshold,contrast=contrast)['xp']
                reads.append(single_ocr(np.where(m,0,255).astype(np.uint8)))
            x,sp=fields()
    xv,sv=agreed(x),agreed(sp)
    evidence=' | '.join(text or '(blank)' for text in reads)
    if xv is not None and sv is not None:
        return 'line',f'You have acquired {xv} XP and {sv} SP.'
    if xv is not None:
        return 'xp_partial',f'You have acquired {xv} XP; SP unknown. [SP conflict: {evidence}]'
    if sv is not None:
        return 'sp_partial',f'You have acquired {sv} SP; XP unknown. [XP conflict or unreadable: {evidence}]'
    return None

def configured_ocr_rows(rows,colours):
    """Respect shared colours: classify by text where a hue is not unique."""
    for row in rows:
        group=row_group(row,colours)
        if not group or group==('other',):continue
        reads=[]
        for tolerance,nearest in ((40,False),(55,True),(30,False)):
            m=pixel_masks(row,colours,tolerance).get(group)
            if m is None:break
            text=single_ocr(np.where(m,0,255).astype(np.uint8),nearest=nearest)
            reads.append(text)
            e=parse(text)
            # Default beige also includes ordinary skill and status messages.
            # Ignore clean, non-target lines instead of flooding the review queue.
            if len(reads)==1 and 'other' in group and not e and not (
                xp_like(text) or adena_like(text) or re.search(r'\b(?:obtained|use|used)\b',text,re.I)
                and not re.match(r'You use\b',text,re.I)):
                break
            valid=[x for text in reads if (x:=parse(text)) and x[0] in group and x[3]>0]
            if len(valid)>=2 and len(set(valid))==1 and valid[0][0]!='xp':
                yield ('line',next(text for text in reads if parse(text)==valid[0]))
                break
        else:
            if 'xp' in group and (len(group)==1 or any(xp_like(x) for x in reads)):
                resolved=configured_xp_resolution(row,reads)
                if resolved:yield resolved;continue
            targets=[k for k in group if k!='other']
            parsed={e[0] for text in reads if (e:=parse(text)) and e[0] in targets}
            if len(targets)==1:category=targets[0]
            elif len(parsed)==1:category=next(iter(parsed))
            elif 'xp' in targets and any(xp_like(x) for x in reads):category='xp'
            elif 'adena' in targets and any(adena_like(x) for x in reads):category='adena'
            elif 'consumable' in targets and any(re.match(r'(?:Use|You have used)\b',x,re.I) for x in reads):category='consumable'
            else:category=None
            evidence=f'{reads[0] or "(blank)"} [colour OCR: {" | ".join(x or "(blank)" for x in reads[1:])}]'
            yield ('uncertain:'+category if category else 'uncertain',evidence)


class App:
    def __init__(self,root):
        self.root=root; root.title(f'L2 Legacy Farming Tracker — v{VERSION} Portable'); root.geometry('1020x780'); root.minsize(850,600)
        self.appearance=Appearance(root)
        self.pause_on_blur=load_focus_pause();self.auto_update=load_auto_update();self.settings_win=None
        self.hud_opacity=load_hud_opacity();self.hud_opacity_save_job=None
        self.hud_net_adena=load_hud_net_adena();self.hud_config=load_hud()
        self.default_prices=load_prices();self.session_prices=dict(self.default_prices);self.consumable_report=cost_report([])
        self.default_loot_prices=load_loot_prices();self.session_loot_prices=dict(self.default_loot_prices);self.loot_report=loot_report([]);self.loot_rows={}
        self.region=None; self.target=None; self.active_seconds=0.0; self.selecting=False; self.pitch=tk.StringVar(value='18'); self.status=tk.StringVar(value='Select the system-message text area.'); self.stats=tk.StringVar(value='No session'); self.events=[]; self.totals=Counter(); self.inbox=queue.Queue(); self.running=False; self.started=None; self.ended=None; self.gaps=0; self.pending=0; self.raw=[]; self.run_id=0
        self.party_members=[]; self.next_party_members=[]; self.kills=0; self.update_busy=False
        self.archive=None; self.session_id=None; self.session_date=None; self.session_end=None; self.session_complete=None; self.history_window=None; self.last_archive_save=0; self.closing=False;self.reset_request=None
        self.pause_gate=PauseGate(self.pause_on_blur); self.position_win=None; self.reviews=ReviewQueue(); self.review_win=None; self.review_count=tk.StringVar(value="Review (0)"); self.saved=None; self.hud=None; self.api=None; self.hud_enabled=tk.BooleanVar(value=self.hud_config['visible'])
        try:
            self.api=Windows()
            self.saved=settings.load()
            if self.saved:
                self.region=dict(self.saved['region']); self.pitch.set(str(self.saved['pitch']))
                self.target=self.api.find_saved(self.saved)
                self.status.set('Saved chat calibration loaded. Start when the matching game is open.')
        except Exception as e: self.status.set(f'Could not restore calibration: {e}. Bind game again.')
        self.chat_style=load_style(fallback_pitch=int(self.pitch.get()));self.pitch.set(str(self.chat_style['pitch']))
        try: self.hud=Hud(preferred=tuple(self.saved["hud_position"]) if self.saved and self.saved.get("hud_position") is not None else None,on_move=self.queue_hud_move,on_pause=self.queue_hud_pause,opacity=self.hud_opacity,on_reset=self.queue_hud_reset)
        except Exception as e: self.hud_enabled.set(False); self.status.set(self.status.get()+f' HUD unavailable: {e}')
        if self.hud:
            try:self.hud.configure_layout(self.hud_config)
            except Exception as e:
                self.hud.close();self.hud=None;self.hud_enabled.set(False);self.status.set('HUD layout unavailable: '+str(e))
        self.player=PlayerStatus(self)
        try: self.archive=Archive()
        except Exception as e: messagebox.showerror("Session storage",f"Could not open session history: {e}")
        header=ttk.Frame(root,padding=(20,15,20,6));header.pack(fill='x')
        ttk.Label(header,text='L2 Legacy Tracker',style='Title.TLabel').pack(side='left')
        ttk.Label(header,text=f'v{VERSION}  ·  Farming analytics',style='Muted.TLabel').pack(side='left',padx=14)
        self.dark_mode=tk.BooleanVar(value=self.appearance.mode=='dark')
        self.party_status=tk.StringVar(value='Next session: solo / no estimates')
        actions=ttk.Frame(root,padding=(20,3,20,8));actions.pack(fill='x')
        self.start_btn=ttk.Button(actions,text='Start session',command=self.start,style='Primary.TButton');self.start_btn.pack(side='left')
        self.pause_btn=ttk.Button(actions,text='Pause',command=self.toggle_pause,state='disabled');self.pause_btn.pack(side='left',padx=7)
        self.stop_btn=ttk.Button(actions,text='Stop',command=self.stop,state='disabled',style='Danger.TButton');self.stop_btn.pack(side='left')
        self.reset_btn=ttk.Button(actions,text='Reset',command=self.reset_session,state='disabled');self.reset_btn.pack(side='left',padx=7)
        ttk.Label(actions,textvariable=self.party_status,style='Muted.TLabel').pack(side='right')
        self.tabs=ttk.Notebook(root)
        self.pages={}
        for key,label in [('dashboard','Dashboard'),('activity','Activity'),('review','Reviews (0)'),('history','History'),('party','Party'),('settings','Settings')]:
            page=ttk.Frame(self.tabs,padding=8);self.pages[key]=page;self.tabs.add(page,text=label)
        self.dashboard_scroll=ScrollPage(self.pages['dashboard']);self.dashboard_scroll.pack(fill='both',expand=True)
        dash=self.dashboard_scroll.content
        self.dashboard=Dashboard(dash);self.dashboard.pack(fill='x',pady=(0,4))
        self.player.build_dashboard(dash)
        ttk.Label(dash,textvariable=self.stats,wraplength=880,padding=(0,3,0,12),style='Muted.TLabel').pack(fill='x')
        loot_header=ttk.Frame(dash);loot_header.pack(fill='x',pady=(2,8))
        ttk.Label(loot_header,text='Session loot',style='Section.TLabel').pack(side='left')
        ttk.Button(loot_header,text='Export CSV',command=self.export).pack(side='right')
        ttk.Button(loot_header,text='Set default value…',command=self.edit_default_loot_value).pack(side='right',padx=5)
        ttk.Button(loot_header,text='Edit item value…',command=self.edit_loot_value).pack(side='right',padx=5)
        loot=ttk.Frame(dash);loot.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(loot,columns=('who','item','qty','unit','value'),show='headings',height=9,selectmode='browse')
        for c,t,w in [('who','Player',120),('item','Item',280),('qty','Quantity',90),('unit','Adena / item',110),('value','Est. sell value',130)]:
            self.tree.heading(c,text=t);self.tree.column(c,width=w,anchor='e' if c in ('qty','unit','value') else 'w',stretch=c=='item')
        self.tree.bind('<Double-1>',self.edit_loot_value)
        table_scroll(loot,self.tree)
        self.loot_status=tk.StringVar(value='No recorded loot values.')
        ttk.Label(dash,textvariable=self.loot_status,style='Muted.TLabel',wraplength=870).pack(fill='x',pady=(3,0))
        usage=ttk.LabelFrame(dash,text='Consumables used (observed activations)',padding=6);usage.pack(fill='x',pady=(8,0))
        cost_controls=ttk.Frame(usage);cost_controls.pack(fill='x')
        ttk.Button(cost_controls,text='Edit selected cost…',command=self.edit_consumable_cost).pack(side='left')
        ttk.Button(cost_controls,text='Set default cost…',command=self.edit_default_cost).pack(side='left',padx=6)
        ttk.Label(usage,text='Adena per activation; double-click a row to edit.',style='Muted.TLabel').pack(anchor='w',pady=3)
        cost_table=ttk.Frame(usage);cost_table.pack(fill='x')
        self.consumable_tree=ttk.Treeview(cost_table,columns=('item','uses','unit','cost'),show='headings',height=4,selectmode='browse')
        for c,label,w in [('item','Consumable',310),('uses','Uses',80),('unit','Adena / use',120),('cost','Known cost',130)]:
            self.consumable_tree.heading(c,text=label);self.consumable_tree.column(c,width=w,anchor='w' if c=='item' else 'e',stretch=c=='item')
        self.consumable_tree.bind('<Double-1>',self.edit_consumable_cost)
        table_scroll(cost_table,self.consumable_tree)
        self.cost_status=tk.StringVar(value='No recorded consumable costs.')
        ttk.Label(dash,textvariable=self.cost_status,style='Muted.TLabel',wraplength=870).pack(fill='x',pady=(3,0))
        activity=self.pages['activity']
        ttk.Label(activity,text='Activity log',style='Title.TLabel').pack(anchor='w')
        ttk.Label(activity,text='Accepted messages, review warnings and ignored OCR lines.',style='Muted.TLabel').pack(anchor='w',pady=(3,10))
        log_frame=ttk.Frame(activity);log_frame.pack(fill='both',expand=True)
        self.log=tk.Text(log_frame,height=12,wrap='word',state='disabled')
        log_scroll=ttk.Scrollbar(log_frame,orient='vertical',command=self.log.yview);self.log.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side='right',fill='y');self.log.pack(fill='both',expand=True)
        bottom=ttk.Frame(root,padding=(12,3,12,7));bottom.pack(side='bottom',fill='x')
        self.tabs.pack(fill='both',expand=True,padx=8,pady=(0,4))
        status_label=ttk.Label(bottom,textvariable=self.status,wraplength=600,style='Status.TLabel');status_label.pack(side='left',fill='x',expand=True)
        status_label.bind('<Configure>',lambda e:status_label.configure(wraplength=max(100,e.width-8)))
        self.updates=UpdateUI(self,bottom)
        self.pitch.trace_add('write',self.pitch_changed)
        self.build_settings(self.pages['settings'])
        self.tabs.bind('<<NotebookTabChanged>>',self.page_changed)
        self.appearance.restyle(root)
        root.after(100,self.tick);root.after(25,self.hud_tick);root.protocol('WM_DELETE_WINDOW',self.close)
    def navigate(self,key):
        if not self.update_busy:self.tabs.select(self.pages[key])
    def page_changed(self,*_):
        if self.update_busy:
            if self.tabs.select()!=str(self.pages['dashboard']):self.tabs.select(self.pages['dashboard'])
            return
        key=next((k for k,v in self.pages.items() if str(v)==self.tabs.select()),None)
        if key=='history':
            if not self.archive:return
            if self.session_id and not self.save_session():return
            if self.history_window:self.history_window.refresh()
            else:self.history_window=HistoryWindow(self,self.pages['history'])
        elif key=='review':self.build_reviews()
        elif key=='party':
            if not getattr(self,'party_setup_window',None):self.party_setup_window=PartySetup(self,self.pages['party'])
    def open_settings(self):
        self.navigate('settings')
    def build_settings(self,win):
        settings_tabs=ttk.Notebook(win);settings_tabs.pack(fill='both',expand=True)
        self.settings_scroll={}
        for label in ('Tracking','HUD','Player status'):
            page=ScrollPage(settings_tabs,padding=8);settings_tabs.add(page,text=label);self.settings_scroll[label]=page
        content,hudpage,playerpage=(self.settings_scroll[k].content for k in ('Tracking','HUD','Player status'))
        ttk.Label(content,text='Tracking settings',style='Title.TLabel').pack(anchor='w')
        ttk.Label(content,text='Game capture',style='Section.TLabel').pack(anchor='w',pady=(14,5))
        calibration=ttk.Frame(content);calibration.pack(fill='x',pady=(0,6))
        ttk.Button(calibration,text='Bind game / chat area',command=self.select).pack(side='left')
        ttk.Label(calibration,text='Text size:').pack(side='left',padx=(14,4))
        self.text_size=tk.StringVar(value=self.chat_style['size'])
        sizes=ttk.Combobox(calibration,textvariable=self.text_size,values=(*TEXT_SIZES,'Manual'),state='readonly',width=9);sizes.pack(side='left');sizes.bind('<<ComboboxSelected>>',self.select_text_size)
        ttk.Label(calibration,text='Line spacing (px):').pack(side='left',padx=(12,4))
        self.pitch_entry=ttk.Entry(calibration,textvariable=self.pitch,width=5,state='normal' if self.text_size.get()=='Manual' else 'readonly');self.pitch_entry.pack(side='left')
        hudtools=ttk.Frame(hudpage);hudtools.pack(fill='x',pady=(0,8))
        ttk.Button(hudtools,text='Position HUD…',command=self.open_position).pack(side='left')
        self.move_btn=ttk.Button(hudtools,text='Move HUD in game',command=self.arm_hud_move);self.move_btn.pack(side='left',padx=8)
        ttk.Label(hudtools,text='HUD: double-click lock to unlock; drag; click to lock.',style='Muted.TLabel').pack(side='left',padx=4)
        palette=ttk.LabelFrame(content,text='In-game system message colours',padding=6);palette.pack(fill='x',pady=(0,6))
        self.colour_vars={};self.colour_swatches={}
        for i,(key,label) in enumerate(LABELS.items()):
            cell=ttk.Frame(palette);cell.grid(row=i//3,column=i%3,sticky='w',padx=(0,12),pady=2)
            ttk.Label(cell,text=label).pack(side='left',padx=(0,4))
            var=tk.StringVar(value=self.chat_style['colours'][key]);self.colour_vars[key]=var
            ttk.Entry(cell,textvariable=var,width=9).pack(side='left')
            swatch=tk.Button(cell,text=' ',width=2,bg=var.get(),command=lambda k=key:self.choose_chat_colour(k));swatch.pack(side='left',padx=3);self.colour_swatches[key]=swatch
        controls=ttk.Frame(palette);controls.grid(row=2,column=0,columnspan=3,sticky='w',pady=(4,0))
        ttk.Button(controls,text='L2 defaults',command=lambda:self.set_chat_palette(DEFAULT_COLOURS)).pack(side='left')
        ttk.Button(controls,text='Distinct colours',command=lambda:self.set_chat_palette(CUSTOM_COLOURS)).pack(side='left',padx=5)
        ttk.Button(controls,text='Apply chat settings',command=self.apply_chat_style).pack(side='left',padx=5)
        ttk.Label(content,text='Match your game colours and text size; apply before starting a session.',style='Muted.TLabel').pack(anchor='w')
        ttk.Label(content,text='Tracking',style='Section.TLabel').pack(anchor='w',pady=(4,5))
        self.focus_pause_var=tk.BooleanVar(master=win,value=self.pause_on_blur)
        ttk.Checkbutton(content,text='Pause when Lineage 2 loses focus',variable=self.focus_pause_var,command=self.change_focus_policy).pack(anchor='w')
        ttk.Label(content,text='Off by default. Capture continues if the game chat is visible; covered, minimised or resized game windows still wait safely.',style='Muted.TLabel',wraplength=500).pack(anchor='w',pady=(3,10))
        hudappearance=ttk.Frame(hudpage);hudappearance.pack(fill='x',pady=(0,2))
        ttk.Checkbutton(hudappearance,text='Show floating game HUD',variable=self.hud_enabled,command=self.apply_hud_config).pack(side='left')
        ttk.Label(hudappearance,text='HUD opacity:').pack(side='left',padx=(16,5))
        self.hud_opacity_var=tk.DoubleVar(value=self.hud_opacity)
        self.hud_opacity_label=tk.StringVar(value=f'{self.hud_opacity}%')
        self.opacity_slider=ttk.Scale(hudappearance,from_=HUD_OPACITY_MIN,to=HUD_OPACITY_MAX,variable=self.hud_opacity_var,command=self.change_hud_opacity,length=160);self.opacity_slider.pack(side='left')
        ttk.Label(hudappearance,textvariable=self.hud_opacity_label,width=5).pack(side='left',padx=5)
        ttk.Button(hudappearance,text='Reset',command=self.reset_hud_opacity).pack(side='left')
        self.hud_net_adena_var=tk.BooleanVar(value=self.hud_net_adena)
        ttk.Checkbutton(hudpage,text='Subtract consumable costs from HUD Adena/hr (net)',variable=self.hud_net_adena_var,command=self.change_hud_net_adena).pack(anchor='w')
        ttk.Label(hudpage,text='Net Adena/h* indicates some recorded uses have no price. Only known costs are deducted.',style='Muted.TLabel',wraplength=760).pack(anchor='w',pady=(0,2))
        self.build_hud_widgets(hudpage)
        self.player.build(playerpage)
        ttk.Separator(content).pack(fill='x',pady=12)
        ttk.Label(content,text='Appearance',style='Section.TLabel').pack(anchor='w')
        ttk.Checkbutton(content,text='Light mode',variable=self.dark_mode,onvalue=False,offvalue=True,command=self.toggle_appearance).pack(anchor='w',pady=(6,5))
        ttk.Separator(content).pack(fill='x',pady=12)
        ttk.Label(content,text='Updates',style='Section.TLabel').pack(anchor='w')
        self.auto_update_var=tk.BooleanVar(master=win,value=self.auto_update)
        ttk.Checkbutton(content,text='Automatically install updates',variable=self.auto_update_var,command=self.change_update_policy).pack(anchor='w',pady=(6,3))
        ttk.Label(content,text='On by default. Checks GitHub on launch and every 30 minutes; installs published releases and restarts only when idle. Turn off to approve updates manually.',style='Muted.TLabel',wraplength=500).pack(anchor='w')
        backup_row=ttk.Frame(content);backup_row.pack(fill='x',pady=(8,2))
        ttk.Label(backup_row,text='Keep installation backups:').pack(side='left',padx=(0,8))
        self.backup_retention_var=tk.StringVar(value={1:'1 previous version',2:'2 previous versions',0:'Keep all'}[load_backup_retention()])
        backup_picker=ttk.Combobox(backup_row,textvariable=self.backup_retention_var,values=('1 previous version','2 previous versions','Keep all'),state='readonly',width=22);backup_picker.pack(side='left');backup_picker.bind('<<ComboboxSelected>>',self.change_backup_retention)
        ttk.Label(content,text='Older recognised installation backups are removed on normal startup and after successful updates. Session history and preferences are stored separately.',style='Muted.TLabel',wraplength=620).pack(anchor='w')
        ttk.Label(content,text='Preferences are saved automatically.',style='Muted.TLabel').pack(anchor='w',pady=(10,0))
        ttk.Button(content,text='Open diagnostic folder',command=self.open_diagnostic_folder).pack(anchor='w',pady=(7,0))
        self.appearance.restyle(win)
    def build_hud_widgets(self,parent):
        row=ttk.Frame(parent);row.pack(fill='x',pady=4)
        self.hud_size=tk.StringVar(value=self.hud_config['size']);self.hud_rows=tk.StringVar(value=self.hud_config['layout'])
        for label,var,options in [('Font',self.hud_size,('compact','standard','large')),('Layout',self.hud_rows,('single','double'))]:
            ttk.Label(row,text=label).pack(side='left',padx=4)
            cb=ttk.Combobox(row,textvariable=var,values=options,state='readonly',width=10);cb.pack(side='left');cb.bind('<<ComboboxSelected>>',self.apply_hud_config)
        presets=ttk.Frame(parent);presets.pack(fill='x',pady=3)
        for name in PRESETS:ttk.Button(presets,text=name,command=lambda n=name:self.hud_preset(n),style='Compact.TButton').pack(side='left',padx=3)
        self.hud_order=list(self.hud_config['order']);self.hud_vars={k:tk.BooleanVar(value=k in self.hud_config['enabled']) for k in WIDGETS}
        self.hud_list=ttk.Frame(parent);self.hud_list.pack(fill='x')
        self.draw_hud_list()
        row=ttk.Frame(parent);row.pack(fill='x',pady=4)
        self.hud_controls={k:tk.BooleanVar(value=self.hud_config[k]) for k in ('status','pause','reset')}
        for k,v in self.hud_controls.items():ttk.Checkbutton(row,text='Show '+k,variable=v,command=self.apply_hud_config).pack(side='left',padx=4)
        ttk.Button(row,text='Restore defaults',command=self.hud_defaults).pack(side='right')
        ttk.Label(parent,text='HUD preview • drag the handles or use arrows to reorder',style='Muted.TLabel').pack(anchor='w')
        self.hud_preview= tk.Canvas(parent,height=110,bg='#454f35',highlightthickness=0);self.hud_preview.pack(fill='x',pady=4)
        self.hud_preview.bind('<Configure>',lambda e:self.preview_hud())
        self.preview_hud()
    def draw_hud_list(self):
        for child in self.hud_list.winfo_children():child.destroy()
        self.hud_order_rows=[]
        for i,k in enumerate(self.hud_order):
            r=ttk.Frame(self.hud_list);r.grid(row=i%4,column=i//4,sticky='ew',padx=5);self.hud_order_rows.append(r)
            grip=ttk.Label(r,text='☷',cursor='fleur');grip.pack(side='left',padx=3)
            grip.bind('<ButtonPress-1>',lambda e,j=i:setattr(self,'hud_drag_index',j))
            grip.bind('<ButtonRelease-1>',self.drop_widget)
            ttk.Checkbutton(r,text=WIDGETS[k][0],variable=self.hud_vars[k],command=self.apply_hud_config,width=24).pack(side='left')
            ttk.Button(r,text='↑',width=2,command=lambda j=i:self.move_widget(j,-1)).pack(side='left')
            ttk.Button(r,text='↓',width=2,command=lambda j=i:self.move_widget(j,1)).pack(side='left')
    def drop_widget(self,event):
        i=getattr(self,'hud_drag_index',None);self.hud_drag_index=None
        if i is None:return
        for j,row in enumerate(self.hud_order_rows):
            x,y=row.winfo_rootx(),row.winfo_rooty()
            if x<=event.x_root<x+row.winfo_width() and y<=event.y_root<y+row.winfo_height():
                if i!=j:self.hud_order.insert(j,self.hud_order.pop(i));self.draw_hud_list();self.apply_hud_config()
                break
    def move_widget(self,i,d):
        j=i+d
        if 0<=j<len(self.hud_order):
            self.hud_order[i],self.hud_order[j]=self.hud_order[j],self.hud_order[i];self.draw_hud_list();self.apply_hud_config()
    def hud_preset(self,name):
        self.hud_order=PRESETS[name]+[k for k in WIDGETS if k not in PRESETS[name]]
        self.draw_hud_list()
        for k,v in self.hud_vars.items():v.set(k in PRESETS[name])
        self.apply_hud_config()
    def hud_defaults(self):
        self.hud_order=list(WIDGETS);self.hud_size.set('compact');self.hud_rows.set('single')
        self.hud_enabled.set(True)
        for v in self.hud_controls.values():v.set(True)
        self.draw_hud_list();self.hud_preset('Classic');self.reset_hud_opacity()
        self.hud_net_adena_var.set(False);self.change_hud_net_adena()
    def apply_hud_config(self,*_):
        self.hud_config=clean_hud(dict(order=self.hud_order,enabled=[k for k,v in self.hud_vars.items() if v.get()],size=self.hud_size.get(),layout=self.hud_rows.get(),visible=self.hud_enabled.get(),**{k:v.get() for k,v in self.hud_controls.items()}))
        try:save_hud(self.hud_config)
        except OSError as e:self.status.set('HUD preferences not saved: '+str(e))
        if self.hud:self.hud.configure_layout(self.hud_config)
        self.preview_hud()
    def preview_hud(self):
        if not hasattr(self,'hud_preview'):return
        g=hud_geometry(self.hud_config);cv=self.hud_preview;cv.delete('all')
        scale=min(1,max(1,cv.winfo_width()-6)/g['width']) if cv.winfo_width()>10 else 1
        height=round(g['height']*scale)+6
        if int(cv.cget('height'))!=height:cv.configure(height=height)
        if not self.hud_config['visible']:
            cv.create_text(10,16,text='HUD hidden',anchor='w',fill='white');return
        def blend(colour):
            foreground=tuple(int(colour[i:i+2],16) for i in (1,3,5));background=(69,79,53);a=self.hud_opacity/100
            return '#%02x%02x%02x'%tuple(round(a*f+(1-a)*b) for f,b in zip(foreground,background))
        cv.create_rectangle(2,2,g['width']+2,g['height']+2,fill=blend('#141921'),outline='')
        sample={'ad':'12,500','xp':'35,000','kills':'120','eta':'3h 48m','level':'19','progress':'16.91%','loot':'4,500','cost':'3,200'}
        for k,x,y,w,rh in g['cells']:
            cv.create_text(x+2,y+3,text=('NET ADENA/H' if k=='ad' and self.hud_net_adena else WIDGETS[k][1]),anchor='nw',font=('Segoe UI',-max(7,round(g['small']*scale))),fill=blend('#B4BECD'))
            cv.create_text(x+2,y+21,text=('9,300' if k=='ad' and self.hud_net_adena else sample[k]),anchor='nw',font=('Segoe UI',-max(9,round(g['large']*scale)),'bold'),fill=blend('#%02x%02x%02x'%WIDGETS[k][2]))
        cv.create_text(g['width']-10,12,text='▣',fill=blend('#FFFFFF'))
        if g['footer']:
            if g['status']:cv.create_text(9,g['height']-14,text='SESSION ACTIVE',anchor='w',fill='#86E0B7')
            for k in ('pause','reset'):
                if g[k]:
                    l,t,r,b=g[k];cv.create_rectangle(l,t,r,b,fill='#2E3D4E',outline='');cv.create_text((l+r)//2,(t+b)//2,text=k.title(),fill=blend('#FFFFFF'))
        if scale<1:cv.scale('all',0,0,scale,scale)
    def select_text_size(self,*_):
        size=self.text_size.get()
        self.pitch_entry.configure(state='normal')
        if size in TEXT_SIZES:self.pitch.set(str(TEXT_SIZES[size]))
        self.pitch_entry.configure(state='normal' if size=='Manual' else 'readonly')

    def choose_chat_colour(self,key):
        current=self.colour_vars[key].get()
        try:_,colour=colorchooser.askcolor(color=current,parent=self.root)
        except tk.TclError:_,colour=colorchooser.askcolor(parent=self.root)
        if colour:
            self.colour_vars[key].set(colour.upper());self.colour_swatches[key].configure(bg=colour)

    def set_chat_palette(self,colours):
        for key,value in colours.items():
            self.colour_vars[key].set(value);self.colour_swatches[key].configure(bg=value)

    def apply_chat_style(self):
        if self.running or self.pending or getattr(self,'selecting',False):
            messagebox.showwarning('Chat settings','Stop tracking before applying chat settings.',parent=self.root);return False
        try:
            style=validate_style(dict(colours={k:v.get() for k,v in self.colour_vars.items()},size=self.text_size.get(),pitch=int(self.pitch.get())))
            if self.region and self.region['height']//style['pitch']<3:raise ValueError('Select a chat area at least three lines high.')
            self.chat_style=save_style(style)
            self.pitch.set(str(style['pitch']))
            self.set_chat_palette(style['colours'])
            if self.target and self.region:self.persist()
            self.status.set('Chat settings saved. Rebind the chat region if changing font size shifted the text.')
            return True
        except (ValueError,OSError) as e:
            messagebox.showwarning('Chat settings',str(e),parent=self.root);return False

    def open_diagnostic_folder(self):
        try:
            folder=settings.settings_path().parent;folder.mkdir(parents=True,exist_ok=True);os.startfile(folder)
        except OSError as e:messagebox.showwarning('Diagnostics',str(e),parent=self.root)
    def change_backup_retention(self,*_):
        try:save_backup_retention({'1 previous version':1,'2 previous versions':2,'Keep all':0}[self.backup_retention_var.get()])
        except OSError as e:messagebox.showwarning('Backups',f'Could not save retention setting: {e}',parent=self.root)
    def change_update_policy(self):
        value=bool(self.auto_update_var.get())
        self.auto_update=value
        try:save_auto_update(value)
        except OSError as e:messagebox.showwarning('Settings',f'Changed for this run, but could not save: {e}',parent=self.root)
    def change_hud_opacity(self,value):
        percent=max(HUD_OPACITY_MIN,min(HUD_OPACITY_MAX,round(float(value))))
        if percent==self.hud_opacity:return
        try:
            if self.hud:self.hud.set_opacity(percent)
        except RuntimeError as e:
            self.hud_opacity_var.set(self.hud_opacity)
            self.status.set(str(e));return
        self.hud_opacity=percent;self.hud_opacity_label.set(f'{percent}%');self.preview_hud()
        # Avoid rewriting preferences for every mouse motion while dragging.
        if self.hud_opacity_save_job is not None:self.root.after_cancel(self.hud_opacity_save_job)
        self.hud_opacity_save_job=self.root.after(250,self.flush_hud_opacity)
    def reset_hud_opacity(self):
        self.hud_opacity_var.set(HUD_OPACITY_DEFAULT)
        self.change_hud_opacity(HUD_OPACITY_DEFAULT)
    def flush_hud_opacity(self):
        if self.hud_opacity_save_job is not None:
            self.root.after_cancel(self.hud_opacity_save_job);self.hud_opacity_save_job=None
        try:save_hud_opacity(self.hud_opacity)
        except OSError as e:self.status.set(f'HUD opacity changed, but could not save: {e}')
    def change_hud_net_adena(self):
        self.hud_net_adena=bool(self.hud_net_adena_var.get());self.preview_hud()
        try:save_hud_net_adena(self.hud_net_adena)
        except OSError as e:self.status.set(f'HUD Adena display changed, but could not save: {e}')
    def change_focus_policy(self):
        value=bool(self.focus_pause_var.get())
        self.pause_on_blur=value;self.pause_gate.set_focus_policy(value)
        try:save_focus_pause(value)
        except OSError as e:messagebox.showwarning('Settings',f'Changed for this run, but could not save: {e}',parent=self.root)
    def toggle_appearance(self):
        mode='dark' if self.dark_mode.get() else 'light'
        self.appearance.apply(mode)
        try:save_mode(mode)
        except OSError as e:messagebox.showwarning('Appearance',f'Theme changed, but preference could not be saved: {e}',parent=self.root)
    def setup_party(self):
        if getattr(self,'update_busy',False):return
        if self.running or self.pending:
            messagebox.showinfo('Party setup','Stop the current session before changing party composition. Start a new session with the new roster; merge them later.')
            return
        self.navigate('party')
    def persist(self):
        if not self.target or not self.region: return
        data=dict(schema=1,title=self.target.title,window_class=self.target.window_class,width=self.target.width,height=self.target.height,pitch=int(self.pitch.get()),region=dict(self.region))
        if self.hud and self.hud.preferred is not None:data['hud_position']=list(self.hud.preferred)
        settings.save(data); self.saved=data
    def queue_hud_pause(self):
        # Native WndProc can be dispatched from inside Tcl/Tk. Never call Tk,
        # take the capture lock or change session state in that callback.
        self.inbox.put(('hud_pause',self.run_id))
    def queue_hud_reset(self):
        # Native callback only enqueues a run-tagged request.
        self.inbox.put(('hud_reset',self.run_id))
    def queue_hud_move(self,position):
        self.inbox.put(('hud_move',position))
    def save_hud_position(self,position):
        if not self.saved:return
        try:
            data=dict(self.saved,hud_position=list(position)); settings.save(data); self.saved=data
        except Exception as e:self.append(f'WARNING: HUD position could not be saved: {e}')
    def pitch_changed(self,*_):
        if self.running or self.pending or not self.saved: return
        try:
            data=dict(self.saved,pitch=int(self.pitch.get())); settings.save(data); self.saved=data
        except (ValueError, OSError): pass
    def select(self):
        if getattr(self,'update_busy',False):return
        if self.running or self.pending or self.selecting: return
        if not messagebox.askokcancel('Bind Lineage 2', 'After clicking OK, you have 5 seconds to focus the actual Lineage 2 game window. The tracker will take one screenshot of that window for chat selection. Keep the chat visible.'): return
        self.selecting=True; self.root.withdraw(); self.root.after(5000,self.selector)
    def selector(self):
        try:
            api=Windows(); target=api.bind_foreground()
            with mss.mss() as s:
                full=dict(left=0,top=0,width=target.width,height=target.height)
                mon,reason=capture_region(api,target,full,s.monitors[0])
                if not mon: raise RuntimeError(reason)
                shot=Image.frombytes('RGB', (mon['width'],mon['height']),s.grab(mon).rgb)
                after,_=capture_region(api,target,full,s.monitors[0])
                if after!=mon: raise RuntimeError('Window focus or position changed during selection. Try again.')
        except Exception as e:
            self.selecting=False; self.root.deiconify(); messagebox.showerror('Capture',str(e)); return
        win=tk.Toplevel(self.root); win.title(f'{target.title} — select chat text, exclude scrollbar'); win.attributes('-topmost',True); self.appearance.restyle(win)
        scale=min(1,(win.winfo_screenwidth()-70)/shot.width,(win.winfo_screenheight()-150)/shot.height)
        iw,ih=round(shot.width*scale),round(shot.height*scale)
        photo=ImageTk.PhotoImage(shot.resize((iw,ih))); canvas=tk.Canvas(win,width=iw,height=ih,cursor='cross',highlightthickness=0); canvas.pack(); canvas.create_image(0,0,image=photo,anchor='nw'); canvas.image=photo
        anchor=[]; rect=[]
        def down(e):
            anchor[:]=[e.x,e.y]
            if rect: canvas.delete(rect[0])
            rect[:]=[canvas.create_rectangle(e.x,e.y,e.x,e.y,outline='cyan',width=2)]
        def drag(e):
            if anchor: canvas.coords(rect[0],*anchor,e.x,e.y)
        def up(e):
            if not anchor:return
            x1,x2=sorted((anchor[0],e.x)); y1,y2=sorted((anchor[1],e.y)); x1=max(0,x1); y1=max(0,y1); x2=min(iw,x2); y2=min(ih,y2)
            l,t=round(x1/scale),round(y1/scale); r,b=round(x2/scale),round(y2/scale)
            if r-l<100 or b-t<54:return
            if not messagebox.askyesno('Confirm game window',f'Bind to {target.title!r}? Only confirm if this is your Lineage 2 game.',parent=win): return
            self.region={'left':l,'top':t,'width':r-l,'height':b-t}; self.target=target
            try:
                self.persist(); self.status.set(f'Saved chat calibration for {target.title}: {r-l} × {b-t}px. Start, then focus game.')
            except Exception as e: self.status.set(f'Bound, but settings could not be saved: {e}')
            self.selecting=False; win.destroy(); self.root.deiconify()
        def cancel(*_): self.selecting=False; win.destroy(); self.root.deiconify()
        canvas.bind('<Button-1>',down); canvas.bind('<B1-Motion>',drag); canvas.bind('<ButtonRelease-1>',up); win.bind('<Escape>',cancel); win.protocol('WM_DELETE_WINDOW',cancel)
    def start(self,rollover=None):
        if getattr(self,'update_busy',False):return
        if self.running or self.pending or self.closing:return
        if rollover is None and hasattr(self,'colour_vars') and not self.apply_chat_style():return
        if self.saved and (not self.target or not self.api.usable(self.target.hwnd) or self.api.pid(self.target.hwnd)!=self.target.pid):
            self.target=self.api.find_saved(self.saved)
        if not self.region or not self.target:
            messagebox.showwarning('Select area','Open the saved game at the original client size, or bind the game and select chat. If several matching clients are open, close the others or bind manually.'); return
        try:
            pitch=rollover['pitch'] if rollover is not None else int(self.pitch.get()); assert 10<=pitch<=40 and self.region['height']//pitch>=3
            pytesseract.get_tesseract_version()
        except Exception as e: messagebox.showerror('Setup',f'Check line height and Tesseract installation.\n{e}'); return
        if rollover is None:
            try: self.persist()
            except Exception as e: messagebox.showwarning('Settings',f'Calibration could not be saved: {e}')
            if not self.save_session():return
        if not self.archive:
            messagebox.showerror('Session storage','History storage is unavailable. Restart the tracker after fixing storage.');return
        self.session_prices=dict(rollover['prices'] if rollover is not None else self.default_prices);self.consumable_report=cost_report([])
        self.session_loot_prices=dict(rollover.get('loot_prices',self.default_loot_prices) if rollover is not None else self.default_loot_prices);self.loot_report=loot_report([]);self.loot_rows={}
        self.party_members=list(rollover['party'] if rollover is not None else self.next_party_members)
        self.party_status.set('Session party: '+(', '.join(self.party_members) or 'solo / no estimates'))
        self.session_id=new_id(); self.session_date=now(); self.session_end=None; self.session_complete=None; self.last_archive_save=0
        if self.review_win and self.review_win.winfo_exists():
            self.review_tree.delete(*self.review_tree.get_children());self.review_selected=None
        self.reviews=ReviewQueue(); self.refresh_reviews()
        self.events=[]; self.raw=[]; self.kills=0; self.totals.clear(); self.tree.delete(*self.tree.get_children());
        if hasattr(self,'consumable_tree'):self.consumable_tree.delete(*self.consumable_tree.get_children())
        if hasattr(self,'cost_status'):self.cost_status.set('No recorded consumable costs.')
        if hasattr(self,'loot_status'):self.loot_status.set('No recorded loot values.')
        self.gaps=0; self.active_seconds=0.0; self.started=time.monotonic(); self.ended=None; self.run_id+=1; self.running=True; self.pending=2
        self.pause_gate=PauseGate(self.pause_on_blur); self.halt=threading.Event(); self.jobs=queue.Queue(maxsize=120); self.start_btn.config(state='disabled'); self.stop_btn.config(state='normal')
        paused=bool(rollover and rollover['paused'])
        if paused:self.pause_gate.toggle()
        self.pause_btn.config(text='Resume' if paused else 'Pause',state='normal')
        if hasattr(self,'reset_btn'):self.reset_btn.config(state='normal')
        self.log.config(state='normal'); self.log.delete('1.0','end'); self.log.config(state='disabled'); self.status.set('Fresh session paused — click Resume to continue.' if paused else 'Waiting for readable Lineage 2 chat. Existing messages will not be counted.')
        if hasattr(self,'dashboard'):self.dashboard.update_metrics(0,0,0,0)
        if not self.save_session():
            self.running=False; self.pending=0; self.started=None; self.session_id=None; self.start_btn.config(state='normal'); self.stop_btn.config(state='disabled'); self.pause_btn.config(state='disabled')
            if hasattr(self,'reset_btn'):self.reset_btn.config(state='disabled')
            return
        self.session_pitch=pitch;self.capture_state='WAITING FOR CHAT'
        self.session_colours=rollover['colours'] if rollover is not None else (dict(self.chat_style['colours']) if hasattr(self,'chat_style') else None)
        threading.Thread(target=self.capture,args=(self.target,dict(self.region),pitch,self.halt,self.jobs,self.pause_gate),daemon=True).start(); threading.Thread(target=self.worker,args=(self.jobs,),daemon=True).start()
    def capture(self,target,region,pitch,halt,jobs,gate):
        revision=None; old=None; failures=0; last_active=None; last_status=None
        frames=0; batches=0; last_report=time.monotonic()
        alignment=None; last_alignment_check=0; state=None; old_rgb=None
        def capture_state(value):
            nonlocal state
            if value!=state:self.inbox.put(('capture_state',value));state=value
        def status(message):
            nonlocal last_status
            if message != last_status:
                self.inbox.put(('status',message)); last_status=message
                diagnostic('capture status: %s',message.replace(target.title,'[game]') if target.title else message)
        def pause(message):
            nonlocal old, failures, last_active, alignment, old_rgb
            old=None; old_rgb=None; failures=0; last_active=None;alignment=None
            capture_state('WAITING FOR CHAT');status(message)
        try:
            api=Windows()
            with mss.mss() as s:
                while not halt.is_set():
                    tick=time.monotonic()
                    manual,current,pause_on_blur=gate.capture_policy()
                    if current!=revision:
                        old=None;old_rgb=None; failures=0; last_active=None; revision=current;alignment=None
                        capture_state('WAITING FOR CHAT')
                    if manual:
                        pause('Manually paused — click Resume to continue.'); halt.wait(.05); continue
                    rect,reason=capture_region(api,target,region,s.monitors[0],pause_on_blur=pause_on_blur)
                    if rect is None:
                        pause(reason); halt.wait(.05); continue
                    shot=s.grab(rect)
                    # Discard frames if focus or geometry changed while capturing.
                    after,reason=capture_region(api,target,region,s.monitors[0],pause_on_blur=pause_on_blur)
                    if after!=rect:
                        pause(reason or 'Paused — window moved during capture; resynchronising.'); halt.wait(.05); continue
                    rgb=np.asarray(shot)[:,:,:3][:,:,::-1]; colours=getattr(self,'session_colours',None)
                    if colours:
                        if alignment is None or (tick-last_alignment_check>=2 and (not alignment[2] or failures>=2)):
                            measured=row_alignment(rgb,pitch,colours);last_alignment_check=tick
                            # Reproject the last committed frame onto the new
                            # lattice instead of dropping messages that scrolled
                            # in while the detector was establishing confidence.
                            if alignment is None or (measured[2] and measured[:2]!=alignment[:2]):
                                if old_rgb is not None and old_rgb.shape==rgb.shape:
                                    old,_=aligned_rows(old_rgb,*measured[:2],colours)
                                else:old=None
                                failures=0;alignment=measured
                                diagnostic('Chat row calibration: configured=%d detected=%d phase=%d confident=%s',pitch,*alignment)
                            elif measured[2] and measured[:2]==alignment[:2]:alignment=measured
                        new,row_rgb=aligned_rows(rgb,*alignment[:2],colours)
                    else:
                        new=rows_of(rgb,pitch);row_rgb=rgb[:len(new)*pitch].reshape(len(new),pitch,rgb.shape[1],3)
                    # Commit only if the same unpaused revision is still current.
                    # A pause/resume during screen capture discards the stale frame.
                    with gate.lock:
                        if halt.is_set() or not gate.accepts(revision):
                            old=None;old_rgb=None; failures=0; last_active=None; alignment=None;continue
                        now=time.monotonic()
                        if last_active is not None: self.active_seconds+=max(0,now-last_active)
                        last_active=now;frames+=1
                        if now-last_report>=10:
                            diagnostic('capture progress: frames=%d queued_batches=%d active_seconds=%.1f',frames,batches,self.active_seconds)
                            last_report=now
                        status(f'Tracking {target.title} — '+('focused only.' if pause_on_blur else 'visible chat, including in background.'))
                        if old is None:
                            old=new;old_rgb=rgb.copy() if colours else None;capture_state('CHAT READY' if new.sum()>=24 else 'WAITING FOR CHAT')
                        else:
                            shift=overlap(old,new)
                            if shift is None:
                                failures+=1;capture_state('SYNCING CHAT')
                                if failures>=4:
                                    self.inbox.put(('gap','No reliable row overlap; resynchronised without counting ambiguous lines.')); old=new;old_rgb=rgb.copy() if colours else None; failures=0
                            else:
                                failures=0;capture_state('SESSION ACTIVE' if batches else 'CHAT READY')
                                if shift:
                                    try:
                                        jobs.put_nowait((datetime.now().isoformat(timespec='seconds'),row_rgb[-shift:].copy()));batches+=1;capture_state('SESSION ACTIVE')
                                    except queue.Full: self.inbox.put(('gap','OCR backlog full; some lines dropped.'))
                                old=new;old_rgb=rgb.copy() if colours else None
                    halt.wait(max(0,.05-(time.monotonic()-tick)))
        except Exception as e:
            diagnostic('capture exception',exc_info=True)
            self.inbox.put(('gap',f'Capture stopped: {e}')); halt.set()
        finally:
            diagnostic('capture ended: frames=%d queued_batches=%d active_seconds=%.1f',frames,batches,self.active_seconds)
            jobs.put(None); self.inbox.put(('done','capture'))
    def worker(self,jobs):
        deferred=None
        while True:
            job=deferred if deferred is not None else jobs.get()
            deferred=None
            if job is None:break
            ts,rows=job
            # Coalesce compatible rows only: automatic alignment can change
            # pitch mid-session while previous OCR jobs remain queued.
            end=False; group=[rows]
            while sum(len(x) for x in group)<16:
                try: nxt=jobs.get_nowait()
                except queue.Empty:break
                if nxt is None: end=True; break
                if nxt[1].shape[1:]!=rows.shape[1:]:
                    deferred=nxt;break
                group.append(nxt[1])
            try:
                colours=getattr(self,'session_colours',None)
                results=configured_ocr_rows(np.concatenate(group),colours) if colours else ocr_rows(np.concatenate(group))
                for kind,line in results:
                    if line.strip():self.inbox.put((kind,(ts,line)))
            except Exception as e:
                diagnostic('OCR exception',exc_info=True)
                self.inbox.put(('gap',f'OCR error: {e}'))
            if end:break
        self.inbox.put(('done','ocr'))
    def toggle_pause(self):
        if not self.running:return
        paused=self.pause_gate.toggle()
        diagnostic('manual pause: %s',paused)
        self.pause_btn.config(text='Resume' if paused else 'Pause')
        self.status.set('Manually paused — click Resume to continue. Buffered lines may still finish.' if paused else 'Resuming — keep Lineage 2 chat visible. Chat will resynchronise.')
        self.append('SESSION: Manually paused.' if paused else 'SESSION: Resumed; skipped messages will not be recovered.')
    def reset_session(self):
        if not self.running or self.closing or getattr(self,'update_busy',False) or getattr(self,'reset_request',None) is not None:return
        # Keep the active configuration, not unapplied edits in Settings.
        colours=getattr(self,'session_colours',None)
        self.reset_request=dict(pitch=self.session_pitch, colours=dict(colours) if colours is not None else None, prices=dict(self.session_prices), loot_prices=dict(getattr(self,'session_loot_prices',{})), party=list(self.party_members), paused=self.pause_gate.snapshot()[0])
        self.stop()
        self.status.set('Resetting — saving this session and finishing buffered OCR…')
    def stop(self):
        if self.hud: self.hud.cancel_placement(); self.hud.hide()
        if self.running:self.halt.set(); self.running=False; self.ended=time.monotonic(); self.session_end=now(); self.stop_btn.config(state='disabled'); self.pause_btn.config(text='Pause',state='disabled'); self.status.set('Stopped capturing; processing buffered lines…')
        if hasattr(self,'reset_btn'):self.reset_btn.config(state='disabled')
    def append(self,s):
        self.log.config(state='normal'); self.log.insert('end',s+'\n',('accepted' if s.startswith('✓') else 'review' if 'REVIEW' in s or s.startswith('WARNING') else 'ignored',)); self.log.see('end'); self.log.config(state='disabled')
    def tick(self):
        try:self.process_inbox()
        except Exception:
            diagnostic('UI processing exception',exc_info=True)
            self.status.set('Tracker UI error — see tracker-diagnostics.log in LocalAppData. Stop and restart the session if needed.')
            if self.running:self.stop()
        finally:
            try:
                if self.root.winfo_exists():self.root.after(100,self.tick)
            except tk.TclError:pass
    def process_inbox(self):
        changed=False; finished=False
        while True:
            try: kind,data=self.inbox.get_nowait()
            except queue.Empty:break
            if kind=='hud_pause':
                if self.running and data==self.run_id:self.toggle_pause()
            elif kind=='hud_reset':
                if self.running and data==self.run_id:self.reset_session()
            elif kind=='hud_move':self.save_hud_position(data)
            elif kind=='done':
                self.pending-=1
                if data=='capture' and self.running:self.stop()
                if not self.pending:
                    finished=True; self.start_btn.config(state='normal'); self.status.set('Session complete. Review OCR lines and warnings before relying on totals.')
            elif kind=='capture_state':self.capture_state=data
            elif kind=='status':
                if self.running and not self.pause_gate.snapshot()[0] and not data.startswith('Manually paused'): self.status.set(data)
            elif kind=='gap':self.gaps+=1; self.append('WARNING: '+data); self.raw.append((datetime.now().isoformat(timespec='seconds'),'gap',data)); changed=True
            elif kind=='uncertain' or kind.startswith('uncertain:'):
                ts,line=data; self.gaps+=1; r=self.reviews.add(ts,line,category=kind.partition(':')[2] or None); self.raw.append((ts,'uncertain',f'#{r.id}: {line}')); self.append(f'REVIEW #{r.id} (not counted): '+line); self.refresh_reviews(); changed=True
            elif kind in ('xp_partial','sp_partial','xp_recovered'):
                ts,line=data; event=parse_xp_resolution(kind,line)
                self.raw.append((ts,kind,line))
                if event:
                    typ,who,item,q,sp=event; self.events.append((ts,typ,who,item,q,sp,line))
                    if q is not None: self.totals[(who,item)]+=q
                    if sp is not None: self.totals[(who,'SP')]+=sp
                    if q is None or sp is None:
                        self.gaps+=1; r=self.reviews.add(ts,line,len(self.events)-1,q,sp); self.refresh_reviews()
                        label='XP counted; SP unknown' if sp is None else 'SP counted; XP unknown'
                        self.append(f'REVIEW #{r.id} ({label}): '+line)
                    else: self.append('✓ (SP majority): '+line)
                    changed=True
            elif kind=='line':
                ts,line=data; event=parse(line); self.raw.append((ts,'parsed' if event else 'ignored',line)); self.append(('✓ ' if event else '  ')+line)
                if event:
                    typ,who,item,q,sp=event; self.events.append((ts,typ,who,item,q,sp,line))
                    if typ!='consumable':self.totals[(who,item)]+=q
                    if typ=='xp':self.totals[(who,'SP')]+=sp
                    changed=True
        if changed: self.refresh_totals()
        if finished and hasattr(self,'player'):self.player.tick(finished=True)
        if self.session_id and (finished or (self.running and time.monotonic()-self.last_archive_save>=15)):
            saved=self.save_session(quiet=not finished)
            if saved and finished:self.status.set('Session saved. Open Session history to rename or merge it.')
            if finished and getattr(self,'reset_request',None) is not None:
                request=self.reset_request;self.reset_request=None
                if saved and not self.closing:
                    # Both old workers have finished and the archive is committed.
                    # Start with a fresh capture baseline and never replay old rows.
                    self.start(rollover=request)
                    if self.running and getattr(self,'history_window',None):self.history_window.refresh()
                elif not saved:self.status.set('Reset cancelled — previous session could not be saved. Retry saving before starting another session.')
        if self.closing and not self.pending:
            self.closing=False
            if self.close():return
        if hasattr(self,'player'):self.player.tick()
        if self.started is not None:
            dur=self.active_seconds; h=max(1,dur)/3600; xp=self.totals[('You','XP / SP')]; sp=self.totals[('You','SP')]; ad=self.totals[('You','Adena')]
            if hasattr(self,'dashboard'):self.dashboard.update_metrics(dur,ad,xp,self.kills)
            if hasattr(self,'cost_status'):self.cost_status.set(cost_summary(self.consumable_report,ad,dur))
            if hasattr(self,'loot_status'):self.loot_status.set(loot_summary(self.loot_report,dur))
            self.stats.set(f'{"PAUSED  |  " if self.running and self.pause_gate.snapshot()[0] else ""}Active {int(dur)//3600:02}:{int(dur)%3600//60:02}:{int(dur)%60:02}  |  SP {sp:,}  |  Capture/OCR warnings {self.gaps}  |  Pending review {len(self.reviews.pending)}')
            if getattr(self,'party_members',[]):
                extra=party_summary(live_party_report(self.party_members,dur,self.totals))
                extra+=f' Each listed member: {ad:,} estimated ({ad/h:,.0f}/h).'
                self.stats.set(self.stats.get()+'\n'+extra)
    def refresh_totals(self):
        self.kills=count_kills(self.events)
        selected_loot=None
        if hasattr(self,'loot_status'):
            selected=self.tree.selection()
            selected_loot=self.loot_rows.get(selected[0]) if selected else None
            self.loot_report=loot_report([dict(events=self.events,loot_prices=self.session_loot_prices)])
            self.loot_rows={}
        self.tree.delete(*self.tree.get_children())
        if hasattr(self,'consumable_tree'):
            selected=self.consumable_tree.selection()
            old=self.consumable_tree.item(selected[0],'values')[0] if selected else None
            self.consumable_report=cost_report([dict(events=self.events,consumable_prices=self.session_prices)])
            self.consumable_tree.delete(*self.consumable_tree.get_children())
            for r in self.consumable_report['rows']:
                unit=money(next(iter(r['prices']))) if len(r['prices'])==1 else 'Not set'
                iid=self.consumable_tree.insert('','end',values=(r['item'],f"{r['uses']:,}",unit,money(r['cost']) if r['priced'] else '—'))
                if r['item']==old:self.consumable_tree.selection_set(iid)
            self.cost_status.set(cost_summary(self.consumable_report,self.totals['You','Adena'],self.active_seconds))
        valued={(r['who'],r['item']):r for r in self.loot_report['rows']} if hasattr(self,'loot_status') else {}
        for (who,item),qty in sorted(self.totals.items()):
            if item in ('XP / SP','SP'):continue
            r=valued.get((who,item))
            if r is None:self.tree.insert('','end',values=(who,item,f'{qty:,}'));continue
            iid=self.tree.insert('','end',values=(who,item,f'{qty:,}',unit_label(r),money(r['value']) if r['priced'] else '—'))
            self.loot_rows[iid]=(who,item)
            if selected_loot==(who,item):self.tree.selection_set(iid)
        if hasattr(self,'loot_status'):self.loot_status.set(loot_summary(self.loot_report,self.active_seconds))
        for row in party_rows(live_party_report(getattr(self,'party_members',[]),self.active_seconds,self.totals)):
            # Rates use the live timer in the summary; row amounts refresh on events.
            if row[1]!='Adena/hr (estimated)':self.tree.insert('','end',values=row)
    def edit_loot_value(self,event=None):
        if getattr(self,'update_busy',False) or getattr(self,'reset_request',None) is not None:return
        if event is not None and self.tree.identify_region(event.x,event.y)!='cell':return
        selected=self.tree.selection()
        pair=self.loot_rows.get(selected[0]) if selected else None
        if not pair:
            messagebox.showinfo('Item value','Select an actual item drop, not Adena or an estimated party row.',parent=self.root);return
        _,item=pair;k=cost_key(item);session_id=self.session_id
        value=simpledialog.askstring('Item sell value',f'{item}: expected Adena received per individual item (e.g. NPC sell price). Blank removes the value. Applies to all copies of this item in this session.',initialvalue=self.session_loot_prices.get(k,''),parent=self.root)
        if value is None or self.session_id!=session_id or getattr(self,'reset_request',None) is not None:return
        try:
            if value.strip():self.session_loot_prices[k]=validate_price(value)
            else:self.session_loot_prices.pop(k,None)
        except ValueError as e:messagebox.showwarning('Item value',str(e),parent=self.root);return
        if self.running or self.pending:
            defaults=dict(self.default_loot_prices)
            if k in self.session_loot_prices:defaults[k]=self.session_loot_prices[k]
            else:defaults.pop(k,None)
            try:save_loot_prices(defaults);self.default_loot_prices=defaults
            except OSError as e:messagebox.showwarning('Item value',f'Session value changed; future default could not be saved: {e}',parent=self.root)
        self.refresh_totals();self.save_session()
    def edit_default_loot_value(self):
        if getattr(self,'update_busy',False):return
        selected=self.tree.selection()
        pair=self.loot_rows.get(selected[0]) if selected else None
        name=simpledialog.askstring('Default item value','Enter the item name exactly as shown in game.',initialvalue=pair[1] if pair else '',parent=self.root)
        if name is None or not cost_key(name):return
        k=cost_key(name)
        value=simpledialog.askstring('Default item value',f'{name}: expected Adena per item for future sessions. Blank removes the default; saved sessions are not repriced.',initialvalue=self.default_loot_prices.get(k,''),parent=self.root)
        if value is None:return
        try:
            defaults=dict(self.default_loot_prices)
            if value.strip():defaults[k]=validate_price(value)
            else:defaults.pop(k,None)
            save_loot_prices(defaults);self.default_loot_prices=defaults
        except (ValueError,OSError) as e:messagebox.showwarning('Item value',str(e),parent=self.root);return
        self.status.set('Default item value saved for future sessions. Edit a recorded item to change the current session.')
    def edit_consumable_cost(self,event=None):
        if getattr(self,'update_busy',False):return
        if event is not None and self.consumable_tree.identify_region(event.x,event.y)!='cell':return
        selection=self.consumable_tree.selection()
        if not selection:
            messagebox.showinfo('Consumable costs','Select a recorded consumable first, or use Set default cost to enter a price before use.',parent=self.root);return
        name=self.consumable_tree.item(selection[0],'values')[0];k=cost_key(name)
        value=simpledialog.askstring('Consumable cost',f'{name}: Adena per observed activation. If each use consumes multiple units, enter their combined cost. Blank removes the price. Applies to all uses in this session.',initialvalue=self.session_prices.get(k,''),parent=self.root)
        if value is None:return
        try:
            if value.strip():self.session_prices[k]=validate_price(value)
            else:self.session_prices.pop(k,None)
        except ValueError as e:messagebox.showwarning('Consumable cost',str(e),parent=self.root);return
        # A historical edit must not silently reprice future sessions.
        if self.running or self.pending:
            defaults=dict(self.default_prices)
            if k in self.session_prices:defaults[k]=self.session_prices[k]
            else:defaults.pop(k,None)
            try:save_prices(defaults);self.default_prices=defaults
            except OSError as e:messagebox.showwarning('Consumable cost',f'Session price changed; future default could not be saved: {e}',parent=self.root)
        self.refresh_totals();self.save_session()

    def edit_default_cost(self):
        if getattr(self,'update_busy',False):return
        selection=self.consumable_tree.selection()
        initial=self.consumable_tree.item(selection[0],'values')[0] if selection else ''
        name=simpledialog.askstring('Default consumable cost','Enter the consumable name exactly as shown in game (e.g. Soulshot: No Grade).',initialvalue=initial,parent=self.root)
        if name is None or not cost_key(name):return
        k=cost_key(name)
        value=simpledialog.askstring('Default cost',f'{name}: Adena per activation for future sessions. Blank removes the default. This does not reprice saved sessions.',initialvalue=self.default_prices.get(k,''),parent=self.root)
        if value is None:return
        try:
            defaults=dict(self.default_prices)
            if value.strip():defaults[k]=validate_price(value)
            else:defaults.pop(k,None)
            save_prices(defaults);self.default_prices=defaults
        except (ValueError,OSError) as e:messagebox.showwarning('Default cost',str(e),parent=self.root);return
        self.status.set('Default consumable cost saved for future sessions. Edit a recorded row to change the current session.')

    def refresh_reviews(self):
        self.review_count.set(f'Review ({len(self.reviews.pending)})')
        if hasattr(self,'tabs'):self.tabs.tab(self.pages['review'],text=f'Reviews ({len(self.reviews.pending)})')
        if not self.review_win or not self.review_win.winfo_exists(): return
        # Preserve current selection and any unsaved manual edit as new OCR arrives.
        ids=set(self.review_tree.get_children())
        category=self.review_filter.get()
        groups={i:(r.category or review_fields(r,parse,xp_numeric_candidate)['kind']) for i,r in self.reviews.pending.items()}
        for key,button in self.review_filters.items():
            count=sum(1 for c in groups.values() if key=='all' or c==key)
            button.configure(text=f'{self.review_labels[key]} ({count})')
        wanted={str(i) for i,c in groups.items() if category=='all' or c==category}
        for i in ids-wanted:self.review_tree.delete(i)
        for i,r in self.reviews.pending.items():
            if str(i) in wanted and str(i) not in ids:
                self.review_tree.insert('','end',iid=str(i),values=(r.timestamp, 'XP already counted' if r.xp_counted is not None else 'SP already counted' if r.sp_counted is not None else 'Not counted',r.text.split(' [',1)[0]))
        if not self.review_tree.selection() and wanted:
            first=self.review_tree.get_children()[0]; self.review_tree.selection_set(first); self.review_tree.focus(first); self.show_review()
        elif not wanted:self.show_review()
    def open_reviews(self):
        self.navigate('review')
    def build_reviews(self):
        if self.review_win and self.review_win.winfo_exists():return
        self.review_win=self.pages['review']
        self.review_scroll=ScrollPage(self.review_win);self.review_scroll.pack(fill='both',expand=True);win=self.review_scroll.content
        ttk.Label(win,text='OCR review',style='Title.TLabel',padding=(12,10,12,0)).pack(anchor='w')
        ttk.Label(win,text='Select a message, confirm the type and enter the missing numbers. Already-counted amounts are locked.',wraplength=740,padding=10).pack(fill='x')
        filters=ttk.Frame(win);filters.pack(fill='x',padx=10,pady=(0,6))
        self.review_filter=tk.StringVar(value='all');self.review_filters={}
        self.review_labels={'all':'All','xp':'XP / SP','adena':'Adena','item':'Items','consumable':'Consumables'}
        for key,label in self.review_labels.items():
            b=ttk.Radiobutton(filters,text=label,value=key,variable=self.review_filter,command=self.refresh_reviews)
            b.pack(side='left',padx=(0,10));self.review_filters[key]=b
        frame=ttk.Frame(win); frame.pack(fill='both',expand=True,padx=10)
        self.review_tree=ttk.Treeview(frame,columns=('time','state','line'),show='headings',selectmode='browse',height=6)
        for c,t,w in [('time','Captured',155),('state','Status',130),('line','Message',460)]:
            self.review_tree.heading(c,text=t); self.review_tree.column(c,width=w)
        scroll=ttk.Scrollbar(frame,orient='vertical',command=self.review_tree.yview); self.review_tree.configure(yscrollcommand=scroll.set); scroll.pack(side='right',fill='y'); self.review_tree.pack(fill='both',expand=True)
        evidence=ttk.Frame(win);evidence.pack(fill='x',padx=10,pady=5)
        self.review_evidence=tk.Text(evidence,height=5,wrap='word',state='disabled'); self.review_evidence.pack(side='left',fill='x',expand=True)
        sb=ttk.Scrollbar(evidence,orient='vertical',command=self.review_evidence.yview);sb.pack(side='right',fill='y');self.review_evidence.configure(yscrollcommand=sb.set)
        editor=ttk.LabelFrame(win,text='Corrected values',padding=8);editor.pack(fill='x',padx=10)
        self.review_kind=tk.StringVar()
        self.review_type_buttons=[]
        types=ttk.Frame(editor);types.pack(fill='x')
        for label,value in [('XP / SP','xp'),('Adena','adena'),('Item','item'),('Consumable','consumable')]:
            b=ttk.Radiobutton(types,text=label,value=value,variable=self.review_kind,command=self.review_mode)
            b.pack(side='left',padx=(0,18));self.review_type_buttons.append(b)
        self.review_xp=tk.StringVar();self.review_sp=tk.StringVar();self.review_adena=tk.StringVar();self.review_who=tk.StringVar()
        self.review_xp_frame=ttk.Frame(editor)
        ttk.Label(self.review_xp_frame,text='XP').pack(side='left')
        self.review_xp_entry=ttk.Entry(self.review_xp_frame,textvariable=self.review_xp,width=13);self.review_xp_entry.pack(side='left',padx=(6,18))
        ttk.Label(self.review_xp_frame,text='SP').pack(side='left')
        self.review_sp_entry=ttk.Entry(self.review_xp_frame,textvariable=self.review_sp,width=13);self.review_sp_entry.pack(side='left',padx=6)
        self.review_adena_frame=ttk.Frame(editor)
        ttk.Label(self.review_adena_frame,text='Adena').pack(side='left')
        self.review_adena_entry=ttk.Entry(self.review_adena_frame,textvariable=self.review_adena,width=13);self.review_adena_entry.pack(side='left',padx=(6,18))
        ttk.Label(self.review_adena_frame,text='Recipient').pack(side='left')
        self.review_who_entry=ttk.Combobox(self.review_adena_frame,textvariable=self.review_who,width=20,values=['You',*getattr(self,'party_members',[])])
        self.review_who_entry.pack(side='left',padx=6)
        self.review_item_frame=ttk.Frame(editor)
        self.review_input=tk.StringVar(); self.review_edit=ttk.Combobox(self.review_item_frame,textvariable=self.review_input,state='normal')
        self.review_edit.pack(fill='x',expand=True)
        self.review_hint=tk.StringVar();self.review_hint_label=ttk.Label(editor,textvariable=self.review_hint,wraplength=740);self.review_hint_label.pack(fill='x',pady=(5,0))
        buttons=ttk.Frame(win,padding=10); buttons.pack(fill='x')
        self.approve_btn=ttk.Button(buttons,text='Approve & count',command=self.approve_review,style='Primary.TButton'); self.approve_btn.pack(side='left')
        self.dismiss_btn=ttk.Button(buttons,text='Dismiss (ignore)',command=self.dismiss_review); self.dismiss_btn.pack(side='left',padx=8)
        ttk.Button(buttons,text='Dashboard',command=lambda:self.navigate('dashboard')).pack(side='right')
        self.appearance.restyle(win)
        self.review_tree.bind('<<TreeviewSelect>>',self.show_review); self.review_selected=None; self.refresh_reviews()
    def selected_review(self):
        sel=self.review_tree.selection()
        return self.reviews.pending.get(int(sel[0])) if sel else None
    def show_review(self,*_):
        r=self.selected_review(); id=r.id if r else None
        if id==self.review_selected and r: return
        self.review_selected=id
        self.review_evidence.config(state='normal'); self.review_evidence.delete('1.0','end')
        self.review_evidence.insert('1.0',r.text if r else 'No pending reviews.'); self.review_evidence.config(state='disabled')
        fields=review_fields(r,parse,xp_numeric_candidate) if r else dict(kind='',xp='',sp='',adena='',who='',full='',options=[])
        for name in ('kind','xp','sp','adena','who'):
            getattr(self,'review_'+name).set(fields[name])
        self.review_who_entry.configure(values=['You',*getattr(self,'party_members',[])])
        self.review_edit.configure(values=fields['options'])
        self.review_input.set(fields['full'])
        self.review_mode()
        self.dismiss_btn.config(state='normal' if r else 'disabled')
    def review_mode(self):
        r=self.selected_review();kind=self.review_kind.get()
        partial=bool(r and r.event_index is not None)
        if partial:kind='xp';self.review_kind.set(kind)
        elif r and r.category:kind=r.category;self.review_kind.set(kind)
        for b in self.review_type_buttons:
            b.config(state='disabled' if not r or partial or r.category else 'normal')
        for frame in (self.review_xp_frame,self.review_adena_frame,self.review_item_frame):frame.pack_forget()
        if kind=='xp' and r:
            self.review_xp_entry.config(state='readonly' if r.xp_counted is not None else 'normal')
            self.review_sp_entry.config(state='readonly' if r.sp_counted is not None else 'normal')
            self.review_xp_frame.pack(fill='x',pady=5,before=self.review_hint_label)
            self.review_hint.set('XP already counted; enter SP only.' if r.xp_counted is not None else 'SP already counted; enter XP only.' if r.sp_counted is not None else 'Enter XP and SP. Conflicting or unknown readings are left blank.')
            if self.review_win.winfo_viewable():(self.review_sp_entry if r.xp_counted is not None else self.review_xp_entry).focus_set()
        elif kind=='adena' and r:
            self.review_adena_frame.pack(fill='x',pady=5,before=self.review_hint_label)
            self.review_hint.set('Enter the Adena amount and confirm the recipient.')
            if self.review_win.winfo_viewable():self.review_adena_entry.focus_set()
        elif kind in ('item','consumable') and r:
            self.review_item_frame.pack(fill='x',pady=5,before=self.review_hint_label)
            self.review_hint.set('Correct the full usage message, e.g. Use Soulshot: No Grade.' if kind=='consumable' else 'Correct the full item message for personal or party loot.')
            if self.review_win.winfo_viewable():self.review_edit.focus_set()
        else:self.review_hint.set('Choose a message type.' if r else 'No pending reviews.')
        self.approve_btn.config(state='normal' if r and kind else 'disabled')
    def approve_review(self):
        r=self.selected_review()
        if not r:return
        try:
            corrected=correction_message(r,self.review_kind.get(),self.review_xp.get(),self.review_sp.get(),self.review_adena.get(),self.review_who.get(),self.review_input.get())
            self.reviews.approve(r.id,corrected,parse,self.events,self.totals)
        except ValueError as e:messagebox.showwarning('Review',str(e),parent=self.review_win); return
        self.raw.append((r.timestamp,'review_approved',f'#{r.id}: {corrected} | original: {r.text}'))
        self.append(f'✓ REVIEW #{r.id} approved: {corrected}'+(' (SP only added; XP already counted)' if r.xp_counted is not None else ' (XP only added; SP already counted)' if r.sp_counted is not None else ''))
        self.refresh_totals(); self.refresh_reviews(); self.save_session()
    def dismiss_review(self):
        r=self.selected_review()
        if not r:return
        if not messagebox.askyesno('Dismiss review','Ignore this uncertain message? Already counted XP or SP will remain.',parent=self.review_win):return
        self.reviews.discard(r.id); self.raw.append((r.timestamp,'review_dismissed',f'#{r.id}: {r.text}')); self.append(f'REVIEW #{r.id} dismissed.'); self.refresh_reviews(); self.save_session()
    def arm_hud_move(self):
        if not self.running or not self.hud or not self.hud_enabled.get():
            messagebox.showinfo('Move HUD','Start a session and enable Game HUD first. You can also use Position HUD without starting.'); return
        if self.hud.placement is not None:
            self.hud.cancel_placement(); self.move_btn.config(text='Move HUD in game'); return
        self.hud.arm_placement()
        self.move_btn.config(text='Cancel HUD move')
        self.status.set('HUD move armed — return to Lineage 2, move the mouse, then tap Shift to save. Alt-tab again to cancel.')
    def open_position(self):
        if getattr(self,'update_busy',False):return
        if self.position_win and self.position_win.winfo_exists():self.position_win.lift();return
        if not self.hud or not self.region or not (self.target or self.saved):
            messagebox.showinfo('Position HUD','Bind the game and chat area first.');return
        WIDTH,HEIGHT=self.hud.dimensions();extra=self.player.protected()
        width,height=(self.target.width,self.target.height) if self.target else (self.saved['width'],self.saved['height'])
        geo=(0,0,width,height); region=dict(self.region)
        if not hud_position(geo,region,size=(WIDTH,HEIGHT),extra=extra):
            messagebox.showinfo('Position HUD','The calibrated game window is too small for the HUD.');return
        self.hud.cancel_placement()
        win=tk.Toplevel(self.root); self.position_win=win; win.title('Position game HUD'); win.transient(self.root); self.appearance.restyle(win)
        scale=min(1,760/width,490/height,max(0.1,(win.winfo_screenwidth()-100)/width),max(0.1,(win.winfo_screenheight()-230)/height))
        ttk.Label(win,text='Drag the HUD in this game layout, then click Save. The shaded chat area is protected.',wraplength=680,padding=10).pack()
        canvas=tk.Canvas(win,width=round(width*scale),height=round(height*scale),bg='#242b35',highlightthickness=0); canvas.pack(padx=12)
        l,t,r,b=(region[k] for k in ('left','top','width','height'))
        canvas.create_rectangle(l*scale,t*scale,(l+r)*scale,(t+b)*scale,fill='#583b36',outline='#be796a')
        canvas.create_text((l+r/2)*scale,(t+b/2)*scale,text='OCR chat area',fill='white')
        for r in extra:canvas.create_rectangle(r['left']*scale,r['top']*scale,(r['left']+r['width'])*scale,(r['top']+r['height'])*scale,fill='#365e83',outline='cyan')
        pos=list(hud_position(geo,region,preferred=self.hud.preferred,size=(WIDTH,HEIGHT),extra=extra)); offset=[]
        def draw():
            canvas.delete('hud'); x,y=pos
            canvas.create_rectangle(x*scale,y*scale,(x+WIDTH)*scale,(y+HEIGHT)*scale,fill='#151a22',outline='#98a6b8',width=2,tags='hud')
            canvas.create_text((x+WIDTH/2)*scale,(y+27)*scale,text='  |  '.join(WIDGETS[k][1] for k in self.hud_config['enabled']),fill='#f4d183',font=('Segoe UI',max(7,int(12*scale)),'bold'),tags='hud')
            canvas.create_text((x+WIDTH-54)*scale,(y+71)*scale,text='Pause',fill='#e6edf5',font=('Segoe UI',max(7,int(10*scale))),tags='hud')
        def down(e):
            x,y=e.x/scale,e.y/scale
            if pos[0]<=x<pos[0]+WIDTH and pos[1]<=y<pos[1]+HEIGHT:offset[:]=[x-pos[0],y-pos[1]]
        def drag(e):
            if offset:
                candidate=safe_position(geo,region,None,(round(e.x/scale-offset[0]),round(e.y/scale-offset[1])),(WIDTH,HEIGHT),extra)
                if candidate is not None:pos[:]=candidate;draw()
        def save():
            self.hud.preferred=tuple(pos); self.save_hud_position(tuple(pos));win.destroy()
        def reset():
            pos[:]=hud_position(geo,region,size=(WIDTH,HEIGHT),extra=extra);draw()
        canvas.bind('<Button-1>',down); canvas.bind('<B1-Motion>',drag);canvas.bind('<ButtonRelease-1>',lambda e:offset.clear());draw()
        buttons=ttk.Frame(win,padding=10); buttons.pack(fill='x')
        ttk.Button(buttons,text='Reset to default',command=reset).pack(side='left')
        ttk.Button(buttons,text='Save position',command=save).pack(side='right')
        ttk.Button(buttons,text='Cancel',command=win.destroy).pack(side='right',padx=8)
    def hud_tick(self):
        if self.hud and self.api:
            try:
                report=getattr(self,'consumable_report',{})
                net=getattr(self,'hud_net_adena',False)
                player=getattr(self,'player',None)
                widgets=dict(getattr(player,'widgets',{}),loot=('LOOT/H',rate_text(getattr(self,'loot_report',{}).get('value',0),self.active_seconds)),cost=('COST/H',rate_text(report.get('cost',0),self.active_seconds)))
                self.hud.update(self.api,self.target,self.region,self.running and self.hud_enabled.get(),self.active_seconds,self.totals[('You','Adena')],self.totals[('You','XP / SP')],self.kills,paused=self.pause_gate.snapshot()[0],consumable_cost=report.get('cost',0) if net else None,unpriced_uses=report.get('unpriced',0) if net else 0,widgets=widgets,protected=player.protected() if player else (),capture_state=getattr(self,'capture_state','SESSION ACTIVE'))
            except Exception as e:
                diagnostic('HUD update exception',exc_info=True)
                hud,self.hud=self.hud,None
                self.hud_enabled.set(False);self.append(f'HUD disabled: {e}')
                try:hud.close()
                except Exception:diagnostic('HUD close exception',exc_info=True)
        self.move_btn.config(text='Cancel HUD move' if self.hud and self.hud.placement is not None else 'Move HUD in game')
        self.root.after(25,self.hud_tick)
    def export(self):
        if getattr(self,'update_busy',False):return
        if self.pending: messagebox.showinfo('Export','Stop tracking and allow the OCR queue to finish first.');return
        path=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')],initialfile='l2-session.csv')
        if not path:return
        with open(path,'w',newline='',encoding='utf-8-sig') as f:
            w=csv.writer(f);w.writerow(['timestamp','type','player','item','quantity_or_xp','sp','raw_text']);w.writerows(self.events)
        rawpath=str(Path(path).with_suffix(''))+'-raw.csv'
        with open(rawpath,'w',newline='',encoding='utf-8-sig') as f:
            w=csv.writer(f);w.writerow(['timestamp','status','raw_text']);w.writerows(self.raw)
        costpath=str(Path(path).with_suffix(''))+'-consumables.csv'
        write_cost_csv(costpath,cost_report([dict(events=self.events,consumable_prices=self.session_prices)]))
        lootpath=str(Path(path).with_suffix(''))+'-loot-values.csv'
        write_loot_csv(lootpath,loot_report([dict(events=self.events,loot_prices=self.session_loot_prices)]))
        messagebox.showinfo('Exported',f'{path}\n{rawpath}\n{costpath}\n{lootpath}')
    def save_session(self,quiet=False):
        if not self.session_id:return True
        self.last_archive_save=time.monotonic()
        try:
            if not self.archive:raise RuntimeError('Session archive is unavailable.')
            self.archive.save(self.session_id,'Session '+self.session_date.replace('T',' '),snapshot(self))
            return True
        except Exception as e:
            if quiet:self.append(f'WARNING: Session checkpoint failed: {e}')
            else:messagebox.showerror('Session save failed',f'{e}\nYour current session remains in memory. Retry or export CSV before closing.')
            return False
    def clear_deleted_session(self):
        # The stopped session can no longer be checkpointed or resurrected.
        self.session_id=None;self.session_date=None;self.session_end=None;self.session_complete=None
        self.started=None;self.ended=None;self.active_seconds=0;self.events=[];self.raw=[];self.totals.clear()
        self.kills=0;self.gaps=0;self.party_members=[];self.reviews=ReviewQueue()
        self.log.config(state='normal');self.log.delete('1.0','end');self.log.config(state='disabled')
        self.refresh_totals();self.refresh_reviews()
        self.dashboard.update_metrics(0,0,0,0);self.stats.set('No session')
        self.party_status.set('Next session: '+(', '.join(self.next_party_members) or 'solo / no estimates'))
        self.status.set('Session deleted. Start a new session when ready.')
    def open_history(self):
        self.navigate('history')
    def restore_session(self,id):
        if getattr(self,'update_busy',False):return False
        if self.running or self.pending:
            messagebox.showinfo('History','Stop tracking and wait for buffered OCR before opening a previous session.');return False
        if not self.save_session():return False
        try:
            r=self.archive.records()[id]
            if r['kind']!='original':raise ValueError('Only original sessions can be opened for review.')
            d=r['data'];events=[tuple(e) for e in d['events']];raw=[tuple(e) for e in d['raw']];reviews=review_queue(d);totals=totals_for(events)
        except Exception as e:messagebox.showerror('History',str(e));return False
        self.session_prices=clean_prices(d.get('consumable_prices',{}))
        self.session_loot_prices=clean_prices(d.get('loot_prices',{}))
        self.party_members=list(d.get('party_members',[]))
        self.party_status.set('Saved session party: '+(', '.join(self.party_members) or 'not configured'))
        self.session_id=id;self.session_date=d['start'];self.session_end=d['end'];self.session_complete=d['complete'];self.active_seconds=d['seconds'];self.events=events;self.raw=raw;self.reviews=reviews;self.totals=totals;self.gaps=d['gaps'];self.started=time.monotonic();self.ended=self.started
        self.log.config(state='normal');self.log.delete('1.0','end');self.log.config(state='disabled')
        for ts,status,line in self.raw[-100:]:self.append(f'{status}: {line}')
        if self.review_win and self.review_win.winfo_exists():
            self.review_tree.delete(*self.review_tree.get_children());self.review_selected=None
        self.refresh_totals();self.refresh_reviews();self.status.set(f"Opened saved session: {r['name']}. Reviews will update the archive and merged reports.")
        return True
    def close(self):
        if getattr(self,'update_busy',False):
            messagebox.showinfo('Update in progress','The update is being verified. Close after it finishes or reports an error.');return False
        if self.running or self.pending:
            if self.closing:return
            self.reset_request=None
            self.closing=True;self.start_btn.config(state='disabled');self.stop();self.status.set('Saving session — finishing buffered OCR before closing…');return
        if not self.save_session():
            if not messagebox.askyesno('Quit without saving','Session could not be saved. Close anyway? Unsaved changes will be lost.'):return False
        if getattr(self,'hud_opacity_save_job',None) is not None:self.flush_hud_opacity()
        if self.hud:self.hud.close()
        self.root.destroy();return True

def portable_self_test(report):
    """Run without opening a session or changing real calibration/history."""
    import json, sqlite3
    from PIL import ImageDraw, ImageFont
    output = Path(report)
    try:
        exe = configure_ocr()
        if not exe: raise RuntimeError('Tesseract not found')
        version = str(pytesseract.get_tesseract_version())
        if 'eng' not in pytesseract.get_languages(config=''):
            raise RuntimeError('English OCR language is missing')
        font = ImageFont.truetype(str(Path(os.environ['WINDIR']) / 'Fonts' / 'arial.ttf'), 36)
        image = Image.new('RGB', (440, 90), 'white')
        ImageDraw.Draw(image).text((16, 16), '221 XP and 9 SP', font=font, fill='black')
        result = pytesseract.image_to_string(image, config='--psm 7', timeout=15).strip()
        if result != '221 XP and 9 SP': raise RuntimeError(f'OCR smoke test mismatch: {result!r}')
        root = tk.Tk(); root.withdraw(); root.update_idletasks(); root.destroy()
        with sqlite3.connect(':memory:') as db: db.execute('SELECT 1').fetchone()
        with mss.mss() as capture:
            if not capture.monitors: raise RuntimeError('Screen capture unavailable')
        output.write_text(json.dumps({'ok': True, 'ocr': version, 'text': result}, indent=2), encoding='utf-8')
        return 0
    except Exception as exc:
        output.write_text(json.dumps({'ok': False, 'error': repr(exc)}, indent=2), encoding='utf-8')
        return 1

if __name__=='__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        sys.exit(portable_self_test(sys.argv[2]))
    if os.name=='nt':
        try:
            import ctypes; ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:pass
    setup_diagnostics()
    root=tk.Tk()
    def callback_error(exc,value,tb):
        diagnostic('Tk callback exception',exc_info=(exc,value,tb))
        messagebox.showerror('Tracker error','A control failed. See tracker-diagnostics.log in the tracker data folder.',parent=root)
    root.report_callback_exception=callback_error
    def open_tracker():
        try:configure_ocr()
        except Exception as e:
            root.withdraw();messagebox.showerror('OCR setup',str(e));root.destroy();return
        App(root)
    if getattr(sys,'frozen',False) and '--after-update' not in sys.argv:
        from startup_update import StartupUpdater
        startup=StartupUpdater(root,open_tracker)
    else:open_tracker()
    root.mainloop()
