"""Local bounded diagnostics; no chat messages, screenshots or session data."""
import logging, faulthandler
from logging.handlers import RotatingFileHandler
from settings import settings_path
from version import VERSION

_logger=logging.getLogger('l2tracker')
_logger.addHandler(logging.NullHandler())
_logger.propagate=False
_crash_file=None

def setup_diagnostics():
    global _crash_file
    try:
        folder=settings_path().parent;folder.mkdir(parents=True,exist_ok=True)
        handler=RotatingFileHandler(folder/'tracker-diagnostics.log',maxBytes=512*1024,backupCount=2,encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(threadName)s %(message)s'))
        _logger.addHandler(handler);_logger.setLevel(logging.INFO)
        # Keep only the current application's native fault dump.
        _crash_file=(folder/'tracker-crash.log').open('w',encoding='utf-8')
        faulthandler.enable(file=_crash_file,all_threads=True)
        diagnostic('Tracker v%s started',VERSION)
    except Exception:pass

def diagnostic(message,*args,**kwargs):
    # No UI calls or game text from worker threads. Log failures must not
    # become tracker failures. Do not include raw chat in diagnostic calls.
    try:_logger.info(message,*args,**kwargs)
    except Exception:pass
