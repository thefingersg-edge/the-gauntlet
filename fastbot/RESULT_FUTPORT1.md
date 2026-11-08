# RESULT — FUTPORT1: trend survives on real futures (Sharpe 0.44, every era positive); sign-based carry fails badly and sinks the portfolio

```
SPEC:     PREREGISTRATION_FUTPORT1.md  sha 76449002…  (frozen 2026-10-12 before any pull)
DATA:     Databento GLBX ohlcv-1d, 29 roots x c.0/c.1, 2010-06 -> 2026-09; total cost $2.60; all 58 shas verified
METHOD:   scripts/futport1_run.py  sha 6b28c761…  (frozen before the run; 5 self-tests pass)
RUN:      2026-10-12, once.   LOG: data/futport1/run_futport1.log
VERDICT:  FAIL on G1, G2 and G3
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

Live period 2012-05 → 2026-09 (14.8 years, after the 2-year warm-up), all scaled to 10% annual volatility:

| | Sharpe (× √yrs) | per year | eras 2010–15 / 16–20 / 21–26 |
|---|---|---|---|
| **portfolio (50/50)** | **−0.53 (−2.05)** | −2.9% | +5.3% / −29.2% / −19.2% |
| **trend sleeve** | **+0.44 (+1.71)** | +3.2% | **+13.9% / +15.4% / +18.6%** |
| carry sleeve | −1.20 (−4.63) | −9.1% | −3.4% / −73.8% / −57.1% |
| long-only, equal risk | +0.32 (+1.25) | +3.3% | −13.7% / +37.5% / +24.6% |

- **Trend works as the literature says, at the literature's size.** Sharpe 0.44, positive in all three eras, worst drawdown −14%. Trend and carry correlate +0.09.
  - **Strongest markets:** livestock (LE +0.72, HE +0.66), soymeal (+0.80), the equity indices (+0.2 to +0.6), heating oil and gold.
  - **Weakest:** the Swiss franc, platinum, and wheat/corn.
  - This is our best-behaved strategy family so far, but alone it misses the bar (t 1.7 vs 2.0). It was not gated by itself.
- **Carry as specified fails badly, and the reason is visible.**
  - The pre-registered carry signal was simply the *sign* of front-vs-second. Metals are almost always in contango, because the curve slope is roughly the interest rate. So the signal stays **short gold and silver for 14 years** while they rallied: GC carry Sharpe −1.8, SI −2.1, PL −1.35, HG −0.8.
  - FX carry by sign was also negative (AUD −0.71, CAD −0.63, GBP −0.51).
  - **Metals alone cost the portfolio about 42%.**
  - The published carry premium is measured *relative across markets* (long the highest carry, short the lowest), and for FX against interest rates. A plain time-series sign is a different thing, and we now know it doesn't work.
- **Implementability (reported):**
  - **$25k:** too small to hold even one micro contract of most markets.
  - **$100k:** rounding keeps only 4% of the target volatility, and the result correlates 0.59 with the intended portfolio.
  - **$1m:** it tracks well (correlation 0.94).
  - A diversified futures book is a six-figure-plus account.

## What it means
- **The documented trend premium is real on proper futures data at modest size: Sharpe ~0.4, t ~1.7 over 15 years.** That is consistent with OILCARRY1's oil carry and the VIX carry: real, small, slow edges.
- **The carry design was wrong, and that was our specification, not the data.** Testing the textbook version (cross-sectional carry ranking, with the interest rate netted out) would need a fresh pre-registration. The data is already on disk.
- **The headline still stands: no portfolio here passes our gates.** The trend sleeve is the strongest lead to come out of the whole programme. It is a lead for a forward record, not money.
