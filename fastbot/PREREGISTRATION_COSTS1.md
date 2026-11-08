# PREREGISTRATION COSTS1: measure the real cost of trading the PEAD signals

Frozen 2026-10-03. **It needs one of two things that only Dave can provide**, so it is ready but not started.

I am not a financial adviser. This is a measurement, not a recommendation.

## Route 1: historical quotes (preferred)
- **Data:** Databento US Equities, 2018 onward, BBO and closing-auction prints. Pay as you go from $0.40/GB; new accounts get $125 of credit (pricing checked 2026-10-03).
- **Sample:** a frozen random sample of 400 PEAD3 signals from 2018–2026, stratified M/S, drawn **before** any quote is read.
- **Measures:**
  - the quoted spread at the open entry;
  - the closing-auction price against the last pre-close midpoint (auction "cost");
  - both compared with our EDGE estimate for the same stock and day.
- **Question:** what fraction of EDGE does each execution style actually pay?
- **Decision rule:** if the closing-auction cost is ≤ 50% of EDGE on the median signal, the auction model of PEAD2 and STRAT1 is accepted for the forward portfolio. Otherwise, full EDGE stays.

## Route 2: paper and live fills
- An IBKR paper account, then a small live sample.
- Each PEAD3 forward signal is bought once at the open (limit at mid + half spread) and once in the closing auction (MOC). Fills are logged in `data/costs1_fills.csv` against the same benchmarks.
- **Verdict:** at 50 fills per style.

## One verdict per route.
