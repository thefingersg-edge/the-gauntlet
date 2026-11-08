# PREREGISTRATION — REGIME2: does trend strength (ADX) help with direction or patterns?

```
STATUS:   frozen before any REGIME2 number is computed (sha in PROVENANCE.md)
WRITTEN:  2026-10-09
DATA:     OANDA 15m bid/ask (struct15 caches; SPX500, NAS100, UK100, XAUUSD) to 2026-09-25;
          SESSION1 trade-level output (data/session1/*.json). Nothing new is pulled.
FOLLOWS:  REGIME1. MA filters do not tell direction (0/10) or help patterns (0/86).
          The open question is whether they work only when the market is "trending".
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## The claim being tested
ADX (Wilder, 14) measures trend *strength*, not direction. The usual advice has three parts:
- **(i)** When ADX ≥ 25, the market is trending. Trade in the direction of +DI vs −DI, or of the moving average.
- **(ii)** In that state, continuation setups (breaks of structure, breakouts, momentum bars) work.
- **(iii)** When ADX < 20, the market is ranging. Reversal setups (pin bars, engulfing, change of character) work.

## Definitions
- **Daily bars:** built from each instrument's in-session 15m bars, using SESSION1's session hours.
  - high = max and low = min of those bars;
  - close = close of the last in-session bar;
  - a day needs ≥ 80% of its normal bar count.
- **Wilder ADX(14), +DI, −DI:**
  - TR, +DM, −DM smoothed with Wilder's RMA (α = 1/14);
  - DX = 100·|+DI − −DI| / (+DI + −DI);
  - ADX = RMA(DX);
  - the first 50 days of each series are discarded as warm-up.
- **States, known at day d's close and used from day d+1:**
  - TREND: ADX ≥ 25;
  - RANGE: ADX < 20;
  - between 20 and 25: neither.
- **Self-test before any verdict:**
  - a synthetic steady trend with noise must give ADX > 40;
  - a random walk must give a median ADX of 15–30;
  - shifting the input by one day must change nothing earlier (causality).

## Q1 — direction when trending (daily; 6 tests; Bonferroni t ≥ 2.64)
Direction signals:
- **D1:** +DI > −DI.
- **D2:** close > SMA200.
- **D3:** 20-day breakout state. "Up" after a close above the prior 20-day high, "down" after a close below the prior 20-day low, and the state is held until the opposite break.

Sample: TREND days only.

Returns:
- next day, close to close (h = 1);
- next 5 days, non-overlapping (every 5th eligible day) (h = 5).

Statistic: b = mean return in the up state minus the down state. It comes from a pooled regression with instrument intercepts, clustered by date (as REGIME1).

Gates (all must pass):
- b > 0 and t ≥ 2.64;
- b > 0 in each era 2005–12, 2013–19, 2020–26;
- b > 0 on ≥ 3 of 4 instruments.

Reported:
- the same b on RANGE days;
- the TREND minus RANGE difference;
- the share of TREND days;
- volatility in TREND and RANGE states.

## Q2 — the right pattern in the right regime (SESSION1 trades; daily ADX at the previous close)
**Pre-assigned classes** (from the setup's usual description, fixed before looking):
- **Continuation:** BOS, marubozu, three_soldiers, wide_range, gap_bar, opening_range, three_bar_pull, inside_bar, nr7.
- **Reversal:** CHoCH, pin_bar, hammer, engulfing, harami, morning_star, key_reversal, reversal_bar, two_bar_rev, three_bar_rev, doji, outside_bar, exhaustion.

**Which trades are kept:**
- **Q2a (primary):** continuation tests keep only trades taken in a TREND state *and* in the +DI/−DI direction. Reversal tests keep only trades taken in a RANGE state.
- Random partners are filtered by exactly the same rule, using their own dates and sides.

**Tests:** every SESSION1 test, one regime each. That is 84 Part B tests (30m and 1h) and 2 Part A tests (15m, k = 3): 86 in total.

**Gates (all must pass):**
- net > 0 with t ≥ 3.4 (Part B) or ≥ 2.24 (Part A), date-clustered;
- beats its filtered random partners, t ≥ 2;
- > 0 in every era;
- n ≥ 200.

**Reported:**
- the same trades in the *wrong* regime;
- "regime lift" = (right − wrong regime) for the pattern minus the same for its random partners.

## Q3 — ADX on the chart's own timeframe (Part A, 15m structure)
- ADX(14) and DI are computed on the 15m bars (24-hour series, as the chart shows), at the signal bar j.
- BOS is kept when ADX ≥ 25 and the break is in the DI direction. CHoCH is kept when ADX < 20.
- Random partners are filtered the same way, with ADX at their own entry bar minus 1.
- Gates as Q2 Part A (t ≥ 2.24, beats random t ≥ 2, eras > 0, n ≥ 200).

## What each outcome means
- **Q1 fails:** "only trust the trend when ADX says it is trending" does not rescue moving-average direction.
- **Q2/Q3 fail:** matching setups to the regime does not create an edge.
- **Any pass:** a lead for a fresh pre-registration with a forward record. It is not money.
