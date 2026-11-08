# Which instrument can carry a 1–5 minute bot at all

Run 2026-08-17. Measured before any signal was hypothesised, per the silver15
rule that a power budget precedes the hypothesis.

**No returns are computed anywhere in this analysis.** Everything below comes
from OANDA bid/ask quotes and realised volatility. Nothing here can rank an
instrument by how well it backtested, because nothing here knows.

---

## The question, reduced to one number

A round trip hands the broker the spread. The move available to capture over a
hold of `H` minutes scales as `sigma_1min * sqrt(H)`. So the whole feasibility
question is:

```
cost/vol(H) = spread_rel / (sigma_1min * sqrt(H))
```

`screen_universe.py` already fixed this project's thresholds: **≤ 0.15 is
comfortable, ≤ 0.35 is reachable, above that the cost swamps the move.**
Rearranged, that gives the number to report:

```
H_min = (spread_rel / (threshold * sigma_1min))^2      minutes
```

the shortest hold at which an instrument is not already dominated by the
spread. If `H_min` sits far above 5 minutes, a 1–5m bot on that instrument is
closed by arithmetic and no filter, parameter or regime argument reopens it.

**Financing does not appear**, and that is a real point in favour of short
intervals: OANDA charges it only past the daily rollover, so a bot that is flat
overnight pays none. It is earned only if the hold stays inside a session —
which is itself a constraint on `H`, handled in §3.

Data: 33 instruments, OANDA mid/bid/ask, 4,614 M15 bars, **2026-06-01 →
2026-08-07**. Spread is the median across quoted bars; volatility is a MAD-based
robust sd on **consecutive bars only**, so session and weekend gaps are never
counted as tradeable movement.

---

## 1. The headline: FX is closed, index CFDs are open

| instrument | spread | vol/min | cost/vol @1m | @5m | H_min (0.15) |
|---|---|---|---|---|---|
| **NAS100** | 0.93bp | 2.79bp | 0.33 | **0.15** | **5m** |
| **SPX500** | 0.66bp | 1.53bp | 0.44 | 0.19 | 8m |
| **US30** | 0.66bp | 1.35bp | 0.49 | 0.22 | 11m |
| **XAUUSD** | 1.50bp | 2.88bp | 0.52 | 0.23 | 12m |
| DAX | 1.22bp | 2.08bp | 0.59 | 0.26 | 15m |
| … | | | | | |
| EURUSD | 1.40bp | 0.57bp | 2.44 | 1.09 | **265m** |
| USDCAD | 1.28bp | 0.52bp | 2.48 | 1.11 | 274m |
| EURGBP | 1.62bp | 0.36bp | 4.52 | 2.02 | **909m** |

**Across all 33 instruments, exactly one clears the comfort bar at a 5-minute
hold, and eight reach the ceiling.**

### The result that inverts the obvious choice

FX is the family a retail trader reaches for at short intervals, because the
pip spread looks tiny. **As a fraction of price it is not even tighter.**
EURUSD quotes 1.40bp against SPX500's 0.66bp and NAS100's 0.93bp; the tightest
FX pair in the set (USDCAD, 1.28bp) is still twice SPX500. And FX moves at a
fifth the speed — 0.57bp per minute on EURUSD against 2.79bp on NAS100.

Both terms point the same way, so the ratio is not close:

```
EURUSD   needs  265 minutes    (4.4 hours)
NAS100   needs    5 minutes
```

**A 1–5m bot on any FX pair is closed by arithmetic.** Not unproven, not
awaiting a better signal — the spread is 1.1× the entire 5-minute move on
EURUSD, and 2.0× on EURGBP. This is the same structure that killed silver15 v6
and the residual mean-reversion family, arriving from a different direction.

---

## 2. What the frequency table costs

Required gross annualised Sharpe from **cost drag alone**, at the 24-hour
blended figures:

| instrument | 1/day | 4/day | 12/day | 48/day |
|---|---|---|---|---|
| NAS100 | 0.2 | 0.6 | 1.7 | 6.6 |
| SPX500 | 0.2 | 0.7 | 2.2 | 8.7 |
| XAUUSD | 0.2 | 0.9 | 2.6 | 10.5 |
| EURUSD | 1.1 | 4.2 | 12.5 | 49.9 |

For scale: a Sharpe of 1.0 is a good systematic strategy, 2.0 is exceptional.
**Trading frequency, not instrument choice, is the dominant term** — NAS100 at
48 round trips a day is harder than EURUSD at one.

---

## 3. The session cut, which is the decisive finding

The 24-hour median blends two different markets. For an index CFD the cash
session and the overnight book have opposite properties, and **both terms move
the same way**, so the effect on the ratio compounds.

**NAS100 by UTC hour:**

| UTC | spread | p90 spread | vol/min | cost/vol @1m | @5m |
|---|---|---|---|---|---|
| 03:00 | 0.95bp | 1.18bp | 2.48bp | 0.38 | 0.17 |
| 10:00 | 0.97bp | 1.18bp | 1.85bp | 0.52 | 0.23 |
| 13:00 | 0.81bp | 1.19bp | 5.62bp | 0.14 | 0.06 |
| **14:00** | **0.44bp** | **0.61bp** | **6.33bp** | **0.07** | **0.03** |
| 15:00 | 0.39bp | 0.54bp | 5.21bp | 0.08 | 0.03 |
| 17:00 | 0.37bp | 0.47bp | 3.58bp | 0.10 | 0.05 |
| 19:00 | 0.37bp | 0.46bp | 4.22bp | 0.09 | 0.04 |
| 22:00 | 1.11bp | 1.35bp | 2.08bp | 0.53 | 0.24 |

