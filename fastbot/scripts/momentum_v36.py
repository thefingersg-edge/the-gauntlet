#!/usr/bin/env python3
"""PREREGISTRATION_v36 -- two survivors from the intraday-momentum literature.

N. NOISE-BAND MOMENTUM (Zarattini, Aziz & Barbon 2024, rules as published,
   unlevered). At each half hour 10:00..15:30 compare the close with a band
   around today's open: sigma_k = mean over the prior 14 sessions of
   |close_k / open_0930 - 1|; upper = max(open, prior close) * (1 + sigma_k),
   lower = min(open, prior close) * (1 - sigma_k). Above upper -> long,
   below lower -> short. A long exits when price closes below max(upper,
   session VWAP) at a checkpoint (short mirrored). Flat by the 15:55 close.
   Fills at the next bar's open, paying the quoted spread.

G. GAMMA-PROXY MOMENTUM (Baltussen, Da, Lammers & Martens 2021). The rest-of-
   day return (prior 15:55 close -> 15:30 open) sets the direction of a
   15:30 open -> 15:55 close trade, ONLY on days whose prior-day VIX is in
   the top third of its trailing 252-day range -- a free stand-in for
   dealers being short gamma. Other days are reported as the contrast.

Gated 2013 -> 2026-09-17 NET. 2005-2012 reported gross.

    python3 momentum_v36.py --self-test | --budget | (run)
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import math
import os
import re
import statistics as st
import sys

import numpy as np

from premarket_factor import regress, tstat
from premarket_levels import read_vix, vix_before
from reactive import load, hm, net_open_to_close, gross_open_to_close

VERSION = "1.0"
DOC = ("PREREGISTRATION_v36.md", "aeffbae5338a7c2bf74fee008e646d85885895ff35138e1e9fde298597e460db")
INSTR = ("spx500usd", "nas100usd", "us30usd")
CHECKS = tuple(hm("09:55", 6 * i) for i in range(12))       # bars closing 10:00..15:30
LOOKBACK = 14
VIX_TRAIL, VIX_Q = 252, 2 / 3
DISC_END, HOLD_END = dt.date(2012, 12, 31), dt.date(2026, 9, 17)
ERAS = ((2013, 2017), (2018, 2021), (2022, 2026))
EXCL = (2020, 2021)
T_GATE, T_REPL = 2.24, 1.64
VIX_FILE = "../data/VIXCLS.csv"

_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def _guard(names):
    bad = sorted(n for n in names if _FORBIDDEN.search(n))
    if bad:
        raise SystemExit(f"namespace guard: {bad}")


def session_vwap(bars, upto):
    num = den = 0.0
    for k in sorted(bars):
        if k > upto:
            break
        v = bars[k]
        num += (v[1] + v[2] + v[3]) / 3.0
        den += 1.0
    return num / den if den else None


def noise_day(bars, prev_close, sig):
    """Run one session. Returns list of (gross, net) trades, or None."""
    if "09:30" not in bars or "15:55" not in bars:
        return None
    op = bars["09:30"][0]
    up_ref, dn_ref = max(op, prev_close), min(op, prev_close)
    side, entry, trades = 0, None, []
    for k in CHECKS:
        nxt = hm(k, 1)
        if k not in bars or nxt not in bars or sig.get(k) is None:
            continue
        c = bars[k][3]
        U, L = up_ref * (1 + sig[k]), dn_ref * (1 - sig[k])
        vw = session_vwap(bars, k)
        if side == 1 and c < max(U, vw):
            trades.append((gross_open_to_close(entry, _as_close(bars[nxt]), 1),
                           net_open_to_close(entry, _as_close(bars[nxt]), 1)))
            side = 0
        elif side == -1 and c > min(L, vw):
            trades.append((gross_open_to_close(entry, _as_close(bars[nxt]), -1),
                           net_open_to_close(entry, _as_close(bars[nxt]), -1)))
            side = 0
        if side == 0:
            if c > U:
                side, entry = 1, bars[nxt]
            elif c < L:
                side, entry = -1, bars[nxt]
    if side != 0:
        trades.append((gross_open_to_close(entry, bars["15:55"], side),
                       net_open_to_close(entry, bars["15:55"], side)))
    return trades


def _as_close(bar):
    """Exit AT a bar's open: present its open prices in the close slots."""
    return (bar[0], bar[1], bar[2], bar[0], bar[4], bar[5], bar[4], bar[5])


def noise_rows(days, ins):
    out, ds, hist = [], sorted(days), []
    for i in range(1, len(ds)):
        d, bars = ds[i], days[ds[i]]
        prev = days[ds[i - 1]]
        mv = ({k: abs(bars[k][3] / bars["09:30"][0] - 1) for k in CHECKS if k in bars}
              if "09:30" in bars else {})
        if len(hist) >= LOOKBACK and "15:55" in prev:
            sig = {}
            for k in CHECKS:
                xs = [h[k] for h in hist[-LOOKBACK:] if k in h]
                sig[k] = st.mean(xs) if len(xs) >= 10 else None
            tr = noise_day(bars, prev["15:55"][3], sig)
            if tr:
                out.append(dict(ins=ins, date=d, n=len(tr),
                                Ng=sum(g for g, _ in tr), Nn=sum(n for _, n in tr)))
        if mv:
            hist.append(mv)
    return out


