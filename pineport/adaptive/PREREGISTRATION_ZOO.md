# Pre-registration — the standard pattern taxonomy, all of it

Written **before any result was looked at**, 2026-08-27.

## What has been tested, and the hole in it

| | tested | result |
|---|---|---|
| converging trendlines — symmetrical triangle, rising and falling wedge | Part B | fail; mark quiet markets that stay quiet |
| level reversals — double top/bottom, head and shoulders ± | B2 | fail; all four mark one mildly bullish state |
| **everything else in the standard taxonomy** | **no** | |

Both families failed the **same** gate for the **same** reason: move the
swing-pivot window by one bar and 40–49% of detections vanish. Pivots are the
problem, not the geometry built on them.

**Which is the reason to run this.** Candlestick patterns use no pivots at all —
they are defined on one to three bars from open, high, low and close. They dodge
the specific failure mode that has killed everything so far. That is a stated
reason to expect a different answer, and it is what makes this worth running
rather than more of the same.

## The taxonomy, scored in full

**Pivot-based (expected to fail on gate 1, included for completeness):**
ascending triangle, descending triangle, rectangle, broadening top/bottom,
triple top, triple bottom, rounding bottom.

**Candlestick — no pivots (the reason for the run):**
bullish/bearish engulfing, hammer, hanging man, shooting star, inverted hammer,
morning star, evening star, bullish/bearish harami, three white soldiers, three
black crows, piercing line, dark cloud cover, marubozu ±, dragonfly and
gravestone doji.

**Gaps:** gap up, gap down.

All candlestick thresholds are expressed in **ATR multiples**, never in price
units — GAUNTLET 1.3.

## Horizons

1, 5 and 21 trading days. Candlestick patterns are held to be short-horizon and
would be unfairly served by a 21-day test alone.

## The control, applied to every pattern

Each detection is compared against non-detection days in the **same market, same
era, same prior-return decile and same volatility decile**. B2 established why:
all four reversal patterns looked directional and were in fact one state, and
only a matched control revealed it.

## Gates, and the multiple-comparison problem stated up front

Roughly **30 patterns × 3 horizons ≈ 90 tests**. At 5% significance, four or five
will clear a t-statistic by luck alone. A t-stat is therefore **not** the gate.

| # | criterion | threshold |
|---|---|---|
| 1 | controlled excess, signed by the textbook call | same sign in **all three eras** |
| 2 | breadth | same sign in ≥ **14 of 21** markets |
| 3 | size | \|excess\| ≥ **0.20%** at some horizon |
| 4 | sample | ≥ 200 detections |
| 5 | stability | ≥ 80% of detections survive perturbing the detector's thresholds by ±50% |

Criteria 1 and 2 together are the multiple-comparison control: under a null,
three-era sign consistency happens 25% of the time and 14-of-21 breadth about
9%, so the joint probability is roughly 2% per pattern — about **0.6 expected
false passes** across the whole taxonomy.

## Stated in advance

If nothing clears, the conclusion is that the standard chart-pattern taxonomy —
both geometric and candlestick, some thirty constructions — carries no
directional information at these horizons on these markets. If something clears,
it is a candidate requiring its own replication, not a finding.
