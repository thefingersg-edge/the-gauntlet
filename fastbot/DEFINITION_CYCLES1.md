# DEFINITION — CYCLES1: what counts as a bull or bear market, and when could you have known?

```
STATUS:   frozen before any phase is dated (sha in PROVENANCE.md). The dates come from the rule, never from hindsight edits.
WRITTEN:  2026-10-09
TYPE:     DESCRIPTIVE CATALOGUE (not a trading test). It is the base layer for later "what caused them" work.
DATA:     (a) S&P Composite monthly price, 1871-01 -> 2026-09: Shiller series via the datasets/s-and-p-500 GitHub mirror
              (data/cycles/shiller_monthly.csv, sha in PROVENANCE). The prices are MONTHLY AVERAGES of daily closes.
              Earnings, CPI, long rate and CAPE run to 2023.
          (b) Daily cash closes 2005-10 -> 2026-09-25: SPX500, NAS100, UK100, XAUUSD (daily_close.py, as v52/REGIME1).
          (c) NBER US recession peak/trough months (table in cycles1_run.py). Typed from the published NBER list;
              to be checked against FRED USREC when the FRED pull runs.
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## The rule (the standard "20% rule", written so a computer applies it the same way every time)
This is the convention used by the press and by Lunde & Timmermann (2004, λ = 20%), applied to closes.
- **Starting state** is taken from the data. Begin at the first close, track the running high and the running low, and assign the first state when one of them is breached by 20%.
- **A bear market** starts at a **peak**: the highest close since the previous trough. The bear exists once a later close is ≤ 80% of that peak.
- **The bear ends** at the **trough**: the lowest close before price closes ≥ 120% of that trough. The next bull runs from that trough to the next peak.
- **Dates:**
  - The *peak date* and *trough date* are the dates of the extreme closes. These are the dates the newspapers use, and they are **only known afterwards**.
  - The *confirmation date* is the first close that crosses the 20% line: down 20% from the peak for a bear, up 20% from the trough for a bull. This is the first day the label could be applied **in real time**.
- **Corrections (reported, not phases):** declines of 10% up to, but not including, 20% inside a bull, measured from the highest close to the lowest close before a new high.
- **Same rule on monthly data.** Monthly averages flatten short crashes. 1987, 1990, 2020 and 2025 may show as corrections, not bears. That is a known limit of series (a), and why series (b) is run alongside it.

## What is measured for each phase
**Dating and real-time measures:**
- peak date, trough date, depth (%), duration, and confirmation date;
- **lag:** time from the peak to confirmation;
- **share already gone:** the share of the eventual fall that had already happened at confirmation (log terms);
- **what was left:** the return from confirmation to the trough;
- **if you had waited for the bull confirmation:** the share of the next bull's gain already gone by its confirmation.

**Context for "causes" (monthly series, reported only, no gates):**
- whether an NBER recession overlapped (it started between 12 months before the peak and the trough);
- CAPE at the peak;
- the change in real earnings from peak to trough;
- the change in the long rate;
- CPI inflation in the 12 months to the peak.

## Real-time "detector" check (reported, no gates)
For each rule, how many bears it caught, how many false alarms it gave, how late its first signal was relative to the peak, and how much of the fall had already happened at that point.

| Rule | Data | Signal |
|---|---|---|
| 20% confirmation | as above | down 20% from the peak |
| Daily trend | daily (b) | close < 200-day SMA (REGIME1 F1) |
| Monthly trend | monthly (a) | close < 10-month SMA ("Faber" rule) |

A rule *catches* a bear if it first signals between the peak and the trough. A *false alarm* is a signal episode that starts and ends inside a bull without a bear following within 6 months.

## What this does and does not claim
- It **defines** bull and bear phases, so every later "cause" study uses the same dates.
- It **measures** how late the label arrives.
- It does **not** test a trading rule. Any rule suggested by the catalogue needs its own pre-registration.
