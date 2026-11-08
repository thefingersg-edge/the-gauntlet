# PREREGISTRATION COSTS2: is the opening price in our backtests a price we could actually trade?

Frozen 2026-10-04, before any opening-auction data is requested. Prompted by PEAD6: half of PEAD3's gross return (+1.4% of +2.8%) is earned between the open and the close of the entry day.

I am not a financial adviser. This is a measurement, not a recommendation.

## Sample
The 400 usable rows of COSTS1 (`data/costs1/measures.csv`, status ok), entry day only. No new draw.

## Data (`scripts/databento_costs2.py`, Dave's Mac)
- Same venue per stock as COSTS1. `statistics` 09:25–09:45 ET on the entry day (official opening price); fallback: the largest print 09:30:00–09:30:05 (the opening cross).
- The first-minute quotes are already on disk from COSTS1 (`raw/*_open.dbn.zst`).

## Measures (per row)
1. **Fidelity:** |Sharadar open − official opening auction price| / official open.
2. **Opening-auction cost (one way):** |official open − first valid midpoint at or after 09:30:00| / that midpoint.
3. **Day-one move check:** entry-day return from the official open to the official close vs from Sharadar's open.

## Decision rules
- **A (data):** if median measure 1 ≤ 0.10%, Sharadar's open is treated as the auction price and the open-entry backtests stand on prices; otherwise they are marked as using an untradeable price.
- **B (cost):** if median (measure 2 + COSTS1 exit-auction cost) ≤ 0.50 × EDGE, the "buy at the opening auction, sell at the closing auction" execution is accepted for the forward portfolio, and PEAD3's open-entry result is re-priced (PEAD7, separately pre-registered).
Medians with bootstrap 90% interval (2,000 draws, seed 20261004).
