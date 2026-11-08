# PREREGISTRATION v25.3: amendment to v25 / v25.1 / v25.2. The calendar forgot its own dates

Written and frozen 2026-10-24, before the next event (NFP, 2026-11-06). Approved by Dave the same day ("stick with your recommendation"). It changes **which dates the calendar keeps** and records one event as missed. Nothing about instruments, windows, signs, costs, stopping rules or gates changes.

- **Calendar:** scripts/calendar_forward.py **v1.6** (sha in PROVENANCE), run by forward_tick.sh exactly as before.
- **Recorder:** scripts/forward_ledger.py v1.1, unchanged.

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. The bug
- calendar_forward.py v1.5 rebuilt data/events_v3.csv on every tick from two sources:
  - events_v2.csv (ALFRED history, which ends 2026-09);
  - the dates **currently shown** on the BLS schedule pages.
- Around 2026-10-10 the BLS pages rolled from "the 2026 schedule" to "the next 14 releases" (Nov 2026 → Dec 2027).
- From then on, the October dates (NFP 2026-10-02, CPI 2026-10-14) were in neither source, so they disappeared from the calendar.
- The ledger asks the calendar which events are due. It never saw **CPI 2026-10-14**, so it wrote nothing for that release.
- **Nothing warned.** The runway check looks forward (it still showed about 420 days), and the tick reported "ok" every time.

## 2. The 2026-10-14 CPI release: counted as MISSED
- It is **not** recorded late from stored bars, even though the OANDA bars exist. Recording an event 10 days after the fact, by hand, is a different procedure from the forward test v25 registered.
- It counts toward no verdict, cost check or fast-arm total. The v25 power arithmetic moves back one more event.
- calendar_forward v1.6 holds an explicit exclusion for (CPI, 2026-10-14), so no later file can bring it back.
- The six NFP 2026-10-02 rows stay void, as in v25.2.
- **The first counted event is now NFP, 2026-11-06.**

## 3. The fix (v1.6)
- Every (release, date) parsed from a BLS page is appended to **data/bls_schedule_seen.csv** (event, date, first_seen_utc, source). The file is append-only and never rewritten.
- events_v3.csv is built from events_v2.csv plus **every** date in that file (minus the exclusion), not just the page's current dates. A date therefore stays in the calendar permanently once any page has shown it.
- Unchanged:
  - the ALFRED/BLS cross-check;
  - the 6–15 dates-per-page parse bounds;
  - the phantom check (two releases sharing dates);
  - the fetch-failure exit (3);
  - the runway warning.
- **Planted self-tests:**
  - the 2026-10-10 roll: the page drops a date and the calendar keeps it, with a check that v1.5's page-only rule would have lost it;
  - the seen file is append-only, with one line per date;
  - CPI 2026-10-14 stays excluded even if a file holds it;
  - releases don't leak into each other.
- **The seen file starts empty.** On the first Mac tick it fills from the current pages (Nov 2026 → Dec 2027). No past date is seeded, so nothing before 2026-11-06 can be recorded late.

## 4. Nothing else changes.
