#!/usr/bin/env python3
"""forward_trend1.py -- FORWARD_BATCH2 parts 1-2 (PREREGISTRATION_FORWARD_BATCH2.md): paper forward records of the FUTPORT1 trend sleeve
(29 markets, fractional) and its FUTMICRO1 $50k whole-contract version. PAPER ONLY: places no order, touches no broker account.
Stdlib only (the Mac tick's plain python3). Databento key from ~/.databento_key or $DATABENTO_API_KEY, never printed.

    python3 forward_trend1.py --self-test   reproduces FUTPORT1's trend-sleeve daily series (data/futport1/futport1_daily.csv) exactly
    python3 forward_trend1.py --tick        append new daily bars (refuses a pull estimated over $1), then append ledger rows
    python3 forward_trend1.py --status      counts only (no running Sharpe before 12 months)

Data: data/trend1fwd/<ROOT>_c_{0,1}.csv are seeded once from data/futport1 (whose frozen files are never touched), then appended.
Ledgers (append-only, VERSION on every row): data/forward_trend1.csv and data/forward_micro1.csv.
A date is recorded only once it is at least 2 calendar days old, so late daily bars can settle; rows are never recomputed.
The rule is exactly scripts/futport1_run.py (trend weights, sigma, costs, sleeve averaging, 252-day scaling) and scripts/futmicro1_run.py.
1.0.1 (2026-10-13): pulls end at (UTC now - 9 h) floored to a date, as forward_oilcarry 1.0.1, because the Databento GLBX.MDP3 licence
  ends ~8 h before the request (the 00:47 and 06:51 ticks failed with dataset_unavailable_range and skipped the ledger step). A failed pull
  now logs one line and the ledger step runs anyway. Data handling and the rule are unchanged.
I am not a financial adviser. This is a measurement, not a recommendation."""
import csv, datetime as dt, hashlib, json, math, os, shutil, subprocess, sys, urllib.parse
VERSION = "1.0.1"
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, "..")
SPEC = os.path.join(FB, "PREREGISTRATION_FORWARD_BATCH2.md"); SPEC_SHA = "65d539aa8303972316d182e91b757977f0f2d990755d91e25d3e571f7acb89fa"
SEED = os.path.join(FB, "data", "futport1"); D = os.path.join(FB, "data", "trend1fwd")
LED = os.path.join(FB, "data", "forward_trend1.csv"); LEDM = os.path.join(FB, "data", "forward_micro1.csv"); PULLLOG = os.path.join(D, "pull_log.jsonl")
START = dt.date(2026, 10, 13); API = "https://hist.databento.com/v0/"; MAXUSD = 1.00
GROUP = {"equity": (["ES", "NQ", "YM", "RTY"], 1.0), "rates": (["ZT", "ZF", "ZN", "ZB"], 1.0), "fx": (["6E", "6J", "6B", "6A", "6C", "6S"], 1.0),
         "metals": (["GC", "SI", "HG", "PL"], 2.0), "energy": (["CL", "NG", "HO", "RB"], 2.0), "grains": (["ZC", "ZS", "ZW", "ZL", "ZM"], 3.0),
         "livestock": (["LE", "HE"], 3.0)}
ROOTS = [r for g in GROUP.values() for r in g[0]]
COST = {r: g[1] * 1e-4 for g in GROUP.values() for r in g[0]}
MICRO = ["ES", "NQ", "YM", "RTY", "GC", "SI", "HG", "CL", "6E", "6A", "6B", "6J", "6C", "6S", "ZC", "ZS", "ZW"]
MULT = {"ES": 5, "NQ": 2, "YM": 0.5, "RTY": 5, "GC": 10, "SI": 1000, "HG": 2500, "CL": 100, "6E": 12500, "6A": 10000, "6B": 6250,
        "6J": 1250000, "6C": 10000, "6S": 12500, "ZC": 10, "ZS": 10, "ZW": 10}
TICK = {"ES": 1.25, "NQ": 0.50, "YM": 0.50, "RTY": 0.50, "GC": 1.00, "SI": 5.00, "HG": 1.25, "CL": 1.00, "6E": 1.25, "6A": 1.00, "6B": 0.625,
        "6J": 1.25, "6C": 1.00, "6S": 1.25, "ZC": 1.25, "ZS": 1.25, "ZW": 1.25}
