@echo off
chcp 65001 >nul 2>&1
cd /d %~dp0..\..
python send_email.py
if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] 邮件发送成功 >> logs\email_task.log
) else (
    echo [%date% %time%] 邮件发送失败，错误码: %ERRORLEVEL% >> logs\email_task.log
)
