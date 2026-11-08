# PREREGISTRATION SPIN1: do spun-off companies beat the market in their first year?

Frozen 2026-10-04, before any spin-off return has been computed (only event counts by year have been looked at). Harness: `singlestock/spin1_run.py`, which pins this file.

I am not a financial adviser. This is a measurement, not a recommendation.

## Background
Classic studies (Cusatis, Miles & Woolridge 1993; McConnell & Ovtchinnikov 2004) found spun-off companies beat the market by roughly 10–20% over 1–3 years, partly because index funds and parent shareholders sell the new stock regardless of value. It is well known, so it may have faded. Never tested here.

## Recent-regime rule (POLICY_RECENT_REGIME.md), decided before looking
**Primary window: entries 2013-01-01 to 2025-09-30** (exits by 2026-09). Earlier years reported only.

## Definition (fixed)
- **Events:** Sharadar `actions` rows `spunofffrom` (ticker = the new company). The new company must be in the price store (US domestic common stock, NYSE/NASDAQ/NYSE American).
- **Entry:** closing auction of the **2nd trading day** of the new company's prices on or after the action date (avoids the first, often when-issued, day). **Hold:** 250 trading days, exit in the closing auction (or the last price if it delists; −30% if delisted for cause, as the engine).
- **Return:** excess over an equal-weighted mix of the L, M and S liquidity-band benchmarks (the new company has no liquidity history at entry).
- **Cost:** 0.50% round trip (above the measured auction cost of 0.1–0.2%) plus 2 × $0.0035/share.
- **Clustering:** entry quarter.

## Gates
- **G1:** mean net excess > 0 with t ≥ 2.0 (primary window).
- **G2:** positive in both 2013–2019 and 2020–2025.
- PASS needs both.

## Reported (not gated)
1998–2004 and 2005–2012; 125-day hold; median and share positive; the parent company over the same 250 days.

## Budget
About 330 spin-offs 2013–25, fewer after the store filter (say 250). With a 12-month excess SD of about 45%, the standard error is about 3% (more with clustering): only an effect of about 6% or more will pass. The classic estimates are above that; a decayed effect will not pass.

## One run.
