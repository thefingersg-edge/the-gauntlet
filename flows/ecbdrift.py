#!/usr/bin/env python3
"""
ecbdrift.py -- FLOWS-5: the 20-day DE30 drift after ECB decisions.
Implements flows/PREREGISTRATION_ECBDRIFT.md; refuses to run if that file or
the frozen decision table has changed.

    python3 ecbdrift.py --self-test      synthetic data only
    python3 ecbdrift.py --check-inputs   files, hashes, bar coverage -- NO returns
    python3 ecbdrift.py --run            the registered test, once
"""
from __future__ import annotations
import argparse, io, json, os, sys
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import common as C

NAME = "ECBDRIFT"
EQ, BUND = "DE30_EUR", "DE10YB_EUR"
BER = ZoneInfo("Europe/Berlin")
H, WIN_MIN = 20, 120
LOG = os.path.join(C.FDATA, "ecbdrift_run.log")
RES = os.path.join(C.FDATA, "ecbdrift_result.json")
TRADES = os.path.join(C.FDATA, "ecbdrift_trades.csv")


def load_events() -> pd.DataFrame:
    C.check_pin("ECB_EVENTS")
    ev = pd.read_csv(os.path.join(C.FDATA, "ecb_events.csv"), parse_dates=["date"])
    return ev[ev["scheduled"] == 1].reset_index(drop=True)


def tau_utc(date: pd.Timestamp, hhmm: str) -> pd.Timestamp:
    h, m = map(int, hhmm.split(":"))
    return pd.Timestamp(date.year, date.month, date.day, h, m, tz=BER).tz_convert("UTC")


def reaction(ba: pd.DataFrame, tau: pd.Timestamp):
    """Mid close of the bar ENDING at tau -> mid close of the bar ending at
    tau + 120 min. Bars are stamped by their START."""
    b0, b1 = tau - pd.Timedelta(minutes=15), tau + pd.Timedelta(minutes=WIN_MIN - 15)
    if b0 not in ba.index or b1 not in ba.index:
        return np.nan
    return float(ba.at[b1, "close_m"] / ba.at[b0, "close_m"] - 1.0)


def build(ev, ba, dly, bund=None, shift_days: int = 0) -> pd.DataFrame:
    """One row per event: shock sign, class, D, signed drifts, trade legs."""
    dates = dly.index
    rows = []
    for _, e in ev.iterrows():
        d0 = e["date"] - pd.Timedelta(days=shift_days)
        tau = tau_utc(d0, e["time_cet"])
        x = reaction(ba, tau)
        row = dict(event=e["date"].date().isoformat(), anchor=d0.date().isoformat(), react=x)
        D = C.trading_date(pd.DatetimeIndex([tau]))[0]
        if not np.isfinite(x) or x == 0 or D not in dates:
            row["drop"] = "no reaction" if not np.isfinite(x) or x == 0 else "D not a trading date"
            rows.append(row); continue
        p = dates.get_loc(D)
        if p + H >= len(dates):
            row["drop"] = "D+20 beyond sample"; rows.append(row); continue
        s = 1.0 if x > 0 else -1.0
        row.update(s=s, D=D.date().isoformat(), D20=dates[p + H].date().isoformat())
        for k in (5, 10, H):
            row[f"R{k}"] = float(dly["close_m"].iloc[p + k] / dly["close_m"].iloc[p] - 1)
            row[f"y{k}"] = s * row[f"R{k}"]
        if bund is not None:
            xb = reaction(bund, tau)
            row["bund"] = xb
            row["info"] = (np.sign(xb) != np.sign(x)) if np.isfinite(xb) and xb != 0 else np.nan
        row["entry_a"], row["entry_b"] = float(dly["close_a"].iloc[p]), float(dly["close_b"].iloc[p])
        row["exit_a"], row["exit_b"] = float(dly["close_a"].iloc[p + H]), float(dly["close_b"].iloc[p + H])
        row["rolls"] = [dates[p + i] for i in range(H)]       # rollovers at the end of D .. D+19
        rows.append(row)
    return pd.DataFrame(rows)


def trade_net(t: pd.DataFrame, fin, cost_bp: float = 0.0) -> pd.Series:
    k = cost_bp * 1e-4
    out = []
    for _, r in t.iterrows():
        if r["s"] > 0:
            g = (r["exit_b"] * (1 - k)) / (r["entry_a"] * (1 + k)) - 1.0
            f = fin.charge(r["rolls"], "long") if fin else 0.0
        else:
            g = 1.0 - (r["exit_a"] * (1 + k)) / (r["entry_b"] * (1 - k))
            f = fin.charge(r["rolls"], "short") if fin else 0.0
        out.append(g + f)
    return pd.Series(out, index=t.index)


