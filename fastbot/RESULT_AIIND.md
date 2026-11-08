# RESULT — AIIND: the two "AI indicators that work" both lose money after costs (AIKNN1 FAIL, AIMA1 FAIL)

```
SPEC:     PREREGISTRATION_AIIND.md (sha bbc0ff63…), frozen 2026-10-19 before any data
METHOD:   scripts/aiind_port.py (sha ab2d0fcd…), scripts/aiind_run.py (sha c5868bc5…); self-tests ALL PASS
PORT:     Zeiierman VERIFIED against TradingView (99.6% trend-state match). lastguru PARTLY VERIFIED (VWMAs exact, 53/53 entries on
          port crossovers; the kNN vote could not be checked because its memory predates the export). data/aiind/verify_aiind.log
RUN:      2026-10-20, once each.   LOGS: data/aiind/run_aiknn1.log, run_aima1.log; post-hoc: posthoc_knn_placebo.log
VERDICTS: AIKNN1 FAIL (G1, G2).  KNN-ADD "helps" as registered, but no better than a random filter (post-hoc).
          AIMA1 FAIL (G1, G2).   AI-ADD "helps" by a hair (t +2.01): it loses slightly less than a plain Supertrend.
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## AIKNN1 — lastguru "VWMA with kNN Machine Learning: MFI/ADX" (5 years after publication)
| BTCUSDT 5m, Jul 2021 → Sep 2026 | trades | net per trade | t |
|---|---|---|---|
| **10 bp per side (registered)** | 4,460 | **−17.9 bp** | −6.96 |
| 2 bp per side | 4,460 | −1.9 bp | −0.73 |
| no costs | 4,460 | +2.1 bp | +0.82 |
| 2021-07 → 2022 / 2023–24 / 2025–26 | 1,236 / 1,664 / 1,560 | −24.3 / −18.3 / −12.4 bp | all < −3.6 |

- **No edge before costs.** Even with zero costs it makes +2.1 bp a trade (t 0.8), which is noise. It trades 2.3 times a day, so at Binance's standard fee it loses about **0.4% a day**.
- **The author's own period (2017 → mid-2021) loses just as much:** −19.9 bp a trade. It never worked after costs.
- **Does the machine learning help?**
  - **As registered, yes:** filtered minus unfiltered is +351 bp a day (t 42).
  - **But that comes from trading less, not from predicting.** The filter drops about 88% of crossovers. The unfiltered crossover makes 36,833 trades and loses 20.4 bp each.
  - **Post-hoc check (not registered):** a *random* filter keeping each crossover with the same 21.6% chance (200 draws) produces the same number of trades. The kNN's gross return per trade beats only 81% of those random filters, which is inside the luck band. So the "AI" adds nothing a coin flip doesn't.
- **Reported only (no gate):** NQ +2.4 bp (t 1.43) and ES +2.7 bp (t 1.63) on futures at half a tick plus commission. These are not significant, and the same rule loses heavily on its own market.

## AIMA1 — Zeiierman "AI Source Switching Moving Average" (8 June → 16 Oct 2026, post-publication)
| 5m, AI Supertrend flips | trades | net per trade | t | plain Supertrend control |
|---|---|---|---|---|
| BTCUSDT (10 bp/side) | 1,461 | **−20.8 bp** | −14.4 | −22.5 bp |
| NQ futures | 885 | −1.0 bp | −0.7 | −0.9 bp |
| ES futures | 902 | −1.5 bp | −1.9 | −2.0 bp |
| **Pooled** | 3,248 | **−10.0 bp** | −10.3 | |

- **It loses in every market, even before costs.** NQ is −0.8 bp and ES −1.0 bp at zero cost; BTC is −4.8 bp at 2 bp per side.
- **The author's design period loses too:** BTC −23 bp over 29,681 trades; NQ −0.1; ES −0.8 (t −4.9).
- **Does the AI help? Only by losing less.** The AI version loses 9.5 bp a day less than the plain Supertrend (t +2.01, just over the bar). That is a slightly smaller loss, and the sign isn't stable:
  - at 15 minutes the AI is worse on BTC and ES;
  - at 1 hour it is worse on ES.
- **What the AI actually picks:** in the test window it chose "Low" as the price source 40–46% of the time on BTC and ES. That shifts the trailing band; it doesn't forecast anything.

## About the video
- The video showed about 100 recent trades, mostly from June, and called the two scripts the "2 of 500 that work".
- On the author's own markets, with standard costs, neither does. TradingView's own strategy report for lastguru shows the same: −42% over the last year on BINANCE:BTCUSD with zero commission, and −47% on KRAKEN:BTCUSD at 15 minutes.
- A shortlist of 2 from 500, picked on recent trades, is what luck produces (TURBO1). Nothing here suggests otherwise.

## Programme status
Both closed. No forward record (AIMA1 did not pass).
