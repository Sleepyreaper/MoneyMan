@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo.
echo  ===================================================
echo    MoneyMan (editable) - opens in your web browser
echo  ===================================================
echo.
echo  This runs MoneyMan as a small web app ON THIS COMPUTER only.
echo  You can type in your home value, debt interest rates, etc.,
echo  click Save, and it remembers - nothing is sent anywhere.
echo.
echo  Leave this black window open while you use it.
echo  Close it (or press Ctrl+C) when you're done.
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY goto :nopy

set "PYTHONUTF8=1"
%PY% -m moneyman serve
echo.
pause
exit /b 0

:nopy
echo  Python 3 was not found. Install it from https://www.python.org/downloads/
echo  (tick "Add python.exe to PATH"), then run this again.
echo.
pause
exit /b 1
