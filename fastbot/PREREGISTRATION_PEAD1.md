# PREREGISTRATION PEAD1: drift after the earnings-announcement return (EAR), US single stocks, by liquidity band

> Named PEAD1 rather than v54: other sessions took v54-v58 on 2026-10-02. A topic name cannot collide.

**Frozen 2026-10-02**, after the Sharadar files were hashed (PROVENANCE.md) and their schema checked, and before any signal-conditioned return was computed. The budget below used counts and squared returns over *all* announcements only. The harness `singlestock/pead1_run.py` pins this file and `pead_engine.py` / `ss_lib.py`.

I am not a financial adviser. This is a measurement, not a recommendation.

## Question
Do US stocks keep drifting after a strongly positive earnings-announcement reaction? Does that survive realistic costs in the liquidity bands a small trader can use, and is it still there in 2018–2026?

## Why EAR, not SUE
- **EAR is fully point-in-time from prices.** Sharadar's fundamentals become available at the 10-Q filing date, often weeks after the press release, so using them at the announcement would be look-ahead.
- **It has the stronger record.** Brandt et al. (1987–2004) find EAR-sorted drift of about 6.3% a year, larger than the SUE version, and not confined to small firms.
- SUE (entered after the 10-Q filing) is **reported only**.

## Data (Sharadar bundle, full history; files hashed before reading)
- **Announcements:** `stocks` (SEP) daily prices including delisted tickers; `events` (8-K code 22 = Item 2.02); `actions` (delistings); `tickers`.
- **Sample:** Item 2.02 exists from August 2004, so the sample is **2005-01 → 2026-09**.
- **Spread:** estimated per stock with EDGE (Ardia, Guidotti & Kroencke, JFE 2024; `bidask` package, vendored wheel sha 8cbd4e27…).

## Definitions (singlestock/pead_engine.py, frozen with this document)
- **Bands:** each month, stocks priced ≥ $5 are ranked by median 20-day dollar volume before the month starts.
  - **L** = top 500, **M** = next 1,000, **S** = next 2,000, **X** = the rest.
  - **The primary universe is M + S.** L is reported. X is reported but excluded, because it is untradeable at size and has unreliable spreads.
- **Benchmark:** the equal-weighted daily return of the stock's band.
- **EAR:** the sum over trading days k−1..k+1 of (stock return − band return), where k is the first trading day on or after the 8-K date.
- **Timing:** EAR is known at the close of k+1. **Entry at the open of k+2**, so the before-open / after-close timing doesn't matter.
- **Signal:** EAR in the top decile of all EARs in the same band known in the prior 91 days (at least 50 of them). **Long only.**
- **Hold:** 60 trading days (primary); 20 days reported.
- **Return:** the stock's total return (adjusted) from the entry open to the exit close, minus the band's return over the same days.
- **Cost:** the EDGE spread from the 60 days before k (band median if missing), plus 2 × $0.0035 / price commission. 0.03% × 2 currency conversion is reported as a variant.
- **Delisting inside the hold:** the position ends at the last close. A non-merger delisting adds −30%.
- **SEs:** clustered by entry week.

## Gates (60-day primary; one primary test, so t ≥ 2.0; 2018+ is a conjunction, not a separate family)
- **G1:** M+S mean net excess > 0, t ≥ 2.0.
- **G2:** net > 0 in each era (2005–12, 2013–19, 2020–26) **and** net > 0 with t ≥ 2.0 on **2018–2026** alone.
- **G3:** net > 0 in M and in S separately.
- **G4:** gross excess beats the 95th percentile of 500 nulls that pick a random 10% of the same band and month's announcements. This checks that EAR selection matters, not just "after earnings".
- **G5, practical:** a calendar-time daily portfolio of open positions has a Sharpe ≥ 0.5 on 2018–2026. It is built from the positions' daily **excess** returns over the band benchmark (equal weight, cost charged on the entry day). That makes it the hedged version, so market drift alone cannot pass it.

## Reported
- L and X bands; 20-day hold; currency-conversion variant.
- Bottom-decile EAR (short side, not traded).
- SUE after the 10-Q date.
- Spread estimates against band.
- Sensitivity to the −30% delisting assumption (0% and −50%).

## Changes forced by the schema (made before freezing, before any signal-conditioned return)
1. **SEP is not sorted by ticker.** The store is built in two passes (hash buckets, then per ticker). Duplicate rows from interrupted checkpoints are removed.
2. **The universe is restricted to US domestic common stock** (incl. Primary/Secondary Class) on NYSE, NASDAQ or NYSE American, delisted included. That is 17,048 tickers (16,904 with at least 60 rows). SEP also carries ADRs, preferreds and Canadian stocks, which are excluded.
3. **Delistings:** Sharadar writes a generic `delisted` action for *every* delisting. The −30% applies only when there is no merger or acquisition action for the ticker (acquisitionby / acquisitioncash / acquisitionstock / spacmerger / spinoff).
4. **Band reality:** after about 2010 there are only about 3,300–3,500 US common stocks at $5 or more, so the S band is "everything below M" and X is nearly empty. Bands are kept as defined.
5. **Standard errors:** these are now clustered by **calendar quarter of entry**, not entry week. 60-day holds overlap across weeks, so week clusters would understate the SE. This is more conservative.

## Data checks (schema only)
- SEP from 1997-12-31; 20,995 SEP tickers, of which 14,661 are delisted.
- 8-K Item 2.02 (code 22): 2004: 5,517 (from August), then about 16,000–20,000 a year through 2025, and 11,759 in 2026 to date.

## Budget (singlestock/budget_pead1.py, log data/budget_pead1.log; counts and squared returns over ALL announcements)
```
M+S 2005-2026: 238,800 announcements, top decile ~23,880, 60d excess RMS 20.7%  -> MDE 0.4% (event-level) to 1.7% (week-level)
M+S 2018-2026:  94,262 announcements, top decile ~ 9,426, RMS 24.2%            -> MDE 0.7% to 3.2%
per era (M+S): 2005-12 MDE 0.5-2.5%   2013-19 0.6-2.6%   2020-26 0.9-3.8%
EDGE round-trip spread, M+S: median 69 bp, 75th pct 116 bp
```
- The literature's EAR drift (about 6% a year long-short in 1987–2004, so roughly 1–1.5% per quarter on the long side) is **at or below the upper MDE and about the size of the cost**.
- **The test can see a surviving full-sample effect. A decayed one, net of about 70 bp, is near the limit.** That is written here before the run.

## Prediction (written now)
- G1 likely passes gross and is uncertain net. In S, EDGE spreads may eat most of it.
- **G2's 2018–2026 condition is where it most likely fails.**

## Harness
`singlestock/pead1_run.py`. The stages (unzip, store, bands, bench, events) run in short, resumable calls. Then `final` runs **once**: it refuses to run twice and refuses unless this document's sha and the engine files are pinned.

The staged end-to-end test on synthetic data (`singlestock/staged_test.py`) runs correctly. With synthetic spreads of about 2%, the planted gross excess of +3.4% (t 5.0) is found. It mostly fails net, which shows the cost charge bites as intended.

## Self-test (done 2026-10-02, synthetic Sharadar-format data, `singlestock/synth_test.py`)
- **Planted drift:** +2.85%, t 5.3 (OK).
- **No drift:** −0.64%, t −1.3 (OK).
