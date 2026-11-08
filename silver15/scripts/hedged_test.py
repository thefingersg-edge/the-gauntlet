#!/usr/bin/env python3
"""Test the hedged-spread variant of the silver mean-reversion signal.

THE INCONSISTENCY THIS ADDRESSES
--------------------------------
`silver_mr.py` builds its signal from a gold-implied residual -- "silver is
cheap RELATIVE TO GOLD" -- and then takes an outright silver position. So the
trade carries the full common precious-metals factor, which is exactly the
drift that swamps the residual at every horizon beyond ~12 bars (see
FINDINGS.md section 3: by h=24 the short side has already flipped positive).

Here the position is the thing the signal actually measures:

    long  1 unit silver  /  short  beta units gold      (and the reverse)

P&L is the hedged pair, in log space, with beta frozen at entry -- which is
how you would actually put the hedge on.

WHAT IS APPROXIMATED, AND WHY IT IS ACCEPTABLE HERE
---------------------------------------------------
Barriers are checked CLOSE-TO-CLOSE, not intrabar. We have OHLC for each leg
separately but not for the spread, and a spread's high does not occur when
either leg's high does -- combining leg extremes would invent a path that
never happened. Close-only checking misses some intrabar take-profit touches
(pessimistic) and some intrabar stop breaches (optimistic).

That bias is real, but it applies identically to the real, reversed and random
signals, so the NULL TEST -- which is what this script exists for -- stays
valid. Do not read the absolute P&L here as tradeable.

    python hedged_test.py --data ../data
    python hedged_test.py --data ../data --entry-z 2.5 --tf 1h
    python hedged_test.py --self-test
"""

from __future__ import annotations

import argparse
import os
import sys
import types

VERSION = "0.1"

# Round-trip costs as a FRACTION OF PRICE, both MEASURED via
# `oanda_intraday.py --sides` on 2026-06 -> 2026-08 (4,560 M15 bars each):
#
#     silver  ask-bid median 0.036 at $59.97  = 0.0600% of price
#     gold    ask-bid median 0.620 at $4106   = 0.0151% of price
#
# RELATIVE, not dollar. An earlier version of this file used fixed dollar
# spreads, which is precisely the error that made silver_mr.py's
# spread_usd=0.08 look catastrophic: silver ranges $11-$120 across the
# sample, so any fixed dollar figure is wrong at both ends. At 2016 prices
# the old 0.019 implied 0.119% -- double the truth.
#
# ASSUMPTION, stated: the spread is roughly constant in PERCENTAGE terms
# across history. It is measured today only. Spreads have generally tightened
# over 20 years, so applying today's percentage to 2006 is likely optimistic
# there; --silver-spread / --gold-spread override for sensitivity testing.
SILVER_SPREAD_REL = 0.03600 / 59.97
GOLD_SPREAD_REL = 0.62000 / 4106.06


def _stub_sklearn() -> None:
    if "sklearn" in sys.modules:
        return
    try:
        import sklearn  # noqa: F401
        return
    except ImportError:
        pass
    m = types.ModuleType("sklearn"); lm = types.ModuleType("sklearn.linear_model")

    class LogisticRegression:                       # pragma: no cover
        def __init__(self, *a, **k):
            raise RuntimeError("stubbed")

    lm.LogisticRegression = LogisticRegression
    m.linear_model = lm
    sys.modules["sklearn"] = m; sys.modules["sklearn.linear_model"] = lm


# --------------------------------------------------------------------------

def build(data_dir: str, tf: str):
    """Load, optionally resample to a slower bar, and build features."""
    import numpy as np, pandas as pd
    import silver_mr as S

    xag = S.load_csv(os.path.join(data_dir, "xagusd_15m.csv"))
    xau = S.load_csv(os.path.join(data_dir, "xauusd_15m.csv"))
    eur = S.load_csv(os.path.join(data_dir, "eurusd_15m.csv"))

    if tf != "15m":
        rule = {"30m": "30min", "1h": "1h", "4h": "4h"}[tf]
        def rs(d):
            o = d.resample(rule, closed="left", label="left").agg(
                {"open": "first", "high": "max", "low": "min", "close": "last"})
            return o.dropna(subset=["open", "high", "low", "close"])
        xag, xau, eur = rs(xag), rs(xau), rs(eur)

    df = S.build_features(xag, xau, eur.rdiv(1.0), S.CFG)
    df["xau"] = xau["close"].reindex(df.index).ffill()
    return S, df


