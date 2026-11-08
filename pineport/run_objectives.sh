#!/bin/bash
# Objective-function study -- PREREGISTRATION_SPX500_objectives.md (2026-09-27).
# All four arms run and ALL FOUR are reported. The result is the comparison,
# never a single arm.
set -e
cd "$(dirname "$0")"
PY=.venv/bin/python
COMMON="--csv spx500usd_oanda_m15.csv --tf M15
        --base configs/spx500_clean_base.json
        --start 2009-01-01 --end 2022-12-31
        --state-triggers --slippage 0.25 --seeds 4 --samples 200"
for OBJ in net calmar sharpe pf; do
  echo
  echo "################ ARM: objective=$OBJ ################"
  $PY train_staged.py $COMMON --objective "$OBJ"
done
echo
echo "All four arms complete. Compare with:  $PY compare_objectives.py"
