#!/usr/bin/env python3
"""OILIMP1 (PREREGISTRATION_OILIMP1.md): can a small account hold the oil carry? Routes M (MCL futures), C (OANDA CFD), E (CRUD ETC, reported).
    python3 oilimp1_run.py --self-test
    python3 oilimp1_run.py main     -> data/run_oilimp1.log      (once; EIA 1987 -> 2024-04-05)
    python3 oilimp1_run.py oos      -> data/run_oilimp1_oos.log  (once, after forward_oilcarry.py --seed: Databento check + 2024-26 stub)
Signal, vol target and roll are oilcarry1_rollfix.py's, unchanged.
Timing: weight decided at month end d, traded at the close of the next trading day, earning from the day after (as rollfix).
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, math, hashlib
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE)
import oilgold_run as G
SPEC = os.path.join(FB, "PREREGISTRATION_OILIMP1.md"); SPEC_SHA = "923437deab315a8f7f0eea6b12a8a8955ea7d09d1bdabcefa61af1353d29533f"
ERAS = ((1987, 2004), (2005, 2014), (2015, 2024)); CAPS = (10_000, 25_000, 50_000)
TICK_USD, COMM, MARGIN, ETC_FEE, ETC_SW = 1.00, 1.50, 0.20, 0.0094, 0.0010
DISC = "I am not a financial adviser. This is a measurement, not a recommendation."
DB = os.path.join(FB, "data", "oil", "databento")


def pin():
    if SPEC_SHA and hashlib.sha256(open(SPEC, "rb").read()).hexdigest() != SPEC_SHA: sys.exit("spec changed -- refused")


def eia():
    F = pd.concat({k: G.series(f"oil/wti_f{k}.csv") for k in (1, 2, 3)}, axis=1).dropna()
    F = F[(F.index >= "1986-01-01") & (F.index <= "2024-04-05")]; idx = F.index
    roll = pd.Series(False, index=idx)
    for y in range(idx[0].year, idx[-1].year + 1):
        for m in range(1, 13):
            p = idx.searchsorted(G.cl_last_trade(y, m), side="right") - 1
            if 0 < p < len(idx): roll.iloc[p] = True
    return F[1], F[2], F[3], roll


def build(f1, f2, roll, f3=None):
    """Roll-adjusted price changes and the OILCARRY1 weight path. Returns a daily frame."""
    ref1 = f1.shift(1).where(~roll, f2.shift(1)); dP1 = (f1 - ref1).fillna(0.0); r1 = (dP1 / ref1.abs()).fillna(0.0)
    sig = np.sqrt((r1 ** 2).ewm(com=60).mean() * 252); idx = f1.index
    me = f1.groupby([idx.year, idx.month]).tail(1).index; c12 = f1 / f2 - 1
    wt = pd.Series(np.nan, index=idx)
    for d in me:
        if sig[d] > 0: wt[d] = float(np.clip(np.sign(c12[d]) * 0.10 / sig[d], -3, 3))
    w = wt.ffill().shift(1).fillna(0.0)                  # weight set on the first trading day after month end ...
    held = w.shift(1).fillna(0.0)                         # ... earns from the following day (rollfix timing)
    reb = (w != w.shift(1)) & (w != 0) | ((w == 0) & (w.shift(1).fillna(0) != 0))
    out = pd.DataFrame(dict(f1=f1, dP1=dP1, r1=r1, w=w, held=held, reb=reb, roll=roll))
    if f3 is not None:
        ref2 = f2.shift(1).where(~roll, f3.shift(1)); out["r2"] = ((f2 - ref2) / ref2.abs()).fillna(0.0)
    return out


def route_M(X, cap):
    n = pd.Series(np.nan, index=X.index)
    for d in X.index[X["reb"]]:
        n[d] = float(np.sign(X.at[d, "w"]) * round(abs(X.at[d, "w"]) * cap / (100 * abs(X.at[d, "f1"]))))
    n = n.where(X["reb"]).ffill().fillna(0.0)               # contracts set at the rebalance close
    nh = n.shift(1).fillna(0.0)                              # held over the next day
    pnl = nh * 100 * X["dP1"]
    cost = (n - nh).abs() * (TICK_USD + COMM) + X["roll"] * nh.abs() * 2 * (TICK_USD + COMM)
    ideal = X["held"] * cap / X["f1"].abs().shift(1) * X["dP1"]
    margin = (MARGIN * n.abs() * 100 * X["f1"].abs())[X["reb"]]
    return pnl - cost, ideal.fillna(0.0), n, margin


def route_C(X, cap, spr_bp, fee):
    u = (X["w"] * cap / X["f1"].abs()).where(X["reb"]).ffill().fillna(0.0)
    u = u.where(X["w"] != 0, 0.0); uh = u.shift(1).fillna(0.0)
    pnl = uh * X["dP1"]
    nights = np.where(X.index.weekday == 4, 3, 1)
    cost = (u - uh).abs() * X["f1"].abs() * 0.5 * spr_bp.reindex(X.index).to_numpy() * 1e-4
    adm = uh.abs() * X["f1"].abs().shift(1).fillna(0) * fee * nights / 365
    return pnl - cost - adm


def route_E(X, cap):
    e = X["w"].clip(lower=0, upper=1); eh = e.shift(1).fillna(0.0)
    return cap * (eh * X["r2"] - eh * ETC_FEE / 252 - (e - eh).abs() * ETC_SW)


def oanda_spreads(index):
    z = np.load(os.path.join(FB, "data", "v51", "wticousd_15m.npz"))
    t = pd.DatetimeIndex(z["t"].astype("datetime64[ns]")).tz_localize("UTC").tz_convert("America/New_York")
    s = pd.Series(z["spr"], t.tz_localize(None)); s = s[(s.index.hour >= 10) & (s > 0)]
    first = s.groupby(s.index.normalize()).first()
    med = float(first[(first.index.year >= 2013) & (first.index.year <= 2024)].median())
    return first.reindex(index).fillna(med), med


def stats(pnl, cap, eras=ERAS):
    x = pnl[pnl.index >= "1987-01-01"] if eras is ERAS else pnl
    yrs = (x.index[-1] - x.index[0]).days / 365.25; sh = x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else float("nan")
    cum = x.cumsum(); dd = float((cum - cum.cummax()).min())
    es = [x[(x.index.year >= a) & (x.index.year <= b)].sum() for a, b in eras]
    return dict(sh=sh, shy=sh * math.sqrt(yrs), ann=x.mean() * 252 / cap, dd=dd, eras=es, yrs=yrs)


def fmt(s, cap):
    return (f"Sharpe {s['sh']:+.2f} (x sqrt {s['yrs']:.0f} yrs = {s['shy']:+.2f}), {s['ann'] * 100:+.1f}%/yr on ${cap:,}, worst drawdown ${s['dd']:,.0f}; eras "
            + "  ".join(f"${e:+,.0f}" for e in s["eras"]))


def main_run():
    pin(); out = os.path.join(FB, "data", "run_oilimp1.log")
    if os.path.exists(out): sys.exit("already run")
    f1, f2, f3, roll = eia(); X = build(f1, f2, roll, f3); spr, med = oanda_spreads(X.index)
    L = ["OILIMP1 -- can a small account hold the oil carry? (PREREGISTRATION_OILIMP1.md)", "  " + DISC,
         f"  EIA {X.index[0].date()} -> {X.index[-1].date()}; OANDA spread median (10:00 NY, 2013-24) {med:.1f} bp used where missing", ""]
    T = 2.24; verdict = {}
    # ---- route M
    for cap in CAPS:
        pnl, ideal, n, margin = route_M(X, cap); s = stats(pnl, cap)
        months0 = float((n[X["reb"] | (X["w"] == 0)].groupby([n[X["reb"] | (X["w"] == 0)].index.year, n[X["reb"] | (X["w"] == 0)].index.month]).last() == 0).mean())
        corr = float(np.corrcoef(pnl[pnl.index >= "1987"], ideal[ideal.index >= "1987"])[0, 1])
        L.append(f"  M MCL ${cap:,}: " + fmt(s, cap))
        L.append(f"     months holding 0 contracts {months0 * 100:.0f}%, mean |contracts| {n[n.index >= '1987'].abs().mean():.2f}, max {n.abs().max():.0f}; "
                 f"corr with fractional ideal {corr:.2f}; worst month-end margin {margin.max() / cap * 100:.0f}% of capital")
        if cap == 10_000:
            g = [s["shy"] >= T, all(e > 0 for e in s["eras"]), s["dd"] >= -3000, corr >= 0.80 and margin.max() <= 0.5 * cap]
            verdict["M"] = g; pm = pnl
    L.append(f"     G1 {'PASS' if verdict['M'][0] else 'FAIL'}  G2 {'PASS' if verdict['M'][1] else 'FAIL'}  G3 {'PASS' if verdict['M'][2] else 'FAIL'}  "
             f"G4 {'PASS' if verdict['M'][3] else 'FAIL'}  -> route M {'PASS' if all(verdict['M']) else 'FAIL'}\n")
    # ---- route C
    for fee in (0.025, 0.015, 0.035):
        for cap in (CAPS if fee == 0.025 else (10_000,)):
            pnl = route_C(X, cap, spr, fee); s = stats(pnl, cap)
            L.append(f"  C CFD ${cap:,} fee {fee * 100:.1f}%: " + fmt(s, cap))
            if cap == 10_000 and fee == 0.025: sC = s; pc = pnl
            if cap == 10_000 and fee == 0.035: s35 = s
    gC = [sC["shy"] >= T, all(e > 0 for e in sC["eras"]), sC["dd"] >= -3000, s35["shy"] >= T]; verdict["C"] = gC
    L.append(f"     G1 {'PASS' if gC[0] else 'FAIL'}  G2 {'PASS' if gC[1] else 'FAIL'}  G3 {'PASS' if gC[2] else 'FAIL'}  "
             f"G4 {'PASS' if gC[3] else 'FAIL'} (fee 3.5%)  -> route C {'PASS' if all(gC) else 'FAIL'}\n")
    # ---- route E (reported)
    pe = route_E(X, 10_000); L.append("  E CRUD long/flat $10,000 (reported): " + fmt(stats(pe, 10_000), 10_000))
    # ---- episodes
    for nm, p in (("M", pm), ("C", pc)):
        mo = p.groupby([p.index.year, p.index.month]).sum(); a20 = p["2020-04-15":"2020-04-30"].sum()
        L.append(f"  episodes {nm} $10k: worst month {mo.idxmin()} ${mo.min():,.0f}; worst day {p.idxmin().date()} ${p.min():,.0f}; 15-30 Apr 2020 ${a20:,.0f}")
    L += ["", f"  OILIMP1: route M {'PASS' if all(verdict['M']) else 'FAIL'}, route C {'PASS' if all(verdict['C']) else 'FAIL'} (Sharpe x sqrt(years) >= {T}, Bonferroni over 2)"]
    open(out, "w").write("\n".join(L) + "\n"); print("\n".join(L))


def load_db():
    def rd(n):
        d = pd.read_csv(os.path.join(DB, f"CL_c{n}.csv"), parse_dates=["date"]).set_index("date").sort_index(); return d
    c0, c1 = rd(0), rd(1); j = c0.join(c1, lsuffix="0", rsuffix="1", how="inner")
    roll = j["instrument_id0"] != j["instrument_id0"].shift(1); roll.iloc[0] = False
    return j["close0"], j["close1"], roll


def oos_run():
    pin(); out = os.path.join(FB, "data", "run_oilimp1_oos.log")
    if os.path.exists(out): sys.exit("already run")
    c0, c1, rollD = load_db(); f1, f2, f3, roll = eia()
    XD = build(c0, c1, rollD); XE = build(f1, f2, roll)
    ov = XD.index.intersection(XE.index); ov = ov[(ov >= "2010-07-01") & (ov <= "2024-04-05")]
    corr = float(np.corrcoef(XD.loc[ov, "dP1"], XE.loc[ov, "dP1"])[0, 1])
    me = [d for d in ov if d in set(XE.index[XE.index.to_series().groupby([XE.index.year, XE.index.month]).transform("max") == XE.index])]
    agree = float(np.mean([np.sign(c0[d] / c1[d] - 1) == np.sign(f1[d] / f2[d] - 1) for d in me]))
    L = ["OILIMP1 oos -- Databento CL.c.0/CL.c.1 check and 2024-26 stub (reported only)", "  " + DISC, "",
         f"  overlap 2010-07 -> 2024-04: corr of daily roll-adjusted changes, Databento vs EIA {corr:.3f}; month-end carry sign agrees {agree * 100:.0f}% ({len(me)} months)"]
    spr, _ = oanda_spreads(XD.index); stub = XD.index >= "2024-04-08"
    stub_eras = ((2024, 2026),)
    pm = route_M(XD, 10_000)[0][stub]; pc = route_C(XD, 10_000, spr, 0.025)[stub]
    pm = pm[pm.index <= "2026-09-30"]; pc = pc[pc.index <= "2026-09-30"]
    L.append("  stub M $10k: " + fmt(stats(pm, 10_000, stub_eras), 10_000))
    L.append("  stub C $10k: " + fmt(stats(pc, 10_000, stub_eras), 10_000))
    open(out, "w").write("\n".join(L) + "\n"); print("\n".join(L))


def self_test():
    ok = True
    idx = pd.bdate_range("2020-01-01", periods=120)
    f1 = pd.Series(np.linspace(50, 60, 120), idx); f2 = f1 + 1.0; roll = pd.Series(False, idx)
    X = build(f1, f2, roll)
    e1 = (X["w"] <= 0).all() and (X["w"].iloc[-1] < 0); ok &= e1
    print(f"  [{'PASS' if e1 else 'FAIL'}] contango (F2 > F1) -> short weight")
    pnl, ideal, n, m = route_M(X, 10_000)
    e2 = (n <= 0).all() and pnl[n.shift(1) < 0].sum() < 0; ok &= e2
    print(f"  [{'PASS' if e2 else 'FAIL'}] short contracts lose on a rising front month")
    roll2 = roll.copy(); roll2.iloc[60] = True; f1b = f1.copy(); f1b.iloc[60:] += 1.0
    Xb = build(f1b, f1b + 1.0 - np.where(np.arange(120) >= 60, 1.0, 0.0), roll2)
    e3 = abs(Xb["dP1"].iloc[60] - (f1b.iloc[60] - (f1b + 1.0 - np.where(np.arange(120) >= 60, 1.0, 0.0)).iloc[59])) < 1e-12; ok &= e3
    print(f"  [{'PASS' if e3 else 'FAIL'}] roll day change measured against yesterday's F2")
    sp = pd.Series(10.0, idx); c = route_C(X, 10_000, sp, 0.0); c0 = route_C(X, 10_000, pd.Series(0.0, idx), 0.0)
    e4 = c.sum() < c0.sum(); ok &= e4; print(f"  [{'PASS' if e4 else 'FAIL'}] CFD spread cost charged on changes")
    f1, f2, f3, roll = eia(); X = build(f1, f2, roll); x = X["held"] * X["r1"] - (X["w"] - X["held"]).abs() * 0.0002; x = x[x.index >= "1987-01-01"]
    sh = x.mean() / x.std() * math.sqrt(252); e5 = abs(sh - 0.54) < 0.01; ok &= e5
    print(f"  [{'PASS' if e5 else 'FAIL'}] reproduces the logged roll-fixed OILCARRY1 Sharpe +0.54 (got {sh:+.3f})")
    print("ALL PASS" if ok else "FAILURES"); return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--self-test"]: sys.exit(0 if self_test() else 1)
    if not self_test(): sys.exit("self-test failed")
    {"main": main_run, "oos": oos_run}[a[0]]()
