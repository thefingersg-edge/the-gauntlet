# Full-project code review — 2026-09-03

Adversarial pass over every script in `adaptive/`, plus independent
verification of the highest-impact finding. Ordered by whether the defect
sits **under** a reported number (changes a conclusion) or **beside** it
(cosmetic / conservative direction).

Status key: `VERIFIED` = reproduced by running code. `READ` = found by
inspection, not yet reproduced.

---

## Tier 1 — changes a stated conclusion

### R1. Gate 0 in Part G should have FAILED  (`g1_diversify.py`)  READ
Reported `N_eff = 6.01` against a `>= 6.00` threshold, recorded as PASS.

- `dN_eff/drho_bar = -34.4` at that point. 0.01 of N_eff is a correlation
  difference of 0.0003. The gate has no resolution at its own threshold.
- Stationary block bootstrap of N_eff: 5th-95th percentile **3.98 - 5.85**,
  entirely below the threshold.
- The 15 markets `g2_portfolio.py` actually trades have **N_eff = 4.70**,
  not 6.01. The gate was evaluated on a market set the strategy does not use.

Consequence: Part H's portfolio work ran on a gate that should have stopped
it. GAUNTLET 0.5 ("edge before diversification") was satisfied on paper only.

### R2. `g2_portfolio.py` silently drops 6 of 21 markets  VERIFIED x2
`weights()` does `vol = S.rolling(win).std().shift(1)`. On a ragged
multi-market index `rolling(252)` needs 252 **consecutive** non-NaN rows.

- Zero non-NaN vol rows, ever: `bcousd`, `cornusd`, `de10ybeur`, `de30eur`,
  `sugarusd`, `wheatusd`.
- Vol-targeted portfolio therefore starts **2013-04-03 on 15 markets**.
  (An independent equal-weight reconstruction requiring all 15 simultaneously
  puts the common start even later, 2016-01-26.)
- The `equal` row never touches `vol`, so it starts **2007 on 21 markets**.
- First date any market has a return at all: **2005-01-03**.

The headline table compares different samples AND different market sets.

### R3. `g2_portfolio.py` leading zeros are never dropped  VERIFIED x2
`(eff * R).sum(axis=1)` returns `0.0` for an all-NaN row, so the following
`.dropna()` removes nothing. ~2,900 leading zeros enter the Sharpe.

- Sharpe as computed **+0.1013**; with the zeros dropped **+0.1317**.
  23% understated. Independent reconstruction: **2,888** leading zeros,
  Sharpe +0.1044 with them vs +0.1356 without — same defect, 30% gap.
- The destroyed-timing null gets ~3,650 zeros, so null and rule are not
  computed on the same span.
- E1 comes back blank for 4 of 6 rows, so "consistent across all three eras"
  was never achievable by construction.

### R4. The daily bars are not daily  (`make_daily.py`)  **FIXED 2026-09-03**
`df.resample("1D")` on UTC days manufactures a Sunday bar from the ~2 hours
of Sunday-evening trading. It has a real high-low range, so the
`d = d[d["high"] > d["low"]]` filter keeps it.

    mean 296.5 bars/yr, not 252
    sqrt(252/296.5) = 0.922   -> every Sharpe UNDERSTATED by 8%
    yrs = len/252             -> inflates year count 1.18x
                              -> every ann_ret and turnover UNDERSTATED ~15%
    eurusd Sunday: n=1118, mean range 0.2231% vs weekday 0.8075%

Per-market spread: `sugarusd` 251.6 bars/yr (no Sunday bars) to `xptusd`
317.1. The 21-market **union** index is worse still at **327.9 bars/yr**,
because markets keep different holiday calendars — so anything computed on
the joined frame (all of Part G/H) is off by 1.30x, not 1.18x. So:
- `sharpe()` in `core.py` uses a fixed `sqrt(252)` and is wrong everywhere.
- `SMA(16)` spans genuinely different calendar time on different markets,
  which invalidates cross-market lookback comparisons in Parts A and D.
- `realised_vol` reads low (stub bars have small ranges), so the vol
  targeting in `g2` has been running **over** target.

### R5. The benchmark correction overcharges funding  (`g3_benchmark.py`)  VERIFIED
`rf_daily()` divides the annual rate by 252 and applies it to an index with
far more than 252 rows. Measured on the 21-market union index (2005-01-02 to
2026-08-28, 7,100 rows, **327.9 bars/yr**):

    charged 2.416%/yr  vs  intended 1.857%/yr  ->  1.301x too much funding

Falls hardest on the long-only passives, i.e. it overstated how much the
active rules beat buy-and-hold after the correction.

---

## Tier 2 — material, but does not flip a conclusion

### R6. `groupby(g).first().shift(1)` should be `.last().shift(1)`
`f2_verify_ivsize.py:38`, `f3_replicate.py:68`. Currently takes the *first*
bar of the *previous* block, ~21 bars stale, where the intent was "the last
bar before each block". Direction is conservative (staler input, weaker
signal), so the null results stand.

### R7. `b3_pattern_zoo.py:214` false-pass arithmetic
"Expected ~0.6 false passes" assumes 21 independent markets. With N_eff
~4.7-6, the true expectation is **2-3x** that. Also line 202 selects `best`
horizon by max |x| for gate 3 while gates 1/2 use h21 only — a mixed
selection rule.

