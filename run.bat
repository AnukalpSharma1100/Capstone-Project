@echo off
title College Resource Hub - Capstone Project
cd /d "%~dp0"

echo ===================================================================
echo           COLLEGE RESOURCE HUB - CAPSTONE PROJECT
echo     Previous Year Question Papers and Academic Archive Server
echo ===================================================================
echo.
echo [1/3] Verifying Python Environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not found in system PATH.
    echo Please install Python 3.8 or higher from python.org and check Add Python to PATH.
    pause
    exit /b
)

echo [2/3] Checking required dependencies...
python -c "import flask, flask_cors, pypdf, docx, PIL, reportlab" >nul 2>&1
if errorlevel 1 (
    echo Missing packages detected. Automatically installing from requirements.txt...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies. Please check your internet connection.
        pause
        exit /b
    )
) else (
    echo All required packages are already installed.
)

echo.
echo [3/3] Launching Server...
echo.
echo * Note: Demo logins are pre-configured.
echo * Opening http://127.0.0.1:5000 in your web browser...
echo * IMPORTANT: Keep this window OPEN while using the website!
echo.
echo Starting server...
python app.py
pause
