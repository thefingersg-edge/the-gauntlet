#!/bin/bash
# SPX500 15m staged training -- the run registered in
# PREREGISTRATION_SPX500_15m.md (2026-09-21).
#
# A script rather than a pasted command: the first attempt was pasted with
# backslash continuations, the continuations were lost, and the shell
# backgrounded a bare `> spx_clean.log 2>&1` -- a 0-byte log, instant "Done",
# and nothing trained. One word to invoke is harder to get wrong.
#
#   bash run_spx500.sh            # all six stages, ~3-4 hours
#   bash run_spx500.sh sma        # one stage only
#   bash run_spx500.sh --report   # what has been accepted so far
set -e
cd "$(dirname "$0")"
PY=.venv/bin/python

COMMON="--csv spx500usd_oanda_m15.csv --tf M15
        --base configs/spx500_clean_base.json
        --start 2009-01-01 --end 2022-12-31
        --state-triggers --objective calmar
        --slippage 0.25 --seeds 4 --samples 200"

if [ "$1" = "--report" ]; then
  exec $PY train_staged.py $COMMON --report
elif [ -n "$1" ]; then
  exec $PY train_staged.py $COMMON --only "$1"
else
  exec $PY train_staged.py $COMMON
fi
