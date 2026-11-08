#!/usr/bin/env bash
#
# Full 15-minute pull for the silver mean-reversion strategy.
#
#   ./pull_15m.sh                 # verify all three, then pull 2016-onward
#   ./pull_15m.sh --verify-only   # just the cheap sanity gate, no long pull
#
# Resumable: every day-file is cached (successes AND 404 weekends), so if this
# dies at hour two, re-run the identical command and it picks up where it left
# off. Failed days are deliberately NOT cached, so retries only re-hit those.
#
set -uo pipefail

cd "$(dirname "$0")" || exit 1

PY="../.venv/bin/python"                 # NOT system python -- pandas lives here
[ -x "$PY" ] || PY=".venv/bin/python"
[ -x "$PY" ] || { echo "!! no venv python found. Run setup_check.py first."; exit 1; }

START=2016
TF=15m
OUT=../data_dukascopy   # OANDA owns ../data now; kept separate for --cross-check
INSTRUMENTS=(XAGUSD XAUUSD EURUSD)
VERIFY_YEAR=2024
VERIFY_MONTH=6

mkdir -p "$OUT" logs

echo "================================================================"
"$PY" dukascopy_intraday.py --version || exit 1
echo "================================================================"

# ---------------------------------------------------------------------------
# GATE 1: offline self-test. Costs nothing, catches a stale/half-copied file.
# ---------------------------------------------------------------------------
echo
echo ">> offline self-test"
if ! "$PY" dukascopy_intraday.py --self-test > logs/selftest.log 2>&1; then
    echo "!! self-test FAILED -- see logs/selftest.log. Not pulling."
    exit 1
fi
echo "   passed"

# ---------------------------------------------------------------------------
# GATE 2: verify the day-index convention PER INSTRUMENT.
#
# It was confirmed one-indexed on XAGUSD 2024-06 by exact price match. That is
# evidence about XAGUSD, not proof about XAUUSD or EURUSD. ~30 requests each to
# find out, against ~2.8 hours of silently day-shifted data if it differs.
# ---------------------------------------------------------------------------
echo
echo ">> verifying day-index convention on each instrument ($VERIFY_YEAR-$(printf %02d $VERIFY_MONTH))"
for INS in "${INSTRUMENTS[@]}"; do
    printf "   %-8s " "$INS"
    if "$PY" dukascopy_intraday.py --verify --instrument "$INS" \
            --year "$VERIFY_YEAR" --month "$VERIFY_MONTH" \
            > "logs/verify_${INS}.log" 2>&1; then
        echo "OK   $(grep -m1 'CONFIRMED' "logs/verify_${INS}.log" | sed 's/^ *//')"
    else
        echo "FAILED"
        echo
        echo "!! $INS did not reproduce its hourly bars. STOPPING."
        echo "!! Read logs/verify_${INS}.log -- check the lag scan first:"
        echo "!!   exact match at a non-zero shift = index bug, fixable"
        echo "!!   no exact match at any shift     = something else is wrong"
        exit 1
    fi
done

if [ "${1:-}" = "--verify-only" ]; then
    echo
    echo "verify-only: stopping before the long pull."
    exit 0
fi

# ---------------------------------------------------------------------------
# THE PULL
# ---------------------------------------------------------------------------
echo
echo ">> pulling $TF from $START -- roughly 2.8 hours cold, near-instant cached"
echo "   weekends 404 and are cached as empty; that is expected, not an error"
echo

for INS in "${INSTRUMENTS[@]}"; do
    LOWER=$(echo "$INS" | tr '[:upper:]' '[:lower:]')
    TARGET="$OUT/${LOWER}_${TF}.csv"
    echo "---- $INS -> $TARGET"
    if ! "$PY" dukascopy_intraday.py \
            --instrument "$INS" --tf "$TF" --start "$START" \
            --out "$TARGET" 2>&1 | tee "logs/pull_${INS}.log" | \
            grep -E "bars|wrote|FAILED|ok [0-9]"; then
        echo "!! $INS pull reported a problem -- see logs/pull_${INS}.log"
    fi
    echo
done

# ---------------------------------------------------------------------------
# Post-pull sanity: the three files must actually overlap in time, or the
# rolling XAG~XAU regression silently runs on almost nothing.
# ---------------------------------------------------------------------------
echo ">> coverage check"
"$PY" - <<'PYEOF'
import os, pandas as pd
out, tf = "../data_dukascopy", "15m"
frames = {}
for ins in ("xagusd", "xauusd", "eurusd"):
    p = os.path.join(out, f"{ins}_{tf}.csv")
    if not os.path.exists(p):
        print(f"   {ins:8} MISSING"); continue
    d = pd.read_csv(p, index_col=0, parse_dates=True)
    frames[ins] = d
    print(f"   {ins:8} {len(d):>9,} bars  {d.index.min()} -> {d.index.max()}")
if len(frames) == 3:
    common = frames["xagusd"].index
    for f in frames.values():
        common = common.intersection(f.index)
    n = len(frames["xagusd"])
    print(f"   common   {len(common):>9,} bars  ({len(common)/n:.1%} of XAGUSD)")
    if len(common) < 0.8 * n:
        print("   !! low overlap -- check for a gap or a failed instrument")
PYEOF

echo
echo "next:  $PY oanda_intraday.py --cross-check"