def nw_mean(y, lags=1):
    y = np.asarray(y, float); y = y[np.isfinite(y)]
    b, se, t, n = C.ols_nw(y, np.ones((len(y), 1)), lags)
    return float(b[0]), float(t[0]), int(n)


def run() -> int:
    buf = io.StringIO()
    def say(*a):
        print(*a); print(*a, file=buf)
    pin, tpin = C.check_pin(NAME), C.check_pin("ECB_EVENTS")
    ev = load_events()
    say(f"FLOWS-5 ECBDRIFT  prereg {pin[:16]}  decisions {tpin[:16]}  ({len(ev)} scheduled)")
    ba, bund = C.load_bidask(EQ), C.load_bidask(BUND)
    dly = C.daily(ba, min_bars=4)
    t = build(ev, ba, dly, bund)
    ok = t[t.get("drop").isna()] if "drop" in t else t
    say(f"  used {len(ok)}; dropped {t['drop'].value_counts().to_dict() if 'drop' in t else {}}")
    m, tt, n = nw_mean(ok["y20"])
    res = {"pin": pin, "events_sha": tpin, "n": n, "mean": m, "t": tt}
    say(f"\n  G1 mean signed 20-day drift {m*1e4:+.1f} bp  t {tt:+.2f}  n {n}")
    eras = {}
    for e, a, b in C.ERAS:
        sub = ok[(pd.to_datetime(ok["event"]) >= a) & (pd.to_datetime(ok["event"]) <= b)]
        eras[e] = dict(zip(("mean", "t", "n"), nw_mean(sub["y20"])))
        say(f"  {e}: {eras[e]['mean']*1e4:+.1f} bp t {eras[e]['t']:+.2f} n {eras[e]['n']}")
    res["eras"] = eras
    snap = C.load_snapshot()
    fin = C.Financing(EQ, snap, C.load_fred("ECBDFR"))
    net = trade_net(ok, fin); net1 = trade_net(ok, fin, 1.0); gross = trade_net(ok, None)
    mn, tn, nn = nw_mean(net)
    e3 = net[pd.to_datetime(ok["event"]) >= pd.Timestamp(C.ERAS[2][1])]
    say(f"\n  G3 trade: gross (fills, no financing) {gross.mean()*1e4:+.1f} bp; NET {mn*1e4:+.1f} bp t {tn:+.2f}; "
        f"+1bp/side {net1.mean()*1e4:+.1f}; E3 net {e3.mean()*1e4:+.1f} bp (n {len(e3)})")
    res["trade"] = dict(gross=float(gross.mean()), net=mn, t=tn, net_stress=float(net1.mean()),
                        e3_net=float(e3.mean()), e3_n=int(len(e3)), financing=float((net - gross).mean()))
    out = ok.drop(columns=["rolls"]).assign(net=net.to_numpy())
    out.to_csv(TRADES, index=False)
    tp = build(ev, ba, dly, None, shift_days=7)
    okp = tp[tp["drop"].isna()] if "drop" in tp else tp
    mp, tp_, np_ = nw_mean(okp["y20"])
    say(f"  G4 placebo (Thursday a week before): {mp*1e4:+.1f} bp t {tp_:+.2f} n {np_}")
    res["placebo"] = dict(mean=mp, t=tp_, n=np_)
    G = {"G1": m > 0 and tt >= 2.0,
         "G2": all(eras[e]["mean"] > 0 for e in eras) and eras["E3"]["mean"] >= 0.5 * m,
         "G3": mn > 0 and tn >= 1.65 and e3.mean() > 0,
         "G4": tp_ < 2.0 and mp < m,
         "G5": n >= 150}
    q = C.bh({"G1": C.p_two_sided(tt), "G4": C.p_two_sided(tp_)})
    res["gates"], res["bh_q"] = G, q
    say("\n  " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in G.items()) + f"   BH q(G1) {q['G1']:.3f}")
    kill = [k for k, g in (("K1", "G1"), ("K2", "G2"), ("K3", "G3"), ("K4", "G4")) if not G[g]]
    res["verdict"] = "DEAD " + ",".join(kill) if kill else ("PASS" if G["G5"] else "PASS but G5 short")
    say(f"  VERDICT: {res['verdict']}")
    say("\n  secondary (descriptive):")
    sec = {}
    for lab, mask in (("information", ok["info"] == True), ("monetary", ok["info"] == False)):  # noqa: E712
        sec[lab] = dict(zip(("mean", "t", "n"), nw_mean(ok.loc[mask, "y20"])))
        say(f"    {lab:11s} shocks: {sec[lab]['mean']*1e4:+.1f} bp t {sec[lab]['t']:+.2f} n {sec[lab]['n']}")
    for k in (5, 10):
        sec[f"y{k}"] = dict(zip(("mean", "t", "n"), nw_mean(ok[f"y{k}"])))
        say(f"    signed drift {k:2d} days: {sec[f'y{k}']['mean']*1e4:+.1f} bp t {sec[f'y{k}']['t']:+.2f}")
    for lab, sgn in (("after positive", 1), ("after negative", -1)):
        r = ok.loc[ok["s"] == sgn, "R20"]
        sec[lab] = dict(mean=float(r.mean()), n=int(len(r)))
        say(f"    unsigned R20 {lab}: {r.mean()*1e4:+.1f} bp (n {len(r)})")
    # the paper's long-or-flat rule vs buy-and-hold, over the event span
    rd = dly["close_m"].pct_change()
    span = rd[(rd.index > pd.Timestamp(ok["D"].iloc[0])) & (rd.index <= pd.Timestamp(ok["D20"].iloc[-1]))]
    flat = pd.Series(False, index=span.index)
    for _, r in ok[ok["s"] < 0].iterrows():
        flat |= (span.index > pd.Timestamp(r["D"])) & (span.index <= pd.Timestamp(r["D20"]))
    yrs = len(span) / 252.0
    finl = pd.Series([fin.charge([d], "long") for d in span.index], index=span.index)
    bh_ann = float((1 + span + finl.shift(1).fillna(0)).prod() ** (1 / yrs) - 1)
    lf = span.where(~flat, 0.0) + finl.shift(1).fillna(0).where(~flat.shift(1, fill_value=False), 0.0)
    lf_ann = float((1 + lf).prod() ** (1 / yrs) - 1)
    sec["long_or_flat"] = dict(ann=lf_ann, buy_hold_ann=bh_ann, share_flat=float(flat.mean()))
    say(f"    long-or-flat rule {lf_ann*100:+.2f}%/yr vs buy-and-hold {bh_ann*100:+.2f}%/yr, both net of "
        f"long financing (flat {flat.mean()*100:.0f}% of days)")
    res["secondary"] = sec
    open(LOG, "w").write(buf.getvalue())
    json.dump(res, open(RES, "w"), indent=1, default=float)
    say(f"\n  log {os.path.basename(LOG)}  result {os.path.basename(RES)}  trades {os.path.basename(TRADES)}")
    return 0


