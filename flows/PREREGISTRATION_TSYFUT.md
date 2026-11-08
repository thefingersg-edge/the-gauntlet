# PREREGISTRATION FLOWS-17 — the Treasury auction concession, on Treasury futures

```
WRITTEN:   2026-10-30, before any intraday Treasury-futures price has been fetched.
STATUS:    FROZEN at its first commit; tsyfut.py pins this file's sha256 (common.PINS["TSYFUT"]).
SOURCE:    FLOWS-11 (RESULT_AUCTIONS.md); Lou, Yan & Zhang (RFS 2013); NY Fed SR1188 (2026);
           Robeco, "US Treasuries up for auction" (2025-03), which says it trades this in 10-year futures.
VEHICLE:   CME 10-Year T-Note futures (ZN), volume-ranked front contract (Databento ZN.v.0).
           Secondary: 30-Year T-Bond futures (ZB.v.0).
DATA:      Databento GLBX.MDP3, schema bbo-1m (best bid and ask, one-minute intervals),
           2010-06-07 -> 2026-09-01, fetched by fetch_tsyfut.py on Dave's Mac (cost shown first, capped at $25).
EVENTS:    data/auction_events.csv, frozen for FLOWS-11 (sha256 d1bfd601…), unchanged.
```

*Measurement, not a recommendation. Not financial advice.*

## 0. Why this, and what is already known
- **FLOWS-11 found the concession real and not decayed** (+2.91 bp, t 4.34; E3 at 93% of full size). It died only on cost: two round trips on the bond CFD cost about 3 bp.
- **Futures are the cheaper vehicle.** A one-tick ZN spread is about 1.4 bp of price, with no CFD financing.
- **Disclosure: these choices were made after seeing FLOWS-11.**
  - FLOWS-11's PRE leg was −1.86 bp, its POST leg +1.05 bp, and its descriptive multi-day legs about −5.5 / +5.3 bp.
  - Robeco's note describes the short-before and long-after trade on 10-year futures.
  - The **futures prices** for these windows have not been seen. ZN and ZB *daily* bars (data/futport1) were read by FUTPORT1 for an unrelated question; this test does not use them.
- **Not a new parameter on a closed family (Rule 2):** FLOWS-11 is closed on CFDs. Its RESULT names a futures test as the follow-up, to be registered before any futures data is read.

## 1. Prices
- **Book at time t:** the latest bbo-1m record for the contract with ts_recv ≤ **t − 60 s**. This avoids any look-ahead, whichever end of the minute Databento stamps. If no record falls within 10 minutes of that, the event is skipped and counted.
- Mid = (bid + ask) / 2. A record with bid ≤ 0, ask ≤ bid, or ask/bid − 1 > 50 bp is unusable and treated as missing.
- **Roll:** a window is used only if every one of its stamps is on the same instrument_id. Windows that straddle a roll are skipped and counted.
- **Cost:** trades buy at the ask and sell at the bid, plus **$2.00 per contract per side** (broker plus exchange, conservative), converted to bp of notional (price × $1,000).

## 2. Events and anchors
- **Auction day:** a date in auction_events.csv with at least one Note or Bond auction, longest tenor recorded, from 2010-06-07 to 2026-08-31 (858 days).
- **Tenor is read from the numeric `years` column, not the label.** Reopenings are labelled "9-Year 10-Month", "29-Year 11-Month" and so on.
  - **10-year auction:** 9.5 < years ≤ 10, new issues and reopenings (196 in sample).
  - **30-year auction:** years > 29.5 (195 in sample).
- **T** = the published competitive close (13:00 ET unless listed otherwise; minute precision, DST-aware).
- **Eras, as FLOWS:** E1 2010-06-07 → 2012-03-31 (short, because futures history starts 2010-06), E2 2012-04 → 2019-06, E3 2019-07 → 2026-08.

## 3. Part A — FLOWS-11 replicated on ZN (all auction days)
- PRE = mid(T) / mid(T − 3 h) − 1. POST = mid(T + 3 h) / mid(T) − 1. **R = POST − PRE**, in bp.
- **Trade:** short at the bid at T − 3 h, cover at the ask at T; buy at the ask at T, sell at the bid at T + 3 h; 4 commissions.

