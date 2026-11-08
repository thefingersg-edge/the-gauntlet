# PREREGISTRATION v34 — the v33 lenses as general intraday signals

Frozen 2026-09-25 before any signed return was read (the budget below read
volatility and counts only). Script: scripts/general_levels.py v1.0.

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. Question
v33 tested VWAP/POC magnets and the Rule of 16 only around release mornings.
Here they are tested as stand-alone intraday signals on every US cash session.

## 2. Data
OANDA 5m bid/ask, SPX500, NAS100, US30, 2005-01 → 2026-09-17, bars 09:30–15:55 ET,
sessions with ≥ 70 bars. Mid = (bid+ask)/2. VIXCLS daily.
Discovery era 2005–2012 (bid = ask before 2012, so gross only).
**Holdout 2013-01-01 → 2026-09-17, gated, NET of the quoted spread**
(long buys ask, sells bid; short the reverse).

## 3. Lens A — VWAP / POC magnet
- Slots 10:30, 11:30, 12:30, 13:30, 14:30 ET; entry at the slot bar's open, exit 60 min later.
- Levels from session bars that closed before the slot: VWAP (typical price ×
  tick volume) and POC (2 bp bins, v33 definition, anchored at the slot price).
- D = (level / price − 1) × 1e4.
- Rule: trade TOWARD the level when |D| ≥ the 80th percentile of the prior 250
  |D| values for the same lens and slot (per instrument, trailing only).
  Direction fixed in advance; never reversed.
- Reported, not gated: slope of the 60-min forward return on D over all slots.

## 4. Lens B — Rule of 16 levels
- C = prior session's 15:55 bar close; I = prior-day VIX × 6.25 bp. Levels C·(1 ± I/1e4).
- Event = first 5m bar (09:30–14:50 start) whose close is beyond a level;
  entry at the next bar's open, exit 60 min later. One event per instrument per day.
- Fade or follow: the sign of mean gross continuation in the discovery era
  (2005–2012), then held fixed for the holdout. No other use of the discovery era.

## 5. Gates (three tests: VWAP rule, POC rule, R16 rule; Bonferroni t ≥ 2.39)
PASS for a lens needs all of:
1. holdout net mean > 0, t ≥ 2.39 (SEs clustered by date);
2. net mean > 0 in each holdout era: 2013–17, 2018–21, 2022–26;
3. holdout excluding 2020–21: net mean > 0, t ≥ 1.64.

## 6. Power budget (holdout, from SDs and counts only)
| lens | trades | dates | SD 60m | median spread | MDE (80%) |
|---|---|---|---|---|---|
| VWAP | 10,356 | 2,049 | 41.5 bp | 1.02 bp | ≈ 3.0 bp |
| POC | 10,554 | 2,382 | 40.0 bp | 1.04 bp | ≈ 2.7 bp |
| R16 | 3,233 | 1,675 | 48.7 bp | — | ≈ 3.8 bp |

**What the budget cannot see.** A net edge of about 1 bp per trade — enough
to be worth running — is below the MDE for every lens. v33's control-morning
hint (b ≈ 0.06, worth about 1 bp) is in that blind zone. So a FAIL means
"no edge of 3 bp or more", not "no edge". The all-slot slope is reported
because it has more power, but it gates nothing. The MDE treats each date as
one independent draw.

## 7. One run. No change of slots, hold, percentile, bins or eras after it.
