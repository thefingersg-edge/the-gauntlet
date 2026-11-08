# PREREGISTRATION v54 — market internals in the event timeline: do they add direction information?

Written and frozen 2026-10-02, before any v54 timeline has been built and before any model has been fitted on the new features. Nothing has been read from the new series except their history length, their range, and the comparison of put/call with the dead Cboe file (19 overlapping days in 2019; levels about 0.01–0.04 apart).

Scripts:
- scripts/tl_build3.py v3.0: tl_build2 unchanged, plus the internals family.
- scripts/v54_build.py: builds the timelines; Gate 0.
- scripts/internals_v54.py v1.0: predict, then test.
- Data: data/tv_20261001/, the frozen 2026-10-01 TradingView pull (tv_series.py 1.0). Its MANIFEST.json sha256 is b287eb00651b4cd9d43ffb4d567f681a1156dd20eecb674fa9890636d86bc9b3.

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. Why
- v40 found a small, real, transferable direction signal in the v37 timeline: AUC 0.512 on five unseen markets.
- The timeline has no **market-internals** family. Its only put/call input (the Cboe file) died on 2019-10-04, so `pc_x1_up/dn` has been constant in every training row since 2019. Its VIX term structure comes from continuous VX futures, which carry roll jumps.
- The TradingView connector supplies, from late 2006: put/call (USI:PCC), VIX3M (roll-free term structure), S&P breadth (% of members above their 50- and 200-day averages) and the NYSE advance/decline series.
- TIMELINE_LIVING.md asks for exactly this: new events stamped when known, a new pre-registration, and **evidence only from data nobody has looked at**.

## 2. The new features (20), fixed now. Thresholds are round conventional numbers.
| family | events (minutes-since feature) | states | known at (ET, same date) |
|---|---|---|---|
| put/call, USI:PCC (values outside [0.3, 3.0] dropped as bad prints) | pcc_x1_up, pcc_x1_dn (crosses 1.0) | pcc, pcc_z (z vs prior 252 obs) | 18:00 |
| VIX / VIX3M | vts_inv (ratio crosses above 1), vts_norm (back below) | vts | 16:15 |
| breadth, INDEX:S5FI and S5TH | s5fi_x20_dn/up, s5fi_x80_up/dn, s5th_x50_up/dn | s5fi, s5th | 18:00 |
| NYSE A/D, USI:ADD / ADV / DECL | add_thrust / add_washout (ADD z vs prior 252 obs > +2 / < −2), zweig_thrust (10-day EMA of ADV/(ADV+DECL) above 0.615 after being below 0.40 within 10 sessions) | add_z, adr10 | 18:00 |

- Decisions are taken 09:40–13:45 ET. Every new value is therefore first usable the **next** session.
- tl_build3's self-test plants a 13:45 decision on 2020-03-16 and requires it to see the 13 March breadth, not the 16 March value.
- Before 2007/2008 the new features are missing and median-imputed, exactly as the old macro features were in their early years.

## 3. Step 0 — Gate 0 (must pass before any prediction)
- SPX500 is rebuilt by tl_build3. Its first 125 columns, its labels, barriers and spreads must equal data/timeline_v37/matrix.npz **exactly** on every one of its 91,116 rows. Otherwise stop.

## 4. The test
- **Models:** FOREST, the frozen v39/v40 recipe (300 trees, min leaf 200, sqrt, seed 7, median impute), fitted twice per test year on **SPX500 hit points dated before that year only**:
  - BASE: the 125 original features (this is v40's model).
  - AUG: the same plus the 20 new ones.
- **Scored on** US30 and NAS100, US cash session, own v37-style timeline and ±1σ(2h) direction labels.
  - No timeline model has ever been fitted to, thresholded on or scored on either market's history.
  - NAS100 enters the live v41 record only from 2026-09-28, after this window.
  - The test window is 2013-01-01 → 2026-08-14, the end of the SPX matrix. That also keeps it clear of the 2026-09-12 phantom calendar rows.
- **Disclosure:** these markets' prices have been used before for other questions (for example v38 Part B ran the noise-band rule on NAS100 and US30 from 2013), but never for direction prediction from the timeline.

## 5. Gates. PASS needs both.
- **G1:** pooled over US30 + NAS100 hit points, the paired day-bootstrap (1,000 resamples, seed 54) 95% lower bound of AUC(AUG) − AUC(BASE) is **> 0**.
- **G2:** AUC(AUG) − AUC(BASE) is **> 0 on each market** and **in each era** (2013–17, 2018–21, 2022–26, pooled markets).
- **Reported, gating nothing:**
  - BASE's own AUC on US30 + NAS100 with its bootstrap lower bound (a v40-style replication on two more unseen markets).
  - The SPX walk-forward difference (SPX is the training market; descriptive).
  - The importance rank of the 20 new features.

## 6. Budget and prediction, written now
- v40's pooled AUC SE was about 0.003 on about 160k points. The paired difference is tighter, because BASE and AUG share 125 features and the seed. **The minimum detectable difference is roughly +0.003 to +0.005.**
- **Prior: low.** Breadth and A/D largely restate the index's own trend and the VIX features already in BASE. US30 and NAS100 move closely with SPX, so this is a weaker independence check than v40's.
- **Prediction:** G1 FAIL (lower bound ≤ 0), with the new features ranked mostly below the median. A PASS would be the first evidence that the timeline can be improved rather than only confirmed.

## 7. What would follow
- **PASS:** the internals family joins the timeline (tl_build3 becomes the default). The live v41 record stays frozen; a new forward record of AUG needs its own pre-registration.
- **FAIL:** tl_build3 is kept as a library only, and the internals family is closed for the timeline. The series stay available for other questions (v56).

## One build, one predict stage, one test stage. No change of features, model, markets, window or gates.
