#!/usr/bin/env python3
"""preholiday.py -- FLOWS-10, implements PREREGISTRATION_PREHOLIDAY.md.
    --self-test | --check-inputs | --run"""
from __future__ import annotations
import argparse, io, json, os, sys
import numpy as np
import pandas as pd
import common as C
import announce as A

NAME = "PREHOLIDAY"
INSTS = ("SPX500_USD", "NAS100_USD", "US30_USD", "DE30_EUR")
NQ = os.path.join(C.FDATA, "fred_nasdaqcom_long.csv")
LOG, RES = (os.path.join(C.FDATA, f) for f in ("preholiday_run.log", "preholiday_result.json"))


def load_pre():
    C.check_pin("PREHOLIDAY_EVENTS")
    ev = pd.read_csv(os.path.join(C.FDATA, "preholiday_events.csv"), parse_dates=["pre_day", "holiday"])
    return ev


def frame(r: pd.Series, pre: set) -> pd.DataFrame:
    df = pd.DataFrame({"r": r})
    df["PRE"] = df.index.isin(list(pre)).astype(float)
    df["FRI"] = (df.index.dayofweek == 4).astype(float)
    nxt = pd.Series(df.index[1:].tolist() + [pd.NaT], index=df.index)
    df["PL"] = nxt.isin(list(pre)).astype(float).to_numpy()          # the trading day before P
    return df


def fit(df, col="PRE"):
    names = [col, "FRI"]
    X = np.column_stack([np.ones(len(df))] + [df[c].to_numpy() for c in names])
    b, se, t, n = C.ols_nw(df["r"].to_numpy(), X, 5)
    return dict(b=float(b[1]), t=float(t[1]), n=int(n), n_ev=int(df[col].sum()))


