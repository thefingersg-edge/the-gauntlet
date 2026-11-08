# PREREGISTRATION v41 — forward record of the v39 random forest on SPX500 and NAS100

Frozen 2026-09-26. **RECORDS ONLY.** Nothing places an order.

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. Why
- v40 confirmed that the timeline carries direction information on five unseen markets (AUC 0.512, 5/5), but it was too weak to pay their spreads.
- On SPX at 2022–26 spreads, the same forest netted about +2 to +2.6 bp a trade (v39 checks). That figure is **post-hoc**: the exits and the era were both picked after looking.
- Only data that did not exist on 2026-09-26 can confirm or kill it.

## 2. What is frozen (data/v41/freeze_v41.json, sha 7c338b95…)
- **Model M:** the v39 FOREST recipe (300 trees, min leaf 200, sqrt, seed 7, median impute), trained on v37 SPX hit points dated before 2026-01-01 (38,748 rows).
  - Model file sha e77aea7c…
  - The check predictions on 2,000 fixed rows must reproduce (sha 03e026a8…). This needs scikit-learn 1.7.2, so the recorder runs in the Cowork VM.
- **Thresholds:** 90/10 percentiles of M's out-of-sample predictions on 2026-01-01 → 2026-08-14.
  - SPX500: long ≥ 0.50065, short ≤ 0.38846.
  - NAS100 (its own v37 timeline, US session): long ≥ 0.51004, short ≤ 0.39249.
- **Entry:** the first decision point each session whose prediction crosses a threshold. One trade per instrument per day, entered at the next bar's open.
- **Exits, both recorded:**
  - **E1:** fixed 2h, stop 1σ.
  - **E2:** to the close, with Dave's tightening stop (1σ → max(0.3, 1 − 0.5·MFE), break-even after +0.5σ).
- Net = gross − the entry bar's quoted spread.
- **Recorder:** scripts/forward_forest.py v1.0 (sha d2c42e695e97d3f431851829214617163716d97892914daf42f5c24d5cc1d039).
  - Prices: forward_tick.sh step 5 now pulls NAS100 and SPX500 M5 into data/v36fwd.
  - The calendar is events_v3 plus weekly claims (identical to v37 before 2026-09-18).
  - Missing macro inputs are logged per trade.
  - Output: data/forward_forest.csv, append-only; every session is logged, including those with no trade.
- **First session: 2026-09-28.**

## 3. Inputs that must be refreshed (about monthly), or the features go stale
- VIXCLS (FRED)
- VX1!/VX2! (TradingView export by Dave)
- SKEW and put/call (Cboe)
- AAII (manual download)
- COT (sentiment_fetch.py)
- DGS2, DTWEXBGS and GASREGW (fred_fetch_v31.py)

Stamps are publication times, so a late refresh adds no look-ahead. Stale inputs appear as missing features (imputed with the training median) and are counted in the missing_macro column.

## 4. Decision rules (pooled SPX + NAS, E1 and E2 reported separately; t clustered by date)
- **Kill:** after at least 250 trades, if E1 mean net is ≤ −1 bp and t ≤ −1.64. The recording stops and the lead is closed.
- **Confirm:** at 500 trades, E1 or E2 mean net > 0 with t ≥ 2.24 (two exits) **and** > 0 in each half of the record.
- Otherwise it continues to 1,000 trades, then a verdict either way.

## 5. Power, and what it cannot see
- About 0.5 trades per instrument per session, so roughly 250 trades a year across the two, which are highly correlated. Per-trade SD is about 25 bp.
- Confirming +2.3 bp at t ≥ 2 needs about 470 trades: **2 to 3 years.**
- It can kill a dead lead much sooner.
- NAS100 was never in any v37–v40 fit or threshold.
- Claims-holiday shifts are not modelled.