def check_inputs() -> int:
    print(f"prereg pin: {C.check_pin(NAME)[:16]} OK")
    ev = load_events()
    print(f"decision table pinned OK: {len(ev)} scheduled, {ev['date'].min().date()}..{ev['date'].max().date()}")
    print("  per year: " + " ".join(f"{y}:{c}" for y, c in ev["date"].dt.year.value_counts().sort_index().items()))
    ba, bund = C.load_bidask(EQ), C.load_bidask(BUND)
    miss = []
    for _, e in ev.iterrows():
        tau = tau_utc(e["date"], e["time_cet"])
        for inst, d in ((EQ, ba), (BUND, bund)):
            for b in (tau - pd.Timedelta(minutes=15), tau + pd.Timedelta(minutes=WIN_MIN - 15)):
                if b not in d.index:
                    miss.append(f"{inst} {e['date'].date()} {b}")
    print(f"window bars missing: {len(miss)}  {miss[:10]}")
    print(f"financing snapshot has {EQ}: {EQ in C.load_snapshot()['instruments']}")
    return 0


def self_test() -> int:
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    check("13:45 CET in winter = 12:45 UTC", tau_utc(pd.Timestamp("2021-01-21"), "13:45") == pd.Timestamp("2021-01-21 12:45", tz="UTC"))
    check("14:15 CEST in summer = 12:15 UTC", tau_utc(pd.Timestamp("2022-07-21"), "14:15") == pd.Timestamp("2022-07-21 12:15", tz="UTC"))
    idx = pd.date_range("2019-01-01", "2020-12-31 23:45", freq="15min", tz="UTC")
    idx = idx[idx.dayofweek < 5]
    rng = np.random.default_rng(5)
    px = 100 * np.exp(np.cumsum(rng.normal(0, 0.0008, len(idx))))
    ba = pd.DataFrame({"close_m": px}, index=idx)
    ba["close_a"], ba["close_b"] = ba["close_m"] + 0.01, ba["close_m"] - 0.01
    ba["open_m"], ba["open_a"], ba["open_b"] = ba["close_m"], ba["close_a"], ba["close_b"]
    thu = [d for d in pd.bdate_range("2019-02-01", "2020-10-31") if d.dayofweek == 3][::6]   # 6 weeks apart: windows do not overlap
    ev = pd.DataFrame({"date": thu, "time_cet": "13:45", "scheduled": 1})
    # plant: a +0.5% jump in the reaction window and a +3% drift over the next 20 trading dates
    for d in thu:
        tau = tau_utc(d, "13:45")
        j = ba.index.get_indexer([tau + pd.Timedelta(minutes=30)])[0]
        ba.iloc[j:, ba.columns.get_indexer(["close_m", "close_a", "close_b", "open_m", "open_a", "open_b"])] *= 1.005
    dly = C.daily(ba, 4)
    for d in thu:
        D = C.trading_date(pd.DatetimeIndex([tau_utc(d, "13:45")]))[0]
        p = dly.index.get_loc(D)
        seg = (ba.index > pd.Timestamp(dly["last_bar"].iloc[p])) & (ba.index <= pd.Timestamp(dly["last_bar"].iloc[p + H]))
        ramp = np.cumsum(seg) / max(seg.sum(), 1) * 0.03
        ba.loc[:, ["close_m", "close_a", "close_b"]] = ba[["close_m", "close_a", "close_b"]].mul(1 + np.where(seg, ramp, np.where(ba.index > pd.Timestamp(dly["last_bar"].iloc[p + H]), 0.03, 0)), axis=0)
    dly = C.daily(ba, 4)
    t = build(ev, ba, dly, None)
    okk = t[t["drop"].isna()] if "drop" in t else t
    check("reaction sign found positive on every planted event", (okk["s"] > 0).all() and len(okk) >= 0.8 * len(thu))
    m, tt, n = nw_mean(okk["y20"])
    check(f"planted +3% drift recovered ({m*1e4:+.0f} bp, t {tt:+.1f})", 0.02 < m < 0.045 and tt > 2)
    r0 = okk.iloc[0]
    check("D+20 is the 20th trading date after D",
          dly.index.get_loc(pd.Timestamp(r0["D20"])) - dly.index.get_loc(pd.Timestamp(r0["D"])) == 20)
    check("20 rollovers held: end of D .. end of D+19", len(r0["rolls"]) == 20 and r0["rolls"][0] == pd.Timestamp(r0["D"]))
    snap = {"fetched_utc": "2026-09-26T00:00:00", "instruments": {EQ: {"longRate": -0.05, "shortRate": 0.0,
            "daysCharged": {"FRIDAY": 3, "SATURDAY": 0, "SUNDAY": 0}}}}
    fin = C.Financing(EQ, snap, pd.Series([0.0], index=[pd.Timestamp("2000-01-01")]))
    one = okk.iloc[[0]].copy()
    g = trade_net(one, None).iloc[0]
    check("long fills: ask in, bid out", abs(g - (one["exit_b"].iloc[0] / one["entry_a"].iloc[0] - 1)) < 1e-12)
    f = trade_net(one, fin).iloc[0] - g
    nfri = sum(pd.Timestamp(d).dayofweek == 4 for d in one["rolls"].iloc[0])
    check("financing: 20 rollovers, Fridays x3", abs(f - (-0.05) * (20 + 2 * nfri) / 365) < 1e-12)
    sh = one.assign(s=-1.0)
    check("short fills: bid in, ask out", abs(trade_net(sh, None).iloc[0] - (1 - sh["exit_a"].iloc[0] / sh["entry_b"].iloc[0])) < 1e-12)
    tp = build(ev, ba, dly, None, shift_days=7)
    okp = tp[tp["drop"].isna()] if "drop" in tp else tp
    check("placebo anchors a week earlier", (pd.to_datetime(okp["anchor"]) == pd.to_datetime(okp["event"]) - pd.Timedelta(days=7)).all())
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test", action="store_true"); g.add_argument("--check-inputs", action="store_true")
    g.add_argument("--run", action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else check_inputs() if a.check_inputs else run())
