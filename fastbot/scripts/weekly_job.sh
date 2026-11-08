#!/bin/bash
# fastbot weekly job (Saturdays): VIX refresh -> FORWARD_C1 recorder; in the first week of each month also the Sharadar refresh
# (a NEW dated folder; the original download is never touched). RECORDS ONLY. Places no order. Keys stay in ~/.fred_key, ~/.sharadar_key.
cd "$(dirname "$0")" || exit 1
LOG=../data/weekly_job.log
say() { echo "[$(date -u +%FT%TZ)] $*" >> "$LOG"; }
say "=== weekly job start ==="
python3 fred_vix_refresh.py >> "$LOG" 2>&1 && say "vix ok" || say "vix FAILED"
python3 c1_forward.py >> "$LOG" 2>&1 && say "c1 ok" || say "c1 FAILED"
if [ "$(date +%d)" -le 7 ] && [ "$(date +%Y%m)" != "202610" ]; then   # first refresh Nov 2026 (forward record starts 5 Oct)
  if ! ls -d ../data/sharadar_fwd_$(date +%Y%m)* >/dev/null 2>&1; then
    python3 sharadar_pull.py --refresh >> "$LOG" 2>&1 && say "sharadar refresh ok" || say "sharadar refresh FAILED"
  fi
fi
say "=== weekly job end ==="
date -u +%FT%TZ > ../data/weekly_heartbeat.txt
