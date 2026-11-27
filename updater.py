"""Release-only updates; no game or session information is transmitted."""
import hashlib, json, os, re, shutil, stat, subprocess, sys, tempfile, uuid, zipfile, time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from version import VERSION, APP_NAME, EXE_NAME, HELPER_NAME, MARKER, zip_name
from preferences import mark_failed_update, load_backup_retention

REPO='xuvenz-source/l2xptracker'
API=f'https://api.github.com/repos/{REPO}/releases/latest'
HOSTS={'api.github.com','github.com','release-assets.githubusercontent.com','objects.githubusercontent.com','github-releases.githubusercontent.com'}
MAX_ZIP=300*1024**2
MAX_UNPACKED=1024**3

def version_key(value):
    if not isinstance(value,str) or not re.fullmatch(r'v?\d{1,5}\.\d{1,5}(?:\.\d{1,5})?',value):
        raise ValueError('Unsupported version')
    parts=tuple(int(x) for x in value.lstrip('v').split('.'))
    return parts+(0,) if len(parts)==2 else parts

def safe_url(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443):
        raise ValueError('Unexpected update host')
    return url

class Redirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        safe_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def open_url(url):
    req=Request(safe_url(url),headers={'User-Agent':f'L2LegacyTracker/{VERSION}'})
    response=build_opener(Redirect()).open(req,timeout=25)
    try:safe_url(response.geturl())
    except Exception:response.close();raise
    return response

def small(url,limit):
    with open_url(url) as response:data=response.read(limit+1)
    if len(data)>limit:raise ValueError('Update metadata too large')
    return data

def release_info(data,current=VERSION):
    if data.get('draft') or data.get('prerelease'):return None
    tag=data.get('tag_name','')
    if not re.fullmatch(r'v\d{1,5}\.\d{1,5}(?:\.\d{1,5})?',tag):raise ValueError('Unexpected release tag')
    if version_key(tag)<=version_key(current):return None
    version=tag[1:];name=zip_name(version)
    def asset(filename):
        matches=[a for a in data.get('assets',[]) if a.get('name')==filename]
        url=f'https://github.com/{REPO}/releases/download/{tag}/{filename}'
        if len(matches)!=1 or matches[0].get('browser_download_url')!=url:
            raise ValueError('Release missing expected portable ZIP or checksum')
        return url
    info=dict(version=version,name=name,url=asset(name),checksum=asset(name+'.sha256'),notes=str(data.get('body') or '')[:1200])
    sizes={a.get('name'):a.get('size') for a in data.get('assets',[])}
    if type(sizes.get(name)) is int and 0<sizes[name]<=MAX_ZIP:info['size']=sizes[name]
    # Older releases and skipped versions still use the verified full package.
    from delta import delta_name
    patch=delta_name(current,version)
    try:
        url=asset(patch);checksum=asset(patch+'.sha256')
        sizes={a.get('name'):a.get('size') for a in data.get('assets',[])}
        if type(sizes.get(patch)) is int and type(sizes.get(name)) is int and 0<sizes[patch]<sizes[name]:
            info['delta']=dict(name=patch,url=url,checksum=checksum,size=sizes[patch])
    except ValueError:pass
    return info

def check_release():
    try:return release_info(json.loads(small(API,2*1024**2)))
    except HTTPError as e:
        if e.code==404:return None
        raise

def expected_hash(data,name):
    m=re.fullmatch(r'([0-9a-fA-F]{64})[ \t]+\*?'+re.escape(name),data.decode('ascii').strip())
    if not m:raise ValueError('Invalid release checksum')
    return m[1].lower()

def download(url,dest,digest,progress=None,expected_size=None):
    total=0;h=hashlib.sha256();last=0
    with open_url(url) as response,dest.open('xb') as out:
        try:length=int(response.headers.get('Content-Length','0'))
        except (ValueError,TypeError,AttributeError):length=0
        size=expected_size if type(expected_size) is int and 0<expected_size<=MAX_ZIP else length if 0<length<=MAX_ZIP else None
        if progress:progress(0,size)
        while chunk:=response.read(256*1024):
            total+=len(chunk)
            if total>MAX_ZIP:raise ValueError('Update archive too large')
            h.update(chunk);out.write(chunk)
            now=time.monotonic()
            if progress and now-last>=.1:progress(total,size);last=now
        if size is not None and total!=size:raise ValueError('Incomplete update download')
    if h.hexdigest()!=digest:raise ValueError('Checksum mismatch; nothing installed')
    if progress:progress(total,size)

