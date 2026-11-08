#!/usr/bin/env python3
"""TF1 harness (PREREGISTRATION_TF1 + TF1.1). One run per timeframe:  python3 tf1_run.py 30m|1h|4h|1m   then   python3 tf1_run.py verdict
Patterns = patterns.py 1.0 detect() (v2, frozen). Structure = struct15.structure_events (v51, pinned).
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, json, math, hashlib, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E, patterns as PT
from struct15 import structure_events
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, "..")
DOCS = {os.path.join(FB, "PREREGISTRATION_TF1.md"): None, os.path.join(FB, "PREREGISTRATION_TF1.1.md"): None}
OUTD = os.path.join(FB, "data", "tf1"); INS = ("NAS100_USD", "SPX500_USD"); T_BONF = 3.4; NDRAW = 20
ERAS = ((2005, 2012), (2013, 2019), (2020, 2026)); ERAS_1M = ((2022, 2023), (2024, 2026))
END = pd.Timestamp("2026-09-26", tz="UTC"); START_1M = pd.Timestamp("2022-01-03", tz="UTC")
RULE = {"30m": "30min", "1h": "1h", "4h": "4h"}; STEP = {"1m": 60, "30m": 1800, "1h": 3600, "4h": 14400}

def policy():
    r = {}
    for row in csv.DictReader(open(os.path.join(FB, "data", "policy_rates.csv"))):
        if row["currency"] == "USD": r[row["month"]] = float(row["rate_pct"]) / 100
    return r
POL = None
def financing(t0, t1, side):
    """BOUNCE1.1 rule: nights crossed at 17:00 New York; Friday night counts 3."""
    global POL
    POL = POL or policy()
    a = t0.tz_convert(E.TZ); b = t1.tz_convert(E.TZ); cost = 0.0
    d = a.normalize() + pd.Timedelta(hours=17)
    if d <= a: d += pd.Timedelta(days=1)
    while d <= b:
        if d.weekday() < 5:
            days = 3 if d.weekday() == 4 else 1; r = POL.get(d.strftime("%Y-%m"), 0.02)
            cost += days / 365 * ((r + 0.025) if side > 0 else -(r - 0.025))
        d += pd.Timedelta(days=1)
    return cost

def load_ohlc(data_dir, inst, suf, step):
    """Same construction as patterns.load_ohlc 1.0 (mid OHLC, spread = (ask close - bid close)/mid); datetime handling made
    explicit because the installed pandas returns object arrays from index.to_numpy()."""
    stem = inst.replace("_", "").lower(); F = {}
    for side in ("bid", "ask"):
        d = pd.read_csv(os.path.join(data_dir, f"{stem}_{side}_{suf}.csv")); d.columns = ["t", "open", "high", "low", "close", "volume"]
        d["t"] = pd.to_datetime(d["t"], utc=True); F[side] = d.drop_duplicates("t").set_index("t")
    idx = F["bid"].index.intersection(F["ask"].index).sort_values(); b, a = F["bid"].loc[idx], F["ask"].loc[idx]
    m = {k: (b[k].to_numpy(float) + a[k].to_numpy(float)) / 2 for k in ("open", "high", "low", "close")}
    local = idx.tz_convert(E.TZ); dtt = np.diff(idx.asi8) / 1e9
    return dict(t=idx, local=local, O=m["open"], H=m["high"], L=m["low"], C=m["close"], V=b["volume"].to_numpy(float),
                spread=(a["close"].to_numpy(float) - b["close"].to_numpy(float)) / m["close"], consec=np.concatenate([[False], dtt == step]),
                hour=local.hour.to_numpy(), year=local.year.to_numpy(), day=local.normalize().to_numpy())

def load(inst, tf):
    if tf == "1m":
        D = load_ohlc(os.path.join(FB, "data", "m1_tf1"), inst, "1m", 60)
        m = (D["t"] >= START_1M) & (D["t"] < END)
        return {k: (v[m] if hasattr(v, "__len__") and len(v) == len(m) else v) for k, v in D.items()}
    D15 = load_ohlc(os.path.join(FB, "data", "v24"), inst, "15m", 900)
    df = pd.DataFrame({"O": D15["O"], "H": D15["H"], "L": D15["L"], "C": D15["C"], "V": D15["V"], "spread": D15["spread"]}, index=D15["t"])
    df = df[df.index < END]
    g = df.resample(RULE[tf], origin="epoch")
    R = pd.DataFrame({"O": g["O"].first(), "H": g["H"].max(), "L": g["L"].min(), "C": g["C"].last(), "V": g["V"].sum(), "spread": g["spread"].first()}).dropna()
    idx = R.index; local = idx.tz_convert(E.TZ); dtt = np.diff(idx.asi8) / 1e9
    return dict(t=idx, local=local, O=R["O"].to_numpy(float), H=R["H"].to_numpy(float), L=R["L"].to_numpy(float), C=R["C"].to_numpy(float),
                V=R["V"].to_numpy(float), spread=R["spread"].to_numpy(float), consec=np.concatenate([[False], dtt == STEP[tf]]),
                hour=local.hour.to_numpy(), year=local.year.to_numpy(), day=local.normalize().to_numpy())

def trades24(D, mask, side, hold, step):
    """TF1.1 execution for 24h bars: v2 stop entry, exit open hold bars later, span cap, 4/day cap."""
    n = len(D["C"]); ok = mask & D["consec"]; out, busy, per = [], -1, {}
    for i in np.flatnonzero(ok):
        j, k = i + 1, i + 1 + hold
        if k >= n or j <= busy: continue
        if (D["t"][k] - D["t"][j]).total_seconds() > 2 * hold * step: continue
        trig = D["H"][i] if side > 0 else D["L"][i]
        if not ((D["H"][j] >= trig) if side > 0 else (D["L"][j] <= trig)): continue
        fill = max(trig, D["O"][j]) if side > 0 else min(trig, D["O"][j]); d = D["day"][j]
        if per.get(d, 0) >= E.MAX_PER_DAY: continue
        out.append((j, k, side, fill)); busy = k; per[d] = per.get(d, 0) + 1
    return out

def pat_pnl(D, tr, tf):
    r, yr, dy = [], [], []
    for j, k, sd, fill in tr:
        ent = fill * (1 + sd * D["spread"][j] / 2); ex = D["O"][k] * (1 - sd * D["spread"][k] / 2)
        v = sd * (ex - ent) / ent
        if tf != "1m": v -= financing(D["t"][j], D["t"][k], sd)
        r.append(v); yr.append(D["year"][j]); dy.append(str(D["day"][j])[:10])
    return np.array(r), np.array(yr), np.array(dy)

def struct_trades(D, tf, k_, H=16):
    ev = structure_events(D["H"], D["L"], D["C"], k_); n = len(D["C"]); out = []
    for j, kind, s in ev:
        a, b = j + 1, j + H
        if b >= n: continue
        if (D["t"][b] - D["t"][a]).total_seconds() > 2 * H * STEP[tf]: continue
        if tf == "1m" and not (D["day"][a] == D["day"][b] and E.SESSION[0] <= D["hour"][a] < E.SESSION[1] and E.SESSION[0] <= D["hour"][b] < E.SESSION[1]): continue
        g = s * (D["C"][b] / D["O"][a] - 1) - D["spread"][a]
        if tf != "1m": g -= financing(D["t"][a], D["t"][b], s)
        out.append((kind, s, a, b, g))
    return out

def cl_t(r, days):
    if len(r) < 2: return float("nan"), float("nan")
    df = pd.DataFrame({"r": r, "d": days}); s = df.groupby("d")["r"].sum(); n = len(r); m = r.mean()
    u = df.assign(u=df["r"] - m).groupby("d")["u"].sum(); se = math.sqrt((u ** 2).sum()) / n
    return m, (m / se if se > 0 else float("nan"))

def matched_random(D, mask, side, tf, seed, runner):
    """Random entries with the test's own firing rate in each (NY hour x year) cell."""
    rng = np.random.default_rng(seed); cell = D["hour"] * 10000 + D["year"]; m = np.zeros(len(mask), bool)
    for c in np.unique(cell[mask]):
        sel = cell == c; p = mask[sel].mean(); m[sel] = rng.random(sel.sum()) < p
    return runner(m, side)

