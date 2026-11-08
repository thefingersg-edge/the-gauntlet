#!/usr/bin/env bash
#
# pull_data.sh -- refresh OANDA price data to a single, consistent vintage.
#
# WHY A SCRIPT RATHER THAN FOUR COMMANDS
#
# On 2026-10-01 the four SPX500 files sat at four different fetch vintages:
#
#     spx500usd_oanda_h1.csv    7 Aug
#     spx500usd_oanda_h4.csv    8 Aug
#     spx500usd_oanda_m15.csv  15 Aug
#     spx500usd_oanda_m5.csv   27 Sep
#
# Training 5m / 1h / 4h arms across those compares timeframes whose data ends
# seven weeks apart, and attributes the difference to the timeframe. CLAUDE.md
# standing rule 5 exists because this tree has already shipped two bugs of this
# class. Pulling one timeframe by hand is how the spread opens up, so the unit
# of work here is "bring an instrument to one vintage", not "fetch a file".
#
# Every pull is followed by verify_feed.py, and the script STOPS on a failed
# verification rather than leaving a bad file in place for a later run to pick
# up silently.
#
# CREDENTIALS -- the token is never passed on the command line, never echoed,
# and never written to a log. fetch_oanda.py reads it from OANDA_API_TOKEN,
# ~/.oanda_token or ./.oanda_token (gitignored). Per standing rule 3 no agent
# needs to see it and it must never be pasted into a chat.
#
# USAGE
#
#   ./pull_data.sh                        # SPX500, all four timeframes, resumed
#   ./pull_data.sh --instrument NAS100_USD
#   ./pull_data.sh --timeframes "M5 M15"  # a subset
#   ./pull_data.sh --fresh                # refetch from --start, ignore existing
#   ./pull_data.sh --spreads-only         # just the bid/ask daily pair
#   ./pull_data.sh --verify-only          # check what is on disk, fetch nothing
#   ./pull_data.sh --dry-run              # print the commands and exit
#
# A resumed pull costs a few pages. --fresh on M5 is ~300 pages and 20 minutes;
# it is almost never what you want.

set -uo pipefail

cd "$(dirname "$0")" || exit 1

PY="${PY:-.venv/bin/python}"
[ -x "$PY" ] || PY="python3"

INSTRUMENT="SPX500_USD"
TIMEFRAMES="M5 M15 H1 H4"
START="2005-01-01"
PAUSE="0.15"
RESUME="--resume"
SPREADS=1
DO_FETCH=1
DRY=0
ONLY_SPREADS=0

while [ $# -gt 0 ]; do
  case "$1" in
    --instrument)   INSTRUMENT="$2"; shift 2 ;;
    --timeframes)   TIMEFRAMES="$2"; shift 2 ;;
    --start)        START="$2"; shift 2 ;;
    --pause)        PAUSE="$2"; shift 2 ;;
    --fresh)        RESUME=""; shift ;;
    --no-spreads)   SPREADS=0; shift ;;
    --spreads-only) ONLY_SPREADS=1; TIMEFRAMES=""; shift ;;
    --verify-only)  DO_FETCH=0; SPREADS=0; shift ;;
    --dry-run)      DRY=1; shift ;;
    -h|--help)      sed -n '2,45p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

# spx500usd / nas100usd / xauusd -- the existing file-naming convention
SLUG="$(echo "$INSTRUMENT" | tr '[:upper:]' '[:lower:]' | tr -d '_')"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="pull_${SLUG}_${STAMP}.log"

# A --dry-run writes no log: it is a question, not a run, and a stray log file
# is one more thing to tidy up by hand.
say() {
  if [ "$DRY" = 1 ]; then printf '%s\n' "$*"
  else printf '%s\n' "$*" | tee -a "$LOG"; fi
}

run() {
  if [ "$DRY" = 1 ]; then printf '  would run: %s\n' "$*"; return 0; fi
  say "  \$ $*"
  "$@" >>"$LOG" 2>&1
}

