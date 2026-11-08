# PREREGISTRATION PEAD4: what drives PEAD3, the SUE confirmation or the later entry?

Frozen 2026-10-03. Harness: `singlestock/pead4_run.py`, which pins this file. Main window: entries from 2005-01, exits by **2023-06-30**. Later entries are reported only.

**Honest status:** the full-sample PEAD3 numbers, including a post-hoc "not confirmed" line, are already known. The sealed window is **not** clean for the PEAD family, because PEAD3 used it. This test splits the mechanism. It does not newly confirm the edge, which only the forward record can do.

I am not a financial adviser. This is a measurement, not a recommendation.

## Events
- **Base:** PEAD1 long signals (top-decile EAR, M+S), matched to the first 10-Q/10-K filing 0–60 days after the 8-K (as PEAD3).
- **Groups:** **confirmed** (SUE ≥ trailing 70th percentile) and **not confirmed**.

## Hypotheses (two, so t ≥ 2.24; SEs clustered by quarter)
- **H4a, SUE adds:**
  - Both groups are entered at the open after the filing, held 60 days, net of the full EDGE cost.
  - Pass: confirmed minus not-confirmed mean net > 0, t ≥ 2.24, positive in each era (2005–12, 2013–17, 2018–23H1).
- **H4b, waiting avoids a dead period:**
  - The excess return (over the band) from the PEAD1 entry (open of k+2) to the close of the filing day, for all matched events.
  - Pass: mean < 0 with t ≤ −2.24. That would mean early buyers carry a losing stretch that the later entry skips.

## Reported
- Each group's net.
- The early-window mean by group.
- Entries after 2023-06 (not clean).

## Prediction
H4a PASS (Brandt et al.). H4b FAIL (no strong negative stretch expected).

## One run.
