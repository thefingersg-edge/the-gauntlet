# PREREGISTRATION PEAD6: PEAD3 executed in the closing auction at the MEASURED cost

Frozen 2026-10-04, after RESULT_COSTS1 and before this run. Harness: `singlestock/pead6_run.py`, which pins this file.

I am not a financial adviser. This is a measurement, not a recommendation.

## Honesty note (read first)
This is a **re-pricing of already-seen data**, not a fresh discovery. PEAD3 was run on the whole history, and its log already reported "closing auction, 25% of EDGE: net +1.09% (t 2.87); 2018+ +1.88%". PEAD6 swaps the assumed 25% for the measured cost and applies PEAD3's full gates. A PASS makes the auction design the one the forward record (FORWARD_PEAD3 / PORT1) should be judged on; it is not independent evidence.

## Definition
- **Events:** PEAD3 SUE-confirmed EAR longs, bands M and S, 2005 onward (identical event list to PEAD3).
- **Execution:** buy in the closing auction of the first full trading day after the 10-Q/10-K filing (e0), sell in the closing auction 60 trading days later. (`ss_events2.study(execution="close")`, unchanged.)
- **Cost (gated):** the **upper 90% bound** of the COSTS1 auction/EDGE ratio by band — **M 0.11 × EDGE, S 0.25 × EDGE** — plus 2 × $0.0035/share commission. Missing EDGE → band median, as before.
- Assumption stated: the 2018–26 ratio is applied to 2005–17 (EDGE itself carries the era's spread level).

## Gates (identical to PEAD3, quarter-clustered)
- G1 M+S net excess > 0, t ≥ 2.0
- G2 all three eras (2005–12, 2013–19, 2020–26) > 0, and 2018–26 t ≥ 2.0
- G3 M > 0 and S > 0
- G5 calendar-time excess Sharpe 2018+ ≥ 0.5

## Reported (not gated)
1. Point-estimate ratios (M 0.10, S 0.20).
2. 120-day hold in the auction (the PEAD4/PEAD5 lead).
3. PEAD3's open entry re-priced at the measured **quoted** open cost (M 1.12 × EDGE, S 1.94 × EDGE) — what marketable orders at the open would really have cost.
4. S band alone, 2018+.

## Prediction
G1 PASS (about +1.2%). G2 FAIL on 2005–12, as in PEAD3. G3 uncertain (M was near zero in PEAD3).

## One run.
