@echo off
:: BatchGotAdmin
:-------------------------------------
REM  --> Check for permissions
>nul 2>&1 "%SYSTEMROOT%\system32\icacls.exe" "%SYSTEMROOT%\system32\config\system"

REM --> If error flag set, we do not have admin
if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    timeout /t 2 /nobreak >nul
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    setlocal
    set "args=%*"
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "%args%", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    if exist "%temp%\getadmin.vbs" ( del "%temp%\getadmin.vbs" )
    pushd "%CD%"
    CD /D "%~dp0"
:--------------------------------------

:: Check if virtual environment exists
if not exist "%CD%\.venv\Scripts\activate.bat" (
    echo Virtual environment not found
    goto RunScript
)

:: Activate the virtual environment
call "%CD%\.venv\Scripts\activate.bat"

:: Check if colorama is installed
python -c "import colorama" >nul 2>&1
if '%errorlevel%' NEQ '0' (
    goto InstallColorama
)

:: Check if pywin32 is installed
python -c "import win32api" >nul 2>&1
if '%errorlevel%' NEQ '0' (
    goto InstallPywin32
)

goto RunScript

:InstallColorama
echo Installing colorama...
pip install colorama
if '%errorlevel%' NEQ '0' (
    echo Failed to install colorama. Please install it manually
    pause
    exit /B
)
echo.

:InstallPywin32
echo Installing pywin32...
pip install pywin32
if '%errorlevel%' NEQ '0' (
    echo Failed to install pywin32. Please install it manually
    pause
    exit /B
)
echo.

:RunScript
python ExeConverter.py %*
if '%errorlevel%' NEQ '0' (
    echo Failed to run ExeConverter.py. Please check the script for errors
    pause
    exit /B
)
pause
