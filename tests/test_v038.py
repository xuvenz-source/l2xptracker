import hashlib,io,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from updater import download,release_info
from updater_view import download_display
from test_updater import release
from startup_update import StartupUpdater

class Response(io.BytesIO):
    def __init__(self,body,headers):
        super().__init__(body);self.headers=headers

class VisualUpdaterTests(unittest.TestCase):
    def test_known_size_download(self):
        data=b'x'*600000;events=[]
        with tempfile.TemporaryDirectory() as d, patch('updater.open_url',return_value=Response(data,{'Content-Length':str(len(data))})):
            path=Path(d)/'a.zip'
            download('url',path,hashlib.sha256(data).hexdigest(),lambda n,t:events.append((n,t)))
            self.assertEqual(path.read_bytes(),data)
        self.assertEqual(events[0],(0,len(data)));self.assertEqual(events[-1],(len(data),len(data)))
    def test_release_size_and_unknown(self):
        r=release();r['assets'][0]['size']=1234
        self.assertEqual(release_info(r)['size'],1234)
        self.assertIsNone(download_display(1024,None)[0]);self.assertEqual(download_display(50,100)[0],50)
    def test_incomplete_download(self):
        with tempfile.TemporaryDirectory() as d,patch('updater.open_url',return_value=Response(b'abc',{})):
            with self.assertRaisesRegex(ValueError,'Incomplete'):
                download('url',Path(d)/'a',hashlib.sha256(b'abc').hexdigest(),expected_size=5)
    def test_startup_respects_disabled_auto_update(self):
        u=StartupUpdater.__new__(StartupUpdater);u.view=Mock();u.install=Mock()
        with patch('startup_update.load_auto_update',return_value=False):
            u.offer({'version':'9.99'})
        u.install.assert_not_called();self.assertEqual(u.state,'offer')
    def test_startup_offers_failed_version(self):
        u=StartupUpdater.__new__(StartupUpdater);u.view=Mock();u.install=Mock()
        with patch('startup_update.load_auto_update',return_value=True),patch('startup_update.failed_update',return_value='9.99'):
            u.offer({'version':'9.99'})
        u.install.assert_not_called()
    def test_startup_auto_install(self):
        u=StartupUpdater.__new__(StartupUpdater);u.view=Mock();u.install=Mock()
        with patch('startup_update.load_auto_update',return_value=True),patch('startup_update.failed_update',return_value=''):
            u.offer({'version':'9.99'})
        u.install.assert_called_once()
    def test_continue_not_during_install(self):
        u=StartupUpdater.__new__(StartupUpdater);u.state='installing';u.open_tracker=Mock()
        u.continue_tracker();u.open_tracker.assert_not_called()
