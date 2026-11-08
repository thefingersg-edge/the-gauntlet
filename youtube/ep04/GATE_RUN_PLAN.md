# Episodes 4/5 — framing and the gate run

```
WRITTEN: 2026-11-02, after all six arms were generated and before any
         gate was run.
```

## The framing, corrected

The Gauntlet is about finding an edge. These episodes are an honest deep
review of Claude building a trading strategy -- positive or negative -- and
every strategy goes through the same gates as everything else on this
channel.

That is not the framing some of these files drifted toward. Earlier notes
treated the episodes as a debunking of the "I asked an AI for a trading
strategy" genre, with the genre's behaviour as the thesis. **It is not the
thesis. It is the reason the question is interesting.** The thesis is the
same one as every other episode: here is a candidate edge, here is the
Gauntlet, here is what survived.

What this changes in practice:

- **No arm is exempt from a gate because its result is interesting.**
  Arm F produced the only strategy with real backtests behind it. It gets
  the same seven gates as a chart pattern from episode 1.
- **Arm F's own figures are not evidence.** Its Sharpe of 0.67 is its
  measurement, on its own 2018-2026 split, with its own cost model. Useful
  as a claim to test. It is not a gate result, and the episode must not
  present it as one.
- **A pass is reported as a pass.** If something clears all seven, the
  episode says so, and the headline changes accordingly. That was
  pre-committed in section 1 of the preregistration and it still holds.

## Arm F faces all seven gates, including breadth

Arm F trades three instruments: spx500usd, nas100usd, de30eur. Gate 2 asks
for the same sign of edge in at least 14 of 21 markets. It will fail.

**That failure is real, and it is not the Arm C situation.** The two look
alike and are not:

| | Arm C | Arm F |
|---|---|---|
| Why it is narrow | **We do not hold the data.** 15-minute bars exist for 11 of 21 markets, so 14 is unreachable at any quality. | **It chose to be.** Daily bars exist for all 21. It tested the dip-buy on the other 18 and rejected them. |
| Verdict | Gate removed, number reported instead | **Gate applied. It fails.** |

A gate removed because the data makes it unsatisfiable is a correction. A
gate removed because the strategy would fail it is a goalpost. Arm F could
have been broad and is not, and the generator said so itself:

> "These rules are a single edge, buying dips, in three stock indices that
> move together. Under CFD financing, nothing else in your 21 markets held
> up across both periods."

> "all three are equity indices, and 54% of entries happen on the same day
> as another."

So a breadth failure is not us being harsh. It is the measurement agreeing
with the strategy's own author about what the strategy is: one edge, three
correlated instruments. That is worth less than a broad edge and more than
nothing, and the episode can say exactly that.

## What the gates measure that Arm F's own backtest does not

Worth being explicit, because the two will produce different numbers and
viewers will ask why.

| Gate | What it adds beyond what Arm F already did |
|---|---|
| 1 Sign consistency | Our three eras (E1 to 2012-03, E2 to 2019-06, E3 to 2026-08), not its single 2005-17 / 2018-26 split. An edge can survive one split and fail three. |
| 2 Breadth | It tested the other 18 markets and rejected them. The gate records how many agreed in sign, which is a number, not a yes/no. |
| 3 Effect size | Per trade after costs, against our cost model, not its 1.5x-spread assumption. |
| 4 Sample | ~1,000 trades in its round-1 version, ~700 in round 2. Comfortably clear. |
| 5 Robustness | Half-step on every parameter. It tested "nearby settings" informally; this is systematic, and under the hypothesis-defining rule Part B's 16:00/09:00 times are held in the secondary run. |
| 6 Matched control | **The one it never did.** Its benchmark is zero, not days matched on era, prior return and volatility. A dip-buy above the 200-day average may be measuring "indices rise" rather than "dips bounce". |
| 7 Daily risk | It marked to market daily already, so this should be clean -- the first arm for which that is true. |

Gate 6 is the one to watch. It is the gate that killed most of episodes 1
to 3, and a long-only strategy in three rising indices is exactly the shape
that a matched control is built to deflate.

## The run

Six strategies, run on our own files, nothing taken on trust:

```
ARM A  Donchian 55/20 breakout + EMA50/200 filter, all 21, daily
ARM B  Path-continuity: 60-day trend, ID <= -0.10 filter, 20-bar hold, all 21
ARM C  Opening-range breakout, nas100usd + de30eur, 15-min -- ARM C GATE SET
ARM D  v3: multi-horizon trend (18 markets) + index mean reversion sleeve
ARM E  Twin Sleeve: trend on 21 + RSI2 index mean reversion
ARM F  Dip-buy (RSI2<20 above SMA200, limit entry) + overnight hold
```

Order of work:

1. **Gate engine first, one strategy to validate it.** Arm F, because it
   is the only one with an independent set of numbers to check against. If
   our engine reproduces its trade count and rough return on the same
   split, the engine is trustworthy for the other five. If it does not, we
   find out why before anything else is run.
2. Then the remaining five, same engine, no per-arm special-casing.
3. Arm C last, since it needs hourly bars and its own eight-gate set.
4. Every arm reported as "cleared N of 7", never as pass/fail alone.

### Two things fixed before the engine is written

- **Cost model.** The arms assume different costs (Arm B states a
  per-market table, Arm F assumes 1.5x index spreads plus 2.5% financing,
  Arm E has its own bp table). The gates use **one** cost model applied to
  all six, fixed before any run, and each arm's own assumption is reported
  beside it. Otherwise we are comparing six strategies and six cost
  models.
- **Implementation ambiguities get logged, not resolved quietly.** Arm A's
  trailing stop says "every bar after the entry bar, including the entry
  bar's own close", which contradicts itself. Every such choice is written
  down with the decision taken, and the episode shows the list.
