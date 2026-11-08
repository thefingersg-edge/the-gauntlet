#!/usr/bin/env python3
"""VIXIMP1 (PREREGISTRATION_VIXIMP1.md): can a $10k account hold short VXM with a crash rule?
python3 viximp1_run.py   -> data/viximp1/run_viximp1.log
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, math, hashlib
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE)
import vix_curve_budget as VC
import vix_daily_risk as VD
PIN = {os.path.join(FB, "PREREGISTRATION_VIXIMP1.md"): "649658dbe0d0f41b1274998de025ccc65008968fcc8ea4f2fb71a36d5de94a49"}
D = os.path.join(FB, "data"); OUT = os.path.join(D, "viximp1")
MULT, TICK, COMM = 100.0, 0.05, 1.50
ROLL_COST = 2 * TICK + 2 * COMM / MULT          # vol pts per contract per roll
SWITCH_COST = TICK + COMM / MULT
MARGIN = 629.0; BUDGET = 0.30; BENCH = 0.051; TG = 2.24
ERAS = ((2004, 2012), (2013, 2019), (2020, 2026))


def pin():
    for f, h in PIN.items():
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")


def nw_t(x, lags=5):
    x = np.asarray(x, float); n = len(x); m = x.mean(); u = x - m; v = (u @ u) / n
    for k in range(1, lags + 1): v += 2 * (1 - k / (lags + 1)) * (u[k:] @ u[:-k]) / n
    return m / math.sqrt(v / n)


def run_rule(pnl, is_roll, on):
    """on: bool Series (position held over day t). Returns net vol-pt P&L per contract."""
    on = on.reindex(pnl.index).fillna(False).astype(bool)
    net = pnl.where(on, 0.0).copy()
    net[on & is_roll.reindex(pnl.index).fillna(False)] -= ROLL_COST
    sw = on.astype(int).diff().abs().fillna(on.astype(int).iloc[0]).astype(bool)
    net[sw] -= SWITCH_COST
    return net, on


def stats(net, on, label, L, gated):
    yrs = (net.index[-1] - net.index[0]).days / 365.25
    eq = net.cumsum(); dd = eq - eq.cummax().clip(lower=0); wdd = float(dd.min())
    t = nw_t(net.to_numpy()); era = [net[(net.index.year >= a) & (net.index.year <= b)].sum() for a, b in ERAS]
    n_c = int(math.floor(BUDGET * 10000 / (abs(wdd) * MULT))) if wdd < 0 else 99
    ann = net.sum() * MULT / yrs
    ret10 = n_c * ann / 10000 if n_c >= 1 else float("nan")
    g1 = net.mean() > 0 and t >= TG; g2 = all(e > 0 for e in era); g3 = abs(wdd) * MULT <= 3000; g4 = n_c >= 1 and ret10 > BENCH
    worst1 = net.min(); worst5 = net.rolling(5).sum().min()
    def ep(a, b): s = net[(net.index >= a) & (net.index <= b)]; return s.sum()
    L.append(f"  {label}")
    L.append(f"    net {net.sum():+.1f} vol pts over {yrs:.1f} yrs = ${ann:+,.0f}/yr per VXM;  t {t:+.2f};  eras " + " / ".join(f"{e:+.1f}" for e in era)
             + f";  in market {on.mean():.0%}")
    L.append(f"    worst drawdown {wdd:.2f} pts = ${abs(wdd) * MULT:,.0f} per VXM;  worst day {worst1:+.2f};  worst 5 days {worst5:+.2f}")
    L.append(f"    episodes: 2008 (Sep-Dec) {ep('2008-09-01', '2008-12-31'):+.1f};  Feb-2018 {ep('2018-01-26', '2018-02-28'):+.1f};  Mar-2020 {ep('2020-02-20', '2020-04-15'):+.1f}")
    for acct in (10000, 25000, 50000):
        n = int(math.floor(BUDGET * acct / (abs(wdd) * MULT))) if wdd < 0 else 0
        if n < 1: L.append(f"    ${acct:,}: 0 contracts fit the 30% budget (1 contract would risk {abs(wdd) * MULT / acct:.0%})"); continue
        eqd = acct + n * eq * MULT; breach = int((eqd < n * MARGIN).sum())
        L.append(f"    ${acct:,}: {n} VXM -> {n * ann / acct:+.1%}/yr, worst drawdown {n * abs(wdd) * MULT / acct:.0%} of account, margin breaches {breach} days")
    if gated:
        L.append(f"    G1 t>={TG} {'PASS' if g1 else 'FAIL'}  G2 eras {'PASS' if g2 else 'FAIL'}  G3 dd<=$3,000 {'PASS' if g3 else 'FAIL'}  "
                 f"G4 $10k return {ret10 if n_c >= 1 else float('nan'):+.1%} > 5.1% {'PASS' if g4 else 'FAIL'}  -> {'PASS' if all((g1, g2, g3, g4)) else 'FAIL'}")
    return all((g1, g2, g3, g4))


def main():
    pin(); os.makedirs(OUT, exist_ok=True)
    vx1 = VC.load_csv(os.path.join(D, "CBOE_DLY_VX1!, 1D_1f2b8.csv"), "VX1!")
    vx2 = VC.load_csv(os.path.join(D, "CBOE_DLY_VX2!, 1D_7782c.csv"), "VX2!")
    idx = vx1.index.intersection(vx2.index); vx1, vx2 = vx1.loc[idx], vx2.loc[idx]
    exps = VD.vx_expiries(idx[0], idx[-1]); rows, best, second, clean = VD.scan_offsets(vx1, vx2, exps)
    if not clean: sys.exit("roll offset not identified -- refused (as vix_daily_risk 1.2)")
    rolls = VD.roll_days(idx, exps, best["offset"]); pnl, is_roll = VD.daily_pnl(vx1, vx2, rolls)
    v = pd.read_csv(os.path.join(D, "VIXCLS.csv")); v.columns = ["date", "vix"]
    v["date"] = pd.to_datetime(v["date"]); v["vix"] = pd.to_numeric(v["vix"], errors="coerce")
    vix = v.set_index("date")["vix"].ffill().reindex(idx, method="ffill")
    L = ["VIXIMP1 -- short Mini VIX (VXM) with a crash rule, sized for a small account (PREREGISTRATION_VIXIMP1.md sha 649658db…)",
         "  I am not a financial adviser. This is a measurement, not a recommendation.",
         f"  roll identified at offset {best['offset']} (t {best['t']:.1f}); {len(rolls)} rolls; {idx[0].date()} -> {idx[-1].date()}", ""]
    on0 = pd.Series(True, index=pnl.index)
    on1 = (vx2 > vx1).shift(1).reindex(pnl.index).fillna(False)
    on2 = (vix <= 25).shift(1).reindex(pnl.index).fillna(False)
    res = {}
    for name, on, gated in (("R0 always short (baseline)", on0, False), ("R1 contango filter (VX2 > VX1 at prior close)", on1, True),
                            ("R2 spot-VIX stop (flat when VIX > 25 at prior close)", on2, True)):
        net, o = run_rule(pnl, is_roll, on); res[name] = stats(net, o, name, L, gated); L.append("")
    # ETP-like route, context only: -1x daily rebalanced on the front month, expense 1.47%/yr
    prev = vx1.shift(1).reindex(pnl.index); r = (pnl / prev).dropna() - 0.0147 / 252
    eq = (1 + r).cumprod(); yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    L.append(f"  ETP route (context only, not available to UK retail): -1x daily short front month, 1.47% fee: CAGR {eq.iloc[-1] ** (1 / yrs) - 1:+.1%}, "
             f"max drawdown {float((eq / eq.cummax() - 1).min()):.0%}, worst day {float(r.min()):+.0%} ({r.idxmin().date()})")
    L.append(f"\n  VERDICT: R1 {'PASS' if res[list(res)[1]] else 'FAIL'}   R2 {'PASS' if res[list(res)[2]] else 'FAIL'}")
    open(os.path.join(OUT, "run_viximp1.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
