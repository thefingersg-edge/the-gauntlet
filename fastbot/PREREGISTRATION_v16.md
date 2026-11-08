# PREREGISTRATION v16 — is the carry book dead or dormant?

```
WRITTEN:  2026-09-04, after RESULT_FXCARRY, and BEFORE any historical
          short-rate series has been joined to the measured markups
REVISED:  2026-09-04 (v16.1) -- the SAMPLE WINDOW is fixed in section 11
          after the coverage check, and still before any spread has been
          computed. No gate and no prediction changed.
STATUS:   FROZEN
SUBJECT:  whether the reachable cross-sectional carry spread has ever
          cleared 2.0 %/yr, and in what regime
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. A correction to RESULT_FXCARRY before anything else

RESULT_FXCARRY §4 said the book fails "because the USD is itself a
high-yielder and a roughly constant markup eats the thin long-side
differentials." **The first half of that is wrong as an explanation of
the spread, and the algebra says so.**

Each leg is held against USD:

```
long the top quintile      r_top    - r_USD   - s
short the bottom quintile  r_USD    - r_bottom - s
                           ------------------------
book                       r_top - r_bottom - 2s
```

**The USD cancels.** Where it sits in the distribution determines
whether the *long leg in isolation* is positive — which is what §4
actually observed — but it has no bearing on the spread. Checked
against the measured numbers:

```
mean(top quintile)   ZAR, HUF, AUD      +1.44 %/yr
mean(bottom)         JPY, CHF, THB      -3.78
gross dispersion                         5.22
total markup         ~1.94 + ~1.92      -3.86
                                        ------
predicted net                            1.36     measured +1.51
```

The residual is the difference between quintile-average rates and the
specific pairs supplying each leg. Close enough that the model is right.

**So the question is not "where is the USD." It is "how dispersed are
global short rates, relative to a fixed toll of ~3.9%/yr."** That is a
better question, it has a longer history, and it reverses what I told
Dave: rate dispersion *collapsed* in the ZIRP years, so the reachable
spread should have been **worse** then, not better.

## 2. What has to be true for the family to be alive

```
r_top - r_bottom  >=  2.0 % + 3.86 %  =  5.86 %/yr
```

Today's dispersion is **5.22%**, which is why the book pays +1.51% and
fails a 2.0% bar. **The family needs roughly 5.9 points of cross-country
short-rate dispersion to be worth trading here.** That is the whole
question, reduced to one number.

## 3. The measurement, frozen

> **For each month, across the currency universe of §4: rank by short
> rate, take the mean of the top quintile minus the mean of the bottom
> quintile, and subtract the markup measured in RESULT_FXCARRY.**

```
gross(t) = mean(top quintile rate at t) - mean(bottom quintile rate at t)
net(t)   = gross(t) - markup_long - markup_short
```

Quintiles by the same rule as v15 (`k = n // 5`, minimum 1), so the
construction is inherited rather than re-chosen.

**Markups are the ones measured on 2026-09-04**, per currency, from
`fx_carry_access.json` — not an average, so a high-markup currency
entering the top quintile carries its own toll.

## 4. The universe, and why it is the conservative choice

The **18 currencies with an implied rate derivable in the v15 run**:

```
ZAR HUF AUD NOK PLN GBP USD CZK NZD HKD EUR DKK SEK SGD CNH JPY CHF THB
```

**CAD, MXN and TRY are excluded**, because OANDA returned no financing
data for their USD pairs and their markup is therefore unmeasured.
Imputing one would be inventing the number the whole test turns on.

**This makes the test harder to pass, not easier**, and the direction
matters: MXN and TRY are two of the highest-yielding currencies in the
sample and would widen the top quintile in most historical periods.
**So a PASS here is a floor, and a FAIL is not conclusive for a book
that could reach them by crosses.** That limitation is stated now rather
than discovered afterwards.

## 5. The assumption this rests on, stated plainly

**Markup constancy.** The tolls are measured once, today, and applied
across the whole history. OANDA does not serve historical financing
rates, so there is no way to measure this and no way to pretend
otherwise.

It is not a safe assumption. Brokers can hide more markup when rates
are high, so today's tolls — measured in a high-rate regime — may be
*wider* than the ZIRP-era equivalents, which would make this test too
harsh on 2009-2021.

**Gate C exists entirely to handle this**, by refusing to return a
verdict that the assumption can flip.

## 6. The gates, frozen

**Gate A — has it ever been reachable.**

```
PASS   net(t) >= 2.0 %/yr in at least 25% of months
FAIL   otherwise
```

**Gate B — was it reachable for long enough to trade.**

```
PASS   at least one contiguous stretch of 24 months with net(t) >= 2.0%
FAIL   otherwise
```

Scattered months are not a strategy. A book that clears the bar one
month in four, never twice running, is a statistical artifact of the
ranking, not something anyone could hold.

**Gate C — does the verdict survive the assumption it rests on.**

```
PASS        Gates A and B give the SAME verdict at markup x0.5, x1.0 and x1.5
UNDETERMINED  otherwise -- and the answer is then a statement about the
              unmeasured markup, not about the market
```

This is the gate that matters. §5's assumption is unfalsifiable with
available data, so the only honest move is to require the conclusion to
be insensitive to it.

## 7. Predictions, registered before any rate series is joined

Rate dispersion was wide before 2008, collapsed when most of the
developed world went to zero, and has partly recovered since 2022.

| period | expected gross | expected verdict |
|---|---|---|
| 2003-2008 | 6-9% | **clears** |
| 2009-2015 | 5-6% | marginal, mostly fails |
| 2016-2021 | 4-5% | **fails** |
| 2022-2026 | 5-6% | marginal |

