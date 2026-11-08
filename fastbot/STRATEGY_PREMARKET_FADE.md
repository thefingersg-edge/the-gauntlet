# STRATEGY — fade the 08:30 release move

```
WRITTEN:  2026-09-12, from RESULT_PREMARKET (investigation 38)
STATUS:   SPECIFIED AND MEASURED. Not recommended, and the reason is
          in section 4 rather than in a caveat at the bottom.
```

**I am not a financial adviser. This is a specification and a
measurement, not a recommendation to take a position.**

---

## 1. The rule, complete enough to code

```
UNIVERSE     SPX500_USD on OANDA
CALENDAR     events_v2.csv -- scheduled US macro releases timed 08:30 ET
             (CPI, non-farm payrolls, initial jobless claims)

SIGNAL BAR   the 15-minute bar 08:30-08:45 ET on a release date
DIRECTION    FADE it.   close > open -> SHORT
                        close < open -> LONG
                        close = open -> no trade
ENTRY        market, at the open of the 08:45 bar.  Cross the spread.
EXIT         market, at the close of the 09:45 bar.  Cross it again.
             Four bars. Sixty minutes. No stop, no target.
SIZE         fixed notional per trade
```

**Why a pure time exit and no stop.** A bracket with a stop at −1R and a
target at +kR on a driftless price has expectation exactly zero for any
k and any stopping rule — the trade's own geometry is the null. Bolting
a stop onto this would not reduce its risk, it would replace the thing
being measured with a different thing that happens to have the same
name.

**One structural merit, and it is real.** The position is opened and
closed inside the same hour, so **it never pays financing.** Dave's
standing requirement is profit after costs *and financing*; this rule
answers half of that by construction. It does not survive the other
half.

## 2. What it is worth, measured

13.4 years, 981 trades, at the round-trip cost actually paid on these
bars (1.77 bp — sell the bid, buy the ask):

```
             n   /yr   gross      net       SD   annual   breakeven cost
  POOLED   981    72   +1.68    -0.09    29.9    -6.6 bp        1.68 bp
  CLAIMS   696    51   +0.59    -1.18    29.5   -60.1 bp        0.59 bp
  CPI      169    12   +2.18    +0.41    26.2    +5.1 bp        2.18 bp
  NFP      162    12   +4.55    +2.78    32.8   +33.2 bp        4.55 bp
```

**The pooled rule loses 6.6 bp a year.** Claims is the worst thing in
the table: 51 trades a year, each paying a 1.77 bp spread to capture
0.59 bp, for −60 bp annually. **Trading it is strictly worse than not
trading.**

**Payrolls is the only line that is positive**, and at Dave's actual
cost base it clears comfortably — break-even is 4.55 bp against 1.77 paid.
**This is not a cost problem.** For the first time in the project, a
candidate is not killed by the spread.

## 3. So why is it still not a strategy

```
             annual     Sharpe    +/- SE    years to distinguish from zero
  POOLED      -6.6 bp    -0.03      0.27           5,832
  CLAIMS     -60.1 bp    -0.29      0.27              49
  CPI         +5.1 bp    +0.05      0.27           1,331
  NFP        +33.2 bp    +0.29      0.27              46
```

**Payrolls is a Sharpe of 0.29 with a standard error of 0.27.** It would
take 46 years of payrolls prints to tell it from zero at two standard
errors. The sample is 13.4.

And then the number that settles it:

```
  best stratum   NFP     Sharpe +0.29  =  +1.07 of its own standard error
  worst stratum  CLAIMS  Sharpe -0.29  =  -1.07 of its own standard error

  expected |max| of 4 draws from noise              1.03
```

**The best and worst of the four strata sit symmetrically either side of
zero, each almost exactly where the extreme of four noise draws is
expected to sit.** That is not a signal in payrolls and a catastrophe in
claims. It is one null cut four ways.

This is the selection signature this project has learned to recognise:
the apparent edge lives in the smallest cell, and its size is what
picking the maximum of N would produce for free.

> **CORRECTION, added 2026-09-12 after RESULT_CONFIRM §4. This section
> is wrong.** The Sharpes above are *net of cost*, and subtracting a
> fixed 1.77 bp from strata with different gross edges is what
> manufactured the symmetry. Gross, none of them is negative — claims
> +0.59, CPI +2.18, payrolls +4.55. Claims is not the mirror image of
> payrolls; it is the same effect, smaller, with the spread eating it.
> The held-out run then reproduced payrolls at +3.23 bp with a stable
> sign, which a maximum-of-four-noise-draws would have had no reason to
> do. **Read §2's economics and §5's confirmation design; do not read
> this section's argument.**

## 4. The mechanism I proposed is not supported either

RESULT_PREMARKET §8 explained the reversion as a thin pre-market
overshooting, corrected when real liquidity arrives at 09:30. That story
makes a prediction — **a bigger overshoot should revert further** — and
the prediction fails on the data that generated it:

```
  quintile by the size of the release-bar move
  Q1  |move|  1.43 bp   gross +1.16   t +0.81
  Q2          4.27      gross +2.37   t +1.41
  Q3          7.86      gross -0.45   t -0.27
  Q4         14.19      gross +4.66   t +2.22
  Q5         34.24      gross +0.66   t +0.20
```

**Non-monotonic, sign-flipping, and the largest moves show nothing.** Q4
at t = 2.22 is one cell of five doing what an isolated cell does.

A hypothesis cannot be confirmed on the data that produced it, but it
can be **disconfirmed** there, and this one is. The overshoot story in
RESULT_PREMARKET §8 should be read as what it was — a plausible
narrative written before anyone checked it.

## 5. What would actually change the verdict

Not a tuned horizon, not a filtered subset, not a stop. Two things, in
order of how much they would settle:

**a) Confirmation on data never used for this question.** If payrolls
reversion is real it should appear in SPX500_USD 2003-2012 — 422
releases at this slot, excluded from v22 for a documented reason (bid
equals ask there, so cost is unmeasurable) that **does not affect the
sign question.** The old bars are not flat back-fill: they move a median
16.44 bp at 08:30 against 7.87 bp in the modern sample. The sign can be
asked there; the cost cannot, and does not need to be.

**b) Confirmation on other instruments.** NAS100, US30 and DE30 all
react to US payrolls and none has been looked at for this. It needs an
OANDA history fetch — the local files hold ten weeks each — and it would
give genuinely independent samples with real bid and ask.

**Registered prediction, before either is run: both fail.** If payrolls
is the maximum of four noise draws, a held-out sample has no reason to
reproduce it, and the honest expectation is a gross figure near zero
with the sign unstable. **If it reproduces at +4 bp or better on 120
held-out events, I am wrong about this being selection** — and that is
the outcome worth having.

## 6. What this is good for as it stands

Nothing tradeable. But the rule is fully specified, its cost is
measured rather than assumed, its statistical resolution is stated in
years, and the reason it fails is arithmetic rather than opinion.

**It is also the cleanest teaching case the project has produced**: a
candidate that survives the cost gate — the thing that killed the
previous six — and dies anyway, on sample size, in the one stratum that
looked best.
