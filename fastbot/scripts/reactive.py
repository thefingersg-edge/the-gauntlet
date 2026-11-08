#!/usr/bin/env python3
"""PREREGISTRATION_v35 -- reactive signals: does the first step of a move
tell you it will keep going?

A. SHOCK FOLLOW-THROUGH (5m, RTH, SPX500 / NAS100 / US30)
   z = 5m bar return / RMS of the same time-slot's return over the prior
   20 sessions. The day's FIRST bar with |z| >= 3 (09:30-14:55) is the shock.
   A1 every first shock: enter next bar open WITH the shock.
   A2 held: the next bar gives back less than half the shock; enter after it.
   A3 out of calm: the hour before the shock was quieter than the median of
      the prior 20 sessions' same hour.
   Exit: the 15:55 bar's close.
B. INTRADAY MOMENTUM: sign of prior 15:55 close -> 10:00 open sets the
   direction of a 15:30 open -> 15:55 close trade.

Direction is fixed in advance (WITH the move). Discovery 2005-2012 is
reported gross; the gate is 2013 -> 2026-09-17 NET of the quoted spread.

    python3 reactive.py --self-test | --budget | (run)
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import math
import os
import re
import statistics as st
import sys

import numpy as np

from premarket_factor import regress, tstat
from premarket_levels import to_et

VERSION = "1.0"
DOC = ("PREREGISTRATION_v35.md", "bca23cad5a474fa893daaec0ff9c046f0e5572e1a5d6a5cde6ab943222e3f7fb")
INSTR = ("spx500usd", "nas100usd", "us30usd")
Z_SHOCK, SIG_N = 3.0, 20
LAST_SHOCK = "14:55"
DISC_END, HOLD_END = dt.date(2012, 12, 31), dt.date(2026, 9, 17)
ERAS = ((2013, 2017), (2018, 2021), (2022, 2026))
EXCL = (2020, 2021)
T_GATE, T_REPL = 2.50, 1.64
MIN_BARS = 70

_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def _guard(names):
    bad = sorted(n for n in names if _FORBIDDEN.search(n))
    if bad:
        raise SystemExit(f"namespace guard: {bad}")


# bar tuple: mid o,h,l,c, bid_o, ask_o, bid_c, ask_c
def load(data_dir, ins):
    ask = {}
    with open(os.path.join(data_dir, f"{ins}_ask_5m.csv")) as fh:
        rd = csv.reader(fh)
        next(rd)
        for r in rd:
            if 13 <= int(r[0][11:13]) <= 20:
                ask[r[0]] = tuple(float(x) for x in r[1:5])
    days = {}
    with open(os.path.join(data_dir, f"{ins}_bid_5m.csv")) as fh:
        rd = csv.reader(fh)
        next(rd)
        for r in rd:
            if not 13 <= int(r[0][11:13]) <= 20 or r[0] not in ask:
                continue
            e = to_et(r[0])
            if not dt.time(9, 30) <= e.time() <= dt.time(15, 55):
                continue
            b = tuple(float(x) for x in r[1:5])
            a = ask[r[0]]
            m = tuple((b[i] + a[i]) / 2 for i in range(4))
            days.setdefault(e.date(), {})[e.strftime("%H:%M")] = m + (b[0], a[0], b[3], a[3])
    return {d: v for d, v in days.items() if len(v) >= MIN_BARS}


def ret(bar):
    return (bar[3] / bar[0] - 1.0) * 1e4


def hm(t0, k):
    return (dt.datetime.strptime(t0, "%H:%M") + dt.timedelta(minutes=5 * k)).strftime("%H:%M")


def net_open_to_close(b_in, b_out, side):
    """Enter at b_in's open, leave at b_out's close, paying the quoted spread."""
    if side > 0:
        return (b_out[6] / b_in[5] - 1.0) * 1e4
    return -(b_out[7] / b_in[4] - 1.0) * 1e4


def gross_open_to_close(b_in, b_out, side):
    return side * (b_out[3] / b_in[0] - 1.0) * 1e4


def slot_sigma(hist):
    """RMS of the PRIOR SIG_N same-slot returns; None until full."""
    if len(hist) < SIG_N:
        return None
    w = hist[-SIG_N:]
    s = math.sqrt(sum(x * x for x in w) / SIG_N)
    return s if s > 0 else None


def shock_rows(days, ins):
    out, hist, hvol = [], {}, []
    for d in sorted(days):
        bars = days[d]
        # hour-before-shock quietness needs per-day realised vol by slot;
        # we compare the 12 bars before the shock with the prior 20 sessions'
        # same 12 bars (stored per day as {hm: |ret|}).
        today_abs = {k: abs(ret(v)) for k, v in bars.items()}
        sig = {k: slot_sigma(hist.get(k, [])) for k in bars}
        first = None
        for k in sorted(bars):
            if k > LAST_SHOCK:
                break
            s = sig[k]
            if s is None:
                continue
            z = ret(bars[k]) / s
            if abs(z) >= Z_SHOCK:
                first = (k, z)
                break
        for k, v in bars.items():
            hist.setdefault(k, []).append(ret(v))
        prior_days = hvol[-SIG_N:]
        hvol.append(today_abs)
        if not first or "15:55" not in bars:
            continue
        k, z = first
        side = 1 if z > 0 else -1
        e1, e2 = hm(k, 1), hm(k, 2)
        row = dict(ins=ins, date=d, hm=k, z=z, side=side)
        if e1 in bars:
            row["A1g"] = gross_open_to_close(bars[e1], bars["15:55"], side)
            row["A1n"] = net_open_to_close(bars[e1], bars["15:55"], side)
            row["A1_60"] = (side * (bars[hm(k, 13)][0] / bars[e1][0] - 1) * 1e4
                            if hm(k, 13) in bars else None)
            body = bars[k][3] - bars[k][0]
            give = (bars[e1][3] - bars[k][3]) * side
            held = give > -0.5 * abs(body)
            if held and e2 in bars and e2 <= "15:50":
                row["A2g"] = gross_open_to_close(bars[e2], bars["15:55"], side)
                row["A2n"] = net_open_to_close(bars[e2], bars["15:55"], side)
            before = [hm(k, -j) for j in range(1, 13)]
            if len(prior_days) == SIG_N and all(b in bars for b in before):
                mine = sum(today_abs[b] for b in before)
                ref = [sum(p.get(b, 0.0) for b in before) for p in prior_days
                       if all(b in p for b in before)]
                if len(ref) >= 10 and mine < st.median(ref):
                    row["A3g"], row["A3n"] = row["A1g"], row["A1n"]
        out.append(row)
    return out


def mom_rows(days, ins):
    out, ds = [], sorted(days)
    for i in range(1, len(ds)):
        d, prev, bars = ds[i], days[ds[i - 1]], days[ds[i]]
        if not all(k in bars for k in ("10:00", "15:30", "15:55")) or "15:55" not in prev:
            continue
        r1 = (bars["10:00"][0] / prev["15:55"][3] - 1) * 1e4
        if r1 == 0:
            continue
        side = 1 if r1 > 0 else -1
        out.append(dict(ins=ins, date=d, r1=r1, side=side,
                        Bg=gross_open_to_close(bars["15:30"], bars["15:55"], side),
                        Bn=net_open_to_close(bars["15:30"], bars["15:55"], side),
                        fwd=(bars["15:55"][3] / bars["15:30"][0] - 1) * 1e4))
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
    if main and era_ok and ex_ok:
        return "PASS"
    return "FAIL" + (" (main passed; eras/ex-2020-21 did not)" if main else "")


_guard(list(globals()))


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, np.bool_)):
            raise TypeError(name)
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"   {detail}" if detail else ""))

    print(f"reactive.py v{VERSION} self-test\n")

    def bar(o, c):
        return (o, max(o, c), min(o, c), c, o - .01, o + .01, c - .01, c + .01)

    check("sigma uses prior values only and needs 20", slot_sigma([1.0] * 19) is None
          and abs(slot_sigma([2.0] * 20) - 2.0) < 1e-12)
    check("net < gross both sides",
          net_open_to_close(bar(100, 100), bar(101, 101), 1) < gross_open_to_close(bar(100, 100), bar(101, 101), 1)
          and net_open_to_close(bar(100, 100), bar(99, 99), -1) < gross_open_to_close(bar(100, 100), bar(99, 99), -1))
    # synthetic: 21 quiet days then a shock day
    t0 = dt.datetime(2020, 1, 1, 9, 30)
    slots = [(t0 + dt.timedelta(minutes=5 * i)).strftime("%H:%M") for i in range(78)]
    days = {}
    rng = np.random.default_rng(1)
    for j in range(22):
        d = dt.date(2020, 1, 1) + dt.timedelta(days=j)
        p, bars = 100.0, {}
        for s in slots:
            c = p * (1 + float(rng.normal(0, 1e-4)))
            bars[s] = bar(p, c)
            p = c
        days[d] = bars
    last = max(days)
    b = days[last]
    o = b["11:00"][0]
    b["11:00"] = bar(o, o * 1.003)                       # ~30 sigma up
    b["11:05"] = bar(o * 1.003, o * 1.0029)               # holds
    rows = shock_rows(days, "x")
    r = [x for x in rows if x["date"] == last]
    check("the planted shock is found at 11:00, side +1",
          len(r) == 1 and r[0]["hm"] == "11:00" and r[0]["side"] == 1)
    check("A2 fires when the next bar holds", "A2n" in r[0])
    b["11:05"] = bar(o * 1.003, o * 1.0005)               # gives back >50%
    r = [x for x in shock_rows(days, "x") if x["date"] == last]
    check("PLANTED: A2 does NOT fire when the next bar gives most of it back",
          "A2n" not in r[0])
    check("A1 enters at the NEXT bar, not the shock bar",
          abs(r[0]["A1g"] - gross_open_to_close(b["11:05"], b["15:55"], 1)) < 1e-9)
    noise = [dict(date=i, y=float(rng.normal(0, 10))) for i in range(4000)]
    good = [dict(date=i, y=1.0 + float(rng.normal(0, 10))) for i in range(4000)]
    g, n0 = cl_mean(good, "y"), cl_mean(noise, "y")
    check("planted +1 bp edge is found", g[1] >= T_GATE, f"t {g[1]:+.2f}")
    check("PLANTED FAIL: noise does not pass", not (n0[0] > 0 and n0[1] >= T_GATE), f"t {n0[1]:+.2f}")
    check("verdict needs eras", verdict((1, 3, 0), [(1, 2, 0), (-1, 0, 0), (1, 2, 0)], (1, 2, 0)) != "PASS")
    check("verdict all good", verdict((1, 3, 0), [(1, 2, 0)] * 3, (1, 2, 0)) == "PASS")
    check("frozen", Z_SHOCK == 3.0 and SIG_N == 20 and T_GATE == 2.50 and LAST_SHOCK == "14:55")
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
    print(f"reactive.py v{VERSION}   PREREGISTRATION_v35\n")
    print("  I am not a financial adviser. This is a measurement, not a")
    print("  recommendation to take a position.\n")
    if not a.budget:
        got = hashlib.sha256(open(os.path.join(here, "..", DOC[0]), "rb").read()).hexdigest()
        if got != DOC[1]:
            print(f"  {DOC[0]} changed since frozen ({got[:12]}). Refused.")
            sys.exit(2)
        print(f"  {DOC[0]} sha256 {got[:16]}... matches\n")
    sh, mo = [], []
    for ins in INSTR:
        days = load(a.data_dir, ins)
        s, m = shock_rows(days, ins), mom_rows(days, ins)
        sh += s
        mo += m
        print(f"  {ins:<10} {len(days):>5} sessions  {len(s):>5} shock days  {len(m):>5} momentum days")
    for r in sh + mo:
        r["era"] = era_of(r["date"])
    tests = (("A1 every shock", sh, "A1"), ("A2 shock that holds", sh, "A2"),
             ("A3 shock out of calm", sh, "A3"), ("B  intraday momentum", mo, "B"))
    if a.budget:
        print("\n  POWER BUDGET (holdout; spread and |return| scale only, no signs)")
        for name, rows, k in tests:
            hs = [r for r in rows if r["era"] == "hold" and r.get(k + "n") is not None]
            spread = [r[k + "g"] - r[k + "n"] for r in hs]
            sd = st.stdev(abs(r[k + "g"]) for r in hs) * 0 + math.sqrt(
                st.mean(r[k + "g"] ** 2 for r in hs))
            nd = len({r["date"] for r in hs})
            print(f"    {name:<22} trades {len(hs):>5}  dates {nd:>5}  RMS {sd:5.1f} bp"
                  f"  cost {st.median(spread):.2f} bp  MDE ~ {(T_GATE + .84) * sd / math.sqrt(nd):.2f} bp")
        return
    res = {}
    print("\n  gross = before costs, NET = after the quoted spread; t clustered by date")
    for name, rows, k in tests:
        dg = cl_mean([r for r in rows if r["era"] == "disc"], k + "g")
        hs = [r for r in rows if r["era"] == "hold"]
        hg, hn = cl_mean(hs, k + "g"), cl_mean(hs, k + "n")
        eras = [cl_mean([r for r in hs if lo <= r["date"].year <= hi], k + "n") for lo, hi in ERAS]
        ex = cl_mean([r for r in hs if r["date"].year not in EXCL], k + "n")
        v = verdict(hn, eras, ex)
        res[name.split()[0]] = v
        print(f"\n  {name}")
        print(f"    disc gross {dg[0]:+.2f} (t {dg[1]:+.2f}, n {dg[2]})   hold gross {hg[0]:+.2f}"
              f" (t {hg[1]:+.2f})   HOLD NET {hn[0]:+.2f} t {hn[1]:+.2f} n {hn[2]}")
        print("    net by era  " + "   ".join(f"{lo}-{hi} {e[0]:+.2f} (t {e[1]:+.2f})"
                                              for (lo, hi), e in zip(ERAS, eras))
              + f"   ex-2020/21 {ex[0]:+.2f} (t {ex[1]:+.2f})  -> {v}")
        for ins in INSTR:
            x = cl_mean([r for r in hs if r["ins"] == ins], k + "n")
            print(f"      {ins:<10} hold net {x[0]:+.2f} t {x[1]:+.2f} n {x[2]}")
    a60 = cl_mean([r for r in sh if r["era"] == "hold"], "A1_60")
    print(f"\n  reported only: A1 shock, 60-min gross (mid) in holdout {a60[0]:+.2f} t {a60[1]:+.2f}")
    print("\n  VERDICTS  " + "   ".join(f"{k}: {v}" for k, v in res.items()))


if __name__ == "__main__":
    main()
