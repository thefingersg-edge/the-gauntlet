# Pre-registration v6: does FX carry survive OANDA's financing markup?

Written 2026-08-11, **after** the power budget and the provenance check, and
**before** any backtest.

---

## Why this is not an eighth variation on the same idea

Seven families have failed. Every one was a **prediction**: read a signal,
forecast direction, take a position. v3 and v4 established why that kept
failing — the gross signal is ~zero *before* any cost. v3 pooled +0.0067 vol
units at zero cost across 13,013 trades; v4 was −0.00006 gross. v5 extended the
same finding to weekly CFTC positioning across 38 years and six markets.

Carry is not a forecast. Uncovered interest parity says the high-yielding
currency should *fall* by exactly the differential. The empirical claim is that
it falls by **less**, and the residual is compensation for bearing crash risk.
You are not predicting anything; you are being paid to hold something others
want to shed.

Two consequences matter for testing:

- **The edge accrues continuously, not per decision.** A prediction strategy's
  sample is its number of independent decisions — which is why v4's 258
  rebalances were fatal. A risk premium is earned every day held, so the
  sample is the number of independent *return* periods.
- **Signal persistence becomes a feature.** Carry barely moves month to month.
  For every prior family that meant a collapsed effective sample; here it
  means near-zero turnover and near-zero spread cost.

## THE EPISTEMIC HAZARD, STATED FIRST BECAUSE IT IS NEW

**This is the first pre-registration in the project written after a budget that
PASSED.** All seven predecessors were written knowing the budget was marginal
or hopeless, so the failure mode was wasted effort. Here it inverts: the
failure mode is now **confirmation**.

The project's own record is the warning. Every rejection so far was robust to a
bug that flattered it; the one PASS — v3's Sharpe +1.51 — was *entirely* a
barrier-snapping bug. A result that agrees with the budget will feel like
corroboration and will be exactly the kind of result this project has
historically got wrong.

Therefore: the engine gets synthetic controls **before** the run, the criteria
below are fixed **now**, and a pass triggers a forward test rather than
capital.

## Power budget, computed first (carry_budget.py, run 2026-08-11)

Live OANDA snapshot, 123 instruments. NO P&L computed.

```
gross annual carry (dispersion)   +4.668%
annual markup, charged every leg  +1.015%
NET ANNUAL CARRY                  +3.653%
book volatility (32,720 H4 bars)   5.19%
NET annual Sharpe                  +0.70     bar 0.45
MAX TOLERABLE MARKUP              +2.372%    actual +1.015%   headroom +1.357%
```

The decisive quantity is the markup. OANDA quotes `longRate` and `shortRate`;
in a frictionless market they would be exact negatives, so

```
carry_i  = (longRate - shortRate) / 2        markup-free differential
markup_i = -(longRate + shortRate) / 2       annual cost per side
```

Measured FX markup is **1.01–1.11% per side**, against a tolerance of 2.37%.
That headroom is why this family is testable and the previous seven were not.

Two structural findings from the same snapshot, both of which vindicate
excluding non-FX **before** any result was visible:

- BCO_USD returns a "carry" of **+63.7%** — the Brent futures roll expressed as
  financing, not carry at all.
- Every EUR index shares identical rates (−0.0468/−0.0032); every USD index
  identical (−0.0612/+0.0112), including JP225_USD, a *Japanese* index paying
  the *USD* rate. Index financing is pure funding with no instrument-specific
  carry. Index markup is 2.50% per side, 2.4× FX.

## Data provenance — verified before use

Six provenance failures in this project, all of which produced plausible
output. The rates are therefore **not** trusted for coming from FRED. They are
trusted because the differential they imply *today* agrees with the financing
OANDA is *quoting* today:

| | |
|---|---|
| pairs cross-checked | 13 |
| within 1.00pp tolerance | **13** |
| outside | **0** |
| largest gap | EUR_JPY 0.48pp |

