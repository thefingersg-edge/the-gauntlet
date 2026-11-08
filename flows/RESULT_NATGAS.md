# RESULT — FLOWS-6: natural gas on EIA storage days. DEAD, and the sign is REVERSED.

```
SPEC:     PREREGISTRATION_NATGAS.md (sha 74674683…)
METHOD:   natgas.py   log data/natgas_run.log   result data/natgas_result.json
DATA:     NATGAS_USD M15 bid+ask 2005-01-03 .. 2026-08-31 (465,220 bars, grid OK);
          eia_events.csv 9f208aac… (898 report weeks; 895 report days with bars)
RUN:      2026-09-27, once, in the Cowork VM
VERDICT:  G1 FAIL  G2 FAIL  G3 FAIL  G4 FAIL  G5 PASS  ->  DEAD
```

*Measurement, not a recommendation. Not financial advice.*

## The registered test

| | estimate | t | gate |
|---|---|---|---|
| report-day excess b (18:00 ET the evening before → 17:00 ET) | **−41.8 bp** | **−3.38** | G1 FAIL (registered b > 0) |
| by era | E1 −63.5, E2 −14.6, E3 −47.3 | −2.69 / −0.88 / −2.03 | G2 FAIL |
| long on report days, ask in / bid out | −53.9 bp | −4.83 | G3 FAIL |
| placebo, the Wednesday before | +11.1 bp | +0.96 | G4 FAIL* |

*G4 fails only on its second condition (b_placebo < b), which assumed a
positive b. The placebo itself is not significant. K4's intent, "a general
mid-week effect", did not fire.

## Read it plainly

- **The paper's premium is not there. The opposite is.** On OANDA's natgas
  CFD, report days lose about 42 bp relative to other days, and have done so
  in all three eras (Benjamini-Hochberg q 0.001). Weekday means over the
  retained weeks: Mon +22, Tue +14, Wed +11, **Thu −32**, Fri −6 bp.
- **About three-quarters of it comes before 10:30 ET** (−23 bp from the
  previous evening to the release, −9 bp after). That is consistent with the
  paper's "half the move is before the release", with the opposite sign.
- **This is a finding, not a trade.** The registered hypothesis was long.
  Shorting report days is a new hypothesis that has now been seen, so it is
  post-hoc. Checked descriptively: short at the bid, cover at the ask, it
  makes +54 bp in E1, **−19 bp in E2 and −8 bp in E3**. See the data note.
- **The roll check is clean.** The largest intraday bar gaps cluster at
  14:30/15:30 UTC, which is 10:30 ET, the report itself. They are not roll
  artefacts inside the window.

## Data note that matters

**OANDA's natgas history has bid = ask on every bar from 2005 to 2011, and
92% of bars in 2012.** Spreads appear from 2013. So E1 costs are zero by
construction. Every E1 net figure here, including the short's +54 bp, is
gross in disguise. The quoted round-trip spread on report days was 24.6 bp
in E2 and **43.7 bp in E3**. A negative drift of 35–47 bp a day does not
survive that. The mid-price result (the sign reversal) is unaffected.

## What this closes

Long natural gas on EIA days on the OANDA CFD: dead. A short-Thursday
pre-registration is possible, but only on forward data. At current spreads
it needs a drift of more than 44 bp a day just to break even, which is about
the full-sample average. Recommendation: do not pursue it on this vehicle.
