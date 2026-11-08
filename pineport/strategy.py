"""Python port of the Pine v5 strategy "RSI Boll Squeeze Strategy" (Gold 1hr New).

This is a *faithful* translation, not a cleaned-up reimplementation. Several
constructs in the original behave differently from what their names suggest;
each is reproduced exactly and annotated with a ``QUIRK`` comment so the port
can be verified against TradingView before anything is changed. ``QUIRKS.md``
collects them with the reasoning.

Structure:
  * :class:`Params` -- every ``input()`` from the Pine source, same defaults.
  * :func:`compute_indicators` -- the position-independent series, vectorised.
  * :func:`run_strategy` -- the position-dependent stop ladder and order
    submission, bar by bar, because it cannot be vectorised honestly.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

import pine_ta as ta
from broker import BrokerConfig, PineBroker
from data import security_lookahead_off


# ==========================================================================
# inputs
# ==========================================================================

@dataclass
class Params:
    """Every ``input()`` in the Pine script, with the script's own defaults."""

    # -- risk / sizing
    risk_percent: float = 1.0
    #: divisor in the Pine sizing formula: ceil(cashRisk / (50 * pointvalue))
    size_divisor: float = 50.0
    #: "divisor" reproduces the original hardcoded 50; "stop_distance" divides
    #: by close * sl_percent_long / 100, which is scale-free. Must match the
    #: Pine script -- they diverge on equity, and therefore on qty, otherwise.
    size_mode: str = "divisor"

    # -- RSI
    rsi_length_long: int = 1
    rsi_length_short: int = 5
    #: Allow the entry crossovers to coincide within N bars instead of
    #: demanding the same bar. 0 = original behaviour, bar-for-bar identical.
    #: See the `_tol` helper in compute_indicators for the measurement that
    #: motivated it (46.7% trade reproducibility across data vendors).
    trigger_tolerance: int = 0
    #: Use STATE tests (`RSI > level`, `close < band`) instead of crossovers.
    #: Defaults False so existing configs are unchanged. See compute_indicators
    #: for why a config trained under one is meaningless under the other.
    rsi_state: bool = False
    bb_state: bool = False
    rsi_oversold: float = 29.0       # long trigger level (crossover)
    rsi_overbought: float = 20.0     # short trigger level (crossunder)

    # -- fast/slow SMAs (named LSMA/SSMA in the source but they are ta.sma)
    lsma_length_long: int = 2
    lsma_length_short: int = 1
    ssma_length_long: int = 26
    ssma_length_short: int = 2

    # -- ADX
    adx_len: int = 6
    adx_smooth: int = 20
    adx_threshold: float = 23.0

    # -- higher-timeframe trend
    bullish_sma: int = 20
    htf: str = "4h"

    # -- volatility gate
    atr_long: int = 5
    vol_long: int = 60
    # The 15m version gates each direction with its OWN ATR pair
    # (long ATR(3) vs SMA(7), short ATR(39) vs SMA(24)), so the short gate
    # can no longer share the long one.
    atr_short: int = 5
    vol_short: int = 60

    # -- stop shaping
    flex_up: float = 0.95
    flex_down: float = 0.95
    gap_down: float = 0.995
    gap_up: float = 0.995
    stopvalue_short_seed: float = 1_000_000.0
    stopvalue_long_seed: float = 0.0
    profit_line_up: float = 1.0
    profit_line_down: float = 1.0
    trace_line_up: float = 0.001
    trace_line_down: float = 0.001
    mark_up: float = 190.0
    lock_profit_up: float = 170.0
    mark_down: float = 10_000.0
    lock_profit_down: float = 10_000.0
    range_long: float = 750.0
    range_short: float = 10_000.0
    ladder_steps: int = 5            # k = 0..4 in the source

    # -- squeeze
    bb_length_l: int = 3
    bb_length_s: int = 3
    bb_mult: float = 2.0             # QUIRK: declared but never used
    kc_length_l: int = 76
    kc_length_s: int = 942
    kc_mult: float = 2.5
    long_val: float = 0.0
    short_val: float = 960.0
    use_true_range: bool = True

    # -- exit sizing
    sl_percent_long: float = 2.7
    limit_percent_long: float = 6.7
    r_ratio_long: float = 3.0
    sl_percent_short: float = 3.3
    limit_percent_short: float = 1.0
    r_ratio_short: float = 3.0

    # -- entry Bollinger bands
    bb_period_long: int = 15
    bb_stdev_long: float = 2.1
    bb_period_short: int = 111
    bb_stdev_short: float = 1.6

    # -- entry trigger toggles, for decomposing where the edge actually lives.
    #    The long entry is a conjunction of three crossovers plus four filters;
    #    without these it is impossible to ask which component carries the
    #    information and which is along for the ride.
    use_bb_trigger: bool = True       # crossover(close, BBlower)
    use_sma_trigger: bool = True
    #: the `(SSMAS < SSMAL)` leg of the short entry
    use_sma_trigger_short: bool = True      # crossover(sma(close,1), sma(close,2))
    use_rsi_trigger: bool = True      # crossover(rsi(close,1), 29) -- redundant

    #: Replace the original short entry with a true mirror of the long entry.
    #:
    #: The original short leg is not a mirror and cannot fire: it asks for
    #: RSI(5) below 20 (a sharp 5-bar selloff) at the same instant price crosses
    #: DOWN through the upper Bollinger band (price extended upward). Measured
    #: over 124,450 bars those two co-occur 32 times, all four conditions 19
    #: times, and zero times once sqzDown is included.
    #:
    #: The mirror is defined entirely by symmetry with the long side -- same
    #: band parameters, same SMA pair, same linreg threshold sign-flipped, same
    #: three filters with the macro one inverted. No free parameters, nothing
    #: fitted.
    mirror_short: bool = False

    #: Gate the short entry on a bearish regime -- 4H close BELOW its SMA, and
    #: (when the rate filter is active) the real yield ABOVE its average.
    #: The original short leg had no regime filter at all, which is why its
    #: trades fired throughout a 980% bull market and produced a -30% drawdown.
    short_regime_filter: bool = False

    # -- cross-market confirmation (see PREREGISTRATION.md)
    #: "off"     -- current logic, macro filter on XAUUSD only            (H0)
    #: "replace" -- macro filter computed on the auxiliary series instead (H1)
    #: "both"    -- require macro bullish on BOTH series                  (H2)
    #: The filter form is deliberately identical to the existing one (4H close
    #: above a 20-period 4H SMA); only the series it is computed on changes, so
    #: the comparison isolates the denominator rather than the filter design.
    cross_market_mode: str = "off"

    # -- real-yield regime filter (see PREREGISTRATION.md, test 2)
    #: "off" / "replace" / "both", mirroring cross_market_mode.
    #: Gold rises when real yields FALL, so the bullish condition is the
    #: inverse of the price version: yield BELOW its own moving average.
    rate_filter_mode: str = "off"
    #: Lookback in trading days for the real-yield moving average. Set to 20 to
    #: mirror `bullish_sma`; deliberately not tuned.
    rate_sma_days: int = 20

    # -- state vs event triggers (4H "new" variant) --------------------------
    #: Use `LSMAS > LSMAL` (a STATE) instead of `crossover(LSMAS, LSMAL)`.
    #: States are markedly more robust to feed and alignment differences than
    #: crossovers -- see NEXT_STEPS.md. Same for the short SMA pair.
    lsma_state: bool = False
    ssma_state: bool = False

    #: Second, independent ADX for the short leg, tested with `<` not `>`
    #: (the short side wants a WEAK trend, the long side a strong one).
    use_adx_filter_short: bool = False
    adx_len_short: int = 50
    adx_smooth_short: int = 1
    adx_threshold_short: float = 30.0

    # -- trend filters introduced in the 4H variant --------------------------
    #: close > sma(close, sma_long)
    use_sma_filter: bool = False
    #: close > ema(close, ema_uses_sma_length ? sma_long : ema_long)
    use_ema_filter: bool = False
    sma_long: int = 40
    ema_long: int = 50
    #: The 4H script writes `ta.ema(price, SMALong)` -- it passes the SMA length
    #: to the EMA, leaving its own `EMALong` input dead. Reproduced faithfully;
    #: set False to use `ema_long` as the input name implies.
    ema_uses_sma_length: bool = True

    # -- filter toggles (all True == faithful to the original)
    use_macro_filter: bool = True
    use_adx_filter: bool = True
    use_volatility_filter: bool = True
    use_volatility_filter_short: bool = False
    use_squeeze_filter: bool = True
    allow_longs: bool = True
    allow_shorts: bool = True

    # -- repairs, all OFF by default so the baseline stays faithful.
    #    See QUIRKS.md; each one is switched on individually in variants.py so
    #    its effect can be attributed rather than guessed at.
    #: use ta.tr() for the Keltner range instead of the raw high (QUIRK 2)
    fix_keltner_range: bool = False
    #: ratchet the long stop from price_stop_long[1] rather than 0.0 (QUIRK 5)
    fix_long_stop_ratchet: bool = False
    #: place the take-profit at the target instead of target +/- 10000 (QUIRK 6)
    enable_take_profit: bool = False
    #: drop the duplicated RSI(1) trigger, keeping the SMA crossover (QUIRK 7)
    drop_duplicate_long_trigger: bool = False
    # -- scale-invariant ladder and stop (QUIRK 8) -----------------------
    #: How the profit ladder rungs are measured.
    #:   "dollars" -- the original: markUp/lockProfitUp/range are absolute USD
    #:   "atr"     -- multiples of ATR at the entry bar
    #:   "percent" -- percentages of the entry price
    #: The dollar rungs are the reason 2006-2022 is not a fair test: +190 was
    #: 22x ATR at 2024-26 prices but 63x ATR in 2006-10, so the ladder was
    #: effectively unreachable in the early history.
    #: Disable the markUp/markDown profit ladder entirely. The rungs then never
    #: fire and the stop is driven purely by the percentage trail, the ratchet
    #: and profitLockin. Measured to fire on only ~30 of 138 trades -- and on
    #: exactly the big winners -- so switching it off is a real simplification,
    #: not a cosmetic one.
    use_ladder: bool = True
    ladder_mode: str = "dollars"
    atr_ladder_len: int = 14
    #: ATR multiples, calibrated so the 2024-26 behaviour matches the dollar
    #: original (median ATR(14) was 8.59 there: 190/8.59 = 22.1, etc.)
    mark_up_atr: float = 22.1
    lock_profit_up_atr: float = 19.8
    range_long_atr: float = 87.4
    mark_down_atr: float = 1164.0
    lock_profit_down_atr: float = 1164.0
    range_short_atr: float = 1164.0
    #: percentages of entry price, calibrated the same way (190/3216 = 5.9%)
    mark_up_pct: float = 5.91
    lock_profit_up_pct: float = 5.29
    range_long_pct: float = 23.32
    mark_down_pct: float = 311.0
    lock_profit_down_pct: float = 311.0
    range_short_pct: float = 311.0

    #: Trailing stop distance. "percent" is the original 2.7%/3.3%; "atr" uses
    #: a multiple of the CURRENT bar's ATR, so the stop widens in volatile
    #: markets and tightens in quiet ones.
    stop_mode: str = "percent"
    #: calibrated to the original at 2024-26 levels: 2.7% of 3216 = 10.1x ATR
    sl_atr_long: float = 10.1
    sl_atr_short: float = 12.3

    #: Treat `sqzOn` as True instead of computing it, while keeping the live
    #: `valL > longVal` / `valS < shortVal` tests. `sqzOn` is provably true on
    #: every warmed-up bar (QUIRK 2), so this changes no signal -- but it drops
    #: the long side's warm-up from 942 bars to 76, which is what makes short
    #: TradingView chart exports verifiable. Not a behaviour change; a warm-up
    #: shortcut whose safety follows from QUIRK 2.
    assume_squeeze_on: bool = False

    def with_(self, **kwargs) -> "Params":
        return replace(self, **kwargs)


