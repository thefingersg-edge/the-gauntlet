# Pre-registration v2 — the ten bar patterns

```
WRITTEN:   2026-08-17
STATUS:    FROZEN BEFORE ANY PATTERN WAS COMPUTED ON THIS DATA
SOURCE:    tradingview.com/chart/EURUSD/zk1YPPgw  (external, pre-specified)
FAMILY:    intrabar OHLC geometry -- a different vocabulary to v1 and to
           DESIGN_BRIEF.md, which tested smoothed/derived indicators only
```

---

## 1. Why this is worth a test, and why it is a screen not a hypothesis

**The strength, and it is real:** the list of patterns is **externally sourced
and fully specified before anyone looked at the data.** Nothing here was
chosen because it worked. That is a better starting position than most of what
this project has tested — `pineport` selected copper and palladium *because*
they backtested well, and `DESIGN_BRIEF` records that this produced an 80%
hedging artefact.

**The weakness, and it is equally real:** this is **20 simultaneous tests**
(ten patterns, two directions each), not one hypothesis. silver15 established
that *14 combinations at 2σ give a >50% chance of a spurious pass.* At an
uncorrected bar of net Sharpe 0.76 on 7 years — about 2.0σ, one-tailed
p ≈ 0.022 — **20 tests yield ~0.44 expected false positives.** So:

> **One pattern passing the screen is not evidence.** It is roughly what
> chance produces. The screen is a filter, not a verdict, and §5 defines what
> a survivor must then do.

**What the literature says**, stated before running rather than cited
afterwards to explain a result: candlestick profitability studies are mixed,
and the recurring finding is that apparent edges shrink or vanish once
transaction costs and out-of-sample testing are applied. That is a prior
against, not a reason to skip the measurement.

## 2. Two predictions, made in advance, from v1's result

`RESULT_v1.md` established that on NAS100 in the US session a 3-sigma 5-minute
bar is followed by **continuation, not reversion**, sign-consistent across all
seven years. Two things follow, and both are falsifiable:

**Prediction A — direction.** Despite being called *reversal* patterns, all
ten entry rules in the source are **breakout entries in the direction of the
final bar** ("buy above the bullish pattern"). These are continuation trades.
v1 therefore predicts they will be **positive but small** — v1 measured
continuation at net +0.36 Sharpe, under half the bar. *If these patterns come
back strongly negative, v1's finding is contradicted and something is wrong
with one of the two tests.*

**Prediction B — cost, and it is specific.** Inside Bar and NR7 fire on the
**smallest-range bars in the sequence, by definition.** cost/vol is
`cost / dispersion`, so these two patterns enter precisely when the ratio is
at its worst. v1 measured the opposite case — entering after a 3-sigma bar
gave 1.74× the unconditional dispersion and a 1.74× cost discount. The
compression patterns should get a penalty of similar magnitude in the other
direction. **Inside Bar and NR7 are predicted to be the worst two patterns on
a net basis, and the gap to their own gross should be the largest.**

Recording these now means the run can embarrass them.

## 3. The patterns, quantified

The source is vague in places ("long tail dominating", "strong bearish bar").
Every threshold below is **fixed here, before the run, at a round value**, and
none may be adjusted afterwards. Where a choice was needed it is flagged.

Let bar `i` have `O,H,L,C,V`; `rng = H-L`; `body = |C-O|`.

| # | pattern | bullish condition |
|---|---|---|
| 1 | Reversal Bar | `L[i] < L[i-1]` and `C[i] > C[i-1]` |
| 2 | Key Reversal | `O[i] < L[i-1]` and `C[i] > H[i-1]` |
| 3 | Exhaustion | `O[i] < L[i-1]` and `H[i] < L[i-1]` (gap unfilled) and `C[i] >= L[i]+0.75·rng[i]` and `V[i] > median(V[i-20..i-1])` |
| 4 | Pin Bar | `min(O,C)[i] - L[i] >= 0.66·rng[i]` |
| 5 | Two-Bar Reversal | `C[i-1] <= L[i-1]+0.33·rng[i-1]` and `C[i] >= L[i]+0.67·rng[i]` |
| 6 | Three-Bar Reversal | `C[i-2]<O[i-2]`; `H[i-1]<H[i-2]` and `L[i-1]<L[i-2]`; `L[i]>L[i-1]` and `C[i]>H[i-1]` |
| 7 | Three-Bar Pullback | `C<O` for `i-3,i-2,i-1`; `C[i]>O[i]` |
| 8 | Inside Bar | `H[i]<H[i-1]` and `L[i]>L[i-1]` — direction from the break |
| 9 | Outside Bar | `H[i]>H[i-1]` and `L[i]<L[i-1]` — direction from the break |
| 10 | NR7 | `rng[i] == min(rng[i-6..i])` — direction from the break |

Bearish conditions are the exact mirror.

### Extended set — the classical candlestick family

Added so the test covers the family rather than one author's shortlist. Same
rules, same freeze, same report.

| # | pattern | bullish condition |
|---|---|---|
| 11 | Engulfing | `C[i-1]<O[i-1]`; `C[i]>O[i]`; `O[i]<=C[i-1]` and `C[i]>=O[i-1]` |
| 12 | Harami | `C[i-1]<O[i-1]`; `body[i] < 0.5·body[i-1]`; `max(O,C)[i]<=O[i-1]` and `min(O,C)[i]>=C[i-1]` |
| 13 | Hammer | `min(O,C)[i]-L[i] >= 2·body[i]` and `H[i]-max(O,C)[i] <= 0.25·rng[i]` |
| 14 | Marubozu | `body[i] >= 0.9·rng[i]` and `C[i]>O[i]` |
| 15 | Doji | `body[i] <= 0.1·rng[i]` — direction from the break |
| 16 | Morning Star | `C[i-2]<O[i-2]`; `body[i-1] <= 0.3·body[i-2]`; `C[i]>O[i]` and `C[i] >= O[i-2]-0.5·body[i-2]` |
| 17 | Three Soldiers | `C>O` for `i-2,i-1,i`; each `C` above the last; each `O` inside the prior body |
| 18 | Wide-Range Bar | `rng[i] >= 2·median(rng[i-20..i-1])` — direction from the close's half |
| 19 | Gap Bar | `O[i] > H[i-1]` (gap up) — direction from the break |
| 20 | Opening Range Break | first bar of the session; direction from the break of its range |

