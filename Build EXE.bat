@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe python -m venv .venv
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller==6.22.3
if errorlevel 1 goto error
.venv\Scripts\python.exe scripts\build_windows.py
if errorlevel 1 goto error
exit /b
:error
echo Build failed. Check the error above.
pause
