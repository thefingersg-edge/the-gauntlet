# PREREGISTRATION v17 — the opening "liquidity candle"

```
WRITTEN:  2026-09-11, after a frequency-only precondition check and
          BEFORE any forward return has been computed
STATUS:   FROZEN
SUBJECT:  whether a large opening 15m candle predicts reversal, whether
          that is about the OPEN or about the SIZE, and whether prior
          context separates the successes from the failures
SOURCE:   the rule as described by Dave from a YouTube video. The video
          itself could not be fetched (HTTP 429) at the time of writing,
          so the rule is transcribed from his description and section 2
          records exactly what is assumed.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The precondition check already reframes the question

Frequency only — no forward return was computed. SPX500_USD M15,
5,842 RTH sessions, 2003-03-21 to 2026-08-28, 151,519 bar-observations.

```
ET       n      median range/ATR14    fires at >=25%
09:30   5826         0.260                54.0%
09:45   5828         0.224                39.6%
10:00   5828         0.237                45.0%
10:30   5828         0.199                29.4%
11:00   5827         0.173                20.7%
12:00   5828         0.136                12.4%
14:00   5828         0.152                17.6%
15:45   5828         0.201                31.3%
ALL              0.163                20.6%
```

**Two facts that the rule as stated does not survive intact.**

**The threshold is at the median of the thing it selects.** The 09:30
bar's median range is 0.260 of ATR14 and the rule's cut is 0.25. It
therefore fires on **54% of days**. A filter that passes more than half
its candidates is not identifying a rare liquidity event; it is
identifying an ordinary opening bar.

**A fixed threshold across the day mostly just selects the open.**
Intraday range follows the familiar U-shape — 0.260 at 09:30, 0.136 at
midday, 0.201 into the close. So "range ≥ 25% of ATR14" fires 54% of the
time at the open and 12% at noon. **"A big candle at the open" and "the
open" are nearly the same statement**, and any test that does not
separate them cannot tell which one is doing the work.

That separation is the design below, and it is the question Dave asked
himself when he asked whether it happens at other times of day.

## 2. What is assumed, because the source could not be read

- the candle is the **first 15m bar of the US cash session, 09:30-09:45
  ET**;
- "14 day average trading range" is the **mean of the previous 14 RTH
  daily high-low ranges**, strictly prior, no lookahead;
- "reversal" means the move **against the candle's own direction**
  (close vs open) after it completes.

**If the video defines any of these differently the run is void and
re-specified before re-running, not adjusted afterwards.** These are
written down now so that the comparison is possible.

## 3. The measurement, frozen

For **every** 15m bar in the RTH session, not only the opening one:

```
entry   the MID OPEN of bar t+1          (the signal bar's own close is
exit    the MID CLOSE of bar t+H          never the entry price)
rev_bp  -sign(close_t - open_t) x (exit/entry - 1) x 1e4
```

Positive `rev_bp` is a reversal; negative is continuation. Entering on
the **next** bar's open is both implementable and the only way to avoid
measuring the signal bar's own closing print.

**Primary horizon H = 4 bars (one hour).** Pre-specified robustness at
H = 1 and H = 12, reported together and never substituted for each
other.

### The grid, which is the whole point

Bars are bucketed by **time of day**, and within each time slot by
**quartile of range/ATR14 computed among bars at that same slot**.

Normalising size *within* the time slot is what separates the two
stories. Comparing a 09:30 bar against a 12:00 bar without it just
re-measures the U-shape in §1.

## 4. The gates, frozen

**Gate A — is there any reversal at the open at all.**

```
PASS   mean rev_bp in the top size quartile at 09:30, t >= 2.0
FAIL   otherwise
```

**Gate B — is it about the OPEN.**

```
PASS   top-quartile rev_bp at 09:30 exceeds the mean of top-quartile
       rev_bp across midday slots (11:00-14:00), t >= 2.0
FAIL   -> the effect is not opening-specific
```

**Gate C — is it about the SIZE.**

```
PASS   at 09:30, top size quartile minus bottom size quartile, t >= 2.0
FAIL   -> the 25%-of-ATR threshold is doing no work and the rule is
          "the open reverses", which is a different and much older claim
