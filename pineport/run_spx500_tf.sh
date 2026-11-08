#!/bin/bash
# SPX500 5m / 1h / 4h retrain -- PREREGISTRATION_SPX500_timeframes.md
#
# Each timeframe gets a neutral base built from ITS OWN volatility (stops as
# ATR multiples carried from a working config, not copied percentages), then
# six staged searches with seed-consensus acceptance on an unseen validation
# slice. All three arms are reported whatever they show.
#
#   bash runlog.sh tf.log bash run_spx500_tf.sh          # all three
#   bash runlog.sh tf.log bash run_spx500_tf.sh H4       # one timeframe
set -e
cd "$(dirname "$0")"
PY=.venv/bin/python

run_tf () {
  TF=$1; CSV=$2
  if [ ! -f "$CSV" ]; then
    echo "### $TF SKIPPED -- $CSV missing (fetch it first)"; return 0
  fi
  BASE="configs/spx500_${TF}_base.json"
  echo
  echo "################ SPX500 $TF ################"
  $PY make_base.py --csv "$CSV" --out "$BASE" --state-triggers
  $PY train_staged.py --csv "$CSV" --tf "$TF" --base "$BASE" \
      --start 2009-01-01 --end 2022-12-31 \
      --state-triggers --objective calmar \
      --slippage 0.25 --seeds 4 --samples 200
}

if [ -n "${1:-}" ]; then
  case "$1" in
    M5) run_tf M5 spx500usd_oanda_m5.csv ;;
    H1) run_tf H1 spx500usd_oanda_h1.csv ;;
    H4) run_tf H4 spx500usd_oanda_h4.csv ;;
    *)  echo "usage: run_spx500_tf.sh [M5|H1|H4]"; exit 2 ;;
  esac
else
  run_tf H4 spx500usd_oanda_h4.csv      # fastest first, ~10 min
  run_tf H1 spx500usd_oanda_h1.csv      # ~30 min
  run_tf M5 spx500usd_oanda_m5.csv      # slowest, ~4-5 h
fi
echo
echo "Arms complete. Score the holdouts before drawing any conclusion."
