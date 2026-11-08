#!/usr/bin/env python3
"""
announce.py -- FLOWS-4: the macro-announcement day premium when VIX is high.
Implements flows/PREREGISTRATION_ANNOUNCE.md; refuses to run if that file or
the frozen event table has changed.

    python3 announce.py --self-test      synthetic data only
    python3 announce.py --check-inputs   files, hashes, coverage -- NO returns
    python3 announce.py --run            the registered test, once
"""
from __future__ import annotations
import argparse, csv, io, json, os, sys
from contextlib import redirect_stdout
import numpy as np
import pandas as pd
import common as C

NAME = "ANNOUNCE"
INST, SECONDARY = "SPX500_USD", "DE30_EUR"
START = pd.Timestamp("2005-01-03")
NW_LAGS, MIN_BARS, VIX_WIN = 5, 40, 252
TYPES = ("CPI", "NFP", "GDP", "ISM")
VIXF = os.path.join(C.ROOT, "fastbot", "data", "VIXCLS.csv")
LOG = os.path.join(C.FDATA, "announce_run.log")
RES = os.path.join(C.FDATA, "announce_result.json")
TRADES = os.path.join(C.FDATA, "announce_trades.csv")


# ------------------------------------------------------------------ inputs
def load_events() -> pd.DataFrame:
    C.check_pin("ANNOUNCE_EVENTS")
    ev = pd.read_csv(os.path.join(C.FDATA, "announce_events.csv"), parse_dates=["date"])
    return ev[(ev["date"] >= START) & (ev["date"] <= C.END)]


def load_vix() -> pd.Series:
    v = pd.read_csv(VIXF)
    v["date"] = pd.to_datetime(v["date"]); v["vix"] = pd.to_numeric(v["vix"], errors="coerce")
    return v.dropna().set_index("date")["vix"].sort_index()


def high_state(vix: pd.Series, dates: pd.DatetimeIndex) -> pd.Series:
    """HIGH_t: VIX on the last calendar date BEFORE t that has a value, above
    the median of the 252 values ending on that date (section 3)."""
    med = vix.rolling(VIX_WIN, min_periods=VIX_WIN).median()
    hi = (vix > med).where(med.notna())
    pos = vix.index.searchsorted(dates, side="left") - 1      # strictly before t
    out = np.full(len(dates), np.nan)
    ok = pos >= 0
    out[ok] = hi.to_numpy()[pos[ok]].astype(float)
    return pd.Series(out, index=dates)


def day_table(inst: str) -> pd.DataFrame:
    ba = C.load_bidask(inst)
    dly = C.daily(ba, min_bars=1)
    nd = int((dly["nbars"] < MIN_BARS).sum())
    dly = dly[(dly["nbars"] >= MIN_BARS) & (dly.index >= START)].copy()
    dly.attrs["dropped_short"] = nd
    dly["r"] = dly["close_m"] / dly["open_m"] - 1.0
    return dly, ba


# ------------------------------------------------------------------ design
def design(dly: pd.DataFrame, ev: pd.DataFrame, vix: pd.Series) -> pd.DataFrame:
    idx = dly.index
    fomc = set(ev.loc[ev["event"] == "FOMC", "date"])
    df = pd.DataFrame({"r": dly["r"].to_numpy()}, index=idx)
    df["FOMC"] = idx.isin(list(fomc)).astype(float)
    for k in TYPES:
        df[k] = idx.isin(list(set(ev.loc[ev["event"] == k, "date"]))).astype(float)
    df["A"] = ((df[list(TYPES)].sum(axis=1) > 0) & (df["FOMC"] == 0)).astype(float)
    df["HIGH"] = high_state(vix, idx).to_numpy()
    df = df.dropna(subset=["HIGH"])
    df["AH"] = df["A"] * df["HIGH"]; df["AL"] = df["A"] * (1 - df["HIGH"])
    return df


def _fit(df, names):
    cols = [np.ones(len(df))] + [df[n].to_numpy() for n in names]
    keep = [0] + [i + 1 for i, n in enumerate(names) if np.ptp(df[n].to_numpy()) > 0]
    X = np.column_stack([cols[i] for i in keep])
    b, se, t, n = C.ols_nw(df["r"].to_numpy(), X, NW_LAGS)
    labs = ["c"] + names
    return {labs[i]: dict(b=float(b[j]), se=float(se[j]), t=float(t[j])) for j, i in enumerate(keep)} | {"n": int(n)}