def vix_hot(vix, d):
    """Prior-day VIX in the top third of the prior 252 closes (all before d)."""
    ds = [x for x, _ in vix]
    import bisect
    i = bisect.bisect_left(ds, d) - 1
    if i < VIX_TRAIL:
        return None
    w = sorted(v for _, v in vix[i - VIX_TRAIL:i])
    return vix[i][1] >= w[int(VIX_Q * VIX_TRAIL)]


def gamma_rows(days, ins, vix):
    out, ds = [], sorted(days)
    for i in range(1, len(ds)):
        d, bars, prev = ds[i], days[ds[i]], days[ds[i - 1]]
        if not all(k in bars for k in ("15:30", "15:55")) or "15:55" not in prev:
            continue
        hot = vix_hot(vix, d)
        if hot is None:
            continue
        rod = bars["15:30"][0] / prev["15:55"][3] - 1
        if rod == 0:
            continue
        s = 1 if rod > 0 else -1
        out.append(dict(ins=ins, date=d, hot=hot,
                        Gg=gross_open_to_close(bars["15:30"], bars["15:55"], s),
                        Gn=net_open_to_close(bars["15:30"], bars["15:55"], s)))
    return out


def era_of(d):
    return "disc" if d <= DISC_END else ("hold" if d <= HOLD_END else None)


def cl_mean(rows, key):
    rows = [r for r in rows if r.get(key) is not None]
    if len(rows) < 30:
        return None, None, len(rows)
    beta, V = regress([r[key] for r in rows], [[1.0] for _ in rows], [r["date"] for r in rows])
    return float(beta[0]), tstat(beta, V, 0), len(rows)


def verdict(hold, eras, ex):
    m, t, _ = hold
    main = m is not None and m > 0 and t is not None and t >= T_GATE
    era_ok = all(e[0] is not None and e[0] > 0 for e in eras)
    ex_ok = ex[0] is not None and ex[0] > 0 and ex[1] is not None and ex[1] >= T_REPL
    return "PASS" if main and era_ok and ex_ok else (
        "FAIL" + (" (main passed; eras/ex-2020-21 did not)" if main else ""))


