"""
j1_xsection.py — cross-sectional ranking across markets.
Pre-registered in PREREGISTRATION_XSECTION.md.

Every test in Parts A-I asked "is this market above its own average?".
This one asks "is it above the OTHER markets?" — a different statistical
object, dollar-neutral, with the market factor differenced out.
"""
from __future__ import annotations
import os, glob
import numpy as np
import pandas as pd
import core

RNG, NBOOT = np.random.default_rng(20260903), 2000
END    = "2026-08-07"     # last date all 21 price series are live (GAUNTLET 1.6)
MIN_N  = 12               # min live markets for a date to be ranked
VOL_WIN = 63

BLOC = {"xauusd":"metals","xagusd":"metals","xptusd":"metals","xcuusd":"metals",
        "eurusd":"fx","gbpusd":"fx","audusd":"fx","usdcad":"fx","usdjpy":"fx",
        "eurgbp":"fx","eurjpy":"fx",
        "bcousd":"energy","natgasusd":"energy",
        "cornusd":"ags","wheatusd":"ags","sugarusd":"ags",
        "spx500usd":"index","nas100usd":"index","de30eur":"index",
        "usb10yusd":"rates","de10ybeur":"rates"}


def markets():
    return sorted(os.path.basename(p).replace("_d1.csv","")
                  for p in glob.glob(os.path.join(core.DATA,"*_d1.csv")))


def load_panel(mkts):
    R, V = {}, {}
    for m in mkts:
        df = core.load(m).loc[:END]
        r = np.log(df["close"]).diff()
        R[m] = r
        V[m] = r.rolling(VOL_WIN).std()
    return pd.DataFrame(R), pd.DataFrame(V)


def mom(M, n, skip):
    """Sum of the n monthly returns ending `skip` months before the signal date."""
    return M.shift(skip).rolling(n).sum()


def signals(R, V, spec=(11, 1)):
    """Month-end signals, vol-normalised. Ranking a gold CFD against a Bund
    CFD on RAW return would be a volatility sort, so every signal is divided
    by trailing realised vol before it is ranked."""
    M  = R.resample("ME").sum(min_count=15)
    Vm = V.resample("ME").last()
    n, skip = spec
    return {"S1_mom":  mom(M, n, skip) / Vm,
            "S2_3m":   mom(M, 3, 0)    / Vm,
            "S3_rev": -mom(M, 1, 0)    / Vm}


def to_daily(sig_m, index):
    """Month-end signal -> held constant through the following month."""
    s = sig_m.shift(1)
    return s.reindex(s.index.union(index)).ffill().reindex(index)


def zweights(S):
    live = S.notna().sum(axis=1) >= MIN_N
    z = S.sub(S.mean(axis=1), axis=0).div(S.std(axis=1).replace(0, np.nan), axis=0)
    z = z.sub(z.mean(axis=1), axis=0)
    return z.div(z.abs().sum(axis=1).replace(0, np.nan), axis=0).where(live)


def qweights(S, q=0.2):
    live = S.notna().sum(axis=1) >= MIN_N
    rk = S.rank(axis=1, pct=True)
    w = pd.DataFrame(0.0, index=S.index, columns=S.columns).where(S.notna())
    w = w.mask(rk >= 1-q, 1.0).mask(rk <= q, -1.0)
    return w.div(w.abs().sum(axis=1).replace(0, np.nan), axis=0).where(live)


def run(R, Sd, wfun=zweights, cost_bps=1.0):
    w = wfun(Sd); eff = w.shift(1)
    turn = eff.diff().abs().sum(axis=1).fillna(0.0)
    return ((eff*R).sum(axis=1, min_count=1) - turn*cost_bps/1e4).dropna(), eff


def n_eff(R, eff):
    x = (eff*R).dropna(how="all")
    x = x.loc[:, x.notna().sum() > 250]
    C = x.corr(); N = len(C)
    rho = (C.values.sum() - N)/(N*(N-1))
    return N/(1 + (N-1)*rho), rho


def boot(r, n=NBOOT, mb=63):
    x = r.dropna().values; N = len(x); out = np.empty(n)
    for i in range(n):
        idx, j = [], 0
        while j < N:
            st = RNG.integers(0, N); L = max(1, RNG.geometric(1/mb))
            idx += [(st+k) % N for k in range(min(L, N-j))]; j += L
        y = x[np.array(idx[:N])]
        out[i] = y.mean()/y.std()*np.sqrt(core.ppy(r)) if y.std() else np.nan
    return out


