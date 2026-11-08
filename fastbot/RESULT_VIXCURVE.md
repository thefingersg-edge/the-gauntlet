# The VIX term structure — the first thing here to survive its own crisis era

```
RUN:      2026-08-17, RESTATED 2026-10-27
METHOD:   vix_curve_budget.py v1.1 — MEASUREMENT ONLY
DATA:     VX1! vs VX2!, TradingView, 269 months, 2004-03 to 2026-07
          (also run on VIX/VIX3M proxy and a truncated 2016+ futures export)
VERDICT:  a real term-structure carry premium, ~0.34 vol pts of carry,
          positive in all three eras including 2008 and 2020. Ahead of equity
          beta before costs, by less than the first write-up claimed.
          Not a rejection.
```

> **RESTATEMENT NOTE — 2026-10-27.** The original figures in this file were
> computed before `RESULT_VIXDAILY.md` found that TradingView stamps a daily
> futures bar at the session *open* — 17:00 America/Chicago on the previous
> calendar day — which labelled every date one day early by an amount that
> changed with daylight saving. That fix landed in
> `vix_curve_budget.load_csv` at 15:08 on 2026-08-18; this file was written at
> 11:32 and never re-run. Reintroducing the bug reproduces the old figures
> exactly, so the cause is established rather than inferred.
>
> **The verdict does not change. Two supporting claims do.** The premium is
> majority *mean reversion*, not majority carry, and the slope-versus-level
> signature stays wrong. Superseded figures are listed in §8.

---

## 1. I got the direction of this wrong, and the full sample says so

Last run, on a truncated 2016–2026 export, I wrote that **"every volatility
premium measured so far looks excellent on a sample that starts after the
previous disaster"** and expected adding 2008 to make things worse.

The headline Sharpe did fall — 0.82 on 2016+, **0.70** on 2004+. That part
held. But the thing that actually matters went the other way:

| sample | beta | carry share | **carry (vol pts)** |
|---|---|---|---|
| VIX3M proxy, 2009+ | +1.15 | −13% | — (negative) |
| real futures, 2016+ | **+1.05** | **−5%** | **−0.05** |
| **real futures, 2004+** | **+0.60** | **39%** | **+0.34** |

On the truncated sample the carry component is **not merely small, it is
absent**: beta 1.05 is a pure forecast, and you collect nothing. Adding
history takes carry from roughly zero to 39% of the premium. My claim was
directionally wrong and the correction is worth more than the original point.

*(The proxy row is carried over from the original run. It needs a VIX3M
series that is not in `data/`, so it has not been re-run under the date fix.)*

### Why, and it is not a fluke

Beta is identified by **variation in the regressor**. The 2016–2026 sample
sits in a low-dispersion regime — the curve rarely moved far from its mean, so
there was little slope variation from which to estimate how much of it gets
realised. The full sample contains slopes from **−7.25** (November 2008) to
strongly positive, and estimates beta far more precisely.

The truncated sample did not give a *pessimistic* answer. It gave a *noisy*
one, and noise in the regressor biases beta toward 1 in this setup by
shrinking the estimate's identification. The longest sample is the best
estimate, not merely the most complete.

## 2. The decomposition, on the full history

```
premium +0.86  =  intercept +0.52 (61%)  +  carry +0.34 (39%)
```

| component | value |
|---|---|
| whole premium | +0.86 vol pts, Sharpe +0.70, t +3.30 |
| mean reversion (intercept) | +0.52 |
| **term-structure carry (slope)** | **+0.34** |

**The majority of the premium is mean reversion — VIX drifting down — not
carry.** The original write-up claimed the opposite, on the pre-fix dates.
Carry is a real and substantial minority of a real premium, which is a weaker
claim than the one this file used to make and is the one the data supports.

### Three signatures: two right on the full history, one still wrong

| | proxy 2009+ | real 2016+ | **real 2004+** |
|---|---|---|---|
| contango pays more than backwardation? | **no** (1.75 vs 4.24) | **no** (0.85 vs 1.39) | **yes** (0.97 vs 0.24) |
| premium tracks slope more than level? | **no** (−0.05 vs +0.31) | **no** (−0.02 vs +0.29) | **no** (+0.13 vs +0.16) |
| beta below 1? | **no** (1.15) | **no** (1.05) | **yes** (0.60) |

A carry trade should earn more when the curve is steep and should track the
slope rather than the level. On the full history the first and third are
right, and by wide margins — contango months pay four times what
backwardation months pay. The second is still wrong: the premium tracks the
VIX *level* slightly better than the *slope*, which is what a mean-reversion
story predicts, and is consistent with the decomposition above.

That is a coherent picture, but it is the picture of a premium that is **part
carry and more than half mean reversion** — not the clean carry signature the
original claimed.

