# PREREGISTRATION v21 — does the CAUSE of volatility carry a sign?

```
WRITTEN:  2026-09-11, after a correlation-only precondition check and
          BEFORE any forward return has been computed
STATUS:   FROZEN
SUBJECT:  whether splitting volatility by its apparent cause -- news,
          informed flow, or liquidity withdrawal -- produces a signed
          prediction where volatility alone produces none
ORIGIN:   Dave's question, not the literature's. There is no published
          result to anchor to, so section 6 registers priors rather
          than replications.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The idea, stated precisely

v19 measured that candle shape carries **7.5× more information about
magnitude than about direction**. That is not a quirk — **volatility is
a scalar and has no sign.** Knowing a big move is coming cannot tell you
which way it goes.

But the *cause* might:

```
volatility because INFORMATION ARRIVED     price has genuinely repriced
                                           -> the move should PERSIST

volatility because THE BOOK WENT THIN      nothing was learned, someone
                                           simply had to trade
                                           -> the move should REVERT
```

Same observed volatility, opposite predictions. **If the two can be told
apart, the scalar acquires a sign.**

## 2. Why this is measurable here and usually is not

The precondition check, correlations only:

```
corr(spread, range), 2013-2026, n=319,147   =  +0.001
```

**Spread and volatility are independent on this instrument.** The
obvious objection — that wide spreads are just volatility restated —
does not apply. The liquidity axis is orthogonal to the volatility axis,
so the 2×2 below is a real decomposition rather than a re-slicing.

Spread and volume line up as expected:

```
tight spread + high volume   52,249      wide spread + high volume  27,543
tight spread + low  volume   27,537      wide spread + low  volume  52,245
```

23 years of **bid and ask**, not mid-only, is what makes the liquidity
axis a measurement rather than a proxy.

## 3. Hard precondition: the sample starts in 2013

RESULT_PREANN established that **every bar before 2012 has bid exactly
equal to ask** — back-filled index data, not dealt quotes. The spread
axis does not exist there.

```
SAMPLE   2013-01-01 to 2026-08-28, RTH bars only
```

Using pre-2013 data would put half the sample in a cell where the
liquidity measure is identically zero. **That is not a judgement call,
it is the difference between a measurement and a fiction.**

## 4. The construction, frozen

Every RTH bar is placed on two axes, each normalised **within its
time-of-day slot and calendar year** — because the intraday U-shape is
real and OANDA's tick volume is badly non-stationary (median 13 in 2005,
494 in 2020, 407 in 2025). Raw comparisons across eras would measure the
platform's growth, not the market.

```
VOLATILITY   range / ATR14,  above or below its slot-year median
LIQUIDITY    rank(spread) - rank(volume), above or below its
             slot-year median  ->  ILLIQUID / LIQUID
```

An **EVENT** overlay marks bars containing a scheduled release from
`events.csv` (FOMC, CPI, NFP — 1,092 events with sourced timestamps).
Those are information-driven by construction, and are the one cell whose
cause is known rather than inferred.

**The outcome — continuation, signed:**

```
entry    the MID OPEN of the next bar      (never the signal bar's close)
exit     the MID CLOSE of bar t+H
cont_bp  +sign(close_t - open_t) x (exit/entry - 1) x 1e4
```

Positive is **continuation**, negative is **reversion**. Primary
H = 4 bars; H = 1 and H = 12 pre-specified as robustness, reported
together and never substituted.

## 5. The gates

**Gate A — the positive control, and it can void the run.**

```
PASS   high-volatility bars are followed by larger |moves| than
       low-volatility bars, t >= 5.0
```

Volatility clustering is the one thing here that is certainly true. **A
method that cannot reproduce it cannot be trusted to report anything
else**, and Gate A failing discards the whole run — the same rule that
made v19's direction result readable.

**Gate B — does illiquid volatility revert.**

```
PASS   high-vol ILLIQUID bars show cont_bp < 0, t <= -2.0
```

**Gate C — is the cause doing the work.**

```
PASS   high-vol LIQUID minus high-vol ILLIQUID, t >= 2.0
```

**This difference is the entire hypothesis.** Gate B alone could be
generic short-horizon reversal; Gate C is what says the *cause* carries
the sign.

**Gate D — the mechanical check, which is the one most likely to kill it.**

```
PASS   the same liquidity split on LOW-volatility bars does NOT show
       the same pattern
FAIL   -> the effect is microstructure: selecting on a wide spread and
          then measuring reversion manufactures reversion, and it would
          do so at any volatility level
```

**Gate E — cost, and it is stacked against us by construction.**

```
PASS   the Gate C difference exceeds 2x the spread ACTUALLY PAID in the
       illiquid cell
```

The edge, if it exists, lives precisely where the spread is widest.
**You would pay the illiquidity to harvest the illiquidity premium.**
That is the classic way this family of effects dies and it is named here
in advance.

**Gate F — present in all three disjoint eras.**

## 6. Predictions, registered before the run

No published result to anchor to, so these are priors and are labelled
as such.

- **Gate A passes comfortably.** Calibration.
- **Gate B passes.** Illiquid high-vol bars revert — short-horizon
  reversal after liquidity-driven moves is a real, documented effect.
- **Gate C passes but modestly** — I expect a difference of **2 to 6 bp**
  between the liquid and illiquid cells.
- **Gate D is a coin flip and it is the one I am least sure of.** If
  low-vol wide-spread bars revert just as much, the whole thing is
  bid-ask bounce.
- **Gate E FAILS.** This is the prediction I hold most firmly: the
  difference will be real and roughly equal to the spread you must cross
  to collect it. Five candidates in this project have died at exactly
  this step.

**If Gate E passes I should suspect the spread measurement before
celebrating**, because an illiquidity premium that exceeds its own
illiquidity cost would be unusual.

## 7. Kill conditions

- **The signal bar's close is never an entry price.** Entry is the next
  bar's open, per v17 and v18.
- **No lookahead.** ATR14 is strictly prior; the slot-year medians use
  the full sample and set *bucket boundaries only*, never outcomes, and
  the Gate C contrast is within-cell so a boundary shift cannot create a
  difference.
- **A result above 30 bp** at H=4 is a bug until proven otherwise.
- **One run.** No moving the liquidity definition, H, or the buckets.

## 8. What this cannot do

**It cannot identify the cause, only proxy it.** A wide spread with thin
volume is *consistent with* liquidity withdrawal; it is not proof of it.
The event overlay is the only cell where the cause is actually known.

**OANDA's volume is tick count at one venue**, not exchange volume. It
measures activity on the platform Dave trades on — which is arguably the
right thing for this purpose, and is not the same thing as market-wide
participation.

**Investigation thirty-seven.** The first in this project testing an
idea that did not come from a paper or a video.
