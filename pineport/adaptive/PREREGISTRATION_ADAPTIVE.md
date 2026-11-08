# Pre-registration — adaptive lookback, and chart shapes

Written **before any result was looked at**, 2026-08-27, following the same
discipline as `PREREGISTRATION.md`: a criterion agreed after seeing results is
not a criterion.

Data: OANDA H1 resampled to UTC daily, eleven markets, 2005-01 → 2026-08
(gold and silver from 2006-03). Eras, fixed in advance and equal in span:

```
E1  2005-01 → 2012-03
E2  2012-04 → 2019-06
E3  2019-07 → 2026-08
```

Execution model throughout: signal from bar t's close, position held from
t+1's close, daily rebalance, costs charged on turnover.

---

## Question A — can a lookback be adapted to the current environment?

The claim under test: *there exists an observable state variable, measurable
today, that tells you whether a moving-average crossover should be faster or
slower over the coming period.*

Three tests, in cost order. **A1 failing kills A2 and A3** — if the thing you
would adapt towards is not persistent, no adaptation rule can reach it.

### A1 — Is the optimal lookback persistent at all?

For each market, non-overlapping calendar quarters. In each quarter, the
realised return of every `(fast, slow)` SMA crossover pair on a fixed grid.
Define the quarter's optimal speed `s* = log2(slow*)`.

| # | criterion | threshold |
|---|---|---|
| A1a | lag-1 Spearman autocorrelation of `s*` | median across markets ≥ **+0.20** and positive in ≥ **8 of 11** |
| A1b | "trade last quarter's winner" vs a fixed median pair | adaptive wins in ≥ **8 of 11** markets **and** in all three eras |

A1b is the decision-relevant form. A1a can pass on a slow drift that is
useless to trade; A1b cannot.

### A2 — Is next period's optimal speed predictable from today's state?

State variables, all measured at the **last bar of the prior quarter** and
therefore known at decision time:

`efficiency_ratio(63)`, `realised_vol(63)`, `vol_of_vol(63)`,
`variance_ratio(5,63)`, `hurst(63)`, `adx(14)`, `dominant_cycle` (zero-crossing
period of the detrended series), `autocorr_1` (signed) and `abs_autocorr_1`.

| # | criterion | threshold |
|---|---|---|
| A2 | Spearman ρ(state ₜ₋₁ , s*ₜ) | \|ρ\| ≥ **0.15**, **same sign in all three eras**, in ≥ **7 of 11** markets, for at least one state variable |

Eight variables × eleven markets is a wide search. Sign-consistency across
three eras *and* across markets is the control, and it is the same standard
that rejected every other candidate in this project.

### A3 — Does an adaptive rule beat a fixed one?

Four rules, same grid, same costs: **fixed** `SMA(50/200)`; **ER-adaptive**
(Kaufman efficiency ratio drives the smoothing constant); **vol-scaled**
(lookback ∝ realised vol, clipped); **cycle-scaled** (lookback = k × measured
dominant cycle).

| # | criterion | threshold |
|---|---|---|
| A3a | pooled equal-weight Sharpe | adaptive > fixed |
| A3b | per-market | adaptive > fixed in ≥ **7 of 11** |
| A3c | per-era | adaptive > fixed in **all three** |
| A3d | shape of the improvement | **PLATEAU**, not SPIKE, across the adaptation parameter |
| A3e | costs | survives 5 bp per unit turnover |

A3d matters most. Vol targeting is the only thing this project has ever
found that produced a plateau, and it is the only thing that has held up.

---

## Question B — do chart shapes carry information?

The claim under test: *converging-trendline shapes (wedges, triangles) predict
the direction of the move that follows.*

Detection: fractal pivots on daily bars, a wedge/triangle recorded when the
upper and lower trendlines through the last three pivots each side converge by
more than a stated ratio within a stated bar window. Breakout = close beyond
the relevant trendline.

| # | criterion | threshold |
|---|---|---|
| B1 | **detection stability** — same detections under pivot lookback ±1 and start-offset 0–4 bars | ≥ **80%** overlap (the project's existing feed-robustness gate) |
| B2 | **sample size** | ≥ **30** detections per era, pooled across markets |
| B3 | **direction** — 21-day forward return after breakout, signed by pattern direction | same sign in all three eras **and** ≥ **7 of 11** markets |
| B4 | **magnitude** — forward \|return\| ÷ prior realised vol, after compression | same sign in all three eras **and** ≥ **7 of 11** markets |

B3 and B4 are stated separately and in advance so that a failure on direction
cannot be re-described afterwards as a success on magnitude. They are
different claims and only one of them is what a chart-pattern trader believes.

---

## What counts as a result

A PASS on A1 makes the adaptive programme worth building. A FAIL on A1 ends it
in an afternoon, which is the point of running it first.

A FAIL on B3 with a PASS on B4 would mean the shapes are a volatility signal
wearing directional clothing — which changes what they are for, not whether
they are useless.
