#!/usr/bin/env python3
"""fixes.py -- FLOWS-8, implements PREREGISTRATION_FIXES.md.  --self-test | --check-inputs | --run"""
from __future__ import annotations
import argparse, io, json, os, sys
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import common as C

NAME = "FIXES"
PAIRS = ("EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CAD", "USD_CHF", "NZD_USD", "USD_NOK", "USD_SEK")
SIGN = {p: (1.0 if p.startswith("USD_") else -1.0) for p in PAIRS}     # + = dollar up
FIXES = {"TOKYO": ("Asia/Tokyo", 8, 10, 12), "LONDON": ("Europe/London", 14, 16, 18),
         "ECB": ("Europe/Berlin", None, None, None)}                     # ECB handled separately (14:15)
LOG, RES = (os.path.join(C.FDATA, f) for f in ("fixes_run.log", "fixes_result.json"))


def times(days: pd.DatetimeIndex, tz: str, hm0, hm1, hm2):
    z = ZoneInfo(tz)
    mk = lambda hm: pd.DatetimeIndex([pd.Timestamp(d.year, d.month, d.day, hm[0], hm[1], tz=z) for d in days]).tz_convert("UTC")
    return mk(hm0), mk(hm1), mk(hm2)


def at_end(ba, col, t):
    """Value of `col` on the bar ENDING at t (bar start t - 15 min)."""
    return ba[col].reindex(t - pd.Timedelta(minutes=15)).to_numpy()


def legs(ba, sign, t0, t1, t2):
    m0, m1, m2 = (at_end(ba, "close_m", t) for t in (t0, t1, t2))
    b0, b1, b2 = (at_end(ba, "close_b", t) for t in (t0, t1, t2))
    a0, a1, a2 = (at_end(ba, "close_a", t) for t in (t0, t1, t2))
    pre, post = sign * (m1 / m0 - 1), sign * (m2 / m1 - 1)
    if sign > 0:      # long USD = long the pair, then short it
        npre = b1 / a0 - 1; npost = 1 - a2 / b1
    else:             # long USD = short the pair, then long it
        npre = 1 - a1 / b0; npost = b2 / a1 - 1
    return pre, post, npre, npost


def fix_table(data: dict, days, tz, h0, h1, h2, m0=0, m1=0, m2=0):
    t0, t1, t2 = times(days, tz, (h0, m0), (h1, m1), (h2, m2))
    per = {}
    for p, ba in data.items():
        pre, post, npre, npost = legs(ba, SIGN[p], t0, t1, t2)
        per[p] = pd.DataFrame({"pre": pre, "post": post, "net": npre + npost}, index=days)
    pre = pd.concat({p: d["pre"] for p, d in per.items()}, axis=1)
    post = pd.concat({p: d["post"] for p, d in per.items()}, axis=1)
    net = pd.concat({p: d["net"] for p, d in per.items()}, axis=1)
    ok = pre.notna() & post.notna() & net.notna()
    bas = pd.DataFrame({"pre": pre.where(ok).mean(axis=1), "post": post.where(ok).mean(axis=1),
                        "net": net.where(ok).mean(axis=1), "npairs": ok.sum(axis=1)})
    bas["R"] = bas["pre"] - bas["post"]
    return bas[bas["npairs"] >= 1], per


def nw(x, lags=5):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    b, se, t, n = C.ols_nw(x, np.ones((len(x), 1)), lags)
    return float(b[0]), float(t[0]), int(n)


