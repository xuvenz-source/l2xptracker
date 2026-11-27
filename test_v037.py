import tempfile,unittest
from pathlib import Path
from history import Archive,history_forest,folder_options,folder_move_plan
from test_v016 import data

class FolderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.a=Archive(Path(self.tmp.name)/'sessions.sqlite3')
        for i,k in enumerate('abc',1):self.a.save(k,k,data(100*i,10*i,20*i))
    def paths(self):
        r=self.a.organised_records();s={i:self.a.summary(i,r) for i,x in r.items() if x['kind']!='folder'}
        return set(history_forest(r,s))
    def test_nested_and_reopen(self):
        section=self.a.create_folder('Warcryer');f=self.a.create_folder('Cruma',section)
        self.a.move_entries(['a','b'],f)
        self.assertIn((section,f,'a'),self.paths())
        self.assertEqual(self.a.summary('a')['seconds'],100)
        self.assertIn((f,'Warcryer / Cruma'),folder_options(self.a.organised_records()))
        self.a=Archive(self.a.path);self.assertIn((section,f,'b'),self.paths())
        self.a.move_entries(['a'],'');self.assertIn(('a',),self.paths())
    def test_default_and_checkpoint(self):
        f=self.a.create_folder('Character');self.a.set_default_folder(f)
        self.a.save('d','new',data(10,10,10))
        self.a.move_entries(['d'],'');self.a.save('d','checkpoint',data(20,20,20))
        self.assertEqual(self.a.organised_records()['d']['folder'],'')
        self.a.save('e','new',data(20,20,20));self.assertEqual(self.a.organised_records()['e']['folder'],f)
    def test_cycles_and_nested_multi_move(self):
        f=self.a.create_folder('A');g=self.a.create_folder('B',f);h=self.a.create_folder('C')
        with self.assertRaises(ValueError):self.a.move_entries([f],g)
        self.a.move_entries(['a'],g);self.a.move_entries([f,g,'a'],h)
        self.assertIn((h,f,g,'a'),self.paths())
    def test_folder_delete_preserves_contents(self):
        f=self.a.create_folder('A');g=self.a.create_folder('B',f);h=self.a.create_folder('C',g)
        self.a.move_entries(['a'],g);self.a.set_default_folder(g)
        self.a.delete_entries([g]);self.assertEqual(self.a.default_folder(),f)
        self.assertIn((f,'a'),self.paths());self.assertIn((f,h),self.paths())
        self.assertIn('a',self.a.records())
    def test_delete_original_updates_all_reports(self):
        g=self.a.merge(['a','b'],'One');h=self.a.merge([g,'c'],'Two')
        self.a.delete_entries(['a'])
        self.assertEqual(self.a.summary(g)['sources'],['b'])
        self.assertEqual(set(self.a.summary(h)['sources']),{'b','c'})
        self.a.delete_entries([g]);self.assertIn('b',self.a.records())
        self.assertEqual(self.a.summary(h)['seconds'],500)
        self.a.delete_entries(['b','c']);self.assertNotIn(h,self.a.records())
    def test_explicit_folders_and_reports_are_independent(self):
        f=self.a.create_folder('One');g=self.a.create_folder('Two')
        self.a.move_entries(['a'],f);self.a.move_entries(['b'],g)
        report=self.a.merge(['a','b'],'Combined')
        self.assertIn((f,'a'),self.paths());self.assertIn((g,'b'),self.paths())
        self.assertIn((report,'a'),self.paths())
        with self.assertRaises(ValueError):self.a.delete_entries(['a'],['a'])
        self.assertIn('a',self.a.records())
        self.a.delete_entries([report]);self.assertIn((f,'a'),self.paths())
    def test_same_folder_merge(self):
        f=self.a.create_folder('A');self.a.move_entries(['a','b'],f)
        g=self.a.merge(['a','b'],'Combined')
        self.assertIn((f,g),self.paths());self.assertEqual(self.a.summary(g)['seconds'],300)
    def test_folder_not_mergeable(self):
        f=self.a.create_folder('A')
        with self.assertRaises(ValueError):Archive.sources([f],self.a.organised_records())
