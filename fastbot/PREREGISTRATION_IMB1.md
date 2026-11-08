# PREREGISTRATION IMB1: does the S&P 500 closing-auction imbalance at 15:50 predict the index's last minutes?

Frozen 2026-10-04, before any imbalance or price data has been requested. Member list: `data/imb1/members.csv` (point-in-time S&P 500 members and listing venue, built by `singlestock/imb1_members.py`; sha in PROVENANCE).

I am not a financial adviser. This is a measurement, not a recommendation.

## Mechanism
From 15:50 ET, Nasdaq and NYSE publish each stock's closing-auction imbalance (shares waiting to buy or sell at the close beyond those already matched). A large net buy (sell) imbalance across the index must be absorbed by liquidity providers before 16:00, which may push prices up (down) in the last ten minutes. Closing auctions have grown sharply since 2018, so this is a recent-regime question by design.

## Data (Databento, pulled on Dave's Mac by `scripts/databento_imb1.py`)
- `imbalance` schema, XNAS.ITCH (Nasdaq-listed members) and XNYS.PILLAR (NYSE-listed members), 15:50:00–15:50:20 ET each trading day, 2018-05-01 to 2026-09-30. Per stock: the **first** message at or after 15:50:00.
- SPY quotes (`bbo-1s`, XNAS.ITCH): midpoint at 15:51:00 and at 15:59:59.

## Signal and target
- Signed dollar imbalance per stock = total imbalance quantity × reference price × (+1 buy side, −1 sell side, 0 none).
- **S_t** = Σ signed dollar imbalance / Σ paired dollar value (paired quantity × reference price), over all members with a message.
- **z_t** = (S_t − mean of the prior 250 days) / SD of the prior 250 days (no future information).
- **Target r_t** = SPY midpoint 15:59:59 / midpoint 15:51:00 − 1, in bp. Entry is one minute after publication, so the signal is known.

## Gates (all days with z_t, 2019-05 onward after the 250-day warm-up)
- **G1:** OLS of r_t on z_t: slope > 0 with heteroskedasticity-robust t ≥ 2.0.
- **G2 (tradeable):** on days with |z_t| ≥ 1, take sign(z_t) × r_t minus the cost; mean > 0 with t ≥ 2.0. Cost = 1.0 bp round trip (OANDA SPX500's quoted spread near the close is about 0.4–1 bp; the higher value is used).
- **G3:** G2's mean net positive in each of 2019–20, 2021–23 and 2024–26.
- PASS needs G1, G2 and G3.

## Reported (not gated)
Nasdaq-only and NYSE-only signals; |z| ≥ 2; the 15:51 → 15:55 part alone; days with fewer than 400 members reporting.

## Budget
About 1,850 days after warm-up. The 9-minute SPY return has an SD of about 10 bp, so the standard error of a daily mean is about 0.25 bp, and a correlation of about 0.05 is enough for G1. On the ~600 days with |z| ≥ 1, an edge of about 1.0 bp net is needed for G2.

## One run (after the pull completes).