def spread_barriers(S, df, sig, cfg, silver_spread, gold_spread,
                    hedged=True, no_overlap=False):
    """Walk each signal forward to a barrier, in HEDGED log-spread units.

    Returns one row per candidate trade. `pnl_sig` is P&L in units of the
    spread's own volatility, so it is directly comparable to the outright
    version's pnl_atr.
    """
    import numpy as np, pandas as pd

    ag = df["close"].to_numpy(float)
    au = df["xau"].to_numpy(float)
    beta = df["beta"].to_numpy(float)

    lag, lau = np.log(ag), np.log(au)
    r_ag = np.diff(lag, prepend=np.nan)
    r_au = np.diff(lau, prepend=np.nan)

    # Volatility of the hedged spread, in log units -- the unit the barriers
    # are quoted in. Uses the rolling beta so it tracks the actual hedge.
    resid = pd.Series(r_ag - beta * r_au, index=df.index)
    svol = resid.rolling(cfg["atr_window"]).std().to_numpy()

    # Cost, in log units, paid on entry and again on exit. The hedge is not
    # free: you cross gold's spread too, scaled by beta. Spreads arrive as
    # FRACTIONS OF PRICE, so they are already in log units and must NOT be
    # divided by price again.
    half_ag = np.full(len(ag), silver_spread / 2)
    half_au = np.full(len(au), gold_spread / 2)

    sigv = sig.to_numpy(int)
    idxs = np.flatnonzero(sigv != 0)
    n = len(df)
    rows = []

    # resid_z autocorrelates at ~0.96, so |z|>=2 stays true for many
    # consecutive bars and the "trades" are overlapping views of the same
    # episode. Every significance number computed on them is inflated,
    # because the sample size is a fiction. no_overlap enforces one trade per
    # max_hold window, which gives genuinely independent draws.
    if no_overlap:
        kept, last = [], -10**9
        for i in idxs:
            if i - last >= cfg["max_hold"]:
                kept.append(i); last = i
        idxs = np.array(kept, dtype=int)

    for i in idxs:
        if i + 1 >= n or not np.isfinite(svol[i]) or svol[i] <= 0:
            continue
        if not np.isfinite(beta[i]):
            continue
        side = int(sigv[i])
        b = beta[i] if hedged else 0.0

        cost = half_ag[i] + abs(b) * half_au[i]           # one side
        tp = cfg["tp_atr"] * svol[i]
        sl = cfg["sl_atr"] * svol[i]

        end = min(i + 1 + cfg["max_hold"], n)
        cum = 0.0
        outcome, real, bars = "time", 0.0, end - 1 - i
        for j in range(i + 1, end):
            step = (lag[j] - lag[j - 1]) - b * (lau[j] - lau[j - 1])
            if not np.isfinite(step):
                break
            cum += side * step
            # Record the ACTUAL level at the breach, not the barrier level.
            # Snapping biases P&L whenever barriers are ASYMMETRIC: the
            # near barrier is hit more often, so its understatement wins.
            # Symmetric barriers happen to cancel, which is why only the
            # asymmetric engines failed the synthetic control.
            if cum <= -sl:
                outcome, real, bars = "sl", cum, j - i
                break
            if cum >= tp:
                outcome, real, bars = "tp", cum, j - i
                break
        else:
            real = cum
        if outcome == "time":
            real = cum

        pnl_log = real - 2 * cost                     # cross on the way in and out
        rows.append(dict(t=df.index[i], side=side, outcome=outcome, bars=bars,
                         beta=b, svol=svol[i],
                         pnl_sig=pnl_log / svol[i],
                         win=int(pnl_log > 0)))

    if not rows:
        return pd.DataFrame(columns=["t", "side", "outcome", "pnl_sig", "win"])
    return pd.DataFrame(rows)


