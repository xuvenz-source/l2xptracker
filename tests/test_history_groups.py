import tempfile,unittest
from pathlib import Path
from history import Archive,history_children,history_forest
from test_v016 import data

class GroupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.archive=Archive(Path(self.tmp.name)/'sessions.sqlite3')
        for i,x in enumerate('abcd',1):self.archive.save(x,x.upper(),data(100*i,10*i,20*i))
    def view(self):
        r=self.archive.records();s={i:self.archive.summary(i,r) for i in r}
        return r,list(history_forest(r,s))
    def test_parent_hides_top_level_sources(self):
        g=self.archive.merge(['a','b'],'Farm')
        r,paths=self.view()
        self.assertEqual(set(paths),{(g,),(g,'a'),(g,'b'),('c',),('d',)})
        self.assertEqual(r[g]['data']['children'],['a','b'])
        self.assertEqual(self.archive.summary(g)['seconds'],300)
    def test_nested_groups_and_deduplication(self):
        g=self.archive.merge(['a','b'],'First')
        h=self.archive.merge([g,'a','c'],'Combined')
        r,paths=self.view()
        self.assertEqual(set(paths),{(h,),(h,g),(h,g,'a'),(h,g,'b'),(h,'c'),('d',)})
        self.assertEqual(r[h]['data']['children'],[g,'c'])
        self.assertEqual(self.archive.summary(h)['totals']['You','Adena'],120)
        self.archive.rename('a','Changed')
        self.assertEqual(self.archive.records()['a']['name'],'Changed')
    def test_shared_source_is_not_copied(self):
        g=self.archive.merge(['a','b'],'First')
        h=self.archive.merge(['b','c'],'Second')
        r,paths=self.view()
        self.assertIn((g,'b'),paths);self.assertIn((h,'b'),paths);self.assertNotIn(('b',),paths)
        self.assertEqual(len(r),6)
        self.archive.save('b','B',data(200,40,500))
        self.assertEqual(self.archive.summary(g)['totals']['You','Adena'],520)
        self.assertEqual(self.archive.summary(h)['totals']['You','Adena'],560)
    def test_legacy_report(self):
        import json
        with self.archive.db() as db:db.execute('INSERT INTO sessions VALUES (?,?,?,?)',('legacy','Old','merged',json.dumps({'sources':['a','b']})))
        r,paths=self.view()
        self.assertIn(('legacy','a'),paths);self.assertNotIn(('a',),paths)
        self.assertEqual(self.archive.summary('legacy')['seconds'],300)
    def test_old_reader_still_has_flat_sources(self):
        g=self.archive.merge(['a','b'],'First')
        h=self.archive.merge([g,'c'],'Second')
        self.assertEqual(self.archive.records()[h]['data']['sources'],['a','b','c'])
    def test_invalid_children_cannot_hide_unrelated_records(self):
        import json
        with self.archive.db() as db:db.execute('INSERT INTO sessions VALUES (?,?,?,?)',('legacy','Old','merged',json.dumps({'sources':['a','b'],'children':['c','legacy']})))
        r,paths=self.view()
        self.assertIn(('c',),paths);self.assertIn(('legacy','a'),paths)
