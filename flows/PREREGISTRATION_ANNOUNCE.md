# PREREGISTRATION FLOWS-4 — the macro-announcement day premium, when VIX is high

```
WRITTEN:   2026-09-26, before any index return on any announcement day has
           been joined to a VIX state on OANDA data. No FLOWS-4 event table
           and no harness exist yet.
STATUS:    FROZEN at its first commit. The harness must pin this file's
           sha256 and refuse to run if it has changed.
SOURCE:    research/LITERATURE_2026-09_market_behaviour_change.md, rank 4
VEHICLE:   OANDA CFD SPX500_USD (DE30_EUR secondary)
```

*Measurement, not a recommendation. Not financial advice.*

---

## 0. The claim, and what this project already knows

Ai, Bansal & Guo, *Macroeconomic Announcement Premium* (NBER w31923, sample
1961–2023; a survey of their own and others' work): on days with FOMC,
payrolls, GDP, ISM manufacturing or CPI/PPI releases, the US market earns
**about 10.7 bp a day on average, against about 0.9 bp on other days**.
Roughly 44 announcement days a year carry most of the equity premium. Hu,
Pan, Wang & Zhu (JFE 2022) and Fisher, Martineau & Sheng (RFS 2022) find
the premium is **larger when uncertainty is high before the release**.

**Overlap, stated first.** fastbot v10 (`RESULT_PREANN.md`) tested the
*pre-announcement* window (T−24h to T−1h) on CPI, NFP and FOMC. FOMC paid
(+24.5 bp excess, t 3.1, and more on high-VIX days, Gate D). CPI and NFP did
not (−1.9 and −7.5 bp), and v14 (`RESULT_SESSION.md`) confirmed CPI's
day-before session pays nothing. So:

- **FOMC is excluded from the primary.** Its premium is already measured.
  FOMC days are a control dummy and reported only.
- The primary is the **non-FOMC announcement day**, measured over the whole
  trading date: this includes the release itself and the session after it,
  which v10 and v14 never measured. For an 08:30 release, part of this window
  (18:00 the evening before to 08:30) overlaps v10's pre-window, which was
  flat for CPI and NFP. If FLOWS-4 passes, the pre/post split (section 5)
  shows where the money was made.
- This is not a fourth parameter on v10: different window (the day, not the
  run-up), different event set (GDP and ISM added, FOMC removed) and a
  different claim (a premium for bearing the release, not for waiting for it).

**Registered expectation.** Doubtful. v10 found CPI and NFP pay nothing
before release, and fastbot's release work (v22, v35) found the post-release
move reverts and that shocks do not continue. The most likely outcome is
that G1 fails. A pass would contradict two earlier fastbot results, and the
pre/post split must then explain the difference.

**Power, stated before the run.** Roughly 1,000 non-FOMC announcement days,
about half with high VIX. With an SPX within-day standard deviation near
1.5% on high-VIX days, the standard error of the excess is about 7 bp, so
**t = 2 needs an excess of about 14–15 bp**. The published unconditional
premium (about 10 bp) sits below that. A true effect of the published size
would most likely fail G1. The test can see a premium only if VIX
conditioning makes it larger, which is the claim being tested.

## 1. Step 0 — the event table, built and frozen before any return is joined

`flows/data/announce_events.csv`, one row per (date, event), columns
`event,date,time_et,quality,source`. sha256 recorded in the result.
**No price is read while the table is built.**

| event | dates | time ET | source |
|---|---|---|---|
| CPI | `fastbot/data/events.csv` rows, as frozen (sha256 recorded) | 08:30 | ALFRED rid=10 via event_table.py |
| NFP | `fastbot/data/events.csv` rows | 08:30 | ALFRED rid=50 |
| GDP | every release of ALFRED rid=53, title verified as "Gross Domestic Product" before any date is read | 08:30 | ALFRED |
| ISM | RULE: the first US business day of each month (a weekday that is not a US federal holiday) | 10:00 | ISM's published practice; quality `RULE` |
| FOMC | `fastbot/data/events.csv` | 14:00 (14:15 before 2013-04) | control only |

PPI is not included (the paper uses "CPI or PPI, whichever is earlier"; this
test uses CPI only, since that is what is on file). Expected sizes for
2005-01 to 2026-08: CPI ≈ 260, NFP ≈ 260, GDP ≈ 195, ISM ≈ 260, of which some
coincide. A GDP year with fewer than 11 or more than 13 releases is a parse
failure (the 2013 and 2018–19 shutdowns may move or merge releases; that is
allowed, and each such year is listed).

## 2. Data

- SPX500_USD and DE30_EUR M15 bid and ask, `fastbot/data/v24/` (the
  forward_tick files; truncated at 2026-08-31 by the harness).
- VIX: `fastbot/data/VIXCLS.csv` (FRED VIXCLS), sha256 recorded.
- Trading date: 17:00 New York rollover, DST-aware (`common.trading_date`).
- **Day return r_t** = mid close of the last M15 bar of trading date t,
  divided by the mid open of its first bar, minus 1. This spans roughly
  18:00 ET the evening before to 17:00 ET on t, contains every release in
  the table, and **crosses no rollover** (no financing, no dividend
  adjustment at the roll).
- Days with fewer than 40 bars are dropped (holidays, broken sessions); the
  count is reported.
- Sample 2005-01-03 to 2026-08-31. Eras as in FLOWS-1: E1 2005-01–2012-03,
  E2 2012-04–2019-06, E3 2019-07–2026-08.

## 3. Definitions

- **A_t** = 1 if trading date t is a CPI, NFP, GDP or ISM date and is **not**
  an FOMC statement date.
- **FOMC_t** = 1 on an FOMC statement date.
- **HIGH_t** = 1 if VIX on the last calendar date before t that has a value
  is above the median of the 252 VIX values ending on that date. Known before
  t opens. No look-ahead.

## 4. Primary test

On every trading day t:

    r_t = a + b1·A_t + b2·HIGH_t + b3·A_t·HIGH_t + g·FOMC_t + u      Newey-West SE (5 lags)

**θ = b1 + b3**, the announcement-day excess on high-VIX days. The claim
predicts **θ > 0** and **b3 > 0**.

## 5. Gates — thresholds fixed now

| gate | test | pass |
|---|---|---|
| **G1** premium | θ, full sample | θ > 0 and t ≥ 2.0 |
| **G2** eras, with a floor | θ in E1, E2, E3 | θ > 0 in all three **and θ_E3 ≥ 0.5 × θ_full** |
| **G3** conditioning | b3, full sample | b3 > 0 |
| **G4** vehicle and cost | trade below, net | mean net > 0 with t ≥ 1.65, **and mean net in E3 > 0** |
| **G5** size | count of A∧HIGH days | ≥ 150 |

**G2's floor is new, and comes from FLOWS-2.** FLOWS-2 passed a sign-only era
gate with an E3 effect of 1.3 bp against 18.7 bp in E1. A gate that a
decayed effect can pass is not a gate. From here on the recent era must
carry at least half the full-sample effect.

**G4 trade.** On each A∧HIGH day, buy SPX500_USD at the **ask open** of the
first M15 bar of the trading date and sell at the **bid close** of its last
bar. No rollover is crossed, so no financing. Stress at +1 bp per side.

## 6. Kill conditions

- **K1** G1 fails.
- **K2** G2 fails (including the E3 floor).
- **K3** G4 fails.

G3 failing with G1 passing means an unconditional premium, not an
uncertainty premium. That is reported as such, and it is not a pass of the
claim as registered.

## 7. Secondary, descriptive (gate nothing)

- θ per event type (CPI, NFP, GDP, ISM), Benjamini-Hochberg at q < 0.10 over
  the four.
- The low-VIX excess b1.
- FOMC: mean r on FOMC days, high and low VIX (compare with fastbot v10).
- Pre/post split on the 08:30 releases: open → 08:30 bar start, and 08:30 →
  close.
- DE30_EUR: the same primary regression and θ.

## 8. Declared test count

Inferential: G1. The per-type θ are four more tests, controlled by BH. The
rest is sign-only or descriptive.

## 9. Files

    flows/fetch_announce.py            Step 0: GDP from ALFRED, ISM rule, merge with events.csv
    flows/data/announce_events.csv     frozen table, sha256 recorded
    flows/announce.py                  harness — pins this file's sha256
    flows/RESULT_ANNOUNCE.md           result
