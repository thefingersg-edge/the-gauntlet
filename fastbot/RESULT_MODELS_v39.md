# RESULT — v39: six model types on the timeline. Direction information is real, faint, and not yet worth money.

```
SPEC:     PREREGISTRATION_v39.md  sha f42c19b2…
METHOD:  v39_models.py 1.0 (logs data/v39/run_models.log, run_meta.log; per-year data/v39/model_years.csv)
          v39_deep.py -- Part D, to be run on Dave's Mac (pending)
VERDICT:  Part A winner (frozen rule): FOREST   Part M: FAIL   Part D: DEEP eligible, ranks below FOREST (winner unchanged)
```

**I am not a financial adviser. This is a measurement, not a recommendation.**
All SPX dates used here had already been looked at (v37–v37.3). This can pick a winner, not confirm one.

## Part A — direction AUC by year, 2012–2026 (yearly walk-forward, expanding window)
```
model    mean AUC  years>0.5  traded 2013-26 (net of spread)   eligible
FOREST   0.555     14/15      2,722 trades  -0.23 bp  t -0.42    yes  <- WINNER
LGBM     0.544     14/15      3,068         -0.29      -0.49     yes
KNN-EV   0.534     13/15      4,057         -0.86      -1.91     yes
RULES    0.533     15/15      2,560         -0.16      -0.24     yes
LOGIT    0.525     12/15      3,099         -2.28      -3.78     yes
KNN-SH   0.502      9/15      5,463         -1.41      -3.35     no   (price-shape matching)
NULL     0.503      8/15      reference: mean + 2SE = 0.514
```

## Part M — meta-labelling the noise-band trades
```
all trades 2013-26   3,407  net +0.01 bp   t 0.01
kept (top ~60%)      2,113  net +1.12 bp   t 1.28
value of the filter          +0.69 bp/trade offered, t 1.56   -> FAIL (needs t >= 2.0 on both)
the "will this trade win" model scored AUC 0.51-0.60, above 0.5 in 14 of 14 years
```

## Read it plainly
- **Five of six model types find direction information above the null, in nearly every year since 2012.** This is the most consistent signal the project has measured. The best is the random forest, at 0.555 on average and positive in 14 of 15 years.
- **None of it makes money after costs** as a stand-alone trade. An AUC of about 0.55 is too weak to beat the spread with 1σ, 2-hour trades.
- **Price-shape matching (KNN-SH) finds nothing,** no better than the null. Past 2-hour chart shapes do not predict the next 2 hours. The events and states around the price carry the information; the drawn shape does not.
- **Meta-labelling helps a little but not enough.** Filtering the noise-band trades lifted them from +0.0 to +1.1 bp a trade (t 1.3). The filter's win-prediction was above chance in every year, which makes it the best candidate to combine with cheaper execution or new instruments.
- **What the readable rule tree says** (fitted on 2005–2025, descriptive only):
  - The strongest split is the 5-day return. After a strong 5-day rally, with price above yesterday's close, the next 2-hour move is down-first 64% of the time (2,816 vs 1,586). That is short-term overextension reversing.
  - Below yesterday's close but not through the noise band's lower edge, up-first is slightly more likely.
  - FOMC press-conference timing and dollar moves also appear.
  - None of this is new theory. It is short-term reversal, which the timeline rediscovered on its own.

## Next
- **Part D:** run v39_deep.py on the Mac; it joins the race if eligible.
- **Confirmation (to be pre-registered as v40):** the winner (FOREST) and the meta-filter, frozen, on the v38 indices once pulled (scripts/run_v38_pull.sh), and on forward data. tl_build must first be generalised to each index's session times.

## Part D — deep learning (run on Dave's Mac, 2026-09-26; data/v39/deep_years.csv)
```
DEEP        mean AUC 0.527   years > 0.5: 12/15   traded 3,881 trades, net -1.74 bp
DEEP-NULL   mean AUC 0.507   reference mean + 2SE = 0.518
```
- DEEP is ELIGIBLE (above its own null in 12 of 15 years), but it ranks below FOREST (0.555), LGBM, KNN-EV and RULES.
- **The winner stays FOREST.** A CNN on 78 bars of price shape plus the timeline adds nothing over a random forest on the timeline alone. That fits KNN-SH: price shape carries no direction information.
- The trading thresholds (last year's 10/90 percentiles) were unstable for the network, whose output scale drifts year to year. Some years produced 0–8 trades. This is reported as found, not fixed after the fact.
