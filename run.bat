@echo off
REM GFORM DUGA - Windows batch commands
setlocal

if "%~1"=="install" goto install
if "%~1"=="gui"     goto gui
if "%~1"=="bot"     goto bot
if "%~1"=="help"    goto help
if "%~1"==""        goto help

echo Unknown command: %~1
goto help

:install
echo Installing dependencies...
py -m pip install -r requirements.txt
goto end

:gui
echo Launching GFORM DUGA GUI...
py gui_launcher.py
goto end

:bot
if "%~2"=="" (
    echo Usage: run.bat bot ^<form-url^> [count] [config.json]
    echo Example: run.bat bot "https://docs.google.com/forms/d/e/XXX/viewform" 10
    goto end
)
set "COUNT=%~3"
if "%COUNT%"=="" set "COUNT=1"
set "CFG=%~4"
echo Running %COUNT% submission^(s^)...
if "%CFG%"=="" (
    py gform_bot_playwright.py --url "%~2" --count %COUNT%
) else (
    py gform_bot_playwright.py --url "%~2" --count %COUNT% --config "%CFG%"
)
goto end

:help
echo.
echo GFORM DUGA - Command Help
echo ========================
echo.
echo Commands:
echo   install                Install Python dependencies
echo   gui                    Launch the Tkinter GUI
echo   bot ^<url^> [count] [cfg]  Run N submissions from the CLI
echo   help                   Show this help
echo.
echo Examples:
echo   run.bat install
echo   run.bat gui
echo   run.bat bot "https://docs.google.com/forms/d/e/XXX/viewform" 10
echo.
goto end

:end
endlocal
