#!/usr/bin/env bash
#
# 15-minute data pull for the silver mean-reversion strategy, from OANDA.
#
#   ./pull_15m.sh --stage1          # auth, history depth, mid-vs-bid  (~3 min)
#   ./pull_15m.sh --price M         # the real pull                    (~3 min)
#   ./pull_15m.sh --price B
#
# Two stages on purpose. Stage 1 ends with a question only you can answer --
# which price side matches your TradingView chart -- and picking that wrong is
# a small, permanent, silent error in every backtested fill. Three minutes of
# looking beats discovering it after a month of results.
#
# The Dukascopy path still exists as ./pull_15m_dukascopy.sh and writes to
# ../data_dukascopy, so `oanda_intraday.py --cross-check` can diff the two.
# Two independent feeds is how you tell a signal from a feed artefact.
#
set -uo pipefail
cd "$(dirname "$0")" || exit 1

PY="../.venv/bin/python"
[ -x "$PY" ] || PY=".venv/bin/python"
[ -x "$PY" ] || { echo "!! no venv python found. Run setup_check.py first."; exit 1; }

START=2016-01-01
DATA=../data
mkdir -p "$DATA" logs

echo "================================================================"
"$PY" oanda_intraday.py --version || exit 1
echo "================================================================"

# GATE: offline self-tests. Free, and catches a stale or half-copied file.
echo
echo ">> offline self-tests"
for M in fetch_oanda oanda_intraday; do
    printf "   %-16s " "$M"
    if "$PY" "$M.py" --self-test > "logs/selftest_${M}.log" 2>&1; then
        echo "passed"
    else
        echo "FAILED -- see logs/selftest_${M}.log"; exit 1
    fi
done

# ---------------------------------------------------------------------------
if [ "${1:-}" = "--stage1" ]; then
    echo
    echo ">> auth check"
    "$PY" oanda_intraday.py --check || exit 1

    echo
    echo ">> M15 history depth"
    "$PY" oanda_intraday.py --probe --start "$START" || exit 1

    echo
    echo ">> mid vs bid on silver"
    "$PY" oanda_intraday.py --sides --start "$START" \
        --data-dir "$DATA" 2>&1 | tee logs/sides.log

    echo
    echo "================================================================"
    echo "STAGE 1 DONE. Open XAGUSD on TradingView with the OANDA source,"
    echo "pick any 15m bar, and see which of these reproduces its close:"
    echo "    $DATA/xagusd_mid_15m.csv"
    echo "    $DATA/xagusd_bid_15m.csv"
    echo "Then run:  ./pull_15m.sh --price M     (or --price B)"
    exit 0
fi

# ---------------------------------------------------------------------------
PRICE="M"
if [ "${1:-}" = "--price" ] && [ -n "${2:-}" ]; then
    PRICE="$2"
elif [ -n "${1:-}" ]; then
    echo "usage: $0 [--stage1 | --price M|B|A]"; exit 1
else
    echo
    echo "!! No --price given, defaulting to mid (M)."
    echo "!! If you have not run --stage1 yet, do that first."
    sleep 3
fi

echo
echo ">> pulling XAG_USD, XAU_USD, EUR_USD at M15 (price $PRICE) from $START"
echo "   ~55 paginated requests per instrument; this takes minutes, not hours"
echo
"$PY" oanda_intraday.py --pull --price "$PRICE" --start "$START" \
    --data-dir "$DATA" 2>&1 | tee logs/pull_oanda.log
STATUS=${PIPESTATUS[0]}

if [ "$STATUS" -ne 0 ]; then
    echo
    echo "!! pull reported a problem -- see logs/pull_oanda.log"
    exit "$STATUS"
fi

echo
echo "================================================================"
echo "next:"
echo "  $PY silver_mr.py --data $DATA"
echo "  ./pull_15m_dukascopy.sh && $PY oanda_intraday.py --cross-check"
