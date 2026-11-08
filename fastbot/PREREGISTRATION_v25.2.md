# PREREGISTRATION v25.2: amendment to v25 / v25.1. The ledger recorded events before they happened

Written and frozen 2026-10-04, before the next event (CPI, 2026-10-14). Approved by Dave the same day. It changes **when** a row is written and nothing else: no instrument, window, sign, cost, stopping rule or gate.

- **Recorder:** scripts/forward_ledger.py **v1.1** (sha256 9943a104aba5…), run by forward_tick.sh as before.

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. The bug
- forward_ledger.py v1.0 treated an event as due when its date was ≤ `dt.date.today()`, on the **Mac's local calendar**.
  - The 23:52 UTC tick on 2026-10-01 ran at 00:52 London, already 2 October there, and wrote all six NFP rows with `bars_present=no`.
  - The ledger is append-only, so those rows can never be filled.
- Moving to UTC or New York time would not have fixed it: the 05:53 and 11:53 UTC ticks on the day also come before the 08:30 ET release. **As written, v1.0 would have recorded every future event as skipped.**
- The self-test missed it because it pinned `today` to a fixed date and never tested the time of day.

## 2. The fix (v1.1)
- An event is **due only once now ≥ 10:30 ET on the event date**. That is the 09:45 exit bar closing at 10:00, plus 30 minutes for OANDA to publish the completed candle.
- `today` (used for runway) is now the New York date.
- Planted tests cover:
  - the exact 2026-10-01 23:52 UTC case;
  - the 05:53 and 11:53 UTC ticks;
  - 10:29 vs 10:30 ET;
  - 13:53 ET;
  - a winter (EST) CPI day.
- A genuinely missing bar after 10:30 ET is still recorded as a skip, exactly as v25 §4 requires.

## 3. The 2026-10-02 rows (v25 §7: history is never recomputed)
- The six NFP rows written by v1.0 **stay in data/forward_ledger.csv unchanged.** They are marked here as **void by the v25.2 bug** and count toward no verdict, cost check or fast-arm total.
- **Descriptive only, not ledger rows, not counted.** On 2026-10-04, v1.1 run against an empty scratch ledger gave what the event would have recorded:

| instrument | direction | gross bp | net bp | spread in / out bp |
|---|---|---|---|---|
| SPX500 | short | −17.12 | −17.70 | 0.65 / 0.52 |
| NAS100 | short | −23.72 | −24.26 | 0.81 / 0.26 |
| US30 | short | +6.51 | +5.88 | 0.58 / 0.68 |
| DE30 | long | +26.58 | +24.99 | 1.98 / 1.19 |
| EUR_USD | short | −13.12 | −14.50 | 1.33 / 1.42 |
| XAU_USD | short | +58.91 | +57.42 | 1.71 / 1.29 |

- The first counted event is therefore **CPI, 2026-10-14**. v25's power arithmetic (about 5 months to validate execution) moves back by one event.

## 4. Nothing else changes.
