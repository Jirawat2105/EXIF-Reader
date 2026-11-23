@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  python -m venv .venv
  if errorlevel 1 goto error
)
.venv\Scripts\python.exe -c "import PySide6, PIL, reportlab" >nul 2>&1
if errorlevel 1 (
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 goto error
)
.venv\Scripts\python.exe scripts\install_exiftool.py
if errorlevel 1 goto error
start "" .venv\Scripts\pythonw.exe main.py
exit /b
:error
echo Setup failed. Check the message above, Python 3.11+, and your internet connection.
pause
