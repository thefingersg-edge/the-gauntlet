# What changed in Unger's DAX system after 2016, how a professional would have handled it, and what we do next

```
STATUS:   POST-HOC and EXPLORATORY. Nothing here is a test result: every number was found by looking after UNGER2.
          A lead below only counts if it is pre-registered and confirmed on data we haven't looked at.
DATA:     OANDA DE30 5m (data/unger2/de30_5m.npz), UNGER2 A trade list; 2026-10-12
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## 1. What died: the "context", not the core idea
Measures: every day's opening-range breakout (a 5m close beyond the 08:00–09:00 range ± 1×range during 09:00–10:00 Berlin), entry at the next open, held to 22:00, gross.

| | 2006 → Jun 2016 | Jun 2016 → 2026 |
|---|---|---|
| **all breakouts, no filters, no stop** (the bare core) | +12.0 bp, t 2.4 (751) | **+8.1 bp, t 2.7 (868)** |
| after an indecisive day (Dfactor < 0.5), **his filter** | **+20.8 bp, t 3.0** | +4.1 bp, t 1.1 |
| after a decisive day (Dfactor ≥ 0.5), the days he skipped | −1.7 bp | **+13.3 bp, t 2.8** |
| Fridays (he skipped them) | −3.2 bp | **+13.6 bp, t 2.0** |

- **The bare core held up.** Breakouts of the opening range kept following through after 2016, at about +8 bp gross, or about +6.5 bp after the ~1.4 bp spread.
- **Both context filters flipped sign.** The days the filters let in became the weak ones, and the days they removed became the strong ones. The stop at the range edge cut further.
- **This matches what UNGER2's harness found:** the published system was −0.8 bp after publication, but "no Dfactor filter" was +2.9 bp and "Fridays included" was +1.3 bp.
- **The most likely story is that the filters were fitted to 2006–2016.** They were real in that sample, but they were a description of the past rather than a property of the market. Filters tuned to one sample are the first thing to break. The simple idea was what lasted.
- **Market structure also moved:**
  - **Volatility:** 2017 had the smallest opening ranges of the whole series (median 21.9 bp) and few breakouts (25% of days).
  - **Trading hours:** from late 2018, OANDA's feed shows DAX trading from about 01:15 Berlin. Before that, the 08:00–09:00 hour *was* the open; now it is the middle of a session that has already digested the overnight news. This did not cause the 2016 break, but it changed what the "opening range" means.

## 2. How a professional would have caught it, and roughly when Unger would have acted
- His stated process is to monitor live systems, retire broken ones rather than patch them, and rotate monthly. Standard monitoring rules, applied to the published system from its publication date, would have fired here:

| kill rule | fires on | loss by then (bp of notional, summed) |
|---|---|---|
| rolling 30-trade mean < 5th pct of the backtest | **Feb 2017** | −126 |
| rolling 50-trade mean < 5th pct of the backtest | Jun 2017 | −157 |
| drawdown > the backtest's worst drawdown | Jul 2017 | −191 |
| (kept running to today) | — | **−331** |

- **So a disciplined operator would have retired it within 8–13 months, at about a third to a half of the eventual loss.** That is probably where his real edge sits: in the **process** (incubate, deploy small, monitor, retire, replace) more than in any single rule.
- **What he would have built next:** the evidence above points to re-running his "probe" on the newer data. That would show the bare breakout still works and the old filters are inverted. The new system would be the core plus *new* context fitted on recent years, which will itself decay in time. Every published system therefore has a shelf life, and **selling or publishing a system is consistent with it already being near the end of its life.**

## 3. Thinking like a professional: where this leaves fastbot
**What about 170 pre-registered tests have taught us:**
1. **Short-interval signals on CFDs almost never survive costs.** Spreads plus financing of the policy rate + 2.5% kill most ideas that hold for days. The same idea on futures sometimes survives: gold hourly made +2.7 bp on futures and ~0 on CFDs.
2. **What does pay is risk premia, not prediction:** VIX carry (Sharpe ~0.4), oil carry (~0.5), and maybe IMB2's thin closing-imbalance flow. These are small, real and documented.
3. **Simple cores outlast fitted context.** The DAX example above is the clearest case.
4. **Edges decay.** The work is a pipeline, not a discovery.

**What a professional desk would do next** (each pre-registered and frozen before any data, as always):

| # | step | why |
|---|---|---|
| 1 | **ORBCORE1:** the bare opening-range core (no filters; no stop or a wide stop), tested on markets and periods we have NOT used: EU50, UK100 and US index cash opens, plus a forward record on DAX | turns today's post-hoc lead into a fair test; DAX itself is now "seen" |
| 2 | **LIFECYCLE1:** apply one fixed kill rule (e.g. the rolling 30-trade mean below the backtest's 5th percentile) to every system in our registry that has a trade list | measures whether "retire broken systems" adds value: the process edge, not a signal |
| 3 | **FUTPORT1:** time-series trend + carry across 20–30 liquid futures on daily bars (Databento, cost-checked first) | the best-documented premia, tested properly; our TSMOM failures were on 5 CFDs paying financing |
| 4 | **Incubator:** one page that tracks every forward record (IMB2, oil carry, NAS noise-band, NQ) against its backtest band, with kill rules built in | the operating layer we don't have yet; it is how money would ever be allowed |

- **Honest expectation:** a realistic end state is a diversified, futures-based book of modest premia and simple cores at a portfolio Sharpe of perhaps 0.5–0.8, run with strict kill rules. It is not a short-interval bot printing money. The series has already shown why the 99% don't get there: they buy fitted systems at the end of their shelf life.
