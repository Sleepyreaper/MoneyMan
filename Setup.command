#!/usr/bin/env bash
# MoneyMan one-time Setup (macOS / Linux).
# Installs a small OFFLINE library that lets MoneyMan read PDF statements.
# It reads PDFs on your computer and sends nothing anywhere.
cd "$(dirname "$0")" || exit 1

echo
echo "  ==================================================="
echo "    MoneyMan one-time Setup"
echo "  ==================================================="
echo

PY=""
if command -v python3 >/dev/null 2>&1; then PY="python3"
elif command -v python >/dev/null 2>&1; then PY="python"; fi

if [ -z "$PY" ]; then
  echo "  Python 3 was not found."
  echo "    1) Install Python 3 from https://www.python.org/downloads/"
  echo "       (macOS: you can also use 'brew install python')."
  echo "    2) Run this Setup again."
  echo
  read -rsn1 -p "  Press any key to close..."; echo
  exit 1
fi

"$PY" -m pip install --upgrade pip
"$PY" -m pip install pypdf pdfplumber
echo
echo "  Setup complete. MoneyMan can now read PDF statements."
echo "  Next: open Run-MoneyMan.command (or Try-Demo.command to see a demo)."
echo
read -rsn1 -p "  Press any key to close..."; echo
