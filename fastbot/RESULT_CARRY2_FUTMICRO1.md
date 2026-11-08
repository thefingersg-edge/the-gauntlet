# RESULT — CARRY2 and FUTMICRO1: carry still fails in every design we tried, and the micro-sized trend book loses its best markets

```
SPECS:    PREREGISTRATION_CARRY2.md (sha dddef328…), PREREGISTRATION_FUTMICRO1.md (sha ae167b33…), frozen 2026-10-12 before any number
METHOD:   scripts/carry2_run.py (sha 3213af62…), scripts/futmicro1_run.py (sha c09a3949…), both on futport1_run.py (frozen) and data/futport1
RUN:      2026-10-12, once each.   LOGS: data/futport1/run_carry2.log, run_futmicro1.log
VERDICTS: CARRY2 A FAIL, B FAIL, C FAIL.   FUTMICRO1 FAIL (G1, G2; holdability G3 passes).
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## CARRY2: three carry designs on 29 CME futures, 2012–2026
| design | Sharpe | eras 10–15 / 16–20 / 21–26 | adds to trend? (50/50 vs trend 0.44) | gold net short 2019–26 |
|---|---|---|---|---|
| A cross-sectional (Koijen et al.) | **−0.81** | −20% / −67% / −38% | no (−0.40) | 59% of days, tiny weight |
| B demeaned time-series | −0.32 | +9% / −29% / −12% | no (+0.09) | 54% |
| C carry only when trend agrees | +0.27 | +23% / −3% / +4% | no (+0.39), and it correlates +0.74 with trend | 22% |

- **The "constant climb" problem is fixed. Losing money is not.** All three designs stopped being structurally short gold: weights near zero, or short only a minority of days. The constant-climb fix worked.
- **They lost anyway.** Cross-sectional carry lost in every class except rates (+0.05) and ags (+0.08):
  - metals −1.09;
  - FX −0.39 (the 2010s high-carry currencies, AUD and CAD, fell);
  - equity −0.34;
  - energy −0.28.
- **Design C is nearly a copy of trend** (correlation +0.74), so it adds nothing.
- **A data caveat, written down rather than fixed:** we used *calendar* front and second contracts. For metals and some ags the calendar front is often a thin serial month with stale closes, which adds noise to the measured carry. The published studies use the most liquid contracts. That might explain part of the gap, but not a −0.8 Sharpe across most classes. A rebuild on liquid (volume-rolled) contracts would need a new pre-registration and a new pull.
- **Conclusion:** across four designs (FUTPORT1's plus these three), carry on this CME universe since 2010 does not pay. **The carry line is closed for this universe**, apart from the oil-only OILCARRY1 result (which used EIA data back to 1987), still on forward record.

## FUTMICRO1: can $50k hold the trend sleeve with micros?
| | Sharpe | eras | notes |
|---|---|---|---|
| 29-market trend sleeve (reference) | +0.44 | +14% / +15% / +19% | |
| **the 17 micro/mini markets, fractional** | **+0.18** | +15% / +10% / −0.5% | the best trend markets (livestock, soymeal, heating oil) have no small contract |
| $50k, whole contracts (PRIMARY) | −0.08 | +9% / −6% / −13% | correlation 0.83, vol 7.8%, margin fine: **holdable but not profitable** |
| $25k | +0.05 | | holds zero contracts in most markets most days |
| $100k | +0.14 | | correlation 0.95 |

- **The sleeve can be held at $50k:** it tracks well, volatility is in range and margin is fine. **But the markets small enough to trade are the ones where trend worked worst.** The edge lived in livestock, soymeal and heating oil, which have no micro contracts.
- **Trend's Sharpe 0.44 needs the full 29-market universe,** which means about a $1m account.

## Where this leaves the programme
- **Still alive:**
  - the 29-market trend sleeve (Sharpe 0.44, every era positive): forward record **FORWARD_TREND1**, descriptive for any account under ~$1m;
  - oil carry (OILIMP1, CFD route), forward;
  - IMB2, forward;
  - the DAX bare-core forward record;
  - GOLDRY1, forward.
- **Closed:**
  - CME carry in every design;
  - micro-account trend;
  - every short-interval signal tested so far.
