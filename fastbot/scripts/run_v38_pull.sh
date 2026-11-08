#!/bin/bash
# v38 data pull -- OANDA 5-minute BID and ASK candles for five index CFDs this
# project has never tested the noise-band rule or the timeline on.
# Run on your Mac (Terminal), from anywhere:
#     bash ~/RStudio/Claude/fastbot/scripts/run_v38_pull.sh
# It uses your OANDA token the same way the forward job does (never printed).
# RESUMES if interrupted: just run it again. Nothing here trades.
set -u
cd "$(dirname "$0")" || exit 1
OUT=../data/v38
mkdir -p "$OUT"
LOG=$OUT/pull_v38.log
INS=UK100_GBP,JP225_USD,AU200_AUD,EU50_EUR,DE30_EUR
echo "[$(date -u +%FT%TZ)] v38 pull start" | tee -a "$LOG"
# 1. how far back does OANDA serve M5 for each? (a few requests)
python3 pull_m1.py --probe --instruments "$INS" 2>&1 | tee -a "$LOG"
# 2. the pull itself: bid and ask, M5, from 2005 (OANDA starts wherever it starts)
python3 pull_m1.py --pull --data-dir "$OUT" --instruments "$INS" \
        --granularity M5 --sides B,A --start 2005-01-01 2>&1 | tee -a "$LOG"
# 3. check what was written
python3 pull_m1.py --verify --data-dir "$OUT" --instruments "$INS" --granularity M5 2>&1 | tee -a "$LOG"
echo "[$(date -u +%FT%TZ)] v38 pull done -- files in fastbot/data/v38" | tee -a "$LOG"
