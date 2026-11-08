#!/usr/bin/env python3
"""
lowvix.py -- FLOWS-7: the release-day premium on LOW-VIX evenings.
Implements flows/PREREGISTRATION_LOWVIX.md; refuses to run if it changed.

    python3 lowvix.py --self-test       synthetic only
    python3 lowvix.py --check-inputs    files and hashes -- NO returns
    python3 lowvix.py --holdout         Part H, once (1994-2004)
    python3 lowvix.py --forward         Part F: appends the forward log; prints only the
                                        trade COUNT until the 75th (kill check) and 150th trade
"""
from __future__ import annotations
import argparse, io, json, os, sys
import numpy as np
import pandas as pd
import common as C
import announce as A

NAME = "LOWVIX"
H0, H1, HALF = pd.Timestamp("1994-01-01"), pd.Timestamp("2004-12-31"), pd.Timestamp("1999-12-31")
F0 = pd.Timestamp("2026-09-01")
NQ, SP = (os.path.join(C.FDATA, f) for f in ("fred_nasdaqcom_hold.csv", "spx_stooq_hold.csv"))
LOG = os.path.join(C.FDATA, "lowvix_holdout_run.log")
RES = os.path.join(C.FDATA, "lowvix_holdout_result.json")
FWD = os.path.join(C.FDATA, "lowvix_forward_trades.csv")


def load_close(path) -> pd.DataFrame:
    d = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
    d["close"] = pd.to_numeric(d["close"], errors="coerce")
    d = d.dropna()
    return pd.DataFrame({"r": d["close"] / d["close"].shift(1) - 1}).dropna()


def frame(r: pd.DataFrame, ev: pd.DataFrame, vix: pd.Series) -> pd.DataFrame:
    df = A.design(r, ev, vix)
    df["LOW"] = 1 - df["HIGH"]
    df["AL"] = df["A"] * df["LOW"]
    return df


def fit(df) -> dict:
    f = A._fit(df, ["AL", "AH", "HIGH", "FOMC"])
    return dict(bL=f["AL"]["b"], tL=f["AL"]["t"], bH=f.get("AH", {}).get("b", np.nan),
                tH=f.get("AH", {}).get("t", np.nan), n=f["n"], n_AL=int(df["AL"].sum()))


def holdout() -> int:
    buf = io.StringIO()
    def say(*a):
        print(*a); print(*a, file=buf)
    pin, tpin = C.check_pin(NAME), C.check_pin("HOLDOUT_EVENTS")
    ev = pd.read_csv(os.path.join(C.FDATA, "holdout_events.csv"), parse_dates=["date"])
    vix = A.load_vix()
    say(f"FLOWS-7 Part H  prereg {pin[:16]}  events {tpin[:16]}  NASDAQCOM {C.sha256(NQ)[:16]}")
    res = {"pin": pin, "events_sha": tpin, "nasdaq_sha": C.sha256(NQ)}
    df = frame(load_close(NQ), ev, vix)
    df = df[(df.index >= H0) & (df.index <= H1)]
    P = fit(df); res["primary"] = P
    say(f"  days {len(df)}; A&LOW {P['n_AL']}; A&HIGH {int(df['AH'].sum())}; FOMC {int(df['FOMC'].sum())}")
    say(f"\n  bL (release excess, LOW VIX) {P['bL']*1e4:+.2f} bp  t {P['tL']:+.2f}")
    halves = {}
    for lab, a, b in (("1994-99", H0, HALF), ("2000-04", HALF + pd.Timedelta(days=1), H1)):
        halves[lab] = fit(df[(df.index >= a) & (df.index <= b)])
        say(f"  {lab}: bL {halves[lab]['bL']*1e4:+.2f} bp t {halves[lab]['tL']:+.2f} n_AL {halves[lab]['n_AL']}")
    res["halves"] = halves
    G = {"H1": P["bL"] > 0 and P["tL"] >= 1.65, "H2": P["bL"] >= 0.0005,
         "H3": all(h["bL"] > 0 for h in halves.values())}
    res["gates"] = G
    res["verdict"] = "CONFIRMED" if all(G.values()) else "NOT CONFIRMED"
    say("\n  " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in G.items()) + f"   VERDICT: {res['verdict']}")
    say("\n  secondary (descriptive):")
    say(f"    bH (release excess, HIGH VIX) {P['bH']*1e4:+.2f} bp t {P['tH']:+.2f}")
    per = {}
    for k in A.TYPES:
        d2 = df.assign(KL=df[k] * (1 - df["FOMC"]) * df["LOW"], OA=((df["A"] == 1) & (df[k] == 0)).astype(float))
        f = A._fit(d2, ["KL", "OA", "HIGH", "FOMC"])
        per[k] = dict(b=f["KL"]["b"], t=f["KL"]["t"], n=int(d2["KL"].sum()))
        say(f"    {k:4s} low-VIX {per[k]['b']*1e4:+.2f} bp t {per[k]['t']:+.2f} (n {per[k]['n']})")
    res["per_type"] = per
    if os.path.exists(SP):
        ds = frame(load_close(SP), ev, vix); ds = ds[(ds.index >= H0) & (ds.index <= H1)]
        Ps = fit(ds); res["spx_stooq"] = Ps
        say(f"    S&P 500 (stooq, secondary): bL {Ps['bL']*1e4:+.2f} bp t {Ps['tL']:+.2f} (n_AL {Ps['n_AL']})")
    else:
        say("    S&P 500 (stooq): not fetched")
    open(LOG, "w").write(buf.getvalue())
    json.dump(res, open(RES, "w"), indent=1, default=float)
    return 0


