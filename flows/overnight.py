#!/usr/bin/env python3
"""
overnight.py -- FLOWS-3: the overnight drift after a US sell-off.
Implements flows/PREREGISTRATION_OVERNIGHT.md; refuses to run if it changed.

    python3 overnight.py --self-test      synthetic bars only, planted drift
    python3 overnight.py --check-inputs   files, grids, bar coverage -- NO returns
    python3 overnight.py --run            the registered test, once

Definitions read strictly from the pre-registration:
  window   open of the bar starting 02:00 ET -> close of the bar starting 02:45 ET
  session  open of the 09:30 ET bar -> close of the 15:45 ET bar; both bars
           must exist and at least 20 of the 26 bars must be present
  sell-off prior session's return below the 10th percentile of all EARLIER
           sessions (expanding, >= 250 of them)
"""
from __future__ import annotations
import argparse, datetime as dt, io, json, os, sys
import numpy as np
import pandas as pd
import common as C

NAME = "OVERNIGHT"
PRIMARY, CONFIRM, DESCR = "SPX500_USD", ("NAS100_USD", "US30_USD"), "DE30_EUR"
P2_START = pd.Timestamp("2021-01-01")
WINDOWS = {"main": (200, 245), "plateau_a": (145, 245), "plateau_b": (200, 300), "placebo": (2000, 2045)}
LOG = os.path.join(C.FDATA, "overnight_run.log")


def ny_frame(ba: pd.DataFrame) -> pd.DataFrame:
    ny = ba.index.tz_convert(C.NY)
    f = ba[["open_m", "close_m", "open_a", "close_b"]].copy()
    f["date"] = pd.DatetimeIndex(ny.tz_localize(None)).normalize()
    f["hm"] = ny.hour * 100 + ny.minute
    return f


def window(f: pd.DataFrame, first_hm: int, last_hm: int) -> pd.DataFrame:
    """Per NY date: open of the bar starting first_hm to close of the bar
    starting last_hm. Both bars must exist."""
    a = f[f["hm"] == first_hm].set_index("date"); b = f[f["hm"] == last_hm].set_index("date")
    j = a[["open_m", "open_a"]].join(b[["close_m", "close_b"]], how="inner")
    return pd.DataFrame({"gross": j["close_m"] / j["open_m"] - 1.0,
                         "net": j["close_b"] / j["open_a"] - 1.0})


def sessions(f: pd.DataFrame) -> pd.Series:
    s = f[(f["hm"] >= 930) & (f["hm"] <= 1545)]
    n = s.groupby("date").size()
    op = s[s["hm"] == 930].set_index("date")["open_m"]
    cl = s[s["hm"] == 1545].set_index("date")["close_m"]
    ok = n[n >= 20].index.intersection(op.index).intersection(cl.index)
    return (cl[ok] / op[ok] - 1.0).sort_index()


def selloffs(sess: pd.Series, q: float = 0.10, min_hist: int = 250) -> pd.Series:
    """True where the session return is below the q-quantile of all EARLIER
    session returns. Causal: session i never sees itself or anything later."""
    v = sess.to_numpy(); out = np.zeros(len(v), bool)
    for i in range(min_hist, len(v)):
        out[i] = v[i] < np.quantile(v[:i], q)
    s = pd.Series(out, index=sess.index)
    s.iloc[:min_hist] = False
    return s


def prior_session(dates: pd.DatetimeIndex, sess_dates: pd.DatetimeIndex) -> pd.Series:
    """For each window date, the latest session date strictly before it."""
    pos = np.searchsorted(sess_dates.values, dates.values, side="left") - 1
    out = pd.Series(pd.NaT, index=dates)
    ok = pos >= 0
    out[ok] = sess_dates.values[pos[ok]]
    return out


def stat(x):
    m, t, n = C.mean_t(x); return dict(mean=m, t=t, n=n)


def analyse(f: pd.DataFrame, sess: pd.Series, so: pd.Series) -> dict:
    out = {}
    for k, (a, b) in WINDOWS.items():
        w = window(f, a, b)
        if k == "placebo":            # evening of the session day itself
            w = w[w.index.isin(sess.index)]
            cond = pd.Series(w.index.isin(so.index[so.to_numpy()]), index=w.index)
        else:
            ps = prior_session(w.index, sess.index)
            cond = pd.Series(ps.isin(so.index[so.to_numpy()]).to_numpy(), index=w.index)
        p2 = w.index >= P2_START
        out[k] = dict(
            uncond_P1=stat(w.loc[~p2, "gross"]), uncond_P2=stat(w.loc[p2, "gross"]),
            cond_P1=stat(w.loc[~p2 & cond.to_numpy(), "gross"]), cond_P2=stat(w.loc[p2 & cond.to_numpy(), "gross"]),
            cond_P2_net=stat(w.loc[p2 & cond.to_numpy(), "net"]))
        if k == "main":
            mon = w.index.dayofweek == 0
            out[k]["cond_P2_monday"] = stat(w.loc[p2 & cond.to_numpy() & mon, "gross"])
            out[k]["cond_P2_not_monday"] = stat(w.loc[p2 & cond.to_numpy() & ~mon, "gross"])
            out[k]["cond_P2_net_stress_1bp"] = stat(w.loc[p2 & cond.to_numpy(), "net"] - 2e-4)
            out[k]["cond_P2_net_stress_3bp"] = stat(w.loc[p2 & cond.to_numpy(), "net"] - 6e-4)
    return out