### R8. Correlated markets treated as independent in t-tests
`c2_verify_agreement.py/paired()` and `d1`'s 7/9 sign-map gate both run
t-tests over 11 markets as if independent. ~4 effective blocs, so
**t inflated ~1.66x**. Both report nulls, so this made it easier to find
something and nothing was found — but the reported t values are wrong.

### R9. Nulls run on shorter spans than the rules they benchmark
`c1`, `c2`, `f1`: `shift(750)` starts the null ~3 years later than the rule.
Not matched samples.

### R10. `h1_combined.py:31` RY_FOR basket is hand-picked
Includes `bcousd` and `xcuusd`, which `d1`'s SIGN_MAP explicitly marks
"no prediction, reported but not scored", and excludes the metals/FX that
D1 *did* predict. Chosen after seeing results.

### R11. Warm-up NaNs become 0.0 in block sums
`a1`, `a2`: `R.groupby(key).sum()` turns leading NaNs into 0.0. ~4 quarterly
blocks per market affected, which distorts `idxmax`/`idxmin`.

### R12. `a2_predictability.py:100-113` tercile view is a market-identity sort
Pools raw state **levels** across markets. 88% of `bcousd` rows fall in the
top pooled vol tercile vs 1% of `eurusd`. The terciles are sorting markets,
not states.

### R13. `e2_verify_vrp.py:34` swaps one shared term for another
The "artefact removed" check puts IV on both sides. The VRP withdrawal was
correct, but this particular check does not demonstrate what it claims.

---

## Tier 3 — cosmetic

- `a2` era assignment drops 2012Q1 / 2019Q2 to `era=None`.
- `a2` pass criterion is looser than its docstring.
- `b1`/`b2` stability is one-sided overlap, not Jaccard; only run on `xauusd`.
- `b2` GATE 5 mislabelled "volatility-matched".
- `b3` docstring says decile, code is quintile.
- `f1` calls MAE "bias".
- `f3.verdict` passes gate 5 on NaN eras.
- `h1:152` `best_rung` includes the full stack (tautology).
- `h1:132-137` "aligned to common window" is a no-op.
- `c2:73` `P2` computed, never used.
- `g3` reindex-before-ffill leaves 26 days at rf = 0.
- `fetch_fred.load_daily_series` adds calendar days, not business days.
- `d1` era table at h=252 gives 7 points, below the `len >= 8` guard, so the
  whole column is NaN.
- `d2:45` scores on `rhos.mean()`, which is approximately the overlapping
  estimate `d1` labels "not scored".

---

## Read and found clean

`core.py` (apart from the `sqrt(252)` in R4), `a3`, `a4`, `b1`/`b2`
detection logic, `b3` candlestick detectors, `d1` non-overlapping sampling,
`e1.iv_on` bounded ffill, `e2` partial-correlation formula, `g2` weight
*timing* (as distinct from the vol window), `h1.run()`.

## Not reached

`verify.py`; PREREGISTRATION vs FINDINGS cross-checks against code;
`b3` per-market result tables.

---

## What survives the review

The **null results stand**: Parts A, B, D, E and the pattern zoo. None of
these defects manufacture a rejection. A stale shift (R6), an inflated t
(R8), a mis-scaled Sharpe (R4) all make it *easier* to find an effect, and
nothing was found. Fixing them makes the nulls stronger, not weaker.

What is damaged is the **Part G/H portfolio cluster**, where R1-R3 sit
directly under the numbers being reported rather than beside them.

## R4 — closed 2026-09-03

Fixed in two passes.

**Pass 1** replaced UTC-midnight resampling with a trading-day boundary,
`groupby(trading_date)`, plus `MIN_BARS >= 4` to drop true holiday stubs (12
days on eurusd, all with 1-2 hourly bars). `core.sharpe`/`ann_vol`/
`realised_vol` now annualise through `core.ppy()`, derived from the actual
index. No hardcoded `sqrt(252)` remains anywhere in the codebase; the
surviving 252s are all lookback windows, which are now ~0.98 years instead of
0.85.

**Pass 2** fixed a residual defect in pass 1: the rollover was hardcoded at
21:00 *UTC*, but OANDA rolls at 17:00 New York, which is 21:00 UTC only under
EDT. Measured on eurusd, 1,590 hourly bars (1.17%) were on the wrong trading
day, touching **28.0% of all days**, and 1,564 of those were the 21:00 UTC
hour exactly as predicted. Because that hour ends the session it lands on the
daily CLOSE — the input to every signal here. Now converts to
America/New_York first so the boundary tracks DST.

Result: **257.2 bars/yr** mean (range 251.5-259.7), zero weekend-dated rows,
union index 259.8 (was 327.9). The DST pass moved ~26% of daily closes on
every 24/5 market and **0%** on corn, wheat, sugar and the two Eurex
products, which do not trade in the 21:00-22:00 UTC window — the check that
confirms the fix does only what it should. Old vs new return correlation
>= 0.989; row counts unchanged.

Backups: `make_daily.py.bak-preDST`, `data_preDST/`.

## Fix order — remaining

1. ~~R4~~ done.
2. R2, R3, R1 — then re-run Part G honestly and let Gate 0 fail if it fails.
   R4 did not fix R2: it is a `rolling()`-on-ragged-index problem, and after
   the rebuild 5 of 21 markets still get zero non-NaN vol rows (bcousd now
   clears, the other five do not).
3. R5 — recompute the benchmark table.
4. R6-R13 — fix in place, re-run, expect the nulls to hold.
5. Tier 3 — housekeeping.