COMM, CAP = 0.85, 50_000.0
NAN = float("nan")


def pin():
    if hashlib.sha256(open(SPEC, "rb").read()).hexdigest() != SPEC_SHA: sys.exit("REFUSING: PREREGISTRATION_FORWARD_BATCH2.md changed")


def isnan(x): return x != x


# ------------------------------------------------------------------ data
def read_sym(path):
    rows = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            d = dt.date.fromisoformat(r["ts_event"][:10])
            if d.weekday() < 5: rows[d] = (int(r["instrument_id"]), float(r["close"]))      # later duplicates win (keep last)
    return rows


def load(root, base):
    a = read_sym(os.path.join(base, f"{root}_c_0.csv")); b = read_sym(os.path.join(base, f"{root}_c_1.csv"))
    ds = sorted(d for d in a if d in b)
    return ds, [a[d][1] for d in ds], [b[d][1] for d in ds], [a[d][0] for d in ds]


def market(ds, c0, c1, iid):
    n = len(ds); r = [0.0] * n; roll = [False] * n
    for t in range(1, n):
        roll[t] = iid[t] != iid[t - 1]; ref = c1[t - 1] if roll[t] else c0[t - 1]
        r[t] = (c0[t] - ref) / abs(ref) if ref != 0 else 0.0
    a = 1 / 61; num = den = 0.0; ew = [0.0] * n
    for t in range(n):
        num = r[t] ** 2 + (1 - a) * num; den = 1 + (1 - a) * den; ew[t] = num / den
    sig = [NAN] + [math.sqrt(ew[t] * 252) for t in range(n - 1)]
    cs = []; s = 0.0
    for x in r: s += x; cs.append(s)
    sgn = lambda v: (v > 0) - (v < 0)
    w = [NAN] * n
    for t in range(252, n):
        tr = (sgn(cs[t] - cs[t - 21]) + sgn(cs[t] - cs[t - 63]) + sgn(cs[t] - cs[t - 252])) / 3
        if not isnan(sig[t]) and sig[t] > 0: w[t] = max(-4.0, min(4.0, tr * 0.10 / sig[t]))
    return dict(ds=ds, r=r, roll=roll, w=w, c0=c0, c1=c1, iid=iid)


def sleeve(M):
    cal = sorted(set().union(*[set(m["ds"]) for m in M.values()]))
    pos = {k: {d: i for i, d in enumerate(m["ds"])} for k, m in M.items()}
    W = {k: [NAN] * len(cal) for k in M}; raw = [NAN] * len(cal); gross = [NAN] * len(cal); nact = [0] * len(cal)
    for k, m in M.items():
        last = NAN
        for i, d in enumerate(cal):
            j = pos[k].get(d)
            if j is not None: last = m["w"][j]
            W[k][i] = last
    for i, d in enumerate(cal):
        if i == 0: continue
        tot = g = 0.0; n = 0
        for k, m in M.items():
            wp, w = W[k][i - 1], W[k][i]
            if isnan(wp): continue
            j = pos[k].get(d); r = m["r"][j] if j is not None else 0.0; rl = m["roll"][j] if j is not None else False
            cost = (abs(w - wp) if not isnan(w) else 0.0) * COST[k] + (abs(wp) * 2 * COST[k] if rl else 0.0)
            tot += wp * r - cost; g += wp * r; n += 1
        if n: raw[i] = tot / n; gross[i] = g / n; nact[i] = n
    sc = [NAN] * len(cal)
    for i in range(253, len(cal)):
        win = raw[i - 252:i]
        if any(isnan(x) for x in win): continue
        mu = sum(win) / 252; sd = math.sqrt(sum((x - mu) ** 2 for x in win) / 251) * math.sqrt(252)
        if sd > 0: sc[i] = min(3.0, 0.10 / sd)
    return cal, W, raw, gross, nact, sc