The tolerance is deliberately wide: OANDA quotes a tom-next FX swap including
its own funding, FRED quotes unsecured interbank, and cross-currency basis
makes them legitimately differ. `fetch_rates.py --self-test` control 12
verifies the gate actually **rejects** a scrambled series — a gate that never
fires is decoration, which is how the `convertRootToCOTCode("Auto")` bug
survived.

**Rate family frozen on coverage, a data property, with no P&L in existence:**

| family | currencies | common window |
|---|---|---|
| overnight | 8/8 | 1994-01 → **2024-03** (CHF discontinued) |
| **3-month** | **8/8** | **2002-04 → 2026-01** |

Overnight is the better match on mechanism — CFD financing is charged daily —
but it loses CHF after 2024-03, and CHF is a funding currency on both sides of
the current book. 3-month is chosen for coverage. This is a choice between two
candidates and is frozen here.

---

## Hypothesis (fixed)

**H1.** A long-short FX carry book, held on OANDA CFDs and charged OANDA's
actual financing markup and measured spreads, earns a positive net return over
2006–2026, with a maximum drawdown no worse than 25%.

**H0.** It does not.

**Direction, stated in advance:** long the highest-carry instruments, short the
lowest. This is the sign the risk-premium mechanism predicts. The reversed
variant is a diagnostic, not an alternative hypothesis — and per the v5
precedent, a positive reversed result **must not** be flipped and re-run.

## Configuration (frozen)

```
universe      13 OANDA FX instruments with both price and rate coverage:
              EUR_USD GBP_USD AUD_USD NZD_USD USD_CAD USD_CHF EUR_GBP
              EUR_JPY GBP_JPY EUR_CHF EUR_AUD AUD_NZD NZD_CAD
signal        carry(BASE_QUOTE) = r_BASE - r_QUOTE
rates         FRED OECD IR3TIB01<CC>M156N, monthly
LAG           TWO FULL MONTHS after the observation month
book          long top 3 carry, short bottom 3
weighting     vol-scaled legs, gross risk normalised to 1 unit
vol window    12 months TRAILING, using only returns already realised
rebalance     monthly, non-overlapping
days scaling  carry and markup both scaled by daysCharged/7
              (GBP_JPY and EUR_JPY charge 6, not 7)
costs         (a) financing markup, per instrument, from the measured OANDA
                  snapshot, charged continuously on EVERY leg
              (b) measured spread from SPREAD_REL, charged on legs that change
window        2006-02-28 -> 2026-01-01   19.8 years   238 monthly observations
statistic     ONE pooled net return series
```

**Why a two-month lag.** FRED monthly values are period averages that are not
complete until the month ends, and OECD series publish with a further lag.
Trading month M on month M's average would be look-ahead. One month is the
honest minimum; **two is used because carry autocorrelates ~0.99 monthly, so
the extra month costs almost nothing and removes any argument about
publication timing.** The self-test includes an unlagged probe that must show
an inflated result; if it does not, the lag machinery is not working.

**No threshold on entry.** A threshold is a free parameter with no stated
mechanism.

**Top/bottom 3 of 13** is frozen now. It was chosen for the budget before any
P&L existed, and must not be revisited after seeing results.

**The 12-month trailing vol window** was not named in the first draft of this
document — a genuine gap, recorded rather than quietly filled. It is fixed
here, before the engine was run and before any P&L existed, at the shortest
window that still estimates a monthly volatility sensibly. Note the budget
used full-sample volatility for its denominator, which is in-sample; the test
uses trailing only, and the two numbers will therefore differ slightly.

## Success criteria (ALL three required)

1. **Profitable after all costs.** Pooled mean net return > 0, with the lower
   bound of a 1,000-sample bootstrap 95% CI also > 0.
2. **Maximum drawdown ≤ 25%**, peak-to-trough on the net equity curve.
3. **Not one pair or one year.** No single instrument contributes more than 35%
   of gross positive P&L; no single calendar year more than 30%.

Criterion 2 exists because Sharpe is the wrong statistic for carry taken alone.
The premium is compensation for crash risk: it earns steadily and loses
violently. A 0.70 Sharpe with severe negative skew is not the same object as a
0.70 Sharpe on a symmetric strategy, and low maximum drawdown is the project's
stated second priority.

