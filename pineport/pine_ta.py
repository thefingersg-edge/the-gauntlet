"""Pine Script v5 ``ta.*`` equivalents, implemented to match TradingView bar-for-bar.

Design rule: where TradingView's implementation differs from the textbook
definition, TradingView wins. The point of this module is reproducing a
TradingView backtest, not being "correct" in the abstract.

Notable fidelity points:
  * ``rma`` is seeded with the SMA of the first full window (not with the first
    value, and not with an exponential ramp-up). This is what Pine does and it
    shifts every Wilder-smoothed series (RSI, ATR, DMI) by a visible amount.
  * ``stdev`` is the *population* standard deviation (ddof=0).
  * ``vwma`` is ``sma(src*volume, n) / sma(volume, n)`` -- so a feed with zero
    volume produces NaN, not a plain SMA. See ``vwma``'s ``zero_volume`` note.
  * ``dmi`` applies Pine's ``fixnan`` (forward fill) to +DI/-DI before the ADX
    smoothing step.
  * Warm-up periods return NaN rather than partial-window values.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = [
    "change", "sma", "rma", "ema", "stdev", "vwma", "true_range", "atr", "rsi",
    "dmi", "linreg", "highest", "lowest", "crossover", "crossunder",
    "barssince", "fixnan", "nz",
]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _as_series(x, like: pd.Series | None = None) -> pd.Series:
    if isinstance(x, pd.Series):
        return x.astype(float)
    if like is not None:
        return pd.Series(np.full(len(like), float(x)), index=like.index)
    return pd.Series(np.asarray(x, dtype=float))


def nz(series: pd.Series, replacement=0.0) -> pd.Series:
    """Pine ``nz`` -- replace na with a value (default 0)."""
    return series.fillna(replacement)


def fixnan(series: pd.Series) -> pd.Series:
    """Pine ``fixnan`` -- carry the last non-na value forward over na values."""
    return series.ffill()


def change(series: pd.Series, length: int = 1) -> pd.Series:
    """Pine ``ta.change`` -- src - src[length]."""
    return series.astype(float).diff(length)


# --------------------------------------------------------------------------
# moving averages
# --------------------------------------------------------------------------

def sma(series: pd.Series, length: int) -> pd.Series:
    """Pine ``ta.sma``. NaN until a full window is available."""
    length = int(length)
    if length <= 1:
        return series.astype(float).copy()
    return series.astype(float).rolling(length, min_periods=length).mean()


def ema(series: pd.Series, length: int) -> pd.Series:
    """Pine ``ta.ema`` -- alpha = 2/(n+1), seeded with the first SMA window."""
    return _recursive_smooth(series, 2.0 / (int(length) + 1.0), int(length))


def rma(series: pd.Series, length: int) -> pd.Series:
    """Pine ``ta.rma`` (Wilder's smoothing) -- alpha = 1/n, seeded with SMA(n).

    Pine's definition::

        alpha = 1 / length
        sum = 0.0
        sum := na(sum[1]) ? ta.sma(src, length) : alpha * src + (1 - alpha) * nz(sum[1])

    The SMA seed matters: seeding with the first observation instead (as many
    Python TA libraries do) leaves a persistent offset in RSI and ATR that never
    fully decays for long lookbacks.
    """
    return _recursive_smooth(series, 1.0 / int(length), int(length))


def _recursive_smooth(series: pd.Series, alpha: float, seed_length: int) -> pd.Series:
    src = series.astype(float)
    values = src.to_numpy(dtype=float)
    n = values.size
    out = np.full(n, np.nan)

    if seed_length <= 0 or n == 0:
        return pd.Series(out, index=src.index)

    seed = src.rolling(seed_length, min_periods=seed_length).mean().to_numpy(dtype=float)
    start_candidates = np.flatnonzero(~np.isnan(seed))
    if start_candidates.size == 0:
        return pd.Series(out, index=src.index)

    start = int(start_candidates[0])
    out[start] = seed[start]
    prev = out[start]
    for i in range(start + 1, n):
        x = values[i]
        if np.isnan(x):
            # Pine propagates the previous accumulator rather than poisoning it.
            out[i] = prev
            continue
        prev = alpha * x + (1.0 - alpha) * prev
        out[i] = prev
    return pd.Series(out, index=src.index)


def stdev(series: pd.Series, length: int) -> pd.Series:
    """Pine ``ta.stdev`` -- population (biased, ddof=0) standard deviation."""
    length = int(length)
    return series.astype(float).rolling(length, min_periods=length).std(ddof=0)


def vwma(series: pd.Series, volume: pd.Series, length: int) -> pd.Series:
    """Pine ``ta.vwma`` = ``sma(src * volume, n) / sma(volume, n)``.

    If the data feed reports zero volume for every bar (yfinance does this for
    ``XAUUSD=X``) the denominator is zero and the result is NaN for the entire
    series -- which silently disables every VWMA-derived signal. ``load_ohlcv``
    checks for this and can substitute unit volume; it never happens silently.
    """
    length = int(length)
    src = series.astype(float)
    vol = volume.astype(float)
    num = (src * vol).rolling(length, min_periods=length).sum()
    den = vol.rolling(length, min_periods=length).sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        out = num / den
    return out.replace([np.inf, -np.inf], np.nan)


# --------------------------------------------------------------------------
# range / volatility
# --------------------------------------------------------------------------

def true_range(high: pd.Series, low: pd.Series, close: pd.Series,
               handle_na: bool = True) -> pd.Series:
    """Pine ``ta.tr(handle_na)``.

    With ``handle_na=True`` the first bar's true range is ``high - low`` rather
    than NaN, which is what ``ta.atr`` uses internally.
    """
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    if handle_na:
        tr = tr.where(prev_close.notna(), high - low)
    else:
        tr = tr.where(prev_close.notna(), np.nan)
    return tr


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.Series:
    """Pine ``ta.atr`` = ``rma(tr(true), n)``."""
    return rma(true_range(high, low, close, handle_na=True), length)


# --------------------------------------------------------------------------
# oscillators
# --------------------------------------------------------------------------

def rsi(series: pd.Series, length: int) -> pd.Series:
    """Pine ``ta.rsi``.

    Pine computes::

        u = max(src - src[1], 0)
        d = max(src[1] - src, 0)
        rs = rma(u, n) / rma(d, n)
        res = 100 - 100 / (1 + rs)

    At ``length=1`` this degenerates: alpha = 1, so rma(x, 1) == x, giving RSI
    of exactly 100 on any up bar and exactly 0 on any down bar. On an unchanged
    bar both sides are zero and the result is NaN (0/0), which Pine treats as
    ``na``. This is preserved rather than papered over, because the strategy
    that uses it depends on the resulting crossover pattern.
    """
    src = series.astype(float)
    delta = src.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)

    roll_up = rma(up, length)
    roll_down = rma(down, length)

    with np.errstate(divide="ignore", invalid="ignore"):
        rs = roll_up / roll_down
    out = 100.0 - 100.0 / (1.0 + rs)
    # up>0, down==0 -> rs=inf -> 100.  up==0, down==0 -> rs=nan -> nan (Pine na).
    out = out.where(~((roll_down == 0) & (roll_up > 0)), 100.0)
    out = out.where(~((roll_up == 0) & (roll_down > 0)), 0.0)
    return out


def dmi(high: pd.Series, low: pd.Series, close: pd.Series,
        di_length: int, adx_smoothing: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Pine ``ta.dmi(diLength, adxSmoothing)`` -> (+DI, -DI, ADX).

    Mirrors the reference implementation in the Pine docs, including the
    ``fixnan`` forward-fill on +DI/-DI and the ``sum == 0 ? 1 : sum`` guard.
    """
    up = change(high)
    down = -change(low)

    plus_dm = pd.Series(
        np.where((up > down) & (up > 0), up.fillna(0.0), 0.0), index=high.index
    ).where(up.notna(), np.nan)
    minus_dm = pd.Series(
        np.where((down > up) & (down > 0), down.fillna(0.0), 0.0), index=high.index
    ).where(down.notna(), np.nan)

    trur = rma(true_range(high, low, close, handle_na=True), di_length)

    with np.errstate(divide="ignore", invalid="ignore"):
        plus = fixnan(100.0 * rma(plus_dm, di_length) / trur)
        minus = fixnan(100.0 * rma(minus_dm, di_length) / trur)

    total = plus + minus
    dx = 100.0 * rma((plus - minus).abs() / total.where(total != 0, 1.0), adx_smoothing)
    return plus, minus, dx


# --------------------------------------------------------------------------
# regression / extremes
# --------------------------------------------------------------------------

def linreg(series: pd.Series, length: int, offset: int = 0) -> pd.Series:
    """Pine ``ta.linreg(source, length, offset)``.

    Fits ``y = a + b*x`` by ordinary least squares over the trailing ``length``
    bars with ``x = 0 .. length-1`` (oldest to newest), then returns
    ``a + b * (length - 1 - offset)``.
    """
    length = int(length)
    offset = int(offset)
    src = series.astype(float)
    y = src.to_numpy(dtype=float)
    n = y.size
    out = np.full(n, np.nan)
    if length <= 1 or n < length:
        return pd.Series(out, index=src.index)

    x = np.arange(length, dtype=float)
    sum_x = x.sum()
    sum_x2 = (x * x).sum()
    denom = length * sum_x2 - sum_x * sum_x
    if denom == 0:
        return pd.Series(out, index=src.index)

    valid = ~np.isnan(y)
    y_filled = np.where(valid, y, 0.0)

    # Rolling sums via cumulative sums (O(n)); rolling sum(x*y) via convolution.
    csum = np.concatenate(([0.0], np.cumsum(y_filled)))
    sum_y = csum[length:] - csum[:-length]

    cvalid = np.concatenate(([0.0], np.cumsum(valid.astype(float))))
    window_valid = (cvalid[length:] - cvalid[:-length]) == length

    # np.convolve reverses the kernel, so pass x reversed to get x ascending
    # (oldest bar weighted 0, newest weighted length-1) within each window.
    sum_xy = np.convolve(y_filled, x[::-1], mode="valid")

    slope = (length * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y / length) - slope * (sum_x / length)
    values = intercept + slope * (length - 1 - offset)

    out[length - 1:] = np.where(window_valid, values, np.nan)
    return pd.Series(out, index=src.index)


def highest(series: pd.Series, length: int) -> pd.Series:
    """Pine ``ta.highest``."""
    length = int(length)
    return series.astype(float).rolling(length, min_periods=length).max()


def lowest(series: pd.Series, length: int) -> pd.Series:
    """Pine ``ta.lowest``."""
    length = int(length)
    return series.astype(float).rolling(length, min_periods=length).min()


# --------------------------------------------------------------------------
# crossings / counters
# --------------------------------------------------------------------------

def crossover(a: pd.Series, b) -> pd.Series:
    """Pine ``ta.crossover(a, b)`` -- ``a > b and a[1] <= b[1]``.

    NaN on either side of either bar yields False, matching Pine's na handling.
    """
    a = a.astype(float)
    b = _as_series(b, like=a)
    return (a > b) & (a.shift(1) <= b.shift(1))


def crossunder(a: pd.Series, b) -> pd.Series:
    """Pine ``ta.crossunder(a, b)`` -- ``a < b and a[1] >= b[1]``."""
    a = a.astype(float)
    b = _as_series(b, like=a)
    return (a < b) & (a.shift(1) >= b.shift(1))


def barssince(condition: pd.Series) -> pd.Series:
    """Pine ``ta.barssince`` -- 0 on the bar the condition is true, NaN before
    the condition has ever been true."""
    cond = condition.fillna(False).astype(bool).to_numpy()
    n = cond.size
    out = np.full(n, np.nan)
    last = -1
    for i in range(n):
        if cond[i]:
            last = i
        if last >= 0:
            out[i] = i - last
    return pd.Series(out, index=condition.index)