def run() -> int:
    buf = io.StringIO()
    def say(*a):
        print(*a); print(*a, file=buf)
    pin, tpin = C.check_pin(NAME), C.check_pin("PREHOLIDAY_EVENTS")
    ev = load_pre(); pre = set(ev["pre_day"])
    say(f"FLOWS-10 PREHOLIDAY  prereg {pin[:16]}  calendar {tpin[:16]}  ({len(ev)} pre-holiday days)")
    res = {"pin": pin, "cal_sha": tpin}
    dly, _ = A.day_table("SPX500_USD")
    dly = dly[dly.index <= C.END]
    df = frame(dly["r"], pre)
    P = fit(df); res["primary"] = P
    say(f"  SPX500 days {len(df)}, P days {P['n_ev']} ({dly.attrs['dropped_short']} short days dropped)")
    say(f"\n  G1 b {P['b']*1e4:+.2f} bp  t {P['t']:+.2f}")
    eras = {}
    for e, a, b in C.ERAS:
        eras[e] = fit(df[(df.index >= a) & (df.index <= b)])
        say(f"  {e}: b {eras[e]['b']*1e4:+.2f} bp t {eras[e]['t']:+.2f} n {eras[e]['n_ev']}")
    res["eras"] = eras
    tr = A.trade(dly, df.index[df["PRE"] == 1])["net"]
    m, t, n = C.mean_t(tr)
    e3 = tr[tr.index >= pd.Timestamp(C.ERAS[2][1])]
    say(f"\n  G3 trade net {m*1e4:+.2f} bp t {t:+.2f} n {n}; E3 net {e3.mean()*1e4:+.2f} (n {len(e3)})")
    res["trade"] = dict(net=m, t=t, n=n, e3_net=float(e3.mean()))
    PL = fit(df, "PL"); res["placebo"] = PL
    say(f"  G4 placebo (day before P): b {PL['b']*1e4:+.2f} bp t {PL['t']:+.2f}")
    G = {"G1": P["b"] > 0 and P["t"] >= 2.0,
         "G2": all(eras[e]["b"] > 0 for e in eras) and eras["E3"]["b"] >= 0.5 * P["b"],
         "G3": m > 0 and t >= 1.65 and e3.mean() > 0,
         "G4": PL["t"] < 2.0 and PL["b"] < P["b"],
         "G5": P["n_ev"] >= 150}
    res["gates"] = G
    kill = [k for k, g in (("K1", "G1"), ("K2", "G2"), ("K3", "G3"), ("K4", "G4")) if not G[g]]
    res["verdict"] = "DEAD " + ",".join(kill) if kill else ("PASS" if G["G5"] else "PASS, G5 short")
    say("\n  " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in G.items()) + f"   VERDICT: {res['verdict']}")
    say("\n  secondary (descriptive):")
    sec = {}
    for inst in INSTS[1:]:
        d2, _ = A.day_table(inst); d2 = d2[d2.index <= C.END]
        f = fit(frame(d2["r"], pre)); sec[inst] = f
        say(f"    {inst:10s} b {f['b']*1e4:+.2f} bp t {f['t']:+.2f}")
    if os.path.exists(NQ):
        q = pd.read_csv(NQ, parse_dates=["date"]).set_index("date")["close"].astype(float)
        rq = (q / q.shift(1) - 1).dropna()
        rq = rq[(rq.index >= "1971-02-08") & (rq.index <= "2004-12-31")]
        # pre-2005 NYSE calendar by the same rule (no special closures before 2005 are listed)
        import fetch_preholiday as FP, datetime as dt
        closed = {}
        for y in range(1970, 2006): closed.update(FP.nyse_holidays(y))
        pre_old = set()
        for d in closed:
            p = d - dt.timedelta(days=1)
            while p.weekday() >= 5 or p in closed: p -= dt.timedelta(days=1)
            pre_old.add(pd.Timestamp(p))
        f = fit(frame(rq, pre_old)); sec["NASDAQCOM_1971_2004"] = f
        say(f"    NASDAQCOM 1971-2004 (close-to-close; rule calendar, MLK from 1998 not modelled) b {f['b']*1e4:+.2f} bp t {f['t']:+.2f} n {f['n_ev']}")
    else:
        say("    NASDAQCOM long history: not fetched yet (fetch_longrun.py)")
    byh = {}
    for name, g in ev.groupby("name"):
        x = df.loc[df.index.isin(list(g["pre_day"])), "r"]
        byh[name] = float(x.mean())
    say("    by holiday (raw mean bp): " + "  ".join(f"{k} {v*1e4:+.1f}" for k, v in sorted(byh.items())))
    res["secondary"] = sec | {"by_holiday": byh}
    open(LOG, "w").write(buf.getvalue()); json.dump(res, open(RES, "w"), indent=1, default=float)
    return 0


def check_inputs():
    print(f"prereg {C.check_pin(NAME)[:16]} OK; calendar {C.check_pin('PREHOLIDAY_EVENTS')[:16]} OK; {len(load_pre())} rows")
    for i in INSTS:
        ba = C.load_bidask(i); print(f"{i}: {len(ba)} bars, grid OK")
    print("NASDAQCOM long:", "present" if os.path.exists(NQ) else "missing (secondary only)")
    return 0


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    days = pd.bdate_range("2005-01-03", "2026-08-31")
    rng = np.random.default_rng(4)
    pre = set(days[::25])
    r = rng.normal(0, 0.011, len(days)); r[days.isin(list(pre))] += 0.004
    r[days.dayofweek == 4] += 0.002
    df = frame(pd.Series(r, index=days), pre)
    f = fit(df)
    check(f"planted +40bp recovered with a Friday effect present ({f['b']*1e4:+.0f}, t {f['t']:+.1f})", abs(f["b"] - 0.004) < 0.0027 and f["t"] > 2)   # 3 se; unbiased over 20 seeds (mean +40.3)
    check("placebo = the trading day before each P", all(df.index[i + 1] in pre for i in np.where(df["PL"] == 1)[0]))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--self-test", "--check-inputs", "--run"): g.add_argument(f, action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else check_inputs() if a.check_inputs else run())