**Diagnostics, explicitly NOT criteria:** reversed signal, randomised-sign
null, return skewness, net currency exposure, and the result at 2× markup.

## Stated power

19.8 years gives a 2-sigma bar of **0.449** annual Sharpe. The budget implies
0.70 at today's dispersion. A null therefore means *"no FX carry edge at or
above Sharpe 0.45, net of OANDA's actual costs, over 2006–2026"* — informative,
not underpowered.

**But effective breadth is far below six legs.** Decomposing the current book
to currency level:

```
long   USD +2   GBP +2   AUD +1
short  CHF -2   EUR -2   JPY -1
```

Six instruments resolve to roughly a three-way bet: long USD/GBP, short
CHF/EUR. That is coherent with the mechanism — those *are* the funding
currencies — but it means the book is far less diversified than the leg count
suggests, and one currency regime could dominate. Criterion 3 partly tests
this; the currency decomposition is reported as a diagnostic.

## Multiple-testing budget

**One run. One pooled statistic.** No sweep over book size, rebalance
frequency, lag, rate family, weighting or universe subset. If it fails, the
line is closed.

## Anticipated failure modes

- **Negative skew fails criterion 2 while criterion 1 passes.** The most likely
  outcome, and it is the gate working, not a defect. Carry lost ~30% in weeks
  in 2008 and the sample contains that.
- **Today's markup applied across 20 years is optimistic.** Broker markups have
  fallen over time, so the historical charge was probably higher. This is the
  one cost input that is a snapshot rather than a history. The 2× markup
  diagnostic exists to show how much it matters.
- **The 2008 sample is a feature, not a bug.** A window without a crisis would
  overstate carry badly. Any result must be checked for whether it depends on
  excluding it.
- **Monthly rates are period averages**, not point-in-time observations. The
  two-month lag absorbs this.
- **EUR 3-month ends 2026-01**, truncating the window by ~7 months.
- **Rank overlap.** EUR appears in five of the thirteen instruments, so ranks
  are not independent draws and the book concentrates by construction.
- **Regime.** 2006–2026 spans ZIRP, negative rates in EUR/CHF/JPY, and
  normalisation. Carry dispersion was near zero for much of 2012–2021, so a
  large part of the sample may contribute nothing either way.

---

## What would end this line

A null on criterion 1, or a drawdown so far beyond 25% that no position sizing
rescues it. At that point price-derived signals, positioning, and risk premia
have all been tested on obtainable data, and the honest conclusion is that
retail-accessible information does not support a demonstrable edge.

**A pass does not end it either.** A pass means: re-run `audit.py`, then
forward-test on unseen data. Not capital.

---

# RESULT (recorded 2026-08-11)

**H1 REJECTED.** Criteria 1 and 2 failed; criterion 3 passed.

| | |
|---|---|
| observations | 226 months, 2007-02 → 2025-11, 18.8 years |
| mean gross per month | **−0.00109** |
| mean cost per month | +0.00090 |
| **mean net per month** | **−0.00198** |
| bootstrap 95% CI | **[−0.00399, −0.00005]** — entirely below zero |
| implied annual Sharpe | **−0.43** (bar 0.46) |
| **maximum drawdown** | **37.5%** (gate 25%) |
| positive months | 46.5% |
| top instrument / year | EUR_AUD 15.0% / 2010 14.5% |

The window starts 2007-02 rather than 2006-02 because the 12-month trailing
vol window and the 2-month lag consume the first year of price history.

## The cost was not the binding constraint

**Gross Sharpe at ZERO cost: −0.23.** The book lost money before a single
basis point of markup or spread was charged. This is the same finding as v3
(+0.0067 gross at zero cost), v4 (−0.00006 gross) and v5 — the signal is not
being eaten by costs, it is not there.

That matters for interpreting the budget, and the distinction is worth being
precise about rather than glossing:

- **The budget measured the right thing and got it right.** It asked whether
  OANDA's markup leaves room under the detectability bar. Answer: yes, 1.36pp
  of headroom, and that remains true.
- **The budget could not measure whether the premium exists.** A carry book's
  return is *carry earned plus the spot move*, and the budget only ever saw
  the carry half — published financing rates contain no information about what
  the exchange rate then does. Uncovered interest parity predicts the spot move
  cancels the carry exactly; the entire empirical case for carry is that it
  cancels less than fully. **Only the test could measure that, and in this
  sample the spot move more than cancelled it.**

So the budget was not wrong, it was silent on the decisive quantity. A power
budget bounds what a test can resolve; it cannot tell you the effect is there.
That distinction was implicit in every earlier budget and is now explicit.

## The forecast was wrong, and in an instructive direction

The pre-registration's stated expectation was *"criterion 1 passes and
criterion 2 fails on 2008."* Both halves were wrong in the informative way:

- criterion 1 also failed, because gross was negative
- skewness came in at **−0.18**, nowhere near the violent left tail carry is
  famous for — precisely *because* the book never earned the premium that the
  tail is supposed to be compensation for. No premium, no crash risk, no skew.

The drawdown of 37.5% is therefore not a carry crash. It is the slow bleed of
a position with a small negative drift.

## Direction: do not flip it

Diagnostic: real −0.00198, random −0.00113 (sd 0.00081), reversed **+0.00019**.
Real sits **−1.05 sd** from random — not a significant anti-signal, just weak
and negative.

The reversed variant is +0.00019, which is **indistinguishable from zero** and
far below the bar. Even setting aside that the pre-registration forbids
flipping a rejected hypothesis after the fact, there is nothing here to flip
*to*. Recorded explicitly so that the v5 temptation is not re-run in a
different costume.

## The 2× markup diagnostic

Mean −0.00285, Sharpe −0.62, maxDD 48.3%. Stated in advance as a robustness
check on the one cost input that was a snapshot rather than a history. It does
not change the verdict in either direction, which is the useful outcome: the
conclusion does not rest on the markup assumption.

## Anticipated failure mode, confirmed

The document predicted: *"carry dispersion was near zero for much of 2012–2021,
so a large part of the sample may contribute nothing either way."* Today's
dispersion of 4.67% is a post-normalisation figure, and using it in the budget
implicitly assumed a rate environment that held for a minority of the window.

## The engine was verified before the run

Thirteen synthetic controls passed, including a two-sided look-ahead probe:
an edge planted for an unlagged engine gave **+0.01910 unlagged vs −0.00118
lagged**, and an edge planted at the engine's own lag gave **+0.01727 lagged
vs +0.00043 unlagged**. The shift moves the signal, and in the right direction.

Two controls failed on first run, both defects in the harness:

1. **The look-ahead probe could not fail.** It planted the leak on a
   random-walk carry surface — but real carry is near-unit-root, so
   `rank(C[m])` and `rank(C[m−2])` are almost the same ranking and *no* lag
   can be shown to destroy anything. The probe returned +0.01857 unlagged and
   +0.01882 lagged and would have "passed" a broken lag. Fixed by planting on
   an i.i.d. surface.
2. **An off-by-one in the planted alignment.** An engine at lag L reads
   `C[m−L]` and earns `rets[m+1]`, so an edge it should capture must be
   planted at `shift(L+1)`, not `shift(L)`. Control 2 had been passing at the
   wrong lag, rescued by the very persistence that broke control 6.

Both are the same underlying error and both flattered the engine. They are
documented in the code, since a control that fails for the right reason is
worth keeping.

---

## Status of this line

**Closed.** Per the multiple-testing budget: one run, one statistic, no
retuning, no sign flip, no parameter sweep.

Eight families have now been pre-registered and rejected. Price-derived
signals, positioning, and risk premia have each been tested on the best
obtainable data, and in every case the gross signal was at or below zero
*before* costs. The honest conclusion is unchanged and now better supported:
retail-accessible information does not support a demonstrable edge on these
instruments.
