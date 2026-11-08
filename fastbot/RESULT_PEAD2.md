# RESULT — PEAD2: PEAD1 bought and sold in the closing auction. Net positive on the full sample (+0.62%, t 2.1), but not in recent years or in mid caps. FAIL.

```
SPEC:     PREREGISTRATION_PEAD2.md  sha c55ca77c…
METHOD:   singlestock/batch2_run.py pead2 (ss_events2.py cf4bfa27…); log data/run_pead2.log
RUN:      2026-10-03
VERDICT:  G1 PASS  G2 FAIL  G3 FAIL  G5 FAIL  -> FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
G1  net +0.62% (t 2.11), gross +0.94%, mean cost 0.32% (25% of EDGE + commission)    PASS
G2  2005-12 +0.55%  2013-19 +0.35%  2020-26 +1.00%   2018-26 +0.64% (t 1.22)             FAIL
G3  M -0.16%   S +1.07% (t 3.05)                                                        FAIL
G5  calendar-time Sharpe 2018+ +0.42                                                   FAIL
cost sensitivity: 0% +0.90% (t 3.0, 2018+ t 1.8)   50% +0.34%   100% -0.21%
```
- As predicted, only the cost assumption separates a pass from a fail. Even at zero auction cost, 2018+ reaches only t 1.8.
- The plain EAR signal is too weak to trade on its own. Mid caps carry no drift.
