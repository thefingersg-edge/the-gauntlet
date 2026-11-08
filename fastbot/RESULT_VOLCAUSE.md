# RESULT — does the cause of volatility carry a sign?

```
RUN:      2026-09-11
SPEC:     PREREGISTRATION_v21, frozen before any forward return
CODE:     vol_cause.py 1.0
SAMPLE:   SPX500_USD M15 RTH, 3,403 sessions, 84,163 bars, 2013-2026
VERDICT:  No. And the contrast with the volatility result is the
          sharpest number this project has produced.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The one comparison that matters

Same 84,163 bars. Same machinery. Same run.

```
predicting MAGNITUDE   high-vol 22.00 bp vs low-vol 14.80 bp    t = 46.9
predicting DIRECTION   every cell of the 2x2                   |t| <= 1.6
```

**A thirty-fold difference in signal strength between forecasting how
much and forecasting which way.** v19 put that ratio at 7.5× in
information terms; measured as returns on the same bars it is far
starker.

Gate A was the positive control — a method that cannot see volatility
clustering cannot be trusted to report absence of anything else. It saw
it at **t = 46.9**. The direction nulls that follow are therefore
readable.

## 2. The 2×2 is flat

```
                        LIQUID                 ILLIQUID
                   n   cont bp    t        n   cont bp    t
HIGH VOL      25,842     -0.05  -0.2   16,327     +0.37   1.5
low  vol      16,060     +0.05   0.3   25,934     +0.13   1.0
```

Continuation in bp; negative would be reversion. **All four cells sit
within 0.42 bp of each other and none reaches |t| = 1.6**, on 84,163
observations. That is not an inconclusive result — it is a precise zero.

```
[FAIL] Gate B  illiquid high-vol +0.37 bp, t = 1.54
[FAIL] Gate C  liquid minus illiquid -0.42 bp, t = -1.27   <- THE HYPOTHESIS
[PASS] Gate D  low-vol split -0.08 bp, t = -0.35
[FAIL] Gate E  0.42 bp vs a 3.53 bp bar
[FAIL] Gate F  eras -0.79  +0.15  -0.64
```

Robustness at both pre-specified horizons is equally flat: H=1 gives
−0.07 bp, H=12 gives −0.25 bp, both at t ≈ −0.42.

**Gate D passing is the one piece of good news.** The worry was that
selecting on a wide spread and then measuring reversion would
manufacture reversion mechanically. It didn't — the low-volatility
split shows nothing either. So the zero is a real zero, not a
microstructure artifact cancelling a real effect.

## 3. My predictions were wrong, including the sign

| | predicted | measured | |
|---|---|---|---|
| Gate A | pass comfortably | t = 46.9 | **held** |
| Gate B | **pass** — illiquid reverts | **+0.37, continuation** | **missed, wrong sign** |
| Gate C | **pass, +2 to +6 bp** | **−0.42 bp** | **missed, wrong sign** |
| Gate D | coin flip | pass | held |
| Gate E | **fail** | fail | **held** |

I predicted liquidity-driven moves would revert because short-horizon
reversal after illiquidity is a documented effect. They don't — not at
this timescale, on this instrument, with these instruments for measuring
liquidity.

## 4. Why the idea was still right, and where it probably went

The reasoning was sound: volatility is a scalar, and its cause could
carry a sign. The precondition check even confirmed the decomposition
was available — `corr(spread, range) = +0.001`, so the liquidity axis
really is orthogonal to the volatility axis rather than a restatement of
it.

The most likely explanation for the null is not that the mechanism is
absent but that **it is somebody else's business already**. If
liquidity-driven moves reverted predictably, providing that liquidity
and collecting the reversion is precisely what a market maker does. By
the time the effect reaches a 15-minute bar on a retail CFD, it has been
harvested at second scale by people with co-located infrastructure.

That is this project's oldest finding wearing new clothes: **nothing
died of absence, everything died of access.** Now six for six.

## 5. The gap worth knowing about

**The one cell where the cause is actually known had 108
observations.**

```
scheduled event   n=   108   cont +1.19 bp   t +0.20
no event          n=42,061   cont +0.11 bp   t +0.66
```

CPI and payrolls release at **08:30 ET — before the 09:30 RTH open** —
so the sample choice made for other reasons excluded almost every event
where causation is documented rather than inferred. Only FOMC at 14:00
lands inside the window.

Spread and volume are *proxies* for the cause. The event table is the
only **instrument** — a bar where information provably arrived. It was
barely tested, and extending the sample to pre-market bars (which OANDA
quotes) would recover roughly ten times the events.

**That is a well-posed follow-up with a known instrument, and it is the
honest next step rather than tuning the liquidity definition until
something appears.**

## 6. What this does and does not settle

**It settles the question as asked.** Splitting volatility by spread and
volume does not produce a signed prediction at 15 minutes on SPX500_USD
over 2013-2026, at any of three horizons, in any era, and the difference
is a fifth of the cost of acting on it.

**It does not settle the idea.** Spread and tick volume are coarse
instruments for liquidity; real depth data would be better and OANDA
does not provide it. And the timescale may simply be wrong — if the
mechanism operates in seconds, a 15-minute bar cannot see it.

**It does not test the event route**, for the reason in §5.

---

**Investigation thirty-seven.** The first idea in this project that came
from Dave rather than from a paper or a video — and the first null where
the positive control was thirty times stronger than anything it was
looking for.
