@echo off
setlocal

cd /d "%~dp0"

echo Starting AI Town LLM backend...
start "AI Town LLM Backend" cmd /k "cd /d ""%~dp0"" && npm run start:llm"

call conda activate AI_Town
if errorlevel 1 (
    echo Failed to activate conda environment AI_Town.
    echo Make sure Anaconda/Miniconda is initialized for Command Prompt.
    pause
    exit /b 1
)

python python_town\main.py
if errorlevel 1 (
    echo.
    echo AI Town exited with an error.
    pause
    exit /b 1
)

endlocal
