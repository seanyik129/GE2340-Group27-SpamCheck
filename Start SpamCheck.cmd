@echo off
setlocal
where npm.cmd >nul 2>&1
if errorlevel 1 (
    echo Install Node.js and follow the setup steps in README.md.
    pause
    exit /b 1
)
call npm.cmd --prefix "%~dp0electron" start %*
if errorlevel 1 (
    echo Follow the desktop setup steps in README.md before starting SpamCheck.
    pause
    exit /b 1
)
