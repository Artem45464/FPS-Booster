@echo off
REM Universal FPS Booster - Windows Launcher v2.5
REM Enhanced with better error handling and validation

title Universal FPS Booster - Windows Launcher
color 0A

setlocal EnableDelayedExpansion

REM Configuration
set SCRIPT_NAME=main.py
set LOG_FILE=fps_booster.log

cls
echo.
echo ========================================
echo    🚀 Universal FPS Booster v2.5 🚀
echo ========================================
echo.

REM Check if script exists
if not exist "%SCRIPT_NAME%" (
    color 0C
    echo ❌ ERROR: %SCRIPT_NAME% not found!
    echo.
    echo Please ensure %SCRIPT_NAME% is in the same folder:
    echo %CD%\%SCRIPT_NAME%
    echo.
    goto :end
)

REM Check for Administrator privileges
echo [Checking privileges...]
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Running as Administrator
    set ADMIN=1
) else (
    color 0E
    echo ⚠️  NOT running as Administrator
    echo.
    echo For best results, right-click this file and select
    echo "Run as administrator"
    echo.
    set /p "continue=Continue anyway? (Y/N): "
    if /i not "!continue!"=="Y" (
        echo.
        echo Cancelled by user.
        goto :end
    )
    set ADMIN=0
    color 0A
)

echo.
echo [Detecting Python...]

REM Try to find Python and check version
set PYTHON_CMD=
set PYTHON_VERSION=

REM Try python command
where python >nul 2>&1
if !errorLevel! == 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    if defined PYTHON_VERSION (
        echo Found: python version !PYTHON_VERSION!
        set PYTHON_CMD=python
        goto :python_found
    )
)

REM Try python3 command
where python3 >nul 2>&1
if !errorLevel! == 0 (
    for /f "tokens=2" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
    if defined PYTHON_VERSION (
        echo Found: python3 version !PYTHON_VERSION!
        set PYTHON_CMD=python3
        goto :python_found
    )
)

REM Try py launcher
where py >nul 2>&1
if !errorLevel! == 0 (
    for /f "tokens=2" %%i in ('py --version 2^>^&1') do set PYTHON_VERSION=%%i
    if defined PYTHON_VERSION (
        echo Found: py launcher version !PYTHON_VERSION!
        set PYTHON_CMD=py
        goto :python_found
    )
)

REM Python not found
color 0C
echo.
echo ❌ Python not found!
echo.
echo Please install Python 3.8 or higher:
echo   1. Download from: https://www.python.org/downloads/
echo   2. During installation, CHECK "Add Python to PATH"
echo   3. Restart this script after installation
echo.
goto :end

:python_found
echo ✓ Using: %PYTHON_CMD%
echo.

REM Check dependencies
echo [Checking dependencies...]
%PYTHON_CMD% -c "import psutil" 2>nul
if !errorLevel! neq 0 (
    echo ⚠️  psutil not found (will be auto-installed by script)
) else (
    echo ✓ psutil is installed
)

echo.
echo ========================================
echo Ready to optimize your system!
echo ========================================
echo.
echo Press any key to start or Ctrl+C to cancel...
pause >nul

echo.
echo [Starting optimization...]
echo Output will be saved to: %LOG_FILE%
echo.
echo ----------------------------------------
echo.

REM Run the script (with logging if tee is available)
where tee >nul 2>&1
if !errorLevel! == 0 (
    %PYTHON_CMD% "%SCRIPT_NAME%" 2>&1 | tee "%LOG_FILE%"
) else (
    REM Fallback without tee
    %PYTHON_CMD% "%SCRIPT_NAME%" 2>&1
)

set SCRIPT_EXIT_CODE=!errorLevel!

echo.
echo ----------------------------------------
echo.

REM Show results based on exit code
if !SCRIPT_EXIT_CODE! == 0 (
    color 0A
    echo ✅ SUCCESS - Optimization completed!
    echo.
    echo Your system has been optimized for gaming.
    echo Launch your game now for best performance!
) else (
    color 0E
    echo ⚠️  FAILED - Exit code: !SCRIPT_EXIT_CODE!
    echo.
    echo Possible issues:
    
    if !ADMIN! == 0 (
        echo   • Missing Administrator privileges ^(try "Run as administrator"^)
    )
    
    echo   • Python dependencies not installed
    echo   • Anti-virus blocking the script
    echo   • Script was cancelled by user
    echo.
    
    if exist "%LOG_FILE%" (
        echo Check %LOG_FILE% for details
    )
)

:end
echo.
echo ========================================
echo Press any key to exit...
pause >nul
exit /b !SCRIPT_EXIT_CODE!
