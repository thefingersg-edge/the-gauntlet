#!/usr/bin/env python3
"""Test the widely-used indicators this project never looked at.

Everything examined so far came from one script: SMA, EMA, RSI, Bollinger,
Keltner, ADX/DMI, ATR, linreg. That is a narrow slice of what traders actually
use, so this adds the major families we skipped and puts them through the same
test that separated signal from noise in DESIGN_BRIEF.md:

    does the condition keep the SAME SIGN in every era?

A condition whose edge flips sign between 2006-12, 2013-19 and 2020-26 cannot be
traded forward, however good its backtest. That single filter rejected 14 of 14
price conditions at an 8-day horizon and passed most of them at 3 months, which
is the most useful thing measured in this project.

Implementations are standard textbook forms, written here because pine_ta only
carries what the ported strategy needed.

    python indicator_scan.py                 # daily gold, 3-month horizon
    python indicator_scan.py --horizon 21
    python indicator_scan.py --csv xagusd_oanda_h1.csv
"""
from __future__ import annotations

import argparse
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import _normalise, _read_csv          # noqa: E402

ERAS = [("2006-12", "2006-01-01", "2012-12-31"),
        ("2013-19", "2013-01-01", "2019-12-31"),
        ("2020-26", "2020-01-01", None)]


# ---------------------------------------------------------------- indicators
def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rma(s, n):
    return s.ewm(alpha=1 / n, adjust=False).mean()


def true_range(h, l, c):
    pc = c.shift(1)
    return pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)


def atr(h, l, c, n=14):
    return rma(true_range(h, l, c), n)


def macd(c, fast=12, slow=26, sig=9):
    line = ema(c, fast) - ema(c, slow)
    signal = ema(line, sig)
    return line, signal, line - signal


def stochastic(h, l, c, n=14, d=3):
    ll, hh = l.rolling(n).min(), h.rolling(n).max()
    k = 100 * (c - ll) / (hh - ll)
    return k, k.rolling(d).mean()


def cci(h, l, c, n=20):
    tp = (h + l + c) / 3
    ma = tp.rolling(n).mean()
    md = (tp - ma).abs().rolling(n).mean()
    return (tp - ma) / (0.015 * md)


def williams_r(h, l, c, n=14):
    hh, ll = h.rolling(n).max(), l.rolling(n).min()
    return -100 * (hh - c) / (hh - ll)


def supertrend(h, l, c, n=10, mult=3.0):
    """Popular on TradingView; a banded trend flip around an ATR envelope."""
    hl2 = (h + l) / 2
    a = atr(h, l, c, n)
    up, dn = hl2 - mult * a, hl2 + mult * a
    trend = pd.Series(1, index=c.index)
    for i in range(1, len(c)):
        up.iloc[i] = (max(up.iloc[i], up.iloc[i - 1])
                      if c.iloc[i - 1] > up.iloc[i - 1] else up.iloc[i])
        dn.iloc[i] = (min(dn.iloc[i], dn.iloc[i - 1])
                      if c.iloc[i - 1] < dn.iloc[i - 1] else dn.iloc[i])
        if c.iloc[i] > dn.iloc[i - 1]:
            trend.iloc[i] = 1
        elif c.iloc[i] < up.iloc[i - 1]:
            trend.iloc[i] = -1
        else:
            trend.iloc[i] = trend.iloc[i - 1]
    return trend


def ichimoku(h, l, c):
    conv = (h.rolling(9).max() + l.rolling(9).min()) / 2
    base = (h.rolling(26).max() + l.rolling(26).min()) / 2
    a = ((conv + base) / 2).shift(26)
    b = ((h.rolling(52).max() + l.rolling(52).min()) / 2).shift(26)
    return conv, base, a, b


def aroon(h, l, n=25):
    up = h.rolling(n + 1).apply(lambda x: 100 * (n - (len(x) - 1 - x.argmax())) / n, raw=True)
    dn = l.rolling(n + 1).apply(lambda x: 100 * (n - (len(x) - 1 - x.argmin())) / n, raw=True)
    return up, dn


def vortex(h, l, c, n=14):
    tr = true_range(h, l, c).rolling(n).sum()
    vp = (h - l.shift(1)).abs().rolling(n).sum()
    vm = (l - h.shift(1)).abs().rolling(n).sum()
    return vp / tr, vm / tr


def obv(c, v):
    return (np.sign(c.diff()).fillna(0) * v).cumsum()


def mfi(h, l, c, v, n=14):
    tp = (h + l + c) / 3
    mf = tp * v
    pos = mf.where(tp > tp.shift(1), 0).rolling(n).sum()
    neg = mf.where(tp < tp.shift(1), 0).rolling(n).sum()
    return 100 - 100 / (1 + pos / neg)


def choppiness(h, l, c, n=14):
    tr = true_range(h, l, c).rolling(n).sum()
    rng = h.rolling(n).max() - l.rolling(n).min()
    return 100 * np.log10(tr / rng) / np.log10(n)


