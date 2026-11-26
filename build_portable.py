"""Run on the existing Windows tracker PC; produce a tested portable ZIP."""
import argparse, json, os, shutil, struct, subprocess, sys, tempfile, zipfile
from importlib import metadata
from pathlib import Path
from version import VERSION, APP_NAME, HELPER_NAME, MARKER, zip_name
from updater import install_manifest

ROOT = Path(__file__).resolve().parent
NAME = APP_NAME
ZIPNAME = zip_name()


def find_tesseract(override=None):
    possible = [override] if override else [shutil.which('tesseract.exe'), str(Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Tesseract-OCR' / 'tesseract.exe'), str(Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Tesseract-OCR' / 'tesseract.exe')]
    for item in possible:
        if not item: continue
        exe = Path(item).expanduser().resolve()
        if exe.is_dir(): exe = exe / 'tesseract.exe'
        if exe.is_file() and (exe.parent/'tessdata'/'eng.traineddata').is_file(): return exe
    raise RuntimeError('Cannot find Tesseract with English language data. Run Build Portable.bat with your Tesseract installation folder as an argument, or reinstall English OCR data.')


def copy_ocr(exe, dest):
    # Preserve the installed runtime, its adjacent DLLs and language data,
    # including available notices/licenses; exclude uninstallers and shortcuts.
    dest.mkdir()
    for source in exe.parent.iterdir():
        name=source.name.lower()
        if source.is_file() and (name=='tesseract.exe' or name.endswith('.dll') or name.startswith(('license','licence','copying','notice','copyright','readme','authors'))):
            shutil.copy2(source,dest/source.name)
        elif source.is_dir() and name in ('tessdata','licenses','licences','doc','docs','share'):
            shutil.copytree(source,dest/source.name)
    assert (dest/'tesseract.exe').is_file()
    assert (dest/'tessdata'/'eng.traineddata').is_file()


def copy_python_notices(dest):
    dest.mkdir()
    # Preserve installed license and notice files for bundled dependencies.
    for dist in metadata.distributions():
        name = dist.metadata.get('Name') or 'unknown'
        for entry in dist.files or []:
            if not any(part.lower().startswith(('license','licence','copying','notice','copyright')) for part in entry.parts): continue
            source = Path(dist.locate_file(entry))
            if not source.is_file(): continue
            rel = Path(*entry.parts)
            if rel.is_absolute() or '..' in rel.parts: continue
            target = dest / name / rel
            target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target)
    for name in ('LICENSE.txt','LICENSE','README.txt'):
        source = Path(sys.base_prefix)/name
        if source.is_file(): shutil.copy2(source, dest/('Python-'+name))


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--tesseract'); args=parser.parse_args()
    if os.name!='nt' or struct.calcsize('P')!=8 or os.environ.get('PROCESSOR_ARCHITECTURE','').upper() not in ('AMD64','X86_64'):
        raise RuntimeError('Run this builder on 64-bit x86 Windows using 64-bit Python.')
    ocr=find_tesseract(args.tesseract)
    print('Using OCR:',ocr,flush=True)
    with tempfile.TemporaryDirectory(prefix='L2PortableBuild-') as tmp:
        work=Path(tmp)
        cmd=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed','--noupx','--name',NAME,'--distpath',str(work/'dist'),'--workpath',str(work/'build'),'--specpath',str(work),'--paths',str(ROOT),'--hidden-import','mss.windows','--copy-metadata','pytesseract','--icon',str(ROOT/'tracker.ico'),str(ROOT/'tracker.py')]
        subprocess.run(cmd,cwd=ROOT,check=True)
        app=work/'dist'/NAME
        helper_cmd=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed','--noupx','--name',Path(HELPER_NAME).stem,'--distpath',str(work/'helper-dist'),'--workpath',str(work/'helper-build'),'--specpath',str(work),'--paths',str(ROOT),str(ROOT/'updater.py')]
        subprocess.run(helper_cmd,cwd=ROOT,check=True)
        shutil.copy2(work/'helper-dist'/HELPER_NAME,app/HELPER_NAME)
        copy_ocr(ocr,app/'ocr')
        copy_python_notices(app/'Third-party notices')
        shutil.copy2(ROOT/'READ ME - Portable.txt',app/'READ ME.txt')
        shutil.copy2(ROOT/'THIRD PARTY.txt',app/'THIRD PARTY.txt')
        report=work/'smoke.json'
        # Avoid relying on PATH or Python environment settings from this PC.
        env=os.environ.copy(); env['PATH']=str(Path(os.environ['WINDIR'])/'System32')+';'+os.environ['WINDIR']
        for key in ('PYTHONHOME','PYTHONPATH','TESSDATA_PREFIX'): env.pop(key,None)
        exe=app/(NAME+'.exe')
        p=subprocess.run([str(exe),'--self-test',str(report)],cwd=work,env=env,timeout=90)
        if not report.is_file(): raise RuntimeError('Frozen app did not write its self-test report. No ZIP created.')
        result=json.loads(report.read_text(encoding='utf-8'))
        if p.returncode or not result.get('ok'): raise RuntimeError('Frozen app failed self-test: '+str(result))
        helper_report=work/'helper-smoke.txt'
        p=subprocess.run([str(app/HELPER_NAME),'--self-test',str(helper_report)],cwd=work,env=env,timeout=90)
        if p.returncode or not helper_report.is_file() or helper_report.read_text(encoding='utf-8')!='ok':raise RuntimeError('Update helper self-test failed')
        shutil.copy2(report,app/'Build self-test.json')
        (app/MARKER).write_text(json.dumps(install_manifest(app,VERSION),indent=2),encoding='utf-8')
        output=ROOT/'Share with friends'; output.mkdir(exist_ok=True)
        final=output/ZIPNAME; partial=output/(ZIPNAME+'.tmp')
        try:
            with zipfile.ZipFile(partial,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
                for f in sorted(app.rglob('*')):
                    if f.is_file(): z.write(f,Path(NAME)/f.relative_to(app))
            with zipfile.ZipFile(partial) as z:
                if z.testzip() is not None: raise RuntimeError('ZIP integrity check failed')
            os.replace(partial,final)
        finally: partial.unlink(missing_ok=True)
        print('\nBUILD SUCCESS. Share this entire ZIP:\n'+str(final),flush=True)

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('\nBUILD FAILED:',exc,file=sys.stderr); sys.exit(1)
