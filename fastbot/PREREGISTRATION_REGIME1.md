# PREREGISTRATION — REGIME1: does a moving-average "overall direction" filter tell direction, and do patterns taken with it work?

```
STATUS:   frozen before any REGIME1 or SESSION1 number is computed (sha in PROVENANCE.md)
WRITTEN:  2026-10-09
DATA:     daily cash closes from daily_close.py (SPX500, NAS100, UK100, XAUUSD; 2005 -> 2026-09-25);
          trade-level output of SESSION1 (same commit).
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## Why
The common advice is: "find the overall direction first, using a moving average, a crossover or higher-timeframe structure, and only take patterns in that direction." Two questions follow, and we test them separately:
- **Q1:** does the filter *tell direction* at all?
- **Q2:** do patterns taken *with* the filter make money beyond what the filter gives on its own?

The second part matters because indices drift upward. A filter that is long 75% of the time will make any long-biased pattern look better. The honest comparison is against random entries filtered the same way.

Earlier related tests:
- **v52:** 200-day MA as a risk overlay. It cut drawdowns but showed no Sharpe timing.
- **TSMOM1:** 12-month trend. Sharpe 0.38, t 1.73.

Neither asked Q1 directly, and neither asked Q2 at all.

## Filters (state known at the cash close of day d, used from day d+1)
| | filter | "up" when |
|---|---|---|
| F1 (primary) | price vs 200-day SMA | close > SMA200 |
| F2 | golden / death cross | SMA50 > SMA200 |
| F3 | fast crossover | EMA20 > EMA50 |
| F4 | 12-month trend | close > close 252 days earlier |
| F5 | 200-day slope | SMA200 today > SMA200 20 days earlier |

## Q1 — does it tell direction?
- **Returns:**
  - next-day close-to-close return (h = 1);
  - next 5-day return, non-overlapping: every 5th trading day starting from the first valid day (h = 5).
- **Statistic:** b in the pooled regression r = instrument intercepts + b·Up, with SEs clustered by date. b is the difference in average return between up-state and down-state days.
- **Gates per filter × horizon (10 tests; Bonferroni t ≥ 2.81). All must pass:**
  - b > 0 and t ≥ 2.81;
  - b > 0 in each era 2005–12, 2013–19, 2020–26;
  - b > 0 on at least 3 of 4 instruments.
- **Reported:**
  - share of days in the up state;
  - hit rate (sign of next return matches the state) against the always-long hit rate;
  - mean return in up and down states;
  - vol in each state.

## Q2 — do patterns taken with the filter work?
- **Input:** every SESSION1 trade and its random-entry partners (Part B, 30m and 1h, 42 tests each; Part A, BOS and CHoCH, k = 3).
- **Aligned trades:** a trade is "aligned" if it is long in the F1 up state or short in the F1 down state. The state used is the one at the last cash close before the trade's date.
- **Random partners:** filtered by the same rule, using their own dates and sides.
- **Gates for an aligned test (all must pass):**
  - net mean > 0 with t ≥ 3.4 (Part B) or ≥ 2.24 (Part A k = 3), date-clustered;
  - beats the aligned random partners with t ≥ 2;
  - > 0 in every era;
  - n ≥ 200.
- **Reported, no gate:**
  - the same tests under F2;
  - the counter-trend subset;
  - "filter lift" = (aligned − counter) for the pattern minus (aligned − counter) for its random partners. This is the part of the improvement owed to the pattern rather than to the filter.

## What each outcome means
- **Q1 fails for all filters:** moving averages do not tell next-day or next-week direction better than chance on these markets. Their known value is drawdown control (v52), not direction.
- **Q1 passes:** that filter becomes a candidate *bias input* for later tests. A pass is not a trading rule.
- **A Q2 PASS:** the pattern is a lead for a fresh pre-registration with a forward record, not money.
- **Q2 shows aligned trades better than counter, but no better than aligned random:** the filter is doing the work, not the pattern.
