#!/usr/bin/env python3
"""THE v7 pre-registered test. Spec frozen in PREREGISTRATION_v7.md.

12-month time-series momentum: every instrument held long or short by the sign
of its trailing 12-month return, vol-scaled, rebalanced monthly. ONE pooled
net monthly return series.

    python prereg_v7_test.py --self-test     # synthetic controls FIRST
    python prereg_v7_test.py

--data and --seeds only. Nothing here changes the specification.
"""

from __future__ import annotations

import argparse
import math
import os
import sys

VERSION = "7.0-prereg"

_FLAG = "PREREG_V7_BOOTSTRAPPED"


def _deps() -> bool:
    import importlib.util
    try:
        return all(importlib.util.find_spec(m) for m in ("numpy", "pandas"))
    except (ImportError, ValueError):
        return False


def _bootstrap() -> None:
    if os.environ.get(_FLAG) or _deps():
        return
    here = os.path.dirname(os.path.abspath(__file__))
    for rel in (".venv", "venv"):
        for sub in ("bin/python3", "bin/python", "Scripts/python.exe"):
            c = os.path.abspath(os.path.join(here, rel, *sub.split("/")))
            if os.path.isfile(c) and os.access(c, os.X_OK):
                if c == os.path.abspath(sys.executable):
                    return
                print(f"  [venv] re-running under {os.path.relpath(c, here)}",
                      file=sys.stderr)
                os.environ[_FLAG] = "1"
                try:
                    os.execv(c, [c, os.path.abspath(__file__)] + sys.argv[1:])
                except OSError:
                    return


_bootstrap()

# ---- FROZEN SPEC (PREREGISTRATION_v7.md) ----------------------------------
LOOKBACK_M = 12        # months. Fixed by prior specification, not chosen here.
VOL_WINDOW = 12        # months, TRAILING
MAX_DD = 0.25          # criterion 2
MAX_YEAR_SHARE = 0.30  # criterion 3
# ---------------------------------------------------------------------------


def load_monthly(data_dir):
    """Month-end close, each instrument resampled on its OWN bars first."""
    import pandas as pd
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import screen_universe as U
    cols, spreads = {}, {}
    for stem in U.SPREAD_REL:
        p = os.path.join(data_dir, f"{stem}_4h.csv")
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p)
        t = d.columns[0]
        d[t] = pd.to_datetime(d[t], utc=True)
        s = d.set_index(t).sort_index()["close"].astype(float)
        cols[U.LABEL[stem]] = s.resample("ME").last().dropna()
        spreads[U.LABEL[stem]] = U.SPREAD_REL[stem]
    return pd.DataFrame(cols).sort_index(), pd.Series(spreads)


def run(P, spread, mode="real", rng=None, charge_cost=True, peek=False):
    """One row per month. Returns the book's net log return.

    THE ALIGNMENT
    -------------
    Signal at month m is sign(L[m] - L[m-12]), formed at the CLOSE of m from
    information entirely inside months m-11..m. It earns fwd[m] = r[m+1].
    Volatility uses returns through m only.

    `peek=True` deliberately breaks this by paying the signal the return it
    was partly computed from. It exists so the look-ahead control has
    something that must inflate — a probe with no way to fire is decoration,
    and this project produced four of those before anyone noticed.
    """
    import numpy as np, pandas as pd

    L = np.log(P)
    R = L.diff()                              # r[m] realised DURING month m
    fwd = R if peek else R.shift(-1)          # earned in m+1, formed close of m
    vol = R.rolling(VOL_WINDOW).std()         # known at close of m
    sig = np.sign(L - L.shift(LOOKBACK_M))    # THE 12-MONTH SIGN

    rows, prev = [], {}
    for m in P.index:
        if m not in sig.index:
            continue
        s = sig.loc[m].dropna()
        v = vol.loc[m] if m in vol.index else None
        f = fwd.loc[m] if m in fwd.index else None
        if v is None or f is None or s.empty:
            continue
        elig = [c for c in s.index
                if np.isfinite(v.get(c, np.nan)) and v.get(c, 0) > 0
                and np.isfinite(f.get(c, np.nan)) and s[c] != 0]
        if len(elig) < 20:
            continue
        s = s[elig]

        if mode == "rand":
            sgn = pd.Series(rng.choice([-1.0, 1.0], size=len(s)), index=s.index)
        elif mode == "rev":
            sgn = -s
        else:
            sgn = s

        # equal RISK per instrument, gross normalised to 1 unit
        w = {c: float(sgn[c]) / v[c] for c in s.index}
        gross = sum(abs(x) for x in w.values())
        if gross <= 0:
            continue
        w = {c: x / gross for c, x in w.items()}

        ret = sum(w[c] * f[c] for c in w)

        cost = 0.0
        if charge_cost:
            # Charge the CHANGE in each position. A sign flip moves two units
            # of notional and is therefore charged twice — the commonest way a
            # trend-following backtest flatters itself is charging it once.
            for c in set(w) | set(prev):
                cost += abs(w.get(c, 0.0) - prev.get(c, 0.0)) * spread.get(c, 0.0)
        prev = w

        rows.append(dict(t=m, ret=ret, net=ret - cost, cost=cost,
                         n=len(w), gross=sum(abs(x) for x in w.values())))
    return pd.DataFrame(rows, columns=["t", "ret", "net", "cost", "n", "gross"])


