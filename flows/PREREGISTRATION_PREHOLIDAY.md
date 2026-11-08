# PREREGISTRATION FLOWS-10 — the day before a US market holiday

```
WRITTEN:   2026-09-28, before any pre-holiday return has been computed on OANDA data.
STATUS:    FROZEN at its first commit; preholiday.py pins this file's sha256.
SOURCE:    Ariel (1990, JF); Lakonishok & Smidt (1988, RFS). The pre-holiday
           return is one of the oldest calendar anomalies. A day before a
           market holiday earned many times an ordinary day.
VEHICLE:   OANDA CFD SPX500_USD (NAS100, US30, DE30 secondary)
```

*Measurement, not a recommendation. Not financial advice.*

## 0. The claim and the expectation

Stock indices rise on the last trading day before an exchange holiday. The
effect is old and widely published. **Registered expectation: decayed.**
Seven published timing effects have now replicated in their paper's era and
died since. This test is run for completeness.

## 1. Step 0 — the calendar (offline, frozen)

- NYSE full-day closures 2005–2026 by rule: New Year's Day, MLK Day, Presidents'
  Day, Good Friday, Memorial Day, Juneteenth (from 2022), Independence Day, Labor
  Day, Thanksgiving and Christmas, on observed dates; plus the special closures
  2007-01-02, 2012-10-29/30, 2018-12-05 and 2025-01-09.
- **P** = the last NYSE trading day before each closure (or run of closures).
- Frozen as `data/preholiday_events.csv` by `fetch_preholiday.py`.

## 2. Data and return

SPX500_USD M15 bid/ask. r_t = the trading date's last mid close over its
first mid open, minus 1 (17:00-NY trading dates; no rollover crossed). Days
with fewer than 40 bars are dropped. Sample 2005-01-03 → 2026-08-31.

## 3. Primary

    r_t = a + b·PRE_t + g·FRI_t + u      Newey-West (5 lags)

FRI_t controls for the many P that fall on a Friday before a Monday holiday.
The claim predicts **b > 0**.

## 4. Gates

| gate | test | pass |
|---|---|---|
| **G1** | b | > 0, t ≥ 2.0 |
| **G2** | b in E1, E2, E3 | > 0 in all three, **E3 ≥ 0.5 × full** |
| **G3** | trade: ask open → bid close on P | mean net > 0, t ≥ 1.65, **E3 net > 0** |
| **G4** | placebo: the trading day before P | t_placebo < 2.0 and b_placebo < b |
| **G5** | size | ≥ 150 P days |

**Kills:** K1 is G1 failing, K2 is G2, K3 is G3, K4 is G4.

## 5. Secondary

- NAS100, US30 and DE30, with the same construction.
- Long history: FRED NASDAQCOM close-to-close, 1971–2004, with the same
  regression. This shows whether the effect existed before the CFD sample.
- b by holiday.

## 6. Power

About 200 P days. With day-return SD near 1.1%, the standard error is about
7.7 bp, so **t = 2 needs about 16 bp**. The historical effect was 15–25 bp.

## 7. Files

    flows/fetch_preholiday.py  data/preholiday_events.csv  flows/preholiday.py  flows/RESULT_PREHOLIDAY.md
