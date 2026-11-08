#!/usr/bin/env python3
"""aiind_run.py -- the AIIND batch (PREREGISTRATION_AIIND.md): AIKNN1 (lastguru VWMA + kNN) and AIMA1 (Zeiierman AI MA).
    python3 aiind_run.py prep ES 2019          one futures symbol-year -> data/aiind/fut/ES_2019.npz (5m, in-year back-adjusted)
    python3 aiind_run.py prep-topup ES         the Sep-Oct 2026 top-up -> data/aiind/fut/ES_2026b.npz
    python3 aiind_run.py verify                port check against the TradingView exports in data/aiind/tv/ (entries / states only)
    python3 aiind_run.py aiknn1                run once -> data/aiind/run_aiknn1.log
    python3 aiind_run.py aima1                 run once -> data/aiind/run_aima1.log
I am not a financial adviser. This is a measurement, not a recommendation."""
import glob, hashlib, io, math, os, sys, zipfile
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, HERE)


class _Lazy:                       # the ports need numba; 'prep' (run on the Mac's VM) does not
    def __getattr__(self, k):
        import aiind_port; return getattr(aiind_port, k)


P = _Lazy()
D = os.path.join(FB, "data", "aiind"); FUT = os.path.join(FB, "..", "flows", "data", "futures")
SPEC = os.path.join(FB, "PREREGISTRATION_AIIND.md"); SPEC_SHA = "bbc0ff63f41a456b683c6b471bcb2d901ca0b4a2a87113858fe173fa779dc52a"
DISC = "I am not a financial adviser. This is a measurement, not a recommendation."
TICK = {"ES": (0.25, 50.0), "NQ": (0.25, 20.0)}; COMM = 2.25
FIVE = 300


def to_unix(x, utc=True):
    """datetime-like Series -> int64 unix seconds, whatever resolution pandas inferred."""
    d = pd.to_datetime(x, utc=utc)
    if utc: d = d.dt.tz_convert(None)
    return d.to_numpy().astype("datetime64[s]").astype(np.int64)


def pin():
    if hashlib.sha256(open(SPEC, "rb").read()).hexdigest() != SPEC_SHA: sys.exit("PREREGISTRATION_AIIND.md changed -- refused")


# ------------------------------------------------------------------ data
def load_btc():
    rows = []
    for z in sorted(glob.glob(os.path.join(D, "binance", "BTCUSDT-5m-*.zip"))):
        with zipfile.ZipFile(z) as f:
            txt = f.read(f.namelist()[0]).decode()
        a = pd.read_csv(io.StringIO(txt), header=None, usecols=range(6))
        if not str(a.iloc[0, 0]).strip().lstrip("-").isdigit(): a = a.iloc[1:]          # tolerate a header row
        rows.append(a)
    df = pd.concat(rows).astype(float); t = df[0].to_numpy()
    t = np.where(t > 1e14, t / 1e6, t / 1e3)                                               # Binance spot moved to microseconds in 2025
    out = pd.DataFrame({"t": t.astype(np.int64), "o": df[1].to_numpy(), "h": df[2].to_numpy(), "l": df[3].to_numpy(), "c": df[4].to_numpy(), "v": df[5].to_numpy()})
    return out.drop_duplicates("t").sort_values("t").reset_index(drop=True)


