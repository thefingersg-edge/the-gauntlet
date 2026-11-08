# RESULT — ORBCORE1 and LIFECYCLE1: the DAX core doesn't travel, and a simple "retire it" rule fires on noise

```
SPECS:    PREREGISTRATION_ORBCORE1.md (sha 66c0aca9…), PREREGISTRATION_LIFECYCLE1.md (sha 74ca3c9f…), both frozen 2026-10-12 before any number
METHOD:   scripts/orbcore1_run.py (sha 75dfd732…, one logged mechanical fix for AU200's empty range), scripts/lifecycle1_run.py (sha 149e787a…)
RUN:      2026-10-12, once each.   LOGS: data/orbcore1/run_orbcore1.log, data/lifecycle1/run_lifecycle1.log
VERDICTS: ORBCORE1 FAIL (G1, G2, G3; only G4 passes).   LIFECYCLE1 FAIL (G1, G2, G3).
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## ORBCORE1: the bare opening-range core on 7 markets not used before
| market | trades | net bp/trade (t) | gross |
|---|---|---|---|
| EU50 | 1,098 | −4.32 (−1.51) | +1.14 |
| UK100 | 1,355 | −1.95 (−0.88) | +0.04 |
| SPX500 | 2,306 | +0.38 (+0.23) | +2.84 |
| **NAS100** | 2,937 | **+3.93 (+2.26)** | +5.92 |
| US30 | 2,542 | +0.53 (+0.36) | +1.69 |
| JP225 | 1,203 | −1.90 (−0.82) | +3.19 |
| AU200 | 0 | not testable: OANDA's AU200 only quotes from 09:50 Sydney | — |
| **POOLED** | 11,441 | **+0.36 (t 0.34)** | +2.92 |

- **Eras:** +1.5 / −1.7 / +1.6. Markets positive: 3 of 7. It beats the random-direction placebo (−2.6) only because random entries pay the spread for nothing.
- **Read it plainly:**
  - **The DAX core does not travel.** On the other European indices it loses (EU50 −4.3, UK100 −2.0).
  - **NAS100 is the only market that shows anything** (+3.9 bp, t 2.3). That is one market of six, so it is not significant once the multiple tests are counted, and it is a lead at most.
  - **The Unger stop and the wide stop change little** (pooled +0.5 / +0.2 bp).
- **The DAX forward record has started regardless** (pre-registered; first day 2026-10-13). It is the only way to know whether DAX's post-2016 +8 bp gross is real.

## LIFECYCLE1: does "retire broken systems" beat chance?
- The rule (rolling 30-trade / 60-day live mean below the 5th percentile of the backtest) **retired 45 of 48 systems.** It retired 20 of the 21 systems whose live half was *profitable*.
- **G1:** the improvement vs keeping everything was +0.012 (t 0.10). **G2:** vs random retirement at the same rate it was −0.018 (t −0.28). **G3:** it killed profitable systems as often as random retirement did (95% vs 94%).
- **The other rules we reported were worse:**
  - N = 50 trades / 120 days: −0.076 vs placebo (t −1.31);
  - the drawdown rule ("live drawdown worse than the backtest's worst"): −0.149 vs placebo (**t −2.24, worse than random**).
- **Why: it is a multiple-looks problem.**
  - A 5% band checked every day for ~2,700 live days is almost certain to be breached at least once by noise alone. The median kill came after 283 units.
  - "25 false alarms" means 25 systems retired that went on to be profitable: crude carry/trend, NAS mean reversion, and the UNGER2 crude systems on futures.
  - A monitor with a fixed 5% trigger is not a skill; it is a coin that eventually lands tails.
- **What would be needed:**
  - a sequential test calibrated for repeated looks (CUSUM, or a band set so that a *good* system has, say, a 5% chance of being retired over its whole life, not per check);
  - a rule that compares the live edge with zero, not with the backtest's tail.
  - That would be a new pre-registration. Until then, the INCUBATOR shows the flag as **warning only**, which its spec already required.

## What this does to the plan
- **Unger's "retire broken systems" process is not something a simple rule reproduces.** Whatever judgement he applies, a mechanical 5% trigger performs no better than chance on our library, and the drawdown rule performs worse.
- That leaves FUTPORT1 (trend + carry on 29 futures) as the main open line, waiting on Dave's Databento cost check, plus the forward records.
