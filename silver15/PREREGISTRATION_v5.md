# Pre-registration v5: does COT positioning change predict returns?

Written 2026-08-10, **after** the power budget and **before** any backtest.

---

## Why this is not a seventh variation on the same idea

Six families have failed. Every one read the same OHLC series, and v3 and v4
established why: **the gross signal is ~zero before any cost.** v3 pooled
+0.0067 vol units at zero cost across 13,013 trades; v4 was −0.00006 gross.
There is no directional content in the price history to harvest, so no filter,
barrier, horizon or execution improvement can help.

COT is the first genuinely **non-price** input this project has obtained with
usable history. It is what participants actually hold, published weekly by the
CFTC since 1986. It is not a transform of data already shown to be empty.

**Mechanism.** Commercials are hedgers: producers and consumers whose
positioning changes when they hedge forward physical supply or demand. A shift
in commercial exposure is an information event about physical markets, not a
restatement of the price. Large speculators take the other side. That is a
stated reason for predictive content to exist — most failed families here had
only a correlation story.

## Data provenance — verified, after four failures

This project has now had five data-provenance failures. The COT series took
three attempts:

| export | verdict |
|---|---|
| "Commercials / Non-Commercials / Retail Traders", 30.6y | **NOT CFTC.** Correlates −0.69 with real COT; "Retail Traders" is a broker client category. Discarded. |
| CoT-Buschi with `convertRootToCOTCode("Auto")` | **Symbol-blind.** Gold and silver exports byte-identical across 10,271 days, max diff 0.00. `"Auto"` cannot map a CFD root, and `ignore_invalid_symbol=true` failed silently. Discarded. |
| **explicit CFTC code** | **VERIFIED.** Six codes give six distinct series, zero identical pairs. |

Verification of the accepted data:

- start dates **1986-01-15** for gold/silver/USDX/WTI — exactly when CFTC
  legacy reporting begins; 1989 copper, 1998 corn
- gold commercial shorts: 396k (2011), 355k (2016), 408k (2020), 282k (2026)
  — correct magnitude, and the 2011/2020 peaks land on real extremes
- ~47 updates/year against a nominal 52 (holidays, 2018-19 shutdown)
- nulls before each series begins, not forward-filled zeros

## THE LOOK-AHEAD HAZARD — the single most important line here

**CFTC positions are measured Tuesday and published Friday 15:30 ET.**
The indicator plots on the **position date**: 90–98% of updates land on a
Tuesday. Reading Tuesday's value on Tuesday trades on information that does
not exist for three more days.

**This test lags the signal by one full calendar week.** Not the four-day
minimum — a full week, so no plausible release-timing variation can leak.

An earlier note in this project said "1-bar lag is safe". That was wrong, and
derived from the discarded non-CFTC series which plotted on Sundays.

## Power budget, computed first (cot_budget.py)

Transform choice, on **autocorrelation only** — no returns computed:

| transform | mean n_eff across 6 markets |
|---|---|
| raw level | 17 |
| COT index 52w | 57 |
| z-score 26w | 91 |
| **weekly change** | **1,107** |

The standard 52-week COT index yields **57 effective observations from 38
years**. Anyone backtesting it believes they have 1,900.

| | |
|---|---|
| mean span | 38.0 years |
| **2σ bar** | **0.32** |
| cross-market mean \|ρ\| | 0.138 |
| 6 markets behave like | 3.6 independent |
| **effective observations** | **3,936** |

Lowest bar and largest effective sample in the project. Gold/silver correlate
0.57 as expected; **corn is near-independent of everything** (0.00–0.06).

---

## Hypothesis (fixed)

**H1.** The weekly change in commercial net positioning predicts the following
week's return, pooled across six CFTC markets, with mean P&L greater than zero
after costs.

**H0.** It does not.

**Direction, stated in advance:** commercials are hedgers who sell into
strength. Rising commercial net (less short) is expected to precede **positive**
returns. The test is signed; the reversed variant is a diagnostic.

## Configuration (frozen)

```
data        TradingView CFTC legacy COT via explicit code, weekly
markets     gold 088691, silver 084691, copper 085692,
            WTI 067651, corn 002602, USDX 099741
signal      weekly change in Commercials net
normalise   z-score of that change over a trailing 52 weeks, per market
entry       sign of the z-score; no threshold
LAG         ONE FULL WEEK after the plotted (Tuesday) date
horizon     one week, non-overlapping
position    vol-scaled to 1 unit of risk per market
costs       measured spreads: gold 0.0151%, silver 0.0600%, copper 0.0316%,
            WTI 0.0501%; corn and USDX not measured -> use 0.0500% (the
            worst measured value) as a conservative stand-in
statistic   ONE pooled mean across all markets and weeks
```

**No threshold on entry.** A threshold is a free parameter with no stated
mechanism, and it would cut the sample that makes this testable.

