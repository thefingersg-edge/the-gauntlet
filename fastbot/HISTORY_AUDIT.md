# The 21.6 years is not 21.6 years

Run 2026-08-17 on NAS100_USD M5, 1,458,154 bars, OANDA live.

The probe reported 21.6 years and the depth is real — the bars exist. What the
audit establishes is that **the usable history is roughly 13 years, and the
seven years before 2012 are unusable in a way that would have flattered a
backtest rather than broken it.**

---

## 1. Seven years carry no spread data at all

```
2005-2011    ask - bid = 0.00bp on every bar
2012         3.76bp
2026         0.39bp
```

`ask == bid` for 2005 through 2011. OANDA is serving the same series twice.

**This is a missing input, not a zero cost**, and the distinction is the whole
point. A backtest charging the measured per-bar spread — which is the correct
design, and the one this project was heading for — would have traded those
seven years **completely free** and reported a spectacular result on a third of
the sample. It would not have crashed, warned, or looked wrong. It would have
looked like an edge.

This is the silver15 pattern in its purest form: *an absent input that presents
as a favourable measurement*. Five of that project's bugs had this shape. The
tool now reports these years as `UNUSABLE — no spread in feed` and excludes
them, rather than scoring them at 0.0×.

## 2. The early bars are a different, thinner process

| year | bars/day | flat bars | med range |
|---|---|---|---|
| 2005 | 167 | **26.5%** | 5.90bp |
| 2006 | 182 | 23.4% | 4.10bp |
| 2008 | 208 | 10.1% | 10.27bp |
| 2011 | 224 | 3.4% | 6.74bp |
| 2013 | 213 | 5.4% | 3.63bp |
| 2015 | 226 | 0.2% | 5.27bp |
| 2018+ | 224–228 | **0.0–0.1%** | — |

Two independent signals moving together. Bars per day rises 167 → 226, so the
early feed covers ~14 hours a day against ~19 now. And the share of **zero-range
5-minute bars** falls monotonically from 26.5% to essentially zero.

A quarter of 2005's bars have `high == low`. For a strategy whose entry is a
5-minute bar, a bar that never moved is not an observation. Whatever process
generated 2005–2011 is not the process generating 2018–2026, and a rule fitted
across both is fitted to the seam.

## 3. The spread the budget assumed is a 2019-onwards number

Measured in-session (13:00–20:00 UTC), against the 0.44bp `COST_BUDGET.md` used:

| era | in-session spread | vs budget |
|---|---|---|
| 2012–2013 | 3.32–3.76bp | **7.6–8.5×** |
| 2014–2017 | 1.39–1.64bp | 3.2–3.7× |
| 2018 | 0.91bp | 2.1× |
| **2019–2026** | **0.35–0.69bp** | **0.8–1.6×** |

Mean in-session spread 2019–2026 is **0.444bp** — the budget figure is right,
but only for that window. Applying it to 2014 would understate cost by 3.4×,
and cost is the entire reason NAS100 was selected over everything else.

---

## 4. What this does to the hurdle

The detectability bar is `2/sqrt(years)`, and the year count just fell.

| sample | years | detect bar | + cost @4/day | + cost @12/day |
|---|---|---|---|---|
| *as probed* | *21.6* | *0.43* | *0.70* | *1.25* |
| spread ≤2× budget | 8 | 0.71 | **0.98** | 1.53 |
| clean mid + real spread | 13 | 0.55 | **0.82** | 1.37 |

**The required gross Sharpe at 4 round trips a day rises from 0.70 to
0.82–0.98.** Still inside what a good systematic strategy produces, so this does
not close the project — but the comfortable margin the probe appeared to give
was not real, and it is better to know now than after fitting.

## 5. The sample decision, and a design point that falls out of it

Three windows, by what they can support:

```
2005-2011   UNUSABLE      no spread data; thin, heavily flat bars
2012-2013   marginal      real spread but 8x today's; clean-ish bars
2014-2026   USABLE        flat% <1%, 224+ bars/day, real spread throughout
```

**Proposal: use 2014–2026 and charge the spread that applied at the time, per
bar.** Thirteen years, detect bar 0.55.

Do *not* truncate to 2019+ merely because it is cheap. The expensive years are
informative precisely because they are expensive — and they suggest a rule that
comes out of the budget rather than out of fitting:

> **Trade only when the measured spread clears the cost/vol threshold.**
> Not a fitted parameter — the 0.15 comfort bar was set in `screen_universe.py`
> before any of this. In 2014–2017 such a rule trades rarely or not at all; from
> 2019 it trades freely. That is the correct behaviour, and it makes all
> thirteen years usable rather than forcing a choice between sample size and
> cost realism.

It also transfers directly to live trading, where the spread is observable
before every entry.

### The split, to be fixed now

```
FIT       2014-01-01 -> 2020-12-31      7 years
HELD OUT  2021-01-01 -> 2026-08-17      5.6 years, detect bar 0.85
```

Not to be opened until a pre-registration names the criteria. `pineport`'s
verdict line — *"out-of-sample evidence exists: ❌ none left — fitted on
everything"* — is what this avoids.

---

## 6. A bug in the audit, found by running it

The first version flagged `COARSE-GRID` on **every year including 2026**. That
is a gate firing on everything, which is exactly as useless as one firing on
nothing.

The cause was mine. NAS100 quotes to one decimal place, so `round(price*100) %
100` can only ever take 10 values. The synthetic control used a continuous
random price where it takes 100, so the control could not distinguish *coarse
because interpolated* from *coarse because that is the tick size*.

Fixed by making every test **relative to the instrument's own recent
behaviour** rather than to an absolute constant: a year is flagged if its price
grid, bar count or flat-bar share departs from the same instrument's baseline.
An absolute threshold cannot know an instrument's tick size; a within-instrument
comparison does not need to.

Worth recording that the false positive was harmless and the *real* finding —
zero spread before 2012 — was sitting in a column printed as `0.00bp / 0.0x`,
i.e. formatted as the best possible score. The noisy gate was obvious; the
dangerous one was silent.
