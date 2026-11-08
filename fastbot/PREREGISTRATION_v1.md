# Pre-registration v1 — NAS100 M5 liquidity provision

```
WRITTEN:     2026-08-17
STATUS:      FROZEN BEFORE ANY BACKTEST WAS RUN
AUTHOR:      Claude, for Dave
SUPERSEDES:  nothing. First pre-registration in fastbot.
```

> **Nothing in this document may be changed after a result is seen.** If the
> design genuinely needs to change, that is a **v2 with a new date**, and v1's
> result is reported as a failure regardless. Changing a criterion after
> seeing the outcome is the same offence in either direction — silver15
> recorded v7's concentration gate as PASSED rather than retroactively
> tightening it, and that is the standard here.

---

## 1. The hypothesis, and why it should work without reference to a backtest

**A sharp 5-minute move against a thin book is partly an inventory shock, not
information. Whoever absorbs it is bearing inventory risk and is compensated
for it.**

That is a risk premium with a named bearer and a named risk, of the same
family as the crypto cash-and-carry basis that silver15 found to be real (it
was rejected there on *size*, at +1.46% against T-bills at 3.66% — not on
existence). It is not a pattern noticed in a chart.

Two things make it testable *here specifically*, and both come out of the
measurement work rather than from hope:

1. **The cost structure and the entry condition coincide.** cost/vol is
   `spread / (vol x sqrt(hold))`, so it is cheapest exactly when volatility is
   highest. This strategy only enters after a volatility spike. In 2022 —
   the highest-volatility year measured, 5.81bp/min — cost/vol at a 5-minute
   hold is **0.03**. No other family considered has its entry condition
   aligned with its cost this way.
2. **It is the one short-horizon effect with a mechanism.** `DESIGN_BRIEF.md`
   established that 0 of 14 price conditions and 0 of 25 indicators are
   sign-consistent across eras at intraday horizons. Every one of those was a
   *directional prediction*. This is not: it is payment for providing
   immediacy.

**Stated in advance — what would make this false.** If the sharp move is
information rather than inventory, price does not revert and the reversed-side
null (§6) will beat the primary. That is a real possibility, it is the
single most likely way this fails, and it is measured rather than argued.

## 2. Instrument, sample, and the split

```
INSTRUMENT     NAS100_USD (OANDA), M5 bid/ask
SESSION        09:00-16:00 America/New_York   (exchange-local, never UTC)
EXCLUDED       2005-2011  -- ask == bid, no spread in the feed
SECONDARY      2012-2013  -- reported separately, cost/vol 0.57-0.63 at 5m

FIT WINDOW     2014-01-01 -> 2020-12-31    7.0 years
HOLDOUT        2021-01-01 -> 2026-08-17    5.6 years   NOT TO BE OPENED
                                                        UNTIL §7 IS SATISFIED
```

Rationale for every boundary is in `HISTORY_AUDIT.md` and `REGIME_FINDINGS.md`
and was fixed before this document.

## 3. The signal, complete and minimal

On the close of each M5 bar `t` inside the session:

```
sigma_t = 1.4826 * median(|r - median(r)|)   over the previous N bars,
                                              consecutive and in-session only
z_t     = r_t / sigma_t                       r_t = log(mid_t / mid_{t-1})

ENTRY   z_t <= -k   ->  LONG      (absorb the down-shock)
        z_t >= +k   ->  SHORT     (absorb the up-shock)
EXIT    unconditionally at the open of bar t+1+H
```

### Parameters — three, all fixed a priori, none fitted on returns

| | value | chosen because |
|---|---|---|
| `N` | **24 bars** (2h) | long enough for a stable robust sd, short enough to stay intraday. Not tuned. |
| `k` | **3.0** | a 3-sigma bar. At ~84 session bars/day this fires ~1-2x/day given fat tails, which lands inside the round-trip budget of §4. |
| `H` | **6 bars** (30 min) | leaves room for 4 non-overlapping trades in a 7-hour session, and sits at cost/vol 0.02-0.07 in 2018+. |

**Every value is set by the cost budget and the sample-size requirement, not
by any return.** This is deliberate and it is the whole design: `pineport`
reached 49 parameters at non-round optimised values, and silver15 established
that 14 combinations at 2σ give a >50% chance of a spurious pass. Here the
count of return-fitted parameters is **zero**, so there is no multiple-testing
correction to apply.

Choosing parameters to satisfy a *cost* constraint is legitimate and is the
same principle as `screen_universe.py`, which ranks pairs on affordability and
sample and computes no returns at all.

### The spread gate — not a parameter

```
enter only if   spread_t / (sigma_t_per_min * sqrt(H*5))  <=  0.15
```

`0.15` is inherited from `screen_universe.py`, written for a different project
before this data existed. In 2014–2017 this gate will suppress most entries; in
2018+ it will rarely bind. That behaviour is predicted here, in advance.

### Execution model, pinned

```
signal on close of bar t  ->  enter at OPEN of bar t+1
long  enters at ASK, exits at BID          short is the mirror
exit  at OPEN of bar t+1+H
cost  the ACTUAL spread on the actual bar. Never a constant, never an average.
size  constant notional per trade
flat  by 16:00 local. No position is ever carried overnight, so financing
      is zero by construction and is not modelled.
no stop in the primary specification (see §5)
```

