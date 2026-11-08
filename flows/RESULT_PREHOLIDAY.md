# RESULT — FLOWS-10: the day before a US market holiday. DEAD (K1), narrowly.

```
SPEC:     PREREGISTRATION_PREHOLIDAY.md (sha b6aa1c2f…); calendar 0a9d89b3… (200 pre-holiday days)
METHOD:   preholiday.py   log data/preholiday_run.log   result data/preholiday_result.json
RUN:      2026-10-01, once
VERDICT:  G1 FAIL  G2 PASS  G3 PASS  G4 PASS  G5 PASS  ->  DEAD (K1)
```

*Measurement, not a recommendation. Not financial advice.*

| | result | gate |
|---|---|---|
| pre-holiday excess, SPX500 (Friday controlled) | **+9.37 bp, t 1.45** | G1 FAIL (needs t ≥ 2) |
| by era | +6.3 / +3.2 / **+17.9** (t 2.1) | G2 PASS |
| trade, ask open → bid close | +10.7 bp, t 1.70; E3 +21.1 | G3 PASS |
| placebo, the day before | −1.2 bp, t −0.2 | G4 PASS |

## Read it plainly

- **It fails on its primary gate, so it is dead as registered.** The rule
  stands even though the other four gates pass. The plan stated that t = 2
  needed about 16 bp, and the estimate is 9.4 bp.
- **It points the right way everywhere.** NAS100 +10.9, US30 +5.5 and DE30
  +13.4 bp; NASDAQ 1971–2004 **+15.0 bp, t 2.35** (n 299). It is also the
  first old calendar effect in this programme to be *largest* in the most
  recent era (+17.9 bp since 2019).
- **One day distorts it.** 2018-12-04, the day before the Bush mourning
  closure, fell 315 bp. Dropping one day after seeing it would be
  post-hoc, so it stays in.
- **What it leaves.** About 9 pre-holiday days a year makes a forward
  confirmation take decades. Under rule 2 it is not re-tested with another
  window. This is the closest miss of the batch.
