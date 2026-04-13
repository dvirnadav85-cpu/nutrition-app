@echo off
REM Sets up a daily Windows Task Scheduler task to run reminder.py at 20:00

set SCRIPT_DIR=%~dp0
set PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe
set SCRIPT=%SCRIPT_DIR%reminder.py
set TASK_NAME=NutritionReminder

echo Setting up daily reminder task at 20:00...

schtasks /create /tn "%TASK_NAME%" /tr "\"%PYTHON%\" \"%SCRIPT%\"" /sc daily /st 20:00 /f

if %errorlevel% == 0 (
    echo.
    echo Task created successfully!
    echo The reminder will run every day at 20:00.
    echo To view it: open Task Scheduler and look for "%TASK_NAME%"
    echo To remove it: schtasks /delete /tn "%TASK_NAME%" /f
) else (
    echo.
    echo Failed to create task. Try running this file as Administrator.
    echo Right-click setup_reminder.bat and choose "Run as administrator"
)

pause
