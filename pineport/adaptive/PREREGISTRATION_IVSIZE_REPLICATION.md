# Pre-registration — replicating the implied-vol sizing result

Written **before the replication data exists**, 2026-08-27. Held to
`../GAUNTLET.md`, rule 5.1: a rejected candidate stays rejected, and an accepted
one is replicated where it was not fitted rather than extended.

## What is being replicated

`FINDINGS_IVSIZE.md`, primary claim only: **sizing a volatility target off
implied volatility calibrates exposure better than sizing it off 60-day trailing
realised volatility.** It passed on S&P 500, gold and Brent; it failed on
EURUSD.

The secondary claim (that this improves Sharpe) was not established and is **not
part of this replication.** It will not be re-tested and a favourable Sharpe
number appearing in the output is not a result.

## The rule is frozen

```
direction    sign(A), the unfitted 26-pair grid agreement
target       10% annualised
cap          3x
RV window    60 days
rescale      252-day expanding causal ratio
block        21 days, non-overlapping
```

**Any change to any of these invalidates the replication.** If a parameter needs
to move, that is a new candidate with a new pre-registration, not a replication.

## What this replication can and cannot do — measured, before running

The four tested markets have an effective sample size of **2.42**. Adding the
two markets a volatility index is available for:

| set | mean pairwise ρ | N_eff |
|---|---|---|
| tested: S&P, gold, Brent, EURUSD | +0.217 | **2.42** of 4 |
| + NAS100 | +0.271 | **2.40** of 5 |
| + NAS100 and silver | +0.302 | **2.39** of 6 |

**Adding both makes the effective sample smaller, not larger.** NAS100 is 0.927
correlated with the S&P; silver is 0.801 correlated with gold. They are not new
observations, they are the same two observations again.

The consequence, stated now so it cannot be spun later:

> **This replication can falsify the result. It cannot confirm it.**

A pass will be reported as *consistent with* the original and nothing more; the
evidence base does not grow. A failure is informative precisely because these
markets are near-duplicates of ones that passed — a rule that works on the S&P
and fails on the Nasdaq is not measuring what it claims to.

There is no free volatility index for a market uncorrelated with these. The
ceiling on this result is N_eff ≈ 2.4 and no available data lifts it. That is a
property of the claim, not a to-do item.

## Pairs, in order of what they are worth

| implied vol | instrument | have the instrument? | what a result means |
|---|---|---|---|
| **VXNCLS** | NAS100 | yes | ρ 0.927 with the S&P — pure falsification test |
| **VXSLVCLS** | XAGUSD | yes | ρ 0.801 with gold — same, and the series may be discontinued |
| RVXCLS | Russell 2000 | **no** — needs `US2000_USD` from OANDA | slightly more independent than NAS100 |
| VXDCLS | Dow | **no** — needs `US30_USD` | least useful, most correlated |

## Gates, fixed now

| # | criterion | threshold |
|---|---|---|
| 1 | dispersion of realised block vol around target lower for the IV rule | on **each** new pair independently |
| 2 | mean absolute bias lower for the IV rule | on **each** new pair |
| 3 | beats the destroyed-timing null (750-day lag) | on **each** new pair |
| 4 | gate 7 re-run: forecasts frozen at the block boundary, sharing no bars with the target | must survive on each new pair |
| 5 | holds in all three eras on each new pair | 3 of 3 |

Each pair is scored on its own. There is no "3 of 4" here — with two near-duplicate
markets, an aggregate threshold would let one carry the other.

## Stated interpretations, written in advance

- **NAS100 passes:** consistent with the S&P result. Report as such. N_eff unchanged.
- **NAS100 fails:** the S&P result is in doubt. A rule that calibrates a 0.927-correlated
  market worse than trailing realised vol does is not doing what the mechanism says.
  This would send F1 back to candidate status.
- **Silver passes, gold passed:** consistent. Nothing new.
- **Silver fails, gold passed:** the gold result is in doubt, same reasoning at ρ 0.801.
- **Either fails only in one era:** report the era, do not average it away.

## What would actually strengthen the original result

Not on the list above, and worth writing down so it is not confused with it: a
volatility index on something uncorrelated with equities and metals — rates
volatility being the obvious one. No free daily source is known. Until one
exists, F1 is a result about four markets that behave like two.
