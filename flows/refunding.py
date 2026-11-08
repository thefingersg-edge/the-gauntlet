#!/usr/bin/env python3
"""
refunding.py -- FLOWS-2: the Friday before Treasury's borrowing estimates.
Implements flows/PREREGISTRATION_REFUNDING.md; refuses to run if that file
or the frozen event table has changed.

    python3 refunding.py --self-test      synthetic data only
    python3 refunding.py --check-inputs   files, hashes, event coverage -- NO returns
    python3 refunding.py --run            the registered test, once
"""
from __future__ import annotations
import argparse, csv, datetime as dt, io, json, os, sys
import numpy as np
import pandas as pd
import common as C

NAME = "REFUNDING"
BD, SECONDARY = "USB10Y_USD", ("USB30Y_USD", "DE10YB_EUR")
START, G1_END, POST = pd.Timestamp("2005-01-01"), pd.Timestamp("2023-12-31"), pd.Timestamp("2024-01-01")
NW_LAGS = 5
LOG = os.path.join(C.FDATA, "refunding_run.log")


def load_events() -> pd.DataFrame:
    C.check_pin("EVENTS")
    ev = pd.read_csv(os.path.join(C.FDATA, "refunding_events.csv"), parse_dates=["T", "P"])
    bad = ev[~ev["status"].astype(str).str.startswith("OK")]
    if len(bad):
        raise SystemExit(f"event rows not OK: {bad['quarter'].tolist()}")
    return ev


def fomc_dates() -> set:
    out = set()
    for r in csv.DictReader(open(os.path.join(C.ROOT, "fastbot", "data", "events.csv"))):
        if r["event"] == "FOMC":
            out.add(pd.Timestamp(r["date"]))
    return out


def design(close: pd.Series, pre: set, fomc: set) -> pd.DataFrame:
    """One row per trading day: return and the regressors of section 3."""
    idx = close.index
    df = pd.DataFrame({"r": close / close.shift(1) - 1.0}, index=idx)
    df["PRE"] = idx.isin(list(pre)).astype(float)
    per = idx.to_period("M")
    rank_from_end = pd.Series(1, index=idx).groupby(per).cumcount(ascending=False)
    df["EOM"] = (rank_from_end.to_numpy() < 5).astype(float)
    nxt = pd.Series(idx[1:].tolist() + [pd.NaT], index=idx)
    df["FOMC"] = [float(d in fomc or (pd.notna(n) and n in fomc)) for d, n in zip(idx, nxt)]
    df["FRI"] = (idx.dayofweek == 4).astype(float)
    return df.iloc[1:]


def fit(df, pre_col="PRE"):
    """r = c + d*PRE + e*EOM + g*FOMC + h*FRI, Newey-West (5 lags). A control
    that is all zero in the sample (e.g. no FOMC day in a sub-period) is
    dropped rather than left to make the design singular, and recorded."""
    names = ["c", "d", "EOM", "FOMC", "FRI"]
    cols = [np.ones(len(df)), df[pre_col].to_numpy(), df["EOM"].to_numpy(),
            df["FOMC"].to_numpy(), df["FRI"].to_numpy()]
    keep = [i for i, c in enumerate(cols) if i < 2 or np.ptp(c) > 0]
    X = np.column_stack([cols[i] for i in keep])
    b, se, t, n = C.ols_nw(df["r"].to_numpy(), X, NW_LAGS)
    return dict(d=float(b[1]), t=float(t[1]), se=float(se[1]), n=int(n),
                coef=dict(zip([names[i] for i in keep], b.tolist())),
                dropped=[names[i] for i in range(5) if i not in keep])


def placebo_days(P: pd.Series, idx: pd.DatetimeIndex) -> set:
    s = set(idx)
    return {p - pd.Timedelta(days=7) for p in P if (p - pd.Timedelta(days=7)) in s}


def trade(ba15: pd.DataFrame, td: pd.DatetimeIndex, P) -> dict:
    """G5. Buy at the ask OPEN of the first 15-min bar of trading date P (just
    after the 17:00 NY rollover), sell at the bid CLOSE of its last bar (just
    before the next rollover). Crosses no rollover: no financing."""
    bars = ba15[td == P]
    if len(bars) < 4:
        return None
    return dict(P=P, net=bars["close_b"].iloc[-1] / bars["open_a"].iloc[0] - 1.0,
                gross=bars["close_m"].iloc[-1] / bars["open_m"].iloc[0] - 1.0,
                first_bar=str(bars.index[0]), last_bar=str(bars.index[-1]))


