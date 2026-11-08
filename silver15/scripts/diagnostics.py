#!/usr/bin/env python3
"""Signal diagnostics that must pass BEFORE a meta-model is fitted.

A logistic P(win) is a filter on an existing edge, not a source of one. Fitted
on a signal with no edge it will still produce a number, and purged
walk-forward CV will not stop it -- it will just make the number look careful.
These checks are the gate.

    python diagnostics.py --all              # everything
    python diagnostics.py --null             # the decisive one
    python diagnostics.py --costs            # spread sensitivity
    python diagnostics.py --horizon          # does resid_z predict anything?
    python diagnostics.py --self-test        # offline, no data needed

WHY EACH CHECK EXISTS
---------------------
--costs    A mean P&L worse than the stop loss is structurally impossible and
           means the cost model is swamping the barriers. Found exactly that:
           spread_usd=0.08 exceeded 15m ATR for most of 2016-2019, so trades
           that HIT their take-profit were booked as losses.

--null     With tp/sl barriers, a driftless coin flip wins sl/(tp+sl) of the
           time -- 60% at tp=1.0/sl=1.5. That, not 50%, is the bar. Compares
           the real signal against reversed and randomised sides at ZERO cost.
           If it does not clear random by several standard deviations
           frictionlessly, the signal has no direction and nothing downstream
           can rescue it.

--horizon  Separates "no effect" from "effect too small" from "effect
           contaminated by drift". These need different fixes and look
           identical in a P&L curve.

CAVEAT ON THE NULL TEST
-----------------------
resid_z autocorrelates at +0.96 (1 bar), so signals fire in clusters and the
trades are not independent draws. The reported standard deviation across seeds
is therefore OPTIMISTIC -- the effective sample is much smaller than the trade
count. Treat a marginal pass as a fail.
"""

from __future__ import annotations

import argparse
import os
import sys
import types

VERSION = "0.1"


def _stub_sklearn() -> None:
    """Let silver_mr import without sklearn.

    Everything here is pure pandas/numpy -- the point is to run HIS feature
    and barrier code, not a reimplementation of it that could quietly differ.
    Only the meta-model needs sklearn, and by design none of these checks
    touch it.
    """
    if "sklearn" in sys.modules:
        return
    try:
        import sklearn  # noqa: F401
        return
    except ImportError:
        pass
    m = types.ModuleType("sklearn")
    lm = types.ModuleType("sklearn.linear_model")

    class LogisticRegression:                     # pragma: no cover
        def __init__(self, *a, **k):
            raise RuntimeError("sklearn stubbed: diagnostics never fit a model")

    lm.LogisticRegression = LogisticRegression
    m.linear_model = lm
    sys.modules["sklearn"] = m
    sys.modules["sklearn.linear_model"] = lm


def load_all(data_dir: str):
    import silver_mr as S
    xag = S.load_csv(os.path.join(data_dir, "xagusd_15m.csv"))
    xau = S.load_csv(os.path.join(data_dir, "xauusd_15m.csv"))
    dxy = S.load_csv(os.path.join(data_dir, "eurusd_15m.csv")).rdiv(1.0)
    df = S.build_features(xag, xau, dxy, S.CFG)
    return S, df


# --------------------------------------------------------------------------

def costs(S, df, measured: float) -> None:
    import numpy as np
    print("\n15-minute ATR vs the assumed spread")
    print("=" * 72)
    a = df[["atr", "close"]].dropna()
    print(f"  {'year':<6}{'ATR $':>9}{'median px':>12}{'half-spread in ATR':>22}")
    for y, g in a.groupby(a.index.year):
        med = float(g.atr.median())
        ratio = S.CFG["spread_usd"] / (2 * med)
        flag = "  <-- TP booked as a loss" if ratio > S.CFG["tp_atr"] else ""
        print(f"  {y:<6}{med:>9.4f}{float(g.close.median()):>12.2f}"
              f"{ratio:>22.2f}{flag}")
    print(f"\n  Take-profit is +{S.CFG['tp_atr']} ATR. Any year where the last")
    print("  column exceeds that cannot book a winner, however good the entry.")

    sig = S.primary_signal(df, S.CFG)
    print(f"\n{'spread_usd':>12}{'trades':>9}{'win rate':>11}{'mean pnl_atr':>15}"
          f"{'total ATR':>13}")
    for sp in (S.CFG["spread_usd"], 0.04, measured, 0.010, 0.0):
        cfg = dict(S.CFG); cfg["spread_usd"] = sp
        tr = S.triple_barrier(df, sig, cfg)
        tag = ""
        if abs(sp - measured) < 1e-9:
            tag = "  <-- measured"
        elif abs(sp - S.CFG["spread_usd"]) < 1e-9:
            tag = "  <-- current CFG"
        print(f"{sp:>12.3f}{len(tr):>9,}{tr.win.mean():>10.2%}"
              f"{tr.pnl_atr.mean():>+15.4f}{tr.pnl_atr.sum():>+13.1f}{tag}")


