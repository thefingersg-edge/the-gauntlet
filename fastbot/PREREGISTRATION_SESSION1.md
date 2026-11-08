# PREREGISTRATION — SESSION1: do the 24-hour structure and pattern failures survive a cash-session-only re-run?

```
STATUS:   frozen before any SESSION1 number is computed (sha in PROVENANCE.md)
WRITTEN:  2026-10-09
TYPE:     ROBUSTNESS CHECK of already-published FAILs (v51 15m BOS/CHoCH; TF1 30m and 1h).
          The 24-hour results are known. This test answers one objection only:
          "structure / pattern traders only trade the cash session — your 24-hour test includes thin hours."
DATA:     the same files as v51 and TF1 (OANDA bid/ask 15m, data/v24 + data/v38), end 2026-09-26. Nothing new.
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## Why
`OBJECTIONS_2026-10-09.md` item B: v51 (break of structure / change of character) and TF1 30m/1h/4h ran on all 24 CFD hours. Every other bar-pattern test (v1, v2, 1m TF1) used the New York cash session. 4h is left out: a 4-hour bar cannot sit inside one cash session.

## Part A — v51 structure, cash session only
- **Instruments, bars, events:** as v51 (SPX500, NAS100, UK100, XAUUSD; 15m mid bars; `struct15.structure_events`, pinned; widths k = 2, 3, 4, 5).
- **Sessions (local time, DST-aware):** SPX500 and NAS100 09:30–16:00 New York; UK100 08:00–16:30 London; XAUUSD 08:30–13:30 New York (COMEX hours on the 15m grid).
  A bar is "in session" if it **starts** at or after the open and **ends** at or before the close.
- **Primary (A1):** events are computed on the full 24-hour series (a trader sees the whole chart). A trade is taken only if the entry bar a = j+1 is in session. Exit = close of bar min(j+16, last in-session bar of that day). Hold therefore ≤ 4h and always flat by the close; no financing.
- **Cost:** one full quoted spread at the entry bar (as v51).
- **Gates (all must pass, per kind, as v51):**
  - G1 net > 0 and t ≥ 2.24 (clustered by date) at every k.
  - G2 excess over the in-session drift (mean of every in-session window with the same exit rule, by year) > 0 at every k.
  - G3 k=3 net > 0 in each era 2005–12, 2013–19, 2020–26.
  - G4 k=3 net > 0 on at least 3 of 4 instruments.
  - G5 (new) k=3 net beats random in-session entries (same instrument, same direction, same exit rule, 20 draws per trade, seed 0) with two-sample t ≥ 2.
- **Reported, no gate (A2):** events computed on a series made of in-session bars only (each day's session spliced to the next), same trade rule.

## Part B — TF1 30m and 1h, cash session only
- **Instruments, patterns:** as TF1 (NAS100, SPX500; `patterns.detect` 1.0, 40 pattern tests; BOS and CHoCH, k = 2–5 pooled).
- **Bars:** TF1's construction (15m resampled, origin epoch).
- **Session and execution:** the v2 engine's cash session (`engine.SESSION` 09:00–16:00 New York) and v2's `patterns.trades`:
  - signal bar, entry bar and exit bar all in session on the same day;
  - stop entry;
  - at most 4 trades a day;
  - spread paid on both sides;
  - no financing (flat by the close).
- **Hold:** 3 clock hours on both timeframes. On 30m that is 6 bars, as in TF1. On 1h it is 3 bars, because a 6-bar hold cannot fit inside a 7-hour session. Structure trades use the same hold: H = 6 on 30m, 3 on 1h. Entry is at the open of j+1 and exit at the close of j+H, with entry and exit in session on the same day.
- **Benchmark:** TF1's matched random entries, at the same firing rate per (New York hour × year) cell, 20 draws, seeds as TF1. They run through the same session engine.
- **Gates (as TF1):**
  - t ≥ 3.4 (date-clustered).
  - Beats random with t ≥ 2.
  - Mean > 0 in every era.
  - n ≥ 200.
  - Structure tests only: the sign is the same at each k.

## Verdict and what each outcome means
- SESSION1 **changes nothing** if every test that FAILED on 24 hours also FAILS on the cash session. In that case objection B is answered.
- Any test that PASSES here is a **lead, not a finding**, because the 24-hour version was seen first. It would go to a fresh pre-registration with a forward record, never straight to money.
- Reported, no gate: the 24-hour vs cash-session mean side by side for every test.

## Trade-level output
Each trade is saved with instrument, date, side, net return, and its random-draw partners. This lets **REGIME1** (pre-registered in the same commit) filter them by higher-timeframe direction without re-running anything.
