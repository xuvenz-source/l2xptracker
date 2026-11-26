import hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
from updater import release_info,expected_hash,extract_portable,install_manifest,validate_install,switch_install,safe_url,version_key,REPO
from version import VERSION,APP_NAME,EXE_NAME,HELPER_NAME,MARKER,zip_name

def release(version='0.21'):
    name=zip_name(version);tag='v'+version
    return dict(tag_name=tag,assets=[dict(name=x,browser_download_url=f'https://github.com/{REPO}/releases/download/{tag}/{x}') for x in (name,name+'.sha256')])

def install(root,version):
    root.mkdir(parents=True)
    for name in (EXE_NAME,HELPER_NAME):(root/name).write_text(version)
    for name in ('_internal','ocr'):(root/name).mkdir()
    (root/MARKER).write_text(json.dumps(install_manifest(root,version)))

class UpdateTests(unittest.TestCase):
    def test_release(self):
        self.assertEqual(release_info(release())['version'],'0.21')
        self.assertIsNone(release_info(release(VERSION)))
        self.assertIsNone(release_info(dict(release(),draft=True)))
        self.assertIsNone(release_info(dict(release(),prerelease=True)))
        self.assertGreater(version_key('0.100'),version_key('0.21'))
        with self.assertRaises(ValueError):release_info(dict(release(),assets=[]))
        with self.assertRaises(ValueError):safe_url('https://github.com.evil.example/file')
    def test_hash(self):
        name=zip_name('0.21');digest=hashlib.sha256(b'x').hexdigest()
        self.assertEqual(expected_hash((digest+'  '+name+'\n').encode(),name),digest)
        with self.assertRaises(ValueError):expected_hash((digest+'  wrong.zip').encode(),name)
    def test_zip_paths(self):
        for name in ('../evil',APP_NAME+'/../evil',APP_NAME+'/file:stream',APP_NAME+'/CON',APP_NAME+'/bad\\path'):
            with tempfile.TemporaryDirectory() as d:
                p=Path(d);z=p/'x.zip'
                with zipfile.ZipFile(z,'w') as out:out.writestr(name,'bad')
                with self.assertRaises(ValueError):extract_portable(z,p/'stage')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);z=p/'x.zip'
            with zipfile.ZipFile(z,'w') as out:out.writestr(APP_NAME+'/file.txt','ok')
            self.assertEqual((extract_portable(z,p/'stage')/'file.txt').read_text(),'ok')
    def test_switch_and_backup(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d).resolve();root=p/'current';stage=p/'.l2tracker-update-test'
            install(root,VERSION);install(stage/APP_NAME,'0.21')
            backup=switch_install(root,stage,'0.21',launch=lambda r:None)
            validate_install(root,'0.21');validate_install(backup,VERSION)
    def test_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d).resolve();root=p/'current';stage=p/'.l2tracker-update-test'
            install(root,VERSION);install(stage/APP_NAME,'0.21')
            def fail(r):raise RuntimeError('startup failure')
            with self.assertRaisesRegex(RuntimeError,'restored'):switch_install(root,stage,'0.21',launch=fail)
            validate_install(root,VERSION)
    def test_unrelated_files_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d).resolve()/'current';install(p,VERSION)
            (p/'personal.txt').write_text('preserve me')
            with self.assertRaises(ValueError):validate_install(p,VERSION)
