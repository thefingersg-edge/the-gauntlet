#!/usr/bin/env python3
"""LIFECYCLE1 harness (PREREGISTRATION_LIFECYCLE1.md, sha 74ca3c9f...): does a "retire broken systems" rule beat random retirement?
    python3 lifecycle1_run.py --self-test
    python3 lifecycle1_run.py run      -> data/lifecycle1/run_lifecycle1.log  (refuses to run twice)
Mechanical readings fixed here BEFORE the run (logged in PROVENANCE):
  * Library (48), regenerated from frozen code:
    - PROBE1 / PROBE1-OIL: the frozen runs' data/probe1/<m>_daily.csv, column net_probe (6);
    - unger_batch.py: MULTI1 S1-S3 raw daily net on SPX/NAS/UK100/XAU/WTI/Brent (18); GOLDTREND A/B/C (3); CONTEXT F1-F6 (6);
    - unger2_run.py: A; B CFD + GC futures; C CFD + CL futures; D k = 0/5/10/20/40 CFD + CL futures (15). Net bp per trade; futures trades with a roll excluded.
  * Daily units are the daily net return (NaN days dropped); no-position days count as 0, as the source series already record them.
    Trade units are ordered by entry time.
  * Split: units dated before the midpoint (first date + (last - first) / 2) form the backtest half; the rest are live.
  * Band: the 5th percentile of 20,000 bootstrap means of N units from the backtest half. One numpy Generator(seed 0), used in library order.
  * Kill: the first live unit j (j >= N-1) whose rolling N-unit live mean < band. Units after j are set to 0.
  * Improvement = -(sum of live units after j) / (sd of backtest units x sqrt(n_live)). It is 0 if never killed.
  * Placebo: q = the share of systems the rule killed. Each draw picks round(q x 48) systems at random and kills each at a uniform random live unit.
    The placebo improvement per system is the average over 1,000 draws (Generator seed 0, after the bands).
  * G3: among systems whose live sum > 0, the rule's kill share vs q (the placebo's expected share).
  * t statistics are cross-sectional over the 48 systems: mean / (sd / sqrt 48).
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, math, hashlib, contextlib, io
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE)
SPEC = os.path.join(FB, "PREREGISTRATION_LIFECYCLE1.md"); SPEC_SHA = "74ca3c9f74decdfeb17ca29a48f869820498202db0fb2212809d367f65d01394"
OUT = os.path.join(FB, "data", "lifecycle1")
DISC = "I am not a financial adviser. This is a measurement, not a recommendation."


def pin():
    if hashlib.sha256(open(SPEC, "rb").read()).hexdigest() != SPEC_SHA: sys.exit("spec changed -- refused")


def library():
    import unger_batch as UB, unger2_run as U2
    L = []
    for m in ("spx500usd", "nas100usd", "uk100gbp", "xauusd", "wticousd", "bcousd"):
        d = pd.read_csv(os.path.join(FB, "data", "probe1", f"{m}_daily.csv"), parse_dates=["day"])
        L.append((f"PROBE1 {m}", "day", d["day"].to_numpy(), d["net_probe"].to_numpy(float)))
    SY = UB.systems(UB.CORE + UB.OIL)
    for s in UB.CORE + UB.OIL:
        for k in ("S1 trend", "S2 meanrev", "S3 breakout"):
            M, R = SY[(s, k)]["M"], SY[(s, k)]["R"]; L.append((f"MULTI1 {s} {k}", "day", pd.to_datetime(M["date"]).to_numpy(), R["net"]))
    M = UB.market("xauusd"); dates = pd.to_datetime(M["date"]).to_numpy()
    for nm, R in (("A weekly probe", UB.probe_lv(M, *UB.prior_week_levels(M))), ("B close-confirmed", UB.daily_engine(M, UB.rule_close_confirm(M))),
                  ("C 20-day channel", UB.daily_engine(M, UB.rule_channel(M)))):
        L.append((f"GOLDTREND {nm}", "day", dates, R["net"]))
    with contextlib.redirect_stdout(io.StringIO()):
        HI, LO = UB.prior_day_levels(M); nd = len(M["C"]); A = UB.atr(M, 20); med = pd.Series(A).rolling(250).median().to_numpy(); rng = M["H"] - M["L"]
        A1, m1 = np.r_[np.nan, A[:-1]], np.r_[np.nan, med[:-1]]
        nr4 = np.zeros(nd, bool); nr4[3:] = [rng[d] <= rng[d - 3:d].min() for d in range(3, nd)]
        ins = np.zeros(nd, bool); ins[1:] = (M["H"][1:] <= M["H"][:-1]) & (M["L"][1:] >= M["L"][:-1])
        F = {"F1": np.isfinite(m1) & (A1 > m1), "F2": np.isfinite(m1) & (A1 < m1), "F3": np.r_[False, nr4[:-1]], "F4": np.r_[False, ins[:-1]],
             "F5": np.r_[False, (M["O"][1:] >= M["L"][:-1]) & (M["O"][1:] <= M["H"][:-1])]}
        for k, act in F.items(): L.append((f"CONTEXT {k}", "day", dates, UB.probe_lv(M, HI, LO, active=act)["net"]))
        sma = pd.Series(M["C"]).rolling(100).mean().to_numpy(); al = np.r_[0, np.where(M["C"] > sma, 1, -1)[:-1]]; ok6 = np.r_[False, np.isfinite(sma[:-1])]
        L.append(("CONTEXT F6", "day", dates, UB.probe_lv(M, HI, LO, active=ok6, allow=al)["net"]))
    R = U2.usd_rates()
    def tr(nm, T):
        T = T[~T["roll"]].sort_values("t0"); L.append((nm, "trade", pd.to_datetime(T["t0"]).to_numpy(), T["net_bp"].to_numpy(float)))
    tr("UNGER2 A DAX", U2.sys_A(U2.bars_dax(), R))
    Bx, Bg, Bw, Bc = U2.bars_cfd("xauusd"), U2.bars_fut("GC"), U2.bars_cfd("wticousd"), U2.bars_fut("CL")
    tr("UNGER2 B gold CFD", U2.sys_B(Bx, R)); tr("UNGER2 B gold GC", U2.sys_B(Bg, R))
    tr("UNGER2 C crude CFD", U2.sys_C(Bw, R)); tr("UNGER2 C crude CL", U2.sys_C(Bc, R))
    for k in (0, 5, 10, 20, 40):
        tr(f"UNGER2 D k{k} CFD", U2.sys_D(Bw, R, k)); tr(f"UNGER2 D k{k} CL", U2.sys_D(Bc, R, k))
    assert len(L) == 48, len(L)
    out = []
    for nm, unit, d, x in L:
        d = np.asarray(d, "datetime64[ns]"); x = np.asarray(x, float); ok = np.isfinite(x); out.append((nm, unit, d[ok], x[ok]))
    return out


def split(d, x):
    mid = d[0] + (d[-1] - d[0]) / 2; b = d < mid; return x[b], x[~b]


def band(bt, N, rng, B=20000):
    idx = rng.integers(0, len(bt), size=(B, N)); return float(np.percentile(bt[idx].mean(1), 5))


def kill_index(live, N, thr):
    if len(live) < N: return None
    r = np.convolve(live, np.ones(N) / N, mode="valid")              # r[k] = mean(live[k:k+N]) -> unit k+N-1
    hit = np.flatnonzero(r < thr)
    return None if not len(hit) else int(hit[0] + N - 1)


def dd_kill(bt, live):
    cb = np.cumsum(bt); worst = float((cb - np.maximum.accumulate(np.r_[0, cb])[1:]).min())
    cl = np.cumsum(live); dd = cl - np.maximum.accumulate(np.r_[0, cl])[1:]; hit = np.flatnonzero(dd < worst)
    return None if not len(hit) else int(hit[0])


def improvement(bt, live, j):
    if j is None: return 0.0
    sd = bt.std(); return float(-live[j + 1:].sum() / (sd * math.sqrt(len(live)))) if sd > 0 else 0.0


def evaluate(lib, Nmap, rng, draws=1000, rule="roll"):
    rows = []
    for nm, unit, d, x in lib:
        bt, lv = split(d, x); N = Nmap[unit]
        if rule == "roll": j = kill_index(lv, N, band(bt, N, rng))
        else: j = dd_kill(bt, lv)
        rows.append(dict(name=nm, unit=unit, n_bt=len(bt), n_live=len(lv), live_sum=float(lv.sum()), killed=j is not None, j=j,
                         imp=improvement(bt, lv, j), after_mean=float(lv[j + 1:].mean()) if j is not None and j + 1 < len(lv) else np.nan, bt=bt, lv=lv))
    S = pd.DataFrame(rows); q = S["killed"].mean(); k = int(round(q * len(S)))
    pl = np.zeros(len(S))
    for _ in range(draws):
        pick = rng.choice(len(S), size=k, replace=False)
        for i in pick:
            r = S.iloc[i]; j = int(rng.integers(0, len(r["lv"]))); pl[i] += improvement(r["bt"], r["lv"], j)
    S["placebo"] = pl / draws
    return S, q


def tstat(v):
    v = np.asarray(v, float); return v.mean() / (v.std(ddof=1) / math.sqrt(len(v))) if v.std(ddof=1) > 0 else float("nan")


def run():
    pin(); os.makedirs(OUT, exist_ok=True); P = os.path.join(OUT, "run_lifecycle1.log")
    if os.path.exists(P): sys.exit("already run")
    with contextlib.redirect_stdout(io.StringIO()): lib = library()
    rng = np.random.default_rng(0)
    S, q = evaluate(lib, {"trade": 30, "day": 60}, rng)
    m1, t1 = S["imp"].mean(), tstat(S["imp"]); diff = S["imp"] - S["placebo"]; m2, t2 = diff.mean(), tstat(diff)
    pos = S["live_sum"] > 0; share_pos = S.loc[pos, "killed"].mean() if pos.any() else float("nan")
    g1 = m1 > 0 and t1 >= 2.0; g2 = m2 > 0 and t2 >= 2.0; g3 = pos.any() and share_pos < q
    L = ["LIFECYCLE1 -- does 'retire broken systems' beat random retirement? (48 systems, backtest half -> live half)", "  " + DISC, "",
         f"  kill rule: rolling 30-trade / 60-day live mean < 5th pct of the backtest bootstrap.  Killed {int(S['killed'].sum())}/48 (q = {q:.2f}); "
         f"median time to kill {np.nanmedian(S['j'].astype(float)):.0f} units",
         f"  live halves positive: {int(pos.sum())}/48 systems",
         f"  G1 mean standardised improvement {m1:+.3f} (t {t1:+.2f})  -> {'PASS' if g1 else 'FAIL'}",
         f"  G2 rule minus random retirement {m2:+.3f} (t {t2:+.2f})  [rule {m1:+.3f} vs placebo {S['placebo'].mean():+.3f}]  -> {'PASS' if g2 else 'FAIL'}",
         f"  G3 kill share among live-positive systems {share_pos:.2f} vs q {q:.2f}  -> {'PASS' if g3 else 'FAIL'}",
         f"  LIFECYCLE1: {'PASS' if g1 and g2 and g3 else 'FAIL'}", "", "  per system (live sum in units; killed at unit j of n_live; standardised improvement; placebo):"]
    for _, r in S.iterrows():
        L.append(f"    {r['name']:28s} {r['unit']:5s} live sum {r['live_sum']:+10.4g}  {'KILLED at ' + str(r['j']) + '/' + str(r['n_live']) if r['killed'] else 'kept':>22s}"
                 f"  imp {r['imp']:+.3f}  placebo {r['placebo']:+.3f}" + (f"  after-kill mean {r['after_mean']:+.4g}" if r['killed'] else ""))
    rec = S[S["killed"] & (S["after_mean"] > 0)]
    L.append(f"\n  reported: killed systems that were positive after the kill (false alarms): {len(rec)} -- " + ", ".join(rec["name"]))
    for Nm, lab in (({"trade": 50, "day": 120}, "N = 50 trades / 120 days"),):
        V, qv = evaluate(lib, Nm, np.random.default_rng(1)); dv = V["imp"] - V["placebo"]
        L.append(f"  reported {lab}: killed {int(V['killed'].sum())}/48; improvement {V['imp'].mean():+.3f} (t {tstat(V['imp']):+.2f}); vs placebo {dv.mean():+.3f} (t {tstat(dv):+.2f})")
    V, qv = evaluate(lib, {"trade": 30, "day": 60}, np.random.default_rng(2), rule="dd"); dv = V["imp"] - V["placebo"]
    L.append(f"  reported drawdown rule (live DD > backtest worst DD): killed {int(V['killed'].sum())}/48; improvement {V['imp'].mean():+.3f} (t {tstat(V['imp']):+.2f}); "
             f"vs placebo {dv.mean():+.3f} (t {tstat(dv):+.2f})")
    S.drop(columns=["bt", "lv"]).to_csv(os.path.join(OUT, "lifecycle1_systems.csv"), index=False)
    open(P, "w").write("\n".join(L) + "\n"); print("\n".join(L))


def self_test():
    ok = True
    live = np.r_[np.full(40, 1.0), np.full(60, -1.0)]
    j = kill_index(live, 30, 0.0); e1 = j is not None and np.mean(live[j - 29:j + 1]) < 0 and np.mean(live[j - 30:j]) >= 0
    ok &= e1; print(f"  [{'PASS' if e1 else 'FAIL'}] kill fires at the first unit where the rolling 30-mean drops below the band (j = {j})")
    bt = np.r_[np.ones(50), -np.ones(50)]; imp = improvement(bt, live, j)
    e2 = abs(imp - (-live[j + 1:].sum() / (bt.std() * 10))) < 1e-12 and imp > 0
    ok &= e2; print(f"  [{'PASS' if e2 else 'FAIL'}] improvement = minus the post-kill sum, standardised ({imp:+.3f})")
    e3 = kill_index(np.ones(100), 30, 0.0) is None; ok &= e3; print(f"  [{'PASS' if e3 else 'FAIL'}] no kill when always above the band")
    rng = np.random.default_rng(0); b = band(np.random.default_rng(5).normal(0, 1, 5000), 30, rng)
    e4 = abs(b - (-1.645 / math.sqrt(30))) < 0.05; ok &= e4; print(f"  [{'PASS' if e4 else 'FAIL'}] bootstrap band ~ -1.645/sqrt(30) on N(0,1) ({b:+.3f})")
    print("ALL PASS" if ok else "FAILURES"); return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--self-test"]: sys.exit(0 if self_test() else 1)
    if not self_test(): sys.exit("self-test failed")
    if a == ["run"]: run()
