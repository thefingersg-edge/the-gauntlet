# PREREGISTRATION IMB2: is any of the 15:50 imbalance move still there after a realistic reaction delay?

Frozen 2026-10-08, before any of the data below has been requested.

I am not a financial adviser. This is a measurement, not a recommendation.

## Why
BOUNCE1 Part B: 75% of the move (+3.4 bp per z of +4.7) happens between 15:50:00 and 15:50:15. Nasdaq's own study says about 80% of the close move is priced within **300 ms** of publication. A retail setup (an API at a broker, not co-located) reacts in roughly 0.25–2 seconds. This test measures what is left at those delays.

## Data (Databento, `scripts/databento_imb2b.py` on Dave's Mac)
For each IMB1 trading day (2018-05 → 2026-09):
- `imbalance` schema, all point-in-time S&P 500 members, 15:49:59.5–15:50:05 ET, **with arrival timestamps** (first message per stock).
- SPY `mbp-1` (XNAS.ITCH) and E-mini S&P futures `mbp-1` (GLBX.MDP3, front contract `ES.c.0`), 15:49:59.5–15:51:01: bid and ask at fixed offsets from 15:50:00.000 = −500, 0, 50, 100, 250, 500, 1,000, 2,000, 5,000, 15,000, 60,000 ms (last quote at or before each).

## Signal at delay L
S_L = IMB1's imbalance ratio using only the messages that had arrived by 15:50:00 + L; z_L standardised on the previous 250 days of S_L (as IMB1).

## Trade
On |z_L| ≥ 1: buy SPY at the **ask** (sell at the **bid**) at 15:50:00 + L in the direction of z_L; exit at the opposite side at 15:51:00. Cost = the quoted spread paid on both sides (from the data) + 2 × $0.0035 per share commission.

## Gates (primary delay L = 1 second)
- **G1:** mean net > 0 with t ≥ 2.0.
- **G2:** mean net positive in each of 2019–20, 2021–23, 2024–26.
- PASS needs both.

## Reported (not gated)
- L = 0, 50, 100, 250, 500 ms and 2 and 5 s.
- Exit at 15:50:15 instead of 15:51.
- E-mini futures instead of SPY (fees: Micro E-mini at IBKR, about $1.80 a side per $5 × index, plus the quoted spread).
- Mid-to-mid move by offset (where exactly inside the first second the move happens).
- The arrival-time distribution of the imbalance messages.

## Prediction
G1 FAIL: if Nasdaq's 300 ms figure holds for the index, little is left at 1 second.

## One run.
