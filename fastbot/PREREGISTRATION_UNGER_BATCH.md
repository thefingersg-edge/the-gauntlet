# PREREGISTRATION — UNGER BATCH: PROBE1-OIL, GOLDTREND1, CONTEXT1, MULTI1, ROTATE1, TURBO1

```
STATUS:   frozen before any number in this batch is computed (sha in PROVENANCE.md). Each test is run ONCE, in the order listed.
WRITTEN:  2026-10-09
CONTEXT:  fastbot/UNGER_PUZZLE.md. These test public principles attributed to Andrea Unger (youtube/course1/UNGER_NOTES.md) on our markets and costs.
          They are generic textbook rules chosen in advance, NOT his proprietary systems.
DATA:     OANDA 15m bid/ask (struct15 caches): SPX500, NAS100, UK100, XAUUSD; WTI/Brent once Saturday's pull lands. End 2026-09-25.
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## Shared rules (apply to every test below)
- **Trading day:** 17:00 → 17:00 New York, as in PROBE1.
  - **Clean days (new; learnt from PROBE1's gold data issue):** drop weekend labels and any day with fewer than 50% of that market's median bars per day. A dropped day's bars are removed before any level is computed.
- **Prices:** OHLC from mid 15m bars. Entries "at the next open" use the first bar of the next clean day.
- **Costs, CFD route (primary):**
  - the full quoted spread at the bar of each position change (half to exit, half to enter);
  - financing at each 17:00 roll held: longs pay policy rate + 2.5%, shorts receive policy rate − 2.5%, Friday counts 3 nights;
  - policy rates: USD (GBP for UK100).
  - Index spreads before 2012 are missing in the source. For SPX, NAS and UK100, days before 2012 use each market's 2012–2014 median spread. This is a disclosed imputation, not data.
- **Costs, futures route (reported, not gated):** spread 0.5 bp per side and financing at the policy rate only (long pays r, short receives r), approximating the cost of carry embedded in futures.
- **Statistics:**
  - daily net returns; t-stats Newey–West with 5 lags; Sharpe annualised √252;
  - eras: 2005/06–2012, 2013–2019, 2020–2026;
  - "OOS" means 2016-01-01 → 2026-09-25.

---

## 1. PROBE1-OIL
- **What:** PROBE1 exactly as frozen (PREREGISTRATION_PROBE1.md: rules, Q1/Q2 gates, Q2 threshold t ≥ 2.50) on WTI and Brent. The clean-day rule above applies.
- **What it settles:** Unger's "crude trends". It is confirmed if Q1 shows a stable TREND character on WTI.

## 2. GOLDTREND1: a slower, cheaper gold trend
PROBE1 found gold trends (t 3.9), but about 110–320 reversals a year gave the edge away in costs. Three slower rules, fixed in advance:

| | rule | detail |
|---|---|---|
| A | weekly probe | stop-and-reverse at a break of the **prior week's** high/low. Week = Mon–Fri clean days. Same fill rules as PROBE1. |
| B | close-confirmed daily | reverse only when a day **closes** beyond the prior day's high/low. Enter at the next open. |
| C | 20-day channel | reverse when the close exceeds the highest close (or falls below the lowest close) of the prior 20 days. Enter at the next open. |

**Gates per rule (all must pass; Bonferroni over 3 rules, one-sided t ≥ 2.13):**
- G1: full-sample CFD-net mean > 0 with t ≥ 2.13;
- G2: CFD-net mean > 0 in every era;
- G3: OOS CFD-net mean > 0.

**Reported:**
- reversals per year;
- the share of gross lost to spread and to financing;
- futures-route net;
- gold buy-and-hold Sharpe (net of CFD financing) for comparison.

## 3. CONTEXT1: "simple idea + context" on the gold probe
- **Base:** the PROBE1 daily probe on gold, trend direction, under the clean-day rule.
- **Filters:** each is computed only from data up to the previous clean day's close. When a filter is OFF for day d, the position is flat for day d (exit or no entry at the first bar, spread charged). When it is ON, the probe runs normally.

| | filter: probe active on day d when… |
|---|---|
| F1 | ATR(20) at d−1 is above its 250-day median (high volatility) |
| F2 | ATR(20) at d−1 is below its 250-day median (low volatility) |
| F3 | day d−1 was an NR4 day (its range is the smallest of the last 4) |
| F4 | day d−1 was an inside day (high ≤ prior high and low ≥ prior low) |
| F5 | day d opens inside day d−1's range (no gap) |
| F6 | only trades in the direction of close(d−1) vs its 100-day SMA; flat when a reversal would go against it |

**Gates per filter (Bonferroni over 6, one-sided t ≥ 2.39):**
- G1: OOS CFD-net mean > 0 with t ≥ 2.39;
- G2: filtered net beats the unfiltered probe's net in BOTH 2006–2015 and OOS.

**Reported:**
- time in market;
- trades per year;
- lift in each era.

## 4. MULTI1: several simple system types per market, combined
**Three systems per market** (SPX, NAS, UK100, gold; WTI/Brent are added if PROBE1-OIL has run, reported separately):
- **S1 trend:** a 20-day close channel, stop-and-reverse (the same rule as GOLDTREND1-C).
- **S2 mean reversion:**
  - buy at the next open when the close is the lowest of the last 5 closes, and short when it is the highest;
  - exit at the open 3 clean days later;
  - one position at a time.
- **S3 volatility breakout (day trade):**
  - each clean day, a buy stop at open + 0.5 × ATR(10) and a sell stop at open − 0.5 × ATR(10), with ATR known at d−1;
  - the first stop hit is taken and the second is ignored;
  - exit at that day's last bar close; no financing.

**Portfolio:**
- each system is scaled to a 10% annual vol target, using the standard deviation of its own net daily returns over the trailing 60 days (lagged one day; no position until 60 days of history);
- the portfolio is the equal-weight average of all systems;
- the leverage implied by vol targeting is capped at 5×.

**Gates (all must pass):**
- G1: portfolio net Sharpe > 0 with NW t ≥ 2.0, 2006–2026;
- G2: portfolio net > 0 in every era;
- G3: portfolio net Sharpe > the equal-weight buy-and-hold of the same markets (net of CFD financing, vol-targeted the same way) over OOS.

**Reported:**
- every component's net Sharpe;
- the average pairwise correlation of components;
- the diversification ratio (portfolio vol ÷ average component vol).

## 5. ROTATE1: monthly rotation to recent winners
- **Library:** MULTI1's 12 core systems (4 markets × 3 types), each vol-targeted as in MULTI1. Oil is excluded, so the library is fixed.
- **Rule:**
  - on each month's last clean day, rank systems by trailing 6-month net return;
  - hold the top 4, equally weighted, for the next month;
  - a turnover cost is charged as the spread on positions opened or closed by the switch.
- **Gate:** the paired monthly difference (rotation − hold all 12) has mean > 0 with t ≥ 2.0, and is positive in every era.
- **Reported:**
  - 3- and 12-month lookbacks;
  - "bottom 4" (anti-rotation) as a check for chance.

## 6. TURBO1: how a contest is won (simulation, descriptive, no gates)
**Input:**
- the gold probe's clean-day CFD-net daily returns 2006–2026 (PROBE1 logic plus the clean-day rule);
- demeaned, then re-centred to a true annual Sharpe of 0.0, 0.5 and 1.0.

**Simulation:**
- 100,000 one-year paths (252 days) per setting, by block bootstrap with 20-day blocks (seed 0);
- leverage scaled to annual vol of 10%, 25%, 50%, 100% and 200%, compounded daily;
- a path is "ruined" once equity falls to ≤ 10% of its start, and it stays there.

**Reported per (Sharpe, vol):**
- median year;
- P(year ≥ +100%) and P(year ≥ +600%);
- P(max drawdown ≥ 50%);
- P(ruin).

**Contest view:**
- 200 entrants per contest, all at the same Sharpe and 100% vol, simulated 10,000 times;
- the distribution of the winner's return, and how often the winner had Sharpe 0 (pure luck) when a mix of 190 Sharpe-0 and 10 Sharpe-1.0 traders enters.

## Order and stopping
- **Order:** PROBE1-OIL (after the Saturday pull), then GOLDTREND1, CONTEXT1, MULTI1, ROTATE1, TURBO1.
- **One run each.** Any mechanical change (chunking, path fixes) is logged in PROVENANCE as mechanical.
- **Any PASS** is a lead for a forward record, not money.
