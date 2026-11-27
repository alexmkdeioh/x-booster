#!/bin/bash

# Move to current directory
cd "$(dirname "$0")"

# Set window title
echo -ne "\033]0;X (Twitter) Multi-Account Automation Tool\007"

echo "======================================================================"
echo "            X (TWITTER) MULTI-ACCOUNT ENGAGEMENT SUITE"
echo "======================================================================"
echo ""

# Ensure tokens.txt exists
if [ ! -f "tokens.txt" ]; then
    touch "tokens.txt"
fi

# Count valid lines in tokens.txt
count=$(grep -v '^[[:space:]]*#' "tokens.txt" | grep -v '^[[:space:]]*$' | wc -l | tr -d ' ')

echo "Saved Tokens in tokens.txt: $count"
echo ""

if [ "$count" -eq 0 ]; then
    echo "[!] WARNING: Your tokens.txt is empty!"
    echo "    Please paste your auth_tokens into tokens.txt first."
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# Determine python command
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    if command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "[!] Python is not installed. Please install Python 3."
        read -p "Press Enter to exit..."
        exit 1
    fi
fi

# Check if playwright is installed, if not, auto-install
if ! $PYTHON_CMD -c "import playwright" &>/dev/null; then
    echo "[*] First time run detected: Installing browser engine requirements..."
    $PYTHON_CMD -m pip install --upgrade playwright
    $PYTHON_CMD -m playwright install chromium
    echo "[✓] Browser engine installed successfully!"
    echo ""
fi

$PYTHON_CMD -u "space_listener_browser_bot.py"

echo ""
echo "[*] Script finished."
read -p "Press Enter to close this window..."
