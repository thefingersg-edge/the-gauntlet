# RESULT — v57: the v56 breadth effect is NOT SHOWN BEYOND VIX. The verdict was predicted; the mechanism was not.

```
SPEC:     PREREGISTRATION_v57.md  sha 2ed58dfb…  (frozen in commit 15c6c22)
METHOD:   breadth_vix_v57.py 1.0 (sha b256aadc…); data/tv_20261001 (MANIFEST b287eb00…); OANDA SPX500 15m bid/ask (data/v24)
LOG:      data/v57_run.log
RUN:      2026-10-02
VERDICT:  NOT SHOWN BEYOND VIX  (G1 FAIL t -1.73, G2 FAIL rotation p 0.075, G3 FAIL t +1.91)
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## The registered run (h = 20, n 4,896, 326 low-breadth days, no VIX gaps)
| model | breadth term | VIX term |
|---|---|---|
| v56, breadth alone | −23.87 bp per 10 pp (t −2.06) | — |
| r20 ~ S5FI + ln VIX (G1) | **−18.97 (t −1.73)** | +59.3 (t +0.63) |
| FWL partial, rotation null (G2) | t −1.73, **p 0.075**, null sd of t 1.19 | — |
| r20 ~ (S5FI < 20) + ln VIX (G3) | **+195.3 bp (t +1.91)** | +53.8 (t +0.59) |

All three gates fail.

## Reported (not gated)
- **corr(S5FI, ln VIX) = −0.49.** That is lower than the −0.6 to −0.8 I predicted.
- **VIX alone:** r20 ~ ln VIX is +115 bp per unit (t +1.27). In this sample VIX is a *weaker* predictor of the next month than breadth.
- **VIX on low-breadth days:** quartiles 25.0 / 30.7 / 44.7, against 13.9 / 17.0 / 21.5 on the rest.
- **Within VIX ≥ 25** (872 days, 244 low-breadth): low minus rest +165 bp (t +1.15, indicative).
- **With the 50-day trailing S&P return added:** breadth −12.72 (t −0.87), ln VIX t +0.53, 50-day return t −0.56. **Nothing survives** once the three collinear "the market has been falling" measures share the variance.
- **h = 5:** breadth beyond VIX −5.17 (t −1.46); low beyond VIX +44.8 (t +1.08).

## How to read it, plainly
- **What I predicted wrongly.** I expected VIX to absorb breadth: breadth's coefficient collapsing and VIX taking the slope. It did not. Breadth kept about 80% of its size. VIX carried little on its own, and its partial t is 0.6.
- **What actually happened.** v56 was a weak effect (rotation p 0.048) that shares its variance with two other measures of a falling market. Controlling for either costs enough to take it below the bar. With 26 independent low-breadth episodes, the data cannot say whether breadth, VIX or the drawdown is the carrier.
- **So the "variance premium in disguise" reading is not supported either.** I am not filing v56 under premia, as PREREGISTRATION_v57 §6 said I would on a FAIL. That instruction assumed VIX would absorb the effect, and it didn't. The honest label is: **one weak post-decline effect, carrier unidentified.**
- The rest of §6 stands. No breadth rule is pursued. A forward record is not registered: at about 1.3 episodes a year it would take decades to separate +200 bp from luck.
- **Rule 2 applies.** Breadth as a predictor of the S&P month is closed. A survivorship-free rebuild would refine a series whose effect is already not separable from VIX or the drawdown, so it is not worth sourcing for this question.

## What the programme learns
- v56 joins the pattern in PROGRAMME.md: effects that look directional sit on top of "being long after the market has fallen". That is the one place every measured premium in this programme lives.
- The audit's method point stands on its own. NW t on overlapping horizons was overconfident by about a sixth again here (rotation null sd 1.19), so future overlapping-horizon gates should register a rotation null.
