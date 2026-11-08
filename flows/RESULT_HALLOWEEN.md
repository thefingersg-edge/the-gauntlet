# RESULT — FLOWS-12: Sell in May. DEAD (K1, K2).

```
SPEC:     PREREGISTRATION_HALLOWEEN.md (sha e7101aa1…)
METHOD:   halloween.py   log data/halloween_run.log   result data/halloween_result.json
DATA:     FRED NASDAQCOM 1971-02 .. 2026-08 (666 months, sha 51dd9b04…); SPX500 CFD 2005-2026
RUN:      2026-10-01, once
VERDICT:  G1 FAIL  G2 FAIL  G3 PASS  G4 FAIL  ->  DEAD
```

*Measurement, not a recommendation. Not financial advice.*

| | result | gate |
|---|---|---|
| Nov–Apr minus May–Oct, monthly, NASDAQ 1971–2026 | +0.81%/month, t 1.78 | G1 FAIL |
| thirds | **1971–89 +1.82% (t 2.6)**, 1990–2007 +0.43%, **2008–26 +0.14%** | G2 FAIL |
| SPX500 CFD 2005–26 | +0.34% (t 0.7) | G3 PASS (sign only) |
| long winters only vs buy-and-hold, net Sharpe | 0.31 vs 0.34 | G4 FAIL |

The oldest seasonal in finance is there in the 1970s and 80s and fades to
nothing after 2008. Holding only in the winter months does worse than
simply holding.
