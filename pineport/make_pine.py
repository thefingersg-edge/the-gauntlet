#!/usr/bin/env python3
"""Render a complete, paste-ready Pine v6 strategy from a trained JSON config.

WHY A GENERATOR RATHER THAN FOUR HAND-EDITED FILES

`train_tf.py --report` prints an input BLOCK, not a script: you still have to
paste ~40 values into an existing .pine by hand, once per timeframe. Every one
of those is a chance to transpose a digit, and a transposed digit produces a
strategy that looks plausible and is not the one that was tested. This renders
the whole file, so what you paste into TradingView is what the Python port
scored -- or it is a bug in one place instead of four.

WHAT IT GETS RIGHT THAT HAND-EDITING MISSED

* LADDER MODE. `emit_pine` printed the DOLLAR rungs unconditionally. For a
  --ladder-mode percent run that meant markUp=10000 (the disabled sentinel)
  while the scored config had mark_up_pct=8.07. The Pine described a different
  strategy from the results table. Here the rung block follows ladder_mode.

* max_bars_back. Pine's default is 300 and it silently returns wrong values
  past that rather than erroring. `ta.dmi(len, smooth)` needs len + smooth
  bars, so the NAS100 M15 config needs 1869 + 1223 = 3092. Computed per config
  from the actual parameters, not guessed.

* FILTER TOGGLES. use_adx_filter / use_volatility_filter / use_macro_filter
  are read from the config, so a filter the ladder REVERTED cannot arrive
  switched on.

    python make_pine.py --config configs/nas100usd_oanda_h4_H4_trained.json \
                        --tf H4 --symbol NAS100 --out NAS100_4h.pine
    python make_pine.py --all-nas100
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strategy import Params                            # noqa: E402

TF_LABEL = {"D": "Daily", "H4": "4h", "H1": "1h", "M15": "15m"}

#: Pine caps max_bars_back at 5000. Anything above needs request.security on a
#: higher timeframe -- see m5_htf_filters.pine for that pattern.
PINE_MAX_BARS_BACK = 5000


def required_lookback(c: dict) -> tuple[int, str]:
    """Longest history any indicator in this config needs, and what drives it."""
    need = {
        "lsma_length_long": c["lsma_length_long"],
        "lsma_length_short": c["lsma_length_short"],
        "ssma_length_long": c["ssma_length_long"],
        "ssma_length_short": c["ssma_length_short"],
        "rsi_length_long": c["rsi_length_long"],
        "rsi_length_short": c["rsi_length_short"],
        "bb_period_long": c["bb_period_long"],
        "bb_period_short": c["bb_period_short"],
        "kc_length_l": c["kc_length_l"],
        "kc_length_s": c["kc_length_s"],
        # ta.dmi needs len + smooth, which is why an ADX pair can break the
        # limit even though neither number alone does.
        "adx_len + adx_smooth": c["adx_len"] + c["adx_smooth"],
        "adx_len_short + adx_smooth_short": (c["adx_len_short"]
                                             + c["adx_smooth_short"]),
    }
    if c.get("use_volatility_filter"):
        need["atr_long"] = c.get("atr_long", 0)
        need["vol_long"] = c.get("vol_long", 0)
    if c.get("use_volatility_filter_short"):
        need["atr_short"] = c.get("atr_short", 0)
        need["vol_short"] = c.get("vol_short", 0)
    k = max(need, key=need.get)
    return int(need[k]), k


def num(v) -> str:
    """Pine literal: ints stay ints, floats keep 6 significant figures."""
    f = float(v)
    return str(int(f)) if f.is_integer() else f"{f:.6g}"


def ladder_block(c: dict) -> tuple[str, str]:
    """Input declarations and price-conversion for the rungs, per ladder_mode."""
    mode = c.get("ladder_mode", "dollars")
    if mode == "percent":
        decl = "\n".join(
            f'{p:<18}= input.float({num(c[k + "_pct"])}, "{p}", step=0.1)'
            for p, k in [("markUpPct", "mark_up"), ("lockProfitUpPct", "lock_profit_up"),
                         ("markDownPct", "mark_down"), ("lockProfitDownPct", "lock_profit_down"),
                         ("rangeLPct", "range_long"), ("rangeSPct", "range_short")])
        conv = """// Rungs are PERCENTAGES OF THE ENTRY PRICE, fixed at entry so they cannot
