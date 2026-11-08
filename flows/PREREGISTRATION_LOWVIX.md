# PREREGISTRATION FLOWS-7 — the announcement-day premium on LOW-VIX days: two confirmations

```
WRITTEN:   2026-09-27, AFTER FLOWS-4 found this pattern post hoc on
           SPX500 2005-01 .. 2026-08 (RESULT_ANNOUNCE.md, LEADS_POSTHOC.md).
           Neither confirmation sample below has been read: no index price
           before 2005 is on disk, and no CFD bar after 2026-08-31 has been
           used in any statistic.
STATUS:    FROZEN at its first commit. lowvix.py pins this file's sha256.
```

*Measurement, not a recommendation. Not financial advice.*

---

## 0. The lead, and why it needs a sample it was not found in

In FLOWS-4, non-FOMC release days (CPI, NFP, GDP, ISM) on evenings when VIX
was at or below its 252-day median paid SPX500 **+12.0 bp more than other
low-VIX days (t 3.23)**. That held in all three eras (+13.2 / +8.0 / +15.2),
in all four release types (+6 to +18), on NAS100, US30 and DE30 (+9.6 to
+10.9), and with the ten best days removed (+8.8). It paid about +10.9 bp a
trade after the spread (t 3.1, about 25 trades a year). On high-VIX evenings
it was zero. This fits Ai, Bansal & Guo's unconditional ~10 bp premium, with
the high-VIX days adding noise and no premium.

It was **found**, not predicted, and the registered claim pointed the other
way. So none of those numbers count as evidence. Two samples it was not
found in are available:

- **H, a history holdout, 1994-01 .. 2004-12.** Available now. The releases
  are dated from 1994, VIX from 1990. The CFD history starts in 2005, so
  none of it has been looked at.
- **F, forward, from 2026-09-01.** The CFD trade exactly as found, net of the
  spread. Slow: see the power section.

## 1. Definitions (identical in H and F, and identical to FLOWS-4)

- **A_t**: trading date t is a CPI, NFP, GDP or ISM date, and not an FOMC
  statement date.
- **LOW_t**: VIX on the last date before t is at or below the median of the
  252 VIX values ending on that date. HIGH_t = 1 − LOW_t.
- Dates: CPI, NFP and FOMC from `fastbot/data/events.csv`. GDP from GDPC1
  vintage dates (amendment A1 method). ISM from the first-US-business-day
  rule. 1994–2004 dates are built into `flows/data/holdout_events.csv` and
  frozen before any price is read.

## 2. Part H — history holdout (the decisive test)

- **Data.** NASDAQ Composite daily close (FRED NASDAQCOM), 1993-12-31 ..
  2004-12-31. It is the only broad US index on FRED with daily history this
  far back. S&P 500 daily closes are fetched too, if a free source answers
  (stooq ^spx); they are **secondary**. The primary is fixed to NASDAQCOM now
  so that the choice cannot follow the result.
- **Return.** Close-to-close, r_t = C_t / C_{t−1} − 1. For 08:30 and 10:00
  releases this spans the release; for FOMC (14:15 then) it does too.
- **Regression**, Newey-West (5 lags):

      r_t = c + bL·A_t·LOW_t + bH·A_t·HIGH_t + d·HIGH_t + g·FOMC_t + u

- **Gates**
  | gate | pass |
  |---|---|
  | **H1** | bL > 0 and t ≥ 1.65 (one-sided 5%: this is a confirmation of a stated direction) |
  | **H2** | bL ≥ 5 bp (at least ~half the discovery estimate) |
  | **H3** | bL > 0 in both halves, 1994–1999 and 2000–2004 |
- **Verdict.** H1 ∧ H2 ∧ H3 = CONFIRMED. Anything else = NOT CONFIRMED. The
  lead is then closed and Part F is not run.
- **Power, stated before the run.** On about 270 A∧LOW days, with NASDAQ
  low-VIX daily standard deviation near 1.2%, the standard error is about
  7 bp. A true effect of 10 bp gives an expected t of about 1.4: **roughly a
  40% chance of passing H1 even if the lead is real**. A NOT CONFIRMED
  verdict is weak evidence against the lead, and it is still binding.
- **Secondary (descriptive):** bH; per release type; the S&P series if it
  was fetched.

## 3. Part F — forward CFD confirmation (only if H is CONFIRMED)

- **Trade.** On every A∧LOW trading date from 2026-09-01: buy SPX500_USD at
  the ask open of the first M15 bar of the trading date, and sell at the
  bid close of its last bar. No rollover, so no financing. The log is
  appended by `lowvix.py --forward` from the v24 files that
  `forward_tick.sh` keeps current. The events table for dates after 2026-08
  is extended with the same three sources, each date added before its day
  trades.
- **Single evaluation at the 150th trade** (about 6 years). This is not
  peeked at before then, except for the kill below.
  | gate | pass |
  |---|---|
  | **F1** | mean net > 0 and t ≥ 1.65 |
  | **F2** | mean net ≥ 4 bp |
- **Early kill:** at the 75th trade, stop if the mean net is ≤ −4 bp.
- **Power.** The per-trade standard deviation is about 80 bp, so at n = 150
  the standard error is about 6.5 bp. A true +10.9 bp gives an expected t of
  about 1.7, so roughly a 50% chance of passing. That is slow and noisy.
  It is written down so that nobody mistakes a pass for proof.

## 4. What this does not do

It does not change FLOWS-4's verdict, which was on the registered VIX-high
claim. It does not re-test FLOWS-6's natgas lead: see LEADS_POSTHOC.md for
why that one is parked.

## 5. Files

    flows/LEADS_POSTHOC.md              the post-hoc diagnostics that motivated this
    flows/fetch_holdout.py              Step 0 on the Mac: NASDAQCOM, stooq ^spx, GDPC1 1994-2004
    flows/data/holdout_events.csv       frozen before any price
    flows/lowvix.py                     --self-test / --check-inputs / --holdout / --forward
    flows/RESULT_LOWVIX.md
