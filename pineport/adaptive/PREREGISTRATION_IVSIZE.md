# Pre-registration — sizing off implied volatility instead of trailing realised

Written **before any result was looked at**, 2026-08-27, and held to
`../GAUNTLET.md`.

## The claim, and the reason it might work

Volatility targeting needs a **forecast** of the coming period's volatility. The
rule that has survived everything in this project uses 60-day trailing realised
volatility as that forecast. The VRP study measured implied volatility
forecasting next month's realised volatility with ρ ≈ +0.4 **beyond** what
trailing realised already says, on all four markets that have a volatility
index. A better forecast of the denominator should produce exposure closer to
the target. That is the entire purpose of the rule.

Direction is held fixed at `sign(A)` — the unfitted grid-agreement rule from the
agreement study — so the only thing varying is the size.

```
position = sign(A) x clip( target / vol_forecast , 0, 3 )
    RV rule : vol_forecast = 60-day trailing realised vol
    IV rule : vol_forecast = implied vol, causally rescaled (below)
    blend   : vol_forecast = the average of the two
```

## Gate 1.4 — the scale problem, handled in advance

Implied volatility sits systematically **above** realised volatility; that gap
*is* the premium. Feeding it in raw would give the IV rule permanently smaller
positions, and the comparison would measure average exposure rather than
timing. So implied vol is rescaled by an **expanding** (therefore causal) ratio
of mean realised to mean implied, computed only from data before each bar. The
two rules then carry the same average exposure by construction and differ only
in *when* they lean.

## The primary claim is calibration, not return — stated before running

A better volatility forecast implies **better-calibrated exposure**. It does
*not* imply a higher Sharpe; those are different claims, and only the first
follows from the mechanism. Under GAUNTLET 0.3 they are separated now so that a
failure on one cannot be re-described afterwards as a success on the other.

| | claim | why it is the primary |
|---|---|---|
| **PRIMARY** | realised volatility of the sized position sits closer to target, and varies less around it | follows directly from the mechanism; ~240 monthly observations per market, so adequately powered |
| **SECONDARY** | Sharpe of the sized trend rule improves | does *not* follow from the mechanism, and is **underpowered** — see below |

## What this test cannot establish, stated up front

Only four markets have a volatility index: S&P 500, gold, Brent, EURUSD. Under
GAUNTLET 3.2 their effective sample size is roughly **two**, not four. A
"3 of 4" result on *returns* is therefore weak evidence whatever it shows, and
will be reported as such rather than as a finding. The calibration claim is
better placed: it is measured on ~240 non-overlapping monthly volatility
observations per market, where the quantity is far less noisy than returns.

**This test can establish that implied vol is the better sizing input. It cannot
establish that doing so makes money.**

## Gates

| # | criterion | threshold |
|---|---|---|
| 1 | mean \|realised block vol − target\| lower for the IV rule | ≥ **3 of 4** markets |
| 2 | dispersion of realised block vol around target lower for the IV rule | ≥ **3 of 4** markets |
| 3 | both hold in **all three eras** | 3 of 3 |
| 4 | beats a **destroyed-timing null** — implied vol lagged 750 days, same distribution, wrong timing (GAUNTLET 3.5) | pooled and ≥ 3 of 4 |
| 5 | **plateau** across the rescaling window and the leverage cap (GAUNTLET 3.6) | plateau, not spike |
| 6 | survives **5bp** costs (GAUNTLET 4.1) | yes |
| 7 | **shared-term check** (GAUNTLET 1.1): realised vol appears in the RV rule's forecast *and* in the metric. The IV rule must still win when calibration is scored against a forward realised vol computed on a **non-overlapping** window that shares no bars with either forecast | must survive |

Gate 7 is the one the VRP study bought at full price. Realised volatility is on
both sides of this comparison and the arrangement has to be checked before the
number is believed.

## What failure looks like

The blend beating both means implied vol *adds* information rather than
replacing realised vol — a weaker and more honest claim, and it gets reported as
that. The destroyed-timing null matching the real rule means the exposure
profile is doing the work, not the forecast. Either is a rejection of the claim
as stated.