def forward() -> int:
    C.check_pin(NAME)
    r = json.load(open(RES)) if os.path.exists(RES) else {}
    if r.get("verdict") != "CONFIRMED":
        print(f"Part F does not run: Part H verdict is {r.get('verdict', 'not run')!r} (section 3).")
        return 0
    ev = pd.read_csv(os.path.join(C.FDATA, "announce_events.csv"), parse_dates=["date"])
    extra = os.path.join(C.FDATA, "lowvix_forward_events.csv")
    if os.path.exists(extra):
        ev = pd.concat([ev, pd.read_csv(extra, parse_dates=["date"])])
    vix = A.load_vix()
    ba = C.load_bidask("SPX500_USD", end=pd.Timestamp.today().normalize())
    dly = C.daily(ba, 1); dly = dly[(dly["nbars"] >= A.MIN_BARS) & (dly.index >= F0)]
    dly["r"] = dly["close_m"] / dly["open_m"] - 1
    df = frame(dly, ev, vix)
    days = df.index[df["AL"] == 1]
    tr = A.trade(dly, days)
    tr.to_csv(FWD)
    n = len(tr)
    print(f"forward A&LOW trades logged: {n} (since {F0.date()}); VIX missing for {int(dly.index.difference(df.index).size)} days")
    if n >= 150:
        m, t, _ = C.mean_t(tr["net"].iloc[:150])
        print(f"EVALUATION at 150: mean net {m*1e4:+.2f} bp t {t:+.2f}  F1 {'PASS' if m > 0 and t >= 1.65 else 'FAIL'}  F2 {'PASS' if m >= 4e-4 else 'FAIL'}")
    elif n >= 75:
        m = tr["net"].iloc[:75].mean()
        print(f"kill check at 75: {'KILL' if m <= -4e-4 else 'continue'} (the mean itself is not printed)")
    return 0


def check_inputs() -> int:
    print(f"prereg pin {C.check_pin(NAME)[:16]} OK; events {C.check_pin('HOLDOUT_EVENTS')[:16]} OK")
    ev = pd.read_csv(os.path.join(C.FDATA, "holdout_events.csv"), parse_dates=["date"])
    print("events:", ev["event"].value_counts().to_dict(), ev["date"].min().date(), "..", ev["date"].max().date())
    for p in (NQ, SP):
        if os.path.exists(p):
            d = pd.read_csv(p)
            print(f"{os.path.basename(p)}: {len(d)} rows {d['date'].iloc[0]} .. {d['date'].iloc[-1]}")
        else:
            print(f"{os.path.basename(p)}: missing")
    return 0


def self_test() -> int:
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    days = pd.bdate_range("1993-01-04", "2004-12-31")
    rng = np.random.default_rng(9)
    vix = pd.Series(18 + 6 * np.sin(np.arange(len(days)) / 50) + rng.normal(0, 1, len(days)), index=days)
    evd = [d for d in days if d.day <= 7 and d.dayofweek == 4]
    ev = pd.DataFrame({"event": "NFP", "date": evd})
    r = rng.normal(0, 0.012, len(days))
    low = (1 - A.high_state(vix, days)).fillna(0).to_numpy()
    r[days.isin(evd) & (low == 1)] += 0.01
    df = frame(pd.DataFrame({"r": r}, index=days), ev, vix)
    df = df[df.index >= H0]
    P = fit(df)
    check(f"planted +100bp on A&LOW recovered ({P['bL']*1e4:+.0f} bp, t {P['tL']:+.1f})", abs(P["bL"] - 0.01) < 0.004 and P["tL"] > 2)
    check("AL + AH = A", int((df["AL"] + df["AH"] - df["A"]).abs().sum()) == 0)
    P0 = fit(frame(pd.DataFrame({"r": rng.normal(0, 0.012, len(days))}, index=days), ev, vix))
    check(f"null: bL not significant (t {P0['tL']:+.2f})", abs(P0["tL"]) < 2.5)
    c = pd.DataFrame({"date": ["2001-01-02", "2001-01-03"], "close": [100.0, 101.0]})
    p = os.path.join(C.FDATA, "_lowvix_selftest.csv"); c.to_csv(p, index=False)
    rr = load_close(p); os.remove(p)
    check("close-to-close return", abs(rr["r"].iloc[0] - 0.01) < 1e-12)
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--self-test", "--check-inputs", "--holdout", "--forward"):
        g.add_argument(f, action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else check_inputs() if a.check_inputs else holdout() if a.holdout else forward())
