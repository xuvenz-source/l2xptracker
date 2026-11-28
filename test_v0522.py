import unittest,tempfile
from pathlib import Path
from test_v050 import mob,event,library
from monster_library import context,classify,sync,assign,counts,save,load
from preferences import write_preference

class DefaultMonsterTests(unittest.TestCase):
    def test_default_works_without_signature_or_level_in_party(self):
        p=mob('Pincher');lib=library(p);lib['default']=p['id']
        for level,solo in [(None,False),(19,False),(19,True)]:
            for e in [event(247,9),event(247,None),event(None,9)]:
                r=classify(e,context(lib,level,solo))
                self.assertEqual((r['id'],r['method']),(p['id'],'default'))
        lib['full_solo']=False
        self.assertEqual(classify(event(),context(lib,None,False))['id'],p['id'])
    def test_exact_match_priority_and_no_default(self):
        p=mob('Pincher');q=mob('Other',19,500,20);lib=library(p,q);lib['default']=p['id']
        self.assertEqual(classify(event(500,20),context(lib,19,True))['id'],q['id'])
        lib['default']=None
        self.assertIsNone(classify(event(247,9),context(lib,19,False))['id'])
    def test_capture_time_and_manual_override(self):
        p=mob('Pincher');q=mob('Other');lib=library(p,q);lib['default']=p['id']
        a=context(lib,None,False);lib['default']=q['id'];b=context(lib,None,False)
        events=[event(ts='b'),event(ts='d'),event(ts='d'),('d','xp','Other','XP / SP',353,14,'reward')]
        records={};timeline=[dict(at='a',context=a),dict(at='c',context=b)]
        sync(events,records,timeline)
        self.assertEqual(counts(events,records)[0],{p['id']:1,q['id']:2})
        assign(records,events,[0],q);assign(records,events,[1],None)
        events[0]=event(400,14,ts='b');events[1]=event(400,14,ts='d');sync(events,records,timeline)
        self.assertEqual(records['0']['id'],q['id']);self.assertIsNone(records['1']['id'])
        self.assertEqual(records['1']['method'],'manual_unknown');self.assertNotIn('3',records)
    def test_migration_and_explicit_disable_persist(self):
        p=mob('Pincher');lib=library(p);lib['full_solo']=False;lib.pop('default')
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'prefs.json';write_preference('monster_library',lib,path)
            migrated=load(path);self.assertEqual(migrated['default'],p['id'])
            migrated['default']=None;save(migrated,path);self.assertIsNone(load(path)['default'])
            migrated['default']=p['id'];save(migrated,path);self.assertEqual(load(path)['default'],p['id'])
    def test_old_context_remains_unknown(self):
        self.assertIsNone(classify(event(),dict(level=None,normal=False,candidates=[]))['id'])
