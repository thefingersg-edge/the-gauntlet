#!/bin/bash
# Is tolerance 1 a sweet spot, or did its search get a lucky draw?
#
# The tolerance study gave tol1 the only WIN: reproducibility 62.7%, OOS Sharpe
# 0.93 and 1.20. But tol2 and tol3 were also re-trained and came back WORSE on
# the 2006-2012 window (0.60, 0.42) despite reaching higher reproducibility at
# fixed parameters -- so the picture is not smooth, and search_robustness.py
# already showed that on this strategy the SEED moves out-of-sample results
# more than the search METHOD does (sd 0.541 vs 0.377).
#
# Everything here is identical to the tol1 run except the random seed.
#
# PRE-REGISTERED:
#   all 4 seeds clear repro >= 60% AND both OOS Sharpe >= 0.8
#       -> tolerance 1 is real and reproducible; adopt it
#   results scatter across the bars
#       -> the single WIN was a draw, and the trade-off table (reproducibility
#          bought at the cost of the 2006-2012 Sharpe) is the honest summary
#
# ~2 hours per seed, ~8 hours total. Checkpointed; seed is in the tag.
set -e
cd "$(dirname "$0")"
PY=.venv/bin/python
for S in 0 1 2 3; do
  echo "=== tolerance 1, seed $S ==="
  $PY train_tf.py --csv xauusd_oanda_m15.csv --tf M15 \
      --base configs/gold_15m_live_current.json \
      --ladder-mode dollars --trigger-tolerance 1 --seed $S \
      --start 2013-01-01 --end 2023-12-31 \
      --objective calmar --filter-objective calmar \
      --slippage 0.25 --samples 400 --fresh
done
echo; echo "Compare with:  $PY compare_tolerance.py"
