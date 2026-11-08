# RESULT — v35: reactive signals. Shock follow-through and intraday momentum all fail.

```
SPEC:     PREREGISTRATION_v35.md  sha bca23cad…
METHOD:   scripts/reactive.py 1.0   log data/reactive_v35_run.log
GATED:    2013 → 2026-09-17, NET of quoted spread, SPX500/NAS100/US30 5m
VERDICT:  A1 FAIL  A2 FAIL  A3 FAIL  B FAIL
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## Numbers (bp per trade, t clustered by date)
```
                         2005-12 gross    2013-26 gross   2013-26 NET     eras (net)
A1 every 3σ shock→close  +0.76 (t 0.29)   -0.18 (-0.10)   -1.58 (-0.90)   -2.77 -1.22 -0.53
A2 shock that holds      +1.11 (t 0.41)   +0.21 (+0.12)   -1.19 (-0.67)   -2.87 +1.50 -1.40
A3 shock out of calm     +4.05 (t 1.47)   -1.38 (-0.63)   -2.80 (-1.27)   -1.90 -0.13 -5.64
B  first 30m → last 30m  +2.86 (t 3.12)   -0.30 (-0.67)   -1.66 (-3.63)   -2.17 -1.59 -1.16
```
Reported only: A1 60-minute gross in 2013–26 is −0.01 bp.

## Read it plainly
- **A 3-sigma shock does not tell you the rest of the day's direction.**
  The average follow-through to the close is about zero before costs, whether
  or not the shock holds, and whether or not it came out of a quiet hour.
  This test could only see an edge of about 6 bp or more per trade. A trend
  payoff that large is not there.
- **Intraday momentum is a textbook case of a published effect decaying.** It
  was real in 2005–12 (+2.86 bp, t 3.1, before costs) and gone in 2013–26
  (−0.30 bp). After the spread it loses in every era and on every index.
- **NAS100 is the only index that leans positive** on A1/A2 (+2.7 / +3.1 net,
  t 1.1–1.25). It was not gated per instrument, SPX and US30 are negative,
  and v1 already looked at NAS100 over 2014–20, which sits inside this
  window. It is not a finding. At most it is a forward-only watch item.

## Caveats in the body
- Holding to the close makes A noisy. An edge between 1 and 6 bp per trade
  is below what the test can resolve.
- Breadth across markets (DAX, gold) was not tested, because 5m bars are
  available only for the three US indices.
- The three indices are close to one market, and the date clustering accounts for that.