def valid_part(p):
    reserved={'CON','PRN','AUX','NUL',*(f'COM{x}' for x in '123456789¹²³'),*(f'LPT{x}' for x in '123456789¹²³')}
    return bool(p and p not in ('.','..') and not re.search(r'[<>:"\\|?*\x00-\x1f]',p)
                and not p.endswith((' ','.')) and p.split('.')[0].upper() not in reserved)

def extract_portable(archive,directory):
    seen=set();total=0
    with zipfile.ZipFile(archive) as z:
        entries=z.infolist()
        if len(entries)>20000:raise ValueError('Too many archive entries')
        for e in entries:
            # ZipInfo normalizes native separators and truncates NUL on some
            # platforms. Validate the original archive name, not the sanitized one.
            raw=e.orig_filename
            if raw!=e.filename:raise ValueError('Unsafe normalized archive path')
            parts=raw.rstrip('/').split('/')
            if parts[0]!=APP_NAME or not all(valid_part(p) for p in parts) or (len(parts)==1 and not e.is_dir()):
                raise ValueError('Unsafe archive path')
            mode=(e.external_attr>>16)&0xffff
            if stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR) or e.external_attr&0x400:
                raise ValueError('Unsupported archive file type')
            key='/'.join(parts).casefold()
            if key in seen:raise ValueError('Duplicate archive path')
            seen.add(key);total+=e.file_size
            if total>MAX_UNPACKED:raise ValueError('Unpacked update too large')
            dest=directory.joinpath(*parts)
            if e.is_dir():dest.mkdir(parents=True,exist_ok=True);continue
            dest.parent.mkdir(parents=True,exist_ok=True)
            with z.open(e) as src,dest.open('xb') as out:shutil.copyfileobj(src,out,256*1024)
    return directory/APP_NAME

def install_manifest(root,version):
    return dict(schema=1,version=version,entries=sorted(p.name for p in root.iterdir() if p.name!=MARKER))

def validate_install(root,version):
    if root.is_symlink() or root.resolve()!=root or not root.is_dir():
        raise ValueError('Use a normal local installation folder')
    if json.loads((root/MARKER).read_text(encoding='utf-8'))!=install_manifest(root,version):
        raise ValueError('Installation folder changed; extract a fresh ZIP to a dedicated folder')
    for name in (EXE_NAME,HELPER_NAME,'_internal','ocr'):
        p=root/name
        if p.is_symlink() or not p.exists():raise ValueError('Incomplete installation')
    if not (root/EXE_NAME).is_file() or not (root/HELPER_NAME).is_file() or not (root/'_internal').is_dir() or not (root/'ocr').is_dir():
        raise ValueError('Incomplete installation')

def clean_env():
    env=os.environ.copy()
    for k in list(env):
        if k.startswith('_PYI_') or k in ('PYTHONHOME','PYTHONPATH','TESSDATA_PREFIX'):env.pop(k,None)
    env['PYINSTALLER_RESET_ENVIRONMENT']='1'
    if os.name=='nt':
        windows=Path(os.environ.get('WINDIR',r'C:\Windows'))
        env['PATH']=str(windows/'System32')+';'+str(windows)
    return env

def smoke_test(root,report):
    proc=subprocess.run([str(root/EXE_NAME),'--self-test',str(report)],cwd=root,env=clean_env(),timeout=100)
    if proc.returncode or not report.is_file() or not json.loads(report.read_text(encoding='utf-8')).get('ok'):
        raise RuntimeError('New application failed its self-test; current version unchanged')

