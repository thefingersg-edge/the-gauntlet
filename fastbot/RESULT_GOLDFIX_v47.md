# RESULT — v47: the London gold fix. The old PM-fix drop replicates; after the 2015 reform it has faded and cannot pay the spread.

```
SPEC:     PREREGISTRATION_v47.md  sha 47a5d6eb…
METHOD:   goldfix_v47.py 1.0; XAU/USD OANDA 15m bid/ask (data/v24), London time; log data/run_v47.log
RUN:      2026-09-27
VERDICT:  G1 PASS (pre-reform replication)   G2 FAIL (post-reform, tradeable)
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## Numbers (bp per day, t on daily observations)
```
PM fix window 14:45-15:15 London
  pre-reform  2006-03 -> 2015-03-19   -2.00 bp  t -3.00  n 2,323   G1 PASS
  post-reform 2015-03-20 -> 2026-09   -0.44 bp  t -0.95  n 2,973   G2 FAIL
  short the window post-reform, net of the quoted spread (median 2.0 bp):  -1.88 bp  t -4.01
reported: AM window 10:15-10:45   pre -1.36 (t -4.00)   post -0.84 (t -4.11)
reported: after the PM fix, 15:15-16:15   pre -0.40   post +0.31 (no reversal)
by year, PM window: 2006-11 all negative (-2.6 to -5.6); 2012-13 positive; since 2015 small, mostly negative
```

## Read it plainly
- **The pre-2015 finding is real on this data.** Gold fell about 2 bp in the half-hour around the PM fix, in five of the six years to 2011. This matches Abrantes-Metz & Metz and Caminschi & Heaney, the era that ended in fines and the fix's replacement.
- **After the March 2015 reform it shrank to −0.4 bp, which is not significant.** The published, investigated effect decayed, as every other one in the programme has.
- **The AM window (reported only) still shows −0.8 bp, t −4.1, after the reform.** That is statistically real, but it is less than half the 2 bp spread. It is most likely part of gold's known tendency to drift down during London hours, not a fix effect. It was not gated, and it cannot be traded on a CFD.
- **Nothing here pays the spread.** A short over either window loses after costs.

## Caveats
- 15m bars blur the exact auction moment.
- OANDA gold is a spot CFD, not the auction itself.
