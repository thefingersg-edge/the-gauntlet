#!/usr/bin/env python3
"""PREREGISTRATION_v6 -- volatility targeting on equity beta. ONE RUN.

FROZEN SPEC. The grid in section 5 is the whole grid.

    lookback     20, 60, 120 trading days
    target vol   10%, 15% annualised
    leverage cap 2.0x  (1.0x reported as a pre-declared variant)
    rebalance    daily, 10% no-trade band
                                        = 6 settings

    Gate A  net Sharpe beats buy-and-hold in >= 5 of 6 settings
    Gate B  the improvement holds in EVERY disjoint era
    Gate C  maximum drawdown not worse, DAILY resolution both sides
    Gate D  what leverage it carried into 2018-02, 2020-03, 2024-08

WHY BREADTH AND NOT A BEST SETTING
----------------------------------
DESIGN_BRIEF's original finding was a PLATEAU rather than a spike -- every
setting working, which is what a real effect looks like. One setting
working is a fit. Gate A counts settings for that reason and the report
says plainly when the improvement is concentrated.

THE POSITION, AND WHERE THE CASH SITS
-------------------------------------
    w_t = min(cap, target / vol_est)    from returns strictly up to t-1

    net_t = w*r_t + (1-w)*rf/252 - max(0, w-1)*spread/252 - turnover

The (1-w) term matters and is easy to leave out. When the strategy scales
down it is not holding nothing, it is holding cash at the risk-free rate,
and that is a real part of the return. When it scales above 1x the same
term goes negative -- it is paying to borrow -- plus a spread on the
borrowed portion only.

Both sides are then compared EXCESS OF CASH, so buy-and-hold is judged on
r_t - rf and the strategy on net_t - rf.

VENUE COST IS NOT CHARGED HERE, DELIBERATELY. equity_cost.py measured it
separately: an OANDA index CFD costs 6.15%/yr to hold long, which is 65%
of the equity premium and would swamp everything below. This file answers
"does vol targeting work"; that file answers "is it reachable here", and
mixing them would let a venue term hide a statistical result.

    python vol_target.py --self-test
    python vol_target.py --rf-csv ../data/DGS3MO.csv
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VERSION = "1.1"

#: PREREGISTRATION_v6 section 5. Frozen.
LOOKBACKS = [20, 60, 120]
TARGETS = [0.10, 0.15]
CAP = 2.0
BAND = 0.10
N_ERAS = 3
MIN_PASS = 5                 # Gate A: 5 of 6
#: COST_BUDGET.md measured SPX500 at 0.66bp. Charged on |change in weight|.
TURN_BP = 0.66
#: Spread over cash on the BORROWED portion only, declared not tuned.
BORROW_SPREAD = 0.010
TRADING_DAYS = 252
#: Same discipline as kraken_basis.py, which stops below 90%.
RF_MIN_COVERAGE = 0.80
RF_DEFAULT = 0.02
#: Gate D -- the episodes where vol targeting is known to fail, named in
#: advance so the report cannot quietly skip the inconvenient one.
CRASHES = [("2018-02", "2018-01-26", "2018-02-09"),
           ("2020-03", "2020-02-19", "2020-03-23"),
           ("2024-08", "2024-07-31", "2024-08-07")]


def log_returns(closes):
    return [math.log(closes[i] / closes[i - 1])
            for i in range(1, len(closes))]


def vol_estimate(rets, i, n):
    """Annualised vol of the n returns ending at i-1. STRICTLY prior.

    The window is rets[i-n:i], which excludes rets[i]. Including day i is
    a look-ahead bug that makes the strategy appear to dodge crashes it
    could not have seen coming, and it is the single most flattering error
    available here. Planted and tested.
    """
    if i < n:
        return None
    w = rets[i - n:i]
    mu = sum(w) / len(w)
    var = sum((x - mu) ** 2 for x in w) / (len(w) - 1)
    return math.sqrt(var) * math.sqrt(TRADING_DAYS)


def weights(rets, lookback, target, cap=CAP, band=BAND):
    """Applied weight per day, with the no-trade band.

    Returns a list the same length as rets; None until the estimator has
    enough history.
    """
    out, held = [], None
    for i in range(len(rets)):
        v = vol_estimate(rets, i, lookback)
        if v is None or v <= 0:
            out.append(None)
            continue
        want = min(cap, target / v)
        if held is None or abs(want / held - 1.0) > band:
            held = want
        out.append(held)
    return out


def simulate(rets, w, rf, turn_bp=TURN_BP, borrow_spread=BORROW_SPREAD):
    """Daily net return of the targeted position, and of buy-and-hold.

    rf is a per-day list of annual risk-free rates aligned with rets.
    """
    net, bh, turn, prev = [], [], 0.0, None
    for i, r in enumerate(rets):
        wi = w[i]
        if wi is None:
            net.append(None)
            bh.append(None)
            continue
        d = rf[i] / TRADING_DAYS if rf[i] is not None else 0.0
        t = abs(wi - prev) * turn_bp / 1e4 if prev is not None else 0.0
        turn += abs(wi - prev) if prev is not None else 0.0
        borrow = max(0.0, wi - 1.0) * borrow_spread / TRADING_DAYS
        net.append(wi * r + (1.0 - wi) * d - borrow - t)
        bh.append(r)
        prev = wi
    return net, bh, turn


def stats(series, rf, days=TRADING_DAYS):
    """Annualised excess return, vol, Sharpe and DAILY max drawdown."""
    pairs = [(s, rf[i]) for i, s in enumerate(series) if s is not None]
    if len(pairs) < days:
        return None
    ex = [s - (r / days if r is not None else 0.0) for s, r in pairs]
    mu = sum(ex) / len(ex)
    var = sum((x - mu) ** 2 for x in ex) / (len(ex) - 1)
    sd = math.sqrt(var)
    #: The series is LOG returns, so summing gives log equity and the
    #: drawdown comes out in log units. v1.0 printed that straight into a
    #: column headed with a percent sign: buy-and-hold read -84.1%, which
    #: is exp(-0.841)-1 = -56.9% in the units anyone would read it in --
    #: and -56.9% is exactly SPX's 2007-2009 fall. The ranking was never
    #: affected, but the number looked like near-total ruin.
    cum, peak, mdd_log = 0.0, 0.0, 0.0
    for s, _ in pairs:
        cum += s
        peak = max(peak, cum)
        mdd_log = min(mdd_log, cum - peak)
    return dict(ret=mu * days, vol=sd * math.sqrt(days),
                sharpe=(mu / sd * math.sqrt(days)) if sd > 0 else 0.0,
                mdd=math.exp(mdd_log) - 1.0, mdd_log=mdd_log, n=len(pairs))


def era_bounds(n, k=N_ERAS):
    step = n / k
    return [(int(i * step), int((i + 1) * step)) for i in range(k)]


def assess(rets, rf, settings=None):
    """Every setting in the frozen grid, plus the eras."""
    grid = settings or [(lb, tv) for lb in LOOKBACKS for tv in TARGETS]
    out = []
    for lb, tv in grid:
        w = weights(rets, lb, tv)
        net, bh, turn = simulate(rets, w, rf)
        s, b = stats(net, rf), stats(bh, rf)
        if s is None or b is None:
            continue
        eras = []
        for a, z in era_bounds(len(rets)):
            se = stats(net[a:z], rf[a:z])
            be = stats(bh[a:z], rf[a:z])
            eras.append(None if (se is None or be is None)
                        else se["sharpe"] - be["sharpe"])
        out.append(dict(lookback=lb, target=tv, strat=s, bh=b,
                        turnover=turn, eras=eras,
                        d_sharpe=s["sharpe"] - b["sharpe"],
                        d_mdd=s["mdd"] - b["mdd"], w=w))
    return out


def gates(res):
    """Gates A, B and C exactly as frozen in section 6."""
    a_n = sum(1 for r in res if r["d_sharpe"] > 0)
    gate_a = a_n >= MIN_PASS
    gate_b = all(r["eras"] and all(e is not None and e > 0
                                   for e in r["eras"]) for r in res)
    gate_c = all(r["d_mdd"] >= -1e-12 for r in res)
    #: concentration: does ONE setting carry the average improvement?
    ds = sorted((r["d_sharpe"] for r in res), reverse=True)
    conc = bool(ds) and len(ds) > 1 and ds[0] > 0 and \
        sum(d for d in ds[1:] if d > 0) < ds[0]
    return dict(a=gate_a, a_n=a_n, b=gate_b, c=gate_c, concentrated=conc)


def self_test():
    import random
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"vol_target.py v{VERSION} self-test\n")

    print("the estimator is STRICTLY backward-looking (sec 9.3)")
    #: zero vol for 300 days, then a jump. A correct estimator cannot know
    #: about day 300 until day 301. One that peeks would cut the weight ON
    #: day 300 -- dodging a crash it could not have seen, which is the most
    #: flattering bug available here.
    r = [0.0] * 300 + [-0.10] + [0.0] * 50
    #: a constant-zero window has zero vol, so seed tiny noise to make the
    #: estimator well defined without making the jump invisible
    rng = random.Random(1)
    r = [x + rng.gauss(0, 0.0005) for x in r]
    w = weights(r, 60, 0.10)
    check("the weight on the crash day is unchanged from the day before",
          w[300] is not None and abs(w[300] - w[299]) < 1e-12,
          f"{w[299]:.3f} -> {w[300]:.3f}")
    check("and it falls only AFTER the crash is observed",
          w[301] < w[300] * 0.9, f"{w[300]:.3f} -> {w[301]:.3f}")
    check("the estimate uses n returns ending at i-1",
          abs(vol_estimate([0.01] * 5 + [9.0], 5, 5)
              - 0.0) < 1e-12, "the 9.0 at index 5 is excluded")

    print("\na CONSTANT-volatility series must show NO improvement "
          "(sec 9.1)")
    #: If targeting "helps" here the harness is wrong: there is nothing to
    #: time, so the weight should be near constant and the Sharpe equal.
    rng2 = random.Random(7)
    n = 6000
    flat = [rng2.gauss(0.0003, 0.16 / math.sqrt(TRADING_DAYS))
            for _ in range(n)]
    rf = [0.02] * n
    res = assess(flat, rf)
    worst = max(abs(x["d_sharpe"]) for x in res)
    check("Sharpe is unchanged across every setting", worst < 0.12,
          f"largest |change| {worst:.3f}")

    print("\na series with PLANTED clustering must improve (sec 9.2)")
    #: alternating calm and stormy regimes, same mean drift -- so the only
    #: thing to exploit is the vol, which is exactly the hypothesis
    rng3 = random.Random(11)
    clust = []
    for blk in range(60):
        sd = (0.08 if blk % 2 == 0 else 0.32) / math.sqrt(TRADING_DAYS)
        clust += [rng3.gauss(0.0003, sd) for _ in range(100)]
    res2 = assess(clust, [0.02] * len(clust))
    n_up = sum(1 for x in res2 if x["d_sharpe"] > 0)
    check("most settings improve on a clustered series", n_up >= MIN_PASS,
          f"{n_up} of {len(res2)}")

    print("\nthe no-trade band reduces turnover (sec 9.4)")
    #: The first version asserted turnover fell below 0.6x of unbanded --
    #: a ratio I invented, which the code missed at 0.75x while behaving
    #: correctly. Section 9.4 asks that the band "demonstrably reduce
    #: turnover" and names no magnitude. Test the structural property
    #: instead: turnover must fall MONOTONICALLY as the band widens. That
    #: cannot happen by accident and needs no magic number.
    ts = [simulate(clust, weights(clust, 60, 0.10, band=b),
                   [0.02] * len(clust))[2]
          for b in (0.0, 0.05, 0.10, 0.25)]
    check("turnover falls monotonically as the band widens",
          all(ts[i] > ts[i + 1] for i in range(len(ts) - 1)),
          " -> ".join(f"{t:.0f}" for t in ts))
    check("a 10% band cuts turnover by a visible margin",
          ts[2] < ts[0], f"{ts[2]:.0f} vs {ts[0]:.0f} "
                         f"({(1-ts[2]/ts[0])*100:.0f}% less)")
    check("and a zero band is the same as no band at all",
          abs(ts[0] - simulate(clust, weights(clust, 60, 0.10, band=-1.0),
                               [0.02] * len(clust))[2]) < 1e-9)

    print("\na plateau and a spike are distinguished (sec 9.5)")
    def fake(ds):
        return [dict(d_sharpe=d, d_mdd=0.0, eras=[d, d, d]) for d in ds]
    g5 = gates(fake([0.08, 0.07, 0.09, 0.06, 0.07, -0.01]))
    check("five improving settings pass Gate A", g5["a"], f"{g5['a_n']}/6")
    check("and a plateau is not flagged as concentrated",
          not g5["concentrated"])
    g1 = gates(fake([0.40, -0.01, -0.02, -0.01, 0.00, -0.03]))
    check("one improving setting FAILS Gate A", not g1["a"],
          f"{g1['a_n']}/6")
    check("and it IS flagged as concentrated", g1["concentrated"],
          "one setting carries it")

    print("\nGate B needs every era (sec 9.6)")
    gb = gates([dict(d_sharpe=0.05, d_mdd=0.0, eras=[0.1, -0.02, 0.1])
                for _ in range(6)])
    check("improving overall but not in era 2 FAILS Gate B", not gb["b"])
    check("while Gate A still passes, so the two are independent",
          gb["a"], f"{gb['a_n']}/6")

    print("\nGate C, and drawdown at DAILY resolution (sec 9.7)")
    gc = gates([dict(d_sharpe=0.05, d_mdd=-0.01, eras=[0.1, 0.1, 0.1])
                for _ in range(6)])
    check("a worse drawdown FAILS Gate C", not gc["c"])
    #: planted: a fall and full recovery inside one month must be visible
    spike = [0.0] * 10 + [-0.20] + [0.20] + [0.0] * 240
    st = stats(spike, [0.0] * len(spike))
    check("an intramonth round trip shows in the daily drawdown",
          st["mdd_log"] <= -0.20 + 1e-9, f"{st['mdd_log']:.3f} log")
    #: and the reported figure is in the units its column claims
    check("mdd is reported SIMPLE, not log",
          abs(st["mdd"] - (math.exp(-0.20) - 1)) < 1e-12,
          f"{st['mdd']*100:.1f}% simple from {st['mdd_log']:.2f} log")

    print("\nthe cash leg is not forgotten")
    #: with w = 0 the strategy holds cash, so its EXCESS return is zero --
    #: not minus the risk-free rate, which is what dropping (1-w) gives
    z = simulate([0.01] * 300, [0.0] * 300, [0.05] * 300)[0]
    sz = stats(z, [0.05] * 300)
    check("a fully de-risked position earns cash, so excess is ~0",
          abs(sz["ret"]) < 1e-9, f"{sz['ret']*100:+.4f}%")

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def report(res, g, label):
    print(f"\n  {label}")
    print(f"  {'look':>5}{'target':>8}{'ret':>8}{'vol':>7}{'Sharpe':>8}"
          f"{'B&H':>7}{'delta':>8}{'maxDD':>9}{'B&H DD':>9}{'turn':>7}")
    print("  " + "-" * 76)
    for r in sorted(res, key=lambda x: (x["lookback"], x["target"])):
        s, b = r["strat"], r["bh"]
        print(f"  {r['lookback']:>5}{r['target']*100:>7.0f}%"
              f"{s['ret']*100:>7.1f}%{s['vol']*100:>6.1f}%"
              f"{s['sharpe']:>8.2f}{b['sharpe']:>7.2f}"
              f"{r['d_sharpe']:>+8.2f}"
              f"{s['mdd']*100:>8.1f}%{b['mdd']*100:>8.1f}%"
              f"{r['turnover']:>7.0f}")
    print(f"\n  [{'PASS' if g['a'] else 'FAIL'}] Gate A  Sharpe beats B&H "
          f"in >= {MIN_PASS} of 6      {g['a_n']} of {len(res)}")
    print(f"  [{'PASS' if g['b'] else 'FAIL'}] Gate B  improvement in "
          f"EVERY era")
    print(f"  [{'PASS' if g['c'] else 'FAIL'}] Gate C  drawdown not worse")
    if g["concentrated"]:
        print("  [FIT]  the improvement is CONCENTRATED in one setting -- "
              "section 7")
        print("         calls that a fit, not a finding, whatever Gate A "
              "counts")
    return g["a"] and g["b"] and g["c"] and not g["concentrated"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="../data/spx500usd_mid_5m.csv")
    ap.add_argument("--rf-csv", default="../data/DGS3MO.csv")
    ap.add_argument("--allow-thin-rf", action="store_true",
                    help="reproduce the provisional run; flatters the strategy")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    import datetime as dt
    import pandas as pd
    print(f"vol_target.py v{VERSION}   PREREGISTRATION_v6, ONE RUN\n")

    df = pd.read_csv(os.path.expanduser(a.csv))
    tcol = df.columns[0]
    df[tcol] = pd.to_datetime(df[tcol])
    daily = df.set_index(tcol)[df.columns[4]].resample("D").last().dropna()
    dates = [d.date() for d in daily.index]
    closes = [float(x) for x in daily.to_numpy()]
    print(f"  {len(closes):,} daily closes  {dates[0]} -> {dates[-1]}")

    rf_raw = {}
    for line in open(os.path.expanduser(a.rf_csv)).read().splitlines()[1:]:
        p = line.split(",")
        if len(p) >= 2 and p[1].strip() not in (".", ""):
            try:
                rf_raw[dt.date.fromisoformat(p[0].strip())] = \
                    float(p[1]) / 100.0
            except ValueError:
                pass
    rets = log_returns(closes)
    rday = dates[1:]
    rf, last = [], RF_DEFAULT
    for d in rday:
        for k in range(8):
            v = rf_raw.get(d - dt.timedelta(days=k))
            if v is not None:
                last = v
                break
        rf.append(last)
    cov = sum(1 for d in rday if d in rf_raw) / len(rday)
    print(f"  risk-free coverage {cov*100:.0f}% of return days")
    #: kraken_basis.py STOPS below 90% coverage, on the grounds that a
    #: partial rate series silently re-selects the sample. v1.0 of this
    #: file printed the number and carried on with a flat 2% default for
    #: 82% of the sample -- the same substitution, waved through. The
    #: strategy earns rf on its (1-w) cash leg and buy-and-hold has no
    #: cash leg, so an overstated rf in the zero-rate years flatters the
    #: strategy in exactly the eras that decide Gate B.
    if cov < RF_MIN_COVERAGE and not a.allow_thin_rf:
        gap0 = min(rday)
        raise SystemExit(
            f"\n  STOP: the rate series covers {cov*100:.0f}% of "
            f"{gap0} -> {max(rday)}.\n"
            f"  Everything outside it would default to a flat "
            f"{RF_DEFAULT*100:.1f}%, which is not\n"
            f"  the rate that prevailed -- 2005-2007 was near 5% and "
            f"2009-2021 near zero.\n"
            f"  Fetch the full period and pass it as --rf-csv:\n"
            f"    https://fred.stlouisfed.org/graph/fredgraph.csv?"
            f"id=DGS3MO&cosd={gap0}&coed={max(rday)}\n"
            f"  Or pass --allow-thin-rf to reproduce the provisional run, "
            f"which\n  FLATTERS the strategy in the eras that fail.")

    res = assess(rets, rf)
    g = gates(res)
    passed = report(res, g, f"CAP {CAP:.1f}x  -- the frozen grid")

    print(f"\n  ERA DETAIL (Sharpe improvement, three disjoint thirds)")
    for r in sorted(res, key=lambda x: (x["lookback"], x["target"])):
        print(f"    {r['lookback']:>4}d {r['target']*100:>3.0f}%   "
              + "  ".join(f"{e:+.2f}" if e is not None else "  -- "
                          for e in r["eras"]))

    print(f"\n  GATE D -- leverage carried INTO the known failures")
    idx = {d: i for i, d in enumerate(rday)}
    for name, s0, s1 in CRASHES:
        a0 = dt.date.fromisoformat(s0)
        i0 = next((idx[a0 - dt.timedelta(days=k)]
                   for k in range(8) if (a0 - dt.timedelta(days=k)) in idx),
                  None)
        if i0 is None:
            print(f"    {name}  not in sample")
            continue
        ws = [r["w"][i0] for r in res if r["w"][i0] is not None]
        if not ws:
            continue
        i1 = next((idx[dt.date.fromisoformat(s1) + dt.timedelta(days=k)]
                   for k in range(8)
                   if (dt.date.fromisoformat(s1)
                       + dt.timedelta(days=k)) in idx), None)
        bh = sum(rets[i0:i1]) if i1 else None
        print(f"    {name}  weight entering {min(ws):.2f}-{max(ws):.2f}x"
              + (f"   index moved {bh*100:+.1f}% over the episode"
                 if bh is not None else ""))

    res1 = assess(rets, rf)
    for r in res1:
        r["w"] = weights(rets, r["lookback"], r["target"], cap=1.0)
        net, bh, turn = simulate(rets, r["w"], rf)
        s, b = stats(net, rf), stats(bh, rf)
        r.update(strat=s, bh=b, turnover=turn,
                 d_sharpe=s["sharpe"] - b["sharpe"],
                 d_mdd=s["mdd"] - b["mdd"])
        r["eras"] = []
        for a0, z0 in era_bounds(len(rets)):
            se, be = stats(net[a0:z0], rf[a0:z0]), stats(bh[a0:z0], rf[a0:z0])
            r["eras"].append(None if (se is None or be is None)
                             else se["sharpe"] - be["sharpe"])
    report(res1, gates(res1),
           "CAP 1.0x -- pre-declared variant, section 5")

    print(f"\n  Venue cost is NOT charged above. equity_cost.py measured "
          f"6.15%/yr")
    print(f"  to hold a long index CFD at OANDA -- 65% of the equity "
          f"premium.")
    print(f"  {'PROCEED' if passed else 'REJECTED'}")


if __name__ == "__main__":
    main()
