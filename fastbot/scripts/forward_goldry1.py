#!/usr/bin/env python3
"""forward_goldry1.py -- FORWARD_BATCH2 part 3 (PREREGISTRATION_FORWARD_BATCH2.md): weekly paper record of GOLDRY1 (gold's snap-back after
drifting from real yields). PAPER ONLY. Stdlib only. FRED key from ~/.fred_key (never printed); read-only.

    python3 forward_goldry1.py --self-test   residuals equal the frozen oilgold_run.py goldry construction (pandas cross-check where available)
    python3 forward_goldry1.py --tick        refresh DFII10 from FRED, then append completed Fridays to data/forward_goldry1.csv
    python3 forward_goldry1.py --status

Residual (exactly oilgold_run.goldry): Friday gold = the close of the 15:45 New York 15m bar (OANDA XAU mid, data/v24 bid/ask), log price lg.
ry = the latest DFII10 dated BEFORE that Friday. g4 = lg - lg 4 Fridays earlier; dy4 likewise. OLS g4 ~ dy4 over the previous 104 Fridays
(>= 80 valid) gives residual = g4 - fitted.
Paper rule (FORWARD_BATCH2, fixed now): position for the next week = -sign(residual) x 0.10 / sigma, where sigma = the sd of the last 52 weekly
log returns x sqrt 52. Each Friday row records the return earned over the ending week by the position set the previous Friday.
Mechanical note: the spec says DFII10 is refreshed by the Mac's existing FRED step; that step does not include DFII10, so this recorder
refreshes data/gold/DFII10.csv itself (append-only).
Start: Friday 2026-10-16.
I am not a financial adviser. This is a measurement, not a recommendation."""
import csv, datetime as dt, hashlib, json, math, os, subprocess, sys, urllib.parse
from zoneinfo import ZoneInfo
VERSION = "1.0"
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, "..")
SPEC = os.path.join(FB, "PREREGISTRATION_FORWARD_BATCH2.md"); SPEC_SHA = "65d539aa8303972316d182e91b757977f0f2d990755d91e25d3e571f7acb89fa"
BID, ASK = (os.path.join(FB, "data", "v24", f"xauusd_{s}_15m.csv") for s in ("bid", "ask"))
RY = os.path.join(FB, "data", "gold", "DFII10.csv"); LED = os.path.join(FB, "data", "forward_goldry1.csv")
START = dt.date(2026, 10, 16); NY, UTC = ZoneInfo("America/New_York"), dt.timezone.utc
COLS = ["friday", "gold", "dfii10", "g4", "dy4", "residual", "sigma", "position_next_week", "ret_week_ending", "pos_week_ending", "pnl_week_ending", "written_utc", "version"]
NAN = float("nan")


def pin():
    if hashlib.sha256(open(SPEC, "rb").read()).hexdigest() != SPEC_SHA: sys.exit("REFUSING: PREREGISTRATION_FORWARD_BATCH2.md changed")


def fridays_gold():
    def rd(p):
        out = {}
        with open(p) as f:
            r = csv.reader(f); next(r)
            for x in r: out[x[0]] = float(x[4])
        return out
    b, a = rd(BID), rd(ASK); px = {}
    for k in b:
        if k not in a: continue
        t = dt.datetime.strptime(k[:16], "%Y-%m-%d %H:%M").replace(tzinfo=UTC).astimezone(NY)
        if t.hour == 15 and t.minute == 45 and t.weekday() == 4: px.setdefault(t.date(), (b[k] + a[k]) / 2)
    return px


def read_ry():
    out = []
    with open(RY) as f:
        for r in csv.DictReader(f):
            k = [c for c in r if c.lower() != "date" and c.lower() != "observation_date"]
            dk = "date" if "date" in r else ("observation_date" if "observation_date" in r else list(r)[0])
            try: out.append((dt.date.fromisoformat(r[dk][:10]), float(r[k[-1]])))
            except ValueError: pass
    return sorted(out)


def build(px, ry):
    ds = sorted(px); rows = []; j = 0; last = None
    for d in ds:
        while j < len(ry) and ry[j][0] < d: last = ry[j][1]; j += 1
        if last is not None: rows.append([d, math.log(px[d]), last])
    n = len(rows); g4 = [NAN] * n; dy4 = [NAN] * n; res = [NAN] * n
    for i in range(4, n): g4[i] = rows[i][1] - rows[i - 4][1]; dy4[i] = rows[i][2] - rows[i - 4][2]
    for i in range(108, n):
        h = [(dy4[k], g4[k]) for k in range(i - 104, i) if g4[k] == g4[k] and dy4[k] == dy4[k]]
        if len(h) < 80 or g4[i] != g4[i] or dy4[i] != dy4[i]: continue
        mx = sum(x for x, _ in h) / len(h); my = sum(y for _, y in h) / len(h)
        sxx = sum((x - mx) ** 2 for x, _ in h); b1 = sum((x - mx) * (y - my) for x, y in h) / sxx; b0 = my - b1 * mx
        res[i] = g4[i] - (b0 + b1 * dy4[i])
    return rows, g4, dy4, res


