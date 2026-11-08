# PREREGISTRATION — CARRY2: carry done properly, three designs that cannot sit short a market that keeps climbing

```
STATUS:   frozen before any CARRY2 number is computed (sha in PROVENANCE.md). The harness is frozen separately before its one run.
WRITTEN:  2026-10-12 (Dave: "is there a better way of designing it? How do we protect against a constant climb?")
ORIGIN:   FUTPORT1 time-series carry = sign(F1/F2 - 1): Sharpe -1.20, short gold/silver for 14 years (metals sit in contango by construction).
          The published premium (Koijen, Moskowitz, Pedersen & Vrugt, "Carry", JFE 2018) is mainly CROSS-SECTIONAL: long high carry, short low
          carry, within an asset class, so a market that is always in contango is only short RELATIVE to others.
DATA:     on disk: data/futport1 (29 roots, c.0/c.1, 2010-06 -> 2026-09, sha-verified). No new pull.
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## Common construction
- **Carry, annualised:** C = (c0/c1 − 1) / τ, positive = backwardation.
  - τ = the median gap between consecutive c.0 contract changes over the trailing 2 years, in years. It is estimated from past rolls only, with a minimum of 2 rolls.
  - Recomputed at each Friday close and held for the next week.
- **Returns, σ, costs, roll handling, weekend stubs, the c.0/c.1 join, sleeve scaling to 10% and the 3× cap** are all as FUTPORT1 (scripts/futport1_run.py).
- **Classes:** equity (4), rates (4), FX (6), metals (4), energy (4), and **ags** = grains + livestock (7).

## The three designs (each its own sleeve, judged separately; Bonferroni over 3, so one-sided Sharpe × √years ≥ 2.13)
| | design | why it can't get stuck short a climbing market |
|---|---|---|
| **A: cross-sectional** | within each class, rank markets by C. Weight = (rank − mean rank), scaled so the long and short legs each total 1, × 0.10/σ. Classes are equal-weighted. | it is long the *least* contango'd metal against the *most*. A market that is always in contango is only short when it is the worst of its class |
| **B: demeaned time-series** | signal = sign(C − its own trailing 252-day mean of C); weight = signal × 0.10/σ | a market's normal contango is subtracted out. Only *unusual* carry for that market counts, so gold's permanent contango reads as neutral |
| **C: carry + trend agreement** | position = sign(C) × 0.10/σ only when sign(C) equals FUTPORT1's trend signal sign; otherwise 0 | a carry short against a rising market is vetoed by the trend |

## Gates per design (all must pass)
- **G1:** net Sharpe × √years ≥ 2.13 over the live period (the same start as FUTPORT1, 2012-05).
- **G2:** net positive in each era: 2010–15, 2016–20, 2021–26.
- **G3:** a 50/50 combination with the FUTPORT1 trend sleeve has a higher Sharpe than the trend sleeve alone (+0.44). The point of carry is to diversify trend.

## Reported (no gates)
- each class's Sharpe within design A;
- turnover;
- the correlation with the trend sleeve and with ES;
- the worst drawdown;
- the gold and silver positions over time: does each design still end up net short the 2019–2026 metals rally?

## Prediction
- **A:** Sharpe 0.2–0.5. The literature is stronger, but our universe is CME-only and FX carry had a poor 2010s.
- **B and C:** weaker (0–0.3). G3 is most likely to pass for A.