def hull(c, n=20):
    half = c.rolling(n // 2).mean() * 2 - c.rolling(n).mean()
    return half.rolling(int(np.sqrt(n))).mean()


def kama(c, n=10, fast=2, slow=30):
    ch = (c - c.shift(n)).abs()
    vol = c.diff().abs().rolling(n).sum()
    sc = (ch / vol * (2 / (fast + 1) - 2 / (slow + 1)) + 2 / (slow + 1)) ** 2
    out = c.copy()
    for i in range(1, len(c)):
        if np.isfinite(sc.iloc[i]):
            out.iloc[i] = out.iloc[i - 1] + sc.iloc[i] * (c.iloc[i] - out.iloc[i - 1])
    return out


def build(d: pd.DataFrame) -> dict:
    o, h, l, c = d["open"], d["high"], d["low"], d["close"]
    v = d["volume"] if "volume" in d else pd.Series(1.0, index=d.index)
    ml, ms, mh = macd(c)
    k, dd = stochastic(h, l, c)
    conv, base, sa, sb = ichimoku(h, l, c)
    au, ad = aroon(h, l)
    vp, vm = vortex(h, l, c)
    ob = obv(c, v)
    return {
        # --- momentum oscillators, never tested here
        "MACD line > signal":      ml > ms,
        "MACD histogram > 0":      mh > 0,
        "MACD line > 0":           ml > 0,
        "Stochastic %K > %D":      k > dd,
        "Stochastic %K < 20":      k < 20,
        "Stochastic %K > 80":      k > 80,
        "CCI(20) > +100":          cci(h, l, c) > 100,
        "CCI(20) < -100":          cci(h, l, c) < -100,
        "CCI(20) > 0":             cci(h, l, c) > 0,
        "Williams %R > -50":       williams_r(h, l, c) > -50,
        # --- trend / breakout systems
        "Supertrend long":         supertrend(h, l, c) > 0,
        "Donchian 20 breakout":    c >= h.rolling(20).max().shift(1),
        "Donchian 55 breakout":    c >= h.rolling(55).max().shift(1),
        "close > Donchian mid20":  c > (h.rolling(20).max() + l.rolling(20).min()) / 2,
        "Ichimoku above cloud":    (c > sa) & (c > sb),
        "Ichimoku conv > base":    conv > base,
        "Aroon up > down":         au > ad,
        "Vortex VI+ > VI-":        vp > vm,
        "close > Hull(20)":        c > hull(c, 20),
        "close > KAMA(10)":        c > kama(c, 10),
        # --- volume
        "OBV > its SMA(20)":       ob > ob.rolling(20).mean(),
        "MFI(14) > 50":            mfi(h, l, c, v) > 50,
        "MFI(14) < 20":            mfi(h, l, c, v) < 20,
        # --- regime
        "Choppiness < 38 (trending)": choppiness(h, l, c) < 38,
        "Choppiness > 62 (ranging)":  choppiness(h, l, c) > 62,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default="xauusd_oanda_m15.csv")
    ap.add_argument("--horizon", type=int, default=63, help="forward bars (daily)")
    args = ap.parse_args()

    raw = _normalise(_read_csv(args.csv))
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in raw:
        agg["volume"] = "sum"
    d = raw.resample("1D").agg(agg).dropna()
    c = d["close"]
    fwd = (c.shift(-args.horizon) / c - 1) * 100
    sigs = build(d)

    print(f"\nUNTESTED INDICATOR FAMILIES -- {os.path.basename(args.csv)}, "
          f"daily bars, {args.horizon}-day forward horizon")
    print("  edge = mean forward return when TRUE minus when FALSE")
    print("=" * 92)
    print(f"{'condition':<28}{'fires':>7}"
          + "".join(f"{e[0]:>12}" for e in ERAS) + f"{'mean':>9}{'consistent':>12}")
    print("-" * 92)
    rows = []
    for name, s in sigs.items():
        s = s.reindex(d.index).fillna(False).astype(bool)
        eds = []
        for _, a, b in ERAS:
            ss, ff = s[a:b], fwd[a:b]
            eds.append(ff[ss].mean() - ff[~ss].mean()
                       if ss.any() and (~ss).any() else np.nan)
        ok = all(np.isfinite(e) for e in eds) and len({np.sign(e) for e in eds}) == 1
        rows.append((name, 100 * s.mean(), eds, np.mean(eds), ok))
        print(f"{name:<28}{100*s.mean():>6.0f}%"
              + "".join(f"{e:>+12.2f}" for e in eds)
              + f"{np.mean(eds):>+9.2f}{('YES' if ok else 'no'):>12}")

    good = sorted([r for r in rows if r[4]], key=lambda x: -abs(x[3]))
    print(f"\nSIGN-CONSISTENT ACROSS ALL THREE ERAS: {len(good)} of {len(rows)}")
    for n, fires, eds, m, _ in good:
        print(f"  {n:<28} mean {m:+6.2f}%   fires {fires:>3.0f}%   "
              f"per era {[round(e, 2) for e in eds]}")
    if not good:
        print("  none")


if __name__ == "__main__":
    main()