def stage_update(info,root,progress=lambda text:None,byte_progress=None):
    def fetch(asset,archive,digest):
        if byte_progress is None:download(asset['url'],archive,digest)
        else:download(asset['url'],archive,digest,progress=byte_progress,expected_size=asset.get('size'))
    progress('Checking installation and preparing update…')
    validate_install(root,VERSION)
    if version_key(info['version'])<=version_key(VERSION):raise ValueError('Update is not newer')
    staging=Path(tempfile.mkdtemp(prefix='.l2tracker-update-',dir=root.parent)).resolve()
    try:
        patch=info.get('delta')
        if patch:
            try:
                from delta import reconstruct
                progress(f"Downloading incremental patch ({patch['size']/1024**2:.1f} MiB)…")
                digest=expected_hash(small(patch['checksum'],4096),patch['name'])
                archive=staging/patch['name'];fetch(patch,archive,digest)
                progress('Verifying and reconstructing incremental update…')
                new=reconstruct(archive,root,staging,VERSION,info['version'])
                progress('Testing the updated application…')
                smoke_test(new,staging/'smoke.json');archive.unlink();return staging
            except Exception as exc:
                progress(f'Incremental patch unavailable: {exc}. Using full package.')
                shutil.rmtree(staging)
                staging.mkdir()
        progress('Downloading full update package…')
        digest=expected_hash(small(info['checksum'],4096),info['name'])
        archive=staging/info['name'];fetch(info,archive,digest)
        progress('Extracting and verifying update files…')
        new=extract_portable(archive,staging)
        validate_install(new,info['version']);progress('Testing the updated application…');smoke_test(new,staging/'smoke.json')
        archive.unlink();return staging
    except Exception:
        shutil.rmtree(staging,ignore_errors=True);raise

def launch_helper(root,staging,version):
    work=Path(tempfile.mkdtemp(prefix='L2TrackerUpdater-')).resolve()
    helper=work/HELPER_NAME;shutil.copy2(root/HELPER_NAME,helper)
    return subprocess.Popen([str(helper),'--apply',str(os.getpid()),str(root),str(staging),version],
                            cwd=work,env=clean_env(),close_fds=True)

def wait_for_exit(pid,timeout=60):
    import ctypes
    from ctypes import wintypes
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
    k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];k.WaitForSingleObject.restype=wintypes.DWORD
    k.CloseHandle.argtypes=[wintypes.HANDLE];k.CloseHandle.restype=wintypes.BOOL
    h=k.OpenProcess(0x00100000,False,pid)
    if not h:
        if ctypes.get_last_error()==87:return
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if k.WaitForSingleObject(h,int(timeout*1000))!=0:raise RuntimeError('Tracker did not exit; update cancelled')
    finally:k.CloseHandle(h)

def launch_app(root):
    proc=subprocess.Popen([str(root/EXE_NAME),'--after-update'],cwd=root,env=clean_env(),close_fds=True)
    try:code=proc.wait(timeout=4)
    except subprocess.TimeoutExpired:return
    raise RuntimeError(f'Updated application exited during startup ({code})')

def switch_install(root,staging,new_version,launch=launch_app):
    if staging.parent!=root.parent or not staging.name.startswith('.l2tracker-update-'):
        raise ValueError('Invalid staging location')
    new=staging/APP_NAME
    validate_install(root,VERSION);validate_install(new,new_version)
    if version_key(new_version)<=version_key(VERSION):raise ValueError('Cannot downgrade')
    backup=root.with_name(root.name+'.backup-'+VERSION+'-'+uuid.uuid4().hex[:8])
    os.replace(root,backup);moved=False
    try:
        os.replace(new,root);moved=True;launch(root)
    except Exception as exc:
        try:
            if moved:os.replace(root,root.with_name(root.name+'.failed-'+uuid.uuid4().hex[:8]))
            os.replace(backup,root)
        except Exception as rollback:
            raise RuntimeError(f'Update failed. Restore backup manually: {backup}. Rollback error: {rollback}') from rollback
        raise RuntimeError(f'Update failed; previous installation restored: {exc}') from exc
    return backup

def ordinary_tree(path):
    """Do not follow symlinks, junctions or other reparse points."""
    def ordinary(p):
        st=p.lstat()
        return not (stat.S_ISLNK(st.st_mode) or getattr(st,'st_file_attributes',0)&0x400) and (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode))
    if not ordinary(path):return False
    for folder,dirs,files in os.walk(path,followlinks=False,onerror=lambda e:(_ for _ in ()).throw(e)):
        for name in dirs+files:
            if not ordinary(Path(folder)/name):return False
    return True