def main():
    mkts = markets(); R, V = load_panel(mkts)
    print(f"J1 cross-section | {len(mkts)} markets | {R.index[0].date()} -> {R.index[-1].date()}")
    width = R.notna().sum(axis=1)
    print(f"panel reaches full width ({len(mkts)}) on {width[width==len(mkts)].index[0].date()}; "
          f"{(width>=MIN_N).sum()} of {len(width)} days have >= {MIN_N} live\n")

    sig = signals(R, V); results = {}
    for name, sm in sig.items():
        Sd = to_daily(sm, R.index)
        r, eff = run(R, Sd)
        z = zweights(Sd).dropna(how="all")
        assert np.nanmax(np.abs(z.sum(axis=1))) < 1e-9, "weights not dollar-neutral"
        ne, rho = n_eff(R, eff)
        sh = core.sharpe(r); results[name] = sh
        eras = [core.sharpe(r.loc[a:b]) for a, b in core.ERAS.values()]
        rq, _ = run(R, Sd, wfun=qweights)
        rn, _ = run(R, Sd.shift(750)); nb = boot(rn)
        print("="*70)
        print(f"{name}   rank-weighted Sharpe {sh:+.4f}   (pass requires >= +0.29)")
        print("="*70)
        print(f"  ann ret {core.ann_return(r):+.3%}  ann vol {core.ann_vol(r):.3%}  "
              f"turnover {eff.diff().abs().sum(axis=1).mean()*core.ppy(r):.1f}/yr")
        print(f"  eras         {eras[0]:+.3f} {eras[1]:+.3f} {eras[2]:+.3f}"
              f"   {'consistent' if len({np.sign(e) for e in eras})==1 else 'SIGN FLIP'}")
        print(f"  quintile     {core.sharpe(rq):+.4f}"
              f"   {'agrees' if np.sign(core.sharpe(rq))==np.sign(sh) else 'DISAGREES'}")
        print(f"  3bp cost     {core.sharpe(run(R,Sd,cost_bps=3.0)[0]):+.4f}")
        print(f"  null (750)   {core.sharpe(rn):+.4f}   bootstrap p95 {np.nanpercentile(nb,95):+.4f}"
              f"   {'beats null' if sh>np.nanpercentile(nb,95) else 'INSIDE NULL BAND'}")
        print(f"  realised N_eff {ne:.2f} (rho_bar {rho:.3f}) — 21 names, ~{ne:.0f} independent bets")

    print("\n" + "="*70); print("PLATEAU — neighbouring formation windows for S1"); print("="*70)
    for label, spec in [("11-1",(10,1)), ("12-1",(11,1)), ("12-2",(10,2)), ("6-1",(5,1))]:
        s = signals(R, V, spec)["S1_mom"]
        print(f"  {label}: {core.sharpe(run(R, to_daily(s, R.index))[0]):+.4f}")

    print("\n" + "="*70); print("MIRROR — rank on 1/vol alone, return term removed"); print("="*70)
    inv = to_daily(1.0/V.resample("ME").last(), R.index)
    print(f"  Sharpe {core.sharpe(run(R, inv)[0]):+.4f}   (if this reproduces a result, it is a low-vol tilt)")

    print("\n" + "="*70); print("BLOC CONCENTRATION — is the top quintile routinely one bloc?"); print("="*70)
    w = qweights(to_daily(sig["S1_mom"], R.index)).dropna(how="all")
    longs = w > 0; comp = {}
    for m in w.columns:
        b = BLOC.get(m, "?"); comp[b] = comp.get(b, 0) + int(longs[m].sum())
    tot = sum(comp.values())
    for b, c in sorted(comp.items(), key=lambda kv: -kv[1]):
        print(f"  {b:8s} {100*c/tot:5.1f}% of long slots")

    kill = all(v < 0.29 for v in results.values())
    print("\n" + "="*70)
    print(f"J1 VERDICT: {'FAIL — no signal clears +0.29' if kill else 'PASS ('+max(results,key=results.get)+')'}")
    print(f"KILL CONDITION MET: {kill}")
    print("="*70)


if __name__ == "__main__":
    main()
