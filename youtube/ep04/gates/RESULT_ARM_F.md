# ARM F — gate result

```
RUN:     2026-11-05
ENGINE:  gates/ — validated against Arm F's own published figures to
         within 1-2% on trades, returns, drawdown and end equity.
VERDICT: part A alone  cleared 5 of 7
         full spec     cleared 4 of 7
```

## The headline

**The round-3 "improvement" is worthless under a consistent cost model, and
it costs the arm a gate.**

Arm F's part A (dip-buy) clears five of seven. Adding part B (the overnight
sleeve) — the change it made at round 3, which raised its in-sample Sharpe
from 1.08 to 1.23 — takes it to four of seven. The sleeve breaks gate 3 and
contributes nothing.

| | part A only | full spec (A + B) |
|---|---|---|
| 1 sign consistency | PASS | PASS |
| 2 breadth | FAIL 3/21 | FAIL 3/21 |
| 3 effect size | **PASS** 0.513%/trade | **FAIL** 0.042%/trade |
| 4 sample | PASS 696 | PASS 8,709 |
| 5 robustness | FAIL 72% | FAIL 67% / 78% |
| 6 matched control | PASS +0.439% | PASS +0.439% |
| 7 daily risk | PASS -10.2% | PASS -20.7% vs -21.1% claimed |
| **cleared** | **5 of 7** | **4 of 7** |

## Why part B fails, and it is entirely the cost model

| part B, per trade | |
|---|---|
| gross | **+0.0508%** |
| our cost | **-0.0497%** |
| net | **+0.0011%** |

8,013 trades of almost exactly nothing.

**We agree with it about the gross edge.** Our gross works out at ~14.5% a
year on notional for nas100usd; it reported "about 11-14% a year before
costs in the Nasdaq and DAX in both periods." That is a match, which means
the overnight drift is real and both of us measured it.

**We disagree only about costs.** It assumed 1.5x spreads of 0.015%
(nas100) and 0.010% (de30eur). Our single model charges 0.040% round trip
on both, plus financing. On its numbers the sleeve is worth ~2.5-4% a
year; on ours it is worth 0.4%.

So the entire value of the round-3 improvement rests on a spread
assumption. **This is the clearest demonstration in the whole study of why
the cost model had to be fixed before any arm was run, and why each arm's
own assumption is reported beside ours.** Neither of us is lying; one
number decides the result.

## Why adding it breaks gate 3

Gate 3 asks for 0.2% per trade after costs. Pooling both sleeves:

```
   696 trades at +0.513%   (part A)
 8,013 trades at +0.001%   (part B)
 -----------------------------------
 8,709 trades at +0.042%   -> FAILS
```

That is the literal reading of the gate and it is the right one. A sleeve
whose edge does not clear its own costs is not an improvement, and burying
it in an average is how it would be hidden. Both sleeves are reported
separately so nothing is concealed by the pooling either.

## What it got right, confirmed independently

- **Its drawdown claim is honest.** It said 21.1%. We measure 20.7% at
  daily resolution with open positions marked. Gate 7 passes.
- **Its session boundary claim is correct.** It said the daily bars run
  17:00 New York to 17:00 New York and that it verified this against the
  hourly data on 100% of bars. We rebuilt the check independently
  (`verify_h1.py`) and confirm it: 100% match on high, low and close across
  5,591 nas100usd and 5,490 de30eur sessions.
- **Its backtest reproduces.** 696 trades against its 697; at 4% risk,
  21.8%/yr vs its 20.1%, 19.8% drawdown vs its 20.9%, end equity 248,203
  vs its ~251,700.

## Where our figures differ, and why

| | ours | its |
|---|---|---|
| combined CAGR | 8.3% | 12.6% |
| combined daily max DD | 20.7% | 21.1% |
| end equity | 52,605 | ~132,500 |

The drawdown matches; the return does not. The whole gap is part B earning
~0.4% a year under our costs instead of ~4% under its own, compounded over
twenty years.

## Gate 5, both readings

Under the uniform +/-25% rule fixed on 2026-11-02:

- **Primary** (every parameter perturbed, session hours included): worst is
  the nas100usd entry hour moved from 16:00 to 20:00, leaving 67%.
- **Secondary** (hypothesis-defining session hours held, per the
  GATES_ARM_C.md amendment): worst is rsi_exit 70 -> 52, leaving 78%.

It fails both, so the verdict does not depend on that rule. Both failures
in the secondary reading are on the RSI thresholds — entry 20 -> 25 gives
78%, exit 70 -> 52 gives 72%. The trend filter, ATR period, stop multiple,
limit offset and holding period are all stable at 87-106%. The edge lives
specifically in how deep the dip is and how far the bounce runs.

## Known approximation, declared

Part B's P&L is applied to the daily equity curve on its exit date rather
than marked at the 17:00 close it spans. The position is open across one
daily mark, so the daily-resolution drawdown is very slightly understated.
Fixing it requires an hourly equity curve and would move gate 7 by a
fraction of a point, not across its threshold.
