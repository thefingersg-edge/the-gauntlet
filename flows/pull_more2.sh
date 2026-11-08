#!/bin/bash
# pull_more2.sh -- the two amended Step 0 pulls (FLOWS-9 A1, FLOWS-13 A1). RUN ON YOUR MAC.
set -u; cd "$(dirname "$0")" || exit 1
PY=python3; [ -x ../pineport/.venv/bin/python ] && PY=../pineport/.venv/bin/python
"$PY" fetch_earnings.py --self-test >/dev/null && "$PY" fetch_fxvalue_a1.py --self-test >/dev/null || { echo "STOP: self-test"; exit 1; }
echo "=== FLOWS-9 A1: earnings universe + dates, rebuilt with the screen ==="
"$PY" fetch_earnings.py || echo "  WARNING: fetch_earnings"
echo "=== FLOWS-13 A1: BIS consumer prices + FRED EXGEUS ==="
"$PY" fetch_fxvalue_a1.py || echo "  WARNING: fetch_fxvalue_a1"
echo "Done. Nothing here computed a return. Tell Claude."
