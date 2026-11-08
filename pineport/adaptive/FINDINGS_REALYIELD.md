# Real yields at 3–12 months — the gold claim fails, something else survives

Run 2026-08-27 against `PREREGISTRATION_REALYIELD.md`, written first. DFII10
via the project's own `fetch_fred.load_daily_series`, one-business-day
publication lag, joined to eleven daily market series 2006–2026. Reproduce with
`python3 d1_realyield.py` and `python3 d2_verify_realyield.py`.

---

## Verdict: 1 of 5 criteria, and the one that passes is for the wrong markets

| # | pre-registered criterion | observed | |
|---|---|---|---|
| 1 | sign map matched ≥ 7/9 **including USDJPY flipping** | 7/9 at 63d, but **USDJPY does not flip** (−0.038) | ✗ |
| 2 | gold's predicted sign holds in all three eras | **+0.046 / +0.000 / −0.074** | ✗ |
| 3 | \|ρ\| ≥ 0.20 on gold at some horizon | **max 0.087** | ✗ |
| 4 | survives on non-overlapping windows | the non-overlapping result was **grid-dependent** — see below | ✗ |
| 5 | not merely a dollar proxy | equities survive partialling the dollar out | ✓ |

**The core claim — gold responds to real yields once you test it at the right
horizon — is rejected.** ρ of −0.037 at a quarter, 70% sign-stable, sign
flipping across eras. The horizon was not the problem.

---

## The trap this test was built to avoid, and it was real

Using the **level** of the real yield rather than its change gives, on gold:

| horizon | 63d | 126d | 252d |
|---|---|---|---|
| ρ(real yield level, forward gold return) | **+0.293** | **+0.484** | **+0.635** |

Large, monotone in horizon, and **the opposite sign to the mechanism** — high
real yields predicting *higher* gold. That is not a discovery, it is one
twenty-year swing: real yields were high in 2006–08 before gold's run, and deeply
negative in 2020–22 while gold went sideways. The level is close to a unit root,
so twenty years is close to a single observation. Anyone testing this the
obvious way gets a confident, backwards number with ρ = 0.64 attached.

Silver does the same (+0.589) and USDJPY comes out −0.378 against a predicted
positive. Sign map matched 1–2 of 9 on the level. Rejected as pre-registered.

## The sampling grid mattered more than the signal

A non-overlapping sample at a 252-day horizon has ~24 points, and it has to
start somewhere. Re-running every possible start:

| horizon | range of ρ across all grid starts | sign stability |
|---|---|---|
| 63 days | ±0.2 typical | 60–100% |
| 126 days | ±0.35 typical | 52–94% |
| **252 days** | **−0.51 to +0.53** | **51–69%** |

The first pass produced AUDUSD at −0.472 and USDJPY at +0.212 on one grid.
Averaged over all 252 starts those become −0.010 and −0.047. **Both were
artefacts of where the sample happened to begin** — the same class of error as
the 4H bar-alignment finding already in this project, and the reason criterion 4
exists. Sign-map matches fall from 7/9 to 4/9 at 252 days once it is removed.

---

## What did survive

At a **63-day** horizon, averaged over all 63 grid starts, a rise in the real
yield over the prior quarter predicts lower returns over the next one — and it
holds in every era, in exactly the markets discount-rate logic points at:

| market | 2005–12 | 2012–19 | 2019–26 | all | sign-stable across grid starts |
|---|---|---|---|---|---|
| **NAS100** | −0.238 | −0.000 | −0.233 | **−0.182** | **100%** |
| **Brent** | −0.256 | −0.142 | −0.163 | **−0.192** | **100%** |
| **S&P 500** | −0.185 | −0.077 | −0.183 | **−0.155** | **100%** |
| **Copper** | −0.166 | −0.096 | −0.102 | **−0.133** | **100%** |
| DAX | −0.096 | −0.037 | −0.113 | −0.098 | 98% |
| gold | +0.046 | +0.000 | −0.074 | −0.037 | 70% |
| silver | −0.007 | +0.016 | −0.080 | −0.052 | 73% |

And it is not the dollar wearing a hat. Partialling a synthetic dollar (built
from the four USD pairs on disk) out of the equity correlations barely moves
them:

| | raw 63d | partial | raw 126d | partial | raw 252d | partial |
|---|---|---|---|---|---|---|
| S&P 500 | −0.113 | −0.107 | −0.242 | −0.208 | −0.418 | −0.398 |
| NAS100 | −0.106 | −0.099 | −0.180 | −0.138 | −0.226 | −0.190 |

**This is the first non-price signal in this project to survive era
consistency and a robustness check at the same time.** Two things stop that
being exciting:

- **ρ ≈ −0.16 is not a strategy.** With ~99 non-overlapping quarters that is
  about t = −1.6 on its own. What carries it is the sign holding across three
  eras, five markets and every sampling grid — a coherent pattern, not a
  significant single number.
- **Nobody needs telling that rising real yields are bad for equities.** It is
  in every textbook. The open question is not whether it is true but whether it
  adds anything to a trend rule that already knows the price went down. That is
  the next test, and it has not been run.

Note also that Brent and copper were listed as **"no prediction"** in the
pre-registration — growth and discount-rate effects offset, so no sign was
committed. They came out among the strongest. That is a genuine result but it
is not a confirmed prediction, and it should be scored as the former.

---

## Where this leaves it

1. **Gold's real-yield story does not survive measurement here.** It is the
   most-repeated explanation of gold in financial media, and on twenty years of
   daily data the relationship at 3–12 months is nil, era-unstable, and
   backwards in level form. The 2022-onward decoupling is widely discussed;
   this measures it rather than arguing about it.
2. **The one live thread is the discount-rate channel on equities**, and the
   test that matters next is incremental: does `Δ real yield` add anything to a
   trend rule on the indices, or is it already in the price? Pre-register that
   before running it — the honest prior is that it is already in the price.
3. **The sampling-grid check should be standard from now on.** It changed the
   headline number by more than any other single decision in this study, and it
   costs one loop.
