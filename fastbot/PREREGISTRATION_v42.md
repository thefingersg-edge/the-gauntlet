# PREREGISTRATION v42 — does intraday momentum live on days when dealers are short gamma?

Frozen 2026-09-27. The budget read counts and squared returns only; no signed return split by GEX has been read.
Script: scripts/gex_v42.py v1.0.

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. The mechanism, tested with the real input for the first time
- Baltussen, Da, Lammers & Martens (JFE 2021) and Barbon & Buraschi (*Gamma Fragility*) say intraday momentum comes from option dealers who are **short gamma**: their hedging buys rallies and sells dips.
- v36 G and v38 B could only use a VIX stand-in, and it pointed the wrong way. Here the input is SqueezeMetrics GEX, the dealer gamma exposure estimated from S&P options open interest.
  - File: data/gex/DIX.csv, downloaded by Dave on 2026-09-27, sha256 b64bccce…
  - Coverage: 2011-05-02 → 2026-09-25, 3,874 days; GEX < 0 on 9% of them.

## 2. Timing (no look-ahead)
- GEX is an end-of-day number, so day d uses **the last GEX dated before d**.
- A self-test plants a same-day value and checks that it is never used.

## 3. Tests (SPX500, NAS100, US30, OANDA 5m bid/ask, 2011-05-03 → 2026-08-14)
- **H1, last-30-minute momentum:** the sign of the prior 15:55 close → 15:30 open return sets a 15:30 open → 15:55 close trade (v36 G's rule, without the VIX filter).
- **H2, noise-band rule N (v36), per instrument-day:** unchanged.
- **Split:** negative-GEX days (prior-day GEX < 0) against positive-GEX days.

## 4. Gates (two tests, Bonferroni t ≥ 2.24; SEs clustered by date)
PASS for each H requires all of:
1. gross(negative) − gross(positive) > 0 with t ≥ 2.24;
2. gross on negative-GEX days > 0;
3. the negative-minus-positive difference > 0 in at least 2 of the 3 eras (2011–16, 2017–21, 2022–26). Negative-GEX days cluster in 2022 (104) and 2018/2020, so all three eras are not required.

Net of spread on negative-GEX days is reported, gating nothing.

## 5. Budget and blind spots
- **H1:** 1,022 negative-GEX instrument-days on 341 dates; RMS 30.7 bp; MDE for the difference about 5.3 bp.
- **H2:** 731 on 285 dates; RMS 56.5 bp; MDE about 10.8 bp.
- H2 can only see a large effect. H1 is the informative test.
- **Blind spots:**
  - GEX is SqueezeMetrics' estimate (their assumptions about which side dealers hold), not an observed dealer book.
  - The momentum rules were already run on these years (v35/v36), unconditioned. Only the conditioning on GEX is new, so this is less than a fully blind test.
  - v38 B found momentum weaker on stressed days. Negative GEX often coincides with stress, so the prior is honestly mixed.

## 6. One run.
