# Where next — review after v40 (2026-09-26)

I am not a financial adviser. This is a research plan, not a recommendation.

## 1. What is lined up (updated the same evening: the flows tests had already run)
| item | state |
|---|---|
| flows FLOWS-1 month-end rebalancing | RUN 19:35: replicated 2005–23 (t −3.64), **gone since April 2023**. DEAD |
| flows FLOWS-2 pre-refunding Treasuries | RUN 20:12: all gates PASS as registered, but **+0.39 bp net since 2019**. Decayed; a forward test would need about 17 years |
| flows FLOWS-3 overnight drift after sell-offs | RUN 20:12: replicated to 2020 (t 3.59), **zero since 2021**. DEAD |
| FORWARD_v36 NAS100 noise-band | recording from 2026-09-28 |
| v25/v32 release fade | recording, first event 2026-10-02 |
| **v41 (proposed)** forward record of the frozen v39 forest on SPX + NAS100 | not written |

**The lesson of the day:** six published effects now replicate in their paper's era and die afterwards (pre-FOMC, intraday momentum, overnight drift, month-end, pre-refunding, and the release fade's drivers). Timing strategies that are published get arbitraged. What survives in the record is **risk premia**, where you are paid to hold something unpleasant, and that is the case for the options route below.

## 2. One free lead from this review: real dealer-gamma data
- v36 G and v38 B used VIX as a stand-in for "dealers short gamma", and it pointed the wrong way.
- The mechanism papers (Baltussen, Da, Lammers & Martens, JFE 2021; Barbon & Buraschi, *Gamma Fragility*) use dealer gamma computed from options open interest.
- SqueezeMetrics publishes a daily GEX (dealer gamma exposure) and DIX series, reportedly free to download, from about 2011. **To verify before designing anything.**
- If it is available, this is a free, pre-registerable test of the actual mechanism: does noise-band or last-30-minute momentum live on negative-GEX days?

## 3. If we pay for data — what, and what it must clear
### The two bars any paid dataset must clear
1. **Statistical:** a strategy is only distinguishable from noise at about Sharpe > 2/√years (COST_BUDGET arithmetic).
   - 19 years of history → 0.46
   - 5 years → 0.89
   - 1 year → 2.0
   Short, expensive histories (order books, intraday options) raise the bar sharply.
2. **Economic:** yearly data cost < account size × net return. At a realistic 5–10% net a year:
   - $1,800/yr of data needs roughly $18–36k of capital just to pay for itself;
   - $21k/yr needs $210–420k.
   For scale, the best post-hoc numbers we have (forest on SPX 2022–26, about +2 bp a trade, about 1 trade a day) are about 5% a year on notional, unlevered, before any confirmation.

### Candidates, ranked by prior
| rank | data | cost (Sept 2026) | what it unlocks | prior |
|---|---|---|---|---|
| 1 | **Options history, ORATS near-end-of-day** | $599 once (2007→now, ~500 GB) + $99/month going forward | the variance risk premium harvested with a real hedge (RESULT_VRP said this was the missing piece); dealer gamma computed ourselves; IV-based sizing (pineport F passed) | **Highest.** A premium, 19 years of history. Needs an options broker (not OANDA/Kraken), and the left tail is the whole risk |
| 2 | **Futures bars, Databento (usage-based, 1-min OHLCV 16+ years on every plan; $125 free credit)** | likely tens of dollars for 1-min bars of a few contracts; Standard $199/month for 1 year of L1 | futures roll/carry (ASSESSMENT rank 2, never tested); true exchange volume for VWAP/POC; a clean check of CFD prices | Medium. Carry has a published out-of-sample record. Cheap to try with the free credit |
| 3 | Futures order book (L1/L2, trades) for order-flow imbalance | Plus $1,750/month or Unlimited $4,500/month for 16-year depth history | order-flow-imbalance signals | **Low for us.** The literature (Cont et al.) finds predictability decays within minutes. That is HFT territory, where latency and the spread we pay are the edge |
| 4 | Closing-auction imbalance feeds (NYSE/Nasdaq) | paid exchange feeds | predicting close-auction moves | Low for us: the vehicle is market-on-close orders on stocks/ETFs, not CFDs |
| 5 | News or sentiment feeds | expensive | news trading | Closed by ASSESSMENT: HFTs 300 ms from the wire own the window and still don't profit after costs |

## 4. Suggested order (revised after the flows results)
1. Verify the free GEX history, then pre-register a gamma-conditioned momentum test. This is free, and it tests the one mechanism behind our only gross edge.
2. v41: the forest's forward record on SPX/NAS100.
3. **Decide on ORATS** ($599 + $99/month) for a pre-registered variance-risk-premium-with-hedge test. After six decayed timing effects, a risk premium is the best-evidenced remaining route. The budget and account-size arithmetic are written into it first, and it needs an options broker.

Sources: ORATS near-EOD pricing https://orats.com/near-eod-data · Databento pricing https://databento.com/pricing ·
Barbon & Buraschi, Gamma Fragility https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3725454 ·
SqueezeMetrics DIX/GEX https://squeezemetrics.com/monitor/dix · Cross-impact of order flow imbalance https://arxiv.org/html/2112.13213v4
