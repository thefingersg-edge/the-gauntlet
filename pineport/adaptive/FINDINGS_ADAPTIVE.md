# Adaptive lookbacks and chart shapes — measured

Run 2026-08-27 against `PREREGISTRATION_ADAPTIVE.md`, written first.
Eleven markets, OANDA H1 resampled to UTC daily, 2005-01 → 2026-08
(~5,500–6,800 days each). Signal at bar close, position held from the next
bar, 1bp per unit turnover. Reproduce with `python3 a1_persistence.py`,
`a2_predictability.py`, `a3_adaptive_vs_fixed.py`, `a4_retrain.py`,
`b1_shapes.py`, `verify.py`.

**Both ideas fail their pre-registered criteria. The way they fail is the
useful part, and one of the failures directly contradicts the premise that
started this — that a shifting market means the model needs retraining.**

---

## A1 — the optimal lookback is not persistent. It mildly anti-persists.

For every calendar block, the realised return of all 26 `(fast, slow)` SMA
crossover pairs; `s* = log2(slow*)` of the winner.

| block | median ρ(s*ₜ , s*ₜ₋₁) | positive in | chase-winner Sharpe | fixed centre pair | chase-**loser** |
|---|---|---|---|---|---|
| month | **−0.078** | 0/11 | −0.125 | +0.128 | +0.050 |
| quarter | **−0.061** | 4/11 | −0.015 | +0.133 | +0.068 |
| year | **−0.162** | 3/11 | +0.058 | +0.125 | +0.051 |

Pre-registered pass was ρ ≥ +0.20 in ≥8 of 11. **Observed: negative.**
Trading last block's best pair beat a single fixed pair in 1/11, 2/11 and 3/11
markets. At monthly and quarterly blocks, deliberately trading last block's
**worst** pair did better than trading its best.

Smoothing the target (top-5 centroid instead of the argmax) raises the
quarterly ρ to +0.017 — still nil — and lifts the returns, which is what
reducing estimator noise does, not what finding a signal does.

**Reading:** the parameter you would adapt *towards* is not there next
period. Every downstream adaptation question inherits this.

---

## A2 — no state variable predicts next quarter's best speed

Target: the FAST-minus-SLOW block return spread, i.e. "should the crossover
be quicker or slower over the coming quarter". Predictors stamped on the last
bar of the prior quarter.

| state variable | pooled ρ, E1 | E2 | E3 | sign-consistent across eras |
|---|---|---|---|---|
| efficiency ratio | −0.136 | −0.017 | +0.024 | 2/11 |
| realised vol | −0.045 | +0.128 | −0.069 | 3/11 |
| variance ratio | −0.043 | −0.046 | +0.012 | 1/11 |
| Hurst | −0.050 | +0.008 | +0.014 | 1/11 |
| ADX | −0.117 | −0.005 | +0.018 | 2/11 |
| dominant cycle | +0.022 | −0.002 | −0.043 | 4/11 |
| autocorrelation(1) | +0.050 | −0.007 | +0.030 | 1/11 |

Pre-registered pass was |ρ| ≥ 0.15, same sign in all three eras, in ≥7 of 11
markets. **Best observed: 4/11.** Under a null, sign-consistency across three
eras happens 25% of the time by chance — 2.75 of 11 — so 4/11 is barely above
noise and the pooled ρ values are all inside ±0.14.

The tercile view says the same thing in units of money: sorting quarters by
any of these state variables moves the fast-minus-slow spread by well under
one percent of quarterly return, and the sign flips between eras in 8 of 9
variables.

---

## A3 — published adaptive moving averages lose to a fixed one

Same rule family throughout: `position = sign(close − VMA)`, where the VMA is
an EMA whose lookback varies. Equal-weight 11-market portfolio Sharpe.

| rule | portfolio | 2005–12 | 2012–19 | 2019–26 |
|---|---|---|---|---|
| **fixed L=160** | **+0.276** | +0.391 | +0.006 | +0.338 |
| fixed L=320 | +0.244 | +0.299 | +0.060 | +0.321 |
| cycle-scaled ×4 | +0.192 | +0.258 | −0.088 | +0.318 |
| vol-scaled (any γ) | +0.026 … +0.104 | | | |
| **KAMA (all settings)** | **−0.286 … −0.248** | −0.504 … −0.430 | −0.130 … −0.023 | −0.230 … −0.158 |

