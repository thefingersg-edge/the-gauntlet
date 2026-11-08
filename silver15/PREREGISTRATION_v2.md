# Pre-registration v2: is the cross-metal residual PROFITABLE after costs?

Written 2026-08-09, after the v1 test was rejected and **after** a power budget
was computed but **before** any v2 backtest has been run.

---

## What changed since v1, and why

v1 failed all four criteria — and then the power calculation showed it could
never have passed: it needed ~1,400 independent trades and generated 165. The
thresholds and the sample floor were not mutually achievable. That is a defect
in the pre-registration, not a finding about markets, and it would have
invalidated a *positive* result exactly as much as the negative one.

Two things are different here.

**1. The power budget came first.** `power_budget.py` was run before this
document existed. It looks only at spreads, trade counts, cost/volatility
ratios and cross-pair correlations — **never at win rates or P&L**. Choosing a
design on statistical power is legitimate; choosing one on returns is dredging.
That boundary is enforced by the tool not computing returns at all.

**2. The question changed from "is there an edge" to "is it profitable".**

This is the substantive correction. v1 was sized to detect a 3.5pp edge. But
with symmetric barriers at ±B and round-trip cost C, in the same volatility
units:

```
E[pnl] = (2w - 1) * B - C        break-even w = 0.5 + C/(2B)
```

At the measured C = 0.260 and B = 2.0, break-even is **56.5%** — so a 3.5pp
edge (53.5%) *loses money*. v1 was powered to deliver a statistically valid
confirmation of an unprofitable strategy.

Testing profitability requires a **larger** effect, and larger effects are
**easier** to detect. The economically meaningful question is also the
better-powered one.

---

## Power budget (computed before the hypothesis)

Measured round-trip spreads, as a fraction of price:

| metal | spread | | metal | spread |
|---|---|---|---|---|
| gold | 0.0151% | | platinum | 0.1343% |
| copper | 0.0316% | | palladium | 0.2367% |
| silver | 0.0600% | | | |

Nine of ten candidate pairs are affordable (cost/vol < 0.35). Only
palladium/platinum is excluded, at 0.592.

| | |
|---|---|
| pairs included | 9 |
| raw trades (hold 8, 20.4y) | 5,771 |
| mean \|correlation\| between pair residuals | 0.440 |
| **effective independent trades** | **1,277** (4.5× inflation discounted) |
| trades needed for 3 sd at B=3.0 | 914 |
| **margin** | **1.40×** |

At B = 3.0 the strategy must clear **54.3%** to break even — a 4.3pp edge.

---

## Hypothesis (fixed)

**H1.** A hedged cross-metal residual basket produces **mean P&L greater than
zero after measured transaction costs**.

**H0.** It does not.

Note this is deliberately *not* "the signal contains information". v1 already
suggested it does, weakly. Information that cannot pay a spread is not a
strategy.

---

## Configuration (frozen)

```
data        OANDA H4 mid, 2006-03 -> 2026-08 (~32,000 bars per instrument)
metals      XAG, XAU, XPT, XPD, XCU
pairs       all 9 affordable combinations; palladium/platinum EXCLUDED
            (cost/vol 0.592) — excluded on cost, before any return was seen
position    long 1 unit A / short beta units B, beta frozen at entry
beta_window 120 H4 bars
resid_window 30 H4 bars
z_window    120 H4 bars
entry       |resid_z| >= 2.0          (unchanged from v1 — not re-selected)
barriers    tp = sl = 3.0 spread-vol  (symmetric; break-even 54.3%)
max_hold    8 H4 bars (~1.3 days)
overlap     one trade per max_hold window, per pair
costs       MEASURED ask-bid per leg, as a fraction of price
pooling     ALL PAIRS POOLED INTO ONE STATISTIC
```

**Pooling is not optional.** Testing nine pairs and reporting the best is nine
chances to find noise. There is one number: mean P&L across the pooled basket.

**`entry_z` stays at 2.0** — carried over unchanged. It was not re-selected
after seeing v1's results, and changing it now would be exactly the retune the
v1 document forbade.

---

## Primary metric

Mean P&L per trade in spread-volatility units, after measured costs, pooled
across all 9 pairs, on non-overlapping trades.

## Success criteria (both required)

1. **Profitable.** Pooled mean P&L after costs > 0, with the lower bound of a
   1,000-sample bootstrap 95% CI also > 0.
2. **Not one pair or one episode.** No single pair contributes more than 35%
   of gross positive P&L, and no single calendar year more than 30%.

A directional null test (real vs reversed vs randomised side) is reported
alongside as diagnostic context, but **is not a success criterion**. v1
established that information exists; the question here is whether it pays.

## Stated power, so a null is interpretable

