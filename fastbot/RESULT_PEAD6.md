> **VOID 2026-10-04 — look-ahead bug: trades whose 10-Q was filed on the 8-K day were bought before the EAR signal was complete. See RESULT_AUDIT_LOOKAHEAD.md (corrected: FAIL).**

# RESULT — PEAD6: PEAD3 in the closing auction at measured cost. FAIL (2005–12 and mid caps), but small caps since 2013 hold up.

```
SPEC:     PREREGISTRATION_PEAD6.md  sha 48272fdd…
METHOD:   singlestock/pead6_run.py; same 7,762 M+S events as PEAD3; cost = M 0.11 / S 0.25 × EDGE + commission; log data/run_pead6.log
RUN:      2026-10-04  (re-pricing of already-seen data -- not independent evidence)
VERDICT:  G1 PASS  G2 FAIL  G3 FAIL  G5 PASS  -> FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
G1 M+S net +1.14% (t 3.00); gross +1.38%, mean cost 0.24%                     PASS
G2 2005-12 -0.07% | 2013-19 +1.03% (t 2.07) | 2020-26 +2.71% (t 3.65); 2018-26 +1.93% (t 2.91)   FAIL
G3 M -0.15% | S +2.00% (t 4.04)                                                 FAIL
G5 calendar Sharpe 2018+ 0.79                                                   PASS
reported: point ratios +1.18% (t 3.10)
          120-day hold in the auction: +1.93% (t 3.61); 2018+ +2.65% (t 3.07)
          PEAD3 open entry at measured QUOTED open cost: +1.07% (t 2.65); 2018+ +2.52%
          S band 2018+, auction: +3.08% (t 3.31, n 1,920)
```
## Read it plainly
- Cheap auction execution keeps the strategy positive after costs overall, but it fails the same two places PEAD3 did: **2005–12 was flat and mid caps earn nothing.** It is a small-cap, post-2013 effect.
- **The big puzzle:** gross falls from +2.80% (buy at the open) to +1.38% (buy at that day's close). Half the gross return happens between the open and the close of the first day. Either that day's move is real and only capturable with an opening-auction (market-on-open) order, or Sharadar's open price is a stale or bid-side print that no one could actually trade at. **COSTS2 answers this from Databento for a few dollars.**
- The 120-day auction hold (+1.9%, t 3.6) is the strongest variant seen, but it is reported, not gated.