def null_test(S, df, cfg, silver_spread, gold_spread, hedged, seeds, label,
              no_overlap=False):
    import numpy as np, pandas as pd

    sig = S.primary_signal(df, cfg)
    geom = cfg["sl_atr"] / (cfg["tp_atr"] + cfg["sl_atr"])
    print(f"\n{label}")
    print("=" * 72)
    print(f"  coin-flip baseline from barrier geometry: {geom:.1%}")

    out = {}
    for cost_on in (False, True):
        sp_ag = silver_spread if cost_on else 0.0
        sp_au = gold_spread if cost_on else 0.0
        tag = "with measured cost" if cost_on else "ZERO cost"
        print(f"\n  --- {tag} ---")
        print(f"  {'variant':<24}{'trades':>8}{'win rate':>11}{'mean pnl_sig':>15}")

        real = spread_barriers(S, df, sig, cfg, sp_ag, sp_au, hedged, no_overlap)
        if len(real) == 0:
            print("  no trades"); return None
        print(f"  {'REAL signal':<24}{len(real):>8,}{real.win.mean():>10.2%}"
              f"{real.pnl_sig.mean():>+15.4f}")
        rev = spread_barriers(S, df, -sig, cfg, sp_ag, sp_au, hedged, no_overlap)
        print(f"  {'REVERSED signal':<24}{len(rev):>8,}{rev.win.mean():>10.2%}"
              f"{rev.pnl_sig.mean():>+15.4f}")

        wr = []
        for seed in range(seeds):
            rng = np.random.default_rng(seed)
            vals = sig.to_numpy(dtype=int, copy=True)
            nz = vals != 0
            vals[nz] = rng.choice([-1, 1], size=int(nz.sum()))
            rs = pd.Series(vals, index=sig.index, dtype=int)
            wr.append(spread_barriers(S, df, rs, cfg, sp_ag, sp_au,
                                      hedged, no_overlap).win.mean())
        mu, sd = float(np.mean(wr)), float(np.std(wr))
        z = (real.win.mean() - mu) / sd if sd > 0 else 0.0
        print(f"  {'RANDOM side':<24}{len(real):>8,}{mu:>10.2%}"
              f"{'':>15}   (sd {sd:.4f})")
        print(f"  real beats random by {real.win.mean()-mu:+.4f} = {z:+.2f} sd")
        if not cost_on:
            print("  >> " + ("PASS at zero cost" if z >= 3 else
                             "FAIL: inside noise frictionlessly"))
        out[tag] = (real, z)
        if cost_on:
            print(f"  outcomes: {real.outcome.value_counts().to_dict()}")
    return out


# --------------------------------------------------------------------------

