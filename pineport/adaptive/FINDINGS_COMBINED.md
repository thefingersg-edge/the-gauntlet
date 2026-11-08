# The passes, combined — and the prediction written before the run was right

Run 2026-08-27 against `PREREGISTRATION_COMBINED.md`. Reproduce with
`python3 h1_combined.py`. 21 markets, equal weight rebalanced monthly.

The pre-registration said: *"the combination that survives will be a risk
overlay on long exposure, not a trading strategy."* That is what happened.

---

## The ladder — one component per rung

| rung | Sharpe | 2005–12 | 2012–19 | 2019–26 | ann ret | vol | max DD | turnover |
|---|---|---|---|---|---|---|---|---|
| 0 · buy and hold the basket | +0.582 | +0.611 | +0.112 | +0.915 | +4.51% | 8.16% | −32.7% | 0.0 |
| 1 · + trailing-vol sizing | +0.635 | +0.778 | +0.108 | +0.961 | +2.27% | 3.64% | **−11.6%** | 2.8 |
| **2 · + implied-vol sizing** | **+0.649** | **+0.771** | **+0.144** | **+0.980** | +2.28% | 3.57% | **−11.6%** | 3.6 |
| 3 · + sign(A) direction | +0.281 | +0.561 | −0.029 | +0.243 | +0.95% | 3.60% | −12.8% | 18.9 |
| 4 · + real-yield overlay | +0.257 | +0.523 | −0.041 | +0.220 | +0.87% | 3.61% | −13.5% | 19.4 |

**The two sizing passes combine. The direction pass destroys it.** Adding
`sign(A)` takes the stack from +0.649 to +0.281 — it more than halves the
Sharpe and cuts the return by two thirds, for a slightly *worse* drawdown.

| gate | result |
|---|---|
| 1 · full stack beats its own best rung | **FAIL** — +0.257 against +0.649. Stopping at rung 2 is better than finishing the stack |
| 2 · beats buy-and-hold in all three eras | **FAIL** for the full stack; **rung 2 passes it** (+0.771/+0.144/+0.980 against +0.611/+0.112/+0.915) |
| 3 · beats buy-and-hold on Sharpe, or state the risk case | full stack **FAIL**; rung 2 +0.649 vs +0.582 |
| 4 · survives 5bp | rung 2 **+0.609 vs +0.582** — turnover is only 3.6/yr, so costs barely touch it |
| 5 · real-yield overlay beats its destroyed-timing null | **FAIL** — +0.257 real against **+0.271 shuffled**. Rung 4 dropped, as pre-registered |

Rung 5 is worth pausing on: the real-yield overlay performs *worse* than the
same overlay with its timing destroyed by a 750-day lag. D3's correlation was
real and survived era-consistency and the sampling grid, and it still adds
nothing as a strategy component. A correlation that survives measurement is not
the same thing as a usable input, and this is the cleanest demonstration of that
distinction the project has produced.

---

## A correction to the run, found before reporting

The first version charged **buy-and-hold 38 units of turnover a year**, which is
nonsense. Re-deriving equal weights every day across 21 different trading
calendars manufactures rebalancing that nobody does: on any given day some
markets are closed, the weights reshuffle, and the cost model charges for it.
With positions carried across non-trading days and the weight rebalanced
monthly, buy-and-hold's turnover is 0.0 and the 5bp gate becomes meaningful for
every row. The first run's 5bp numbers were wrong for all five rungs.

## The Sharpe advantage is not significant. The drawdown difference is the result.

Stationary block bootstrap, 21-day blocks, 5,000 draws:

| | difference | 95% CI | P(>0) |
|---|---|---|---|
| rung 1 vs buy-and-hold | +0.053 | [−0.131, +0.217] | 69% |
| **rung 2 vs buy-and-hold** | **+0.067** | **[−0.111, +0.232]** | 75% |
| rung 2 vs rung 1 (the implied-vol increment) | +0.015 | [−0.015, +0.045] | 82% |

**Every interval spans zero.** On twenty-one years and an effective sample size
near six, a Sharpe improvement of 0.067 is not distinguishable from nothing, and
saying otherwise would be the mistake this project exists to avoid.

What is not in doubt is the exposure. At **matched volatility** — rung 2 levered
2.29× to buy-and-hold's 8.16% — the comparison is:

| | Sharpe | ann return | vol | max drawdown |
|---|---|---|---|---|
| buy and hold | +0.582 | +4.51% | 8.16% | **−32.7%** |
| rung 2, levered to match | +0.649 | +5.09% | 8.16% | **−24.8%** |

Slightly more return and **eight points less drawdown at the same volatility**.
That is a statement about the shape of the loss distribution, not about mean
returns, and it does not depend on the Sharpe difference being significant.

---

## What this actually is

Not a trading strategy. A **drawdown-control overlay on long exposure**: hold the
basket, size it by inverse volatility, and use implied volatility as the forecast
where an index exists. It turns over 3.6 times a year, survives realistic costs,
and is better than doing nothing in all three eras.

Every ingredient in it was already known. Volatility-managed portfolios are a
published result; implied vol beating historical vol as a forecast is older
still. The contribution here is that both were held to the same gauntlet as
everything that failed, and they are what was left standing.

## The caveats that belong next to it

- **The return is half.** 2.28% against 4.51% unlevered. Reaching parity needs
  2.29× leverage, and that assumption is doing real work in the matched-vol
  table.
- **The period flatters the benchmark.** A long basket of metals, indices and
  commodities over 2005–2026 caught gold and equities running hard. Rung 0's
  +4.51% is not a constant of nature.
- **Six of 21 markets have a volatility index**, two of those series have already
  been discontinued, and the whole implied-vol increment is +0.015 Sharpe.
- **N_eff ≈ 6 across 21 markets.** Everything above rests on roughly six
  independent bets, which is why the bootstrap intervals are as wide as they are.
