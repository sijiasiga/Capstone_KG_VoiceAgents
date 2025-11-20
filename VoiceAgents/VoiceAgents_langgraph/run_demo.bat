@echo off
REM Voice Agent Demo Launcher
REM This script runs the Streamlit demo with the correct Python environment

echo Starting Voice Agent Demo...
echo.

REM Change to the correct directory
cd /d "%~dp0"

REM Activate virtual environment and run streamlit
call venv\Scripts\activate.bat
cd prototype_demo
streamlit run streamlit_app.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo An error occurred! Press any key to exit...
    pause >nul
)
