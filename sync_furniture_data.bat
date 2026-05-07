@echo off
setlocal
cd /d "%~dp0"
python python_town\tools\sync_furniture_data.py
if errorlevel 1 goto done
start "" "%~dp0python_town\data\furniture_catalog.csv"
start "" "%~dp0python_town\data\furniture_placements.csv"
:done
echo.
pause
