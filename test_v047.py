import unittest,tempfile
from pathlib import Path
from unittest.mock import Mock,patch
from hud_layout import geometry,clean,save,load,row_choice,row_settings,ROW_OPTIONS,WIDGETS
from tracker import App

class WidgetLayoutTests(unittest.TestCase):
    def test_all_column_limits_and_sizes(self):
        for size in ('compact','standard','large'):
            for count in range(9):
                for n in range(1,9):
                    g=geometry(dict(enabled=list(WIDGETS)[:count],size=size,widgets_per_row=n))
                    rows={}
                    for k,x,y,w,h in g['cells']:
                        rows.setdefault(y,[]).append(k)
                        self.assertLessEqual(x+w,g['lock'][0])
                        self.assertLessEqual(y+h,g['height'])
                    self.assertEqual(len(g['cells']),count)
                    self.assertEqual(len(rows),(count+n-1)//n)
                    self.assertTrue(all(len(row)<=n for row in rows.values()))
    def test_legacy_layout_and_preference_roundtrip(self):
        for layout in ('single','double'):
            c=clean(dict(layout=layout,enabled=list(WIDGETS)))
            self.assertIsNone(c['widgets_per_row'])
            self.assertEqual(len(set(y for _,x,y,w,h in geometry(c)['cells'])),1 if layout=='single' else 2)
            self.assertEqual(row_settings(row_choice(c))['layout'],layout)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prefs.json'
            save(dict(enabled=['ad','xp','eta'],**row_settings('2')),p)
            c=load(p);self.assertEqual(row_choice(c),'2');self.assertEqual(c['widgets_per_row'],2)
        for bad in (True,0,len(WIDGETS)+1,'2'):
            self.assertIsNone(clean(dict(widgets_per_row=bad))['widgets_per_row'])
    def test_menu_uses_same_widget_and_row_variables(self):
        a=App.__new__(App);a.running=True;a.root=Mock();a.root.winfo_pointerxy.return_value=(10,20)
        from hud_layout import PROGRESSION
        a.hud_vars={k:Mock() for k in WIDGETS};a.hud_rows=Mock();a.hud_panel_rows={'progression':Mock()};a.apply_hud_config=Mock()
        menu,widgets,rows=Mock(),Mock(),Mock()
        with patch('tracker.tk.Menu',side_effect=[menu,widgets,rows]):a.show_hud_settings('progression')
        self.assertEqual([c.kwargs['variable'] for c in widgets.add_checkbutton.call_args_list],[a.hud_vars[k] for k in PROGRESSION])
        self.assertEqual([c.kwargs['value'] for c in rows.add_radiobutton.call_args_list],['Shared default',*ROW_OPTIONS[:2],*map(str,range(1,len(PROGRESSION)+1))])
        self.assertTrue(all(c.kwargs['variable'] is a.hud_panel_rows['progression'] for c in rows.add_radiobutton.call_args_list))
        widgets.add_checkbutton.call_args_list[0].kwargs['command']()
        rows.add_radiobutton.call_args_list[-1].kwargs['command']()
        self.assertEqual(a.apply_hud_config.call_count,2)
    def test_apply_preserves_session_and_shared_state(self):
        a=App.__new__(App);a.running=True;a.session_id='existing';a.events=['reward'];a.active_seconds=120
        a.hud_order=list(WIDGETS);a.hud_vars={k:Mock(get=Mock(return_value=k in ('ad','eta','xp'))) for k in WIDGETS}
        a.hud_size=Mock(get=Mock(return_value='compact'));a.hud_rows=Mock(get=Mock(return_value='2'))
        a.hud_enabled=Mock(get=Mock(return_value=True));a.hud_controls={k:Mock(get=Mock(return_value=True)) for k in ('status','pause','reset')}
        a.hud=Mock();a.preview_hud=Mock()
        with patch('tracker.save_hud') as save:a.apply_hud_config()
        self.assertEqual(a.hud_config['widgets_per_row'],2)
        self.assertEqual(a.hud_config['enabled'],['ad','xp','eta'])
        save.assert_called_once_with(a.hud_config);a.hud.configure_layout.assert_called_once_with(a.hud_config)
        self.assertEqual((a.session_id,a.events,a.active_seconds,a.running),('existing',['reward'],120,True))
