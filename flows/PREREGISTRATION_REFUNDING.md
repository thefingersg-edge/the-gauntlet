# PREREGISTRATION FLOWS-2 — the Friday before Treasury's borrowing estimates

```
WRITTEN:   2026-09-26, before any bond return on any pre-refunding day has
           been computed on OANDA data. No event table and no harness exist yet.
STATUS:    FROZEN at its first commit. The harness must pin this file's
           sha256 and refuse to run if it has changed.
SOURCE:    research/LITERATURE_2026-09_market_behaviour_change.md, rank 2
           -- CORRECTED here: see section 0
VEHICLE:   OANDA CFD USB10Y_USD (USB30Y_USD and DE10YB_EUR secondary)
```

*Measurement, not a recommendation. Not financial advice.*

---

## 0. The claim, and a correction to the literature report

Wang & Zhao, *Pre-Refunding Announcement Gains in U.S. Treasurys* (SSRN
4764295, under revision at RFS; sample Q4 1991 – Q4 2023, 129 events):
medium- and long-term Treasuries earn large returns on the trading day before
each quarterly refunding announcement. 10-year: **12.6 bp on pre-announcement
days against 1.8 bp on other days**; 30-year: 24.3 bp. Sharpe above 4 from
four days a year. The gain strengthened after 2002 as debt-to-GDP rose, is
about triple near debt-ceiling stress, and roughly **doubles when an FOMC
meeting precedes the announcement** (insignificant when it follows).
Mechanism offered: resolution of fiscal-supply uncertainty.

**Correction.** The literature report said "the day before each quarterly
refunding announcement" and was read as the Wednesday refunding statement.
The paper's event is the **Monday 15:00 ET primary release of marketable
borrowing estimates**, so the pre-announcement day is **normally a Friday**.
This pre-registration uses the paper's definition.

**Registered expectation.** G1 is plausible — thirty years of evidence and a
named mechanism. The post-paper check (about 11 events) cannot be more than a
sign. The confound most likely to kill it is a general Friday effect in
bonds, which G4 and the Friday term in the regression exist to catch.

## 1. Step 0 — the event table, built and frozen before any return is joined

- **Event day T** = the date of Treasury's quarterly "Marketable Borrowing
  Estimates" release (normally Monday, 15:00 ET), February, May, August and
  November, 2005 to 2026-08.
- **Source:** Treasury press releases and the quarterly-refunding archive at
  home.treasury.gov. Cross-checked against Wang & Zhao's event list where
  their paper or appendix gives one (2005-2023). Where the two disagree,
  Treasury's own date is used and every disagreement is listed.
- **Pre-announcement day P** = the last full trading day before T.
- Frozen as `flows/data/refunding_events.csv` (T, P, weekday of P, whether an
  FOMC announcement fell in the 5 trading days before T, debt-ceiling flag
  left blank — not used), sha256 recorded in the result. **No price is read
  while the table is built.**
- Expected size: about 87 events; about 76 inside the paper's sample, about
  11 after it (2024-Q1 onward).

## 2. Data

- USB10Y_USD M15 bid and ask from the Step 0 pull shared with FLOWS-1
  (`flows/data/`). USB30Y_USD and DE10YB_EUR if the pull returns them.
- Daily bars close at 17:00 New York, DST-aware, from mid prices. The bar
  dated P runs from 17:00 on the day before P to 17:00 on P, which for a
  Friday is Thursday 17:00 to Friday 17:00.
- FOMC dates from `fastbot/data/events.csv` (280 FOMC rows, sourced).
- Sample 2005-01 to 2026-08. Eras as in FLOWS-1.

## 3. Primary test

On every trading day t in the sample:

    r_t = c + d·PRE_t + e·EOM_t + g·FOMC_t + h·FRI_t + u      Newey-West SE (5 lags)

- PRE_t = 1 if t is a pre-announcement day P
- EOM_t = 1 in the last five trading days of the month (as the paper controls)
- FOMC_t = 1 on an FOMC announcement day or the day before
- FRI_t = 1 on Fridays — because P is almost always a Friday

The claim predicts **d > 0**.

## 4. Gates — thresholds fixed now

| gate | test | pass |
|---|---|---|
| **G1** replication | primary, 2005 – 2023-12 | d > 0 and t ≥ 2.0 |
| **G2** eras | primary in E1, E2, E3 | d > 0 in all three |
| **G3** post-paper | mean r on P, 2024-Q1 on | > 0 (sign only; about 11 events) |
| **G4** placebo | PRE moved to the same weekday one week earlier | t < 2.0 and d_placebo < d |
| **G5** vehicle and cost | trading rule below, net | mean net return per event > 0 |
| **G6** FOMC interaction (sign check, not a kill) | P preceded by FOMC vs not | mean(with FOMC) > mean(without) |

**G5 trading rule.** Buy USB10Y_USD at the ask of the first M15 bar after
the 17:00 NY rollover on the day before P; sell at the bid of the last M15 bar
before the 17:00 rollover on P. The position crosses **no rollover and pays no
financing** — which matters, because OANDA books weekend financing on Friday
for index CFDs and holding through Friday 17:00 would be charged three days.
The bond CFD's own days-charged table is read from the API and recorded, as
evidence the trade avoids it. Stress tests at +1 bp and +3 bp per side.

**Secondary, descriptive:** the same primary on USB30Y_USD (strongest in the
paper) and DE10YB_EUR (spillover). Monday up to 15:00 ET reported, not gated.

## 5. Kill conditions

- **K1** G1 fails.
- **K2** G4 placebo is as large as the primary — a Friday effect, not a
  refunding effect.
- **K3** G5 net ≤ 0.

## 6. Declared test count

Inferential: G1 and G4. Benjamini-Hochberg at q < 0.10. The rest is sign-only
or descriptive.

## 7. Files

    flows/data/refunding_events.csv   Step 0 table, sha256 recorded
    flows/refunding.py                harness — pins this file's sha256
    flows/RESULT_REFUNDING.md         result
