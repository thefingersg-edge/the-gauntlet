# PREREGISTRATION FLOWS-15 — fastbot v36 noise-band momentum on index FUTURES

```
WRITTEN:   2026-09-28, before any futures bar has been bought, fetched or read.
STATUS:    FROZEN at its first commit; vehicle.py pins this file's sha256.
SOURCE:    fastbot PREREGISTRATION_v36.md (frozen rule N) and RESULT_MOMENTUM_v36.md:
           gross +3.42 bp/instrument-day (t 3.17) on 2013–26 CFDs, killed by
           2.3 bp/day of CFD spread.
DATA:      Databento GLBX.MDP3 (CME), 1-minute OHLCV, ES and NQ (YM secondary).
           NEEDS DAVE: a Databento account (usage-based; new accounts get free credit).
```

*Measurement, not a recommendation. Not financial advice.*

## 0. The question — the vehicle, not the rule

This is not a new signal and not a re-tuning. v36's rule N is used
**unchanged** (fastbot `scripts/momentum_v36.py`, imported, not copied). The
one question is whether a gross edge that the CFD spread killed survives the
cost of exchange-traded futures. The cost of the vehicle has decided more
results in this programme than any signal.

**Registered expectation:** plausible. The gross effect was t 3.2 on CFD mid
prices. A futures round trip costs about 1 tick (ES ~0.45 bp, NQ ~0.13 bp
at 2026 levels) plus commission, against 2.3 bp/day on CFDs.

## 1. Data (Step 0)

- Databento GLBX.MDP3, `ohlcv-1m`, continuous front month by volume
  (`ES.v.0`, `NQ.v.0`, `YM.v.0`), 2012-12 → 2026-08. Resampled to 5-minute bars
  09:30–15:55 ET to match v36. Sessions with fewer than 70 bars are dropped,
  as in v36.
- **Roll days:** the first session after each change of underlying contract
  is dropped. v36's bands use the prior close, and a roll gap would
  corrupt it.
- Frozen with sha256s before any rule is run.

## 2. Fills and costs

- Fills at the next bar's open, as in v36. Each side pays **half a tick plus
  a slippage of half a tick**, i.e. one full tick per side. That is
  deliberately harsher than the quoted spread, because 1-minute OHLCV has no
  quotes. Commission is **$2.50 per contract per round trip**, converted to
  bp at the session's price and multiplier (ES $50, NQ $20, YM $5).

## 3. Gates (v36's own, plus the recent-era floor)

Unit: net P&L per instrument-day, over days with at least one trade. Gated
2013-01-01 → 2026-08-31. Standard errors clustered by date.

| gate | pass |
|---|---|
| **G1** | pooled ES+NQ net > 0 with t ≥ 2.24 (v36's Bonferroni bar) |
| **G2** | net > 0 in each of 2013–17, 2018–21 and 2022–26, **and 2022–26 ≥ 0.5 × full** |
| **G3** | excluding 2020–21: net > 0 with t ≥ 1.64 |
| **G4** | gross on futures within ±50% of v36's gross on the matching CFD (SPX500↔ES, NAS100↔NQ). This checks that the vehicle carries the same signal |

**Kills:** K1 is G1 failing, K2 is G2, K3 is G4. If G4 fails, the futures
are not the same bet, and the test is void rather than failed.

## 4. Secondary

YM; each instrument separately; the cost at which net = 0 (break-even ticks).

## 5. Files

    flows/fetch_futures.py (Mac, Databento key in ~/.databento_key, never printed)
    flows/vehicle.py   flows/RESULT_VEHICLE.md
