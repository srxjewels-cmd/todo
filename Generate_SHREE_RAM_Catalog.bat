@echo off
REM ============================================================
REM  Double-click this file to build the SHREE RAM catalogue.
REM  Keep it in the same folder as catalog_generator.py
REM ============================================================
setlocal

REM Folder that holds your product photos (edit if it ever moves):
set "PHOTOS=D:\SHREE RAM"

REM Run the generator that sits next to this launcher:
cd /d "%~dp0"

REM Use the details file if you have created one, otherwise run plain.
if exist "catalog_details_template.csv" (
    python "catalog_generator.py" "%PHOTOS%" --details "catalog_details_template.csv"
) else (
    python "catalog_generator.py" "%PHOTOS%"
)

echo.
echo Done. Look for the *_Catalog.html file in this folder.
echo Open it in a browser, then File ^> Print ^> Save as PDF.
echo.
pause
