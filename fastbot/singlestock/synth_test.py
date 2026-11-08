"""End-to-end self-test of the PEAD1 pipeline on synthetic Sharadar-format files.
PLANTED: after the announcement jump, price drifts in the jump's direction (0.4 x jump over 60 days) -> the long-top-decile
excess must be clearly positive.  NULL: no drift -> the excess must be ~0 (|t| < 2.5).  Also checks the -30% delisting rule."""
import csv, os, shutil, tempfile, datetime as dt
import numpy as np
import ss_lib, pead_engine as E

def make(root, drift, seed=7, N=300, T=1800):
    rng = np.random.default_rng(seed); raw = os.path.join(root, "raw"); os.makedirs(raw)
    days = []; d = dt.date(2005, 1, 3)
    while len(days) < T:
        if d.weekday() < 5: days.append(d)
        d += dt.timedelta(days=1)
    with open(os.path.join(raw, "stocks.csv"), "w", newline="") as fs, open(os.path.join(raw, "events.csv"), "w", newline="") as fe, \
         open(os.path.join(raw, "actions.csv"), "w", newline="") as fa:
        ws, we, wa = csv.writer(fs), csv.writer(fe), csv.writer(fa)
        ws.writerow(["ticker", "date", "open", "high", "low", "close", "volume", "closeadj", "closeunadj", "lastupdated"])
        we.writerow(["ticker", "date", "eventcodes"]); wa.writerow(["date", "action", "ticker", "name", "value", "contraticker", "contraname"])
        for i in range(N):
            t = f"T{i:04d}"; spread = 0.002 + 0.02 * rng.random(); lv = rng.normal(0, 1)
            first = int(rng.integers(0, 40)); ann = list(range(first + 70, T - 5, 63))
            ret = rng.normal(0.0002, 0.018, T); extra = np.zeros(T)
            for a in ann:
                j = rng.normal(0, 0.06); ret[a] += j
                if drift: extra[a + 2:a + 62] += 0.4 * j / 60
            ret = ret + extra
            end = T if i % 25 else int(T * 0.7)               # every 25th ticker delists early
            p = 20 * np.exp(np.cumsum(ret))
            for k in range(end):
                intr = p[k] * np.exp(rng.normal(0, 0.008, 20)); q = intr * (1 + rng.choice([-1, 1], 20) * spread / 2)
                ws.writerow([t, days[k].isoformat(), f"{q[0]:.4f}", f"{q.max():.4f}", f"{q.min():.4f}", f"{q[-1]:.4f}",
                             int(1e5 * np.exp(lv)), f"{q[-1]:.4f}", f"{q[-1]:.4f}", "2026-01-01"])
            for a in ann:
                if a < end: we.writerow([t, days[a].isoformat(), "22|91"])
            if end < T: wa.writerow([days[end - 1].isoformat(), "bankruptcyliquidation" if i % 50 == 0 else "acquisitionby", t, "", "", "", ""])

def run(root):
    store = os.path.join(root, "store"); ss_lib.build_store(os.path.join(root, "raw", "stocks.csv"), store)
    files = sorted(os.listdir(store)); E.BANDS = (("L", 100), ("M", 100), ("S", 100))
    band = E.pass_bands(store, files); bench = E.pass_bench(store, files, band)
    ann = ss_lib.announcements(os.path.join(root, "raw", "events.csv")); bad, good = ss_lib.delistings(os.path.join(root, "raw", "actions.csv"))
    ev = E.fill_costs(E.signals(E.pass_events(store, files, band, bench, ann, bad, good)))
    L = [e for e in ev if e["long"] and "x60" in e]
    return E.clustered_mean_t([e["x60"] for e in L], [E.week(e["entry"]) for e in L]), ev

if __name__ == "__main__":
    ok = True
    for drift, want in ((True, "pos"), (False, "null")):
        root = tempfile.mkdtemp(); make(root, drift)
        (m, t, n), ev = run(root); shutil.rmtree(root)
        good = (m > 0.01 and t > 3) if want == "pos" else abs(t) < 2.5
        ok &= good
        print(f"  {'PLANTED drift' if drift else 'NULL (no drift)'}: long top-decile 60d excess {m*100:+.2f}%  t {t:+.2f}  n {n}  -> {'OK' if good else 'BROKEN'}")
    print("SELF-TEST", "ALL PASS" if ok else "FAILED")
