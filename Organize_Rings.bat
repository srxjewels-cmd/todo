@echo off
setlocal
rem Reorganize scraped rings into Engagement Ring / Others, sorted by price,
rem renumbered, with each details.txt renamed to the product's price.
rem
rem Double-click to use the default folder (D:\quine p\prd\Rings),
rem or drag a folder onto this file to organize that folder instead.

cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install it from https://www.python.org/downloads/
  echo ^(tick "Add python.exe to PATH"^), then run this again.
  pause
  exit /b 1
)

if "%~1"=="" (
  python organize_rings.py "D:\quine p\prd\Rings"
) else (
  python organize_rings.py "%~1"
)
