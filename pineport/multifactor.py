#!/usr/bin/env python3
"""Port of the SPX500 Multi-Factor Strategy, with the risk-block bugs fixed.

A DIFFERENT strategy from the RSI/Boll/squeeze family in strategy.py. Six
factors vote, the weighted score crosses a threshold, and a bracket of
stop/target/trailing-stop manages the position. It reuses pine_ta, PineBroker,
metrics and data, so it inherits the execution model that was verified
trade-for-trade against TradingView rather than a second guess at one.

FOUR BUGS IN THE PINE SOURCE, FIXED HERE. Each is implemented the corrected
way, and `bug_compat` reproduces the original behaviour so the cost of each can
be measured rather than asserted.

1. SHORTS HAD NO STOP WHEN TRAILING WAS ON. The long branch passed
   `stop=longStop`; the short branch passed only `limit` and the trail. Since
   `useTrailing` defaulted true, every short ran with no hard stop and a trail
   that cannot arm until the trade is already profitable. A short that went
   against you from the open had nothing beneath it.

2. trail_points / trail_offset ARE IN TICKS, NOT PRICE. Pine's signature says
   "profit specified in ticks". The script passed `atr * trailATR`, a price
   quantity. At SPX500's 0.1 mintick a 50-point intended trail became 50 ticks
   = 5.0 points -- roughly 10x too tight, which is what makes a trailing stop
   look broken.

3. THE STOP FLOATED WITH CURRENT ATR. `longStop = position_avg_price -
   atr * stopATR` was recomputed every bar from the CURRENT atr, and
   strategy.exit was re-issued every bar. So the stop widened when volatility
   expanded -- it retreated as the trade went against you. Here the ATR is
   captured once on the entry bar and held.

4. SLIPPAGE WAS UNDER-CHARGED. `slippage=1` is one tick = 0.1 points. The
   measured OANDA SPX500 spread is 0.50 round trip, 0.25 per fill -- about
   2.5 ticks. Cost is a broker-config input here, so it is set by the caller
   and 0.25 is the measured value.

The trailing stop implemented here: once price has moved `trail_atr` x ATR in
favour, the stop follows the best close by that distance, and NEVER retreats.
The hard stop stays live underneath throughout.
"""
from __future__ import annotations

import dataclasses as dc
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from broker import BrokerConfig, PineBroker          # noqa: E402
import pine_ta as ta                                 # noqa: E402


@dc.dataclass
class MFParams:
    trade_longs: bool = True
    trade_shorts: bool = True
    # -- trend
    fast_len: int = 50
    slow_len: int = 200
    use_trend: bool = True
    # -- momentum
    short_mom_len: int = 20
    long_mom_len: int = 120
    use_momentum: bool = True
    # -- breakout
    breakout_len: int = 50
    use_breakout: bool = True
    # -- volatility regime (context for mean reversion, not a vote)
    atr_len: int = 14
    vol_lookback: int = 100
    high_vol_pct: float = 70.0
    low_vol_pct: float = 30.0
    use_volatility: bool = True
    # -- mean reversion
    rsi_len: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    z_len: int = 20
    z_threshold: float = 2.0
    use_mean_reversion: bool = True
    # -- volume
    volume_len: int = 20
    volume_mult: float = 1.2
    use_volume: bool = True
    # -- weights
    trend_w: float = 1.0
    momentum_w: float = 1.0
    breakout_w: float = 1.0
    volume_w: float = 1.0
    meanrev_w: float = 1.0
    entry_threshold: float = 1.0
    # -- risk
    stop_atr: float = 2.0
    target_atr: float = 4.0
    use_trailing: bool = True
    trail_atr: float = 2.5
    use_reversal_exit: bool = True
    wait_for_signal_reset: bool = True
    #: Reproduce the Pine bugs instead of the fixes, to measure what each cost.
    #: "none" | "no_short_stop" | "floating_stop" | "tight_trail" | "all"
    bug_compat: str = "none"


