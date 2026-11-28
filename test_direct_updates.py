import hashlib,json,shutil,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from test_updater import install,release
from version import APP_NAME,zip_name
from delta import delta_name,build_delta,reconstruct,inventory,MANIFEST
from updater import release_info,stage_update,REPO
from release_bases import select_bases,MAX_BASES

def public(tag,**kw):
    name=zip_name(tag[1:])
    r=dict(tag_name=tag,draft=False,prerelease=False,assets=[dict(name=name,size=100000,state='uploaded'),dict(name=name+'.sha256',size=120,state='uploaded')])
    r.update(kw);return r

class DirectUpdateTests(unittest.TestCase):
    def test_select_recent_stable_bases_numerically(self):
        data=[public(f'v0.{i}') for i in range(40,52)]
        data.extend([public('v0.50.1'),public('v0.50.2',draft=True),public('v0.50.3',prerelease=True),public('v0.99'),public('v0.49.9',assets=[]),public('bad')])
        self.assertEqual(select_bases([data[:6],data[6:]],'0.50.4'),['v0.50.1','v0.50','v0.49','v0.48','v0.47','v0.46','v0.45','v0.44'])
        self.assertEqual(len(select_bases([data],'1.0')),MAX_BASES)
    def test_one_package_uses_final_files_and_omits_reverted_changes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d).resolve();base='0.40';target='0.50.2'
            old,mid,new=p/'old',p/'mid',p/'new'
            for r,v in ((old,base),(mid,'0.45'),(new,target)):install(r,v)
            for r,data in ((old,b'original'),(mid,b'intermediate'),(new,b'final')):
                (r/'_internal'/'changed.dll').write_bytes(data)
                (r/'ocr'/'same.dat').write_bytes(b'constant')
                (r/'ocr'/'reverted.dat').write_bytes(b'temporary' if r==mid else b'original')
            (old/'ocr'/'removed.dat').write_bytes(b'old')
            (mid/'ocr'/'intermediate-only.dat').write_bytes(b'temp')
            (new/'ocr'/'new.dat').write_bytes(b'new')
            patchfile=p/delta_name(base,target)
            build_delta(old,new,base,target,patchfile)
            with zipfile.ZipFile(patchfile) as z:
                self.assertEqual(z.read(APP_NAME+'/_internal/changed.dll'),b'final')
                manifest=json.loads(z.read(APP_NAME+'/'+MANIFEST))
                self.assertNotIn('ocr/reverted.dat',manifest['changed'])
                self.assertNotIn('ocr/same.dat',manifest['changed'])
                self.assertNotIn('ocr/intermediate-only.dat',manifest['files'])
                self.assertNotIn('ocr/removed.dat',manifest['files'])
            rebuilt=reconstruct(patchfile,old,p/'verify',base,target)
            self.assertEqual(inventory(rebuilt),inventory(new))
            r=release(target)
            for a in r['assets']:a['size']=1000000
            for v in (base,'0.45','0.50.1'):
                name=delta_name(v,target)
                for n in (name,name+'.sha256'):r['assets'].append(dict(name=n,size=patchfile.stat().st_size,browser_download_url=f'https://github.com/{REPO}/releases/download/v{target}/{n}'))
            info=release_info(r,current=base)
            self.assertEqual(info['delta']['name'],patchfile.name)
            self.assertNotIn('delta',release_info(r,current='0.39'))
            def fetch(url,dest,digest):
                self.assertEqual(url,info['delta']['url']);shutil.copyfile(patchfile,dest)
            checksum=(hashlib.sha256(patchfile.read_bytes()).hexdigest()+'  '+patchfile.name).encode()
            with patch('updater.VERSION',base),patch('updater.small',return_value=checksum),patch('updater.download',side_effect=fetch) as download,patch('updater.smoke_test') as smoke:
                stage=stage_update(info,old)
            self.assertEqual(download.call_count,1);smoke.assert_called_once()
            self.assertEqual(inventory(stage/APP_NAME),inventory(new))
            self.assertTrue((old/'ocr'/'removed.dat').exists())
