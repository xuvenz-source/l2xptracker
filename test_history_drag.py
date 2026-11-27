import unittest,tempfile,json
from pathlib import Path
from history import Archive,history_children,history_forest,group_drop_plan
from test_v016 import data

class DragGroupingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.arc=Archive(Path(self.tmp.name)/'sessions.sqlite3')
        for i,key in enumerate('abcdef',1):self.arc.save(key,key,data(i*100,i*10,i*20))
    def test_append_to_existing_group(self):
        g=self.arc.merge(['a','b'],'Farm')
        self.assertTrue(self.arc.add_to_group(g,['c']))
        r=self.arc.records()
        self.assertEqual(r[g]['name'],'Farm')
        self.assertEqual(r[g]['data']['children'],['a','b','c'])
        self.assertEqual(self.arc.summary(g)['seconds'],600)
        self.assertEqual(len(r),7)
    def test_duplicate_drop_is_noop(self):
        g=self.arc.merge(['a','b'],'Farm')
        self.assertFalse(self.arc.add_to_group(g,['b','b']))
        self.assertEqual(self.arc.summary(g)['seconds'],300)
    def test_nested_ancestor_updates(self):
        g=self.arc.merge(['a','b'],'Farm')
        h=self.arc.merge([g,'c'],'Parent')
        j=self.arc.merge([h,'d'],'Grandparent')
        k=self.arc.merge([g,'e'],'Shared parent')
        self.arc.add_to_group(g,['f'])
        r=self.arc.records()
        self.assertEqual(set(r[j]['data']['sources']),set('abcdf'))
        self.assertEqual(set(r[k]['data']['sources']),set('abef'))
        self.assertIn(g,history_children(r)[h])
        self.assertEqual(self.arc.summary(j)['totals']['You','Adena'],320)
    def test_cycle_rejected_atomically(self):
        g=self.arc.merge(['a','b'],'Farm')
        h=self.arc.merge([g,'c'],'Parent')
        original=self.arc.records()
        for ids in ([h],[g],['d',h]):
            with self.assertRaises(ValueError):self.arc.add_to_group(g,ids)
            self.assertEqual(self.arc.records(),original)
    def test_shared_source_group(self):
        g=self.arc.merge(['a','b'],'Farm')
        h=self.arc.merge(['b','c'],'Other')
        self.arc.add_to_group(g,[h,'c'])
        r=self.arc.records()
        self.assertEqual(r[g]['data']['children'],['a','b',h])
        self.assertEqual(set(r[g]['data']['sources']),set('abc'))
        self.assertEqual(self.arc.summary(g)['seconds'],600)
        self.assertEqual(self.arc.summary(h)['seconds'],500)
    def test_legacy_add(self):
        with self.arc.db() as db:db.execute('INSERT INTO sessions VALUES (?,?,?,?)',('legacy','Old','merged',json.dumps({'sources':['a','b']})))
        self.arc.add_to_group('legacy',['c','d'])
        self.assertEqual(self.arc.records()['legacy']['data']['children'],list('abcd'))
    def test_plan_is_pure(self):
        g=self.arc.merge(['a','b'],'Farm')
        r=self.arc.records();old=json.dumps(r)
        plan=group_drop_plan(r,g,['d'])
        self.assertIn('d',plan[g]['sources'])
        self.assertEqual(json.dumps(r),old)


    def test_ui_drop_actions(self):
        from history_ui import HistoryWindow
        from unittest.mock import Mock,patch
        from types import SimpleNamespace
        h=HistoryWindow.__new__(HistoryWindow)
        h.archive=self.arc;h.records=self.arc.records()
        h.row_records={'a-row':'a','b-row':'b','c-row':'c'}
        h.tree=Mock();h.tree.winfo_width.return_value=700;h.tree.winfo_height.return_value=400
        h.tree.identify_row.return_value='b-row'
        h.dragging=True;h.drag_ids=['a'];h.cancel_drag=Mock();h.refresh=Mock();h.win=Mock()
        event=SimpleNamespace(x=100,y=100)
        with patch('history_ui.simpledialog.askstring',return_value='Duo'):
            self.assertEqual(h.drag_end(event),'break')
        g=next(i for i,r in self.arc.records().items() if r['kind']=='merged')
        self.assertEqual(self.arc.summary(g)['seconds'],300)
        h.records=self.arc.records();h.row_records['group-row']=g
        h.tree.identify_row.return_value='group-row';h.dragging=True;h.drag_ids=['c']
        self.assertEqual(h.drag_end(event),'break')
        self.assertEqual(self.arc.summary(g)['seconds'],600)
        h.refresh.assert_called_with([g])
