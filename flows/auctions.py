#!/usr/bin/env python3
"""auctions.py -- FLOWS-11, implements PREREGISTRATION_AUCTIONS.md.  --self-test | --check-inputs | --run"""
from __future__ import annotations
import argparse, io, json, os, re, sys
import numpy as np
import pandas as pd
import common as C
from fixes import at_end, nw

NAME, INST, SEC = "AUCTIONS", "USB10Y_USD", "USB30Y_USD"
LOG, RES = (os.path.join(C.FDATA, f) for f in ("auctions_run.log", "auctions_result.json"))


def close_hm(s: str):
    m = re.match(r"\s*(\d{1,2}):(\d{2})\s*([AP]M)?", str(s or ""), re.I)
    if not m:
        return (13, 0)
    h, mi = int(m.group(1)), int(m.group(2))
    if m.group(3) and m.group(3).upper() == "PM" and h != 12:
        h += 12
    return (h, mi - mi % 15)


def load_days():
    C.check_pin("AUCTION_EVENTS")
    ev = pd.read_csv(os.path.join(C.FDATA, "auction_events.csv"), parse_dates=["date"])
    g = ev.sort_values("years").groupby("date").agg(years=("years", "max"), close=("close_competitive", "first"))
    return g


def windows(dates, hm):
    t1 = pd.DatetimeIndex([pd.Timestamp(d.year, d.month, d.day, h, m, tz=C.NY) for d, (h, m) in zip(dates, hm)]).tz_convert("UTC")
    return t1 - pd.Timedelta(hours=3), t1, t1 + pd.Timedelta(hours=3)


def table(ba, dates, hm):
    t0, t1, t2 = windows(dates, hm)
    m0, m1, m2 = (at_end(ba, "close_m", t) for t in (t0, t1, t2))
    b0, b1, b2 = (at_end(ba, "close_b", t) for t in (t0, t1, t2))
    a0, a1, a2 = (at_end(ba, "close_a", t) for t in (t0, t1, t2))
    df = pd.DataFrame({"pre": m1 / m0 - 1, "post": m2 / m1 - 1,
                       "net": (1 - a1 / b0) + (b2 / a1 - 1)}, index=dates)   # short pre, long post
    df["R"] = df["post"] - df["pre"]
    return df.dropna()


