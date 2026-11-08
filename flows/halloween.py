#!/usr/bin/env python3
"""halloween.py -- FLOWS-12, implements PREREGISTRATION_HALLOWEEN.md.  --self-test | --check-inputs | --run"""
from __future__ import annotations
import argparse, io, json, os, sys
import numpy as np
import pandas as pd
import common as C

NAME = "HALLOWEEN"
NQ = os.path.join(C.FDATA, "longrun", "NASDAQCOM.csv")
LOG, RES = (os.path.join(C.FDATA, f) for f in ("halloween_run.log", "halloween_result.json"))
THIRDS = (("1971-1989", "1971-01-01", "1989-12-31"), ("1990-2007", "1990-01-01", "2007-12-31"), ("2008-2026", "2008-01-01", "2026-08-31"))


def monthly(close: pd.Series) -> pd.Series:
    me = close.groupby(close.index.to_period("M")).last()
    r = np.log(me / me.shift(1)).dropna()
    r.index = r.index.to_timestamp()
    return r


def fit(r: pd.Series):
    W = r.index.month.isin([11, 12, 1, 2, 3, 4]).astype(float)
    X = np.column_stack([np.ones(len(r)), W])
    b, se, t, n = C.ols_nw(r.to_numpy(), X, 6)
    return dict(b=float(b[1]), t=float(t[1]), n=int(n))


def run():
    buf = io.StringIO()
    def say(*a):
        print(*a); print(*a, file=buf)
    pin = C.check_pin(NAME)
    q = pd.read_csv(NQ, parse_dates=["date"]).set_index("date")["value"].astype(float)
    q = q[q.index <= C.END]
    r = monthly(q); r = r[r.index >= "1971-03-01"]
    say(f"FLOWS-12 HALLOWEEN  prereg {pin[:16]}  NASDAQCOM {C.sha256(NQ)[:16]}  months {len(r)} {r.index[0].date()}..{r.index[-1].date()}")
    P = fit(r)
    say(f"\n  G1 b (Nov-Apr minus May-Oct, monthly log) {P['b']*100:+.3f}%  t {P['t']:+.2f}")
    th = {}
    for lab, a, b in THIRDS:
        th[lab] = fit(r[(r.index >= a) & (r.index <= b)])
        say(f"  {lab}: b {th[lab]['b']*100:+.3f}% t {th[lab]['t']:+.2f}")
    dly = C.daily(C.load_bidask("SPX500_USD"), 4)
    s = dly["close_m"]; rs = monthly(s)
    P3 = fit(rs)
    say(f"  G3 SPX500 CFD 2005-2026: b {P3['b']*100:+.3f}% t {P3['t']:+.2f}")
    fin = C.Financing("SPX500_USD", C.load_snapshot(), C.load_fred("DGS3MO"))
    rd = s.pct_change().dropna()
    held = rd.index.month.isin([11, 12, 1, 2, 3, 4])
    charge = pd.Series([fin.charge([d], "long") for d in s.index], index=s.index).shift(1).reindex(rd.index).fillna(0)
    bh = rd + charge
    rule = pd.Series(np.where(held, rd + charge, 0.0), index=rd.index)
    sh = lambda x: float(x.mean() / x.std() * np.sqrt(252))
    say(f"  G4 Sharpe net of financing: rule {sh(rule):+.3f}  buy-and-hold {sh(bh):+.3f}")
    G = {"G1": P["b"] > 0 and P["t"] >= 2.0,
         "G2": all(v["b"] > 0 for v in th.values()) and th["2008-2026"]["b"] >= 0.5 * P["b"],
         "G3": P3["b"] > 0, "G4": sh(rule) > sh(bh)}
    kill = [k for k, gg in (("K1", "G1"), ("K2", "G2")) if not G[gg]]
    res = {"pin": pin, "primary": P, "thirds": th, "spx_cfd": P3, "sharpe_rule": sh(rule), "sharpe_bh": sh(bh), "gates": G,
           "verdict": "DEAD " + ",".join(kill) if kill else ("PASS" if G["G3"] and G["G4"] else "PASS on the index; CFD checks: see G3/G4")}
    say("\n  " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in G.items()) + f"   VERDICT: {res['verdict']}")
    open(LOG, "w").write(buf.getvalue()); json.dump(res, open(RES, "w"), indent=1, default=float)
    return 0


def check_inputs():
    print(f"prereg {C.check_pin(NAME)[:16]} OK")
    q = pd.read_csv(NQ); print(f"NASDAQCOM {len(q)} rows {q['date'].iloc[0]} .. {q['date'].iloc[-1]}")
    return 0


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    d = pd.bdate_range("1971-01-01", "2026-08-31")
    rng = np.random.default_rng(2)
    lr = rng.normal(0.0003, 0.012, len(d)) + np.where(d.month.isin([11, 12, 1, 2, 3, 4]), 0.0006, 0.0)
    c = pd.Series(100 * np.exp(np.cumsum(lr)), index=d)
    r = monthly(c); P = fit(r)
    check(f"planted ~1.26%/month winter premium recovered ({P['b']*100:+.2f}%, t {P['t']:+.1f})", 0.6 < P["b"] * 100 < 1.9 and P["t"] > 2)
    check("monthly returns are month-end to month-end", r.index[0] == pd.Timestamp("1971-02-01"))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--self-test", "--check-inputs", "--run"): g.add_argument(f, action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else check_inputs() if a.check_inputs else run())
