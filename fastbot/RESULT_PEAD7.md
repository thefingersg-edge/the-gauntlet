> **VOID 2026-10-04 — look-ahead bug: trades whose 10-Q was filed on the 8-K day were bought before the EAR signal was complete. See RESULT_AUDIT_LOOKAHEAD.md (corrected: FAIL).**

# RESULT — PEAD7: PEAD3 bought in the opening auction at measured cost. FAIL on one gate only: 2005–12 was flat. Everything since 2013 passes strongly.

```
SPEC:     PREREGISTRATION_PEAD7.md (sha in PROVENANCE)
METHOD:   singlestock/pead7_run.py; same 7,762 events as PEAD3; open-auction entry, close-auction exit; cost M 0.64 / S 1.06 x EDGE + commission; log data/run_pead7.log
RUN:      2026-10-04  (re-pricing of already-seen data -- not independent evidence)
VERDICT:  G1 PASS  G2 FAIL  G3 PASS  G5 PASS  -> FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
G1 M+S net +1.83% (t 4.58); gross +2.80%, mean cost 0.97%                       PASS
G2 2005-12 -0.14% | 2013-19 +1.86% (t 3.78) | 2020-26 +4.14% (t 6.08); 2018-26 +3.32% (t 5.30)   FAIL
G3 M +0.44% (t 0.91) | S +2.76% (t 5.30)                                         PASS
G5 calendar Sharpe 2018+ 1.54                                                     PASS
reported: point ratios +1.97% (t 4.94)
          120-day hold, open-auction entry: +2.77% (t 4.85); 2018+ +4.29% (t 4.75)
          S band 2018+: +4.69% (t 5.32, n 1,920)
```
## Read it plainly
- With **measured** costs, the opening-auction version is the best-costed form of the strategy: it beats the closing-auction version (PEAD6, +1.14%) because the first-day move (+1.7%) is worth more than the extra cost (about 0.4%).
- Measured costs turn out close to what PEAD3 assumed (0.97% vs 1.06%), so **PEAD3's numbers were realistic after all**, for the right reason now: open-auction orders, not marketable orders at the open.
- **The single failure is the same as every PEAD variant: 2005–12 did not work.** The effect has been strong since 2013 and strongest since 2020. Whether it is a durable post-2013 effect or a phase that can end is exactly what the forward record must show.
- Execution for the forward record and PORT1: market-on-open entry, market-on-close exit. The FORWARD_PEAD3 recorder already prices this way (open of e0, close of exit day).

## Appendix (DESCRIPTIVE, post hoc, 2026-10-04): what changed? `singlestock/pead7_posthoc_years.py`, log `data/pead7_posthoc_years.log`
- **2005–12 was not a dead era: it lost in three years.** Net by year: 2005 +1.9, 2006 −1.5, 2007 +1.3, **2008 −4.6, 2009 −1.9**, 2010 +0.2, 2011 +1.2, 2012 +1.3. The financial crisis (and the 2009 junk rally) did the damage. Since 2013 only 2019 was negative (−1.0).
- **The first-day move has grown steadily**: open-to-close on the entry day was about +0.0 to +0.5% in 2005–07, about +1% in 2010–15, +1.7 to +2.1% in 2016–19, and +2.3 to +3.3% in 2022–26. Days 2–60 were roughly flat in size (about +1 to +4%) apart from crisis years.
- **Small caps carry it from 2013**; mid caps are noisy around zero.
- Untested hypotheses for the growing day-one move: machine-readable filings (XBRL, phased in 2009–11, small companies from 2011) letting the market react to the 10-Q the next morning; fewer analysts covering small caps; more retail flow since 2020. None of these is established by this table.
- Implication: the main historical risk is a crisis year, which PORT1's 200-day / VIX entry filter is designed to sit out. Whether the filter would have helped in 2008–09 has not been tested.
