#!/usr/bin/env python3
"""OILGOLD batch harness (PREREGISTRATION_OILGOLD_BATCH.md): OILCARRY1, EIA1, GOLDRY1. (TSMOM2 runs on tsmom1_run.py; GLDFLOW1 separately.)
python3 oilgold_run.py carry | eia | goldry      -> data/run_<test>.log (refuses to run twice)
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, math, hashlib
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE)
SPEC = os.path.join(FB, "PREREGISTRATION_OILGOLD_BATCH.md"); SPEC_SHA = "182b6e9f88835a9cb10485dcbfdb2946dfc15f1e65664535b5669f0636198f94"
END = pd.Timestamp("2026-09-26")


def pin():
    if hashlib.sha256(open(SPEC, "rb").read()).hexdigest() != SPEC_SHA: sys.exit("spec changed -- refused")


def nw(y, x, lags):
    """OLS y = a + b x with Newey-West SE. Returns b, t."""
    y, x = np.asarray(y, float), np.asarray(x, float); X = np.c_[np.ones_like(x), x]
    XtXi = np.linalg.inv(X.T @ X); b = XtXi @ X.T @ y; u = y - X @ b; S = (X * u[:, None]).T @ (X * u[:, None])
    for k in range(1, lags + 1):
        w = 1 - k / (lags + 1); G = (X[k:] * u[k:, None]).T @ (X[:-k] * u[:-k, None]); S += w * (G + G.T)
    V = XtXi @ S @ XtXi; return b[1], b[1] / math.sqrt(V[1, 1])


def series(fn):
    d = pd.read_csv(os.path.join(FB, "data", fn)); d.columns = ["date", "v"]
    d["date"] = pd.to_datetime(d["date"]); d["v"] = pd.to_numeric(d["v"], errors="coerce"); return d.dropna().set_index("date")["v"].sort_index()


def out(tag, L):
    p = os.path.join(FB, "data", f"run_{tag}.log"); open(p, "w").write("\n".join(L) + "\n"); print("\n".join(L))


def guard(tag):
    if os.path.exists(os.path.join(FB, "data", f"run_{tag}.log")): sys.exit("already run")


# ------------------------------------------------------------------ OILCARRY1
def cl_last_trade(y, m):
    """NYMEX CL: trading ends 3 business days before the 25th of the month before delivery (4 if the 25th is not a business day).
    Contract 1 during month m is the (m+1) delivery until its last trading day in month m. Holidays ignored (approximation)."""
    d25 = pd.Timestamp(year=y, month=m, day=25); bd = pd.offsets.BDay()
    base = d25 if d25.weekday() < 5 else d25 - bd
    return base - 3 * bd


def carry():
    pin(); guard("oilcarry1")
    F = pd.concat({k: series(f"oil/wti_f{k}.csv") for k in (1, 2, 4)}, axis=1).dropna(); F = F[(F.index >= "1986-01-01") & (F.index < END)]
    idx = F.index
    ltd = {cl_last_trade(y, m) for y in range(idx[0].year, idx[-1].year + 1) for m in range(1, 13)}
    roll = pd.Series(False, index=idx)
    for d in ltd:
        p = idx.searchsorted(d, side="right")      # first trading day after the last trading day
        if p < len(idx): roll.iloc[p] = True
    ref = F[1].shift(1).where(~roll, F[2].shift(1))
    r = ((F[1] - ref) / ref.abs()).fillna(0.0)
    # roll identification check: on roll days the new front should sit closer to yesterday's F2 than yesterday's F1
    rd = roll[roll].index[1:]; hit = np.mean([abs(F[1][d] - F[2].shift(1)[d]) < abs(F[1][d] - F[1].shift(1)[d]) for d in rd])
    sig = np.sqrt((r ** 2).ewm(com=60).mean() * 252)
    me = F[1].groupby([idx.year, idx.month]).tail(1).index

    def strat(weight_fn):
        wt = pd.Series(np.nan, index=idx)
        for d in me:
            if sig[d] > 0: wt[d] = float(np.clip(weight_fn(d) * 0.10 / sig[d], -3, 3))
        w = wt.ffill().shift(1).fillna(0.0); held = w.shift(1).fillna(0.0)
        return held * r - (w - held).abs() * 0.0002
    c12 = F[1] / F[2] - 1; c14 = F[1] / F[4] - 1
    sign_net = strat(lambda d: np.sign(c12[d]))
    cont = strat(lambda d: float(np.clip(c12[d] / c12[:d].tail(756).abs().mean(), -2, 2)) if c12[:d].tail(756).abs().mean() > 0 else 0)
    slope4 = strat(lambda d: np.sign(c14[d]))

    def st(x):
        x = x[x.index >= "1987-01-01"]; yrs = (x.index[-1] - x.index[0]).days / 365.25; sh = x.mean() / x.std() * math.sqrt(252)
        eq = (1 + x).cumprod(); dd = float((eq / eq.cummax() - 1).min()); return sh, sh * math.sqrt(yrs), x.mean() * 252, dd, yrs
    sh, t, ann, dd, yrs = st(sign_net); eras = [sign_net[(sign_net.index.year >= a) & (sign_net.index.year <= b)].sum() for a, b in ((1987, 2004), (2005, 2014), (2015, 2026))]
    g1 = t >= 2.0; g2 = all(e > 0 for e in eras)
    L = ["OILCARRY1 -- WTI curve carry (F1/F2) -> long backwardation / short contango, 10% vol target (PREREGISTRATION_OILGOLD_BATCH sha 182b6e9f…)",
         "  I am not a financial adviser. This is a measurement, not a recommendation.", "",
         f"  EIA RCLC1-4 daily {idx[0].date()} -> {idx[-1].date()}; {int(roll.sum())} roll days by the CL calendar; roll check: new front closer to yesterday's F2 on {hit:.0%} of roll days",
         f"  share of months in backwardation (carry > 0): {np.mean([c12[d] > 0 for d in me]):.0%}", "",
         f"  PRIMARY sign(F1/F2-1), net of 2 bp/unit: Sharpe {sh:+.2f}, Sharpe x sqrt(yrs) {t:+.2f} over {yrs:.1f} yrs, {ann * 100:+.1f}%/yr, worst drawdown {dd * 100:.0f}%",
         "  eras (sum of daily net): " + "  ".join(f"{a}-{b} {e * 100:+.0f}%" for (a, b), e in zip(((1987, 2004), (2005, 2014), (2015, 2026)), eras)),
         f"  G1 {'PASS' if g1 else 'FAIL'}   G2 {'PASS' if g2 else 'FAIL'}   -> {'PASS' if g1 and g2 else 'FAIL'}", "", "  reported:"]
    for nm, x in (("carry as continuous weight", cont), ("F1/F4 slope sign", slope4)):
        s = st(x); L.append(f"    {nm:<28} Sharpe {s[0]:+.2f} (x sqrt yrs {s[1]:+.2f}), worst drawdown {s[3] * 100:.0f}%")
    ex = sign_net.drop(sign_net["2020-04-15":"2020-04-30"].index); s = st(ex); L.append(f"    primary excluding 15-30 Apr 2020 (negative prices): Sharpe {s[0]:+.2f} (x sqrt yrs {s[1]:+.2f})")
    out("oilcarry1", L)


# ------------------------------------------------------------------ EIA1
def eia():
    pin(); guard("eia1")
    from struct15 import load15
    from pandas.tseries.holiday import USFederalHolidayCalendar
    st_ = series("oil/crude_stocks_exspr.csv"); ch = st_.diff().dropna()
    wk = ch.index.isocalendar().week.astype(int); yr = ch.index.year
    surpr = {}
    for d, v in ch.items():
        prev = [ch[(yr == y) & (wk == wk[ch.index.get_loc(d)])] for y in range(d.year - 5, d.year)]
        vals = [p.iloc[0] for p in prev if len(p)]
        if len(vals) == 5: surpr[d] = v - np.mean(vals)
    hol = set(USFederalHolidayCalendar().holidays("1990-01-01", "2027-12-31"))
    d15 = load15("wticousd"); m = d15["t"] < np.datetime64("2026-09-26")
    t = pd.DatetimeIndex(d15["t"][m].astype("datetime64[ns]")).tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
    O, C, SPR = d15["o"][m], d15["c"][m], d15["spr"][m]; pos = {ts: i for i, ts in enumerate(t)}
    rows = []
    for ref, s in surpr.items():
        mon = ref + pd.Timedelta(days=3); week = [mon + pd.Timedelta(days=k) for k in range(3)]
        rel = (ref + pd.Timedelta(days=5)).normalize() + pd.Timedelta(hours=10, minutes=30)
        if any(w in hol for w in week): rel = (ref + pd.Timedelta(days=6)).normalize() + pd.Timedelta(hours=11)
        if rel.year < 2006: continue
        ent = rel + pd.Timedelta(minutes=15); ex = rel.normalize() + pd.Timedelta(hours=14, minutes=15)
        if ent not in pos or ex not in pos or rel not in pos: continue
        i, j, k = pos[ent], pos[ex], pos[rel]
        side = -np.sign(s)
        if side == 0: continue
        g = side * (C[j] / O[i] - 1) * 1e4; net = g - SPR[i]
        first15 = (C[k] / O[k] - 1) * 1e4
        rows.append((rel, s, net, first15))
    R = pd.DataFrame(rows, columns=["rel", "s", "net", "first15"])
    n = len(R); mu = R.net.mean(); tt = mu / (R.net.std(ddof=1) / math.sqrt(n))
    eras = [R.net[(R.rel.dt.year >= a) & (R.rel.dt.year <= b)].mean() for a, b in ((2006, 2012), (2013, 2019), (2020, 2026))]
    zs = R.s / R.s.std(); b15, t15 = nw(R.first15, zs, 1)
    g1 = mu > 0 and tt >= 2.0; g2 = all(e > 0 for e in eras)
    L = ["EIA1 -- weekly crude-stock surprise, trade 15 min after release until 14:30 (PREREGISTRATION_OILGOLD_BATCH sha 182b6e9f…)",
         "  I am not a financial adviser. This is a measurement, not a recommendation.", "",
         f"  {n} releases 2006 -> 2026 matched to WTI 15m bars (surprise = weekly change minus the same-week average of the prior 5 years)",
         f"  reported: first 15 minutes (release bar) on surprise (z): {b15:+.2f} bp per 1 sd (NW t {t15:+.2f})  [negative = draws are bullish]",
         f"  PRIMARY net after spread: {mu:+.2f} bp per release (t {tt:+.2f});  eras " + " / ".join(f"{e:+.2f}" for e in eras),
         f"  G1 {'PASS' if g1 else 'FAIL'}   G2 {'PASS' if g2 else 'FAIL'}   -> {'PASS' if g1 and g2 else 'FAIL'}"]
    out("eia1", L)


# ------------------------------------------------------------------ GOLDRY1
def goldry():
    pin(); guard("goldry1")
    from struct15 import load15
    g = load15("xauusd"); t = pd.DatetimeIndex(g["t"].astype("datetime64[ns]")).tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
    s = pd.Series(g["c"], index=t); s = s[(s.index.hour == 15) & (s.index.minute == 45)]; s.index = s.index.normalize(); s = s[~s.index.duplicated()]
    s = s[s.index < END]
    ry = series("gold/DFII10.csv")
    # knowability: a Friday-close decision uses the latest DFII10 dated BEFORE that Friday (H.15 publishes the next business day)
    fr = s[s.index.weekday == 4]
    rows = []
    for d, px in fr.items():
        y_prior = ry[ry.index < d]
        if len(y_prior) == 0: continue
        rows.append((d, math.log(px), y_prior.iloc[-1]))
    W = pd.DataFrame(rows, columns=["d", "lg", "ry"]).set_index("d")
    W["g4"] = W.lg - W.lg.shift(4); W["dy4"] = W.ry - W.ry.shift(4); W["fwd4"] = W.lg.shift(-4) - W.lg
    res = pd.Series(np.nan, index=W.index)
    for i in range(108, len(W)):
        h = W.iloc[i - 104:i].dropna(subset=["g4", "dy4"])
        if len(h) < 80 or pd.isna(W.dy4.iloc[i]) or pd.isna(W.g4.iloc[i]): continue
        X = np.c_[np.ones(len(h)), h.dy4]; b = np.linalg.lstsq(X, h.g4, rcond=None)[0]
        res.iloc[i] = W.g4.iloc[i] - (b[0] + b[1] * W.dy4.iloc[i])
    W["res"] = res; Z = W.dropna(subset=["res", "fwd4"])
    b, tb = nw(Z.fwd4, Z.res, 4)
    eras = [nw(Z.fwd4[(Z.index.year >= a) & (Z.index.year <= c)], Z.res[(Z.index.year >= a) & (Z.index.year <= c)], 4)[0] for a, c in ((2005, 2012), (2013, 2019), (2020, 2026))]
    g1 = b < 0 and tb <= -2.0; g2 = all(e < 0 for e in eras)
    beta_full = np.polyfit(W.dropna(subset=["g4", "dy4"]).dy4, W.dropna(subset=["g4", "dy4"]).g4, 1)[0]
    L = ["GOLDRY1 -- does gold snap back when it drifts away from real yields? (PREREGISTRATION_OILGOLD_BATCH sha 182b6e9f…)",
         "  I am not a financial adviser. This is a measurement, not a recommendation.", "",
         f"  weekly Fridays {Z.index[0].date()} -> {Z.index[-1].date()}, n {len(Z)}; DFII10 lagged one business day (knowability)",
         f"  reported: full-sample 4-week gold return per +1pp 4-week real-yield change: {beta_full * 100:+.1f}%",
         f"  PRIMARY next-4-week gold return on residual: slope {b:+.3f} (NW t {tb:+.2f})  [negative = snap-back];  eras " + " / ".join(f"{e:+.3f}" for e in eras),
         f"  G1 {'PASS' if g1 else 'FAIL'}   G2 {'PASS' if g2 else 'FAIL'}   -> {'PASS' if g1 and g2 else 'FAIL'}"]
    out("goldry1", L)


if __name__ == "__main__":
    {"carry": carry, "eia": eia, "goldry": goldry}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