def run() -> int:
    buf = io.StringIO()
    def say(*a):
        s = " ".join(str(x) for x in a); print(s); buf.write(s + "\n")
    pin = C.check_pin(NAME); ev = load_events()
    say(f"FLOWS-2 refunding.py  run {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}")
    say(f"  {NAME} sha256 {pin[:16]}... and event table {C.PINS['EVENTS'][:16]}... match")
    fomc = fomc_dates()
    ba = C.load_bidask(BD); dly = C.daily(ba); dly = dly[dly.index >= START]
    ev = ev[ev["P"] <= C.END]
    have = ev["P"].isin(dly.index)
    say(f"  events: {len(ev)} with P <= {C.END.date()}; {int(have.sum())} have a bond bar on P; "
        f"dropped {ev.loc[~have, 'quarter'].tolist() or 'none'}")
    ev = ev[have]
    df = design(dly["close_m"], set(ev["P"]), fomc)
    res = {"pin": pin, "events_used": len(ev)}
    g1 = df[df.index <= G1_END]
    res["G1"] = fit(g1)
    res["full"] = fit(df)
    res["G2"] = {e: fit(df[[C.era_of(d) == e for d in df.index]]) for e, _, _ in C.ERAS}
    post_P = ev.loc[ev["T"] >= POST, "P"]
    m, t, n = C.mean_t(df.loc[df.index.isin(post_P), "r"]); res["G3"] = dict(mean=m, t=t, n=n)
    pl = placebo_days(ev["P"], dly.index)
    g1p = g1.copy(); g1p["PRE_pl"] = g1p.index.isin(list(pl)).astype(float)
    res["G4"] = fit(g1p, "PRE_pl")
    td = C.trading_date(ba.index)
    trs = [x for x in (trade(ba, td, p) for p in ev["P"]) if x]
    tr = pd.DataFrame(trs); tr.to_csv(os.path.join(C.FDATA, "refunding_trades.csv"), index=False)
    g5 = {}
    for col in ("gross", "net"):
        m, t, n = C.mean_t(tr[col]); g5[col] = dict(mean=m, t=t, n=n)
    for bp in (1, 3):
        m, t, n = C.mean_t(tr["net"] - 2 * bp / 1e4); g5[f"net_stress_{bp}bp"] = dict(mean=m, t=t, n=n)
    snap = C.load_snapshot()
    g5["days_charged_evidence"] = snap["instruments"][BD]["daysCharged"]
    g5["note"] = "entry after the 17:00 rollover, exit before the next: no rollover crossed"
    res["G5"] = g5
    fo = ev.set_index("P")["fomc_in_prior_week"].astype(str) == "True"
    rP = df.loc[df.index.isin(ev["P"]), "r"]
    fomc_mask = rP.index.map(fo).to_numpy(dtype=bool)
    res["G6"] = dict(with_fomc=dict(zip(("mean", "t", "n"), C.mean_t(rP[fomc_mask]))),
                     without_fomc=dict(zip(("mean", "t", "n"), C.mean_t(rP[~fomc_mask]))))
    sec = {}
    for inst in SECONDARY:
        d2 = C.daily(C.load_bidask(inst)); d2 = d2[d2.index >= START]
        e2 = ev[ev["P"].isin(d2.index)]
        sec[inst] = fit(design(d2["close_m"], set(e2["P"]), fomc))
    res["secondary_full_sample"] = sec
    mon = []
    for r in ev.itertuples():
        t_ny = pd.Timestamp(r.T.date(), tz=C.NY) + pd.Timedelta(hours=14, minutes=45)
        bar = ba.index[ba.index == t_ny.tz_convert("UTC")]
        if len(bar) and r.P in dly.index:
            mon.append(ba.at[bar[0], "close_m"] / dly.at[r.P, "close_m"] - 1.0)
    res["monday_to_1500_descriptive"] = dict(zip(("mean", "t", "n"), C.mean_t(mon)))

    gates = {"G1": res["G1"]["d"] > 0 and res["G1"]["t"] >= 2.0,
             "G2": all(res["G2"][e]["d"] > 0 for e in res["G2"]),
             "G3": res["G3"]["mean"] > 0,
             "G4": res["G4"]["t"] < 2.0 and res["G4"]["d"] < res["G1"]["d"],
             "G5": g5["net"]["mean"] > 0,
             "G6_sign": res["G6"]["with_fomc"]["mean"] > res["G6"]["without_fomc"]["mean"]}
    pv = {"G1": C.p_two_sided(res["G1"]["t"]), "G4": C.p_two_sided(res["G4"]["t"])}
    kills = {"K1_G1_fails": not gates["G1"],
             "K2_placebo_as_large": res["G4"]["d"] >= res["G1"]["d"] or res["G4"]["t"] >= 2.0,
             "K3_net_not_positive": not gates["G5"]}
    res.update(pvalues=pv, bh_q=C.bh(pv), gates=gates, kills=kills,
               verdict="DEAD" if any(kills.values()) else ("ALL GATES PASS" if all(gates.values()) else "SURVIVES KILLS, SOME GATES FAIL"))
    say(f"\n  G1 (2005-2023)  d {res['G1']['d']*1e4:+.2f} bp  t {res['G1']['t']:+.2f}  n {res['G1']['n']}")
    say(f"  full sample     d {res['full']['d']*1e4:+.2f} bp  t {res['full']['t']:+.2f}")
    for e in res["G2"]:
        say(f"  G2 {e}           d {res['G2'][e]['d']*1e4:+.2f} bp  t {res['G2'][e]['t']:+.2f}")
    say(f"  G3 post-paper   mean {res['G3']['mean']*1e4:+.2f} bp  n {res['G3']['n']}")
    say(f"  G4 placebo      d {res['G4']['d']*1e4:+.2f} bp  t {res['G4']['t']:+.2f}")
    say(f"  G5 trade        net {g5['net']['mean']*1e4:+.2f} bp (t {g5['net']['t']:+.2f}, n {g5['net']['n']}), "
        f"stress 3bp {g5['net_stress_3bp']['mean']*1e4:+.2f} bp")
    say(f"  G6 FOMC before  {res['G6']['with_fomc']['mean']*1e4:+.2f} bp vs {res['G6']['without_fomc']['mean']*1e4:+.2f} bp")
    for k, v in sec.items():
        say(f"  secondary {k}  d {v['d']*1e4:+.2f} bp  t {v['t']:+.2f}")
    say(f"  BH q: {res['bh_q']}\n  gates: {gates}\n  kills: {kills}\n  VERDICT: {res['verdict']}")
    json.dump(res, open(os.path.join(C.FDATA, "refunding_result.json"), "w"), indent=2, default=str)
    open(LOG, "w").write(buf.getvalue())
    return 0


