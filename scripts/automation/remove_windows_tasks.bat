@echo off
echo ========================================
echo   News Analyzer - Remove All Tasks
echo ========================================
echo.

:: Check admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo Removing all scheduled tasks...
echo.

:: Delete tasks
schtasks /delete /tn "News-Collect-Report-7AM" /f >nul 2>&1
echo [OK] Removed News-Collect-Report-7AM

schtasks /delete /tn "News-Collect-7AM" /f >nul 2>&1
echo [OK] Removed News-Collect-7AM

schtasks /delete /tn "News-Collect-3PM" /f >nul 2>&1
echo [OK] Removed News-Collect-3PM

schtasks /delete /tn "News-Collect-Report-11PM" /f >nul 2>&1
echo [OK] Removed News-Collect-Report-11PM

schtasks /delete /tn "News-Collect-11PM" /f >nul 2>&1
echo [OK] Removed News-Collect-11PM

schtasks /delete /tn "News-Report-Generate" /f >nul 2>&1
echo [OK] Removed News-Report-Generate

schtasks /delete /tn "News-Email-Send" /f >nul 2>&1
echo [OK] Removed News-Email-Send

echo.
echo ========================================
echo   All tasks removed successfully!
echo ========================================
echo.
pause