def refresh_ry():
    p = os.path.expanduser("~/.fred_key"); k = open(p).read().strip() if os.path.exists(p) else ""
    if not k: print("no ~/.fred_key -- DFII10 not refreshed"); return
    last = max(d for d, _ in read_ry()); start = (last + dt.timedelta(days=1)).isoformat()
    url = "https://api.stlouisfed.org/fred/series/observations?" + urllib.parse.urlencode(dict(series_id="DFII10", api_key=k, file_type="json", observation_start=start))
    r = subprocess.run(["curl", "-sS", "--fail", "--max-time", "60", url], capture_output=True, text=True)
    if r.returncode != 0: print("FRED refresh failed (non-fatal)"); return
    try:
        obs = [o for o in json.loads(r.stdout).get("observations", []) if o["value"] not in (".", "")]
    except (ValueError, AttributeError, KeyError, TypeError) as e:
        print(f"FRED refresh bad response (non-fatal): {type(e).__name__}"); return
    hdr = open(RY).readline().strip().split(",")
    with open(RY, "a") as f:
        for o in obs: f.write(f"{o['date']},{o['value']}\n" if len(hdr) == 2 else ",".join([o["date"]] + [o["value"]] * (len(hdr) - 1)) + "\n")
    print(f"DFII10 +{len(obs)} observations")


def tick():
    px = fridays_gold(); ry = read_ry(); rows, g4, dy4, res = build(px, ry)
    have = {r["friday"] for r in csv.DictReader(open(LED))} if os.path.exists(LED) else set()
    new = not os.path.exists(LED); now = dt.datetime.now(UTC).isoformat(timespec="seconds"); n = 0
    lg = [r[1] for r in rows]
    def sigma(i):
        rets = [lg[k] - lg[k - 1] for k in range(max(1, i - 51), i + 1)]
        if len(rets) < 52: return NAN
        m = sum(rets) / 52; return math.sqrt(sum((x - m) ** 2 for x in rets) / 51) * math.sqrt(52)
    pos = [(-math.copysign(1, res[i]) * 0.10 / sigma(i)) if res[i] == res[i] and sigma(i) == sigma(i) and res[i] != 0 else 0.0 for i in range(len(rows))]
    with open(LED, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(COLS)
        for i, r in enumerate(rows):
            d = r[0]
            if d < START or d.isoformat() in have: continue
            if d >= dt.datetime.now(NY).date() and dt.datetime.now(NY).hour < 17: continue
            ret = lg[i] - lg[i - 1]; pp = pos[i - 1]
            w.writerow([d.isoformat(), f"{math.exp(r[1]):.2f}", r[2], f"{g4[i]:.6f}", f"{dy4[i]:.4f}", f"{res[i]:.6f}", f"{sigma(i):.4f}", f"{pos[i]:+.4f}",
                        f"{ret:+.6f}", f"{pp:+.4f}", f"{pp * ret:+.6f}", now, VERSION]); n += 1
    print(f"forward_goldry1: +{n} rows")


def self_test():
    ok = True
    px = fridays_gold(); ry = read_ry(); rows, g4, dy4, res = build(px, ry)
    try:
        import numpy as np, pandas as pd
        W = pd.DataFrame([(r[0], r[1], r[2]) for r in rows], columns=["d", "lg", "ry"]).set_index("d")
        W["g4"] = W.lg - W.lg.shift(4); W["dy4"] = W.ry - W.ry.shift(4); ref = pd.Series(np.nan, index=W.index)
        for i in range(108, len(W)):                                         # the frozen oilgold_run.goldry loop, verbatim logic
            h = W.iloc[i - 104:i].dropna(subset=["g4", "dy4"])
            if len(h) < 80 or pd.isna(W.dy4.iloc[i]) or pd.isna(W.g4.iloc[i]): continue
            X = np.c_[np.ones(len(h)), h.dy4]; b = np.linalg.lstsq(X, h.g4, rcond=None)[0]; ref.iloc[i] = W.g4.iloc[i] - (b[0] + b[1] * W.dy4.iloc[i])
        mine = np.array(res); err = np.nanmax(np.abs(mine - ref.to_numpy())); same_nan = (np.isnan(mine) == ref.isna().to_numpy()).all()
        e1 = err < 1e-10 and same_nan; print(f"  [{'PASS' if e1 else 'FAIL'}] residuals equal the frozen goldry construction on {int((~ref.isna()).sum())} Fridays (max diff {err:.1e})")
    except ImportError:
        e1 = sum(1 for x in res if x == x) > 500; print(f"  [{'PASS' if e1 else 'FAIL'}] residual series builds (pandas absent: cross-check skipped)")
    ok &= e1
    e2 = all(r[0].weekday() == 4 for r in rows) and len(rows) > 900; ok &= e2; print(f"  [{'PASS' if e2 else 'FAIL'}] {len(rows)} Fridays, all Fridays")
    print("ALL PASS" if ok else "FAILURES"); return ok


if __name__ == "__main__":
    pin(); a = sys.argv[1:]
    if a == ["--self-test"]: sys.exit(0 if self_test() else 1)
    if a == ["--tick"]: refresh_ry(); tick(); sys.exit(0)
    if a == ["--status"]: print((sum(1 for _ in open(LED)) - 1) if os.path.exists(LED) else 0, "rows"); sys.exit(0)
    print(__doc__)
