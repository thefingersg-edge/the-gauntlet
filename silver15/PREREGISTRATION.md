# Pre-registration: does the gold-implied silver residual work at multi-day horizons?

Written 2026-08-09, **before** any multi-day backtest has been run.

The point of writing this first is that the intraday version failed, and the
temptation now is to search until something passes. With ~2,000 independent
trades and a dozen tunable parameters, a search will find something. This
document fixes the specification and the pass mark in advance so that a pass
means something and a fail is accepted rather than retuned.

---

## Rationale (structural, not empirical)

FINDINGS.md established three things about the 15-minute version:

1. Hedged, on independent trades, the signal carries genuine directional
   information: +3.32 sd over a randomised-side null, with real/reversed
   separation consistently signed across every configuration tried.
2. Unhedged it carries none (+0.12 sd). The hedge is what reveals it.
3. It is untradeable anyway, because the round-trip cost is **1.39 spread-vol
   units against a 1.0 take-profit**. You pay more to enter and exit than the
   trade can make.

(3) is a statement about horizon, not about the signal. Cost is fixed per
round trip; the spread's volatility grows with holding time. So the same edge
becomes fundable at a longer horizon, if it survives there.

Measured on OANDA H4 data, 2006-03 → 2026-08 (31,583 bars):

| horizon | round-trip cost / per-bar spread-vol |
|---------|--------------------------------------|
| 15m (measured) | 1.39 |
| **H4 (measured)** | **0.329** (p25 0.219, p75 0.485) |

And the residual does travel far enough to reach a barrier:

| holding period | median abs. cumulative residual |
|----------------|-------------------------------|
| 24h (6 H4 bars) | 1.53 spread-vol |
| 48h (12 bars) | 2.22 spread-vol |
| **120h (30 bars)** | **3.67 spread-vol** |

With a 2.0 spread-vol barrier, cost is **16.4%** of the profit target rather
than 139%. That is the entire reason this test is worth running. It is not a
prediction that it will pass.

---

## Hypothesis (fixed)

**H1.** Over a 5-day horizon, the gold-implied silver residual mean-reverts,
and a hedged position sized to that residual produces positive expectancy
after measured transaction costs.

**H0.** It does not: the hedged multi-day signal is statistically
indistinguishable from a randomised-side null, or its edge does not survive
measured costs.

---

## Configuration (fixed now, nothing tuned later)

```
data          OANDA H4 mid, XAG_USD / XAU_USD / EUR_USD, 2006-03 -> 2026-08
position      long 1 silver / short beta gold  (beta frozen at entry)
beta_window   120 H4 bars  (~20 trading days)
resid_window  30 H4 bars   (5 days) — cumulative residual
z_window      120 H4 bars
entry         |resid_z| >= 2.0
barriers      tp = sl = 2.0 spread-vol   (symmetric: break-even is 50%)
max_hold      30 H4 bars (5 days)
overlap       one trade per max_hold window — independent draws, enforced
costs         MEASURED ask-bid, both legs (see "Data required")
```

**Deliberately removed from the intraday version, with reasons:**

- `sessions = [(7,16)]` — a session filter is meaningless on a 5-day hold.
- `er_max` regime gate, `vol_pct` band — these were chosen for the intraday
  strategy and never independently validated. Carrying them forward would
  import two unexamined free parameters into a test whose whole purpose is to
  have few. Removing them also increases the sample, which is the binding
  constraint at this horizon.

**Barrier choice justified in advance:** 2.0 spread-vol, because cost is 16.4%
of that target and the residual's median 5-day excursion (3.67) comfortably
exceeds it. Symmetric because asymmetric barriers require beating a 60%
win rate on geometry alone, and the measured edge is 3–4 percentage points.

---

## Data split — and an honesty note about contamination

The 2016–2026 period has already been examined extensively at M15. Anything
found there now is partly a memory of what I have already looked at.

- **Primary test: 2006-03 → 2015-12.** Genuinely unseen. This is the result
  that counts.
- **Secondary: 2016-01 → 2026-08.** Contaminated by prior inspection. Reported
  for consistency, but a pass here does not rescue a failure above.

Success is judged on the primary window. This ordering is fixed now precisely
because it would be tempting to reverse it afterwards.

---

## Primary metric

Mean P&L per trade in spread-vol units, after measured costs, on
non-overlapping trades — with a randomised-side null run alongside, as in
`hedged_test.py`.

---

## Success criteria (all four, fixed in advance)

On the **primary window (2006–2015)**:

1. **Signal is real.** Real signal beats the randomised-side null by
   **≥ 3.0 standard deviations** at zero cost, over ≥ 20 seeds.
2. **Direction is coherent.** Ordering is real > random > reversed. A signal
   that beats random but whose reversal also beats random is measuring
   volatility, not direction.
3. **It survives costs.** Mean P&L per trade after measured ask-bid costs is
   **> 0**, with the lower bound of a 1,000-sample bootstrap 95% CI also **> 0**.
4. **It is not one episode.** No single calendar year contributes more than
   **40%** of total P&L. Silver's 2011 spike is in this window and could carry
   the whole result on its own.

