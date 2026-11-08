# PREREGISTRATION — LIFECYCLE1: does a "retire broken systems" rule beat chance?

```
STATUS:   frozen before any LIFECYCLE1 number is computed (sha in PROVENANCE.md). The harness is frozen separately before its one run.
WRITTEN:  2026-10-12 (Dave: "pre register all of them so we can start pulling data")
ORIGIN:   ANALYSIS_WHAT_CHANGED_2026-10-12.md. Unger says he retires broken strategies rather than patching them; on the published DAX system a
          30-trade kill rule would have fired in Feb 2017. Question: is that a real skill (spotting broken systems) or only the trivial benefit
          of switching off losers?
DATA:     no new data. Every system is regenerated from frozen fastbot harnesses (list below).
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## The library (fixed now; 48 systems, all from frozen code)

| source (frozen harness) | systems | unit |
|---|---|---|
| PROBE1 / PROBE1-OIL (probe1_run.py, probe1_oil.py): daily probe, trend direction, net | 6 markets | day |
| UNGER batch MULTI1 (unger_batch.py): S1 / S2 / S3 on SPX, NAS, UK100, XAU, WTI, Brent | 18 | day |
| UNGER batch GOLDTREND1 A/B/C + CONTEXT1 F1–F6 (unger_batch.py) | 9 | day |
| UNGER2 (unger2_run.py): A DAX; B gold CFD and futures; C crude CFD and futures; D crude k = 0/5/10/20/40 CFD and futures | 15 | trade |

Trade-unit systems use net bp per trade; day-unit systems use daily net return. Days with no position count as 0.

## The rule (fixed)
- **Split:** each system's history is split in half by time. The first half is its "backtest", the second half its "live" period.
- **Reference band:** the 5th percentile of 20,000 bootstrap means of N units drawn from the backtest half (seed 0).
  - N = 30 trades for trade systems; N = 60 days for daily systems.
- **Kill:** in the live half, a system is **retired permanently** at the first unit where the rolling N-unit live mean falls below its band. After that its live return is 0.
- **Placebo:** each system is retired at a **random** time instead. The retirement rate matches the rule's: the same share of systems is retired, with random dates in the live half. 1,000 draws, seed 0.

## Measure
- For each system, the improvement is ( live total with rule − live total without ) ÷ ( backtest unit SD × √n_live ). That puts every system on the same scale.
- The same is computed under the placebo; each system's placebo value is the average over the draws.

## Gates (all must pass)
- **G1:** the mean improvement across the 48 systems is > 0, with t ≥ 2.0 (cross-sectional).
- **G2 (the real question):** the paired difference (rule − placebo) across systems has mean > 0 with t ≥ 2.0. The rule must beat random retirement, not just beat keeping losers.
- **G3:** among systems whose live half was positive, the rule retires a smaller share than the placebo does (fewer false kills).

## Reported (no gates)
- the kill rate, and the median time to kill;
- the same with N = 50 / 120 and a drawdown rule (live drawdown > the backtest's worst);
- the systems the rule retired that later recovered.

## Prediction
- **G1 PASS, trivially:** most systems in the library lose, so switching anything off helps.
- **G2 is the honest test, and borderline.** With mostly zero-edge systems, a performance rule mostly reacts to noise.
