# Result v3 — REJECTED at Gate 1, and the escape hatch does not apply

```
RUN:      2026-08-17
SPEC:     PREREGISTRATION_v3.md, unmodified
DATA:     SPX500_USD + US30_USD, 2014-2020, never previously examined
VERDICT:  FAIL. And -- see section 3 -- the pre-declared M1 response is
          DECLINED, because its precondition turned out to be false.
```

---

## 1. The result

```
POOLED   low-q n=921   high-q n=919
         difference +0.04bp per trade    t +0.04
```

| criterion | required | actual | |
|---|---|---|---|
| pooled t | ≥ 2.0 | **+0.04** | ✗ |
| difference positive | yes | +0.04bp | ✓ |
| sign agrees on both instruments | yes | SPX +0.20, US30 −0.12 | ✗ |
| ≥200 trades per half | yes | 921 / 919 | ✓ |
| ≥5 of 7 years agree | yes | 4 of 7 | ✗ |

A t of 0.04 on 1,840 trades is not a near miss. Both instruments are
independently flat and they disagree on sign.

## 2. The diagnostic — this is NOT a resolution failure

`q` split at **1.00** on both instruments, which is what a splitter with no
signal looks like. So before reading the null as evidence:

```
SPX500   q at shock bars:  p5 0.996  p25 0.999  p50 1.001  p75 1.002  p95 1.007
US30     q at shock bars:  p5 0.989  p25 0.999  p50 1.001  p75 1.005  p95 1.503

spread on 3-sigma bars vs quiet bars:   SPX 2.024 / 2.043 = 0.991
                                        US30 0.976 / 1.011 = 0.965

distinct in-session spread values:      SPX 30,732     US30 70,984
bar-to-bar spread CV:                   SPX 0.308      US30 0.388
```

Read those together, because separately they mislead.

**The feed has plenty of spread resolution.** 30,000–71,000 distinct values,
and a bar-to-bar coefficient of variation of 0.31–0.39. The spread moves, a
lot, and it is finely measured. The instrument was not too blunt.

**But it does not move in response to shocks.** On a 3-sigma bar the spread is
0.991× and 0.965× its quiet-bar level — unchanged, or if anything a shade
*narrower*. And 90% of shock bars sit within ±1% of the trailing median.

So the spread's large variation is **slow** — the intraday schedule already
visible in `REGIME_FINDINGS.md`, wide at the open and close, tight midday. A
20-bar trailing median tracks that slow component almost perfectly, `q`
divides it out by construction, and **there is nothing fast left underneath.**

## 3. Declining the pre-declared M1 response

`PREREGISTRATION_v3` §8 said, before the run:

> The measurement is coarse and a null could be a resolution failure rather
> than an absent effect. **M1 data is available and would resolve this** —
> that is the pre-declared response to a null on Gate 1.

**That response is now declined, because its precondition is false.** It was
written for the case where the measurement was too coarse to see a real
reaction. The diagnostic shows the measurement is fine and the reaction is
absent — 0.991 and 0.965 against a hypothesis that predicts a ratio well
above 1.

Pulling M1 would be ~50 minutes and ~700MB spent looking for a sub-5-minute
version of a response that leaves no trace at all at five minutes, in a
sample of 1,840 shocks, on a snapshot measure that would still miss a
transient. That is chasing an escape hatch because it exists, not because the
evidence points through it.

> Worth stating plainly: a pre-declared fallback is permission to do
> something, not an obligation. Using one whose stated condition was not met
> is the same offence as skipping a gate that was — it just feels like rigour
> instead of laziness.

**If the sub-5-minute question is ever worth reopening it needs tick data, not
M1** — and that is a different project on a different venue.

## 4. What this actually establishes, which is bigger than v3

**OANDA's index CFD spread is a schedule, not a response.**

It varies substantially and predictably by time of day, and it does not react
to individual price events. That is consistent with a retail CFD book quoting
from a rule set and internalising flow, hedging in aggregate rather than
repricing against each print — economically sensible, and not what a
venue-level order book does.

The consequence reaches past this hypothesis:

> **Every "read the dealer's quote" signal is closed on this venue**, not just
> the informed-versus-inventory split. Quote skew was already closed by
> construction (mid is exactly `(bid+ask)/2`, verified to 9e-13). Quote
> *reaction* is now closed by measurement. There is no third channel: bid,
> ask and their timing is the entire surface OANDA exposes.

That is a budget-style closure — it removes a whole family from consideration
in one test rather than one hypothesis at a time, which is what silver15's
`power_budget.py` was built to do. Anything in this direction needs an
exchange feed with real depth, which is a different data problem and a
different cost structure.

## 5. What survives

- **The NAS100 holdout is still sealed.** 2021-2026, never examined. Three
  hypotheses have now been tested without spending it.
- **SPX500 and US30 2021-2026 are also still unexamined** — v3 used only
  2014-2020 on them.
- **The v3 machinery is reusable.** `spread_split.py` splits any trade
  population on any pre-declared conditioning variable and reports the
  difference with the right standard error. The conditioning variable is the
  only thing that was wrong.
- **The controls caught a sign-inverting fixture bug before the run.** The
  first synthetic loaded every unplanted shock into the low-`q` arm and
  reported t = −2.97 on a planted +11bp effect. Had that reached real data it
  would have produced a confident, significant, backwards conclusion that
  read as a discovery.

## 6. Scoreboard

**Fourteen hypotheses tested across silver15, pineport and fastbot. Fourteen
rejected.**

v3 is the first to be rejected on a *measurement* rather than on an effect
size — the mechanism could not be observed on this venue at all. That is a
different and more useful kind of no: it closes a family rather than a
candidate, and it took one test on data that had never been touched.
