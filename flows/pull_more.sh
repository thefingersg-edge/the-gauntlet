#!/bin/bash
# pull_more.sh -- Step 0 data for FLOWS-8..15. RUN ON YOUR MAC:
#     bash ~/RStudio/Claude/flows/pull_more.sh
# Needs: OANDA token (FX pairs), FRED key (long series), and for the SEC step a
# User-Agent line in ~/.sec_user_agent ("Name you@example.com"). Databento
# (FLOWS-15) is a separate, paid step: see the end. Reads no returns.
set -u
cd "$(dirname "$0")" || exit 1
S=../fastbot/scripts; DATA="$PWD/data"
step(){ printf '\n=== %s ===\n' "$*"; }
warn(){ printf '  WARNING: %s (continuing)\n' "$*"; }
PY=python3
for c in ../pineport/.venv/bin/python; do [ -x "$c" ] && "$c" -c "import pandas" 2>/dev/null && PY="$c"; done
echo "python: $PY"
step "0. self-tests"
for f in fetch_longrun fetch_auctions fetch_earnings fetch_futures; do "$PY" $f.py --self-test >/dev/null || { echo "STOP: $f self-test"; exit 1; }; done
echo "all pass"
step "1. FX pairs, M15 bid + ask from 2005 (FLOWS-8; resumable)"
"$PY" "$S/pull_m1.py" --pull --granularity M15 --sides B,A --start 2005-01-01 \
   --instruments USD_JPY,GBP_USD,AUD_USD,USD_CAD,USD_CHF,NZD_USD,USD_NOK,USD_SEK --data-dir "$DATA" || warn "FX pull -- re-run to resume"
step "2. FRED long series + Shiller (FLOWS-10/12/13/14)"
"$PY" fetch_longrun.py || warn "fetch_longrun"
step "3. Treasury auctions (FLOWS-11)"
if [ -f "$DATA/auction_events.csv" ] && [ "${REBUILD:-0}" != "1" ]; then echo "  exists -- not rebuilt"; else "$PY" fetch_auctions.py || warn "fetch_auctions"; fi
step "4. SEC earnings dates (FLOWS-9)"
if [ -f "$DATA/earnings_events.csv" ] && [ "${REBUILD:-0}" != "1" ]; then echo "  exists -- not rebuilt"; else "$PY" fetch_earnings.py || warn "fetch_earnings (is ~/.sec_user_agent set?)"; fi
step "5. Databento futures (FLOWS-15) -- price check only, downloads nothing"
if [ -f ~/.databento_key ] || [ -n "${DATABENTO_API_KEY:-}" ]; then "$PY" fetch_futures.py || warn "databento"
else echo "  no Databento key: skipped. To do FLOWS-15, open an account, put the key in ~/.databento_key,"
     echo "  run  $PY fetch_futures.py  to see the price, then  --confirm  to buy."; fi
echo; echo "Done. Nothing here computed a return. Tell Claude."