**52-week z-score of the change**, not the level. Frozen now: it was chosen on
n_eff, a power property, before any P&L existed — but it is still one of five
candidates examined, and must not be revisited after seeing results.

## Success criteria (both required)

1. **Profitable.** Pooled mean P&L after costs > 0, with the lower bound of a
   1,000-sample bootstrap 95% CI also > 0.
2. **Not one market or regime.** No single market contributes more than 35% of
   gross positive P&L; no single decade more than 50%.

A randomised-sign null and the reversed signal are reported as diagnostics,
not criteria.

## Stated power

3,936 effective observations over 38 years resolves a gross annual Sharpe of
**~0.32**. A null therefore means **"no COT edge at or above Sharpe 0.32 on
these six markets"** — an informative result, not an underpowered one.

## Multiple-testing budget

**One run. One pooled statistic.** No sweep over transform, lookback, lag,
threshold, horizon or market subset. If it fails, the line is closed.

## Anticipated failure modes

- **The most independent transform is often the noisiest.** Weekly change has
  ac1 = 0.15 precisely because much of it may be reporting jitter. Low
  autocorrelation makes a test *valid*, not *promising*.
- **COT is heavily published.** Any simple edge has been visible since 1986.
- **Corn and USDX costs are assumed**, not measured. Flagged in the config.
- **Release timing varies.** Holidays shift publication; the one-week lag is
  deliberately conservative to absorb this.
- **Contract-size changes.** CFTC contract specifications have changed over 38
  years; a change in net contracts may reflect a definitional change rather
  than behaviour. The z-score over a trailing window absorbs slow drift but
  not a discrete redefinition.
- **Regime.** 1986–2026 spans floor trading to electronic, and the growth of
  index funds after 2004 changed who "commercials" are. The decade criterion
  partly tests this.

---

# RESULT (recorded 2026-08-10)

**H1 REJECTED.** Criterion 1 failed; criterion 2 passed.

| | |
|---|---|
| observations | 10,129 weekly, 1988-04 → 2026-07, 38.3 years |
| **mean P&L** | **−0.03047 vol units per week** |
| bootstrap 95% CI | **[−0.05239, −0.00931]** — entirely below zero |
| implied annual Sharpe | **−0.19** (bar 0.32) |
| positive weeks | 49.6% |
| top market / decade | WTI 18.5% / 2000s 31.6% |

Per market, every one negative:

| market | n | mean | t |
|---|---|---|---|
| copper | 1,764 | −0.0446 | −1.79 |
| USDX | 1,395 | −0.0506 | −1.82 |
| silver | 1,849 | −0.0367 | −1.52 |
| gold | 1,849 | −0.0240 | −0.99 |
| WTI | 1,848 | −0.0153 | −0.63 |
| corn | 1,424 | −0.0133 | −0.49 |

## The direction was wrong, and consistently so

Diagnostic: real −0.03047, random −0.01139 (sd 0.01054), **reversed +0.01228**.
Real is **−1.81 sd** below random; reversed is the only positive variant.

The pre-registration stated the direction in advance: commercials are hedgers
who sell into strength, so *rising* commercial net should precede *positive*
returns. The data says the opposite, in all six markets independently.

**This is not a licence to flip the sign and re-run.** Reversed sits at
+0.01228 against a random mean of −0.01139 — about 2.2 sd, on a statistic
chosen *after* seeing that it was the better of two. The pre-registration
forbids exactly this, and with good reason: the reversed variant is a
diagnostic, and inverting a rejected hypothesis after the fact is how a null
becomes a false discovery. It is a hypothesis for a fresh pre-registration
with its own mechanism, not a result.

## The engine was verified before the run

Six synthetic controls passed, including a look-ahead probe: with a leak
planted at lag zero, the unlagged run captured **+0.6531** and the correctly
lagged run **+0.0064**. The lag does real work.

Two controls failed on first attempt — both defects in the test harness, not
the engine. One planted an edge at lag 0 while the engine applies lag 1, so
the lag correctly destroyed it; the other built the leak's price path with
`cumsum(fwd)` instead of `cumsum(roll(fwd,1))`, hiding it from both runs.
Both are documented in the code, since a control that fails for the right
reason is worth keeping.

## Data provenance, finally verified

This test used the third COT export. The first was not CFTC data at all
(correlated −0.69 with the real thing); the second was symbol-blind and
returned byte-identical series for gold and silver. Only the explicit-CFTC-code
version passed: six distinct series, correct 1986 start dates, gold commercial
shorts at 396k/355k/408k across 2011/2016/2020.

---

## What would end this line

A null on criterion 1. At that point neither price-derived nor positioning
signals clear a demonstrable bar on obtainable data, and the honest conclusion
is that retail-accessible information does not support a demonstrable edge.
