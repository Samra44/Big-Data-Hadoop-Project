@echo off
REM EarthScape one-click start (Windows)
cd /d "%~dp0app"
if not exist ".venv" (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
start "" http://127.0.0.1:5000
python app.py
pause
