#!/usr/bin/env python3
"""CARRY2 harness (PREREGISTRATION_CARRY2.md, sha dddef328...): three carry designs that cannot sit short a market that keeps climbing.
    python3 carry2_run.py --self-test
    python3 carry2_run.py run     -> data/futport1/run_carry2.log  (refuses to run twice)
Built on scripts/futport1_run.py (frozen, sha 6b28c761...): load, market (returns, roll, sigma timing, trend), costs, scale, stats.
Mechanical readings fixed here BEFORE the run (logged in PROVENANCE):
  * tau_t = the median gap (days / 365) between consecutive c.0 contract changes dated within (t - 730 days, t]. It needs >= 2 such changes, else NaN.
  * C_t = (c0_t / c1_t - 1) / tau_t. "Weekly": the value at each calendar week's last data row is carried forward to the following rows, so a
    Friday value is first used for the weight set at Friday's close, which earns from Monday (futport1 timing: w_{t-1} x r_t).
  * sigma = the futport1 sigma (EWMA com 60 of r^2 x 252, lagged one row). Weight cap +-4. No weight before row 252 (as futport1).
  * A: per date, within each class with >= 2 markets that have a weekly C and a sigma: d = rank(C) - mean rank; long leg normalised to +1 and
    short leg to -1; w = d_norm x 0.10/sigma (capped); each class x 1/(number of classes active that date). Sleeve P&L = SUM over markets.
  * B: S = sign(C_week - mean of daily C over the trailing 252 rows, both at the week's last row); w = S x 0.10/sigma. Sleeve = mean over active (futport1).
  * C: w = sign(C_week) x 0.10/sigma if sign(C_week) == sign(futport1 trend at t), else 0. Sleeve = mean over active (futport1).
  * Every sleeve is scaled by futport1.scale (10% target, 3x cap). Live = the dates where the futport1 trend sleeve and the design sleeve are both defined.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, math, hashlib
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE)
import futport1_run as FP
SPEC = os.path.join(FB, "PREREGISTRATION_CARRY2.md"); SPEC_SHA = "dddef3284f5fd80e535e165811662ac2c82d7c06f592e501459d192e36b846c1"
CLASS = {"equity": ["ES", "NQ", "YM", "RTY"], "rates": ["ZT", "ZF", "ZN", "ZB"], "fx": ["6E", "6J", "6B", "6A", "6C", "6S"],
         "metals": ["GC", "SI", "HG", "PL"], "energy": ["CL", "NG", "HO", "RB"], "ags": ["ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE"]}
T = 2.13
DISC = FP.DISC


def pin():
    if hashlib.sha256(open(SPEC, "rb").read()).hexdigest() != SPEC_SHA: sys.exit("spec changed -- refused")


def carry_frame(j):
    m = FP.market(j); idx = j.index; c0, c1 = j["close0"].to_numpy(float), j["close1"].to_numpy(float)
    rolls = idx[m["roll"].to_numpy()]
    tau = np.full(len(idx), np.nan)
    for i, t in enumerate(idx):
        w = rolls[(rolls > t - pd.Timedelta(days=730)) & (rolls <= t)]
        if len(w) >= 2: tau[i] = np.median(np.diff(w.values).astype("timedelta64[D]").astype(float)) / 365
    C = (c0 / c1 - 1) / tau
    r = m["r"].to_numpy(); var = pd.Series(r ** 2).ewm(com=60).mean().to_numpy(); sig = np.r_[np.nan, np.sqrt(var * 252)[:-1]]
    sig = np.where(np.arange(len(idx)) >= 252, sig, np.nan)
    wk = pd.Series(idx.isocalendar().year.astype(int) * 100 + idx.isocalendar().week.astype(int), index=idx)
    last = (wk != wk.shift(-1)).to_numpy()
    Cw = pd.Series(np.where(last, C, np.nan), index=idx).ffill().to_numpy()
    Cm = pd.Series(C).rolling(252, min_periods=252).mean().to_numpy()
    Bw = pd.Series(np.where(last, np.sign(C - Cm), np.nan), index=idx).ffill().to_numpy()
    tr = np.sign(m["w_tr"].to_numpy())
    return pd.DataFrame(dict(r=m["r"], roll=m["roll"], c0=c0, C=C, Cw=Cw, Bs=Bw, sig=sig, trs=tr, w_tr=m["w_tr"]), index=idx)


def wcap(s, sig): return np.where(np.isfinite(sig) & (sig > 0) & np.isfinite(s), np.clip(s * 0.10 / np.where(sig > 0, sig, 1), -4, 4), np.nan)


def design_A(M):
    cal = pd.DatetimeIndex(sorted(set().union(*[m.index for m in M.values()])))
    Cw = pd.DataFrame({k: m["Cw"].reindex(cal).ffill() for k, m in M.items()})
    SG = pd.DataFrame({k: m["sig"].reindex(cal).ffill() for k, m in M.items()})
    W = pd.DataFrame(np.nan, index=cal, columns=list(M))
    ok = Cw.notna() & SG.notna() & (SG > 0)
    for t in range(len(cal)):
        act_classes = []
        for cl, rs in CLASS.items():
            rs = [x for x in rs if ok.iat[t, W.columns.get_loc(x)]]
            if len(rs) >= 2: act_classes.append(rs)
        if not act_classes: continue
        for rs in act_classes:
            v = Cw.iloc[t][rs]; rk = v.rank(method="average"); d = rk - rk.mean()
            pos = d[d > 0].sum()
            if pos <= 0: continue
            dn = d / pos
            for x in rs:
                W.iat[t, W.columns.get_loc(x)] = float(np.clip(dn[x] * 0.10 / SG.iat[t, W.columns.get_loc(x)], -4, 4)) / len(act_classes)
    return W


def pnl_from_weights(M, W, mode):
    """mode 'sum' (design A, weights already normalised) or 'mean' (futport1-style average over active markets)."""
    cal = W.index; P = {}
    for k, m in M.items():
        w = W[k]; r = m["r"].reindex(cal).fillna(0.0); roll = m["roll"].reindex(cal).fillna(False).astype(bool)
        wp = w.shift(1)
        P[k] = wp * r - (w - wp).abs().fillna(0) * FP.COST[k] - np.where(roll, wp.abs() * 2 * FP.COST[k], 0.0)
    P = pd.DataFrame(P); act = W.shift(1).notna()
    if mode == "sum": raw = P.where(act).sum(axis=1).where(act.any(axis=1))
    else: raw = P.where(act).sum(axis=1) / act.sum(axis=1).replace(0, np.nan)
    turnover = (W - W.shift(1)).abs().sum(axis=1)
    return raw, P.where(act), turnover


def weights_TS(M, which):
    cal = pd.DatetimeIndex(sorted(set().union(*[m.index for m in M.values()])))
    W = {}
    for k, m in M.items():
        if which == "B": s = m["Bs"].to_numpy()
        else:
            cs = np.sign(m["Cw"].to_numpy()); s = np.where(np.isfinite(cs) & np.isfinite(m["trs"].to_numpy()), np.where(cs == m["trs"].to_numpy(), cs, 0.0), np.nan)
        W[k] = pd.Series(wcap(s, m["sig"].to_numpy()), index=m.index).reindex(cal).ffill()
    return pd.DataFrame(W)


def run():
    pin(); P = os.path.join(FP.D, "run_carry2.log")
    if os.path.exists(P): sys.exit("already run")
    J = {r: FP.load(r) for r in FP.ROOTS}
    M = {r: carry_frame(J[r]) for r in FP.ROOTS}
    MF = {r: FP.market(J[r]) for r in FP.ROOTS}
    tr_raw, _, _ = FP.sleeve_pnl(MF, "w_tr"); trend, _ = FP.scale(tr_raw)
    es = MF["ES"]["r"]
    L = ["CARRY2 -- three carry designs (cross-sectional / demeaned / trend-agreeing) on 29 CME futures", "  " + DISC, ""]
    res = {}
    for nm, (W, mode) in (("A cross-sectional", (design_A(M), "sum")), ("B demeaned time-series", (weights_TS(M, "B"), "mean")),
                          ("C carry + trend agreement", (weights_TS(M, "C"), "mean"))):
        raw, Pm, to = pnl_from_weights(M, W, mode); sc, s = FP.scale(raw)
        live = sc.dropna().index.intersection(trend.dropna().index); x = sc.reindex(live); tv = trend.reindex(live)
        S = FP.stats(x); St = FP.stats(tv); combo = 0.5 * x + 0.5 * tv; Sc = FP.stats(combo)
        g1 = S["shy"] >= T; g2 = all(e > 0 for e in S["eras"]); g3 = Sc["sh"] > St["sh"]
        res[nm] = (g1, g2, g3)
        gold = W[["GC", "SI"]].reindex(live)[(live >= "2019-01-01")]
        L += [f"  {nm}: " + FP.fmt(S),
              f"     combo 50/50 with the trend sleeve: Sharpe {Sc['sh']:+.2f} vs trend alone {St['sh']:+.2f};  corr with trend {x.corr(tv):+.2f}, with ES {x.corr(es.reindex(live).fillna(0)):+.2f};"
              f"  mean daily turnover {to.reindex(live).mean():.3f}",
              f"     gold / silver average weight 2019-26: {gold['GC'].mean():+.3f} / {gold['SI'].mean():+.3f} (share of days net short: {(gold['GC'] < 0).mean() * 100:.0f}% / {(gold['SI'] < 0).mean() * 100:.0f}%)",
              f"     G1 {'PASS' if g1 else 'FAIL'} (x sqrt(yrs) >= {T})  G2 {'PASS' if g2 else 'FAIL'}  G3 {'PASS' if g3 else 'FAIL'}  -> {'PASS' if g1 and g2 and g3 else 'FAIL'}"]
        if nm.startswith("A"):
            for cl, rs in CLASS.items():
                xc = Pm[rs].sum(axis=1).reindex(live) * s.reindex(live)
                L.append(f"       class {cl:7s} Sharpe {xc.mean() / xc.std() * math.sqrt(252) if xc.std() > 0 else float('nan'):+.2f}  sum {xc.sum() * 100:+.1f}%")
        L.append("")
    L.append("  CARRY2: " + ", ".join(f"{k.split()[0]} {'PASS' if all(v) else 'FAIL'}" for k, v in res.items()))
    open(P, "w").write("\n".join(L) + "\n"); print("\n".join(L))


def self_test():
    ok = True
    idx = pd.bdate_range("2018-01-01", periods=700)
    c0 = 100 + np.arange(700) * 0.05; c1 = c0 * 1.01
    iid = (np.arange(700) // 63)                                       # a roll every 63 rows
    j = pd.DataFrame(dict(instrument_id0=iid, close0=c0, instrument_id1=iid + 1, close1=c1), index=idx)
    F = carry_frame(j)
    tau = (0.01 / -F["C"].iloc[-1])                                     # C = -0.01/1.01/tau
    e1 = abs((1 / 1.01 - 1) / F["C"].iloc[-1] - (91 / 365)) < 0.02     # 63 business days ~ 91 calendar days
    ok &= e1; print(f"  [{'PASS' if e1 else 'FAIL'}] tau from the median roll gap (~91 days) -> annualised carry")
    wkend = F.index[(F.index.weekday == 4)][-2]; nxt = F.index[F.index.get_loc(wkend) + 1]
    e2 = F.at[nxt, "Cw"] == F.at[wkend, "C"]; ok &= e2; print(f"  [{'PASS' if e2 else 'FAIL'}] Friday carry carried into the next week")
    # design A on a planted class: two markets, one deeper contango -> it is the short
    M = {}
    for k, prem in (("GC", 1.02), ("SI", 1.005)):
        jj = j.copy(); jj["close1"] = jj["close0"] * prem; M[k] = carry_frame(jj)
    global CLASS
    keep = CLASS; CLASS = {"metals": ["GC", "SI"]}
    W = design_A(M); CLASS = keep
    last = W.dropna().iloc[-1]
    e3 = last["GC"] < 0 < last["SI"] and abs(last["GC"] + 0.10 / M["GC"]["sig"].iloc[-1]) < 1e-9 and last["SI"] == 4.0   # SI hits the 4x cap
    ok &= e3; print(f"  [{'PASS' if e3 else 'FAIL'}] cross-sectional: deeper contango is short, shallower long, risk-balanced legs")
    print("ALL PASS" if ok else "FAILURES"); return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--self-test"]: sys.exit(0 if self_test() else 1)
    if not self_test(): sys.exit("self-test failed")
    if a == ["run"]: run()
