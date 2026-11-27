@echo off
setlocal EnableDelayedExpansion
title Telegram Remote Bot Controller

cd /d "%~dp0"

echo ======================================================================
echo              TELEGRAM REMOTE CONTROLLER FOR X SUITE
echo ======================================================================
echo.

python -u "%~dp0telegram_bot.py"

echo.
pause
