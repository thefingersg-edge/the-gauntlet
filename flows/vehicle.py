#!/usr/bin/env python3
"""vehicle.py -- FLOWS-15, implements PREREGISTRATION_VEHICLE.md: fastbot v36 rule N,
imported unchanged, on CME futures 5-minute bars built from Databento 1-minute OHLCV.
    --self-test | --check-inputs | --run"""
from __future__ import annotations
import argparse, datetime as dt, glob, io, json, os, sys
import numpy as np
import pandas as pd
import common as C
sys.path.insert(0, os.path.join(C.ROOT, "fastbot", "scripts"))
import momentum_v36 as M     # noqa: E402  (the frozen v36 rule)
import reactive as RX        # noqa: E402

NAME = "VEHICLE"
FUT = {"ES": dict(tick=0.25, mult=50.0, cfd="spx500usd"), "NQ": dict(tick=0.25, mult=20.0, cfd="nas100usd"),
       "YM": dict(tick=1.0, mult=5.0, cfd="us30usd")}
COMM_USD = 2.50
FD = os.path.join(C.FDATA, "futures")
G0, G1 = dt.date(2013, 1, 1), dt.date(2026, 8, 31)
ERAS = ((2013, 2017), (2018, 2021), (2022, 2026))
LOG, RES = (os.path.join(C.FDATA, f) for f in ("vehicle_run.log", "vehicle_result.json"))


def load_fut(root: str) -> pd.DataFrame:
    fs = sorted(glob.glob(os.path.join(FD, f"{root}_*.csv")))
    d = pd.concat([pd.read_csv(f, usecols=["ts_event", "instrument_id", "open", "high", "low", "close"]) for f in fs])
    d["ts"] = pd.to_datetime(d["ts_event"], utc=True)
    return d.drop(columns="ts_event").sort_values("ts").drop_duplicates("ts")


def days_from(d: pd.DataFrame, tick: float) -> tuple[dict, dict]:
    """{date: {'HH:MM': (o,h,l,c, bid_o, ask_o, bid_c, ask_c)}} on 5-minute bars 09:30-15:55 ET,
    bid/ask = price -/+ one tick (the registered one-tick-per-side cost); plus {date: instrument_id}."""
    et = d["ts"].dt.tz_convert(C.NY)
    d = d.assign(et=et.dt.tz_localize(None))
    t = d["et"].dt.time
    d = d[(t >= dt.time(9, 30)) & (t < dt.time(16, 0))]
    d = d.set_index("et")
    g = d.resample("5min", label="left", closed="left")
    b = pd.DataFrame({"o": g["open"].first(), "h": g["high"].max(), "l": g["low"].min(), "c": g["close"].last(),
                      "iid": g["instrument_id"].agg(lambda x: x.mode().iloc[0] if len(x) else np.nan)}).dropna()
    days, iid = {}, {}
    for ts, r in b.iterrows():
        k = ts.strftime("%H:%M")
        if not ("09:30" <= k <= "15:55"):
            continue
        days.setdefault(ts.date(), {})[k] = (r.o, r.h, r.l, r.c, r.o - tick, r.o + tick, r.c - tick, r.c + tick)
        iid.setdefault(ts.date(), []).append(r.iid)
    days = {k: v for k, v in days.items() if len(v) >= RX.MIN_BARS}
    iid = {k: pd.Series(v).mode().iloc[0] for k, v in iid.items() if k in days}
    return days, iid


def drop_rolls(days, iid):
    ds = sorted(days); out = {}; dropped = 0
    for i, d in enumerate(ds):
        if i > 0 and iid[d] != iid[ds[i - 1]]:
            dropped += 1; continue
        out[d] = days[d]
    return out, dropped


def prep(root):
    """Execution only (1.1, 2026-10-10): each device call is time-limited, so the
    5-minute session dicts are built once per root and cached. Same function,
    same output; the cache is keyed to the raw files' sha256s in futures.meta.json."""
    import pickle
    meta = json.load(open(os.path.join(C.FDATA, "futures.meta.json")))
    key = {k: v["sha256"] for k, v in meta["files"].items() if k.startswith(root + "_")}
    p = os.path.join(FD, f"_cache_{root}.pkl")
    if os.path.exists(p):
        k, days, iid = pickle.load(open(p, "rb"))
        if k == key:
            return days, iid
    days, iid = days_from(load_fut(root), FUT[root]["tick"])
    pickle.dump((key, days, iid), open(p, "wb"))
    return days, iid


def rows_for(root):
    spec = FUT[root]
    days, iid = prep(root)
    days, nroll = drop_rolls(days, iid)
    rows = M.noise_rows(days, root)
    for r in rows:
        px = days[r["date"]]["09:30"][0]
        comm_bp = COMM_USD / (px * spec["mult"]) * 1e4
        r["Nn"] = r["Nn"] - r["n"] * comm_bp
    return [r for r in rows if G0 <= r["date"] <= G1], nroll


