#!/usr/bin/env python3
"""THE pre-registered multi-day test. Spec frozen in PREREGISTRATION.md.

Run it, read the verdict, accept it. The configuration below is deliberately
hard-coded rather than exposed as flags: this test exists precisely because a
search over ~2,000 trades and a dozen parameters will always find something,
and the only defence is not being able to search.

    python prereg_test.py --data ../data_h4

Everything is fixed. --data and --seeds are the only knobs, and --seeds only
sharpens the null estimate. If you find yourself wanting another flag here,
that is the feeling this file exists to stop.
"""

from __future__ import annotations

import argparse
import os
import sys
import types

VERSION = "1.0-prereg"

# ---- FROZEN SPEC (PREREGISTRATION.md) -------------------------------------
BETA_WINDOW = 120        # H4 bars, ~20 trading days
RESID_WINDOW = 30        # H4 bars, 5 days
Z_WINDOW = 120
ENTRY_Z = 2.0
TP = 2.0                 # spread-vol units, symmetric -> break-even 50%
SL = 2.0
MAX_HOLD = 30            # H4 bars, 5 days
VOL_WINDOW = 14

# MEASURED round-trip spreads, as a fraction of price (oanda_intraday --sides)
SILVER_REL = 0.03600 / 59.97      # 0.0600%
GOLD_REL = 0.62000 / 4106.06      # 0.0151%

PRIMARY = ("2006-01-01", "2015-12-31")    # unseen -> this is the result
SECONDARY = ("2016-01-01", "2026-12-31")  # already inspected at M15 -> context

# Success thresholds, fixed in advance
MIN_SD = 3.0
MIN_TRADES = 200
MAX_YEAR_SHARE = 0.40
# ---------------------------------------------------------------------------


def _stub_sklearn():
    try:
        import sklearn  # noqa: F401
        return
    except ImportError:
        pass
    m = types.ModuleType("sklearn"); lm = types.ModuleType("sklearn.linear_model")

    class LogisticRegression:                     # pragma: no cover
        def __init__(self, *a, **k):
            raise RuntimeError("stubbed")
    lm.LogisticRegression = LogisticRegression
    m.linear_model = lm
    sys.modules["sklearn"] = m; sys.modules["sklearn.linear_model"] = lm


def load(data_dir):
    import numpy as np, pandas as pd

    def rd(name):
        d = pd.read_csv(os.path.join(data_dir, name))
        t = d.columns[0]
        d[t] = pd.to_datetime(d[t], utc=True)
        return d.set_index(t).sort_index()

    ag, au = rd("xagusd_4h.csv"), rd("xauusd_4h.csv")
    idx = ag.index.intersection(au.index)
    ag, au = ag.loc[idx], au.loc[idx]

    r_ag = np.log(ag["close"]).diff()
    r_au = np.log(au["close"]).diff()
    beta = (r_ag.rolling(BETA_WINDOW).cov(r_au)
            / r_au.rolling(BETA_WINDOW).var().replace(0, np.nan)).clip(0.5, 4.0)
    resid = r_ag - beta * r_au
    cum = resid.rolling(RESID_WINDOW).sum()
    z = (cum - cum.rolling(Z_WINDOW).mean()) / cum.rolling(Z_WINDOW).std()

    return pd.DataFrame({"ag": ag["close"], "au": au["close"], "beta": beta,
                         "z": z, "svol": resid.rolling(VOL_WINDOW).std()})


def trades(df, sides, cost_on):
    """Walk each entry to a barrier on the HEDGED log spread. Non-overlapping."""
    import numpy as np, pandas as pd

    lag = np.log(df["ag"].to_numpy(float))
    lau = np.log(df["au"].to_numpy(float))
    beta = df["beta"].to_numpy(float)
    svol = df["svol"].to_numpy(float)
    sv = sides.to_numpy(int)

    cost_side = (SILVER_REL / 2 + np.abs(beta) * GOLD_REL / 2) if cost_on \
        else np.zeros(len(df))

    idxs = np.flatnonzero(sv != 0)
    kept, last = [], -10**9
    for i in idxs:                                  # independence, enforced
        if i - last >= MAX_HOLD:
            kept.append(i); last = i

    n, rows = len(df), []
    for i in kept:
        if i + 1 >= n or not np.isfinite(svol[i]) or svol[i] <= 0:
            continue
        if not np.isfinite(beta[i]):
            continue
        side, b = int(sv[i]), beta[i]
        tp, sl = TP * svol[i], SL * svol[i]
        end = min(i + 1 + MAX_HOLD, n)
        cum, outcome = 0.0, "time"
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
                outcome = "sl"; break
            if cum >= tp:
                outcome = "tp"; break
        pnl = cum - 2 * cost_side[i]
        rows.append(dict(t=df.index[i], pnl=pnl / svol[i], win=int(pnl > 0),
                         outcome=outcome))
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["t", "pnl", "win", "outcome"])


