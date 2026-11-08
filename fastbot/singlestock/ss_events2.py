"""Event builders and a generic event study for PEAD2 / PEAD3 / INSIDER1 / STRAT1.
Does NOT modify the frozen PEAD1 engine; reuses its band/bench caches and conventions.
I am not a financial adviser. This is a measurement tool, not a recommendation."""
import os, csv, bisect, subprocess, io, pickle
import numpy as np
from collections import defaultdict
import ss_lib, pead_engine as E

D = ss_lib.DATA; CACHE = os.path.join(D, "cache")
STORE = os.environ.get("SS_STORE") or os.path.join(D, "store")
COMM = 0.0035


def stream(table):
    """csv reader over a Sharadar table; falls back to the unzip binary for zip64 streams Python can't open."""
    p = ss_lib.find(table)
    try:
        fh = ss_lib.open_table(p)
    except Exception:
        proc = subprocess.Popen(["unzip", "-p", p], stdout=subprocess.PIPE)
        fh = io.TextIOWrapper(proc.stdout, encoding="utf-8-sig", newline="")
    rd = csv.reader(fh); head = [h.strip().lower() for h in next(rd)]
    return rd, {c: i for i, c in enumerate(head)}


def fundamentals_arq(universe):
    """ticker -> sorted list of (datekey int, reportperiod int, eps float), as-reported quarterly (ARQ)."""
    rd, ix = stream("fundamentals"); out = defaultdict(list)
    for r in rd:
        if r[ix["dimension"]] != "ARQ": continue
        t = r[ix["ticker"]]
        if universe and t.replace("/", "_") + ".npz" not in universe: continue
        try: out[t].append((ss_lib.d2i(r[ix["date"]]), ss_lib.d2i(r[ix["reportperiod"]]), float(r[ix["eps"]])))
        except ValueError: continue
    for t in out: out[t] = sorted(set(out[t]))
    return out


def sue_events(arq):
    """SUE = (eps_q - eps_{q-4}) / sd of the previous 8 seasonal differences; known at datekey (the 10-Q/10-K filing date).
    Quarters are ordered by reportperiod; requires 12 prior quarters. Returns list of (ticker, datekey, reportperiod, sue)."""
    ev = []
    for t, rows in arq.items():
        byp = {}
        for dk, rp, eps in rows:                     # keep the FIRST filing for each report period (no restatements)
            if rp not in byp: byp[rp] = (dk, eps)
        rps = sorted(byp); eps = [byp[p][1] for p in rps]
        for i in range(12, len(rps)):
            if rps[i] - rps[i - 4] > 380 or rps[i] - rps[i - 4] < 350: continue      # 4 quarters apart
            diffs = [eps[j] - eps[j - 4] for j in range(i - 8, i)]
            sd = float(np.std(diffs, ddof=1))
            if sd <= 0: continue
            ev.append((t, byp[rps[i]][0], rps[i], (eps[i] - eps[i - 4]) / sd))
    return ev


def insider_buys(universe, min_value=10000):
    """Open-market purchases (code P) on Form 4 by an officer or director. Returns ticker -> list of (filing date int, owner, value)."""
    rd, ix = stream("insiders"); out = defaultdict(list)
    for r in rd:
        if r[ix["formtype"]].strip() != "4" or r[ix["transactioncode"]].strip() != "P": continue
        if r[ix["isofficer"]] != "Y" and r[ix["isdirector"]] != "Y": continue
        t = r[ix["ticker"]]
        if universe and t.replace("/", "_") + ".npz" not in universe: continue
        try:
            v = float(r[ix["transactionvalue"]] or 0) or float(r[ix["transactionshares"]] or 0) * float(r[ix["transactionpricepershare"]] or 0)
            out[t].append((ss_lib.d2i(r[ix["date"]]), r[ix["ownername"]].strip().upper(), abs(v)))
        except ValueError:
            continue
    return {t: sorted(v) for t, v in out.items() if v}


