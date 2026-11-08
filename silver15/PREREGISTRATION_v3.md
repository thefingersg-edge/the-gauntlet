# Pre-registration v3: does a slow directional signal pay after costs?

Written 2026-08-10, **after** the power budget and **before** any backtest.

---

## Why this family, and why it is not another variation

The residual mean-reversion family is closed by arithmetic, not by evidence:

```
required(H) = C/(2 · 0.75 · √H) + k·√H     floor = 2√(a·k) = 4.73pp
```

No hold, barrier, instrument or basket gets below that floor, and the measured
effect is 3–4pp. Four tests were run and rejected; the fifth was shown
impossible before running.

This is a different family with different arithmetic. A directional trade pays
**one** spread instead of two, and earns on the instrument's **full**
volatility rather than a deliberately-shrunk residual. Measured cost/vol falls
from **0.146 to 0.071**.

## The power budget, computed first

**The detectability bar depends only on history length:**

```
required annual Sharpe (net) = k_sigma / √years
```

This is independent of instrument count — more instruments raise both the
total sample and the trades per year, and the two cancel. That is why 28
instruments did not rescue the pair family and 80 would not have.

| | |
|---|---|
| history | 20.4 years |
| net bar at 2σ | **0.44** |
| cost drag at hold 60 | 0.13 |
| **gross annual Sharpe required** | **≈ 0.57** |
| plausible for a simple trend rule | 0.3–0.6 |

**0.57 sits inside the plausible band.** That is the entire justification for
running this test, and it is why 2σ rather than 3σ: at 3σ the requirement is
0.79 gross, above anything a simple trend rule plausibly produces, so a null
would mean "underpowered" rather than "no edge" — the exact failure this
project has now made four times.

**Cost drag falls as ~1/hold**, which is why the design is slow (hold 60 H4
bars ≈ 10 days) rather than fast. Faster trading pays the spread more often;
that is what made the directional advantage narrower than it first appeared.

## Signal decorrelation — checked, not assumed

The pair budget was invalidated once by assuming trades spaced `hold` apart
were independent when the signal was a 30-bar rolling sum. Measured here:

| lookback | decorrelation lag | ratio |
|---|---|---|
| 8 | 4 | 0.50 |
| 30 | 16 | 0.53 |
| 60 | 31 | 0.52 |

A momentum z-score decorrelates in ~0.5×lookback, so holding for the full
lookback gives genuinely independent draws. The residual signal decorrelated
at 0.73× its window, which is why shortening its hold destroyed independence.

---

## Hypothesis (fixed)

**H1.** A slow directional momentum signal, applied across the 28-instrument
universe, produces mean P&L greater than zero after measured transaction costs.

**H0.** It does not.

## Configuration (frozen)

```
data          OANDA H4 mid, 2006-03 -> 2026-08, 28 instruments
signal        momentum z = (logP - MA(60)) / rolling sd(60)
entry         |z| >= 1.0, in the direction of the move (TREND, not reversion)
position      single instrument, unhedged, vol-scaled to 1 unit of risk
barriers      sl = 2.90 vol, tp = 8.71 vol   (T/S = 3, trend geometry)
              break-even win rate 25.6%
hold          60 H4 bars (~10 days), non-overlapping per instrument
costs         MEASURED ask-bid per instrument, as a fraction of price
pooling       ALL 28 INSTRUMENTS POOLED INTO ONE STATISTIC
```

**Asymmetric barriers because that is how trend is traded.** Forcing tp = sl
would neuter the family's defining property. T/S = 3 was chosen on the power
budget (it lowers required mean P&L per trade from 0.0564 to 0.0499 vol units),
not on returns.

**Entry threshold |z| >= 1.0** — deliberately loose. A tighter threshold cuts
sample without a stated mechanism for why extreme moves trend more.

## Success criteria (both required)

1. **Profitable.** Pooled mean P&L after measured costs > 0, with the lower
   bound of a 1,000-sample bootstrap **95%** CI also > 0.
2. **Not one instrument or regime.** No single instrument contributes more than
   25% of gross positive P&L; no single calendar year more than 25%.

A randomised-side null is reported as diagnostic context, not as a criterion.

## Stated power, so a null is interpretable

