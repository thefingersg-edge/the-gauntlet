#!/usr/bin/env python3
"""
natgas.py -- FLOWS-6: natural gas on EIA storage-report days.
Implements flows/PREREGISTRATION_NATGAS.md; refuses to run if that file or
the frozen calendar has changed.

    python3 natgas.py --self-test      synthetic data only
    python3 natgas.py --check-inputs   files, hashes, coverage -- NO returns
    python3 natgas.py --run            the registered test, once
"""
from __future__ import annotations
import argparse, io, json, os, sys
import numpy as np
import pandas as pd
import common as C

NAME, INST = "NATGAS", "NATGAS_USD"
NW_LAGS, MIN_BARS = 5, 40
LATEST_START, MIN_YEARS = pd.Timestamp("2008-01-01"), 10
LOG = os.path.join(C.FDATA, "natgas_run.log")
RES = os.path.join(C.FDATA, "natgas_result.json")
TRADES = os.path.join(C.FDATA, "natgas_trades.csv")


def load_calendar():
    C.check_pin("EIA_EVENTS")
    cal = pd.read_csv(os.path.join(C.FDATA, "eia_events.csv"), parse_dates=["week_monday", "report_day"])
    keep = set(cal.loc[cal["status"] == "REPORT", "week_monday"])
    rep = set(cal.loc[cal["status"] == "REPORT", "report_day"])
    return keep, rep


def sample_start(first_bar: pd.Timestamp):
    """First full month of data (section 1); None if the test is void."""
    f = pd.Timestamp(first_bar.tz_convert(C.NY).date())
    s = f if f.day == 1 else (f + pd.offsets.MonthBegin(1))
    s = max(s, pd.Timestamp("2005-01-03"))
    void = s > LATEST_START and (C.END - s).days / 365.25 < MIN_YEARS
    return s, void


def design(dly: pd.DataFrame, keep: set, rep: set) -> pd.DataFrame:
    idx = dly.index
    wk = idx - pd.to_timedelta(idx.dayofweek, unit="D")
    df = pd.DataFrame({"r": (dly["close_m"] / dly["open_m"] - 1).to_numpy()}, index=idx)
    df = df[wk.isin(list(keep)) & (idx.dayofweek < 5)]
    df["EIA"] = df.index.isin(list(rep)).astype(float)
    df["WED"] = df.index.isin([d - pd.Timedelta(days=1) for d in rep]).astype(float)
    return df


def fit(df, col):
    X = np.column_stack([np.ones(len(df)), df[col].to_numpy()])
    b, se, t, n = C.ols_nw(df["r"].to_numpy(), X, NW_LAGS)
    return dict(b=float(b[1]), t=float(t[1]), n=int(n), n_ev=int(df[col].sum()))


def trade(dly, days, cost_bp=0.0):
    d = dly.loc[dly.index.isin(list(days))]
    k = cost_bp * 1e-4
    return (d["close_b"] * (1 - k)) / (d["open_a"] * (1 + k)) - 1.0


def prepost(ba, dly, days):
    ny = ba.index.tz_convert(C.NY)
    at = ba[(ny.hour == 10) & (ny.minute == 30)]
    p = pd.Series(at["open_m"].to_numpy(), index=C.trading_date(at.index))
    p = p[~p.index.duplicated()]
    d = dly.loc[dly.index.isin(list(days))]
    p = p.reindex(d.index)
    return pd.DataFrame({"pre": p / d["open_m"] - 1, "post": d["close_m"] / p - 1}).dropna()


def gaps(ba: pd.DataFrame, n=20) -> pd.DataFrame:
    td = C.trading_date(ba.index)
    prev_close = ba["close_m"].shift(1)
    same = pd.Series(td, index=ba.index) == pd.Series(td, index=ba.index).shift(1)
    g = (ba["open_m"] / prev_close - 1).where(same.to_numpy())
    top = g.abs().dropna().sort_values(ascending=False).head(n).index
    return pd.DataFrame({"gap": g.loc[top], "trading_date": pd.Series(td, index=ba.index).loc[top].astype(str)})


