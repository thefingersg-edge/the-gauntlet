#!/usr/bin/env python3
"""earnings.py -- FLOWS-9, implements PREREGISTRATION_EARNINGS.md.  --self-test | --check-inputs | --run
Implementation reading, CHECKED before any price was joined (2026-09-28): the hour
histogram of the 7,425 Item 2.02 acceptances in data/earnings.meta.json peaks at 20-21h
and 10-13h as written, i.e. 16-17h and 06-09h ET -- after the close and before the open.
So EDGAR's 'Z' is genuine UTC, and it is converted to New York time. (The docstring
first written here guessed the opposite; the histogram check it called for caught it.)"""
from __future__ import annotations
import argparse, datetime as dt, io, json, os, sys
import numpy as np
import pandas as pd
import common as C
import fetch_preholiday as FP
from fixes import at_end

NAME, INST, SEC = "EARNINGS", "SPX500_USD", "NAS100_USD"
ACCEPT_TZ = "UTC"
LOG, RES = (os.path.join(C.FDATA, f) for f in ("earnings_run.log", "earnings_result.json"))


def nyse_days(a="2008-01-01", b="2026-12-31") -> pd.DatetimeIndex:
    closed = set(FP.SPECIAL)
    for y in range(2007, 2028):
        closed |= set(FP.nyse_holidays(y))
    d = pd.bdate_range(a, b)
    return d[~d.isin([pd.Timestamp(x) for x in closed])]


def load_events(tdays):
    C.check_pin("EARNINGS_UNIVERSE"); C.check_pin("EARNINGS_EVENTS")
    uni = pd.read_csv(os.path.join(C.FDATA, "earnings_universe.csv"))
    ev = pd.read_csv(os.path.join(C.FDATA, "earnings_events.csv"))
    acc = pd.to_datetime(ev["acceptance_raw"].str[:19])                       # wall clock as written
    ev["acc_et"] = acc.dt.tz_localize(ACCEPT_TZ).dt.tz_convert(C.NY)
    ev = ev.dropna(subset=["acc_et"])
    fy = np.where(ev["acc_et"].dt.month >= 4, ev["acc_et"].dt.year, ev["acc_et"].dt.year - 1)
    ev["uyear"] = fy
    u = uni.rename(columns={"year_from_april": "uyear"})[["uyear", "cik", "rank"]]
    ev = ev.merge(u, on=["uyear", "cik"], how="inner")
    ev["anchor"] = [anchor_of(t, tdays) for t in ev["acc_et"]]
    return ev.dropna(subset=["anchor"]), uni


def anchor_of(t, tdays):
    """Trading date d whose 15:45 ET is the last one strictly before t."""
    d = pd.Timestamp(t.date())
    if d in tdays and (t.hour, t.minute) > (15, 45):
        return d
    i = tdays.searchsorted(d) - 1
    return tdays[i] if i >= 0 else pd.NaT


def windows(ba, tdays):
    t = pd.DatetimeIndex([pd.Timestamp(d.year, d.month, d.day, 15, 45, tz=C.NY) for d in tdays]).tz_convert("UTC")
    m, b, a = (at_end(ba, c, t) for c in ("close_m", "close_b", "close_a"))
    df = pd.DataFrame({"m": m, "b": b, "a": a}, index=tdays).dropna()
    nxt = df.shift(-1)
    out = pd.DataFrame({"r": nxt["m"] / df["m"] - 1, "gross_fill": nxt["b"] / df["a"] - 1,
                        "next": pd.Series(df.index, index=df.index).shift(-1)}, index=df.index).dropna()
    out["MON"] = ((out["next"] - out.index.to_series()).dt.days > 1).astype(float)
    return out


def fit(df, col="EARN"):
    X = np.column_stack([np.ones(len(df)), df[col].to_numpy(), df["MON"].to_numpy()])
    b, se, t, n = C.ols_nw(df["r"].to_numpy(), X, 5)
    return dict(b=float(b[1]), t=float(t[1]), n=int(n), n_ev=int(df[col].sum()))


