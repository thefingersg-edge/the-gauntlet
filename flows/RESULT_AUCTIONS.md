# RESULT — FLOWS-11: Treasury auctions. The concession is real and alive; the CFD spread eats it. DEAD (K3).

```
SPEC:     PREREGISTRATION_AUCTIONS.md (sha 1c200ebf…); auction_events.csv d1bfd601… (1,013 auction days)
METHOD:   auctions.py   log data/auctions_run.log   result data/auctions_result.json
RUN:      2026-10-01, once
VERDICT:  G1 PASS  G2 PASS  G3 PASS  G4 FAIL  G5 PASS  ->  DEAD (K3)
```

*Measurement, not a recommendation. Not financial advice.*

| | result | gate |
|---|---|---|
| R = post − pre, USB10Y price, 3 h either side of the close | **+2.91 bp, t 4.34** (n 1,000) | G1 PASS |
| by era | +5.16 / +1.53 / **+2.71 (t 2.8)** | G2 PASS: E3 is 93% of full |
| shape | pre −1.86, post +1.05 bp | G3 PASS |
| trade: short into the auction, long after, at bid/ask | **−0.13 bp**, t −0.2; E3 −1.69 | G4 FAIL |
| placebo, non-auction weekdays | −0.26 bp, t −0.7 | G5 PASS |

## Read it plainly

- **This is the first effect in the flows programme that has not decayed.**
  The 2019–26 era carries almost the full-sample size. That fits the
  mechanism: deficits keep auctions growing, and dealers must still absorb
  them. It also fits SR1188, which found the effect smaller since 2015 but
  still there.
- **It fails only on cost.** Two round trips on the bond CFD cost about
  3 bp, which is what the edge is.
- **The 30-year is larger:** +6.6 bp, t 4.8 (descriptive). The 10-year sector
  (8–11y tenors) is +5.7 bp. Over several days, the price falls 5.5 bp over
  the five days before an auction and recovers 5.3 bp over the five after
  (overlapping, descriptive). That is Lou, Yan & Zhang's pattern.
- **Note:** 72 auctions had no published close time and used 13:00, the
  standard. 23 listed 11:30.

## What it leaves

This is the strongest case in the programme for **cheaper execution**.
Treasury futures (ZN, ZB) cost a fraction of a CFD round trip, and a
one-tick ZN spread is about 1.5 bp of price. A futures test of this
concession would be a **new pre-registration**, written before any futures
data is read. It belongs next to FLOWS-15.
