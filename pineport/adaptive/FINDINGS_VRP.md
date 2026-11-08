# The variance risk premium — rejected on direction, and the sizing result was arithmetic

Run 2026-08-27 against `PREREGISTRATION_VRP.md`, written first. Implied-vol
series from FRED, lagged one business day. Reproduce with `python3 e1_vrp.py`
and `python3 e2_verify_vrp.py`.

---

## Direction — 0 of 5 gates

| # | criterion | observed | |
|---|---|---|---|
| 1 | predicted sign on ≥ 3/4 pairs, grid-stable | 3/4 at 21d but **grid-stable on 1/4** | ✗ |
| 2 | sign stable in ≥ 80% of sampling grids | **54–72%** on seven of twelve cells | ✗ |
| 3 | era stability on VIX/SPX | **+0.162 / −0.021 / −0.055** | ✗ |
| 4 | **VRP beats the implied-vol level alone** | **0 of 4** at 21d and 63d | ✗ |
| 5 | own vol index beats VIX on that instrument | **VIX wins on gold** | ✗ |

**Gate 4 is the one that matters.** The level of implied volatility predicts
forward returns better than the premium does, on every pair:

| | VRP | IV level |
|---|---|---|
| VIX → S&P, 63d | +0.063 | **+0.198** |
| OVX → Brent, 126d | +0.035 | **+0.174** |
| EVZ → EURUSD, 126d | −0.030 | **+0.193** |

Subtracting realised volatility *destroys* information rather than isolating a
premium. Whatever weak signal is there is "buy when people are frightened" — a
much older and much less interesting claim than the variance risk premium, and
one that gate 3 then kills anyway: on VIX/S&P the whole effect sits in
2005–2012 and has been absent since.

Gate 5 says the same thing from another angle. VIX predicts **gold** better
than gold's own volatility index does (+0.156 against +0.035 at a quarter).
There is one global risk factor in these numbers, not four instrument-specific
premiums.

---

## The sizing result, and why it was withdrawn

`PREREGISTRATION_VRP.md` stated the sizing question in advance so that a
direction failure could not be re-described as a sizing success. On first
measurement it looked like the strongest thing in the whole project:

| VRP → \|forward return\| ÷ realised vol | 21 days | grid-stable |
|---|---|---|
| S&P 500 | +0.239 | 100% |
| gold | +0.247 | 100% |
| Brent | +0.211 | 100% |
| EURUSD | +0.174 | 100% |

**It is arithmetic.** `VRP = IV − RV`, and the target divides by `RV`. A low
realised vol raises the numerator's predictor and shrinks the denominator, so a
positive correlation follows without any information changing hands. Two checks
confirm it:

| | VRP → \|move\|÷RV | **RV alone → the same target** | VRP → \|move\|÷**IV** |
|---|---|---|---|
| S&P 500 | +0.239 | **−0.209** | −0.051 |
| gold | +0.247 | **−0.318** | +0.057 |
| Brent | +0.211 | **−0.214** | +0.000 |
| EURUSD | +0.174 | **−0.151** | −0.039 |

Realised volatility alone produces the mirror image, and normalising the target
by *implied* vol instead — which takes RV out of it — collapses the result to
nothing, and turns it negative at six months (gold −0.129, Brent −0.150,
EURUSD −0.188).

**Withdrawn.** It was the most impressive number produced in this project and it
was a shared term in two formulas.

---

## What is actually there, asked properly

The honest question is not whether the premium predicts returns but whether the
option market knows something about **volatility** that the price history does
not. Correlation with forward realised volatility, 21 days:

| | RV (persistence) | IV | **IV controlling for RV** |
|---|---|---|---|
| S&P 500 | +0.566 | +0.677 | **+0.457** |
| gold | +0.554 | +0.653 | **+0.424** |
| Brent | +0.591 | +0.684 | **+0.431** |
| EURUSD | +0.696 | +0.717 | **+0.391** |

Implied volatility forecasts next month's realised volatility, and it adds
**ρ ≈ +0.4 beyond what trailing realised vol already says**, on all four
markets. The effect decays with horizon — +0.08 to +0.22 at a quarter, and
nothing at six months for gold and Brent.

(`VRP | RV` and `IV | RV` come out nearly identical, which is not a coincidence:
holding RV fixed, `VRP = IV − RV` is a linear function of IV. Once you control
for realised vol the two are the same test.)

This is textbook — implied vol containing information beyond historical vol is
one of the oldest results in options research. It is worth having here for one
reason only, and it is the next candidate.

---

## The next candidate, stated but not run

The one rule that has survived everything in this project sizes positions by
**60-day trailing realised volatility**. This study says implied volatility is a
materially better forecast of next month's realised volatility than trailing
realised is. So:

> Does sizing the vol-target rule off **implied** volatility instead of
> trailing realised volatility improve it?

It connects the one thing that works to the one informative non-price series,
it is a *sizing* use rather than a directional one, and it has a stated reason
to work that does not reference a backtest. It needs its own pre-registration
before it is run.

**One practical limit:** only four of the eleven markets have a volatility
index. Any implied-vol sizing rule covers S&P, gold, Brent and the euro, and
nothing else — so it can improve part of a portfolio, not the whole of it.

---

## Data problems found in the fetch, worth fixing before the next run

- **BAMLH0A0HYM2 came back with 787 observations starting 2023-08.** The FRED
  graph endpoint truncates that series without an explicit start date. Add
  `&cosd=1996-01-01` to the URL in `fetch_fred.py` (or a `--start` flag) and
  re-pull. The credit-spread candidate is **untested**, not tested badly.
- **EVZCLS is discontinued** — it ends 2025-03-11. Seventeen years is still
  usable; it will not extend.
- **VXNCLS (Nasdaq) was not in the fetch** and is missing.
- **OVX is built on USO, a WTI product, and was used against Brent.** Close, but
  not the same instrument; a caveat on that row.
