# Pre-registration — N1, the pattern zoo on H1 bars

Written 2026-09-18, before any H1 pattern is detected or scored.

## What this is and is not

B3 ran the full candlestick and chart-shape zoo on **daily bars only**. So did
B1, B2 and L1. Twelve families of testing used exactly one timeframe out of
the four on disk. This runs the **identical detector set** on H1 bars.

Identical is the point: `CANDLES()` and `PIVOTED()` from `b3_pattern_zoo.py`
are imported and called unchanged, with H1 bars substituted for daily. Any
difference in result is therefore attributable to the timeframe and not to a
new pattern definition. **Bar-count parameters are deliberately NOT rescaled**
— `PIVOTED(lo_bars=10, hi_bars=120, confirm=20)` means 10 to 120 *hours* here
where it meant 10 to 120 days before. That is what "the same pattern on the
H1 chart" means to anyone reading one, and rescaling would make it a
different test.

## The thing that must be said first

**More bars is not more information.** H1 gives roughly 23x the rows of
daily, but it is the same 21.6 calendar years across the same 21 correlated
markets. The effective sample size is bounded by calendar span and
cross-market independence, not by how finely the span is sliced. Anyone
reading "n = 400,000 detections" should read it as the same information the
daily test had, resampled.

What H1 can genuinely add is different: **patterns too fast to exist at daily
resolution.** A three-bar reversal spanning three hours is invisible on a
daily chart. That, and only that, is the reason to run this.

## Prior — low, and the reason is arithmetic

B3 on daily found nothing after its control was fixed: the `+/-21` bar
exclusion window had manufactured a +4.67% baseline against a +0.76%
unconditional, and nine apparent passes vanished when it was corrected. L1's
unsupervised version found nothing across 462 tests with a max |t| of 1.97.

This run multiplies the test count again. The correction needed to keep it
honest grows with it, which is exactly the mechanism that erased L1.

## Design

**Universe.** All 21 markets, `*_oanda_h1.csv`, 2005 to 2026-08-07.

**Horizons, in H1 bars.** `h ∈ {6, 24, 120}` — about 6 hours, 1 day, 5 days.
The 24 and 120 overlap the daily test's 1-day and 5-day horizons at the same
calendar distance, so those two are directly comparable. The 6-hour horizon
is the genuinely new one and is where any intraday-only effect would live.

**Non-overlap thinning — required, and new.** B3 accepted overlapping forward
windows on daily, documenting it as "the lesser evil than an empty control."
On H1 detections are ~23x denser and a 120-bar window overlaps its neighbour
by 119/120. Within each market and pattern, a detection is kept only if it
falls at least `h` bars after the last kept one. This costs sample size and
buys a t-statistic that means something.

**Control.** The b3 matched control unchanged: every non-firing bar in the
same era, prior-return quintile and volatility quintile. Not a window
exclusion — that is the defect b3 already fixed.

**Effective sample size.** `n_eff = n_thinned x (5 / markets_contributing)`,
the same deflation L1 used. Thinning handles serial correlation; this handles
cross-market correlation.

## Costs — and why b3 could ignore them and this cannot

B3 measured raw forward return against a control, never net of cost. At a
21-day horizon on daily bars that was defensible; the edges it reported were
around 2bp and cost was not what killed them.

At a 6-hour horizon it is not defensible. XAU_USD round-trip spread is about
**1.5bp** of price. **Every effect is reported in basis points alongside the
round-trip spread**, and an effect smaller than the spread is reported as
unusable regardless of its t-statistic.

## Pass criteria — fixed in advance

A pattern passes only if ALL of:

1. |t| >= 3.0, computed on `n_eff`, not on the raw detection count.
2. Benjamini-Hochberg q < 0.05 across every pattern x horizon tested.
3. Same sign in all three eras.
4. Effect exceeds **2x the round-trip spread** at that horizon.
5. Its daily-bar counterpart in `b3_zoo.csv` is not strongly opposite-signed
   — a pattern that works on H1 and inverts on daily is a timeframe artefact,
   not a finding.

## "Shows promise" — the trigger for extending to other timeframes

Defined now so that the decision to go on is not a judgement made after
seeing the numbers.

**Promise = at least one pattern clears all five criteria above.**

Secondary, reported but not sufficient on its own: the count of patterns at
uncorrected p < 0.05 exceeding **twice** the number expected by chance at
that threshold. That would indicate aggregate signal without any individual
pattern surviving, and would justify a narrower follow-up rather than a
sweep across M15 and H4.

**If neither holds, the timeframe question is closed** — not just for H1 but
for the family. The daily result and the H1 result agreeing on nothing, with
L1's unsupervised search agreeing with both, is three independent looks at
the same absence. A fourth timeframe would be the search problem L1 closed,
wearing a clock face.

## What a pass would still not license

An H1 pattern that clears all five criteria would be a statistical result on
21 CFDs, measured gross of slippage and of the funding this project now
charges, and would still have to survive the forward test that nothing here
has been through. The ceiling is "worth pre-registering a strategy around".
