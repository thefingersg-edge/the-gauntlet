#!/bin/bash
# Does relaxing the trigger COINCIDENCE requirement buy reproducibility that is
# worth what it costs -- once each tolerance is given its own parameters?
#
# WHY THIS SUPERSEDES THE FIRST SWEEP
#
# The first attempt applied tolerance 1/2/3 to parameters hand-tuned at
# tolerance 0 and reported a clean monotonic decline (Sharpe 1.32 -> 0.88 as
# reproducibility rose 47% -> 64%). That comparison was invalid. At tolerance 3
# entries fire 2.3x as often, so the selective parameters -- RSI level, band
# width, stop distance -- should all be tighter. Tuned settings versus untuned
# settings measures the mismatch, not the idea. Same error as the stop_scale
# box that excluded the only stops known to work.
#
# So: train each tolerance separately, on identical data, then compare.
#
# WHAT IS HELD CONSTANT
#   data, training window, objective, sample budget, base config, slippage
# WHAT VARIES
#   trigger_tolerance only
#
# PRE-REGISTERED, BEFORE RUNNING
#
#   A tolerance level WINS if, after its own training, it clears BOTH:
#       cross-feed trade reproducibility >= 60%   (the gate that failed at 46.7%)
#       out-of-sample Sharpe >= 0.8 on BOTH unseen windows
#
#   If no level clears both, the honest conclusion is that this strategy's
#   edge and its fragility are the same property, and it cannot be made
#   reproducible without ceasing to work. That is a real finding, not a
#   failure to search hard enough.
#
# Train 2013-2023. Unseen either side: 2006-2012 and 2024-2026.
# ~2 hours per tolerance on 7 workers, ~8 hours total. Checkpointed.
#
#   bash run_tolerance_study.sh
set -e
cd "$(dirname "$0")"
PY=.venv/bin/python

for TOL in 0 1 2 3; do
  echo "=== gold 15m, trigger_tolerance = $TOL ==="
  $PY train_tf.py --csv xauusd_oanda_m15.csv --tf M15 \
      --base configs/gold_15m_live_current.json \
      --ladder-mode dollars --trigger-tolerance $TOL \
      --start 2013-01-01 --end 2023-12-31 \
      --objective calmar --filter-objective calmar \
      --slippage 0.25 --samples 400 --fresh
done

echo
echo "All four trained. Compare with:  $PY compare_tolerance.py"
