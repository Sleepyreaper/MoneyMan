@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo.
echo  ===================================================
echo    MoneyMan DEMO  -  using realistic fake data
echo  ===================================================
echo.
echo  This creates pretend bank statements (no real data needed)
echo  and shows you what your report will look like.
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY goto :nopy

set "PYTHONUTF8=1"
%PY% -m moneyman --demo
echo.
echo  Done. The demo report should have opened in your browser.
echo  The fake data lives in a separate "MoneyMan-Demo" folder so it
echo  never mixes with your real statements.
echo.
pause
exit /b 0

:nopy
echo  Python 3 was not found. Install it from https://www.python.org/downloads/
echo  (tick "Add python.exe to PATH"), then double-click this file again.
echo.
pause
exit /b 1