def micro(M):
    """The 17-market sleeve (its own averaging and scaling, as futmicro1_run.py), then FUTMICRO1 $50k whole contracts: k_t = round(CAP x s_t x w_t / n_t / (|c0_t| x mult)); P&L_t = k_{t-1} x mult x (c0_t - ref_t) - costs."""
    cal, W, raw, gross, nact, sc = sleeve({r: M[r] for r in MICRO})
    pnl = [0.0] * len(cal); K = {r: [0.0] * len(cal) for r in MICRO}
    for r in MICRO:
        m = M[r]; pos = {d: i for i, d in enumerate(m["ds"])}; k = 0.0; prev_c0 = prev_c1 = prev_iid = None
        for i, d in enumerate(cal):
            j = pos.get(d); kp = k
            if j is not None:
                c0, c1, iid = m["c0"][j], m["c1"][j], m["iid"][j]
                if prev_c0 is not None:
                    rl = iid != prev_iid; ref = prev_c1 if rl else prev_c0
                    pnl[i] += kp * MULT[r] * (c0 - ref) - (abs(kp) * 2 * (TICK[r] + COMM) if rl else 0.0)
                n = nact[i + 1] if i + 1 < len(cal) else nact[i]
                tgt = CAP * sc[i] * W[r][i] / n if (n and not isnan(sc[i]) and not isnan(W[r][i])) else NAN
                k = float(round(tgt / (abs(c0) * MULT[r]))) if not isnan(tgt) else 0.0
                pnl[i] -= abs(k - kp) * (TICK[r] + COMM)
                prev_c0, prev_c1, prev_iid = c0, c1, iid
            K[r][i] = k
    return cal, pnl, K


# ------------------------------------------------------------------ Databento (curl, as forward_oilcarry.py)
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


def seed():
    if os.path.isdir(D) and all(os.path.exists(os.path.join(D, f"{r}_c_{k}.csv")) for r in ROOTS for k in (0, 1)): return
    os.makedirs(D, exist_ok=True)
    for r in ROOTS:
        for k in (0, 1):
            dst = os.path.join(D, f"{r}_c_{k}.csv")
            if not os.path.exists(dst): shutil.copyfile(os.path.join(SEED, f"{r}_c_{k}.csv"), dst)
    print("seeded data/trend1fwd from data/futport1")


def pull(k):
    today = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=9)).date().isoformat(); plans = []; tot = 0.0   # 1.0.1: licensed window ends ~8 h before request
    for r in ROOTS:
        for c in (0, 1):
            p = os.path.join(D, f"{r}_c_{c}.csv"); last = max(read_sym(p)).isoformat() if os.path.exists(p) else "2010-06-06"
            start = (dt.date.fromisoformat(last) + dt.timedelta(days=1)).isoformat()
            if start >= today: continue
            q = dict(dataset="GLBX.MDP3", symbols=f"{r}.c.{c}", stype_in="continuous", schema="ohlcv-1d", start=start, end=today)
            plans.append((p, q)); tot += float(api("metadata.get_cost", q, k))
    with open(PULLLOG, "a") as f: f.write(json.dumps(dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(), files=len(plans), est_usd=tot)) + "\n")
    if tot > MAXUSD: sys.exit(f"REFUSING: estimated ${tot:.2f} > ${MAXUSD:.2f}")
    for p, q in plans:
        txt = api("timeseries.get_range", dict(q, encoding="csv", pretty_px="true", pretty_ts="true", map_symbols="true"), k)
        lines = [ln for ln in txt.splitlines()[1:] if ln.strip()]
        if lines:
            with open(p, "a") as f: f.write("\n".join(lines) + "\n")
    print(f"pulled {len(plans)} symbol updates (est ${tot:.3f})")


# ------------------------------------------------------------------ ledgers
def compute(base):
    M = {r: market(*load(r, base)) for r in ROOTS}
    cal, W, raw, gross, nact, sc = sleeve(M)
    net = [raw[i] * sc[i] if not isnan(raw[i]) and not isnan(sc[i]) else NAN for i in range(len(cal))]   # futport1.scale: s_i uses raw[i-252..i-1]
    return M, cal, W, raw, gross, nact, sc, net