def run():
    buf = io.StringIO()
    def say(*a):
        print(*a); print(*a, file=buf)
    pin = C.check_pin(NAME); C.check_pin("EARNINGS_A1")
    tdays = nyse_days()
    ev, uni = load_events(tdays)
    first = pd.Timestamp(f"{int(uni['year_from_april'].min())}-04-01")
    say(f"FLOWS-9 EARNINGS  prereg {pin[:16]}  universe years {uni['year_from_april'].min()}..{uni['year_from_april'].max()}  "
        f"events {len(ev)}  firms {ev['cik'].nunique()}  sample from {first.date()}")
    ba = C.load_bidask(INST)
    w = windows(ba, tdays); w = w[(w.index >= first) & (w["next"] <= C.END)]
    earn = set(ev["anchor"])
    w["EARN"] = w.index.isin(list(earn)).astype(float)
    P = fit(w)
    say(f"  windows {len(w)}, earnings windows {P['n_ev']}\n\n  G1 b {P['b']*1e4:+.2f} bp  t {P['t']:+.2f}")
    eras = {}
    for e, a, b in C.ERAS:
        sub = w[(w.index >= a) & (w.index <= b)]
        eras[e] = fit(sub) if sub["EARN"].sum() > 10 else dict(b=np.nan, t=np.nan, n_ev=int(sub["EARN"].sum()))
        say(f"  {e}: b {eras[e]['b']*1e4:+.2f} bp t {eras[e]['t']:+.2f} n {eras[e]['n_ev']}")
    fin = C.Financing(INST, C.load_snapshot(), C.load_fred("DGS3MO"))
    ew = w[w["EARN"] == 1]
    net = ew["gross_fill"] + pd.Series([fin.charge([d], "long") for d in ew.index], index=ew.index)
    m, t, n = C.mean_t(net); e3 = net[net.index >= pd.Timestamp(C.ERAS[2][1])]
    say(f"\n  G3 trade net {m*1e4:+.2f} bp t {t:+.2f} n {n}; E3 {e3.mean()*1e4:+.2f} (n {len(e3)})")
    G = {"G1": P["b"] > 0 and P["t"] >= 2.0,
         "G2": all(np.isfinite(eras[e]["b"]) and eras[e]["b"] > 0 for e in ("E2", "E3")) and eras["E3"]["b"] >= 0.5 * P["b"],
         "G3": m > 0 and t >= 1.65 and e3.mean() > 0, "G4": P["n_ev"] >= 300}
    kill = [k for k, gg in (("K1", "G1"), ("K2", "G2"), ("K3", "G3")) if not G[gg]]
    res = {"pin": pin, "primary": P, "eras": eras, "trade": dict(net=m, t=t, n=n, e3=float(e3.mean())), "gates": G,
           "verdict": "DEAD " + ",".join(kill) if kill else ("PASS" if G["G4"] else "PASS, G4 short")}
    say("\n  " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in G.items()) + f"   VERDICT: {res['verdict']}")
    say("\n  secondary (descriptive):")
    w2 = windows(C.load_bidask(SEC), tdays); w2 = w2[(w2.index >= first) & (w2["next"] <= C.END)]
    w2["EARN"] = w2.index.isin(list(earn)).astype(float); P2 = fit(w2)
    say(f"    NAS100: b {P2['b']*1e4:+.2f} bp t {P2['t']:+.2f}")
    h = ev["acc_et"].dt.hour + ev["acc_et"].dt.minute / 60
    sec = {"NAS100": P2}
    for lab, mask in (("pre-open", h < 9.5), ("after-close", h >= 16), ("top-3", ev["rank"] <= 3), ("rank 4-10", ev["rank"] > 3)):
        w["X"] = w.index.isin(list(set(ev.loc[mask, "anchor"]))).astype(float)
        f = fit(w, "X"); sec[lab] = f
        say(f"    {lab:11s}: b {f['b']*1e4:+.2f} bp t {f['t']:+.2f} n {f['n_ev']}")
    res["secondary"] = sec
    open(LOG, "w").write(buf.getvalue()); json.dump(res, open(RES, "w"), indent=1, default=float)
    return 0


def check_inputs():
    print(f"prereg {C.check_pin(NAME)[:16]} OK")
    ev, uni = load_events(nyse_days())
    print(f"universe pinned OK ({len(uni)} rows); events pinned OK: {len(ev)} in-universe, {ev['anchor'].nunique()} windows")
    print("  acceptance hour ET:", ev["acc_et"].dt.hour.value_counts().sort_index().to_dict())
    return 0


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    td = nyse_days("2025-01-01", "2025-12-31")
    a = lambda s: anchor_of(pd.Timestamp(s, tz=C.NY), td)
    check("after-close Thursday -> anchor that Thursday", a("2025-07-31 16:30") == pd.Timestamp("2025-07-31"))
    check("pre-open Thursday -> anchor Wednesday", a("2025-07-31 07:00") == pd.Timestamp("2025-07-30"))
    check("pre-open Tuesday after Labor Day -> anchor Friday before", a("2025-09-02 07:00") == pd.Timestamp("2025-08-29"))
    check("Good Friday 2025 is not an NYSE day", pd.Timestamp("2025-04-18") not in td)
    idx = pd.date_range("2025-07-30 18:00", "2025-08-05 21:00", freq="15min", tz="UTC")
    px = pd.Series(np.linspace(6000, 6060, len(idx)), index=idx)
    ba = pd.DataFrame({"close_m": px, "close_b": px - 0.3, "close_a": px + 0.3})
    wdf = windows(ba, td[(td >= "2025-07-30") & (td <= "2025-08-05")])
    check("windows: 15:45 -> next trading day 15:45; Friday window flagged as weekend",
          wdf.loc["2025-08-01", "MON"] == 1 and wdf.loc["2025-07-31", "MON"] == 0 and (wdf["r"] > 0).all())
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--self-test", "--check-inputs", "--run"): g.add_argument(f, action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else check_inputs() if a.check_inputs else run())
