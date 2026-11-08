# RESULT — how much carry actually arrives through OANDA

```
RUN:      2026-09-04
SPEC:     PREREGISTRATION_v15, frozen before the API call
CODE:     fx_carry_access.py 1.1  (1.0 ran; 1.1 fixes a bug in 1.0)
VERDICT:  FAIL on Gate D -- and the reason is more useful than the verdict
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The verdict

```
[PASS] Gate A  39 pairs with net carry > 0 (need 5)
[PASS] Gate B  median pass-through 71.3% on the top 10 by |d| (need 50%)
[PASS] Gate C  median |residual| 0.5 bp, MAX 5.0 bp (need <= 25)
[FAIL] Gate D  long-short book +1.51 %/yr (need 2.0)

    FAIL
```

68 currency pairs, one API call, no price series, no positions.

**OANDA passes carry through better than I predicted, and the reference
is honest.** The family still fails, and it fails on the one gate I
said in advance I expected it to fail on — but not for the reason I
assumed.

## 2. A zero is not a rate — and it was my bug, again

The first run reported violent chaining failures:

```
EUR_TRY    residual  -2811.0 bp
TRY_JPY    residual  +2808.0 bp
CAD_CHF    residual   -149.5 bp     (and five more CAD crosses at ~147.5)
```

Twenty-eight percentage points looks like a broker shading a reference
beyond recognition. It was nothing of the kind.

`USD_CAD`, `USD_MXN` and `USD_TRY` return **`longRate = shortRate =
0.000`**. That is the API saying it has no rate, not a rate of zero.
v1.0 took them at face value, so the anchored rate for CAD, MXN and TRY
came out at exactly 0.00 %/yr, and every cross involving them was then
compared against a fiction.

**None of that was OANDA. All of it was this file.** Excluding the three
missing rows:

```
                        v1.0        v1.1
crosses tested            48          38
median |residual|        0.5 bp      0.5 bp
MAX |residual|        2811.0 bp      5.0 bp
above the 25 bp gate       8           0
```

**The reference is clean.** Every cross chains to within 5 bp.

The tell was available without any of this: a genuine zero differential
still carries a markup, so both rates would be **negative and equal**.
Both *exactly* zero would mean a broker quoting a pair with no
differential and no markup, which is not a thing that exists.

This is the fourth time in this project that a placeholder has been read
as a measurement — after `tradeable` read as traded, a 2000-row page cap
read as history depth, and nine years of `bid == ask` read as a zero
spread. v1.1's self-test now reproduces the failure on planted data and
recovers the same +2808 bp, so the check can fail rather than merely
assert.

**The fix ran toward the candidate.** Removing the corrupted rates moved
Gate D from +1.35% to **+1.51%**, closer to passing. It still failed.
Recording that because a correction that helps the thing being tested is
the one that most needs stating.

## 3. What passed, and it is not nothing

**Gate B — 71.3% pass-through.** I predicted 50-75% and it landed at the
top. The markup is about **1.0%/yr per side on the majors**:

```
pair        longRate  shortRate   d %/yr  s %/yr  net %/yr  pass-thru
USD_CHF        2.800     -4.860     3.83    1.03      2.80     73.1%
AUD_JPY        2.340     -4.400     3.37    1.03      2.34     69.4%
USD_JPY        1.790     -3.810     2.80    1.01      1.79     63.9%
EUR_CHF        1.370     -3.450     2.41    1.04      1.37     56.8%
```

It rises where the carry is: **2.4%/yr on ZAR and HUF pairs, 3.7% on
USD_THB, 7.4% on the TRY crosses.** The broker charges most exactly
where the differential is largest, which is not a conspiracy — it is
the same risk being priced twice.

**Gate C — the reference is real.** This was the test worth building.
It cost one function, needed no external rate data, and it now says
positively that OANDA is not shading the differential per pair. So `s`
is the whole cost, and Gate B's 71.3% is a pass-through and not merely
an upper bound on one.

## 4. Why Gate D failed, which is the actual finding

```
long  ZAR, HUF, AUD    -0.35 %/yr
short JPY, CHF, THB    +1.86 %/yr
                       ---------
