#!/usr/bin/env bash
# Fetch the full multi-market test set from Dukascopy.
#
# PROBE FIRST. Instrument names and price scaling differ, and index/commodity
# CFDs have shorter history than FX and metals. One probe per instrument costs
# a single request and tells you the name resolves, the prices look sane and
# the divisor is right. A full pull of a mis-named instrument wastes 200+
# requests and gets you throttled.
#
#   bash fetch_all.sh probe     # one month each, ~1 minute total
#   bash fetch_all.sh full      # the real pull, expect 30-60 minutes
#
# Everything is cached, so a re-run after a 503 storm only fetches what failed.

set -uo pipefail
cd "$(dirname "$0")"
PY="${PY:-.venv/bin/python}"
[ -x "$PY" ] || PY=python3

# name:start_year -- FX and metals go back to 2006, CFDs start later.
MARKETS=(
  "XAUUSD:2006"          # gold        (have it)
  "XAGUSD:2006"          # silver      (have it)
  "EURUSD:2006"          # euro        (have it)
  "GBPUSD:2006"          # sterling
  "USDJPY:2006"          # yen
  "AUDUSD:2006"          # aussie -- commodity currency, different driver
  "USA500IDXUSD:2012"    # S&P 500 CFD
  "DEUIDXEUR:2012"       # DAX CFD
  "BRENTCMDUSD:2012"     # Brent crude
  "COPPERCMDUSD:2012"    # copper
)

MODE="${1:-probe}"

if [ "$MODE" = "probe" ]; then
    echo "Probing ${#MARKETS[@]} instruments (one month each)..."
    echo "Check each shows sensible prices and no scale warning."
    echo
    for entry in "${MARKETS[@]}"; do
        sym="${entry%%:*}"
        printf '=== %s ' "$sym"
        printf '%.0s=' {1..40}; echo
        "$PY" dukascopy.py --instrument "$sym" --probe --year 2024 --month 6 \
            2>&1 | grep -E "probing|raw bars|bars kept|median close|PRICE SCALE|Try --price|No data|first 5|^20[0-9]" | head -8
        echo
    done
    echo "All probes done. Any instrument showing 'No data' has the wrong name;"
    echo "any showing 'PRICE SCALE LOOKS WRONG' needs --price-divisor set."
    echo "Then run:  bash fetch_all.sh full"
    exit 0
fi

if [ "$MODE" != "full" ]; then
    echo "usage: bash fetch_all.sh [probe|full]"; exit 1
fi

echo "Full pull of ${#MARKETS[@]} instruments. Cached months are skipped, so"
echo "re-running after failures is cheap. Ctrl-C is safe."
echo

for entry in "${MARKETS[@]}"; do
    sym="${entry%%:*}"; start="${entry##*:}"
    out="$(echo "$sym" | tr '[:upper:]' '[:lower:]')_1h.csv"
    if [ -f "$out" ]; then
        echo "--- $sym: $out already exists, skipping (delete it to refetch)"
        continue
    fi
    echo "--- $sym from $start -> $out"
    "$PY" dukascopy.py --instrument "$sym" --start "$start" --out "$out" \
        --pause 1.5 --timeout 60 --retries 8 2>&1 | tail -12
    echo
done

echo "=================================================="
echo "Done. Files present:"
ls -1 *_1h.csv 2>/dev/null
echo
echo "Any instrument that failed can be retried by re-running this script --"
echo "completed ones are skipped and cached months are not re-downloaded."
