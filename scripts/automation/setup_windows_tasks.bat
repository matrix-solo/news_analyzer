@echo off
echo ========================================
echo   News Analyzer - Task Scheduler Setup
echo ========================================
echo.

:: Check admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Project path (parent of scripts folder)
set SCRIPTS_PATH=%~dp0
set SCRIPTS_PATH=%SCRIPTS_PATH:~0,-1%
for %%I in ("%SCRIPTS_PATH%") do set PROJECT_PATH=%%~dpI
set PROJECT_PATH=%PROJECT_PATH:~0,-1%

echo Project path: %PROJECT_PATH%
echo Scripts path: %SCRIPTS_PATH%
echo.

:: Create collect + report task - 7:00 AM (main task)
echo Creating task: News-Collect-Report-7AM
schtasks /create /tn "News-Collect-Report-7AM" /tr "\"%SCRIPTS_PATH%\run_collect_and_report.bat\"" /sc daily /st 07:00 /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] News-Collect-Report-7AM (07:00 - Collect + Generate Report)
) else (
    echo [FAIL] News-Collect-Report-7AM
)

:: Create email task - 8:30 AM
echo Creating task: News-Email-Send
schtasks /create /tn "News-Email-Send" /tr "\"%SCRIPTS_PATH%\run_send_email_auto.bat\"" /sc daily /st 08:30 /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] News-Email-Send (08:30)
) else (
    echo [FAIL] News-Email-Send
)

:: Create collect task - 3:00 PM (supplementary)
echo Creating task: News-Collect-3PM
schtasks /create /tn "News-Collect-3PM" /tr "\"%SCRIPTS_PATH%\run_collect_auto.bat\"" /sc daily /st 15:00 /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] News-Collect-3PM (15:00)
) else (
    echo [FAIL] News-Collect-3PM
)

:: Create collect task - 11:00 PM (supplementary)
echo Creating task: News-Collect-11PM
schtasks /create /tn "News-Collect-11PM" /tr "\"%SCRIPTS_PATH%\run_collect_auto.bat\"" /sc daily /st 23:00 /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] News-Collect-11PM (23:00)
) else (
    echo [FAIL] News-Collect-11PM
)

echo.
echo ========================================
echo   All tasks created successfully!
echo ========================================
echo.
echo Schedule (Beijing Time):
echo   07:00  Collect News + Generate Report (MAIN)
echo   08:30  Send Email
echo   15:00  Collect News (supplementary)
echo   23:00  Collect News (supplementary)
echo.
echo Data Coverage:
echo   Report covers: Yesterday 07:00 - Today 07:00
echo   This includes: China day + Europe afternoon + US day
echo.
echo Tip: Open "Task Scheduler" to manage these tasks
echo.
pause
