#!/usr/bin/env python3
"""
monthend.py -- FLOWS-1: month-end rebalancing, one flow, one test.
Implements flows/PREREGISTRATION_MONTHEND.md exactly; refuses to run if that
file's sha256 differs from the pin in common.py.

    python3 monthend.py --self-test      synthetic data only, planted effects
    python3 monthend.py --check-inputs   files, grids, coverage -- NO returns
    python3 monthend.py --run            the registered test, once

Writes data/monthend_run.log (tracked) and data/monthend_result.json.
"""
from __future__ import annotations
import argparse, datetime as dt, io, json, os, sys
import numpy as np
import pandas as pd
import common as C

NAME = "MONTHEND"
EQ, BD, EQ2, BD2 = "SPX500_USD", "USB10Y_USD", "DE30_EUR", "DE10YB_EUR"
START = pd.Timestamp("2005-01-01")
G1_END, HOLD_START = pd.Timestamp("2023-03-31"), pd.Timestamp("2023-04-01")
ROLL_TOL, DURATION, NW_LAGS = 0.0075, 8.5, 3
LOG = os.path.join(C.FDATA, "monthend_run.log")


# ------------------------------------------------------------------ structure
def month_table(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """One row per calendar month: D0 (last trading day of the previous
    month), D5 (day 5), D10 (day 10), Dm5 (D-5), D (last day), and N1..N5
    (first five trading days of the next month, for the reversal check).
    Trading days are the dates BOTH legs trade."""
    dates = pd.DatetimeIndex(sorted(dates))
    per = dates.to_period("M")
    rows = []
    months = per.unique()
    for i, m in enumerate(months):
        d = dates[per == m]
        if i == 0 or len(d) < 11:
            continue
        prev = dates[per == months[i - 1]]
        nxt = dates[per == months[i + 1]] if i + 1 < len(months) else pd.DatetimeIndex([])
        rows.append(dict(month=str(m), D0=prev[-1], D5=d[4], D10=d[9], Dm5=d[-6], D=d[-1],
                         W=list(d[-5:]), N5=(nxt[4] if len(nxt) >= 5 else pd.NaT),
                         Dm5_to_D=list(d[-6:-1])))
    return pd.DataFrame(rows)


def rel(eq: pd.Series, bd: pd.Series, a, b) -> tuple:
    """Equity, bond and equity-minus-bond return from close a to close b."""
    re, rb = eq[b] / eq[a] - 1.0, bd[b] / bd[a] - 1.0
    return re, rb, re - rb


def build(mt: pd.DataFrame, eq: pd.Series, bd: pd.Series) -> pd.DataFrame:
    out = []
    for r in mt.itertuples():
        E, B, S = rel(eq, bd, r.D0, r.Dm5)
        _, _, Y = rel(eq, bd, r.Dm5, r.D)
        _, _, Sp = rel(eq, bd, r.D0, r.D5)
        _, _, Yp = rel(eq, bd, r.D5, r.D10)
        Yr = rel(eq, bd, r.D, r.N5)[2] if pd.notna(r.N5) else np.nan
        out.append(dict(month=r.month, D=r.D, S=S, E=E, B=B, Y=Y, S_placebo=Sp,
                        Y_placebo=Yp, Y_reversal=Yr))
    return pd.DataFrame(out).set_index("month")


def fit(df, ycol, xcols):
    X = np.column_stack([np.ones(len(df))] + [df[c].to_numpy() for c in xcols])
    b, se, t, n = C.ols_nw(df[ycol].to_numpy(), X, NW_LAGS)
    return dict(coef=b.tolist(), se=se.tolist(), t=t.tolist(), n=int(n))


# ------------------------------------------------------------------ roll flags
def roll_flags(bdaily: pd.DataFrame, dgs10: pd.Series) -> pd.DataFrame:
    """Section 5: days where the bond CFD's return departs from the
    duration-implied return by more than 0.75%. Frozen before Y exists.
    dgs10 is a DECIMAL yield (common.load_fred divides FRED's percent by 100)."""
    c = bdaily["close_m"]
    r = c / c.shift(1) - 1.0
    y = dgs10.reindex(c.index, method="ffill")
    implied = -DURATION * (y - y.shift(1))
    gap = (r - implied).abs()
    f = pd.DataFrame({"cfd_ret": r, "implied_ret": implied, "gap": gap})
    return f[f["gap"] > ROLL_TOL]


# ------------------------------------------------------------------ trading rule
def trades(mt, _unused, fin_eq, fin_bd, eq_ba, bd_ba, S) -> pd.DataFrame:
    """G7. Enter at the close of D-5 when |S| beats the 67th percentile of all
    earlier |S| (>= 36 months of history); position -sign(S); exit at close D.
    Long legs buy at the ask and sell at the bid; short legs the reverse."""
    out, hist = [], []
    for r in mt.itertuples():
        s = S.get(r.month, np.nan)
        if not np.isfinite(s):
            continue
        take = len(hist) >= 36 and abs(s) > np.percentile(np.abs(hist), 67)
        hist.append(s)
        if not take:
            continue
        a, b = r.Dm5, r.D
        eq_long = s < 0                                # S<0: equities lagged -> buy equity, sell bond
        def leg(ba, long):
            if long:
                return ba.at[b, "close_b"] / ba.at[a, "close_a"] - 1.0
            return -(ba.at[b, "close_a"] / ba.at[a, "close_b"] - 1.0)
        def gross(ba, long):
            g = ba.at[b, "close_m"] / ba.at[a, "close_m"] - 1.0
            return g if long else -g
        roll = r.Dm5_to_D
        f_eq = fin_eq.charge(roll, "long" if eq_long else "short")
        f_bd = fin_bd.charge(roll, "short" if eq_long else "long")
        px = leg(eq_ba, eq_long) + leg(bd_ba, not eq_long)
        out.append(dict(month=r.month, D=r.D, S=s, side="long eq / short bond" if eq_long else "short eq / long bond",
                        gross_mid=gross(eq_ba, eq_long) + gross(bd_ba, not eq_long),
                        after_spread=px, financing=f_eq + f_bd, net=px + f_eq + f_bd))
    return pd.DataFrame(out)


# ------------------------------------------------------------------ run
def load_all():
    raw = {i: C.load_bidask(i) for i in (EQ, BD, EQ2, BD2)}
    dly = {i: C.daily(v) for i, v in raw.items()}
    for i in dly:
        dly[i] = dly[i][dly[i].index >= START]
    return dly


def run() -> int:
    buf = io.StringIO()
    def say(*a):
        s = " ".join(str(x) for x in a); print(s); buf.write(s + "\n")
    pin = C.check_pin(NAME)
    say(f"FLOWS-1 monthend.py  run {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}")
    say(f"  {NAME} sha256 {pin[:16]}... matches the frozen copy")
    dly = load_all()
    dgs10, dgs3m = C.load_fred("DGS10"), C.load_fred("DGS3MO")

    # --- section 5 first: roll flags, frozen before any Y is computed
    flags = roll_flags(dly[BD], dgs10)
    fpath = os.path.join(C.FDATA, "roll_flags_usb10y.csv")
    flags.to_csv(fpath)
    say(f"  roll flags: {len(flags)} days  -> {os.path.basename(fpath)} sha256 {C.sha256(fpath)[:16]}")

    common = dly[EQ].index.intersection(dly[BD].index)
    mt = month_table(common)
    eq, bd = dly[EQ]["close_m"], dly[BD]["close_m"]
    flagged = set(flags.index)
    mt["flagged"] = [any(d in flagged for d in w) for w in mt["W"]]
    allm = build(mt, eq, bd)
    fl_by_month = mt.set_index("month")["flagged"].astype(bool)
    prim = allm[~allm.index.map(fl_by_month).to_numpy(dtype=bool)]
    say(f"  months: {len(allm)} built, {len(allm) - len(prim)} excluded for a roll-flagged window, "
        f"{len(prim)} in the primary")

    res = {"pin": pin, "roll_flag_days": len(flags), "months_primary": len(prim)}
    Dcol = pd.to_datetime(prim["D"])
    g1 = prim[Dcol <= G1_END]; ho = prim[Dcol >= HOLD_START]
    res["primary_full"] = fit(prim, "Y", ["S"])
    res["G1"] = fit(g1, "Y", ["S"])
    res["G2"] = {e: fit(prim[[C.era_of(d) == e for d in Dcol]], "Y", ["S"]) for e, _, _ in C.ERAS}
    res["G3"] = fit(ho, "Y", ["S"])
    res["G4"] = fit(prim, "Y", ["E", "B"])
    res["G5"] = fit(prim, "Y_placebo", ["S_placebo"])
    res["G6"] = fit(prim.dropna(subset=["Y_reversal"]), "Y_reversal", ["S"])

    # robustness -- reported, never selected among
    res["R2_include_flagged"] = fit(allm, "Y", ["S"])
    y = dgs10
    def imp(a, b):
        return -DURATION * (y.asof(b) - y.asof(a))
    r3 = []
    for r in mt[~mt["flagged"]].itertuples():
        S = (eq[r.Dm5] / eq[r.D0] - 1) - imp(r.D0, r.Dm5)
        Y = (eq[r.D] / eq[r.Dm5] - 1) - imp(r.Dm5, r.D)
        r3.append(dict(S=S, Y=Y))
    res["R3_dgs10_bond_leg"] = fit(pd.DataFrame(r3), "Y", ["S"])
    rets = {k: dly[k]["close_m"].pct_change() for k in (EQ, BD)}
    vol = {k: v.rolling(63, min_periods=50).std() for k, v in rets.items()}
    r1 = []
    for r in mt[~mt["flagged"]].itertuples():
        se, sb = vol[EQ].get(r.Dm5, np.nan), vol[BD].get(r.Dm5, np.nan)
        S = (eq[r.Dm5] / eq[r.D0] - 1) / se - (bd[r.Dm5] / bd[r.D0] - 1) / sb
        Y = (eq[r.D] / eq[r.Dm5] - 1) / se - (bd[r.D] / bd[r.Dm5] - 1) / sb
        r1.append(dict(S=S, Y=Y))
    res["R1_vol_scaled"] = fit(pd.DataFrame(r1).dropna(), "Y", ["S"])

    # G8 -- independent market, no roll handling (no daily German yield on file)
    c2 = dly[EQ2].index.intersection(dly[BD2].index)
    res["G8_DE30_DE10YB"] = fit(build(month_table(c2), dly[EQ2]["close_m"], dly[BD2]["close_m"]), "Y", ["S"])

    # quarter-end months, descriptive only
    qe = prim[[m[-2:] in ("03", "06", "09", "12") for m in prim.index]]
    res["quarter_end_descriptive"] = fit(qe, "Y", ["S"])

    # G7 -- trading rule, net of spreads and financing
    snap = C.load_snapshot()
    fin_eq = C.Financing(EQ, snap, dgs3m)
    fin_bd = C.Financing(BD, snap, dgs3m, dgs10)
    tr = trades(mt[~mt["flagged"]], None, fin_eq, fin_bd, dly[EQ], dly[BD], prim["S"])
    tpath = os.path.join(C.FDATA, "monthend_trades.csv"); tr.to_csv(tpath, index=False)
    trD = pd.to_datetime(tr["D"])
    g7 = {"trades": len(tr)}
    for lab, sub in (("full", tr), ("holdout", tr[trD >= HOLD_START])):
        for col in ("gross_mid", "after_spread", "net"):
            m, t, n = C.mean_t(sub[col]); g7[f"{lab}_{col}"] = dict(mean=m, t=t, n=n)
        for bp in (1, 3):
            m, t, n = C.mean_t(sub["net"] - 4 * bp / 1e4); g7[f"{lab}_net_stress_{bp}bp"] = dict(mean=m, t=t, n=n)
    res["G7"] = g7

    # gates
    b = lambda f, i=1: f["coef"][i]
    t = lambda f, i=1: f["t"][i]
    gates = {
        "G1": b(res["G1"]) < 0 and t(res["G1"]) <= -2.0,
        "G2": all(b(res["G2"][e]) < 0 for e in res["G2"]),
        "G3": b(res["G3"]) < 0,
        "G4": b(res["G4"], 1) < 0 and b(res["G4"], 2) > 0,
        "G5": t(res["G5"]) > -2.0 and abs(b(res["G5"])) < abs(b(res["primary_full"])),
        "G6_support": b(res["G6"]) > 0,
        "G7": g7["full_net"]["mean"] > 0 and g7["holdout_net"]["mean"] > 0,
        "G8_confirmatory": b(res["G8_DE30_DE10YB"]) < 0,
    }
    pv = {"G1": C.p_two_sided(t(res["G1"])), "G4_b1": C.p_two_sided(t(res["G4"], 1)),
          "G4_b2": C.p_two_sided(t(res["G4"], 2)), "G5": C.p_two_sided(t(res["G5"]))}
    res["pvalues"], res["bh_q"], res["gates"] = pv, C.bh(pv), gates
    kills = {"K1_G1_fails": not gates["G1"], "K2_momentum_not_rebalancing": b(res["G4"], 1) > 0,
             "K3_era_sign_flip": any(b(res["G2"][e]) > 0 for e in res["G2"]), "K4_net_not_positive": not gates["G7"]}
    res["kills"] = kills
    res["verdict"] = "DEAD" if any(kills.values()) else ("ALL GATES PASS" if all(v for k, v in gates.items()) else "SURVIVES KILLS, SOME GATES FAIL")

    say("\n  gate                         b         t      n")
    for k in ("primary_full", "G1", "G3", "G4", "G5", "G6", "R1_vol_scaled", "R2_include_flagged",
              "R3_dgs10_bond_leg", "G8_DE30_DE10YB", "quarter_end_descriptive"):
        f = res[k]
        say(f"  {k:<26} {b(f):+.5f} {t(f):+7.2f} {f['n']:>5}" + (f"   b2 {b(f,2):+.5f} t {t(f,2):+.2f}" if k == "G4" else ""))
    for e in res["G2"]:
        say(f"  G2 {e:<23} {b(res['G2'][e]):+.5f} {t(res['G2'][e]):+7.2f} {res['G2'][e]['n']:>5}")
    say(f"\n  G7 trades {g7['trades']}: full net {g7['full_net']['mean']*1e4:+.1f} bp (t {g7['full_net']['t']:+.2f}), "
        f"holdout net {g7['holdout_net']['mean']*1e4:+.1f} bp, stress 3bp {g7['full_net_stress_3bp']['mean']*1e4:+.1f} bp")
    say(f"  BH q: {', '.join(f'{k} {v:.3f}' for k, v in res['bh_q'].items())}")
    say(f"  gates: {gates}")
    say(f"  kills: {kills}")
    say(f"  VERDICT: {res['verdict']}")
    json.dump(res, open(os.path.join(C.FDATA, "monthend_result.json"), "w"), indent=2, default=str)
    open(LOG, "w").write(buf.getvalue())
    return 0


def check_inputs() -> int:
    """Files, hashes, grids and coverage. Computes no return of any kind."""
    print(f"  {NAME} sha256 {C.check_pin(NAME)[:16]}... matches")
    dly = load_all()
    for i, d in dly.items():
        print(f"  {i:<11} {len(d):>5} trading days  {d.index[0].date()} .. {d.index[-1].date()}")
    common = dly[EQ].index.intersection(dly[BD].index)
    mt = month_table(common)
    print(f"  primary pair: {len(common)} common days, {len(mt)} usable months "
          f"({(pd.to_datetime(mt['D']) <= G1_END).sum()} replication, {(pd.to_datetime(mt['D']) >= HOLD_START).sum()} holdout)")
    snap = C.load_snapshot()
    print(f"  financing snapshot {snap['fetched_utc']}: {', '.join(sorted(snap['instruments']))}")
    for s in ("DGS10", "DGS3MO"):
        f = C.load_fred(s); print(f"  FRED {s}: {f.index[0].date()} .. {f.index[-1].date()}")
    return 0


def self_test() -> int:
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    days = pd.bdate_range("2005-01-03", "2026-08-31")
    mt = month_table(days)
    r = mt.iloc[10]; d = days[days.to_period("M") == pd.Period(r.month)]
    check("D = last day, D-5 = sixth from last, window = last five",
          r.D == d[-1] and r.Dm5 == d[-6] and r.W == list(d[-5:]))
    check("D0 = last trading day of the previous month", r.D0 == days[days < d[0]][-1])
    check("placebo days 5 and 10; reversal = 5th day of next month",
          r.D5 == d[4] and r.D10 == d[9] and r.N5 == days[days > d[-1]][4])
    check("rollovers held = D-5 .. D-1 (five)", r.Dm5_to_D == list(d[-6:-1]))
    def synth(k, seed):
        rng = np.random.default_rng(seed)
        re = pd.Series(rng.normal(0, 0.01, len(days)), days); rb = pd.Series(rng.normal(0, 0.004, len(days)), days)
        for row in mt.itertuples():
            eqc = (1 + re[(days > row.D0) & (days <= row.Dm5)]).prod() - 1
            bdc = (1 + rb[(days > row.D0) & (days <= row.Dm5)]).prod() - 1
            re[row.W] += -k * (eqc - bdc) / 5
        return (1 + re).cumprod() * 100, (1 + rb).cumprod() * 100
    eq, bd = synth(0.5, 7)
    f = fit(build(mt, eq, bd), "Y", ["S"])
    check(f"planted reversal recovered (b {f['coef'][1]:+.3f}, t {f['t'][1]:+.1f})", f["coef"][1] < -0.3 and f["t"][1] < -2)
    g4 = fit(build(mt, eq, bd), "Y", ["E", "B"])
    check("planted rebalancing gives b1<0 and b2>0 (G4 shape)", g4["coef"][1] < 0 and g4["coef"][2] > 0)
    fp = fit(build(mt, eq, bd), "Y_placebo", ["S_placebo"])
    check(f"placebo window finds nothing (t {fp['t'][1]:+.1f})", abs(fp["t"][1]) < 2)
    eq0, bd0 = synth(0.0, 11)
    f0 = fit(build(mt, eq0, bd0), "Y", ["S"])
    check(f"no effect planted -> no effect found (t {f0['t'][1]:+.1f})", abs(f0["t"][1]) < 2)
    # roll flags
    bdl = pd.DataFrame({"close_m": [100.0, 100.1, 102.0, 102.1]}, index=days[:4])
    y = pd.Series([0.0400, 0.0399, 0.0398, 0.0397], index=days[:4])   # decimal, as load_fred gives
    fl = roll_flags(bdl, y)
    check("roll flag fires on a 1.9% jump the yield does not explain", list(fl.index) == [days[2]])
    # trading rule fills
    ba = pd.DataFrame({"close_b": [99.9, 100.9], "close_a": [100.1, 101.1], "close_m": [100.0, 101.0]}, index=days[:2])
    class NoFin:
        def charge(self, *_): return 0.0
    row = pd.DataFrame([dict(month="x", Dm5=days[0], D=days[1], Dm5_to_D=[days[0]])])
    hist = pd.Series([0.01] * 40 + [-0.05], index=[f"h{i}" for i in range(40)] + ["x"])
    rows = pd.concat([pd.DataFrame([dict(month=f"h{i}", Dm5=days[0], D=days[1], Dm5_to_D=[days[0]])]) for i in range(40)] + [row])
    tr = trades(rows, None, NoFin(), NoFin(), ba, ba, hist)
    got = tr.iloc[-1]
    check("S<0 -> long equity (buy ask, sell bid) and short bond (sell bid, buy ask)",
          got["side"] == "long eq / short bond"
          and abs(got["after_spread"] - ((100.9/100.1 - 1) - (101.1/99.9 - 1))) < 1e-12)
    check("threshold needs 36 months of history before trading", len(tr) == 1)
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test", action="store_true"); g.add_argument("--check-inputs", action="store_true")
    g.add_argument("--run", action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else check_inputs() if a.check_inputs else run())
