@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install it from https://www.python.org/downloads/
  echo ^(check "Add python.exe to PATH" during install^), then run this again.
  pause
  exit /b 1
)
echo Installing dependencies (quick after the first run)...
python -m pip install --quiet playwright requests pillow
python -m playwright install chromium
echo.
echo Starting scraper - a Chrome window will open so you can watch.
echo Output goes to D:\jewels\neckless\1
echo.
python quince_scraper.py
pause
