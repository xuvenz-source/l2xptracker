"""Preview every registered HUD widget and exercise the settings callback."""
import unittest
from unittest.mock import Mock,patch
from tracker import App
from hud_layout import WIDGETS,clean

class HudVitalsPreviewTests(unittest.TestCase):
    def app(self):
        a=App.__new__(App)
        a.hud_preview=Mock()
        a.hud_preview.winfo_width.return_value=900
        a.hud_preview.cget.return_value='110'
        a.hud_opacity=92
        a.hud_net_adena=False
        return a
    def test_every_widget_preview(self):
        for key in WIDGETS:
            with self.subTest(widget=key):
                a=self.app();a.hud_config=clean(dict(enabled=[key]))
                a.preview_hud()
                self.assertIn(WIDGETS[key][1],[c.kwargs.get('text') for c in a.hud_preview.create_text.call_args_list])
    def test_vitals_toggle_callback_and_preview(self):
        for enabled in (['hp'],['mp'],['hp','mp'],list(WIDGETS)):
            with self.subTest(enabled=enabled):
                a=self.app();a.hud=Mock();a.hud_order=list(WIDGETS)
                a.hud_vars={k:Mock(get=Mock(return_value=k in enabled)) for k in WIDGETS}
                a.hud_size=Mock(get=Mock(return_value='compact'))
                a.hud_rows=Mock(get=Mock(return_value='Auto (one row)'))
                a.hud_enabled=Mock(get=Mock(return_value=True))
                a.hud_controls={k:Mock(get=Mock(return_value=True)) for k in ('pause','reset')}
                with patch('tracker.save_hud') as save:a.apply_hud_config()
                self.assertEqual(set(a.hud_config['enabled']),set(enabled))
                save.assert_called_once_with(a.hud_config)
                a.hud.configure_layout.assert_called_once_with(a.hud_config)
                texts=[c.kwargs.get('text') for c in a.hud_preview.create_text.call_args_list]
                for k,v in (('hp','449/505 - 89%'),('mp','58/187 - 31%')):
                    if k in enabled:self.assertIn(v,texts)
