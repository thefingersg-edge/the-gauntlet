# PREREGISTRATION v59 — slow macro in the event timeline: do credit, yield-curve, policy, oil, financial-conditions and jobless-claims states add direction information?

Written and frozen 2026-10-10, before any v59 data was pulled, any timeline built or any model fitted.
- The FRED **monthly** series pulled for CYCLES2 have been looked at only at bear-market peaks (RESULT_CYCLES2_F), never against intraday direction.
- The daily series named below have not been pulled at all.

Scripts (to be written and frozen **before** the data lands; shas into PROVENANCE):
- `scripts/fred_v59_pull.py`: Mac-only pull of the daily and weekly FRED series below into data/v59/fred/.
- `scripts/tl_build4.py`: tl_build2 unchanged, plus the slow-macro family.
- `scripts/v59_build.py`: builds the timelines; runs Gate 0.
- `scripts/macro_v59.py`: predicts, then tests (the v54 procedure with the market and the features swapped).

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. Why, and the rules this follows (TIMELINE_LIVING.md)
- The timeline already has the **times** of CPI, NFP, claims and FOMC, plus the 2-year yield, the dollar, gasoline, VIX, the VX curve, SKEW, AAII, COT and put/call. v54 added market internals: FAIL.
- It has no **slow macro state**: credit stress, curve shape, policy direction, the oil trend, broad financial conditions, or the jobless-claims level.
- Rule: stamp every value when it was known, and add a self-test that fails if a value is stamped early.
- Rule: evidence must come from **data nobody has looked at** for timeline direction.
  - US30 and NAS100 (v54) and UK100, JP225, AU200, EU50 and DE30 (v38/v40) have all been used.
  - This test is scored on **US2000 (Russell 2000 CFD)**, which appears in no script, pre-registration or result in this repo. A US small-cap index is also the market most exposed to credit and the economy.

## 2. Revision safety, decided now
FRED serves *today's revised* history. Monthly activity series (payrolls, industrial production, unemployment, permits, sentiment) are revised after release, so their history leaks information a trader didn't have. **They are excluded.**

Only market-based or lightly-revised series are used:

| family | FRED series | frequency | stamped known at (ET) | events | states |
|---|---|---|---|---|---|
| credit | DBAA − DAAA | daily | 18:00 on the **next** business day | cs_up20 / cs_dn20 (20-day change ≥ +0.20 / ≤ −0.20 pp) | cs, cs_chg20 |
| curve | T10Y3M | daily | 18:00 next business day | yc_inv (crosses below 0) / yc_uninv (crosses above 0) | yc, yc_chg20 |
| policy | DFF | daily | 18:00 next business day | fed_up (DFF − DFF 5 obs earlier ≥ +0.20) / fed_dn (≤ −0.20) | dff_chg60 |
| oil | DCOILWTICO | daily | 18:00 next business day | oil_up10 / oil_dn10 (20-day return ≥ +10% / ≤ −10%) | oil_ret20 |
| conditions | NFCI | weekly | Wednesday 08:30 after the week it describes | nfci_x0_up / nfci_x0_dn (crosses 0) | nfci |
| claims | ICSA | weekly | Thursday 08:30 after the week it describes | claims_up15 (4-week average ≥ 1.15 × its lowest value over the prior 26 weeks) / claims_dn15 (4-week average ≤ 0.85 × its highest value over the prior 26 weeks) | claims_z (z of the 4-week average vs prior 52 weeks) |

**That is 12 events (minutes-since) and 9 states, 21 new features.**
- Decisions run 09:40–13:45 ET, so daily values are first usable the session after their stamp.
- **Self-test in tl_build4:** a decision at 13:45 on Thursday 2020-03-19 must see the claims print of 2020-03-19 08:30 (week ending 14 Mar) but **not** the 2020-03-26 print. A 13:45 decision on 2020-03-17 must see the DBAA value of 2020-03-13, not that of 2020-03-16.
- **Disclosed residual leak:** NFCI and ICSA are revised slightly after release. Only the current vintage is available here, and that is accepted.
- **Missing early values** are median-imputed, as for the existing macro features.

## 3. Step 0 — Gate 0 (must pass before any prediction)
SPX500 is rebuilt by tl_build4. Its first 125 columns, labels, barriers and spreads must equal data/timeline_v37/matrix.npz **exactly** on every row. Otherwise stop.

## 4. The test (v54's frozen procedure)
- **Models:** FOREST (300 trees, min leaf 200, sqrt features, seed 7, median impute), fitted per test year on **SPX500 hit points dated before that year**:
  - BASE = the 125 original features;
  - AUG = BASE + the 21 new features.
- **Scored on** US2000, US cash session, with its own v37-style timeline and ±1σ(2h) direction labels.
- **Window:** 2013-01-01 → 2026-08-14, the same as v54 (the end of the SPX matrix).
- **Data needed:** OANDA US2000_USD 5-minute bid/ask from 2005, pulled on the Mac into data/ (pull_m1.py, as v38).
  - If OANDA's US2000 history starts after 2013, the window starts at the first full year of data. This is written now.
  - If it has fewer than 5 full years, the test is **not run** and is reported as infeasible.

## 5. Gates (PASS needs both)
- **G1:** pooled US2000 hit points, the paired day-bootstrap (1,000 resamples, **seed 59**) 95% lower bound of AUC(AUG) − AUC(BASE) is **> 0**.
- **G2:** AUC(AUG) − AUC(BASE) is **> 0 in each era**: 2013–17, 2018–21, 2022–26.
- **Reported, gating nothing:**
  - BASE's own AUC on US2000 with its bootstrap lower bound. This is a third out-of-market replication of the v40 signal.
  - The importance rank of the 21 new features.
  - AUG − BASE on SPX walk-forward (descriptive).

## 6. Prediction, written now
**Prior: low.** These states change over weeks. The labels cover two hours. RESULT_CYCLES2_F found the monthly versions uninformative even at bear-market tops.

**Prediction:** G1 FAIL. A PASS would be the first evidence that slow macro improves intraday direction.

## 7. What follows
- **PASS:** tl_build4 joins the timeline (as a candidate default). A new forward record needs its own pre-registration. The live v41 record stays frozen.
- **FAIL:** tl_build4 stays a library only, and the slow-macro family is closed for the timeline.

## One pull, one build, one predict stage, one test stage. No change of features, model, market, window or gates.
