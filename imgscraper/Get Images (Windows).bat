@echo off
setlocal EnableExtensions
title Image Grabber
cd /d "%~dp0"

echo ============================================
echo   Image Grabber
echo ============================================
echo.

rem ---- find Python: the "py" launcher first, then "python" ----
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY (
    echo Python is not installed yet. One-time setup:
    echo.
    echo   1. A download page will open in your browser - click "Download Python".
    echo   2. Run the installer and TICK the box "Add Python to PATH".
    echo   3. When it finishes, double-click this file again.
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

rem ---- one-time: install the pieces the tool needs ----
%PY% -c "import requests, bs4, PIL, tqdm" >nul 2>&1
if errorlevel 1 (
    echo First run - setting things up. This takes a minute or two...
    %PY% -m pip install -q -r requirements.txt || %PY% -m pip install -q --user -r requirements.txt
)
%PY% -c "import requests, bs4, PIL, tqdm" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Setup hit a problem. Take a screenshot of this window and send it to Claude.
    pause
    exit /b 1
)

echo.
set "URL="
set /p "URL=Paste the website address and press Enter: "
if not defined URL (
    echo No address given - nothing to do.
    pause
    exit /b 1
)
set "MAX="
set /p "MAX=How many images maximum? Press Enter for no limit: "
set "EXTRA="
if defined MAX set "EXTRA=--max-images %MAX%"

echo.
%PY% imgscraper.py "%URL%" %EXTRA%

echo.
if exist "%cd%\images" (
    echo Opening the folder with your images...
    start "" "%cd%\images"
)
pause
