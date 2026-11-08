# PREREGISTRATION — ORBCORE1: does the bare opening-range breakout core work on markets we haven't used?

```
STATUS:   frozen before any ORBCORE1 number is computed (sha in PROVENANCE.md). The harness is frozen separately before its one run.
WRITTEN:  2026-10-12 (Dave: "pre register all of them so we can start pulling data")
ORIGIN:   ANALYSIS_WHAT_CHANGED_2026-10-12.md. A post-hoc look at UNGER2 A found the bare core (no filters, no stop) on DAX at +8.1 bp gross
          after 2016 (t 2.7). DAX has now been seen, so it is EXCLUDED from the gated test and gets a forward record instead.
DATA:     OANDA 5m bid/ask already on disk:
            data/v38: eu50eur, uk100gbp, jp225usd, au200aud
            data/:    spx500usd, nas100usd, us30usd (5m)
          From each market's first clean day to its last bar on disk (2026-08 or 2026-09). No pull needed.
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## The rule (identical on every market; only the clock changes)
- **Range:** the 60 minutes **before the cash open**, giving high HH and low LL. It needs at least 50 minutes covered by bars. delta = 1 × (HH − LL).
- **Signal window:** the first 60 minutes of the cash session.
  - A 5m bar that **closes** above HH + delta: long at the next bar's open.
  - A 5m bar that closes below LL − delta: short.
  - Only the first signal of the day is taken.
- **Exit:** at the close of the last bar before the session exit (table below). **No stop, no filters, no day-of-week rule.**
- **Costs:** the quoted half-spread at the entry bar and at the exit bar. No position is held over 17:00 New York, so there is no financing.

| market | clock | range | signal window | exit |
|---|---|---|---|---|
| EU50 (Euro Stoxx 50) | Europe/Berlin | 08:00–09:00 | 09:00–10:00 | 22:00 |
| UK100 (FTSE 100) | Europe/London | 07:00–08:00 | 08:00–09:00 | 21:00 |
| SPX500, NAS100, US30 | America/New_York | 08:30–09:30 | 09:30–10:30 | 16:00 |
| JP225 (Nikkei) | Asia/Tokyo | 08:00–09:00 | 09:00–10:00 | 15:00 |
| AU200 (ASX 200) | Australia/Sydney | 09:00–10:00 | 10:00–11:00 | 16:00 |

Missing spreads (zeros in early source data) take that market's 2012–2014 median, as in the UNGER batch.

## Gates (all must pass)
- **G1:** the pooled per-trade net mean across all 7 markets is > 0, with day-clustered t ≥ 2.0.
- **G2:** the pooled net mean is positive in each era: 2005–2012, 2013–2019, 2020–2026.
- **G3:** at least 5 of the 7 markets have a positive net mean.
- **G4:** the pooled mean beats the 95th percentile of a 1,000-draw random-direction placebo (same entries, exits and costs; seed 0).

## Reported (no gates)
- per market: n, net mean, t;
- the original Unger stop at the range edge;
- a wide stop at 2 × range from entry;
- long vs short;
- the pre-open-hour coverage by year (when each CFD started quoting before the cash open).

## Forward record on DAX (paper, appends only)
- **The record:** from 2026-10-13, the same bare rule on OANDA DE30, Berlin clock, using the 15m bars the Mac tick already pulls. One ledger row per trading day goes to data/forward_orbcore_dax.csv.
- **Review at 24 months:** KEEP if the forward mean net > 0 and is above the 5th percentile of the post-2016 DAX distribution of 24-month means; otherwise DROP.

## Prediction
- **G1 borderline.** Opening-range continuation is a documented intraday-momentum effect, but our SPX/NAS breakout tests (TF1, SESSION1) failed.
- **G3 uncertain:** the US indices may drag the pool down.