**This raises the count to 40 tests** (patterns 1–7, 11–14, 16–17 directional
= 26; 8–10, 15, 18–20 bidirectional = 14). Expected false positives at the
uncorrected bar rise from ~0.44 to **~0.9**. That does not weaken the design,
because §5's power was never in the screen — but it does mean **the screen
result alone is worth nothing at all**, and it makes the >6-of-7-years sign
requirement and the two-instrument confirmation load-bearing rather than
decorative.

### Project-level test counter — kept because nobody ever does

Every family tested against the same NAS100 fit window compounds the risk that
*something* eventually passes.

| version | family | tests |
|---|---|---|
| v1 | liquidity provision | 1 |
| v2 | bar patterns | 40 |
| **running total on this window** | | **41** |

At 41 tests, roughly **1 spurious pass at the uncorrected bar is expected by
chance alone.** If v2 returns exactly one advancing pattern, the correct prior
is that it is that one. Confirmation on untouched instruments is the only
thing that separates them, and this counter is why.

**Three declared judgement calls, none revisitable:**

1. **Thresholds 0.66 / 0.33 / 0.67 / 0.75 are invented.** The source gives no
   numbers. They are set at round fractions and are *not* swept. If a pattern
   fails, "a different tail fraction might work" is not available — that is
   the v1 §5 rule applied here.
2. **The source's bearish Three-Bar Reversal is asymmetric** — it specifies a
   middle bar with "higher high and lower low", which is an outside bar, while
   the bullish version uses "lower high and lower low". This is treated as a
   typo and the symmetric mirror is used. Noted rather than silently fixed.
3. **Volume on an OANDA CFD is tick count, not traded size.** Pattern 3 needs
   volume and this is a proxy. Its result carries that caveat permanently.

## 4. Execution — pinned, and comparable to v1

```
ENTRY   stop order at the pattern bar's high (long) / low (short),
        live for the NEXT BAR ONLY
FILL    only if that bar trades through the trigger.
        price = max(trigger, bar open) for a long -- a gap through the
        trigger fills at the open, not the trigger. Never the better of the two.
        long pays the ASK, short receives the BID, actual spread on the bar
EXIT    at the open of the bar H=6 later (30 min), same as v1
SIZE    constant notional
SESSION 09:00-16:00 America/New_York, flat overnight, financing zero
LIMITS  non-overlapping per pattern; <= 4 round trips/day per pattern
```

`H=6` is carried over from v1 unchanged so the two families are directly
comparable and no new parameter is introduced.

**No spread gate.** v1's gate blocked 39% of signals; applying it here would
confound Prediction B, which is precisely about which patterns are expensive.
Cost is charged in full and reported instead.

## 5. Gates

### Screen — NAS100, fit window 2014-2020

Already opened by v1, so no further out-of-sample capacity is spent.

```
report ALL 20 with net Sharpe, gross Sharpe, cost, trade count, and the
sign in each of the 7 years. No pattern is discarded from the report.

A pattern ADVANCES only if:
  net Sharpe >= 0.76   AND   >= 200 trades   AND   <= 4 round trips/day
  AND the sign is consistent in >= 6 of 7 years
```

The year-sign requirement is the cheap filter `DESIGN_BRIEF` found most
effective, and it is what a spurious pass is least likely to survive.

### Confirmation — SPX500 and US30, never touched

```
An advancing pattern must show the SAME SIGN and net Sharpe > 0 on BOTH,
over the same 2014-2020 window, with identical parameters.
```

These instruments have never been pulled, so this is genuine out-of-sample —
but they are highly correlated with NAS100 and this is recorded now as **weak
confirmation**, as it was in v1.

### Final — the NAS100 holdout, opened for at most ONE pattern

```
If exactly one pattern survives screen AND confirmation, it may be tested
once on 2021-2026, requiring net Sharpe >= 0.85.
If more than one survives, the one with the highest SCREEN Sharpe is
selected -- chosen by rank, not re-examined.
If none survives, the holdout STAYS SEALED.
```

## 6. Kill conditions

- **Zero patterns advance** → the family is rejected. No re-quantification of
  thresholds, no adding an eleventh pattern, no changing `H`.
- **A pattern advances but fails confirmation** → rejected. That is what the
  ~0.44 expected false positives look like, and it is the outcome the design
  anticipates.
- **More than four patterns advance** → treat with *more* suspicion, not
  less. Twenty correlated tests on one instrument producing five passes is a
  signature of a common factor or a bug, not five discoveries. Investigate
  before believing.

## 7. What this cannot establish

- Twenty tests on one instrument over one window. The screen alone is worth
  little; the design's power is entirely in the confirmation step.
- Bar patterns on a **dealer-priced CFD feed** are partly a property of the
  dealer's quote construction, not of the underlying market. An inside bar on
  OANDA's NAS100 need not be an inside bar on the CME future.
- Stop-entry fills are modelled conservatively but are still modelled. Real
  stop fills in a fast market are worse than `max(trigger, open)`.
- Volume-dependent pattern 3 rests on tick count.

---

```
FROZEN 2026-08-17, before any pattern was computed on this data.
```
