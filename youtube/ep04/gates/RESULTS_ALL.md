# Episodes 4/5 — the Gauntlet result, all six arms

```
RUN:    2026-11-06
ENGINE: gates/ — one implementation, no per-arm special-casing.
        Validated against ARM F's own published figures to within 1-2% on
        trade count, in- and out-of-sample return, drawdown and end equity.
COSTS:  one model for all six — per-market round-trip spread plus OANDA
        financing at 2.5%/365 per calendar night, both directions.
        *** the spread table still needs Dave's sign-off ***
```

## The scoreboard

| Arm | What it is | Cleared | Trades | Mkts | Net/trade | Gross | Cost | Median hold |
|---|---|---|---|---|---|---|---|---|
| **F** part A | dip-buy, RSI2 < 20 above SMA200, 3 indices | **5 of 7** | 696 | 3 | **+0.513%** | +0.590% | 0.077% | 4 n |
| **F** full | part A + overnight sleeve | **4 of 7** | 8,709 | 3 | +0.042% | +0.094% | 0.052% | — |
| **C** | first-hour -> last-hour, 1h bars, 2 indices | **6 of 8** | 6,110 | 2 | −0.016% | +0.019% | 0.035% | 0 n |
| **D** | v3: multi-horizon trend + index MR | 2 of 7 | 2,835 | 19 | +0.050% | +0.360% | 0.310% | 7 n |
| **B** | path continuity (information discreteness) | 2 of 7 | 4,096 | 21 | −0.053% | +0.232% | 0.285% | 27 n |
| **A** | Donchian 55/20 + EMA 50/200 | 1 of 7 | 1,307 | 21 | −0.078% | +0.324% | 0.403% | 33 n |
| **E** | twin sleeve: EMA trend + RSI2 index MR | 1 of 7 | 2,069 | 21 | −0.051% | +0.563% | 0.614% | 28 n |

ARM C is scored on its own eight-gate set (GATES_ARM_C.md): breadth and
effect size removed as unsatisfiable, three gates added that the daily arms
never face. It is not comparable to the others by count alone.

## The finding

**Every arm found a positive gross edge. One of them survives its own
costs.**

```
          gross    cost     net
  ARM A  +0.324%  0.403%  -0.078%     33 nights
  ARM B  +0.232%  0.285%  -0.053%     27 nights
  ARM E  +0.563%  0.614%  -0.051%     28 nights
  ARM D  +0.360%  0.310%  +0.050%      7 nights
  ARM C  +0.019%  0.035%  -0.016%      0 nights (1h hold, spread only)
  ARM F  +0.590%  0.077%  +0.513%      4 nights
```

Six strategies, six sealed chats that never saw a price, four different
families of idea. The one that survives is not the one with the best
signal — ARM E's gross edge is larger than ARM F's part A on a per-trade
basis once you account for its holding period, and ARM A's is comparable.
**The one that survives is the one that holds for four days instead of
thirty.** Financing at 2.5% a year on a leveraged CFD is 0.21% a month, and
a trend system holding a month pays it every month.

ARM F — the only arm that could see the data — said exactly this in its
first round:

> "Trend following failed. Seven trend and momentum variants all lost money
> after costs from 2018 onwards. Before costs they made 6-10% a year in
> 2005-2017, but overnight CFD financing on months-long leveraged positions
> wiped that out."
> "Short dip-buys worked. Buying a sharp pullback in an uptrend and holding
> for about 4 days avoids most financing."

Our gates reach the same conclusion independently, from four specifications
written by chats that had no data at all.

## The second pattern: 2012

| Arm | E1 2005-2012 | E2 2012-2019 | E3 2019-2026 |
|---|---|---|---|
| A | **+0.499%** | −0.449% | −0.198% |
| B | **+0.242%** | −0.287% | −0.114% |
| D | **+0.520%** | −0.384% | +0.149% |
| E | **+0.956%** | −0.730% | −0.139% |
| F part A | +0.575% | +0.518% | +0.459% |

Every trend-based arm is positive in era 1 and negative in era 2. None of
them knew; all four were written blind. ARM F's dip-buy is the only thing
here that is positive in all three, and it decays gently rather than
flipping.

## Where the cost model decides the answer

Two places, and both are worth saying out loud because they are the
difference between a result and an artefact.

**ARM F's overnight sleeve.** Gross +0.0508%/trade, our cost 0.0497%, net
+0.0011%. On its own cheaper spread assumption it is worth 2.5-4% a year;
on ours, 0.4%. Our gross matches its own ("11-14% a year before costs"), so
we agree about the edge and differ only on the bill.

**ARM C.** Gross +1.92bp/trade, our cost 3.50bp, net −1.58bp. Its own
assumption was about 1.3bp round trip, under which it is marginally
positive. Same disagreement, same shape.

In both cases a real but small edge sits just either side of the spread.
That is not a flaw in the test — it is the answer. An edge this size is a
bet on your broker, not on the market.

## What the arms got right, verified independently

- **ARM F's backtest reproduces.** 696 trades vs its 697; at 4% risk,
  21.8%/yr vs 20.1%, 19.8% drawdown vs 20.9%, end equity 248,203 vs
  ~251,700.
- **ARM F's drawdown claim is honest.** It said 21.1%; we measure 20.7% at
  daily resolution with open positions marked.
- **ARM F's session-boundary claim is correct.** We rebuilt the check from
  scratch: hourly bars are UTC by open, 100% match to daily on high, low
  and close across 5,591 nas100usd and 5,490 de30eur sessions.
- **ARM C's timezone handling is correct**, and it was the only arm to
  specify the DST mapping explicitly without being asked.

## Engine corrections made during the run, all of which removed a pass

1. **Same-day exits were never closed.** A stop hit on the entry bar left a
   phantom position marked to market forever. It inflated bull years and
   produced a −32% 2022 from seven trades averaging −1.46%. Caught by the
   per-trade table.
2. **Robustness on a negative base is meaningless** — a less-negative
   perturbation scores as a larger fraction. Now reported as not applicable
   and counted as not cleared.
3. **The matched control needs non-trade bars.** ARM E's always-in-market
   sleeve left only 14% of trades matchable; the gate was showing +1.12% on
   a biased remnant. Now reported as not determinable.
4. **Gate 6 is a daily control** and cannot match ARM F's hourly overnight
   trades at all. Reported on the daily sleeve with the limitation stated.

## Data defect found, and why it mattered

`spx500usd_oanda_h1.csv` carries `+00:00` for 129,175 rows and then switches
to **naive** timestamps for its last 907, from 2026-08-07 15:00 onward.
Price continuity across the boundary (7756.4 -> 7756.3) and sequential hours
confirm the tail is UTC like the rest. Had it been local time, every session
boundary after that date would have been wrong by four or five hours and
nothing in the pipeline would have flagged it.

## Still open

- The spread table needs sign-off. It decides ARM F's part B and ARM C.
- Gate 7's threshold (claim may understate the measured figure by at most
  25%) is mine, not preregistered. It needs the same sign-off.
- Forward tracking of all six arms from the seal date, per FORWARD_TEST.md.
