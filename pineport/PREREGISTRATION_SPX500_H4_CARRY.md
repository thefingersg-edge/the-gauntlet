# Pre-registration — what does financing cost the SPX500 H4 strategy?

**Registered:** 2026-10-10, before any financing figure is computed.
**Subject:** the **cost of carry** on the trained SPX500 H4 config from
`PREREGISTRATION_SPX500_timeframes.md` — a charge that registration never
priced. Not a retest of the strategy and not an appeal against its verdict.

---

## 1. Why this is a new question, not a reopening

The H4 arm is **closed**: it failed conditions 1 and 4 (2005-2008 Sharpe 0.53
against a 0.8 bar; 0.36 at 1.00/fill). Standing rule 2 forbids reopening a
closed family with a fourth parameter, and §6 of that registration forbids
selecting its post-2023 window, relaxing the Sharpe bar, or adding a filter.

**None of that is done here.** The config is frozen exactly as trained — no
parameter is searched, fitted, or varied. The question is about a charge that
was omitted from the accounting:

> The timeframes registration priced the **spread** (0.25/fill, measured) and
> found H4's break-even spread at 2.5-3.0 points — a 10x margin. It never priced
> **financing**. What does carry cost, and does any of H4's return survive it?

A cost that was never charged is not a parameter. Adding it can only make the
result worse, which is why this cannot function as a rescue: there is no
outcome of this test that turns H4's failure into a pass. It can only move H4
from "failed on risk-adjusted return" to "failed on risk-adjusted return and
was never economic in the first place" — a materially different and more useful
closing statement.

**This follows standing rule 6** (costs are the usual killer; price the vehicle
early) and the programme's central finding that every measured premium "died on
access". Gold 15m is the precedent: Sharpe 0.86 became **2.93%/yr net** after
ETF costs, and on a CFD at rf+2.5% it was **worse than cash**, with break-even
carry 4.35%.

---

## 2. Why it is likely to matter here — the arithmetic, stated before running

Measured on the frozen config, 2026-10-10:

| window | exposure | time-weighted financed notional | median hold | return |
|---|---|---|---|---|
| 2005-2008 | 50.9% | **0.138x equity** | 21 bars (3.5 d) | **+1.32%/yr** |
| 2023-2026 | 51.5% | **0.614x equity** | 32 bars (5.3 d) | +14.53%/yr |

Carry per year ≈ *financed notional* x *all-in financing rate*. So a 6.5%
all-in rate costs the pre window ≈ 0.138 x 6.5% = **0.90%/yr against a
+1.32%/yr return** — about two thirds of it. The same rate costs the post
window ≈ 0.614 x 7.3% ≈ 4.5%/yr against +14.53%/yr, which it survives.

The windows differ by more than 4x in financed notional because position size
is equity-based and equity grew, so carry is **not** a uniform haircut. The
pre window is where this bites, and the pre window is the one that already
failed.

---

## 3. What is measured

For each holdout window, the strategy's net return and Sharpe **after a daily
financing charge on open positions**, computed as:

    long:   charge_t = notional_t x (benchmark_t + markup) x (days_t / 365)
    short:  credit_t = notional_t x (benchmark_t - markup) x (days_t / 365)

- `notional_t` — position size x price, marked daily while a position is open.
- `benchmark_t` — the actual short rate of the day, lagged one business day at
  use, per the lookahead note in `fetch_fred.py`.

  **Amendment, 2026-10-10, before any figure was computed.** This section first
  specified **DFF** (effective fed funds). FRED is unreachable from the
  environment this runs in (`fetch_fred.py` returns `403 Forbidden` through the
  proxy), so the benchmark is **`fastbot/data/DGS3MO.csv`** — the 3-month
  Treasury yield, already in the tree, daily, spanning 2004-12-01 to 2026-08-17,
  which covers both holdout windows. `fastbot/data/policy_rates.csv` (USD
  monthly policy rate) is computed alongside as a cross-check, and **if the two
  benchmarks disagree on any kill condition, the test is reported as
  inconclusive on that condition** rather than resolved by choosing one.

  Limitation, stated now: the 3-month bill is not an overnight rate. It carries
  a small term premium over effective fed funds — normally within ~25bp, wider
  when the curve is steep or policy is turning, as in 2007-2008. That biases the
  benchmark *upward* in the pre window, so it makes carry look slightly more
  expensive than it was. The direction is against the strategy, which is the
  conservative direction for a cost test, but it is a real limitation and the
  break-even markup must be read with it in mind.
