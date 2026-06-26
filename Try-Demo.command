#!/usr/bin/env bash
# MoneyMan DEMO — using realistic fake data (macOS / Linux).
# Creates pretend statements (no real data needed) and shows a full report.
cd "$(dirname "$0")" || exit 1

echo
echo "  ==================================================="
echo "    MoneyMan DEMO  -  using realistic fake data"
echo "  ==================================================="
echo
echo "  This creates pretend bank statements (no real data needed)"
echo "  and shows you what your report will look like."
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
"$PY" -m moneyman --demo
echo
echo "  Done. The demo report should have opened in your browser."
echo "  The fake data lives in a separate \"MoneyMan-Demo\" folder so it"
echo "  never mixes with your real statements."
echo
read -rsn1 -p "  Press any key to close..."; echo
