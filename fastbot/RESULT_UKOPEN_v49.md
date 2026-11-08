# RESULT — v49: the FTSE open does not under-react to overnight US moves. Following them loses; fading them earns about 1 bp, less than the noise.

```
SPEC:     PREREGISTRATION_v49.md  sha 6a612316…
METHOD:   ukopen_v49.py 1.0; UK100, DE30 (OANDA 5m, data/v38), SPX500 (OANDA 15m, data/v24), London time; log data/run_v49.log
RUN:      2026-09-28
VERDICT:  G1 FAIL   G2 FAIL
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## Interpretations fixed in the harness before the run
- **Overnight moves:**
  - UK_on runs from the prior 16:25 bar close to today's 07:55 bar close.
  - US_on runs from the last SPX 15m bar closing at or before 16:30 to the last bar closing at or before 07:55.
  - EU_pre runs from the DE30 07:00 bar open to the 07:55 bar close.
- **β:** a 250-day rolling OLS of US_on on UK_on, with today excluded.
- **The G2 top fifth** is measured against the prior 250 |R| values.
- **Costs:** the quoted spread at the 08:00 open.
- **Self-test:** a planted under-reaction passes G1, and a planted over-reaction fails it. It passed.

## Numbers (bp; SEs clustered by date)
```
usable days 2,887; with residual 2,637; median beta 1.05; median 08:00 spread 2.43 bp
RMS: first hour 36.8   R 48.7   EU_pre 25.5   UK_on 64.3
G1  First hour = a + b1*R + b2*EU_pre     b1 -0.005   t -0.14                          FAIL
G2  top-fifth |R|, trade sign(R)          n 513  gross -3.95  net -6.81  t -3.18  hit 44%
                                          eras 2013-17 -8.07   2018-21 -6.13   2022-26 -7.27   FAIL
reported: b2 (DE30 pre-open) -0.052  t -0.61
reported: reverse sign (fade the top-fifth R): gross +3.95, net +1.08 bp
reported: first hour on UK_on alone -0.058 (t -1.45);  on US_on alone -0.029 (t -1.74)
reported by era  b1: 2013-17 +0.30 (t 1.13)   2018-21 -0.01 (t -0.11)   2022-26 -0.06 (t -2.49)
                 b2: 2013-17 +0.27 (t 2.29)   2018-21 -0.17           2022-26 +0.03
```

## Read it plainly
- **The overnight CFD already prices the US move.** Once the UK100's own overnight change is accounted for, the leftover US move (R) predicts nothing about the first hour (t −0.1). The European pre-open doesn't either.
- **Following big residuals loses money.** Trading the first hour in the direction of a large R loses about 4 bp gross and 7 bp net. That holds in every era, and the t is −3.2 in the wrong direction.
- **The opposite direction is small.** A mild *over*-reaction is reported: fading gives +3.95 bp gross and +1.1 bp net. It was not a registered hypothesis, and after the 2.4 bp spread there is almost nothing left.
  - In 2022–26 alone, b1 is −0.06 (t −2.5), which points the same way.
  - A fade test would need its own pre-registration. At about +1 bp net, it is under the 4.2 bp this design could detect.
- **2013–17 looked like the hypothesis** (b1 +0.30, b2 +0.27 with t 2.3), but on only 462 days, and it had gone by 2018. That is the programme's usual decay pattern.

## Caveats
- **Missing early data:** OANDA's UK100 has no 07:55 bar before mid-2015. 2013–14 are almost all missing, which is why there are 2,887 usable days rather than the budgeted 3,441. The per-year count is in data/v49_missing_diag.py.
- **Spread is higher than budgeted:** the median at 08:00 is 2.4 bp, above the pre-registration's 1.5–2 bp.
- **SPX timing:** the 15m SPX bars put the "US close" mark up to 15 minutes early.
