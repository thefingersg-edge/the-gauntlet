#!/usr/bin/env python3
"""macro.py -- FLOWS-14, implements PREREGISTRATION_MACRO.md.  --self-test | --check-inputs | --run"""
from __future__ import annotations
import argparse, io, json, math, os, sys
import numpy as np
import pandas as pd
import common as C

NAME = "MACRO"
LR = os.path.join(C.FDATA, "longrun")
XLS = os.path.join(LR, "ie_data.xls")
EST0, OOS0, OOS_RECENT = pd.Timestamp("1934-01-01"), pd.Timestamp("1965-01-01"), pd.Timestamp("2000-01-01")
LOG, RES = (os.path.join(C.FDATA, f) for f in ("macro_run.log", "macro_result.json"))


def fred(name):
    d = pd.read_csv(os.path.join(LR, f"{name}.csv"), parse_dates=["date"]).set_index("date")["value"].astype(float)
    d.index = d.index.to_period("M").to_timestamp(); return d


def shiller() -> pd.DataFrame:
    raw = pd.read_excel(XLS, sheet_name="Data", header=None)
    hr = next(i for i in range(40) if str(raw.iat[i, 0]).strip() == "Date")
    hdr = [str(x).strip() for x in raw.iloc[hr]]
    df = raw.iloc[hr + 1:].copy(); df.columns = hdr
    df = df[pd.to_numeric(df["Date"], errors="coerce").notna()]
    x = df["Date"].astype(float)
    yr = np.floor(x).astype(int); mo = np.round((x - yr) * 100).astype(int)
    df.index = pd.to_datetime(dict(year=yr, month=mo, day=1))
    gs = [c for c in df.columns if c.startswith("Rate GS10") or c == "GS10"][0]
    out = pd.DataFrame({"P": pd.to_numeric(df["P"], errors="coerce"), "D": pd.to_numeric(df["D"], errors="coerce"),
                        "CAPE": pd.to_numeric(df["CAPE"], errors="coerce"), "GS10": pd.to_numeric(df[gs], errors="coerce")})
    return out[out.index <= C.END]


def dataset():
    sh = shiller(); tb = fred("TB3MS"); baa = fred("BAA"); aaa = fred("AAA")
    idx = sh.index
    r = np.log((sh["P"] + sh["D"] / 12) / sh["P"].shift(1)) - np.log(1 + tb.reindex(idx).shift(1) / 1200)
    X = pd.DataFrame({"CAPE": np.log(sh["CAPE"]), "TERM": sh["GS10"] - tb.reindex(idx),
                      "CREDIT": baa.reindex(idx) - aaa.reindex(idx)}, index=idx)
    return r.rename("r"), X.shift(2)        # predictor known at end of t-1, plus one month of publication lag


def oos(r: pd.Series, x: pd.Series):
    d = pd.concat([r.rename("r"), x.rename("x")], axis=1).dropna()
    d = d[d.index >= EST0]
    rows = []
    for t in d.index[d.index >= OOS0]:
        h = d[d.index < t]
        b1, b0 = np.polyfit(h["x"], h["r"], 1)
        rows.append((t, d.at[t, "r"], b0 + b1 * d.at[t, "x"], h["r"].mean(), h["r"].iloc[-60:].var()))
    return pd.DataFrame(rows, columns=["date", "r", "f", "mean", "var60"]).set_index("date")


def stats(o: pd.DataFrame):
    e1, e0 = o["r"] - o["f"], o["r"] - o["mean"]
    r2 = 1 - (e1 ** 2).sum() / (e0 ** 2).sum()
    cw = e0 ** 2 - (e1 ** 2 - (o["mean"] - o["f"]) ** 2)
    b, se, t, n = C.ols_nw(cw.to_numpy(), np.ones((len(cw), 1)), 5)
    w = (o["f"] / (3 * o["var60"])).clip(0, 1.5)
    sh = lambda x: float(x.mean() / x.std() * math.sqrt(12))
    return dict(r2=float(r2), cw_t=float(t[0]), n=int(n), sharpe_timing=sh(w * o["r"]), sharpe_bh=sh(o["r"]))


