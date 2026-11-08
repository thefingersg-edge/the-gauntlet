# RESULT — PROBE1-OIL: Unger's "crude trends" holds for WTI. Brent's character is unstable, and neither pays after costs out of sample

```
SPEC:     PREREGISTRATION_PROBE1.md (sha 1320a760…) + PREREGISTRATION_UNGER_BATCH.md §1 (sha ce14205e…, clean-day rule)
METHOD:   scripts/probe1_oil.py (mechanical wrapper around the frozen probe1_run.py; sha in PROVENANCE)
DATA:     OANDA WTICO_USD and BCO_USD 15m bid/ask, pulled 2026-10-10, 2005 -> 2026-09-25
RUN:      2026-10-10       LOG: data/probe1/run_probe1_oil.log
VERDICT:  Q1  WTI TREND (stable), Brent UNSTABLE      Q2  0 of 2 PASS
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## Q1 — character (gross, no costs)
```
market   gross bp/day   t       Sharpe   2005-12   2013-19   2020-26   character
WTI      +7.55          +2.50   +0.50    +5.80     +5.94     +11.30    TREND (stable)
Brent    +4.27          +1.53   +0.31    +3.20     -2.04     +12.04    unstable (2013-19 negative)
```
- **WTI trends in every era.** That matches Unger's published claim that crude trends.
- **Brent is weaker:** it mean-reverted from 2013 to 2019.
- **The trend is lumpy.** The big years carry it: 2009 (+84%), 2020 (+98%) and 2026 so far (+47%). In several years it lost (2008 −48%, 2012 −18%).

## Q2 — chosen on 2005–15, traded 2016–26, after costs
```
market   chosen   gross   - spread  - financing  = net bp/day   t       Sharpe   buy & hold Sharpe (net)
WTI      TREND    +8.30   -2.87     -1.00        +4.43          +0.94   +0.26    +0.31
Brent    TREND    +6.99   -2.65     -0.99        +3.34          +0.80   +0.22    +0.31
```
**0 of 2 pass.** Both stay positive after costs, but they are far too noisy to clear t ≥ 2.5. Neither beats simply holding oil.

## The probe's verdict across all six markets so far
| market | character | stable? |
|---|---|---|
| Gold | trend (t 3.9) | yes |
| WTI | trend (t 2.5) | yes |
| Brent | trend-leaning | no |
| SPX | weakly mean-reverting | no |
| NAS100 | flipped after 2013 | no |
| UK100 | flips | no |

Unger's split, **commodities trend and indices don't**, is confirmed on our data. But the raw probe doesn't pay anywhere after costs out of sample.

## Next (already pre-registered in the UNGER batch)
GOLDTREND1 tests slower, cheaper trend rules on gold. On the same evidence, WTI is the obvious second candidate, but the batch names gold only. Adding WTI needs its own short pre-registration.
