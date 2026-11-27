@echo off
setlocal EnableDelayedExpansion
title X (Twitter) Multi-Account Automation Tool

cd /d "%~dp0"

echo ======================================================================
echo              X (TWITTER) MULTI-ACCOUNT ENGAGEMENT SUITE
echo ======================================================================
echo.

if not exist "tokens.txt" (
    type nul > "tokens.txt"
)

set count=0
for /f "usebackq delims=" %%a in ("tokens.txt") do (
    set /a count+=1
)

echo Saved Tokens in tokens.txt: %count%
echo.

if %count%==0 (
    echo [!] WARNING: Your tokens.txt is empty!
    echo     Please paste your auth_tokens into tokens.txt first.
    echo.
    pause
    exit /b
)

python -u "%~dp0space_listener_browser_bot.py"

echo.
echo [*] Process completed.
pause
