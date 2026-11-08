"""
m1_asymmetry.py — volatility asymmetry as a directional signal.
Pre-registered in PREREGISTRATION_ASYMMETRY.md.

Volatility is a second moment and direction is a first moment, so a better
sigma forecast cannot produce direction. What can is the THIRD moment. This
tests whether the asymmetry of realised variation predicts returns.

RSJ was measured at rho = +0.842 against the same day's return BEFORE this was
written, so the primary signal is the cross-sectional RESIDUAL of RSJ on the
trailing return — the part that is not simply momentum.
"""
from __future__ import annotations
import os, glob
import numpy as np
import pandas as pd
import core

RNG, NBOOT = np.random.default_rng(20260912), 2000
SRC   = os.path.dirname(core.HERE)
END   = "2026-08-07"
MIN_BARS   = 12        # a trading day needs this many H1 bars to contribute
MIN_N      = 12        # live markets needed for a date to be ranked
EXCLUDE    = {"sugarusd"}          # median 10 bars/day, 18.3% of days >= 12
FORM       = 21                    # formation window, trading days
BAR        = 0.21                  # 3 x the 0.070 floor at N_eff ~9.5
ROLLOVER_TZ, ROLLOVER_HOUR = "America/New_York", 17


def trading_date(t: pd.Series) -> pd.Series:
    """Same 17:00 New York boundary as make_daily.py. If the intraday day
    differed from the daily bar's day the two would be misaligned by exactly
    the hours the R4 defect turned into 296.5 bars a year."""
    ny = t.dt.tz_convert(ROLLOVER_TZ) - pd.Timedelta(hours=ROLLOVER_HOUR)
    td = pd.to_datetime(ny.dt.date) + pd.Timedelta(days=1)
    dow = td.dt.dayofweek
    td = td.where(dow != 5, td - pd.Timedelta(days=1))
    td = td.where(dow != 6, td + pd.Timedelta(days=1))
    return td.dt.tz_localize("UTC")


def rsj_daily(mkt: str) -> pd.DataFrame:
    """Per trading day: RSJ, RV, bar count, realised skewness."""
    df = pd.read_csv(os.path.join(SRC, f"{mkt}_oanda_h1.csv"), usecols=["time", "close"])
    t = pd.to_datetime(df["time"], utc=True)
    r = np.log(df["close"]).diff()
    g = pd.DataFrame({"td": trading_date(t), "r": r}).dropna()
    p, m = g.r.clip(lower=0), g.r.clip(upper=0)
    agg = pd.DataFrame({
        "rvp": (p ** 2).groupby(g.td).sum(),
        "rvm": (m ** 2).groupby(g.td).sum(),
        "r3":  (g.r ** 3).groupby(g.td).sum(),
        "n":   g.r.groupby(g.td).size()})
    agg = agg[agg["n"] >= MIN_BARS]
    agg["rv"] = agg.rvp + agg.rvm
    agg["rsj"] = (agg.rvp - agg.rvm) / agg.rv.replace(0, np.nan)
    agg["rskew"] = np.sqrt(agg.n) * agg.r3 / agg.rv.pow(1.5).replace(0, np.nan)
    return agg[["rsj", "rv", "rskew", "n"]]


def panel():
    mkts = sorted(m for m in (os.path.basename(p).replace("_d1.csv", "")
                              for p in glob.glob(os.path.join(core.DATA, "*_d1.csv")))
                  if m not in EXCLUDE
                  and os.path.exists(os.path.join(SRC, f"{m}_oanda_h1.csv")))
    R, S, V, K, N = {}, {}, {}, {}, {}
    for m in mkts:
        d = core.load(m).loc[:END]
        a = rsj_daily(m).reindex(d.index)
        R[m] = np.log(d["close"]).diff()
        S[m], V[m], K[m], N[m] = a["rsj"], a["rv"], a["rskew"], a["n"]
    f = lambda x: pd.DataFrame(x)
    return mkts, f(R), f(S), f(V), f(K), f(N)


