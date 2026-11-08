# RESULT — PEAD5: holding the EAR long for 120 days. FAIL. Longer holds help small caps only; mid caps lose.

```
SPEC:     PREREGISTRATION_PEAD5.md  sha 6f84fda8…
METHOD:   singlestock/pead5_run.py; entry k+2, 120 trading days, full EDGE cost; main window to 2023-06-30; log data/run_pead5.log
RUN:      2026-10-03
VERDICT:  G1 FAIL   G2 PASS   G3 FAIL   -> FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
G1 120d net +0.74% (t +1.56, n 20,248); gross +1.87%                         FAIL
G2 eras +0.12% (t 0.20) / +1.75% (t 1.85) / +0.67% (t 0.70)                  PASS
G3 M -0.58% (t -1.02)   S +1.49% (t +2.74)                                    FAIL
reported: 90 days net +0.23% (t 0.58); 180 days net +0.94% (t 1.66)
reported (not clean): entries after 2023-06, 120d net +2.60% (t 2.40, n 3,433)
```
## Read it plainly
- A longer hold on its own is not enough: +0.74% net is not significant across all M and S signals.
- **Small caps carry it** (+1.49%, t 2.7). Mid caps lose after cost. The PEAD4 "late entry" lead is therefore mostly a small-cap effect plus the SUE selection, not a pure holding-period effect.
- The most recent years are again the strongest (+2.6% after 2023-06), which the PEAD3 forward record will test.
- No new search: the forward record (FORWARD_PEAD3, from 2026-10-05) already flags the S band and the late-entry group, so both are tracked without another fitted test.
