# Pre-registration v3 — the spread as a signal, not a cost

```
WRITTEN:   2026-08-17
STATUS:    FROZEN BEFORE ANY OF IT WAS COMPUTED ON ANY DATA
FAMILY:    microstructure. Not price geometry. Nothing in DESIGN_BRIEF.md,
           silver15 or v2 tests anything of this kind.
TESTED ON: SPX500_USD and US30_USD, 2014-2020 -- NEVER PULLED, NEVER SEEN
```

---

## 1. The idea

Every strategy this project has tested — thirteen of them — has used **price
only**. The spread has appeared exclusively as a cost to be paid.

But this project holds something most retail backtests do not: **bid and ask,
separately, at 5-minute resolution, over twelve usable years.** The spread is
not just what you pay. It is the dealer's own statement, printed every five
minutes, about how dangerous they think the current flow is.

That is a data asset nobody in the candlestick literature is using, because
candlestick studies run on mid or last price.

## 2. Why this specifically, and why now

`RESULT_v1.md` established that fading a 3-sigma bar loses 2.39bp gross,
sign-consistent across seven years. The conclusion drawn was *"a 3-sigma bar
is information, not inventory."*

**That conclusion pools two populations that theory says are different.**
Market-microstructure theory (Glosten–Milgrom adverse selection; Ho–Stoll
inventory) says a dealer facing a large print does one of two things:

| the print is | dealer response | price afterwards |
|---|---|---|
| **informed** | widen hard and stay wide — protection against being picked off | **continues** |
| **uninformed inventory** | widen transiently, then narrow as the position is laid off | **reverts** |

v1 fired on both and measured the average. The average was negative, which
tells us the informed population dominates. **It does not tell us the inventory
population is absent** — and the inventory population is the one v1's
hypothesis was actually about.

The dealer knows which is which, in real time, and tells you: **by how much
they widen.**

> This is not a sign flip on v1. The direction is unchanged — still fade.
> What is added is a **conditioning variable**, one that was part of the
> theory from the start and simply was not used. v1's own failure is what
> identifies where to look.

## 3. The hypothesis

```
q_t = spread_t / median(spread over bars t-20 .. t-1)
```

`q` is how far the dealer widened on the shock bar, relative to their own
recent normal. It uses bars ≤ t only.

**H1 (mechanism).** Among 3-sigma bars, those with LOW `q` — the dealer did
not feel threatened — revert more than those with HIGH `q`.

**H2 (tradeability).** The low-`q` half, faded, clears the bar on its own.

These are different claims and are gated separately. silver15's crypto funding
case was *real, positive, and not worth having* (+1.46% against T-bills at
3.66%). H1 can be true while H2 is false, and that outcome is a finding, not a
disappointment.

## 4. Specification — zero new free parameters

Everything is inherited from v1 unchanged:

```
shock       |z| >= 3.0,  sigma = MAD over previous N=24 in-session bars
side        FADE the shock (long after a down-shock)   [unchanged from v1]
entry       OPEN of bar t+1, long pays ASK, short receives BID
exit        OPEN of bar t+1+H, H=6                     [unchanged from v1]
session     09:00-16:00 America/New_York, flat overnight
limits      non-overlapping, <= 4 round trips/day
```

The only addition:

```
split       at the MEDIAN of q, computed per instrument within the window
```

**Clarification made before the run, not after: v1's cost/vol ≤ 0.15 spread
gate is NOT inherited.** It has to be dropped, and the reason is structural
rather than convenient. That gate removes bars whose spread is wide relative
to volatility — which is close to removing high-`q` bars, exactly the half
this test needs in order to have something to compare against. Keeping it
would censor one arm of the experiment. Cost is therefore charged in full on
every trade and never gated. This costs Gate 2 something and is the right
trade: Gate 1 is the claim worth testing.

`q` is a **ratio to the instrument's own recent spread**, so it is regime-
neutral by construction — which is what makes a single median split valid
across a window where the raw spread falls by 3× (SPX500 2.50bp in 2014 to
0.66bp in 2025). The per-year distribution of `q` is reported so that
assumption can be checked rather than trusted.

