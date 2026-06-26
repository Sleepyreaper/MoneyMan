#!/usr/bin/env bash
# MoneyMan Interview — personalize your plan (macOS / Linux).
cd "$(dirname "$0")" || exit 1

echo
echo "  ==================================================="
echo "    MoneyMan Interview - let's personalize your plan"
echo "  ==================================================="
echo
echo "  I'll ask a few plain questions (home, rental, cars, savings,"
echo "  and the interest rate on each debt). Press Enter to skip any."
echo "  Everything stays on this computer."
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
"$PY" -m moneyman interview
echo
echo "  When you're done, open Run-MoneyMan.command to see your plan."
echo
read -rsn1 -p "  Press any key to close..."; echo