def run() -> int:
    buf = io.StringIO()
    def say(*a):
        print(*a); print(*a, file=buf)
    pin, cpin = C.check_pin(NAME), C.check_pin("EIA_EVENTS")
    keep, rep = load_calendar()
    ba = C.load_bidask(INST)
    start, void = sample_start(ba.index[0])
    say(f"FLOWS-6 NATGAS  prereg {pin[:16]}  calendar {cpin[:16]}  data from {ba.index[0]}  sample from {start.date()}")
    res = {"pin": pin, "cal_sha": cpin, "start": str(start.date())}
    if void:
        say("  VOID: fewer than 10 years of data (section 1)")
        res["verdict"] = "VOID"
        open(LOG, "w").write(buf.getvalue()); json.dump(res, open(RES, "w"), indent=1)
        return 0
    dly = C.daily(ba, min_bars=1)
    short = int(((dly["nbars"] < MIN_BARS) & (dly.index >= start)).sum())
    dly = dly[(dly["nbars"] >= MIN_BARS) & (dly.index >= start)]
    df = design(dly, keep, rep)
    say(f"  days {len(df)} (dropped <{MIN_BARS} bars: {short}); report days {int(df['EIA'].sum())}")
    P = fit(df, "EIA"); res["primary"] = P
    say(f"\n  G1 b (report-day excess) {P['b']*1e4:+.2f} bp  t {P['t']:+.2f}")
    eras = {}
    for e, a, b in C.ERAS:
        sub = df[(df.index >= a) & (df.index <= b)]
        eras[e] = fit(sub, "EIA") if sub["EIA"].sum() > 10 else dict(b=np.nan, t=np.nan, n=len(sub), n_ev=int(sub["EIA"].sum()))
        say(f"  {e}: b {eras[e]['b']*1e4:+.2f} bp t {eras[e]['t']:+.2f} report days {eras[e]['n_ev']}")
    res["eras"] = eras
    ev_days = df.index[df["EIA"] == 1]
    net, net1 = trade(dly, ev_days), trade(dly, ev_days, 1.0)
    m, t, n = C.mean_t(net)
    e3 = net[net.index >= pd.Timestamp(C.ERAS[2][1])]
    say(f"\n  G3 trade: net {m*1e4:+.2f} bp t {t:+.2f} n {n}; +1bp/side {net1.mean()*1e4:+.2f}; E3 net {e3.mean()*1e4:+.2f} (n {len(e3)})")
    res["trade"] = dict(net=m, t=t, n=n, net_stress=float(net1.mean()), e3_net=float(e3.mean()), e3_n=int(len(e3)))
    pd.DataFrame({"net": net, "gross_mid": df.loc[ev_days, "r"]}).to_csv(TRADES)
    PL = fit(df, "WED"); res["placebo"] = PL
    say(f"  G4 placebo (Wednesday before): b {PL['b']*1e4:+.2f} bp t {PL['t']:+.2f}")
    G = {"G1": P["b"] > 0 and P["t"] >= 2.0,
         "G2": all(np.isfinite(eras[e]["b"]) and eras[e]["b"] > 0 for e in eras) and eras["E3"]["b"] >= 0.5 * P["b"],
         "G3": m > 0 and t >= 1.65 and e3.mean() > 0,
         "G4": PL["t"] < 2.0 and PL["b"] < P["b"],
         "G5": P["n_ev"] >= 400}
    q = C.bh({"G1": C.p_two_sided(P["t"]), "G4": C.p_two_sided(PL["t"])})
    res["gates"], res["bh_q"] = G, q
    say("\n  " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in G.items()) + f"   BH q(G1) {q['G1']:.3f}")
    kill = [k for k, g in (("K1", "G1"), ("K2", "G2"), ("K3", "G3"), ("K4", "G4")) if not G[g]]
    res["verdict"] = "DEAD " + ",".join(kill) if kill else ("PASS" if G["G5"] else "PASS but G5 short")
    say(f"  VERDICT: {res['verdict']}")
    say("\n  secondary (descriptive):")
    pp = prepost(ba, dly, ev_days)
    res["prepost"] = dict(pre=float(pp["pre"].mean()), post=float(pp["post"].mean()), n=len(pp))
    say(f"    report days: open->10:30 {pp['pre'].mean()*1e4:+.2f} bp, 10:30->close {pp['post'].mean()*1e4:+.2f} bp (n {len(pp)})")
    wd = df.groupby(df.index.dayofweek)["r"].agg(["mean", "count"])
    res["weekday"] = {int(k): dict(mean=float(v["mean"]), n=int(v["count"])) for k, v in wd.iterrows()}
    say("    weekday means: " + "  ".join(f"{'MTWTF'[k]} {v['mean']*1e4:+.2f}" for k, v in wd.iterrows()))
    sp = ((dly.loc[ev_days, "open_a"] - dly.loc[ev_days, "open_b"]) / dly.loc[ev_days, "open_m"]
          + (dly.loc[ev_days, "close_a"] - dly.loc[ev_days, "close_b"]) / dly.loc[ev_days, "close_m"]) / 2
    res["spread_by_era"] = {e: float(sp[(sp.index >= a) & (sp.index <= b)].mean()) for e, a, b in C.ERAS}
    say("    round-trip spread paid by era: " + "  ".join(f"{e} {v*1e4:.1f} bp" for e, v in res["spread_by_era"].items()))
    gp = gaps(ba[ba.index >= start.tz_localize(C.NY)])
    res["top_gaps"] = [dict(bar=str(i), gap=float(r["gap"]), td=r["trading_date"]) for i, r in gp.iterrows()]
    say("    20 largest intraday bar gaps:")
    for i, r in gp.iterrows():
        say(f"      {i}  {r['gap']*100:+.2f}%  (trading date {r['trading_date'][:10]})")
    open(LOG, "w").write(buf.getvalue())
    json.dump(res, open(RES, "w"), indent=1, default=float)
    say(f"\n  log {os.path.basename(LOG)}  result {os.path.basename(RES)}  trades {os.path.basename(TRADES)}")
    return 0


