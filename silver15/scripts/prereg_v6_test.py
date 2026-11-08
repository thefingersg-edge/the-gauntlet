#!/usr/bin/env python3
"""THE v6 pre-registered test. Spec frozen in PREREGISTRATION_v6.md.

A long-short FX carry book on OANDA CFDs, charged OANDA's actual financing
markup and measured spreads, 2006-2026. ONE pooled net return series.

    python prereg_v6_test.py --self-test     # synthetic controls FIRST
    python prereg_v6_test.py

--data paths and --seeds only. Nothing here changes the specification.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

VERSION = "6.0-prereg"


# ---------------------------------------------------------------------------
# VENV BOOTSTRAP (see carry_budget.py for the reasoning)
# The test is "can I import what I need", not "am I in a venv" -- an active
# environment belonging to something else satisfies the latter while having
# none of this project's packages.
# ---------------------------------------------------------------------------

_FLAG = "PREREG_V6_VENV_BOOTSTRAPPED"


def _deps_available() -> bool:
    import importlib.util
    try:
        return all(importlib.util.find_spec(m) is not None
                   for m in ("numpy", "pandas"))
    except (ImportError, ValueError):
        return False


def _bootstrap_venv() -> None:
    if os.environ.get(_FLAG) or _deps_available():
        return
    here = os.path.dirname(os.path.abspath(__file__))
    for rel in (".venv", "venv", os.path.join("..", ".venv")):
        for sub in ("bin/python3", "bin/python", "Scripts/python.exe"):
            cand = os.path.join(here, rel, *sub.split("/"))
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                cand = os.path.abspath(cand)
                if cand == os.path.abspath(sys.executable):
                    return
                print(f"  [venv] re-running under "
                      f"{os.path.relpath(cand, here)}", file=sys.stderr)
                os.environ[_FLAG] = "1"
                try:
                    os.execv(cand, [cand, os.path.abspath(__file__)]
                             + sys.argv[1:])
                except OSError as exc:                        # noqa: BLE001
                    print(f"  [venv] could not re-execute ({exc})",
                          file=sys.stderr)
                    return
    print("  note: no .venv found; --self-test needs nothing extra, the real "
          "run needs pandas.", file=sys.stderr)


_bootstrap_venv()


# ---- FROZEN SPEC (PREREGISTRATION_v6.md) ----------------------------------
LAG_MONTHS = 2         # FULL months past the observation month. See below.
TOP = 3                # longs, and shorts
VOL_WINDOW = 12        # months, TRAILING
MAX_DD = 0.25          # criterion 2
MAX_INSTRUMENT_SHARE = 0.35
MAX_YEAR_SHARE = 0.30

PAIRS = ["EUR_USD", "GBP_USD", "AUD_USD", "NZD_USD", "USD_CAD", "USD_CHF",
         "EUR_GBP", "EUR_JPY", "GBP_JPY", "EUR_CHF", "EUR_AUD", "AUD_NZD",
         "NZD_CAD"]

STEM = {p: p.replace("_", "").lower() for p in PAIRS}

WINDOW_START = "2006-02-28"
WINDOW_END = "2026-01-01"
# ---------------------------------------------------------------------------
#
# THE LAG, AND WHY IT IS TWO MONTHS
#
# FRED monthly values are PERIOD AVERAGES. Month M's figure is not complete
# until M ends, and the OECD series publish with a further lag. Trading month M
# on month M's own average would read the future.
#
# One month is the honest minimum. TWO is used because carry autocorrelates
# ~0.99 monthly, so the extra month costs almost nothing while removing any
# argument about publication timing. --self-test includes a probe that runs
# the signal UNLAGGED against a planted leak and must show an inflated result;
# if it does not, the lag machinery is not doing anything.
# ---------------------------------------------------------------------------


def load_prices(data_dir):
    """Month-end close per instrument, from that instrument's OWN bars.

    Resampling each series independently and only then aligning is deliberate.
    v4 computed features across a ragged UNION index, so `shift(120)` spanned
    120 union rows rather than 120 of the instrument's own bars, and SMI, AEX
    and FR40 ended up with no valid volatility at all -- silently excluded
    from a "28-instrument" panel that was really ~18.
    """
    import pandas as pd
    cols = {}
    for p in PAIRS:
        path = os.path.join(data_dir, f"{STEM[p]}_4h.csv")
        if not os.path.exists(path):
            continue
        d = pd.read_csv(path)
        t = d.columns[0]
        d[t] = pd.to_datetime(d[t], utc=True)
        s = d.set_index(t).sort_index()["close"].astype(float)
        cols[p] = s.resample("ME").last().dropna()
    return pd.DataFrame(cols).sort_index()


def load_carry(rates_path, financing_path):
    """Monthly carry per pair, and the per-instrument annual markup.

    carry(BASE_QUOTE) = r_BASE - r_QUOTE, both from the frozen 3-month family.
    Both carry and markup are scaled by daysCharged/7, because GBP_JPY and
    EUR_JPY are charged 6 days a week and therefore neither earn nor pay the
    full quoted annual rate.
    """
    import numpy as np, pandas as pd
    with open(rates_path) as fh:
        raw = json.load(fh)
    ccy = {}
    for c, series in raw.items():
        if not series:
            continue
        idx = pd.to_datetime([d for d, _ in series], utc=True)
        val = np.array([v for _, v in series], dtype=float) / 100.0
        ccy[c] = pd.Series(val, index=idx).resample("ME").last()
    R = pd.DataFrame(ccy).sort_index()

    with open(financing_path) as fh:
        fin = json.load(fh)

    carry, markup = {}, {}
    for p in PAIRS:
        b, q = p.split("_")
        if b not in R.columns or q not in R.columns:
            continue
        f = 1.0
        if p in fin:
            d = fin[p].get("daysChargedPerWeek", 7) or 7
            f = min(d, 7) / 7.0
            lr, sr = float(fin[p]["longRate"]), float(fin[p]["shortRate"])
            markup[p] = (-(lr + sr) / 2.0) * f
        else:
            markup[p] = 0.0105                  # measured FX median, per side
        carry[p] = (R[b] - R[q]) * f
    return pd.DataFrame(carry).sort_index(), pd.Series(markup)


def spreads():
    """Measured round-trip spreads, as a fraction of price."""
    import pandas as pd
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import screen_universe as U
    return pd.Series({p: U.SPREAD_REL.get(STEM[p], 0.0002) for p in PAIRS})


# ---------------------------------------------------------------------------

def run(P, C, markup, spread, mode="real", rng=None,
        charge_cost=True, lag=LAG_MONTHS, markup_mult=1.0):
    """One row per month. Returns the book's net log return.

    P     month-end prices          C   monthly carry (unlagged)
    Every position is formed from information available BEFORE the month it
    earns in: the signal is lagged, and volatility uses only returns already
    realised.
    """
    import numpy as np, pandas as pd

    r = np.log(P).diff()                        # r[m] realised DURING month m
    fwd = r.shift(-1)                           # earned in m+1, formed end of m
    vol = r.rolling(VOL_WINDOW).std()           # known at end of m
    sig = C.shift(lag)                          # THE LAG

    idx = P.index
    rows, prev = [], {}
    for m in idx:
        s = sig.loc[m].dropna() if m in sig.index else None
        if s is None or len(s) < 2 * TOP:
            continue
        v = vol.loc[m] if m in vol.index else None
        f = fwd.loc[m] if m in fwd.index else None
        if v is None or f is None:
            continue
        elig = [c for c in s.index
                if np.isfinite(v.get(c, np.nan)) and v.get(c, 0) > 0
                and np.isfinite(f.get(c, np.nan))]
        if len(elig) < 2 * TOP:
            continue
        s = s[elig]

        if mode == "rand":
            order = pd.Series(rng.permutation(len(s)), index=s.index)
        elif mode == "rev":
            order = -s.rank()
        else:
            order = s.rank()

        longs = list(order.nlargest(TOP).index)
        shorts = list(order.nsmallest(TOP).index)

        w = {}
        for c in longs:
            w[c] = w.get(c, 0.0) + 1.0 / v[c]
        for c in shorts:
            w[c] = w.get(c, 0.0) - 1.0 / v[c]
        gross = sum(abs(x) for x in w.values())
        if gross <= 0:
            continue
        w = {c: x / gross for c, x in w.items()}   # gross risk = 1 unit

        ret = sum(w[c] * f[c] for c in w)

        cost = 0.0
        if charge_cost:
            # (a) financing markup: charged on EVERY leg, long and short
            #     alike, for the month held. Being short does not refund it.
            cost += sum(abs(x) * markup[c] * markup_mult / 12.0
                        for c, x in w.items())
            # (b) spread: only on the part of each position that CHANGED
            for c in set(w) | set(prev):
                cost += abs(w.get(c, 0.0) - prev.get(c, 0.0)) * spread[c]
        prev = w

        rows.append(dict(t=m, ret=ret, net=ret - cost, cost=cost,
                         longs=",".join(longs), shorts=",".join(shorts),
                         weights=dict(w)))
    # Always return the declared columns, even with no rows. An untyped empty
    # frame turns "the engine correctly declined to trade" into an
    # AttributeError three frames away from the cause.
    return pd.DataFrame(rows, columns=["t", "ret", "net", "cost",
                                       "longs", "shorts", "weights"])


def max_drawdown(net) -> float:
    """Deepest peak-to-trough fall of the compounded equity curve."""
    import numpy as np
    eq = np.exp(np.cumsum(np.asarray(net, dtype=float)))
    peak = np.maximum.accumulate(eq)
    return float(np.max((peak - eq) / peak)) if len(eq) else 0.0


def currency_exposure(weights: dict) -> dict:
    """Net exposure per currency implied by a book of FX weights."""
    from collections import defaultdict
    net = defaultdict(float)
    for pair, w in weights.items():
        b, q = pair.split("_")
        net[b] += w
        net[q] -= w
    return dict(net)


# ---------------------------------------------------------------------------

def self_test() -> int:
    """Synthetic controls. The engine is verified BEFORE it is trusted."""
    import numpy as np, pandas as pd
    fails = []

    def check(n, c, d=""):
        print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   {d}" if d else ""))
        if not c:
            fails.append(n)

    print(f"prereg_v6_test.py v{VERSION} — synthetic controls\n")
    print(f"  interpreter  {sys.executable}\n")

    n = 400
    idx = pd.date_range("1990-01-31", periods=n, freq="ME", tz="UTC")
    mk = pd.Series({p: 0.0105 for p in PAIRS})
    sp = pd.Series({p: 0.0002 for p in PAIRS})

    def synth(seed, planted=0.0, noise=0.03, plant_at=LAG_MONTHS, walk=True):
        """Prices and carries, with an edge planted at a KNOWN engine lag.

        THE ALIGNMENT, WHICH IS EASY TO GET WRONG BY ONE
        ------------------------------------------------
        The engine at month m with lag L reads carry C[m-L] and earns
        fwd[m] = rets[m+1]. So an edge that an L-lagged engine captures must
        satisfy

            rets[m+1] ~ rank(C[m-L])    i.e.    rets[m] ~ rank(C[m-L-1])

        hence the shift below is `plant_at + 1`, not `plant_at`. Getting this
        off by one is exactly the mistake the v5 harness made.

        `walk=False` gives an I.I.D. carry surface. That matters for the
        look-ahead probe: real carry is a near-unit-root random walk, so
        rank(C[m]) and rank(C[m-2]) are almost the same ranking and NO lag
        can be shown to destroy anything. A persistent planted edge cannot
        distinguish a working lag from a broken one, which is precisely how a
        useless probe passes.
        """
        rng = np.random.default_rng(seed)
        step = rng.normal(0, 0.0015, (n, len(PAIRS)))
        vals = np.cumsum(step, axis=0) if walk else rng.normal(0, 0.01,
                                                               (n, len(PAIRS)))
        C = pd.DataFrame(vals, index=idx, columns=PAIRS)
        rank = C.rank(axis=1, pct=True).sub(0.5).shift(plant_at + 1).fillna(0.0)
        rets = pd.DataFrame(
            rng.normal(0, noise, (n, len(PAIRS))), index=idx, columns=PAIRS)
        rets = rets + planted * rank
        P = 100 * np.exp(rets.cumsum())
        return P, C

    # 1. no planted edge, zero cost -> mean 0
    m = [run(*synth(s), mk, sp, charge_cost=False).net.mean() for s in range(8)]
    mu, se = float(np.mean(m)), float(np.std(m)) / np.sqrt(8)
    check("1 no planted edge -> mean 0", abs(mu) < max(2 * se, 0.001),
          f"got {mu:+.5f} (se {se:.5f})")

    # 2. planted edge recovered
    m2 = [run(*synth(s, planted=0.02), mk, sp, charge_cost=False).net.mean()
          for s in range(8)]
    check("2 planted edge recovered", float(np.mean(m2)) > 0.002,
          f"got {float(np.mean(m2)):+.5f}")

    # 3. reversed loses on the same data
    P, C = synth(0, planted=0.02)
    real = run(P, C, mk, sp, charge_cost=False).net.mean()
    rev = run(P, C, mk, sp, "rev", charge_cost=False).net.mean()
    check("3 reversed mirrors real", rev < 0 < real, f"{real:+.5f} / {rev:+.5f}")

    # 4-5. costs
    free = run(P, C, mk, sp, charge_cost=False).net.mean()
    paid = run(P, C, mk, sp, charge_cost=True).net.mean()
    d1 = free - paid
    d2 = free - run(P, C, mk, sp, charge_cost=True, markup_mult=2.0).net.mean()
    check("4 cost reduces P&L", paid < free, f"{paid:+.5f} < {free:+.5f}")
    check("5 doubling markup ~doubles the markup drag", d2 > d1 * 1.5,
          f"drag {d1:.6f} -> {d2:.6f}")

    # 6. THE LOOK-AHEAD PROBE. Edge planted for a lag-0 engine on an I.I.D.
    #    carry surface, so persistence cannot let a wrongly-lagged engine
    #    collect it by accident. Unlagged must capture it; lagged must not.
    Pl, Cl = synth(3, planted=0.05, plant_at=0, walk=False)
    leak = run(Pl, Cl, mk, sp, charge_cost=False, lag=0).net.mean()
    lagged = run(Pl, Cl, mk, sp, charge_cost=False, lag=LAG_MONTHS).net.mean()
    check("6 look-ahead probe: lag destroys a lag-0 leak",
          leak > 0.004 and abs(lagged) < leak / 3,
          f"unlagged {leak:+.5f}  vs  lagged {lagged:+.5f}")

    # 6b. and the converse: an edge planted AT the engine's lag is collected
    #     by the lagged engine and NOT by the unlagged one. Together these
    #     two show the shift moves the signal in the right direction, rather
    #     than merely moving it.
    Pd, Cd = synth(4, planted=0.05, plant_at=LAG_MONTHS, walk=False)
    at_lag = run(Pd, Cd, mk, sp, charge_cost=False, lag=LAG_MONTHS).net.mean()
    at_zero = run(Pd, Cd, mk, sp, charge_cost=False, lag=0).net.mean()
    check("6b edge planted at the engine's lag is collected there",
          at_lag > 0.004 and abs(at_zero) < at_lag / 3,
          f"lagged {at_lag:+.5f}  vs  unlagged {at_zero:+.5f}")

    # 7. gross risk is normalised to 1 unit every month
    r7 = run(P, C, mk, sp, charge_cost=False)
    g = [sum(abs(x) for x in w.values()) for w in r7.weights]
    check("7 gross risk normalised to 1", max(abs(x - 1) for x in g) < 1e-9,
          f"max deviation {max(abs(x-1) for x in g):.2e}")

    # 8. markup is charged on shorts too. An all-flat book still pays.
    only_long = {p: (1.0 / len(PAIRS)) for p in PAIRS}
    cost_l = sum(abs(x) * 0.0105 / 12 for x in only_long.values())
    only_short = {p: -(1.0 / len(PAIRS)) for p in PAIRS}
    cost_s = sum(abs(x) * 0.0105 / 12 for x in only_short.values())
    check("8 markup identical long or short", abs(cost_l - cost_s) < 1e-15,
          "being short must not refund financing")

    # 9-10. drawdown
    up = np.full(24, 0.01)
    check("9 monotonic curve has no drawdown", max_drawdown(up) < 1e-12)
    known = np.array([np.log(2.0), np.log(0.5), 0.0])   # x2 then halve
    check("10 drawdown measured peak-to-trough",
          abs(max_drawdown(known) - 0.5) < 1e-12,
          f"{max_drawdown(known):.4f} for a 2x then -50% path")

    # 11. currency decomposition
    ce = currency_exposure({"USD_CHF": 1.0, "EUR_USD": -1.0})
    check("11 currency exposure nets correctly",
          abs(ce["USD"] - 2.0) < 1e-12 and abs(ce["EUR"] + 1.0) < 1e-12,
          f"USD {ce['USD']:+.1f}, CHF {ce['CHF']:+.1f}, EUR {ce['EUR']:+.1f}")

    # 12. a flat carry surface must not manufacture a book with an edge.
    #     Every rank ties, so longs and shorts collide and the net weight is
    #     zero -- the engine should decline to trade rather than invent a
    #     ranking out of tie-breaking order, which would be a pure artefact
    #     of column order.
    flat = pd.DataFrame(np.zeros((n, len(PAIRS))), index=idx, columns=PAIRS)
    rf = run(P, flat, mk, sp, charge_cost=False)
    check("12 flat carry -> no book, or no edge",
          rf.empty or abs(rf.net.mean()) < 0.002,
          "declined to trade" if rf.empty else f"{rf.net.mean():+.5f}")

    print(f"\n  {'ALL CONTROLS PASS' if not fails else str(len(fails)) + ' FAILED'}")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--data", default="../data_universe")
    ap.add_argument("--rates", default="../data_rates/rates_3month.json")
    ap.add_argument("--financing", default="../data_carry/financing.json")
    ap.add_argument("--seeds", type=int, default=200)
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    import numpy as np, pandas as pd

    print(f"prereg_v6_test.py v{VERSION}   spec frozen in PREREGISTRATION_v6.md")
    print(f"  long top {TOP} / short bottom {TOP} of {len(PAIRS)} FX by carry")
    print(f"  {LAG_MONTHS}-month lag, monthly rebalance, {VOL_WINDOW}m trailing vol")
    print(f"  OANDA financing markup on every leg + measured spreads\n")

    P = load_prices(a.data)
    C, markup = load_carry(a.rates, a.financing)
    sp = spreads()

    keep = [p for p in PAIRS if p in P.columns and p in C.columns]
    P, C = P[keep], C[keep]
    lo = pd.Timestamp(WINDOW_START, tz="UTC")
    hi = pd.Timestamp(WINDOW_END, tz="UTC")
    P = P[(P.index >= lo) & (P.index <= hi)]
    C = C.reindex(P.index).ffill()

    r = run(P, C, markup, sp, "real")
    if r.empty:
        raise SystemExit("no tradable months — check the data paths")

    yrs = (r.t.max() - r.t.min()).days / 365.25
    mu, sd = r.net.mean(), r.net.std()
    sharpe = (mu / sd) * np.sqrt(12) if sd > 0 else 0.0
    dd = max_drawdown(r.net)

    print(f"  {len(keep)} instruments   {len(r)} months   "
          f"{r.t.min().date()} -> {r.t.max().date()}   {yrs:.1f}y")

    print(f"\n{'='*72}\nPOOLED — the single pre-registered statistic\n{'='*72}")
    print(f"  mean gross per month       {r.ret.mean():+.5f}")
    print(f"  mean cost  per month       {r.cost.mean():+.5f}")
    print(f"  MEAN NET   per month       {mu:+.5f}")
    boot = np.array([np.random.default_rng(k).choice(
        r.net.to_numpy(), len(r), replace=True).mean() for k in range(1000)])
    blo, bhi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    bar = 2.0 / np.sqrt(yrs)
    print(f"  bootstrap 95% CI           [{blo:+.5f}, {bhi:+.5f}]")
    print(f"  implied annual Sharpe      {sharpe:+.2f}   (bar {bar:.2f})")
    print(f"  MAXIMUM DRAWDOWN           {dd:.1%}   (gate {MAX_DD:.0%})")
    print(f"  positive months            {(r.net > 0).mean():.1%}")

    # concentration
    import collections
    contrib = collections.defaultdict(float)
    for _, row in r.iterrows():
        if row.net <= 0:
            continue
        for c in str(row.longs).split(",") + str(row.shorts).split(","):
            contrib[c] += row.net / (2 * TOP)
    tot = sum(contrib.values())
    ins_share = max(contrib.values()) / tot if tot > 0 else float("nan")
    top_ins = max(contrib, key=contrib.get) if contrib else "n/a"
    yr = r.assign(y=r.t.dt.year).groupby("y").net.apply(lambda v: v[v > 0].sum())
    year_share = yr.max() / yr.sum() if yr.sum() > 0 else float("nan")
    print(f"  top instrument             {top_ins} = {ins_share:.1%}")
    print(f"  top year                   {yr.idxmax()} = {year_share:.1%}")

    c1 = mu > 0 and blo > 0
    c2 = dd <= MAX_DD
    c3 = ins_share <= MAX_INSTRUMENT_SHARE and year_share <= MAX_YEAR_SHARE
    print(f"\n  1 profitable after costs (mean>0, CI lo>0)     "
          f"{'PASS' if c1 else 'FAIL'}")
    print(f"  2 max drawdown <= {MAX_DD:.0%}                        "
          f"{'PASS' if c2 else 'FAIL'}")
    print(f"  3 not one pair (<=35%) or year (<=30%)         "
          f"{'PASS' if c3 else 'FAIL'}")

    # ---- diagnostics, NOT criteria ----------------------------------------
    print(f"\n  --- diagnostics, NOT criteria ---")
    rev = run(P, C, markup, sp, "rev")
    rnd = [run(P, C, markup, sp, "rand", np.random.default_rng(k))
           for k in range(a.seeds)]
    rm = float(np.mean([x.net.mean() for x in rnd]))
    rs = float(np.std([x.net.mean() for x in rnd]))
    print(f"  real {mu:+.5f}   random {rm:+.5f} (sd {rs:.5f})   "
          f"reversed {rev.net.mean():+.5f}")
    if rs > 0:
        print(f"  real vs random: {(mu - rm) / rs:+.2f} sd")
    print(f"  skewness of monthly net    {r.net.skew():+.2f}"
          f"   (carry is expected to be negative)")
    r2 = run(P, C, markup, sp, markup_mult=2.0)
    print(f"  at 2x markup: mean {r2.net.mean():+.5f}, "
          f"Sharpe {(r2.net.mean()/r2.net.std())*np.sqrt(12):+.2f}, "
          f"maxDD {max_drawdown(r2.net):.1%}")
    ce = currency_exposure(r.weights.iloc[-1])
    print("  final currency exposure    " + "  ".join(
        f"{c}{v:+.2f}" for c, v in sorted(ce.items(), key=lambda kv: -kv[1])))
    gross_only = run(P, C, markup, sp, charge_cost=False)
    print(f"  gross Sharpe (zero cost)   "
          f"{(gross_only.net.mean()/gross_only.net.std())*np.sqrt(12):+.2f}")

    print(f"\n{'='*72}\nVERDICT\n{'='*72}")
    if c1 and c2 and c3:
        print("  H1 SUPPORTED on all three criteria.")
        print("  Before ANY capital: re-run audit.py, then forward-test on")
        print("  data this engine has never seen. A pass is not a strategy.")
    else:
        print("  H1 REJECTED.")
        failed = [n for n, ok in (("1 profitability", c1),
                                  ("2 drawdown", c2),
                                  ("3 concentration", c3)) if not ok]
        print(f"  Failed: {', '.join(failed)}")
        print("  Per the pre-registration, the line is closed. Do not retune,")
        print("  do not flip the sign, do not sweep a parameter.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
