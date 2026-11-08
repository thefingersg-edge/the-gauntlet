# RESULT — COSTS2: Sharadar's open IS the official opening-auction price (Rule A PASS). Buying in the opening auction costs more than the close (Rule B FAIL).

```
SPEC:     PREREGISTRATION_COSTS2.md (sha in PROVENANCE)
DATA:     Databento statistics 09:25-09:45 ET on the entry day, 400 COSTS1 rows; 2 dropped (opening-price stat undefined) -> 398
METHOD:   scripts/databento_costs2.py -> data/costs1/measures2.csv; singlestock/costs2_verdict.py; log data/run_costs2.log
RUN:      2026-10-04
VERDICT:  RULE A PASS   RULE B FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
                                         ALL               M                 S
1 |Sharadar open - official open|        0.000%            0.000%            0.000%
2 opening auction vs first mid, |one way| 0.48% (0.43-0.55) 0.35%             0.68%
  signed (open - mid)                    +0.10%            +0.10%            +0.11%
3 day one, official open -> close (mean) +1.69%            +1.34%            +2.04%
  same with Sharadar prices              +1.76%            +1.43%            +2.09%
round trip (open auction + exit auction) 0.56%             0.43%             0.77%
round trip / EDGE                        0.70 (0.63-0.80)  0.56              0.89
```
## Read it plainly
- **The PEAD6 puzzle is solved: the first-day move is real.** Sharadar's open is exactly the official opening-auction price, and the stocks really do rise about +1.7% (small caps +2.0%) from the opening auction to the close on the first day. A market-on-open order gets that price.
- **But the opening auction is a noisier place to trade than the close.** The open sits on average 0.48% away from the first quoted midpoint (vs 0.05% for the close). By the pre-registered measure the round trip costs 0.70 × EDGE, above the 0.50 limit, so Rule B fails and PEAD7 is not automatically triggered.
- Nuance: measure 2 is a distance in either direction. The signed figure shows a buyer at the open pays only about +0.10% above the next midpoint on average; much of the 0.48% is price discovery in both directions, not a cost. The pre-registered measure is the conservative one and it stands.

## What it means
- Buying at the open captures roughly twice the gross of buying at the close (PEAD3 +2.8% vs PEAD6 +1.4%) for about 0.4% more round-trip cost (0.56% vs 0.11%, before commission). On the face of it, the opening auction is the better execution, especially for small caps.
- A properly costed test of that is PEAD7 (open-auction entry, close-auction exit, cost = the measured ratio's upper bound, M 0.64 / S 1.06 × EDGE). Under COSTS2's own rule it needs a fresh decision because Rule B failed.
