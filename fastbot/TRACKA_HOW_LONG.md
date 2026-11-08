# How long does Track A need to run?

```
ASKED:    2026-08-29, after four observations
ANSWER:   ~28 days for the observation that matters most (25 September),
          ~5 to 9 weeks for the one that can actually be decided.
          Beyond that the binding constraint is not patience — it is that
          the rule transacts on 4 days a year and nothing changes that.
```

---

## 1. First, what is actually being measured

Not the premium. v8 §1 settled that: a forward significance test on the
basis needs **4.3 years** to reach 2σ on something already measured over 18
cycles. Running one would be waste.

Track A measures **entry cost**, which after the collateral costs came in
small is the largest unpriced term left in the candidate.

## 2. Why one bad roll matters so much

Era 3 measured **+2.56** against a **+2.0** bar. Headroom: **0.56 points.**

| wide rolls per year (of 4) | roll cost | |
|---|---|---|
| 0 | 0.08 pts | within margin |
| **1** | **0.85 pts** | **exceeds the entire margin** |
| 2 | 1.62 pts | |
| 4 | 3.17 pts | |

**One wide roll out of four eats the whole headroom.** So the question is not
"what is the average spread" — it is "how often is a roll date a wide day",
and that is a tail-frequency question, not a mean.

## 3. What four observations can and cannot say

September spreads so far: **1.00, 158.38, 3.78, 13.62 bp.** One of four
over 100bp.

| observations | 95% interval on the wide-day rate |
|---|---|
| **1 of 4 (today)** | **4.6% – 69.9%** |
| 3 of 20 | 5.2% – 36.0% |
| 5 of 40 | 5.5% – 26.1% |
| 12 of 100 | 7.0% – 19.8% |

At n=4 the interval spans almost the entire range. It is consistent with
wide days being a once-a-month curiosity and with them being a third of all
days. **Four observations have not narrowed anything.**

## 4. The three horizons

**28 days — to 25 September.** The first actual quarterly roll date, and the
only day of the year the rule transacts this quarter. One observation of the
thing that matters most, plus ~28 daily spreads. Roll-date observations to
date: **zero.**

**~32 days — to early October.** Enough daily data to test the observed rate
against a 10% null at conventional power. This is the point where "wide days
are rare" becomes a claim you can make or reject.

**~62 days — to late October.** Enough to separate a 10% world from a 30%
world at 80% power. This is the properly powered version of the same
question.

**One year.** Four roll dates. The only way to observe roll-day spread
directly rather than inferring it from all days.

## 5. The honest ceiling

Daily observation bounds the roll-day risk; it does not measure it. If wide
days are a fraction *p* of all days and roll dates are unremarkable draws:

| p | chance of ≥1 wide roll per year | expected roll cost |
|---|---|---|
| 5% | 18.5% | 0.23 pts |
| 10% | 34.4% | 0.38 pts |
| 20% | 59.0% | 0.69 pts |
| 33% | 79.8% | 1.10 pts |

**Only the top two rows are survivable** against 0.56 points of headroom, and
even at p=5% there is roughly a one-in-five chance in any given year of a
roll that costs more than the entire margin.

That assumes roll dates are ordinary days. They may not be — quarterly
settlement could bring more depth, or less. **Nothing in the daily series
answers that**, and only the four-a-year sample does.

## 6. So: how long

**Run it to late October.** That is ~60 daily observations plus the 25
September roll, and it is the point at which the data stops changing what
you would conclude. Before then the interval is too wide to act on; after
then daily observations add very little, because the residual uncertainty is
about roll dates specifically and those arrive four times a year regardless.

It costs one API call a day and the cron is already running, so there is no
reason to stop it in late October either — just no reason to *wait* past it.

## 7. What would shorten it

Three things, in descending order of value:

1. **Kraken publishes historical order-book or trade data.** If depth
   history for `FF_XBTUSD` quarterlies is retrievable, the wide-day rate is
   measurable retrospectively over years instead of prospectively over
   weeks. This is worth checking before waiting two months.
2. **Intraday sampling.** The cron fires once a day; the 158bp reading may
   have been a minutes-long gap. Sampling hourly turns 60 observations into
   1,400 and characterises whether wide *days* are really wide *moments*.
   That distinction decides whether the rule can simply not cross at that
   instant.
3. **Accepting a limit order instead of crossing.** The rule as frozen
   crosses the spread. Posting at the mid and waiting removes the cost
   entirely at the price of execution uncertainty — but that is a change to
   the rule, and it belongs in v9 rather than in a running protocol.