def percentrank(s: pd.Series, length: int) -> pd.Series:
    """Pine ta.percentrank: % of the previous `length` values <= the current one.

    Vectorised over the offsets rather than rolling.apply -- 100 array
    comparisons instead of 500,000 Python calls.
    """
    x = s.to_numpy(float)
    cnt = np.zeros(len(x))
    for k in range(1, length + 1):
        prev = np.concatenate([np.full(k, np.nan), x[:-k]])
        cnt += (prev <= x)
    out = 100.0 * cnt / length
    out[:length] = np.nan
    return pd.Series(out, index=s.index)


def compute_factors(df: pd.DataFrame, p: MFParams) -> pd.DataFrame:
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
    out = pd.DataFrame(index=df.index)

    ema_f, ema_s = ta.ema(c, p.fast_len), ta.ema(c, p.slow_len)
    trend = np.where((c > ema_s) & (ema_f > ema_s), 1,
                     np.where((c < ema_s) & (ema_f < ema_s), -1, 0))

    sm = c / c.shift(p.short_mom_len) - 1
    lm = c / c.shift(p.long_mom_len) - 1
    mom = np.where((sm > 0) & (lm > 0), 1, np.where((sm < 0) & (lm < 0), -1, 0))

    prev_hi = ta.highest(h, p.breakout_len).shift(1)
    prev_lo = ta.lowest(l, p.breakout_len).shift(1)
    brk = np.where(c > prev_hi, 1, np.where(c < prev_lo, -1, 0))

    atr = ta.atr(h, l, c, p.atr_len)
    out["atr"] = atr
    vol_pr = percentrank(atr / c * 100, p.vol_lookback)
    high_vol = vol_pr >= p.high_vol_pct
    low_vol = vol_pr <= p.low_vol_pct
    out["high_vol"], out["low_vol"] = high_vol.fillna(False), low_vol.fillna(False)

    rsi = ta.rsi(c, p.rsi_len)
    basis, sd = ta.sma(c, p.z_len), ta.stdev(c, p.z_len)
    z = ((c - basis) / sd).where(sd != 0, 0.0)
    ok = (~p.use_volatility) | out["low_vol"]
    mr = np.where(ok & (rsi < p.rsi_oversold) & (z < -p.z_threshold), 1,
                  np.where(ok & (rsi > p.rsi_overbought) & (z > p.z_threshold), -1, 0))

    avg_v = ta.sma(v, p.volume_len)
    rel_v = (v / avg_v).where(avg_v > 0, 1.0)
    vol_vote = np.where((rel_v >= p.volume_mult) & (c > df["open"]), 1,
                        np.where((rel_v >= p.volume_mult) & (c < df["open"]), -1, 0))

    score = (trend * p.trend_w * p.use_trend
             + mom * p.momentum_w * p.use_momentum
             + brk * p.breakout_w * p.use_breakout
             + vol_vote * p.volume_w * p.use_volume
             + mr * p.meanrev_w * p.use_mean_reversion)
    out["score"] = score
    out["long_signal"] = p.trade_longs & (score >= p.entry_threshold)
    out["short_signal"] = p.trade_shorts & (score <= -p.entry_threshold)
    return out


@dc.dataclass
class MFResult:
    equity: pd.Series
    trades: pd.DataFrame
    factors: pd.DataFrame


