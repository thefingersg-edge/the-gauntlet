# RESULT — FLOWS-4: the macro-announcement premium when VIX is high. DEAD (K1, K2, K3).

```
SPEC:     PREREGISTRATION_ANNOUNCE.md (sha 9705a725…) + amendment A1 (056f6f5d…)
METHOD:   announce.py   log data/announce_run.log   result data/announce_result.json
DATA:     SPX500_USD / DE30_EUR M15 bid+ask 2005-01-03 .. 2026-08-31 (5,588 days, 11 dropped <40 bars)
          announce_events.csv cfcbad38… (CPI 277, NFP 265, GDP 258, ISM 260, FOMC 180), VIXCLS f7d1f93f…
RUN:      2026-09-27, once, in the Cowork VM
VERDICT:  G1 FAIL  G2 FAIL  G3 FAIL  G4 FAIL  G5 PASS  ->  DEAD
```

*Measurement, not a recommendation. Not financial advice.*

## The registered test

| | estimate | t | gate |
|---|---|---|---|
| θ: non-FOMC announcement excess on **high-VIX** days (460 days) | **−0.29 bp** | −0.04 | G1 FAIL |
| b3: high-VIX minus low-VIX | −12.30 bp | −1.44 | G3 FAIL (wrong sign) |
| θ by era | E1 +3.41, E2 +10.90, **E3 −14.49** | +0.22 / +1.13 / −1.07 | G2 FAIL |
| trade, ask in / bid out, on A∧HIGH days | +4.14 bp net | +0.59 | G4 FAIL (E3 net −2.20) |

The claim fails as registered. On a high-VIX evening, a CPI, payrolls, GDP or
ISM release the next day adds nothing to the S&P CFD's return. VIX
conditioning pointed the wrong way.

## What the secondary table shows (descriptive, gates nothing)

- **The unconditional premium is there, but on LOW-VIX days.** b1, the
  low-VIX announcement excess, is **+12.0 bp, t 3.23**, and it is positive in
  every era (E1 +13.2, E2 +8.0, E3 +15.2 bp; t 1.65 / 1.72 / 2.46). That fits
  Ai, Bansal & Guo's unconditional ~10 bp. It is the **opposite** of the
  uncertainty story this test registered. It was found here, so it is a
  **post-hoc** observation, not a result. Confirming it honestly needs
  forward data. At about 25 low-VIX announcement days a year and a
  day-return standard deviation near 0.8%, that means roughly 7–9 years.
- **FOMC days:** +51.2 bp on high-VIX days (n 86) against +6.2 bp on low (n
  94). This agrees with fastbot v10 Gate D. It is not new.
- **By release type, high VIX:** GDP **+31.6 bp, t 2.46, BH q 0.06**; CPI −2.0,
  NFP −21.1, ISM −4.1. GDP clears q < 0.10 among the four secondary tests. It
  is one of four, it is not a gate, and it has not been checked in another
  sample.
- **Where the day's return sits (08:30 releases, high VIX):** +1.95 bp before
  08:30 and +5.10 bp after, against +5.05 / +0.54 on high-VIX control days.
- **DE30:** θ −7.25 bp (t −0.87). Same answer.

## Cost context

Opening spread paid on the trade: 1.53 bp. Gross mid on A∧HIGH days was +5.55
bp. So cost was not the reason it failed: there was no premium to pay for.

## What this closes

The "uncertainty premium on macro release days" family is closed for CPI,
NFP, GDP and ISM on the S&P and DAX CFDs, together with fastbot v10/v14 for
the pre-release window. FOMC stays as v10 left it. Candidates for a **new**
pre-registration, to be tested on forward data only: the low-VIX
announcement-day drift and GDP days.