say "pull_data.sh  $(date)"
say "instrument $INSTRUMENT   timeframes: ${TIMEFRAMES:-none}   start $START"
if [ -n "$RESUME" ]; then
  say "mode: resume (continues each CSV from its last bar)   log $LOG"
else
  say "mode: FRESH -- full refetch from $START. M5 is ~300 pages."
  say "      log $LOG"
fi
say ""

# --- token present? fail here rather than 300 pages in --------------------
if [ "$DRY" = 0 ] && { [ "$DO_FETCH" = 1 ] || [ "$SPREADS" = 1 ]; }; then
  if [ -z "${OANDA_API_TOKEN:-}" ] && [ ! -f "$HOME/.oanda_token" ] \
     && [ ! -f ".oanda_token" ]; then
    say "No OANDA token found. Set one of:"
    say "  export OANDA_API_TOKEN='...'"
    say "  echo '...' > ~/.oanda_token && chmod 600 ~/.oanda_token"
    say "Do not paste the token into a chat or commit it (standing rule 3)."
    exit 1
  fi
  if [ "$DRY" = 0 ]; then
    say "checking auth (token not displayed)..."
    if ! $PY fetch_oanda.py --check >>"$LOG" 2>&1; then
      say "AUTH FAILED -- see $LOG. A practice token will not work against live."
      exit 1
    fi
    say "  auth ok"
  fi
fi

# --- record the vintage spread BEFORE we touch anything -------------------
say ""
say "vintage before this pull:"
for tf in M5 M15 H1 H4 D; do
  f="${SLUG}_oanda_$(echo "$tf" | tr '[:upper:]' '[:lower:]').csv"
  if [ -f "$f" ]; then
    say "  $(printf '%-34s' "$f") $(date -r "$f" '+%Y-%m-%d %H:%M' 2>/dev/null)"
  fi
done

FAILED=""

# --- price bars ------------------------------------------------------------
for tf in $TIMEFRAMES; do
  # --verify-only must not fetch. Without this guard it fetched AND then ran
  # the verify sweep, so a command meant to inspect the disk silently changed
  # it -- which is exactly the kind of thing that puts files at two vintages.
  [ "$DO_FETCH" = 0 ] && continue
  lower="$(echo "$tf" | tr '[:upper:]' '[:lower:]')"
  out="${SLUG}_oanda_${lower}.csv"
  say ""
  say "=== $INSTRUMENT $tf -> $out ==="
  if run $PY fetch_oanda.py --instrument "$INSTRUMENT" --granularity "$tf" \
        --price M --start "$START" --out "$out" --pause "$PAUSE" $RESUME; then
    [ "$DRY" = 1 ] && continue
    tail -4 "$LOG" | sed 's/^/    /'
    # Verification is part of the pull, not a separate chore. --expect-
    # granularity is the check that catches a resampled grid posing as native
    # bars, which this tree has shipped once already.
    if $PY verify_feed.py --expect-granularity "$tf" "$out" 2>&1 | tee -a "$LOG"; then
      say "  verified ok"
    else
      say "  VERIFY FAILED for $out -- see above. Not using this file."
      FAILED="$FAILED $out"
    fi
  else
    [ "$DRY" = 1 ] && continue
    say "  FETCH FAILED for $tf (see $LOG)"
    FAILED="$FAILED $tf"
  fi
done

# --- bid/ask daily, for cost measurement ----------------------------------
# Standing rule 6: costs are the usual killer, so price the vehicle early and
# MEASURE the spread rather than guessing it. Half the median bid/ask gap is
# the per-fill cost. Daily is enough -- the half-spread is stable within a day
# and a 5m bid/ask pull is 3M candles for no extra information.
if [ "$SPREADS" = 1 ] || [ "$ONLY_SPREADS" = 1 ]; then
  short="$(echo "$SLUG" | sed 's/usd$//')"
  say ""
  say "=== daily bid/ask for cost measurement ==="
  for side in B:bid A:ask; do
    code="${side%%:*}"; name="${side##*:}"
    out="${short}_${name}_d.csv"
    if run $PY fetch_oanda.py --instrument "$INSTRUMENT" --granularity D \
          --price "$code" --start "$START" --out "$out" --pause "$PAUSE"; then
      [ "$DRY" = 0 ] && say "  wrote $out"
    else
      [ "$DRY" = 0 ] && { say "  FAILED $out"; FAILED="$FAILED $out"; }
    fi
  done
  if [ "$DRY" = 0 ] && [ -f "${short}_bid_d.csv" ] && [ -f "${short}_ask_d.csv" ]; then
    $PY - "$short" <<'PYEOF' 2>&1 | tee -a "$LOG"
