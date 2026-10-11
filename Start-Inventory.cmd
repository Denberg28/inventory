@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3.12 run_inventory.py
) else (
    python run_inventory.py
)
if errorlevel 1 pause
