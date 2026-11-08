# PREREGISTRATION v41.1: amendment to v41, made before its first record

Written 2026-10-01, frozen 2026-10-02 (its first commit), before forward_forest.py has written a single row (data/forward_forest.csv does not exist; sessions from 2026-09-28 are unrecorded). Amendments before a run are legitimate and dated (CLAUDE.md rule 1). The recorder is scripts/forward_forest.py **v1.1**; its sha256 is recorded in the commit that freezes this file.

I am not a financial adviser. This is a measurement, not a recommendation.

## What does NOT change
- The model (data/v41/forest_v41.pkl, sha e77aea7c…; freeze_v41.json sha 7c338b95…), its check predictions, the thresholds, START (2026-09-28), entries, exits E1/E2, the cost rule, and every decision rule in v41 section 4.

## What changes, and why
Found on 2026-10-01 while checking the inputs against the TradingView connector:

1. **Phantom releases.** events.csv, events_v2.csv and events_v3.csv each carry CPI, NFP and CLAIMS rows dated **Saturday 2026-09-12** (an ALFRED vintage date, not a release). Forward, they would have made "minutes since NFP" count from 12 Sep instead of 4 Sep, and "minutes since CPI" from 12 Sep instead of 11 Sep, until the next real releases. **Fix:** the forward calendar drops any release dated on a weekend. The tables are not edited: closed results ran on them, and the v25 ledger starts on 2026-09-19, after the bad rows.
2. **Stale inputs give wrong values without any warning.** VIXCLS.csv ended 2026-08-31; the VX1!/VX2! exports ended on 2026-08-18 with a partial (mid-session) last row (18.2 / 19.9 against settlements of 18.1906 / 19.7247). Two VIX drops above 10% (2026-09-11, 2026-09-17) were absent. The "minutes since" features for an input's events cannot be marked missing; they silently count from the last event in the file. v41's `missing_macro` counted only the state features, so it could not see this.
3. **The registered refresh could not refresh.** v41 section 3 names fred_fetch_v31.py and sentiment_fetch.py. The first skips any file already on disk; the second never re-downloads the current year's CFTC zip. Running them would have changed nothing for FRED or COT.

## The fix
- **Inputs are assembled, never edited.** Each run, forward_forest.py v1.1 builds data/v41/inputs/data/ from each ORIGINAL input file, appending only rows dated after that file's last row, then calls tl_build2.macro_events **unchanged** on that folder:
  - VIX, VX1, VX2, SKEW: from data/tv/ (TradingView connector; tv_series.py; MANIFEST.json holds the shas). Verified on 2026-10-01: VX identical on 4,968 overlapping sessions; VIX matches FRED on 4,969 of 4,978 days; SKEW matches Cboe on 4,974 of 4,991 (only rows after each original's last date are used).
  - The VX export's last row is treated as partial and replaced by the settled value.
  - AAII, COT (CFTC TFF), DGS2, DTWEXBGS, GASREGW: from data/v41/refresh/, written by the new scripts/refresh_v41_inputs.py on the Mac (forward_tick.sh step 6, at most once a day, non-fatal). A refreshed AAII workbook is used only if it matches the original on every shared week.
  - Self-test: the assembled inputs reproduce every original macro event and state value before 2026-08-17 exactly.
- **Completeness guard.** A session d is recorded only when EVERY event-producing input (VIX, VX1, VX2, SKEW, AAII, COT, DGS2, DTWEXBGS, GASREGW) has its last row available at or after 13:45 ET on d, using tl_build2's own availability stamps. Until then the session is not recorded, not logged as no-signal, and is listed in data/forward_forest_deferred.log. It is retried at the next run. Because every stamp is a publication time, a late record adds no look-ahead.
  - Excluded: the Cboe total put/call file. It ended on 2019-10-04, so its events were absent from every training row after 2019-12, and they stay absent forward. Using a different series for it would change the model's inputs.

## Consequences, stated now
- Weekly inputs (AAII, COT) delay recording by up to about 10 days after a session. Monthly runs are unaffected.
- **The VM cannot reach FRED, CFTC or AAII** (checked 2026-10-02: no network from the Cowork VM). Only the Mac's forward_tick.sh step 6 can refresh those five inputs. On 2026-10-02 their last rows are: COT 2026-09-15 report, AAII 2026-09-24 survey, DGS2 2026-09-23, DTWEXBGS 2026-09-18, GASREGW 2026-09-21. **Every session from 2026-09-28 is therefore deferred until step 6 has run at least once.** That is the guard working, not a fault.
- If the Mac refresh never runs, v41 records nothing and says why in the log. That is the intended failure: a confident wrong record is worse than none.
- The kill and confirm counts (250 / 500 / 1,000 trades) and their horizons are unchanged.

## One recorder. No change to model, thresholds, exits or gates.

## Addendum 2026-10-02, before any record
- forward_forest.py **1.1.1**: build_inputs() rewrites the assembled files in place instead of deleting the folder first. The Cowork VM cannot delete files in Dave's folder without a per-session approval, which a scheduled run cannot give. Nothing that is computed or recorded changes; the self-test is unchanged and passes.
- First run, 2026-10-02 06:4x UTC: all four sessions (2026-09-28 to 10-01) deferred on both instruments, waiting for AAII, COT, DGS2, DTWEXBGS and GASREGW. Expected, as stated above.
- tv_series.py: a short refresh pull (the monthly task pulls 300 bars) now keeps the older stored rows instead of replacing the file. Self-tested. The v41 recorder reads only rows after each original file's last date, so nothing it computes changes.
