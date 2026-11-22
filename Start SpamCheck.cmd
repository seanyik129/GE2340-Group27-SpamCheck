@echo off
setlocal
set "spamcheck_app=%~dp0electron"
set "spamcheck_electron=%spamcheck_app%\node_modules\electron\dist\electron.exe"
if not exist "%spamcheck_electron%" (
    echo Install Electron using the setup instructions in electron\README.md.
    pause
    exit /b 1
)
start "" "%spamcheck_electron%" "%spamcheck_app%"
