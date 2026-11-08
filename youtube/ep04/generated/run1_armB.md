# RUN 1 — ARM B (open book) — raw first output

```
RECEIVED: 2026-11-01
PROMPT:   PROMPTS_TO_RUN.md, ARM B, pasted verbatim
RUN:      fresh chat, no project, memory off
STATUS:   first output, unedited.
SOURCE:   delivered as a Claude document --
          https://claude.ai/artifact/WniiXaH6zRSZYqJojcn433
          Text below is the version Dave pasted back, plus the chat
          message that accompanied it.
```

PROCEDURAL NOTE, recorded because it differs between arms: this arm was
produced in a chat where document creation was available, and the output
came back as a document rather than a chat reply. Arm A came back as a
plain reply. The prompt was identical in both. This is a difference in the
generating environment between arms of the same run and is disclosed rather
than smoothed over.

The two questions it asked at the end were NOT answered. Per
preregistration section 2 the first output is the one that gets tested.
It stated its own assumptions for both, so the specification is complete
without them.

---

## Accompanying chat message

Outline is up; now writing the summary and the key design insight.
The specification doc is ready for you to read, edit inline, or comment on.
The strategy: It trades 60-day trends on daily bars in all 21 markets. It only enters when the trend came from many small same-direction days, not a few big jumps. Each trade is held for 20 bars, with a wide stop checked on closes only.
Why this design: Your matched control on prior return and volatility gives plain momentum or mean reversion an edge of zero by construction. So the signal has to use something those two numbers don't capture, which here is how the return was spread across the days.
Economic reason: Limited attention, the "frog in the pan" effect. Big, obvious moves get priced at once. A slow drip of small moves gets underreacted to, so it keeps going.
What would make me abandon it: The doc lists seven pre-committed kill conditions. The sharpest is a mirror test. Run the same rules on jump-built trends instead. If those do as well as the smooth-trend trades against the matched control, the filter does nothing and I'd drop the strategy.
I wrote this without seeing your data, so it should be run once, unchanged. Two things would let me tighten it before you run it:

* Does your grader have its own cost and financing model? I assumed fixed spreads plus 2% a year financing.
* Are your three eras 2005-2011, 2012-2018 and 2019-2026, or split differently?

---

## Document

Path-Continuity Trend Strategy — Specification
1 Nov 2026 · @Dave

### Summary

The strategy trades 60-day trends in all 21 markets on daily bars, but only when the trend was built from many small moves rather than a few large jumps. It holds each trade for 20 bars with a wide disaster stop.

The design is driven by criterion 6. A control matched on prior return and volatility gives any signal built only from prior return or volatility an edge of zero by construction. Plain momentum and plain mean reversion both fail it. So the signal must carry information that prior return and volatility do not: here, how the return was distributed across days.

This specification was written without looking at your data, and it should be run once, unchanged. Any tuning after the first run turns the test into an in-sample fit.

### Economic rationale

The mechanism is limited attention, known in the equity literature as "frog in the pan" (Da, Gurun and Warachka, 2014). Information that arrives as a large, salient jump is noticed and priced quickly. Information that arrives as a long run of small moves, each too small to attract attention, is priced slowly, so the move keeps going.

The same structure exists in macro markets. A data surprise, an OPEC decision or a central-bank shock produces a jump that is absorbed at once. A slow repricing of the rate path, a gradual supply deficit in a metal or a drift in risk appetite produces many small same-direction days, and participants who rebalance slowly keep pushing it.

Two trends with the same 60-day return and the same volatility should therefore behave differently. The one made of many small days should continue more. That difference is exactly what criterion 6 isolates, which is why this signal suits the test.

The published evidence is for the cross-section of US stocks. Its extension to time-series trades in FX, metals, indices, energy, rates and softs is the hypothesis being tested here, not an established result.

### Specification

**Instruments.** All 21: eurusd, gbpusd, usdjpy, usdcad, audusd, eurgbp, eurjpy, xauusd, xagusd, xptusd, xcuusd, spx500usd, nas100usd, de30eur, bcousd, natgasusd, usb10yusd, de10ybeur, cornusd, wheatusd, sugarusd. Each is traded independently, long or short. When the list order matters below, it is this order.

**Timeframe and data handling**

1. Daily bars only. Hourly and 15-minute bars are not used.
2. Any bar dated Saturday or Sunday is merged into the next weekday bar: open from the weekend bar, high and low as the extremes of both, close from the weekday bar. A weekend bar with no following weekday bar is dropped.
3. A bar with a missing close is treated as absent. Missing days are not filled.
4. All lookbacks count bars that exist in that market's series, not calendar days.
5. Signals are computed at the close of bar t. Orders fill at the open of bar t+1 or at the close of a named bar, as stated below. No intraday prices are used.