import sys, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
import pandas as pd
from data import _normalise, _read_csv
s = sys.argv[1]
b = _normalise(_read_csv(f"{s}_bid_d.csv"))["close"]
a = _normalise(_read_csv(f"{s}_ask_d.csv"))["close"]
j = pd.concat({"bid": b, "ask": a}, axis=1).dropna()
sp = (j["ask"] - j["bid"])
# 2005-2011 OANDA spreads are backfilled at bid == ask, so the early years are
# a floor, not a measurement. Report the recent window separately.
rec = sp[sp.index >= sp.index.max() - pd.Timedelta(days=5*365)]
print("\n  MEASURED SPREAD (daily closes differenced)")
print(f"    all {len(sp):,} days      median {sp.median():.4f}   "
      f"-> {sp.median()/2:.4f} per fill")
print(f"    last 5y {len(rec):,} days  median {rec.median():.4f}   "
      f"-> {rec.median()/2:.4f} per fill   <-- use this")
z = int((sp == 0).sum())
if z:
    print(f"    {z:,} days at bid == ask (backfilled, pre-2011) -- "
          f"early-year costs are a FLOOR, not a measurement")
PYEOF
  fi
fi

# --- verify-only sweep -----------------------------------------------------
if [ "$DO_FETCH" = 0 ]; then
  say ""
  say "=== verifying files on disk, no fetch ==="
  for tf in $TIMEFRAMES; do
    lower="$(echo "$tf" | tr '[:upper:]' '[:lower:]')"
    f="${SLUG}_oanda_${lower}.csv"
    [ -f "$f" ] && { $PY verify_feed.py --expect-granularity "$tf" "$f" \
        2>&1 | tee -a "$LOG" || FAILED="$FAILED $f"; }
  done
fi

# --- vintage after, and the whole point of the script ---------------------
if [ "$DRY" = 0 ]; then
  say ""
  say "vintage after this pull -- these should now agree:"
  LAST=""
  SPREAD_WARN=0
  for tf in $TIMEFRAMES; do
    lower="$(echo "$tf" | tr '[:upper:]' '[:lower:]')"
    f="${SLUG}_oanda_${lower}.csv"
    if [ -f "$f" ]; then
      end="$($PY - "$f" <<'PYEOF' 2>/dev/null
import sys, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from data import _normalise, _read_csv
print(_normalise(_read_csv(sys.argv[1])).index[-1].date())
PYEOF
)"
      say "  $(printf '%-34s' "$f") last bar $end"
      [ -n "$LAST" ] && [ "$end" != "$LAST" ] && SPREAD_WARN=1
      LAST="$end"
    fi
  done
  [ "$SPREAD_WARN" = 1 ] && say "
  NOTE: last bars still differ across timeframes. That is EXPECTED when the
  pull ran mid-session (a 4h bar closes less often than a 5m one), but if the
  gap is days rather than hours the pull did not complete -- re-run before
  training across these timeframes."
fi

say ""
if [ -n "$FAILED" ]; then
  say "FAILED:$FAILED"
  say "Fix these before training. A bad panel produces a confident wrong answer."
  [ "$DRY" = 0 ] && { echo "rc=1 $(date)" > "$LOG.FAILED"; printf '\a'; }
  exit 1
fi
say "all pulls verified. log: $LOG"
if [ "$DRY" = 0 ]; then
  echo "$(date)" > "$LOG.DONE"
  printf '\a'
  command -v osascript >/dev/null 2>&1 && osascript -e \
    "display notification \"$INSTRUMENT data pulled and verified\" with title \"pull_data.sh\"" 2>/dev/null
fi
