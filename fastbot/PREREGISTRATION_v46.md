# PREREGISTRATION v46 — turn of the month ("dash for cash")

Frozen 2026-09-27, before any turn-of-month return has been computed on this data. The harness (scripts/tom_v46.py) must pin this sha256.

I am not a financial adviser. This is a measurement, not a recommendation.

## Question
Equity returns have historically concentrated at the turn of the month:
- Ariel (1987) and Lakonishok & Smidt (1988) documented the effect.
- Etula, Rinne, Suominen & Vaittinen (RFS 2020) tie it to institutions' month-end cash needs: selling before payment dates, buying after.

This is a different mechanism from the pension rebalancing that died in FLOWS-1. Is it still there, net of costs?

## Data
SPX500 and NAS100 (OANDA 5m, 2005-01 → 2026-08-14) and UK100 (5m, data/v38, 2005 → 2026-09-25). Daily cash-session closes are taken from those files.

## Definitions
- **Turn-of-month window (TOM):** long from the close of the second-last trading day of the month to the close of the third trading day of the next month (four sessions).
- **Reference:** every other four-session window, non-overlapping.
- **Costs:** one round-trip quoted spread, plus overnight financing at DGS3MO + 2.5% a year (OANDA's markup) for each night held (Friday counts 3). Real spreads start in 2012–13; earlier years use the 2013 median spread.

## Gates (pooled across the three indices; SEs clustered by month)
- **G1:** mean TOM net − reference mean > 0 with t ≥ 2.0.
- **G2:** TOM net > 0 in each of 2005–12, 2013–19 and 2020–26.
- **G3:** holding a long only in TOM windows has a Sharpe of at least 0.46 (the 19-year bar).
- **Reported:** per index; the Etula pre-turn weakness window (days −6 to −3).

## Budget
- 260 months. The four-session RMS is about 266 bp, so the MDE is about 47 bp per window.
- The historical TOM effect is roughly 50–100 bp per window, so the test can see it if it has survived.

## Blind spots
- A long-biased window picks up the market's general upward drift. The reference comparison removes it.
- The financing proxy is not OANDA's actual historical rate.

## One run.