**Definitions at signal bar t**

Daily log return, for each bar i:  r_i = ln(C_i / C_{i-1})

Trend return over L = 60 bars, and its direction:
  R_t = ln(C_t / C_{t-60}),   d_t = sign(R_t)

Volatility: sigma_t = sample standard deviation (divisor n-1) of r over bars t-59 to t (W = 60 returns).

Up and down day counts over bars t-59 to t: P_t = number of r_i > 0, N_t = number of r_i < 0. A return of exactly zero counts as neither.

Information discreteness (the signal):
  ID_t = d_t x (N_t - P_t) / 60

ID_t is negative when most days moved in the trend's direction (continuous information) and near zero or positive when the trend came from a few large days.

**Entry.** At the close of bar t, open a position in direction d_t at the open of bar t+1 if all of these hold:

1. No position is open in that market.
2. Bar t-60 exists in the series (at least 61 bars of history).
3. R_t != 0 and sigma_t > 0.
4. ID_t <= -0.10. With L = 60 this means at least 6 more days in the trend direction than against it.

Entry price E = open of bar t+1. Bar t+1 is holding bar 1.

**Exit**

1. Time exit: close the position at the close of holding bar H = 20 (bar t+20).
2. Disaster stop: stop distance, fixed at entry, in log units:  D = 2.5 x sigma_t x sqrt(20)
3. At the close of each holding bar j = 1 to 19, if d x ln(C_{t+j} / E) <= -D, exit at the open of bar t+j+1. Stops are checked on closes only, never on intraday highs or lows.
4. No profit target, no trailing stop, no other exit.
5. If the data ends with a position open, it is closed at the last available close and counted as a trade.
6. Re-entry: after a time exit, the entry rule is evaluated at that same close and may open a new trade at the next open. After a stop exit at the open of bar t+j+1, the first eligible signal is the close of bar t+j+1. Every exit and re-entry is a separate trade and pays full costs.

**Trade return.** Per-trade return, in percent, after costs:

  net = 100 x [ d ln(X / E) - c - 0.02 x (n / 365) ]

X is the exit price, c is the round-trip cost from the table below as a fraction, and n is calendar nights between the entry date and the exit date. The 0.02 term is financing at 2.0% a year on notional, charged long and short.

**Costs (round trip, % of price)**

| Market | Cost % | Market | Cost % | Market | Cost % |
|---|---|---|---|---|---|
| eurusd | 0.02 | xauusd | 0.05 | bcousd | 0.08 |
| gbpusd | 0.03 | xagusd | 0.10 | natgasusd | 0.30 |
| usdjpy | 0.02 | xptusd | 0.25 | usb10yusd | 0.06 |
| usdcad | 0.03 | xcuusd | 0.15 | de10ybeur | 0.06 |
| audusd | 0.03 | spx500usd | 0.03 | cornusd | 0.25 |
| eurgbp | 0.03 | nas100usd | 0.04 | wheatusd | 0.25 |
| eurjpy | 0.04 | de30eur | 0.04 | sugarusd | 0.30 |

These are fixed assumptions for retail CFD spreads plus slippage. In the daily equity curve, half the round-trip cost is charged at entry, half at exit, and financing accrues each calendar night.

**Position sizing ($10,000 account)**

1. Equity Q_t = account value at the close of bar t: cash plus open positions marked at their closes, after all costs charged so far. Start Q = $10,000.
2. Target USD notional = 0.0015 x Q_t / sigma_t. Each position is sized for a daily volatility of 0.15% of equity.
3. Units = notional / V, where V is the USD value of one unit at C_t:
   - eurusd, gbpusd, audusd: V = C_t (1 unit = 1 unit of base currency).
   - usdjpy, usdcad: V = 1.
   - eurgbp, eurjpy: V = eurusd close on the same date.
   - de30eur, de10ybeur: V = C_t x eurusd close on the same date.
   - all other markets: V = C_t.
   - If eurusd has no bar that date, use its most recent earlier close.
4. Gross cap: total USD notional of open positions (at their latest closes) plus the new one must not exceed 5 x Q_t. If it would, the new position is cut to the remaining room. If no room remains, the trade is skipped.
5. When several markets signal on the same close, they are sized and capped in the instrument-list order above.
6. Units are fixed for the life of the trade. No pyramiding, no resizing.
7. Profit and loss in a non-USD quote currency is converted at that day's close: JPY / usdjpy, CAD / usdcad, GBP x gbpusd, EUR x eurusd.
8. In the backtest, fractional units are allowed. Live, units are rounded down to the broker's smallest increment, and a trade that rounds to zero is skipped.

