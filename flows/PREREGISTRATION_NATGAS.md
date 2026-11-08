# PREREGISTRATION FLOWS-6 — natural gas on EIA storage-report days

```
WRITTEN:   2026-09-26, before any natural-gas CFD bar has been pulled or
           read. No natgas bid/ask data, no event table and no harness exist.
STATUS:    FROZEN at its first commit. The harness must pin this file's
           sha256 and refuse to run if it has changed.
SOURCE:    research/LITERATURE_2026-09_market_behaviour_change.md, rank 7
VEHICLE:   OANDA CFD NATGAS_USD
```

*Measurement, not a recommendation. Not financial advice.*

---

## 0. The claim

Prokopczuk, Wese Simen & Wichmann, *The Natural Gas Announcement Day Puzzle*
(Energy Journal 42(2), 2021; SSRN 3575861): **more than half of the annual
return on natural gas futures is earned on the days the EIA publishes its
weekly storage report**. About half of that day's intraday return comes
**before** the 10:30 ET release, on days when storage later surprises. The
literature report marked the direction as unverified. The paper's abstract
gives it as positive, and it is registered here as positive.

This is the first natural gas test in the programme. pineport holds natgas
H1 mid prices but has never tested EIA dates. No overlap.

**Registered expectation.** Uncertain. The paper's sample predates 2020 and
nobody has checked it since. Natural gas CFDs carry wide spreads. The day
cannot be separated from "Thursday", because the report is almost always on a
Thursday. Either way the effect would be tradable, but it would be
mislabelled.

**Power, stated before the run.** About 950 report days after exclusions.
The day-return standard deviation of natural gas is about 3%, so the standard
error of the excess over other days is about 11 bp, and **t = 2 needs about
22 bp a day**.

## 1. Step 0 — data and the event calendar, both frozen before any return is computed

- **Pull:** NATGAS_USD M15 bid and ask, 2005-01-01 onward, into
  `flows/data/`, with `fastbot/scripts/pull_m1.py` (resumable). The first
  and last bar dates and the bar count are recorded in the meta file. If
  OANDA's history starts later than 2008-01, the sample starts at the first
  full month. If that leaves fewer than 10 years, the test is **void, not
  failed**.
- **Calendar (RULE):** `flows/data/eia_events.csv`, built by
  `fetch_eia_calendar.py` without any network access or price.
  - Report day = the Thursday of each Monday–Friday week, release 10:30 ET.
  - **Every week that contains a US federal holiday (observed date) on any
    weekday is excluded entirely**, from both the event group and the
    control group. In those weeks the EIA shifts the release by a day or
    two, and the true date is not on file. Special federal closures are
    treated the same way: 2007-01-02, 2012-10-29/30, 2018-12-05 and
    2025-01-09.
  - Weeks inside the federal shutdowns of 2013-10-01–10-16,
    2018-12-22–2019-01-25 and 2025-10-01–11-12 are excluded, because
    publication may have been disrupted.
  - Expected: about 48 report days a year, about 1,030 in 2005-01 to
    2026-08 before any data-start cut.

## 2. Data

- Trading date on the 17:00 New York rollover (`common.trading_date`).
- **Day return r_t** = mid close of the last M15 bar of trading date t
  divided by the mid open of its first bar, minus 1. This spans roughly
  18:00 ET the evening before to 17:00 ET, contains the 10:30 release, and
  **crosses no rollover**. So there is no financing. If OANDA rolls the
  underlying contract at the daily rollover, as assumed, the roll gap also
  falls outside the window. §6's gap list checks this assumption.
- Days with fewer than 40 bars are dropped and counted.
- Sample 2005-01-03 (or the first full month of data) to 2026-08-31, less
  the excluded weeks. Eras as in FLOWS-1.

## 3. Primary test

On every retained trading day t:

    r_t = a + b·EIA_t + u        Newey-West SE (5 lags)

EIA_t = 1 on a report day. The claim predicts **b > 0**.

## 4. Gates — thresholds fixed now

| gate | test | pass |
|---|---|---|
| **G1** premium | b, full sample | b > 0 and t ≥ 2.0 |
| **G2** eras, with a floor | b in E1, E2, E3 | > 0 in all three **and b_E3 ≥ 0.5 × b_full** |
| **G3** vehicle and cost | trade below, net | mean net > 0 with t ≥ 1.65, **and mean net in E3 > 0** |
| **G4** placebo | EIA moved to the Wednesday before (same weeks) | t_placebo < 2.0 and b_placebo < b |
| **G5** size | report days | ≥ 400 (this allows for a late data start) |

**G3 trade.** On each report day, buy NATGAS_USD at the **ask open** of the
first M15 bar of the trading date and sell at the **bid close** of its last
bar. Stress at +1 bp per side.

## 5. Kill conditions

- **K1** G1 fails.
- **K2** G2 fails.
- **K3** G3 fails.
- **K4** G4 placebo matches the primary. That would be a general
  mid-week effect, not the report.

## 6. Secondary, descriptive (gate nothing)

- Pre/post split: first-bar open → close of the bar ending 10:30 ET, and
  10:30 → last-bar close. The paper says about half comes before the
  release.
- Mean r by weekday, Monday to Friday, over retained weeks. This shows how
  much of any effect is simply Thursday.
- The quoted spread paid on the G3 trade, by era.
- The 20 largest absolute gaps from one M15 close to the next M15 open
  within a trading date. These are listed with dates so that any roll
  artefact inside the window would be visible. The list is not used to
  exclude anything.

## 7. Declared test count

Inferential: G1 and G4. Benjamini-Hochberg at q < 0.10. The rest is sign-only
or descriptive.

## 8. Files

    flows/fetch_eia_calendar.py    Step 0 calendar (offline, deterministic)
    flows/data/eia_events.csv      frozen, sha256 recorded
    flows/data/natgasusd_{bid,ask}_15m.csv   pulled on the Mac
    flows/natgas.py                harness — pins this file's sha256
    flows/RESULT_NATGAS.md         result