Constant notional is chosen so that the primary statistic measures the
*signal* and cannot be manufactured by sizing. `DESIGN_BRIEF.md` found that
volatility targeting was the one robust thing in the entire project — which is
precisely why it must be kept out of the primary test.

## 4. Hard constraints, from the budget

```
MAX ROUND TRIPS   4 per day        overlapping signals are IGNORED, not stacked
NON-OVERLAPPING   a new entry is refused while a position is open
```

If the realised trade rate exceeds 4/day the run is **invalid**, not
reinterpreted — the cost table in `REGIME_FINDINGS.md` was computed at that
rate and a higher rate changes the hurdle.

## 5. Declared secondary variants — reported, never primary

Declared now so they cannot be discovered later:

1. **Stop at 2× the entry bar's range.** Reported alongside. The primary
   result is the no-stop one whatever the comparison shows.
2. **Inverse-volatility position sizing.**
3. **H = 3 and H = 12** as a robustness sweep, reported as **PLATEAU or
   SPIKE** per `sweep.py`. Used to characterise, never to select. If `H=6`
   fails and `H=3` passes, the strategy has **failed**.

## 6. Null tests — all three run, all three reported

Per silver15: *real vs reversed vs randomised side.*

| null | what it kills |
|---|---|
| **randomised side** | same entry bars, coin-flip direction. Kills "the entry times are just high-vol moments". |
| **reversed side** | take momentum instead of reversion. If this wins, the shock is information and the hypothesis is simply wrong. |
| **random entry, matched exposure and time-of-day** | kills "any 30-minute in-session hold would have done this". |

1,000 draws each. The primary must exceed the **95th percentile** of all three.

### Look-ahead probe, run where the honest answer is zero

silver15's v7 leak probe was run on strongly trending data, where a planted
edge swamps a leak — 54× inflation on a driftless path, 1.1× on a trend. So:
the full pipeline is run on a **driftless synthetic series with no planted
edge**, and must return a net Sharpe indistinguishable from zero. Then on the
same series with a known edge planted, and must recover it. A probe that has
never been observed to fail has not been tested.

## 7. Pass and fail, stated before the run

### Gate A — the fit window, before the holdout is opened

```
PROCEED only if  gross Sharpe >= 0.94  on 2014-2020
                 AND >= 200 non-overlapping trades
                 AND realised round trips <= 4/day
```

0.94 is the §3 hurdle in `REGIME_FINDINGS.md`. **If Gate A fails, the project
stops. No retuning, no v2 with different N/k/H.** The holdout stays sealed and
is still available for a genuinely different hypothesis.

### Gate B — the holdout, opened exactly once

```
PASS requires ALL of:
  1. NET Sharpe >= 0.85 on 2021-2026            (= 2/sqrt(5.6), the 2-sigma bar)
  2. >= 200 non-overlapping trades
  3. beats all three nulls at the 95th percentile
  4. leave-one-year-out: removing the single best year does not flip the
     sign of net P&L                            (the silver15 v7 lesson --
                                                 2008 was 225% of that result
                                                 while passing a concentration
                                                 gate measured on gross)
  5. same fixed parameters give net Sharpe > 0 on BOTH SPX500_USD and
     US30_USD over the holdout
```

**Criterion 5 is weak evidence and is recorded as such now.** The three US
indices are highly correlated; passing on all three is much closer to one
observation than to three. It is included because failing it would be
informative, not because passing it proves anything.

### Anything else is a failure

Not "promising", not "worth another look with a different exit". A result
between the nulls and the bar is **inconclusive**, and inconclusive is
reported as a failure of this pre-registration.

## 8. What this test cannot see

Per the silver15 v6 lesson — *a budget bounds what a test can resolve; it
cannot tell you the effect is there* — written down before the run:

- **Quoted spread is a floor, not execution cost.** OANDA index CFDs are
  dealer-priced. Slippage, requotes and rejection on a 5-minute entry are
  unmeasured and only observable live. If the real cost is 2× quoted, the
  hurdle at 4 round trips/day rises from 0.94 to 1.32 and a marginal pass
  here would be a live loss.
- **Entering at the next bar's open assumes the open is fillable.** After a
  3-sigma bar it is the moment least likely to be.
- **12.6 years is 12.6 annual observations** for an annualised Sharpe. Sign
  consistency across three eras is three observations, not proof.
- **The test says nothing about 2005-2013**, which is a third of the feed.
- **A pass on three correlated US indices is close to a single observation.**

## 9. Order of work

```
1. build the engine; synthetic controls first, each gate PROVEN to fail
2. look-ahead probe on a driftless series -> must return zero
3. pull SPX500_USD and US30_USD M5, audit both     (~12 min)
4. Gate A on 2014-2020
5. STOP if Gate A fails
6. Gate B, once
7. write the result -- pass or fail -- before touching anything else
```

---

```
FROZEN 2026-08-17.  Signed off before any P&L was computed on this data.
```
