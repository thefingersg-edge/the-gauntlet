# PREREGISTRATION INSIDER1: clusters of open-market insider buying

Frozen 2026-10-03. Harness: `singlestock/batch2_run.py insider1`, which pins this file. Events come from `ss_events2.insider_buys` / `insider_clusters` on the Sharadar insiders table. Budget: `singlestock/budget_batch2.py`, log `data/budget_batch2.log` (counts and RMS only).

I am not a financial adviser. This is a measurement, not a recommendation.

## Question
- When several company insiders buy their own stock on the open market at about the same time, does the stock outperform afterwards?
- The literature finds yes, especially in small firms: Lakonishok & Lee 2001; Cohen, Malloy & Pomorski 2012.
- **This trigger has never been looked at in this programme.**

## Definition
- **Purchases:** Form 4, transaction code P (open-market purchase), by an officer or director, dated by the **filing date**.
- **Cluster:** at least 2 distinct insiders buying within 10 calendar days (by filing date), with a total value of at least $100k. At most one signal per ticker per 60 days.
- **Built:** 17,219 clusters, 2008–2026. The insider data effectively starts in 2008.
- **Entry:** the **open** after the filing that completes the cluster. **Hold:** 60 trading days. **Return:** excess over the band.
- **Cost:** full EDGE spread plus commission (as PEAD1).
- **Eras:** 2008–12, 2013–19, 2020–26.

## Gates (single test, t ≥ 2.0, quarter-clustered)
- **G1:** M+S net > 0, t ≥ 2.0.
- **G2:** net > 0 in every era, **and** 2018–26 net > 0 with t ≥ 2.0.
- **G3:** net > 0 in M and S.
- **G5:** calendar-time excess Sharpe ≥ 0.5 on 2018–26.

## Reported (not gated)
- L band.
- Closing-auction execution at 25% cost.
- Single-insider purchases (no cluster) as a contrast.
- CEO/CFO-involved clusters.
- 20-day hold.

## Budget
- 11,785 clusters have a full outcome. M+S: 2,816 / 3,851 / 3,677 by era, and 4,828 on 2018–26.
- 60-day excess RMS is 20–27%. **MDE is about 1.0–1.3% (event level), larger when clustered.** Literature effects are several percent over six months.

## Prediction
G1 PASS gross. Net is uncertain: insider-cluster stocks are small, so their spreads are wide.

## One run.
