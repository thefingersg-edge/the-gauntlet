# RESULT — GLDFLOW2: monthly gold-ETF flows do not predict next month's gold (FAIL, as predicted)

```
SPEC:     PREREGISTRATION_GLDFLOW2.md (sha da425cab…), frozen 2026-10-16 before any number
DATA:     data/gold/WGC_ETF_Flows_2026-09.xlsx (World Gold Council Goldhub, downloaded by Dave; sha 54c8ae7a…); OANDA XAUUSD 15m
METHOD:   scripts/gldflow2_run.py (sha c79d8859…), self-test PASS
RUN:      2026-10-16, once.   LOG: data/gold/run_gldflow2.log
VERDICT:  G1 FAIL, G2 FAIL -> FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

| | n months | slope (bp next-month gold per 1% change in tonnes) | NW t | 2006–12 | 2013–19 | 2020–26 |
|---|---|---|---|---|---|---|
| **GLD tonnes (primary)** | 244 (2006-04 → 2026-07) | **−0.1** | **−0.01** | −23.3 (t −1.49) | +9.4 (t +0.81) | +26.4 (t +1.57) |
| All gold ETFs (reported) | 244 | −0.9 | −0.07 | −27.9 | +12.5 | +28.2 |

- **No signal overall.** Last month's GLD buying or selling says nothing about next month's gold price.
- **Flows follow price.** Same-month correlation of flows with gold is +0.44, so flows mostly report what gold already did.
- **The sign has flipped across eras:** negative in 2006–12, positive since 2013. None of the three eras is significant.
  - The recent-era slope (+26 bp, t 1.57) fits Dave's "markets changed" view, but at this sample size it is indistinguishable from noise. It is noted here, not promoted.
- **Quintile gap:** GLD's top-minus-bottom quintile is +123 bp/month, but the regression slope is about zero. So a few extreme months drive the gap, not a steady relationship.
- **Sample end:** the sample stops at 2026-07 because the gold price cache ends before the August window closes. One extra month would not change the verdict.
- **GLDFLOW1** (the weekly version) stays pending until daily SPDR holdings history is available. On this evidence the prior is FAIL.
