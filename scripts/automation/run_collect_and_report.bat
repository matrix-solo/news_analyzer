@echo off
cd /d %~dp0..\..
python task1_collector.py && python task2_reporter.py --no-email
pause
