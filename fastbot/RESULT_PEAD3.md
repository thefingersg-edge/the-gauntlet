> **VOID 2026-10-04 — look-ahead bug: trades whose 10-Q was filed on the 8-K day were bought before the EAR signal was complete. See RESULT_AUDIT_LOOKAHEAD.md (corrected: FAIL).**

# RESULT — PEAD3: EAR confirmed by the reported earnings surprise. Strong after full costs (+1.74%, t 4.4; 2018–26 +3.23%, t 5.2), but negative in 2005–12, so it FAILS G2 as registered. This is the programme's strongest lead.

```
SPEC:     PREREGISTRATION_PEAD3.md  sha 23419e48…
METHOD:   singlestock/batch2_run.py pead3 (ss_events2.py cf4bfa27…); log data/run_pead3.log
          note: the first call timed out while printing the REPORTED lines. The second call reproduced identical gated numbers
          (deterministic, cached) and wrote the log. The SUE threshold was memoised between calls: speed only, same values.
RUN:      2026-10-03
VERDICT:  G1 PASS  G2 FAIL  G3 PASS  G5 PASS  -> FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
PEAD1 longs 24,266 -> SUE-confirmed 7,868 | not confirmed 11,628 | no 10-Q within 60 days 4,770
G1  net +1.74% (t 4.35, n 7,762), gross +2.80%, cost 1.06% (FULL EDGE + commission, open execution)   PASS
G2  2005-12 -0.24% (t -0.37)   2013-19 +1.80% (t 3.63)   2020-26 +4.05% (t 5.96)   2018-26 +3.23% (t 5.17)  FAIL (first era)
G3  M +0.12% (t 0.25)   S +2.83% (t 5.44)                                                     PASS
G5  calendar-time excess Sharpe 2018+ +1.49                                                   PASS
reported: closing auction, 25% cost: +1.09% (t 2.87), 2018+ +1.88% (t 2.84)
          EAR long NOT confirmed by SUE: gross +2.23%, net +1.09% (n 11,473)
          SUE alone (top decile): gross +0.80% (t 3.44), net -0.16%
data check (descriptive): the 10-Q filing lag is stable across years (median 40-42 days), so there is no sign of a time-varying look-ahead in the filing dates
```
## Read it plainly
- **Waiting for the 10-Q, and buying only when it confirms a strong earnings reaction, gives the largest net effect this programme has found.**
  - +1.7% per 60-day trade after the full spread. +3.2% on 2018–26 alone.
  - It sits in the smaller stocks.
  - A calendar-time Sharpe of 1.5 on 2018+.
- **It fails as registered because 2005–12 was slightly negative.** Unlike everything else in the programme, it has *strengthened* over time rather than decayed. That is either a real change (more retail-driven small caps, slower reaction to filings) or luck in a 9-year window. Only forward data can tell.
- **Buying all EAR longs at the filing date (confirmed or not) was also positive net (+1.09%).** Part of the gain comes from entering later (after the first weeks), not only from SUE confirmation. That is post-hoc, and is noted for the next registration.
