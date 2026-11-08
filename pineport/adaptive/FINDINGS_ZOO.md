# The standard pattern taxonomy — twenty-five constructions, none holds

Run 2026-08-27 against `PREREGISTRATION_ZOO.md`, written first. 21 markets,
2005–2026, horizons of 1, 5 and 21 days. Reproduce with
`python3 b3_pattern_zoo.py`.

## Why this was worth running rather than more of the same

Parts B and B2 both failed the **same** gate for the **same** reason: move the
swing-pivot window by one bar and 40–49% of detections vanish. Pivots were the
problem, not the geometry.

**Candlestick patterns use no pivots.** They are defined on one to three bars
from open, high, low and close, so they dodge the specific failure mode that had
killed everything. That was the stated reason to expect a different answer.

## What was tested

**Candlestick (18):** bullish/bearish engulfing, hammer, hanging man, shooting
star, inverted hammer, bullish/bearish harami, bullish/bearish marubozu,
dragonfly and gravestone doji, morning star, evening star, three white soldiers,
three black crows, piercing line, dark cloud cover.
**Pivot-based (5):** ascending and descending triangle, triple top, triple
bottom, rounding bottom. **Gaps (2):** gap up, gap down.

All candlestick thresholds in ATR multiples, never price units (GAUNTLET 1.3).

## Result: nothing passes

Controlled excess return, signed by each pattern's textbook call, matched on
market / era / prior-return quintile / volatility quintile:

| pattern | n | 21-day excess | markets | era-consistent |
|---|---|---|---|---|
| gap down | 498 | **+0.76%** | 11/21 | yes |
| descending triangle | 1,482 | +0.84% | 10/21 | no |
| triple bottom | 13,585 | +0.16% | 7/21 | yes |
| bullish engulfing | 4,248 | +0.03% | 11/21 | no |
| bearish engulfing | 4,233 | +0.10% | 13/21 | no |
| bullish marubozu | 9,782 | −0.03% | 9/21 | no |
| bearish marubozu | 8,586 | −0.01% | 10/21 | no |
| three white soldiers | 2,856 | −0.08% | 11/21 | no |
| three black crows | 2,593 | −0.28% | 11/21 | no |
| hammer | 890 | −0.17% | 9/21 | yes |
| shooting star | 764 | −0.68% | 8/21 | yes |
| … 14 others | | −0.35% to +0.21% | | |

**Passed all four gates: none.** The largest effect in the taxonomy is gap-down
at +0.76%, era-consistent, and it holds its sign in only 11 of 21 markets.

Twenty-five patterns × three horizons is 75 tests; the pre-registration set
three-era sign-consistency *and* 14-of-21 breadth as the multiple-comparison
control, expecting about 0.6 false passes. Zero passed, which is one fewer than
chance would have given.

## The correction that produced this table

**The first run returned nine passes**, including bullish marubozu at +2.59% and
bearish marubozu at +3.31% — both positive when signed by their own opposite
calls, on 21 of 21 markets, era-consistent. Effects of 3% over 21 days, on
thousands of detections, in a project where nothing else has cleared 0.1%.

The symmetry is what gave it away: every bullish/bearish pair passing together
is the signature of a broken baseline, not a discovery.

The control excluded a **±21-bar window** around every detection from the
control pool. With a pattern firing thousands of times that removes nearly the
entire series, and each cell mean is then computed on a handful of unrepresentative
survivors. Checked directly on gold: the control reported a baseline of
**+4.67%** against an unconditional **+0.76%**.

With the pool corrected to exclude only the detection bars themselves, marubozu
goes from +2.59%/+3.31% to −0.03%/−0.01%, engulfing from +0.96%/+0.88% to
+0.03%/+0.10%, and all nine passes vanish.

**This is the third time in this project that a control has manufactured a
result** — after the shared `RV` term in the variance-risk-premium study and the
forward-filled volatility series in the sizing study. Each was caught by the same
habit: when a number is far larger than everything around it, check what the two
sides of the comparison share before believing it.

`FINDINGS_REVERSALS.md` used the same broken construction and has been corrected.

## Where the pattern programme now stands

| family | constructions | detections | verdict |
|---|---|---|---|
| converging trendlines | 3 | 3,448 | fail — 41% pivot stability; direction +0.02% against +0.52% unconditional |
| level reversals | 4 | 1,774 | fail — 43% pivot stability; textbook direction +0.21%, t +1.22, 13/21 markets |
| candlestick, gaps, other geometry | 25 | ~85,000 | **fail — nothing passes** |

**Thirty-two constructions. None of them holds.** The candlestick family, which
was the reason to run this and which avoids the pivot problem entirely, produces
the smallest effects in the whole set — the largest is shooting star at −0.68%
against its own call, on 8 of 21 markets.

The one construction with any life left is double bottom, at +0.98% and t = +2.33
on 410 detections (`FINDINGS_REVERSALS.md`). Against ninety-odd tests, one t of
2.3 is exactly what chance delivers, and its nearest relative here — triple
bottom, on 13,585 detections — returns +0.16%.
