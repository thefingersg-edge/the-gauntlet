# RESULT — FLOWS-7: the low-VIX release-day premium, 1994–2004 holdout. NOT CONFIRMED.

```
SPEC:     PREREGISTRATION_LOWVIX.md (sha 03fbeac5…)
METHOD:   lowvix.py --holdout   log data/lowvix_holdout_run.log   result data/lowvix_holdout_result.json
DATA:     FRED NASDAQCOM daily close 1993-12 .. 2004-12 (2,793 closes, dd86f17f…);
          holdout_events.csv 09dfd680… (CPI 134, NFP 134, GDP 134, ISM 132, FOMC 89);
          stooq ^spx did not answer (HTML page, 0 rows) -- the secondary series was skipped, as registered
RUN:      2026-09-28, once, in the Cowork VM
VERDICT:  H1 FAIL  H2 PASS  H3 PASS  ->  NOT CONFIRMED.  Part F is not run.
```

*Measurement, not a recommendation. Not financial advice.*

## The registered test

| | estimate | t | gate |
|---|---|---|---|
| bL, release-day excess on LOW-VIX evenings, 232 days | **+15.13 bp** | **+1.32** | H1 FAIL (needs t ≥ 1.65) |
| size | +15.13 ≥ 5 bp | | H2 PASS |
| halves | 1994–99 +21.36 (t 1.44), 2000–04 +12.29 (t 0.75) | | H3 PASS |

## Read it plainly

- **The verdict is NOT CONFIRMED, and it is binding.** The lead is closed
  and the forward CFD test (Part F) does not start.
- **It failed on precision, not direction.** The holdout estimate is larger
  than the discovery estimate (+15.1 against +12.0 bp). It is positive in
  both halves and in all four release types (CPI +9, NFP +36, GDP +4, ISM
  +10). On the high-VIX side it is +4.2 bp (t 0.3). This is the outcome the
  pre-registration's power section warned about. NASDAQ in 1994–2004
  (dot-com, 2000–02) was so volatile that a true 10–15 bp effect had roughly
  a 40% chance of reaching t 1.65, and it did not.
- **What that means for the record.** This is not evidence *against* a
  release-day premium. Ai, Bansal & Guo document one over 1961–2023, and both
  samples here point the same way. It is a failure to confirm the
  **specific, found** low-VIX version to the standard set in advance. Under
  rule 2, it is not re-tested with a new window, index or threshold.

## What this closes

Lead A (FLOWS-4 post-hoc): closed, NOT CONFIRMED. Lead B (natgas Thursdays)
was parked in LEADS_POSTHOC.md. **Both leads are now finished.**
