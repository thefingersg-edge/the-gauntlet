# FORWARD_v36.1: amendment to FORWARD_v36. Also record sessions with no trade

Written and frozen 2026-10-04. Approved by Dave the same day.

- **Recorder:** scripts/forward_noiseband.py **v1.1** (sha256 576e33dd57a4…).
- **Start date for the new rows:** **2026-10-05** (FORWARD_v36 §4: any change is a new document with a new start date).

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. Why
- v1.0 wrote a row only when the rule traded. A missing date could mean either "no trade" or "no data", and v25 §4's principle applies here too: a skip must be written down.

## 2. The change
The rule is untouched: momentum_v36 `noise_rows()`, imported unchanged. The self-test checks that traded rows are identical to v1.0's. From 2026-10-05, every complete NAS100 session gets exactly one row:
- **traded:** as before;
- **no trade:** `trades = 0`, gross 0, net 0, when the session has its 09:30 and 15:55 bars and the prior session's 15:55;
- **could not be evaluated:** `trades` blank, gross/net blank (a skip).

## 3. Before 2026-10-05
- No rows are added for earlier sessions.
- **Descriptive only.** Run on 2026-10-04, the rule gives 28 Sep 2 trades, 29 Sep **0**, 30 Sep 1, 1 Oct **0**, 2 Oct **0**. The three missing dates were no-trade sessions, not data gaps.

## 4. Nothing else changes.
