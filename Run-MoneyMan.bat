@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo.
echo  ===================================================
echo    MoneyMan  -  your private, offline finance analyst
echo  ===================================================
echo.
echo  Reading the statements in your MoneyMan folder...
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY goto :nopy

set "PYTHONUTF8=1"
%PY% -m moneyman %*
echo.
echo  Done. Your report should have opened in your web browser.
echo  If it did not, open the newest file in your MoneyMan "Reports" folder.
echo.
pause
exit /b 0

:nopy
echo  --------------------------------------------------------
echo   Python 3 was not found on this computer.
echo   MoneyMan needs Python 3 (a free, safe program).
echo.
echo     1) Open  https://www.python.org/downloads/
echo     2) Install Python 3. IMPORTANT: tick the box
echo        "Add python.exe to PATH" during setup.
echo     3) Double-click this file again.
echo  --------------------------------------------------------
echo.
pause
exit /b 1