- **Gate A: I expect a PASS, at 25-40% of months**, concentrated before
  2008.
- **Gate B: I expect a PASS**, on a stretch somewhere in 2005-2008.
- **Gate C: this is the one I expect to fail.** A 3.86% toll against a
  5-6% gross means halving or doubling the markup moves the verdict in
  most of the sample. If so the honest answer is UNDETERMINED, and that
  is a real answer.

**If Gate A fails outright — if the spread has never cleared 2% in
twenty years — the family is closed permanently**, not dormant, and
that is worth more than any of the above.

## 8. Precondition

**Monthly short rates for at least 14 of the 18 currencies, spanning at
least 15 years, from a single sourced provider.** Central bank policy
rates or 3-month interbank rates, one convention applied throughout —
mixing conventions across currencies would manufacture dispersion out
of definitional differences, which is exactly the failure mode this
document is trying to avoid.

**If fewer than 14 can be sourced, this returns UNDETERMINED and
stops.** It does not proceed on a reduced universe, because dropping
currencies changes the quintiles and therefore changes the answer.

## 9. Kill conditions

- **A gross spread above 25%/yr** in any month → treated as a bad rate
  series (a hyperinflation currency, or a percent/decimal error) and
  investigated before it enters a mean.
- **Mixed rate conventions.** Checked per currency; a currency whose
  series is not the same measure as the rest is dropped and counted.
- **No lookahead is possible here** — this is a contemporaneous
  cross-section with no forward return — but for the same reason
  **nothing in this document is a backtest and no P&L may be computed
  from it.** It measures a toll against a dispersion. Turning it into a
  return series is a separate pre-registration.
- **One run.** No re-choosing quintile size, no re-choosing the 2.0%
  bar, no dropping a currency to widen the spread.

## 10. What each outcome means

| | |
|---|---|
| **A, B, C pass** | The family is dormant, not dead, and the condition is measurable monthly. Then the crash-risk question, which nothing has touched. |
| **A, B pass; C undetermined** | The answer depends entirely on a markup we cannot measure historically. Honest stopping point, and it names exactly what OANDA would have to publish to resolve it. |
| **A fails** | Twenty years without the spread clearing the toll. The family is closed at this broker permanently — and that is the most valuable outcome, because it stops it being reconsidered every time rates move. |

**Investigation thirty-two.**

---

## 11. Amendment (v16.1) — the sample window

```
Written 2026-09-04, after bis_rates.py returned coverage and BEFORE any
spread has been computed. No gate, no threshold and no prediction in
sections 6 or 7 is altered. Only the window the gates are scored over
is fixed, because the coverage check showed §3's construction is not
interpretable across the whole 81 years the download returned.
```

### 11.1 What the coverage check found

**Problem one — the quintile is degenerate before 1986.**

```
period       currencies      k = n // 5    the "quintile" is
1946-1985       5  - 9            1        ONE currency vs ONE
1986-1995       9  - 13         1-2
1996-2005      13  - 16         2-3
2006-2026      15  - 16           3
```

Before 1986 the measurement is not a cross-section at all — it is the
highest single rate minus the lowest single rate, drawn from five or six
developed economies. Worse, **the universe itself changes**: the
emerging-market currencies that supply most of the dispersion enter
between 1980 and 2000. Dispersion measured in 1960 and dispersion
measured in 2020 are not the same quantity, so a fraction-of-months
statistic computed across both is meaningless.

**Problem two — JPY's gaps are not random, and they lean one way.**

```
JPY missing 116 months:
  1999-03 .. 2000-07   17 months
  2001-04 .. 2006-02   59 months
  2013-05 .. 2016-08   40 months
```

BIS records no policy rate for Japan through those stretches, which are
**precisely the ZIRP and QE periods when the yen was the deepest funding
currency in the world.** The missingness is correlated with the very
quantity being measured.

Its direction is knowable in advance and is stated here rather than
discovered later: with JPY absent, the bottom quintile is built from the
next-lowest currencies, which are **higher**, so `r_bottom` rises and
**the measured spread is understated in exactly those months.** That
runs against the candidate, so it cannot manufacture a pass — but it is
large enough that a marginal FAIL in those stretches means less than it
appears to.

Nothing is imputed. Filling the gap with a zero would be reading a
missing value as a measurement, which is the error `fx_carry_access`
v1.0 made four days ago and `bis_rates` refuses by construction.
Substituting a Bank of Japan series would break §8's one-convention
rule, which exists for exactly this temptation.

### 11.2 The window, fixed

> **PRIMARY SAMPLE: 2000-08 to 2026-08 — the 313 months in which all
> sixteen currencies are present.**

A constant universe, so dispersion is comparable month to month, and
26 years against §8's 15-year floor.

> **SECONDARY, reported but NOT gated: 1986-03 onward**, where n ≥ 10
> and so k ≥ 2. Shown with the currency count per month, and read as a
> growing universe rather than a stable one.

> **EXCLUDED: before 1986-03**, where k = 1 and the construction is a
> pair, not a quintile.

**This is conservative and the direction should be said out loud.** The
1980s and 1990s carried far wider rate dispersion than anything since;
excluding them removes the era in which this family would have looked
best. A PASS on the primary sample is therefore a floor.

### 11.3 What this amendment is allowed to be

Legitimate only because **no spread has been computed.** The same change
made after seeing a result would be worthless, and §9's "one run" still
binds: the window is fixed here, once, and the measurement runs against
it once.

**A mandatory diagnostic**, so the §11.1 bias is visible rather than
argued about: the spread is reported separately for months where JPY is
present and months where it is absent. If those two differ materially,
the JPY gap is doing the work and the verdict is reported as resting on
it.
