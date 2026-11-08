# PREREGISTRATION v33 — two lenses from the TradingView survey

Frozen 2026-09-25, before any fade was computed for these regressors.
Script: scripts/premarket_levels.py v1.0 (checks this file's sha256).

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. Questions
A. **Level magnets.** Is the 08:45→09:45 release fade heading back to a
   price level the market marked out before 08:30? (Volume profile / VWAP /
   fair-value-gap scripts.)
B. **Rule of 16.** Does a release move that is large against what options
   priced (prior-day VIX/16) fade more than one that is large only in bp?

## 2. Data and sample
v27's trades exactly: six instruments (SPX500, NAS100, US30, DE30, EUR_USD,
XAU_USD), OANDA 15m bid/ask mids in data/v24, events_v2.csv. S1 = CPI or
payrolls, S2 = claims-only, S3 = all other mornings. Dates ≥ 2026-09-18
excluded. Fade = v27's gross_H0 (Gate 0: every matched trade to 1e-6 bp).

## 3. Regressors (all from information available before 08:45)
- Overnight = 15m bars starting 18:00 ET prior day up to and excluding
  08:30 ET. Mornings with < 20 overnight bars are dropped.
- VWAP = Σ typical price × tick volume / Σ tick volume over the overnight.
- POC = busiest 2 bp bin (bins anchored at the 08:45 entry price), each
  bar's volume spread evenly across the bins its range covers; ties → bin
  nearest entry.
- GAP = the 08:15 bar's high (up move) or low (down move).
- D_level = direction × (level / entry − 1) × 1e4; positive when the level
  lies where the fade trades.
- I = last VIX close strictly before the release date × 6.25 bp (VIX/16 %).
  VIX is used for all six instruments.

## 4. Models (OLS, SEs clustered by date)
- A: fade = a + b·D_level + c·|move|, one fit per level. Gated: VWAP, POC.
- B: fade/I = a + b·(|move|/I). Gated.
- GAP is reported only: corr(D_GAP, |move|) = 0.94, MDE 0.49 — the budget
  says it cannot be resolved separately from move size (already tested, v28).
- fade = a + c·I + d·|move| is reported only and is NOT blind: v31 already
  showed VIX level vs bounce at t +1.20.

## 5. Gates (three tests, Bonferroni t ≥ 2.39)
PASS for a lens requires all of:
1. S1: b > 0 and t ≥ 2.39;
2. S2 (claims, independent dates): b > 0 and t ≥ 1.64;
3. S1 excluding 2020–2021: b > 0 and t ≥ 1.64.
S1 alone passing = "S1 ONLY — not a finding". S3 is reported: a magnet that
is as strong on control mornings is a general intraday effect, not a
release effect, and is reported as such.

## 6. Power budget (no fades read; SE scaled from v28's slope SE 0.050)
| lens | SD(x) | corr with |move| | MDE b (80%) | meaningful |
|---|---|---|---|---|
| VWAP | 43.2 bp | 0.77 | 0.20 | 0.10 |
| POC | 47.0 bp | 0.70 | 0.17 | 0.10 |
| GAP | 33.6 bp | 0.94 | 0.49 | 0.10 |
| R16 | 0.276 | — | 0.19 | 0.10 |

**What the budget is silent about / blind to.** No test here can see a
magnet of b ≈ 0.10 (≈2 bp on a median 22 bp distance) — it would need
about four times the sample. A null therefore means "no strong magnet",
never "no magnet". If the whole 3.6 bp fade were magnet-driven, b ≈ 0.16:
POC has ~80% power for that, VWAP ~60%. Tick volume is OANDA's quote
count, not exchange volume; a real-volume POC could differ. The R16
budget is an approximation (outcome scale taken from published SD).

## 7. Descriptive, gating nothing
Take-profit-at-level exit (fill assumed AT the level — optimistic) vs the
fixed 09:45 exit, S1 and S3, gross.

## 8. One run. No sweeps of bin width, window, or level definition.
