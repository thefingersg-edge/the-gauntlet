# AUDIT 2026-10-04 — PEAD3 / PEAD4 (late entry) / PEAD6 / PEAD7 / PEAD8 had a look-ahead bug. Corrected, the strategy FAILS.

```
FOUND:    2026-10-04, while designing CHANGE1 ("what changed after 2013?")
CODE:     singlestock/audit_lookahead.py (log data/audit_lookahead.log); corrected re-run singlestock/pead7c_run.py (log data/run_pead7c.log)
EFFECT:   PEAD3/6/7/8 and PEAD4's late-entry numbers are VOID. COSTS1/COSTS2 cost measurements stand.
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## The bug
- The EAR signal uses the stock's return over days −1, 0 and +1 around the earnings 8-K, so it is only known at the **close of day +1**.
- PEAD3 bought at the open of the day after the **10-Q filing**. When a company files its 10-Q on the **same day** as its earnings 8-K, that open is the open of day +1: the trade was bought **before its own signal was complete**, and the stocks were selected partly on that same day's move.
- The share of such trades rose from **7% (2005) to 57% (2026)** as more companies file the 10-Q with the earnings release. That, not a market change, is the "growing first-day move" and the post-2013 strength.

## The numbers (PEAD7 cost model)
```
                                 n       net per trade
bought before the signal         2,467   +6.18% (t 10.5)   <- look-ahead
bought after the signal          5,179   -0.31% (t -0.8)
corrected re-run PEAD7c (entry = open after BOTH the filing and the signal):
  G1 all M+S       +0.40% (t 1.08)                                   FAIL
  G2 2005-12 -0.71% | 2013-19 +0.45% | 2020-26 +1.67% (t 2.35); 2018+ +0.99% (t 1.59)   FAIL
  G3 M -0.71% | S +1.14% (t 2.33)                                    FAIL
  G5 calendar Sharpe 2018+ 0.35                                      FAIL
  reported: S band 2018+ +2.08% (t 2.28, n 1,898)
```
## Holding period (descriptive, corrected events, 120-day paths)
- Mean cumulative excess: +0.16% day 1, +1.1% day 20, flat to about day 80 (+1.3%), then +2.1% by day 120 (the next quarter's earnings fall around day 60–70 after the filing).
- Net of the ~1.0% round-trip cost: about zero until day 20, +0.3% at day 60, +1.1% at day 120. Best per day of capital: day 120 (+0.009%/day), then days 20–30.
- A single trade's own peak day is not informative: it is spread evenly (median 58; 12% peak in the first five days and 12% in the last five), as for a random walk.
- By era: 2005–12 drift fades after day 39; 2013–19 +2.2% by day 120; 2020–26 still rising at day 120 (+3.8% before costs).

## What still stands
- PEAD1 (EAR only, entry at k+2) and PEAD2/PEAD5 used the correct entry. PEAD1 and PEAD5 FAIL, PEAD2 FAIL — unchanged.
- COSTS1/COSTS2 measured real costs on real stocks and days; they remain valid.
- Small caps since 2018 remain positive after correction (+2.1%, t 2.3), but that is a post-hoc slice, not a test.

## Fixes made
- `pead_forward.py`: each signal now records an `anchor` = the later of the filing date and the EAR-known date; entry is the open after the anchor. The ledger was empty, so no forward data is affected.
- FORWARD_PEAD3 and PORT1 continue as forward records with the corrected entry; their backtest support is now weak.
