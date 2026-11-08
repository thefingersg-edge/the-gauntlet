# PREREGISTRATION FLOWS-1 — month-end rebalancing: one flow, one test

```
WRITTEN:   2026-09-26, before any return in any month-end window has been
           computed on OANDA data for this question. No harness exists yet.
STATUS:    FROZEN at its first commit. The harness must pin this file's
           sha256 and refuse to run if it has changed (fastbot convention).
SOURCE:    research/LITERATURE_2026-09_market_behaviour_change.md, rank 1
VEHICLE:   OANDA CFDs, SPX500_USD vs USB10Y_USD (DE30_EUR vs DE10YB_EUR check)
```

*Measurement, not a recommendation. Not financial advice.*

---

## 0. The mechanism, the claim, and the prior

Fixed-weight pension and balanced funds rebalance at month-end. After equities
beat bonds over the month they must sell equities and buy bonds, and the
reverse. Someone is forced to trade, on a known date, in a knowable direction.

Harvey, Mazzoleni & Melone, *The Unintended Consequences of Rebalancing*
(NBER w33554, rev. Jan 2026; sample Sep 1997 – Mar 2023): a 1 s.d. calendar
signal predicts an equity-minus-bond return about **17 bp lower the next day**,
concentrated in the **last five trading days** of the month, reversing within
about two weeks. Front-running Sharpe about 1.08 (0.90 excluding 2008-09 and
March 2020). The effect grew after 2000 and after the 2006 Pension Protection Act.

Three other published effects share this clock and this trader, so they are
treated as **the same flow and tested once**, not counted as separate hits:
the month-end Treasury rally (Hartley & Schwarz, ~20 bp over the last 2-5
days, sample to 2018), the equity turn-of-month drift (Kayacetin 2026 finds it
at a peak in 2019-23; a public replication finds the classic US window gone),
and the month-end FX fix (excluded here, section 9).

**Registered expectation.** The replication gate (G1) is more likely than not
to show a negative slope. The holdout (41 months) is too short to be more than
a sign check. The most likely failure is G7: two legs, four spreads and five
nights of financing on each trade.

## 1. Data

| leg | instrument | source |
|---|---|---|
| equity (primary) | SPX500_USD | `fastbot/data/v24/spx500usd_{bid,ask}_15m.csv` |
| bond (primary) | USB10Y_USD | Step 0 pull |
| equity (check) | DE30_EUR | `fastbot/data/v24/de30eur_{bid,ask}_15m.csv` |
| bond (check) | DE10YB_EUR | Step 0 pull |

- **Step 0 pull:** `fastbot/scripts/pull_m1.py --pull --granularity M15
  --sides B,A --instruments USB10Y_USD,DE10YB_EUR,USB30Y_USD --data-dir
  flows/data`. Never into `fastbot/data/v24`, which `forward_tick.sh` appends to.
- **Daily bars** close at the 17:00 New York rollover, DST-aware (pineport
  `make_daily.py` convention, R4). Price = mid = (bid + ask) / 2.
- **Sample:** 2005-01 to 2026-08, the last complete month before this was
  written. A month missing a daily close on either leg at D-5 or D is dropped;
  the count is reported.
- **Eras:** E1 2005-01 – 2012-03, E2 2012-04 – 2019-06, E3 2019-07 – 2026-08.
- **Holdout:** 2023-04 – 2026-08, after the paper's sample ends. Reported apart.

## 2. Definitions

- **D** = last trading day of calendar month *m* (last 17:00-NY daily bar dated in *m*).
- **Window W** = trading days D-4 … D. Entry at the close of D-5, exit at the close of D.
- **Signal** S_m = r_eq − r_bond, each from the close of the last trading day of
  *m*-1 to the close of D-5. Known before the window opens.
- **Legs** E_m = r_eq and B_m = r_bond over that same month-to-date span.
- **Outcome** Y_m = r_eq − r_bond from the close of D-5 to the close of D.
  Equal notional, as in the paper. A vol-scaled version is robustness R1.

## 3. Primary test

    Y_m = a + b·S_m + e        OLS, Newey-West SE (3 lags), one row per month, N ≈ 257

