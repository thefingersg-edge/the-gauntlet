# RESULT — cost audit against Dave's real OANDA fills. The backtests' spread assumption matches what he actually pays. The cost the tests barely meet, financing, is what has absorbed his trading profit.

```
SPEC:     none -- a declared MEASUREMENT (fastbot Rule 1), not a backtest. Question set by Dave 2026-10-02: are the fee assumptions right, and are his trades bigger than the tests'?
METHOD:   oanda_fills_pull.py (read-only, run on Dave's Mac; fills.csv sha 05668f37…, financing.csv sha 78c2e0a7…) + fills_audit.py; log data/fills/audit_api.log
          cross-checked against Dave's web export for 2026-05-31 -> 2026-10-01 (realised P/L matches to within a few units of account currency)
RUN:      2026-10-02
VERDICT:  Spread model VALIDATED (paid spread = candle spread, within about 0.1 bp). Financing is the largest real cost. No per-trade edge is distinguishable from zero.
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

1,608 completed trades, 2025-02-24 → 2026-10-01. No account id, balance or margin figure is stored in this file.

## 1. Fees: the spread assumption is right
```
round-trip spread, bp of price   paid (median)   quoted at entry   our OANDA candles, same bar
SPX500                           0.71            0.71              0.81
NAS100                           0.78            0.85              0.73
XAU/USD                          1.71            1.67              1.62
UK100 (n 2)                      1.65            1.46              1.21
Brent oil (BCO)                  4.66            4.40              -- never tested
Silver (XAG)                     7.60            7.33              -- never tested
```
- The backtests charge one full quoted spread per round trip from OANDA's own bid/ask. That is what OANDA charged on these fills: slightly harsh on SPX, about right on NAS and gold.
- **The tests did not fail because they overstated the spread.**

## 2. Size: his trades are much bigger than the spread
- **Holding time:** median 8 hours, mean 32 hours, and 47% held overnight.
- **Price move per trade:** median 46 bp and mean 92 bp, against a spread of about 1–2 bp. The spread is typically **3% of the move**, so on his trades the spread is not what decides the result. Direction is.

## 3. Where the money went (account currency, whole period)
```
realised trading P/L (already net of spread)     +1,064
spread paid inside that (sum of halfSpreadCost)   1,381
financing (daily + at close)                     -1,005
=> trading profit after spread is roughly cancelled by overnight financing
```
- **Financing is the cost that matters for this style of trading.** The tests charge it, but most of them are intraday and never meet it.

## 4. Edge per trade (bp of price, equal weight)
```
all     n 1,608  gross +1.44 (t +0.37)   net -1.10 (t -0.28)   win rate 53%
longs   n 1,201  gross +5.57 (t +1.16)   net +2.92 (t +0.61)
shorts  n   407  gross -10.74 (t -1.80)  net -12.95 (t -2.17)
by holding time (net):  <1h -6.5   1-4h -19.5   4h-1d -4.0   >1d +17.2
by instrument (money):  gold +1,677   SPX +193   NAS -258   oil -428   silver -66   UK100 -53
drift check: gold longs gross +10.6 bp vs +9.8 bp from gold's own rise over the same holding times
profits are concentrated: the top 10 trades made more than the whole total
```

## Read it plainly
- **The cost model holds.** Spread is charged correctly, and it is small relative to how far he trades.
- **The profit has come from being long gold and US indices while they rose.** Gold longs earned almost exactly what gold's own drift would give.
  - Trades held under a day lost money in every holding-time bucket. Shorts lost overall.
  - This matches the tests: short-horizon direction has no edge, and holding long in a rising market earns the market's drift minus financing.
- **Financing has been about as large as the trading profit.** For a style that holds overnight, that is the cost to plan around.
