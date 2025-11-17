@echo off
title Universal FPS Booster - Windows Launcher
color 0A

echo.
echo ========================================
echo    🚀 Universal FPS Booster 🚀
echo ========================================
echo.

REM Check if running as Administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Running as Administrator - Maximum optimization enabled!
) else (
    echo ⚠️  NOT running as Administrator
    echo    Right-click this file and select "Run as administrator" for best results
)

echo.
echo Starting FPS optimization...
echo.

REM Run the Python script
python universal_fps_booster.py

REM Check if Python command worked
if %errorLevel% neq 0 (
    echo.
    echo ❌ Python not found or script failed
    echo Trying alternative Python commands...
    echo.
    
    REM Try python3
    python3 universal_fps_booster.py
    
    if %errorLevel% neq 0 (
        REM Try py launcher
        py universal_fps_booster.py
        
        if %errorLevel% neq 0 (
            echo.
            echo ❌ Could not run Python script
            echo Please install Python 3.8+ from python.org
            echo.
        )
    )
)

echo.
echo ========================================
echo Press any key to exit...
pause >nul