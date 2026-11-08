# Pre-registration v7: does 12-month time-series momentum survive 2006–2026?

Written 2026-08-11, **after** `tsmom_budget.py` and **before** any backtest.

---

## Why this is not v3 or v4 again

v3 tested directional momentum over 120 H4 bars (~20 days) and v4 tested
cross-sectional ranks over the same window. Neither is the construction the
literature documents.

Moskowitz, Ooi & Pedersen (2012) use a **12-month** lookback, monthly
rebalancing, long or short by the sign of that return, vol-scaled per
instrument. **Horizon is not a free parameter here** — it is fixed in advance
by prior work, and momentum is horizon-dependent in sign: 12-month
continuation and 1-month reversal are different effects. A null at 20 days
does not settle 12 months.

This is also the last well-documented cross-asset anomaly reachable with data
already on disk. If it fails, the recognised list is exhausted.

## Power budget, computed first (tsmom_budget.py, run 2026-08-11)

NO strategy P&L computed. Past returns used as signal and as volatility only.

```
28 instruments, 246 months, 20.4 years      bar 0.44
median sign flips           1.59/yr    -> positions held 7.6 months
median annual volatility    13.3%
median annual cost drag     0.0046 Sharpe          NEGLIGIBLE
mean |return correlation|   0.399
mean |signal correlation|   0.300
EFFECTIVE BREADTH           2.4 independent bets   (not 28)
portfolio gross Sharpe needed        0.45
per-instrument gross Sharpe needed   0.29    (plausible band 0.20-0.50)
```

**Two findings shape everything below.**

**Cost is finally not the constraint.** 0.005 Sharpe against a 0.44 bar — the
first family in this project where it rounds to nothing. Drag scales as
`sqrt(trades/year)` and there are 1.59 trades a year. Every family that died
on cost died because that term was large; here it is not.

**Breadth is the constraint instead.** 28 instruments collapse to **2.4
independent bets** at a mean return correlation of 0.399. These are index CFDs
that move together and FX crosses that share legs. The diversification that
makes published TSMOM portfolios look good barely operates on this universe.

## THE EPISTEMIC HAZARD

This is the **second** pre-registration written after a budget that passed.
The first was v6, which then failed with a *negative* gross Sharpe — the
budget had measured the cost side honestly and been silent on the decisive
quantity.

That lesson applies here unchanged and is stated before the run: **the budget
bounds what this test can RESOLVE. It says nothing about whether the effect
exists in 2006–2026.**

**Prior, stated in advance so a favourable result gets scepticism rather than
relief:** published Sharpes of 0.7–1.0 are 1985–2009 *portfolio* figures, not
per-instrument and not this period. Live managed-futures indices have run
nearer 0.2–0.3 since 2009, and this window is almost entirely that weak
period. A pass would be mildly surprising.

---

## Hypothesis (fixed)

**H1.** A vol-scaled long-short book, positioned by the sign of each
instrument's trailing 12-month return and rebalanced monthly, earns a positive
net return over 2006–2026 after measured costs, with a maximum drawdown no
worse than 25%.

**H0.** It does not.

**Direction, stated in advance:** a positive 12-month return implies a LONG
position. This is the sign the momentum hypothesis predicts. The reversed
variant is a diagnostic and — per the v5 and v6 precedent — **must not** be
flipped and re-run if it turns out to be the better of the two.

## Configuration (frozen)

```
universe      28 OANDA instruments, H4 resampled to month-end close,
              each instrument resampled on its OWN bars before alignment
signal        sign( log(P[m] / P[m-12]) )        12-month lookback
LAG           position formed at the close of month m, held through m+1.
              No publication lag is required — price is observable in real
              time — but month m's own return must never fund month m.
book          ALL instruments held, long or short by sign
weighting     vol-scaled to equal risk per instrument, gross normalised to
              1 unit of risk
vol window    12 months TRAILING, using only returns already realised
rebalance     monthly, non-overlapping
costs         measured SPREAD_REL, charged on the CHANGE in each position.
              A sign flip moves TWO units of notional and is charged twice.
window        2006-02 -> 2026, less the 12-month lookback and 12-month vol
              window, so trading begins ~2008
statistic     ONE pooled net monthly return series for the portfolio
```

**No threshold on the signal.** A magnitude threshold is a free parameter with
no stated mechanism, and the specification is a sign.

**The 12-month vol window** is frozen here, before any P&L exists, matching
v6. It was not named in the budget and is recorded as a decision rather than
quietly assumed.

## Success criteria (ALL three required)

1. **Profitable after costs.** Pooled mean net monthly return > 0, with the
   lower bound of a 1,000-sample bootstrap 95% CI also > 0.
2. **Maximum drawdown ≤ 25%**, peak-to-trough on the net equity curve.
3. **Not one year.** No single calendar year contributes more than **30%** of
   gross positive P&L.

Criterion 3 is weighted toward *time* rather than *instrument* concentration,
because unlike v4 this book holds every instrument every month — so
instrument concentration is structurally unlikely while regime concentration
is the live risk. **2008 is in-sample and is TSMOM's single best-known year.**
If the entire result is 2008, criterion 3 should fail and that is the
criterion doing its job.

**Diagnostics, explicitly NOT criteria:** reversed signal, randomised-sign
null, return skewness, per-year attribution, and the result excluding 2008.

## Stated power

