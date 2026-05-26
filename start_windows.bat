@echo off
SETLOCAL EnableDelayedExpansion
title Launching PerfInsight AI Portable...

echo [1/3] Verifying isolated local Python runtime...
set "WIN_PYTHON_DIR=%~dp0python_runtime\win64"

:: Automatically handle the env file cloning if the user missed Step 2
if not exist "%~dp0env" (
    if exist "%~dp0env.example" (
        echo Copying env.example template to live env configuration...
        copy "%~dp0env.example" "%~dp0env" >nul
    )
)

:: Download embedded python package automatically if not present in the bundle
if not exist "%WIN_PYTHON_DIR%\python.exe" (
    echo Local runtime not found. Bootstrapping minimal Windows build...
    mkdir "%WIN_PYTHON_DIR%"
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile '%WIN_PYTHON_DIR%\embed.zip'"
    powershell -Command "Expand-Archive -Path '%WIN_PYTHON_DIR%\embed.zip' -DestinationPath '%WIN_PYTHON_DIR%' -Force"
    del "%WIN_PYTHON_DIR%\embed.zip"
    
    :: Critical for embedded python to recognize local pip packages
    echo import sys >> "%WIN_PYTHON_DIR%\python311._pth"
    echo . >> "%WIN_PYTHON_DIR%\python311._pth"
    
    echo Installing pip package manager tool...
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%WIN_PYTHON_DIR%\get-pip.py'"
    "%WIN_PYTHON_DIR%\python.exe" "%WIN_PYTHON_DIR%\get-pip.py" --no-warn-script-location
    del "%WIN_PYTHON_DIR%\get-pip.py"
)

echo [2/3] Checking system requirement dependencies...
"%WIN_PYTHON_DIR%\Scripts\pip.exe" install -r "%~dp0requirements.txt" --no-warn-script-location --quiet

echo [3/3] Initializing PerfInsight AI Dashboard...
cls
"%WIN_PYTHON_DIR%\Scripts\streamlit.exe" run "%~dp0app.py"
pause