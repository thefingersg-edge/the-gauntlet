# PREREGISTRATION STRAT1: one strategy combining every trigger the programme has evidence for

Frozen 2026-10-03, after PEAD1 and **before** PEAD2, PEAD3 and INSIDER1 were run. Harness: `singlestock/batch2_run.py strat1`, which pins this file.

I am not a financial adviser. This is a measurement, not a recommendation.

## Honest status, stated before the run
- The EAR component's full-sample behaviour is already known from PEAD1. A backtest of this strategy is therefore **partly in-sample**.
- Its rules are fixed **here**, from prior evidence, with **no tuning**, and are not changed after the PEAD2, PEAD3 or INSIDER1 results.
- **The decisive test is the forward record** (see the end).

## The strategy (all rules fixed now)
**Universe:** US domestic common stocks, M+S liquidity bands, priced ≥ $5.

**Triggers (event and price):**
1. **EAR:** top-decile 3-day reaction to the results announcement (PEAD1 signal). Known at the close of k+1.
2. **SUE:** the 10-Q/10-K earnings surprise in the top decile of SUEs filed in the prior 91 days. Known on the filing date.
3. **Insider cluster** (INSIDER1 definition). Known on the filing date.

**Book:**
- **20 slots**, equal weight (5% of equity each). Hold 60 trading days, then sell.
- When more signals arrive than free slots, priority is: insider cluster > EAR-and-SUE on the same stock within 60 days > EAR > SUE. Ties go to the larger signal value. **A stock already held is not bought again.**
- **Execution:** closing auction on the trading day after the signal is known. Exit in the closing auction.
- **Cost:** 25% of EDGE plus commission (the PEAD2 auction model). Also reported at 100%.

**Market risk overlay (from the index work: v52 200-day MA, v50/v53 VIX rule):**
- **No new entries** while SPX500's close is below its 200-day average, **or** VIX is in the top fifth of its prior 250 days (both as of the previous close).
- Positions already held run to their 60-day exit.
- Idle cash earns 0.

**Two versions:**
- **(a) Long-only:** what a cash account earns.
- **(b) Hedged:** each position's return minus its band benchmark (an index-hedged book). The hedge cost is not charged.

## Gates (2008-03 → 2026-09, when all three triggers exist)
- **G1, hedged (b):** calendar-time Sharpe ≥ 0.5 on 2008–26, **and** ≥ 0.5 on 2018–26.
- **G2, long-only (a):** Sharpe greater than the equal-weight M+S benchmark's Sharpe, **and** max drawdown smaller than the benchmark's, on 2008–26 and on 2018–26.
- **G3, eras:** the hedged net return is positive in 2008–12, 2013–19 and 2020–26.

## Reported (not gated)
- 10 and 40 slots.
- Each trigger's contribution.
- No overlay.
- Turnover and average positions held.
- Cost at 100% of EDGE.

## Budget
- About 18.5 years. **A Sharpe ratio's SE is about 0.23.** With 20 slots and a 60-day hold, the book is usually full (there are thousands of signals a year).
- Sharpe gates, not t-statistics, because this is a portfolio test.

## Forward record (the decisive test)
From the first trading day after this result, the strategy is run on paper each day from new Sharadar data.
- Every signal, its execution price (closing auction) and, once Dave has a share-broker account, real fills are logged in `data/strat1_forward.csv`.
- **Verdict at 250 trading days; interim look at 125.**

## One run.