def null_test(S, df, seeds: int = 10) -> bool:
    import numpy as np, pandas as pd
    sig = S.primary_signal(df, S.CFG)
    geom = S.CFG["sl_atr"] / (S.CFG["tp_atr"] + S.CFG["sl_atr"])
    print("\nNULL TEST -- does the signal carry direction?")
    print("=" * 72)
    print(f"  Barriers tp={S.CFG['tp_atr']} sl={S.CFG['sl_atr']}: a driftless")
    print(f"  coin flip wins {geom:.1%} by geometry alone. That is the bar.\n")

    passed = True
    for sp in (0.0, 0.019):
        cfg = dict(S.CFG); cfg["spread_usd"] = sp
        print(f"  --- spread_usd = {sp} ---")
        print(f"  {'variant':<24}{'trades':>8}{'win rate':>11}{'mean pnl_atr':>15}")
        real = S.triple_barrier(df, sig, cfg)
        print(f"  {'REAL signal':<24}{len(real):>8,}{real.win.mean():>10.2%}"
              f"{real.pnl_atr.mean():>+15.4f}")
        rev = S.triple_barrier(df, -sig, cfg)
        print(f"  {'REVERSED signal':<24}{len(rev):>8,}{rev.win.mean():>10.2%}"
              f"{rev.pnl_atr.mean():>+15.4f}")
        wr = []
        for seed in range(seeds):
            rng = np.random.default_rng(seed)
            # pandas 3 returns a READ-ONLY array from .values, so mutating it
            # in place raises. Build a fresh writable array instead -- this
            # works on both pandas 2 and 3.
            vals = sig.to_numpy(dtype=int, copy=True)
            nz = vals != 0
            vals[nz] = rng.choice([-1, 1], size=int(nz.sum()))
            rs = pd.Series(vals, index=sig.index, dtype=int)
            wr.append(S.triple_barrier(df, rs, cfg).win.mean())
        mu, sd = float(np.mean(wr)), float(np.std(wr))
        print(f"  {'RANDOM side':<24}{len(real):>8,}{mu:>10.2%}"
              f"{'':>15}   (sd {sd:.4f}, {seeds} seeds)")
        edge_sd = (real.win.mean() - mu) / sd if sd > 0 else 0.0
        print(f"  real beats random by {real.win.mean()-mu:+.4f} "
              f"= {edge_sd:+.2f} standard deviations")
        if sp == 0.0:
            if edge_sd < 3:
                print("  >> FAIL: inside noise frictionlessly. Re-specify the")
                print("  >> signal. Do not fit a meta-model on this.")
                passed = False
            else:
                print("  >> PASS at zero cost. Now check it survives the spread.")
        print()
    print("  Reminder: resid_z autocorrelates at ~0.96, so these trades are")
    print("  clusters, not independent draws. The sd above is optimistic.")
    return passed


def horizon(S, df, measured: float) -> None:
    import numpy as np, pandas as pd
    z, c, atr = df["resid_z"], df["close"], df["atr"]
    in_sess = (df["hour"] >= 7) & (df["hour"] < 16)
    hurdle = measured / 2 / float(df.atr.median())
    print("\nHORIZON STUDY -- forward return (ATR units) vs resid_z")
    print("=" * 72)
    print(f"  {'bars':>6}{'corr(z,fwd)':>14}{'fwd | z<=-2':>14}{'fwd | z>=+2':>14}")
    for h in (4, 12, 24, 48, 96, 192, 384):
        fwd = (c.shift(-h) - c) / atr
        d = pd.DataFrame({"z": z, "f": fwd})[in_sess]
        d = d.replace([np.inf, -np.inf], np.nan).dropna()
        print(f"  {h:>6}{d.z.corr(d.f):>+14.4f}"
              f"{d[d.z <= -2].f.mean():>+14.4f}{d[d.z >= 2].f.mean():>+14.4f}")
    print(f"\n  Mean reversion needs: corr NEGATIVE, 'z<=-2' POSITIVE,")
    print(f"  'z>=+2' NEGATIVE, and magnitude above ~{hurdle:.2f} ATR of cost.")
    print("  If both columns go positive as the horizon grows, that is the")
    print("  asset's drift, not reversion -- lengthening max_hold will not help.")

    print("\n  resid_z autocorrelation (it is a rolling sum, so it is smooth):")
    for lag in (1, 4, 12, 24, 48, 96):
        print(f"    lag {lag:>3}: {z.autocorr(lag):+.4f}")
    print("  High values mean signals fire in clusters, so the effective")
    print("  sample size is far below the trade count.")


