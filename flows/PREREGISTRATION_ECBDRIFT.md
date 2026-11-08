# PREREGISTRATION FLOWS-5 — the 20-day DE30 drift after ECB decisions

```
WRITTEN:   2026-09-26, before any DE30 return around any ECB decision has
           been computed on OANDA data. No ECB date table and no harness
           exist yet.
STATUS:    FROZEN at its first commit. The harness must pin this file's
           sha256 and refuse to run if it has changed.
SOURCE:    research/LITERATURE_2026-09_market_behaviour_change.md, rank 5
VEHICLE:   OANDA CFD DE30_EUR (DE10YB_EUR used only to classify shocks)
```

*Measurement, not a recommendation. Not financial advice.*

---

## 0. The claim

Valentin, *The Post-ECB Announcement Drift* (working paper, May 2022; AEA
2023 programme; 194 announcements, 2002–2020; no costs): euro-area equities
keep moving **in the direction of their announcement-window reaction for up
to 20 trading days**. After 20 days on the Euro STOXX: regular monetary
shocks **+107 bp after positive, −41 bp after negative**; information shocks
(stocks and short rates move the same way) **+168 bp after positive, −114 bp
after negative**. A long-only rule that steps aside after negative shocks
returns 4.6% a year with a Sharpe of 0.43.

Nothing in this programme has tested ECB dates or any 20-day event drift.
No overlap.

**Registered expectation.** Doubtful. It is a single, unreplicated working
paper whose sample ends in 2020. Post-announcement drifts are the kind of
price-pattern edge the decay literature says has been arbitraged away. A
20-day hold also pays about 20 days of CFD financing.

**Power, stated before the run.** About 190 scheduled decisions fit the
sample. The standard deviation of DE30's 20-day return is about 6%, so the
standard error of the signed mean is about 45 bp, and **t = 2 needs a signed
drift of about 90 bp**. The paper's figures imply about 75 bp for regular
shocks and about 140 bp for information shocks. The test can find the
information-shock effect at the published size, but it will struggle to
find the regular-shock effect at that size.

## 1. Step 0 — the decision table, built and frozen before any return is joined

`flows/data/ecb_events.csv`: `date,time_cet,scheduled,source_url,note`.
sha256 recorded in the result. **No price is read while it is built.**

- One row per **scheduled** Governing Council monetary policy meeting whose
  decision was published as the ECB press release "Monetary policy
  decisions", 2005-01 to 2026-08.
- **Excluded as unscheduled:** the 2008-10-08 coordinated cut, the
  2020-03-18 evening PEPP announcement, the 2022-06-15 ad hoc meeting, and
  any other decision not made at a scheduled monetary policy meeting.
- **Decision time τ:** 13:45 CET/CEST up to and including June 2022; **14:15
  from the July 2022 meeting** (ECB press release of 27 June 2022). The press
  conference follows 45 minutes later in the old regime and 30 minutes later
  from July 2022.
- Source: the ECB website's press-release listings. Year counts are checked:
  2005–2014 monthly schedule (10–13 a year), 2015 onward 8 a year. Any
  decision date that is not a Thursday is listed for review. These are not
  dropped automatically.

## 2. Data

- DE30_EUR M15 bid and ask, `fastbot/data/v24/`. DE10YB_EUR M15 bid and ask,
  `flows/data/`.
- M15 bar start times are UTC and are converted to Europe/Berlin
  (DST-aware).
- Trading dates on the 17:00 New York rollover (`common.trading_date`). The
  announcement's trading date D is the one containing τ.
- Financing: `flows/data/financing_snapshot.json` DE30_EUR, benchmark ECB
  deposit rate (`fred_ecbdfr.csv`), the `common.Financing` model.
- Sample: decisions from 2005-01 whose D+20 falls on or before 2026-08-31.

## 3. Definitions

- **Reaction window:** DE30 mid from the close of the M15 bar ending at τ
  to the close of the M15 bar ending at τ + 120 minutes. This covers the
  decision and the whole press conference in both regimes.
- **s** = sign of the reaction. Events with a reaction of exactly 0, or with
  missing bars in the window, are dropped and counted.
- **Information shock:** the DE30 reaction and the DE10YB_EUR price
  reaction over the same window have **opposite** signs. A Bund price move
  opposite to equities means yields moved with equities. **Monetary shock:**
  the same sign.
- **Drift:** R = DE30 mid close of the last bar of trading date D+20
  divided by the mid close of the last bar of D, minus 1. D+k counts DE30
  trading dates.
- **Signed drift** y = s × R.

## 4. Primary test

Mean of y over all events, t-statistic with Newey-West (1 lag). Events are
at least four weeks apart, so the 20-day windows overlap only slightly.

The claim predicts **mean y > 0**.

## 5. Gates — thresholds fixed now

| gate | test | pass |
|---|---|---|
| **G1** drift | mean y, all events | > 0 and t ≥ 2.0 |
| **G2** eras, with a floor | mean y in E1, E2, E3 | > 0 in all three **and E3 ≥ 0.5 × full** |
| **G3** vehicle and cost | trade below, net | mean net > 0 with t ≥ 1.65, **and mean net in E3 > 0** |
| **G4** placebo | the same construction anchored on the Thursday one week before each decision, same clock | t_placebo < 2.0 and mean y_placebo < mean y |
| **G5** size | events | ≥ 150 |

**G3 trade.** At the last M15 bar of D, go long at the ask close if s > 0,
or short at the bid close if s < 0. Exit at the last bar of D+20 on the
opposite side. Charge financing for the 20 rollovers held, by side, with the
Friday rollover charged three days (DE30's days-charged table). Stress at
+1 bp per side.

The E3 floor in G2 and G3 is the FLOWS-2 lesson, stated in
PREREGISTRATION_ANNOUNCE.md §5.

## 6. Kill conditions

- **K1** G1 fails.
- **K2** G2 fails.
- **K3** G3 fails. The drift exists but does not pay for 20 days of
  financing.
- **K4** G4 placebo matches the primary. That would be a general 20-day
  momentum in DE30, not an ECB effect.

## 7. Secondary, descriptive (gate nothing)

- Mean y for information shocks and for monetary shocks separately. The
  paper predicts information > monetary.
- Signed drift at 5 and 10 days.
- Positive-shock and negative-shock drifts separately (unsigned R), to
  compare with the paper's asymmetry.
- The paper's long-or-flat rule, net of financing, against buy-and-hold DE30
  over the same days.

## 8. Declared test count

Inferential: G1 and G4. Benjamini-Hochberg at q < 0.10. The rest is sign-only
or descriptive.

## 9. Files

    flows/fetch_ecb.py            Step 0: ECB decision dates (run on the Mac)
    flows/data/ecb_events.csv     frozen table, sha256 recorded
    flows/ecbdrift.py             harness — pins this file's sha256
    flows/RESULT_ECBDRIFT.md      result
