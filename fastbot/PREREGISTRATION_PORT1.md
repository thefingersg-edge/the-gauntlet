# PREREGISTRATION PORT1: the PEAD3 signals as a real-sized portfolio (forward only)

Frozen 2026-10-03. Judged **forward only**, on the FORWARD_PEAD3 ledger. Every past window has been seen, so no backtest verdict is possible.

I am not a financial adviser. This is a measurement, not a recommendation.

## Rules (fixed now)
- **Signals:** FORWARD_PEAD3 rows tagged CONFIRMED, **S band first, then M**.
- **Book:** 15 equal slots. Hold 60 trading days. No re-buy of a held stock. At most 3 positions per Sharadar sector.
- **Execution:** open after the filing (as recorded). The auction alternative is logged by COSTS1.
- **Entry filter:** no new entries while SPX500 is below its 200-day average or VIX is in the top fifth of its prior 250 days (both as of the previous close). This is the overlay that helped STRAT1.
- **Two versions:** (a) long-only cash; (b) the same, hedged against the band return.

## Verdict (with FORWARD_PEAD3's, at the same date)
- **(b) hedged:** annualised Sharpe ≥ 0.5.
- **(a) long-only:** maximum drawdown no deeper than a small-cap index over the same days.
- Reported: average slots used, turnover.

## One verdict.