def run():
    buf = io.StringIO()
    def say(*a):
        print(*a); print(*a, file=buf)
    pin, tpin = C.check_pin(NAME), C.check_pin("AUCTION_EVENTS")
    g = load_days(); g = g[(g.index >= "2005-01-01") & (g.index <= C.END)]
    hm = [close_hm(c) for c in g["close"]]
    say(f"FLOWS-11 AUCTIONS  prereg {pin[:16]}  auctions {tpin[:16]}  auction days {len(g)}; close times {pd.Series([f'{h:02d}:{m:02d}' for h, m in hm]).value_counts().to_dict()}")
    ba = C.load_bidask(INST)
    df = table(ba, g.index, hm)
    m, t, n = nw(df["R"])
    say(f"  days with all bars {n}\n\n  G1 mean R (post - pre, price) {m*1e4:+.2f} bp  t {t:+.2f}")
    eras = {}
    for e, a, b in C.ERAS:
        eras[e] = dict(zip(("mean", "t", "n"), nw(df.loc[(df.index >= a) & (df.index <= b), "R"])))
        say(f"  {e}: {eras[e]['mean']*1e4:+.2f} bp t {eras[e]['t']:+.2f} n {eras[e]['n']}")
    say(f"  G3 pre {df['pre'].mean()*1e4:+.2f} bp, post {df['post'].mean()*1e4:+.2f} bp")
    mn, tn, _ = nw(df["net"]); e3 = df.loc[df.index >= pd.Timestamp(C.ERAS[2][1]), "net"]
    say(f"  G4 trade net {mn*1e4:+.2f} bp t {tn:+.2f}; E3 {e3.mean()*1e4:+.2f} (n {len(e3)})")
    wk = pd.bdate_range("2005-01-03", C.END); wk = wk[~wk.isin(g.index)]
    pl = table(ba, wk, [(13, 0)] * len(wk)); pm, pt, pn = nw(pl["R"])
    say(f"  G5 placebo (non-auction weekdays) {pm*1e4:+.2f} bp t {pt:+.2f} n {pn}")
    G = {"G1": m > 0 and t >= 2.0,
         "G2": all(eras[e]["mean"] > 0 for e in eras) and eras["E3"]["mean"] >= 0.5 * m,
         "G3": df["pre"].mean() < 0 and df["post"].mean() > 0,
         "G4": mn > 0 and tn >= 1.65 and e3.mean() > 0,
         "G5": pt < 2.0 and pm < m}
    kill = [k for k, gg in (("K1", "G1"), ("K2", "G2"), ("K3", "G4"), ("K4", "G5")) if not G[gg]]
    res = {"pin": pin, "events_sha": tpin, "mean_R": m, "t": t, "n": n, "eras": eras, "pre": float(df["pre"].mean()),
           "post": float(df["post"].mean()), "trade": dict(net=mn, t=tn, e3=float(e3.mean())),
           "placebo": dict(mean=pm, t=pt), "gates": G,
           "verdict": "DEAD " + ",".join(kill) if kill else ("PASS" if G["G3"] else "PASS but G3")}
    say("\n  " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in G.items()) + f"   VERDICT: {res['verdict']}")
    say("\n  secondary (descriptive):")
    d30 = table(C.load_bidask(SEC), g.index, hm); a30 = nw(d30["R"])
    say(f"    USB30Y: R {a30[0]*1e4:+.2f} bp t {a30[1]:+.2f}")
    bt = {}
    dj = df.join(g["years"])
    for y, sub in dj.groupby(pd.cut(dj["years"], [4, 6, 8, 11, 21, 31]), observed=True):
        bt[str(y)] = float(sub["R"].mean()); say(f"    tenor {y}: R {sub['R'].mean()*1e4:+.2f} bp (n {len(sub)})")
    dly = C.daily(ba, 4)["close_m"]; pos = dly.index.get_indexer(g.index)
    ok = (pos >= 5) & (pos + 5 < len(dly))
    before = dly.to_numpy()[pos[ok]] / dly.to_numpy()[pos[ok] - 5] - 1
    after = dly.to_numpy()[pos[ok] + 5] / dly.to_numpy()[pos[ok]] - 1
    say(f"    multi-day (USB10Y daily): D-5 -> D {np.mean(before)*1e4:+.2f} bp; D -> D+5 {np.mean(after)*1e4:+.2f} bp (n {ok.sum()}, overlapping)")
    res["secondary"] = dict(usb30y=a30[:2], by_tenor=bt, before5=float(np.mean(before)), after5=float(np.mean(after)))
    open(LOG, "w").write(buf.getvalue()); json.dump(res, open(RES, "w"), indent=1, default=float)
    return 0


def check_inputs():
    print(f"prereg {C.check_pin(NAME)[:16]} OK; auctions {C.check_pin('AUCTION_EVENTS')[:16]} OK; days {len(load_days())}")
    ba = C.load_bidask(INST); print(f"{INST} {len(ba)} bars (grid OK)")
    return 0


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    check("close time parse", close_hm("01:00 PM") == (13, 0) and close_hm("11:30 AM") == (11, 30) and close_hm("") == (13, 0))
    d = pd.DatetimeIndex([pd.Timestamp("2025-07-10")])
    t0, t1, t2 = windows(d, [(13, 0)])
    check("13:00 ET in July = 17:00 UTC; windows 10:00 and 16:00 ET", t1[0] == pd.Timestamp("2025-07-10 17:00", tz="UTC")
          and t0[0].hour == 14 and t2[0].hour == 20)
    idx = pd.date_range("2025-07-10 12:00", "2025-07-10 21:00", freq="15min", tz="UTC")
    px = pd.Series(110.0, index=idx); px[(idx >= "2025-07-10 14:00") & (idx < "2025-07-10 16:45")] = np.linspace(110, 109.9, 11)
    px[idx >= "2025-07-10 16:45"] = 109.9; px[idx >= "2025-07-10 17:00"] = np.linspace(109.9, 110.05, (idx >= "2025-07-10 17:00").sum())
    ba = pd.DataFrame({"close_m": px, "close_b": px - 0.01, "close_a": px + 0.01})
    df = table(ba, d, [(13, 0)])
    check(f"inverted-V price pattern gives pre<0, post>0, R>0 ({df['R'].iloc[0]*1e4:+.1f} bp)",
          df["pre"].iloc[0] < 0 and df["post"].iloc[0] > 0 and df["R"].iloc[0] > 0)
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--self-test", "--check-inputs", "--run"): g.add_argument(f, action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else check_inputs() if a.check_inputs else run())
