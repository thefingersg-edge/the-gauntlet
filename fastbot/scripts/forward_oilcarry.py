#!/usr/bin/env python3
"""forward_oilcarry.py -- OILIMP1 forward record (PREREGISTRATION_OILIMP1.md, "Forward record"). PAPER ONLY.
RECORDS ONLY: places no order and touches no broker account. Stdlib only, so it runs under the Mac's plain python3.
Data: Databento GLBX.MDP3 ohlcv-1d, CL.c.0 and CL.c.1 (continuous front and second). The key is read from ~/.databento_key and never printed.

    python3 forward_oilcarry.py --self-test
    python3 forward_oilcarry.py --cost      estimated cost of the seed pull (no download)
    python3 forward_oilcarry.py --seed      pull 2010-06-06 -> today into data/oil/databento/CL_c0.csv, CL_c1.csv (refuses over $1)
    python3 forward_oilcarry.py --tick      append new daily bars (refuses over $1), then append ledger rows (what forward_tick.sh runs)
    python3 forward_oilcarry.py --status

Ledgers (append-only; history is never recomputed; every row carries VERSION):
  data/forward_oilcarry_monthly.csv : one row per month end from 2026-10-30. Signal, sigma, weight, MCL contracts for $10k/$25k/$50k, CFD units for $10k.
  data/forward_oilcarry_daily.csv   : one row per trading day once the first forward weight is held. Roll-adjusted CL change; route M $10k
                                      net P&L (tick + $1.50 per side, roll cost); route C $10k gross P&L, admin fee at 2.5%, units change
                                      (the spread is applied at the review, using the OILIMP1 backtest median).
Closes are last trades, not settlements (disclosed in the spec). Timing as the backtest: a month-end weight is traded at the next day's close.
1.0.1 (2026-10-12): pulls end at safe_end() = (UTC now - 9 h) floored to a date, because the Databento licence on GLBX.MDP3 ends
  8 h before the request; the old end (today) failed the 00:43 and 06:43 ticks with dataset_unavailable_range and skipped the ledger
  step. A still-unavailable range now logs one line and the ledger step runs anyway. Data handling and the rule are unchanged.
I am not a financial adviser. This is a measurement, not a recommendation."""
import csv, datetime as dt, hashlib, json, math, os, subprocess, sys, urllib.parse
VERSION = "1.0.1"
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, "..")
SPEC = os.path.join(FB, "PREREGISTRATION_OILIMP1.md"); SPEC_SHA = "923437deab315a8f7f0eea6b12a8a8955ea7d09d1bdabcefa61af1353d29533f"
DB = os.path.join(FB, "data", "oil", "databento"); MON = os.path.join(FB, "data", "forward_oilcarry_monthly.csv")
DAY = os.path.join(FB, "data", "forward_oilcarry_daily.csv"); PULLLOG = os.path.join(DB, "pull_log.jsonl")
LICENCE_LAG_H = 9  # Databento GLBX.MDP3 on this plan: available up to request time - 8 h (measured 2026-10-12), plus 1 h margin
API = "https://hist.databento.com/v0/"; SEED_START = "2010-06-06"; START = dt.date(2026, 10, 30); MAXUSD = 1.00
TICK_USD, COMM, FEE, CAPS = 1.00, 1.50, 0.025, (10_000, 25_000, 50_000)
MCOLS = ["month_end", "f1", "f2", "carry", "sigma", "w", "n10k", "n25k", "n50k", "units10k", "written_utc", "version"]
DCOLS = ["date", "instrument_id", "close0", "roll", "dP1", "w_held", "n10k_held", "units10k_held", "pnl_M10k_net", "pnl_C10k_gross",
         "admin_C10k", "units10k_change", "written_utc", "version"]


def pin():
    if SPEC_SHA and hashlib.sha256(open(SPEC, "rb").read()).hexdigest() != SPEC_SHA: sys.exit("REFUSING: PREREGISTRATION_OILIMP1.md changed")


def key():
    k = os.environ.get("DATABENTO_API_KEY", "").strip(); p = os.path.expanduser("~/.databento_key")
    if not k and os.path.exists(p): k = open(p).read().strip()
    if not k.startswith("db-"): sys.exit("no Databento key (~/.databento_key)")
    return k


def api(endpoint, params, k):
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    r = subprocess.run(["curl", "-sS", "--fail-with-body", "-u", f"{k}:", "--max-time", "300", url], capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"{endpoint}: {(r.stdout or r.stderr).strip()[:300]}")
    return r.stdout


def safe_end(now=None):
    """Exclusive end date for a pull: the licensed window ends ~8 h before the request, so floor (now - 9 h) to a date."""
    now = now or dt.datetime.now(dt.timezone.utc)
    return (now - dt.timedelta(hours=LICENCE_LAG_H)).date().isoformat()


def q(sym, start, end):
    return dict(dataset="GLBX.MDP3", schema="ohlcv-1d", symbols=sym, stype_in="continuous", start=start, end=end)