Nothing adaptive beat the best fixed lookback. Kaufman's KAMA — the canonical
"speed up when the market is efficient" rule — was the worst family in the
table, negative in every configuration and in every era.

**And the decisive control:** every adaptive rule has an *average* lookback.
Compare each against the fixed rule at that same average:

| | |
|---|---|
| adaptive variants tested | 15 |
| **above the fixed curve at matched average lookback** | **1** |
| KAMA at mean lookback 154 | −0.248 vs fixed +0.263 |

Whatever these rules earn is explained by how slow they are on average. The
adaptation itself subtracts about half a Sharpe point in KAMA's case. The
vol-scaled family peaks at γ = 0 — which *is* the fixed rule.

---

## A4 — the retraining result, and it is the opposite of the premise

Pick the best pair over a trailing window, trade it for the next M bars,
repeat. Strictly out of sample. Equal-weight 11-market portfolio.

| selection | portfolio Sharpe | 2005–12 | 2012–19 | 2019–26 |
|---|---|---|---|---|
| **never retrain** (one fixed pair) | +0.228 | +0.475 | −0.339 | +0.347 |
| **never retrain** (equal-weight all 26 pairs) | +0.217 | +0.348 | −0.094 | +0.267 |
| **expanding window**, re-pick yearly | **+0.245** | +0.159 | +0.319 | +0.329 |
| trailing 252d, re-pick quarterly | +0.083 | +0.163 | −0.115 | +0.128 |
| trailing 63d, re-pick monthly | +0.045 | −0.004 | +0.038 | +0.111 |
| trailing 1008d, re-pick yearly | −0.150 | −0.142 | +0.016 | −0.287 |

Paired per-market differences against never-retraining (this cancels the
common market factor):

| scheme | mean Δ Sharpe | SE | t |
|---|---|---|---|
| expanding window | −0.012 | 0.048 | −0.24 |
| trailing 252d / 63d hold | −0.096 | 0.044 | −2.18 |
| trailing 63d / 21d hold | −0.121 | 0.031 | **−3.86** |
| trailing 1008d / 252d hold | −0.182 | 0.046 | **−3.96** |

**Using all the history you have is statistically indistinguishable from
never retraining. Throwing history away to fit "the current regime" costs
0.10–0.18 Sharpe, consistently, in 9 of 11 markets.**

The one thing re-selection did buy was era-consistency: the expanding-window
scheme is the only row positive in all three eras, where the single fixed pair
lost 0.34 in 2012–19. That is not adaptation — it is the selector drifting
towards the middle of the grid, which is where the equal-weight-everything row
already sits.

---

## B — chart shapes

Causal detector: swing pivots confirmed k bars late, trendlines fitted through
the last three confirmed pivots each side, recorded when the gap between them
has closed by ≥30% over ≥20 bars. 3,448 detections across 11 markets, ~1,100
per era, so sample size is not the problem.

### B1 stability — FAIL, on the one parameter that matters

| perturbation | detections retained |
|---|---|
| swing pivot window 3 → 2 | **41%** |
| swing pivot window 3 → 4 | **49%** |
| convergence threshold 0.7 → 0.6 | 84% |
| convergence threshold 0.7 → 0.8 | 90% |
| pattern lookback 120 → 90 / 150 | 100% / 99% |

Gate was 80%. Changing what counts as a swing high by one bar keeps fewer than
half the patterns — **worse than the 61% cross-vendor trade reproducibility
that this project already treats as disqualifying**. The fragile axis is
exactly the subjective one: where the pivots are.

### B3 direction — FAIL, and worse than being long

| signal | n | 2005–12 | 2012–19 | 2019–26 | all | t |
|---|---|---|---|---|---|---|
| textbook pattern direction | 3,448 | +0.0026 | −0.0028 | +0.0009 | **+0.0002** | +0.18 |
| trade the breakout direction | 1,983 | +0.0023 | −0.0011 | −0.0012 | **−0.0000** | −0.02 |