def run():
    buf = io.StringIO()
    def say(*a):
        print(*a); print(*a, file=buf)
    pin = C.check_pin(NAME)
    say(f"FLOWS-15 VEHICLE  prereg {pin[:16]}  v36 rule from momentum_v36.py {M.VERSION}")
    res = {"pin": pin, "per": {}}
    rows = {}
    for root in FUT:
        if not glob.glob(os.path.join(FD, f"{root}_*.csv")):
            say(f"  {root}: no data"); continue
        rows[root], nroll = rows_for(root)
        g, n = M.cl_mean(rows[root], "Ng"), M.cl_mean(rows[root], "Nn")
        cfd = RX.load(os.path.join(C.ROOT, "fastbot", "data"), FUT[root]["cfd"])
        crows = [r for r in M.noise_rows(cfd, FUT[root]["cfd"]) if G0 <= r["date"] <= G1]
        cg = M.cl_mean(crows, "Ng")
        res["per"][root] = dict(gross=g[0], gross_t=g[1], net=n[0], net_t=n[1], days=n[2], roll_days_dropped=nroll,
                                cfd_gross=cg[0], cfd_days=cg[2])
        say(f"  {root}: days {n[2]} (roll days dropped {nroll}); gross {g[0]:+.2f} bp (t {g[1]:+.2f}); NET {n[0]:+.2f} (t {n[1]:+.2f});"
            f" matching CFD gross {cg[0]:+.2f} bp over {cg[2]} days")
    pool = rows.get("ES", []) + rows.get("NQ", [])
    m, t, n = M.cl_mean(pool, "Nn")
    eras = [M.cl_mean([r for r in pool if a <= r["date"].year <= b], "Nn") for a, b in ERAS]
    ex = M.cl_mean([r for r in pool if r["date"].year not in (2020, 2021)], "Nn")
    say(f"\n  G1 pooled ES+NQ net {m:+.2f} bp/instrument-day t {t:+.2f} (n {n})")
    say("  G2 eras: " + "  ".join(f"{a}-{b} {e[0]:+.2f} (t {e[1]:+.2f})" for (a, b), e in zip(ERAS, eras)))
    say(f"  G3 ex-2020/21 net {ex[0]:+.2f} t {ex[1]:+.2f}")
    g4 = all(res["per"][k]["cfd_gross"] and 0.5 * res["per"][k]["cfd_gross"] <= res["per"][k]["gross"] <= 1.5 * res["per"][k]["cfd_gross"]
             for k in ("ES", "NQ") if k in res["per"])
    G = {"G1": m > 0 and t >= 2.24, "G2": all(e[0] > 0 for e in eras) and eras[2][0] >= 0.5 * m,
         "G3": ex[0] > 0 and ex[1] >= 1.64, "G4": g4}
    verdict = ("VOID (G4: futures gross does not match the CFD signal)" if not G["G4"] else
               "DEAD " + ",".join(k for k, gg in (("K1", "G1"), ("K2", "G2")) if not G[gg]) if not (G["G1"] and G["G2"]) else
               ("PASS" if G["G3"] else "PASS on G1/G2; G3 fails"))
    res |= {"pooled": dict(net=m, t=t, n=n), "eras": eras, "ex2020_21": ex, "gates": G, "verdict": verdict}
    say("\n  " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in G.items()) + f"   VERDICT: {verdict}")
    for root, rr in rows.items():
        gm = M.cl_mean(rr, "Ng")[0]; nt = np.mean([r["n"] for r in rr])
        say(f"    {root}: break-even cost ~ {gm / (2 * nt):.2f} bp per side per trade (avg {nt:.2f} trades/day)")
    open(LOG, "w").write(buf.getvalue()); json.dump(res, open(RES, "w"), indent=1, default=str)
    return 0


def check_inputs():
    print(f"prereg {C.check_pin(NAME)[:16]} OK")
    for root in FUT:
        fs = glob.glob(os.path.join(FD, f"{root}_*.csv"))
        print(f"  {root}: {len(fs)} files")
    return 0


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    ts = pd.date_range("2025-07-10 13:30", "2025-07-10 19:59", freq="1min", tz="UTC")     # 09:30-15:59 EDT
    d = pd.DataFrame({"ts": ts, "instrument_id": 1, "open": 5000.0, "high": 5001.0, "low": 4999.0, "close": 5000.5})
    days, iid = days_from(d, 0.25)
    b = days[dt.date(2025, 7, 10)]
    check("78 five-minute bars 09:30..15:55 ET", len(b) == 78 and "09:30" in b and "15:55" in b and "16:00" not in b)
    check("one tick each side on fills", b["10:00"][5] - b["10:00"][0] == 0.25 and b["10:00"][0] - b["10:00"][4] == 0.25)
    d2 = pd.concat([d, d.assign(ts=d["ts"] + pd.Timedelta(days=1), instrument_id=2), d.assign(ts=d["ts"] + pd.Timedelta(days=2), instrument_id=2)])
    dd, ii = days_from(d2, 0.25); kept, nr = drop_rolls(dd, ii)
    check("first session after a contract change is dropped", nr == 1 and dt.date(2025, 7, 11) not in kept and dt.date(2025, 7, 12) in kept)
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--self-test", "--check-inputs", "--run"): g.add_argument(f, action="store_true")
    g.add_argument("--prep", choices=list(FUT))
    a = ap.parse_args()
    if a.prep:
        d, _ = prep(a.prep); print(f"{a.prep}: {len(d)} sessions cached"); sys.exit(0)
    sys.exit(self_test() if a.self_test else check_inputs() if a.check_inputs else run())
