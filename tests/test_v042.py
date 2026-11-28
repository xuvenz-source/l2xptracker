import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from updater import prune_backups,switch_install
from preferences import load_backup_retention,save_backup_retention
from version import VERSION,APP_NAME
from test_updater import install,NEXT_VERSION

class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name).resolve();self.root=self.p/'Tracker'
        install(self.root,VERSION)
    def backup(self,v,token='1234abcd'):
        p=self.p/f'Tracker.backup-{v}-{token}';install(p,v);return p
    def test_retention_and_unrelated_files(self):
        old=self.backup('0.29');mid=self.backup('0.30');new=self.backup('0.31')
        modified=self.backup('0.28');(modified/'personal.txt').write_text('keep')
        unrelated=self.p/'Other.backup-0.1-1234abcd';install(unrelated,'0.1')
        bad=self.p/'Tracker.backup-not-a-version';bad.mkdir()
        future=self.backup('9.0')
        data=self.p/'sessions.sqlite3';data.write_text('keep')
        removed,warnings=prune_backups(self.root,2)
        self.assertEqual(removed,[old]);self.assertFalse(warnings)
        for p in (mid,new,modified,unrelated,bad,future,data,self.root):self.assertTrue(p.exists())
        self.assertEqual(prune_backups(self.root,1)[0],[mid])
        self.assertTrue(new.exists())
        self.assertEqual(prune_backups(self.root,0),([],[]))
    def test_protect_rollback_and_failure(self):
        a=self.backup('0.29');b=self.backup('0.30')
        self.assertEqual(prune_backups(self.root,1,protect=a)[0],[b])
        self.assertTrue(a.exists())
        stage=self.p/'.l2tracker-update-test';install(stage/APP_NAME,NEXT_VERSION)
        with self.assertRaises(RuntimeError):
            switch_install(self.root,stage,NEXT_VERSION,launch=lambda r:(_ for _ in ()).throw(RuntimeError('failed')))
        self.assertTrue(a.exists());self.assertTrue(self.root.exists())
    def test_symlink_skipped(self):
        a=self.backup('0.29');b=self.backup('0.30');c=self.backup('0.31')
        outside=self.p/'outside';outside.mkdir();(outside/'keep').write_text('safe')
        try:(a/'_internal'/'linked').symlink_to(outside,target_is_directory=True)
        except OSError:self.skipTest('Symlink creation not permitted')
        self.assertEqual(prune_backups(self.root,1)[0],[b])
        self.assertTrue(a.exists());self.assertTrue((outside/'keep').exists());self.assertTrue(c.exists())
    def test_invalid_active_install_no_cleanup(self):
        a=self.backup('0.29');b=self.backup('0.30')
        (self.root/'personal.txt').write_text('keep')
        removed,warnings=prune_backups(self.root,1)
        self.assertFalse(removed);self.assertTrue(warnings);self.assertTrue(a.exists());self.assertTrue(b.exists())
    def test_locked_backup_nonfatal(self):
        a=self.backup('0.29');b=self.backup('0.30')
        with patch('updater.shutil.rmtree',side_effect=PermissionError('locked')):
            removed,warnings=prune_backups(self.root,1)
        self.assertFalse(removed);self.assertTrue(warnings);self.assertTrue(a.exists());self.assertTrue(b.exists())
    def test_preferences(self):
        p=self.p/'prefs.json';self.assertEqual(load_backup_retention(p),2)
        for n in (1,2,0):save_backup_retention(n,p);self.assertEqual(load_backup_retention(p),n)
        for n in (True,3,-1):
            with self.assertRaises(ValueError):save_backup_retention(n,p)