Unconditional 21-day return over the same data: **+0.0052**. Signing a trade
by the wedge is worse than holding the thing.

### B4 magnitude — FAIL, and it inverts

Wedge days are quiet days (21-day vol at detection is 0.97× unconditional, 0.93×
on gold), so the honest test compares each detection against non-detection
days in the same market, same era and same volatility decile.

| | pattern | vol-matched control | |
|---|---|---|---|
| volatility over the next 21 days ÷ volatility now | 1.09 | 1.20 | **lower in 11/11 markets** |
| \|21-day move\| ÷ vol going in | 0.87 | 1.06 | **ratio 0.845, below 1 in 10/11** |

The compression is real — the detector fires in genuinely quiet markets. What
follows it is *less* expansion than a quiet market normally produces.
A converging-trendline pattern is, on this evidence, a marker that the quiet
will persist. That is the opposite of what the pattern is taught to mean, and
it is the only part of B that is consistent across all eleven markets.

---

## Verification

- **Lookahead audit.** Delaying every position one extra bar *raises* Sharpe
  (gold +0.223 → +0.271, S&P +0.196 → +0.232). Edges that live in the fill bar
  fall apart under this; these do not, so the execution model is not leaking.
- **Detector sanity.** Confirmed the shape detector fires in quiet markets
  before concluding anything about what follows — otherwise B4 would have been
  measuring nothing.
- **Noise.** Sharpe measured over 21 years has a standard error near 0.22, so
  single-cell comparisons in A3/A4 are not individually significant. The claims
  above rest on paired per-market differences and on the consistency of the
  pattern across the whole family, not on any one number.

## Caveats that a fair reader would raise

- **Eleven markets is not eleven independent observations.** Five are USD FX
  pairs and two are equity indices. The paired t-statistics overstate their
  significance; the sign counts (9/11, 10/11, 11/11) are the more honest form.
- **One rule family.** Everything in A is a moving-average crossover or
  price-versus-MA. A different signal type could in principle have a persistent
  optimal parameter; this does not test that.
- **Daily bars only.** The adaptive question was not re-run intraday — though
  this project has already measured intraday gold as the worse place to look.
- **One detector.** B tests pivot-and-trendline geometry, which is how a human
  reads a wedge. Motif-based approaches (matrix profile, shapelets) encode
  shape without pivots and are untested here.
- **Costs at 1bp.** A3 and A4 were not re-run at 5bp. Higher costs would
  penalise the faster and more frequently re-selected variants, which are
  already the losers — so this cuts against adaptation, not for it.
- **The vol-matched control matches on level, not on path.** A pattern that
  requires three orderly pivots selects for non-explosive price paths by
  construction, and some of B4's result may be that selection rather than
  information.

## What this changes

1. **Stop treating parameter drift as the problem.** The measurement says the
   optimum does not persist, is not predictable, and that chasing it costs
   money. The retrain treadmill is not fixing a real shift; it is fitting noise
   and paying for the privilege.
2. **Diversify across the grid instead of selecting within it.** Equal-weighting
   all 26 crossover pairs, with no fitting whatsoever, returned +0.217 — within
   noise of the best selection scheme tested and beating every trailing-window
   one. That is free robustness and it needs no retraining schedule.
3. **If something is going to adapt, make it size, not speed.** This is the
   third independent result in this project pointing the same way: fourteen
   directional signals failed, the stop-loss plateau held, volatility targeting
   held. Speed is a directional parameter. Size is not.
4. **The one candidate this generates.** The spread of agreement *across* the
   parameter grid — how many of the 26 pairs point the same way — is a
   continuous number available every day, needs no fitting, and is a sizing
   input rather than a selection input. It has not been tested. It is the
   natural next thing, and it should go through the same gauntlet.
5. **Chart shapes are not a directional edge here.** If they are used at all,
   the measured content is "the quiet is likely to persist", which is a
   volatility and position-sizing input. Anything built on them must first
   survive the pivot-definition perturbation, which the textbook detector does
   not.
