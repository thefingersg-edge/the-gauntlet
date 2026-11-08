# Forward test — registration. Numbers locked.

```
REGISTERED:   2026-11-06, after the gate run, before any forward data is used.
SEAL DATE:    2026-11-01 (run 1 generation)
WINDOW:       2026-11-01 to 2027-11-01, FIXED. Not extended if unsettled,
              not cut short if decisive.
TRACKED:      all six arms, regardless of gate result — a rule fixed before
              the results, so there is no selection effect.
MODE:         paper only. No capital at risk. Stated on screen.
```

## The free three months nobody has looked at

Our daily files end **2026-08-07**. It is now 2026-11-06. **Three months of
real history already exists that no gate run has seen and that ARM F was
never fitted on.**

That is a legitimate holdout for every arm as specified — no arm was tuned
on it — and it is available now for the cost of refreshing the data files.
It is not a substitute for the twelve-month window; it is an early read
with an honest caveat: it falls inside the generating models' likely
training horizon, so it is unseen by *our* fitting but not necessarily by
theirs.

**Action: refresh the 21 daily files to current and re-run the gates on
2026-08-07 -> today as a sealed segment.** Do this before the forward
window is discussed on screen, so the result is registered rather than
discovered.

## The backtest figures these predictions are measured against

Locked from `gates/RESULTS_ALL.md`. Any forward figure is compared to
these and to nothing else.

| Arm | Backtest CAGR | Backtest daily max DD | Net per trade |
|---|---|---|---|
| F part A | 8.4% | 10.2% | +0.513% |
| F full | 8.3% | 20.7% | +0.042% |
| D | 2.5% | 30.1% | +0.050% |
| E | 1.9% | 35.1% | −0.051% |
| A | 4.0% | 65.9% | −0.078% |
| B | 1.3% | 46.3% | −0.053% |
| C | not sized — see note | — | −0.016% |

ARM C needs a sized equity curve at its own 1%-risk rule before the window
opens. Until that exists its forward test is per-trade only.

## The two predictions, registered

```
PREDICTION 1 — we expect this to HOLD
  Forward realised volatility lands within 50% of backtest volatility.
  Forward maximum drawdown is no worse than 2x the backtest figure above.

PREDICTION 2 — we expect this to FAIL
  Forward return is positive AND within 50% of the backtest CAGR above.
```

This is Wiecki's central result stated as a falsifiable claim on our own
cohort: **risk carries over, return does not.** Annual volatility R2 0.67
and maximum drawdown R2 0.34, against annual returns R2 0.015 and negative.

If prediction 1 fails — if realised volatility is nothing like the
backtest — that is evidence our implementation is wrong, not that the
market changed, and we say so.

## The specific prediction for ARM F, which is the interesting one

ARM F produced the only arm that cleared five of seven, and the only one
with a round-by-round record of its own search:

```
  round 1   ~160 configs   IS Sharpe 0.82   OOS 0.61
  round 2   ~220 configs   IS Sharpe 1.08   OOS 0.60
  round 3   ~280 configs   IS Sharpe 1.23   OOS 0.67
```

> **Registered: ARM F's forward Sharpe over the twelve-month window lands
> below 0.67, and closer to round 1's 0.61 than to round 3's 1.23.**

If it lands above 1.0, the whole backtest-overfitting thesis is wrong for
this strategy and the episode says so.

## Decision rule, fixed now

```
BROKEN        forward return <= 0, or realised drawdown exceeds 2x backtest
SURVIVED      forward return positive AND at least half the backtest CAGR,
              with drawdown inside 2x
INCONCLUSIVE  anything else — including positive but much degraded, which
              is what most real forward tests actually produce
```

INCONCLUSIVE is reported as inconclusive, not spun as failure.

## Publication cadence

A monthly tracker, published whether or not anything happened. Partly
channel cadence, partly a commitment device: a public monthly number is
very hard to quietly drop if it starts going the wrong way for our thesis.

## The framing, corrected and kept

We expect all six to degrade, and the degradation to be in return rather
than risk. We have written down what would prove us wrong. **If a strategy
clears the forward window with its edge intact, that is the episode we
publish.**
