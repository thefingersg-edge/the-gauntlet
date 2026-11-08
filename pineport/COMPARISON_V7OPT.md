# New optimised 15m vs previous versions

Config saved as `configs/gold_15m_v7opt.json`. Comparison run on native OANDA
M15, 485,843 bars, FRED filter live.

## 1. On gold it is clearly the best version

| version | trades | L/S | CAGR | Sharpe | max DD | PF | win% |
|---|---|---|---|---|---|---|---|
| **NEW optimised** | 195 | 166/29 | **7.63%** | **1.93** | **−4.75%** | **6.56** | **61.0%** |
| prev scale-free | 273 | 240/33 | 3.97% | 0.99 | −7.15% | 2.00 | 47.3% |
| original v6 | 166 | 133/33 | 3.15% | 0.95 | −11.71% | 2.12 | 51.2% |
| *gold buy-and-hold* | — | — | *10.61%* | *0.52* | *−44.8%* | — | — |

Roughly double the CAGR and double the Sharpe of the previous version, at
two-thirds the drawdown.

## 2. Consistent in every era — but all of it is in-sample

| window | trades | CAGR | Sharpe | max DD | PF | vs random |
|---|---|---|---|---|---|---|
| 2006–2012 | 68 | 5.62% | 1.72 | −4.75% | 3.79 | **100.0** |
| 2013–2019 | 70 | 3.67% | 1.01 | −5.00% | 2.22 | **100.0** |
| 2020–2026 | 57 | 16.03% | 2.43 | −4.47% | 10.65 | **100.0** |

Positive in all three, 100th percentile against random entry in all three, and
a drawdown that never exceeds 5%. That is the strongest era profile produced in
this project.

**The caveat is structural, not a quibble.** This was optimised on 2006-to-date,
so all three eras were in the training set. Sub-period consistency inside the
fitting window is much weaker evidence than out-of-sample consistency, because
the optimiser can and does select parameters that work across the whole span it
can see. The previous version at least held out 2006–2012 and 2024–2026.

## 3. First version whose parameters sit on PLATEAUS

| | −2 | −1 | **opt** | +1 | +2 | shape |
|---|---|---|---|---|---|---|
| `bb_period_long` (96) | 1.49 | 1.75 | **1.93** | 1.88 | 1.61 | **PLATEAU** 3/5 |
| `lsma_length_short` (40) | 1.89 | 1.91 | **1.93** | 1.84 | 1.84 | **PLATEAU** 5/5 |

Every earlier sweep returned SPIKE — 1 of 12 values within 10% of the best,
optima on knife-edges. These curves are smooth and the neighbours hold up.
**This is the single most encouraging result in the project**, because a plateau
is what a real effect looks like and a spike is what fitting looks like.

## 4. Multi-market: still 2 of 9 — REJECT

Vol-scaled stop, nothing else tuned per market, pre-registered ≥80th percentile.

| market | trades | CAGR | Sharpe | pctile |
|---|---|---|---|---|
| *XAUUSD (known)* | 195 | *7.63%* | *1.93* | *100.0* |
| **XAGUSD** | 206 | 0.04% | 0.62 | **85.0** |
| **DE30EUR** | 189 | 5.97% | 0.41 | **81.8** |
| USDJPY | 232 | 0.03% | 0.24 | 62.0 |
| BCOUSD | 246 | 0.05% | 0.22 | 60.2 |
| XCUUSD | 210 | 0.00% | 0.21 | 28.2 |
| AUDUSD | 248 | −0.00% | −0.09 | 24.0 |
| GBPUSD | 229 | −0.00% | −0.35 | 16.8 |
| SPX500USD | 243 | −0.38% | −0.06 | 12.0 |
| EURUSD | 247 | −0.00% | −0.22 | 8.0 |

**2/9, same score as the previous version** (which passed on EURUSD and GBPUSD —
a completely different pair, which is itself a sign the passes are noise). Note
the CAGR column: every non-gold market is within a rounding error of zero.

## 5. Two things reverted that are worth reconsidering

**The ladder is back in dollars** — `markUp` 230, `lockProfitUp` 190,
`markDown` 150, `rangeL` 20. Median entry price across the training trades is
~1,265, where 230 is **18% of price**. Gold today is ~4,500, where the same 230
is **5%**. The first rung means something structurally different now than it did
across most of the data it was fitted on, and it will keep drifting as gold
moves. The percent-of-entry version was verified equivalent at the calibration
point (243 vs 242 trades, CAGR 3.69 vs 3.42), so this is a free change.

**Sizing is back to `/50`** — a dollar constant that approximated the stop
distance at gold ~1,500. At 4,500 the real stop distance is ~134, so the rule
now sizes ~3× larger than the stated 0.8% risk. This is what produced the
margin rejections and the 0.12/2.88 split fill in the earlier export.

## 6. Verdict

| criterion | result |
|---|---|
| beats previous versions on gold | ✅ substantially |
| positive in all eras | ✅ but all in-sample |
| beats random entry | ✅ 100th percentile, all eras |
| **parameters on a plateau** | ✅ **first version to pass this** |
| concentration <40% | ❌ 47.2% |
| **generalises across markets** | ❌ **2/9** |
| out-of-sample evidence exists | ❌ **none left — fitted on everything** |
| beats gold buy-and-hold on return | ❌ 7.63% vs 10.61% |

The plateau finding and the multi-market failure point in opposite directions,
and honestly, they cannot both be resolved from this data. Optimising on the
full history bought a better in-sample fit and spent the only thing that could
have tested it.

**The one remaining test that is not circular is forward performance.** The
parameters are frozen, the port matches at 97.8%, the execution model is pinned,
and `verify_trades.py` will catch any drift. Six months of live-equivalent data
would be worth more than any further backtest.
