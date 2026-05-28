#!/bin/bash
clear
echo "=================================================="
echo " Initializing PerfInsight AI Portable Instance"
echo "=================================================="

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENV_DIR="$SCRIPT_DIR/python_runtime/mac_linux_env"

# 1. Determine local host interpreter variant
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python interpreter wrapper was not detected on this machine."
    echo "Please install Python via Homebrew (brew install python) or official installers."
    exit 1
fi

# 2. Build isolated virtual sandbox environment
if [ ! -d "$VENV_DIR" ]; then
    echo "[1/3] Constructing local sandboxed virtual workspace..."
    $PYTHON_CMD -m venv "$VENV_DIR"
fi

echo "[2/3] Verifying runtime dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" --quiet

echo "[3/3] Booting Streamlit Engine UI..."
"$VENV_DIR/bin/streamlit" run "$SCRIPT_DIR/app.py"