def insider_clusters(buys, window=10, min_insiders=2, min_total=100000):
    """A cluster fires on the filing date when >= min_insiders distinct officers/directors have bought within the
    previous `window` calendar days (filing dates) with total value >= min_total. At most one signal per ticker per 60 days."""
    ev = []
    for t, rows in buys.items():
        last = -10**9
        for i, (d, o, v) in enumerate(rows):
            w = [(dd, oo, vv) for dd, oo, vv in rows[:i + 1] if d - window <= dd <= d]
            if len({oo for _, oo, _ in w}) >= min_insiders and sum(vv for *_, vv in w) >= min_total and d - last >= 60:
                ev.append((t, d)); last = d
    return ev


def study(events, band, bench, bad, good, H=60, execution="open", known_lag=0):
    """Generic event study. events: list of (ticker, signal_day[, extra...]); the signal is known at the close of the
    first trading day >= signal_day + known_lag. execution='open': buy next OPEN, cost = EDGE spread + commission.
    execution='close': buy next CLOSE (closing auction), sell at a CLOSE; cost recorded separately (auction assumption applied later).
    Returns records with gross / excess / spread / comm / path, mirroring the PEAD1 engine."""
    byt = defaultdict(list)
    for e in events: byt[e[0]].append(e)
    out = []
    for t, evs in byt.items():
        f = t.replace("/", "_") + ".npz"
        if not os.path.exists(os.path.join(STORE, f)): continue
        z = ss_lib.load(STORE, f); d = z["d"]; ca = z["ca"]; o, h, l, c, cu = z["o"], z["h"], z["l"], z["c"], z["cu"]; n = len(d)
        for ev in evs:
            k = bisect.bisect_left(d, ev[1] + known_lag)                    # signal known at close of day k
            if k < 61 or k + 2 >= n: continue
            b = band.get((f, int(E.month_of(d[k]))))
            if b is None: continue
            sp = ss_lib.edge_spread(o[k - 60:k], h[k - 60:k], l[k - 60:k], c[k - 60:k])
            e0 = k + 1
            x = e0 + H - 1; delist = 0.0
            if x >= n:
                x = n - 1
                if t in bad and t not in good: delist = -0.30
                if x <= e0: continue
            adj = ca[e0] / c[e0] if c[e0] > 0 else np.nan
            if execution == "open":
                px0 = o[e0] * adj; days = range(e0, x + 1)
                px = np.r_[px0, ca[e0:x + 1]]
            else:                                                            # buy at the close of e0, hold H closes
                px0 = ca[e0]; days = range(e0 + 1, min(e0 + H, n - 1) + 1); x = min(e0 + H, n - 1)
                px = ca[e0:x + 1]
            gross = (1 + delist) * px[-1] / px0 - 1
            bb = [bench.get((int(d[j]), b), 0.0) for j in days]
            dr = px[1:] / px[:-1] - 1
            out.append(dict(t=t, band=b, sig=int(ev[1]), entry=int(d[e0]), y=int(str(np.datetime64(int(d[e0]), "D"))[:4]),
                            g=float(gross), x=float(gross - (np.prod([1 + v for v in bb]) - 1)), spread=sp,
                            comm=2 * COMM / float(cu[k]) if cu[k] > 0 else np.nan, extra=ev[2:],
                            path=(dr - np.array(bb[:len(dr)])).astype(np.float32), rpath=dr.astype(np.float32),
                            dates=np.array([int(d[j]) for j in days][:len(dr)], dtype=np.int32)))
    return out


def costs(recs, frac=1.0):
    med = defaultdict(list)
    for r in recs:
        if np.isfinite(r["spread"]): med[r["band"]].append(r["spread"])
    m = {b: float(np.median(v)) for b, v in med.items()}
    for r in recs:
        sp = r["spread"] if np.isfinite(r["spread"]) else m.get(r["band"], 0.01)
        r["cost"] = frac * sp + (r["comm"] if np.isfinite(r["comm"]) else 0)
    return recs
