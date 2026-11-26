import tempfile, unittest
from pathlib import Path
from runtime_ocr import locate_ocr
from build_portable import find_tesseract, copy_ocr

class PortableTests(unittest.TestCase):
    def test_bundled_paths_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='L2 Tracker ') as d:
            p=Path(d); exe=p/'L2 Legacy Tracker.exe'; ocr=p/'ocr'; (ocr/'tessdata').mkdir(parents=True); (ocr/'tesseract.exe').touch(); (ocr/'tessdata'/'eng.traineddata').touch()
            self.assertEqual(locate_ocr(True,exe),(ocr/'tesseract.exe',ocr/'tessdata'))
    def test_missing_ocr_fails(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError): locate_ocr(True,Path(d)/'tracker.exe')
    def test_copy_preserves_runtime_without_personal_files(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); src=p/'source'; (src/'tessdata').mkdir(parents=True)
            for name in ('tesseract.exe','libtesseract.dll','LICENSE.txt','uninstall.exe','personal.txt'): (src/name).write_text(name)
            (src/'tessdata'/'eng.traineddata').touch()
            self.assertEqual(find_tesseract(src),src/'tesseract.exe')
            copy_ocr(src/'tesseract.exe',p/'output')
            for name in ('tesseract.exe','libtesseract.dll','LICENSE.txt','tessdata/eng.traineddata'): self.assertTrue((p/'output'/name).exists())
            for name in ('uninstall.exe','personal.txt'): self.assertFalse((p/'output'/name).exists())
    def test_missing_language_fails(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'tesseract.exe').touch()
            with self.assertRaises(RuntimeError):find_tesseract(d)
