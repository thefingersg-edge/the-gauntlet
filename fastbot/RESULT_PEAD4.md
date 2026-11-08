> **VOID 2026-10-04 — look-ahead bug: trades whose 10-Q was filed on the 8-K day were bought before the EAR signal was complete. See RESULT_AUDIT_LOOKAHEAD.md (corrected: FAIL).**

# RESULT — PEAD4: what drives PEAD3? Neither registered explanation. The drift simply runs longer than 60 days, and buying after the filing captures more of it.

```
SPEC:     PREREGISTRATION_PEAD4.md  sha d79d7c1a…
METHOD:   singlestock/pead4_run.py; main window entries 2005-01 .. exits 2023-06-30; log data/run_pead4.log
RUN:      2026-10-03
VERDICT:  H4a FAIL   H4b FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
late entry (open after the 10-Q filing), 60 days, FULL EDGE cost, main window (to 2023-06):
  SUE-confirmed       net +1.13% (t 2.86, n 6,477)
  not confirmed       net +0.82% (t 2.17, n 9,508)
H4a confirmed minus not: +0.32% (t 0.76); eras -0.08 / +1.19 / +0.23                         FAIL
H4b early window (PEAD1 entry -> filing day): +0.45% (t +3.37) -- POSITIVE, not a dead period   FAIL
reported: early window confirmed +0.94%, not confirmed +0.10%
reported (not clean): entries after 2023-06: confirmed +5.00% (n 1,204), not confirmed +2.44% (n 1,827)
```
## Read it plainly
- **SUE confirmation adds only a little (+0.3%, not significant).** Its main role is selection: confirmed stocks were already drifting.
- **There is no dead period to skip.** Stocks keep drifting from the first days after the announcement.
- **So why does the late entry net positive (+0.8% to +1.1% after full cost, even before 2023), when PEAD1's 60 days from the announcement did not?** Because the drift lasts **beyond 60 trading days**. The late entry holds from about day 30–40 to about day 100, capturing drift PEAD1 never held. **The holding period is the lever.** One round-trip cost spread over a longer drift.
- **The strongest numbers come from the most recent years:** +5.0% and +2.4% after 2023-06. PEAD3's 2018+ strength was partly this period. That is encouraging if real, and exactly what the forward record must check.

## Next (needs its own pre-registration)
- **PEAD5:** EAR long entered at k+2 and **held 120 trading days**, net of full cost, with the main window to 2023-06.
- That separates "a longer hold" from everything else, and it is the natural design for the forward record.