def primary(df) -> dict:
    """theta = b1 + b3 read directly as the A*HIGH coefficient in the
    equivalent parametrisation r = c + tH*A*HIGH + tL*A*LOW + b2*HIGH + g*FOMC;
    b3 = tH - tL, t-stat from the original parametrisation."""
    f1 = _fit(df, ["AH", "AL", "HIGH", "FOMC"])
    d2 = df.assign(AxH=df["A"] * df["HIGH"])
    f2 = _fit(d2, ["A", "HIGH", "AxH", "FOMC"])
    return dict(theta=f1["AH"]["b"], theta_t=f1["AH"]["t"], low=f1.get("AL", {}).get("b", np.nan),
                low_t=f1.get("AL", {}).get("t", np.nan), b3=f2["AxH"]["b"], b3_t=f2["AxH"]["t"],
                n=f1["n"], n_AH=int(df["AH"].sum()), n_A=int(df["A"].sum()))


def trade(dly: pd.DataFrame, days, cost_bp: float = 0.0) -> pd.DataFrame:
    """Buy at the ask open of the first bar, sell at the bid close of the last
    bar of the trading date. No rollover crossed."""
    d = dly.loc[dly.index.isin(list(days))]
    k = cost_bp * 1e-4
    net = (d["close_b"] * (1 - k)) / (d["open_a"] * (1 + k)) - 1.0
    return pd.DataFrame({"net": net, "gross_mid": d["r"], "first_bar": d["first_bar"].astype(str),
                         "last_bar": d["last_bar"].astype(str)})


def prepost(ba: pd.DataFrame, dly: pd.DataFrame, days) -> pd.DataFrame:
    """Section 7: open -> start of the 08:30 ET bar, and 08:30 -> close."""
    ny = ba.index.tz_convert(C.NY)
    at = ba[(ny.hour == 8) & (ny.minute == 30)]
    td = C.trading_date(at.index)
    p830 = pd.Series(at["open_m"].to_numpy(), index=td)
    p830 = p830[~p830.index.duplicated()]
    d = dly.loc[dly.index.isin(list(days))]
    p = p830.reindex(d.index)
    return pd.DataFrame({"pre": p / d["open_m"] - 1, "post": d["close_m"] / p - 1}).dropna()


