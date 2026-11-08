# PREREGISTRATION v55: economist-consensus surprises, recorded forward beside v32's naive and Kalshi surprises

Written 2026-10-01, frozen 2026-10-02 at its first commit, before the first forward release (payrolls, 2026-10-02 08:30 ET). No consensus figure has been joined to any return. Recorder: scripts/record_consensus.py v1.0. Its sha256, and this file's, are pinned in the commit that freezes them.

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. Why
- v32 Part B records two surprise measures for each forward CPI and payrolls release: **naive** (first print minus the median of the previous 12) and **crowd** (first print minus Kalshi's implied median). It asks whether the v25 release fade is bigger after bigger surprises.
- The measure the literature actually uses is the **economist consensus**, and this programme has never had it. The TradingView connector's economic calendar carries it (`forecast`, `actual`, `previous`) for every US release.
- The calendar only lists events **from today forward**. Past consensus cannot be fetched, so this can only ever be a forward record. Nothing is back-filled.

## 2. What is recorded
- **Pull:** on each US CPI or payrolls release day, after 08:30 ET, a scheduled Claude session calls `get_economic_calendar(countries=["US"], importance=["high"])` for that day. The raw JSON is saved to data/v55/raw/<date>.json, and record_consensus.py appends to data/forward_consensus.csv (append-only).
- **Primary rows:**
  - CPI: "Inflation Rate MoM", the headline m/m in %, as in v32.
  - Payrolls: "Non Farm Payrolls", the change in thousands.
- **Also archived, gating nothing:** every other US high-importance event listed that day (core CPI, unemployment rate, and so on).
- **Columns:** release, date, title, forecast, actual, previous, unit, pulled_utc, status. Status is `ok`, `no_forecast`, `no_actual` or `missed`.
- **No repairs:**
  - A missed pull day is recorded as `missed`.
  - A value is never copied from another source.
  - A later revision is never written over a first print.

## 3. The test (same structure and horizon as v32 Part B, so the three measures can be read side by side)
- **Consensus surprise:** s = actual − forecast.
  - **z** = s / (the median |s| for that series over all recorded releases at verdict time). This is the same scaling as v32's crowd measure.
  - Using the record's own median is a unit choice. It cannot create a sign or a slope.
- **GC:** fade (v25 ledger, six instruments) / σ = a + b·|consensus z|.
  - **PASS** if b > 0 with t ≥ 2.0, SEs clustered by release date, on releases with status `ok`.
- **Reported, gating nothing:**
  - The same regression with v32's naive and crowd z on the same releases.
  - The correlation of the three surprises.
  - Signed z instead of |z|.
- **Horizon:** the same as v32, 150 CPI + payrolls release dates or 2032-09-30, whichever comes first. **Interim report:** 31 January each year, verdict-free, stopping only if |t| ≥ 3.5.

## 4. Failure modes, stated now
- **The connector or its calendar changes or disappears.** The record then stops, and its length at that point is reported. It is not patched from another vendor.
- **The forecast field could be revised after the release.** The recorded pull is made after the print. A second pull is made **before** 08:30 ET whenever a session is running then, saved to data/v55/pre/<date>.json, and never appended. Any difference between the pre- and post-release forecast is reported at the verdict. The first one was pulled on 2026-10-02 at 02:20 ET (payrolls consensus 90k, unemployment 4.1%).
- **A scheduled session can fail** (computer offline, connector down). Those days are recorded as `missed` by the next run that notices. They are counted against the horizon, not replaced.

## 5. Power, said plainly
- This shares v32's arithmetic: about 150 release dates (around six years) to resolve the roughly 6 bp gap the historical hints suggested. **It is a long, cheap record, not a quick answer.**
- **Prediction, written now:** at the verdict, the consensus surprise explains the fade no better than v32's naive measure, and GC fails.

## One recorder. No back-fill. No change after the first record.
