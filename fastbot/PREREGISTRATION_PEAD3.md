# PREREGISTRATION PEAD3: earnings reaction (EAR) confirmed by the reported earnings surprise (SUE)

Frozen 2026-10-03. Harness: `singlestock/batch2_run.py pead3`, which pins this file. SUE events come from Sharadar fundamentals (ARQ, as reported), built by `ss_events2.sue_events`. Built 2026-10-03: 425,561 events. Only counts have been looked at.

I am not a financial adviser. This is a measurement, not a recommendation.

## Question
- Brandt et al. found that combining the price reaction (EAR) with the earnings surprise (SUE) roughly doubled the drift.
- PEAD1 showed EAR alone is real gross but too small for costs.
- **Does requiring a confirming SUE raise the drift enough to pay the full cost?**
- The SUE conditioning has **not** been looked at on this data.

## Definition
- **Base events:** PEAD1 long events (top-decile EAR, M+S).
- **SUE:** (EPS_q − EPS_{q−4}) / SD of the previous 8 seasonal EPS changes. It uses the first filing for each period (no restatements), and is **known at the 10-Q/10-K filing date** (Sharadar `date`).
- **Confirmation:** the first SUE event for the same ticker filed 0–60 days after the 8-K date has SUE ≥ the 70th percentile of all SUEs filed in the prior 91 days (point-in-time).
- **Entry:** the **open** after the filing date. **Hold:** 60 trading days. **Return:** excess over the band.
- **Cost: the full EDGE spread plus commission**, as in PEAD1. This is the conservative model, so a pass does not rely on the auction assumption.
- **Reported (not gated):**
  - closing-auction execution with 25% cost;
  - SUE alone (top decile, all M+S filings);
  - EAR-confirmed against EAR-not-confirmed.

## Gates (single test, t ≥ 2.0, quarter-clustered)
G1, G2 (including 2018–26 with t ≥ 2.0), G3 and G5, exactly as in PEAD2.

## Budget
- PEAD1 had about 24,000 M+S longs. Confirmation by the top 30% of SUE should keep roughly 40%, so **about 9,000–10,000 events**, and about 3,500–4,000 on 2018+.
- 60-day excess RMS is about 21–25%. **MDE is about 0.6% (event level) to 1.5% (clustered)**, against a full cost of about 1.1%.
- **The drift must roughly double from PEAD1's 1.1% to pass. That is the literature's claim.**

## Prediction
G1 uncertain. G2 likely FAIL on 2018+.

## One run.
