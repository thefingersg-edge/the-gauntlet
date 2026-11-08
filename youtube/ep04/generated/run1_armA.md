# RUN 1 — ARM A (naive) — raw first output

```
RECEIVED: 2026-11-01
PROMPT:   PROMPTS_TO_RUN.md, ARM A, pasted verbatim
RUN:      fresh chat, no project, memory off
STATUS:   first output, unedited. Nothing trimmed, nothing tidied.
```

Everything below the line is verbatim as delivered, including the caveat
paragraph and the closing questions. The questions were NOT answered --
per preregistration section 2, the first output is the one that gets
tested.

---

Strategy specification: diversified daily trend follower

What this is, and a caveat first. This is a Donchian-channel breakout system with a moving-average trend filter and volatility-based position sizing, traded across all 21 markets. Trend following is the approach with the longest public track record across this exact mix of FX, metals, indices, energy, rates and softs. The best-known study is Moskowitz, Ooi & Pedersen (2012), "Time Series Momentum."

I have not backtested this on your data, so I can't promise any particular return. Strategies of this kind typically have long flat stretches and drawdowns of 20-40% at the risk level below. Returns come from a small number of large trends. I'm not a financial advisor. Treat this as a rule set to test, not a recommendation to trade.

1. Instruments

All 21: eurusd, gbpusd, usdjpy, usdcad, audusd, eurgbp, eurjpy, xauusd, xagusd, xptusd, xcuusd, spx500usd, nas100usd, de30eur, bcousd, natgasusd, usb10yusd, de10ybeur, cornusd, wheatusd, sugarusd.

Sector groups, used for the caps in section 6:

FX: the 7 currency pairs
Metals: the 4 metals
Indices: the 3 indices
Energy: the 2 energy series
Rates: the 2 bond series
Softs: the 3 softs

2. Timeframe and timing

Bars: daily bars, as supplied. Each instrument's indicators use only its own bars.
When signals are computed: on the close of a completed bar, called bar t.
When orders execute: entry and exit orders from signals fill at the open of bar t+1.
Stops: protective stops are resting orders that can fill intraday (section 4).
Warm-up: an instrument may not trade until it has 200 completed bars.
Data: hourly and 15-minute data are not used.

3. Indicators (all computed at the close of bar t)

HH55_t: the highest High over bars t-55 through t-1. Bar t is excluded.
LL55_t: the lowest Low over bars t-55 through t-1.
HH20_t / LL20_t: the highest High / lowest Low over bars t-20 through t-1.
EMA50_t, EMA200_t: exponential moving averages of Close.
alpha = 2/(N+1).
Each is seeded with the simple average of the first N closes.
ATR20_t: Wilder's Average True Range, 20 periods.
True Range = max(High_t - Low_t, |High_t - Close_t-1|, |Low_t - Close_t-1|).
Seed = simple mean of the first 20 TRs.
After that, ATR_t = (19 x ATR_t-1 + TR_t) / 20.

4. Entry rules

These apply only when there is no open position in the instrument.

Long: Close_t > HH55_t and EMA50_t > EMA200_t.
Short: Close_t < LL55_t and EMA50_t < EMA200_t.
Execution: a market order at the open of bar t+1.
One position per instrument: no pyramiding, and no reversing in a single step.
Re-entry: allowed on any later bar where the entry rule is true again, but never on the same bar as an exit.

5. Exit rules

There is no profit target. Exits happen only through the stop.

Initial stop. It is set at entry and uses the signal bar's values:

Long: Stop = Close_t - 3.0 x ATR20_t
Short: Stop = Close_t + 3.0 x ATR20_t

Trailing update. At the close of every bar after the entry bar, including the entry bar's own close, update the stop:

Long: Stop = max(previous Stop, LL20)
Short: Stop = min(previous Stop, HH20)

The stop only ever moves in the trade's favour.

Stop execution. The stop is a resting stop order.

A long is stopped out on any bar where Low <= Stop. A short is stopped out where High >= Stop.
Normal fill price = the Stop.
Gap rule: if the bar opens through the stop, the fill is the open.
Long fill = min(Open, Stop).
Short fill = max(Open, Stop).
If entry and stop happen on the same bar (it opens, then hits the stop), the trade is closed on that bar at the stop price.

6. Position sizing ($10,000 starting account)

Equity. Equity = account balance plus unrealised P&L, marked at the close of bar t.

USD value of a 1.0 price move per unit (QV). Use the close of bar t for the conversion rates:

Quoted in USD (eurusd, gbpusd, audusd, all metals, spx500usd, nas100usd, bcousd, natgasusd, usb10yusd, the softs): QV = 1
usdjpy, eurjpy: QV = 1 / usdjpy close
usdcad: QV = 1 / usdcad close
eurgbp: QV = gbpusd close
de30eur, de10ybeur: QV = eurusd close

Units.

Units = (0.01 x Equity) / (3.0 x ATR20_t x QV)
So each trade risks 1.0% of equity to the initial stop.
Round down to the broker's minimum trade increment for that instrument.
If the result is below the minimum size, skip the signal.

Notional. Notional = Units x Close_t x QV.

Portfolio caps. These are checked before each new entry. Skip any entry that would breach one.

Max 12 open positions in total.
Max 3 open positions per sector group, long and short combined.
Notional of a single position <= 1.5 x Equity. If it is larger, cut Units down to fit.
Total notional of all open positions <= 6 x Equity.

Several signals on the same day. Rank them by breakout strength:

Longs: (Close_t - HH55_t) / ATR20_t
Shorts: (LL55_t - Close_t) / ATR20_t

Process them highest first, applying the caps in that order.

7. Fixed parameters

Parameter | Value
Entry channel | 55 bars
Trailing channel | 20 bars
Trend filter | EMA 50 vs EMA 200
ATR | Wilder, 20 bars
Initial stop | 3.0 x ATR
Risk per trade | 1.0% of equity
Max positions | 12 total, 3 per sector
Notional caps | 1.5x per position, 6x total
Profit target | None
Warm-up | 200 bars

8. Things the implementer must handle

Futures-based CFDs (bcousd, natgasusd, cornusd, wheatusd, sugarusd, the bond series) roll between contract months.
If your price series aren't back-adjusted, roll gaps will produce false breakouts.
Back-adjust the series before computing indicators.
Costs. Include spread and overnight financing in any backtest. Trades last weeks to months, so financing is material.

You asked for high returns, so here are the obvious ways to raise them, each of which also raises drawdowns:

risk 1.5% instead of 1%;
add one extra unit after each further 1 x ATR move in the trade's favour;
scale total risk to a portfolio volatility target.

I'd test the base version before any of those. If you attach the daily files, I can run that backtest myself, with costs, and report returns, drawdowns and per-sector results. Which broker will this run at? Its minimum unit sizes decide whether the smaller index and bond positions are tradable at $10,000.
