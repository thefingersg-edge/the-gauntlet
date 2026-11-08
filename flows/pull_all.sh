#!/bin/bash
# pull_all.sh -- Step 0 data for FLOWS-1, -2 and -3. RUN ON YOUR MAC:
#
#     bash ~/RStudio/Claude/flows/pull_all.sh
#
# Needs your OANDA token where fetch_oanda.load_token() finds it
# ($OANDA_API_TOKEN or ~/.oanda_token). A FRED key is optional.
# Reads no returns and computes no statistic -- it only fetches and records.
# Safe to re-run: the OANDA pull resumes from what is already on disk.
# Writes only under flows/data/. Never touches fastbot/data/v24, which
# forward_tick.sh appends to.
set -u
cd "$(dirname "$0")" || exit 1
S=../fastbot/scripts
BONDS=USB10Y_USD,DE10YB_EUR,USB30Y_USD
DATA="$PWD/data"
mkdir -p "$DATA"
step(){ printf '\n=== %s ===\n' "$*"; }

# Interpreter. The Mac's plain python3 has no pandas; the pull itself does not
# need it (forward_tick.sh runs pull_m1.py --pull under plain python3), but
# pull_m1's self-test does. Prefer the project's own macOS venv when it can
# import pandas; otherwise run everything else and skip only that check.
PY=python3
for c in ../pineport/.venv/bin/python ../silver15/scripts/.venv/bin/python; do
  if [ -x "$c" ] && "$c" -c "import pandas" 2>/dev/null; then PY="$c"; break; fi
done
HAVE_PANDAS=0; "$PY" -c "import pandas" 2>/dev/null && HAVE_PANDAS=1
echo "python: $PY  (pandas: $([ $HAVE_PANDAS = 1 ] && echo yes || echo no))"
stop(){ printf '\nSTOP: %s\n' "$*"; exit 1; }

step "0. offline self-tests (no network)"
"$PY" refunding_events.py --self-test >/dev/null || stop "refunding_events self-test"
"$PY" fetch_financing.py  --self-test >/dev/null || stop "fetch_financing self-test"
"$PY" fetch_fred.py       --self-test >/dev/null || stop "fetch_fred self-test"
if [ $HAVE_PANDAS = 1 ]; then
  "$PY" "$S/pull_m1.py" --self-test >/dev/null || stop "pull_m1 self-test"
else
  echo "  pull_m1 self-test SKIPPED: needs pandas, which this python lacks"
fi
echo "all pass"

step "1. OANDA authentication (1 request)"
"$PY" "$S/pull_m1.py" --check || stop "OANDA auth -- is the token in ~/.oanda_token?"

step "2. bond CFDs, M15 bid + ask, 2005 onward -> flows/data  (~5 min, resumable)"
"$PY" "$S/pull_m1.py" --pull --granularity M15 --sides B,A --start 2005-01-01 \
        --instruments "$BONDS" --data-dir "$DATA" || stop "bond pull -- re-run to resume"
if [ $HAVE_PANDAS = 1 ]; then
  "$PY" "$S/pull_m1.py" --verify --granularity M15 --instruments "$BONDS" \
          --data-dir "$DATA" || stop "bond verify"
else
  echo "  verify SKIPPED: needs pandas. The harnesses re-check sorting, duplicates"
  echo "  and the 15-minute grid before computing anything."
fi

step "3. financing terms per instrument"
"$PY" fetch_financing.py || stop "financing -- SPX500 or USB10Y not returned"

step "4. FRED rate series"
"$PY" fetch_fred.py || stop "FRED"

step "5. refunding event table (reads no prices)"
# Guard added 2026-09-26: FLOWS-2 ran against the FROZEN table (sha 57be5dea...,
# 2015-Q3 dated by hand). Rebuilding it would silently overwrite that hand fix,
# which is exactly what a re-run of this script did at 20:15 that day. The table
# is only rebuilt if it is missing, or if REBUILD_REFUNDING=1 is set on purpose.
if [ -f "$DATA/refunding_events.csv" ] && [ "${REBUILD_REFUNDING:-0}" != "1" ]; then
  echo "  refunding_events.csv exists and is frozen (FLOWS-2 has run) -- NOT rebuilt."
  rc=0
else
"$PY" refunding_events.py; rc=$?
fi
if [ $rc -eq 2 ]; then
  echo "  Some quarters need a hand check (listed above) before FLOWS-2 can run."
elif [ $rc -ne 0 ]; then
  stop "refunding table"
fi

step "summary"
( cd "$DATA" && for f in *.csv *.json; do
    [ -f "$f" ] && printf "  %-40s %9s rows  %s\n" "$f" "$(($(wc -l < "$f")-1))" "$(shasum -a 256 "$f" 2>/dev/null | cut -c1-16 || sha256sum "$f" | cut -c1-16)"
  done )
echo
echo "Nothing here has computed a return. Next: commit flows/data's metadata"
echo "(the price CSVs stay gitignored) and write the harnesses."