# ==========================================================================
# indicators
# ==========================================================================

def compute_indicators(df: pd.DataFrame, p: Params,
                       aux: pd.DataFrame | None = None,
                       rates: pd.Series | None = None) -> pd.DataFrame:
    """All series that do not depend on position state.

    Kept separate from the bar loop so the optimiser can cache them across
    parameter sets that leave them unchanged, and so each one can be unit
    tested against TradingView independently.
    """
    close, high, low, vol = df["close"], df["high"], df["low"], df["volume"]
    out = pd.DataFrame(index=df.index)

    # -- RSI ---------------------------------------------------------------
    out["rsi_long"] = ta.rsi(close, p.rsi_length_long)
    out["rsi_short"] = ta.rsi(close, p.rsi_length_short)

    # -- SMA pairs ---------------------------------------------------------
    lsma_l = ta.sma(close, p.lsma_length_long)
    lsma_s = ta.sma(close, p.lsma_length_short)
    ssma_l = ta.sma(close, p.ssma_length_long)
    ssma_s = ta.sma(close, p.ssma_length_short)

    # -- ADX ---------------------------------------------------------------
    _plus, _minus, adx = ta.dmi(high, low, close, p.adx_len, p.adx_smooth)
    out["adx"] = adx
    out["trend_active"] = adx > p.adx_threshold

    # -- higher-timeframe trend -------------------------------------------
    htf_close = security_lookahead_off(df, p.htf, lambda h: h["close"])
    htf_sma = security_lookahead_off(df, p.htf, lambda h: ta.sma(h["close"], p.bullish_sma))
    out["htf_close"] = htf_close
    out["htf_sma"] = htf_sma
    out["macro_bullish"] = htf_close > htf_sma

    # -- cross-market confirmation (gold priced in a second currency) -------
    # Same filter shape as above, computed on the auxiliary series and then
    # reindexed onto this frame's bars. Reindexing uses ffill so a missing
    # auxiliary bar carries the last KNOWN value forward rather than peeking at
    # a future one; bars before the auxiliary series starts stay NaN and are
    # treated as "not confirmed".
    if p.cross_market_mode != "off":
        if aux is None:
            raise ValueError(
                f"cross_market_mode={p.cross_market_mode!r} needs an auxiliary "
                f"price frame; pass aux= to compute_indicators/run_strategy")
        aux_close = security_lookahead_off(aux, p.htf, lambda h: h["close"])
        aux_sma = security_lookahead_off(
            aux, p.htf, lambda h: ta.sma(h["close"], p.bullish_sma))
        aux_bull = (aux_close > aux_sma).reindex(df.index, method="ffill")
        out["aux_macro_bullish"] = aux_bull.fillna(False)

        if p.cross_market_mode == "replace":
            out["macro_bullish"] = out["aux_macro_bullish"]
        elif p.cross_market_mode == "both":
            out["macro_bullish"] = out["macro_bullish"] & out["aux_macro_bullish"]
        else:
            raise ValueError(f"unknown cross_market_mode {p.cross_market_mode!r}")

    # -- real-yield regime filter -----------------------------------------
    # Gold's opportunity cost is the real rate, so the gold-bullish state is a
    # FALLING real yield -- the inverse of the price filter's "above its MA".
    #
    # The series is daily and already lagged one business day by
    # fetch_fred.load_daily_series(). Reindexing with method="ffill" carries the
    # last KNOWN observation forward onto hourly bars; it cannot reach forward
    # to an observation that had not been published.
    if p.rate_filter_mode != "off":
        if rates is None:
            raise ValueError(
                f"rate_filter_mode={p.rate_filter_mode!r} needs a `rates` "
                f"series; fetch one with fetch_fred.py and pass rates=")
        r = pd.Series(rates).sort_index()
        r_ma = r.rolling(p.rate_sma_days, min_periods=p.rate_sma_days).mean()
        falling = (r < r_ma).reindex(df.index, method="ffill")
        out["rates_bullish"] = falling.fillna(False)

        if p.rate_filter_mode == "replace":
            out["macro_bullish"] = out["rates_bullish"]
        elif p.rate_filter_mode == "both":
            out["macro_bullish"] = out["macro_bullish"] & out["rates_bullish"]
        else:
            raise ValueError(f"unknown rate_filter_mode {p.rate_filter_mode!r}")

    # -- volatility gate ---------------------------------------------------
    atr_v = ta.atr(high, low, close, p.atr_long)
    out["atr"] = atr_v
    out["volatility_gate"] = atr_v > ta.sma(atr_v, p.vol_long)
    # Both gates test ATR ABOVE its own average -- the 15m source uses `>` for
    # the short gate too, despite the name suggesting otherwise.
    atr_s = (atr_v if (p.atr_short == p.atr_long)
             else ta.atr(high, low, close, p.atr_short))
    out["volatility_gate_short"] = atr_s > ta.sma(atr_s, p.vol_short)
    # Separate, longer ATR for sizing the ladder and the optional ATR stop.
    # Kept distinct from the 5-period gate ATR so the two can be tuned apart.
    out["atr_ladder"] = ta.atr(high, low, close, p.atr_ladder_len)

    # -- squeeze -----------------------------------------------------------
    # QUIRK 1: the band width uses `multKC` (2.5), not `mult` (2.0). `mult` is
    # declared and never referenced, so changing "BB MultFactor" in TradingView
    # does nothing at all.
    basis_l = ta.vwma(close, vol, p.bb_length_l)
    dev_l = p.kc_mult * ta.stdev(close, p.bb_length_l)
    upper_bb = basis_l + dev_l

    basis_s = ta.vwma(close, vol, p.bb_length_s)
    dev_s = p.kc_mult * ta.stdev(close, p.bb_length_s)
    lower_bb = basis_s - dev_s

    # QUIRK 2: `range1 = useTrueRange ? high : (high - low)`. The true-range
    # branch returns the raw HIGH, not ta.tr(). A Keltner channel built on
    # price levels rather than ranges sits thousands of points away from price,
    # which makes the squeeze test below degenerate. Preserved deliberately.
    if p.fix_keltner_range:
        range1 = ta.true_range(high, low, close) if p.use_true_range else (high - low)
    else:
        range1 = high if p.use_true_range else (high - low)

    ma_l = ta.vwma(close, vol, p.kc_length_l)
    ma_s = ta.vwma(close, vol, p.kc_length_s)
    rangema_l = ta.vwma(range1, vol, p.kc_length_l)
    rangema_s = ta.vwma(range1, vol, p.kc_length_s)

    upper_kc = ma_l + rangema_l * p.kc_mult
    lower_kc = ma_s - rangema_s * p.kc_mult

    sqz_on = (lower_bb > lower_kc) & (upper_bb < upper_kc)
    out["upper_bb"], out["lower_bb"] = upper_bb, lower_bb
    out["upper_kc"], out["lower_kc"] = upper_kc, lower_kc
    out["sqz_on"] = sqz_on

    val_l = ta.linreg(
        close - ((ta.highest(high, p.kc_length_l) + ta.lowest(low, p.kc_length_l)) / 2.0
                 + ta.vwma(close, vol, p.kc_length_l)) / 2.0,
        p.kc_length_l, 0,
    )
    val_s = ta.linreg(
        close - ((ta.highest(high, p.kc_length_s) + ta.lowest(low, p.kc_length_s)) / 2.0
                 + ta.vwma(close, vol, p.kc_length_s)) / 2.0,
        p.kc_length_s, 0,
    )
    out["val_l"], out["val_s"] = val_l, val_s
    # `sqzOn` compares a price-scale Keltner channel against a price-hugging
    # Bollinger band, so it is true on every warmed-up bar (QUIRK 2). The linreg
    # tests beside it are NOT inert: `val_l > 0` rejects roughly 40% of long
    # signals. Only the Keltner/Bollinger comparison is dead.
    sqz_on_effective = pd.Series(True, index=df.index) if p.assume_squeeze_on else sqz_on
    out["sqz_up"] = sqz_on_effective & (val_l > p.long_val)
    out["sqz_down"] = sqz_on_effective & (val_s < p.short_val)

    # -- entry Bollinger bands --------------------------------------------
    # bb_basis_long is plotted by the original ("Bollinger Bands SMA Basis
    # Line"), so it is exported and can be diffed against TradingView directly.
    bb_basis_l = ta.vwma(close, vol, p.bb_period_long)
    out["bb_basis_long"] = bb_basis_l
    out["bb_lower"] = bb_basis_l - p.bb_stdev_long * ta.stdev(close, p.bb_period_long)
    bb_basis_s = ta.vwma(close, vol, p.bb_period_short)
    out["bb_basis_short"] = bb_basis_s
    out["bb_upper"] = bb_basis_s + p.bb_stdev_short * ta.stdev(close, p.bb_period_short)

    # -- entry trigger components -----------------------------------------
    def _tol(s: pd.Series) -> pd.Series:
        """"fired on this bar" -> "fired within the last trigger_tolerance bars".

        WHY, and why NOT the obvious alternative. feed_compare put trade
        reproducibility at 46.7% between two vendors whose returns correlate
        at 0.976 -- fewer than half the trades survive a change of data
        supplier, so they will not survive a broker's fills either.

        The cause is not that the triggers are instants. It is that FOUR
        instants must land on the SAME BAR. A 0.03% price difference moves one
        of them a bar, and the conjunction silently evaporates.

        Replacing crossovers with plain states (`RSI < 40` for `RSI crosses
        40`) fixes reproducibility and destroys the strategy, because a state
        is common where a crossover is rare: the conjunction stops being
        selective and entries land on the first bar all four happen to be
        true. Dave tried exactly that on the live script and the results
        collapsed.

        This keeps each trigger as rare as it was and only relaxes the
        COINCIDENCE requirement. tolerance=0 reproduces the original bar-for-bar.
        """
        n = int(getattr(p, "trigger_tolerance", 0) or 0)
        if n <= 0:
            return s
        return s.rolling(n + 1, min_periods=1).max().fillna(0).astype(bool)

    # STATE forms. `rsi_state` turns "RSI crosses above 40" into "RSI > 40",
    # `bb_state` turns "close crosses the lower band" into "close < lower".
    #
    # These are NOT interchangeable and must be trained separately. A crossover
    # is rare; a state is common, so the four-way conjunction stops being
    # selective and entries land on the first bar everything happens to be
    # true. On gold that collapsed the strategy. They are here so the port can
    # follow the Pine script when it uses > / <, not because they are a
    # drop-in improvement -- a config built for one is meaningless under the
    # other.
    out["x_rsi_long"] = ((out["rsi_long"] > p.rsi_oversold) if p.rsi_state
                         else _tol(ta.crossover(out["rsi_long"], p.rsi_oversold)))
    out["x_rsi_short"] = ((out["rsi_short"] < p.rsi_overbought) if p.rsi_state
                          else _tol(ta.crossunder(out["rsi_short"], p.rsi_overbought)))
    out["x_bb_long"] = ((close < out["bb_lower"]) if p.bb_state
                        else _tol(ta.crossover(close, out["bb_lower"])))
    out["x_bb_short"] = ((close > out["bb_upper"]) if p.bb_state
                         else _tol(ta.crossunder(close, out["bb_upper"])))
    # State forms are already true over a range, so tolerance does not apply.
    out["x_sma_long"] = ((lsma_s > lsma_l) if p.lsma_state
                         else _tol(ta.crossover(lsma_s, lsma_l)))
    out["x_sma_short"] = ((ssma_s < ssma_l) if p.ssma_state
                          else _tol(ta.crossunder(ssma_s, ssma_l)))

    if p.use_adx_filter_short:
        _, _, adx_s = ta.dmi(high, low, close, p.adx_len_short, p.adx_smooth_short)
        out["adx_short"] = adx_s
        out["trend_active_short"] = adx_s < p.adx_threshold_short

    # -- assembled signals -------------------------------------------------
    # QUIRK 7: `crossover(rsi(close,1), 29)` and `crossover(sma(close,1),
    # sma(close,2))` are the same test written two ways -- both mean "an up bar
    # following a non-up bar". Two of the three long triggers are one condition.
    long_cond = pd.Series(True, index=df.index)
    if p.use_rsi_trigger and not p.drop_duplicate_long_trigger:
        long_cond &= out["x_rsi_long"]
    if p.use_bb_trigger:
        long_cond &= out["x_bb_long"]
    if p.use_sma_trigger:
        long_cond &= out["x_sma_long"]
    if p.use_squeeze_filter:
        long_cond &= out["sqz_up"]
    if p.use_macro_filter:
        long_cond &= out["macro_bullish"]
    if p.use_adx_filter:
        long_cond &= out["trend_active"]
    if p.use_volatility_filter:
        long_cond &= out["volatility_gate"]
    if p.use_sma_filter:
        out["sma_filter"] = close > ta.sma(close, p.sma_long)
        long_cond &= out["sma_filter"]
    if p.use_ema_filter:
        n = p.sma_long if p.ema_uses_sma_length else p.ema_long
        out["ema_filter"] = close > ta.ema(close, n)
        long_cond &= out["ema_filter"]

    # QUIRK 3: the short leg has NO macro, ADX or volatility filter in the
    # original. The gating is entirely asymmetric between the two directions.
    if p.mirror_short:
        # A true mirror of the long entry, built by symmetry alone.
        bb_upper_mirror = bb_basis_l + p.bb_stdev_long * ta.stdev(
            close, p.bb_period_long)
        out["bb_upper_mirror"] = bb_upper_mirror
        out["x_bb_short_mirror"] = ta.crossunder(close, bb_upper_mirror)
        out["x_sma_short_mirror"] = ta.crossunder(lsma_s, lsma_l)
        out["sqz_down_mirror"] = sqz_on_effective & (val_l < p.long_val)
        out["macro_bearish"] = htf_close < htf_sma

        short_cond = out["x_bb_short_mirror"] & out["x_sma_short_mirror"]
        if p.use_squeeze_filter:
            short_cond &= out["sqz_down_mirror"]
        if p.use_macro_filter:
            short_cond &= out["macro_bearish"]
        if p.use_adx_filter:
            short_cond &= out["trend_active"]
        if p.use_volatility_filter:
            short_cond &= out["volatility_gate"]
    else:
        short_cond = out["x_rsi_short"] & out["x_bb_short"]
        # The SSMA leg is `(SSMAS < SSMAL)` in Pine. It is a separate toggle
        # because the newer scripts comment it out of shortSignal entirely,
        # and a grid search over its two lengths needs to switch it back on.
        if p.use_sma_trigger_short:
            short_cond &= out["x_sma_short"]
        if p.use_squeeze_filter:
            short_cond &= out["sqz_down"]

    if p.use_adx_filter_short:
        short_cond &= out["trend_active_short"]

    if p.use_volatility_filter_short:
        short_cond &= out["volatility_gate_short"]

    if p.short_regime_filter:
        # Mirror of the long-side regime test, not a new indicator: bearish is
        # simply the complement of the bullish condition already computed.
        out["macro_bearish"] = htf_close < htf_sma
        short_cond &= out["macro_bearish"]
        if p.rate_filter_mode != "off":
            # rates_bearish = real yield ABOVE its average = gold-unfriendly.
            out["rates_bearish"] = ~out["rates_bullish"].astype(bool)
            short_cond &= out["rates_bearish"]

    # `if (not na(vrsiL))` in the source
    long_cond &= out["rsi_long"].notna()
    if not p.mirror_short:
        # `if (not na(vrsiS))` in the source. The mirror does not use RSI(5),
        # so the guard would be gating on an unrelated series.
        short_cond &= out["rsi_short"].notna()

    out["long_signal"] = long_cond.fillna(False) & p.allow_longs
    out["short_signal"] = short_cond.fillna(False) & p.allow_shorts
    return out