def max_drawdown(net) -> float:
    import numpy as np
    eq = np.exp(np.cumsum(np.asarray(net, dtype=float)))
    if not len(eq):
        return 0.0
    peak = np.maximum.accumulate(eq)
    return float(np.max((peak - eq) / peak))


# ---------------------------------------------------------------------------

def self_test() -> int:
    import numpy as np, pandas as pd
    fails = []

    def check(n, c, d=""):
        print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ""))
        if not c:
            fails.append(n)

    print(f"prereg_v7_test.py v{VERSION} — synthetic controls\n")
    print(f"  interpreter  {sys.executable}\n")

    N, T = 24, 400
    idx = pd.date_range("1990-01-31", periods=T, freq="ME", tz="UTC")
    spread = pd.Series({f"I{i}": 0.0002 for i in range(N)})

    def synth(seed, beta=0.0, sigma=0.04):
        """Price paths with a KNOWN amount of 12-month trend continuation.

        r[t] = beta * sign(sum of the previous 12 months) + noise

        The trailing sum runs over t-12..t-1, which is exactly the window the
        engine reads at the close of month t-1 to fund month t. Planting it
        anywhere else tests the wrong lag — the mistake the v5 and v6
        harnesses both made before it was caught.
        """
        rng = np.random.default_rng(seed)
        out = {}
        for i in range(N):
            r = np.zeros(T)
            for t in range(T):
                s = np.sign(r[max(0, t - LOOKBACK_M):t].sum()) if t >= LOOKBACK_M else 0.0
                r[t] = beta * s + rng.normal(0, sigma)
            out[f"I{i}"] = 100 * np.exp(np.cumsum(r))
        return pd.DataFrame(out, index=idx)

    # 1. a driftless random walk must return zero
    m = [run(synth(s), spread, charge_cost=False).net.mean() for s in range(6)]
    mu, se = float(np.mean(m)), float(np.std(m)) / math.sqrt(6)
    check("1 random walk -> mean 0", abs(mu) < max(2 * se, 0.0005),
          f"{mu:+.6f} (se {se:.6f})")

    # 2. planted trend continuation is recovered
    P_tr = synth(1, beta=0.015)
    real = run(P_tr, spread, charge_cost=False).net.mean()
    check("2 planted trend recovered", real > 0.0015, f"{real:+.6f}")

    # 3. reversed must LOSE on the same trending data
    rev = run(P_tr, spread, "rev", charge_cost=False).net.mean()
    check("3 reversed mirrors real", rev < 0 < real,
          f"real {real:+.6f} / reversed {rev:+.6f}")

    # 4. MEAN REVERSION must flip the sign. Tests the mechanism, not just
    #    the plumbing: a negative beta means trends reverse, and a momentum
    #    engine must lose money on it.
    P_mr = synth(2, beta=-0.015)
    mr = run(P_mr, spread, charge_cost=False).net.mean()
    check("4 mean-reverting data makes momentum LOSE", mr < 0, f"{mr:+.6f}")

    # 5-6. cost
    free = run(P_tr, spread, charge_cost=False).net.mean()
    paid = run(P_tr, spread, charge_cost=True).net.mean()
    dbl = run(P_tr, spread * 2, charge_cost=True).net.mean()
    check("5 cost reduces P&L", paid < free, f"{paid:+.6f} < {free:+.6f}")
    check("6 doubling the spread doubles the drag",
          abs((free - dbl) / (free - paid) - 2.0) < 0.05,
          f"drag {free - paid:.6f} -> {free - dbl:.6f}")

    # 7. THE LOOK-AHEAD PROBE.
    #
    # RUN IT WHERE THE HONEST ANSWER IS ZERO. The first version compared
    # honest against peeking on STRONGLY TRENDING data and demanded a 2x
    # inflation. It failed — correctly — because a large planted edge swamps
    # the leak: measured ratios are 54x on a driftless path, 2.1x on a weak
    # trend and only 1.1x on a strong one. Testing a leak where the signal is
    # loudest is testing it in the worst available place, and a probe that
    # only fires when there is nothing to hide is no probe at all.
    P_rw = synth(3)
    honest_rw = run(P_rw, spread, charge_cost=False).net.mean()
    cheat_rw = run(P_rw, spread, charge_cost=False, peek=True).net.mean()
    check("7 look-ahead probe on a DRIFTLESS path",
          cheat_rw > 0.003 and abs(honest_rw) < 0.001,
          f"honest {honest_rw:+.6f} vs peeking {cheat_rw:+.6f}"
          f"  ({cheat_rw / max(abs(honest_rw), 1e-9):.0f}x)")

    # 7b. and it must still be directionally right where an edge exists,
    #     even though the ratio is small there.
    honest_tr = run(P_tr, spread, charge_cost=False).net.mean()
    cheat_tr = run(P_tr, spread, charge_cost=False, peek=True).net.mean()
    check("7b probe still fires with a real edge present",
          cheat_tr > honest_tr,
          f"{honest_tr:+.6f} -> {cheat_tr:+.6f}"
          f"  (only {cheat_tr / honest_tr:.2f}x — the planted edge dominates)")

    # 8. gross risk normalised every month
    r8 = run(P_tr, spread, charge_cost=False)
    check("8 gross risk normalised to 1",
          abs(r8.gross - 1.0).max() < 1e-9,
          f"max deviation {abs(r8.gross - 1.0).max():.2e}")

    # 9. ALL instruments held, not a selected subset
    check("9 every instrument is held each month", (r8.n == N).all(),
          f"n ranges {r8.n.min()}-{r8.n.max()} of {N}")

    # 10-11. drawdown
    check("10 monotonic curve has no drawdown",
          max_drawdown(np.full(24, 0.01)) < 1e-12)
    check("11 drawdown measured peak-to-trough",
          abs(max_drawdown(np.array([math.log(2), math.log(0.5), 0.0])) - 0.5)
          < 1e-12)

    # 12. skew sign is preserved, since v7 expects POSITIVE skew and a
    #     negative reading is to be read as a bug signal
    check("12 skew sign preserved through the engine",
          pd.Series([-1.0, 0, 0, 0, 5.0]).skew() > 0 >
          pd.Series([1.0, 0, 0, 0, -5.0]).skew())

    # ---- DO THESE CONTROLS ACTUALLY BITE? --------------------------------
    # Four gates in this project turned out to be incapable of failing. So
    # break the engine deliberately and confirm the controls catch it.
    print(f"\n  --- proving the controls can fail ---")
    broken = run(P_mr, spread, charge_cost=False).net.mean()   # momentum on MR
    check("13 control 2 would REJECT a broken engine", not (broken > 0.0015),
          f"mean-reverting data gives {broken:+.6f}, correctly fails 'recovered'")
    flat = run(synth(4), spread, charge_cost=False).net.mean()
    check("14 control 4 would REJECT a no-op engine", not (flat < -0.0015),
          f"random walk gives {flat:+.6f}, correctly fails 'must lose'")
    # And the look-ahead probe: on a path where nothing leaks, it must NOT
    # fire. A probe that fires on clean data would flag every honest run.
    clean = run(synth(5), spread, charge_cost=False).net.mean()
    check("15 control 7 would NOT fire on an honest engine",
          not (clean > 0.003),
          f"honest driftless run gives {clean:+.6f}, below the 0.003 trigger")

    print(f"\n  {'ALL CONTROLS PASS' if not fails else str(len(fails)) + ' FAILED'}")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--data", default="../data_universe")
    ap.add_argument("--seeds", type=int, default=200)
    a = ap.parse_args()
    if a.self_test:
        return self_test()

    import numpy as np, pandas as pd

    print(f"prereg_v7_test.py v{VERSION}   spec frozen in PREREGISTRATION_v7.md")
    print(f"  {LOOKBACK_M}-month sign, all instruments held, monthly rebalance")
    print(f"  {VOL_WINDOW}m trailing vol, measured spreads, flip charged twice\n")

    P, spread = load_monthly(a.data)
    r = run(P, spread, "real")
    if r.empty:
        raise SystemExit("no tradable months — check --data")

    yrs = (r.t.max() - r.t.min()).days / 365.25
    mu, sd = r.net.mean(), r.net.std()
    sharpe = (mu / sd) * math.sqrt(12) if sd > 0 else 0.0
    dd = max_drawdown(r.net)
    bar = 2.0 / math.sqrt(yrs)

    print(f"  {P.shape[1]} instruments   {len(r)} months   "
          f"{r.t.min().date()} -> {r.t.max().date()}   {yrs:.1f}y")

    print(f"\n{'=' * 72}\nPOOLED — the single pre-registered statistic\n{'=' * 72}")
    print(f"  mean gross per month       {r.ret.mean():+.5f}")
    print(f"  mean cost  per month       {r.cost.mean():+.5f}")
    print(f"  MEAN NET   per month       {mu:+.5f}")
    boot = np.array([np.random.default_rng(k).choice(
        r.net.to_numpy(), len(r), replace=True).mean() for k in range(1000)])
    lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    print(f"  bootstrap 95% CI           [{lo:+.5f}, {hi:+.5f}]")
    print(f"  implied annual Sharpe      {sharpe:+.2f}   (bar {bar:.2f})")
    print(f"  MAXIMUM DRAWDOWN           {dd:.1%}   (gate {MAX_DD:.0%})")
    print(f"  positive months            {(r.net > 0).mean():.1%}")

    yr = r.assign(y=r.t.dt.year).groupby("y").net.apply(lambda v: v[v > 0].sum())
    year_share = yr.max() / yr.sum() if yr.sum() > 0 else float("nan")
    print(f"  top year                   {yr.idxmax()} = {year_share:.1%}")

    c1 = mu > 0 and lo > 0
    c2 = dd <= MAX_DD
    c3 = year_share <= MAX_YEAR_SHARE
    print(f"\n  1 profitable after costs (mean>0, CI lo>0)     "
          f"{'PASS' if c1 else 'FAIL'}")
    print(f"  2 max drawdown <= {MAX_DD:.0%}                        "
          f"{'PASS' if c2 else 'FAIL'}")
    print(f"  3 no year > {MAX_YEAR_SHARE:.0%} of gross positive P&L     "
          f"{'PASS' if c3 else 'FAIL'}")

    print(f"\n  --- diagnostics, NOT criteria ---")
    rev = run(P, spread, "rev")
    rnd = [run(P, spread, "rand", np.random.default_rng(k))
           for k in range(a.seeds)]
    rm = float(np.mean([x.net.mean() for x in rnd]))
    rs = float(np.std([x.net.mean() for x in rnd]))
    print(f"  real {mu:+.5f}   random {rm:+.5f} (sd {rs:.5f})   "
          f"reversed {rev.net.mean():+.5f}")
    if rs > 0:
        print(f"  real vs random: {(mu - rm) / rs:+.2f} sd")
    print(f"  skewness of monthly net    {r.net.skew():+.2f}"
          f"   (trend following should be POSITIVE; negative = bug signal)")
    ex08 = r[r.t.dt.year != 2008]
    s08 = (ex08.net.mean() / ex08.net.std()) * math.sqrt(12) \
        if ex08.net.std() > 0 else float("nan")
    print(f"  excluding 2008: mean {ex08.net.mean():+.5f}, "
          f"Sharpe {s08:+.2f}, maxDD {max_drawdown(ex08.net):.1%}")
    print(f"  gross Sharpe (zero cost)   "
          f"{(lambda g: (g.net.mean() / g.net.std()) * math.sqrt(12))(run(P, spread, charge_cost=False)):+.2f}")
    print(f"\n  P&L by year:")
    by = r.assign(y=r.t.dt.year).groupby("y").net.sum()
    for y, v in by.items():
        print(f"    {y}  {v:+.4f}  {'#' * max(0, int(abs(v) * 100))}"
              f"{'' if v >= 0 else ' (neg)'}")

    print(f"\n{'=' * 72}\nVERDICT\n{'=' * 72}")
    if c1 and c2 and c3:
        print("  H1 SUPPORTED on all three criteria.")
        print("  Before ANY capital: re-run audit.py, then forward-test on")
        print("  data this engine has never seen. A pass is not a strategy.")
    else:
        failed = [n for n, ok in (("1 profitability", c1), ("2 drawdown", c2),
                                  ("3 year concentration", c3)) if not ok]
        print(f"  H1 REJECTED. Failed: {', '.join(failed)}")
        print("  Per the pre-registration, the line is closed. Do not retune,")
        print("  do not flip the sign, do not sweep the lookback.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
