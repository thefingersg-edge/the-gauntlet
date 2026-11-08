#!/usr/bin/env python3
"""ORBCORE1 harness (PREREGISTRATION_ORBCORE1.md, sha 66c0aca9...): the bare opening-range breakout core on 7 markets not used before.
    python3 orbcore1_run.py --self-test
    python3 orbcore1_run.py run        -> data/orbcore1/run_orbcore1.log  (refuses to run twice)
Mechanical readings fixed here BEFORE the run (logged in PROVENANCE):
  * Source: OANDA 5m bid/ask CSVs, times = UTC bar starts. Mid OHLC; spr_bp = (ask_open / bid_open - 1) x 1e4 at each bar's open.
    Spreads <= 0 (early source data) take that market's 2012-14 median of positive spreads.
  * Local clock per market (DST-aware). Range bars = bars starting in [range_start, +60 min). Coverage = 5 min x bars, and must be >= 50.
  * Signal = the first bar starting in [cash_open, +60 min) whose CLOSE is beyond HH + delta / LL - delta. Entry at the next bar's open, if that bar
    starts before the exit time. Exit at the close of the last bar starting before the exit time.
  * Accounting via unger2_run.trade() (half-spread at the entry and exit bars). No position crosses 17:00 New York, so financing is 0 (checked).
  * Pooled t is clustered by UTC entry date across markets. Eras use the entry year.
  * Reported stop variants: Unger's stop at the range edge (HH for a long, LL for a short) and a wide stop at 2 x range from entry. The stop is checked
    from the bar after entry and fills at the level, or at the open if gapped.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, math, hashlib
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE)
import unger2_run as U
SPEC = os.path.join(FB, "PREREGISTRATION_ORBCORE1.md"); SPEC_SHA = "66c0aca9d467bf001150558fc5b63b724c32155cd06b42131ec4661b130f1050"
OUT = os.path.join(FB, "data", "orbcore1"); D = os.path.join(FB, "data")
DISC = "I am not a financial adviser. This is a measurement, not a recommendation."
MK = {  # name: (file stem, folder, tz, range start, cash open, exit)  minutes after local midnight
    "EU50": ("eu50eur", "v38", "Europe/Berlin", 480, 540, 1320),
    "UK100": ("uk100gbp", "v38", "Europe/London", 420, 480, 1260),
    "SPX500": ("spx500usd", "", "America/New_York", 510, 570, 960),
    "NAS100": ("nas100usd", "", "America/New_York", 510, 570, 960),
    "US30": ("us30usd", "", "America/New_York", 510, 570, 960),
    "JP225": ("jp225usd", "v38", "Asia/Tokyo", 480, 540, 900),
    "AU200": ("au200aud", "v38", "Australia/Sydney", 540, 600, 960),
}
ERAS = ((2005, 2012), (2013, 2019), (2020, 2026))


def pin():
    if hashlib.sha256(open(SPEC, "rb").read()).hexdigest() != SPEC_SHA: sys.exit("spec changed -- refused")


def load(stem, folder):
    p = os.path.join(D, folder, f"{stem}_%s_5m.csv")
    b = pd.read_csv(p % "bid"); a = pd.read_csv(p % "ask"); m = b.merge(a, on="time", suffixes=("_b", "_a"))
    t = pd.to_datetime(m["time"]).to_numpy().astype("datetime64[m]")
    mid = {k: ((m[f"{k}_b"] + m[f"{k}_a"]) / 2).to_numpy(float) for k in ("open", "high", "low", "close")}
    spr = ((m["open_a"] / m["open_b"] - 1) * 1e4).to_numpy(float)
    yr = pd.DatetimeIndex(t.astype("datetime64[ns]")).year.to_numpy()
    good = (spr > 0) & (yr >= 2012) & (yr <= 2014)
    med = float(np.median(spr[good])) if good.any() else float(np.median(spr[spr > 0]))
    spr = np.where(spr > 0, spr, med)
    return dict(t=t, o=mid["open"], h=mid["high"], l=mid["low"], c=mid["close"], spr=spr, roll=np.zeros(len(t), bool), kind="cfd")


def orb(B, tz, r0, c0, ex, stop=None):
    """stop: None | 'edge' | 'wide'. Returns (trade frame, coverage-by-year frame)."""
    lt = U.local(B["t"], tz); mm = (lt.hour * 60 + lt.minute).to_numpy(); day = lt.normalize().tz_localize(None).to_numpy()
    o, h, l, c = B["o"], B["h"], B["l"], B["c"]
    ud, st = np.unique(day, return_index=True); en = np.r_[st[1:], len(day)]
    trs, cov = [], []
    for di in range(len(ud)):
        s, e = st[di], en[di]; m = mm[s:e]
        if pd.Timestamp(ud[di]).weekday() >= 5: continue
        rng = np.flatnonzero((m >= r0) & (m < r0 + 60)) + s
        cov.append((pd.Timestamp(ud[di]).year, len(rng) * 5 >= 50))
        if len(rng) * 5 < 50: continue
        HH, LL = h[rng].max(), l[rng].min(); dl = HH - LL
        if dl <= 0: continue
        up, dn = HH + dl, LL - dl
        bars = [i for i in range(s, e) if c0 <= mm[i] < ex]
        if not bars: continue
        sig = None
        for k, i in enumerate(bars):
            if mm[i] >= c0 + 60: break
            if c[i] > up: sig = (k, 1); break
            if c[i] < dn: sig = (k, -1); break
        if sig is None or sig[0] + 1 >= len(bars): continue
        k, sd = sig; i0 = bars[k + 1]; px0 = o[i0]
        lv = None if stop is None else ((HH if sd > 0 else LL) if stop == "edge" else px0 - sd * 2 * dl)
        done = False
        for i in bars[k + 2:]:
            if lv is not None and ((sd > 0 and l[i] <= lv) or (sd < 0 and h[i] >= lv)):
                fill = min(o[i], lv) if sd > 0 else max(o[i], lv)
                trs.append(U.trade(B, {}, i0, px0, i, fill, sd)); done = True; break
        if not done:
            i1 = bars[-1]; trs.append(U.trade(B, {}, i0, px0, i1, c[i1], sd))
    return U.frame(trs), pd.DataFrame(cov, columns=["yr", "ok"])


def mstats(T):
    t = U.ct(T["net_bp"], T["day"]) if len(T) > 2 else float("nan")
    return f"n {len(T):5d}  net {T['net_bp'].mean():+6.2f} bp (t {t:+.2f})  gross {T['gross_bp'].mean():+6.2f}  win {(T['net_bp'] > 0).mean() * 100:.0f}%"


def run():
    pin(); os.makedirs(OUT, exist_ok=True); P = os.path.join(OUT, "run_orbcore1.log")
    if os.path.exists(P): sys.exit("already run")
    L = ["ORBCORE1 -- the bare opening-range breakout core (no filters, no stop) on 7 markets not used before", "  " + DISC, ""]
    allT, per, var = [], {}, {}
    for nm, (stem, fold, tz, r0, c0, ex) in MK.items():
        B = load(stem, fold); T, cov = orb(B, tz, r0, c0, ex)
        if not len(T):                                        # mechanical (logged): no bars in the range hour -> untestable, counts as NOT positive for G3
            per[nm] = pd.DataFrame({"net_bp": [np.nan]})
            L.append(f"  {nm:7s} n     0  -- no bars in the pre-open range hour on this CFD (range-hour coverage 0%); counts as not positive for G3"); continue
        if len(T) and (T["fin"].abs() > 0).any(): sys.exit(f"{nm}: a position crossed 17:00 NY -- harness assumption broken")
        T["mkt"] = nm; allT.append(T); per[nm] = T
        var[nm] = {v: orb(B, tz, r0, c0, ex, stop=v)[0] for v in ("edge", "wide")}
        cy = cov.groupby("yr")["ok"].mean()
        L.append(f"  {nm:7s} {mstats(T)}   | {pd.Timestamp(T['t0'].min()).date()} -> {pd.Timestamp(T['t0'].max()).date()}")
        L.append(f"          long {T[T.side > 0]['net_bp'].mean():+.2f} (n {(T.side > 0).sum()}), short {T[T.side < 0]['net_bp'].mean():+.2f} (n {(T.side < 0).sum()});"
                 f"  edge stop {var[nm]['edge']['net_bp'].mean():+.2f};  wide stop {var[nm]['wide']['net_bp'].mean():+.2f}")
        L.append("          range-hour coverage by year: " + " ".join(f"{y % 100:02d}:{v * 100:.0f}" for y, v in cy.items()))
    A = pd.concat(allT, ignore_index=True)
    A["udate"] = pd.DatetimeIndex(A["t0"].astype("datetime64[ns]")).normalize()
    m, t = A["net_bp"].mean(), U.ct(A["net_bp"], A["udate"])
    yr = pd.DatetimeIndex(A["t0"].astype("datetime64[ns]")).year
    ers = [A[(yr >= a) & (yr <= b)]["net_bp"].mean() for a, b in ERAS]
    npos = sum(bool(per[k]["net_bp"].mean() > 0) for k in per)
    pl = U.placebo(A); p95 = float(np.percentile(pl, 95))
    g1 = m > 0 and t >= 2.0; g2 = all(e > 0 for e in ers); g3 = npos >= 5; g4 = m > p95
    E = pd.concat([var[k]["edge"] for k in var], ignore_index=True); W = pd.concat([var[k]["wide"] for k in var], ignore_index=True)
    L += ["", f"  POOLED: {mstats(A.assign(day=A['udate']))}",
          "  eras " + "  ".join(f"{a}-{b % 100:02d} {e:+.2f}" for (a, b), e in zip(ERAS, ers)) + f";  markets positive {npos}/7;  placebo mean {pl.mean():+.2f}, 95th pct {p95:+.2f}",
          f"  reported: pooled with Unger's edge stop {E['net_bp'].mean():+.2f} bp;  with the wide 2x stop {W['net_bp'].mean():+.2f} bp",
          f"  G1 {'PASS' if g1 else 'FAIL'} (t >= 2.0)  G2 {'PASS' if g2 else 'FAIL'}  G3 {'PASS' if g3 else 'FAIL'} (>= 5 of 7)  G4 {'PASS' if g4 else 'FAIL'}"
          f"  -> ORBCORE1 {'PASS' if g1 and g2 and g3 and g4 else 'FAIL'}"]
    A.drop(columns=["udate"]).to_csv(os.path.join(OUT, "orbcore1_trades.csv"), index=False)
    open(P, "w").write("\n".join(L) + "\n"); print("\n".join(L))


def self_test():
    ok = True
    # planted Euro-style day (Berlin, January = UTC+1): range 08:00-09:00 = 99..101; 09:10 bar closes at 103.5 -> long at the 09:15 open 103.6
    ts, O, H, Lo, C = [], [], [], [], []
    def add(hm, op, hi, lo, cl):
        ts.append((pd.Timestamp("2026-01-08") + pd.Timedelta(minutes=hm - 60)).to_datetime64()); O.append(op); H.append(hi); Lo.append(lo); C.append(cl)
    for m in range(480, 540, 5): add(m, 100, 101, 99, 100)
    add(540, 100, 101, 99.5, 100.5); add(545, 100.5, 102, 100.4, 101.9); add(550, 101.9, 103.6, 101.8, 103.5)
    for m in range(555, 1320, 5): add(m, 103.6, 104.0, 100.5, 103.8)
    B = dict(t=np.array(ts, dtype="datetime64[m]"), o=np.array(O, float), h=np.array(H, float), l=np.array(Lo, float), c=np.array(C, float),
             spr=np.full(len(O), 2.0), roll=np.zeros(len(O), bool), kind="cfd")
    T, _ = orb(B, "Europe/Berlin", 480, 540, 1320)
    e1 = len(T) == 1 and T.iloc[0]["p0"] == 103.6 and T.iloc[0]["p1"] == 103.8 and abs(T.iloc[0]["cost"] - 2 * 0.5 * 2e-4 * 103.7) < 0.01
    ok &= e1; print(f"  [{'PASS' if e1 else 'FAIL'}] bare core: next-open entry, held to the last bar before 22:00, half-spread both sides, no stop")
    Te, _ = orb(B, "Europe/Berlin", 480, 540, 1320, stop="edge")
    e2 = len(Te) == 1 and Te.iloc[0]["p1"] == 101.0                           # lows of 100.5 hit the range-high stop at 101
    ok &= e2; print(f"  [{'PASS' if e2 else 'FAIL'}] edge-stop variant stops at the range high")
    Tw, _ = orb(B, "Europe/Berlin", 480, 540, 1320, stop="wide")
    e3 = len(Tw) == 1 and Tw.iloc[0]["p1"] == 103.8                          # 2x range = 4 below 103.6 = 99.6, never hit
    ok &= e3; print(f"  [{'PASS' if e3 else 'FAIL'}] wide-stop variant (2 x range) not hit")
    B2 = dict(B); keep = np.r_[np.arange(0, 3), np.arange(12, len(O))]; B2 = {k: (v[keep] if isinstance(v, np.ndarray) else v) for k, v in B.items()}
    T2, cov = orb(B2, "Europe/Berlin", 480, 540, 1320)
    e4 = len(T2) == 0 and not cov["ok"].iloc[0]; ok &= e4; print(f"  [{'PASS' if e4 else 'FAIL'}] range coverage < 50 min -> no trade")
    print("ALL PASS" if ok else "FAILURES"); return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--self-test"]: sys.exit(0 if self_test() else 1)
    if not self_test(): sys.exit("self-test failed")
    if a == ["run"]: run()