```

**Gate C is the one that tests the actual claim.** A "liquidity candle"
story requires that big opening candles behave differently from small
ones. If they do not, the threshold is decoration.

**Gate D — era stability.** The span split into three disjoint thirds;
the Gate C difference must be positive in all three. Nested windows are
forbidden — `AUDIT.md`.

**Gate E — does it survive cost.**

```
PASS   the Gate C difference exceeds 2x the measured round-trip spread
FAIL   otherwise
```

SPX500_USD round trip was measured at 0.76-3.31 bp by era in
RESULT_PREANN. Requiring twice it is not conservative; it is the
minimum at which a one-hour trade is worth placing.

## 5. Prior context — the part that is a fishing licence unless caged

Dave's fourth question is: *did the successes have trends before them
that the failures did not?* **As stated, that is a post-hoc split by
outcome, which is the single most reliable way to manufacture a signal
that does not exist.** With enough candidate features, something always
separates winners from losers in-sample.

It is answerable only under three constraints, all fixed here:

**One — the feature list is enumerated in advance and counted.** Ten
features, no more, no substitutions:

```
 1  prior RTH day close-to-close return
 2  prior 3-day return
 3  overnight gap (09:30 open vs prior 16:00 close)
 4  prior bar's direction, same or opposite
 5  count of consecutive same-direction bars immediately before
 6  ATR14 relative to its own 60-day median (vol regime)
 7  close's distance from the prior day's high and low
 8  day of week
 9  hammer / inverted-hammer geometry of the signal bar
10  close location value within the bar's range
```

Feature 9 is Dave's specific question and is fixed with no tunable
parameter after freezing:

```
body = |close - open|,  upper = high - max(o,c),  lower = min(o,c) - low
hammer           lower >= 2 x body AND upper <= body
inverted hammer  upper >= 2 x body AND lower <= body
```

The `2x` is arbitrary. It is chosen now, once, and not moved.

**Two — a family-wise correction.** Holm at α = 0.05 across the ten.
At the uncorrected 5% level, ten tests are expected to throw up one
false positive by chance, which is exactly how this kind of study
usually "works".

**Three — discovery and confirmation are disjoint eras.**

```
DISCOVERY    2003-2014   search all ten, Holm-corrected
CONFIRMATION 2015-2026   ONLY the survivors, and this is the result
```

**Nothing found in discovery is reported as a finding.** A feature that
survives Holm on 2003-2014 and then fails on 2015-2026 is a failure, and
will be reported as one.

## 6. Kill conditions

- **Any lookahead.** ATR14 uses the previous 14 days, never today.
  Size quartiles are computed from the full sample, which is a mild
  in-sample normalisation and is declared here: it sets bucket
  boundaries, not outcomes, and the Gate C contrast is within-slot so a
  boundary shift cannot manufacture a difference.
- **The signal bar's close is never an entry price.** Entry is the next
  bar's open. If any result depends on entering at the signal close, it
  is microstructure, not a finding.
- **A result above 30 bp** on a one-hour horizon is treated as a bug
  until proven otherwise.
- **One run.** No sweeping H, no moving the 25% threshold, no adding an
  eleventh feature.

## 7. What each outcome means

| | |
|---|---|
| **A, B, C pass** | A genuine opening-specific, size-dependent reversal. Then Gate E, and only then anything else. |
| **A, C pass; B fails** | Big candles revert everywhere. That is short-horizon mean reversion, which is old and well documented, and the "opening liquidity" framing adds nothing. |
| **A, B pass; C fails** | The open reverses regardless of candle size. The 25% threshold is decoration and the video's central claim is false even though its trade might not be. |
| **A fails** | No reversal. The clean negative, on 5,826 openings. |

## 8. What this cannot do

**It cannot test the video's full rule**, which includes confirmation
patterns, stops and targets this document does not model. It tests the
premise underneath: that a large opening candle predicts reversal. If
the premise fails, the rule built on it cannot work for the stated
reason, whatever its P&L.

**It says nothing about wedges.** That is a separate and evidentially
much weaker question — a wedge detector carries six to eight free
parameters and no canonical definition, so a null is always deniable and
a positive is usually a fit. It needs its own pre-registration with the
definition frozen in code first, and it is not bolted onto this one.

**Investigation thirty-three.** The first in this project to test a
pattern claim rather than a premium — the category that has gone
0 for 15.
