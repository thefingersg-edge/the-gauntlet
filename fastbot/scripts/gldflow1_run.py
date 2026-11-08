#!/usr/bin/env python3
"""GLDFLOW1 (PREREGISTRATION_OILGOLD_BATCH.md, sha 182b6e9f...): do gold-ETF flows predict gold?
Frozen BEFORE any GLD holdings history is on disk. The 2026-10-10 download (data/gold/GLD_US_archive_EN.csv) turned out to be a
one-day PDF bar list, not the history.

INPUT: data/gold/GLD_history.(csv|xlsx), the SPDR "historical archive" exported by Dave from spdrgoldshares.com.
  - The loader finds a date column (a header containing 'date') and a tonnes column (a header containing 'tonnes').
  - Rows whose tonnes are not numeric (e.g. 'HOLIDAY') are dropped.
GOLD: OANDA XAUUSD 15m mid (struct15 cache). Friday price = the close of the last bar starting before 16:00 New York on that Friday.

TEST (spec):
  - x_w = % change in GLD tonnes from the last holdings day of week w-1 to the last of week w (weeks end Friday).
  - y_w = gold log return from Friday(w) 16:00 to Friday(w+1) 16:00.
  - OLS y on x; Newey-West (1 lag) t.
  - G1: slope > 0 and t >= 2.0.  G2: slope > 0 in 2005-12, 2013-19, 2020-26.
REPORTED (fixed now): the same regression using holdings up to THURSDAY only (strictly known before Friday 16:00, since SPDR
  publishes the day's tonnes after the US close), and the top-vs-bottom quintile gap.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, glob, math
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE)
from struct15 import load15
OUT = os.path.join(FB, "data", "gold"); ERAS = ((2005, 2012), (2013, 2019), (2020, 2026)); END = pd.Timestamp("2026-09-26")


def load_holdings(path=None):
    path = path or ([p for p in glob.glob(os.path.join(OUT, "GLD_history.*")) if p.endswith((".csv", ".xlsx", ".xls"))] or [None])[0]
    if path is None: sys.exit("data/gold/GLD_history.csv or .xlsx not found -- download the SPDR historical archive first")
    if path.endswith(".csv"): df = pd.read_csv(path)
    else: df = pd.read_excel(path)
    dc = [c for c in df.columns if "date" in str(c).lower()][0]; tc = [c for c in df.columns if "tonnes" in str(c).lower()][0]
    s = pd.DataFrame({"date": pd.to_datetime(df[dc], errors="coerce", dayfirst=True), "t": pd.to_numeric(df[tc].astype(str).str.replace(",", ""), errors="coerce")})
    s = s.dropna().sort_values("date").drop_duplicates("date", keep="last"); s = s[s["t"] > 0]
    return s.set_index("date")["t"], path


def gold_friday():
    d = load15("xauusd"); t = pd.DatetimeIndex(d["t"].astype("datetime64[ns]")).tz_localize("UTC").tz_convert("America/New_York")
    s = pd.Series(d["c"], t.tz_localize(None)); s = s[s.index.hour < 16]          # bars starting before 16:00 NY
    fri = s[s.index.weekday == 4]; px = fri.groupby(fri.index.normalize()).last()
    return px[px.index < END]


def nw(x, y, lags=1):
    X = np.c_[np.ones(len(x)), x]; b = np.linalg.lstsq(X, y, rcond=None)[0]; u = y - X @ b; n = len(y)
    S = (X * u[:, None]).T @ (X * u[:, None]) / n
    for k in range(1, lags + 1):
        G = (X[k:] * u[k:, None]).T @ (X[:-k] * u[:-k, None]) / n; S += (1 - k / (lags + 1)) * (G + G.T)
    Q = np.linalg.inv(X.T @ X / n); V = Q @ S @ Q / n
    return b[1], b[1] / math.sqrt(V[1, 1])


def weekly(h, px, thursday=False):
    hh = h[h.index.weekday <= (3 if thursday else 4)]
    wk = hh.groupby(hh.index.to_period("W-FRI")).last()
    x = wk.pct_change() * 100
    y = np.log(px).diff().shift(-1); y.index = y.index.to_period("W-FRI")
    df = pd.DataFrame({"x": x, "y": y}).dropna(); return df[df.index.year >= 2005]


def run(df, label):
    L = []; b, t = nw(df["x"].to_numpy(), df["y"].to_numpy())
    ers = []
    for a, z in ERAS:
        s = df[(df.index.year >= a) & (df.index.year <= z)]; ers.append(nw(s["x"].to_numpy(), s["y"].to_numpy()) if len(s) > 30 else (np.nan, np.nan))
    q = pd.qcut(df["x"], 5, labels=False); gap = (df["y"][q == 4].mean() - df["y"][q == 0].mean()) * 1e4
    L.append(f"  {label}: n {len(df)} weeks; slope {b * 1e4:+.2f} bp of next-week gold per 1% weekly change in tonnes (NW t {t:+.2f})")
    L.append("    eras: " + "  ".join(f"{a}-{z % 100:02d} {e[0] * 1e4:+.2f} (t {e[1]:+.2f})" for (a, z), e in zip(ERAS, ers))
             + f";  top-minus-bottom quintile {gap:+.1f} bp/week")
    return L, b, t, ers


def self_test():
    rng = np.random.default_rng(3); idx = pd.bdate_range("2005-01-03", "2012-12-28")
    h = pd.Series(100 + np.cumsum(rng.normal(0, 0.5, len(idx))), idx)
    px = pd.Series(np.exp(np.cumsum(rng.normal(0, 0.01, len(idx)))), idx); px = px[px.index.weekday == 4]
    wkx = h.groupby(h.index.to_period("W-FRI")).last().pct_change()
    planted = px.copy(); per = planted.index.to_period("W-FRI")
    lr = np.log(px).diff().shift(-1).to_numpy() + 2.0 * np.nan_to_num(wkx.reindex(per).to_numpy())
    planted = pd.Series(np.exp(np.r_[0, np.nancumsum(lr[:-1])]), px.index)
    df = weekly(h, planted); b, t = nw(df["x"].to_numpy(), df["y"].to_numpy())
    df0 = weekly(h, px); b0, t0 = nw(df0["x"].to_numpy(), df0["y"].to_numpy())
    ok = t > 5 and abs(t0) < 3; print(f"  self-test: planted flow effect t {t:+.1f} (>5), no effect t {t0:+.2f} (|t|<3) -> {'OK' if ok else 'BROKEN'}")
    return ok


def main():
    if not self_test(): sys.exit("self-test broken")
    if sys.argv[1:] == ["--self-test"]: return
    h, path = load_holdings(); px = gold_friday()
    L = ["GLDFLOW1 -- do gold-ETF flows predict gold? (PREREGISTRATION_OILGOLD_BATCH.md sha 182b6e9f...)",
         "  I am not a financial adviser. This is a measurement, not a recommendation.", f"  holdings file: {os.path.basename(path)}  {h.index[0].date()} -> {h.index[-1].date()}  ({len(h)} days)", ""]
    l1, b, t, ers = run(weekly(h, px), "PRIMARY (holdings to Friday)"); L += l1
    g1 = b > 0 and t >= 2.0; g2 = all(np.isfinite(e[0]) and e[0] > 0 for e in ers)
    l2, *_ = run(weekly(h, px, thursday=True), "reported (holdings to Thursday, strictly known)"); L += l2
    L += ["", f"  G1 {'PASS' if g1 else 'FAIL'}  G2 {'PASS' if g2 else 'FAIL'}  -> GLDFLOW1 {'PASS' if g1 and g2 else 'FAIL'}"]
    open(os.path.join(OUT, "run_gldflow1.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
