#!/bin/bash
# OILGOLD batch data pull -- RUN ON THE MAC from anywhere:   bash ~/RStudio/Claude/fastbot/scripts/pull_oilgold.sh
# Read-only market data; places no orders. Keys stay in ~/.oanda_token, ~/.eia_key, ~/.fred_key (never printed).
# Each step is independent: if one fails, the others still run. Safe to re-run (OANDA pull resumes).
cd "$(dirname "$0")" || exit 1
LOG=../data/pull_oilgold.log
step() { echo "=== $1 ($(date -u +%FT%TZ))" | tee -a "$LOG"; }
step "1/4 OANDA oil prices, 15-minute bid/ask, 2005 ->"
python3 pull_m1.py --pull --instruments WTICO_USD,BCO_USD --granularity M15 --sides B,A --start 2005-01-01 --data-dir ../data/v24 2>&1 | tail -5 | tee -a "$LOG"
step "2/4 EIA oil futures curve + weekly crude stocks (needs ~/.eia_key)"
python3 eia_fred_gld_pull.py eia 2>&1 | tee -a "$LOG"
step "3/4 FRED 10-year real yield (needs ~/.fred_key)"
python3 eia_fred_gld_pull.py fred 2>&1 | tee -a "$LOG"
step "4/4 SPDR GLD holdings"
python3 eia_fred_gld_pull.py gld 2>&1 | tee -a "$LOG"
step "done -- tell Claude"
