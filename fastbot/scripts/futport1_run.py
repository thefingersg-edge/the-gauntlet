#!/usr/bin/env python3
"""FUTPORT1 harness (PREREGISTRATION_FUTPORT1.md, sha 76449002...): trend + carry across 29 CME futures, daily, 2010-06 -> 2026-09.
    python3 futport1_run.py --self-test
    python3 futport1_run.py run      -> data/futport1/run_futport1.log  (refuses to run twice)
Mechanical readings fixed here BEFORE the run (logged in PROVENANCE):
  * Input: data/futport1/<ROOT>_c_{0,1}.csv (Databento ohlcv-1d; UTC-dated bars). Saturday/Sunday-dated bars (the Sunday-evening session stub)
    are dropped, so each return runs weekday close to weekday close. c.0 and c.1 are joined on common dates (inner join). A thin front month
    (e.g. PL) therefore has multi-day gaps, and its returns span them (disclosed).
  * Roll-adjusted return: r_t = (c0_t - ref) / |ref|, where ref = c0_{t-1} if the c.0 instrument_id is unchanged, else c1_{t-1}.
  * sigma = sqrt(EWMA(com 60) of r^2 x 252) on the market's own rows, lagged one row. Signals are computed at close t and held from t+1.
    Trend = mean of sign(sum r over the last 21 / 63 / 252 rows). Carry = sign(c0/c1 - 1).
  * Each market's weight w = signal x 0.10 / sigma, capped at +-4; it needs 252 rows of history. On the union calendar, a market absent on a date
    keeps its weight and earns 0.
  * Market P&L_t = w_{t-1} x r_t - |w_t - w_{t-1}| x c - (roll day) |w_{t-1}| x 2c, where c = the group's cost per side.
  * Sleeve = equal-weight mean over markets with a defined weight that day. Scale = min(3, 0.10 / (trailing 252-day sd x sqrt 252)), lagged one day.
    It starts once 252 sleeve days exist. Portfolio = 0.5 trend + 0.5 carry (both scaled). The long-only benchmark uses the same construction with signal +1.
  * Sharpe = mean / sd x sqrt 252 over the portfolio's live days; years = live days / 252. Eras: 2010-06..2015, 2016..2020, 2021..2026-09.
  * Implementability (reported): contract multipliers below (micro where one exists) at each day's c.0 price; whole-contract rounding of the
    portfolio's per-market notional at $25k and $100k, with the resulting Sharpe and correlation to the unrounded portfolio.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, math, hashlib
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, "..")
SPEC = os.path.join(FB, "PREREGISTRATION_FUTPORT1.md"); SPEC_SHA = "764490027abe2ef51bef493808dfd701309b0c87904a88f054e082110f2363c6"
D = os.path.join(FB, "data", "futport1")
DISC = "I am not a financial adviser. This is a measurement, not a recommendation."
GROUP = {"equity": (["ES", "NQ", "YM", "RTY"], 1.0), "rates": (["ZT", "ZF", "ZN", "ZB"], 1.0), "fx": (["6E", "6J", "6B", "6A", "6C", "6S"], 1.0),
         "metals": (["GC", "SI", "HG", "PL"], 2.0), "energy": (["CL", "NG", "HO", "RB"], 2.0), "grains": (["ZC", "ZS", "ZW", "ZL", "ZM"], 3.0),
         "livestock": (["LE", "HE"], 3.0)}
ROOTS = [r for g in GROUP.values() for r in g[0]]
COST = {r: g[1] * 1e-4 for g in GROUP.values() for r in g[0]}
GRP = {r: k for k, g in GROUP.items() for r in g[0]}
MULT = {"ES": 5, "NQ": 2, "YM": 0.5, "RTY": 5, "ZT": 2000, "ZF": 1000, "ZN": 1000, "ZB": 1000, "6E": 12500, "6J": 1250000, "6B": 6250,
        "6A": 10000, "6C": 10000, "6S": 12500, "GC": 10, "SI": 1000, "HG": 2500, "PL": 50, "CL": 100, "NG": 1000, "HO": 42000, "RB": 42000,
        "ZC": 10, "ZS": 10, "ZW": 10, "ZL": 600, "ZM": 100, "LE": 400, "HE": 400}       # $ per 1.0 of quoted price (micro / mini where they exist)
ERAS = (("2010-06-01", "2016-01-01"), ("2016-01-01", "2021-01-01"), ("2021-01-01", "2026-10-01"))


def pin():
    if hashlib.sha256(open(SPEC, "rb").read()).hexdigest() != SPEC_SHA: sys.exit("spec changed -- refused")


def load(root):
    def rd(k):
        x = pd.read_csv(os.path.join(D, f"{root}_c_{k}.csv"), usecols=["ts_event", "instrument_id", "close"])
        x["date"] = pd.to_datetime(x["ts_event"].str[:10]); x = x[x["date"].dt.weekday < 5]
        return x.drop_duplicates("date", keep="last").set_index("date")[["instrument_id", "close"]]
    a, b = rd(0), rd(1); j = a.join(b, lsuffix="0", rsuffix="1", how="inner").sort_index()
    return j


def market(j):
    c0, c1, iid = j["close0"].to_numpy(float), j["close1"].to_numpy(float), j["instrument_id0"].to_numpy()
    n = len(c0); r = np.zeros(n); roll = np.zeros(n, bool)
    for t in range(1, n):
        roll[t] = iid[t] != iid[t - 1]; ref = c1[t - 1] if roll[t] else c0[t - 1]
        r[t] = (c0[t] - ref) / abs(ref) if ref != 0 else 0.0
    var = pd.Series(r ** 2).ewm(com=60).mean().to_numpy(); sig = np.sqrt(var * 252); sig = np.r_[np.nan, sig[:-1]]
    cs = np.cumsum(r)
    def past(k): out = np.full(n, np.nan); out[k:] = cs[k:] - cs[:-k]; return out
    trend = (np.sign(past(21)) + np.sign(past(63)) + np.sign(past(252))) / 3
    carry = np.sign(c0 / c1 - 1)
    ok = np.arange(n) >= 252
    def w(sigl):
        x = np.where(ok & np.isfinite(sig) & (sig > 0), np.clip(sigl * 0.10 / np.where(sig > 0, sig, 1), -4, 4), np.nan)
        return x
    # weight on row t is set at close t (signal at t, sigma through t-1); it earns from t+1 via w_{t-1} x r_t in sleeve_pnl
    return pd.DataFrame(dict(r=r, roll=roll, w_tr=w(trend), w_ca=w(carry), w_lo=w(np.ones(n)), c0=c0), index=j.index)


def sleeve_pnl(M, wcol):
    """Returns (daily sleeve raw pnl, per-market contribution frame, weights frame) on the union calendar."""
    cal = sorted(set().union(*[m.index for m in M.values()])); cal = pd.DatetimeIndex(cal)
    P, W = {}, {}
    for k, m in M.items():
        w = m[wcol].reindex(cal).ffill()                       # absent days keep their weight
        r = m["r"].reindex(cal).fillna(0.0); roll = m["roll"].reindex(cal).fillna(False).astype(bool)
        wp = w.shift(1)
        pnl = wp * r - (w - wp).abs().fillna(0) * COST[k] - np.where(roll, wp.abs() * 2 * COST[k], 0.0)
        P[k] = pnl; W[k] = w
    P = pd.DataFrame(P); W = pd.DataFrame(W)
    act = W.shift(1).notna()
    n = act.sum(1).replace(0, np.nan)
    raw = P.where(act).sum(1) / n
    return raw, P.where(act).div(n, axis=0), W


def scale(raw):
    sd = raw.rolling(252).std().shift(1) * math.sqrt(252)
    s = np.minimum(3.0, 0.10 / sd)
    return (raw * s), s


def stats(x):
    x = x.dropna(); sh = x.mean() / x.std() * math.sqrt(252); yrs = len(x) / 252
    cum = x.cumsum(); dd = float((cum - cum.cummax()).min())
    ers = [x[(x.index >= a) & (x.index < b)].sum() for a, b in ERAS]
    return dict(sh=sh, shy=sh * math.sqrt(yrs), yrs=yrs, ann=x.mean() * 252, dd=dd, eras=ers)


def fmt(s): return (f"Sharpe {s['sh']:+.2f} (x sqrt {s['yrs']:.1f} yrs = {s['shy']:+.2f}), {s['ann'] * 100:+.1f}%/yr, worst drawdown {s['dd'] * 100:.1f}%; eras "
                    + " / ".join(f"{e * 100:+.1f}%" for e in s["eras"]))


def run():
    pin(); P = os.path.join(D, "run_futport1.log")
    if os.path.exists(P): sys.exit("already run")
    M = {r: market(load(r)) for r in ROOTS}
    out = {}
    for nm, col in (("trend", "w_tr"), ("carry", "w_ca"), ("longonly", "w_lo")):
        raw, contrib, W = sleeve_pnl(M, col); sc, s = scale(raw); out[nm] = (sc, contrib, W, s)
    port = (0.5 * out["trend"][0] + 0.5 * out["carry"][0]).dropna()
    lo = out["longonly"][0].reindex(port.index)
    S, St, Sc, Sl = stats(port), stats(out["trend"][0].reindex(port.index)), stats(out["carry"][0].reindex(port.index)), stats(lo)
    g1 = S["shy"] >= 2.0; g2 = all(e > 0 for e in S["eras"]); g3 = S["sh"] > Sl["sh"]
    es = M["ES"]["r"].reindex(port.index).fillna(0.0)
    L = ["FUTPORT1 -- trend + carry across 29 CME futures (Databento ohlcv-1d, c.0/c.1), daily", "  " + DISC,
         f"  live {port.index[0].date()} -> {port.index[-1].date()} ({len(port)} days); markets " + ", ".join(f"{r}:{M[r].index[0].year}" for r in ROOTS if M[r].index[0].year > 2010), "",
         "  PORTFOLIO (50/50): " + fmt(S),
         "  trend sleeve:      " + fmt(St), "  carry sleeve:      " + fmt(Sc), "  long-only (equal risk, same construction): " + fmt(Sl),
         f"  corr(trend, carry) {out['trend'][0].reindex(port.index).corr(out['carry'][0].reindex(port.index)):+.2f};  corr(portfolio, ES) {port.corr(es):+.2f}",
         f"  2020 {port['2020'].sum() * 100:+.1f}%   2022 {port['2022'].sum() * 100:+.1f}%", "",
         f"  G1 {'PASS' if g1 else 'FAIL'} (Sharpe x sqrt(years) >= 2.0)  G2 {'PASS' if g2 else 'FAIL'} (every era > 0)  G3 {'PASS' if g3 else 'FAIL'} (beats long-only)"
         f"  -> FUTPORT1 {'PASS' if g1 and g2 and g3 else 'FAIL'}", "", "  group contributions to the portfolio (sum of daily % over the live period):"]
    for g, (rs, _) in GROUP.items():
        ct = sum(0.5 * (out[n][1][rs].reindex(port.index).sum(1) * out[n][3].reindex(port.index)).sum() for n in ("trend", "carry"))
        L.append(f"    {g:9s} {ct * 100:+7.1f}%")
    L.append("\n  per-market Sharpe of the unscaled sleeve legs (trend / carry):")
    for r in ROOTS:
        def msh(col):
            m = M[r]; w = m[col].shift(1); x = (w * m["r"]).dropna(); return x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else float("nan")
        L.append(f"    {r:4s} {GRP[r]:9s} trend {msh('w_tr'):+.2f}   carry {msh('w_ca'):+.2f}")
    # implementability (reported)
    L.append("\n  implementability (whole contracts, micro/mini multipliers; reported):")
    for cap in (25_000, 100_000, 1_000_000):
        rp = []
        for n in ("trend", "carry"):
            sc, contrib, W, s = out[n]; act = W.shift(1).notna(); nact = act.sum(1).replace(0, np.nan)
            for r in ROOTS:
                m = M[r]; px = m["c0"].reindex(W.index).ffill(); mult = MULT[r]
                tgt = 0.5 * W[r].shift(1) / nact * s * cap                             # $ notional wanted for this sleeve leg
                k = (tgt / (px.abs() * mult)).round()                                    # whole contracts
                ret = m["r"].reindex(W.index).fillna(0.0)
                rp.append((k * px.abs() * mult * ret / cap).fillna(0.0).rename(f"{n}{r}"))
        R = pd.concat(rp, axis=1).sum(1).reindex(port.index)
        nz = 0
        L.append(f"    ${cap:>9,}: Sharpe {R.mean() / R.std() * math.sqrt(252) if R.std() > 0 else float('nan'):+.2f}, corr with the unrounded portfolio "
                 f"{R.corr(port):+.2f}, {R.std() * math.sqrt(252) * 100:.1f}% vol (target 10%)")
    port.to_frame("portfolio").assign(trend=out["trend"][0], carry=out["carry"][0], longonly=lo).to_csv(os.path.join(D, "futport1_daily.csv"))
    open(P, "w").write("\n".join(L) + "\n"); print("\n".join(L))


def self_test():
    ok = True
    idx = pd.bdate_range("2020-01-01", periods=400)
    c0 = 100 + np.arange(400) * 0.1; c1 = c0 + 1.0; iid = np.r_[np.ones(200), np.full(200, 2)]
    j = pd.DataFrame(dict(instrument_id0=iid, close0=c0, instrument_id1=iid + 1, close1=c1), index=idx)
    m = market(j)
    e1 = m["roll"].iloc[200] and abs(m["r"].iloc[200] - (c0[200] - c1[199]) / c1[199]) < 1e-12
    ok &= e1; print(f"  [{'PASS' if e1 else 'FAIL'}] roll day return measured against yesterday's c.1")
    e2 = (m["w_tr"].dropna() > 0).all() and (m["w_ca"].dropna() < 0).all() and m["w_tr"].iloc[:252].isna().all()
    ok &= e2; print(f"  [{'PASS' if e2 else 'FAIL'}] rising market -> long trend; contango -> short carry; no weight before 252 rows")
    M = {"ES": m}; global COST; COST = dict(COST); raw, contrib, W = sleeve_pnl(M, "w_tr")
    t = 300; wexp = m["w_tr"].iloc[t - 1] * m["r"].iloc[t] - abs(m["w_tr"].iloc[t] - m["w_tr"].iloc[t - 1]) * COST["ES"]
    e3 = abs(raw.iloc[t] - wexp) < 1e-12; ok &= e3; print(f"  [{'PASS' if e3 else 'FAIL'}] P&L = yesterday's weight x today's return - turnover cost")
    x = pd.Series(np.random.default_rng(0).normal(0, 0.02, 2000), index=pd.bdate_range("2010-01-01", periods=2000)); sc, s = scale(x)
    e4 = abs(sc.iloc[300:].std() * math.sqrt(252) - 0.10) < 0.02 and s.iloc[:252].isna().all(); ok &= e4
    print(f"  [{'PASS' if e4 else 'FAIL'}] sleeve scaled to ~10% annual vol, none before 252 days")
    e5 = len(ROOTS) == 29 and set(MULT) == set(ROOTS); ok &= e5; print(f"  [{'PASS' if e5 else 'FAIL'}] 29 roots, every one with a multiplier and a cost")
    print("ALL PASS" if ok else "FAILURES"); return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--self-test"]: sys.exit(0 if self_test() else 1)
    if not self_test(): sys.exit("self-test failed")
    if a == ["run"]: run()
