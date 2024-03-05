@echo off
:: BatchGotAdmin
:-------------------------------------
REM  --> Check for permissions
>nul 2>&1 "%SYSTEMROOT%\system32\icacls.exe" "%SYSTEMROOT%\system32\config\system"

REM --> If error flag set, we do not have admin.
if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    timeout /t 2 /nobreak >nul
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"

    "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    if exist "%temp%\getadmin.vbs" ( del "%temp%\getadmin.vbs" )
    pushd "%CD%"
    CD /D "%~dp0"
:--------------------------------------

:: Check if colorama is installed
pip show colorama >nul 2>&1
if '%errorlevel%' NEQ '0' (
    echo Installing colorama...
    pip install colorama
    if '%errorlevel%' NEQ '0' (
        echo Failed to install colorama. Please install it manually.
        exit /B
    )
)

:: Run the Python script
python ExeConverter.py
if '%errorlevel%' NEQ '0' (
    echo Failed to run ExeConverter.py. Please check the script for errors.
    exit /B
)

pause