def check_inputs() -> int:
    print(f"  {NAME} sha256 {C.check_pin(NAME)[:16]}... matches")
    ev = load_events()
    print(f"  event table {C.PINS['EVENTS'][:16]}... matches; {len(ev)} rows, all OK")
    dly = C.daily(C.load_bidask(BD)); dly = dly[dly.index >= START]
    ev = ev[ev["P"] <= C.END]; have = ev["P"].isin(dly.index)
    print(f"  {BD}: {len(dly)} trading days {dly.index[0].date()} .. {dly.index[-1].date()}")
    print(f"  events with P <= {C.END.date()}: {len(ev)}; P has a bond bar: {int(have.sum())}; "
          f"replication (T <= 2023): {int((ev['T'] <= G1_END).sum())}; post-paper: {int((ev['T'] >= POST).sum())}")
    print(f"  missing P bars: {ev.loc[~have, ['quarter', 'P']].to_dict('records') or 'none'}")
    print(f"  FOMC dates on file: {len(fomc_dates())}")
    return 0


def self_test() -> int:
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    days = pd.bdate_range("2005-01-03", "2026-08-31")
    P = [d for d in days if d.month in (1, 4, 7, 10) and d.dayofweek == 4 and d.day >= 24][::1]
    P = sorted({max(x for x in P if x.to_period("M") == m) for m in pd.PeriodIndex(P, freq="M").unique()})
    rng = np.random.default_rng(3)
    base = rng.normal(0, 0.004, len(days))
    def close(r): return pd.Series(100 * np.cumprod(1 + r), index=days)
    r1 = base.copy(); r1[days.isin(P)] += 0.0030   # 30bp: machinery check, not a power claim
    df = design(close(r1), set(P), set())
    f = fit(df)
    check(f"planted +30bp on P recovered (d {f['d']*1e4:+.1f}bp, t {f['t']:+.1f})", abs(f["d"] - 0.003) < 0.0012 and f["t"] > 2)
    check("regressors: EOM = last five days of each month", int(df["EOM"].groupby(df.index.to_period("M")).sum().median()) == 5)
    r2 = base.copy(); r2[days.dayofweek == 4] += 0.0015
    f2 = fit(design(close(r2), set(P), set()))
    check(f"a pure Friday effect is NOT credited to P (d {f2['d']*1e4:+.1f}bp, t {f2['t']:+.1f})", abs(f2["t"]) < 2)
    pl = placebo_days(pd.Series(P), days)
    check("placebo = same weekday one week earlier", all((p + pd.Timedelta(days=7)) in set(P) for p in pl) and len(pl) > 0.9 * len(P))
    d3 = design(close(r1), set(P), set()); d3["PRE_pl"] = d3.index.isin(list(pl)).astype(float)
    fp = fit(d3, "PRE_pl")
    check(f"placebo finds nothing when the effect is on P (t {fp['t']:+.1f})", abs(fp["t"]) < 2)
    idx = pd.date_range("2025-07-30 21:00", "2025-08-01 21:00", freq="15min", tz="UTC", inclusive="left")
    ba = pd.DataFrame({"open_a": 100.02, "open_m": 100.0, "close_b": 100.18, "close_m": 100.2}, index=idx)
    td = C.trading_date(ba.index)
    tr = trade(ba, td, pd.Timestamp("2025-08-01"))
    check("trade window = trading date P: first bar after Thu 17:00 NY, last before Fri 17:00 NY",
          tr["first_bar"] == "2025-07-31 21:00:00+00:00" and tr["last_bar"] == "2025-08-01 20:45:00+00:00")
    check("fills: ask in, bid out", abs(tr["net"] - (100.18 / 100.02 - 1)) < 1e-12)
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test", action="store_true"); g.add_argument("--check-inputs", action="store_true")
    g.add_argument("--run", action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else check_inputs() if a.check_inputs else run())
