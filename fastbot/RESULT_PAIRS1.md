# RESULT — PAIRS1: when one US index runs ahead of another during the day, the gap does NOT close by the close. FAIL on all three pairs.

```
SPEC:     PREREGISTRATION_PAIRS1.md (sha in PROVENANCE); scripts/pairs1_run.py; log data/run_pairs1.log
DATA:     OANDA 15m bid/ask SPX500, NAS100, US30, 2005 -> 2026-09-25, US cash session
RUN:      2026-10-07
VERDICT:  all three pairs FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
                 trades   mean net   gross    t       eras (net, bp)
SPX500-NAS100    1,002    -3.89 bp   -1.87   -3.96   -2.6 / -7.4 / -1.7
SPX500-US30        957    -2.30      -0.28   -3.64   -1.5 / -4.0 / -1.4
NAS100-US30        926    -4.80      -3.20   -3.23   -2.2 / -9.0 / -3.8
```
## Read it plainly
- **The gaps keep widening slightly rather than closing** (gross returns are negative for the "gap closes" bet), and two spreads are paid on every trade.
- Reported, not tested: betting the other way (the gap keeps going) would make roughly the same small gross amount (+0.3 to +3.2 bp) — still about the size of the two spreads, so near zero after costs.
- Intraday relative value between these index CFDs is efficient. The one non-directional scalp available at OANDA is closed.
