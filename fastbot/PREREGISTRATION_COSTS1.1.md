# PREREGISTRATION COSTS1.1: amendment fixing the route-1 details (Databento)

Frozen 2026-10-03, **before the sample was drawn and before any quote was requested.** It only makes route 1 of COSTS1 precise; the question and the decision rule are unchanged.

I am not a financial adviser. This is a measurement, not a recommendation.

## Sample (`singlestock/costs1_sample.py`, run once, output `data/costs1/sample.csv`)
- Frame: PEAD3 CONFIRMED signals (frozen PEAD1 engine + PEAD3 SUE ≥ 70th-percentile rule), bands M and S, entry date 2018-05-01 to 2026-06-30. US half-days (3 Jul, 24 Dec, day after Thanksgiving) excluded at entry or exit.
- 200 M + 200 S, random with seed 20261003. The rest of each band is an ordered reserve.
- A sampled row with no usable quotes (symbol not found on that date, outside the dataset's history, empty window) is replaced by the next reserve row of the same band, strictly in order. The number of replacements is reported.

## Data (`scripts/databento_costs1.py`, run on Dave's Mac, key in `~/.databento_key`)
- Venue = the stock's listing exchange: XNAS.ITCH (Nasdaq), XNYS.PILLAR (NYSE), XASE.PILLAR (NYSE American). Primary-venue quotes, not the consolidated NBBO (a stated limitation: primary BBO is the same as or wider than NBBO, so costs are biased up, not down).
- For the entry day and the exit day of each row: `bbo-1s` 09:30:00–09:31:00 and 15:59:00–16:00:00 ET; `statistics` for the day (official closing price).
- `cost` mode prints the price from Databento's free cost endpoint and downloads nothing. `pull` needs `--go`.

## Measures (per row, as fractions of price)
1. **Open quoted cost (round trip):** median quoted spread / mid over 09:30:00–09:31:00 on the entry day (= half-spread in, half-spread out).
2. **Closing-auction cost (round trip):** |official close − last midpoint before 16:00:00| / that midpoint, on the entry day plus the same on the exit day.
3. **Ratio to EDGE:** each of the above divided by the row's EDGE estimate (60 days before the filing, as in the engine). Rows with no EDGE are kept for 1–2, dropped for 3.

## Decision rule (unchanged)
If the median closing-auction ratio (measure 2 / EDGE) is ≤ 0.50, the auction cost model of PEAD2 and STRAT1 is accepted for the forward portfolio. Otherwise full EDGE stays. Measure 1 is reported alongside. Medians come with a bootstrap 90% interval (2,000 draws, seed 20261003). M and S are also reported separately (descriptive).