def xs_residual(Y: pd.DataFrame, X: pd.DataFrame) -> pd.DataFrame:
    """Row-wise cross-sectional OLS residual of Y on X (one intercept+slope
    per date, fitted across markets). Vectorised, no leakage across dates."""
    m = Y.notna() & X.notna()
    y, x = Y.where(m), X.where(m)
    n = m.sum(axis=1)
    xm, ym = x.mean(axis=1), y.mean(axis=1)
    cov = ((x.sub(xm, axis=0)) * (y.sub(ym, axis=0))).sum(axis=1)
    var = ((x.sub(xm, axis=0)) ** 2).sum(axis=1)
    b = (cov / var.replace(0, np.nan)).where(n >= 4)
    return y.sub(ym, axis=0) - x.sub(xm, axis=0).mul(b, axis=0)


def monthly_hold(sig: pd.DataFrame) -> pd.DataFrame:
    """Signal observable at each month end, held through the next month."""
    me = sig.resample("ME").last().shift(1)
    return me.reindex(me.index.union(sig.index)).ffill().reindex(sig.index)


def zweights(S: pd.DataFrame) -> pd.DataFrame:
    live = S.notna().sum(axis=1) >= MIN_N
    z = S.sub(S.mean(axis=1), axis=0).div(S.std(axis=1).replace(0, np.nan), axis=0)
    z = z.sub(z.mean(axis=1), axis=0)
    return z.div(z.abs().sum(axis=1).replace(0, np.nan), axis=0).where(live)


def qweights(S: pd.DataFrame, q=0.2) -> pd.DataFrame:
    live = S.notna().sum(axis=1) >= MIN_N
    rk = S.rank(axis=1, pct=True)
    w = pd.DataFrame(0.0, index=S.index, columns=S.columns).where(S.notna())
    w = w.mask(rk >= 1 - q, 1.0).mask(rk <= q, -1.0)
    return w.div(w.abs().sum(axis=1).replace(0, np.nan), axis=0).where(live)


def run(R, sig, wfun=zweights, cost_bps=1.0):
    eff = wfun(sig).shift(1)
    turn = eff.diff().abs().sum(axis=1).fillna(0.0)
    gross = (eff * R).sum(axis=1, min_count=1)
    r = (gross - turn * cost_bps / 1e4).where(gross.notna()).dropna()
    return r, turn


def boot(r, n=NBOOT, mb=63):
    x = r.dropna().values; N = len(x); out = np.empty(n)
    for i in range(n):
        idx, j = [], 0
        while j < N:
            st = RNG.integers(0, N); L = max(1, RNG.geometric(1 / mb))
            idx += [(st + k) % N for k in range(min(L, N - j))]; j += L
        y = x[np.array(idx[:N])]
        out[i] = y.mean() / y.std() * np.sqrt(core.ppy(r)) if y.std() else np.nan
    return out


def line(name, r, extra=""):
    eras = [core.sharpe(r.loc[a:b]) for a, b in core.ERAS.values()]
    ok = len({np.sign(e) for e in eras}) == 1
    print(f"  {name:<34} {core.sharpe(r):+.4f}   eras {eras[0]:+.2f} {eras[1]:+.2f} "
          f"{eras[2]:+.2f} {'consistent' if ok else 'SIGN FLIP':<11}{extra}")
    return core.sharpe(r), ok