Example: eurusd with sigma = 0.55% on $10,000 gives a notional of about $2,730. Natgasusd with sigma = 3.5% gives about $430.

**Parameters**

| Parameter | Value | Robustness step | Half-step test values |
|---|---|---|---|
| L, trend and ID lookback (bars) | 60 | 20 | 50, 70 |
| W, volatility window (bars) | 60 | 20 | 50, 70 |
| theta, ID entry threshold | -0.10 | 0.10 | -0.05, -0.15 |
| H, holding period (bars) | 20 | 10 | 15, 25 |
| k, stop multiple of sigma*sqrt(H) | 2.5 | 1.0 | 2.0, 3.0 |
| Daily vol per position (% of equity) | 0.15 | 0.10 | 0.10, 0.20 |
| Gross notional cap (x equity) | 5 | 2 | 4, 6 |

Costs and the 2.0% financing rate are assumptions about the market, not strategy parameters, and are not moved in the robustness test. The stop always uses the current H inside sqrt(H).

**How each criterion applies.** Where your grading rules left a choice open, this is the reading the strategy was designed against. If your grader differs, it governs.

1. Sign consistency — Eras assumed to be 2005-2011, 2012-2018, 2019-2026, with each trade assigned by its entry date. The mechanism is behavioural and not tied to any rate or policy regime.
2. Breadth — All 21 markets are traded with identical rules and no per-market settings.
3. Effect size — Mean net return per trade, from the trade-return formula, including spread and financing. A 20-bar hold amortises spread over a move of several daily standard deviations.
4. Sample — Expect very roughly 100 to 200 trades per market and a few thousand in total, far above 200.
5. Robustness — Five signal parameters, each with a declared step (Parameters table). All are round values on a broad grid, not optimised.
6. Matched control — Recommended control: for each trade, take every bar in the same market and era in the same cell of a 5 x 5 grid of quintiles of R_t / (sigma_t sqrt(60)) and of sigma_t, quintiles computed within that market and era. Control return is the mean net return of a 20-bar trade in direction d from each of those bars, with the same costs. Edge = trade net return minus its cell's control return.
7. Daily risk — Every rule acts on daily closes or the next open, so the daily equity curve is the strategy's native resolution. Drawdown is measured on Q_t at every daily close, all markets combined, with open positions marked to market.

### What would make me abandon it

The strategy is abandoned if any one of these holds on the first and only run. None of them can be fixed by changing a parameter afterwards.

1. **The mirror test fails.** Run the same rules with the filter reversed: trades taken only when ID_t >= +0.10 (trends built from a few jumps). The theory says these should do worse than their matched control. If the reversed trades' edge is equal to or above the strategy's edge, the filter is doing nothing, and any profit is plain momentum that the control should have removed.
2. **No monotone gradient.** Split all would-be trend trades (every bar with R_t != 0, ignoring theta) into terciles of ID_t. Edge versus control must rise from the highest-ID tercile to the lowest. If it does not, the mechanism is not what is producing the result.
3. The edge versus the matched control is zero or negative in the full sample or in any one era.
4. Fewer than 14 of 21 markets show a positive edge versus control.
5. Mean net return per trade is below 0.20% after the stated spreads and financing.
6. **Concentration.** One asset class (FX, metals, indices, energy, rates, softs) supplies more than half of total net profit, or removing the single best market cuts mean net return per trade by more than half.
7. **Robustness fails.** Any half-step change in L, W, theta, H or k leaves less than 80% of the edge.

Passing all seven does not prove the mechanism. It earns the strategy a period of live paper trading on new data, judged by the same rules.

### Where it is most likely to fail

The weakest criteria are 6 and 3, in that order. Criterion 6 asks for an effect that has been documented in equities but not, to my knowledge, across these markets.

- **Criterion 6, matched control.** Within a 5 x 5 control cell, low-ID trades may still have slightly larger trend returns than the cell average, which can flatter the edge. Abandonment tests 1 and 2 exist to catch this.
- **Criterion 3, effect size.** Financing at 2.0% a year costs about 0.15% on a 28-night trade, before spread. Low-volatility FX pairs need roughly 0.35-0.40% gross per trade to clear 0.20% net, which is demanding.
- **Criterion 1, sign consistency.** The middle era, 2012-2018, was poor for trend strategies generally. A smaller edge there is likely; a negative one would end it.
- **Data check before running.** If the commodity or bond CFD series contain contract-roll gaps, one jump can distort R_t and trigger false stops. Confirm the series are continuous or back-adjusted first; ID itself is barely affected by a single day.

Open question: if your grader uses its own cost or financing model, substitute it before the run and change nothing else.