def check_inputs() -> int:
    print(f"prereg pin: {C.check_pin(NAME)[:16]} OK")
    keep, rep = load_calendar()
    print(f"calendar pinned OK: {len(keep)} retained weeks, {len(rep)} report days")
    ba = C.load_bidask(INST)
    s, void = sample_start(ba.index[0])
    print(f"{INST}: {len(ba)} bars {ba.index[0]} .. {ba.index[-1]} (grid OK); sample from {s.date()}{'  -> VOID' if void else ''}")
    td = pd.DatetimeIndex(sorted(set(C.trading_date(ba.index))))
    have = sum(1 for d in rep if d >= s and d in td)
    print(f"report days with bars: {have} of {sum(1 for d in rep if d >= s)}")
    return 0


def self_test() -> int:
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    days = pd.bdate_range("2005-01-03", "2026-08-31")
    mons = pd.DatetimeIndex(sorted({d - pd.Timedelta(days=d.dayofweek) for d in days}))
    keep = set(mons[mons.month != 11])                        # drop Novembers, as an exclusion test
    rep = {m + pd.Timedelta(days=3) for m in keep}
    rng = np.random.default_rng(11)
    r = rng.normal(0, 0.03, len(days))
    r[days.isin(list(rep))] += 0.02                            # 200bp: machinery check, not a power claim
    dly = pd.DataFrame({"open_m": 100.0, "close_m": 100 * (1 + r)}, index=days)
    df = design(dly, keep, rep)
    check("excluded weeks are dropped from both groups",
          ((df.index - pd.to_timedelta(df.index.dayofweek, unit="D")).month != 11).all())
    check("report days are Thursdays", (df.index[df["EIA"] == 1].dayofweek == 3).all())
    P = fit(df, "EIA")
    check(f"planted +200bp recovered (b {P['b']*1e4:+.0f}, t {P['t']:+.1f})", abs(P["b"] - 0.02) < 0.006 and P["t"] > 2)
    PL = fit(df, "WED")
    # as registered, WED replaces EIA in the same regression, so a real
    # Thursday effect pushes the placebo NEGATIVE; G4 only bars t >= 2
    check(f"placebo Wednesday is not credited with the Thursday effect (t {PL['t']:+.2f})", PL["t"] < 2.0 and (df.index[df['WED'] == 1].dayofweek == 2).all())
    check("start: data from 2005-06-14 -> sample from 2005-07-01",
          sample_start(pd.Timestamp("2005-06-14 22:00", tz="UTC"))[0] == pd.Timestamp("2005-07-01"))
    check("start after 2008 with < 10 years -> VOID", sample_start(pd.Timestamp("2018-03-05", tz="UTC"))[1])
    idx = pd.date_range("2025-07-30 22:00", "2025-07-31 21:00", freq="15min", tz="UTC", inclusive="left")
    ba = pd.DataFrame({"open_b": 2.99, "open_a": 3.01, "open_m": 3.0, "close_b": 3.09, "close_a": 3.11, "close_m": 3.1,
                       "high_m": 1, "low_m": 1}, index=idx)
    ba.loc[ba.index.tz_convert(C.NY).strftime("%H:%M") == "10:30", "open_m"] = 3.06
    dd = C.daily(ba, 1)
    tr = trade(dd, [pd.Timestamp("2025-07-31")])
    check("trade: ask open in, bid close out", abs(tr.iloc[0] - (3.09 / 3.01 - 1)) < 1e-12)
    pp = prepost(ba, dd, [pd.Timestamp("2025-07-31")])
    check("pre/post split at the 10:30 ET bar", abs(pp["pre"].iloc[0] - 0.02) < 1e-12 and abs(pp["post"].iloc[0] - (3.1 / 3.06 - 1)) < 1e-12)
    ba2 = ba.copy(); ba2.iloc[40, ba2.columns.get_loc("open_m")] = 3.5
    check("gap list finds a planted intraday jump", gaps(ba2, 1).index[0] == ba2.index[40])
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test", action="store_true"); g.add_argument("--check-inputs", action="store_true")
    g.add_argument("--run", action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else check_inputs() if a.check_inputs else run())
