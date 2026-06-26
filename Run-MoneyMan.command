#!/usr/bin/env bash
# MoneyMan — your private, offline finance analyst (macOS / Linux).
# Reads the statements in your MoneyMan folder and opens your plan.
cd "$(dirname "$0")" || exit 1

echo
echo "  ==================================================="
echo "    MoneyMan  -  your private, offline finance analyst"
echo "  ==================================================="
echo
echo "  Reading the statements in your MoneyMan folder..."
echo

PY=""
if command -v python3 >/dev/null 2>&1; then PY="python3"
elif command -v python >/dev/null 2>&1; then PY="python"; fi

if [ -z "$PY" ]; then
  echo "  --------------------------------------------------------"
  echo "   Python 3 was not found on this computer."
  echo "   MoneyMan needs Python 3 (a free, safe program)."
  echo "     1) Open  https://www.python.org/downloads/"
  echo "        (macOS: 'brew install python' also works)."
  echo "     2) Install Python 3, then open this file again."
  echo "  --------------------------------------------------------"
  echo
  read -rsn1 -p "  Press any key to close..."; echo
  exit 1
fi

export PYTHONUTF8=1
"$PY" -m moneyman "$@"
echo
echo "  Done. Your report should have opened in your web browser."
echo "  If it did not, open the newest file in your MoneyMan \"Reports\" folder."
echo
read -rsn1 -p "  Press any key to close..."; echo
