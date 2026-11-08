# PREREGISTRATION — AIIND batch: the two "AI indicators that work" (AIKNN1, AIMA1)

Written and frozen 2026-10-19, before any data for these tests was pulled and before any port was run on real prices. Requested by Dave the same day.

I am not a financial adviser. This is a measurement, not a recommendation.

## The claim being tested
- A YouTube video dated about 2026-10-13 said that, of roughly 500 "AI" indicators on TradingView, only two open-source ones work:
  - "VWMA with kNN Machine Learning: MFI/ADX" by lastguru (published 2021-06-27);
  - "AI Source Switching Moving Average" by Zeiierman (published 2026-06-08).
- The video showed a forward run of the last ~100 trades, mostly from June 2026.
- **Selection warning.** Choosing 2 of ~500 by their record is exactly the TURBO1 trap: with 500 tries, about 5 would clear a 1% significance bar by luck alone. So nothing up to the moment each script was singled out counts as evidence. Only data **after publication** is judged.

## Code (frozen)
- `pine/aiind/lastguru_vwma_knn_mfi_adx.pine` (MPL 2.0) and `pine/aiind/zeiierman_ai_source_switching_ma.pine` (CC BY-NC-SA 4.0), as pasted by Dave from the TradingView "Source code" tabs on 2026-10-19. The Zeiierman file drops display-only lines (tooltips, plots, colours); no calculation is changed. Shas in PROVENANCE.
- **Author defaults only.** No parameter is changed, tuned or searched.
- Code review before any data (done 2026-10-19):
  - **lastguru:** the kNN label for a crossover is "was the open at the NEXT crossover ≥ the open at this one". It is stored only when that next crossover happens, so it uses no future data. Features are ADX (13, smoothing 6) and a 13-bar MFI, raw 0–100 scale, Euclidean distance; k = 45 with ties included; a trade needs a vote margin ≥ 2. Entries reverse the position (stop-and-reverse); a filtered-out crossover leaves the old position open.
  - **Zeiierman:** each stored row pairs features from `horizonBars` (4) bars ago with the move that has since happened. Labels are therefore known when stored; no future data, no `request.security`. The "AI" decides only (a) which of open/high/low/close feeds a 3-bar EMA and (b) how wide the ATR band is (×1.7 to ×3.06). The signal is the flip of that ATR trailing band (its "AI Supertrend").

## Execution rules (both tests)
- Signals are taken at the bar close; trades fill at the **next bar's open** (TradingView's default for strategies).
- Always in the market after the first trade (stop-and-reverse), one unit, no stops or targets beyond the script's own logic.
- Per-trade return = side × (exit open / entry open − 1), minus cost per side.
- **Costs per side:**
  - BTCUSDT: **10 bp** (Binance standard taker fee). Also reported at 2 bp and at 0.
  - ES and NQ futures: half a tick + $2.25 commission, converted to bp at the entry price.
- **Statistics:** mean net return per trade; t clustered by UTC day.

## Data
- **BTCUSDT 5-minute**, Binance spot public archive (data.binance.vision), from 2017-08-17, real volume. Pulled by Dave with `scripts/fetch_aiind.py` (free, no key).
- **ES and NQ 1-minute futures** (Databento GLBX, `.v.0` volume-rolled, real volume), already on disk to 2026-08-31 (flows/data/futures). The same script tops them up to 2026-10-16 (refuses over $2). Resampled to 5 minutes, all sessions. At each contract switch the older history is shifted by the price gap at the switch bar (back-adjusted); a trade open across a switch takes no P&L on the switch bar.
- Both scripts are run from the **first bar of the data**, so the learning memory builds as it would on a chart loaded from that date.

## AIKNN1 — lastguru VWMA + kNN (5 years out of sample)
- **Primary:** BTCUSDT 5m (the author's own market and timeframe). Judged on trades entered **2021-07-01 → 2026-09-30**.
- **G1:** mean net per trade > 0 at 10 bp per side, day-clustered t ≥ 2.0.
- **G2:** mean net per trade > 0 in each sub-period: 2021-07 → 2022-12, 2023-01 → 2024-12, 2025-01 → 2026-09.
- **PASS** = G1 and G2.
- **KNN-ADD (does the machine learning help?):** the same strategy with the filter off ("Apply kNN filter" = false, the author's own switch). Daily net P&L of filtered minus unfiltered, over the same window; **the ML helps** only if the mean difference > 0 with t ≥ 2.0.
- **Reported, no gate:** ES and NQ 5m with the same rules and window; the pre-publication period 2017-08 → 2021-06 (the author's own period); results at 2 bp and 0 bp per side.

## AIMA1 — Zeiierman AI Source Switching MA (about 4 months out of sample)
- **Window W:** trades entered **2026-06-08 → 2026-10-16**. The position is flat at the start of W and the first flip inside W opens it.
- **Markets:** BTCUSDT 5m, ES 5m, NQ 5m.
- **G1:** pooled across the three markets, mean net per trade > 0, day-clustered t ≥ 2.0.
- **G2:** mean net per trade > 0 in each of the three markets.
- **PASS** = G1 and G2.
- **AI-ADD (does the AI help?):** a plain control from the same code. The source is fixed to close (still smoothed by the 3-bar EMA). The band multiplier is fixed at stMult × (1 + stAdapt × (1 − d)), where d = the median aiDrive of that market over the 90 days before W. Daily net P&L of AI minus control, pooled; **the AI helps** only if the mean difference > 0 with t ≥ 2.0.
- **Reported, no gate:** 15-minute and 1-hour versions of the same; the author's design period (data start → 2026-06-07); results at the lower cost levels.
- **Forward:** a paper forward record is added only if AIMA1 passes.

## Port check (before the run counts)
- The Python ports must reproduce TradingView. Dave exports, from TradingView on BINANCE:BTCUSDT 5m with author defaults:
  - (a) lastguru's "List of trades";
  - (b) Zeiierman's chart data ("Export chart data", which includes the AI Supertrend plots).
- The port is started at the first bar of each export.
- **Pass:** at least 95% of TradingView's trade entries (lastguru), or of its trend state per bar (Zeiierman), match the port on the same bar and side. Entries and states are compared, not returns.
- A mismatch is fixed as a logged mechanical change before the main run. If the check cannot be met, the result is reported as **port not verified**.

## Predictions
- AIKNN1 **FAIL**, and KNN-ADD **FAIL**: at 5 minutes, 10 bp a side swamps any small edge, and a 2-feature vote on 0–100 scales mostly echoes ADX.
- AIMA1 **FAIL**, and AI-ADD **FAIL**: the AI only nudges a standard Supertrend, which has no documented edge at 5 minutes after costs.

## Harness
`scripts/aiind_port.py` (ports + planted self-tests) and `scripts/aiind_run.py` (the run), frozen with shas in PROVENANCE before the run. Run once each; logs `data/aiind/run_aiknn1.log`, `run_aima1.log`.
