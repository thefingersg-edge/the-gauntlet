# RESULT — INSIDER1: clusters of insider buying. Small gross effect (+1.2%) that the spread on these small stocks (1.3%) takes completely. FAIL.

```
SPEC:     PREREGISTRATION_INSIDER1.md  sha 9a3c50c5…
METHOD:   singlestock/batch2_run.py insider1 (ss_events2.py cf4bfa27…); log data/run_insider1.log
RUN:      2026-10-03
VERDICT:  G1 FAIL  G2 FAIL  G3 FAIL  G5 FAIL  -> FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
G1  net -0.14% (t -0.38, n 10,344), gross +1.19%, cost 1.33%
G2  2008-12 +0.45%  2013-19 -0.55%  2020-26 -0.17%   2018-26 -0.18%
G3  M -0.87%   S +0.19%
G5  calendar-time Sharpe 2018+ +0.03
reported: L band -0.55%; closing auction 25% cost +0.30% (t 0.8); 20-day -0.43%; single-insider buys gross +0.89%, net -0.26%
```
- Insider buying does carry a small positive drift. But it happens in thinly traded stocks, where the spread is larger than the drift.
