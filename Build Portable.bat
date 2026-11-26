@echo off
setlocal
cd /d "%~dp0"
echo Building L2 Legacy Tracker for Windows x64...
if not exist ".build-venv\Scripts\python.exe" (
  where py >nul 2>nul
  if errorlevel 1 (
    python -m venv .build-venv || goto failed
  ) else (
    py -3 -m venv .build-venv || goto failed
  )
)
".build-venv\Scripts\python.exe" -m pip install -r requirements-build.txt || goto failed
if "%~1"=="" (
  ".build-venv\Scripts\python.exe" build_portable.py || goto failed
) else (
  ".build-venv\Scripts\python.exe" build_portable.py --tesseract "%~1" || goto failed
)
echo.
echo Send your friends the ZIP in the "Share with friends" folder.
pause
exit /b 0
:failed
echo.
echo Build failed. See the error above. No new release was produced.
pause
exit /b 1
