# RESULT — ADD1: new S&P 500 members did NOT lag in the sealed window (2023-07 to 2026-07). FAIL; the effect reversed.

```
SPEC:     PREREGISTRATION_ADD1.md  sha ca59a6f6…
METHOD:   singlestock/add1_run.py (batchB_engine.run unchanged); log data/run_add1.log
RUN:      2026-10-04
VERDICT:  G1 FAIL  G2 FAIL  -> FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
51 additions; mean 60-day excess +5.08% (t +1.07) -- wrong sign for the short       G1 FAIL
short after costs: -5.43% per trade                                                 G2 FAIL
reported: 49% negative; median +0.20%; by year 2023 +0.5% (8) | 2024 +0.7% (13) | 2025 +8.5% (16) | 2026 +7.9% (14)
```
## Read it plainly
- The pre-2023 lag (−2.7%) did not continue. The median addition did about as well as its benchmark; a few large winners in 2025–26 (index joiners in a strong momentum market) pulled the mean up.
- As expected from the budget, one window of 51 events cannot rule a small effect in or out, but a short would have lost money. Closed.
