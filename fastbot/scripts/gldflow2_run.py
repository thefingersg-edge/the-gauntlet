#!/usr/bin/env python3
"""GLDFLOW2 harness (PREREGISTRATION_GLDFLOW2.md): do monthly gold-ETF flows predict next month's gold?
    python3 gldflow2_run.py --self-test
    python3 gldflow2_run.py run      -> data/gold/run_gldflow2.log (refuses to run twice)
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, math, hashlib
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE)
SPEC = os.path.join(FB, "PREREGISTRATION_GLDFLOW2.md"); SPEC_SHA = "da425cabf9f75f954d2daa926f792ffdce1f29676541d730e168a3b9b29f7584"
XL = os.path.join(FB, "data", "gold", "WGC_ETF_Flows_2026-09.xlsx"); XL_SHA = "54c8ae7aff679b681ea6d90ff01aa8da1b976d30887aeb1e2f670c50d5275ec4"
LOG = os.path.join(FB, "data", "gold", "run_gldflow2.log"); ERAS = ((2006, 2012), (2013, 2019), (2020, 2026))
DISC = "I am not a financial adviser. This is a measurement, not a recommendation."


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def holdings():
    raw = pd.read_excel(XL, sheet_name="Holdings by month", header=None)
    hr = raw.index[raw[0].astype(str).str.strip() == "Date"][0]; tick = raw.iloc[0]; head = raw.iloc[hr]
    gcol = [c for c in raw.columns if str(tick[c]).strip().lower() == "gld us equity" and str(head[c]).strip() == "SPDR Gold Shares"]
    tcol = [c for c in raw.columns if str(head[c]).strip() == "Tonnes"]
    assert len(gcol) == 1 and len(tcol) == 1, (gcol, tcol)
    d = raw.iloc[hr + 1:]; idx = pd.to_datetime(d[0], errors="coerce")
    df = pd.DataFrame({"gld": pd.to_numeric(d[gcol[0]], errors="coerce").to_numpy(), "glob": pd.to_numeric(d[tcol[0]], errors="coerce").to_numpy()}, index=idx)
    df = df[df.index.notna()]; df.index = df.index.to_period("M"); return df


def gold_daily():
    from struct15 import load15
    d = load15("xauusd"); t = pd.DatetimeIndex(d["t"].astype("datetime64[ns]")).tz_localize("UTC").tz_convert("America/New_York")
    s = pd.Series(d["c"], t.tz_localize(None)); s = s[s.index.hour < 16]
    return s.groupby(s.index.normalize()).last()


def second_day_px(px):
    """Price at the 2nd trading day of each month, indexed by that month."""
    g = px.groupby(px.index.to_period("M"))
    return g.apply(lambda s: s.iloc[1] if len(s) >= 2 else np.nan)


def monthly(series, px):
    x = series.pct_change() * 100
    p2 = second_day_px(px); y = pd.Series(np.log(p2.shift(-2).to_numpy() / p2.shift(-1).to_numpy()), index=p2.index)   # month m -> 2nd day m+1 .. 2nd day m+2
    me = px.groupby(px.index.to_period("M")).last(); same = np.log(me).diff()                                          # descriptive: gold over month m
    df = pd.DataFrame({"x": x, "y": y, "same": same}).dropna(subset=["x", "y"])
    return df[df.index >= pd.Period("2006-04", "M")]


def nw(x, y, lags=1):
    X = np.c_[np.ones(len(x)), x]; b = np.linalg.lstsq(X, y, rcond=None)[0]; u = y - X @ b; n = len(y)
    S = (X * u[:, None]).T @ (X * u[:, None]) / n
    for k in range(1, lags + 1):
        G = (X[k:] * u[k:, None]).T @ (X[:-k] * u[:-k, None]) / n; S += (1 - k / (lags + 1)) * (G + G.T)
    Q = np.linalg.inv(X.T @ X / n); V = Q @ S @ Q / n
    return b[1], b[1] / math.sqrt(V[1, 1])


def analyse(df, label):
    b, t = nw(df["x"].to_numpy(), df["y"].to_numpy()); ers = []
    for a, z in ERAS:
        s = df[(df.index.year >= a) & (df.index.year <= z)]; ers.append(nw(s["x"].to_numpy(), s["y"].to_numpy()))
    q = pd.qcut(df["x"], 5, labels=False); gap = (df["y"][q == 4].mean() - df["y"][q == 0].mean()) * 1e4
    c = df["x"].corr(df["same"])
    L = [f"  {label}: n {len(df)} months ({df.index[0]} -> {df.index[-1]}); slope {b * 1e4:+.1f} bp next-month gold per 1% monthly change in tonnes (NW t {t:+.2f})",
         "    eras: " + "  ".join(f"{a}-{z % 100:02d} {e[0] * 1e4:+.1f} (t {e[1]:+.2f})" for (a, z), e in zip(ERAS, ers)),
         f"    top-minus-bottom quintile {gap:+.0f} bp/month;  same-month corr(flow, gold) {c:+.2f} (descriptive)"]
    return L, b, t, ers


def self_test():
    rng = np.random.default_rng(5); days = pd.bdate_range("2006-01-02", "2026-09-30")
    h = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.03, len(pd.period_range("2006-01", "2026-09", freq="M"))))), pd.period_range("2006-01", "2026-09", freq="M"))
    px0 = pd.Series(np.exp(np.cumsum(rng.normal(0, 0.01, len(days)))), days)
    ok = True
    d0 = monthly(h, px0); b0, t0 = nw(d0["x"].to_numpy(), d0["y"].to_numpy()); ok &= abs(t0) < 3
    # planted: add 0.5% x flow% to gold over the window that starts on the 2nd trading day of m+1
    lr = np.log(px0).diff().fillna(0); x = h.pct_change() * 100
    per = days.to_period("M"); first2 = pd.Series(days, days).groupby(per).apply(lambda s: s.iloc[1])
    add = pd.Series(0.0, days)
    for m, v in x.dropna().items():
        if (m + 1) in first2.index and (m + 2) in first2.index:
            a0, a1 = first2[m + 1], first2[m + 2]; seg = add.loc[(add.index > a0) & (add.index <= a1)]
            add.loc[seg.index] += 0.005 * v / len(seg)
    px1 = np.exp((lr + add).cumsum()); d1 = monthly(h, px1); b1, t1 = nw(d1["x"].to_numpy(), d1["y"].to_numpy()); ok &= t1 > 3
    pxe = np.exp(add.cumsum()); de = monthly(h, pxe); be, _ = nw(de["x"].to_numpy(), de["y"].to_numpy()); ok &= abs(be - 0.005) < 1e-9   # no noise: exact
    # timing: y for month m must start strictly after month m ends
    m = d1.index[10]; ok &= first2[m + 1] > pd.Timestamp((m).end_time)
    print(f"  [{'PASS' if ok else 'FAIL'}] null t {t0:+.2f} (|t|<3); planted+noise t {t1:+.1f} (>3); planted, no noise, slope {be:.6f} (exactly 0.005); window starts after month end")
    return ok


def run():
    if sha(SPEC) != SPEC_SHA: sys.exit("spec changed -- refused")
    if sha(XL) != XL_SHA: sys.exit("data file changed -- refused")
    if os.path.exists(LOG): sys.exit("already run")
    H = holdings(); px = gold_daily()
    L = ["GLDFLOW2 -- do monthly gold-ETF flows predict next month's gold? (PREREGISTRATION_GLDFLOW2.md sha da425cab...)", "  " + DISC,
         f"  GLD holdings {H['gld'].first_valid_index()} -> {H['gld'].last_valid_index()};  gold OANDA XAU from {px.index[0].date()}", ""]
    l1, b, t, ers = analyse(monthly(H["gld"].dropna(), px), "PRIMARY (GLD tonnes)"); L += l1
    g1 = b > 0 and t >= 2.0; g2 = all(e[0] > 0 for e in ers)
    l2, *_ = analyse(monthly(H["glob"].dropna(), px), "reported (all gold ETFs, tonnes)"); L += [""] + l2
    L += ["", f"  G1 {'PASS' if g1 else 'FAIL'}  G2 {'PASS' if g2 else 'FAIL'}  -> GLDFLOW2 {'PASS' if g1 and g2 else 'FAIL'}"]
    open(LOG, "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    a = sys.argv[1:]
    ok = self_test()
    if a == ["--self-test"]: sys.exit(0 if ok else 1)
    if not ok: sys.exit("self-test failed")
    if a == ["run"]: run()
