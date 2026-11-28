import unittest,tempfile
from pathlib import Path
from monster_library import *
from preferences import write_preference
from history import totals_for,count_kills
from decimal import Decimal

def mob(name,level=16,xp=471,sp=19):
    return profile(dict(monster=name,rows=[dict(name='Ring',group='2',chance='5')],selected=[0],rate=''),level,xp,sp)
def event(xp=353,sp=14,ts='b'):
    return (ts,'xp','You','XP / SP',xp,sp,'reward')
def library(*ps):
    l=empty();l['profiles']={p['id']:p for p in ps};l['active']=list(l['profiles']);l['full_solo']=True;return l

class MonsterTests(unittest.TestCase):
    def test_pincher_and_collision(self):
        p=mob('Pincher');q=mob('Dark Horror')
        self.assertEqual(expected(p,19),(353,14))
        self.assertEqual(classify(event(),context(library(p),19,True))['id'],p['id'])
        self.assertEqual(classify(event(),context(library(p,q),19,True))['method'],'ambiguous')
        self.assertIsNone(classify(event(247,9),context(library(p),19,True))['id'])
        self.assertIsNone(classify(event(),context(library(p),19,False))['id'])
        self.assertIsNone(classify(event(),context(library(p),None,True))['id'])
    def test_capture_context_and_manual_review(self):
        p=mob('Pincher');q=mob('Other',17,588,26);l=library(p,q)
        events=[event(ts='b'),event(247,9,ts='d'),event(ts='b')]
        timeline=[dict(at='a',context=context(l,19,True)),dict(at='c',context=context(l,20,True))]
        r={};sync(events,r,timeline);self.assertEqual(counts(events,r)[0][p['id']],2)
        old=totals_for(events);assign(r,events,[1],q)
        self.assertEqual(totals_for(events),old);self.assertEqual(count_kills(events),3)
        self.assertEqual(counts(events,r)[0][q['id']],1);sync(events,r,timeline)
        self.assertEqual(history_counts([dict(events=events,monster_kills=r)])['unknown'],0)
    def test_partial_and_late_review(self):
        p=mob('Pincher');timeline=[dict(at='',context=context(library(p),19,True))]
        events=[event(353,None)];r={};sync(events,r,timeline);self.assertIsNone(r['0']['id'])
        events[0]=event();sync(events,r,timeline);self.assertEqual(r['0']['id'],p['id'])
    def test_learning_scoped_and_collision(self):
        p=mob('Pincher');q=mob('Other');l=library(p,q)
        events=[event(350,14)];r={};sync(events,r,[dict(at='',context=context(l,19,True))])
        assign(r,events,[0],p);learn(l,r,[0],p)
        self.assertEqual(classify(events[0],context(l,19,True))['id'],p['id'])
        self.assertIsNone(classify(events[0],context(l,20,True))['id'])
        learn(l,r,[0],q);self.assertEqual(classify(events[0],context(l,19,True))['method'],'ambiguous')
    def test_migration_and_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'prefs.json';write_preference('drop_targets',dict(monster='Pincher Lv.16',rows=[],selected=[],rate=''),path)
            l=load(path);self.assertEqual(len(l['profiles']),1);self.assertIsNone(next(iter(l['profiles'].values()))['xp'])
            p=mob('Pincher');l=library(p);save(l,path);self.assertEqual(load(path),l)
    def test_rates_use_identified_kills(self):
        p=mob('Pincher');q=mob('Other');l=library(p,q)
        rows=forecasts(l,Counter({p['id']:100,q['id']:50}),3600)
        self.assertEqual(rows,[('Pincher Lv.16 · Ring','10h 00m'),('Other Lv.16 · Ring','20h 00m')])
    def test_header(self):
        self.assertEqual(header('EXP: 471 SP: 19'),('471','19'))
