# PREREGISTRATION v58: do currencies earn a premium against the dollar on FOMC days? A measurement, not a backtest

Written and frozen 2026-10-02, before any FX return has been computed on any FOMC or non-FOMC day. The only things read so far:
- each FX file's first and last timestamp;
- the FOMC rows of data/events.csv (dates, time stamps, quality flags).

Harness: scripts/fomcfx_v58.py v1.0. I am not a financial adviser. This is a measurement, not a recommendation.

## 1. Why
- **Mueller, Tahbaz-Salehi & Vedolin** ("Exchange rates and monetary policy uncertainty", J. Finance 2017), 1994–2010, 136 scheduled FOMC days:
  - Short USD against nine G10 currencies (DOL) earned **+12.45 bp** on FOMC days against +0.35 bp on other days. Difference +12.10 bp, t 2.34.
  - About 75% of it came before the 2:15 pm announcement.
  - The high-interest third earned +15.17 bp more on FOMC days (t 2.43).
- They read it as **compensation for monetary-policy risk** borne by constrained intermediaries. That makes it a premium, the one class of effect this programme has found to survive (PROGRAMME.md §3, §11).
- It also passes Rule 6 on paper: OANDA major-FX spreads are about 1–2 bp a side against a 12 bp effect, and the hold is one day.
- **Not tested before in this tree.** The FOMC work so far is the pre-FOMC *equity* drift (KUROV: replicated, dead after 2015), FOMC as a timeline event (v37–v41), and the release fade (v25, CPI/NFP only).

## 2. Data
- **OANDA M15 bid and ask, timestamps UTC, bar-start stamped:**
  - EUR_USD from fastbot/data/v24;
  - GBP, AUD, NZD (vs USD) and USD vs CAD, CHF, JPY, NOK, SEK from flows/data.
  - These are nine currencies, the paper's nine.
- **FOMC dates:** fastbot/data/events.csv, rows with event = FOMC.
  - **Announcement day rule, fixed now:** the table lists both days of some two-day meetings (e.g. 2008-01-29 and 2008-01-30). When two FOMC rows fall on consecutive calendar days, only the later one is kept.
  - The table holds scheduled meetings only. Unscheduled moves such as 2008-01-22 and 2008-10-08 are absent, as the paper requires.
  - The harness prints the deduplicated count per year.
- **Sample:** FOMC days 2005-01-01 → 2026-09-30.

## 3. Definitions
- **Day d's return for currency i:**
  - from the mid close of the 15:45 ET bar on the previous NY weekday that has one, to the mid close of the 15:45 ET bar on d;
  - mid = (bid close + ask close) / 2;
  - expressed as a long foreign currency / short USD log return in bp, so USD-base pairs are sign-flipped.
  - Paper's analogue: 4 pm ET to 4 pm ET.
- **DOL(d):** the equal-weight mean over currencies with a return on d. A day needs at least 7 of the 9.
- **FOMC(d) = 1** on deduplicated announcement days.
- **Pre / post split (reported):** previous day 15:45 close → 13:45 bar close on d (before every 14:00/14:15 statement), and 13:45 close → 15:45 close on d.
- **Cost:** per currency, (ask − bid) / mid at the entry close plus the same at the exit close, each halved. That is a round trip crossing half the spread each way, averaged over the currencies used, in bp. Financing is not modelled: one 17:00 ET rollover is at most about ±1.5 bp at G10 rate gaps, and its sign depends on the currency.
- **SEs:** heteroskedasticity-robust (HC1) OLS. Daily returns do not overlap.

## 4. Primary sample: post-publication-sample, 2011-01-01 → 2026-09-30
- The paper's data end on 2010-12-31, so every FOMC day used for the gates is out of the paper's sample.
- About 125 scheduled announcements.

## 5. Gates. PASS needs all three.
- **G1:** in OLS DOL ~ 1 + FOMC over 2011–2026, the FOMC coefficient is > 0 with HC1 t ≥ 2.0.
- **G2, eras and decay:** the coefficient is > 0 in 2011–2018 and in 2019–2026 separately, **and** the 2019–2026 coefficient is at least half the 2011–2026 one (the FLOWS-4 rule).
- **G3, net:** over 2011–2026 FOMC days, mean DOL minus mean round-trip cost is > 0.

## 6. Reported, gating nothing
- **Replication window 2005–2010** (inside the paper's sample): the coefficient and t. The paper's full-sample figure is +12.10 bp.
- Pre/post-announcement split of the FOMC-day mean.
- Per currency, the FOMC coefficient over 2011–2026.
- AUD+NZD (commodity/high-yield) minus JPY+CHF (funding) on FOMC days. This is a fixed bucket, not a rate sort.
- The FOMC-day DOL standard deviation against other days.
- A permutation check: the FOMC dummy reassigned to random non-FOMC days within the same calendar year, 2,000 draws, seed 58. One-sided p.

## 7. Budget and prediction, written now (no returns read)
- **Budget:** a DOL daily standard deviation of about 40–55 bp (published G10 dollar-factor vol of about 7–8% a year) puts the SE on about 125 events near 4–5 bp. An undecayed +12 bp gives t ≈ 2.5–3. **A halved effect is not detectable** (t ≈ 1.3).
- **Prior:** six published timing effects replicated in their era here and decayed afterwards. This one is framed as a premium, not timing, but it is still a published, dated, easily traded rule.
- **Prediction:** 2005–2010 positive, near the paper's size. **G1 FAIL** for 2011–2026, with the coefficient below +6 bp.

## 8. What follows
- **PASS:** a recording-only forward ledger of DOL on FOMC days, added to forward_tick.sh as a non-fatal step under its own pre-registration. Eight events a year means about 4 years to a forward verdict. That is written now.
- **FAIL:** closed under Rule 2. The pre-FOMC family (KUROV, v58) is then closed in both equities and FX.

## One run. No change of currencies, window, dedup rule, sample or gates.