def main():
    mkts, R, RSJ, RV, RSK, NB = panel()
    print(f"M1 volatility asymmetry | {len(mkts)} markets (H1) | "
          f"{R.index[0].date()} -> {R.index[-1].date()}")
    print(f"excluded on data quality: {sorted(EXCLUDE)}   min {MIN_BARS} bars/day\n")

    trail = R.rolling(FORM).sum()                      # trailing 21d return
    rsj_f = RSJ.rolling(FORM).mean()                   # formation-window RSJ

    # G3: bar-count artefact, per market
    g3 = {m: RSJ[m].corr(NB[m]) for m in mkts}
    bad3 = {m: v for m, v in g3.items() if abs(v) >= 0.10}
    print(f"G3 bar-count: max |rho(RSJ, bars)| = {max(abs(v) for v in g3.values()):.3f}"
          f"   breaches: {bad3 or 'none'}")

    # pre-registered sign is NEGATIVE, so the traded signal is -RSJ
    resid = xs_residual(rsj_f, trail)
    sig_primary = monthly_hold(-resid)
    sig_raw     = monthly_hold(-rsj_f)
    sig_rev     = monthly_hold(-trail)                 # plain reversal, G1
    sig_rv      = monthly_hold(-RV.rolling(FORM).mean())   # G2 mirror
    sig_skew    = monthly_hold(-RSK.rolling(FORM).mean())  # G4

    print(f"\n{'='*98}\nPRIMARY — residualised RSJ, rank-weighted, dollar-neutral, "
          f"monthly, 1bp   (bar {BAR:+.2f})\n{'='*98}")
    rp, _ = run(R, sig_primary)
    sh, eras_ok = line("residualised RSJ", rp)
    rq, _ = run(R, sig_primary, wfun=qweights)
    print(f"  {'quintile sort (R2)':<34} {core.sharpe(rq):+.4f}   "
          f"{'agrees' if np.sign(core.sharpe(rq)) == np.sign(sh) else 'DISAGREES'}")
    for c in (0.0, 3.0):
        print(f"  {'cost '+str(int(c))+'bp':<34} {core.sharpe(run(R, sig_primary, cost_bps=c)[0]):+.4f}")

    rn, _ = run(R, sig_primary.shift(750))
    nb = boot(rn)
    p95 = np.nanpercentile(nb, 95)
    print(f"  {'destroyed-timing null':<34} {core.sharpe(rn):+.4f}   bootstrap p95 "
          f"{p95:+.4f}   {'beats null' if sh > p95 else 'INSIDE NULL BAND'}")

    print(f"\n{'='*98}\nGATES\n{'='*98}")
    sh_raw, _ = line("raw RSJ (secondary)", run(R, sig_raw)[0])
    sh_rev, _ = line("G1  plain reversal -sign(21d ret)", run(R, sig_rev)[0])
    sh_rv,  _ = line("G2  mirror: rank on RV alone", run(R, sig_rv)[0])
    sh_sk,  _ = line("G4  mirror: realised skewness", run(R, sig_skew)[0])
    print(f"\n  G1 verdict: raw RSJ {sh_raw:+.4f} vs plain reversal {sh_rev:+.4f} -> "
          f"{'raw beats reversal' if sh_raw > sh_rev else 'RAW DOES NOT BEAT REVERSAL'}")
    print(f"  G2 verdict: {'RV mirror reproduces it — this is the low-vol lead' if abs(sh_rv) >= abs(sh) else 'RV mirror does not reproduce it'}")
    print(f"  momentum component = raw {sh_raw:+.4f} minus residual {sh:+.4f} = {sh_raw - sh:+.4f}")

    print(f"\n{'='*98}\nPLATEAU — formation window\n{'='*98}")
    plat = {}
    for lbl, w in (("weekly (5d)", 5), ("monthly (21d)", 21), ("6-month (126d)", 126)):
        s = monthly_hold(-xs_residual(RSJ.rolling(w).mean(), R.rolling(w).sum()))
        plat[lbl] = core.sharpe(run(R, s)[0])
        print(f"  {lbl:<34} {plat[lbl]:+.4f}")

    ok = (sh >= BAR and eras_ok and sh > p95
          and core.sharpe(run(R, sig_primary, cost_bps=3.0)[0]) >= BAR
          and len({np.sign(v) for v in plat.values()}) == 1
          and sh_raw > sh_rev and not bad3 and abs(sh_rv) < abs(sh))
    print(f"\n{'='*98}")
    print(f"M1 VERDICT: {'PASS' if ok else 'FAIL'}")
    print(f"KILL CONDITION MET: {not ok}")
    print(f"{'='*98}")
    rp.to_csv("m1_returns.csv")


if __name__ == "__main__":
    main()
