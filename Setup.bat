@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo.
echo  ===================================================
echo    MoneyMan one-time Setup
echo  ===================================================
echo.
echo  This installs a small OFFLINE library that lets MoneyMan read PDF
echo  statements. It reads PDFs on your computer and sends nothing anywhere.
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY goto :nopy

%PY% -m pip install --upgrade pip
%PY% -m pip install pypdf pdfplumber
echo.
echo  Setup complete. MoneyMan can now read PDF statements.
echo  Next: double-click Run-MoneyMan.bat (or Try-Demo.bat to see a demo).
echo.
pause
exit /b 0

:nopy
echo  Python 3 was not found.
echo    1) Install Python 3 from https://www.python.org/downloads/
echo    2) During setup, TICK "Add python.exe to PATH".
echo    3) Run this Setup again.
echo.
pause
exit /b 1
