# Track A, day three — the 158bp was an outlier, and my own log was poisoning itself

```
SPEC:     PREREGISTRATION_v8, Track A (observation only) -- registry link added 2026-09-26
RUN:      2026-08-28, third observation, first under --all-dated
METHOD:   basis_monitor.py v1.3 --all-dated (v1.4 ships the fix below)
VERDICT:  entry cost is smaller than day two suggested and larger than day
          one did. One defect found in this file and fixed.
```

---

## 1. The defect, first, because it was mine

```
FF_XBTUSD_260828    linear      534.57 bp    -947.15% ann
```

**−947% is not a rate.** The August contract settled today, so days-to-expiry
was 1, and annualising multiplies by 365/days. A mid sitting 2.59% under the
index on its last day becomes −947% by arithmetic alone.

The append-only log had already swallowed it. Any later average over
`basis_ann_pct` would have been dominated by one dying quote, and the whole
point of an append-only record is that nothing downstream has to know which
rows to distrust.

**v1.4:** below 5 days to expiry the annualisation is withheld and the row
says why. The raw basis, spread, bid and ask are all still recorded — only
the derived column is suppressed. The threshold was set before it could
change any conclusion: Track A has no gates and decides nothing.

The self-test plants today's actual row and asserts it comes back empty.

**A second, quieter bug found alongside it:** `annualise(...) or 0.0` turned
an unannualisable row into a literal **0.0** — indistinguishable in the CSV
from a genuinely flat basis. Two rows meaning "no data" and "no premium"
were being written identically. Now blank, with a test asserting the CSV
cell is empty rather than `0.000000`.

## 2. The September book — three observations now

| date | spread | half-spread a seller crosses |
|---|---|---|
| 19 Aug | 1.00 bp | 0.50 bp |
| 25 Aug | **158.38 bp** | 79.19 bp |
| 28 Aug | 3.78 bp | 1.89 bp |

**Median 3.78 bp. Mean 54.39 bp.** The gap between those two numbers *is* the
finding.

Day one I said the spread was "about one basis point" and called v4's cost
model conservative. Day two I found 158bp and said the 1bp figure was
unsafe. Day three says the 158bp was the outlier, not the rule — **but one
observation in three was over 100bp**, and that is not a rate you can plan
around by taking a median.

December, by contrast: 44.92 / 38.26 / 34.51 bp. Stable, tightening,
no outlier. The far contract is consistently wide and *predictably* wide.
The second contract is usually tight and occasionally not.

## 3. What this does to the roll cost

The frozen rule holds to settlement and rolls on the settlement date. That
means it **never crosses the expiring contract's spread** — the position
cash-settles at the index. Today's 534bp on the August contract is therefore
not a cost the rule pays. Decomposed:

```
implied bid  ~0.948x index      the bid has been pulled
implied ask  ~1.000x index      the ask is still at fair value
```

Nobody wants to buy an expiring contract. The rule never sells it.

So the roll costs **one crossing of the new contract's spread**:

| | half-spread | annualised over 4 rolls |
|---|---|---|
| rolled today | 1.89 bp | **0.08 pts/yr** |
| rolled at the 3-obs median | 1.89 bp | **0.08 pts/yr** |
| rolled on 25 August | 79.19 bp | **3.17 pts/yr** |

v4 assumed 0.05% taker plus one tick — about 7 bp per leg, **0.28 pts/yr**.

**Against the median that assumption is conservative by 3.5×. Against the
worst observed day it is optimistic by 11×.** Both statements are true and
neither is the answer; three observations do not make a distribution.

## 4. Where entry cost now sits

It was the largest unmeasured term in the candidate. It is now the largest
*partially* measured one:

```
best case   roll on a tight day     0.08 pts/yr
typical     the median so far       0.08 pts/yr
bad case    roll on a wide day      3.17 pts/yr
```

Era 3 measured +2.56 and the bar is +2.0. **A roll executed on a day like 25
August, four times a year, would exceed the entire margin.** The rule's own
timing discipline is what protects it — and the rule specifies the
settlement date, which is not a day anyone chooses.

> **CORRECTED 2026-08-29.** This section originally closed: *"Today the
> settlement date happened to be a tight day. That is one observation of the
> thing that matters most, and it went the right way."*
>
> **That was wrong.** `FF_XBTUSD_260828` is a **monthly** contract. The
> frozen rule trades the nearest **quarterly** — as do all 18 of v4's
> cycles, every one of which falls in the last week of March, June,
> September or December. 28 August was not a roll date for the rule and
> nothing about it was an observation of one.
>
> The mechanism above still holds: the rule settles rather than crosses, so
> an expiring contract's spread costs it nothing. But **the count of
> roll-date observations is still zero.** The first one is 25 September.

## 5. What would settle it

The daily log, run to the September settlement on 25 September. That gives
about 20 more observations of the contract the rule trades, and — critically
— **one observation of the spread on an actual roll date**, which is the
only day the rule ever transacts.

Twenty-eight days from now this question is answered properly. Until then:
median 3.78bp, one excursion to 158bp, and no basis for calling either
typical.

## 6. Scoreboard

Unchanged. The candidate still passes every pre-registered gate and still
carries four unpriced items — of which entry cost has now moved from
"unmeasured" to "measured three times, once badly".
