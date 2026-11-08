# RESULT — is the carry book dead or dormant?

```
RUN:      2026-09-04
SPEC:     PREREGISTRATION_v16 / v16.1, frozen before any spread existed
CODE:     bis_rates.py 1.0, carry_dispersion.py 1.1
VERDICT:  UNDETERMINED -- Gate C failed, as registered
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The verdict

```
[PASS] Gate A  63.3% of months clear 2.0 %/yr (need 25%)
[PASS] Gate B  longest contiguous run 148 months (need 24)
[FAIL] Gate C  NOT stable across markup x0.5 / x1.0 / x1.5

    UNDETERMINED
```

```
scale      clears   fraction   longest run   median net
x0.5          292      93.3%           235       +3.97
x1.0          198      63.3%           148       +2.59   <- as measured
x1.5           76      24.3%            21       +1.08
```

**The family is dormant rather than dead — but only if the markup was
what it is today, and that is exactly what cannot be measured.** At one
and a half times today's toll, nothing clears and Gate B collapses from
148 months to 21. v16 §6 wrote that outcome down in advance: the answer
is then "a statement about the unmeasured markup, not about the market."

## 2. The regime pattern, which is clean

```
period      n   median gross   median net   clears
2000-2002   29        10.12        +5.58    100.0%
2003-2008   72         6.75        +3.34    100.0%
2009-2015   84         5.12        +2.36     71.4%
2016-2021   72         4.05        +1.48     11.1%
2022-2026   56         5.67        +2.01     51.8%
```

Cross-country rate dispersion collapsed as the developed world went to
zero and has partly recovered since 2022. Against a **fixed 3.86%/yr
toll**, that translates into a book that was comfortable until 2008,
workable to 2015, dead through the ZIRP years, and marginal now.

**Today's reading is +1.36 computed, +1.51 measured — below the bar.**
So the current regime is at the weak end of "marginal", which is
consistent with RESULT_FXCARRY failing Gate D last week.

## 3. Two errors of mine

**v16.1 §11.2 said the primary window is "the 313 months in which all
sixteen currencies are present." That is false.**

```
k=3   n=15 rankable   213 months
k=2   n=14 rankable    99 months   JPY absent
k=1   n= 9 rankable     1 month    2026-08
```

2000-08 is when all sixteen are first *simultaneously* present — not
when they stay so. JPY drops out again for 99 of the 313 months, and the
final month is short six series that had not yet updated (AUD, GBP, HUF,
NZD, THB, ZAR all end 2026-07). I fixed the coverage cliff at the start
of the sample and asserted a constancy at the end that the data does not
support.

**v16.1 §11.1 predicted the wrong sign on the JPY bias.**

I registered that with JPY absent the bottom quintile would be built
from higher currencies, so the spread would be **understated**. Measured:

```
JPY present   n=214   median net +2.27   clears 55.1%
JPY absent    n= 99   median net +3.16   clears 80.8%
```

**Overstated, not understated.** The reason is one I had already written
down in `carry_dispersion.py`'s own self-test — *"14 gives k=2, so
losing JPY changes the CONSTRUCTION"* — and then failed to carry into
the prediction. Losing a currency shrinks the quintile from three to
two, and a smaller quintile is more extreme, which widens the gross by
more than losing the lowest member narrows it.

Holding the era fixed shows it is the construction and not the market:

```
2001-2006   k=2  n=59  gross 8.88   k=3  n=13  gross 6.17
2013-2016   k=2  n=40  gross 4.95   k=3  n= 8  gross 4.23
```

**Gate A survives it.** Restricted to the 213 k=3 months alone the
figure is **55.4%**, still far above the 25% threshold. So the artifact
inflates the headline without changing the verdict — but it is one third
of the sample and it is reported rather than absorbed.

## 4. Predictions

| | predicted | measured | |
|---|---|---|---|
| gross 2003-2008 | 6-9% | 6.75 | **held** |
| gross 2009-2015 | 5-6% | 5.12 | **held** |
| gross 2016-2021 | 4-5% | 4.05 | **held** |
| gross 2022-2026 | 5-6% | 5.67 | **held** |
| verdict 2009-2015 | mostly fails | 71.4% clears | **missed** |
| Gate A | pass, 25-40% | pass, **63.3%** | direction held, size badly under |
| Gate B | pass, a 2005-08 stretch | pass, **148 months** | held, far longer |
| **Gate C** | **fail** | **fail** | **held** |
| JPY bias direction | understated | **overstated** | **missed** |

Four for four on gross dispersion, which is the quantity the whole test
turns on. Two clear misses, both on things I reasoned about rather than
measured.

## 5. What UNDETERMINED means here, precisely

It does **not** mean "we don't know anything." It means one specific
thing is unknown and it happens to be decisive:

- the **dispersion** is measured, from a single provider on one
  convention, over 313 months;
- the **toll** is measured, once, on 2026-09-04, in a high-rate regime;
- **whether that toll was the same in 2010 is unknowable from anything
  OANDA publishes**, and the verdict flips inside a plausible range.

There is a reason to think today's toll is the *wide* end: brokers have
more room to mark up when rates are high. If so, the ZIRP-era net was
better than computed and the true history looks more like the ×0.5 row.
But that is an argument, not a measurement, and this document does not
get to use it.

## 6. What would actually resolve it

**Record the toll monthly from here.** `fx_carry_access.py` already
measures `s` per currency in one API call. Logging it on a cron — the
way `basis_monitor.py` already logs the Kraken basis — turns Gate C's
assumption into a measurement within a year or two: if rates move and
`s` holds at ~1.0%/yr on majors, markup constancy is supported and the
×1.0 row is the right one. If `s` scales with the rate level, it is not,
and the whole historical reconstruction is void.

That is cheap, it starts paying immediately, and it is the only path
from UNDETERMINED to an answer that does not depend on OANDA publishing
something they do not publish.

## 7. What this still does not touch

**Crash risk**, which is the entire reason the premium exists. Nothing
in v15 or v16 measures it, and a book that clears 2%/yr in financing can
lose several years of that in a week — the 2024 yen unwind being the
canonical case. A PASS on dispersion is permission to ask the question,
not an answer to it.

**Any return series.** v16 §9 forbade one and none was computed. This
measures a toll against a dispersion.

**The excluded currencies.** MXN and TRY are two of the highest-yielding
currencies OANDA quotes and both are absent — TRY has no usable USD pair
and CNH is offshore. Their absence narrows the top quintile, so the
measured dispersion is a **floor**.

## 8. Where it leaves the family

```
is the premium real?          yes, documented, not in dispute
does OANDA pass it through?   71.3% on majors, reference honest to 5 bp
is it reachable long-short?   not today: +1.51 %/yr against a 2.0 bar
has it ever been?             yes -- 63% of months since 2000, and every
                              month from 2000 to 2008
why not now?                  dispersion 5.22 against a 3.86 toll
is that permanent?            no. it is a regime, and it is observable
what is unresolved?           whether the toll was ever different
```

**Investigation thirty-two.** The first to end UNDETERMINED by design
rather than by running out of data — and the first where the gate that
decided it existed only because the assumption underneath was named
before the run.
