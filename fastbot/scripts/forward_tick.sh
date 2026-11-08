#!/bin/bash
# forward_tick.sh -- PREREGISTRATION_v25 / v25.1, the unattended tick.
# RECORDS ONLY. Places no order, touches no broker account.
#
# Order matters: calendar first (so the ledger knows what is coming),
# then prices, then the ledger. Each step's failure is distinguishable
# in the log, because "the tick failed" is not a diagnosis.
set -u
cd "$(dirname "$0")" || exit 1
LOG=../data/forward_tick.log
HB=../data/forward_heartbeat.txt
FIVE=NAS100_USD,US30_USD,DE30_EUR,EUR_USD,XAU_USD
say(){ echo "[$(date -u +%FT%TZ)] $*" | tee -a "$LOG"; }
die(){ say "HALT: $1"; echo "HALT $1 $(date -u +%FT%TZ)" > "$HB"; exit 1; }

say "=== tick start ==="

# 1. calendar. Exit 3 (no source fetched) and 4 (phantom dates) are fatal;
#    the runway warning is not.
python3 calendar_forward.py --events ../data/events_v2.csv \
        --out ../data/events_v3.csv >> "$LOG" 2>&1
rc=$?; [ $rc -ge 3 ] && die "calendar_forward exit $rc"
say "calendar ok (exit $rc)"

# 2. prices, incremental -- pull_m1 resumes from the last row on disk.
#    Everything goes to ../data/v24 so the historical files that closed
#    results ran against are never mutated.
python3 pull_m1.py --pull --data-dir ../data/v24 --instruments "$FIVE" \
        --granularity M15 --sides B,A >> "$LOG" 2>&1 \
  || die "pull_m1 failed for the five"
python3 pull_m1.py --pull --data-dir ../data/v24 --instruments SPX500_USD \
        --granularity M15 --sides B,A --start 2005-01-01 >> "$LOG" 2>&1 \
  || die "pull_m1 failed for SPX500_USD"
say "prices ok"

# 3. the ledger. Exit 2 is the v25.1 hard abort (calendar exhausted).
python3 forward_ledger.py --events ../data/events_v3.csv >> "$LOG" 2>&1
rc=$?; [ $rc -eq 2 ] && die "forward_ledger: calendar exhausted"
[ $rc -ne 0 ] && die "forward_ledger exit $rc"

# 4. v32 Part B -- record forward surprises beside the ledger. NON-FATAL:
#    a failure here is logged and never halts or alters the v25 tick.
python3 forward_surprise.py >> "$LOG" 2>&1 || say "forward_surprise failed (non-fatal, v32)"

# 5. FORWARD_v36 (sha c5eed9075ab841ced934e9e9bbcd07aa5c00b2a55104d62fca432f129e86c490) -- NAS100 noise-band recorder. NON-FATAL, separate
#    data dir; a failure is logged and never halts or alters the v25 tick.
{ python3 pull_m1.py --pull --data-dir ../data/v36fwd --instruments NAS100_USD,SPX500_USD         --granularity M5 --sides B,A --start 2026-08-01 >> "$LOG" 2>&1   && python3 forward_noiseband.py >> "$LOG" 2>&1; }   || say "forward_noiseband failed (non-fatal, FORWARD_v36)"

# 6. PREREGISTRATION_v41.1 -- refresh the v41 forest's Mac-only inputs (AAII,
#    CFTC TFF, FRED DGS2/DTWEXBGS/GASREGW) into ../data/v41/refresh. The Cowork
#    VM has no network, so only this Mac step can do it. NON-FATAL, at most once
#    a day; writes nowhere else, and cannot halt or alter the v25 tick.
RL=../data/v41/refresh/refresh_log.jsonl
if [ ! -f "$RL" ] || [ -n "$(find "$RL" -mmin +1200 2>/dev/null)" ]; then
  python3 refresh_v41_inputs.py >> "$LOG" 2>&1 || say "refresh_v41_inputs failed (non-fatal, v41.1)"
fi

# 7. FORWARD_NQ (flows/PREREGISTRATION_FORWARD_NQ.md, sha de80d50c3cb646b4504f8009dd7c39a303548c19a8de39b830e289bafaf3e494)
#    -- v36 rule N on NQ futures, paper. Pulls new NQ 1m bars from Databento
#    (refuses any single pull over $1) and records complete sessions to
#    flows/data/forward_nq.csv. NON-FATAL: cannot halt or alter the v25 tick.
python3 ../../flows/forward_nq.py --tick >> "$LOG" 2>&1 || say "forward_nq failed (non-fatal, FORWARD_NQ)"

# 8. FORWARD_IMB2 (PREREGISTRATION_FORWARD_IMB2.md, sha bba7f3d414552577b63e4216245857314632734cfc7810ef496655feccfdeda5)
#    -- paper record of the 15:50 imbalance trade at a 1 s delay. Databento pull refuses any day over $1.
#    NON-FATAL: cannot halt or alter the v25 tick.
python3 forward_imb2.py --tick >> "$LOG" 2>&1 || say "forward_imb2 failed (non-fatal, FORWARD_IMB2)"

# 9. OILIMP1 forward record (PREREGISTRATION_OILIMP1.md, sha 923437deab315a8f7f0eea6b12a8a8955ea7d09d1bdabcefa61af1353d29533f)
#    -- monthly oil-carry signal + daily paper marks from Databento CL.c.0/CL.c.1 (refuses any pull over $1).
#    Needs a one-off 'python3 forward_oilcarry.py --seed' first. NON-FATAL.
python3 forward_oilcarry.py --tick >> "$LOG" 2>&1 || say "forward_oilcarry failed (non-fatal, OILIMP1)"

# 10. ORBCORE1 DAX forward record (PREREGISTRATION_ORBCORE1.md, sha 66c0aca9d467bf001150558fc5b63b724c32155cd06b42131ec4661b130f1050)
#     -- bare opening-range core on DE30 15m (already pulled in step 2). Paper only. NON-FATAL.
python3 forward_orbcore_dax.py >> "$LOG" 2>&1 || say "forward_orbcore_dax failed (non-fatal, ORBCORE1)"

# 11. FORWARD_BATCH2 parts 1-2 (PREREGISTRATION_FORWARD_BATCH2.md, sha 65d539aa8303972316d182e91b757977f0f2d990755d91e25d3e571f7acb89fa)
#     -- FUTPORT1 trend sleeve + FUTMICRO1 $50k, paper. Databento ohlcv-1d pull refuses over $1. NON-FATAL.
python3 forward_trend1.py --tick >> "$LOG" 2>&1 || say "forward_trend1 failed (non-fatal, FORWARD_BATCH2)"

# 12. FORWARD_BATCH2 part 3 -- GOLDRY1 weekly paper record (refreshes FRED DFII10 itself). NON-FATAL.
python3 forward_goldry1.py --tick >> "$LOG" 2>&1 || say "forward_goldry1 failed (non-fatal, FORWARD_BATCH2)"

# the redirect fails in the SHELL before wc runs, so wc's own 2>/dev/null
# cannot suppress it. Test for the file instead of catching the error.
if [ -f ../data/forward_ledger.csv ]; then
  N=$(( $(wc -l < ../data/forward_ledger.csv) - 1 ))
else
  N=0
fi
echo "OK $(date -u +%FT%TZ) rows=$N" > "$HB"
say "=== tick ok, ledger rows=$N ==="
