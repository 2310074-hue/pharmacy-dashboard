@echo off
REM ============================================================================
REM PharmaCare - Automated Daily Demand Forecasting & Critical Stock Alert
REM Runs daily at 9:00 AM via Windows Task Scheduler
REM ============================================================================

cd /d "%~dp0"
echo [%date% %time%] Starting PharmaCare Critical Stock Audit... >> daily_alert_log.txt
call .venv\Scripts\python.exe manage.py check_critical_stock >> daily_alert_log.txt 2>&1
echo [%date% %time%] Audit Completed. >> daily_alert_log.txt
