#!/usr/bin/env bash
# MoneyMan (editable) — opens in your web browser (macOS / Linux).
# Runs a tiny web app ON THIS COMPUTER only (127.0.0.1). Nothing is sent anywhere.
cd "$(dirname "$0")" || exit 1

echo
echo "  ==================================================="
echo "    MoneyMan (editable) - opens in your web browser"
echo "  ==================================================="
echo
echo "  This runs MoneyMan as a small web app ON THIS COMPUTER only."
echo "  You can type in your home value, debt interest rates, etc.,"
echo "  click Save, and it remembers - nothing is sent anywhere."
echo
echo "  Leave this window open while you use it."
echo "  Press Ctrl+C when you're done."
echo

PY=""
if command -v python3 >/dev/null 2>&1; then PY="python3"
elif command -v python >/dev/null 2>&1; then PY="python"; fi

if [ -z "$PY" ]; then
  echo "  Python 3 was not found. Install it from https://www.python.org/downloads/"
  echo "  (macOS: 'brew install python'), then open this file again."
  echo
  read -rsn1 -p "  Press any key to close..."; echo
  exit 1
fi

export PYTHONUTF8=1
"$PY" -m moneyman serve
echo
read -rsn1 -p "  Press any key to close..."; echo