## 3. Era sign-consistency — the criterion nothing in this project has passed

```
2002-2009    Sharpe +0.30    worst -26.52    (2008-10)
2010-2017    Sharpe +1.07    worst -14.60    (2015-08)
2018-2026    Sharpe +0.70    worst -23.45    (2020-03)
```

**Three of three positive, including two crisis eras.** `DESIGN_BRIEF.md`
used exactly this test to reject fourteen price conditions and twenty-five
indicators, on the grounds that *"a condition worth trading should at minimum
keep the same sign in every era."*

This is the first thing measured across silver15, pineport and fastbot that
does, and the date correction does not touch it. The era Sharpes all moved;
none of them changed sign.

## 4. And now the caveats, which are not small

**The tail is the product.** Skew −2.13; the worst month is −26.52 vol points
(2008-10) at **6.2 standard deviations**, with 2020-03 at −23.45 behind it.
Both are worse than this file originally reported.

**Skew-adjusted, the margin over doing nothing clever is thin, and thinner
than first written.** Raw Sharpe falls from +0.73 to +0.70 and skew worsens
from −1.85 to −2.13, so the adjusted margin over equity beta narrows on both
terms. The original stated ~+0.57 against ~+0.42; that adjustment needs
redoing in `vix_carry_budget.py` on corrected dates before a number is quoted
here, and it will be smaller.

**Beta 0.60 is still a lower bound, so carry 0.34 is still an upper bound.**
Residual noise in the front-contract slope (time to expiry varies through the
month) continues to attenuate beta toward zero. The original file wrote: *"If
the true beta is 0.60, carry falls to ~0.29."* On corrected dates beta **is**
0.60. The same reasoning now applies one step further out.

**This is gross.** No bid-ask on the VX roll (~0.05 vol points per leg,
monthly, so ~13% of the premium), no margin drag, no financing. And VIX
futures margin *rises* in exactly the months that produce the −26s, which is
the practical mechanism by which people are forced out at the bottom rather
than riding through.

**It needs a futures broker.** Neither OANDA nor Kraken.

## 5. Verdict

**Not a rejection.** After eighteen investigations this is the first candidate
with: a stated economic mechanism, a positive sign in every era including two
crises, and a carry component that survives decomposition — as a minority of
the premium rather than a majority.

**Also not yet a strategy.** ~0.34 vol points of genuine carry, gross, with a
−26-vol-point tail at 6.2 sd and a margin profile that worsens precisely when
it hurts. The honest summary is *a real premium, mostly mean reversion, with a
thin margin over equity beta and a failure mode that is forced liquidation
rather than underperformance.*

The next honest step is a proper cost and margin budget — what the roll costs,
what margin does in a 2008 or 2020 month, and what position size survives a
−26 with the account intact. That is the same discipline that opened this
project, applied to the one candidate that has earned it.

## 6. What this changes about the earlier conclusion

`RESULT_VRP.md` said the variance premium unhedged loses to equity beta, and
that stands — it measured **variance** (convex, so a spike hurts far more) and
read +0.32 including 2008.

Selling **volatility** via the futures curve is a materially different
exposure: linear rather than convex, +0.70 raw over the same kind of sample.
The convexity is most of the gap. That distinction was implicit before and is
now measured.

## 7. Scoreboard

**Eighteen investigations. Fifteen rejections, one measured-but-unreachable
premium, one headline that dissolved on decomposition — and one candidate that
survived the decomposition, the crisis eras and its own author's expectation.**

## 8. Superseded figures — the pre-fix run

Recorded so the restatement is auditable. Left column is what this file said
before 2026-10-27; right column is the same measurement with session dates
corrected.

| | pre-fix | corrected |
|---|---|---|
| whole-premium Sharpe | +0.73 | **+0.70** |
| premium, mean | +0.87 | +0.86 |
| beta | +0.45 | **+0.60** |
| intercept (mean reversion) | +0.39 (45%) | **+0.52 (61%)** |
| carry (slope) | +0.48 (55%) | **+0.34 (39%)** |
| skew | −1.85 | **−2.13** |
| worst month | −23.93, 5.8 sd | **−26.52, 6.2 sd** |
| era 2002-2009 Sharpe | +0.40 | **+0.30** |
| era 2010-2017 Sharpe | +1.16 | **+1.07** |
| era 2018-2026 Sharpe | +0.65 | **+0.70** |
| contango vs backwardation | 0.96 vs 0.45 | **0.97 vs 0.24** |
| premium ~ level vs slope | +0.15 vs +0.18 | **+0.16 vs +0.13** |
| real futures 2016+, beta | +0.79 | **+1.05** |
| real futures 2016+, carry share | 22% | **−5%** |

Unchanged: 269 months, 2004-03 to 2026-07; three-of-three era sign
consistency; the verdict.
