"""File-level delta archives. All target bytes are verified before use."""
import hashlib,json,shutil,stat,tempfile,zipfile
from pathlib import Path
from version import APP_NAME
from updater import valid_part,extract_portable,validate_install,MAX_UNPACKED

MANIFEST='L2Tracker.delta.json'
def delta_name(base,target):return f'L2_Legacy_Tracker_v{base}_to_v{target}_Windows_x64_Delta.zip'

def digest(path):
    with path.open('rb') as src:return hashlib.file_digest(src,'sha256').hexdigest()

def safe_path(root,name):
    if not isinstance(name,str) or not all(valid_part(p) for p in name.split('/')):
        raise ValueError('Unsafe delta path')
    path=root.joinpath(*name.split('/'))
    # Reject symbolic links, junctions and paths escaping the staging/install root.
    for p in (path,*path.parents):
        if p==root:break
        if p.is_symlink() or getattr(p,'is_junction',lambda:False)():raise ValueError('Unsafe delta link')
    if not path.resolve().is_relative_to(root.resolve()):raise ValueError('Unsafe delta path')
    return path

def inventory(root):
    result={}
    for path in root.rglob('*'):
        name=path.relative_to(root).as_posix()
        safe_path(root,name)
        if path.is_dir():continue
        if not path.is_file() or name==MANIFEST:raise ValueError('Invalid installation file')
        result[name]={'size':path.stat().st_size,'sha256':digest(path)}
    return result

def build_delta(old,new,base,target,out):
    validate_install(old,base);validate_install(new,target)
    a,b=inventory(old),inventory(new)
    changed=[name for name,info in b.items() if a.get(name)!=info]
    manifest=dict(schema=1,base=base,target=target,files=b,changed=changed)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr(f'{APP_NAME}/{MANIFEST}',json.dumps(manifest,separators=(',',':')))
        for name in changed:z.write(safe_path(new,name),f'{APP_NAME}/{name}')
    return len(changed),len(b)

def reconstruct(archive,old,staging,base,target):
    validate_install(old,base)
    new=extract_portable(archive,staging)
    manifest=new/MANIFEST
    if not manifest.is_file() or manifest.stat().st_size>8*1024**2:raise ValueError('Invalid delta manifest')
    data=json.loads(manifest.read_text(encoding='utf-8'));manifest.unlink()
    if data.get('schema')!=1 or data.get('base')!=base or data.get('target')!=target:raise ValueError('Wrong delta version')
    files=data['files'];changed=data['changed']
    if not isinstance(files,dict) or not isinstance(changed,list) or len(files)>20000 or len(set(changed))!=len(changed) or not set(changed)<=set(files):raise ValueError('Invalid delta manifest')
    if len({n.casefold() for n in files})!=len(files) or MANIFEST in files:raise ValueError('Duplicate delta path')
    if set(inventory(new))!=set(changed):raise ValueError('Unexpected delta contents')
    total=0
    for name,info in files.items():
        dst=safe_path(new,name)
        if type(info.get('size')) is not int or info['size']<0 or not isinstance(info.get('sha256'),str) or len(info['sha256'])!=64:raise ValueError('Invalid delta file metadata')
        total+=info['size']
        if total>MAX_UNPACKED:raise ValueError('Delta exceeds size limit')
        if name not in changed:
            src=safe_path(old,name)
            if not src.is_file() or src.stat().st_size!=info['size'] or digest(src)!=info['sha256']:raise ValueError('Local file differs; full update required')
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
        if not dst.is_file() or dst.stat().st_size!=info['size'] or digest(dst)!=info['sha256']:raise ValueError('Delta file verification failed')
    validate_install(new,target)
    return new

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('old',type=Path);p.add_argument('new',type=Path);p.add_argument('base');p.add_argument('target');p.add_argument('out',type=Path);a=p.parse_args()
    with tempfile.TemporaryDirectory() as d:
        work=Path(d).resolve()
        old=extract_portable(a.old,work/'old');new=extract_portable(a.new,work/'new')
        changed,total=build_delta(old,new,a.base,a.target,a.out)
        rebuilt=reconstruct(a.out,old,work/'check',a.base,a.target)
        if inventory(rebuilt)!=inventory(new):raise RuntimeError('Delta reconstruction mismatch')
        if a.out.stat().st_size>=a.new.stat().st_size:
            a.out.unlink();print('Full package is smaller; no delta emitted.')
        else:print(f'Delta verified: {changed}/{total} files changed; {a.out.stat().st_size:,} bytes vs {a.new.stat().st_size:,} full.')
if __name__=='__main__':main()
