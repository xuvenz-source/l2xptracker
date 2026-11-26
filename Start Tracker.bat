@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv || goto failed
  .venv\Scripts\python.exe -m pip install -r requirements.txt || goto failed
)
.venv\Scripts\python.exe tracker.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo Setup or launch failed. Check Python and Tesseract installation.
pause