At B = 3.0 with 1,277 effective trades, this test has adequate power for the
4.3pp break-even effect (914 required, 1.40× margin).

**Therefore a null result is informative, not merely underpowered**, and will
be recorded as "the cross-metal residual is not profitable after retail
spreads" rather than "inconclusive". That is the whole point of doing the
budget first.

The shakiest input is the 0.440 mean correlation used to discount the sample.
If the true correlation is materially higher, effective n falls and the margin
erodes. The 1.40× margin is the buffer against that, and B = 2.5 was the
fallback had more been needed.

---

## Multiple-testing budget

**One run. One statistic.** No sweep over entry_z, barriers, windows, hold
length, or pair selection. The pair set is fixed above by a cost screen applied
before any return was computed.

If this fails, the line is abandoned. Not retuned, not re-cut by subperiod,
not rerun on a different hold.

---

## Anticipated failure modes

- **Correlation underestimated.** Pairs sharing a leg are more dependent than a
  simple mean |correlation| implies; effective n may be optimistic.
- **Spreads measured today, applied to 2006.** Retail spreads have generally
  tightened, so this is likely optimistic in the early sample. That biases
  *towards* H1, which is the dangerous direction — a marginal pass should be
  treated with suspicion for this reason alone.
- **Copper is not a precious metal.** It is in the basket because its spread is
  cheap and it is industrially linked to silver. If the result depends on
  copper pairs, that is a different (and less well-motivated) finding.
- **Palladium's 0.2367% spread** makes its pairs marginal even where they pass
  the 0.35 screen.
- **Close-to-close barriers.** Spread highs and lows are not observable from
  separate leg OHLC. This applies equally to all variants but means absolute
  P&L is approximate.

---

# RESULT (recorded 2026-08-09, immediately after running)

**H1 REJECTED. Criterion 1 failed; criterion 2 passed.**

| | |
|---|---|
| pooled trades | 5,769 |
| win rate | **48.57%** |
| break-even required | **54.3%** |
| mean P&L after costs | **−0.1818** spread-vol units |
| bootstrap 95% CI | **[−0.2359, −0.1227]** |
| top pair share | copper/palladium, 12.6% |
| top year share | 2011, 6.1% |

Per pair, every one of the nine is negative:

| pair | trades | win | mean P&L |
|---|---|---|---|
| silver/gold | 674 | 45.3% | −0.3501 |
| silver/copper | 627 | 46.7% | −0.2388 |
| silver/palladium | 650 | 48.5% | −0.1887 |
| silver/platinum | 630 | 48.6% | −0.2322 |
| gold/copper | 641 | 48.7% | −0.1027 |
| gold/palladium | 637 | 47.1% | −0.2290 |
| gold/platinum | 665 | 50.8% | −0.0909 |
| copper/palladium | 642 | 52.5% | −0.0271 |
| copper/platinum | 603 | 49.1% | −0.1731 |

## This is a decisive result, not a marginal one

The confidence interval does not approach zero. The shortfall is **5.7
percentage points** of win rate — not a tuning gap.

**Criterion 2 passing makes it stronger, not weaker.** No pair exceeds 12.6%
of gross positive P&L and no year exceeds 6.1%. The strategy is not
unprofitable because of one bad pair or one bad regime. It is uniformly
unprofitable across nine pairs and twenty years. A concentrated failure could
be argued with; this cannot.

The optimistic biases all ran towards H1 and it still failed: today's tighter
spreads applied to 2006, and close-to-close barriers that miss some intrabar
stop breaches.

## The signal is real. It just does not pay.

Diagnostic (not a criterion): real **48.57%** > random **46.77%** > reversed
**44.91%**, at **+2.69 sd**, with the ordering coherent.

So the residual does carry directional information, confirming v1's weaker
hint and the 15-minute hedged result. The edge is roughly **1.8pp** over a
randomised side. Break-even needs **4.3pp**.

**A real, statistically detectable, reproducible edge that is roughly a third
of the size required to pay retail spreads.** That is the finding.

## One coherent picture across the whole project

Direction flips with horizon, consistently:

| horizon | behaviour |
|---|---|
| minutes → ~1 day | mean-reverts (real > random > reversed here, and at 15m) |
| ~5 days | reverses — v1 found reversed beating real in both windows |

The residual reverts fast and trends slowly. Both effects are small. Neither
covers a spread.

## Per the pre-registration, the line ends here

No retune, no re-cut by subperiod, no different hold. The premise —
that a cross-metal residual is tradeable at retail spreads — is answered, and
the answer is no.

---

## What would end this line entirely

A null on criterion 1 with the stated power. At that point the cross-metal
residual does not pay retail spreads at any horizon or basket this project can
construct, and the premise — not the parameterisation — is wrong.