spread                 +1.51 %/yr   (need +2.00)
```

**The long leg is negative.** Being long the highest-yielding
currencies available here *costs* 0.35%/yr after financing. Every bit of
carry that survives comes from the short side.

The implied rates say why:

```
ZAR  +2.11    HUF  +1.64    AUD  +0.58    NOK  +0.55    PLN  +0.11
GBP  +0.07    USD   0.00    CZK  -0.02    NZD  -0.74    HKD  -1.07
EUR  -1.43    DKK  -1.88    SEK  -1.99    SGD  -2.30    CNH  -2.46
JPY  -2.80    CHF  -3.83    THB  -4.71
```

**USD is currently near the top of the distribution.** Only five
currencies out-yield it at all, and the best of them by 2.11%. Against a
markup of 1.0-2.4% there is nothing left. Meanwhile the funding
currencies sit 2.8 to 4.7 points *below* USD, so the short leg clears
its markup comfortably.

So the honest statement is not "carry is unreachable at OANDA." It is:

> **Carry through OANDA is currently a short-funding-currency trade, not
> a long-short book — because the USD is itself a high-yielder and a
> roughly constant markup eats the thin long-side differentials.**

That is a **conditional** finding, and the condition is observable and
published: where the USD sits in the G10 rate distribution. In a regime
where USD is near the bottom — 2010-2015, or 2020-2021 — the long leg
would carry real differential and this arithmetic would look different.
Which makes it the same shape as the VIX-conditioning idea: a parameter
someone else publishes in real time, rather than something to re-fit.

**That is the next pre-registration, and it is not claimed here.**
Testing it needs historical financing rates, which OANDA does not serve
— so it would have to be approximated from policy rates plus today's
measured markup, and the constancy of that markup is precisely the
assumption that would need defending first.

## 5. The number I am not going to dress up

```
TRY_JPY   longRate +23.510   shortRate -38.250   d +30.88   s 7.37   net +23.51
```

Long TRY against JPY advertises **+23.51%/yr in financing**, at 76%
pass-through. It is the largest number produced in thirty-one
investigations and it deserves four sentences of context rather than
excitement.

It was **not pre-registered** — v15's book is built against USD, and TRY
has no usable USD pair, so this comes from a cross and enters no gate.
The 7.37%/yr markup is **three times** any other pair in the table,
which is the broker pricing the same risk the carry is paying for.
`USD_TRY` returning no financing data at all means the natural way to
express it is simply absent. And the reason a currency pays 23% to hold
is that it has repeatedly lost a third of its value in a year —
**v15 §8 states plainly that crash risk is not measured anywhere in this
document**, and carry's entire premium is compensation for exactly that.

A 23% coupon on an instrument that can gap 30% against you is not an
edge that has been demonstrated here. It is the trade that the carry
literature uses as its canonical example of why the premium exists.

## 6. Gate C's median was the wrong statistic

v15 §4 scored Gate C on the **median** absolute residual, for
robustness. That was a design error: **per-pair shading concentrates in
a few currencies, and a median is built to ignore exactly that.**

In the first run the median was 0.5 bp — a comfortable pass — while
eight crosses sat between 147 and 2811 bp. The gate passed while the
phenomenon it existed to detect was, apparently, all over the table.

It happened to be my own artifact this time, so the gate's pass was
correct by luck rather than by design. v1.1 prints the **max and the
count over threshold** beside the median, and the self-test demonstrates
the flaw on planted data rather than asserting it: twenty clean crosses
and one shaded by 300 bp passes on the median and fails on the max.

The gate is still scored as frozen. The reporting around it is not.

## 7. Predictions

| | predicted | measured | |
|---|---|---|---|
| Gate A, majors clear it | pass | 39 pairs | **held** |
| Gate B pass-through | 50-75% | **71.3%** | held, top of range |
| Gate C residuals | small, non-zero, in the crosses | max 5.0 bp | held |
| **Gate D** | **fail** | **+1.51% vs 2.0%** | **held** |
| "suspicious if everything passes" | — | it did not | n/a |

Four for four, including the one that mattered. The mechanism was
different from what I assumed, though: I expected Gate D to fail because
the spread pays the markup twice. It does — but the binding constraint
turned out to be that **the long leg is negative outright**, which is
about where the USD sits, not about double-charging.

## 8. Where this leaves it

```
is the premium real?        yes, documented and not in dispute
does OANDA pass it through? 71.3% on the majors, reference honest
is it reachable long-short? not now -- +1.51%/yr against a 2.0% bar
why not?                    USD is itself a high-yielder
is that permanent?          no, and the condition is published daily
what is NOT measured?       crash risk, which is the whole cost of carry
```

Screened in a day, before any strategy work, on the access side only —
which is what five consecutive deaths at this step had earned.

**Investigation thirty-one.**