# ==========================================================================
# execution
# ==========================================================================

@dataclass
class RunResult:
    trades: pd.DataFrame
    equity: pd.Series
    position: pd.Series
    indicators: pd.DataFrame
    diagnostics: pd.DataFrame
    params: Params
    broker: PineBroker


def run_strategy(df: pd.DataFrame, p: Params | None = None,
                 broker_cfg: BrokerConfig | None = None,
                 indicators: pd.DataFrame | None = None,
                 signal_filter: np.ndarray | None = None,
                 aux: pd.DataFrame | None = None,
                 rates: pd.Series | None = None) -> RunResult:
    """Run the ported strategy bar by bar.

    Parameters
    ----------
    signal_filter:
        Optional boolean array aligned to ``df``. Where it is False, entry
        signals are suppressed. This is the hook the ML overlay uses; leave it
        as None for the faithful baseline.
    """
    p = p or Params()
    ind = (compute_indicators(df, p, aux, rates) if indicators is None
           else indicators)
    broker = PineBroker(broker_cfg or BrokerConfig())

    n = len(df)
    idx = df.index
    o_arr = df["open"].to_numpy(float)
    h_arr = df["high"].to_numpy(float)
    l_arr = df["low"].to_numpy(float)
    c_arr = df["close"].to_numpy(float)

    atr_ladder = ind["atr_ladder"].to_numpy(float)
    long_sig = ind["long_signal"].to_numpy(bool)
    short_sig = ind["short_signal"].to_numpy(bool)
    if signal_filter is not None:
        allowed = np.asarray(signal_filter, dtype=bool)
        long_sig = long_sig & allowed
        short_sig = short_sig & allowed

    # Previous-bar values needed to evaluate Pine crossovers on series that
    # only exist while a position is open.
    prev_close = np.nan
    prev_target_long = 0.0
    prev_target_short = 0.0
    prev_price_stop_long = 0.0
    prev_price_stop_short = 10_000_000.0
    prev_ladder_long = np.full(p.ladder_steps, np.nan)
    prev_ladder_short = np.full(p.ladder_steps, np.nan)

    # `*_plot` entries mirror what the original's plot() calls draw, which is
    # the *expression*, evaluated before the later `:= 0` / `:= 1e8` resets.
    # The `*_used` entries are the values that actually reach math.max/min.
    # They differ, and the chart only ever showed you the first kind.
    diag = {k: np.full(n, np.nan) for k in
            ("price_stop_long", "price_stop_short", "target_long",
             "target_short", "position", "equity", "qty",
             "profit_lockin_up_plot", "profit_lockin_down_plot",
             "profit_lockin_up_used", "profit_lockin_down_used")}

    for i in range(n):
        ts = idx[i]
        o, h, l, c = o_arr[i], h_arr[i], l_arr[i], c_arr[i]

        # --- broker acts during the bar, before the script body runs ------
        broker.process_bar(i, ts, o, h, l, c)
        broker.mark_to_market(c)

        # ================= Pine script body, at bar close =================
        pos = broker.position_size
        initial_entry = broker.opentrades_entry_price()

        # Re-initialised on every bar: these are plain (non-`var`) declarations
        # in the source, so nothing carries over except via the `[1]` history.
        price_stop_long = 0.0
        price_stop_short = 10_000_000.0
        target_long = 0.0
        target_short = 0.0
        # QUIRK 4: `stopvalue_long_1` / `stopvalue_short_1` are declared with
        # input.float() and then reassigned with `:=`. Pine re-runs the whole
        # body per bar, so they reset to the INPUT DEFAULT every bar rather
        # than persisting. The "stop value Long/Short" inputs are therefore
        # per-bar seed values, not stops.
        stopvalue_long_1 = p.stopvalue_long_seed
        stopvalue_short_1 = p.stopvalue_short_seed
        profit_lockin_up = initial_entry
        profit_lockin_down = initial_entry

        # Ladder rung sizes. In "atr" mode the unit is frozen at the entry bar,
        # matching the original's semantics -- the rungs are fixed relative to
        # the entry price and must not drift once the trade is open.
        mark_up, lock_up, range_l, mark_dn, lock_dn, range_s = (
            p.mark_up, p.lock_profit_up, p.range_long,
            p.mark_down, p.lock_profit_down, p.range_short)
        if p.ladder_mode != "dollars" and broker.open_trade is not None:
            if p.ladder_mode == "atr":
                unit = atr_ladder[broker.open_trade.entry_bar]
                mults = (p.mark_up_atr, p.lock_profit_up_atr, p.range_long_atr,
                         p.mark_down_atr, p.lock_profit_down_atr, p.range_short_atr)
            else:                                    # "percent" of entry price
                unit = initial_entry / 100.0
                mults = (p.mark_up_pct, p.lock_profit_up_pct, p.range_long_pct,
                         p.mark_down_pct, p.lock_profit_down_pct, p.range_short_pct)
            if np.isfinite(unit):
                mark_up, lock_up, range_l, mark_dn, lock_dn, range_s = (
                    m * unit for m in mults)

        # Only materialise the ladders while a position is open. Allocating two
        # arrays on every one of ~124k bars, 95% of which are flat, dominated
        # the loop cost and bought nothing.
        if np.isfinite(initial_entry):
            ladder_long = np.empty(p.ladder_steps)
            ladder_short = np.empty(p.ladder_steps)
            for k in range(p.ladder_steps):
                ladder_long[k] = initial_entry + (mark_up + range_l * k)
                ladder_short[k] = initial_entry - (mark_dn + range_s * k)
        else:
            ladder_long = ladder_short = _NAN_LADDER[:p.ladder_steps]

        # ---------------- long stop ladder --------------------------------
        if pos > 0:
            entry_bar = broker.open_trade.entry_bar
            entry_bar_close = c_arr[entry_bar]      # Pine: close[since_entry_long]

            if p.stop_mode == "atr" and np.isfinite(atr_ladder[i]):
                stopvalue_long = c - p.sl_atr_long * atr_ladder[i]
            else:
                stopvalue_long = c - c * p.sl_percent_long / 100.0
            target_long = entry_bar_close + entry_bar_close * (
                p.limit_percent_long / 100.0) * p.r_ratio_long
            profit_lockin_up = ((target_long - initial_entry) / p.profit_line_up
                                + initial_entry)

            if _crossed_over(c, prev_close, target_long, prev_target_long):
                stopvalue_long = target_long * p.flex_up

            # QUIRK 5 (material): the source writes
            #     stopvalue_long_1 := price_stop_long + ((close - price_stop_long) * gapUp)
            # referencing `price_stop_long` on the CURRENT bar, which has just
            # been re-initialised to 0.0 and not yet assigned. So it collapses
            # to `close * gapUp` -- a fixed 0.5% trailing stop from the close,
            # not the intended ratchet from the previous stop. The short side
            # of the same block correctly uses `price_stop_short[1]`. This
            # asymmetry is a bug in the original; it is reproduced here so the
            # port matches TradingView, and `fix_long_stop_ratchet` in
            # variants.py shows what it does when corrected.
            ratchet_base = prev_price_stop_long if p.fix_long_stop_ratchet else 0.0
            if c > target_long:
                stopvalue_long_1 = ratchet_base + (c - ratchet_base) * p.gap_up
            if c > profit_lockin_up:
                stopvalue_long_1 = ratchet_base + (c - ratchet_base) * (
                    p.gap_up - p.trace_line_up)

            if p.use_ladder:
                for k in range(p.ladder_steps):
                    if _crossed_over(c, prev_close, ladder_long[k], prev_ladder_long[k]):
                        stopvalue_long_1 = initial_entry + (lock_up + range_l * k)

            diag["profit_lockin_up_plot"][i] = profit_lockin_up
            if c < profit_lockin_up:
                profit_lockin_up = 0.0

            price_stop_long = max(stopvalue_long, prev_price_stop_long,
                                  stopvalue_long_1, profit_lockin_up)
            diag["profit_lockin_up_used"][i] = profit_lockin_up

        # ---------------- short stop ladder -------------------------------
        if pos < 0:
            entry_bar = broker.open_trade.entry_bar
            entry_bar_close = c_arr[entry_bar]      # Pine: close[since_entry_short]

            if p.stop_mode == "atr" and np.isfinite(atr_ladder[i]):
                stopvalue_short = c + p.sl_atr_short * atr_ladder[i]
            else:
                stopvalue_short = c + c * p.sl_percent_short / 100.0
            target_short = entry_bar_close - entry_bar_close * (
                p.limit_percent_short / 100.0) * p.r_ratio_short
            profit_lockin_down = initial_entry - (
                (initial_entry - target_short) / p.profit_line_down)

            if _crossed_under(c, prev_close, target_short, prev_target_short):
                stopvalue_short = target_short + (1.0 - p.flex_down) * target_short

            if c < target_short:
                stopvalue_short_1 = prev_price_stop_short - (
                    (prev_price_stop_short - c) * p.gap_down)
            if c < profit_lockin_down:
                stopvalue_short_1 = prev_price_stop_short - (
                    (prev_price_stop_short - c) * (p.gap_down - p.trace_line_down))

            for k in range(p.ladder_steps):
                if _crossed_under(c, prev_close, ladder_short[k], prev_ladder_short[k]):
                    stopvalue_short_1 = initial_entry - (lock_dn + range_s * k)

            diag["profit_lockin_down_plot"][i] = profit_lockin_down
            if c > profit_lockin_down:
                profit_lockin_down = 100_000_000.0

            price_stop_short = min(stopvalue_short, prev_price_stop_short,
                                   stopvalue_short_1, profit_lockin_down)
            diag["profit_lockin_down_used"][i] = profit_lockin_down

        # ---------------- entries -----------------------------------------
        equity = broker.equity
        cash_risk = equity * p.risk_percent / 100.0
        if p.size_mode == "stop_distance":
            # Scale-free. `size_divisor` was a dollar constant that happened to
            # approximate the stop distance when gold was ~1,500 (1500 * 2.94%
            # = 44 ~ 50). At 4,565 the real stop distance is 134, so the fixed
            # divisor sized ~3x too large and asked for positions worth 107% of
            # the account. Dividing by the actual stop delivers the stated risk
            # at any price level.
            unit = c * p.sl_percent_long / 100.0
            qty = max(np.ceil(cash_risk / (unit * broker.cfg.point_value)), 1.0)
        else:
            qty = max(np.ceil(cash_risk /
                              (p.size_divisor * broker.cfg.point_value)), 0.0)

        if long_sig[i]:
            broker.submit_entry(1, qty)
        elif short_sig[i]:
            broker.submit_entry(-1, qty)
        else:
            broker.cancel_entry()

        # ---------------- protective orders for the next bar --------------
        # QUIRK 6: the limit legs are `target + 10000` (long) and
        # `target - 10000` (short) -- displaced so far that they can never
        # fill. Every exit in this strategy is a stop exit; the take-profit is
        # decorative. Passed through unchanged so the port matches.
        tp_offset = 0.0 if p.enable_take_profit else 10_000.0
        if pos > 0:
            broker.set_exit(stop=price_stop_long, limit=target_long + tp_offset)
        elif pos < 0:
            broker.set_exit(stop=price_stop_short, limit=target_short - tp_offset)
        else:
            broker.clear_exit()

        # ---------------- carry history -----------------------------------
        diag["price_stop_long"][i] = price_stop_long
        diag["price_stop_short"][i] = price_stop_short
        diag["target_long"][i] = target_long
        diag["target_short"][i] = target_short
        diag["position"][i] = pos
        diag["equity"][i] = equity
        diag["qty"][i] = qty

        prev_close = c
        prev_target_long = target_long
        prev_target_short = target_short
        prev_price_stop_long = price_stop_long
        prev_price_stop_short = price_stop_short
        prev_ladder_long = ladder_long
        prev_ladder_short = ladder_short

    broker.force_close(n - 1, idx[-1], c_arr[-1])

    return RunResult(
        trades=broker.trades_frame(),
        equity=pd.Series(broker.equity_curve, index=idx[:len(broker.equity_curve)]),
        position=pd.Series(broker.position_history, index=idx[:len(broker.position_history)]),
        indicators=ind,
        diagnostics=pd.DataFrame(diag, index=idx),
        params=p,
        broker=broker,
    )


#: Shared all-NaN ladder used on flat bars. Read-only by convention: the loop
#: never writes into a ladder it did not allocate itself.
_NAN_LADDER = np.full(64, np.nan)


def _crossed_over(a: float, a_prev: float, b: float, b_prev: float) -> bool:
    """Pine ``ta.crossover`` evaluated on scalars; NaN anywhere means False."""
    if not (np.isfinite(a) and np.isfinite(a_prev)
            and np.isfinite(b) and np.isfinite(b_prev)):
        return False
    return a > b and a_prev <= b_prev


def _crossed_under(a: float, a_prev: float, b: float, b_prev: float) -> bool:
    """Pine ``ta.crossunder`` evaluated on scalars; NaN anywhere means False."""
    if not (np.isfinite(a) and np.isfinite(a_prev)
            and np.isfinite(b) and np.isfinite(b_prev)):
        return False
    return a < b and a_prev >= b_prev
