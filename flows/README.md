# flows — forced, dated trading flows

Hypotheses from `research/LITERATURE_2026-09_market_behaviour_change.md`: the
2023-2026 literature finds that the edges still working come from traders who
are forced to trade on known dates, not from price patterns.

| file | question | status |
|---|---|---|
| `PREREGISTRATION_MONTHEND.md` | FLOWS-1: does month-end pension rebalancing reverse the equity-minus-bond return? | **DEAD** (K4) — real 2005-23, absent since. `RESULT_MONTHEND.md` |
| `PREREGISTRATION_REFUNDING.md` | FLOWS-2: do Treasuries rally the Friday before the borrowing estimates? | **ALL GATES PASS**, but decayed to ~0 since 2019. `RESULT_REFUNDING.md` |
| `PREREGISTRATION_OVERNIGHT.md` | FLOWS-3: is the dead overnight drift still alive after US sell-offs? | **DEAD** — gone after sell-offs too. `RESULT_OVERNIGHT.md` |
| `PREREGISTRATION_ANNOUNCE.md` | FLOWS-4: do non-FOMC macro-announcement days (CPI, NFP, GDP, ISM) pay SPX500 a premium when VIX is high? | **DEAD** (K1–K3). Post-hoc: the premium is on *low*-VIX days (+12 bp, t 3.2). `RESULT_ANNOUNCE.md` |
| `PREREGISTRATION_LOWVIX.md` | FLOWS-7: does FLOWS-4's post-hoc low-VIX release-day premium hold in 1994–2004? | **NOT CONFIRMED**: +15 bp, same sign, t 1.3 < 1.65. Lead closed. `RESULT_LOWVIX.md` |
| `PREREGISTRATION_ECBDRIFT.md` | FLOWS-5: does DE30 drift for 20 days in the direction of its ECB-decision reaction? | **DEAD** (K1–K3): +56 bp t 1.6, all from 2005–12. `RESULT_ECBDRIFT.md` |
| `PREREGISTRATION_NATGAS.md` | FLOWS-6: does natgas earn a premium on EIA storage-report days? | **DEAD, sign reversed**: −42 bp t −3.4 on report days; spread (44 bp) eats a short. `RESULT_NATGAS.md` |

