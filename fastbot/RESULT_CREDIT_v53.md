# RESULT — v53: credit spreads and the stock–bond correlation as risk overlays. Both NOT USEFUL. Credit came close on its own but makes things worse when added to VIX. The correlation signal fails outright.

```
SPEC:     PREREGISTRATION_v53.md  sha c8ed1d96…
METHOD:   credit_v53.py 1.0; BAA10Y sha 1c77186b…, DGS10 sha 98af25bb… (fetched by Dave, hashed before reading); SPX500+NAS100 daily closes to 2026-09-25; costs as v52; log data/run_v53.log
RUN:      2026-10-01
VERDICT:  CREDIT  G1 FAIL  G2 FAIL  G3 FAIL -> NOT USEFUL
          CORR    G1 FAIL  G2 FAIL  G3 FAIL -> NOT USEFUL
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

Self-test passed: an always-on position reproduces buy-and-hold, and perfect foresight has a very high Sharpe.

## Numbers (SPX+NAS equal weight, 2006-01 → 2026-09, net of spread and financing)
```
              Sharpe  CAGR    max DD   Calmar  in market   era DD (06-12 / 13-19 / 20-26)
B&H           +0.456  +7.40%  -57.1%   0.130   100%        -57.1 / -20.4 / -32.7
VIX rule      +0.458  +5.51%  -37.9%   0.145    80%        -37.9 / -14.7 / -36.8
CREDIT        +0.515  +6.79%  -41.9%   0.162    78%        -41.9 / -20.5 / -30.2
CREDIT|VIX    +0.336  +3.53%  -35.2%   0.100    69%
CORR          +0.335  +4.57%  -57.1%   0.080    77%
CORR|VIX      +0.398  +4.13%  -37.3%   0.111    60%

CREDIT  G1  DD -41.9% vs needed -42.8%; 2013-19 era -20.5% vs B&H -20.4%       FAIL (both by a hair)
        G2  Sharpe +0.515 vs null 97.5th pct +0.582 (median +0.418)          FAIL
        G3  adding credit to VIX: Calmar 0.100 < 0.145, Sharpe 0.336 < 0.458  FAIL
CORR    G1  DD unchanged -57.1%                                              FAIL
        G2  Sharpe +0.335 vs null 97.5th +0.607                               FAIL
        G3  CORR|VIX Calmar 0.111 < 0.145                                     FAIL
reported: credit level (z>1) Sharpe +0.415 DD -47.2%;  correlation using the 2y yield +0.355 / -57.1%
          per instrument (Sharpe/DD): SPX B&H +0.33/-60 VIX +0.32/-44 CREDIT +0.37/-47 CORR +0.22/-60
                                      NAS B&H +0.55/-56 VIX +0.55/-43 CREDIT +0.61/-37 CORR +0.43/-56
          share of days with rho > 0: 0% in 2008-12 and 2017-20; 55-86% in 2022-26 -> an era switch, as predicted
          UK100 with US credit: Sharpe +0.02 DD -44.9% vs B&H +0.02 DD -51.9%
          HY OAS: FRED history starts 2023-10 -> not computable
```

## Read it plainly
- **Credit on its own looked like the best of the three US overlays: a higher Sharpe than buy-and-hold, and a 15-point smaller drawdown. It still failed every gate.**
  - Its drawdown cut missed the 25% bar by under a point.
  - Its timing did not beat random exits.
  - Combined with the VIX rule it was *worse* than VIX alone, because the two together sit out too much of the recovery.
  - It adds nothing on top of what VIX already does.
- **The correlation signal is what the pre-registration expected: an era switch.**
  - The stock–bond correlation was negative almost every day in 2008–20, and positive most days since 2022.
  - The signal stayed fully invested through 2008 and only stepped aside in the 2022–26 regime, so it did nothing in the crash that mattered.
- **These were the last untested cross-market risk overlays on the list. The free versions of credit and correlation add nothing beyond VIX.** That is the same answer as v50's news-based fear index.

## Caveats
- BAA10Y is investment-grade-ish credit. High-yield spreads, the more sensitive series, are only on FRED from 2023.
- Drawdowns turn on 2008, 2020 and 2022.