_guard(list(globals()))


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, np.bool_)):
            raise TypeError(name)
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"   {detail}" if detail else ""))

    print(f"momentum_v36.py v{VERSION} self-test\n")

    def bar(o, c):
        return (o, max(o, c), min(o, c), c, o - .01, o + .01, c - .01, c + .01)

    t0 = dt.datetime(2020, 1, 1, 9, 30)
    slots = [(t0 + dt.timedelta(minutes=5 * i)).strftime("%H:%M") for i in range(78)]
    check("checkpoints are the bars closing 10:00 .. 15:30",
          CHECKS[0] == "09:55" and CHECKS[-1] == "15:25" and len(CHECKS) == 12)
    sig = {k: 0.002 for k in CHECKS}
    # trend day: price climbs steadily 100 -> 102
    trend = {s: bar(100 + 2 * i / 78, 100 + 2 * (i + 1) / 78) for i, s in enumerate(slots)}
    tr = noise_day(trend, 100.0, sig)
    check("a steady trend day produces a long that makes money",
          bool(tr) and sum(g for g, _ in tr) > 0, f"{tr}")
    flat = {s: bar(100.0, 100.0) for s in slots}
    check("PLANTED: a flat day inside the band trades nothing", noise_day(flat, 100.0, sig) == [])
    # breakout then collapse below VWAP -> long stopped out, loses
    whip = {}
    for s in slots:
        p = 100.0 if s < "09:55" else (101.0 if s < "10:25" else 99.0)
        whip[s] = bar(p, p)
    whip["09:55"] = bar(100.0, 101.0)
    whip["10:25"] = bar(101.0, 99.0)
    tr2 = noise_day(whip, 100.0, sig)
    check("a false breakout is stopped at the next checkpoint and loses",
          bool(tr2) and tr2[0][0] < 0, f"{tr2}")
    check("net < gross on every trade", all(n < g for g, n in tr + tr2))
    vix = [(dt.date(2019, 1, 1) + dt.timedelta(days=i), 10.0 + ((i + 1) % 3)) for i in range(300)]
    vix.append((dt.date(2019, 1, 1) + dt.timedelta(days=300), 50.0))
    check("VIX 50 after a calm year is hot",
          vix_hot(vix, dt.date(2019, 1, 1) + dt.timedelta(days=301)) is True)
    check("PLANTED: prior-day VIX 10 is not hot, and the same-day 50 is never used",
          vix_hot(vix, dt.date(2019, 1, 1) + dt.timedelta(days=300)) is False)
    rng = np.random.default_rng(5)
    noise = [dict(date=i, y=float(rng.normal(0, 30))) for i in range(3000)]
    good = [dict(date=i, y=3.0 + float(rng.normal(0, 30))) for i in range(3000)]
    check("planted +3 bp found", cl_mean(good, "y")[1] >= T_GATE)
    check("PLANTED FAIL: noise fails", not (cl_mean(noise, "y")[0] > 0 and cl_mean(noise, "y")[1] >= T_GATE))
    check("frozen", LOOKBACK == 14 and VIX_TRAIL == 252 and T_GATE == 2.24)
    check("namespace guard", not [n for n in globals() if _FORBIDDEN.search(n)])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="../data")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--budget", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    here = os.path.dirname(os.path.abspath(__file__))
    print(f"momentum_v36.py v{VERSION}   PREREGISTRATION_v36\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")
    if not a.budget:
        got = hashlib.sha256(open(os.path.join(here, "..", DOC[0]), "rb").read()).hexdigest()
        if got != DOC[1]:
            print(f"  {DOC[0]} changed since frozen ({got[:12]}). Refused.")
            sys.exit(2)
        print(f"  {DOC[0]} sha256 {got[:16]}... matches\n")
    vix = read_vix(os.path.join(here, VIX_FILE))
    nz, gm = [], []
    for ins in INSTR:
        days = load(a.data_dir, ins)
        n, g = noise_rows(days, ins), gamma_rows(days, ins, vix)
        nz += n
        gm += g
        print(f"  {ins:<10} {len(days):>5} sessions  {len(n):>5} noise-band trade days"
              f"  {sum(r['hot'] for r in g):>5} hot-VIX days of {len(g)}")
    for r in nz + gm:
        r["era"] = era_of(r["date"])
    tests = (("N  noise-band momentum (per instrument-day)", nz, "N", lambda r: True),
             ("G  last 30 min, hot-VIX days", gm, "G", lambda r: r["hot"]))
    if a.budget:
        print("\n  POWER BUDGET (holdout; RMS and costs only, no signs)")
        for name, rows, k, f in tests:
            hs = [r for r in rows if r["era"] == "hold" and f(r)]
            rms = math.sqrt(st.mean(r[k + "g"] ** 2 for r in hs))
            nd = len({r["date"] for r in hs})
            cost = st.mean(r[k + "g"] - r[k + "n"] for r in hs)
            print(f"    {name:<44} n {len(hs):>5}  dates {nd:>5}  RMS {rms:5.1f} bp"
                  f"  cost {cost:.2f} bp  MDE ~ {(T_GATE + .84) * rms / math.sqrt(nd):.2f} bp")
        tpd = st.mean(r["n"] for r in nz if r["era"] == "hold")
        print(f"    noise-band trades per trading day (holdout): {tpd:.2f}")
        return
    res = {}
    for name, rows, k, f in tests:
        sel = [r for r in rows if f(r)]
        dg = cl_mean([r for r in sel if r["era"] == "disc"], k + "g")
        hs = [r for r in sel if r["era"] == "hold"]
        hg, hn = cl_mean(hs, k + "g"), cl_mean(hs, k + "n")
        eras = [cl_mean([r for r in hs if lo <= r["date"].year <= hi], k + "n") for lo, hi in ERAS]
        ex = cl_mean([r for r in hs if r["date"].year not in EXCL], k + "n")
        v = verdict(hn, eras, ex)
        res[k] = v
        print(f"\n  {name}")
        print(f"    disc gross {dg[0]:+.2f} (t {dg[1]:+.2f}, n {dg[2]})   hold gross {hg[0]:+.2f}"
              f" (t {hg[1]:+.2f})   HOLD NET {hn[0]:+.2f} t {hn[1]:+.2f} n {hn[2]}")
        print("    net by era  " + "   ".join(f"{lo}-{hi} {e[0]:+.2f} (t {e[1]:+.2f})"
                                              for (lo, hi), e in zip(ERAS, eras))
              + f"   ex-2020/21 {ex[0]:+.2f} (t {ex[1]:+.2f})  -> {v}")
        for ins in INSTR:
            x = cl_mean([r for r in hs if r["ins"] == ins], k + "n")
            print(f"      {ins:<10} hold net {x[0]:+.2f} t {x[1]:+.2f} n {x[2]}")
    cold = [r for r in gm if not r["hot"]]
    for era in ("disc", "hold"):
        c = cl_mean([r for r in cold if r["era"] == era], "Gg")
        h = cl_mean([r for r in gm if r["hot"] and r["era"] == era], "Gg")
        print(f"\n  contrast, gross, {era}: hot-VIX {h[0]:+.2f} (t {h[1]:+.2f})   "
              f"other days {c[0]:+.2f} (t {c[1]:+.2f})")
    print("\n  VERDICTS  " + "   ".join(f"{k}: {v}" for k, v in res.items()))


if __name__ == "__main__":
    main()