def run() -> int:
    buf = io.StringIO()
    def say(*a):
        s = " ".join(str(x) for x in a); print(s); buf.write(s + "\n")
    pin = C.check_pin(NAME)
    say(f"FLOWS-3 overnight.py  run {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}")
    say(f"  {NAME} sha256 {pin[:16]}... matches the frozen copy")
    res = {"pin": pin}
    f = ny_frame(C.load_bidask(PRIMARY))
    sess = sessions(f); so = selloffs(sess)
    say(f"  {PRIMARY}: {len(sess)} sessions, {int(so.sum())} sell-offs ({int(so[so.index >= P2_START].sum())} in P2)")
    A = analyse(f, sess, so); res[PRIMARY] = A
    M = A["main"]
    for inst in CONFIRM:
        g = ny_frame(C.load_bidask(inst)); s2 = sessions(g)
        res[inst] = {"main_cond_P2": analyse(g, s2, selloffs(s2))["main"]["cond_P2"]}
    g = ny_frame(C.load_bidask(DESCR))
    res[DESCR + "_on_SPX_selloffs"] = {"main_cond_P2": analyse(g, sess, so)["main"]["cond_P2"]}

    g1, g2 = M["cond_P2"], M["cond_P1"]
    ratio = g1["mean"] / g2["mean"] if g2["mean"] and g2["mean"] > 0 else float("nan")
    gates = {
        "H1_info": M["uncond_P1"]["mean"] > 0,
        "G1": g1["mean"] > 0 and g1["t"] >= 2.0,
        "G2": g2["mean"] > 0 and g2["t"] >= 2.0,
        "G3": bool(np.isfinite(ratio) and ratio >= 0.5),
        "G4": A["placebo"]["cond_P2"]["t"] < 2.0 and A["placebo"]["cond_P2"]["mean"] < g1["mean"],
        "G5": all(np.sign(A[k]["cond_P2"]["mean"]) == np.sign(g1["mean"]) for k in ("plateau_a", "plateau_b")),
        "G6": M["cond_P2_net"]["mean"] > 0,
        "confirm_sign": {i: res[i]["main_cond_P2"]["mean"] > 0 for i in CONFIRM},
    }
    pv = {"G1": C.p_two_sided(g1["t"]), "G2": C.p_two_sided(g2["t"]),
          "G4": C.p_two_sided(A["placebo"]["cond_P2"]["t"])}
    kills = {"K1_G1_fails": not gates["G1"],
             "K2_placebo_as_large": A["placebo"]["cond_P2"]["mean"] >= g1["mean"] or A["placebo"]["cond_P2"]["t"] >= 2.0,
             "K3_net_not_positive": not gates["G6"]}
    core = {k: v for k, v in gates.items() if k.startswith("G")}
    res.update(ratio_G3=ratio, gates=gates, pvalues=pv, bh_q=C.bh(pv), kills=kills,
               verdict="DEAD" if any(kills.values()) else ("ALL GATES PASS" if all(core.values()) else "SURVIVES KILLS, SOME GATES FAIL"))
    bp = lambda d: f"{d['mean']*1e4:+.2f} bp (t {d['t']:+.2f}, n {d['n']})"
    say(f"\n  H1 unconditional P1  {bp(M['uncond_P1'])}")
    say(f"  H2 unconditional P2  {bp(M['uncond_P2'])}")
    say(f"  G2 after sell-off P1 {bp(g2)}")
    say(f"  G1 after sell-off P2 {bp(g1)}   ratio P2/P1 {ratio:+.2f}")
    say(f"  G4 placebo 20:00 P2  {bp(A['placebo']['cond_P2'])}")
    say(f"  G5 plateau a / b     {bp(A['plateau_a']['cond_P2'])} / {bp(A['plateau_b']['cond_P2'])}")
    say(f"  G6 net, P2           {bp(M['cond_P2_net'])}   stress 3bp {bp(M['cond_P2_net_stress_3bp'])}")
    for i in CONFIRM:
        say(f"  confirm {i:<11}  {bp(res[i]['main_cond_P2'])}")
    say(f"  DE30 on SPX sell-offs {bp(res[DESCR + '_on_SPX_selloffs']['main_cond_P2'])}")
    say(f"  BH q: {res['bh_q']}\n  gates: {gates}\n  kills: {kills}\n  VERDICT: {res['verdict']}")
    json.dump(res, open(os.path.join(C.FDATA, "overnight_result.json"), "w"), indent=2, default=str)
    open(LOG, "w").write(buf.getvalue())
    return 0