def evaluate(df, label, seeds, verbose=True):
    import numpy as np, pandas as pd

    sig = pd.Series(0, index=df.index, dtype=int)
    sig[df["z"] <= -ENTRY_Z] = 1
    sig[df["z"] >= ENTRY_Z] = -1

    print(f"\n{'='*72}\n{label}\n{'='*72}")
    real0 = trades(df, sig, False)
    if len(real0) == 0:
        print("  no trades"); return None

    rev0 = trades(df, -sig, False)
    wr = []
    for s in range(seeds):
        rng = np.random.default_rng(s)
        v = sig.to_numpy(dtype=int, copy=True)
        nz = v != 0
        v[nz] = rng.choice([-1, 1], size=int(nz.sum()))
        wr.append(trades(df, pd.Series(v, index=df.index, dtype=int),
                         False).win.mean())
    mu, sd = float(np.mean(wr)), float(np.std(wr))
    z_sd = (real0.win.mean() - mu) / sd if sd > 0 else 0.0

    realc = trades(df, sig, True)
    print(f"  trades (independent): {len(real0):,}")
    print(f"\n  ZERO cost      real {real0.win.mean():.2%}   "
          f"random {mu:.2%} (sd {sd:.4f})   reversed {rev0.win.mean():.2%}")
    print(f"                 real beats random by {z_sd:+.2f} sd")
    print(f"  WITH cost      mean pnl {realc.pnl.mean():+.4f} spread-vol   "
          f"win {realc.win.mean():.2%}")

    boot = [np.random.default_rng(s).choice(realc.pnl.to_numpy(),
                                            len(realc), replace=True).mean()
            for s in range(1000)]
    lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    print(f"                 bootstrap 95% CI [{lo:+.4f}, {hi:+.4f}]")

    yr = realc.assign(y=realc.t.dt.year).groupby("y").pnl.sum()
    tot = yr[yr > 0].sum()
    share = (yr.max() / tot) if tot > 0 else float("nan")
    print(f"                 best year {yr.idxmax()} = {share:.1%} of gross positive P&L")

    c1 = z_sd >= MIN_SD
    c2 = real0.win.mean() > mu > rev0.win.mean()
    c3 = realc.pnl.mean() > 0 and lo > 0
    c4 = (share <= MAX_YEAR_SHARE) if tot > 0 else False
    print(f"\n  1 signal real   (>= {MIN_SD} sd)          {'PASS' if c1 else 'FAIL'}")
    print(f"  2 direction coherent                 {'PASS' if c2 else 'FAIL'}")
    print(f"  3 survives cost (mean>0, CI lo>0)    {'PASS' if c3 else 'FAIL'}")
    print(f"  4 not one episode (<= {MAX_YEAR_SHARE:.0%})        {'PASS' if c4 else 'FAIL'}")
    if len(real0) < MIN_TRADES:
        print(f"\n  !! only {len(real0)} trades (< {MIN_TRADES}). Per the prereg a")
        print("  !! criterion-1 failure here is UNDERPOWERED, not disproved.")
    return all([c1, c2, c3, c4]), len(real0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data_h4")
    ap.add_argument("--seeds", type=int, default=50)
    a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    _stub_sklearn()

    print(f"prereg_test.py v{VERSION}   spec frozen in PREREGISTRATION.md")
    print(f"  entry |z|>={ENTRY_Z}  tp={TP} sl={SL}  hold={MAX_HOLD} H4 bars "
          f"(5d)  hedged, non-overlapping")
    print(f"  costs: silver {SILVER_REL*100:.4f}%  gold {GOLD_REL*100:.4f}% "
          f"of price, round trip (MEASURED)")

    df = load(a.data)
    print(f"  {len(df):,} H4 bars  {df.index.min().date()} -> {df.index.max().date()}")

    res = {}
    for label, (lo, hi) in (("PRIMARY 2006-2015 (unseen -- this is the result)",
                             PRIMARY),
                            ("SECONDARY 2016-2026 (already inspected -- context only)",
                             SECONDARY)):
        sub = df.loc[lo:hi]
        res[label] = evaluate(sub, label, a.seeds)

    print(f"\n{'='*72}\nVERDICT\n{'='*72}")
    primary = list(res.values())[0]
    if primary and primary[0]:
        print("  H1 SUPPORTED on the primary window. All four criteria pass.")
        print("  Next: out-of-sample confirmation, then and only then a meta-model.")
    else:
        print("  H1 REJECTED on the primary window.")
        print("  Per the pre-registration this is a STOP, not a retune.")
        print("  Do not adjust entry_z, barriers, windows or timeframe and re-run.")


if __name__ == "__main__":
    main()
