# PREREGISTRATION v39 — which model type finds direction in the timeline?

Frozen 2026-09-26 before any v39 model was fitted.
- Scripts: scripts/v39_models.py v1.0 (Parts A and M) and scripts/v39_deep.py (Part D, run on Dave's Mac).
- Inputs: data/timeline_v37/matrix.npz (sha 6fc354b2…) and data/v39/shapes.npz and meta.npz (built by build_v39.py).

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. What this is, and what it is not
Every SPX date used here has already been looked at in v37–v37.3. This is a development comparison. It can **pick** a winner with a frozen rule. It cannot **confirm** one: that needs the v38 indices (pull prepared: scripts/run_v38_pull.sh) or forward data, pre-registered separately.

## 2. Common set-up
- **Labels:** v37.1 direction. Among decision points where a ±1σ(2h) barrier was hit, up-first = 1.
- **Yearly walk-forward, 2012 → 2026:** each model is trained on every hit point before 1 January of the test year and tested on that year.
- **Early stopping:** the gradient models stop early on the last ~126 trading days of the training span.
- **Trading (reported):** long when a model's prediction is at or above the 90th percentile of its own out-of-sample predictions from the PREVIOUS test year; short at or below the 10th. One trade at a time, net of spread, from 2013.

## 3. Part A — six model types plus a null
| name | model |
|---|---|
| LGBM | LightGBM, v37 parameters |
| LOGIT | L2 logistic regression, C 0.1, median-impute + standardise |
| FOREST | random forest, 300 trees, min leaf 200, sqrt features |
| RULES | one decision tree, depth 3, min leaf 500 |
| KNN-EV | 250 nearest neighbours on 20 principal components of the timeline ("days like today") |
| KNN-SH | 250 nearest neighbours on the z-normalised shape of the last 24 five-minute returns (price-shape matching) |
| NULL | LGBM trained on day-shifted labels (the reference) |

**Eligibility and winner (frozen rule):**
- A model is ELIGIBLE if its test AUC is above 0.5 in at least 10 of the 15 years **and** its mean yearly AUC is above NULL's mean + 2 SE (SE across years).
- The WINNER is the eligible model with the highest mean yearly AUC. No eligible model means "no winner".

## 4. Part M — meta-labelling (the highest prior)
- **Base trades:** every v36 noise-band trade on SPX500 (5,463). Each is given the latest timeline row at or before its signal bar, plus the trade's side.
- **Model:** LGBM predicts whether the trade wins (gross > 0), yearly walk-forward as above.
- **Rule:** keep a trade if its prediction is at or above the 40th percentile of the previous test year's predictions (keep about 60%).
- **M passes if**, over 2013–2026 and clustered by date:
  - the value of the filter (P&L change from dropping trades, per trade offered) is > 0 with t ≥ 2.0; **and**
  - the kept trades' net is > 0 with t ≥ 2.0.

## 5. Part D — deep learning (run on Dave's Mac)
- **Model:** a 1D CNN on the last 78 z-normalised five-minute returns plus an MLP on the timeline, same folds, early stopping on the last ~126 days, seed 39.
- **Reference:** DEEP-NULL, the same network trained on day-shifted labels.
- **Rules:** the same eligibility rule as Part A, with DEEP-NULL as its reference. If DEEP is eligible it joins the winner race.
- The race is decided when DEEP's results arrive. If Part D is never run, the race is decided without it, and that is stated.

## 6. Power and blind spots
- Each test year has about 5–6k hit points, so the yearly AUC SE is about 0.008 and the mean over 15 years is precise. The binding limit is overfitting and multiple comparisons, not sample size. That is why the NULL reference and the "10 of 15 years" rule exist.
- The best AUC so far is about 0.55–0.58 (v37.3). Even a winner here will be economically thin until it is confirmed on new data.
- No order-book, options-flow or news-text data is included.

## 7. One run of each part. No change of models, parameters, folds or rules after it.
