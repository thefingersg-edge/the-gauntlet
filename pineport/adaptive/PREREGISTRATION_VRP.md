# Pre-registration — the variance risk premium

Written **before any result was looked at**, 2026-08-27. Same eras, same
execution conventions, same daily market data. Implied-vol series pulled from
FRED into `adaptive/macro/` and lagged one business day by
`fetch_fred.load_daily_series`, exactly as the real-yield study did.

## Data actually in hand, and two problems with it

| series | obs | span | note |
|---|---|---|---|
| VIXCLS | 9,260 | 1990-01 → 2026-08 | S&P 500 |
| GVZCLS | 4,589 | 2008-06 → 2026-08 | gold (GLD options) |
| OVXCLS | 4,857 | 2007-05 → 2026-08 | crude (USO options) — **WTI, used against Brent** |
| EVZCLS | 4,360 | 2007-11 → **2025-03** | euro — **discontinued, ends March 2025** |
| BAMLH0A0HYM2 | 787 | **2023-08** → 2026-08 | **truncated — unusable as fetched** |
| NFCI | 2,903 | 1971-01 → 2026-08 | weekly |
| DTWEXBGS, T10YIE | | | control regressors |

VXNCLS (Nasdaq) was not in the fetch and is absent. The high-yield spread came
back with three years instead of thirty — the FRED graph endpoint truncates that
series without an explicit `&cosd=` start date — so the credit candidate is
**not tested here** rather than tested badly.

## The claim

Implied volatility usually exceeds subsequently realised volatility: option
sellers charge an insurance premium. The published claim (Bollerslev, Tauchen
and Zhou and successors) is that the size of that premium predicts forward
returns positively — it is compensation for bearing variance risk, and it is
largest when risk aversion is high.

    VRP_t = IV_t  -  RV21_t          both known at t
    RV21  = 21-day realised volatility, annualised

The mechanism does not reference a backtest: someone is paying a premium, and
the premium is observable.

## Sign map, written first

| implied-vol series | instrument | predicted sign of ρ(VRP, forward return) |
|---|---|---|
| VIXCLS | SPX500 | **positive** |
| GVZCLS | XAUUSD | **positive** |
| OVXCLS | BCOUSD | **positive** (WTI premium against Brent returns) |
| EVZCLS | EURUSD | **positive** |

## Gates

| # | criterion | threshold |
|---|---|---|
| 1 | VRP → forward return, predicted sign | ≥ **3 of 4** matched pairs, at ≥ one horizon |
| 2 | sampling-grid robustness (now standing) | sign stable in ≥ **80%** of grid starts |
| 3 | era stability on the longest series (VIX/SPX, 2005→) | predicted sign in **all three eras** |
| 4 | **VRP beats the implied-vol level alone** | larger \|ρ\| on ≥ 3 of 4 pairs |
| 5 | **the instrument's own vol index beats VIX on that instrument** | ≥ 3 of 4 |

Gate 4 is what separates a variance *premium* from a fear gauge: if the level of
implied vol does the same work, subtracting realised vol has added nothing and
the finding is "buy when people are frightened", which is a different and much
older claim.

Gate 5 is the discriminator. If VIX predicts gold as well as GVZ does, there is
one global risk factor here, not an instrument-specific premium. That would
still be a real result — but it is not this one, and it gets reported as such.

## Stated in advance so it cannot be claimed afterwards

VRP is also tested against forward **|return| ÷ prior volatility** — the sizing
question rather than the direction one. It is written down now precisely so that
a failure on direction cannot be re-described later as a success on sizing. They
are different claims and only the first is the published one.

## Horizons

21, 63 and 126 trading days, on non-overlapping windows, with the correlation
re-computed at every possible start of the sampling grid and averaged — the
check that changed the answer in the real-yield study.
