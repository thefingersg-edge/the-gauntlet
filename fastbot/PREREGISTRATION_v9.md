# PREREGISTRATION v9 — what did a roll actually cost?

```
WRITTEN:  2026-08-29, AFTER kraken_history.py v1.2 returned VIABLE and
          BEFORE a single price has been read from the 1m series
STATUS:   FROZEN
SUBJECT:  executed cost on the Kraken dated BTC quarterlies, measured
          retrospectively over the same 14 cycles v4 measured the premium on
```

**I am not a financial adviser. This is research tooling, not a
recommendation to take a position.**

---

## 1. Why this exists

`RESULT_KRAKENBASIS_LINEAR` passed every pre-registered gate at **+2.56**
in era 3 against a **+2.0** bar. Headroom: **0.56 points.**

Entry cost is the largest unmeasured term against that headroom. Track A has
four observations of the quoted spread — 1.00, 158.38, 3.78, 13.62 bp — and
a 95% interval on the wide-day rate of **4.6% to 69.9%**, which is no answer.
`TRACKA_HOW_LONG` put a properly powered forward read in late October.

Phase 0 established that the same question is answerable backwards, over
**14 quarterly cycles and 2,575 days**, at 1-minute resolution.

## 2. The contamination, stated first

**I already know what result saves two months of waiting.** I wrote the
probe, I read its VIABLE verdict, and I corrected that probe twice in ways
that moved the answer toward the candidate. This document exists because
none of the numbers below can be chosen after seeing the series.

Two specific guards:

- Every threshold in §4 and §5 is **derived from figures already published
  in earlier results**, not selected. Where I had a free choice I have said
  so and given the reasoning in advance.
- The measurement script will assert, by namespace inspection, that it
  contains no function able to re-run itself with different thresholds.

## 3. The measure

For each 1-minute bar on a dated quarterly where a trade occurred:

```
deviation_bp = |trade_close − mark_close| / mark_close × 10,000
```

`trade` is what executed. `mark` is Kraken's own fair value for the same
minute. Their gap is how far transacted prices sat from fair value, which is
the thing v4 assumed away and Track A samples once a day.

**Minutes with no trade are counted separately, never dropped.** A minute
where nobody transacted is not missing data — it is the illiquidity being
measured, and §7 explains why it is also the measure's worst weakness.

## 4. What counts as a WIDE minute — derived, not chosen

Era 3's headroom over the bar is **0.56 points per year**. The rule rolls
**four times a year**. So the per-roll cost that exhausts the entire margin
is:

```
0.56 / 4 = 0.14% = 14 basis points
```

**WIDE = deviation ≥ 14 bp.** That number is not a judgement about
microstructure; it is arithmetic on a result that was published before this
document. A roll costing more than it consumes more than its share of
everything the trade earns above its own counterparty-risk bar.

For reference and not as a threshold: v4 assumed ~7 bp per leg, Track A's
tight days implied 0.5–2 bp of half-spread, and its one wide day implied 79.

## 5. The gates, frozen

**Gate A — the roll-date rate.**
Across the 14 historical settlement dates, on the contract the rule would be
**entering** that day (the next quarterly), the share of traded minutes that
were WIDE.

```
PASS   < 20% of traded minutes wide
FAIL   >= 20%
```

20% is a free choice and I am naming it as one. Reasoning fixed in advance:
at 20%, a roll executed at a uniformly random minute of the settlement day
has a ~1-in-5 chance of costing more than its whole margin share, and four
rolls a year then carry a **59%** chance of at least one. Above that the
rule's cost is dominated by timing luck rather than by the premium.

**Gate B — are settlement days special?**
The same rate computed on all non-settlement days of the same contracts.

```
PASS   roll-date rate is not materially WORSE than the all-days rate
       (roll-date rate <= all-days rate + 10 percentage points)
FAIL   otherwise
```

This is the gate that matters most and the one no amount of daily Track A
sampling can reach. If settlement days are systematically worse, every
forward observation on an ordinary day is misleading about the only day the
rule trades.

**Gate C — enough to say anything.**

```
PASS   >= 8 of the 14 roll dates have >= 30 traded minutes each
FAIL   otherwise -> UNDETERMINED, and Track A's timeline stands
```

**Gate D — does era 3 survive the measured cost?**
Median roll-date deviation, applied as a half-spread four times a year,
subtracted from era 3's +2.56.

```
PASS   result >= 2.0
FAIL   result < 2.0
```

## 6. Kill conditions, fixed now

- **The mark series has gaps where the trade series does not.** Then the
  deviation is being computed against a stale reference and the whole
  measure is void. Reported, not patched.
- **Fewer than 8 usable roll dates** (Gate C) → UNDETERMINED. Not
  "extended to more cycles until it passes".
- **Any threshold above needs changing to get a result** → the run is
  abandoned and recorded as abandoned. One run. No sweeps, no sign flips,
  no re-specification. This is the rule that has held for twenty-four
  investigations and it holds here.
- **The measured deviations are implausibly small** — say a median under
  0.5 bp across all 14 cycles. That would suggest `trade` and `mark` are
  not independent series (mark derived from last trade), which would make
  the whole measure circular. **This is the failure mode I consider most
  likely** and it must be checked before anything is concluded.

## 7. What this cannot answer, and the bias it carries

**The measure is biased optimistic, and the bias is structural.**

It can only see minutes where a trade printed. The minutes when the book was
so bad that nobody transacted — which are exactly the worst minutes, and
plausibly what the 158 bp quote on 25 August represented — leave no print to
measure. **A wide book with no trades looks identical to a calm market.**

So Gate A's rate is a lower bound on how often execution was bad, and the
untraded-minute count in §3 is the only visible shadow of what is missing.
That count will be reported alongside every figure.

Three further limits:

- **No trade direction.** OHLC cannot say whether a print was a buy or a
  sell, so a seller's cost is inferred from a symmetric deviation rather
  than observed.
- **Intra-minute movement is confounded with spread.** A minute in which
  the price genuinely moved shows a deviation that is not a cost.
- **`mark` is Kraken's own valuation.** If it lags, deviations are
  overstated; if it is derived from trades, they are understated. §6's last
  kill condition is the test for the second case.

## 8. What each outcome means

| | |
|---|---|
| **All four gates pass** | Entry cost is measured and era 3 survives it. Track A continues as confirmation rather than as the primary evidence, and the candidate's open-item list drops from four to three. |
| **Gate B fails** | Settlement days are worse than ordinary days. Every Track A observation to date is misleading about the only day that matters, and the forward protocol needs redesigning around roll dates. |
| **Gate A or D fails** | Entry cost consumes the margin. The candidate returns to rejected — on a measurement rather than an assumption, which is what v4 wanted and never had. |
| **Gate C fails** | UNDETERMINED. Track A's late-October timeline stands unchanged. |

## 9. What this does not touch

The premium itself, the collateral costs, the convergence tailwind, and
counterparty risk. This measures one term. `RESULT_KRAKENBASIS_LINEAR` §9
still holds: some risks have a price no amount of data can estimate, and no
result here changes that.

## 10. Scoreboard

**Investigation twenty-five.** The first in the project to test a candidate's
*costs* against history rather than its returns — and the first where the
data being used was found because a two-month wait looked too long.