def _resample_1m(df):
    """df: 1m rows (ts seconds, instrument_id, o,h,l,c,v). Back-adjust within the frame to its LAST contract, then 5m bars."""
    df = df.sort_values("ts").reset_index(drop=True)
    iid = df["instrument_id"].to_numpy(); sw = np.flatnonzero(iid[1:] != iid[:-1]) + 1
    adj = np.zeros(len(df)); gaps = []
    for k in sw:
        g = df["o"].iat[k] - df["c"].iat[k - 1]; gaps.append(g); adj[:k] += g
    for col in ("o", "h", "l", "c"): df[col] = df[col] + adj
    b = (df["ts"] // FIVE) * FIVE
    g = df.groupby(b)
    out = pd.DataFrame({"t": g["ts"].first().index.to_numpy(), "o": g["o"].first().to_numpy(), "h": g["h"].max().to_numpy(),
                        "l": g["l"].min().to_numpy(), "c": g["c"].last().to_numpy(), "v": g["volume"].sum().to_numpy()})
    return out, df["instrument_id"].iat[0], df["instrument_id"].iat[-1], float(sum(gaps)), len(sw)


def _read_fut_csv(p):
    df = pd.read_csv(p, usecols=["ts_event", "instrument_id", "open", "high", "low", "close", "volume"])
    df["ts"] = to_unix(df["ts_event"])
    return df.rename(columns={"open": "o", "high": "h", "low": "l", "close": "c"})[["ts", "instrument_id", "o", "h", "l", "c", "volume"]]


def prep(sym, year, topup=False):
    p = os.path.join(D, f"{sym}_topup.csv") if topup else os.path.join(FUT, f"{sym}_{year}.csv")
    df = _read_fut_csv(p)
    if topup: df = df[df["ts"] >= pd.Timestamp("2026-09-01", tz="UTC").timestamp()]
    raw_first = df.sort_values("ts").iloc[0]; raw_last = df.sort_values("ts").iloc[-1]
    bars, i0, i1, insum, nsw = _resample_1m(df)
    os.makedirs(os.path.join(D, "fut"), exist_ok=True)
    name = f"{sym}_2026b" if topup else f"{sym}_{year}"
    np.savez(os.path.join(D, "fut", name + ".npz"), t=bars.t.to_numpy(), o=bars.o.to_numpy(), h=bars.h.to_numpy(), l=bars.l.to_numpy(),
             c=bars.c.to_numpy(), v=bars.v.to_numpy(), first_iid=i0, last_iid=i1, first_open_raw=raw_first["o"], last_close_raw=raw_last["c"], insum=insum)
    print(f"{name}: {len(bars)} 5m bars, {nsw} contract switches")


def load_fut(sym):
    fs = sorted(glob.glob(os.path.join(D, "fut", f"{sym}_*.npz")))
    parts = [dict(np.load(f)) for f in fs]
    # cross-file switches: gap between the last raw close of one file and the first raw open of the next
    # each file is already adjusted to its own last contract; everything before file k also needs file k's in-file gaps
    # and the gap at the k-1 -> k boundary when the contract changed there
    tot = 0.0
    for k in range(len(parts) - 1, -1, -1):
        for col in ("o", "h", "l", "c"): parts[k][col] = parts[k][col] + tot
        if k > 0:
            tot += float(parts[k]["insum"])
            if int(parts[k]["first_iid"]) != int(parts[k - 1]["last_iid"]):
                tot += float(parts[k]["first_open_raw"]) - float(parts[k - 1]["last_close_raw"])
    df = pd.DataFrame({c: np.concatenate([p[c] for p in parts]) for c in ("t", "o", "h", "l", "c", "v")})
    return df.drop_duplicates("t").sort_values("t").reset_index(drop=True)


def resample(df, sec):
    b = (df.t // sec) * sec; g = df.groupby(b)
    return pd.DataFrame({"t": g.t.first().index.to_numpy(), "o": g.o.first().to_numpy(), "h": g.h.max().to_numpy(), "l": g.l.min().to_numpy(),
                         "c": g.c.last().to_numpy(), "v": g.v.sum().to_numpy()})


# ------------------------------------------------------------------ trading
def trades(df, target, cost_bp, start=None, end=None, flat_start=None):
    """target[t] decided at the close of bar t, filled at the open of bar t+1. Returns entries (time, side, net bp) for trades entered in [start, end]."""
    t, o, c = df.t.to_numpy(), df.o.to_numpy(), df.c.to_numpy(); tg = np.asarray(target, float).copy()
    if flat_start is not None:
        i0 = np.searchsorted(t, flat_start)
        base = tg[i0 - 1] if i0 > 0 else 0.0
        # flat at the start of W: hold 0 until the first change of the target inside W
        k = i0
        while k < len(tg) and tg[k] == base: tg[k] = 0.0; k += 1
        tg[:i0] = 0.0
    out = []; pos = 0.0; ent = None
    for i in range(len(tg) - 1):
        if tg[i] != pos:
            px = o[i + 1]
            if pos != 0: out.append((ent[0], pos, (pos * (px / ent[1] - 1)) * 1e4 - 2 * cost_bp(ent[1]), t[i + 1]))
            pos = tg[i]; ent = (t[i + 1], px) if pos != 0 else None
    if pos != 0: out.append((ent[0], pos, (pos * (c[-1] / ent[1] - 1)) * 1e4 - 2 * cost_bp(ent[1]), t[-1]))
    tr = pd.DataFrame(out, columns=["t_in", "side", "net_bp", "t_out"])
    if start is not None: tr = tr[(tr.t_in >= start) & (tr.t_in <= end)]
    return tr


def daily_pnl(df, target, cost_bp, start, end, flat_start=None):
    t, o = df.t.to_numpy(), df.o.to_numpy(); tg = np.asarray(target, float).copy()
    if flat_start is not None:
        i0 = np.searchsorted(t, flat_start); base = tg[i0 - 1] if i0 > 0 else 0.0; k = i0
        while k < len(tg) and tg[k] == base: tg[k] = 0.0; k += 1
        tg[:i0] = 0.0
    held = np.r_[0.0, tg[:-1]]                                   # position over bar i (filled at its open)
    r = np.r_[o[1:] / o[:-1] - 1, 0.0] * 1e4 * held
    trade = np.abs(np.diff(np.r_[0.0, held])) * np.array([cost_bp(x) for x in o])
    d = pd.Series(r - trade, index=pd.to_datetime(t, unit="s").normalize())
    d = d[(t >= start) & (t <= end)]
    return d.groupby(level=0).sum()


def cluster_t(x, groups):
    x = np.asarray(x, float); n = len(x)
    if n < 3: return np.nan, np.nan
    m = x.mean(); e = pd.Series(x - m).groupby(np.asarray(groups)).sum()
    se = math.sqrt((e ** 2).sum()) / n
    return m, (m / se if se > 0 else np.nan)


def tstat(x):
    x = np.asarray(x, float); return x.mean() / (x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else np.nan


def ts(s): return int(pd.Timestamp(s, tz="UTC").timestamp())


def summ(tr, label):
    m, t = cluster_t(tr.net_bp, pd.to_datetime(tr.t_in, unit="s").dt.date)
    return m, t, f"{label}: n {len(tr)} trades; net {m:+.2f} bp/trade (day-clustered t {t:+.2f}); win {np.mean(tr.net_bp > 0) * 100:.0f}%"


def btc_cost(bp): return lambda px: bp


def fut_cost(sym):
    tick, mult = TICK[sym]
    return lambda px: (0.5 * tick + COMM / mult) / px * 1e4


# ------------------------------------------------------------------ AIKNN1
def aiknn1():
    pin(); LOG = os.path.join(D, "run_aiknn1.log")
    if os.path.exists(LOG): sys.exit("already run")
    W0, W1 = ts("2021-07-01"), ts("2026-09-30 23:59")
    L = ["AIKNN1 -- lastguru 'VWMA with kNN Machine Learning: MFI/ADX', author defaults (PREREGISTRATION_AIIND.md sha bbc0ff63...)", "  " + DISC, ""]
    btc = load_btc(); L.append(f"  BTCUSDT 5m: {len(btc):,} bars {pd.to_datetime(btc.t.iat[0], unit='s')} -> {pd.to_datetime(btc.t.iat[-1], unit='s')}")
    args = [btc[k].to_numpy() for k in "ohlcv"]
    tgt, dg = P.knn_signals(*args); tgt0, _ = P.knn_signals(*args, apply=False)
    tr = trades(btc, tgt, btc_cost(10), W0, W1); m, t, line = summ(tr, "PRIMARY BTCUSDT 5m, 2021-07 -> 2026-09, 10 bp/side"); L.append("  " + line)
    pers = [("2021-07-01", "2022-12-31 23:59"), ("2023-01-01", "2024-12-31 23:59"), ("2025-01-01", "2026-09-30 23:59")]
    pm = []
    for a, b in pers:
        s = tr[(tr.t_in >= ts(a)) & (tr.t_in <= ts(b))]; mm, tt, _ = summ(s, ""); pm.append(mm)
        L.append(f"    {a[:7]} -> {b[:7]}: n {len(s)}; net {mm:+.2f} bp (t {tt:+.2f})")
    g1 = m > 0 and t >= 2.0; g2 = all(x > 0 for x in pm)
    for bp in (2, 0):
        L.append("    " + summ(trades(btc, tgt, btc_cost(bp), W0, W1), f"same at {bp} bp/side")[2])
    gross = trades(btc, tgt, btc_cost(0), W0, W1)
    L.append(f"    trades per day {len(tr) / ((W1 - W0) / 86400):.1f}; mean holding {((tr.t_out - tr.t_in) / 3600).mean():.1f} h; gross {gross.net_bp.mean():+.2f} bp/trade")
    # KNN-ADD
    d1 = daily_pnl(btc, tgt, btc_cost(10), W0, W1); d0 = daily_pnl(btc, tgt0, btc_cost(10), W0, W1)
    dd = (d1 - d0).dropna(); tadd = tstat(dd)
    tr0 = trades(btc, tgt0, btc_cost(10), W0, W1)
    L += ["", "  " + summ(tr0, "unfiltered VWMA crossover (filter off), same window, 10 bp/side")[2],
          f"  KNN-ADD: filtered minus unfiltered daily net {dd.mean():+.1f} bp/day over {len(dd)} days (t {tadd:+.2f}) -> {'ML HELPS' if dd.mean() > 0 and tadd >= 2 else 'ML DOES NOT HELP'}"]
    pre = trades(btc, tgt, btc_cost(10), ts("2017-08-17"), ts("2021-06-30 23:59"))
    L += ["", "  reported: author's own period (pre-publication) " + summ(pre, "BTCUSDT 5m 2017-08 -> 2021-06, 10 bp/side")[2]]
    for sym in ("NQ", "ES"):
        f = load_fut(sym); ta, _ = P.knn_signals(*[f[k].to_numpy() for k in "ohlcv"])
        L.append("  reported: " + summ(trades(f, ta, fut_cost(sym), W0, W1), f"{sym} 5m 2021-07 -> 2026-09, half tick + $2.25/side")[2])
    L += ["", f"  G1 {'PASS' if g1 else 'FAIL'}  G2 {'PASS' if g2 else 'FAIL'}  -> AIKNN1 {'PASS' if g1 and g2 else 'FAIL'}"]
    open(LOG, "w").write("\n".join(L) + "\n"); print("\n".join(L))


# ------------------------------------------------------------------ AIMA1
def aima1():
    pin(); LOG = os.path.join(D, "run_aima1.log")
    if os.path.exists(LOG): sys.exit("already run")
    W0, W1 = ts("2026-06-08"), ts("2026-10-16 23:59")
    L = ["AIMA1 -- Zeiierman 'AI Source Switching Moving Average' (AI Supertrend flips), author defaults (PREREGISTRATION_AIIND.md sha bbc0ff63...)", "  " + DISC, ""]
    mk = {"BTCUSDT": (load_btc(), btc_cost(10)), "NQ": (load_fut("NQ"), fut_cost("NQ")), "ES": (load_fut("ES"), fut_cost("ES"))}
    allt = []; per = {}; dif = []
    for name, (df5, cf) in mk.items():
        for tf, sec in (("5m", 300), ("15m", 900), ("1h", 3600)):
            df = df5 if sec == 300 else resample(df5, sec)
            arr = [df[k].to_numpy() for k in "ohlc"]
            Dai, dg = P.aima_signals(*arr)
            tr = trades(df, Dai, cf, W0, W1, flat_start=W0)
            pre = (df.t >= W0 - 90 * 86400) & (df.t < W0)
            d = float(np.median(dg["drive"][pre.to_numpy()])); Dc, _ = P.aima_signals(*arr, control=d)
            trc = trades(df, Dc, cf, W0, W1, flat_start=W0)
            if tf == "5m":
                allt.append(tr.assign(mkt=name)); m, t, line = summ(tr, f"{name} 5m (primary)"); per[name] = m; L.append("  " + line)
                L.append("    control (close source, fixed band x%.2f): " % (1.7 * (1 + 0.8 * (1 - d))) + summ(trc, "")[2].lstrip(": "))
                da = daily_pnl(df, Dai, cf, W0, W1, flat_start=W0); dc = daily_pnl(df, Dc, cf, W0, W1, flat_start=W0)
                dif.append((da - dc).dropna())
                srcs = np.bincount(dg["best"][(df.t >= W0).to_numpy()], minlength=4) / max(1, (df.t >= W0).sum())
                L.append("    source used in W: " + "  ".join(f"{n_} {x * 100:.0f}%" for n_, x in zip("OHLC", srcs)))
                pre_tr = trades(df, Dai, cf, int(df.t.iat[0]), W0 - 1)
                L.append("    reported, author's design period: " + summ(pre_tr, "")[2].lstrip(": "))
                low = trades(df, Dai, (lambda px: 2.0) if name == "BTCUSDT" else (lambda px: 0.0), W0, W1, flat_start=W0)
                L.append("    reported, " + ("2 bp/side" if name == "BTCUSDT" else "zero cost") + ": " + summ(low, "")[2].lstrip(": "))
            else:
                L.append(f"    reported {tf}: " + summ(tr, "")[2].lstrip(": ") + "   | control: " + summ(trc, "")[2].lstrip(": "))
    A = pd.concat(allt); m, t = cluster_t(A.net_bp, pd.to_datetime(A.t_in, unit="s").dt.date)
    g1 = m > 0 and t >= 2.0; g2 = all(v > 0 for v in per.values())
    dd = pd.concat(dif); tadd = tstat(dd)
    L += ["", f"  POOLED 5m: n {len(A)} trades; net {m:+.2f} bp/trade (day-clustered t {t:+.2f})",
          f"  AI-ADD: AI minus control daily net {dd.mean():+.1f} bp/day over {len(dd)} market-days (t {tadd:+.2f}) -> {'AI HELPS' if dd.mean() > 0 and tadd >= 2 else 'AI DOES NOT HELP'}",
          "", f"  G1 {'PASS' if g1 else 'FAIL'}  G2 {'PASS' if g2 else 'FAIL'}  -> AIMA1 {'PASS' if g1 and g2 else 'FAIL'}"]
    open(LOG, "w").write("\n".join(L) + "\n"); print("\n".join(L))


# ------------------------------------------------------------------ port check against TradingView exports (entries / states only)
def _tv_time(col):
    t = pd.to_numeric(col, errors="coerce")
    if t.notna().all(): return t.astype(np.int64).to_numpy()
    return to_unix(col)


def verify():
    """Files Dave exports from TradingView, BINANCE:BTCUSDT 5m, author defaults, saved in data/aiind/tv/:
         lastguru_chart.csv   (Export chart data, same chart as the strategy)   lastguru_trades.csv (List of trades)
         zeiierman_chart.csv  (Export chart data with the indicator on)
       The port is started at the chart's first bar, as TradingView is. Entries / states are compared, never returns."""
    btc = load_btc(); out = []; tv = os.path.join(D, "tv")
    pc, pt, pz = (os.path.join(tv, f) for f in ("lastguru_chart.csv", "lastguru_trades.csv", "zeiierman_chart.csv"))
    if os.path.exists(pc) and os.path.exists(pt):
        ch = pd.read_csv(pc); t0 = int(_tv_time(ch.iloc[:, 0])[0])
        sub = btc[btc.t >= t0].reset_index(drop=True)
        tg, _ = P.knn_signals(*[sub[k].to_numpy() for k in "ohlcv"])
        fills = {}
        for i in range(len(tg) - 1):
            if tg[i] != (tg[i - 1] if i > 0 else 0): fills[int(sub.t.iat[i + 1])] = int(tg[i])
        x = pd.read_csv(pt); tcol = [c for c in x.columns if "date" in c.lower() or "time" in c.lower()][0]
        ycol = [c for c in x.columns if c.lower().startswith("type")][0]
        e = x[x[ycol].astype(str).str.lower().str.startswith("entry")].copy()
        side = np.where(e[ycol].str.lower().str.contains("long"), 1, -1)
        loc = to_unix(e[tcol], utc=False)                         # naive local chart time, treated as if UTC; offset searched below
        best = (0.0, 0)
        for off in range(-14, 15):                                # the trade list is in the chart's time zone: find the hour offset
            hit = np.mean([fills.get(int(a - off * 3600)) == int(sd) for a, sd in zip(loc, side)])
            if hit > best[0]: best = (hit, off)
        out.append(f"  lastguru: {len(e)} TradingView entries from {pd.to_datetime(t0, unit='s')}; {best[0] * 100:.1f}% match the port on bar and side"
                   f" (chart time zone UTC{best[1]:+d}) -> {'OK' if best[0] >= 0.95 else 'NOT VERIFIED'}")
    if os.path.exists(pz):
        x = pd.read_csv(pz); t = _tv_time(x.iloc[:, 0])
        up = [c for c in x.columns if "supertrend up" in c.lower()][0]; st = np.where(x[up].notna(), 1, -1)
        sub = btc[btc.t >= int(t[0])].reset_index(drop=True)
        Dz, _ = P.aima_signals(*[sub[k].to_numpy() for k in "ohlc"])
        m = pd.Series(Dz, index=sub.t.to_numpy()).reindex(t).to_numpy()
        ok = ~np.isnan(m); skip = 300
        hit = np.mean(m[ok][skip:] == st[ok][skip:])
        out.append(f"  Zeiierman: {int(ok.sum())} bars from {pd.to_datetime(int(t[0]), unit='s')}; trend state matches on {hit * 100:.1f}% after a 300-bar warm-up"
                   f" -> {'OK' if hit >= 0.95 else 'NOT VERIFIED'}")
    txt = "\n".join(["port check vs TradingView (PREREGISTRATION_AIIND.md)"] + (out or ["  no exports found in data/aiind/tv/"]))
    os.makedirs(D, exist_ok=True); open(os.path.join(D, "verify_aiind.log"), "w").write(txt + "\n"); print(txt)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["prep"]: prep(a[1], int(a[2]))
    elif a[:1] == ["prep-topup"]: prep(a[1], 2026, topup=True)
    elif a == ["verify"]: verify()
    elif a == ["aiknn1"]: aiknn1()
    elif a == ["aima1"]: aima1()
    else: print(__doc__)