| gate | test | pass |
|---|---|---|
| **G1** | mean R | > 0, t ≥ 2.0 (Newey–West 5), as FLOWS-11 |
| **G2** | E1, E2, E3 | R > 0 in all three, **E3 ≥ 0.5 × full** |
| **G3** | PRE and POST | PRE < 0 and POST > 0 |
| **G4** | trade net | **mean > 0, t ≥ 2.13** (NW 5), E3 net > 0 |
| **G5** | placebo: same 13:00 windows on non-auction NY weekdays | t < 2.0 and mean < mean R |

**A is tradeable only if G1–G5 all pass.**

## 4. Part B — the pre-auction short only (one round trip)
- Short at the bid at T − 3 h, cover at the ask at T, 2 commissions.
- **B1:** mean net > 0, **t ≥ 2.13** (NW 5).
- **B2:** E3 mean net > 0.

## 5. Part C — the multi-day cycle, 10-year auctions only, on ZN
- **Sessions:** NY weekdays with a usable ZN book at 15:00 ET.
- **Pre leg:** short at the bid at 15:00 ET on the 5th session before D. Cover at the ask at T on D.
- **Post leg:** buy at the ask at T on D. Sell at the bid at 15:00 ET on the 5th session after D.
- Net per event = both legs plus 4 commissions. Gross uses mids. An event with a leg straddling a roll, or without the sessions, is skipped and counted.
- 10-year auctions are about monthly. If an event's entry falls on or before the previous used event's exit, the later event is skipped.
- **C1:** mean net > 0, **t ≥ 2.13** (plain t, because the events do not overlap).
- **C2:** E3 mean net > 0, **and** E3 gross ≥ 0.5 × full gross.

## 6. Verdicts
- Each part gets its own verdict. **The test as a whole is "tradeable on futures" if A, B or C passes.**
- The three trade gates use t ≥ 2.13 (one-sided 5%, Bonferroni over three) because three ways to trade the same effect are being tried.
- A PASS earns a paper forward record with its own pre-registration, not live trading.

## 7. Reported, gating nothing
- ZB on 30-year auction days (A-style windows and trade), and C-style legs on 30-year auctions.
- Part A by longest tenor of the day.
- The post-Robeco subsample, 2025-04 → 2026-08 (A, B, C), because publication by a large manager is a decay risk.
- Median ZN entry spread in ticks and bp, and commission in bp; counts of skipped events by reason.
- **C placebo:** the same legs anchored on the 10th session after each 10-year auction, at 13:00.
- Contract notional (price × $1,000) at the median event. **Account size is not gated.** ZN is about $110k of exposure per contract; margin and the Micro 10-Year Yield contract are to be checked with a broker.

## 8. Power and prediction, written now
- **A:** FLOWS-11's R had SE ≈ 0.67 bp on the 10-year cash price. ZN moves about 0.8× as much (cheapest-to-deliver duration), so R ≈ +2.3 bp and SE ≈ 0.6 bp. The trade costs about 2 × (1 tick ≈ 1.4 bp + 0.36 bp commission) ≈ 3.5 bp. **Prediction: G1 PASS, G4 FAIL.**
- **B:** PRE ≈ −1.5 bp against ≈ 1.8 bp of cost. **Prediction: FAIL.**
- **C:** about 190 events. With a 5-day ZN return SD of roughly 50–60 bp per leg, SE ≈ 5–6 bp, so **only a net effect above about 12 bp could pass**. FLOWS-11's descriptive ≈ 10.8 bp gross on cash (×0.8 for ZN, minus about 3.5 bp of cost) is below that. **Prediction: FAIL, sign positive.**
- So the expected result is that futures **do not** rescue the concession at retail cost. The point of running it is that this is the one effect where the vehicle was the only thing that failed.

## 9. Files and order
    flows/fetch_tsyfut.py    (Mac) price check -> --confirm; writes data/tsyfut/ + tsyfut.meta.json (sha per file)
    flows/tsyfut.py          --self-test | --check-inputs (no returns) | --run (once)
    flows/RESULT_TSYFUT.md

## One run. No change of contract, windows, anchors, cost, eras or gates after any futures price is read.

---
*Amendment A0, 2026-10-30, before any futures data was fetched: the label was changed from FLOWS-16 to FLOWS-17, because FLOWS-16 already denotes MACDFF. Nothing else changed (see the git diff against 6d8f48b).*
