> **VOID 2026-10-04 — look-ahead bug: trades whose 10-Q was filed on the 8-K day were bought before the EAR signal was complete. See RESULT_AUDIT_LOOKAHEAD.md (corrected: FAIL).**

# RESULT — PEAD8: holding 120 days, trailing stops, take-profit and a tightening stop. All FAIL against the plain 60-day exit.

```
SPEC:     PREREGISTRATION_PEAD8.md (sha in PROVENANCE)
METHOD:   singlestock/pead8_run.py; the 7,762 PEAD7 trades; judged on net excess per position-day vs PEAD7 60-day; log data/run_pead8.log
RUN:      2026-10-04  (re-analysis of already-seen data)
VERDICT:  V1 FAIL  V2 FAIL  V3 FAIL  V4 FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
                                   per position-day vs base   Sharpe 2018+   net/trade   avg days   exited by rule   worst year
baseline PEAD7, 60 days            +0.0306%/day               1.54           +1.83%      60         -                2008 -4.57%
V1 hold 120 days                   -0.0065 (t -1.53)          1.24           +2.77%      118        -                2008 -5.97%
V2 trailing stop 15%               -0.0047 (t -0.97)          1.24           +1.96%      61         78%              2006 -1.66%
V3 take-profit +25%                -0.0094 (t -2.04)          1.42           +1.70%      90         43%              2008 -4.16%
V4 tightening stop, no target      -0.0076 (t -1.52)          1.25           +1.53%      59         84%              2006 -1.51%
```
## Read it plainly
- **120 days earns more per trade (+2.8% vs +1.8%) but less per day of capital**, and with a lower Sharpe. With a limited number of portfolio slots, the 60-day exit makes better use of the money.
- **Take-profit hurts most:** it sells the winners that carry the strategy.
- **Stops do not raise the return either,** but they do one useful thing (reported, not gated): they cut the crisis damage. With a 15% trailing stop the worst year is 2006 at −1.7%; without a stop 2008 loses −4.6% to −6.0%. Stops behave like insurance, paid for in normal years.
- Keep the 60-day time exit. If drawdown control matters later, the 200-day/VIX entry filter in PORT1 and a wide trailing stop are the two candidates to test together.
