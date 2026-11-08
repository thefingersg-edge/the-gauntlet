# Findings — N1, the pattern zoo on H1 bars

Pre-registered in `PREREGISTRATION_ZOO_H1.md`. Run 2026-09-18. 21 markets,
`*_oanda_h1.csv`, 2005 to 2026-08-07. Detectors imported unchanged from
`b3_pattern_zoo.py`, so any difference from the daily result is attributable
to the timeframe and not to a new pattern definition.

## Verdict

**FAIL. No promise. The timeframe question is closed.**

    25 patterns x 3 horizons = 75 tests, BH-corrected
    max |t| 2.17      min q 0.9810
    patterns passing all five criteria: 0
    era-consistent cells: 0 of 75

Both pre-registered promise triggers fail:

- **Primary** — at least one pattern clearing all five criteria: **none**.
- **Secondary** — uncorrected p<0.05 count exceeding twice chance: **1
  observed against 3.8 expected**, so fewer than chance, nowhere near the 7.6
  the trigger required.

## The shape of the result

The informative thing is not the absence but its structure. Effect size and
sample size are inversely related — every large effect sits on a thin sample
and every well-sampled pattern has an effect below the cost of trading it:

| pattern | h | markets | n | effect | t |
|---|---|---|---|---|---|
| rounding_bottom | 24 | 12 | 1,924 | **+12.9bp** | 1.12 |
| desc_triangle | 6 | 12 | 1,765 | **-9.8bp** | -1.24 |
| marubozu_bear | 6 | 21 | 104,447 | -0.9bp | -1.65 |
| marubozu_bull | 24 | 21 | 60,979 | +1.4bp | 1.10 |

Thirteen of 75 cells clear the 3bp cost bar. Not one of those thirteen also
clears the t, the q, or era consistency. That is what noise looks like when
you sort it by magnitude: the biggest numbers come from the smallest samples.

**Zero of 75 cells hold their sign across all three eras.** On the daily run
that check killed nine apparent passes. Here there is nothing for it to kill.

## One honest qualification

"Fewer nominally significant results than chance" reads more strongly than it
should. The `n_eff` deflation — dividing the raw detection count by markets
and multiplying by 5 blocs — makes every t conservative by construction, and
the 75 tests are not independent of each other. So the right reading is "no
detectable excess of significant results", not "suspiciously few".

What is not qualified: the thinning. Requiring detections to be at least `h`
bars apart means the forward windows genuinely do not overlap, which is the
one thing b3 could not claim on daily and the reason its t-statistics were
softer than they looked.

## What this closes

Per the pre-registration, failing both triggers closes the timeframe question
for the pattern family — not only H1. Three independent looks now agree:

- **B3**, named patterns, daily bars, nothing after the control was fixed.
- **L1**, unsupervised discovery, daily bars, 462 tests, max |t| 1.97.
- **N1**, the same named patterns on H1, 75 tests, max |t| 2.17.

Different pattern vocabularies, different timeframes, same answer. Extending
to M15 or H4 would be the search problem L1 already closed, wearing a clock
face — and M15 exists for only 11 of 21 markets, so it could not be run at
full width even if it were worth running.

## What would reopen it

A mechanism, not a timeframe. If there were a specific reason to expect a
pattern to work at a particular hour — session boundaries where liquidity
provision genuinely changes, or the futures roll window — that is a testable
hypothesis with a stated cause, and it would get its own pre-registration.
"Try the next timeframe down" is not that.
