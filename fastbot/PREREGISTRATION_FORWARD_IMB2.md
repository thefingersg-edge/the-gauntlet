# PREREGISTRATION — FORWARD_IMB2: a paper forward record of the 15:50 imbalance trade at a 1-second delay

```
STATUS:   frozen before the first forward day (sha in PROVENANCE.md). The ledger appends only, and history is never recomputed.
WRITTEN:  2026-10-11 (Dave: "lets do all 4", option 2 after RESULT_IMB2)
BUILDS ON: IMB2 PASS as registered (L = 1 s, SPY, net +1.31 bp, t 3.15, n 487). Post hoc, 2020 alone made +7.74 bp; the other years
           were about +0.3 bp, and the random-side placebo was -0.60 bp.
CODE:     scripts/forward_imb2.py (stdlib only; it runs on the Mac under forward_tick.sh as a NON-FATAL step).
          The trade maths is defined locally, and its self-test must reproduce IMB2's primary result exactly from the historic files.
```
**I am not a financial adviser. This is a measurement, not a recommendation. Paper only: nothing here places an order.**

## What is recorded, each US trading day from 2026-10-12
- **Data** (Databento, the same requests as scripts/databento_imb2b.py):
  - `imbalance` messages for the S&P 500 members at 15:49:59.5–15:50:05 ET, with arrival times (first message per stock);
  - SPY `mbp-1` at 15:49:59.5–15:51:01.
  - **Membership** is frozen at the last list in data/imb1/members.csv (2026-09-30). Index changes after that are ignored and disclosed.
- **Signal:** exactly IMB2.
  - S = the signed imbalance $ ÷ the paired $ over messages arrived by 15:50:01.000;
  - z is standardised on the previous 250 trading days of S (historic days count);
  - trade when |z| ≥ 1.
- **Paper trade:**
  - buy SPY at the ask (sell at the bid) of the last quote at or before 15:50:01.000, in the direction of z;
  - exit at the opposite side at 15:51:00.000;
  - commission $0.0035 per share each way.
- **Ledger:** data/forward_imb2.csv gets one row per day, with status traded / no_signal / no_auction / missing_px. The row records S, z, the prices, gross and net bp, the mid move, the message count and the code version.
- **Cost guard:** a pull estimated above **$1.00 for one day** is refused and logged. The ledger never fills a day by guessing.

## Decision rules, fixed now
- **No running mean is shown** before the 12-month review. `--status` prints counts only. This stops anyone from stopping early on a good or bad streak.
- **12-month review (2027-10):** reported only, with no decision.
- **24-month review (2028-10), about 130 trades expected at the historic signal rate:**
  - **KEEP** if the forward mean net > 0 bp AND t ≥ 1.0;
  - **DROP** if the forward mean net ≤ 0;
  - otherwise **EXTEND** once, for 12 months, under the same rule, then KEEP or DROP.
- **A KEEP does not mean money.** It permits a new pre-registration for a live-latency test. That test would measure the real broker round-trip at 15:50 and use a small real size, because a paper 1-second fill is an assumption, not a measurement.

## Known limits, written in advance
- **The 1 s fill is an assumption.** A retail API's real delay is unknown until it is measured.
- **The quotes are top-of-book only.** A real order may move the price; an order of a few hundred SPY shares would usually not.
- **The forward period may contain no 2020-like days.** The expected forward edge is the post-2020 figure, about +0.3 bp, which 130 trades cannot separate from zero. The 24-month rule is therefore a **sanity check that it hasn't turned negative**, not proof of an edge.
