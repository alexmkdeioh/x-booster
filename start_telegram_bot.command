#!/bin/bash
cd "$(dirname "$0")"
echo -ne "\033]0;Telegram Remote Bot Controller\007"
echo "======================================================================"
echo "            TELEGRAM REMOTE CONTROLLER FOR X SUITE"
echo "======================================================================"
echo ""

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

$PYTHON_CMD -u "telegram_bot.py"

read -p "Press Enter to exit..."