- `markup` — the broker's spread over benchmark. **Swept, not assumed**, at
  1.0 / 2.5 / 4.0 / 6.0 percentage points.

  **Looked up, 2026-10-10, before running.** OANDA publishes an admin fee of
  **2.5%** on index CFDs: long positions are debited the reference rate **plus**
  2.5%, short positions credited the reference rate **minus** 2.5%, with
  position value taken at the 5pm ET price and a **/365** basis. The reference
  rate for SPX500 is SOFR. So the gold work's 2.5% was not an inherited
  assumption — it is the published figure, and 2.5% is the headline arm of the
  sweep. The other three arms remain, because the fee is account- and
  region-specific (OANDA's Canada, Australia, US and BVI entities publish
  different terms) and OANDA states funding rates may change daily.

  A third-party aggregator (BrokerChooser, collected 2026-02-27) lists the
  SPX500 long financing rate as −6.4%/yr. That is **not used**: a negative rate
  cannot be reconciled with a positive SOFR plus a positive 2.5% markup, so it
  is either a sign convention or an error. Noted so the discrepancy is on the
  record rather than silently discarded.

- **Shorts are credited, not charged** (amended 2026-10-10, before running; the
  first draft charged them symmetrically as a conservative simplification).
  Doing it properly is no harder and avoids overstating the cost. With a
  benchmark near 4% and a 2.5% markup a short *receives* ~1.5%/yr. Shorts are
  only 1.7-2.0% of exposure, so this cannot change a verdict either way.

- **Weekends accrue.** Charging per *calendar* day held automatically carries
  Saturday and Sunday, which matches the broker convention of charging three
  days on Friday. No separate Friday rule is needed.

**Primary output: the break-even markup** — the markup at which each window's
net return reaches zero — compared against what the broker actually charges.

---

## 4. Kill conditions, fixed before computing

The strategy is **not economic on this vehicle** if any of:

1. **Break-even markup below 2.5 points on either holdout window.** 2.5 is the
   figure the gold work used for an OANDA CFD; a strategy that cannot pay it is
   not tradeable there.
2. **The 2005-2008 window goes negative at a 2.5-point markup.**
3. **Post-carry return below 2.0%/yr on either window** — below that it is not
   distinguishable from cash, which is the gold 15m outcome restated.

It is **economic on carry** (which is NOT a pass of the closed registration —
see §6) only if all three clear on both windows.

---

## 5. Predictions, recorded before computing

1. **The 2005-2008 window fails conditions 1, 2 and 3.** Its +1.32%/yr against
   0.138x financed notional implies a break-even all-in rate near 9.6%, and
   2005-2008 fed funds ran 2.3-5.3%, so a markup above roughly 4-7 points would
   sink it. The margin is thin enough that condition 3 (the 2.0%/yr floor)
   fires even where condition 1 does not.
2. **The 2023-2026 window passes all three.** +14.53%/yr against 0.614x
   notional leaves room for a markup well past 6 points.
3. **So the two windows disagree, and the honest reading is the pre window.**
   Carry does not rescue or condemn uniformly; it concentrates the damage in
   the window that already failed, for the same underlying reason — there is
   very little return there to charge against.
4. **Carry is a larger charge than spread in the pre window.** Spread cost at
   0.25/fill over 59 trades is small; carry over 4 years at 50.9% exposure is
   not. If so, the registration's 10x spread margin was measuring the wrong
   cost, and that is the finding worth carrying forward.

---

## 6. What this cannot do

- It **cannot** return H4 to live consideration. The timeframes registration's
  verdict stands on its own conditions whatever happens here.
- It **cannot** be used to argue the post-2023 window is the real result.
  Reporting both windows is required; selecting the favourable one is what §6
  of the parent registration forbids.
- No parameter of the strategy may be changed, re-searched or re-fitted. If a
  markup makes it unprofitable, the response is to record that, not to retune
  stops to hold for fewer days.
- The markup sweep is **not** an outcome to select from. The break-even figure
  is the result; the broker's actual charge is the comparison.

---

## 7. Deliverable

`FINDINGS_SPX500_H4_CARRY.md`: the break-even markup per window, the post-carry
return and Sharpe at each swept markup, the broker's actual published rate, and
the three kill conditions applied. Reported whatever it shows, including if
carry turns out to be immaterial — a null here is worth recording, because it
would mean the spread-only accounting used throughout this tree is adequate for
holds of a few days, which nothing has yet established.

Implementation goes in `carry_cost.py`, reusable: every strategy in this tree
that holds overnight has the same unpriced charge.

*Not financial advice. Measurement, not recommendation.*
