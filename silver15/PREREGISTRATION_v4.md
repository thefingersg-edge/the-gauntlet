# Pre-registration v4: cross-sectional momentum across 28 instruments

Written 2026-08-10, **after** the power budget and **before** any backtest.

---

## Why this is a different family, not another variation

Every previous test read one price series and asked "which way next". v3
settled that question: at zero cost, on 13,013 trades, the pooled gross signal
was **+0.0067 vol units**, +0.23 sd over random. There is no time-series
direction to harvest, so no filter, barrier or execution improvement can help.

A cross-sectional rank asks a different question — **which instrument is
strongest relative to the others** — and trades the difference. That is
relative information, not the absolute information already shown to be empty.
It also differences away the market factor, which is what dominates
directional trading.

## Power budget, computed first (xsec_budget.py)

| | |
|---|---|
| detectability bar, 2σ on 20.4y | 0.44 |
| turnover per rebalance | 55% of a 10-name book |
| annualised cost drag | **0.01** |
| **gross annual Sharpe required** | **0.46** |
| plausible for cross-sectional momentum | 0.3–0.6 |

Cost is nearly irrelevant here — rebalancing every 20 days means the spread is
paid a handful of times a year. That is the structural advantage: the bar is
essentially just the detectability floor.

**Rebalance chosen at 120 bars, not the tool's optimum.** 500 bars gives a
marginally lower bar (0.45) but only **62 independent rebalances**. 120 bars
costs 0.01 Sharpe and buys **264**. The tool optimises the threshold; it does
not weigh estimate stability. That trade is made here explicitly.

**Rank independence verified, not assumed.** Persistence between consecutive
ranks tracks lookback-window overlap exactly (0% overlap → ρ 0.03; 83% overlap
→ ρ 0.76). With lookback equal to rebalance spacing the windows do not
overlap, so consecutive ranks are independent by construction.

---

## Hypothesis (fixed)

**H1.** A long-top / short-bottom cross-sectional momentum portfolio across the
28-instrument universe produces mean return greater than zero after measured
transaction costs.

**H0.** It does not.

## Configuration (frozen)

```
data          OANDA H4 mid, 2006-03 -> 2026-08, 28 instruments
signal        120-bar log return, ranked across the panel at each rebalance
panel         require >= 20 instruments observable; otherwise skip
positions     long top 5, short bottom 5, equal weight, vol-scaled per leg
rebalance     every 120 H4 bars (~20 days), NON-OVERLAPPING lookbacks
costs         MEASURED ask-bid per instrument, charged on the legs that CHANGE
statistic     ONE pooled mean return per rebalance across all rebalances
```

**Vol-scaled legs**, because instruments span 0.10% (EURCHF) to 0.71% (WTI)
per-bar volatility. Equal notional would make the book a bet on crude.

**Top/bottom 5 of ~28.** Fixed in advance. Not swept.

**No barriers, no stops.** A cross-sectional book is held to the rebalance;
adding exits would introduce parameters with no stated mechanism.

## Success criteria (both required)

1. **Profitable.** Pooled mean return per rebalance after measured costs > 0,
   with the lower bound of a 1,000-sample bootstrap 95% CI also > 0.
2. **Not one instrument or regime.** No single instrument contributes more than
   25% of gross positive P&L; no single calendar year more than 25%.

A randomised-rank null is reported as diagnostic context, not as a criterion.

## Stated power, so a null is interpretable

264 independent rebalances over 20.4 years resolves a gross annual Sharpe of
~0.46. **A null means "no cross-sectional edge at or above Sharpe 0.46 on this
universe"** — not "no edge exists".

## Multiple-testing budget

**One run. One pooled statistic.** No sweep over lookback, basket size,
rebalance frequency, or instrument subset. If it fails, the family is closed on
this data and the project ends.

## Anticipated failure modes

- **28 is a small panel.** Published cross-sectional momentum uses hundreds of
  assets. With 28, the top and bottom baskets are 5 names each and the rank has
  few distinct states.
- **Correlation 0.30 across instruments** means the long and short legs will not
  difference out the market factor as cleanly as a broad universe would.
- **The panel is unbalanced** — 13 FX, 13 index, 2 energy. A "cross-sectional"
  rank may end up expressing FX-vs-index rather than anything within a class.
- **Spreads measured today, applied to 2006.** Biases *towards* H1.
- **2σ.** One in twenty such tests passes on noise.
- **Momentum is the most published anomaly in finance.** If it works here it is
  not a discovery, and if it has decayed over the sample the year-share
  criterion should show it.

---

# RESULT (recorded 2026-08-10)

**H1 REJECTED.** Criterion 1 failed; criterion 2 passed.

| | |
|---|---|
| rebalances | 258 (2006-05 → 2026-06) |
| mean gross per rebalance | −0.00006 |
| mean cost per rebalance | +0.00033 |
| **mean net** | **−0.00040** |
| bootstrap 95% CI | **[−0.00244, +0.00160]** |
| implied annual Sharpe | **−0.09** (bar 0.44) |
| positive rebalances | 50.8% |
| top instrument / year | WTI 7.6% / 2008 17.5% |

Diagnostic: real −0.00040, random −0.00035, reversed −0.00027 — **−0.08 sd**.
Indistinguishable from a randomly permuted rank.

## A bug was found and fixed before this result was accepted

The first run gave 113 rebalances starting 2013, against 264 budgeted.
Investigating rather than accepting it:

Momentum and volatility were computed across rows of the **ragged union
index** instead of each instrument's own bars. `shift(120)` therefore spanned
120 union rows rather than 120 bars of that instrument, and `rolling(60)`
required 60 consecutive non-NaN rows. Instruments trading different sessions
were silently destroyed:

| instrument | rows with valid vol |
|---|---|
| SMI, AEX, FR40 | **0.0%** |
| HK33 | 6.3% |
| DAX | 28.2% |
| FX majors | ~67% |

So a "28-instrument cross-sectional test" was really ~18 instruments, almost
entirely FX, over 13 years — **not the pre-registered design**. Fixed by
computing each instrument's momentum and vol on its own bars and then
aligning. Rebalances went 113 → **258**, matching the budget, and the sample
now starts in 2006 as specified.

The engine was re-verified on synthetic controls after the fix: −0.000143
(se 0.000214) on a driftless panel, and it recovers a planted cross-sectional
edge (+0.027).

**The bug made no difference to the verdict** — both versions rejected — but
it would have invalidated a pass, and it broke the pre-registered universe.

## Gross was already negative

Mean gross is **−0.00006** before any cost. Cost is +0.00033. So this is not
"an edge eaten by spread" — there was no edge to eat, the same finding as v3.
Cross-sectional ranking on this panel carries no more information than
time-series momentum did.

---

## What would end this line

A null on criterion 1. At that point neither time-series nor cross-sectional
price-derived signals clear a demonstrable bar on this data, and the honest
conclusion is that the remaining levers are cheaper execution or non-price
information — neither of which is a modelling problem.
