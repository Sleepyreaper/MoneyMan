@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo.
echo  ===================================================
echo    MoneyMan Interview - let's personalize your plan
echo  ===================================================
echo.
echo  I'll ask a few plain questions (home, rental, cars, savings,
echo  and the interest rate on each debt). Press Enter to skip any.
echo  Everything stays on this computer.
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY goto :nopy

set "PYTHONUTF8=1"
%PY% -m moneyman interview
echo.
echo  When you're done, double-click Run-MoneyMan.bat to see your plan.
echo.
pause
exit /b 0

:nopy
echo  Python 3 was not found. Install it from https://www.python.org/downloads/
echo  (tick "Add python.exe to PATH"), then run this again.
echo.
pause
exit /b 1
