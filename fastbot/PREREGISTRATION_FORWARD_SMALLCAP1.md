# PREREGISTRATION FORWARD_SMALLCAP1: earnings drift in small caps, judged forward only

Frozen 2026-10-04, after RESULT_AUDIT_LOOKAHEAD and before any forward signal exists (the record starts 2026-10-05).

I am not a financial adviser. This is a measurement, not a recommendation.

## Why forward only
The idea comes from a post-hoc slice of the corrected backtest (PEAD7c: small caps, entries 2018+, +2.08% net, t 2.28, n 1,898). Every year of history has been seen, so **no backtest can test it honestly**. Only new data can.

## Definition (all frozen; nothing to choose later)
- **Signal:** the corrected PEAD3 rule as implemented in `singlestock/pead_forward.py` (sha in PROVENANCE): top-decile EAR long, confirmed by SUE ≥ 70th percentile of the prior 91 days, from the frozen PEAD1 engine. Ledger rows with `group = CONFIRMED` and `band = S` only.
- **Entry:** official opening auction of the first trading day after the `anchor` (the later of the 10-Q/10-K filing and the day the EAR is known). **Exit:** closing auction 60 trading days later.
- **Return:** excess over the S-band benchmark. **Cost:** the measured COSTS2 cost, 1.06 × EDGE + commission (ledger column `net_pead7`).
- The recorder trades nothing; it is a paper ledger (`data/pead3_forward.csv`), filled monthly by the scheduled task.

## Verdict (once)
- Taken at **600 closed S/CONFIRMED rows or 2029-12-31, whichever comes first.** No interim verdict, no early stop. Interim counts and running means are reported as information only.
- **G1:** mean `net_pead7` > 0 with quarter-clustered t ≥ 2.0.
- **G2:** mean `net_pead7` > 0 in at least two-thirds of calendar years with ≥ 50 closed rows.
- PASS needs both.

## Budget
About 200–220 S/CONFIRMED signals a year (2018–26 rate), so 600 rows take about 3 years. With a per-trade SD of about 25%, 600 rows give a standard error of about 1.0% (more with quarter clustering): only an effect near the backtest's +2% will pass. A smaller real effect will read as FAIL. That is accepted.

## One verdict.