def run_multifactor(df: pd.DataFrame, p: MFParams | None = None,
                    broker_cfg: BrokerConfig | None = None) -> MFResult:
    p = p or MFParams()
    f = compute_factors(df, p)
    br = PineBroker(broker_cfg or BrokerConfig())

    idx = df.index
    o = df["open"].to_numpy(float); hi = df["high"].to_numpy(float)
    lo = df["low"].to_numpy(float); cl = df["close"].to_numpy(float)
    atr = f["atr"].to_numpy(float)
    score = f["score"].to_numpy(float)
    lsig = f["long_signal"].to_numpy(bool)
    ssig = f["short_signal"].to_numpy(bool)

    bug_all = p.bug_compat == "all"
    no_short_stop = bug_all or p.bug_compat == "no_short_stop"
    floating = bug_all or p.bug_compat == "floating_stop"
    tight = bug_all or p.bug_compat == "tight_trail"
    MINTICK = 0.1                     # SPX500 on OANDA

    entry_atr = np.nan
    best = np.nan                     # best close seen since entry
    trail_armed = False
    prev_dir = 0
    pending_close = False             # reversal exit, filled at the next open

    for i in range(len(df)):
        br.process_bar(i, idx[i], o[i], hi[i], lo[i], cl[i])
        # A reversal flagged on the previous close flattens at THIS open, which
        # is how the broker fills every other market order. The broker rejects a
        # zero-qty entry, so `submit_entry(0, 0)` is not a close -- it is a
        # silent no-op, and using it would have left reversal exits unexecuted.
        if pending_close and br.position_size != 0:
            # _close_position rather than force_close: the latter hardcodes the
            # reason "end_of_data", which mislabelled 1,309 reversal exits as
            # end-of-run closes and made the exit mix unreadable. Reaching for
            # one underscore method is better than editing broker.py, which is
            # the component verified trade-for-trade against TradingView.
            br._close_position(i, idx[i], o[i], "reversal")
            br.clear_exit()
        pending_close = False
        d = int(np.sign(br.position_size))

        if d != 0 and prev_dir != d:                  # a new position opened
            # BUG 3 FIX: capture the ATR once, on the entry bar.
            entry_atr = atr[i]
            best = cl[i]
            trail_armed = False
        if d == 0:
            entry_atr, best, trail_armed = np.nan, np.nan, False
        prev_dir = d

        if d != 0 and np.isfinite(entry_atr):
            ref = br.entry_price
            a = atr[i] if floating else entry_atr     # BUG 3: float vs fixed
            stop_d, targ_d = a * p.stop_atr, a * p.target_atr
            trail_d = a * p.trail_atr
            if tight:
                # BUG 2: a price quantity passed to a ticks parameter.
                trail_d = trail_d * MINTICK
            best = max(best, cl[i]) if d > 0 else min(best, cl[i])

            if d > 0:
                hard, targ = ref - stop_d, ref + targ_d
                eff = hard
                if p.use_trailing:
                    if cl[i] >= ref + trail_d:
                        trail_armed = True
                    if trail_armed:
                        eff = max(hard, best - trail_d)
                br.set_exit(stop=eff, limit=targ)
            else:
                hard, targ = ref + stop_d, ref - targ_d
                # BUG 1: the original omitted the short stop entirely when
                # trailing was on, leaving the position unprotected.
                eff = np.inf if (no_short_stop and p.use_trailing) else hard
                if p.use_trailing:
                    if cl[i] <= ref - trail_d:
                        trail_armed = True
                    if trail_armed:
                        t = best + trail_d
                        eff = t if not np.isfinite(eff) else min(eff, t)
                br.set_exit(stop=None if not np.isfinite(eff) else eff, limit=targ)

            if p.use_reversal_exit and ((d > 0 and score[i] < 0)
                                        or (d < 0 and score[i] > 0)):
                pending_close = True

        # entries, evaluated at the close like process_orders_on_close
        if br.position_size <= 0 and lsig[i] and not np.isnan(atr[i]):
            fresh = (not p.wait_for_signal_reset) or br.position_size < 0 \
                    or (i > 0 and not lsig[i - 1])
            if fresh:
                qty = max(1.0, np.floor(br.equity * 0.10 / cl[i]))
                br.submit_entry(1, qty)
        elif br.position_size >= 0 and ssig[i] and not np.isnan(atr[i]):
            fresh = (not p.wait_for_signal_reset) or br.position_size > 0 \
                    or (i > 0 and not ssig[i - 1])
            if fresh:
                qty = max(1.0, np.floor(br.equity * 0.10 / cl[i]))
                br.submit_entry(-1, qty)

        br.mark_to_market(cl[i])

    if br.position_size != 0:
        br.force_close(len(df) - 1, idx[-1], cl[-1])
    return MFResult(pd.Series(br.equity_curve, index=idx[:len(br.equity_curve)]),
                    br.trades_frame(), f)
