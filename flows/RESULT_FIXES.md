# RESULT — FLOWS-8: the dollar around the Tokyo and London fixes. DEAD (K2, K3).

```
SPEC:     PREREGISTRATION_FIXES.md (sha 9d075e40…)
METHOD:   fixes.py   log data/fixes_run.log   result data/fixes_result.json
DATA:     9 USD pairs, OANDA M15 bid/ask 2005-01 .. 2026-08 (5,622 days, all 9 pairs on every day)
RUN:      2026-10-01, once
VERDICT:  G1 PASS  G2 FAIL  G3 PASS  G4 FAIL  G5 PASS  ->  DEAD
```

*Measurement, not a recommendation. Not financial advice.*

| | result | gate |
|---|---|---|
| mean daily R (dollar up before the fix minus after, both fixes, 9-pair basket) | **+2.20 bp, t 4.90** | G1 PASS |
| by era | E1 **+4.57** (t 4.9), E2 +1.63 (t 2.6), **E3 +0.37** (t 0.5) | G2 FAIL (E3 is 17% of full) |
| Tokyo / London | Tokyo +1.55 (t 7.1), London +0.65 (t 1.8) | G3 PASS |
| trade, four spread crossings a fix | **−11.3 bp a day** (t −25) | G4 FAIL |

## Read it plainly

- **Krohn, Mueller & Whelan's W-shape replicates on OANDA data.** The dollar
  rises into the fixes and gives it back afterwards. Tokyo is the stronger
  of the two, at t 7.1.
- **It has decayed like everything else.** It was +4.6 bp a day in 2005–12
  and +0.4 bp since 2019, which is not significant. The paper's data runs to
  about 2020, so this is the same shape again: published, then gone.
- **It was never tradable on CFDs.** Even at full size the pattern is a
  couple of bp a day, and the round trips cost about 11 bp.
- **Descriptive:** the ECB 14:15 CET reference rate shows the same pattern
  (+0.8 bp, t 2.2). **On month-end days the London fix reverses** (−3.9 bp,
  against +0.9 on other days). That is the hedge-rebalancing flow, which
  FLOWS-1 also found and also saw decay.
