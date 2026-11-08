#!/usr/bin/env python3
"""FUTMICRO1 harness (PREREGISTRATION_FUTMICRO1.md, sha ae167b33...): can a $50k account hold the trend sleeve with micro/mini futures?
    python3 futmicro1_run.py --self-test
    python3 futmicro1_run.py run    -> data/futport1/run_futmicro1.log  (refuses to run twice)
Built on scripts/futport1_run.py (frozen): load, market (trend weights), sleeve_pnl, scale, stats.
Mechanical readings fixed here BEFORE the run (logged in PROVENANCE):
  * Fractional sleeve = futport1.sleeve_pnl over the 17 roots, then futport1.scale. Scale factor s_t is lagged, as in futport1.
  * Target $ notional for market i held over day t+1 = capital x s_t x w_i,t / n_t, where n_t = markets active (futport1's averaging).
    Contracts k_i,t = round(target / (|c0_i,t| x mult_i)). Absent days carry the last contracts.
  * $ P&L on day t = k_i,t-1 x mult_i x (c0_t - ref_t), with ref = c1_{t-1} on a roll day, else c0_{t-1}.
    Cost = |k_t - k_{t-1}| x (tick + $0.85), plus on roll days |k_{t-1}| x 2 x (tick + $0.85).
  * Margin proxy: 0.08 x sum |k| x |c0| x mult on each day's close. Live = the futport1 portfolio's live dates.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, math, hashlib
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE)
import futport1_run as FP
SPEC = os.path.join(FB, "PREREGISTRATION_FUTMICRO1.md"); SPEC_SHA = "ae167b336fc79f42eb88ac117310038b6c6a379a38f6e8326554d26ac5958ab5"
ROOTS = ["ES", "NQ", "YM", "RTY", "GC", "SI", "HG", "CL", "6E", "6A", "6B", "6J", "6C", "6S", "ZC", "ZS", "ZW"]
MULT = {"ES": 5, "NQ": 2, "YM": 0.5, "RTY": 5, "GC": 10, "SI": 1000, "HG": 2500, "CL": 100, "6E": 12500, "6A": 10000, "6B": 6250,
        "6J": 1250000, "6C": 10000, "6S": 12500, "ZC": 10, "ZS": 10, "ZW": 10}
TICK = {"ES": 1.25, "NQ": 0.50, "YM": 0.50, "RTY": 0.50, "GC": 1.00, "SI": 5.00, "HG": 1.25, "CL": 1.00, "6E": 1.25, "6A": 1.00, "6B": 0.625,
        "6J": 1.25, "6C": 1.00, "6S": 1.25, "ZC": 1.25, "ZS": 1.25, "ZW": 1.25}
COMM = 0.85
DISC = FP.DISC


def pin():
    if hashlib.sha256(open(SPEC, "rb").read()).hexdigest() != SPEC_SHA: sys.exit("spec changed -- refused")


def contracts_pnl(J, MF, W, n, s, cap):
    cal = W.index; pnl = pd.Series(0.0, index=cal); margin = pd.Series(0.0, index=cal); K = {}
    for r in ROOTS:
        j = J[r].reindex(cal); c0 = j["close0"].ffill(); c1 = j["close1"].ffill(); iid = j["instrument_id0"].ffill()
        present = J[r].reindex(cal)["close0"].notna()
        tgt = cap * s * W[r] / n
        k = (tgt / (c0.abs() * MULT[r])).round().where(present).ffill().fillna(0.0)
        roll = (iid != iid.shift(1)) & present & iid.shift(1).notna()
        ref = np.where(roll, c1.shift(1), c0.shift(1))
        dP = (c0 - ref).where(present, 0.0).fillna(0.0)
        kp = k.shift(1).fillna(0.0)
        cost = (k - kp).abs() * (TICK[r] + COMM) + np.where(roll, kp.abs() * 2 * (TICK[r] + COMM), 0.0)
        pnl += kp * MULT[r] * dP - cost
        margin += 0.08 * k.abs() * c0.abs().fillna(0) * MULT[r]; K[r] = k
    return pnl, margin, pd.DataFrame(K)


def run():
    pin(); P = os.path.join(FP.D, "run_futmicro1.log")
    if os.path.exists(P): sys.exit("already run")
    J = {r: FP.load(r) for r in FP.ROOTS}; MF = {r: FP.market(J[r]) for r in FP.ROOTS}
    full_raw, _, _ = FP.sleeve_pnl(MF, "w_tr"); full, _ = FP.scale(full_raw)
    raw, contrib, W = FP.sleeve_pnl({r: MF[r] for r in ROOTS}, "w_tr"); frac, s = FP.scale(raw)
    live = frac.dropna().index.intersection(full.dropna().index)
    n = W.notna().sum(axis=1).replace(0, np.nan)
    L = ["FUTMICRO1 -- the trend sleeve on the 17 micro/mini markets, whole contracts", "  " + DISC, "",
         "  17-market fractional sleeve: " + FP.fmt(FP.stats(frac.reindex(live))),
         "  29-market FUTPORT1 trend sleeve (reference): " + FP.fmt(FP.stats(full.reindex(live))), ""]
    verdict = None
    for cap in (50_000, 25_000, 100_000):
        pnl, margin, K = contracts_pnl(J, MF, W, n, s, cap)
        x = (pnl / cap).reindex(live); S = FP.stats(x); vol = x.std() * math.sqrt(252); corr = x.corr(frac.reindex(live))
        mfrac = (margin.reindex(live) <= 0.5 * cap).mean()
        cum = pnl.reindex(live).cumsum(); dd = float((cum - cum.cummax()).min())
        Kl = K.reindex(live)
        g1 = S["sh"] >= 0.30; g2 = all(e > 0 for e in S["eras"]); g3 = corr >= 0.80 and 0.06 <= vol <= 0.14 and mfrac >= 0.95
        L += [f"  ${cap:,}{' (PRIMARY)' if cap == 50_000 else ''}: " + FP.fmt(S),
              f"     realised vol {vol * 100:.1f}%;  corr with the fractional sleeve {corr:+.2f};  margin <= 50% on {mfrac * 100:.0f}% of days;  worst drawdown ${dd:,.0f}",
              f"     contracts held per day (mean of sum |k|) {Kl.abs().sum(axis=1).mean():.1f};  turnover (contracts/day) {Kl.diff().abs().sum(axis=1).mean():.2f}",
              "     days at 0 contracts: " + " ".join(f"{r}:{(Kl[r] == 0).mean() * 100:.0f}%" for r in ROOTS)]
        if cap == 50_000:
            verdict = (g1, g2, g3)
            L.append(f"     G1 {'PASS' if g1 else 'FAIL'} (Sharpe >= 0.30)  G2 {'PASS' if g2 else 'FAIL'}  G3 {'PASS' if g3 else 'FAIL'} (holdability)  -> FUTMICRO1 {'PASS' if all(verdict) else 'FAIL'}")
        L.append("")
    open(P, "w").write("\n".join(L) + "\n"); print("\n".join(L))


def self_test():
    ok = True
    idx = pd.bdate_range("2020-01-01", periods=5)
    j = pd.DataFrame(dict(instrument_id0=[1, 1, 1, 2, 2], close0=[100.0, 101, 102, 104, 105], instrument_id1=[2, 2, 2, 3, 3], close1=[103.0, 104, 105, 107, 108]), index=idx)
    global ROOTS
    keep = ROOTS; ROOTS = ["ES"]
    W = pd.DataFrame({"ES": [1.0] * 5}, index=idx); n = pd.Series(1.0, index=idx); s = pd.Series(1.0, index=idx)
    pnl, margin, K = contracts_pnl({"ES": j}, {}, W, n, s, 1000.0)
    ROOTS = keep
    # k = round(1000 / (price x 5)) = 2 (1000/505=1.98, /510=1.96, /520=1.92) -> 2 contracts throughout
    exp = [-(2 * (1.25 + 0.85)), 2 * 5 * 1.0, 2 * 5 * 1.0, 2 * 5 * (104 - 105) - 2 * 2 * (1.25 + 0.85), 2 * 5 * 1.0]
    e1 = np.allclose(pnl.to_numpy(), exp) and (K["ES"] == 2).all()
    ok &= e1; print(f"  [{'PASS' if e1 else 'FAIL'}] whole contracts, $ P&L vs yesterday's front (or c.1 on a roll), entry + roll costs ({list(pnl.round(2))})")
    e2 = abs(margin.iloc[0] - 0.08 * 2 * 100 * 5) < 1e-9; ok &= e2; print(f"  [{'PASS' if e2 else 'FAIL'}] margin proxy 8% of gross notional")
    e3 = len(ROOTS) == 17 and set(ROOTS) == set(MULT) == set(TICK); ok &= e3; print(f"  [{'PASS' if e3 else 'FAIL'}] 17 roots with multipliers and tick values")
    print("ALL PASS" if ok else "FAILURES"); return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--self-test"]: sys.exit(0 if self_test() else 1)
    if not self_test(): sys.exit("self-test failed")
    if a == ["run"]: run()