| `PREREGISTRATION_FIXES.md` | FLOWS-8: does the dollar rise into the Tokyo/London FX fixes and fall after (JF 2024)? | **DEAD** (K2,K3): replicates (t 4.9), decayed to +0.4 bp since 2019; −11 bp net. `RESULT_FIXES.md` |
| `PREREGISTRATION_EARNINGS.md` | FLOWS-9: does the index pay across top-10 firms' earnings releases? | **VOID at Step 0**: SEC float data cannot build the universe (mis-scalers; Apple/MSFT absent). No price read. `STEP0_EARNINGS.md` |
| `PREREGISTRATION_PREHOLIDAY.md` | FLOWS-10: the day before an NYSE holiday | **DEAD** (K1): +9.4 bp t 1.45; positive everywhere, largest since 2019. `RESULT_PREHOLIDAY.md` |
| `PREREGISTRATION_AUCTIONS.md` | FLOWS-11: intraday Treasury concession around note/bond auctions | **DEAD** (K3, cost only): +2.9 bp t 4.3, **not decayed** (E3 93%); net −0.1 bp on CFDs. `RESULT_AUCTIONS.md` |
| `PREREGISTRATION_HALLOWEEN.md` | FLOWS-12: Sell in May (NASDAQ 1971–2026) | **DEAD** (K1,K2): 1970s–80s only. `RESULT_HALLOWEEN.md` |
| `PREREGISTRATION_FXVALUE.md` | FLOWS-13: currency value, five-year real-rate reversal | **DEAD** (K2): +3%/yr, t 2.6, Sharpe 0.43, all from 1990–2002. `RESULT_FXVALUE.md` |
| `PREREGISTRATION_MACRO.md` | FLOWS-14: CAPE, term and credit spreads out of sample (1965–2026) | **DEAD**: none beats the historical mean (Shiller data ends 2023). `RESULT_MACRO.md` |
| `PREREGISTRATION_VEHICLE.md` | FLOWS-15: fastbot v36 noise-band on ES/NQ futures costs | **DEAD** (K2: 2013–17 net −1.5 bp). Pooled net +3.2 bp t 2.7; **NQ +5.8 bp t 3.9, +8.4 since 2022**. Forward-only lead. `RESULT_VEHICLE.md` |
| `PREREGISTRATION_FORWARD_NQ.md` | FORWARD_NQ: v36 rule N on NQ futures, recorded forward (paper) from 2026-10-12 | **RECORDING** via fastbot forward_tick.sh step 7; one evaluation at 500 trade-sessions (~3.5 yrs) |
| `PREREGISTRATION_FORWARD_NQ_STOP.md` | FORWARD_NQ_STOP: the same, with a fixed 0.5% stop (from the stops_nq study) | **RECORDING** alongside FORWARD_NQ; own verdict at 500, stop-vs-no-stop S1 at the base's 500 |
| `PREREGISTRATION_MACDFF.md` | FLOWS-16: MACD "fake filter" exhaustion crosses on NQ futures, 15m | **DEAD** (K1–K3): +0.09 bp/trade; worse than plain crosses and no better than random. `RESULT_MACDFF.md` |
| `PREREGISTRATION_TSYFUT.md` | FLOWS-17: FLOWS-11's auction concession on ZN/ZB futures (intraday A, pre-short B, 5-day cycle C) | **NOT TRADEABLE** (A G4, B1, C1): replicates on ZN (+2.76 bp, t 4.11, E3 91%), but 1-tick spread x4 > edge (net −0.46); nothing since 2025-04. `RESULT_TSYFUT.md` |

**Considered and not registered (2026-09-28), with the reason:**
- Commodity value (five-year reversal): OANDA commodity history starts 2005, which is four independent five-year periods. It cannot be measured.
- Crude-oil EIA report days: the same family as FLOWS-6 (natgas EIA), so it would break rule 2.
- Dividend-payment days: needs a paid calendar.
- Late-day index reversal after 2022: fitted to v35/v36, which have already been seen.
- Country CAPE rotation: no free long history for non-US valuations.

FLOWS-4 to -6 add one gate to every era test: **the most recent era must carry
at least half the full-sample effect.** This comes from FLOWS-2, which passed a
sign-only era gate on an effect that had decayed to almost nothing.

Rank 8 of the literature report (late-day index reversal after May 2022) is
**not registered**. fastbot v35 and v36 have already measured last-30-minute
momentum by era, including its turn negative after 2022, so an index reversal
test on 2022–26 would be fitted to a result already seen. It can only be
confirmed on forward data.

## Step 0 — the data pulls

Run on your Mac (needs the OANDA token; a FRED key is optional):

    bash ~/RStudio/Claude/flows/pull_all.sh

| script | fetches | into `flows/data/` | used by |
|---|---|---|---|
| `fastbot/scripts/pull_m1.py` | USB10Y, DE10YB, USB30Y — M15 bid + ask from 2005 | `*_bid_15m.csv`, `*_ask_15m.csv` + provenance | FLOWS-1, 2 |
| `fetch_financing.py` | OANDA long/short rates and days-charged table, 7 instruments | `financing_snapshot.json` | FLOWS-1 cost; FLOWS-2/3 evidence of no rollover |
| `fetch_fred.py` | DGS10, DGS30, DGS3MO, ECBDFR | `fred_*.csv` | FLOWS-1 roll-flag check, financing benchmarks |
| `refunding_events.py` | Treasury borrowing-estimate release dates, 2005-Q1 to 2026-Q3 | `refunding_events.csv` | FLOWS-2 event table |
| `fetch_eia_calendar.py` | nothing (offline rule): EIA report Thursdays, holiday and shutdown weeks excluded | `eia_events.csv` (frozen 9f208aac…) | FLOWS-6 |
| `fetch_announce.py` | GDP release dates (ALFRED rid=53, name-verified); ISM by rule; CPI/NFP/FOMC from fastbot | `announce_events.csv` | FLOWS-4 |
| `fetch_ecb.py` | scheduled ECB monetary policy decision dates, 2005–2026 | `ecb_events.csv` (+ `ecb_raw/`, ignored) | FLOWS-5 |
| `pull_m1.py` via `pull_next.sh` | NATGAS_USD M15 bid + ask from 2005 | `natgasusd_*_15m.csv` | FLOWS-6 |

