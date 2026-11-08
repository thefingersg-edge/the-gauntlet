# PREREGISTRATION PEAD7: PEAD3 bought in the OPENING auction, sold in the closing auction, at the measured cost

Frozen 2026-10-04, after RESULT_COSTS2 and before this run. Dave chose to run it although COSTS2 Rule B did not trigger it. Harness: `singlestock/pead7_run.py`, which pins this file.

I am not a financial adviser. This is a measurement, not a recommendation.

## Honesty note
A **re-pricing of already-seen data** (PEAD3's own events, entry and exit prices). Not independent evidence; the forward record decides.

## Definition
- **Events:** the PEAD3 SUE-confirmed EAR longs, M and S, 2005 onward (same 7,762 as PEAD3/PEAD6).
- **Execution:** buy in the opening auction of e0 (the first trading day after the filing), sell in the closing auction 60 trading days later. This is `study(execution="open")` unchanged; COSTS2 showed Sharadar's open equals the official opening-auction price.
- **Cost (gated):** the upper 90% bound of the COSTS2 round-trip/EDGE ratio by band — **M 0.64 × EDGE, S 1.06 × EDGE** — plus 2 × $0.0035/share commission.
- Assumption stated: the 2018–26 ratio is applied to 2005–17.

## Gates (identical to PEAD3 / PEAD6)
G1 M+S net > 0, t ≥ 2.0 · G2 all three eras > 0 and 2018–26 t ≥ 2.0 · G3 M > 0 and S > 0 · G5 calendar Sharpe 2018+ ≥ 0.5.

## Reported (not gated)
1. Point-estimate ratios (M 0.56, S 0.89).
2. 120-day hold, open-auction entry.
3. S band 2018+.

## Prediction
G1 PASS. G2 likely FAIL on 2005–12. G3 uncertain (M was +0.12% at full EDGE in PEAD3).

## One run.
