# PREREGISTRATION PAIRS1: intraday relative value between US index CFDs (a non-directional scalp)

Frozen 2026-10-07, before any pair statistic has been computed. Harness: `scripts/pairs1_run.py` (frozen by sha before it runs).

I am not a financial adviser. This is a measurement, not a recommendation.

## Idea
SPX500, NAS100 and US30 move together. When one runs ahead of another during the day, does the gap close by the end of the session? This bets on the gap, not on market direction (one leg long, one short).

## Definition (fixed)
- **Data:** OANDA 15-minute bid/ask (`data/v24`), 2005 → 2026-09-25; US cash session; mid prices for signals, bid/ask for costs. Pairs (A, B): SPX500–NAS100, SPX500–US30, NAS100–US30.
- **Hedge ratio β:** OLS slope of A's 15-minute returns on B's over the previous 20 sessions (cash session only).
- **Gap x_k** at bar k = ln(A close_k / A open 09:30) − β · ln(B close_k / B open 09:30).
- **z_k** = x_k / SD of x at the same bar over the previous 20 sessions (at least 15 needed).
- **Entry:** the first bar from 10:00 to 14:45 (bar start) whose close has |z| ≥ 2.0; trade at the next bar's open: short A / long β·B if z > 0, the reverse if z < 0. One trade per pair per day.
- **Exit:** close of the 15:45 bar (16:00). No overnight positions, so no financing.
- **Return** (bp of A's notional) = −sign(z) · [(A exit / A entry − 1) − β (B exit / B entry − 1)] minus costs: half the quoted spread on each leg at entry and at exit (B's scaled by β).

## Gates (per pair; Bonferroni over 3 pairs)
- **G1:** mean net > 0 with t ≥ 2.4 (one trade per day, so day-level).
- **G2:** positive in each era 2005–12, 2013–19, 2020–26.
- **G3:** at least 200 trades.
- PASS needs all three. Recent-regime route (POLICY_RECENT_REGIME) applies if only 2005–12 fails.

## Prediction
FAIL on all three: these indices are arbitraged continuously, and two spreads must be paid.

## One run.