20.4 years gives a 2σ bar of **0.44** portfolio Sharpe, from 246 monthly
observations. Effective breadth of 2.4 makes the per-instrument requirement
**0.29**, inside the 0.20–0.50 plausible band. A null therefore means *"no
12-month TSMOM edge at or above 0.29 per instrument on this universe over
2006–2026"* — informative, not underpowered.

## Multiple-testing budget

**One run. One pooled statistic.** No sweep over lookback, rebalance
frequency, vol window, weighting, universe subset or threshold. If it fails,
the line is closed.

## Anticipated failure modes

- **2008 carries it.** TSMOM's reputation rests heavily on crisis alpha and
  2008 is in the window. Criterion 3 tests this directly, and the
  excluding-2008 diagnostic will make it visible either way.
- **Whipsaw 2012–2021.** A long low-volatility, range-bound stretch is where
  trend following bleeds, and it is most of this sample.
- **Realised breadth below 2.4.** Signal correlation is 0.300 against return
  correlation 0.399 — positions crowd nearly as much as returns do, so the
  effective bet count during drawdowns is likely worse than the headline.
- **Skew should be POSITIVE.** Trend following is long convexity: it cuts
  losers and rides winners. If realised skew comes out negative, the
  implementation is wrong rather than the effect being absent, and that is a
  bug signal not a result.
- **The effect may simply be gone.** Post-2009 CTA performance is the base
  rate and it is poor.
- **28 CFDs are not the published universe.** MOP used 58 futures across four
  asset classes with far lower correlation. This universe is index- and
  FX-heavy, which is precisely why breadth collapsed to 2.4.

## What this budget cannot see

- whether the effect exists in this period at all
- slippage beyond quoted spread on a monthly rebalance
- that realised breadth in a crisis is typically far below the unconditional
  estimate, because correlations converge exactly when it matters

---

# RESULT (recorded 2026-08-11)

**H1 REJECTED.** Criterion 1 failed; criteria 2 and 3 passed.

| | |
|---|---|
| observations | 233 months, 2007-03 → 2026-07, 19.3 years |
| mean gross per month | +0.00053 |
| mean cost per month | +0.00007 |
| **mean net per month** | **+0.00046** |
| bootstrap 95% CI | **[−0.00165, +0.00288]** — straddles zero |
| implied annual Sharpe | **+0.09** (bar 0.45) |
| maximum drawdown | 24.0% (gate 25%) — PASS, but barely |
| positive months | 52.8% |
| top year | 2008 = 17.8% — PASS |

## The anticipated failure mode, confirmed exactly

The pre-registration predicted: *"2008 carries it. TSMOM's reputation rests
heavily on crisis alpha and 2008 is in the window."*

```
2008 alone          +0.2437
whole 19.3 years    +0.1082
EXCLUDING 2008      -0.1355   (Sharpe -0.14)
```

**2008 is more than double the entire result.** Strip it and the strategy is
negative over eighteen years. The by-year table shows the pattern plainly: one
enormous crisis year, then 2009 (−0.16) and 2011 (−0.10) giving much of it
back, and a long directionless grind through 2016–2024.

## Criterion 3 passed, and it should not have

Criterion 3 was specified as *"no single calendar year contributes more than
30% of gross positive P&L"*, implemented as each year's sum of its POSITIVE
MONTHS over the same across all years. 2008 scored 17.8% and passed
comfortably.

That measure is too weak, and the run proves it: a year can be 225% of the
entire net result while contributing under a fifth of all positive months,
because every other year also has positive months that the denominator counts
and their offsetting negative months that it ignores.

**This is recorded, not fixed.** The criterion passed as written and the
result stands as specified — retroactively tightening a criterion after seeing
it pass is the same offence as loosening one after seeing it fail. The
excluding-2008 diagnostic was pre-registered precisely because concentration
measures are slippery, and it did the job the criterion could not.

**For any future test:** concentration should be measured against NET P&L, or
by leave-one-period-out, not against gross positive P&L.

## The implementation is sound; the effect is absent

Skewness came in at **+0.35, positive**, exactly as trend following should
be — it is long convexity, cutting losers and riding winners. The
pre-registration named negative skew as a *bug signal* rather than a result.
It did not appear, so the engine is behaving as the strategy is supposed to.

**Gross Sharpe at zero cost: +0.11.** Cost was genuinely negligible — 0.00007
per month against 0.00053 gross, exactly as the budget predicted. This is the
first family in the project where the budget's cost estimate was confirmed and
irrelevant at the same time. The signal simply is not there in this period, on
this universe.

Diagnostic: real +0.00046, random −0.00020 (sd 0.00048), reversed −0.00060.
Real is **+1.38 sd** above random — the right sign, too small to matter, and
nowhere near the bar.

## The engine was verified before the run

Fifteen synthetic controls passed, including three that exist solely to prove
the others can fire.

One control failed on first run and was corrected: the look-ahead probe
compared honest against peeking on **strongly trending** data and demanded 2×
inflation. Measured ratios are **54× on a driftless path, 2.1× on a weak
trend, 1.1× on a strong one** — a large planted edge swamps the leak, so the
probe was being run in the worst available place. Moved to a driftless path,
where the honest answer is zero and any leak is unmistakable.

That is the fifth instance in this project of a gate that could not do its
job, and the reason controls 13–15 now exist.

---

## Status of this line

**Closed.** One run, one statistic, no retuning, no sign flip, no lookback
sweep.

Eleven families. The recognised list of documented cross-asset anomalies
reachable with retail data is now exhausted, and in every case the gross
signal was at or below zero *before* costs, or the premium had already been
competed below the relevant hurdle.
