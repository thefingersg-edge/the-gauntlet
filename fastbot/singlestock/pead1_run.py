#!/usr/bin/env python3
"""PREREGISTRATION_PEAD1 harness. Stages run in short resumable calls (VM limit), then ONE final run.
    python3 pead1_run.py unzip | store | bands | bench | events     (repeat each until it prints DONE)
    python3 pead1_run.py final                                        (once; refuses to run twice)
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, json, time, pickle, hashlib, zipfile, shutil, math
import numpy as np
from collections import defaultdict
import ss_lib, pead_engine as E

DOC = ("../PREREGISTRATION_PEAD1.md", "527d3ce58f70aeb47397b37268279bf53cc5732e10c0ea1b675b57874424ae97")        # sha filled in AT FREEZE; empty -> final refuses
PIN_CODE = {"pead_engine.py": "a9a48da76af824c69879aa0c1f8e89bd3de1740ac6e558ac8ad6ba560523d300", "ss_lib.py": "b6a9594e43e16af1f9701cb4f9d9e6ac28666e518db6d40eeeda64de2679cdde"}   # filled in at freeze
D = ss_lib.DATA; RAW = os.path.join(D, "raw"); STORE = os.environ.get("SS_STORE") or os.path.join(D, "store"); CACHE = os.path.join(D, "cache")
CHUNK = 1500; BUDGET = 150
os.makedirs(CACHE, exist_ok=True)


_U = None
def files():
    global _U
    if _U is None: _U = ss_lib.universe() or set()
    F = sorted(f for f in os.listdir(STORE) if f.endswith(".npz"))
    return [f for f in F if f in _U] if _U else F


def chunked(stage, fn):
    t0 = time.time(); F = files(); done = 0
    for i in range(0, len(F), CHUNK):
        p = os.path.join(CACHE, f"{stage}_{i:06d}.pkl")
        if os.path.exists(p): done += 1; continue
        if time.time() - t0 > BUDGET: print(f"{stage}: {done}/{math.ceil(len(F)/CHUNK)} chunks, call again"); return False
        pickle.dump(fn(F[i:i + CHUNK]), open(p, "wb")); done += 1
    print(f"{stage}: DONE ({done} chunks)"); return True


def merged(stage):
    return [pickle.load(open(os.path.join(CACHE, f), "rb")) for f in sorted(os.listdir(CACHE)) if f.startswith(stage + "_")]


def main():
    st = sys.argv[1] if len(sys.argv) > 1 else ""
    if st == "unzip":
        z = zipfile.ZipFile(ss_lib.find("stocks")); name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        out = os.path.join(D, "stocks_unzipped.csv")
        if not os.path.exists(out):
            with z.open(name) as src, open(out + ".part", "wb") as dst: shutil.copyfileobj(src, dst, 1 << 24)
            os.rename(out + ".part", out)
        print("unzip: DONE", os.path.getsize(out) >> 20, "MB")
    elif st == "bucket":
        src = os.environ.get("SEP_CSV") or os.path.join(D, "stocks_unzipped.csv")
        bdir = os.environ.get("BUCKETS") or os.path.join(D, "buckets")
        ok = ss_lib.bucketize_resumable(src, bdir, os.path.join(CACHE, "bucket_state.json"), ss_lib.universe(), BUDGET)
        print("bucket:", "DONE" if ok else "call again")
    elif st == "store2":
        import glob
        bdir = os.environ.get("BUCKETS") or os.path.join(D, "buckets"); os.makedirs(STORE, exist_ok=True)
        src = os.environ.get("SEP_CSV") or os.path.join(D, "stocks_unzipped.csv")
        header = open(src).readline().strip().split(","); t0 = time.time()
        donef = os.path.join(CACHE, "store2_done.txt"); done = set(open(donef).read().split()) if os.path.exists(donef) else set()
        for b in sorted(glob.glob(os.path.join(bdir, "b*.csv"))):
            if os.path.basename(b) in done: continue
            if time.time() - t0 > BUDGET: print(f"store2: {len(done)} buckets done, call again"); break
            n = ss_lib.store_from_bucket(b, STORE, header); done.add(os.path.basename(b)); open(donef, "a").write(os.path.basename(b) + "\n")
        else:
            print("store2: DONE", len(os.listdir(STORE)), "tickers")
    elif st == "store":
        src = os.environ.get("SEP_CSV") or os.path.join(D, "stocks_unzipped.csv")
        ok = ss_lib.build_store_resumable(src, STORE, os.path.join(CACHE, "store_state.json"), BUDGET, allow=ss_lib.universe())
        print("store:", "DONE" if ok else "call again", len(files()), "tickers")
    elif st == "bands":
        if chunked("bandstats", lambda F: dict(E.band_stats(STORE, F))):
            per = defaultdict(list)
            for part in merged("bandstats"):
                for m, lst in part.items(): per[m].extend(lst)
            pickle.dump(E.assign_bands(per), open(os.path.join(CACHE, "band.pkl"), "wb")); print("band.pkl written")
    elif st == "bench":
        band = pickle.load(open(os.path.join(CACHE, "band.pkl"), "rb")); d0, nd = 10000, 12000      # 1997-05 .. 2030
        if chunked("benchacc", lambda F: E.bench_acc(STORE, F, band, d0, nd)):
            S = sum(p[0] for p in merged("benchacc")); C = sum(p[1] for p in merged("benchacc"))
            pickle.dump(E.bench_from(S, C, d0), open(os.path.join(CACHE, "bench.pkl"), "wb")); print("bench.pkl written")
    elif st == "events":
        band = pickle.load(open(os.path.join(CACHE, "band.pkl"), "rb")); bench = pickle.load(open(os.path.join(CACHE, "bench.pkl"), "rb"))
        ann = ss_lib.announcements(ss_lib.find("events")); bad, good = ss_lib.delistings(ss_lib.find("actions"))
        chunked("events", lambda F: E.pass_events(STORE, F, band, bench, ann, bad, good))
    elif st == "final":
        final()
    else:
        print(__doc__)


def final():
    log = os.path.join(D, "..", "run_pead1.log")
    if os.path.exists(log): sys.exit("final already run once -- see data/run_pead1.log")
    if not DOC[1] or hashlib.sha256(open(DOC[0], "rb").read()).hexdigest() != DOC[1]: sys.exit("PREREGISTRATION_PEAD1.md missing/changed or harness not pinned -- refused")
    for f, h in PIN_CODE.items():
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")
    out = []
    def P(s=""): print(s); out.append(s)
    P("pead1_run.py final   PREREGISTRATION_PEAD1 sha matches\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    ev = [e for part in merged("events") for e in part]
    ev = E.fill_costs(E.signals(ev))
    yr = lambda d: int(str(np.datetime64(int(d), "D"))[:4])
    for e in ev: e["y"] = yr(e["entry"])
    L = [e for e in ev if e["long"] and "x60" in e and e["y"] >= 2005]
    net = lambda e, H=60: e[f"x{H}"] - e["cost"]
    def mt(S, H=60, g=False):
        return E.clustered_mean_t([(e[f"x{H}"] if g else net(e, H)) for e in S], [E.quarter(e["entry"]) for e in S])
    MS = [e for e in L if e["band"] in ("M", "S")]
    m, t, n = mt(MS); g1 = m > 0 and t >= 2.0
    P(f"  G1 M+S long top-decile EAR, 60d net excess {m*100:+.2f}%  t {t:+.2f}  n {n}  -> {'PASS' if g1 else 'FAIL'}")
    eras = [mt([e for e in MS if lo <= e["y"] <= hi]) for lo, hi in ((2005, 2012), (2013, 2019), (2020, 2026))]
    recent = mt([e for e in MS if e["y"] >= 2018])
    g2 = all(x[0] > 0 for x in eras) and recent[0] > 0 and recent[1] >= 2.0
    P("  G2 eras " + "  ".join(f"{x[0]*100:+.2f}% (t {x[1]:+.2f}, n {x[2]})" for x in eras) + f"   2018-26 {recent[0]*100:+.2f}% (t {recent[1]:+.2f}, n {recent[2]})  -> {'PASS' if g2 else 'FAIL'}")
    bm = {b: mt([e for e in MS if e["band"] == b]) for b in ("M", "S")}
    g3 = all(v[0] > 0 for v in bm.values())
    P("  G3 bands " + "  ".join(f"{b} {v[0]*100:+.2f}% (t {v[1]:+.2f}, n {v[2]})" for b, v in bm.items()) + f"  -> {'PASS' if g3 else 'FAIL'}")
    # G4: random announcements, same band x month counts, gross excess
    rng = np.random.default_rng(1); pool = defaultdict(list); need = defaultdict(int)
    for e in ev:
        if e["band"] in ("M", "S") and "x60" in e and e["y"] >= 2005: pool[(e["band"], E.month_of(e["entry"]).item())].append(e["x60"])
    for e in MS: need[(e["band"], E.month_of(e["entry"]).item())] += 1
    real = np.mean([e["x60"] for e in MS]); null = []
    for _ in range(500):
        s = []
        for k_, c in need.items():
            p = pool[k_]; s.extend(rng.choice(p, size=c, replace=len(p) < c))
        null.append(np.mean(s))
    q95 = float(np.quantile(null, 0.95)); g4 = real > q95
    P(f"  G4 gross excess {real*100:+.2f}% vs random-announcement null 95th pct {q95*100:+.2f}% (median {np.median(null)*100:+.2f}%)  -> {'PASS' if g4 else 'FAIL'}")
    # G5: calendar-time daily portfolio of open positions, excess returns, costs on entry day, 2018+
    daily = defaultdict(list)
    for e in MS:
        if "path" not in e: continue
        p = e["path"].astype(float).copy(); p[0] -= e["cost"]
        for i, r in enumerate(p): daily[e["entry"] + i * 7 // 5].append(r)        # trading-day -> approx calendar mapping
    ds = sorted(daily); pr = np.array([np.mean(daily[d]) for d in ds]); yrs = np.array([yr(d) for d in ds])
    rec = pr[yrs >= 2018]; sh = rec.mean() / rec.std() * math.sqrt(252) if len(rec) > 50 else float("nan"); g5 = sh >= 0.5
    P(f"  G5 calendar-time excess portfolio 2018+: Sharpe {sh:+.2f} (days {len(rec)})  -> {'PASS' if g5 else 'FAIL'}")
    P("\n  reported:")
    for b in ("L", "X"):
        v = mt([e for e in L if e["band"] == b]); P(f"    band {b}: net {v[0]*100:+.2f}% (t {v[1]:+.2f}, n {v[2]})")
    v = mt([e for e in MS if "x20" in e], H=20); P(f"    20-day hold M+S: net {v[0]*100:+.2f}% (t {v[1]:+.2f})")
    v = mt(MS, g=True); P(f"    gross (before cost) M+S: {v[0]*100:+.2f}% (t {v[1]:+.2f});  median round-trip cost {np.median([e['cost'] for e in MS])*1e4:.0f} bp")
    v = E.clustered_mean_t([e["x60"] - e["cost"] - 0.0006 for e in MS], [E.quarter(e["entry"]) for e in MS]); P(f"    with 2 x 0.03% currency conversion: {v[0]*100:+.2f}% (t {v[1]:+.2f})")
    Bot = [e for e in ev if e["band"] in ("M", "S") and np.isfinite(e.get("thr", np.nan)) and "x60" in e and e["y"] >= 2005]
    P(f"    all M+S announcements, 60d gross excess {np.mean([e['x60'] for e in Bot])*100:+.2f}% (n {len(Bot)})")
    for b in ("M", "S"):
        P(f"    EDGE spread {b}: median {np.nanmedian([e['spread'] for e in ev if e['band'] == b])*1e4:.0f} bp")
    P(f"\n  VERDICT  G1 {'P' if g1 else 'F'} G2 {'P' if g2 else 'F'} G3 {'P' if g3 else 'F'} G4 {'P' if g4 else 'F'} G5 {'P' if g5 else 'F'}  -> {'PASS' if all((g1, g2, g3, g4, g5)) else 'FAIL'}")
    open(log, "w").write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
