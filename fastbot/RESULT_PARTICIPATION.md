# RESULT — v29 Part 1: does participation move the bounce? No.

```
RUN:      2026-09-25   SPEC: PREREGISTRATION_v29 section 3 (sha256 checked)
CODE:     premarket_participation.py 1.0
SAMPLES:  S1 CPI+payrolls 2,981   S2 claims 4,820   S3 control 23,377
VERDICT:  G1 FAILS (b +0.055, t +1.36). G2 not reached. As predicted.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.** Inputs and caveats: PROVENANCE.md.

Gate 0: 31,178 trades matched v27's file, max difference 5e-07 bp.

```
fade/sigma = a + b ln(P)       n       b       t    raw bp per ln P      t
S1 CPI + payrolls           2981  +0.055  +1.36              +1.15  +1.14
S2 claims                   4820  -0.027  -0.32              -0.09  -0.08
S3 control                 23377  -0.060  -0.92              -0.09  -0.16

thirds of P (tick count against its own trailing median), mean fade bp
S1   P~0.48  +1.99    P~1.09  +4.69    P~2.08  +3.50
S2   P~0.57  +1.22    P~1.01  +0.44    P~1.99  -0.13
S3   P~0.57  -0.14    P~1.00  +0.04    P~1.94  +0.60
```

**How many participants showed up does not predict the bounce.** The
slope is small, its sign disagrees between release types, and the thirds
are non-monotonic on the release sample. The stale-quote story (b < 0)
and the crowded-flow story (b > 0) both fail to find support.

Predictions: G1 fails — RIGHT. G2 not reached — RIGHT.

Mechanism scoreboard, updated: overshoot, selection, the 09:30 open,
risk premium, absorption-vs-information, and now participation. Part 2
— the content of the release — is registered and waiting on data.

---

**Investigation forty-five, Part 1.**
