# silver15 — project state and handover

**Status: closed 2026-08-11. Eleven strategy families tested, eleven rejected. No
live strategy. The tooling is sound, reusable, and the conclusions are
recorded with the evidence that produced them.**

Read `FINDINGS.md` first, then the seven pre-registrations in order.

---

## The one-line conclusion

On retail-accessible data and retail execution, nothing tested here clears its
own detectability bar. The *prediction* families had **no gross signal
before costs were charged at all** — including v7, where cost was finally
negligible and the gross Sharpe was still +0.11. The *risk-premium* families
had a real premium already competed below the relevant hurdle.

That is not bad luck across eleven attempts. It is what an efficient market
looks like from a retail vantage point, and it took eleven pre-registered
tests to say it with evidence rather than as an opinion.

## The arithmetic that governs everything

```
required annual Sharpe = k_sigma / sqrt(years)      = 0.44 at 2 sigma on 20.4 years
```

Independent of instrument count — more instruments raise both the total sample
and the trades per year, and they cancel. **Only more history moves it.** That
is why 28 instruments never rescued anything, and why 80 would not have.

Cost drag adds on top and scales as `sqrt(trades per year)`. For residual
mean-reversion that produced an irreducible floor:

```
required(H) = C/(2 x 0.75 x sqrt(H)) + k*sqrt(H)     floor = 4.73pp
```

against a measured effect of 3–4pp. Closed by arithmetic, not by evidence.

**The one family where this framework inverted** was crypto cash-and-carry:
the fee is a one-off four fills amortised over the hold, so it falls as
`1/hold` instead of rising as `sqrt(trades)`. Patience was rewarded there and
punished everywhere else.

## The eleven families

| | strategy | verdict |
|---|---|---|
| — | silver_mr as configured | cost model swamped barriers; unusable |
| — | hedged 15m silver/gold | signal real (+3.32 sd) but ~1/3 the size needed |
| v1 | multi-day silver/gold residual | rejected; also shown unpowerable |
| v2 | cross-metal residual basket | rejected, all 9 pairs negative |
| v3 | slow directional momentum, 28 instruments | rejected (after a bug-driven false PASS) |
| v4 | cross-sectional momentum | rejected, gross negative before cost |
| v5 | CFTC positioning, 6 markets, 38 years | rejected, all six markets negative |
| v6 | FX carry vs OANDA financing markup | rejected: gross −0.23 Sharpe, 37.5% drawdown |
| — | small-cap / low-float microstructure | closed on cost, **without buying data** |
| — | crypto perpetual funding | closed **below cash**: +1.46% vs T-bill 3.66% |
| v7 | 12-month time-series momentum | rejected: Sharpe +0.09, and 2008 is 225% of it |

The two unnumbered entries above v7 were closed by budget alone, before any
test was written — which is the framework working as intended.

## What each rejection actually taught

- **v3/v4** — the gross signal in price history is ~zero *before* cost. No
  filter, barrier, horizon or execution improvement can help, because there is
  nothing being eaten.
- **v5** — the same is true of positioning, across 38 years and six markets,
  at the lowest bar and largest effective sample the project ever had.
- **v6** — *a power budget bounds what a test can RESOLVE; it cannot tell you
  the effect is there.* The budget measured OANDA's financing markup honestly
  and was simply **silent** on the spot move, which decided the outcome. This
  is the single most transferable lesson in the project.
- **small caps** — the inefficiency really is larger (in-play volatility 17%
  against a 7.2% average, exactly as predicted) and the spreads widen right
  alongside it. Required edge 0.45–1.16 vol units per trade, 16–40× anything
  measured here. **Uniquely, the bar term is 0.04 of that: more data cannot
  help.** It is cost, not sample.
- **crypto funding** — a premium can be real, positive, and still not worth
  having. +1.46% net against cash at 3.66%.
- **v7** — cost was finally negligible (0.005 Sharpe against a 0.44 bar) and
  it made no difference: gross Sharpe +0.11. The whole 19-year result is
  2008; excluding it the strategy is negative. Skew came in POSITIVE (+0.35)
  as trend following should, so the implementation was sound and the effect
  was simply absent.

## Bugs found, and the pattern that matters

Roughly two dozen, across the data layer, the engines, the test harnesses and
the reporting. Almost none raised an exception; nearly all produced
plausible-looking output.

**The dominant failure mode, seen FIVE separate times, is a gate that cannot
fire:**

1. `cot.convertRootToCOTCode("Auto")` with `ignore_invalid_symbol=true` —
   returned byte-identical series for gold and silver, silently.
2. The v6 look-ahead probe — planted its leak on a *persistent* carry surface,
   so no lag could be shown to destroy anything. It returned +0.01857 unlagged
   against +0.01882 lagged and would have certified a completely broken lag.