def cost(start, end, k):
    return sum(float(api("metadata.get_cost", q(s, start, end), k)) for s in ("CL.c.0", "CL.c.1"))


def read(n):
    p = os.path.join(DB, f"CL_c{n}.csv")
    if not os.path.exists(p): return []
    with open(p) as f: return [(r["date"], float(r["close"]), int(r["instrument_id"])) for r in csv.DictReader(f)]


def pull(start, end, k):
    c = cost(start, end, k)
    os.makedirs(DB, exist_ok=True)
    with open(PULLLOG, "a") as f: f.write(json.dumps(dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(), start=start, end=end, est_usd=c)) + "\n")
    if c > MAXUSD: sys.exit(f"REFUSING: estimated ${c:.2f} > ${MAXUSD:.2f}")
    for n in (0, 1):
        txt = api("timeseries.get_range", dict(q(f"CL.c.{n}", start, end), encoding="csv", pretty_px="true", pretty_ts="true", map_symbols="true"), k)
        rows = list(csv.DictReader(txt.splitlines())); have = {r[0] for r in read(n)}
        p = os.path.join(DB, f"CL_c{n}.csv"); new = not os.path.exists(p)
        with open(p, "a", newline="") as f:
            w = csv.writer(f)
            if new: w.writerow(["date", "close", "instrument_id"])
            for r in rows:
                d = r["ts_event"][:10]
                if d not in have and d < end: w.writerow([d, r["close"], r["instrument_id"]]); have.add(d)
    print(f"pulled {start} -> {end} (est ${c:.3f})")


# ------------------------------------------------------------------ the rule (same as oilimp1_run.build)
def series():
    a = {d: (c, i) for d, c, i in read(0)}; b = {d: c for d, c, _ in read(1)}
    ds = sorted(d for d in a if d in b)
    return ds, [a[d][0] for d in ds], [b[d] for d in ds], [a[d][1] for d in ds]


def compute(ds, c0, c1, iid):
    n = len(ds); dP = [0.0] * n; r1 = [0.0] * n; roll = [False] * n
    for t in range(1, n):
        roll[t] = iid[t] != iid[t - 1]; ref = c1[t - 1] if roll[t] else c0[t - 1]
        dP[t] = c0[t] - ref; r1[t] = dP[t] / abs(ref) if ref else 0.0
    a = 1 / 61; num = den = 0.0; sig = [0.0] * n
    for t in range(n):
        num = r1[t] ** 2 + (1 - a) * num; den = 1 + (1 - a) * den; sig[t] = math.sqrt(num / den * 252)
    wt = [None] * n; me = []
    for t in range(n - 1):
        if ds[t][:7] != ds[t + 1][:7]:
            me.append(t)
            if sig[t] > 0: wt[t] = max(-3.0, min(3.0, math.copysign(1, c0[t] / c1[t] - 1) * 0.10 / sig[t])) if c0[t] != c1[t] else 0.0
    w = [0.0] * n; cur = 0.0
    for t in range(n):
        if t >= 1 and wt[t - 1] is not None: cur = wt[t - 1]
        w[t] = cur                                                       # set on the first trading day after month end
    return dict(dP=dP, roll=roll, sig=sig, w=w, me=me)


def tick_ledgers():
    ds, c0, c1, iid = series()
    if len(ds) < 300: sys.exit("not enough history -- run --seed first")
    R = compute(ds, c0, c1, iid); now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    have_m = {r["month_end"] for r in csv.DictReader(open(MON))} if os.path.exists(MON) else set()
    have_d = {r["date"] for r in csv.DictReader(open(DAY))} if os.path.exists(DAY) else set()
    nm = nd = 0
    newm = not os.path.exists(MON)
    with open(MON, "a", newline="") as f:
        w = csv.writer(f)
        if newm: w.writerow(MCOLS)
        for t in R["me"]:
            if ds[t] < START.isoformat() or ds[t] in have_m or t + 1 >= len(ds): continue
            wt = R["w"][t + 1]; ns = [math.copysign(round(abs(wt) * c / (100 * abs(c0[t + 1]))), wt) if wt else 0.0 for c in CAPS]
            w.writerow([ds[t], c0[t], c1[t], f"{c0[t] / c1[t] - 1:+.5f}", f"{R['sig'][t]:.4f}", f"{wt:+.4f}", *[int(x) for x in ns],
                        f"{wt * 10_000 / abs(c0[t + 1]):+.2f}", now, VERSION]); nm += 1
    first = min((t + 2 for t in R["me"] if ds[t] >= START.isoformat() and t + 2 < len(ds)), default=None)
    if first is None: print(f"monthly rows +{nm}; no forward day yet"); return
    n10 = [0.0] * len(ds); u10 = [0.0] * len(ds)
    for t in range(1, len(ds)):
        if ds[t][:7] != ds[t - 1][:7] or R["w"][t] != R["w"][t - 1]:     # rebalance day = first trading day after a month end
            n10[t] = math.copysign(round(abs(R["w"][t]) * 10_000 / (100 * abs(c0[t]))), R["w"][t]) if R["w"][t] else 0.0
            u10[t] = R["w"][t] * 10_000 / abs(c0[t])
        else: n10[t], u10[t] = n10[t - 1], u10[t - 1]
    newd = not os.path.exists(DAY)
    with open(DAY, "a", newline="") as f:
        w = csv.writer(f)
        if newd: w.writerow(DCOLS)
        for t in range(first, len(ds)):
            if ds[t] in have_d: continue
            nh, uh = n10[t - 1], u10[t - 1]
            pm = nh * 100 * R["dP"][t] - abs(n10[t] - nh) * (TICK_USD + COMM) - (abs(nh) * 2 * (TICK_USD + COMM) if R["roll"][t] else 0.0)
            nights = 3 if dt.date.fromisoformat(ds[t]).weekday() == 4 else 1
            w.writerow([ds[t], iid[t], c0[t], int(R["roll"][t]), f"{R['dP'][t]:+.4f}", f"{R['w'][t - 1]:+.4f}", int(nh), f"{uh:+.2f}",
                        f"{pm:+.2f}", f"{uh * R['dP'][t]:+.2f}", f"{abs(uh) * abs(c0[t - 1]) * FEE * nights / 365:.2f}", f"{u10[t] - uh:+.2f}", now, VERSION]); nd += 1
    print(f"monthly rows +{nm}, daily rows +{nd}")