`pull_next.sh` runs the last four in one go **on the Mac**. The Cowork VM's
proxy blocks ALFRED, the ECB and OANDA.

FLOWS-3 needs no new data: SPX500, NAS100, US30 and DE30 bid/ask are already
in `fastbot/data/v24`. The index legs of FLOWS-1 come from there too.

Nothing in Step 0 computes a return. The refunding table reads no prices and
is frozen by its sha256 before any bond price is joined to it; any quarter it
cannot confirm automatically is marked and must be resolved by hand first.

The price CSVs stay gitignored. The event table, `financing_snapshot.json`
and every `*.meta.json` provenance file are tracked.

## The harnesses

    python3 flows/<test>.py --self-test      synthetic data, planted effects -- run any time
    python3 flows/<test>.py --check-inputs   files, hashes, coverage -- computes NO returns
    python3 flows/<test>.py --run            the registered test. Run once.

`monthend.py` (FLOWS-1), `refunding.py` (FLOWS-2), `overnight.py` (FLOWS-3),
sharing `common.py`. Each refuses to run if its pre-registration's sha256
differs from the pin in `common.py`; `refunding.py` also pins the event table.
Each `--run` writes `data/<test>_run.log` and `data/<test>_result.json`
(both tracked), plus its trade list. Needs numpy and pandas: in the Cowork VM
plain `python3` has them; on the Mac use `pineport/.venv/bin/python`.

Input checks on 2026-09-26, no returns computed: FLOWS-1 259 usable months
(218 replication, 41 holdout); FLOWS-2 87 events, every P has a bond bar
(76 replication, 11 post-paper); FLOWS-3 1,463 windows in P2, about 146
sell-offs expected.

## Implementation readings, fixed before any run (2026-09-26)

Where a pre-registration left something open, the harness takes the reading
below. Written down and committed before any `--run`, so none of them can
have been chosen after seeing a result.

1. **FLOWS-1 bond-CFD financing.** The document says "benchmark plus OANDA's
   markup". For a bond CFD the live rates only make sense as carry: a long
   earns the yield and pays the benchmark. So long = (DGS10 - DGS3MO) -
   markup_long and short = (DGS3MO - DGS10) - markup_short, each markup
   calibrated from today's live rate. Index CFDs use the oanda_financing.py
   method unchanged. Affects G7 costs only.
2. **FLOWS-1 G4, G5, G6 sample.** No sub-period is named, so they use the
   full primary sample (the "N ≈ 257" of section 3). G1 and G3 use the
   periods their rows name.
3. **FLOWS-2 G4 placebo sample.** Compared against G1, so fitted on G1's
   sample, 2005-2023. A control that is all zero in a sub-sample is dropped
   and recorded rather than left to make the design singular.
4. **FLOWS-3 definitions.** A session needs both its 09:30 and 15:45 bars as
   well as 20 of 26 bars; a window needs its 02:00 and 02:45 bars. The
   placebo 20:00-21:00 ET window is the evening of the sell-off session
   itself. The descriptive DE30 check conditions on SPX500 sell-offs, since
   the mechanism is the US closing imbalance. NAS100 and US30 each use their
   own sessions.