def tick_ledgers():
    M, cal, W, raw, gross, nact, sc, net = compute(D)
    calm, pnl, K = micro(M); im = {d: i for i, d in enumerate(calm)}
    cutoff = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=2)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    for path, cols, rowf in ((LED, ["date", "net", "gross", "scale_used", "n_markets"] + [f"w_{r}" for r in ROOTS] + ["written_utc", "version"],
                              lambda i: [cal[i].isoformat(), f"{net[i]:.8f}", f"{gross[i] * sc[i]:.8f}", f"{sc[i]:.6f}", nact[i]]
                              + [("" if isnan(W[r][i]) else f"{W[r][i]:.6f}") for r in ROOTS] + [now, VERSION]),
                             (LEDM, ["date", "pnl_usd", "capital"] + [f"k_{r}" for r in MICRO] + ["written_utc", "version"],
                              lambda i: [cal[i].isoformat(), f"{pnl[im[cal[i]]]:.2f}", int(CAP)] + [int(K[r][im[cal[i]]]) for r in MICRO] + [now, VERSION])):
        have = {r["date"] for r in csv.DictReader(open(path))} if os.path.exists(path) else set(); new = not os.path.exists(path); n = 0
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            if new: w.writerow(cols)
            for i, d in enumerate(cal):
                if d < START or d > cutoff or d.isoformat() in have or isnan(net[i]) or (path == LEDM and d not in im): continue
                w.writerow(rowf(i)); n += 1
        print(f"{os.path.basename(path)}: +{n} rows")


def self_test():
    ok = True
    M, cal, W, raw, gross, nact, sc, net = compute(SEED)
    ref = {}
    with open(os.path.join(SEED, "futport1_daily.csv")) as f:
        for r in csv.DictReader(f):
            if r["trend"] not in ("", "nan"): ref[dt.date.fromisoformat(r[next(iter(r))][:10])] = float(r["trend"])
    mine = {d: net[i] for i, d in enumerate(cal) if not isnan(net[i])}
    common = [d for d in ref if d in mine]
    err = max(abs(mine[d] - ref[d]) for d in common) if common else 1.0
    e1 = len(common) == len(ref) and err < 1e-10
    ok &= e1; print(f"  [{'PASS' if e1 else 'FAIL'}] reproduces FUTPORT1's trend sleeve on {len(common)}/{len(ref)} days, max abs diff {err:.1e}")
    calm, pnl, K = micro(M)
    try:                                                                      # cross-check vs the frozen futmicro1 harness when pandas is available
        import futmicro1_run as FM, futport1_run as FP, pandas as pd
        J = {r: FP.load(r) for r in FP.ROOTS}; MF = {r: FP.market(J[r]) for r in FP.ROOTS}
        raw17, _, W17 = FP.sleeve_pnl({r: MF[r] for r in FM.ROOTS}, "w_tr"); frac, s17 = FP.scale(raw17)
        p50, _, _ = FM.contracts_pnl(J, MF, W17, W17.notna().sum(axis=1).replace(0, float("nan")), s17, 50_000)
        ref = {d.date(): v for d, v in p50.items()}; err = max(abs(pnl[i] - ref[d]) for i, d in enumerate(calm) if d in ref)
        e2 = err < 1e-6; print(f"  [{'PASS' if e2 else 'FAIL'}] micro $50k P&L equals futmicro1_run.contracts_pnl (max abs diff ${err:.2e})")
    except ImportError:
        e2 = len(pnl) == len(calm) and set(K) == set(MICRO); print(f"  [{'PASS' if e2 else 'FAIL'}] micro ledger computes for all 17 markets (pandas absent: cross-check skipped)")
    ok &= e2
    print("ALL PASS" if ok else "FAILURES"); return ok


if __name__ == "__main__":
    pin(); a = sys.argv[1:]
    if a == ["--self-test"]: sys.exit(0 if self_test() else 1)
    if a == ["--tick"]:
        seed()
        try: pull(key())
        except RuntimeError as e: print(f"pull skipped (non-fatal): {str(e)[:160]}")
        tick_ledgers(); sys.exit(0)
    if a == ["--status"]:
        for p in (LED, LEDM): print(os.path.basename(p), (sum(1 for _ in open(p)) - 1) if os.path.exists(p) else 0, "rows (no running Sharpe before 12 months)")
        sys.exit(0)
    print(__doc__)