# ------------------------------------------------------------------ run
def run() -> int:
    buf = io.StringIO()
    def say(*a):
        print(*a); print(*a, file=buf)
    pin = C.check_pin(NAME); C.check_pin("ANNOUNCE_A1"); tpin = C.check_pin("ANNOUNCE_EVENTS")
    ev, vix = load_events(), load_vix()
    say(f"FLOWS-4 ANNOUNCE  prereg {pin[:16]}  events {tpin[:16]}  VIXCLS {C.sha256(VIXF)[:16]}")
    res = {"pin": pin, "events_sha": tpin, "vix_sha": C.sha256(VIXF)}
    dly, ba = day_table(INST)
    df = design(dly, ev, vix)
    say(f"  {INST}: {len(df)} days {df.index[0].date()}..{df.index[-1].date()}, "
        f"{dly.attrs['dropped_short']} dropped (<{MIN_BARS} bars)")
    say(f"  A days {int(df['A'].sum())}  A&HIGH {int(df['AH'].sum())}  FOMC {int(df['FOMC'].sum())}  "
        f"HIGH share {df['HIGH'].mean():.2f}")
    P = primary(df); res["primary"] = P
    say(f"\n  theta (A excess, high VIX) {P['theta']*1e4:+.2f} bp  t {P['theta_t']:+.2f}")
    say(f"  b3 (high minus low)        {P['b3']*1e4:+.2f} bp  t {P['b3_t']:+.2f}")
    say(f"  low-VIX excess b1          {P['low']*1e4:+.2f} bp  t {P['low_t']:+.2f}")
    eras = {}
    for e, a, b in C.ERAS:
        sub = df[(df.index >= a) & (df.index <= b)]
        eras[e] = primary(sub)
        say(f"  {e}: theta {eras[e]['theta']*1e4:+.2f} bp  t {eras[e]['theta_t']:+.2f}  n_AH {eras[e]['n_AH']}")
    res["eras"] = eras
    AH = df.index[df["AH"] == 1]
    tr = trade(dly, AH); tr1 = trade(dly, AH, 1.0)
    m, t, n = C.mean_t(tr["net"]); m1, t1, _ = C.mean_t(tr1["net"])
    e3 = tr[tr.index >= pd.Timestamp(C.ERAS[2][1])]
    m3, t3, n3 = C.mean_t(e3["net"])
    spread = float(((dly.loc[AH, "open_a"] - dly.loc[AH, "open_b"]) / dly.loc[AH, "open_m"]).mean())
    say(f"\n  G4 trade on A&HIGH days: net {m*1e4:+.2f} bp t {t:+.2f} (n {n}); +1bp/side {m1*1e4:+.2f}; "
        f"E3 net {m3*1e4:+.2f} bp (n {n3}); gross mid {tr['gross_mid'].mean()*1e4:+.2f}; open spread {spread*1e4:.2f} bp")
    tr.to_csv(TRADES)
    res["trade"] = dict(net=m, t=t, n=n, net_stress=m1, e3_net=m3, e3_n=n3, open_spread=spread)
    G = {
        "G1": P["theta"] > 0 and P["theta_t"] >= 2.0,
        "G2": all(eras[e]["theta"] > 0 for e in eras) and eras["E3"]["theta"] >= 0.5 * P["theta"],
        "G3": P["b3"] > 0,
        "G4": m > 0 and t >= 1.65 and m3 > 0,
        "G5": P["n_AH"] >= 150,
    }
    res["gates"] = G
    say("\n  " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in G.items()))
    kill = [k for k, g in (("K1", "G1"), ("K2", "G2"), ("K3", "G4")) if not G[g]]
    verdict = "DEAD " + ",".join(kill) if kill else ("PASS" if G["G3"] and G["G5"] else "PASS-UNCONDITIONAL / SIZE: see G3, G5")
    res["verdict"] = verdict
    say(f"  VERDICT: {verdict}")
    # ---- secondary
    say("\n  secondary (descriptive):")
    pv, per = {}, {}
    for k in TYPES:
        d2 = df.assign(KH=df[k] * (1 - df["FOMC"]) * df["HIGH"], KL=df[k] * (1 - df["FOMC"]) * (1 - df["HIGH"]),
                       OA=((df["A"] == 1) & (df[k] == 0)).astype(float))
        f = _fit(d2, ["KH", "KL", "OA", "HIGH", "FOMC"])
        per[k] = dict(theta=f["KH"]["b"], t=f["KH"]["t"], n=int(d2["KH"].sum()))
        pv[k] = C.p_two_sided(f["KH"]["t"])
    q = C.bh(pv)
    for k in TYPES:
        per[k]["q"] = q[k]
        say(f"    {k:4s} high-VIX excess {per[k]['theta']*1e4:+.2f} bp t {per[k]['t']:+.2f} q {q[k]:.2f} (n {per[k]['n']})")
    res["per_type"] = per
    fo = df[df["FOMC"] == 1]
    res["fomc"] = dict(high=float(fo.loc[fo["HIGH"] == 1, "r"].mean()), low=float(fo.loc[fo["HIGH"] == 0, "r"].mean()),
                       n_high=int(fo["HIGH"].sum()), n_low=int((1 - fo["HIGH"]).sum()))
    say(f"    FOMC mean day return: high VIX {res['fomc']['high']*1e4:+.2f} bp (n {res['fomc']['n_high']}), "
        f"low {res['fomc']['low']*1e4:+.2f} bp (n {res['fomc']['n_low']})")
    rel830 = df.index[(df["AH"] == 1) & ((df["CPI"] + df["NFP"] + df["GDP"]) > 0)]
    ctl = df.index[(df["A"] == 0) & (df["FOMC"] == 0) & (df["HIGH"] == 1)]
    pa, pc = prepost(ba, dly, rel830), prepost(ba, dly, ctl)
    res["prepost"] = dict(pre=pa["pre"].mean(), post=pa["post"].mean(), n=len(pa),
                          ctl_pre=pc["pre"].mean(), ctl_post=pc["post"].mean(), ctl_n=len(pc))
    say(f"    08:30 releases, high VIX: pre {pa['pre'].mean()*1e4:+.2f} post {pa['post'].mean()*1e4:+.2f} bp (n {len(pa)}); "
        f"control high-VIX days pre {pc['pre'].mean()*1e4:+.2f} post {pc['post'].mean()*1e4:+.2f} (n {len(pc)})")
    d30, _ = day_table(SECONDARY)
    P2 = primary(design(d30, ev, vix)); res["de30"] = P2
    say(f"    DE30: theta {P2['theta']*1e4:+.2f} bp t {P2['theta_t']:+.2f}; b3 {P2['b3']*1e4:+.2f}")
    open(LOG, "w").write(buf.getvalue())
    json.dump(res, open(RES, "w"), indent=1, default=float)
    say(f"\n  log {os.path.basename(LOG)}  result {os.path.basename(RES)}  trades {os.path.basename(TRADES)}")
    return 0


