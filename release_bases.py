"""Select bounded public base releases for direct-to-latest deltas."""
import json,sys
from updater import version_key,MAX_ZIP
from version import zip_name
MAX_BASES=8

def select_bases(pages,target,limit=MAX_BASES):
    newest=version_key(target);found={}
    for page in pages:
        for release in page:
            if release.get('draft') or release.get('prerelease'):continue
            tag=release.get('tag_name','')
            if not isinstance(tag,str) or not tag.startswith('v'):continue
            try:key=version_key(tag)
            except ValueError:continue
            if key>=newest:continue
            name=zip_name(tag[1:]);assets=release.get('assets',[])
            full=[a for a in assets if a.get('name')==name and a.get('state')=='uploaded' and type(a.get('size')) is int and 0<a['size']<=MAX_ZIP]
            sums=[a for a in assets if a.get('name')==name+'.sha256' and a.get('state')=='uploaded' and type(a.get('size')) is int and 0<a['size']<4096]
            if len(full)==1 and len(sums)==1:found[tag]=key
    return sorted(found,key=lambda tag:(found[tag],tag),reverse=True)[:limit]

if __name__=='__main__':
    for tag in select_bases(json.load(sys.stdin),sys.argv[1]):print(tag)