def prune_backups(root,keep=None,active_version=VERSION,protect=None):
    """Only prune recognised sibling installations, after checking the active one.
    Cleanup is best-effort and never changes an update's success/rollback result.
    """
    keep=load_backup_retention() if keep is None else keep
    if type(keep) is not int or keep not in (0,1,2):raise ValueError('Invalid backup retention')
    removed=[];warnings=[]
    if not keep:return removed,warnings
    root=Path(root)
    # Do not manage other installations when launched from a recovery copy.
    if re.search(r'\.(?:backup|failed)-',root.name):return removed,warnings
    pattern=re.compile(re.escape(root.name)+r'\.backup-(\d{1,5}\.\d{1,5}(?:\.\d{1,5})?)-[0-9a-f]{8}')
    try:
        validate_install(root,active_version)
        candidates=[]
        for path in root.parent.iterdir():
            match=pattern.fullmatch(path.name)
            if not match:continue
            try:
                version=match[1]
                if version_key(version)>=version_key(active_version):continue
                if not ordinary_tree(path):continue
                validate_install(path,version)
                candidates.append((version_key(version),path.stat().st_mtime_ns,path.name,path,version))
            except (OSError,ValueError,TypeError):continue
        candidates.sort(reverse=True)
        retained=set()
        if protect is not None:retained.add(Path(protect))
        for _,_,_,path,_ in candidates:
            if len(retained)>=keep:break
            retained.add(path)
        for _,_,_,path,version in candidates:
            if path in retained:continue
            try:
                if not ordinary_tree(path):continue
                validate_install(path,version)
                shutil.rmtree(path);removed.append(path)
            except (OSError,ValueError,TypeError) as e:warnings.append(f'{path.name}: {e}')
    except (OSError,ValueError,TypeError) as e:warnings.append(str(e))
    return removed,warnings

def helper_main():
    if len(sys.argv)==3 and sys.argv[1]=='--self-test':
        Path(sys.argv[2]).write_text('ok',encoding='utf-8');return 0
    if len(sys.argv)!=6 or sys.argv[1]!='--apply' or os.name!='nt':return 1
    _,_,pid,old,staged,version=sys.argv
    # A separate visible window survives the old application's exit.
    import tkinter as tk
    from updater_view import UpdateView
    import queue, threading
    root=tk.Tk();root.title('L2 Legacy Tracker — installing update')
    root.resizable(False,False)
    view=UpdateView(root,version)
    view.pack(fill='both',expand=True)
    view.stage('Waiting for the old tracker to close…')
    root.protocol('WM_DELETE_WINDOW',lambda:None)
    q=queue.Queue();result=[1]
    def work():
        try:
            wait_for_exit(int(pid))
            q.put(('stage','Installing verified files and retaining a backup…'))
            backup=switch_install(Path(old),Path(staged),version)
            shutil.rmtree(staged,ignore_errors=True)
            q.put(('stage','Removing older installation backups…'))
            # Never enter the rollback/error branch because of optional cleanup.
            try:removed,warnings=prune_backups(Path(old),active_version=version,protect=backup)
            except Exception as e:removed,warnings=[],[str(e)]
            q.put(('done',(len(removed),len(warnings))))
        except Exception as exc:
            try:mark_failed_update(version)
            except OSError:pass
            q.put(('error',str(exc)))
    def poll():
        try:
            while True:
                kind,value=q.get_nowait()
                if kind=='stage':view.stage(value)
                elif kind=='done':
                    count,warnings=value;result[0]=0
                    view.complete('Update installed. Tracker launched.'+(f' Removed {count} old backup(s).' if count else '')+(' Some backups could not be cleaned.' if warnings else ''))
                    root.after(450,root.destroy);return
                else:
                    view.error(value+'\nSettings and session history were not modified.')
                    view.actions([('Close',root.destroy)])
                    root.protocol('WM_DELETE_WINDOW',root.destroy);return
        except queue.Empty:root.after(75,poll)
    threading.Thread(target=work,daemon=True).start()
    root.after(75,poll);root.mainloop();return result[0]

if __name__=='__main__':sys.exit(helper_main())
