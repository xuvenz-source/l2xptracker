import json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from test_updater import install,release,NEXT_VERSION
from version import VERSION,APP_NAME,MARKER,zip_name
from updater import install_manifest,release_info,REPO,stage_update
from delta import delta_name,build_delta,reconstruct,inventory

class DeltaTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name).resolve();self.old=self.p/'old';self.new=self.p/'new'
        install(self.old,VERSION);install(self.new,NEXT_VERSION)
        for r in (self.old,self.new):
            (r/'ocr'/'same.dat').write_bytes(b'same'*10000)
            (r/'_internal'/'runtime.dll').write_bytes(b'runtime')
        (self.old/'ocr'/'obsolete.dat').write_bytes(b'old')
        (self.new/'ocr'/'added.dat').write_bytes(b'new')
        self.patch=self.p/'delta.zip'
        build_delta(self.old,self.new,VERSION,NEXT_VERSION,self.patch)
    def test_reconstruction(self):
        new=reconstruct(self.patch,self.old,self.p/'stage',VERSION,NEXT_VERSION)
        self.assertEqual(inventory(new),inventory(self.new))
        self.assertFalse((new/'ocr'/'obsolete.dat').exists())
        self.assertTrue((self.old/'ocr'/'obsolete.dat').exists())
        with zipfile.ZipFile(self.patch) as z:self.assertNotIn(APP_NAME+'/ocr/same.dat',z.namelist())
    def test_tampered_local(self):
        (self.old/'ocr'/'same.dat').write_bytes(b'wrong')
        with self.assertRaises(ValueError):reconstruct(self.patch,self.old,self.p/'stage',VERSION,NEXT_VERSION)
    def test_wrong_base(self):
        with self.assertRaises(ValueError):reconstruct(self.patch,self.old,self.p/'stage',VERSION,'9.99')
    def test_release_patch_choice(self):
        r=release();name=delta_name(VERSION,NEXT_VERSION)
        for a in r['assets']:a['size']=1000000
        for n in (name,name+'.sha256'):r['assets'].append(dict(name=n,size=100,browser_download_url=f'https://github.com/{REPO}/releases/download/v{NEXT_VERSION}/{n}'))
        self.assertEqual(release_info(r)['delta']['name'],name)
        self.assertNotIn('delta',release_info(r,current='0.1'))
    def test_fallback(self):
        full=self.p/'full.zip'
        with zipfile.ZipFile(full,'w') as z:
            for p in self.new.rglob('*'):
                if p.is_file():z.write(p,APP_NAME+'/'+p.relative_to(self.new).as_posix())
        import hashlib,shutil
        name=zip_name(NEXT_VERSION);patchname=delta_name(VERSION,NEXT_VERSION)
        info=dict(version=NEXT_VERSION,name=name,url='full',checksum='fullhash',delta=dict(name=patchname,url='patch',checksum='patchhash',size=100))
        def small(url,limit):
            return (hashlib.sha256(full.read_bytes()).hexdigest()+'  '+name).encode() if url=='fullhash' else b'bad'
        def download(url,dest,digest):shutil.copyfile(full,dest)
        with patch('updater.small',side_effect=small),patch('updater.download',side_effect=download),patch('updater.smoke_test'):
            stage=stage_update(info,self.old)
        self.assertEqual(inventory(stage/APP_NAME),inventory(self.new))

    def test_successful_patch_never_downloads_full(self):
        import hashlib,shutil
        name=delta_name(VERSION,NEXT_VERSION)
        info=dict(version=NEXT_VERSION,name=zip_name(NEXT_VERSION),url='full',checksum='fullhash',delta=dict(name=name,url='patch',checksum='patchhash',size=100))
        def small(url,limit):
            self.assertEqual(url,'patchhash')
            return (hashlib.sha256(self.patch.read_bytes()).hexdigest()+'  '+name).encode()
        def download(url,dest,digest):
            self.assertEqual(url,'patch');shutil.copyfile(self.patch,dest)
        with patch('updater.small',side_effect=small),patch('updater.download',side_effect=download),patch('updater.smoke_test'):
            stage=stage_update(info,self.old)
        self.assertEqual(inventory(stage/APP_NAME),inventory(self.new))
