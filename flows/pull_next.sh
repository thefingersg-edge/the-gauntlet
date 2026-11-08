#!/bin/bash
# pull_next.sh -- Step 0 data for FLOWS-4, -5 and -6. RUN ON YOUR MAC:
#
#     bash ~/RStudio/Claude/flows/pull_next.sh
#
# Needs the OANDA token where pull_m1 finds it ($OANDA_API_TOKEN or
# ~/.oanda_token) for the natgas pull only. Reads no returns and computes no
# statistic. Safe to re-run: the natgas pull resumes, and a table that already
# exists is NOT rebuilt (it may already be frozen) unless REBUILD=1.
set -u
cd "$(dirname "$0")" || exit 1
S=../fastbot/scripts
DATA="$PWD/data"
step(){ printf '\n=== %s ===\n' "$*"; }
stop(){ printf '\nSTOP: %s\n' "$*"; exit 1; }
PY=python3
for c in ../pineport/.venv/bin/python ../silver15/scripts/.venv/bin/python; do
  if [ -x "$c" ] && "$c" -c "import pandas" 2>/dev/null; then PY="$c"; break; fi
done
HAVE_PANDAS=0; "$PY" -c "import pandas" 2>/dev/null && HAVE_PANDAS=1
echo "python: $PY  (pandas: $([ $HAVE_PANDAS = 1 ] && echo yes || echo no))"

step "0. offline self-tests (no network, no prices)"
"$PY" fetch_eia_calendar.py --self-test >/dev/null || stop "fetch_eia_calendar self-test"
"$PY" fetch_announce.py     --self-test >/dev/null || stop "fetch_announce self-test"
"$PY" fetch_ecb.py          --self-test >/dev/null || stop "fetch_ecb self-test"
echo "all pass"

build(){  # build TABLE with SCRIPT unless it exists (frozen) and REBUILD != 1
  if [ -f "$DATA/$1" ] && [ "${REBUILD:-0}" != "1" ]; then
    echo "  $1 exists -- NOT rebuilt (set REBUILD=1 only if it has not been pinned)"
  else
    "$PY" "$2" || stop "$2"
  fi
}
step "1. FLOWS-6 EIA calendar (offline; already frozen at 9f208aac...)"
build eia_events.csv fetch_eia_calendar.py
step "2. FLOWS-4 announcement table (ALFRED, GDP only)"
build announce_events.csv fetch_announce.py
step "3. FLOWS-5 ECB decision table (ecb.europa.eu)"
build ecb_events.csv fetch_ecb.py

step "4. OANDA auth (1 request)"
"$PY" "$S/pull_m1.py" --check || stop "OANDA auth -- is the token in ~/.oanda_token?"
step "5. NATGAS_USD M15 bid + ask, 2005 onward -> flows/data (resumable)"
"$PY" "$S/pull_m1.py" --pull --granularity M15 --sides B,A --start 2005-01-01 \
        --instruments NATGAS_USD --data-dir "$DATA" || stop "natgas pull -- re-run to resume"
if [ $HAVE_PANDAS = 1 ]; then
  "$PY" "$S/pull_m1.py" --verify --granularity M15 --instruments NATGAS_USD \
          --data-dir "$DATA" || stop "natgas verify"
else
  echo "  verify SKIPPED (no pandas); natgas.py --check-inputs re-checks the grid"
fi

step "summary"
( cd "$DATA" && for f in eia_events.csv announce_events.csv ecb_events.csv natgasusd_bid_15m.csv natgasusd_ask_15m.csv; do
    [ -f "$f" ] && printf "  %-28s %9s rows  %s\n" "$f" "$(($(wc -l < "$f")-1))" "$(shasum -a 256 "$f" | cut -c1-16)"
  done )
echo
echo "Nothing here has computed a return. Tell Claude it has finished:"
echo "the two new tables get pinned and committed BEFORE any harness runs."