def run(tf, only=None, part="PS", half=None):
    """Chunked execution (mechanical only, 2026-10-07): one instrument / part / half of the pattern list per call, so each fits
    the VM's 175 s limit. The computation per test is unchanged; verdict() pools the chunk files."""
    tag = "_".join(x for x in (tf, only, part if part != "PS" else None, str(half) if half is not None else None) if x)
    out = os.path.join(OUTD, f"tf1_{tag}.json")
    if os.path.exists(out): sys.exit(f"{tag} already run")
    os.makedirs(OUTD, exist_ok=True); res = {}
    for inst in ([only] if only else INS):
        D = load(inst, tf); hold = E.H_HOLD
        runner = (lambda m, s: PT.trades(D, m, s)) if tf == "1m" else (lambda m, s: trades24(D, m, s, hold, STEP[tf]))
        P, BI = PT.detect(D) if "P" in part else ({}, set())
        names = sorted(P)
        if half is not None:
            gi, gn = (half, 2) if isinstance(half, int) else map(int, half.split("of"))
            names = [nm for i_, nm in enumerate(names) if i_ * gn // len(names) == gi]
        for name in names:
            bull, bear = P[name]
            for side, mask in ((1, bull), (-1, bear)):
                r, yr, dy = pat_pnl(D, runner(mask, side), tf)
                rr = [pat_pnl(D, matched_random(D, mask, side, tf, 1000 + s, runner), tf)[0] for s in range(NDRAW)] if mask.any() else []
                res.setdefault(f"P {name} {'long' if side > 0 else 'short'}", []).append(dict(r=r.tolist(), yr=yr.tolist(), dy=dy.tolist(), rand=np.concatenate(rr).tolist() if rr else []))
        for kind in (("BOS", "CHOCH") if "S" in part else ()):
            rows = []
            for k_ in (2, 3, 4, 5):
                for kd, s, a, b, g in struct_trades(D, tf, k_):
                    if kd == kind: rows.append((k_, g, int(D["year"][a]), str(D["day"][a])[:10], a, s))
            # random benchmark: same entry bars' hour/year cells, random sides? -> same side, random bars
            cell_mask = {1: np.zeros(len(D["C"]), bool), -1: np.zeros(len(D["C"]), bool)}
            for k_, g, y, d, a, s in rows: cell_mask[s][a - 1] = True
            rand = []
            for s_ in (1, -1):
                if not cell_mask[s_].any(): continue
                for sd in range(NDRAW):
                    m = matched_random(D, cell_mask[s_], s_, tf, 5000 + sd, lambda mm, ss: np.flatnonzero(mm))
                    for i in m:
                        a, b = i + 1, i + 16
                        if b >= len(D["C"]) or (D["t"][b] - D["t"][a]).total_seconds() > 32 * STEP[tf]: continue
                        if tf == "1m" and not (D["day"][a] == D["day"][b] and E.SESSION[0] <= D["hour"][a] < E.SESSION[1] and E.SESSION[0] <= D["hour"][b] < E.SESSION[1]): continue
                        g = s_ * (D["C"][b] / D["O"][a] - 1) - D["spread"][a] - (financing(D["t"][a], D["t"][b], s_) if tf != "1m" else 0)
                        rand.append(g)
            res.setdefault(f"S {kind}", []).append(dict(r=[x[1] for x in rows], k=[x[0] for x in rows], yr=[x[2] for x in rows], dy=[x[3] for x in rows], rand=rand))
        print(f"  {tf} {inst}: {len(D['C']):,} bars done", flush=True)
    json.dump(res, open(out, "w")); print("wrote", out)

def verdict():
    tfs = ("1m", "30m", "1h", "4h"); L = ["TF1 verdict (PREREGISTRATION_TF1 + TF1.1)", "  I am not a financial adviser. This is a measurement, not a recommendation.", ""]
    npass = 0
    for tf in tfs:
        import glob
        files = sorted(f for f in glob.glob(os.path.join(OUTD, f"tf1_{tf}*.json")) if os.path.basename(f) == f"tf1_{tf}.json" or os.path.basename(f).startswith(f"tf1_{tf}_"))
        if not files: L.append(f"  {tf}: NOT RUN"); continue
        res = {}
        for f in files:
            for k, v in json.load(open(f)).items(): res.setdefault(k, []).extend(v)
        L.append(f"  {tf}:  test                      n      mean bp   t(date)   vs random t   eras -> verdict")
        for name, parts in sorted(res.items()):
            r = np.concatenate([np.array(x["r"]) for x in parts]); yr = np.concatenate([np.array(x["yr"]) for x in parts]); dy = np.concatenate([np.array(x["dy"]) for x in parts])
            rand = np.concatenate([np.array(x["rand"]) for x in parts]) if any(len(x["rand"]) for x in parts) else np.array([])
            if len(r) < 2: L.append(f"    {name:<26} n {len(r)} -> FAIL (too few)"); continue
            m, t = cl_t(r, dy)
            tr = (m - rand.mean()) / math.sqrt(np.var(r, ddof=1) / len(r) + np.var(rand, ddof=1) / len(rand)) if len(rand) > 1 else float("nan")
            eras = ERAS_1M if tf == "1m" else ERAS; em = [r[(yr >= a) & (yr <= b)].mean() if ((yr >= a) & (yr <= b)).any() else float("nan") for a, b in eras]
            kok = True
            if name.startswith("S "):
                k = np.concatenate([np.array(x["k"]) for x in parts]); kok = all(np.sign(r[k == kk].mean()) == np.sign(m) for kk in (2, 3, 4, 5) if (k == kk).any())
            ok = m > 0 and t >= T_BONF and tr >= 2.0 and all(e > 0 for e in em) and len(r) >= 200 and kok
            rec = (not ok) and tf != "1m" and m > 0 and len(r) >= 200 and em[0] <= 0 and all(e > 0 for e in em[1:])
            npass += ok
            L.append(f"    {name:<26} {len(r):>6} {m*1e4:+8.2f} {t:+8.2f} {tr:+10.2f}   " + " ".join(f"{e*1e4:+.1f}" for e in em) + f" -> {'PASS' if ok else 'FAIL'}{'  (recent-regime candidate)' if rec else ''}")
    L.append(f"\n  PASSES: {npass} of 168 (Bonferroni t >= {T_BONF})")
    open(os.path.join(FB, "data", "run_tf1_verdict.log"), "w").write("\n".join(L) + "\n"); print("\n".join(L))

if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else ""
    if a in ("1m", "30m", "1h", "4h"):
        x = sys.argv[2:]; run(a, x[0] if len(x) > 0 else None, x[1] if len(x) > 1 else "PS", (x[2] if "of" in x[2] else int(x[2])) if len(x) > 2 else None)
    elif a == "verdict": verdict()
    else: print(__doc__)
