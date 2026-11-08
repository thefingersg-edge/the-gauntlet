# PREREGISTRATION v57 — is the v56 breadth effect just high VIX? A measurement, not a backtest

Written and frozen 2026-10-02, before any S&P forward return has been joined to VIX in this sample. Only VIX's history length and range have been read (5,000 rows, 2006-12-15 to 2026-10-01).

- **Harness:** scripts/breadth_vix_v57.py v1.0. It reuses breadth_v56's `sessions`, `fwd` and `nw_ols` unchanged.
- **Data:** data/tv_20261001, the same frozen snapshot v56 used (MANIFEST sha256 b287eb00…), and OANDA SPX500 15m bid/ask (data/v24).

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. Why
- v56 passed: S&P breadth (S5FI, % of members above their 50-day average) predicts a stronger next month, slope −23.87 bp per 10 pp, NW t −2.06. Low breadth (S5FI < 20) carries +229.6 bp.
- The audit (AUDIT_v54_v56.md) found the code correct, but the evidence borderline: rotation null p 0.048, and NW t overstated by about a sixth.
- **Washed-out breadth and high VIX are the same days, mostly.** fastbot has already measured the variance premium at z = 10. If breadth is a restatement of VIX, v56 found the known premium again rather than a new effect. This decides which.

## 2. Definitions (all as v56 unless stated)
- **r20(t):** mid open of the 09:30 ET bar on session t+1 to mid close of the 15:45 bar on session t+20, in bp. Sample t from 2007-01-02, exit on or before 2026-09-25.
- **x(t):** S5FI / 10.
- **low(t):** 1 if S5FI < 20.
- **v(t):** ln(VIX close on t). Available 16:15 ET on t, so before the t+1 entry. Days without a VIX value are dropped (reported count).
- **SEs:** Newey–West (Bartlett) lag 20.

## 3. Gates. "BREADTH ADDS BEYOND VIX" needs all three; otherwise the verdict is "NOT SHOWN BEYOND VIX".
- **G1:** in OLS r20 ~ 1 + x + v, the coefficient on x is < 0 with NW t ≤ −2.0.
- **G2:** rotation null (the audit's lesson).
  - By Frisch–Waugh, residualise x on [1, v] and r20 on [1, v].
  - Rotate the x-residual circularly against the r20-residual by 2,000 offsets drawn uniformly from [252, n − 252], seed 57.
  - Compute the NW t each time. The one-sided p = share of rotated t ≤ the observed partial t, and it must be **≤ 0.05**.
- **G3:** in OLS r20 ~ 1 + low + v, the coefficient on low is > 0 with NW t ≥ 2.0.

## 4. Reported, gating nothing
- corr(x, v).
- The VIX-only slope (r20 ~ 1 + v) with NW t.
- The median and quartiles of VIX on low-breadth days and on the rest.
- Within VIX ≥ 25 only: the mean r20 on low-breadth days minus the rest, with NW t.
- G1's model with a third control, the SPX 50-session trailing return (15:45 mid on t vs on t−50).
- h = 5 versions of G1 and G3.

## 5. Prediction, written now
- S5FI and ln VIX are strongly correlated; I expect |corr| ≈ 0.6–0.8.
- **Prediction:** G1 FAIL. The breadth coefficient shrinks toward zero (|t| < 1.5) once VIX is in, and VIX alone carries most of v56's slope.
- **Verdict predicted:** NOT SHOWN BEYOND VIX. v56 would then be read as the variance premium seen through breadth.

## 6. What follows
- **FAIL (predicted):**
  - v56's PASS stands as registered, but PROGRAMME.md files it under premia (§3), not as a new timing signal.
  - No breadth trading rule is pursued.
  - The S5FI < 20 forward record (proposed in RESULT_BREADTH_v56) is not worth a separate registration, because the VIX premium is already measured.
- **PASS:** breadth carries information that VIX does not. The forward record and a survivorship-free rebuild each get their own pre-registration.

## One run. No change of data, sample, controls, horizon or gates.