Between 03:00 and 14:00 UTC the spread **halves** and volatility **rises 2.6×**.
The ratio improves **5.4×**. At 14:00 UTC, NAS100 clears the comfort threshold
at a **one-minute** hold with better than 2× margin — the 24-hour blend said it
barely cleared at five.

The p90 column matters as much as the median: in-session, NAS100's 90th
percentile spread is 0.61bp against a 0.44bp median. **The spread does not blow
out inside the session**, which is not true overnight (1.20bp p90 at 03:00).

### Cost drag restricted to the comfortable hours

| instrument | window UTC | h/day | ann vol | 1/day | 4/day | 12/day | 48/day |
|---|---|---|---|---|---|---|---|
| **NAS100** | 00-01, **12-20** | 9 | 14.5% | **0.07** | **0.27** | **0.82** | 3.28 |
| SPX500 | 13-20 | 7 | 7.8% | 0.17 | 0.69 | 2.07 | 8.27 |
| US30 | 13-20 | 7 | 6.7% | 0.18 | 0.72 | 2.16 | 8.63 |
| XAUUSD | 12-15 | 3 | 10.1% | 0.38 | 1.51 | 4.52 | 18.07 |
| DAX | 07-08 | 1 | 4.7% | 0.63 | 2.53 | 7.60 | 30.41 |
| EURUSD | **none** | 0 | — | — | — | — | — |

**NAS100 traded 12:00–20:00 UTC at up to 12 round trips a day has a cost drag
of 0.82 Sharpe, and at 4 round trips a day, 0.27.** That is the first number in
this project's history where cost is a detail rather than the whole problem.

---

## 4. What this licenses, and what it does not

### The design this points to

```
instrument   NAS100USD  (OANDA)
bar          1m or 5m
hours        12:00-20:00 UTC only
round trips  <= 12/day, target ~4/day
overnight    flat, so financing is zero by construction
```

The important reframing: **a 1–5 minute bar does not require a 1–5 minute
hold.** The bar is entry-timing resolution; the hold is a separate decision and
it is the hold that pays the cost. A 1m bar with a 90-minute hold at 4 round
trips a day is a "short interval bot" under any reasonable reading of the goal,
and it is affordable. A 1m bar with a 5-minute hold at 48 round trips a day is
not.

### What has NOT been established

This is a budget. Per silver15's v6 lesson — *a power budget bounds what a test
can resolve; it cannot tell you the effect is there* — here is what it is
silent about:

1. **Whether any signal exists on NAS100 at these horizons.** Nothing above
   touches that, and the prior on it is bad: `DESIGN_BRIEF.md` found 0 of 14
   price conditions sign-consistent across eras at intraday-to-8-day horizons,
   and 0 of 25 standard-setting indicators. **The budget has moved the cost
   obstacle out of the way; it has not produced evidence of an edge, and the
   edge is where every previous attempt died.**
2. **Quoted spread is not execution cost.** OANDA index CFDs are dealer-priced.
   Slippage, requotes and rejections at 1m granularity are not in these numbers
   and can only be measured live. Treat 0.44bp as a floor, not an estimate.
3. **Nine and a half weeks, one regime.** 2026-06 to 2026-08 contains no stress
   event. Spreads widen when it matters most, and this sample cannot say by how
   much. The p90 column is reassuring within the sample and says nothing about
   outside it.
4. **The 15m → 1m volatility scaling is assumed, not measured.** `sqrt`-of-time
   from M15 is used because measured 1m vol is inflated by bid-ask bounce, which
   is not capturable movement — so this is the conservative direction. It still
   needs verifying against real M1 candles.
5. **The detectability bar depends on M1 history depth, which is unmeasured.**
   The 2σ hurdle is `2/sqrt(years)`. If OANDA serves only a year or two of M1,
   that term alone is 1.4–2.0 Sharpe and dominates everything in §3.

Point 5 is the one most likely to close this. **It should be settled before any
strategy code is written**, and it needs an API token.

---

## 5. Next, in order

1. **Probe OANDA's M1 history depth** (`oanda_intraday.py --probe --granularity
   M1`). If it is under ~3 years the detectability bar exceeds the cost drag by
   several times and the project changes shape. Needs the token.
2. **Pull NAS100 M1 bid/ask** for the full available depth and re-run both
   scripts natively, replacing the sqrt-scaling assumption with measurement.
3. **Verify the session profile holds out of the current sample** — re-run the
   hourly cut on each earlier year separately. If the 12:00–20:00 window is not
   stable across years, it was fitted.
4. **Only then** pre-register a signal family, a held-out period, and pass/fail
   criteria — with the round-trip budget of ≤12/day treated as a hard
   constraint on the strategy, not an outcome of it.

## Tooling

| file | purpose | self-test |
|---|---|---|
| `interval_budget.py` | cost/vol and `H_min` across the universe | 15 checks, each gate shown failing |
| `session_profile.py` | the same by UTC hour, plus session-restricted drag | recovers a planted two-regime day to 15%; a flat day shows no structure |

Both compute **no returns**. Both self-tests plant a known answer and confirm
the gate fires on a case built to fail it, per the silver15 finding that a gate
never observed to fail has not been tested.

```
python interval_budget.py --self-test && python interval_budget.py --data ../data
python session_profile.py  --self-test && python session_profile.py  --data ../data
```