# --------------------------------------------------------------------------

def self_test() -> int:
    fails = []

    def check(n, c, d=""):
        print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"  {d}" if not c else ""))
        if not c:
            fails.append(n)

    print(f"diagnostics.py v{VERSION}")
    print(f"  file: {os.path.abspath(__file__)}")
    import numpy as np, pandas as pd
    print(f"  pandas {pd.__version__}   numpy {np.__version__}\n")

    print("sklearn stub")
    _stub_sklearn()
    check("sklearn importable (real or stubbed)", "sklearn" in sys.modules
          or __import__("importlib").util.find_spec("sklearn") is not None)

    print("\nsilver_mr imports and exposes what the checks need")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import silver_mr as S
    for fn in ("load_csv", "build_features", "primary_signal", "triple_barrier"):
        check(f"silver_mr.{fn} present", hasattr(S, fn))
    check("CFG has tp_atr/sl_atr/spread_usd",
          all(k in S.CFG for k in ("tp_atr", "sl_atr", "spread_usd")))

    print("\nbarrier geometry baseline")
    geom = S.CFG["sl_atr"] / (S.CFG["tp_atr"] + S.CFG["sl_atr"])
    check("coin-flip win rate is between 50% and 80%", 0.5 <= geom <= 0.8,
          f"{geom:.3f}")

    print("\npandas API used here works on this version")
    idx = pd.date_range("2024-01-01", periods=200, freq="15min", tz="UTC")
    s = pd.Series(np.arange(200.0), index=idx)
    check("Series.autocorr", isinstance(float(s.autocorr(4)), float))
    d = pd.DataFrame({"a": s, "b": s * 2})
    check("groupby on index.year", len(d.groupby(d.index.year)) >= 1)
    check("Series.corr", abs(float(d.a.corr(d.b)) - 1.0) < 1e-9)
    check("rdiv (used for the DXY proxy)",
          abs(float(pd.Series([2.0]).rdiv(1.0).iloc[0]) - 0.5) < 1e-12)

    # pandas 3 made .values read-only, which broke the null test's side
    # randomisation at runtime -- after the expensive part had already run.
    # Exercise the exact mutation pattern here, where it costs nothing.
    print("\nnull-test randomisation (the pandas 3 read-only trap)")
    base = pd.Series([0, 1, -1, 0, 1], index=range(5), dtype=int)
    try:
        rng = np.random.default_rng(0)
        vals = base.to_numpy(dtype=int, copy=True)
        nz = vals != 0
        vals[nz] = rng.choice([-1, 1], size=int(nz.sum()))
        rs = pd.Series(vals, index=base.index, dtype=int)
        ok = (rs == 0).tolist() == (base == 0).tolist()
        check("sides randomised without mutating a read-only array", ok,
              "zero/non-zero pattern changed")
    except Exception as exc:                              # noqa: BLE001
        check("sides randomised without mutating a read-only array", False,
              f"{type(exc).__name__}: {exc}")

    print("\ngroupby-apply used by the by-hour breakdown")
    d2 = pd.DataFrame({"ra": np.arange(48.0), "rb": np.arange(48.0) * 2},
                      index=pd.date_range("2024-01-01", periods=48, freq="h",
                                          tz="UTC"))
    try:
        by_hour = pd.Series({h: g.ra.corr(g.rb)
                             for h, g in d2.groupby(d2.index.hour)})
        check("per-hour correlation without include_groups", len(by_hour) == 24,
              f"got {len(by_hour)}")
    except Exception as exc:                              # noqa: BLE001
        check("per-hour correlation without include_groups", False,
              f"{type(exc).__name__}: {exc}")

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
    ap.add_argument("--measured-spread", type=float, default=0.019,
                    help="round-trip, from oanda_intraday.py --sides")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--costs", action="store_true")
    ap.add_argument("--null", action="store_true")
    ap.add_argument("--horizon", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()

    if a.version:
        print(f"diagnostics.py v{VERSION}")
        print(f"  running from: {os.path.abspath(__file__)}")
        print(f"  python      : {sys.executable}")
        sys.exit(0)
    if a.self_test:
        sys.exit(self_test())

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    _stub_sklearn()
    print(f"\ndiagnostics.py v{VERSION}  [{os.path.abspath(__file__)}]")
    S, df = load_all(a.data)
    print(f"  {len(df):,} bars   {df.index.min()} -> {df.index.max()}")

    ran = False
    if a.costs or a.all:
        costs(S, df, a.measured_spread); ran = True
    if a.null or a.all:
        null_test(S, df, a.seeds); ran = True
    if a.horizon or a.all:
        horizon(S, df, a.measured_spread); ran = True
    if not ran:
        ap.print_help()


if __name__ == "__main__":
    main()
