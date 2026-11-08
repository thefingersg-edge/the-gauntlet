"""Synthetic gold-like hourly OHLCV, for testing without a data feed.

Not a substitute for real data in a backtest -- purely so the engine, the
indicators and the order model can be exercised deterministically, including on
a machine with no network access.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_bars(n: int = 6000, start_price: float = 2400.0, seed: int = 7,
              start: str = "2024-01-01", freq: str = "1h",
              drift_per_bar: float = 0.00004,
              vol_per_bar: float = 0.0022) -> pd.DataFrame:
    """Generate a random-walk OHLCV series with volatility clustering.

    The GARCH-ish volatility term matters: a constant-volatility walk would make
    the ATR gate in the strategy trivially true or false, which would hide bugs.
    """
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start=start, periods=n, freq=freq, tz="UTC")

    vol = np.empty(n)
    vol[0] = vol_per_bar
    shock = rng.standard_normal(n)
    for i in range(1, n):
        vol[i] = np.sqrt(0.00000002 + 0.06 * (vol[i - 1] * shock[i - 1]) ** 2
                         + 0.92 * vol[i - 1] ** 2)

    rets = drift_per_bar + vol * shock
    close = start_price * np.exp(np.cumsum(rets))

    open_ = np.empty(n)
    open_[0] = start_price
    open_[1:] = close[:-1] * (1.0 + 0.15 * vol[1:] * rng.standard_normal(n - 1))

    wick = np.abs(rng.standard_normal(n)) * vol * close * 0.8
    high = np.maximum(open_, close) + wick
    low = np.minimum(open_, close) - np.abs(rng.standard_normal(n)) * vol * close * 0.8
    low = np.minimum(low, np.minimum(open_, close))
    high = np.maximum(high, np.maximum(open_, close))

    volume = np.maximum(1.0, rng.lognormal(mean=8.0, sigma=0.7, size=n).round())

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )
