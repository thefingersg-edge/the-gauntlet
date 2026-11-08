# PREREGISTRATION v40 — confirming the v39 winner on five markets no model has seen

Frozen 2026-09-26. Only label base rates, spreads and barrier sizes have been read for these markets. No prediction and no signed return has been computed.
Scripts: scripts/v40_build.py (timelines), scripts/v40_confirm.py v1.0 (predict, then test).

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. What is being confirmed
- **Model:** the v39 winner, FOREST (random forest, 300 trees, min leaf 200, sqrt features, seed 7, median impute), frozen. The v39 plateau check found 0.554–0.559 AUC across 12 settings, so the setting is not a lucky pick.
- **Exits:** the two chosen in the v39 checks.
  - **E1:** fixed 2h with a 1σ stop.
  - **E2:** held to the close with a tightening stop (1σ shrinking as max(0.3, 1 − 0.5·MFE/σ)σ, never below break-even after +0.5σ).
- **The honest status of E1/E2:** both exits and the "first signal per day" entry were chosen after looking at SPX data. This test is the first time they meet data they were not chosen on.

## 2. Markets and timelines
- UK100, DE30, EU50, JP225 and AU200: OANDA 5m bid/ask (data/v38), each in its cash session (as in v38).
- Each market's v37 timeline is built by tl_build2 (tl_build 1.1 with the session made a parameter). Macro and calendar stamps are converted to the market's local time.
- **Gate 0 (passed):** tl_build2 with the US session reproduces the v37 SPX matrix exactly on 42,121 rows (2005–14): keys, all 125 features and labels.
- Decision points run every 15 minutes from open + 15 to close − 2h15. The labels are the v37.1 direction labels on each market's own ±1σ(2h) barriers.

## 3. No market is trained on
- Yearly walk-forward. For test year Y, FOREST is fitted on **SPX500 hit points dated before Y only** and predicts all five markets in year Y.
- No non-US data is ever used for fitting or thresholds, other than each market's own PREVIOUS-year predictions, which set its 90/10 percentile trading thresholds (as in v39).
- Trades: 2013 → 2026-09-25. One per market per day (the first signal). Only bars with a real quoted spread. Net = gross − the entry bar's spread.

## 4. Gates
- **G1 direction:** on hit points 2013+ pooled over the five markets, the day-bootstrap 95% lower bound of AUC is > 0.5, **and** AUC > 0.5 on at least 4 of the 5 markets.
- **G2 (E1) and G3 (E2), Bonferroni t ≥ 2.24:** pooled net per trade > 0 with t ≥ 2.24 (clustered by date); > 0 in each of 2013–17, 2018–21 and 2022–26; excluding 2020–21, > 0 with t ≥ 1.64.
- **Reported, gating nothing:** per-market AUC and net; a control (random decision points traded both ways, same exits), and how much the signal adds over it.

## 5. Budget and blind spots (read before running)
- **Hit points 2013+:** UK100 40,247; DE30 39,668; EU50 37,787; JP225 22,678; AU200 23,192. Pooled AUC SE is about 0.003, so G1 can resolve AUC 0.51.
- **Median spreads:** UK 1.46, DE 1.00, EU 4.43, JP 4.59, AU 2.80 bp, against SPX's 1.78 over 2013–26 (0.7 in 2022–26). Median barriers are 27–39 bp.
- On SPX the signal added about +2.5 bp gross per trade over the control. **G2/G3 are therefore expected to fail on the high-spread markets.** G1 is the informative gate: does the SPX-trained direction signal exist on other markets at all?
- **Blind spots:**
  - The features are US-centric (VIX, US releases, AAII, COT on the S&P). A market-specific timeline could do better or worse.
  - JP225's early years are thin (quotes sparse before about 2012).

## 6. One predict stage, one test stage. No change of model, exits, thresholds or gates.
