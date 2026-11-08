# PREREGISTRATION v37.3 — has the world changed? Recent-trained vs old-world-trained timeline models

Frozen 2026-09-26. Script: scripts/timeline_v37_3.py v1.0.
Inputs are pinned by sha256: matrix.npz 6fc354b2… (tl_build 1.1) and the v37.2 LOCK fb2f89ae….

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. Dave's hypothesis
Markets changed fundamentally after COVID: how businesses work, how people behave, who trades. A model trained on 2005–12 is "old-world". Trained on 2022–24, the timeline should predict direction better on the years that follow.

## 2. Part A — the post-COVID test
- **NEW model:** v37.1's direction model and parameters, unchanged. Trained on hit points dated 2022-01-01 → 2024-02-29, with early stopping on 2024-03-01 → 2024-08-14.
- **OLD model:** the v37.2 LOCK, unchanged.
- **ALL model:** trained on 2005 → 2024-02-29 with the same early-stopping slice (reported only).
- **Test window:** 2024-08-15 → 2026-08-14, the two years after the NEW model's training (the data ends 2026-08-14).
- **Honest caveat:** this window lies inside the v37.2 sealed period, so the OLD model has already been scored there once. It is unseen by the NEW model, not by the researcher.

**Gates:**
- **A1:** NEW test AUC above all 20 day-shift nulls (the NEW recipe refitted on day-shifted labels), and below the 0.65 leak void.
- **A2:** NEW − OLD test AUC > 0, with the lower end of a day-bootstrap 95% interval (1,000 resamples of days) above 0.
- **A3 (reported):** NEW model trades, using the 90th/10th percentiles of its predictions on the early-stopping slice, net of spread.

## 3. Part B — is "train on recent data" a real effect or luck?
- **8 rolling windows.** RECENT = the 3 calendar years before the test; ALL-PRIOR = 2005 up to the same point. Both stop early on the last 6 months of their span. Test = the next 2 calendar years.
- **Recent spans:** 2007–09, 2009–11, 2011–13, 2013–15, 2015–17, 2017–19, 2019–21, 2021–23.
- **B passes if** RECENT beats ALL-PRIOR on test AUC in at least 6 of 8 windows **and** the mean AUC gain across windows has t ≥ 2.0.
- Per-window bootstrap intervals are reported.

## 4. Power and blind spots
- The Part A test has about 2 years of hit points (roughly 2,700–3,000). The AUC SE is about 0.011, so A2 can resolve an AUC gain of about 0.03 or more.
- A gain that small would still be economically thin: v37.2's sealed AUC of 0.55 made +1.5 bp a trade.
- The NEW model has only about 2.6 years of training data, around 8,000 hit points. That is small for 125 features. "Recent but small" is traded against "old but large", and Part B measures that trade-off.
- The features are the v37 timeline, unchanged. Nothing new is added here.

## 5. One run.
