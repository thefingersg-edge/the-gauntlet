#!/usr/bin/env python3
"""THE v5 pre-registered test. Spec frozen in PREREGISTRATION_v5.md.

Weekly change in commercial net positioning, z-scored over 52 weeks, lagged a
full week past the plotted (Tuesday) date, predicting the following week's
return. Six CFTC markets pooled into ONE statistic.

    python prereg_v5_test.py --self-test     # synthetic controls FIRST
    python prereg_v5_test.py --data ../data_cot

--data and --seeds only. Nothing here changes the specification.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys

VERSION = "5.0-prereg"

# ---- FROZEN SPEC (PREREGISTRATION_v5.md) ----------------------------------
Z_WINDOW = 52          # weeks, for z-scoring the weekly change
LAG_WEEKS = 1          # FULL week past the plotted Tuesday date. See below.
HORIZON = 1            # weeks held, non-overlapping
MAX_MARKET_SHARE = 0.35
MAX_DECADE_SHARE = 0.50

MARKETS = {"088691": "gold", "084691": "silver", "085692": "copper",
           "067651": "wti", "002602": "corn", "099741": "usdx"}

# Measured round-trip spreads as a fraction of price. Corn and USDX were not
# measured; the WORST measured value is used as a conservative stand-in
# rather than a flattering guess.
SPREAD = {"gold": 0.62 / 4106.06, "silver": 0.036 / 59.97,
          "copper": 0.00199 / 6.29, "wti": 0.040 / 79.89,
          "corn": 0.0500 / 100.0, "usdx": 0.0500 / 100.0}
# ---------------------------------------------------------------------------
#
# THE LAG, AND WHY IT IS A FULL WEEK
#
# CFTC measures positions at Tuesday's close and publishes Friday 15:30 ET.
# This indicator plots on the POSITION date -- 90-98% of updates land on a
# Tuesday, verified in cot_budget.py. Reading Tuesday's value on Tuesday
# therefore trades on information that does not exist for three more days,
# and would manufacture an edge that looks entirely real.
#
# The minimum honest lag is until the following Monday (~4 trading days).
# LAG_WEEKS = 1 is deliberately more conservative so that holiday-shifted
# releases cannot leak. --self-test includes a probe that runs the signal
# UNLAGGED and must show an inflated result; if it does not, the lag
# machinery is not doing anything.
# ---------------------------------------------------------------------------


def load(data_dir):
    import pandas as pd
    out = {}
    for f in sorted(glob.glob(os.path.join(data_dir, "cot_*_*.csv"))):
        m = re.search(r"_(\d{6})\.csv$", f)
        if not m or m.group(1) not in MARKETS:
            continue
        d = pd.read_csv(f)
        d["t"] = pd.to_datetime(d["time"], unit="s", utc=True)
        d = d.set_index("t").sort_index()
        cols = [c for c in d.columns
                if c not in ("time", "open", "high", "low", "close", "Volume")]
        for c in cols:
            d[c] = pd.to_numeric(d[c], errors="coerce")
        d = d.dropna(subset=cols, how="all")
        out[MARKETS[m.group(1)]] = d
    return out


def weekly_obs(d):
    """Collapse daily rows to genuine weekly COT updates, with the price at
    each update and the price one week later."""
    import numpy as np, pandas as pd
    cols = [c for c in d.columns if "Commercials" in c]
    upd = d[cols].diff().abs().sum(axis=1) > 1e-9
    w = d[upd].copy()
    w["net"] = w["Commercials net"]
    return w


def signals(d, mode="real", rng=None, lag_weeks=LAG_WEEKS):
    """One row per tradable week: signal, forward return, cost."""
    import numpy as np, pandas as pd

    w = weekly_obs(d)
    if len(w) < Z_WINDOW + 10:
        return pd.DataFrame(columns=["t", "sig", "fwd", "pnl"])

    chg = w["net"].diff()
    z = (chg - chg.rolling(Z_WINDOW).mean()) / chg.rolling(Z_WINDOW).std()

    # THE LAG. Shift the signal forward so the trade uses only information
    # published before the holding period begins.
    zl = z.shift(lag_weeks)

    # forward return over HORIZON weeks, from the price at the tradable week
    px = w["close"].astype(float)
    fwd = np.log(px.shift(-HORIZON) / px)

    df = pd.DataFrame({"z": zl, "fwd": fwd}).dropna()
    if df.empty:
        return pd.DataFrame(columns=["t", "sig", "fwd", "pnl"])

    s = np.sign(df["z"].to_numpy())
    if mode == "rev":
        s = -s
    elif mode == "rand":
        s = rng.choice([-1.0, 1.0], size=len(s))

    # vol-scale so each market contributes equal risk
    vol = df["fwd"].rolling(Z_WINDOW).std().bfill()
    vol = vol.replace(0, np.nan).ffill().fillna(df["fwd"].std())
    pnl = s * df["fwd"].to_numpy() / vol.to_numpy()

    return pd.DataFrame({"t": df.index, "sig": s,
                         "fwd": df["fwd"].to_numpy(), "pnl": pnl})


def pooled(S, mode="real", rng=None, charge_cost=True, lag_weeks=LAG_WEEKS):
    import numpy as np, pandas as pd
    frames = []
    for k, d in sorted(S.items()):
        r = signals(d, mode, rng, lag_weeks)
        if len(r) == 0:
            continue
        if charge_cost:
            # position flips cost a round trip; scale by the same vol used above
            flip = np.abs(np.diff(r["sig"].to_numpy(), prepend=r["sig"].iloc[0])) / 2
            vol = r["fwd"].rolling(Z_WINDOW).std().bfill().replace(0, np.nan)
            vol = vol.ffill().fillna(r["fwd"].std())
            sp = SPREAD.get(k, 0.0005)   # synthetic markets get a nominal cost
            r = r.assign(pnl=r["pnl"] - flip * sp / vol.to_numpy())
        frames.append(r.assign(mkt=k))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ---------------------------------------------------------------------------

def self_test():
    """Synthetic controls. The engine must be verified BEFORE it is trusted."""
    import numpy as np, pandas as pd
    fails = []

    def check(n, c, d=""):
        print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ""))
        if not c:
            fails.append(n)

    print(f"prereg_v5_test.py v{VERSION} — synthetic controls\n")

    def synth(n_weeks, seed, planted=0.0, noise=0.02):
        """Weekly panel. `planted` couples the COT change to the NEXT return."""
        rng = np.random.default_rng(seed)
        idx = pd.date_range("1986-01-15", periods=n_weeks, freq="7D", tz="UTC")
        chg = rng.normal(0, 1000, n_weeks)
        net = np.cumsum(chg)
        z = (chg - chg.mean()) / chg.std()
        # The engine uses z[i-LAG] to predict fwd[i]. A synthetic that plants
        # z[i] -> fwd[i] tests the WRONG thing: the lag correctly destroys it,
        # and the control fails for a good reason. Plant it at the lag the
        # engine actually applies.
        zl = np.roll(z, LAG_WEEKS)
        zl[:LAG_WEEKS] = 0.0
        fwd = planted * zl + rng.normal(0, noise, n_weeks)
        px = 100 * np.exp(np.cumsum(np.roll(fwd, 1)))
        return pd.DataFrame({"close": px, "Commercials net": net,
                             "Commercials long": net, "Commercials short": -net},
                            index=idx)

    # 1. no planted edge -> mean 0
    m = []
    for s in range(8):
        S = {"x": synth(1800, s, planted=0.0)}
        m.append(pooled(S, charge_cost=False).pnl.mean())
    mu, se = float(np.mean(m)), float(np.std(m)) / np.sqrt(8)
    check("1 no planted edge -> mean 0", abs(mu) < max(2 * se, 0.02),
          f"got {mu:+.4f} (se {se:.4f})")

    # 2. planted edge -> engine finds it
    m2 = []
    for s in range(8):
        S = {"x": synth(1800, s, planted=0.010)}
        m2.append(pooled(S, charge_cost=False).pnl.mean())
    check("2 recovers a planted edge", float(np.mean(m2)) > 0.05,
          f"got {np.mean(m2):+.4f}")

    # 3. reversed loses it
    m3 = []
    for s in range(8):
        S = {"x": synth(1800, s, planted=0.010)}
        m3.append(pooled(S, "rev", charge_cost=False).pnl.mean())
    check("3 reversed loses on the same data", float(np.mean(m3)) < float(np.mean(m2)),
          f"real {np.mean(m2):+.4f} rev {np.mean(m3):+.4f}")

    # 4. cost reduces P&L
    S = {"x": synth(1800, 3, planted=0.010)}
    a = pooled(S, charge_cost=False).pnl.mean()
    b = pooled(S, charge_cost=True).pnl.mean()
    check("4 cost reduces P&L", b < a, f"{a:+.4f} -> {b:+.4f}")

    # 5. THE LAG PROBE. Plant the edge so the COT change predicts the
    #    CONTEMPORANEOUS return, i.e. information that is not yet public.
    #    Unlagged must show a large edge; correctly lagged must not.
    def synth_leak(n_weeks, seed):
        """Leak model: the COT change in week i is correlated with the return
        realised BETWEEN Tuesday i and Tuesday i+1 -- which includes the
        Tue->Fri window before publication. An unlagged signal captures it;
        a correctly lagged one cannot.

        The price path must be built as cumsum(roll(fwd,1)) so that
        log(px[i+1]/px[i]) == fwd[i]. Building it as cumsum(fwd) offsets the
        leak by one week and hides it from BOTH runs -- which is what made
        this control fail on its first attempt.
        """
        rng = np.random.default_rng(seed)
        idx = pd.date_range("1986-01-15", periods=n_weeks, freq="7D", tz="UTC")
        chg = rng.normal(0, 1000, n_weeks)
        net = np.cumsum(chg)
        z = (chg - chg.mean()) / chg.std()
        fwd = 0.03 * z + rng.normal(0, 0.02, n_weeks)     # plant at lag ZERO
        px = 100 * np.exp(np.cumsum(np.roll(fwd, 1)))
        return pd.DataFrame({"close": px, "Commercials net": net,
                             "Commercials long": net, "Commercials short": -net},
                            index=idx)

    S = {"x": synth_leak(1800, 11)}
    unlagged = pooled(S, charge_cost=False, lag_weeks=0).pnl.mean()
    lagged = pooled(S, charge_cost=False, lag_weeks=1).pnl.mean()
    check("5 lag probe: unlagged sees the leak", unlagged > 0.10,
          f"unlagged {unlagged:+.4f}")
    check("6 lag probe: LAGGED does NOT", abs(lagged) < 0.5 * abs(unlagged),
          f"unlagged {unlagged:+.4f} -> lagged {lagged:+.4f}")

    print("\n" + "=" * 60)
    if fails:
        print(f"{len(fails)} FAILED: {', '.join(fails)}")
        return 1
    print("all synthetic controls passed — engine may be trusted")
    return 0


def main():
    import numpy as np, pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data_cot")
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        sys.exit(self_test())

    print(f"prereg_v5_test.py v{VERSION}   spec frozen in PREREGISTRATION_v5.md")
    print(f"  weekly change in Commercials net, z over {Z_WINDOW}w,")
    print(f"  LAGGED {LAG_WEEKS} full week past the plotted Tuesday date,")
    print(f"  {HORIZON}-week horizon, six markets POOLED, 2 sigma\n")

    S = load(a.data)
    print(f"  markets: {', '.join(sorted(S))}")
    pool = pooled(S, "real")
    yrs = (pool.t.max() - pool.t.min()).days / 365.25
    print(f"  {len(pool):,} weekly observations   "
          f"{pool.t.min().date()} -> {pool.t.max().date()}   {yrs:.1f}y")

    mu, sd = pool.pnl.mean(), pool.pnl.std()
    per_year = len(pool) / yrs
    sharpe = (mu / sd) * np.sqrt(per_year / len(S)) if sd > 0 else 0.0

    print(f"\n{'='*72}\nPOOLED — the single pre-registered statistic\n{'='*72}")
    print(f"  MEAN P&L per week    {mu:+.5f} vol units")
    boot = np.array([np.random.default_rng(k).choice(
        pool.pnl.to_numpy(), len(pool), replace=True).mean() for k in range(1000)])
    lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    print(f"  bootstrap 95% CI     [{lo:+.5f}, {hi:+.5f}]")
    print(f"  implied ann. Sharpe  {sharpe:+.2f}   (bar 0.32)")
    print(f"  positive weeks       {(pool.pnl>0).mean():.1%}")

    print(f"\n  per market:")
    print(f"  {'market':<9}{'n':>7}{'mean':>10}{'t':>8}")
    for k, g in pool.groupby("mkt"):
        se = g.pnl.std() / np.sqrt(len(g))
        print(f"  {k:<9}{len(g):>7,}{g.pnl.mean():>+10.4f}"
              f"{g.pnl.mean()/se if se>0 else 0:>+8.2f}")

    gp = pool[pool.pnl > 0].groupby("mkt").pnl.sum()
    mshare = gp.max() / gp.sum() if gp.sum() > 0 else float("nan")
    dec = pool.assign(d=(pool.t.dt.year // 10) * 10).groupby("d").pnl.apply(
        lambda v: v[v > 0].sum())
    dshare = dec.max() / dec.sum() if dec.sum() > 0 else float("nan")
    print(f"\n  top market  {gp.idxmax()} = {mshare:.1%}")
    print(f"  top decade  {dec.idxmax()}s = {dshare:.1%}")

    c1 = mu > 0 and lo > 0
    c2 = mshare <= MAX_MARKET_SHARE and dshare <= MAX_DECADE_SHARE
    print(f"\n  1 profitable after costs (mean>0, CI lo>0)   "
          f"{'PASS' if c1 else 'FAIL'}")
    print(f"  2 not one market (<=35%) or decade (<=50%)   "
          f"{'PASS' if c2 else 'FAIL'}")

    print(f"\n  --- diagnostics, NOT criteria ---")
    rev = pooled(S, "rev")
    wr = [pooled(S, "rand", np.random.default_rng(k)).pnl.mean()
          for k in range(a.seeds)]
    rm, rs = float(np.mean(wr)), float(np.std(wr))
    print(f"  real {mu:+.5f}   random {rm:+.5f} (sd {rs:.5f})   "
          f"reversed {rev.pnl.mean():+.5f}")
    if rs > 0:
        print(f"  real vs random: {(mu-rm)/rs:+.2f} sd")
    unl = pooled(S, "real", lag_weeks=0)
    print(f"  UNLAGGED (would be look-ahead): {unl.pnl.mean():+.5f}  "
          f"vs lagged {mu:+.5f}")
    print(f"  a large gap here means the lag is doing real work")

    print(f"\n{'='*72}\nVERDICT\n{'='*72}")
    if c1 and c2:
        print("  H1 SUPPORTED at 2 sigma.")
        print("  Before ANY capital: re-run audit.py and --self-test, then")
        print("  forward-test. COT has been public since 1986 -- a simple edge")
        print("  surviving 40 years of scrutiny deserves suspicion, not haste.")
    else:
        print("  H1 REJECTED.")
        print("  Per PREREGISTRATION_v5.md: no COT edge at or above an annual")
        print("  Sharpe of ~0.32 on these six markets. The line ends here.")


if __name__ == "__main__":
    main()