def check_inputs() -> int:
    print(f"  {NAME} sha256 {C.check_pin(NAME)[:16]}... matches")
    for inst in (PRIMARY,) + CONFIRM + (DESCR,):
        f = ny_frame(C.load_bidask(inst))
        s = f[(f["hm"] >= 930) & (f["hm"] <= 1545)].groupby("date").size()
        full = f[f["hm"].isin([930, 1545])].groupby("date")["hm"].nunique()
        n_sess = int(((s >= 20) & (full.reindex(s.index) == 2)).sum())
        w = f[f["hm"].isin([200, 245])].groupby("date")["hm"].nunique()
        n_win = int((w == 2).sum()); n_win2 = int(((w == 2) & (w.index >= P2_START)).sum())
        print(f"  {inst:<11} bars {f.index[0].date()} .. {f.index[-1].date()}  usable sessions {n_sess}  "
              f"windows {n_win} (P2 {n_win2})")
    return 0


def self_test() -> int:
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    idx = pd.date_range("2019-01-01", "2022-12-31", freq="15min", tz="UTC")
    rng = np.random.default_rng(5)
    r = rng.normal(0, 0.0008, len(idx))
    ny = idx.tz_convert(C.NY); hm = ny.hour * 100 + ny.minute
    date = pd.DatetimeIndex(ny.tz_localize(None)).normalize()
    wk = ny.dayofweek < 5
    r[~wk] = 0.0
    mid = 100 * np.exp(np.cumsum(r))
    ba = pd.DataFrame({"open_m": np.r_[100, mid[:-1]], "close_m": mid}, index=idx)
    ba["open_a"], ba["close_b"] = ba["open_m"] + 0.01, ba["close_m"] - 0.01
    f = ny_frame(ba)
    sess = sessions(f); so = selloffs(sess, min_hist=100)
    w = window(f, 200, 245)
    ps = prior_session(w.index, sess.index)
    cond = pd.Series(ps.isin(so.index[so.to_numpy()]).to_numpy(), index=w.index)
    # plant +25bp into the 02:00-03:00 bars after sell-offs, then rebuild
    bump = pd.Series(0.0, index=idx)
    target = set(w.index[cond.to_numpy()])
    m = np.isin(date.values, np.array(sorted(target), dtype="datetime64[ns]")) & (hm >= 200) & (hm <= 245)
    r2 = r.copy(); r2[m] += 0.0025 / 4
    mid2 = 100 * np.exp(np.cumsum(r2))
    ba2 = pd.DataFrame({"open_m": np.r_[100, mid2[:-1]], "close_m": mid2}, index=idx)
    ba2["open_a"], ba2["close_b"] = ba2["open_m"] + 0.01, ba2["close_m"] - 0.01
    f2 = ny_frame(ba2); sess2 = sessions(f2)
    check("planting inside the window leaves session returns untouched", np.allclose(sess2.values, sess.values))
    A = analyse(f2, sess2, so)
    c = A["main"]
    t0 = pd.Timestamp("2021-07-01 06:00", tz="UTC"); t1 = pd.Timestamp("2021-01-04 07:00", tz="UTC")
    check("02:00 ET is 06:00Z in summer and 07:00Z in winter",
          f2.loc[t0, "hm"] == 200 and f2.loc[t1, "hm"] == 200)
    check(f"planted drift found after sell-offs (P1 {c['cond_P1']['mean']*1e4:+.1f}bp, P2 {c['cond_P2']['mean']*1e4:+.1f}bp)",
          min(c["cond_P1"]["mean"], c["cond_P2"]["mean"]) > 0.0015)
    check(f"unconditional drift diluted (P2 {c['uncond_P2']['mean']*1e4:+.1f}bp)", c["uncond_P2"]["mean"] < 0.6 * c["cond_P2"]["mean"])
    check(f"placebo window finds nothing (t {A['placebo']['cond_P2']['t']:+.1f})", abs(A["placebo"]["cond_P2"]["t"]) < 2)
    check("net = bid out / ask in, below gross", c["cond_P2_net"]["mean"] < c["cond_P2"]["mean"])
    s = pd.Series(np.r_[np.zeros(300), -1.0, 0.0], index=pd.bdate_range("2020-01-01", periods=302))
    so2 = selloffs(s, min_hist=250)
    check("sell-off flag is causal and needs 250 earlier sessions", so2.iloc[300] and not so2.iloc[301] and not so2.iloc[:250].any())
    wd = pd.DatetimeIndex(["2021-03-08"]); sd = pd.DatetimeIndex(["2021-03-04", "2021-03-05"])
    check("Monday window -> Friday session", prior_session(wd, sd).iloc[0] == pd.Timestamp("2021-03-05"))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test", action="store_true"); g.add_argument("--check-inputs", action="store_true")
    g.add_argument("--run", action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else check_inputs() if a.check_inputs else run())
