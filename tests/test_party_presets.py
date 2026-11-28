import tempfile,unittest
from pathlib import Path
from party_presets import load_presets,save_preset,rename_preset,delete_preset
from preferences import save_auto_update,load_auto_update,save_focus_pause,load_focus_pause,write_preference
from history import Archive
from test_v016 import data

class PartyPresetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'tracker_preferences.json'
    def test_save_reload_normalizes(self):
        self.assertEqual(load_presets(self.path),{})
        save_preset(' Duo ',['Alpha','alpha','You','Beta'],self.path)
        self.assertEqual(load_presets(self.path),{'Duo':['Alpha','Beta']})
    def test_preserve_other_settings(self):
        save_auto_update(False,self.path);save_focus_pause(True,self.path)
        save_preset('Duo',['Alpha'],self.path)
        self.assertFalse(load_auto_update(self.path));self.assertTrue(load_focus_pause(self.path))
        save_focus_pause(False,self.path)
        self.assertEqual(load_presets(self.path),{'Duo':['Alpha']})
    def test_duplicate_and_replace(self):
        save_preset('Duo',['Alpha'],self.path)
        with self.assertRaises(ValueError):save_preset('duo',['Beta'],self.path)
        save_preset('Duo',['Beta'],self.path,replace=True)
        self.assertEqual(load_presets(self.path),{'Duo':['Beta']})
    def test_rename_and_delete(self):
        save_preset('Duo',['Alpha'],self.path);save_preset('Trio',['Beta','Gamma'],self.path)
        with self.assertRaises(ValueError):rename_preset('Duo','trio',self.path)
        rename_preset('Duo','Friend',self.path)
        delete_preset('Trio',self.path)
        self.assertEqual(load_presets(self.path),{'Friend':['Alpha']})
    def test_validation_and_corrupt_entries(self):
        for name,members in [('', ['Alpha']),('Duo',[]),('Duo',['Two words']),('Too many',[f'P{i}' for i in range(9)])]:
            with self.assertRaises(ValueError):save_preset(name,members,self.path)
        write_preference('party_presets',{'Valid':['Alpha'],'Bad':None,'Empty':[],'Invalid':['Two words']},self.path)
        self.assertEqual(load_presets(self.path),{'Valid':['Alpha']})
    def test_historical_roster_unchanged(self):
        save_preset('Duo',['Alpha'],self.path)
        arc=Archive(Path(self.tmp.name)/'sessions.sqlite3')
        d=data(60,100,200);d['party_members']=load_presets(self.path)['Duo']
        arc.save('a','Original',d)
        save_preset('Duo',['Beta'],self.path,replace=True);delete_preset('Duo',self.path)
        self.assertEqual(arc.records()['a']['data']['party_members'],['Alpha'])
        self.assertEqual(arc.summary('a')['party']['estimated_party'],400)
