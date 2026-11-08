# RESULT — STRAT1: a 20-slot book combining EAR, SUE and insider triggers, with the market overlay. It slightly beats its benchmark's Sharpe long-only, with deeper drawdowns. The hedged version is too weak. FAIL.

```
SPEC:     PREREGISTRATION_STRAT1.md  sha e1f3bddd…
METHOD:   singlestock/batch2_run.py strat1 (strat1_engine.py 9b8dccf1…, ss_events2.py cf4bfa27…); log data/run_strat1.log
RUN:      2026-10-03
VERDICT:  G1 FAIL  G2 FAIL  G3 FAIL  -> FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
signals (M+S, 2008-03+): 47,812  -- INS 10,200  EAR+SUE 2,433  EAR 20,394  SUE 14,785;  average 16.9 of 20 slots held
G1  hedged Sharpe 2008-26 +0.35, 2018-26 +0.65 (CAGR +3.1%, max DD -35.5%)                          FAIL (needs >= 0.5 in both)
G2  long-only 2008-26 Sharpe +0.54 vs benchmark +0.51; max DD -59.7% vs -52.9%; CAGR +9.9% vs +9.2%
              2018-26 Sharpe +0.46 vs +0.42; max DD -59.7% vs -43.3%                                 FAIL (drawdown)
G3  hedged return by era: 2008-12 +4.8%  2013-19 -16.0%  2020-26 +98.8%                             FAIL
reported: 10 slots hedged +0.22 | 40 slots hedged +0.67 (2018+ +0.88), long-only +0.62 | no overlay hedged +0.01
          cost at 100% EDGE: hedged +0.05 | by trigger alone (hedged): INS +0.11, EAR+SUE +0.52, EAR +0.31, SUE +0.29
```
## Read it plainly
- **Mixing every trigger diluted the one that works.** 20 slots fill mostly with plain EAR and SUE signals (35,000 of 48,000). The EAR+SUE trigger that drives PEAD3 got only 2,433 of the candidate signals.
- **Twenty positions in small stocks fall harder than the small-cap index** (−60% against −43%). Concentration risk outweighs the edge.
- **The overlay helped:** hedged Sharpe 0.35 with it against 0.01 without.
- **The pre-registered forward record is not started on this design**, because it failed and a better-specified candidate exists (PEAD3). That is Dave's decision.
