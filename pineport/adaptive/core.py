"""
core.py — shared machinery for the adaptive-lookback and chart-shape study.

Execution model, applied identically everywhere:
    signal is computed from bar t's CLOSE
    the position is held over bar t+1
    returns are simple daily returns of the close
    cost is charged on |change in position|
Nothing here reads a value that would not have been known at the signal bar.
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

MARKETS = ["audusd", "bcousd", "de30eur", "eurusd", "gbpusd", "nas100usd",
           "spx500usd", "usdjpy", "xagusd", "xauusd", "xcuusd"]

ERAS = {
    "E1_2005_2012": ("2005-01-01", "2012-03-31"),
    "E2_2012_2019": ("2012-04-01", "2019-06-30"),
    "E3_2019_2026": ("2019-07-01", "2026-08-31"),
}

# log-spaced crossover grid; s* = log2(slow)
FAST = [2, 4, 8, 16, 32, 64]
SLOW = [8, 16, 32, 64, 128, 256]
PAIRS = [(f, s) for f in FAST for s in SLOW if s >= 2 * f]
CENTRE_PAIR = (16, 128)          # geometric centre of the grid — the fixed benchmark


def load(mkt: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(DATA, f"{mkt}_d1.csv"), parse_dates=["time"])
    df = df.set_index("time").sort_index()
    df["ret"] = df["close"].pct_change()
    return df


def ppy(x) -> float:
    """
    Bars per year implied by the ACTUAL index — never assume 252.

    R4: the daily feed is FX/CFD, which trades ~257 days/year, not the 252 of
    the US equity calendar. Before the make_daily.py fix it was 296.5 and
    varied 251.6-317.1 across markets, so a hard-coded sqrt(252) understated
    every Sharpe by ~8% and len/252 understated every ann_ret by ~15%.
    Deriving it from the index is correct whatever the feed turns out to be.
    """
    idx = x.index if hasattr(x, "index") else x
    idx = pd.DatetimeIndex(idx)
    if len(idx) < 2:
        return np.nan
    yrs = (idx[-1] - idx[0]).days / 365.25
    return len(idx) / yrs if yrs > 0 else np.nan


def era_of(idx: pd.DatetimeIndex) -> pd.Series:
    out = pd.Series(index=idx, dtype=object)
    for name, (a, b) in ERAS.items():
        m = (idx >= pd.Timestamp(a, tz="UTC")) & (idx <= pd.Timestamp(b, tz="UTC"))
        out[m] = name
    return out


# ---------------------------------------------------------------------------
# crossover grid
# ---------------------------------------------------------------------------

def pair_positions(close: pd.Series) -> dict[tuple[int, int], pd.Series]:
    """position in {-1,+1} for every (fast,slow) pair, already lagged one bar."""
    smas = {n: close.rolling(n).mean() for n in sorted(set(FAST + SLOW))}
    out = {}
    for f, s in PAIRS:
        pos = np.sign(smas[f] - smas[s])
        out[(f, s)] = pos.shift(1)      # decided at t's close, held over t+1
    return out


def pair_returns(df: pd.DataFrame, cost_bps: float = 1.0) -> pd.DataFrame:
    """daily net strategy return for every pair, as a DataFrame."""
    pos = pair_positions(df["close"])
    cols = {}
    for k, p in pos.items():
        turn = p.diff().abs().fillna(0.0)
        cols[k] = p * df["ret"] - turn * cost_bps / 1e4
    return pd.DataFrame(cols, index=df.index)


# ---------------------------------------------------------------------------
# state variables — all causal, all known at the bar they are stamped on
# ---------------------------------------------------------------------------

def efficiency_ratio(close: pd.Series, n: int = 63) -> pd.Series:
    net = (close - close.shift(n)).abs()
    path = close.diff().abs().rolling(n).sum()
    return net / path.replace(0, np.nan)


def realised_vol(ret: pd.Series, n: int = 63) -> pd.Series:
    return ret.rolling(n).std() * np.sqrt(ppy(ret))


def vol_of_vol(ret: pd.Series, n: int = 63) -> pd.Series:
    return ret.rolling(21).std().rolling(n).std() * np.sqrt(ppy(ret))


def variance_ratio(ret: pd.Series, q: int = 5, n: int = 63) -> pd.Series:
    v1 = ret.rolling(n).var()
    vq = ret.rolling(q).sum().rolling(n).var()
    return vq / (q * v1.replace(0, np.nan))


def hurst(close: pd.Series, n: int = 63, ks=(1, 2, 3, 5, 8)) -> pd.Series:
    lr = np.log(close).diff()
    logk = np.log(np.array(ks, dtype=float))
    cols = [np.log(lr.rolling(k).sum().rolling(n).std()) for k in ks]
    M = pd.concat(cols, axis=1)
    xc = logk - logk.mean()
    denom = (xc ** 2).sum()
    return (M.sub(M.mean(axis=1), axis=0) * xc).sum(axis=1) / denom


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - df["close"].shift()).abs(),
                    (df["low"] - df["close"].shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * pd.Series(plus, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr
    mdi = 100 * pd.Series(minus, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean()


def dominant_cycle(close: pd.Series, detrend: int = 50, win: int = 252) -> pd.Series:
    """zero-crossing period of the detrended series — a robust cycle estimator."""
    osc = close - close.rolling(detrend).mean()
    sign = np.sign(osc)
    cross = (sign != sign.shift(1)) & sign.notna() & sign.shift(1).notna()
    n_cross = cross.rolling(win).sum()
    return (2.0 * win / n_cross.replace(0, np.nan)).clip(upper=win)


def autocorr_1(ret: pd.Series, n: int = 63) -> pd.Series:
    return ret.rolling(n).corr(ret.shift(1))


def state_frame(df: pd.DataFrame) -> pd.DataFrame:
    ret = df["ret"]
    st = pd.DataFrame(index=df.index)
    st["efficiency_ratio"] = efficiency_ratio(df["close"])
    st["realised_vol"] = realised_vol(ret)
    st["vol_of_vol"] = vol_of_vol(ret)
    st["variance_ratio"] = variance_ratio(ret)
    st["hurst"] = hurst(df["close"])
    st["adx"] = adx(df)
    st["dominant_cycle"] = dominant_cycle(df["close"])
    st["autocorr_1"] = autocorr_1(ret)
    st["abs_autocorr_1"] = autocorr_1(ret).abs()
    return st


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------

def sharpe(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) < 30 or r.std() == 0:
        return np.nan
    return float(r.mean() / r.std() * np.sqrt(ppy(r)))


def ann_return(r: pd.Series) -> float:
    """Geometric annual return on the series' own calendar."""
    r = r.dropna()
    if len(r) < 30:
        return np.nan
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    return float((1 + r).prod() ** (1 / yrs) - 1) if yrs > 0 else np.nan


def years(x) -> float:
    """Calendar years spanned by the index — never len/252."""
    idx = x.index if hasattr(x, "index") else x
    idx = pd.DatetimeIndex(idx)
    return (idx[-1] - idx[0]).days / 365.25 if len(idx) >= 2 else np.nan


def ann_vol(r: pd.Series) -> float:
    r = r.dropna()
    return float(r.std() * np.sqrt(ppy(r))) if len(r) >= 30 else np.nan


def spearman(a, b) -> float:
    s = pd.concat([pd.Series(a).reset_index(drop=True),
                   pd.Series(b).reset_index(drop=True)], axis=1).dropna()
    if len(s) < 8:
        return np.nan
    x = s.iloc[:, 0].rank()
    y = s.iloc[:, 1].rank()
    if x.std() == 0 or y.std() == 0:
        return np.nan
    return float(x.corr(y))          # Pearson on ranks == Spearman, no scipy


if __name__ == "__main__":
    d = load("xauusd")
    print(d.shape, d.index[0].date(), "->", d.index[-1].date())
    print("pairs:", len(PAIRS))
    st = state_frame(d)
    print(st.dropna().describe().T[["mean", "std", "min", "max"]].round(3))
