@echo off
setlocal
rem Downloads the scraped Quince photos and installs them to D:\jewels\neckless\1
set ZIP=%TEMP%\quince_results.zip
set EXTRACT=%TEMP%\quince_extract

echo Downloading photos (about 100 MB, may take a minute)...
curl -L -sS -o "%ZIP%" https://github.com/srxjewels-cmd/todo/archive/refs/heads/claude/quince-scrape-results.zip
if not exist "%ZIP%" (
  echo Download failed. Check your internet connection and run this again.
  pause
  exit /b 1
)

echo Extracting...
if exist "%EXTRACT%" rmdir /s /q "%EXTRACT%"
mkdir "%EXTRACT%"
tar -xf "%ZIP%" -C "%EXTRACT%"

set SRC=
for /d %%D in ("%EXTRACT%\todo-*") do set SRC=%%D
if "%SRC%"=="" (
  echo Could not find the extracted folder. Nothing was copied.
  pause
  exit /b 1
)

if not exist D:\ (
  echo Drive D: was not found on this computer.
  echo The photos are in: %SRC%\out\jewels
  echo Copy that folder wherever you like.
  pause
  exit /b 1
)

echo Copying to D:\jewels\neckless\1 ...
xcopy /E /I /Y /Q "%SRC%\out\jewels" "D:\jewels" >nul

del "%ZIP%"
rmdir /s /q "%EXTRACT%"

echo.
echo Done! Folders 1 to 15 are now in D:\jewels\neckless\1
start "" "D:\jewels\neckless\1"
pause
