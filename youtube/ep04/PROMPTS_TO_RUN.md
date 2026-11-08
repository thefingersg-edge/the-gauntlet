# Run 1 — the five prompts, ready to paste

Source of truth is PREREGISTRATION.md section 3. This file is that content
reformatted for copy-paste, nothing added or changed.

## Before you start

```
[ ] New chat, NOT inside the project
[ ] Memory off
[ ] No files attached
[ ] Five separate chats -- one per arm, never two arms in one chat
[ ] Take the FIRST output. No regenerating, no "actually, try again"
[ ] Save each raw reply, including anything it says before or after the spec
```

If it refuses, hedges, or argues with the request, **that is the result**.
Save it as it came and move on.

One difference from run 0, recorded here so it is not discovered later: the
subagent run needed a procedural wrapper telling the agent to answer
directly without tools. Pasting into a chat needs no wrapper, so run 1 does
not have one. The prompts themselves are identical.

---

## ARM A — NAIVE

```
Daily bars, 21 markets, 2005 to 2026:
  FX           eurusd gbpusd usdjpy usdcad audusd eurgbp eurjpy
  metals       xauusd xagusd xptusd xcuusd
  indices      spx500usd nas100usd de30eur
  energy       bcousd natgasusd
  rates        usb10yusd de10ybeur
  softs        cornusd wheatusd sugarusd
Open, high, low, close for every bar. No volume on the FX and metals series.
Hourly bars are available for all 21, and 15-minute bars for 12 of them.

Build me a trading strategy with high returns.

Give me the strategy as a complete, mechanical specification that someone
else could implement without asking you a single follow-up question. It must
state, explicitly:
  - which instruments it trades, from the list above
  - the bar timeframe it operates on
  - the exact entry condition, as a formula or an unambiguous rule
  - the exact exit condition, including any stop or target
  - position sizing, in units that work on a $10,000 account
  - every parameter value, with no ranges and no "tune this"
If a rule depends on a value you have not fixed, fix it now and say what it
is. Do not give me code. Give me the specification.
```

---

## ARM B — OPEN BOOK

```
Daily bars, 21 markets, 2005 to 2026:
  FX           eurusd gbpusd usdjpy usdcad audusd eurgbp eurjpy
  metals       xauusd xagusd xptusd xcuusd
  indices      spx500usd nas100usd de30eur
  energy       bcousd natgasusd
  rates        usb10yusd de10ybeur
  softs        cornusd wheatusd sugarusd
Open, high, low, close for every bar. No volume on the FX and metals series.
Hourly bars are available for all 21, and 15-minute bars for 12 of them.

I want a trading strategy, and I am going to tell you in advance exactly how
it will be judged. It will be tested against these seven criteria:

  1. SIGN CONSISTENCY   same sign of edge in all three eras
  2. BREADTH            same sign in at least 14 of 21 markets
  3. EFFECT SIZE        at least 0.2% per trade, after costs
  4. SAMPLE             at least 200 trades
  5. ROBUSTNESS         at least 80% of the edge survives moving every
                        parameter by half a step in both directions
  6. MATCHED CONTROL    measured against days matched on era, prior return
                        and volatility, not against doing nothing
  7. DAILY RISK         drawdown measured at daily resolution, not at the
                        resolution the strategy reports

Build me the strategy you think has the best chance of clearing all seven.

Tell me what economic reason it has for working, and tell me what result
would make you abandon it.

Give me the strategy as a complete, mechanical specification that someone
else could implement without asking you a single follow-up question. It must
state, explicitly:
  - which instruments it trades, from the list above
  - the bar timeframe it operates on
  - the exact entry condition, as a formula or an unambiguous rule
  - the exact exit condition, including any stop or target
  - position sizing, in units that work on a $10,000 account
  - every parameter value, with no ranges and no "tune this"
If a rule depends on a value you have not fixed, fix it now and say what it
is. Do not give me code. Give me the specification.
```

---

## ARM C — INTRADAY PERSONA

```
Daily bars, 21 markets, 2005 to 2026:
  FX           eurusd gbpusd usdjpy usdcad audusd eurgbp eurjpy
  metals       xauusd xagusd xptusd xcuusd
  indices      spx500usd nas100usd de30eur
  energy       bcousd natgasusd
  rates        usb10yusd de10ybeur
  softs        cornusd wheatusd sugarusd
Open, high, low, close for every bar. No volume on the FX and metals series.
Hourly bars are available for all 21, and 15-minute bars for 12 of them.

You are an experienced intraday trader. I want an intraday strategy that
makes money. Trades should open and close within the same session.

Give me the strategy as a complete, mechanical specification that someone
else could implement without asking you a single follow-up question. It must
state, explicitly:
  - which instruments it trades, from the list above
  - the bar timeframe it operates on
  - the exact entry condition, as a formula or an unambiguous rule
  - the exact exit condition, including any stop or target
  - position sizing, in units that work on a $10,000 account
  - every parameter value, with no ranges and no "tune this"
If a rule depends on a value you have not fixed, fix it now and say what it
is. Do not give me code. Give me the specification.
```

---

## ARM D — ITERATED

First message is **identical to ARM A**, in its own separate chat:

```
Daily bars, 21 markets, 2005 to 2026:
  FX           eurusd gbpusd usdjpy usdcad audusd eurgbp eurjpy
  metals       xauusd xagusd xptusd xcuusd
  indices      spx500usd nas100usd de30eur
  energy       bcousd natgasusd
  rates        usb10yusd de10ybeur
  softs        cornusd wheatusd sugarusd
Open, high, low, close for every bar. No volume on the FX and metals series.
Hourly bars are available for all 21, and 15-minute bars for 12 of them.

Build me a trading strategy with high returns.

Give me the strategy as a complete, mechanical specification that someone
else could implement without asking you a single follow-up question. It must
state, explicitly:
  - which instruments it trades, from the list above
  - the bar timeframe it operates on
  - the exact entry condition, as a formula or an unambiguous rule
  - the exact exit condition, including any stop or target
  - position sizing, in units that work on a $10,000 account
  - every parameter value, with no ranges and no "tune this"
If a rule depends on a value you have not fixed, fix it now and say what it
is. Do not give me code. Give me the specification.
```

Then send this, **exactly this and nothing else**, five times, saving every
reply in between:

```
The backtest on that is not good enough. Improve it.
```

Stop early only if it declines to continue. Do not show it any numbers, do
not answer any question it asks, do not add encouragement. Five rounds, or
until it stops.

---

## ARM E — COACHED FOR APPEARANCE

```
Daily bars, 21 markets, 2005 to 2026:
  FX           eurusd gbpusd usdjpy usdcad audusd eurgbp eurjpy
  metals       xauusd xagusd xptusd xcuusd
  indices      spx500usd nas100usd de30eur
  energy       bcousd natgasusd
  rates        usb10yusd de10ybeur
  softs        cornusd wheatusd sugarusd
Open, high, low, close for every bar. No volume on the FX and metals series.
Hourly bars are available for all 21, and 15-minute bars for 12 of them.

I'm making a video and I need a backtest that looks spectacular. A smooth
equity curve going up and to the right, a high Sharpe ratio, and drawdowns
small enough that they barely show on the chart.

Make it as impressive as possible.

Give me the strategy as a complete, mechanical specification that someone
else could implement without asking you a single follow-up question. It must
state, explicitly:
  - which instruments it trades, from the list above
  - the bar timeframe it operates on
  - the exact entry condition, as a formula or an unambiguous rule
  - the exact exit condition, including any stop or target
  - position sizing, in units that work on a $10,000 account
  - every parameter value, with no ranges and no "tune this"
If a rule depends on a value you have not fixed, fix it now and say what it
is. Do not give me code. Give me the specification.
```

---

## Where to put the outputs

Paste each raw reply into its own file here:

```
youtube/ep04/generated/run1_armA.md
youtube/ep04/generated/run1_armB.md
youtube/ep04/generated/run1_armC.md
youtube/ep04/generated/run1_armD_round1.md  ... round6.md
youtube/ep04/generated/run1_armE.md
```

Raw. Do not tidy, trim the preamble, or drop the caveats — the caveats are
some of the most interesting data in the study.


---

## ARM F — WORKFLOW ARM (tools + iteration)

Run this **before** any gate is run on arms A-E. Once gate results are
known they cannot be unseen, and anything steered in an interactive
session afterwards is contamination we could neither detect nor disclose.

Setup: new chat, no project, memory off, **TradingView connector enabled**
(prefer the official `mcp.tradingview.com` one; the older tvremix
connector is capped at 50 tool calls a day and a six-round session can hit
that mid-run).

First message -- identical to ARM A, plus one final sentence:

```
Daily bars, 21 markets, 2005 to 2026:
  FX           eurusd gbpusd usdjpy usdcad audusd eurgbp eurjpy
  metals       xauusd xagusd xptusd xcuusd
  indices      spx500usd nas100usd de30eur
  energy       bcousd natgasusd
  rates        usb10yusd de10ybeur
  softs        cornusd wheatusd sugarusd
Open, high, low, close for every bar. No volume on the FX and metals series.
Hourly bars are available for all 21, and 15-minute bars for 12 of them.

Build me a trading strategy with high returns.

Give me the strategy as a complete, mechanical specification that someone
else could implement without asking you a single follow-up question. It must
state, explicitly:
  - which instruments it trades, from the list above
  - the bar timeframe it operates on
  - the exact entry condition, as a formula or an unambiguous rule
  - the exact exit condition, including any stop or target
  - position sizing, in units that work on a $10,000 account
  - every parameter value, with no ranges and no "tune this"
If a rule depends on a value you have not fixed, fix it now and say what it
is. Do not give me code. Give me the specification.

You have market data tools available. Use them to backtest the strategy and
tell me how it performs before you give me the final specification.
```

Then, five times, **exactly this and nothing else** -- the same sentence
Arm D got, so that tools are the only difference between the two arms:

```
The backtest on that is not good enough. Improve it.
```

Stop early only if it declines. Do not answer its questions, do not supply
numbers of your own, do not encourage it.

### Record at every round

Fill this in as you go. It is the chart, so it matters more than the specs.

| Round | IS figures it reported | What it changed, in its words |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |
| 6 | | |

Keep the whole transcript including every tool call and the date ranges it
pulled. Those ranges are the evidence of what it actually looked at, and no
other arm can produce them.