Rebalancing predicts **b < 0**. A generic turn-of-month or dash-for-cash effect
predicts a ≠ 0 with b ≈ 0. The model separates them in one fit.

## 4. Gates — thresholds fixed now

| gate | test | pass |
|---|---|---|
| **G1** replication | primary, 2005-01 – 2023-03 | b < 0 and t ≤ −2.0 |
| **G2** eras | primary in E1, E2, E3 separately | b < 0 in all three |
| **G3** holdout | primary, 2023-04 – 2026-08 | b < 0 (sign only; 95% CI reported) |
| **G4** mechanism / shared term | Y = a + b1·E + b2·B | **b1 < 0 and b2 > 0** |
| **G5** placebo timing | window = trading days 6-10, signal to end of day 5 | t > −2.0 and \|b_placebo\| < \|b\| |
| **G6** reversal (support, not a kill) | relative return over first 5 days of *m*+1 on S_m | b_rev > 0 |
| **G7** vehicle and cost | trading rule below, net | mean net return per trade > 0, full sample; same sign in holdout |
| **G8** independent market (confirmatory) | primary on DE30 vs DE10YB | b < 0 |

**G4 is the shared-term check.** S is built from trailing returns, and
time-series momentum was rejected in pineport. Momentum predicts b1 > 0
(continuation); rebalancing predicts b1 < 0 and b2 > 0 (sell the winner, buy
the loser). Only the second pattern passes.

**G7 trading rule.** At the close of D-5, trade only if |S_m| exceeds the
67th percentile of all earlier |S| (expanding, at least 36 months of history).
Position −sign(S): short equity and long bond when S > 0, the reverse when S <
0. Exit at the close of D. Fills at the actual bid or ask of the M15 bar ending
at 17:00 NY. Financing per leg for every 17:00 rollover held, at benchmark rate
plus OANDA's markup, with the instrument's days-charged table read from the
API (the `fastbot/scripts/oanda_financing.py` method; OANDA books the weekend
on Friday for SPX500). Stress tests at +1 bp and +3 bp per side.

## 5. Bond-CFD roll mechanics — handled before the outcome is computed

OANDA bond CFDs may carry roll adjustments near the futures roll (last days of
February, May, August, November), which is inside W. Before Y is computed:

1. Compute each day's USB10Y CFD return and the duration-implied return from
   FRED DGS10: r_implied = −8.5 × Δyield.
2. Flag any day with |r_CFD − r_implied| > 0.75%.
3. Freeze the flag list with its sha256.

Fixed now: the **primary excludes** months whose window contains a flagged day.
R2 includes them. R3 replaces the bond leg entirely with the DGS10-implied
return, which has no vehicle artefact. No selection among R1-R3: the primary
stands whatever they show.

## 6. Kill conditions

- **K1** G1 fails.
- **K2** G4 gives b1 > 0: the signal is momentum, not rebalancing.
- **K3** G2 shows b > 0 in any era.
- **K4** G7 net ≤ 0: the flow may be real but is not reachable here.

## 7. What each outcome would mean

- All pass: first mechanism-backed flow in the programme to survive a CFD test.
  Forward-test before any capital.
- G1-G4 pass, G7 fails: a real flow that retail costs eat. Record it; stop.
- G1 passes, G4 fails: the literature's "rebalancing" is momentum in disguise
  on this vehicle. Stop.
- G1 fails: no rebalancing pressure visible on OANDA daily bars. Stop.

## 8. Declared test count

Inferential: G1, the two G4 coefficients, G5 — four tests, Benjamini-Hochberg
at q < 0.10. Everything else is sign-only or descriptive.

## 9. Out of scope, declared now

- The month-end FX fix leg (weakest evidence, minute-scale). A separate
  pre-registration if ever wanted.
- Dividend-payment pressure (needs a paid calendar). Named as a confound.
- Quarter-end months: b reported separately for descriptive interest, no gate.

## 10. Files

    flows/monthend.py            harness — pins this file's sha256
    flows/data/                  Step 0 pulls and the roll-flag list
    flows/RESULT_MONTHEND.md     result