def run() -> int:
    buf = io.StringIO()
    def say(*a):
        print(*a); print(*a, file=buf)
    pin = C.check_pin(NAME)
    data = {p: C.load_bidask(p) for p in PAIRS}
    say(f"FLOWS-8 FIXES  prereg {pin[:16]}  pairs: " + ", ".join(f"{p} {data[p].index[0].date()}" for p in PAIRS))
    days = pd.bdate_range("2005-01-03", C.END)
    tk, _ = fix_table(data, days, "Asia/Tokyo", 8, 10, 12)
    ld, perL = fix_table(data, days, "Europe/London", 14, 16, 18)
    daily = pd.concat([tk["R"], ld["R"]], axis=1).sum(axis=1, min_count=1).dropna()
    dnet = pd.concat([tk["net"], ld["net"]], axis=1).sum(axis=1, min_count=1).dropna()
    m, t, n = nw(daily)
    res = {"pin": pin, "n_days": n, "mean_R": m, "t": t}
    say(f"  days {n}; Tokyo fixes {len(tk)}, London {len(ld)}; mean pairs {tk['npairs'].mean():.1f} / {ld['npairs'].mean():.1f}")
    say(f"\n  G1 mean daily R (pre - post, both fixes) {m*1e4:+.3f} bp  t {t:+.2f}")
    eras = {}
    for e, a, b in C.ERAS:
        eras[e] = dict(zip(("mean", "t", "n"), nw(daily[(daily.index >= a) & (daily.index <= b)])))
        say(f"  {e}: {eras[e]['mean']*1e4:+.3f} bp t {eras[e]['t']:+.2f}")
    fx = {k: dict(zip(("mean", "t", "n"), nw(v["R"]))) | {"pre": float(v["pre"].mean()), "post": float(v["post"].mean())}
          for k, v in (("TOKYO", tk), ("LONDON", ld))}
    for k, v in fx.items():
        say(f"  G3 {k}: R {v['mean']*1e4:+.3f} bp t {v['t']:+.2f}   (pre {v['pre']*1e4:+.3f}, post {v['post']*1e4:+.3f})")
    mn, tn, nn = nw(dnet)
    e3 = dnet[dnet.index >= pd.Timestamp(C.ERAS[2][1])]
    say(f"\n  G4 trade, basket, both fixes, net: {mn*1e4:+.3f} bp/day t {tn:+.2f}; E3 {e3.mean()*1e4:+.3f}")
    G = {"G1": m > 0 and t >= 2.0,
         "G2": all(eras[e]["mean"] > 0 for e in eras) and eras["E3"]["mean"] >= 0.5 * m,
         "G3": fx["TOKYO"]["mean"] > 0 and fx["LONDON"]["mean"] > 0,
         "G4": mn > 0 and tn >= 1.65 and e3.mean() > 0,
         "G5": n >= 3000}
    kill = [k for k, g in (("K1", "G1"), ("K2", "G2"), ("K3", "G4")) if not G[g]]
    res |= {"eras": eras, "fixes": fx, "trade": dict(net=mn, t=tn, e3=float(e3.mean())), "gates": G,
            "verdict": "DEAD " + ",".join(kill) if kill else ("PASS" if G["G3"] and G["G5"] else "PASS but G3/G5")}
    say("\n  " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in G.items()) + f"   VERDICT: {res['verdict']}")
    say("\n  secondary (descriptive):")
    for p in PAIRS:
        d = perL[p]
        say(f"    London {p}: pre {d['pre'].mean()*1e4:+.3f} post {d['post'].mean()*1e4:+.3f} net {d['net'].mean()*1e4:+.3f} bp")
    ecb, _ = fix_table(data, days, "Europe/Berlin", 12, 14, 16, 15, 15, 15)
    em, et_, _ = nw(ecb["R"])
    say(f"    ECB 14:15 CET: R {em*1e4:+.3f} bp t {et_:+.2f} (pre {ecb['pre'].mean()*1e4:+.3f}, post {ecb['post'].mean()*1e4:+.3f})")
    me = ld.index.to_series().groupby(ld.index.to_period("M")).transform("max") == ld.index.to_series()
    say(f"    London R on month-end days {ld.loc[me.to_numpy(), 'R'].mean()*1e4:+.3f} vs other {ld.loc[~me.to_numpy(), 'R'].mean()*1e4:+.3f} bp")
    res["secondary"] = dict(ecb=dict(R=em, t=et_), month_end=float(ld.loc[me.to_numpy(), "R"].mean()),
                            other=float(ld.loc[~me.to_numpy(), "R"].mean()))
    open(LOG, "w").write(buf.getvalue()); json.dump(res, open(RES, "w"), indent=1, default=float)
    return 0


def check_inputs():
    print(f"prereg {C.check_pin(NAME)[:16]} OK")
    for p in PAIRS:
        try:
            ba = C.load_bidask(p); print(f"  {p}: {len(ba)} bars {ba.index[0]} .. {ba.index[-1]} (grid OK)")
        except FileNotFoundError:
            print(f"  {p}: MISSING")
    return 0


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    t0, t1, t2 = times(pd.DatetimeIndex([pd.Timestamp("2025-07-10")]), "Europe/London", (14, 0), (16, 0), (18, 0))
    check("London 16:00 in summer = 15:00 UTC", t1[0] == pd.Timestamp("2025-07-10 15:00", tz="UTC"))
    t0, t1, t2 = times(pd.DatetimeIndex([pd.Timestamp("2025-01-10")]), "Asia/Tokyo", (8, 0), (10, 0), (12, 0))
    check("Tokyo 10:00 JST = 01:00 UTC", t1[0] == pd.Timestamp("2025-01-10 01:00", tz="UTC"))
    idx = pd.date_range("2025-07-10 00:00", "2025-07-10 23:45", freq="15min", tz="UTC")
    mid = pd.Series(1.10, index=idx)
    mid[(idx >= "2025-07-10 13:00") & (idx < "2025-07-10 15:00")] = 1.10 - np.linspace(0, 0.0011, 8)   # EURUSD falls = USD up
    mid[idx >= "2025-07-10 15:00"] = 1.0989 + np.linspace(0, 0.0011, (idx >= "2025-07-10 15:00").sum())
    ba = pd.DataFrame({"close_m": mid, "close_b": mid - 0.00005, "close_a": mid + 0.00005})
    days = pd.DatetimeIndex([pd.Timestamp("2025-07-10")])
    bas, per = fix_table({"EUR_USD": ba}, days, "Europe/London", 14, 16, 18)
    check(f"planted W on EUR/USD gives R > 0 ({bas['R'].iloc[0]*1e4:+.1f} bp) with USD up before, down after",
          bas["pre"].iloc[0] > 0 and bas["post"].iloc[0] < 0 and bas["R"].iloc[0] > 0)
    flat = pd.DataFrame({"close_m": 1.1, "close_b": 1.1 - 0.00005, "close_a": 1.1 + 0.00005}, index=idx)
    b2, _ = fix_table({"EUR_USD": flat}, days, "Europe/London", 14, 16, 18)
    check("flat prices: the trade costs exactly two round-trip spreads", abs(b2["net"].iloc[0] + 2 * (0.0001 / 1.10005)) < 2e-7)
    idx2 = pd.date_range("2025-07-09 20:00", "2025-07-10 06:00", freq="15min", tz="UTC")
    fj = pd.DataFrame({"close_m": 150.0, "close_b": 149.99, "close_a": 150.01}, index=idx2)
    bj, _ = fix_table({"USD_JPY": fj}, days, "Asia/Tokyo", 8, 10, 12)
    check("USD_JPY sign: flat -> R = 0", abs(bj["R"].iloc[0]) < 1e-15)
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--self-test", "--check-inputs", "--run"): g.add_argument(f, action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else check_inputs() if a.check_inputs else run())
