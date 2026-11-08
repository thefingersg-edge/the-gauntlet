# PREREGISTRATION PEAD8: how long to hold, and do stops or targets help? (exits on the PEAD7 trades)

Frozen 2026-10-04, before any exit rule below has been computed. Harness: `singlestock/pead8_run.py`, which pins this file.

I am not a financial adviser. This is a measurement, not a recommendation.

## Honesty note
Same 7,762 PEAD3/PEAD7 events; the whole history has been seen. The 120-day hold's per-trade figure was already printed in PEAD7 (+2.77%). Exits were tested before only on zero-edge intraday patterns (RESULT_v2: no barrier can create an edge where there is none). PEAD has a real drift, so exits are a fair new question here, but the result is a re-analysis, not independent evidence.

## The right yardstick: return per unit of capital-time
A 120-day trade ties up money twice as long as a 60-day one; a stopped trade frees it early. With a 15-slot portfolio (PORT1) capital is the constraint, so every variant is judged on **net excess return per position-day**: for each entry quarter q, R_q = Σ net / Σ days held, compared with the baseline's R_q for the same events.

## Baseline
PEAD7 as frozen: buy opening auction of e0, sell closing auction 60 trading days later; cost M 0.64 / S 1.06 × EDGE + commission.

## Variants (all: same entry, same cost, maximum hold 120 trading days, checks on daily closes)
- **V1 time exit at 120 days.**
- **V2 trailing stop:** exit when the close falls 15% below the highest close since entry.
- **V3 take-profit:** exit when the close is 25% above the entry price.
- **V4 tightening stop ("don't quit while you're ahead", no target):** stop 20% below the highest close; once the peak is ≥ 10% above entry the gap tightens to 12%; once ≥ 25% above entry, to 7%.
- A triggered rule exits in the **next day's** closing auction (the trigger is only known at the close). Delisting rules as in the engine; an exit before the data ends carries no delisting penalty.

## Gates (per variant vs baseline; Bonferroni across 4 variants)
- G1 per-position-day return higher than baseline: mean of (R_q,variant − R_q,base) over entry quarters > 0 with t ≥ 2.5.
- G2 higher in each era (2005–12, 2013–19, 2020–26), point estimate.
- G3 calendar-time excess Sharpe 2018+ ≥ baseline's.
A variant PASSES only with G1, G2 and G3.

## Reported (not gated)
Per-trade net, average days held, share of trades exited by the rule, worst calendar year.

## Prediction
V1 FAIL (more per trade, less per day). V2–V4 FAIL: stops usually cut drift trades in noisy small caps.

## One run.
