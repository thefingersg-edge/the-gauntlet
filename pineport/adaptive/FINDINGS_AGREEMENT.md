# Grid agreement as a sizing input — rejected, 7 gates of 7

Run 2026-08-27 against `PREREGISTRATION_AGREEMENT.md`, written first. Same
eleven markets, same daily data, same execution model. Reproduce with
`python3 c1_agreement.py` and `python3 c2_verify_agreement.py`.

`A_t` = mean of `sign(SMA_fast − SMA_slow)` over the 26 fixed pairs. Nothing
fitted. The claim was that |A| — how much the lookbacks agree — is worth
something as an exposure multiplier.

---

## The verdict

| # | pre-registered criterion | threshold | observed | |
|---|---|---|---|---|
| 1 | pooled Sharpe beats the best fixed pair | > +0.228 | **+0.220** | ✗ |
| 2 | beats the fixed centre pair per market | ≥ 7/11 | **4/11** | ✗ |
| 3 | positive in all three eras | 3/3 | **E2 −0.089** | ✗ |
| 4 | beats the shuffled-magnitude null | ≥ 7/11 | **6/11** | ✗ |
| 5 | beats `sign(A)` at full size | > +0.267 | **+0.220** | ✗ |
| 6 | plateau across the sizing exponent γ | plateau | **monotone decline** | ✗ |
| 7 | survives 5bp | > fixed at 5bp | **+0.121 vs +0.202** | ✗ |

**Criterion 5 is the one that settles it.** Using only the *sign* of the grid
agreement, at full size, returns +0.267. Sizing by its magnitude returns
+0.220. The information is entirely in which way the lookbacks lean, not in how
strongly.

The exponent sweep says the same thing without ambiguity — Sharpe falls
monotonically as the sizing gets more aggressive, with the maximum sitting on
the boundary at γ = 0, which *is* the control:

| γ in `sign(A)·\|A\|^γ` | 0 (sign only) | 0.5 | 1.0 | 1.5 | 2.0 |
|---|---|---|---|---|---|
| portfolio Sharpe | **+0.267** | +0.234 | +0.220 | +0.212 | +0.208 |
| average exposure | 0.97 | 0.74 | 0.61 | 0.53 | 0.47 |

That is a SPIKE-at-the-null shape, and `sweep.py`'s rule applies: reject.
Threshold gates (`|A| ≥ θ`) fail the same way — best at θ = 0.4 with +0.242,
still below the sign-only control, and falling from there.

Paired per-market: `agree_linear − agree_sign_only` = **−0.025, SE 0.030,
t = −0.84, 4 of 11**. Not merely unproven. Absent, and slightly negative.

---

## What the run found instead, and how much to believe it

The rule that survived the same table is **direction from the grid's sign,
size from inverse volatility** — both of them already-established effects
rather than new ones.

| pooled, 11 markets, 1bp | Sharpe | 2005–12 | 2012–19 | 2019–26 |
|---|---|---|---|---|
| single fixed pair (16/128) | +0.228 | +0.475 | −0.339 | +0.347 |
| `sign(A)` — average the lookbacks | +0.267 | +0.412 | −0.097 | +0.350 |
| shuffled-timing volatility scale (null) | +0.252 | +0.498 | −0.090 | +0.280 |
| **`sign(A)` × inverse-vol sizing** | **+0.382** | **+0.493** | **+0.135** | **+0.489** |

Four things make this credible rather than another fit:

- **It adds where it should.** `voltgt − sign_only` = +0.059, SE 0.023,
  **t = +2.59, 9 of 11 markets**.
- **The null lands where it should.** Applying the *same distribution* of
  leverage with the timing destroyed (a 750-day lag) gives +0.252 — right on
  top of the un-targeted rule at +0.267, and negative in 2012–19 exactly like
  it. The timing is what pays, not the exposure profile. Against the real rule
  the null loses in 9 of 11, though at t = +1.71 this is the weakest of the
  four checks.
- **It is a plateau, not a spike.** Across all twenty combinations of
  volatility window (20–250 days) and target (5–20%), the pooled Sharpe spans
  **+0.343 to +0.382**. No isolated peak. The 60-day window is best at every
  target — independently reproducing the 60d-beats-20d result this project
  already found on gold alone.
- **It tolerates implementation lag.** Delaying the volatility scale by 1, 2 or
  5 days gives +0.390, +0.398, +0.383. The only component that decays is the
  direction (+0.382 → +0.295 at one day), which is ordinary signal decay in a
  daily trend rule, not a timing artefact.

**And none of it is a discovery.** This is the published volatility-managed-
portfolio effect reproducing at the expected size, which is the point: a known
effect showing up where it should, measured on eleven markets rather than one.

---

## The comparison that stops it being a success

| pooled, 11 markets, 1bp | Sharpe | ann return | ann vol | max DD |
|---|---|---|---|---|
| **buy and hold the basket** | **+0.571** | **+5.89%** | 11.11% | −38.5% |
| vol-targeted buy and hold | +0.481 | +2.72% | 5.95% | −19.8% |
| `sign(A)` × inverse-vol sizing | +0.382 | +1.81% | 5.03% | −12.9% |

Doing nothing beats it, on Sharpe and on return. The trend rule delivers under
a third of the return at two thirds the risk-adjusted quality. What it does buy
is drawdown — −12.9% against −38.5% — so it is a risk case, not a return case,
and that is exactly the position the RSI Boll Squeeze ended in.

(The basket's own buy-and-hold number deserves a caveat: four of the eleven are
USD FX pairs held long, which have no expected drift, so most of the +5.89%
comes from gold, silver and the two equity indices over a period that suited
all four.)

---

## One post-hoc observation, explicitly not a result

Dropping the short leg — long when the grid agrees up, flat otherwise, sized by
inverse volatility — returns Sharpe **+0.574** at **−9.4%** maximum drawdown,
matching buy-and-hold's risk-adjusted return with a quarter of the drawdown,
and positive in all three eras.

**This was found after looking at the table. It is a hypothesis, not a
finding.** It has not been pre-registered, its short-leg removal is exactly the
kind of choice that a rising sample rewards for free, and it has been fitted to
the same eleven markets as everything above. If it is worth anything it will
survive its own pre-registration on markets or a period not used here. Until
then it goes in the candidate list, not the results.

---

## Where this leaves the programme

1. **The candidate list is now empty again**, and that is the process working.
   Fifteen things tested across these two studies; the survivors are a bug fix,
   a diversification effect, and a sizing rule that was already published.
2. **Every surviving result is about size.** Not one directional test has
   passed in this project. The evidence for "manage exposure, don't predict
   direction" is now four independent measurements deep.
3. **The next candidate has to come from outside price.** Everything tested so
   far is a transformation of the same OHLC series, and the transformations have
   stopped producing anything. The DESIGN_BRIEF's own list — real yields at a
   3–12 month horizon, central bank purchases, futures basis and roll yield —
   is where a candidate with a non-backtest reason to work still exists.
