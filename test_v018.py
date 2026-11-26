import unittest
from party import roster, report, display_rows
from tracker import parse
from history import Archive, snapshot
from test_v016 import data
import tempfile
from pathlib import Path

class PartyTests(unittest.TestCase):
    def test_roster(self):
        self.assertEqual(roster(' Alpha, alpha, You, Beta '),['Alpha','Beta'])
        self.assertEqual(roster(''),[])
        with self.assertRaises(ValueError):roster('two words')
    def test_parse(self):
        self.assertEqual(parse('Alpha has earned 85 Adena.'),('adena','Alpha','Adena',85,0))
        self.assertEqual(parse('Alpha has obtained 85 Adena.'),('adena','Alpha','Adena',85,0))
        self.assertEqual(parse('Alpha has obtained Suede.'),('item','Alpha','Suede',1,0))
        self.assertEqual(parse('You have earned 85 Adena.'),('adena','You','Adena',85,0))
    def test_estimates_do_not_add_observed(self):
        a=data(3600,1000,2000);a['party_members']=['Alpha']
        a['events'].append(('t','adena','alpha','Adena',50,0,'visible'))
        r=report([a]); self.assertEqual(r['estimated_party'],4000)
        self.assertEqual(r['rows'][0]['observed'],50)
        self.assertEqual(r['rows'][0]['estimate'],2000)
        self.assertIn(('Alpha','Adena/hr (estimated)','2,000'),list(display_rows(r)))
    def test_legacy_without_roster(self):
        self.assertIsNone(report([data(3600,100,200)])['estimated_party'])
    def test_different_rosters_and_nested_merge(self):
        with tempfile.TemporaryDirectory() as d:
            arc=Archive(Path(d)/'history.sqlite3')
            a=data(3600,100,200);a['party_members']=['Alpha']
            b=data(7200,100,300);b['party_members']=['Alpha','Beta']
            c=data(3600,100,500)
            for key,value in [('a',a),('b',b),('c',c)]:arc.save(key,key,value)
            m=arc.merge(['a','b'],'first');n=arc.merge([m,'a','c'],'second')
            s=arc.summary(n);p=s['party']
            self.assertEqual(p['estimated_party'],1300)
            self.assertEqual(p['seconds'],10800)
            self.assertEqual(s['totals']['You','Adena'],1000)
            self.assertEqual([(x['name'],x['estimate'],x['seconds']) for x in p['rows']],[('Alpha',500,10800),('Beta',300,7200)])
