# DRAFT — PREREGISTRATION PEAD1: drift after the earnings-announcement return (EAR), US single stocks, by liquidity band

> Named PEAD1 rather than v54: other sessions took v54-v58 on 2026-10-02. A topic name cannot collide.

**Status: DRAFT, not frozen.** It is frozen by sha256 after the Sharadar files are hashed and their schema checked (column names, Item 2.02 coverage, delisted tickers present). That happens before any return is computed. Any change from this draft is listed in the frozen version.

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

## Budget
`budget_pead1.py`, computed from announcement counts and squared returns only, will be run and written in **before** freezing.

## Prediction (written now)
- G1 likely passes gross and is uncertain net. In S, EDGE spreads may eat most of it.
- **G2's 2018–2026 condition is where it most likely fails.**

## Harness
`singlestock/pead1_run.py`. The stages (unzip, store, bands, bench, events) run in short, resumable calls. Then `final` runs **once**: it refuses to run twice and refuses unless this document's sha and the engine files are pinned.

The staged end-to-end test on synthetic data (`singlestock/staged_test.py`) runs correctly. With synthetic spreads of about 2%, the planted gross excess of +3.4% (t 5.0) is found. It mostly fails net, which shows the cost charge bites as intended.

## Self-test (done 2026-10-02, synthetic Sharadar-format data, `singlestock/synth_test.py`)
- **Planted drift:** +2.85%, t 5.3 (OK).
- **No drift:** −0.64%, t −1.3 (OK).