**The median is used precisely so there is no threshold to choose.** It is
parameter-free, gives two equal samples, and cannot be tuned. A `q` cutoff at
1.2 or 1.5 would be a fitted parameter and is not permitted, now or later.

**Running parameter count for this hypothesis: zero.** Every value is
inherited from a pre-registration that was frozen before this idea existed.

## 5. The test statistic is the DIFFERENCE

```
PRIMARY:   mean_return(fade | q below median) - mean_return(fade | q above median)
```

Not the level of either half. The difference is a within-sample contrast: it
holds constant whatever common drift, cost regime and era effect both halves
share, and it is exactly what H1 predicts. Testing the low-`q` level alone
would confound the mechanism with the market's overall direction.

`t` on the difference, with unequal-variance standard errors, pooled across
SPX500 and US30.

## 6. Gates

### Gate 1 — H1, the mechanism. SPX500 + US30, 2014-2020, never seen.

```
PASS requires ALL of:
  1. difference > 0 with t >= 2.0 pooled across both instruments
  2. the sign of the difference agrees on BOTH instruments separately
  3. >= 200 trades in each half, pooled
  4. the difference holds in >= 5 of the 7 years, pooled
```

### Gate 2 — H2, tradeability. Same data, only if Gate 1 passes.

```
PASS requires:
  net Sharpe of the low-q half >= 0.76, charging the actual per-bar spread
```

### Gate 3 — NAS100 holdout, opened once, only if Gates 1 and 2 both pass.

```
net Sharpe >= 0.85 on 2021-2026
```

### Kill conditions

- **Gate 1 fails** → the mechanism is absent at this horizon on these
  instruments. Reject. No re-splitting on a different quantile, no trying `q`
  measured over a different window, no moving to a different `H`.
- **Gate 1 passes, Gate 2 fails** → *the mechanism is real and not tradeable.*
  Record it as such and stop. This is the crypto-funding outcome and it is a
  legitimate, useful result — but it is not a strategy and must not be
  promoted into one by relaxing anything.
- **The difference comes out NEGATIVE and significant** → the theory is
  backwards here: dealers widen for inventory rather than information. That
  would be genuinely interesting and would still be a rejection of this
  pre-registration.

## 7. Two things this design gets right that v1 did not

1. **It is tested on data that has never been touched.** SPX500 and US30 have
   not been pulled. The NAS100 fit window is spent and will not be used, even
   though looking would be easy and would tell us whether it is worth pulling
   the others. Looking first *is* the HARKing failure, and the whole cost of
   avoiding it is twelve minutes of downloading.
2. **The mechanism and the tradeability are gated separately**, so a real
   effect that is too small to trade gets recorded as a real effect that is
   too small to trade — not quietly upgraded, and not thrown away.

## 8. What this cannot establish

- **The spread here is a dealer's quote, not a market's.** OANDA's NAS100
  spread reflects OANDA's risk appetite and hedging, which is related to but
  not identical to the underlying CME order book. A result would be a fact
  about trading *this venue*.
- **`q` is measured on the close of the shock bar.** A dealer may widen and
  re-narrow within the five minutes, invisibly. The measurement is coarse and
  a null could be a resolution failure rather than an absent effect. **M1 data
  is available (21.6 years, already probed) and would resolve this** — that is
  the pre-declared response to a null on Gate 1, and it is a *measurement*
  improvement, not a re-specification.
- Correlated instruments again: SPX500 and US30 are close to one observation,
  not two.
- Thirteen rejections precede this. The honest prior is poor.

## 9. Also considered, and one door that is closed

**Tick-count / range divergence.** OANDA's `volume` is tick count — quote
updates, not traded size. High tick count with a *small* range is absorption:
lots of activity, no price movement, someone is soaking up flow. Not in any
candlestick list, uses the same untouched data. Held as a candidate for v4
rather than bundled here, to keep the test count honest.

**Quote skew — closed, do not attempt.** The natural idea is to check whether
the dealer skews quotes (ask further from mid than bid) to reveal inventory.
**It is not measurable on this feed:** OANDA's mid is exactly `(bid+ask)/2`,
verified across 4,560 bars to a maximum difference of 9e-13. The skew is
identically zero by construction. Recorded here so nobody spends a day
rediscovering it.

---

```
FROZEN 2026-08-17, before any computation on any instrument.
```
