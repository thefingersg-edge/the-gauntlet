# PREREGISTRATION v50.1 — amendment to v50, frozen 2026-09-28, BEFORE the fear table was built or joined to any price

Parent: PREREGISTRATION_v50.md (sha 8560ed09ba26aad15dc3e637340203c8fc70d7fd57d57bfc10bdabfebcfda269). Everything not changed here stands as written in v50. The harness pins both files.

I am not a financial adviser. This is a measurement, not a recommendation.

## What was learned from the raw files' structure (headers and date ranges only; no values compared with anything)
- **EPU daily** (daily_policy_index) runs 1985-01-01 → 2026-09-27.
- **GPR daily** (GPRD) runs 1985-01-01 → 2026-09-21.
- **TPU daily** (sheet TPU_DAILY, TPUD_index) **starts only in 2015-01-01** and runs to 2026-09-21. v50 assumed it had a long daily history; only the monthly TPU goes back to 1960.
- **Google Trends** came as **monthly, United Kingdom** exports, 2004-01 → 2026-09, not weekly US.

## Why an amendment is needed
v50 says the sample starts when every component has 500 days of history. With TPU from 2015, that would put the start in 2017. G1's 2005–12 era would have no data, so G1 could not pass by construction, and the power in the budget would not hold. v50 did not intend that, and it would waste the test.

## Changes (fixed now)
1. **Primary composite:** C = mean(z_EPU, z_GPR). This has the same A_i and z_i definitions and the same t−2 timing as v50. G1, G2 and G3 are all computed on this C over the full sample (expected start 2006).
2. **The three-component composite C3 = mean(z_EPU, z_GPR, z_TPU)** is run on its own available sample (from about 2017) and is **reported only**. There is no gate.
3. **TPU zeros:** the early TPU daily index contains zeros. For TPU only, A_i uses log(mean + 1). This affects only the reported C3.
4. **Google Trends** stays reported only: monthly UK search interest against the next calendar month's mean SPX500 log RV.
5. **Calendar days:** the index series are calendar-daily. The "7 days" and "250 days" in A_i and z_i are **calendar days** for the 7-day mean, and **the last 250 index observations** for the 250-day mean and the SD. "Dated t−2 or earlier" is calendar date ≤ target date − 2 days.

## Gate thresholds
HAC t ≥ 2.39 is unchanged. The budget holds as written, since the sample again starts around 2006.

## One run.
