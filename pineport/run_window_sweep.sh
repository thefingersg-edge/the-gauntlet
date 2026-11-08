#!/bin/bash
# Does the rolling-retrain result depend on how much history you train on?
#
# ALL THREE LENGTHS ARE SCORED ON THE SAME TEST MONTHS. A 10-year training
# window cannot produce a test month before 2016-03 on gold or 2015-01 on
# NAS100, so if each run started as early as it could, the 3y version would be
# judged on 2009-2026 and the 10y version on 2016-2026 -- and any difference
# between them would be the market, not the window length. Both --start dates
# below are pinned to what the 10-year run can first reach.
#
# WHAT WOULD COUNT AS DEFINITIVE, fixed before running:
#
#   all three lengths non-significant vs frozen AND vs random, on both
#   instruments  ->  re-fitting adds nothing at any history depth. Settled.
#
#   any length significant (|t| > 2) vs BOTH frozen and random
#                ->  that depth is worth a closer look; not settled.
#
# ONE ARTEFACT TO WATCH. As train_years grows, the retrained config changes
# less from month to month, so `retrained` converges toward `frozen` by
# construction. If the 10-year run looks better than the 3-year one, check
# whether it has simply become the frozen control rather than learned more --
# the `vs frozen` column is what distinguishes those.
#
#   bash run_window_sweep.sh          # ~5-6 hours on 7 workers
set -e
cd "$(dirname "$0")"
PY=.venv/bin/python

for Y in 3 5 10; do
  echo "=== GOLD 4H, ${Y}y training ==="
  $PY rolling_retrain.py --csv xauusd_oanda_h4.csv --tf H4 \
      --train-years $Y --start 2016-04-01 --samples 100 --slippage 0.25
done

for Y in 3 5 10; do
  echo "=== NAS100 4H, ${Y}y training ==="
  $PY rolling_retrain.py --csv nas100usd_oanda_h4.csv --tf H4 \
      --train-years $Y --start 2015-01-01 --samples 100 --slippage 2.0 \
      --ladder-mode percent
done

echo
echo "All six done. Compare with:  $PY compare_windows.py"
