@echo off
setlocal
rem One-time installer: downloads the Jewels Scraper app, installs its
rem dependencies, and puts a "Jewels Scraper" launcher on your Desktop.
set DEST=%USERPROFILE%\JewelsScraper
set ZIP=%TEMP%\jewels_scraper_src.zip

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on this computer.
  echo Opening the download page - install it and TICK "Add python.exe to PATH",
  echo then run this file again.
  start https://www.python.org/downloads/
  pause
  exit /b 1
)

echo Downloading the app...
curl -L -sS -o "%ZIP%" https://github.com/srxjewels-cmd/todo/archive/refs/heads/claude/quince-necklace-scraper-w0th5x.zip
if not exist "%ZIP%" (
  echo Download failed. Check your internet connection and run this again.
  pause
  exit /b 1
)
if exist "%TEMP%\jewels_scraper_src" rmdir /s /q "%TEMP%\jewels_scraper_src"
mkdir "%TEMP%\jewels_scraper_src"
tar -xf "%ZIP%" -C "%TEMP%\jewels_scraper_src"
set SRC=
for /d %%D in ("%TEMP%\jewels_scraper_src\todo-*") do set SRC=%%D
if "%SRC%"=="" (
  echo Could not unpack the download.
  pause
  exit /b 1
)
if not exist "%DEST%" mkdir "%DEST%"
copy /Y "%SRC%\scraper_app.pyw" "%DEST%" >nul
copy /Y "%SRC%\catalog_scraper.py" "%DEST%" >nul
copy /Y "%SRC%\SCRAPER_README.md" "%DEST%" >nul
del "%ZIP%"
rmdir /s /q "%TEMP%\jewels_scraper_src"

echo Installing Python packages (this can take a few minutes the first time)...
python -m pip install --quiet playwright requests pillow
python -m playwright install chromium

> "%USERPROFILE%\Desktop\Jewels Scraper.bat" (
  echo @echo off
  echo cd /d "%DEST%"
  echo where pythonw ^>nul 2^>nul ^&^& ^(start "" pythonw scraper_app.pyw^) ^|^| ^(start "" python scraper_app.pyw^)
)

echo.
echo Installed! A "Jewels Scraper" launcher is now on your Desktop.
echo Starting the app...
cd /d "%DEST%"
where pythonw >nul 2>nul && (start "" pythonw scraper_app.pyw) || (start "" python scraper_app.pyw)
pause
