# Pre-registration — real yields at the horizon that was never tested

Written **before any result was looked at**, 2026-08-27. Data: `dfii10.csv`
(FRED DFII10, 10-year TIPS yield, 5,901 daily observations 2003-01 → 2026-08),
joined to the eleven daily market series with the **one-business-day
publication lag** that `fetch_fred.py::load_daily_series` already applies.

The previous test of this series in the project put it in as a 15-minute entry
filter on a 26-day crossover, which is the wrong horizon and the wrong form.
This tests it as the literature does: a slow-moving level, at 3–12 months.

---

## The mechanism, stated before the test

Gold pays no coupon, so its opportunity cost is the real interest rate. When
real yields fall, holding a zero-yield store of value costs less, and gold
should rise. The same discount-rate logic applies to any long-duration asset.
That is a reason to work that does not reference a backtest, which is the bar
this project sets for a candidate.

## The sign map — the actual test

A signal that "works" on everything is a common factor, not a mechanism. So the
prediction is written per market **before looking**, and the result is scored on
whether it matches this map rather than on whether anything is significant.

| market | predicted sign vs real yield | why |
|---|---|---|
| **XAUUSD** | **negative** | zero-yield store of value — the core claim |
| **XAGUSD** | **negative** | same, weaker (industrial component) |
| **SPX500 / NAS100 / DE30** | **negative** | long-duration cash flows, discount-rate effect |
| **EURUSD / GBPUSD / AUDUSD** | **negative** | higher US real yields → stronger USD → these fall |
| **USDJPY** | **positive** | quoted the other way round — the sign must flip |
| BCOUSD / XCUUSD | *no prediction* | growth and discount-rate effects offset; reported, not scored |

**USDJPY is the discriminating case.** If it comes out negative like everything
else, the result is a common factor or a spurious trend, not a rate mechanism.

## Signals

Primary is the **change**, because the level is close to a unit root and gold
rose over the same twenty years that real yields fell — a level regression over
one long swing is close to a single observation.

| # | signal | form |
|---|---|---|
| S1 | Δ real yield over 63 days | stationary — **primary** |
| S2 | Δ real yield over 252 days | stationary |
| S3 | real yield level | **secondary, with the persistence caveat attached** |

## Horizons and sampling

Forward returns at **63, 126 and 252 trading days**, measured on
**non-overlapping** windows. Overlapping windows are reported alongside but are
not scored: at a 252-day horizon over 20 years there are roughly 20 independent
observations, and overlapping them inflates every t-statistic.

## Pre-registered pass criteria

| # | criterion | threshold |
|---|---|---|
| 1 | **sign map matched** on the primary signal | ≥ **7 of 9** scored markets, including **USDJPY flipping** |
| 2 | era stability | predicted sign holds in **all three eras** for gold |
| 3 | magnitude | rank correlation \|ρ\| ≥ **0.20** on gold at ≥ one horizon |
| 4 | independence | result survives on **non-overlapping** windows, not just overlapping |
| 5 | not a dollar proxy | survives when the same test is run on the dollar index as a control regressor |

Criterion 1 is the one that carries the argument. Nine markets each with a
sign written in advance is a 1-in-512 coincidence if the mechanism is absent,
and unlike a t-statistic it cannot be inflated by overlapping windows.

## What failure looks like

Everything negative including USDJPY → common factor, reject. Signs matching
only on the level and not the change → the twenty-year swing, reject. Signs
matching only with overlapping windows → sampling artefact, reject.
