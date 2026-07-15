@echo off
setlocal
rem Refreshes just the app files (no dependency reinstall). Run this to get
rem the latest catalog_scraper.py / scraper_app.pyw.
set DEST=%USERPROFILE%\JewelsScraper
set ZIP=%TEMP%\jewels_update.zip

if not exist "%DEST%" (
  echo Jewels Scraper is not installed yet. Run Setup_Jewels_Scraper.bat first.
  pause
  exit /b 1
)
echo Downloading the latest version...
curl -L -sS -o "%ZIP%" https://github.com/srxjewels-cmd/todo/archive/refs/heads/claude/quince-necklace-scraper-w0th5x.zip
if not exist "%ZIP%" (
  echo Download failed. Check your internet connection and try again.
  pause
  exit /b 1
)
if exist "%TEMP%\jewels_update" rmdir /s /q "%TEMP%\jewels_update"
mkdir "%TEMP%\jewels_update"
tar -xf "%ZIP%" -C "%TEMP%\jewels_update"
set SRC=
for /d %%D in ("%TEMP%\jewels_update\todo-*") do set SRC=%%D
copy /Y "%SRC%\scraper_app.pyw" "%DEST%" >nul
copy /Y "%SRC%\catalog_scraper.py" "%DEST%" >nul
copy /Y "%SRC%\SCRAPER_README.md" "%DEST%" >nul
del "%ZIP%"
rmdir /s /q "%TEMP%\jewels_update"
echo.
echo Updated! Launch "Jewels Scraper" from your Desktop as usual.
pause
