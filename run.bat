@echo off
echo Starting SmartAttend...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred while running the application.
    pause
)