def self_test() -> int:
    import numpy as np, pandas as pd
    fails = []

    def check(n, c, d=""):
        print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"  {d}" if not c else ""))
        if not c:
            fails.append(n)

    print(f"hedged_test.py v{VERSION}")
    print(f"  file: {os.path.abspath(__file__)}")
    print(f"  pandas {pd.__version__}  numpy {np.__version__}\n")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    _stub_sklearn()
    import silver_mr as S

    print("hedge removes the common factor it is supposed to remove")
    n = 4000
    rng = np.random.default_rng(0)
    idx = pd.date_range("2020-01-01", periods=n, freq="15min", tz="UTC")
    # gold with strong drift; silver = 2x gold + pure noise, NO own edge
    r_au = rng.normal(0.0002, 0.001, n)
    r_ag = 2 * r_au + rng.normal(0, 0.001, n)
    au = 2000 * np.exp(np.cumsum(r_au))
    ag = 30 * np.exp(np.cumsum(r_ag))
    d = pd.DataFrame({"close": ag, "xau": au, "beta": 2.0}, index=idx)
    sig = pd.Series(0, index=idx, dtype=int)
    sig.iloc[100:-100:37] = 1                       # always long
    cfg = dict(S.CFG); cfg["max_hold"] = 12; cfg["atr_window"] = 14

    unh = spread_barriers(S, d, sig, cfg, 0.0, 0.0, hedged=False)
    hed = spread_barriers(S, d, sig, cfg, 0.0, 0.0, hedged=True)
    check("unhedged and hedged both produce trades",
          len(unh) > 50 and len(hed) > 50, f"{len(unh)}/{len(hed)}")
    # An always-long position should profit from drift when unhedged and be
    # ~flat when hedged. That is the whole point of the hedge.
    check("unhedged captures the drift", unh.pnl_sig.mean() > hed.pnl_sig.mean(),
          f"unhedged {unh.pnl_sig.mean():+.4f} vs hedged {hed.pnl_sig.mean():+.4f}")
    check("hedged is closer to flat than unhedged",
          abs(hed.pnl_sig.mean()) < abs(unh.pnl_sig.mean()),
          f"hedged {hed.pnl_sig.mean():+.4f} vs unhedged {unh.pnl_sig.mean():+.4f}")

    print("\nbarriers respected")
    check("no trade loses more than the stop",
          hed.pnl_sig.min() >= -cfg["sl_atr"] - 1e-9,
          f"min {hed.pnl_sig.min():.4f} vs sl {-cfg['sl_atr']}")
    check("no trade gains more than the take-profit",
          hed.pnl_sig.max() <= cfg["tp_atr"] + 1e-9,
          f"max {hed.pnl_sig.max():.4f} vs tp {cfg['tp_atr']}")

    print("\ncosts reduce P&L")
    withcost = spread_barriers(S, d, sig, cfg, 0.0006, 0.00015, hedged=True)
    check("adding spread lowers mean P&L",
          withcost.pnl_sig.mean() < hed.pnl_sig.mean())

    print("\nrandomisation is pandas-3 safe")
    try:
        vals = sig.to_numpy(dtype=int, copy=True)
        vals[vals != 0] = rng.choice([-1, 1], size=int((vals != 0).sum()))
        check("sides randomised without read-only error", True)
    except Exception as exc:                                # noqa: BLE001
        check("sides randomised without read-only error", False, str(exc))

    print("\n" + "=" * 58)
    if fails:
        print(f"{len(fails)} FAILED: {', '.join(fails)}")
        return 1
    print("all offline checks passed")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="../data")
    ap.add_argument("--tf", default="15m", choices=["15m", "30m", "1h", "4h"])
    ap.add_argument("--entry-z", type=float, default=None)
    ap.add_argument("--max-hold", type=int, default=None)
    ap.add_argument("--tp", type=float, default=None)
    ap.add_argument("--sl", type=float, default=None)
    ap.add_argument("--silver-spread", type=float, default=SILVER_SPREAD_REL,
                    help="round-trip, as a FRACTION of price (0.0006 = 0.06%%)")
    ap.add_argument("--gold-spread", type=float, default=GOLD_SPREAD_REL,
                    help="round-trip, as a FRACTION of price")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--no-overlap", action="store_true",
                    help="one trade per max_hold window: independent draws")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()

    if a.version:
        print(f"hedged_test.py v{VERSION}")
        print(f"  running from: {os.path.abspath(__file__)}")
        sys.exit(0)
    if a.self_test:
        sys.exit(self_test())

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    _stub_sklearn()
    print(f"\nhedged_test.py v{VERSION}  [{os.path.abspath(__file__)}]")
    S, df = build(a.data, a.tf)
    cfg = dict(S.CFG)
    if a.entry_z is not None:
        cfg["entry_z"] = a.entry_z
    if a.max_hold is not None:
        cfg["max_hold"] = a.max_hold
    if a.tp is not None:
        cfg["tp_atr"] = a.tp
    if a.sl is not None:
        cfg["sl_atr"] = a.sl
    print(f"  tf {a.tf}   {len(df):,} bars   entry_z {cfg['entry_z']}   "
          f"max_hold {cfg['max_hold']}")
    print(f"  costs (round trip, MEASURED, as %% of price): "
          f"silver {a.silver_spread*100:.4f}%   gold {a.gold_spread*100:.4f}%")

    null_test(S, df, cfg, a.silver_spread, a.gold_spread, False,
              a.seeds, "UNHEDGED (outright silver) -- the current design",
              a.no_overlap)
    null_test(S, df, cfg, a.silver_spread, a.gold_spread, True,
              a.seeds, "HEDGED (long silver / short beta x gold)",
              a.no_overlap)


if __name__ == "__main__":
    main()
