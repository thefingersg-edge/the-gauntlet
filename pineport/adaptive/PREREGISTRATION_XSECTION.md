# Pre-registration — J1, cross-sectional momentum

Written 2026-09-03, before any cross-sectional return is computed.

## Why this is not another trend variant

I1 fired its kill condition and retired the trend-speed family. J1 is
admitted anyway because it is a **different statistical object**, not a
different slice of the same one:

- Time-series momentum asks "is this market above its own average?" Every
  test in Parts A-I asked that.
- Cross-sectional momentum asks "is this market above *the other markets*?"
  The portfolio is dollar-neutral, the market factor is differenced out, and
  it can pay in regimes where time-series momentum does not.

Nothing in this project has ever ranked one market against another.

## Honest prior — low

The literature does not promise much:

- In 35 commodity futures 2004-2020, a moving-average *trend* factor
  "outperforms the momentum factor by more than nine times in the Sharpe
  ratio", while conventional cross-sectional momentum "delivered
  insignificant results" in the financialised era.
- Equity cross-sectional momentum has declining returns and is crash-prone.

So this is being run to close a genuine gap in coverage, not because we
expect it to work. That expectation is recorded here so that a marginal
result is read against it.

## The binding constraint — N_eff

Measured N_eff for this universe is **4.70-6.01**, not 21. A quintile sort
gives ~4 names a side, drawn from an effective population of about five
independent blocs. That is close to degenerate: the "cross-section" would be
two or three real bets wearing eight names.

Two consequences, fixed in advance:

1. The **primary** specification is NOT a quintile sort. It is a continuous
   rank-weighted portfolio — cross-sectionally z-score the signal each month,
   demean to dollar-neutral, scale to unit gross — which uses all 21 markets
   and does not throw away the middle.
2. The quintile sort is reported as a **secondary** specification only, and a
   disagreement between the two is scored as a failure of robustness, not as
   licence to report the better one.

## Universe and panel

21 markets, daily bars post-R4. Panel truncated at **2026-08-07**, the last
date on which all 21 are live — 10 markets currently end there while 10 run
to 2026-08-28 (GAUNTLET 1.6, stale inputs). The 15 rows after that date are
dropped rather than ranked on a shrinking cross-section.

Cross-sectional ranking requires markets to be comparable, so all signals are
computed on **volatility-normalised** returns, not raw ones. Ranking a gold
CFD against a Bund CFD on raw return would be a volatility sort.

## Signals — three, fixed

Each computed at each month end, on close data only:

    S1  12-1 momentum   sum of log returns over months t-12..t-2, skipping
                        the most recent month (standard, avoids short-term
                        reversal contamination)
    S2  3-month         sum of log returns over months t-3..t-1
    S3  1-month reversal   negative of last month's return

All divided by trailing 63-day realised vol before ranking.

## Rebalance and cost

Monthly, at the first bar of the month, on the previous month-end signal.
Cost 1bp per unit turnover, with 0bp and 3bp as robustness. Positions held
constant within the month (no daily re-derivation — that is the turnover
artefact fixed in `h1_combined.py`).

## Pass criteria — fixed in advance

A signal passes only if ALL of:

1. Sharpe of the rank-weighted portfolio exceeds the noise floor for this
   sample. Post-2005 is 21.6 years; at N_eff 5 that is ~108 market-years,
   SE(Sharpe) ~ 1/sqrt(108) = **0.096**. Require Sharpe >= **0.29** (3 SE),
   set here rather than after seeing the number.
2. Sign consistency across all three eras E1/E2/E3.
3. Beats its destroyed-timing null — signal lagged 750 bars — at the 95th
   percentile of a stationary block bootstrap (mean block 63 bars).
4. Rank-weighted and quintile specifications agree in sign.
5. Survives at 3bp cost.
6. Plateau, not spike: the neighbouring formation windows (11-1, 12-2, 6-1)
   retain the same sign.

## Traps specific to this test

- **Market-identity sort.** This is the `a2` defect (88% of bcousd rows in
  one pooled tercile). Ranking must be *within date, across markets*, never
  on pooled levels. Asserted in code by checking every cross-section has
  mean rank equal to (n+1)/2.
- **Survivorship in the panel.** sugarusd starts 2007-02, xagusd and xauusd
  2006-03. The cross-section is smaller before 2007. Require n >= 12 live
  markets for a date to be ranked; report the date at which the panel
  reaches full width.
- **Shared term.** The vol normalisation divides both the signal and,
  effectively, the return being predicted. Run the mirror check: rank on
  1/vol alone with the return term removed. If that reproduces the result,
  the signal is a low-vol tilt and is withdrawn.
- **Correlated names.** Gold, silver, platinum are one bloc; the four EUR
  and USD crosses are another. Report the realised N_eff of the resulting
  portfolio, and if the top quintile is routinely one bloc, say so.

## Kill condition

If none of S1/S2/S3 clears criterion 1 in the rank-weighted specification,
the cross-sectional family is closed for this universe. It would not be
reopened with a fourth formation window.