At 2σ with 20.4 years, this test resolves a gross annual Sharpe of ~0.57. A
null therefore means **"no edge at or above Sharpe 0.57"**, not "no edge at
all". That distinction is recorded now so it cannot be blurred later.

## Multiple-testing budget

**One run. One pooled statistic.** No sweep over lookback, threshold, barrier
ratio, hold, or instrument subset. The universe is all 28 instruments with
measured spreads; nothing is selected on performance.

If it fails, the directional family is closed on this data and the project ends.

## Anticipated failure modes

- **Correlation 0.295 at signal level** — the 28 instruments behave like ~3
  independent ones. Already priced into the budget, but it also means the
  strategy fails *together*: drawdowns hit everything at once. A win-rate
  framework does not capture that, and it is the main risk this family carries.
- **Trend is widely known and heavily traded.** Unlike a cointegrated pair
  there is no arbitrage mechanism forcing the effect to persist. Any edge may
  have decayed over the sample; the year-share criterion partly tests this.
- **Fat left tails.** Trend strategies suffer sharp reversals that a mean and
  a bootstrap CI understate.
- **Spreads measured today, applied to 2006.** Retail spreads have tightened,
  so early-sample costs are understated. This biases *towards* H1 — the
  dangerous direction — so a marginal pass should be distrusted.
- **2σ is a weaker bar than this project has used.** One in twenty such tests
  passes on noise. It is justified only because the design is a single
  pre-registered pooled statistic with no selection, and because 3σ would make
  the test unable to resolve anything realistic.

---

# RESULT (recorded 2026-08-10)

**H1 REJECTED.** Criterion 1 failed; criterion 2 passed.

| | |
|---|---|
| trades | 13,013 |
| win rate | 33.86% (break-even ~25.6%) |
| **mean P&L** | **−0.0791 vol units** |
| bootstrap 95% CI | **[−0.1849, +0.0216]** |
| implied annual Sharpe | −0.35 |
| top instrument / year | GBPJPY 4.5% / 2021 5.4% |

Diagnostic: real 33.86%, random 33.34%, reversed 32.84% — **+1.49 sd**, inside
noise.

## The first run reported a PASS. It was a bug in my harness.

The initial run gave mean P&L **+0.2846**, CI [+0.2010, +0.3652], implied
Sharpe **+1.51**, and both criteria passing.

Two things did not add up: an implied Sharpe of 1.51 against the 0.3–0.6 this
document called plausible, and a directional diagnostic of only +1.49 sd. A
strategy cannot be that profitable while being that close to random.

Checking mean P&L rather than win rate for each variant:

| variant | mean P&L |
|---|---|
| real | +0.2846 |
| **reversed** | **+0.2011** |
| **random** | **+0.2504** |

**It was profitable backwards.** That is never a signal; it is always the
harness.

**Synthetic control** — a driftless random walk at zero cost, where the correct
answer is 0.0 — returned **+0.278 vol units per trade**.

**Cause.** On a barrier breach the code recorded P&L as *exactly* the barrier
level. In reality the bar that breaches −2.90 closes at −3.55. Snapping back
to the barrier understates every loss, and because the near stop is hit ~3×
more often than the far target (8,173 vs 2,525) the optimism is severely
asymmetric. Recording the actual close instead: control returns **−0.0045**,
and the real result flips from +0.2846 to **−0.0791**.

## This bug also affects v1, v2 and hedged_test — in the safe direction

The same barrier-snapping is in `prereg_test.py`, `prereg_v2_test.py` and
`hedged_test.py`. All three **rejected**, and the bias is *optimistic*, so they
rejected despite a tailwind. Their conclusions stand and are if anything
understated. Only a PASS could have been manufactured by this bug, which is
exactly what happened here.

## What this result means

Per the stated power: no edge at or above a **gross annual Sharpe of ~0.57**
on this universe and history. Not "no edge exists". The mean is −0.079 with a
CI straddling zero, so this is a genuine null rather than a strong negative.

---

## What would end this line

A null on criterion 1. At that point no signal family this project can
construct — mean-reverting or directional, at any speed, on any of 28
instruments over 20 years — pays retail spreads at a demonstrable level, and
the honest conclusion is that retail execution cost is the binding constraint
rather than the absence of signal.