def check_inputs() -> int:
    print(f"prereg pin: {C.check_pin(NAME)[:16]} OK; amendment A1 {C.check_pin('ANNOUNCE_A1')[:16]} OK")
    ev = load_events()
    print(f"event table pinned OK; rows {len(ev)}: " + ", ".join(f"{k} {int((ev['event']==k).sum())}" for k in ("FOMC",) + TYPES))
    vix = load_vix()
    print(f"VIXCLS {vix.index[0].date()}..{vix.index[-1].date()} ({len(vix)} values), sha {C.sha256(VIXF)[:16]}")
    for inst in (INST, SECONDARY):
        ba = C.load_bidask(inst)
        print(f"{inst}: {len(ba)} bars {ba.index[0]} .. {ba.index[-1]}  (grid OK)")
    return 0


# ------------------------------------------------------------------ self-test
def self_test() -> int:
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    days = pd.bdate_range("2005-01-03", "2026-08-31")
    rng = np.random.default_rng(7)
    vix = pd.Series(15 + 5 * np.sin(np.arange(len(days)) / 40) + rng.normal(0, 1, len(days)), index=days)
    hi = high_state(vix, days)
    j = 3000
    v2 = vix.copy(); v2.iloc[j] = 500
    check("HIGH_t uses VIX before t only (a spike ON t does not set HIGH_t)",
          high_state(v2, days).iloc[j] == hi.iloc[j] and high_state(v2, days).iloc[j + 1] == 1.0)
    check("first 252 VIX values give no state", hi.iloc[:252].isna().all())
    evd = [d for d in days if d.day <= 7 and d.dayofweek == 4]
    fomc = evd[::6]
    ev = pd.DataFrame({"event": ["NFP"] * len(evd) + ["FOMC"] * len(fomc), "date": evd + fomc})
    r = rng.normal(0, 0.01, len(days))
    hv = high_state(vix, days).fillna(0).to_numpy()
    isA = days.isin(evd) & ~days.isin(fomc)
    r[isA & (hv == 1)] += 0.008                 # 80bp: a machinery check, not a power claim
    r[days.isin(fomc)] += 0.02
    dly = pd.DataFrame({"r": r, "open_m": 100.0, "close_m": 100 * (1 + r)}, index=days)
    df = design(dly, ev, vix)
    check("FOMC days are never A", int(((df["A"] == 1) & (df["FOMC"] == 1)).sum()) == 0)
    P = primary(df)
    check(f"planted +80bp on A&HIGH recovered (theta {P['theta']*1e4:+.1f}, t {P['theta_t']:+.1f})",
          abs(P["theta"] - 0.008) < 0.003 and P["theta_t"] > 2)
    check(f"b3 = high minus low (b3 {P['b3']*1e4:+.1f}, low {P['low']*1e4:+.1f})",
          abs(P["b3"] - (P["theta"] - P["low"])) < 1e-10)
    check("a planted FOMC effect does not leak into theta", abs(P["theta"] - 0.008) < 0.003)
    r0 = rng.normal(0, 0.01, len(days))
    P0 = primary(design(dly.assign(r=r0), ev, vix))
    check(f"null data: theta not significant (t {P0['theta_t']:+.2f})", abs(P0["theta_t"]) < 2.5)
    idx = pd.date_range("2025-07-30 22:00", "2025-07-31 21:00", freq="15min", tz="UTC", inclusive="left")
    ba = pd.DataFrame({"open_b": 99.98, "open_a": 100.02, "open_m": 100.0, "close_b": 100.18,
                       "close_a": 100.22, "close_m": 100.2, "high_m": 1, "low_m": 1}, index=idx)
    ba.loc[idx[-1], ["close_b", "close_m"]] = [101.0, 101.02]
    dd = C.daily(ba, 1); dd["r"] = dd["close_m"] / dd["open_m"] - 1
    tr = trade(dd, [pd.Timestamp("2025-07-31")])
    check("trade: ask open of first bar in, bid close of last bar out",
          abs(tr["net"].iloc[0] - (101.0 / 100.02 - 1)) < 1e-12
          and tr["first_bar"].iloc[0].startswith("2025-07-30 22:00"))
    ba.loc[ba.index.tz_convert(C.NY).strftime("%H:%M") == "08:30", "open_m"] = 100.5
    pp = prepost(ba, dd, [pd.Timestamp("2025-07-31")])
    check("pre/post split at the 08:30 ET bar", abs(pp["pre"].iloc[0] - 0.005) < 1e-12
          and abs(pp["post"].iloc[0] - (101.02 / 100.5 - 1)) < 1e-12)
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test", action="store_true"); g.add_argument("--check-inputs", action="store_true")
    g.add_argument("--run", action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else check_inputs() if a.check_inputs else run())