3. The small-cap validation control — counted only controls that returned data
   *and* were too wide, so when every control returned **no** data it passed
   by default, having validated nothing.
4. A synthetic control in `funding_budget.py` that literally ended in
   `or True`.
5. v7's look-ahead probe, run on strongly trending data where a planted edge
   swamps the leak — 54x inflation on a driftless path, 1.1x on a strong
   trend. A leak must be probed where the honest answer is ZERO.

Each was written by someone who had just finished warning about the previous
one. **A gate that has never been observed to fail has not been tested.**

The second pattern, from the earlier work: **every rejection was robust to a
bug that flattered it; the one PASS was entirely a bug** (v3's Sharpe +1.51,
which was barrier snapping). Optimistic errors survive review because the
result looks like success.

Third: **a criterion can pass and still be wrong.** v7's concentration gate
measured share of gross POSITIVE P&L; 2008 scored 17.8% and passed while being
225% of the entire net result. Measure concentration against NET P&L or by
leave-one-period-out. The criterion was recorded as passed rather than
retroactively tightened — changing a criterion after seeing the result is the
same offence in either direction.

Fourth: **failed estimates are not measurements.** 41% of in-play spread
estimates came back clamped to exactly zero, and the first version fed them
into a median as though those stocks traded for free. That reported 0.45 when
the honest answer was a range of 0.45–1.16.

Fifth: **a wrong denominator is worse than none.** `funding_budget.py` v1.0
divided net funding by the volatility of the funding stream and printed a
Sharpe of +8.48. v1.1 prints no Sharpe at all and benchmarks against cash.

## Tooling (all verified by synthetic controls)

| file | purpose |
|---|---|
| `audit.py` | **run first.** 8 synthetic controls per engine, known answers |
| `power_budget.py` | can a test resolve anything? Run BEFORE hypothesising |
| `fast_signal_budget.py` | signal-speed vs cost trade-off; finds the floor |
| `directional_budget.py` | same for single-instrument families |
| `xsec_budget.py` | cross-sectional: rank persistence, turnover, breadth |
| `cot_budget.py` | positioning: release timing, transform choice, n_eff |
| `carry_budget.py` | decomposes broker financing into carry and markup |
| `smallcap_budget.py` | Abdi–Ranaldo spreads from daily H/L/C, in-play filter |
| `funding_budget.py` | published perpetual funding vs fees vs cash |
| `tsmom_budget.py` | 12-month momentum: flips, cost drag, effective breadth |
| `screen_universe.py` | ranks pairs on cost and sample. Computes NO returns |
| `oanda_intraday.py` | data layer: pull, `--sides` spreads, `--audit` provenance |
| `fetch_rates.py` | FRED rate history + provenance cross-check vs OANDA |
| `diagnostics.py` | null test, cost sensitivity, horizon study |

Every budget file computes **no returns**. Several say so in the banner and
were grepped to confirm it.

Data: 28 instruments H4 2006–2026 (OANDA mid, **100% exact OHLC parity** with
a TradingView export in `parity/`), six CFTC markets 1986–2026, FRED OECD
rates for eight currencies, Kraken funding history.

## The method, if nothing else survives

1. **Measure costs, never assume them.** As a fraction of price, not dollars.
2. **Power budget before hypothesis.** If the test cannot resolve the effect,
   do not run it — a null teaches nothing and a pass is noise.
3. **Know what the budget is silent about.** It bounds resolution; it does not
   establish existence. Write down what it cannot see, before the run.
4. **Pre-register, then one run.** No sweeps, no sign flips, no retuning.
5. **Null test always:** real vs reversed vs randomised side.
6. **Synthetic controls on every engine** — and *prove each control can fail*.
7. **Non-overlapping trades**, checked against actual signal decorrelation.
8. **Verify provenance from bytes, not filenames.** Six failures here.
9. **Distrust passes far more than failures.**

## What is left, honestly

Not another signal. Three things survive the analysis:

- **Discretionary skill.** The small-cap budget left a real gap: 0.45 vol units
  per trade is implausible for a written-down rule but not for a trader
  selecting a few setups a day. That is outside what backtesting can validate.
  The honest route is small live size and a journal, not more Python.
- **Infrastructure.** Cross-exchange arbitrage, market making, latency. Real,
  and not available to a retail account.
- **Accepting market risk.** Equity beta has paid ~0.4–0.5 Sharpe for a
  century with an undisputed mechanism. Eleven strategies failed to beat it.

Combining signals does not help: a filter keeping half the trades must make
each survivor 41% better merely to break even, and 14 combinations at 2σ give
a >50% chance of a spurious pass.

## If picking this up again

Run `python audit.py` and every `*_budget.py --self-test` first. They are the
part of this project worth trusting, and they will tell you within a minute
whether the environment still reproduces. Everything else is downstream of
whether those pass.
