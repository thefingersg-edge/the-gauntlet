# RESULT — v31: can public data call the market move before 08:30? No.

```
RUN:      2026-09-25   SPEC: PREREGISTRATION_v31 (sha256 checked)
CODE:     fred_fetch_v31.py 1.0 (Dave's machine) + premarket_public.py 1.0
DATA:     petrol (EIA weekly) 2000-2026; ADP as published 2011-2023
          (FRED holds no earlier vintages and none after ADP's 2023
          relaunch); claims as published 2009-2026; 2y yield, dollar, VIX
VERDICT:  G1, G2, G3 all FAIL. Petrol calls CPI; nothing calls the
          market's move.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.** Inputs and caveats: PROVENANCE.md.

Gate 0: 31,178 trades matched v27, max difference 5e-07 bp. Dropped:
16 ADP vintages reporting the wrong month; 8 claims "dates" that carried
no new print (vintage dates, not release days).

## 1. Q1 — does it call the PRINT? (the positive control)

```
                                   as run              without 2020-21
petrol accel -> CPI m/m change     t +23.6, 82% sign   83% sign  (n 244)
ADP surprise -> payrolls surprise  t +50.6, 58% sign   55% sign  (n 103)
claims trend -> claims change      t  +5.4, 38% sign   37% sign  (n 737)
```

**Petrol calls headline CPI -- about five months in six.** ADP barely
calls payrolls; its huge t is the pandemic's 20-million-job months, and
without them it gets the sign right 55% of the time. Claims do the
OPPOSITE of trending: a jump in one week is usually partly reversed the
next (37% same sign), and the positive t is again 2020.

## 2. Q2 — does it call the 08:30 MOVE? The gates.

```
             n       b       t     halves (b, t)                    
G1  CPI     1441  +0.025  +0.36    +0.109 (+2.21) / -0.032 (-0.28)   FAIL
G2  jobs     748  +0.030  +0.62                                      FAIL
G3  claims  4785  +0.016  +0.32                                      FAIL
```

**None of them calls the market.** The market already has petrol --
exactly as v30's Kalshi number said. CPI's first half reaching t 2.21
and its second half reversing is the "regime, not an edge" pattern v31
registered in advance.

**A design weakness found on review.** Predictors were scaled by their
full-sample spread, which for ADP and claims is dominated by 2020. Least
squares then weights the pandemic months heavily, so G2 and G3 as run
mostly measured 2020. Post-hoc, without 2020-21: CPI t +0.33, payrolls
t +2.11 (on the sign alone, t +1.27), claims t -0.57. Still no pass, and
the registered verdict stands -- but the payrolls figure is the one to
watch below.

## 3. Reported, gating nothing

```
Q3 bounce vs |predictor|   CPI t +1.22   payrolls t +3.97 (+2.90 without
                           2020-21)      claims t -1.61
backdrop (t vs direction / vs bounce, release mornings)
  VIX level        -1.51 / +1.20     2y yield 5-day  +1.32 / +0.74
  dollar 5-day     -0.09 / +0.63     own overnight   -0.29 / +0.11
```

No backdrop number clears |t| = 2.

**The one recurring thread.** The bounce on payrolls mornings is bigger
when ADP had missed its own trend by more (t +2.90 without the
pandemic). v29 found the same shape for CPI -- a bigger naive surprise,
a bigger bounce (t +2.15 without the pandemic). Two different releases,
two different surprise measures, same direction -- while v28 showed the
bounce does NOT grow with the size of the PRICE move. Both are ungated,
post-hoc and on samples now seen. Together they are the most coherent
lead this line has produced, and they can only be tested honestly on
data nobody has looked at: forward.

## 4. Predictions, scored

```
Q1 passes for CPI                          RIGHT
Q1 weak for payrolls and claims            RIGHT for payrolls; claims are
                                           informative, but in reverse
G1, G2, G3 fail                            RIGHT
no backdrop variable clears |t| = 2        RIGHT
```

---

**Investigation forty-seven.**
