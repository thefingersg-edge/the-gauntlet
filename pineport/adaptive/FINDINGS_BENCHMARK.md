# The benchmark correction — and the Sharpe error it exposed

Run 2026-08-27 following `FINDINGS_BENCHMARK_AUDIT.md`. Reproduce with
`python3 g3_benchmark.py`.

Two errors are fixed. One is a bad benchmark. The other ran through **every
number in this project**.

---

## Error 1 — Sharpe was computed on raw returns, not excess returns

Sharpe is (return − risk-free) ÷ volatility. Every figure in this project used
return ÷ volatility with no risk-free subtraction, over a period when fed funds
averaged **1.86%**. Every Sharpe reported before this file is inflated.

| | as reported | correct (excess) |
|---|---|---|
| buy and hold the 21-market basket | +0.582 | **+0.365** |
| rung 2, implied-vol sizing | +0.649 | **+0.117** |
| rung 3, with direction | +0.281 | **+0.200** |

## Error 2 — the benchmark was not something anyone could hold

An equal-weight long basket of 21 CFDs, gross of funding, padded with seven
arbitrarily-long FX pairs. Replaced with comparators that exist.

---

## The corrected table — everything as excess return over cash

| | excess Sharpe | excess return | vol | max DD | 2005–12 | 2012–19 | 2019–26 |
|---|---|---|---|---|---|---|---|
| **equities + gold, equal weight** | **+0.564** | **+7.14%** | 13.95% | −43.0% | +0.387 | +0.653 | +0.745 |
| 14 non-FX basket | +0.450 | +4.53% | 11.24% | −41.2% | +0.542 | +0.024 | +0.650 |
| S&P 500, long | +0.385 | +5.26% | 17.12% | −58.6% | +0.083 | +0.714 | +0.549 |
| 21-market basket *(the old benchmark)* | +0.361 | +2.64% | 8.14% | −33.2% | +0.410 | −0.004 | +0.575 |
| 60/40, S&P and US 10y | +0.325 | +2.75% | 9.84% | −36.9% | +0.077 | +0.713 | +0.376 |
| | | | | | | | |
| rung 3 · sign(A) direction | **+0.200** | +0.66% | 3.60% | **−13.1%** | +0.437 | −0.043 | +0.149 |
| rung 4 · + real-yield overlay | +0.176 | +0.57% | 3.61% | −13.8% | +0.399 | −0.055 | +0.126 |
| rung 2 · implied-vol sizing | +0.117 | +0.35% | 3.57% | −12.1% | +0.198 | −0.078 | +0.201 |
| rung 1 · trailing-vol sizing | +0.111 | +0.34% | 3.64% | −12.1% | +0.208 | −0.110 | +0.203 |
| cash | 0 by definition | | | | | | |

**All five rungs beat cash. One of five beats even the weakest passive
comparator, and that one is the old benchmark itself.**

The ordering among the rungs flips a third time. Gross, rung 2 led. Charged for
funding, **rung 3 leads** — the long/short rule runs net exposure of 0.106
against the long-only rungs' 0.96, so it pays 0.20% a year of funding where they
pay 1.78%. Every reordering in this project has come from a cost or a control,
never from a signal.

## With a realistic retail CFD financing spread

Adding 2% over the reference rate, which is ordinary for a retail account:

| | excess Sharpe | excess return |
|---|---|---|
| buy and hold | +0.120 | +0.65% |
| rung 3 · direction | +0.141 | +0.44% |
| rung 4 | +0.117 | +0.36% |
| rung 1 · trailing-vol sizing | **−0.415** | **−1.57%** |
| rung 2 · implied-vol sizing | **−0.419** | **−1.55%** |

**The two rungs built on the project's one surviving result go negative.** They
are long-only and vol-targeted to 10% against a basket whose natural volatility
is 8%, so they run leverage — and leverage on a retail CFD is expensive enough to
consume the entire edge.

## The era that decides it

| | 2012–2019 |
|---|---|
| equities + gold | **+0.653** |
| S&P 500 | +0.714 |
| every rung | −0.043 to −0.110 |

Every strategy here was flat-to-negative through 2012–2019 while passive
exposure returned its best numbers of the period. The rules failed precisely
when owning the assets worked.

---

## What the corrected picture says

1. **"Trend loses to buy-and-hold" was the wrong summary.** The correct one is
   that **nothing here — including the old benchmark — came close to simply
   owning equities and gold**, which returned +7.14% excess at Sharpe 0.564.
2. **The risk case survives, and is the only thing that does.** Rung 3 delivers
   +0.200 excess Sharpe at a **−13.1%** drawdown against equities-and-gold's
   +0.564 at **−43.0%**. A third of the risk-adjusted return at under a third of
   the drawdown. That is a real trade-off, and at 0.66% a year of excess return
   it is not a business.
3. **The implied-vol sizing result is unharmed as a forecasting claim and
   worthless as a return claim.** Calibration is measured on volatility, where
   funding does not enter and the data has power. The moment it is expressed as
   a levered long position, financing takes more than it earns.
4. **Three reorderings, three causes, none of them a signal.** Daily-rebalance
   turnover artefact, then funding, then the excess-return correction. In a
   project where no signal moved the ranking, the accounting moved it three
   times.