def self_test():
    ok = True
    ds = [(dt.date(2020, 1, 1) + dt.timedelta(days=i)).isoformat() for i in range(200)]
    c0 = [50 + 0.05 * i for i in range(200)]; c1 = [x + 1 for x in c0]; iid = [1] * 100 + [2] * 100
    R = compute(ds, c0, c1, iid)
    e1 = all(x <= 0 for x in R["w"]) and min(R["w"]) < 0; ok &= e1; print(f"  [{'PASS' if e1 else 'FAIL'}] contango -> short weight")
    e2 = R["roll"][100] and abs(R["dP"][100] - (c0[100] - c1[99])) < 1e-12; ok &= e2; print(f"  [{'PASS' if e2 else 'FAIL'}] roll measured vs yesterday's second contract")
    t = R["me"][0]; e3 = R["w"][t] == 0.0 and R["w"][t + 1] != 0.0; ok &= e3
    print(f"  [{'PASS' if e3 else 'FAIL'}] month-end weight takes effect the next trading day")
    try:
        import pandas as pd, numpy as np
        s = pd.Series(R["dP"]) / pd.Series([abs(c1[i - 1]) if R["roll"][i] else abs(c0[i - 1]) for i in range(200)]).replace(0, np.nan)
        s = s.fillna(0.0); ref = np.sqrt((s ** 2).ewm(com=60).mean() * 252).to_numpy()
        e4 = np.allclose(ref, R["sig"]); ok &= e4; print(f"  [{'PASS' if e4 else 'FAIL'}] EWMA sigma equals pandas ewm(com=60)")
    except ImportError: print("  [skip] pandas not available for the EWMA cross-check")
    n0 = dt.datetime(2026, 10, 12, 0, 43, tzinfo=dt.timezone.utc); n1 = dt.datetime(2026, 10, 12, 12, 43, tzinfo=dt.timezone.utc)
    e5 = safe_end(n0) == "2026-10-11" and safe_end(n1) == "2026-10-12"; ok &= e5
    print(f"  [{'PASS' if e5 else 'FAIL'}] safe_end stays inside the 8 h licence lag (00:43 -> 10-11, 12:43 -> 10-12)")
    print("ALL PASS" if ok else "FAILURES"); return ok


def main():
    pin(); a = sys.argv[1:]
    if a == ["--self-test"]: sys.exit(0 if self_test() else 1)
    end = safe_end()
    if a == ["--cost"]: print(f"seed estimate ${cost(SEED_START, end, key()):.3f}"); return
    if a == ["--seed"]: pull(SEED_START, end, key()); return
    if a == ["--tick"]:
        last = max((r[0] for r in read(0)), default=None)
        if last is None: sys.exit("run --seed first")
        nxt = (dt.date.fromisoformat(last) + dt.timedelta(days=1)).isoformat()
        if nxt < end:
            try: pull(nxt, end, key())
            except RuntimeError as e:
                if "dataset_unavailable_range" not in str(e): raise
                print(f"pull {nxt} -> {end} not yet licensed; ledgers updated from bars on file")
        tick_ledgers(); return
    if a == ["--status"]:
        for p in (MON, DAY): print(os.path.basename(p), (sum(1 for _ in open(p)) - 1) if os.path.exists(p) else 0, "rows")
        return
    print(__doc__)


if __name__ == "__main__":
    main()