// drift mid-trade. The dollar original meant something different at every
// price level, which is why no window spanning two eras could be fitted.
ladderUnit     = na(initialEntryPrice) ? na : initialEntryPrice / 100.0
markUp         = markUpPct         * ladderUnit
lockProfitUp   = lockProfitUpPct   * ladderUnit
markDown       = markDownPct       * ladderUnit
lockProfitDown = lockProfitDownPct * ladderUnit
rangeL         = rangeLPct         * ladderUnit
rangeS         = rangeSPct         * ladderUnit"""
        return decl, conv
    decl = "\n".join(
        f'{p:<18}= input.float({num(c[k])}, "{p}", step=1)'
        for p, k in [("markUp", "mark_up"), ("lockProfitUp", "lock_profit_up"),
                     ("markDown", "mark_down"), ("lockProfitDown", "lock_profit_down"),
                     ("rangeL", "range_long"), ("rangeS", "range_short")])
    return decl, "// Rungs are ABSOLUTE POINTS (the Pine original)."


def render(c: dict, tf: str, symbol: str, note: str = "") -> str:
    mbb_need, driver = required_lookback(c)
    mbb = min(max(500, mbb_need + 50), PINE_MAX_BARS_BACK)
    warn = ""
    if mbb_need > PINE_MAX_BARS_BACK:
        warn = (f"// !! {driver} = {mbb_need} EXCEEDS Pine's {PINE_MAX_BARS_BACK}-bar\n"
                f"// !! ceiling. Compute it on a higher timeframe via request.security\n"
                f"// !! (see m5_htf_filters.pine). This script WILL be wrong as-is.\n")

    ldecl, lconv = ladder_block(c)
    title = f"{symbol} {TF_LABEL.get(tf, tf)}"

    # RESOLVE TOGGLES THROUGH Params, NOT c.get(). A key ABSENT from the JSON
    # takes the dataclass default, which is not always False:
    # gold_15m_scalefree.json omits use_sma_trigger_short, Params defaults it
    # to True, and the port therefore REQUIRED SSMAS < SSMAL on every short.
    # Reading c.get() gave false and would have emitted a script that takes
    # short trades the scored strategy never took -- a different strategy
    # wearing the same numbers.
    p = Params(**c)
    tf_ = lambda v: "true" if v else "false"          # noqa: E731
    adxL = tf_(p.use_adx_filter)
    adxS = tf_(p.use_adx_filter_short)
    volL = tf_(p.use_volatility_filter)
    volS = tf_(p.use_volatility_filter_short)
    fred = tf_(p.use_macro_filter)
    smaS = tf_(p.use_sma_trigger_short)

    return f'''//@version=6
// =============================================================================
// {title} -- generated by make_pine.py from a trained config.
// DO NOT hand-edit: regenerate instead, or the script and the backtest that
// justified it will drift apart.
//
{note}// -----------------------------------------------------------------------------
// max_bars_back = {mbb}
//   Longest lookback in this config is {driver} = {mbb_need} bars.
//   Pine's DEFAULT IS 300 and it returns wrong values past that WITHOUT
//   erroring, so this must be set explicitly or the backtest is silently junk.
{warn}// =============================================================================
strategy("{title}", shorttitle="{symbol} {tf}", overlay=true,
         initial_capital              = 6000,
         margin_long                  = 0,
         margin_short                 = 0,
         pyramiding                   = 0,
         commission_type              = strategy.commission.percent,
         commission_value             = 0,
         slippage                     = 0,
         process_orders_on_close      = false,
         fill_orders_on_standard_ohlc = true,
         use_bar_magnifier            = false,
         calc_on_every_tick           = false,
         calc_on_order_fills          = false,
         max_bars_back                = {mbb})

// margin_long/short = 0 is REQUIRED. v6 changed the default to 100, which
// silently rejects any entry whose notional exceeds equity -- and made results
// depend on the backtest range, because whether equity had grown enough to
// price you out of your own next trade depended on where the test started.

riskPercent = input.float({num(c.get("risk_percent", 0.8))}, "Risk % of equity", minval=0.0, step=0.1)

// ------------------------------------------------------------------ entries
RSIlengthL    = input.int({num(c["rsi_length_long"])}, "RSI Period LengthL")
RSIlengthS    = input.int({num(c["rsi_length_short"])}, "RSI Period LengthS")
RSIoverSold   = input.float({num(c["rsi_oversold"])}, "Over Sold")
RSIoverBought = input.float({num(c["rsi_overbought"])}, "Under Sold")

LSMAlengthL = input.int({num(c["lsma_length_long"])}, "LSMA Period LengthL")
LSMAlengthS = input.int({num(c["lsma_length_short"])}, "LSMA Period LengthS")
SSMAlengthL = input.int({num(c["ssma_length_long"])}, "SSMA Period LengthL")
SSMAlengthS = input.int({num(c["ssma_length_short"])}, "SSMA Period LengthS")

adx_len     = input.int({num(c["adx_len"])}, "ADX DI Length")
adx_smooth  = input.int({num(c["adx_smooth"])}, "ADX Smoothing Length")
adxVar      = input.float({num(c["adx_threshold"])}, "adx var")
adx_lenS    = input.int({num(c["adx_len_short"])}, "ADX DI LengthS")
adx_smoothS = input.int({num(c["adx_smooth_short"])}, "ADX Smoothing LengthS")
adxVarS     = input.float({num(c["adx_threshold_short"])}, "adx varS")

atr_longL = input.int({num(c.get("atr_long", 14))}, "atr_longL")
Vol_longL = input.int({num(c.get("vol_long", 20))}, "Vol LongL")
atr_longS = input.int({num(c.get("atr_short", 14))}, "atr_longS")
Vol_longS = input.int({num(c.get("vol_short", 20))}, "Vol LongS")
rate_sma_len = input.int({num(c.get("rate_sma_days", 26))}, "Rate SMA Len FRED")

// Toggles below are the state the TRAINING left them in. A filter the ladder
// reverted is off here; turning one on gives you a strategy that was not tested.
useAdxLong     = input.bool({adxL}, "Long ADX filter")
useAdxShort    = input.bool({adxS}, "Short ADX filter")
useVolGateLong = input.bool({volL}, "Long volatility gate")
useVolGateShort= input.bool({volS}, "Short volatility gate")
useRateFilter  = input.bool({fred}, "FRED real-yield filter")
useSmaShort    = input.bool({smaS}, "Short SMA trigger")
enableShorts   = input.bool(true, "Enable short trades")

// ------------------------------------------------------------------ squeeze
lengthL      = input.int({num(c["bb_length_l"])}, "BB Length L")
lengthS      = input.int({num(c["bb_length_s"])}, "BB Length S")
lengthKCL    = input.int({num(c["kc_length_l"])}, "KC Length L")
lengthKCS    = input.int({num(c["kc_length_s"])}, "KC Length S")
multKC       = input.float({num(c["kc_mult"])}, "KC MultFactor")
longVal      = input.float({num(c["long_val"])}, "Long Condition Value")
shortVal     = input.float({num(c["short_val"])}, "Short Condition Value")
useTrueRange = input.bool({"true" if c.get("use_true_range", True) else "false"}, "Use TrueRange (KC)")

BBlengthL = input.int({num(c["bb_period_long"])}, "Bollinger Period Length L", minval=1)
BBmultL   = input.float({num(c["bb_stdev_long"])}, "Bollinger StdDev L", minval=0.001, maxval=50)
BBlengthS = input.int({num(c["bb_period_short"])}, "Bollinger Period Length S", minval=1)
BBmultS   = input.float({num(c["bb_stdev_short"])}, "Bollinger StdDev S", minval=0.001, maxval=50)

// ------------------------------------------------------------- stop shaping
flexUp   = input.float({num(c.get("flex_up", 0.95))}, "Limit Flex", step=0.001)
flexDown = input.float({num(c.get("flex_down", 0.95))}, "Loss Flex", step=0.001)
gapUp    = input.float({num(c.get("gap_up", 0.995))}, "Gap reducer Up", step=0.01)
gapDown  = input.float({num(c.get("gap_down", 0.995))}, "Gap reducer Down", step=0.01)
seedStopLong  = input.float(0, "Long stop seed (per bar)", step=0.01)
seedStopShort = input.float(1000000, "Short stop seed (per bar)", step=0.01)

SL_percent_basedL = input.float({num(c["sl_percent_long"])}, "Loss % Stop MultiplierL", minval=0.0, step=0.1)
L_percent_basedL  = input.float({num(c["limit_percent_long"])}, "Limit % Stop MultiplierL", minval=0.0, step=0.1)
r_ratioL          = input.float({num(c["r_ratio_long"])}, "Risk Reward RatioL", minval=0.0, step=0.1)
SL_percent_basedS = input.float({num(c["sl_percent_short"])}, "Loss % Stop MultiplierS", minval=0.0, step=0.1)
L_percent_basedS  = input.float({num(c["limit_percent_short"])}, "Limit % Stop MultiplierS", minval=0.0, step=0.1)
r_ratioS          = input.float({num(c["r_ratio_short"])}, "Risk Reward RatioS", minval=0.0, step=0.1)

profitLineUp   = input.float({num(c.get("profit_line_up", 1))}, "Profit Line Up", step=1)
profitLineDown = input.float({num(c.get("profit_line_down", 1))}, "Profit Line Down", step=1)
TraceLineUp    = input.float({num(c.get("trace_line_up", 0.001))}, "Trace Line Up", step=0.01)
TraceLineDown  = input.float({num(c.get("trace_line_down", 0.001))}, "Trace Line Down", step=0.01)

{ldecl}

// SCALE-FREE SIZING. A hardcoded divisor is a dollar constant that only
// approximates the stop distance at one price level; dividing by the ACTUAL
// stop distance delivers the stated risk % at any price.
cashRisk     = strategy.equity * riskPercent / 100
stopDistL    = close * SL_percent_basedL / 100
positionSize = math.max(1, math.ceil(cashRisk / (stopDistL * syminfo.pointvalue)))

// =============================================================================
// INDICATORS -- every ta.* call is at global scope. Nothing may sit inside a
// conditional or on the right of an `and`/`or`: v6 evaluates those lazily and
// would skip the state update.
// =============================================================================
price = close

vrsiL = ta.rsi(price, RSIlengthL)
vrsiS = ta.rsi(price, RSIlengthS)
LSMAL = ta.sma(price, LSMAlengthL)
LSMAS = ta.sma(price, LSMAlengthS)
SSMAL = ta.sma(price, SSMAlengthL)
SSMAS = ta.sma(price, SSMAlengthS)

[plus_di,  minus_di,  adx_value]  = ta.dmi(adx_len,  adx_smooth)
[plus_diS, minus_diS, adx_valueS] = ta.dmi(adx_lenS, adx_smoothS)
trend_is_active  = adx_value  > adxVar
trend_is_activeS = adx_valueS < adxVarS

upperBB = ta.vwma(price, lengthL) + multKC * ta.stdev(price, lengthL)
lowerBB = ta.vwma(price, lengthS) - multKC * ta.stdev(price, lengthS)
range1  = useTrueRange ? ta.tr(true) : (high - low)
upperKC = ta.vwma(price, lengthKCL) + ta.vwma(range1, lengthKCL) * multKC
lowerKC = ta.vwma(price, lengthKCS) - ta.vwma(range1, lengthKCS) * multKC
sqzOn   = (lowerBB > lowerKC) and (upperBB < upperKC)

valL = ta.linreg(price - math.avg(math.avg(ta.highest(high, lengthKCL), ta.lowest(low, lengthKCL)), ta.vwma(price, lengthKCL)), lengthKCL, 0)
valS = ta.linreg(price - math.avg(math.avg(ta.highest(high, lengthKCS), ta.lowest(low, lengthKCS)), ta.vwma(price, lengthKCS)), lengthKCS, 0)
sqzUp   = sqzOn and (valL > longVal)
sqzDown = sqzOn and (valS < shortVal)

BBbasisL = ta.vwma(price, BBlengthL)
BBlower  = BBbasisL - BBmultL * ta.stdev(price, BBlengthL)
BBupper  = ta.vwma(price, BBlengthS) + BBmultS * ta.stdev(price, BBlengthS)

atrL = ta.atr(atr_longL)
atrS = ta.atr(atr_longS)
volatility_gateL = atrL > ta.sma(atrL, Vol_longL)
volatility_gateS = atrS > ta.sma(atrS, Vol_longS)

[real_yield, real_yield_ma] = request.security("FRED:DFII10", "D", [close, ta.sma(close, rate_sma_len)], barmerge.gaps_off, barmerge.lookahead_off)
rates_bullish = real_yield < real_yield_ma

// `not X or Y`: an unticked filter passes everything. Every gate is computed
// at global scope above, so lazy evaluation cannot skip a ta.* call.
longFilters  = (not useRateFilter  or rates_bullish)
           and (not useVolGateLong or volatility_gateL)
           and (not useAdxLong     or trend_is_active)
shortFilters = (not useVolGateShort or volatility_gateS)
           and (not useAdxShort     or trend_is_activeS)
           and (not useSmaShort     or (SSMAS < SSMAL))

buyEntry   = ta.crossover(price,  BBlower)
sellEntry  = ta.crossunder(price, BBupper)
rsiCrossUp = ta.crossover(vrsiL,  RSIoverSold)
rsiCrossDn = ta.crossunder(vrsiS, RSIoverBought)

bought = strategy.position_size > strategy.position_size[1]
sold   = strategy.position_size < strategy.position_size[1]

// Captured on the entry bar and held. Replaces close[since_entry_long], a
// dynamic history offset that asked for data further back than the buffer and
// made results depend on how much chart history was loaded.
var float entryCloseL = 0.0
var float entryCloseS = 0.0
if bought
    entryCloseL := close
if sold
    entryCloseS := close

stop_loss_amountL = close * SL_percent_basedL / 100
stop_loss_amountS = close * SL_percent_basedS / 100

// The ternary guard matters: hoisted to global scope these also run on FLAT
// bars, where strategy.opentrades is 0 and entry_price(-1) is out of range.
initialEntryPrice = strategy.opentrades > 0 ? strategy.opentrades.entry_price(0) : na
lastEntry         = strategy.opentrades > 0 ? strategy.opentrades.entry_price(strategy.opentrades - 1) : na

{lconv}

// =============================================================================
// TRAILING STOP / TARGET
// =============================================================================
price_stop_long     = 0.0
price_stop_short    = 10000000.0
targetvalue_long_1  = 0.0
targetvalue_short_1 = 0.0
stopvalue_long      = 0.0
stopvalue_short     = 0.0
stopvalue_long_1    = seedStopLong
stopvalue_short_1   = seedStopShort
profitLockinUp      = initialEntryPrice
profitLockinDown    = initialEntryPrice

if (strategy.position_size > 0)
    stopvalue_long     := close - stop_loss_amountL
    targetvalue_long_1 := entryCloseL + entryCloseL * (L_percent_basedL / 100) * r_ratioL
    profitLockinUp     := ((targetvalue_long_1 - initialEntryPrice) / profitLineUp) + initialEntryPrice

    if ta.crossover(close, targetvalue_long_1)
        stopvalue_long := targetvalue_long_1 * flexUp
    if close > targetvalue_long_1
        stopvalue_long_1 := price_stop_long + ((close - price_stop_long) * gapUp)
    if close > profitLockinUp
        stopvalue_long_1 := price_stop_long + ((close - price_stop_long) * (gapUp - TraceLineUp))

    // Rungs stay unrolled: ta.crossover cannot take a different level per
    // iteration inside a loop.
    if ta.crossover(close, lastEntry + markUp)
        stopvalue_long_1 := lastEntry + lockProfitUp
    if ta.crossover(close, lastEntry + markUp + rangeL)
        stopvalue_long_1 := lastEntry + lockProfitUp + rangeL
    if ta.crossover(close, lastEntry + markUp + rangeL * 2)
        stopvalue_long_1 := lastEntry + lockProfitUp + rangeL * 2
    if ta.crossover(close, lastEntry + markUp + rangeL * 3)
        stopvalue_long_1 := lastEntry + lockProfitUp + rangeL * 3
    if ta.crossover(close, lastEntry + markUp + rangeL * 4)
        stopvalue_long_1 := lastEntry + lockProfitUp + rangeL * 4

    if close < profitLockinUp
        profitLockinUp := 0
    price_stop_long := math.max(stopvalue_long, price_stop_long[1], stopvalue_long_1, profitLockinUp)
else
    price_stop_long := 0.0

if (strategy.position_size < 0)
    stopvalue_short     := close + stop_loss_amountS
    targetvalue_short_1 := entryCloseS - entryCloseS * (L_percent_basedS / 100) * r_ratioS
    profitLockinDown    := initialEntryPrice - ((initialEntryPrice - targetvalue_short_1) / profitLineDown)

    if ta.crossunder(close, targetvalue_short_1)
        stopvalue_short := targetvalue_short_1 + ((1 - flexDown) * targetvalue_short_1)
    if close < targetvalue_short_1
        stopvalue_short_1 := price_stop_short[1] - ((price_stop_short[1] - close) * gapDown)
    if close < profitLockinDown
        stopvalue_short_1 := price_stop_short[1] - ((price_stop_short[1] - close) * (gapDown - TraceLineDown))

    if ta.crossunder(close, lastEntry - markDown)
        stopvalue_short_1 := lastEntry - lockProfitDown
    if ta.crossunder(close, lastEntry - markDown - rangeS)
        stopvalue_short_1 := lastEntry - lockProfitDown - rangeS
    if ta.crossunder(close, lastEntry - markDown - rangeS * 2)
        stopvalue_short_1 := lastEntry - lockProfitDown - rangeS * 2
    if ta.crossunder(close, lastEntry - markDown - rangeS * 3)
        stopvalue_short_1 := lastEntry - lockProfitDown - rangeS * 3
    if ta.crossunder(close, lastEntry - markDown - rangeS * 4)
        stopvalue_short_1 := lastEntry - lockProfitDown - rangeS * 4

    if close > profitLockinDown
        profitLockinDown := 100000000
    price_stop_short := math.min(stopvalue_short, price_stop_short[1], stopvalue_short_1, profitLockinDown)
else
    price_stop_short := 10000000.0

// =============================================================================
// ORDERS
// =============================================================================
longSignal  = rsiCrossUp and buyEntry and sqzUp and (LSMAS > LSMAL) and longFilters
shortSignal = enableShorts and rsiCrossDn and sellEntry and sqzDown and shortFilters

if longSignal
    strategy.entry("long", strategy.long, qty=positionSize)
else
    strategy.cancel("long")

if shortSignal
    strategy.entry("short", strategy.short, qty=positionSize)
else
    strategy.cancel("short")

// v6 removed the `when=` parameter from strategy.*(), so exits are wrapped.
if strategy.position_size > 0
    strategy.exit("long exit", from_entry="long", limit=targetvalue_long_1 + 10000, stop=price_stop_long)
if strategy.position_size < 0
    strategy.exit("short exit", from_entry="short", limit=targetvalue_short_1 - 10000, stop=price_stop_short)

// =============================================================================
// PLOTS
// =============================================================================
plot(BBbasisL, "BB Basis")
p2 = plot(BBlower, "BB Lower")
p1 = plot(BBupper, "BB Upper")
fill(p1, p2)
plot(price_stop_long  > 0 ? price_stop_long : na,              "SL Long",      color.red,  style=plot.style_linebr)
plot(price_stop_long  > 0 ? targetvalue_long_1 : na,           "Target Long",  color.aqua, style=plot.style_linebr)
plot(price_stop_short < 10000000.0 ? price_stop_short : na,    "SL Short",     color.red,  style=plot.style_linebr)
plot(price_stop_short < 10000000.0 ? targetvalue_short_1 : na, "Target Short", color.aqua, style=plot.style_linebr)
plotchar(strategy.opentrades, "opentrades", "", location.top)
'''


NAS100 = [("D", "configs/nas100usd_oanda_d_D_trained.json", "NAS100_Daily.pine"),
          ("H4", "configs/nas100usd_oanda_h4_H4_trained.json", "NAS100_4h.pine"),
          ("H1", "configs/nas100usd_oanda_h1_H1_trained.json", "NAS100_1h.pine"),
          ("M15", "configs/nas100usd_oanda_m15_M15_trained.json", "NAS100_15m.pine")]

#: Measured out-of-sample results, keyed by (SYMBOL, timeframe). Keyed on the
#: symbol too because an earlier version keyed on timeframe alone, which would
#: have stamped the NAS100 verdict onto a GOLD 15m script -- the same class of
#: mistake as the ladder-mode bug: a report describing something other than
#: what it labels.
OOS_NOTE = {
    ("NAS100", "D"): [
        "in-sample Sharpe 1.33, maxDD -9.7%  ->  UNSEEN 2023-26: Sharpe -0.83, maxDD -67.2%",
        "2012-14 Sharpe -0.43. 11 trades in the post window. FAILS.",
        "Buy-and-hold NAS100 over the same window: Sharpe 1.14, maxDD -22.9%."],
    ("NAS100", "H4"): [
        "in-sample Sharpe 1.71, maxDD -17.8% ->  UNSEEN 2023-26: Sharpe 0.84, maxDD -60.1%",
        "2012-14 Sharpe 0.12, 2005-11 CAGR -0.03%. FAILS.",
        "Buy-and-hold NAS100 over the same window: Sharpe 1.14, maxDD -22.9%."],
    ("NAS100", "H1"): [
        "in-sample Sharpe 1.12, maxDD -24.3% ->  UNSEEN 2023-26: Sharpe 1.02, maxDD -43.0%",
        "2012-14 Sharpe -0.36, 2005-11 Sharpe -0.90. FAILS.",
        "Buy-and-hold NAS100 over the same window: Sharpe 1.14, maxDD -22.9%."],
    ("NAS100", "M15"): [
        "in-sample Sharpe 1.02, maxDD -43.3% ->  UNSEEN 2023-26: Sharpe 1.16, maxDD -54.5%",
        "Clears Sharpe 0.8 on both unseen windows, but on -43% and -54% drawdowns",
        "and CAGR swinging 7.71 -> 66.86 between them. Stable Sharpe, unstable risk."],
    ("GOLD", "M15"): [
        "THE ONE THAT HELD UP. Sharpe by era, trained on 2013-2023 only:",
        "  2006-2012 UNSEEN   97 trades   Sharpe 0.81   CAGR 3.41%   maxDD  -5.1%",
        "  2013-2023 train   145 trades   Sharpe 0.97   CAGR 4.51%   maxDD  -6.8%",
        "  2024-2026 UNSEEN   31 trades   Sharpe 0.94   CAGR 5.01%   maxDD -11.9%",
        "In-sample is barely better than out-of-sample, which is what NOT being",
        "overfitted looks like. Every other config here collapsed (PF 2.18 -> 0.93).",
        "CAVEATS: gold-specific -- on nine other markets it ranked 27th percentile",
        "or worse except EURUSD/GBPUSD, which pass on percentile but return ~0%/yr.",
        "Only 31 trades in the 2024-26 window. Returns are small: 3.4-5.0%/yr",
        "against cash at 2.34%. It loses heavily to buying and holding gold."],
}


def note_for(symbol: str, tf: str, custom: str | None = None) -> str:
    if custom:
        lines = [custom]
    elif (symbol.upper(), tf) in OOS_NOTE:
        lines = OOS_NOTE[(symbol.upper(), tf)]
    else:
        return ""
    body = "\n".join(f"//   {ln}" for ln in lines)
    return ("// OUT-OF-SAMPLE RESULT -- READ BEFORE TRADING THIS\n"
            f"{body}\n//\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config")
    ap.add_argument("--tf")
    ap.add_argument("--symbol", default="NAS100")
    ap.add_argument("--out")
    ap.add_argument("--all-nas100", action="store_true")
    ap.add_argument("--note", help="override the out-of-sample header comment")
    a = ap.parse_args()

    jobs = ([(tf, cfg, out) for tf, cfg, out in NAS100] if a.all_nas100
            else [(a.tf, a.config, a.out)])
    if not a.all_nas100 and not (a.tf and a.config and a.out):
        raise SystemExit("pass --config/--tf/--out, or --all-nas100")

    for tf, cfgp, out in jobs:
        c = json.load(open(cfgp))
        need, driver = required_lookback(c)
        txt = render(c, tf, a.symbol, note_for(a.symbol, tf, a.note))
        open(out, "w").write(txt)
        flag = "  !! EXCEEDS 5000" if need > PINE_MAX_BARS_BACK else ""
        print(f"  wrote {out:<22}{len(txt.splitlines()):>4} lines   "
              f"max_bars_back {min(max(500, need + 50), PINE_MAX_BARS_BACK):>5}"
              f"  (driver {driver} = {need}){flag}")


if __name__ == "__main__":
    main()
