# AUDIT 2026-10-07 — the assumptions under every test: which are measured, which were checked today, which remain

**I am not a financial adviser. This is a measurement, not a recommendation.**

Rule followed: an assumption can be **measured** or **stress-tested** freely; a strategy parameter must **not** be re-tuned on data already seen (that manufactures passes). "Best numbers" therefore means *correct inputs*, not *best-looking settings*.

## 1. Already measured (no action)
| Assumption | Status |
|---|---|
| OANDA spread = candle spread | VALIDATED on Dave's real fills (RESULT_FILLS_AUDIT), within ~0.1 bp |
| US single-stock trading cost | MEASURED 2018–26 (COSTS1/COSTS2): closing auction 0.14 × EDGE, opening auction 0.70 × EDGE, quoted open 1.43 × EDGE |
| Kraken fees / collateral / financing (basis work) | MEASURED (RESULT_KRAKENBASIS_LINEAR, TRACKA_D3) |
| VIX carry drawdown and minimum size | MEASURED (RESULT_VIXDAILY −68 vol points; RESULT_VIXCARRY 0.63 mini contracts) |
| Entry after the signal is known | AUDITED twice (RESULT_AUDIT_LOOKAHEAD, RESULT_AUDIT_INDEX); fixes made |

## 2. Checked today
| Assumption | Check | Result |
|---|---|---|
| **Overnight CFD financing = flat 2 bp/night (BOUNCE1)** | `data/oanda_financing.json` (live SPX500_USD): longs pay policy rate + 2.5%, shorts *receive* policy rate − 2.5%, Friday ×3 | **Wrong in both directions** (longs over a weekend pay ~5 bp; shorts were *paid* in 2023–26). Fixed by **PREREGISTRATION_BOUNCE1.1**, frozen before any BOUNCE1 data exists |
| Auction-cost ratio is stable over time (used to extrapolate costs before 2018) | COSTS1 rows by year 2018–26 | Stable: auction/EDGE 0.08–0.20 every year; open/EDGE 0.97–1.99. Extrapolation reasonable, not proven for 2005–17 |
| −30% return for stocks delisted for cause | Re-ran PEAD1 and the corrected PEAD7c at 0%, −30%, −60%, −100% (`singlestock/audit_delist.py`) | **Immaterial**: PEAD1 −0.03% → −0.05%; PEAD7c +0.40% → +0.39%. No verdict changes |

## 3. Remaining assumptions (named, not yet tested)
| Assumption | Where it matters | Risk / note |
|---|---|---|
| No market impact from our own orders | every test | Fine at a retail size; must be re-checked before scaling (auction size data from Databento) |
| Costs before 2018 = the 2018–26 ratio × EDGE | single-stock 2005–17 eras | Cannot be measured (Databento history starts 2018). Affects only already-failed tests |
| Liquidity-band benchmark for stock excess returns | PEAD, BATCHB, INSIDER1, SPIN1 | Reasonable; an S&P or equal-weight-market benchmark would differ slightly. All these tests fail by wide margins |
| Standard-error method fixed per test (quarter clusters / Newey-West lags) | near-misses: v56 (passes only under its registered SE), GEX v42 H1 (t 1.98), BREADTH2 G2 (t −1.69), IMB1 G1 (t 1.62) | Correct as long as the method is fixed **before** the run (it was). Switching after would be cherry-picking |
| Strategy parameters from the literature, not tuned (EAR top decile, SUE ≥ 70th pct, 60-day hold, noise-band 14 sessions, S5FI < 20, |z| ≥ 1) | most tests | Deliberate. PEAD8 and v39_CHECKS showed exits/holds do not rescue anything; further searching on seen data would overfit. A parameter question goes to a fresh pre-registration or the forward record |
| OANDA CFD tracks the cash index at the close | v52/C1, v56, IMB1 cross-checks | Small; C1's 20–30-minute VIX timing gap already noted |
| Sharadar 5-year tier is enough for the forward recorders | FORWARD_PEAD3 / SMALLCAP1 / BREADTH1 | First real check: the November refresh (task on 9 Nov reports it) |
| AAII is downloaded by hand | v41 forward record | v41 sessions are deferred until it is refreshed |
| **VIX carry costs: VX mini spreads/commissions at IBKR, short-VIX ETP fees and tracking** | Saturday's discussion | **Not yet measured — the one input to source before any VIX carry decision** |