def run():
    buf = io.StringIO()
    def say(*a):
        print(*a); print(*a, file=buf)
    pin = C.check_pin(NAME)
    r, X = dataset()
    say(f"FLOWS-14 MACRO  prereg {pin[:16]}  Shiller {C.sha256(XLS)[:16]}  returns {r.dropna().index[0].date()}..{r.dropna().index[-1].date()}")
    res, pv = {"pin": pin, "predictors": {}}, {}
    for k in X.columns:
        o = oos(r, X[k]); a = stats(o); rec = stats(o[o.index >= OOS_RECENT])
        G = {"G1": a["r2"] > 0 and a["cw_t"] >= 1.65, "G2": rec["r2"] > 0, "G3": a["sharpe_timing"] > a["sharpe_bh"]}
        pv[k] = 0.5 * math.erfc(a["cw_t"] / math.sqrt(2))                   # one-sided
        res["predictors"][k] = dict(full=a, since2000=rec, gates=G, passed=all(G.values()))
        say(f"\n  {k:6s} R2_oos {a['r2']*100:+.2f}%  CW t {a['cw_t']:+.2f}  | since 2000 R2 {rec['r2']*100:+.2f}%  | "
            f"timing Sharpe {a['sharpe_timing']:+.3f} vs buy-hold {a['sharpe_bh']:+.3f}  (n {a['n']})")
        say("         " + "  ".join(f"{g} {'PASS' if v else 'FAIL'}" for g, v in G.items()))
    q = C.bh(pv)
    for k in X.columns:
        res["predictors"][k]["bh_q"] = q[k]
    passed = [k for k in X.columns if res["predictors"][k]["passed"]]
    res["verdict"] = ("PASS: " + ", ".join(passed)) if passed else "DEAD: no predictor passes G1-G3"
    say(f"\n  BH q (G1): " + "  ".join(f"{k} {q[k]:.3f}" for k in X.columns) + f"\n  VERDICT: {res['verdict']}")
    open(LOG, "w").write(buf.getvalue()); json.dump(res, open(RES, "w"), indent=1, default=float)
    return 0


def check_inputs():
    print(f"prereg {C.check_pin(NAME)[:16]} OK")
    sh = shiller(); print(f"Shiller {sh.index[0].date()}..{sh.index[-1].date()}, CAPE from {sh['CAPE'].first_valid_index().date()}")
    for n in ("TB3MS", "BAA", "AAA"):
        f = fred(n); print(f"  {n} {f.index[0].date()}..{f.index[-1].date()}")
    return 0


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    idx = pd.date_range("1930-01-01", "2026-08-01", freq="MS")
    rng = np.random.default_rng(3)
    xv = np.zeros(len(idx)); e = rng.normal(0, 1, len(idx))
    for i in range(1, len(idx)): xv[i] = 0.95 * xv[i - 1] + e[i]           # persistent, like a valuation ratio
    x = pd.Series(xv, index=idx)
    r = pd.Series(0.004 + 0.003 * x.shift(2).fillna(0) + rng.normal(0, 0.04, len(idx)), index=idx)   # R2 ~5%
    o = oos(r, x.shift(2)); a = stats(o)
    check(f"a real predictor gets R2_oos > 0 (R2 {a['r2']*100:+.2f}%, CW t {a['cw_t']:+.1f})", a["r2"] > 0 and a["cw_t"] > 1.65)
    o0 = oos(pd.Series(rng.normal(0.004, 0.04, len(idx)), index=idx), x.shift(2)); a0 = stats(o0)
    check(f"a useless predictor gets R2_oos <= ~0 (R2 {a0['r2']*100:+.2f}%)", a0["r2"] < 0.005)
    check("forecasts use only the past (first OOS month is 1965-01)", o.index[0] == OOS0)
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--self-test", "--check-inputs", "--run"): g.add_argument(f, action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else check_inputs() if a.check_inputs else run())
