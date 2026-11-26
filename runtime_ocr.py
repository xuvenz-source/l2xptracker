"""Locate bundled OCR first, without modifying system installation."""
import os, sys, shutil
from pathlib import Path


def locate_ocr(frozen=None, executable=None):
    frozen = getattr(sys, 'frozen', False) if frozen is None else frozen
    if frozen:
        folder = Path(executable or sys.executable).resolve().parent / 'ocr'
        exe = folder / 'tesseract.exe'
        if not exe.is_file() or not (folder / 'tessdata' / 'eng.traineddata').is_file():
            raise FileNotFoundError('Bundled OCR is missing. Extract the complete portable ZIP, not just the EXE.')
        return exe, folder / 'tessdata'
    default = Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Tesseract-OCR' / 'tesseract.exe'
    found = shutil.which('tesseract')
    exe = Path(found) if found else default
    return (exe, None) if exe.is_file() else (None, None)


def configure_ocr():
    import pytesseract
    exe, data = locate_ocr()
    if exe:
        pytesseract.pytesseract.tesseract_cmd = str(exe)
    if data:
        os.environ['TESSDATA_PREFIX'] = str(data)
        # Tesseract is a separate executable with its own DLLs. Remove the
        # frozen bootloader's inherited DLL override before launching it.
        if os.name == 'nt':
            import ctypes
            if not ctypes.windll.kernel32.SetDllDirectoryW(None):
                raise ctypes.WinError()
    return exe
