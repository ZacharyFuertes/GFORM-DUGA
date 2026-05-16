@echo off
REM Google Form Bot - Windows batch commands

if "%1"=="install" (
    echo Installing dependencies...
    py -m pip install -r requirements.txt
    echo Done!
    goto end
)

if "%1"=="setup" (
    echo Running configuration setup...
    py setup_config.py
    goto end
)

if "%1"=="test" (
    echo Running single submission test...
    py gform_bot.py --count 1
    goto end
)

if "%1"=="run" (
    if "%2"=="" (
        echo Usage: run.bat run [count]
        echo Example: run.bat run 100
        goto end
    )
    echo Running %2 submissions...
    py gform_bot.py --count %2
    goto end
)

if "%1"=="report" (
    echo Generating report...
    py log_analyzer.py report
    goto end
)

if "%1"=="gui" (
    echo Launching GFORM DUGA GUI...
    py gui_launcher.py
    goto end
)

if "%1"=="log" (
    echo Showing last 20 log lines...
    py log_analyzer.py tail 20
    goto end
)

if "%1"=="help" (
    goto help
)

if "%1"=="" (
    goto help
)

echo Unknown command: %1

:help
echo.
echo Google Form Bot - Command Help
echo ==============================
echo.
echo Commands:
echo   install     Install Python dependencies
echo   setup       Interactive configuration setup
echo   test        Run single submission test
echo   gui         Launch the browser-based GUI
echo   run [N]     Run N submissions
echo   report      Show submission report
echo   log         Show last 20 log lines
echo   help        Show this help message
echo.
echo Examples:
echo   run.bat install
echo   run.bat setup
echo   run.bat test
echo   run.bat run 100
echo   run.bat report
echo.

:end
