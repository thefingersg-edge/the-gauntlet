# RESULT — v42: last-30-minute momentum on negative-GEX days. FAIL, narrowly, and in the direction the mechanism predicts.

```
SPEC:     PREREGISTRATION_v42.md  sha bd1cb691…
METHOD:   gex_v42.py 1.0; SqueezeMetrics DIX.csv (sha b64bccce…); log data/gex/run_v42.log
RUN:      2026-09-27
VERDICT:  H1 FAIL (difference t 1.98 < 2.24)   H2 FAIL (wrong sign)
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## Numbers (gross bp per instrument-day, SPX/NAS/US30, 2011-05 → 2026-08; t clustered by date)
```
                           negative GEX          positive GEX         difference          eras (neg-pos)
H1 last-30 momentum        +7.45 (t 2.04, n 1,022)  +0.18 (t 0.52, n 10,357)  +7.27 (t 1.98)   +5.26 +15.21 +3.53
H2 noise-band N            -0.45 (t -0.08, n 731)   +4.20 (t 4.57, n 6,168)   -4.65 (t -0.81)  +1.17 -11.92 -3.23
net on negative-GEX days:  H1 +6.23 (t 1.71)   H2 -2.52
```

## Read it plainly
- **H1 behaves exactly as Baltussen et al. predict.** End-of-day momentum is about +7 bp on the 9% of days when dealers are short gamma, and zero on all other days. The difference is positive in all three eras. It misses the pre-registered bar by a hair (t 1.98 against 2.24), so it is a FAIL, and it is the closest near-miss in the programme with a named mechanism behind it.
- The VIX stand-in (v36 G, v38 B) pointed the wrong way because VIX is not dealer gamma. The real input restores the textbook sign.
- **H2: noise-band momentum does NOT come from dealer gamma.** It lives on positive-GEX days (+4.2 bp, t 4.6) and vanishes on negative ones. Whatever drives our only before-costs edge, it is not dealer hedging.
- **Why it is hard to use:**
  - There are only about 22 negative-GEX dates a year (bunched: 104 of them in 2022).
  - Confirming +7 bp forward at t ≥ 2 needs roughly 80–100 such dates, which is 4–5 years.
  - GEX must be downloaded by hand.

## Status
Recorded as a FAIL with a mechanism-consistent pattern. Candidate for a forward record (pre-register it separately if wanted), with GEX refreshed monthly alongside the v41 inputs.