**If any criterion fails, H1 is rejected and the approach is abandoned — not
retuned.** Failing at 3 but passing 1 and 2 means "real but unfundable", which
is where the intraday version already sits, and is a stop.

---

## Multiple-testing budget

**Exactly one configuration.** The parameters above are fixed. No sweep over
`entry_z`, barrier size, windows, or timeframe.

If curiosity demands variants afterwards, they are exploratory, must be
labelled as such, and cannot be reported as confirming H1.

---

## Anticipated failure modes — read before interpreting any result

- **Sample starvation.** 5-day non-overlapping trades over 10 years may yield
  only 150–400 independent trades. The null-test standard deviation scales as
  1/√n, so a true 3pp edge may be undetectable. **A fail on criterion 1 with
  fewer than 200 trades is "underpowered", not "disproved"** — and the correct
  response is more history or a different instrument pair, not a looser
  threshold.
- **The 2011 spike.** Silver ran to $49 and collapsed inside the primary
  window. Criterion 4 exists for this.
- **Beta instability.** A 120-bar rolling beta over 20 days will move a lot in
  2008 and 2011. A hedge with the wrong beta is not a hedge.
- **Gold's spread is currently an assumption.** Every cost figure above uses
  0.25 $/oz for gold, which is a guess. It must be measured before the test
  runs, or criterion 3 is meaningless.
- **Regime change.** The 2006–2015 world had different rates, different
  liquidity, and no retail CFD flow at today's scale. Passing there does not
  guarantee 2026.

---

## Data required — what has to be run before this test

1. **Measure both legs' real spreads** (never assumed):

   ```
   python oanda_intraday.py --sides --instrument XAU_USD --start 2026-06-01
   python oanda_intraday.py --sides --instrument XAG_USD --start 2026-06-01
   ```

   This now fetches bid, ask AND mid, and reports ask−bid directly rather than
   doubling mid−bid. Feed the medians into `--gold-spread` / `--silver-spread`.
   If p75 differs materially from the median, use p75: a backtest priced at the
   median and executed at p75 is a different strategy.

2. **Pull H4 history back to 2006** into this project (pineport has its own
   copy; the two projects stay separate by design):

   ```
   python oanda_intraday.py --pull --price M --start 2006-03-01 \
       --granularity H4 --data-dir ../data_h4
   ```

   ~31,600 bars per instrument, about 7 requests each. Minutes, not hours.

3. Confirm provenance before running anything:

   ```
   python oanda_intraday.py --audit --data-dir ../data_h4
   ```

---

---

# RESULT (recorded 2026-08-09, immediately after running)

**H1 REJECTED on the primary window. All four criteria failed.**

| | primary 2006–2015 | secondary 2016–2026 |
|---|---|---|
| independent trades | 165 | 178 |
| real, zero cost | 47.27% | 43.82% |
| random | 49.50% (sd 3.40pp) | 49.51% (sd 3.93pp) |
| reversed | 52.73% | 56.18% |
| vs random | **−0.66 sd** | −1.45 sd |
| mean P&L after cost | −0.3153 | −0.4493 |
| bootstrap 95% CI | [−0.632, −0.012] | [−0.756, −0.168] |
| best year's share | 67.1% (2008) | 64.6% (2019) |

## The test was underpowered — and unpowerable

Both windows fell below the 200-trade minimum I set (165, 178), which under
the prereg makes this "underpowered, not disproved". But the power calculation
I should have run *before* writing this document shows something worse:

| edge to detect | trades needed at 3 sd | years of this design |
|---|---|---|
| 3.0pp | 1,907 | 116 |
| 3.5pp | 1,401 | 85 |
| 5.0pp | 687 | 42 |

This design yields **~16 independent trades per year** — one pair, 5-day
non-overlapping holds, |z| ≥ 2. OANDA's entire H4 history is 20 years.

**The test could never have passed on the available data.** Any configuration
that had shown a 3 sd result would have been noise. That is a defect in the
pre-registration, not in the strategy, and it is mine: I fixed thresholds and
a sample-size floor without checking they were mutually achievable.

## The one thing worth recording

Reversed beat real in **both** windows — 47.27/52.73 and 43.82/56.18. Neither
is individually significant (1.6 and 1.7 sd), but two independent periods
agreeing on sign is weak evidence that the multi-day residual **trends rather
than reverts** — the opposite of this project's premise.

Inverting the signal and retrading it is precisely the retune this document
forbids. It is a hypothesis for a *new* pre-registration with an achievable
power budget, not a result.

## Consequences for any future test

Any successor must state its power budget first and be abandoned before
running if the required sample is unobtainable. Concretely, that means:

- **more independent observations per year**, not more parameters — a basket
  of pairs (XAG/XAU, XPT/XAU, XAG/XPT) rather than one, or shorter holds;
- or **accepting a larger detectable edge** (a 5pp edge still needs 42 years
  on this design, so this alone is not enough);
- or **abandoning the null-test framework** for this question, and accepting
  that the answer cannot be established with retail data.

---

## What would make me abandon this line entirely

If the multi-day hedged test fails criterion 1 with an adequate sample
(≥ 200 independent trades), then the gold-implied residual does not carry
tradeable directional information at any horizon this project can test, and
the premise is wrong rather than the parameters.
